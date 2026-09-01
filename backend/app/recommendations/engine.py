"""Recommendation engine: cause -> concrete action, predicted gain, predicted recovery."""

from __future__ import annotations

from ..analytics import revenue_risk
from ..models import ActionType, Campaign, CampaignHealthRecord, CauseCode, Recommendation

# How much of the projected shortfall each action type typically recovers.
RECOVERY_RATIO: dict[ActionType, float] = {
    "EXPAND_TARGETING": 0.72,
    "PAUSE_TAG": 0.55,
    "RAISE_PRIORITY": 0.48,
    "ADJUST_FREQ_CAP": 0.40,
    "REPLACE_CREATIVE": 0.60,
    "INVESTIGATE_ONLY": 0.0,
}

CAUSE_TO_ACTION: dict[str, ActionType] = {
    "TARGETING_RESTRICTION": "EXPAND_TARGETING",
    "SUPPLY_SHORTAGE": "EXPAND_TARGETING",
    "VAST_PLAYBACK_ERRORS": "PAUSE_TAG",
    "GAM_COMPETITION": "RAISE_PRIORITY",
    "FREQUENCY_CAP": "ADJUST_FREQ_CAP",
    "CREATIVE_ISSUE": "REPLACE_CREATIVE",
    "BUDGET_PACING": "INVESTIGATE_ONLY",
    "DATA_QUALITY": "INVESTIGATE_ONLY",
}


def build(
    *,
    incident_id: str,
    cause: CauseCode,
    record: CampaignHealthRecord,
    campaign: Campaign,
    projected_gap: float,
    confidence: float,
) -> Recommendation:
    action = CAUSE_TO_ACTION.get(cause, "INVESTIGATE_ONLY")
    current, proposed, title = _states(action, record, campaign)
    gain = int(projected_gap * RECOVERY_RATIO[action])
    recovery = revenue_risk.compute(realized_gap=0.0, projected_gap=gain, ecpm=record.ecpm)
    recovery.method = (
        f"{gain:,} recoverable impressions ({RECOVERY_RATIO[action] * 100:.0f}% of the "
        f"{int(projected_gap):,} projected shortfall for a {action.replace('_', ' ').lower()} "
        f"action) / 1000 x ${record.ecpm:.2f} eCPM."
    )
    return Recommendation(
        incident_id=incident_id,
        title=title,
        action_type=action,
        current_state=current,
        proposed_state=proposed,
        predicted_impression_gain=gain,
        predicted_recovery=recovery,
        confidence=round(min(0.97, confidence * 0.96), 3),
        rationale=_rationale(action, record),
        requires_approval=True,
    )


def _states(
    action: ActionType, record: CampaignHealthRecord, campaign: Campaign
) -> tuple[dict, dict, str]:
    t = campaign.targeting
    if action == "EXPAND_TARGETING":
        drop = record.worst_platform if record.worst_platform in t.platforms else None
        platforms = [p for p in t.platforms if p != drop] if drop and len(t.platforms) > 1 else t.platforms
        expanded = sorted(set(platforms) | {"LG", "Fire TV"}) if not drop else platforms
        title = (
            f"Remove {drop} platform restriction"
            if drop and expanded != t.platforms
            else "Broaden platform targeting"
        )
        return (
            {"platforms": t.platforms, "geos": t.geos, "content_categories": t.content_categories},
            {"platforms": expanded, "geos": t.geos, "content_categories": t.content_categories},
            title,
        )
    if action == "PAUSE_TAG":
        return (
            {"failing_platform": record.worst_platform, "vast_code": record.worst_vast_code,
             "error_rate": record.error_rate},
            {"action": f"Pause {record.worst_platform} tags emitting {record.worst_vast_code}",
             "expected_error_rate": record.baseline_error_rate},
            f"Pause {record.worst_platform} tags emitting {record.worst_vast_code}",
        )
    if action == "RAISE_PRIORITY":
        return (
            {"priority": campaign.priority},
            {"priority": max(1, campaign.priority - 2)},
            f"Raise line item priority {campaign.priority} -> {max(1, campaign.priority - 2)}",
        )
    if action == "ADJUST_FREQ_CAP":
        cap = t.frequency_cap or 3
        return (
            {"frequency_cap": cap},
            {"frequency_cap": cap + 2},
            f"Increase frequency cap {cap} -> {cap + 2} per user/day",
        )
    if action == "REPLACE_CREATIVE":
        return (
            {"creative_error_share": record.creative_error_share},
            {"action": "Re-transcode and redeploy the failing creative"},
            "Replace the failing creative",
        )
    return ({}, {}, "Investigate before actioning delivery")


def _rationale(action: ActionType, record: CampaignHealthRecord) -> str:
    if action == "EXPAND_TARGETING":
        return (
            f"Eligible inventory is {record.eligible_inventory_change_pct:.1f}% below baseline. "
            f"Restoring addressable supply is the fastest lever on delivery rate."
        )
    if action == "PAUSE_TAG":
        return (
            f"Errors are running at {record.error_rate:.2f}% against a "
            f"{record.baseline_error_rate:.2f}% baseline. Removing the failing tags converts "
            f"wasted responses back into impressions."
        )
    if action == "RAISE_PRIORITY":
        return (
            f"Auction pressure is up {record.auction_pressure_change_pct:.1f}%. A priority bump "
            f"restores win rate without changing targeting."
        )
    if action == "ADJUST_FREQ_CAP":
        return (
            f"Reach saturation at {record.unique_reach_saturation * 100:.0f}% means the cap, not "
            f"supply, is the binding constraint."
        )
    if action == "REPLACE_CREATIVE":
        return "A single creative accounts for the majority of playback failures."
    return "Data integrity must be confirmed before any delivery change is made."
