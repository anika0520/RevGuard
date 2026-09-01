"""What-if simulator: score a hypothetical targeting change before anyone approves it."""

from __future__ import annotations

from ..analytics import revenue_risk
from ..models import Campaign, CampaignHealthRecord, RevenueRisk
from ..store.world import DEVICES, GEOS, PLATFORMS, TYPES

UNIVERSE = {
    "platforms": len(PLATFORMS),
    "geos": len(GEOS),
    "devices": len(DEVICES),
    "content_categories": len(TYPES),
}
# Not every dimension moves addressable supply equally.
ELASTICITY = {"platforms": 0.55, "geos": 0.30, "devices": 0.25, "content_categories": 0.20}


def evaluate(
    *,
    campaign: Campaign,
    record: CampaignHealthRecord,
    proposed: dict[str, list[str]],
    projected_gap: float,
) -> dict:
    current = campaign.targeting.model_dump(mode="json")
    expansion = 0.0
    deltas: list[dict] = []

    for dim, universe in UNIVERSE.items():
        now = list(current.get(dim) or [])
        new = list(proposed.get(dim, now))
        added = [v for v in new if v not in now]
        removed = [v for v in now if v not in new]
        if not added and not removed:
            continue
        share_now = max(1, len(now)) / universe
        share_new = max(1, len(new)) / universe
        change = (share_new - share_now) / max(share_now, 1e-6) * ELASTICITY[dim]
        expansion += change
        deltas.append(
            {"dimension": dim, "added": added, "removed": removed,
             "inventory_effect_pct": round(change * 100, 1)}
        )

    inventory_effect = max(-0.9, min(1.5, expansion))
    recoverable = max(0.0, min(0.85, inventory_effect * 0.6))
    gain = int(projected_gap * recoverable)
    recovery: RevenueRisk = revenue_risk.compute(
        realized_gap=0.0, projected_gap=gain, ecpm=record.ecpm
    )
    recovery.method = (
        f"Targeting change expands addressable inventory by {inventory_effect * 100:+.1f}%, "
        f"recovering {recoverable * 100:.0f}% of the {int(projected_gap):,} projected shortfall "
        f"at ${record.ecpm:.2f} eCPM."
    )
    return {
        "current": {k: current.get(k) for k in UNIVERSE},
        "proposed": {k: proposed.get(k, current.get(k)) for k in UNIVERSE},
        "deltas": deltas,
        "inventory_effect_pct": round(inventory_effect * 100, 1),
        "predicted_impression_gain": gain,
        "predicted_recovery": recovery,
        "confidence": round(min(0.94, 0.55 + abs(inventory_effect) * 0.6), 3),
    }
