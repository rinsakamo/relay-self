"""DEV-only one-step occlusion and counterfactual transfer probe.

Synthetic, deterministic evaluation boundary. No Minecraft, native source
attestation, persistent WorldModel, Action issuer, Memory or S10 mutation.
The derived drift is an observer-local *hypothesis*, not World truth.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Literal

ARM_PERSIST = "persist"
ARM_LOCAL = "local"
ARM_TRANSFER = "transfer"
ACTION_HOLD = "HOLD"
ACTION_NUDGE = "NUDGE"
_SYNTHETIC_SCOPE = "SYNTHETIC_DEV"


class TransferProbeBlocked(ValueError):
    """Malformed, non-isolated or counterfeit experimental input."""


class ScoreStatus(str, Enum):
    SCORED = "scored"
    UNAVAILABLE = "unavailable"


def _name(name: str, value: object) -> None:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise TransferProbeBlocked(f"invalid {name}")


def _integer(name: str, value: object) -> None:
    if type(value) is not int:
        raise TransferProbeBlocked(f"{name} must be integer")


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class PositivePosition:
    self_id: str
    session_id: str
    region_id: str
    target_id: str
    source_ref: str
    step: int
    x: int
    source_scope: Literal["SYNTHETIC_DEV"] = _SYNTHETIC_SCOPE

    def __post_init__(self) -> None:
        for key in ("self_id", "session_id", "region_id", "target_id", "source_ref"):
            _name(key, getattr(self, key))
        _integer("step", self.step)
        _integer("x", self.x)
        if self.step < 0 or self.source_scope != _SYNTHETIC_SCOPE:
            raise TransferProbeBlocked("only nonnegative synthetic source allowed")


@dataclass(frozen=True, slots=True)
class PositiveTransition:
    before: PositivePosition
    after: PositivePosition
    action: Literal["HOLD"] = ACTION_HOLD

    def __post_init__(self) -> None:
        a, b = self.before, self.after
        if not isinstance(a, PositivePosition) or not isinstance(b, PositivePosition):
            raise TransferProbeBlocked("two positive readings required")
        if (a.self_id, a.session_id, a.region_id, a.target_id) != (
            b.self_id, b.session_id, b.region_id, b.target_id
        ):
            raise TransferProbeBlocked("mixed source identities")
        if b.step != a.step + 1 or b.source_ref == a.source_ref:
            raise TransferProbeBlocked("training step or source replay")
        if self.action != ACTION_HOLD:
            raise TransferProbeBlocked("intervened samples confound idle drift")


@dataclass(frozen=True, slots=True)
class DriftHypothesis:
    self_id: str
    session_id: str
    delta_x: int
    trained_regions: tuple[str, ...]
    trained_targets: tuple[str, ...]
    evidence_pairs: tuple[tuple[str, str], ...]
    training_last_step: int
    source_scope: Literal["SYNTHETIC_DEV"] = _SYNTHETIC_SCOPE

    def __post_init__(self) -> None:
        _name("candidate self_id", self.self_id)
        _name("candidate session_id", self.session_id)
        _integer("delta_x", self.delta_x)
        _integer("training_last_step", self.training_last_step)
        if self.training_last_step < 1:
            raise TransferProbeBlocked("invalid training end step")
        if self.source_scope != _SYNTHETIC_SCOPE:
            raise TransferProbeBlocked("candidate source scope is not synthetic")
        if not (
            isinstance(self.trained_regions, tuple)
            and isinstance(self.trained_targets, tuple)
            and isinstance(self.evidence_pairs, tuple)
        ):
            raise TransferProbeBlocked("candidate evidence must be immutable")
        count = len(self.evidence_pairs)
        if count < 2 or count != len(self.trained_regions) or (
            count != len(self.trained_targets)
        ):
            raise TransferProbeBlocked("candidate evidence is incomplete")
        if len(set(self.trained_regions)) < 2 or (
            len(set(self.trained_targets)) != count
        ):
            raise TransferProbeBlocked("candidate training diversity missing")
        refs = []
        for region, target, pair in zip(
            self.trained_regions, self.trained_targets,
            self.evidence_pairs, strict=True,
        ):
            _name("trained region", region)
            _name("trained target", target)
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise TransferProbeBlocked("bad source pair")
            for ref in pair:
                _name("training source ref", ref)
                refs.append(ref)
        if len(set(refs)) != len(refs):
            raise TransferProbeBlocked("duplicated training source")

    @property
    def digest(self) -> str:
        return _digest((
            self.self_id, self.session_id, self.delta_x,
            self.trained_regions, self.trained_targets,
            self.evidence_pairs, self.training_last_step, self.source_scope,
        ))


def compress_drift(
    training: tuple[PositiveTransition, ...],
) -> DriftHypothesis | None:
    """Require two distinct locations, entities and independent positive pairs."""
    if not isinstance(training, tuple) or len(training) < 2:
        return None
    if not all(isinstance(pair, PositiveTransition) for pair in training):
        raise TransferProbeBlocked("typed training pairs only")
    a = training[0].before
    owner = a.self_id, a.session_id
    regions = tuple(pair.before.region_id for pair in training)
    targets = tuple(pair.before.target_id for pair in training)
    evidence = tuple(
        (pair.before.source_ref, pair.after.source_ref) for pair in training
    )
    refs = tuple(ref for pair in evidence for ref in pair)
    if any(
        (pair.before.self_id, pair.before.session_id) != owner
        for pair in training
    ):
        raise TransferProbeBlocked("cross-self training")
    if (
        len(set(regions)) < 2 or len(set(targets)) != len(targets)
        or len(set(refs)) != len(refs)
    ):
        return None
    deltas = {pair.after.x - pair.before.x for pair in training}
    if len(deltas) != 1:
        return None
    return DriftHypothesis(
        owner[0], owner[1], deltas.pop(), regions, targets, evidence,
        max(pair.after.step for pair in training),
    )


@dataclass(frozen=True, slots=True)
class OccludedTask:
    """Only pre-gap observations and a decision objective are visible."""

    history: tuple[PositivePosition, ...]
    goal_x: int
    nudge_delta_x: int = 2
    nudge_cost: int = 1
    gap_status: Literal["OCCLUDED", "UNOBSERVED"] = "OCCLUDED"

    def __post_init__(self) -> None:
        if not isinstance(self.history, tuple) or len(self.history) not in (1, 2):
            raise TransferProbeBlocked("one or two pre-gap observations required")
        if not all(isinstance(x, PositivePosition) for x in self.history):
            raise TransferProbeBlocked("positive typed history required")
        _integer("goal_x", self.goal_x)
        _integer("nudge_delta_x", self.nudge_delta_x)
        _integer("nudge_cost", self.nudge_cost)
        if self.nudge_cost < 0:
            raise TransferProbeBlocked("negative intervention cost")
        if self.gap_status not in {"OCCLUDED", "UNOBSERVED"}:
            raise TransferProbeBlocked("unqualified gap status")
        last = self.history[-1]
        if len(self.history) == 2:
            previous = self.history[0]
            if (
                previous.self_id, previous.session_id,
                previous.region_id, previous.target_id,
            ) != (
                last.self_id, last.session_id,
                last.region_id, last.target_id,
            ):
                raise TransferProbeBlocked("foreign pre-gap history")
            if previous.step + 1 != last.step or (
                previous.source_ref == last.source_ref
            ):
                raise TransferProbeBlocked("non-consecutive pre-gap history")

    @property
    def latest(self) -> PositivePosition:
        return self.history[-1]

    @property
    def fingerprint(self) -> str:
        return _digest({
            "scope": _SYNTHETIC_SCOPE,
            "history": [
                (x.self_id, x.session_id, x.region_id, x.target_id,
                 x.source_ref, x.step, x.x)
                for x in self.history
            ],
            "goal": self.goal_x,
            "nudge_delta": self.nudge_delta_x,
            "nudge_cost": self.nudge_cost,
            "gap_status": self.gap_status,
        })


@dataclass(frozen=True, slots=True)
class SealedForecast:
    """Committed predictions; cannot contain later observation/outcomes."""

    task_fingerprint: str
    method: Literal["persist", "local", "transfer"]
    hold_x: int | None
    nudge_x: int | None
    selected_action: Literal["HOLD", "NUDGE"] | None
    learned_rule_digest: str | None
    commitment: str


def _decision(task: OccludedTask, hold_x: int, nudge_x: int) -> str:
    hold_loss = (hold_x - task.goal_x) ** 2
    nudge_loss = (nudge_x - task.goal_x) ** 2 + task.nudge_cost
    return ACTION_HOLD if hold_loss <= nudge_loss else ACTION_NUDGE


def issue_forecast(
    task: OccludedTask,
    *,
    method: Literal["persist", "local", "transfer"],
    rule: DriftHypothesis | None = None,
) -> SealedForecast:
    """Prediction is produced without access to the hidden World trajectory."""
    if not isinstance(task, OccludedTask):
        raise TransferProbeBlocked("typed task required")
    if method not in {ARM_PERSIST, ARM_LOCAL, ARM_TRANSFER}:
        raise TransferProbeBlocked("unknown prediction method")
    if method != ARM_TRANSFER and rule is not None:
        raise TransferProbeBlocked("baseline cannot receive learned rule")
    previous = task.latest
    rule_digest = None
    drift = None
    if method == ARM_PERSIST:
        drift = 0
    elif method == ARM_LOCAL:
        if len(task.history) == 2:
            drift = task.history[-1].x - task.history[-2].x
    else:
        if not isinstance(rule, DriftHypothesis):
            raise TransferProbeBlocked("transfer requires typed learned rule")
        if (rule.self_id, rule.session_id) != (
            previous.self_id, previous.session_id
        ):
            raise TransferProbeBlocked("cross-self transfer")
        if previous.region_id in rule.trained_regions or (
            previous.target_id in rule.trained_targets
        ):
            raise TransferProbeBlocked("not an unseen region/target")
        if rule.training_last_step > previous.step:
            raise TransferProbeBlocked("future training at forecast issuance")
        used = {ref for pair in rule.evidence_pairs for ref in pair}
        if any(x.source_ref in used for x in task.history):
            raise TransferProbeBlocked("train/evaluation evidence leaked")
        rule_digest = rule.digest
        drift = rule.delta_x

    hold = previous.x + drift if drift is not None else None
    nudge = hold + task.nudge_delta_x if hold is not None else None
    chosen = (
        _decision(task, hold, nudge) if hold is not None and nudge is not None
        else None
    )
    assertion = (
        task.fingerprint, method, hold, nudge, chosen, rule_digest,
        _SYNTHETIC_SCOPE,
    )
    return SealedForecast(
        task.fingerprint, method, hold, nudge, chosen, rule_digest,
        _digest(assertion),
    )


@dataclass(frozen=True, slots=True)
class SyntheticTwinOutcome:
    """Both potential outcomes exist ONLY in a synthetic cloned fixture."""

    task_fingerprint: str
    prior_ref: str
    after_ref_hold: str
    after_ref_nudge: str
    hold_x: int
    nudge_x: int
    source_scope: Literal["SYNTHETIC_DEV"] = _SYNTHETIC_SCOPE


def simulate_twin(
    task: OccludedTask, *, hidden_drift: int,
    after_ref_hold: str, after_ref_nudge: str,
) -> SyntheticTwinOutcome:
    """Independent evaluator; its hidden_drift is never an issue_forecast arg."""
    if not isinstance(task, OccludedTask):
        raise TransferProbeBlocked("typed task required")
    _integer("hidden_drift", hidden_drift)
    for key, value in (("after_ref_hold", after_ref_hold),
                       ("after_ref_nudge", after_ref_nudge)):
        _name(key, value)
    if (after_ref_hold == after_ref_nudge
            or task.latest.source_ref in (after_ref_hold, after_ref_nudge)
            or any(x.source_ref in (after_ref_hold, after_ref_nudge)
                   for x in task.history)):
        raise TransferProbeBlocked("future/source identity replay")
    hold_x = task.latest.x + hidden_drift
    return SyntheticTwinOutcome(
        task.fingerprint, task.latest.source_ref,
        after_ref_hold, after_ref_nudge,
        hold_x, hold_x + task.nudge_delta_x,
    )


@dataclass(frozen=True, slots=True)
class ForecastEvaluation:
    status: ScoreStatus
    occluded_error: int | None
    counterfactual_error: int | None
    selected_action: str | None
    realized_loss: int | None
    best_synthetic_loss: int | None
    regret: int | None


def score_sealed(
    task: OccludedTask,
    forecast: SealedForecast,
    outcome: SyntheticTwinOutcome,
) -> ForecastEvaluation:
    """Retrospective evaluation of a previously frozen prediction digest."""
    if not isinstance(task, OccludedTask):
        raise TransferProbeBlocked("typed task required")
    if not isinstance(forecast, SealedForecast):
        raise TransferProbeBlocked("typed forecast required")
    if not isinstance(outcome, SyntheticTwinOutcome):
        raise TransferProbeBlocked("typed synthetic twin required")
    if (
        forecast.task_fingerprint != task.fingerprint
        or outcome.task_fingerprint != task.fingerprint
        or outcome.prior_ref != task.latest.source_ref
        or outcome.source_scope != _SYNTHETIC_SCOPE
    ):
        raise TransferProbeBlocked("foreign task/outcome provenance")
    assertion = (
        forecast.task_fingerprint, forecast.method,
        forecast.hold_x, forecast.nudge_x,
        forecast.selected_action, forecast.learned_rule_digest,
        _SYNTHETIC_SCOPE,
    )
    if _digest(assertion) != forecast.commitment:
        raise TransferProbeBlocked("forecast modified after commitment")
    if (
        outcome.nudge_x != outcome.hold_x + task.nudge_delta_x
        or outcome.after_ref_hold == outcome.after_ref_nudge
        or outcome.after_ref_hold in {x.source_ref for x in task.history}
        or outcome.after_ref_nudge in {x.source_ref for x in task.history}
    ):
        raise TransferProbeBlocked("synthetic twin provenance inconsistent")
    if forecast.hold_x is None or forecast.nudge_x is None:
        return ForecastEvaluation(
            ScoreStatus.UNAVAILABLE, None, None, None, None, None, None
        )
    if forecast.selected_action != _decision(
        task, forecast.hold_x, forecast.nudge_x
    ):
        raise TransferProbeBlocked("forecast action does not match stated rule")
    occluded_error = abs(forecast.hold_x - outcome.hold_x)
    cf_error = (
        abs(forecast.hold_x - outcome.hold_x)
        + abs(forecast.nudge_x - outcome.nudge_x)
    )
    hold_loss = (outcome.hold_x - task.goal_x) ** 2
    nudge_loss = (outcome.nudge_x - task.goal_x) ** 2 + task.nudge_cost
    realized = (
        hold_loss if forecast.selected_action == ACTION_HOLD else nudge_loss
    )
    best = min(hold_loss, nudge_loss)
    return ForecastEvaluation(
        ScoreStatus.SCORED, occluded_error, cf_error,
        forecast.selected_action, realized, best, realized - best,
    )
