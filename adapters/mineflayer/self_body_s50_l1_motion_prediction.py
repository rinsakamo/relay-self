"""#653 L1-MP1: one-step S50 sampled-displacement forecast, readonly DEV.

This is a cheap, non-authoritative linear model. A source-pinned archival
audit summary is NOT the immutable Paper original or a live typed admission.
No goal/reward, S10/S11, P1 WAIT, World action, L0 policy, or persistence.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Mapping

from adapters.mineflayer.m02_paper_dev.s50_live_paper_window import (
    S50LivePaperWindow,
)

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ALLOWED_AUDITS = frozenset({
    "DEV_LIVE_NEXT_L0_NATIVE_EPOCH_REFERENCED_PASS",
    "DEV_LIVE_L1_MOTION_SHADOW_ORIGINAL_AUDIT_PASS",
})


class MotionPredictionRejected(ValueError):
    """Unqualified/mixed Paper sequence or invalid train/heldout boundary."""


@dataclass(frozen=True, slots=True)
class MotionStep:
    world_tick: int
    displacement_m: float
    last_reported_input_active: bool


@dataclass(frozen=True, slots=True)
class MotionSequence:
    session_id: str
    paper_world_uuid: str
    action_id: str
    subject_uuid: str
    paper_prefix_sha256: str
    steps: tuple[MotionStep, ...]
    source_ceiling: str


@dataclass(frozen=True, slots=True)
class MotionForecast:
    """One parameter fitted ONLY from an earlier World. Not a Habit/policy."""

    train_session_id: str
    train_world_uuid: str
    train_prefix_sha256: str
    slope: float
    training_pairs: int
    trained_measured_mean_m: float
    learned_l1_policy: bool = False
    s10_updates: int = 0
    s11_grants: int = 0
    action_issues: int = 0


@dataclass(frozen=True, slots=True)
class ForecastErrors:
    mae_m: float
    rmse_m: float


@dataclass(frozen=True, slots=True)
class MotionHeldoutComparison:
    train_session_id: str
    heldout_session_id: str
    train_world_uuid: str
    heldout_world_uuid: str
    train_prefix_sha256: str
    heldout_prefix_sha256: str
    sample_pairs: int
    slope: float
    no_memory_zero: ForecastErrors
    last_value: ForecastErrors
    training_mean: ForecastErrors
    l1_linear: ForecastErrors
    cheap_same_linear: ForecastErrors
    exact_cheap_equivalence: bool
    classification: str = "CHEAP_LINEAR_EQUIVALENT"
    provenance_ceiling: str = "ARCHIVAL_READBACK_REPLAY_NOT_REAUTHENTICATED"
    goal: str = "UNDETERMINED"
    learning_updates: int = 0
    s10_updates: int = 0
    s11_grants: int = 0
    p1_wait_admitted: int = 0
    extra_actions: int = 0
    native_probes: int = 0


def _require_sequence(sequence: MotionSequence) -> None:
    if not isinstance(sequence, MotionSequence):
        raise MotionPredictionRejected("typed bounded sequence required")
    if any(
        type(v) is not str or not v or len(v) > 128 or any(c.isspace() for c in v)
        for v in (
            sequence.session_id, sequence.paper_world_uuid,
            sequence.action_id, sequence.subject_uuid,
        )
    ):
        raise MotionPredictionRejected("missing or unbounded source identity")
    if (
        type(sequence.paper_prefix_sha256) is not str
        or _SHA.fullmatch(sequence.paper_prefix_sha256) is None
        or sequence.source_ceiling not in (
            "ARCHIVAL_READBACK_NOT_REAUTHENTICATED",
            "LIVE_PROVISIONAL_PAPER_ONLY",
        )
        or type(sequence.steps) is not tuple or len(sequence.steps) != 8
    ):
        raise MotionPredictionRejected("invalid source digest or bounded Paper window")
    for i, row in enumerate(sequence.steps):
        if (
            not isinstance(row, MotionStep)
            or type(row.world_tick) is not int or row.world_tick < 0
            or type(row.displacement_m) is not float
            or not math.isfinite(row.displacement_m)
            or not 0.0 <= row.displacement_m <= 64.0
            or type(row.last_reported_input_active) is not bool
            or (i > 0 and row.world_tick != sequence.steps[i - 1].world_tick + 1)
        ):
            raise MotionPredictionRejected("missing, invalid or discontinuous Paper tick")


def from_live_window(source: S50LivePaperWindow) -> MotionSequence:
    """Read original in-process S50 typed source without declaring it final."""
    if (
        not isinstance(source, S50LivePaperWindow)
        or source.scope != "IN_SESSION_PAPER_CALLBACK_WINDOW_ONLY"
        or not source.provisional or source.final_source_verified
        or source.node_trace_complete or source.full_tick_input_idle
        or source.physical_stability_attested or source.goal_admitted
        or source.p1_wait_granted or source.l10_pairs
        or source.s10_updates or source.s11_grants
        or source.effective_clear_tick != "NOT_ATTESTED"
        or source.marker_id != f"{source.action_id}-{source.session_id}"
    ):
        raise MotionPredictionRejected("source is not the original provisional Paper view")
    output = MotionSequence(
        source.session_id, source.paper_world_uuid, source.action_id,
        source.subject_uuid, source.paper_prefix_sha256,
        tuple(MotionStep(x.world_tick, x.displacement_m,
                         x.last_reported_input_active) for x in source.ticks),
        "LIVE_PROVISIONAL_PAPER_ONLY",
    )
    _require_sequence(output)
    return output


def from_archival_readback(report: Mapping[str, Any]) -> MotionSequence:
    """Offline replay of an existing audit's sampled fields, NOT original auth.

    Caller must pin the *repository commit* containing the audit JSON and
    separately preserve/check original evidence. Never use this converter
    as a live SelfBody/S50 source or qualified training admission.
    """
    if not isinstance(report, dict):
        raise MotionPredictionRejected("audit report mapping required")
    if (
        report.get("classification") not in _ALLOWED_AUDITS
        or report.get("goal") != "UNDETERMINED"
        or report.get("qualification") != "NO_GO"
        or report.get("science") != "NOT_RUN"
    ):
        raise MotionPredictionRejected("wrong archival DEV-only report classification")
    r = report.get("route_b", report)
    if not isinstance(r, dict) or not isinstance(r.get("live_window"), dict):
        raise MotionPredictionRejected("missing archived route B window")
    source = r["live_window"]
    if (
        source.get("scope") != "IN_SESSION_PAPER_CALLBACK_WINDOW_ONLY"
        or source.get("provisional") is not True
        or source.get("final_source_verified") is not False
        or source.get("node_trace_complete") is not False
        or source.get("full_tick_input_idle") is not False
        or source.get("physical_stability_attested") is not False
        or source.get("goal_admitted") is not False
        or source.get("effective_clear_tick") != "NOT_ATTESTED"
        or any(source.get(k) != 0 for k in (
            "p1_wait_granted", "l10_pairs", "s10_updates", "s11_grants",
        ))
        or not isinstance(source.get("ticks"), list)
        or len(source["ticks"]) != 8
        or source.get("marker_id") != (
            f"{source.get('action_id')}-{source.get('session_id')}"
        )
    ):
        raise MotionPredictionRejected("archived S50 source scope / limitation forged")
    try:
        steps = tuple(MotionStep(
            item["world_tick"], item["displacement_m"],
            item["last_reported_input_active"],
        ) for item in source["ticks"])
        output = MotionSequence(
            source["session_id"], source["paper_world_uuid"],
            source["action_id"], source["subject_uuid"],
            source["paper_prefix_sha256"], steps,
            "ARCHIVAL_READBACK_NOT_REAUTHENTICATED",
        )
    except (KeyError, TypeError) as exc:
        raise MotionPredictionRejected("missing archived original fields") from exc
    _require_sequence(output)
    return output


def freeze_forecast(training: MotionSequence) -> MotionForecast:
    """Fit one cheap nonnegative linear coefficient from PREVIOUS World only."""
    _require_sequence(training)
    xs = tuple(row.displacement_m for row in training.steps)
    denominator = math.fsum(x * x for x in xs[:-1])
    numerator = math.fsum(a * b for a, b in zip(xs[:-1], xs[1:]))
    slope = numerator / denominator if denominator else 0.0
    mean = math.fsum(xs[1:]) / (len(xs) - 1)
    if not math.isfinite(slope):
        raise MotionPredictionRejected("nonfinite fitted slope")
    return MotionForecast(
        training.session_id, training.paper_world_uuid,
        training.paper_prefix_sha256, slope, len(xs) - 1, mean,
    )


def _errors(actual: tuple[float, ...], predicted: tuple[float, ...]) -> ForecastErrors:
    n = len(actual)
    return ForecastErrors(
        math.fsum(abs(a - p) for a, p in zip(actual, predicted)) / n,
        math.sqrt(math.fsum((a - p) ** 2 for a, p in zip(actual, predicted)) / n),
    )


def evaluate_heldout(training: MotionSequence, heldout: MotionSequence) -> MotionHeldoutComparison:
    """Compare time-ordered one-step forecasts against independent World source.

    At each heldout tick t, *only* x[t] enters predictions of x[t+1].
    Never fit using the heldout future x[t+1], Goal or unissued actions.
    """
    _require_sequence(training)
    _require_sequence(heldout)
    if (
        training.session_id == heldout.session_id
        or training.paper_world_uuid == heldout.paper_world_uuid
        or training.paper_prefix_sha256 == heldout.paper_prefix_sha256
        or training.subject_uuid != heldout.subject_uuid
        or training.source_ceiling != heldout.source_ceiling
    ):
        raise MotionPredictionRejected("training and heldout source must be distinct matched Worlds")
    model = freeze_forecast(training)
    xs = tuple(row.displacement_m for row in heldout.steps)
    actual = xs[1:]
    last = xs[:-1]
    zeros = (0.0,) * len(actual)
    avg = (model.trained_measured_mean_m,) * len(actual)
    linear = tuple(model.slope * x for x in last)
    learned = _errors(actual, linear)
    cheap = _errors(actual, linear)  # deliberately the same-information cheap rule
    return MotionHeldoutComparison(
        training.session_id, heldout.session_id,
        training.paper_world_uuid, heldout.paper_world_uuid,
        training.paper_prefix_sha256, heldout.paper_prefix_sha256,
        len(actual), model.slope, _errors(actual, zeros),
        _errors(actual, last), _errors(actual, avg), learned, cheap,
        exact_cheap_equivalence=learned == cheap,
        provenance_ceiling=(
            "ARCHIVAL_READBACK_REPLAY_NOT_REAUTHENTICATED"
            if training.source_ceiling == "ARCHIVAL_READBACK_NOT_REAUTHENTICATED"
            else "LIVE_PROVISIONAL_PAPER_ONLY_NOT_QUALIFIED"
        ),
    )
