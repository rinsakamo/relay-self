"""L-BCG: bounded, read-only conditional *attention* from admitted motor outcomes.

This module does not authenticate Paper/S16 bytes, retain Memory, certify a
Goal, choose an Action, or promote an L1/S11 policy. S/R owners must verify the
two original digests and actual post-clear physical interval *before* supplying
an admission. Existing #653 provisional Paper samples are not eligible.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import combinations
from math import isfinite

from relay_self.habit_shadow import MAX_SAMPLES

_SHA_CHARS = frozenset("0123456789abcdef")
_AXES = ("clearance_band", "fast_gait", "fatigue_high", "energy_low", "obstacle")
_MAX_AXES = 2
_MIN_WORLDS_PER_CELL = 2


class BCGRejected(ValueError):
    """Untrusted source, invalid contrast, or train/evaluation leakage."""


class Attention(str, Enum):
    DEFER = "DEFER_UNKNOWN"
    RECHECK = "RECHECK_BEFORE_NEXT_MOVE"
    CONTINUE = "CONTINUE_CANDIDATE_NOT_ACTION"


@dataclass(frozen=True, slots=True)
class MotionContext:
    self_id: str
    session_id: str
    world_id: str
    world_revision: int
    body_source_ref: str
    world_source_ref: str
    source_kind: str
    remaining_m: float
    tolerance_m: float
    gait: str
    fatigue_high: bool
    energy_low: bool
    obstacle: bool
    freshness_ok: bool
    regime: str


@dataclass(frozen=True, slots=True)
class MotorOutcome:
    """Caller-owned join of existing Memory/S16 and separately observed S50.

    A typed object is not physical attestation. No new Memory DB is introduced.
    """

    context: MotionContext
    action_id: str
    original_s16_sha256: str
    original_settling_sha256: str
    settling_m: float
    settling_grade: str


@dataclass(frozen=True, slots=True)
class MotorSourceAdmission:
    """Original source admission supplied and audited by existing S/R owner."""

    s16_digests: frozenset[str]
    settling_digests: frozenset[str]


@dataclass(frozen=True, slots=True)
class BCGShadow:
    """Ephemeral hypothesis, never an executable instruction."""

    advice: Attention
    reason: str
    selected_axes: tuple[str, ...]
    matched_worlds: int
    training_worlds: int
    cheap_one_bit: Attention
    cheap_fixed_clearance: Attention
    cheap_recent: Attention
    cheap_exact_cue: Attention
    learning_updates: int = 0
    habit_grants: int = 0
    action_issues: int = 0
    action_authority: bool = False
    physical_improvement_attested: bool = False


def _sha(value: object) -> bool:
    return (
        type(value) is str and len(value) == 64
        and all(char in _SHA_CHARS for char in value)
    )


def _text(value: object) -> bool:
    return type(value) is str and bool(value) and len(value) <= 160


def _validate_context(c: MotionContext) -> None:
    if not isinstance(c, MotionContext):
        raise BCGRejected("typed current SelfBody/SelfWorld projection required")
    strings = (
        c.self_id, c.session_id, c.world_id, c.body_source_ref,
        c.world_source_ref, c.gait, c.regime,
    )
    if (
        any(not _text(v) for v in strings)
        or type(c.world_revision) is not int or c.world_revision < 0
        or c.source_kind != "OBSERVED"
        or c.gait not in ("WALK", "JOG", "RUN", "DASH")
        or type(c.remaining_m) not in (float, int)
        or type(c.tolerance_m) not in (float, int)
        or not isfinite(c.remaining_m) or not isfinite(c.tolerance_m)
        or c.remaining_m < 0 or c.tolerance_m < 0
        or any(type(v) is not bool for v in (
            c.fatigue_high, c.energy_low, c.obstacle, c.freshness_ok,
        ))
    ):
        raise BCGRejected("unqualified or inferred current cue")
    if not c.freshness_ok:
        raise BCGRejected("stale original cue: no L1 advice")


def _features(c: MotionContext) -> dict[str, bool]:
    return {
        "clearance_band": c.remaining_m - c.tolerance_m <= 0.15,
        "fast_gait": c.gait in ("RUN", "DASH"),
        "fatigue_high": c.fatigue_high,
        "energy_low": c.energy_low,
        "obstacle": c.obstacle,
    }


def _validate_training(
    training: tuple[MotorOutcome, ...],
    admission: MotorSourceAdmission,
    current: MotionContext,
) -> tuple[tuple[dict[str, bool], bool], ...]:
    if (
        not isinstance(training, tuple)
        or len(training) > MAX_SAMPLES
        or not isinstance(admission, MotorSourceAdmission)
        or not isinstance(admission.s16_digests, frozenset)
        or not isinstance(admission.settling_digests, frozenset)
        or any(not _sha(s) for s in (
            *admission.s16_digests, *admission.settling_digests,
        ))
    ):
        raise BCGRejected("bounded S/R admission required")
    seen_sessions: set[str] = set()
    seen_worlds: set[str] = set()
    seen_receipts: set[str] = set()
    pairs: list[tuple[dict[str, bool], bool]] = []
    for row in training:
        if not isinstance(row, MotorOutcome):
            raise BCGRejected("typed completed motor outcome required")
        c = row.context
        _validate_context(c)
        if (
            c.self_id != current.self_id
            or c.session_id == current.session_id
            or c.world_id == current.world_id
            or c.regime != current.regime
            or c.world_revision >= current.world_revision
            or c.world_id in seen_worlds
            or c.session_id in seen_sessions
            or row.action_id in seen_receipts
            or not _text(row.action_id)
            or not _sha(row.original_s16_sha256)
            or not _sha(row.original_settling_sha256)
            or row.original_s16_sha256 == row.original_settling_sha256
            or row.original_s16_sha256 not in admission.s16_digests
            or row.original_settling_sha256 not in admission.settling_digests
            or row.settling_grade != "PHYSICAL_POST_CLEAR_VERIFIED"
            or type(row.settling_m) not in (int, float)
            or not isfinite(row.settling_m)
            or row.settling_m < 0
        ):
            raise BCGRejected("foreign, repeated, provisional, or unaudited World outcome")
        seen_sessions.add(c.session_id)
        seen_worlds.add(c.world_id)
        seen_receipts.add(row.action_id)
        # Observed residual displacement vs independently measured clearance.
        # This is a *proxy risk label*, not a goal-success or Action utility label.
        risk = row.settling_m > max(0.0, c.remaining_m - c.tolerance_m)
        pairs.append((_features(c), risk))
    return tuple(pairs)


def compare_conditional_motion_shadow(
    *, current: MotionContext, training: tuple[MotorOutcome, ...],
    admission: MotorSourceAdmission, memory_enabled: bool,
) -> BCGShadow:
    """Learn up to two cue axes by coverage, not hardcoded FAST->RECHECK.

    Every selected cell needs at least two independent training Worlds and
    consistent observed residual-risk labels. Neither train labels nor heldout
    labels are read from the current World. Unknown conditions abstain.
    """
    _validate_context(current)
    if type(memory_enabled) is not bool:
        raise BCGRejected("explicit memory ablation flag required")
    if not memory_enabled:
        return BCGShadow(
            Attention.DEFER, "MEMORY_OFF", (), 0, 0,
            Attention.DEFER, Attention.DEFER, Attention.DEFER, Attention.DEFER,
        )
    data = _validate_training(training, admission, current)
    current_features = _features(current)
    cheap_one_bit = (
        Attention.RECHECK if any(risk for _, risk in data)
        else Attention.CONTINUE if data else Attention.DEFER
    )
    cheap_fixed = (
        Attention.RECHECK if current_features["clearance_band"] else Attention.CONTINUE
    )
    cheap_recent = (
        Attention.RECHECK if data[-1][1] else Attention.CONTINUE
    ) if data else Attention.DEFER
    # Same admitted inputs: cheapest full-cue memory lookup, not induced abstraction.
    exact = tuple(
        risk for features, risk in data
        if all(features[axis] == current_features[axis] for axis in _AXES)
    )
    cheap_exact = (
        Attention.RECHECK if exact and all(exact)
        else Attention.CONTINUE if exact and not any(exact)
        else Attention.DEFER
    )

    if not data:
        return BCGShadow(
            Attention.DEFER, "NO_ADMITTED_TRAINING", (), 0, 0,
            cheap_one_bit, cheap_fixed, cheap_recent, cheap_exact,
        )
    # Do not generalize a new environmental/safety dimension by dropping it.
    for axis in _AXES:
        if current_features[axis] not in {features[axis] for features, _ in data}:
            return BCGShadow(
                Attention.DEFER, "UNSEEN_CUE_VALUE", (), 0, len(data),
                cheap_one_bit, cheap_fixed, cheap_recent, cheap_exact,
            )

    best: tuple[int, int, tuple[str, ...], dict[tuple[bool, ...], bool]] | None = None
    for size in range(1, _MAX_AXES + 1):
        for axes in combinations(_AXES, size):
            cells: dict[tuple[bool, ...], list[bool]] = {}
            for features, risk in data:
                key = tuple(features[axis] for axis in axes)
                cells.setdefault(key, []).append(risk)
            stable = {
                key: labels[0] for key, labels in cells.items()
                if len(labels) >= _MIN_WORLDS_PER_CELL and len(set(labels)) == 1
            }
            if len(set(stable.values())) != 2:
                continue  # no learned conditional discrimination
            coverage = sum(len(cells[key]) for key in stable)
            candidate = (coverage, -size, axes, stable)
            if best is None or candidate[:2] > best[:2]:
                best = candidate

    if best is None:
        return BCGShadow(
            Attention.DEFER, "NO_STABLE_CONDITIONAL_RULE", (), 0, len(data),
            cheap_one_bit, cheap_fixed, cheap_recent, cheap_exact,
        )
    _, _, axes, stable = best
    key = tuple(current_features[axis] for axis in axes)
    if key not in stable:
        return BCGShadow(
            Attention.DEFER, "UNSUPPORTED_CUE_COMBINATION", axes, 0, len(data),
            cheap_one_bit, cheap_fixed, cheap_recent, cheap_exact,
        )
    support = sum(
        tuple(features[axis] for axis in axes) == key for features, _ in data
    )
    return BCGShadow(
        Attention.RECHECK if stable[key] else Attention.CONTINUE,
        "TRAINED_RESIDUAL_RISK_PROXY_ONLY", axes, support, len(data),
        cheap_one_bit, cheap_fixed, cheap_recent, cheap_exact,
    )
