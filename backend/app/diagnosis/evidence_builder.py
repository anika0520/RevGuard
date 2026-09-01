"""Builds the evidence package. Nothing reaches the AI except this.

Every downstream claim -- rule firings, cause confidences, and the LLM narrative --
must cite an EvidenceItem id from here. That is what makes the diagnosis auditable.
"""

from __future__ import annotations

from datetime import timedelta

from ..config import get_settings
from ..models import Campaign, CampaignHealthRecord, EvidenceItem, EvidencePackage


def _strength(magnitude: float, strong: float, moderate: float) -> str:
    if magnitude >= strong:
        return "STRONG"
    if magnitude >= moderate:
        return "MODERATE"
    return "WEAK"


def build(record: CampaignHealthRecord, campaign: Campaign) -> EvidencePackage:
    cfg = get_settings()
    window_end = record.ts
    window_start = window_end - timedelta(hours=cfg.current_window_hours)
    window = (
        f"{window_start.strftime('%d %b %H:%M')}-{window_end.strftime('%H:%M')} UTC "
        f"({cfg.current_window_hours}h)"
    )
    baseline_window = f"trailing {cfg.baseline_window_days} days"
    items: list[EvidenceItem] = []

    def add(**kw) -> None:
        items.append(EvidenceItem(id=f"EV-{len(items) + 1:02d}", **kw))

    add(
        metric="pacing_pct",
        label=(
            f"Delivery rate is at {record.pacing_pct:.1f}% of the required rate "
            f"({record.pacing_gap_pts:+.1f} pts vs plan)"
        ),
        current_value=record.pacing_pct,
        baseline_value=100.0,
        delta_pct=record.pacing_gap_pts,
        source="GAM",
        window=window,
        unit="%",
        strength=_strength(abs(record.pacing_gap_pts), 25, 12),
    )
    add(
        metric="delivery_pct",
        label=(
            f"Cumulative delivery is {record.delivery_pct:.1f}% of plan "
            f"({record.actual_impressions:,} of {record.expected_impressions:,} impressions)"
        ),
        current_value=record.delivery_pct,
        baseline_value=100.0,
        delta_pct=round(record.delivery_pct - 100.0, 2),
        source="GAM",
        window="flight to date",
        unit="%",
        strength=_strength(abs(record.delivery_pct - 100.0), 15, 6),
    )
    add(
        metric="fill_rate",
        label=(
            f"Fill rate {record.fill_rate:.1f}% vs {record.baseline_fill_rate:.1f}% baseline "
            f"({record.fill_deviation_pct:+.1f}%)"
        ),
        current_value=record.fill_rate,
        baseline_value=record.baseline_fill_rate,
        delta_pct=record.fill_deviation_pct,
        z_score=record.fill_z_score,
        source="SPRINGSERVE",
        window=f"{window} vs {baseline_window}",
        unit="%",
        strength=_strength(abs(record.fill_deviation_pct), 20, 8),
    )
    multiple = (
        record.error_rate / record.baseline_error_rate if record.baseline_error_rate else 1.0
    )
    add(
        metric="error_rate",
        label=(
            f"VAST error rate {record.error_rate:.2f}% vs {record.baseline_error_rate:.2f}% "
            f"baseline ({multiple:.1f}x)"
        ),
        current_value=record.error_rate,
        baseline_value=record.baseline_error_rate,
        delta_pct=record.error_deviation_pct,
        z_score=record.error_z_score,
        source="SPRINGSERVE",
        window=f"{window} vs {baseline_window}",
        unit="%",
        strength=_strength(record.error_deviation_pct, 150, 60),
    )
    add(
        metric="eligible_inventory",
        label=f"Eligible inventory {record.eligible_inventory_change_pct:+.1f}% vs baseline",
        current_value=record.eligible_inventory_change_pct,
        baseline_value=0.0,
        delta_pct=record.eligible_inventory_change_pct,
        source="ATHENA",
        window=f"{window} vs {baseline_window}",
        unit="%",
        strength=_strength(abs(record.eligible_inventory_change_pct), 25, 12),
    )

    if record.targeting_changed_recently and campaign.targeting.last_changed_at:
        hours_ago = (record.ts - campaign.targeting.last_changed_at).total_seconds() / 3600
        add(
            metric="targeting_change",
            label=(
                f"Targeting was modified {hours_ago:.0f}h ago "
                f"(platforms: {', '.join(campaign.targeting.platforms) or 'none'})"
            ),
            current_value=round(hours_ago, 1),
            source="GAM",
            window=campaign.targeting.last_changed_at.strftime("%d %b %H:%M UTC"),
            unit="hours ago",
            strength="STRONG" if hours_ago <= 24 else "MODERATE",
        )

    if record.vast_error_breakdown and record.worst_vast_code:
        top = record.worst_vast_code
        total = sum(record.vast_error_breakdown.values()) or 1
        share = record.vast_error_breakdown.get(top, 0) / total * 100
        add(
            metric="vast_error_code",
            label=(
                f"{share:.0f}% of errors are {top} concentrated on {record.worst_platform} "
                f"({record.vast_error_breakdown.get(top, 0):,} events)"
            ),
            current_value=round(share, 1),
            source="SPRINGSERVE",
            window=window,
            unit="% of errors",
            strength=_strength(share, 55, 30),
        )

    if abs(record.auction_pressure_change_pct) >= 5:
        add(
            metric="auction_pressure",
            label=f"Auction pressure {record.auction_pressure_change_pct:+.1f}% vs baseline",
            current_value=record.auction_pressure_change_pct,
            baseline_value=0.0,
            delta_pct=record.auction_pressure_change_pct,
            source="GAM",
            window=f"{window} vs {baseline_window}",
            unit="%",
            strength=_strength(abs(record.auction_pressure_change_pct), 25, 12),
        )

    if record.unique_reach_saturation >= 0.7:
        add(
            metric="reach_saturation",
            label=(
                f"Unique-reach saturation at {record.unique_reach_saturation * 100:.0f}% "
                f"against a frequency cap of {campaign.targeting.frequency_cap}"
            ),
            current_value=record.unique_reach_saturation,
            source="DERIVED",
            window=window,
            unit="ratio",
            strength=_strength(record.unique_reach_saturation * 100, 88, 75),
        )

    if record.creative_error_share >= 0.4:
        add(
            metric="creative_error_share",
            label=f"{record.creative_error_share * 100:.0f}% of errors trace to a single creative",
            current_value=record.creative_error_share,
            source="SPRINGSERVE",
            window=window,
            unit="ratio",
            strength=_strength(record.creative_error_share * 100, 60, 40),
        )

    if record.data_quality.verdict != "OK":
        add(
            metric="data_quality",
            label=(
                f"Data quality {record.data_quality.verdict} "
                f"(failed: {', '.join(record.data_quality.failed_checks) or 'none'})"
            ),
            current_value=record.data_quality.score,
            baseline_value=1.0,
            source="DERIVED",
            window=window,
            unit="score",
            strength="STRONG" if record.data_quality.verdict == "BAD" else "MODERATE",
        )

    return EvidencePackage(
        campaign_id=record.campaign_id,
        campaign_name=record.campaign_name,
        generated_at=record.ts,
        window=window,
        items=items,
        facts={
            "advertiser": record.advertiser,
            "campaign_type": record.campaign_type,
            "pacing_pct": record.pacing_pct,
            "delivery_pct": record.delivery_pct,
            "fill_rate": record.fill_rate,
            "baseline_fill_rate": record.baseline_fill_rate,
            "error_rate": record.error_rate,
            "baseline_error_rate": record.baseline_error_rate,
            "eligible_inventory_change_pct": record.eligible_inventory_change_pct,
            "auction_pressure_change_pct": record.auction_pressure_change_pct,
            "health_score": record.health_score,
            "targeting": campaign.targeting.model_dump(mode="json"),
            "worst_platform": record.worst_platform,
            "worst_vast_code": record.worst_vast_code,
            "ecpm": record.ecpm,
        },
    )


def index_by_metric(package: EvidencePackage) -> dict[str, str]:
    return {item.metric: item.id for item in package.items}
