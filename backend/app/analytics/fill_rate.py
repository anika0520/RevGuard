"""Supply-side rate formulas."""

from __future__ import annotations


def fill_rate(responses: float, requests: float) -> float:
    """fill_rate = responses / requests * 100"""
    if requests <= 0:
        return 0.0
    return responses / requests * 100.0
