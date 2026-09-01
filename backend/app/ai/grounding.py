"""Evidence grounding validator -- the anti-hallucination gate.

Two checks on every AI narrative:
  1. every [EV-xx] citation must exist in the evidence package
  2. every number in the prose must appear in the evidence package (1% tolerance)

Violations are rejected. One retry, then we fall back to the deterministic provider.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..models import EvidencePackage

CITATION_RE = re.compile(r"\[(EV-\d{2})\]")
NUMBER_RE = re.compile(r"(?<![\w-])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)")
TOLERANCE = 0.01


@dataclass
class GroundingResult:
    passed: bool
    violations: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)


def _allowed_numbers(package: EvidencePackage) -> set[float]:
    allowed: set[float] = {0.0, 1.0, 100.0}

    def absorb(value) -> None:
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            allowed.add(abs(round(float(value), 4)))
        elif isinstance(value, (list, tuple)):
            for v in value:
                absorb(v)
        elif isinstance(value, dict):
            for v in value.values():
                absorb(v)

    for item in package.items:
        for value in (item.current_value, item.baseline_value, item.delta_pct, item.z_score):
            absorb(value)
        for token in NUMBER_RE.findall(item.label):
            allowed.add(abs(float(token.replace(",", ""))))
    absorb(package.facts)
    return allowed


def validate(text: str, package: EvidencePackage, cited: list[str] | None = None) -> GroundingResult:
    valid_ids = {item.id for item in package.items}
    result = GroundingResult(passed=True)

    found = CITATION_RE.findall(text)
    result.citations = list(dict.fromkeys(found))
    for eid in set(found) | set(cited or []):
        if eid not in valid_ids:
            result.violations.append(f"Citation {eid} does not exist in the evidence package.")

    if not found:
        result.violations.append("Narrative contains no evidence citations.")

    allowed = _allowed_numbers(package)
    prose = CITATION_RE.sub("", text)
    for token in NUMBER_RE.findall(prose):
        value = abs(float(token.replace(",", "")))
        if value <= 12 and value == int(value):
            continue  # small counts / ordinals are not metric claims
        if not any(
            abs(value - a) <= max(TOLERANCE * max(abs(a), 1.0), 0.05) for a in allowed
        ):
            result.violations.append(
                f"Number {token} in the narrative does not appear in the evidence package."
            )

    result.passed = not result.violations
    return result
