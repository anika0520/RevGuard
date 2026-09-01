"""Revenue-at-risk. Always 'at risk', never 'lost' -- the whole point is it is recoverable."""

from __future__ import annotations

from ..config import get_settings
from ..models import RevenueRisk


def compute(
    *,
    realized_gap: float,
    projected_gap: float,
    ecpm: float,
) -> RevenueRisk:
    gap = max(0.0, realized_gap + projected_gap)
    expected = gap / 1000.0 * ecpm
    f = get_settings().revenue_risk
    method = (
        f"({int(realized_gap):,} realized gap + {int(projected_gap):,} projected gap if the "
        f"current delivery rate holds) / 1000 x ${ecpm:.2f} eCPM. Projection horizon is 7 days "
        f"or flight end, whichever is sooner. Range = expected x {f.conservative_multiplier} "
        f"(partial natural recovery) to x {f.worst_case_multiplier} (continued degradation)."
    )
    return RevenueRisk(
        impression_gap=int(gap),
        ecpm=ecpm,
        conservative=round(expected * f.conservative_multiplier, 2),
        expected=round(expected, 2),
        worst_case=round(expected * f.worst_case_multiplier, 2),
        method=method,
    )
