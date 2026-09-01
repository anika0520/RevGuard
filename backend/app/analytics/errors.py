"""Error-rate formulas."""

from __future__ import annotations


def error_rate(errors: float, requests: float) -> float:
    """error_rate = errors / requests * 100"""
    if requests <= 0:
        return 0.0
    return errors / requests * 100.0


def error_multiple(current: float, baseline: float) -> float:
    if baseline <= 1e-9:
        return 1.0
    return current / baseline
