"""M1 follow-on: prediction-only learning vs explicitly supplied appraisal.

EXPERIMENT-LOCAL prequential 12-cell arithmetic, not an L-lane learning owner.
Only cue, action and sensor reading enter the probe. Zero reward/fitness input.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import asdict, dataclass, field
from typing import Literal

from experiments.metabolism_m1 import M1Config, M1Result, run_trial

Actions = ("WAIT", "MOVE", "FIGHT")
Preference = Literal["none", "higher", "lower"]


@dataclass
class DeltaProbe:
    """Read-only one-step action/sensor projection with fixed 4x3 capacity.

    Previous action's delta is learned from next step's sensed reading.
    The final step at starvation is censored, never learned from true E/death.
    """

    retained: bool
    counts: dict[tuple[int, str], int] = field(default_factory=dict)
    totals: dict[tuple[int, str], float] = field(default_factory=dict)
    pending: tuple[int, str, float, float] | None = None
    sum_absolute_error: float = 0.0
    scored: int = 0
    sensor_min: float = math.inf
    sensor_max: float = -math.inf

    def estimate(self, cue: int, action: str) -> float:
        key = (cue, action)
        count = self.counts.get(key, 0)
        return self.totals[key] / count if count else 0.0

    def arrive(self, reading: float) -> None:
        if not math.isfinite(reading):
            raise ValueError("non-finite sensed reading")
        self.sensor_min = min(self.sensor_min, reading)
        self.sensor_max = max(self.sensor_max, reading)
        if self.pending is None:
            return
        cue, action, previous, forecast = self.pending
        actual = reading - previous
        self.sum_absolute_error += abs(actual - forecast)
        self.scored += 1
        if self.retained:
            key = (cue, action)
            self.counts[key] = self.counts.get(key, 0) + 1
            self.totals[key] = self.totals.get(key, 0.0) + actual
        self.pending = None

    def commit(self, cue: int, action: str, reading: float) -> None:
        if cue not in range(4) or action not in Actions or self.pending is not None:
            raise ValueError("invalid or unobserved predictive transition")
        self.pending = (cue, action, reading, self.estimate(cue, action))


@dataclass(frozen=True)
class ProbeResult:
    preference: Preference
    retained: bool
    trial: M1Result
    scored_transitions: int
    learned_cells: int
    mean_absolute_error: float | None
    observed_sensor_span: float


def run_probe(
    *,
    seed: int,
    preference: Preference,
    retained: bool,
    config: M1Config | None = None,
    exploration: float = 0.25,
) -> ProbeResult:
    """Retained forecast updates never become a value/goal signal.

    'higher'/'lower' deliberately inject a directional appraisal. A physical
    survival consequence of 'higher' is therefore NOT emergent motivation.
    """
    if preference not in ("none", "higher", "lower"):
        raise ValueError("unknown appraisal condition")
    if type(retained) is not bool or not math.isfinite(exploration):
        raise ValueError("invalid retention/exploration")
    if not 0.0 <= exploration <= 1.0:
        raise ValueError("exploration must be in [0, 1]")
    rng = random.Random(seed ^ 0x4D315052)
    model = DeltaProbe(retained=retained)

    def select(cue: int, reading: float) -> str:
        # No physical E, terminal outcome, meals, or reward are supplied here.
        model.arrive(reading)
        chance_action = rng.choice(Actions)
        exploratory = rng.random() < exploration
        if preference == "none" or exploratory:
            chosen = chance_action
        else:
            forecasts = [(model.estimate(cue, action), action) for action in Actions]
            if preference == "higher":
                best = max(value for value, _ in forecasts)
            else:
                best = min(value for value, _ in forecasts)
            chosen = next(action for value, action in forecasts if value == best)
        model.commit(cue, chosen, reading)
        return chosen

    trial = run_trial(
        seed=seed,
        policy="external",
        learning=False,
        config=config,
        external_selector=select,
    )
    return ProbeResult(
        preference=preference,
        retained=retained,
        trial=trial,
        scored_transitions=model.scored,
        learned_cells=len(model.counts),
        mean_absolute_error=(
            model.sum_absolute_error / model.scored if model.scored else None
        ),
        observed_sensor_span=(
            model.sensor_max - model.sensor_min if model.scored else 0.0
        ),
    )


def paired_probes(seed: int, config: M1Config | None = None) -> dict[str, ProbeResult]:
    """Paired opportunity streams; not a V-certified randomized study."""
    arms: tuple[tuple[str, Preference, bool], ...] = (
        ("passive_retained", "none", True),
        ("passive_frozen", "none", False),
        ("directional_higher_retained", "higher", True),
        ("directional_higher_frozen", "higher", False),
        ("directional_lower_retained", "lower", True),
    )
    return {
        name: run_probe(
            seed=seed, preference=preference, retained=retained, config=config
        )
        for name, preference, retained in arms
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline M1 forecast/appraisal separation")
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    output = {
        name: {
            "preference": arm.preference,
            "retained": arm.retained,
            "completed_ticks": arm.trial.completed_ticks,
            "terminal": arm.trial.terminal,
            "meals": arm.trial.meals,
            "final_energy": arm.trial.final_energy,
            "scored_transitions": arm.scored_transitions,
            "learned_cells": arm.learned_cells,
            "mean_absolute_error": arm.mean_absolute_error,
            "observed_sensor_span": arm.observed_sensor_span,
        }
        for name, arm in paired_probes(args.seed).items()
    }
    print(json.dumps(output, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
