"""Quantized P1 interoception threshold robustness (DEV-only, pure).

A model FatigueObservation at quantum 0.01 is not an exact fatigue truth:
a reading 0.05 represents values around [0.045, 0.055]. A strict
positive-threshold gate must not treat the lower edge as >=0.05.
Additionally a configurable predeclared safety margin may be applied.
This never changes the original pinned P1 physics or issues an Action.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

NOMINAL_THRESHOLD = 0.05
SENSOR_QUANTUM = 0.01
DEV_MARGIN = 0.025


class P1SensorThresholdRejected(ValueError):
    pass


@dataclass(frozen=True)
class ThresholdChoice:
    reading: float
    quantum: float
    threshold: float
    margin: float
    admissible_lower: float
    admissible_upper: float
    nominal_rest: bool
    uncertainty_guard_rest: bool
    safety_margin_rest: bool
    abstain_due_to_quantization: bool
    safety_margin_suppressed_rest: bool

    def to_dict(self) -> dict:
        return asdict(self)


def sensitivity(reading: float, *, quantum: float = SENSOR_QUANTUM,
                threshold: float = NOMINAL_THRESHOLD,
                margin: float = DEV_MARGIN) -> ThresholdChoice:
    if (
        type(reading) is not float or not math.isfinite(reading)
        or reading < 0 or reading > 1
        or type(quantum) is not float or not 0 < quantum <= 0.1
        or type(threshold) is not float or not 0 < threshold <= 1
        or type(margin) is not float or not 0 <= margin <= 0.1
        or not all(math.isfinite(x) for x in (quantum, threshold, margin))
    ):
        raise P1SensorThresholdRejected("invalid quantified virtual fatigue input")
    lower = max(0.0, reading - quantum / 2)
    upper = min(1.0, reading + quantum / 2)
    nominal = reading >= threshold
    guard = lower >= threshold
    safe = lower >= threshold + margin
    return ThresholdChoice(
        reading=reading, quantum=quantum, threshold=threshold, margin=margin,
        admissible_lower=lower, admissible_upper=upper,
        nominal_rest=nominal,
        uncertainty_guard_rest=guard,
        safety_margin_rest=safe,
        abstain_due_to_quantization=nominal and not guard,
        safety_margin_suppressed_rest=nominal and not safe,
    )
