"""Rolling baselines and statistical deviation. This is the 'historical memory'.

Deliberately simple: rolling mean/stddev + z-score. Defensible, explainable, and
replaceable by ML forecasting later without changing any downstream contract.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np


def rolling_mean(values: Sequence[float]) -> float:
    arr = np.asarray(list(values), dtype=float)
    return float(arr.mean()) if arr.size else 0.0


def rolling_std(values: Sequence[float]) -> float:
    arr = np.asarray(list(values), dtype=float)
    if arr.size < 2:
        return 0.0
    return float(arr.std(ddof=1))


def z_score(current: float, baseline: float, stddev: float) -> float:
    """z = (current - baseline) / stddev, guarded against a degenerate stddev."""
    if stddev < 1e-6:
        return 0.0
    return (current - baseline) / stddev


def deviation_pct(current: float, baseline: float) -> float:
    """deviation = (current - baseline) / baseline * 100"""
    if abs(baseline) < 1e-9:
        return 0.0
    return (current - baseline) / baseline * 100.0
