"""DEV C1/C4 seam: one attempted MOVE Intent -> one motion experience -> S10 reuse.

Pure composition of ORIGINAL S49 terminal receipts and existing S10 retained owner.
No new Action issuer, Memory store, World truth, autonomous scheduling or Habit writer.
A typed/fixture receipt alone does not independently attest a physical Minecraft run.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.normal_action import NormalActionReceipt
from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.action import ActionState
from relay_self.epoch_continuation import read_retained_preference
from relay_self.intent import IntentCommitment, IntentEventKind
from relay_self.learning import (
    FeedbackDirection,
    LearningCommitResult,
    LearningFeedback,
    LearningPreferenceState,
    LearningUpdateAuthority,
    LearningUpdateRule,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance


class IntentMotionRejected(ValueError):
    """The attempted Intent, source receipts or retained handoff did not match."""


class MotionComparison(str, Enum):
    SHORTER = "shorter"
    WITHIN_TOLERANCE = "within_tolerance"
    LONGER = "longer"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class IntentMotionForecast:
    self_id: str
    intent_id: str
    session_id: str
    source_probe_seq: int
    target_id: str
    owner_revision: int
    predicted_total_m: float
    source_provenance: Provenance


@dataclass(frozen=True, slots=True)
class IntentMotionExperience:
    """ONE attempt-level evidence association; never a successful-escape claim."""

    experience_id: str
    forecast: IntentMotionForecast
    terminal_kind: IntentEventKind
    action_receipts: tuple[NormalActionReceipt, ...]
    decision_probes: tuple[MineflayerObservation, ...]
    measured_total_m: float | None
    comparison: MotionComparison
    tolerance_m: float
    # Physical movement != the Intent's external Goal success.
    intent_goal_verified: bool = False


def forecast_from_retained(
    owner: LearningPreferenceState,
    supplied: LearningPreferenceState,
    *,
    self_id: str,
    intent_id: str,
    session_id: str,
    native_probe_seq: int,
    expected_revision: int,
    source_provenance: Provenance,
) -> IntentMotionForecast:
    """Predict a bounded motion magnitude from the *exact* current S10 owner.

    DEV representation: retained nonnegative integer is decimeters of motion.
    No universal movement model or permission to issue MOVE is implied.
    """
    for value in (self_id, intent_id, session_id):
        if not isinstance(value, str) or not value.strip() or any(c.isspace() for c in value):
            raise IntentMotionRejected("structured self/intent/session identity required")
    if type(native_probe_seq) is not int or native_probe_seq < 0:
        raise IntentMotionRejected("native source sequence required")
    if not isinstance(source_provenance, Provenance):
        raise IntentMotionRejected("native source provenance required")
    read = read_retained_preference(
        owner, supplied, required_target_id="motion_decimeters",
        expected_revision=expected_revision, provenance=source_provenance,
    )
    if read.snapshot.value < 0 or read.snapshot.maximum > 1000:
        raise IntentMotionRejected("bounded nonnegative motion model required")
    return IntentMotionForecast(
        self_id, intent_id, session_id, native_probe_seq,
        read.snapshot.target_id, read.revision, read.snapshot.value / 10.0,
        source_provenance,
    )


def close_motion_intent_experience(
    intent: IntentCommitment,
    forecast: IntentMotionForecast,
    receipts: tuple[NormalActionReceipt, ...],
    *,
    attempt_id: str,
    tolerance_m: float = 0.05,
    decision_probes: tuple[MineflayerObservation, ...] | None = None,
) -> IntentMotionExperience:
    """Associate original S49 receipts at terminal Intent assessment, NOT per Action.

    Only a native observed motion magnitude is compared. S16 OUTCOME itself
    never certifies escape success. UNKNOWN closes without learning feedback.
    No storage operation is performed; callers deduplicate by experience_id.

    Original S49's admission/decision probe and S15's internal before probe
    are DIFFERENT native observations. The original caller passes the exact
    decision_probes already held by its owner; NormalActionReceipt.source
    binds each such probe. A missing argument is only a legacy offline shape
    where receipt.source identifies consequence.before_observation itself.
    """
    if not isinstance(intent, IntentCommitment) or not isinstance(forecast, IntentMotionForecast):
        raise IntentMotionRejected("typed Intent and pre-result forecast required")
    if not isinstance(attempt_id, str) or not attempt_id.strip() or any(
        c.isspace() for c in attempt_id
    ):
        raise IntentMotionRejected("bounded attempt identity required")
    if type(receipts) is not tuple or not 1 <= len(receipts) <= 8:
        raise IntentMotionRejected("attempted MOVE needs 1..8 original Action receipts")
    if type(tolerance_m) not in (int, float) or not math.isfinite(tolerance_m) or tolerance_m < 0:
        raise IntentMotionRejected("finite nonnegative motion tolerance required")
    if type(forecast.predicted_total_m) not in (int, float) or not math.isfinite(
        forecast.predicted_total_m
    ) or forecast.predicted_total_m < 0:
        raise IntentMotionRejected("invalid motion forecast")
    # The original owner retains prior Intent events. Only its latest attempt
    # can be closed: an older terminal must never be replayed after a successor.
    events = intent.events
    starts = [i for i, event in enumerate(events) if event.kind is IntentEventKind.COMMITTED]
    if not starts:
        raise IntentMotionRejected("an original committed Intent is required")
    attempt = events[starts[-1]:]
    if any(event.intent_id != forecast.intent_id for event in attempt):
        raise IntentMotionRejected("foreign or superseded Intent event lineage")
    terminal = attempt[-1]
    if terminal.kind not in {
        IntentEventKind.COMPLETED, IntentEventKind.FAILED,
        IntentEventKind.INVALIDATED, IntentEventKind.RECONSIDERED_RELEASE,
    }:
        raise IntentMotionRejected("Intent attempt must reach terminal assessment")
    if not isinstance(forecast.source_provenance, Provenance):
        raise IntentMotionRejected("forecast source identity is missing")

    if decision_probes is not None and (
        type(decision_probes) is not tuple
        or len(decision_probes) != len(receipts)
        or not all(isinstance(p, MineflayerObservation) for p in decision_probes)
    ):
        raise IntentMotionRejected("one exact S49 decision probe per Action required")

    seen_actions: set[str] = set()
    seen_decisions: set[tuple[int, str]] = set()
    last_after_seq = -1
    measured = 0.0
    complete = True
    for index, receipt in enumerate(receipts):
        if not isinstance(receipt, NormalActionReceipt):
            raise IntentMotionRejected("requires original typed S49 receipt")
        action = receipt.terminal
        consequence = receipt.consequence
        before = consequence.before_observation
        after = consequence.after_observation
        # Legacy synthetic tests contain the selected probe as S15 before.
        # Live S49 MUST supply decision_probes because S15 re-observes.
        selected = before if decision_probes is None else decision_probes[index]
        if not isinstance(selected, MineflayerObservation):
            raise IntentMotionRejected("original S49 decision probe missing")
        if (
            selected.kind != "probe"
            or not selected.request_id
            or selected.session_id != forecast.session_id
            or selected.provenance.source != "mineflayer"
            or receipt.source != selected.provenance
            or (selected.seq, selected.request_id) in seen_decisions
            or selected.seq <= last_after_seq
        ):
            raise IntentMotionRejected("decision source missing, replayed or foreign")
        if (
            action.action_id in seen_actions
            or action.intent_id != forecast.intent_id
            or action.action_id != consequence.action_id
            or consequence.session_id != forecast.session_id
            or before is None
            or before.session_id != forecast.session_id
            or before.kind != "probe"
            or before.provenance.source != "mineflayer"
            or consequence.action_ref != "MOVE_BACKWARD"
            or before.seq < selected.seq
            or (decision_probes is not None and (
                before.seq <= selected.seq
                or before.provenance == selected.provenance
            ))
        ):
            raise IntentMotionRejected("S49 original Intent/native source mismatch")
        if not seen_actions and (
            selected.seq != forecast.source_probe_seq
            or selected.provenance != forecast.source_provenance
        ):
            raise IntentMotionRejected("forecast is not bound to pre-Action native source")
        if (
            after is None or after.kind != "probe"
            or after.session_id != forecast.session_id
            or after.provenance.source != "mineflayer"
            or after.seq <= before.seq
        ):
            raise IntentMotionRejected("missing or stale post-Action native probe")
        if (
            action.state is not ActionState.OUTCOME
            or consequence.status is not WorldConsequenceStatus.EXECUTED
            or type(consequence.movement_distance) not in (int, float)
            or not math.isfinite(consequence.movement_distance)
            or consequence.movement_distance < 0
        ):
            complete = False
        else:
            measured += consequence.movement_distance
        seen_actions.add(action.action_id)
        seen_decisions.add((selected.seq, selected.request_id))
        last_after_seq = after.seq

    if not complete:
        comparison = MotionComparison.UNKNOWN
        actual: float | None = None
    else:
        actual = measured
        delta = measured - forecast.predicted_total_m
        comparison = (
            MotionComparison.SHORTER if delta < -tolerance_m
            else MotionComparison.LONGER if delta > tolerance_m
            else MotionComparison.WITHIN_TOLERANCE
        )
    return IntentMotionExperience(
        experience_id=f"{forecast.self_id}:{forecast.session_id}:{forecast.intent_id}:{attempt_id}",
        forecast=forecast,
        terminal_kind=terminal.kind,
        action_receipts=receipts,
        decision_probes=tuple(
            r.consequence.before_observation for r in receipts
        ) if decision_probes is None else decision_probes,
        measured_total_m=actual,
        comparison=comparison,
        tolerance_m=float(tolerance_m),
    )


def learn_from_motion_experience(
    experience: IntentMotionExperience,
    owner: LearningPreferenceState,
    rule: LearningUpdateRule,
    authority: LearningUpdateAuthority,
    *,
    provenance: Provenance,
) -> LearningCommitResult:
    """Use existing S10 revision/authority to update NEXT Intent's forecast.

    No direction is inferred for UNKNOWN. Replay is rejected by comparing the
    original forecast revision with the current retained owner revision, even
    if unrelated feedback was committed in between.
    """
    if not isinstance(experience, IntentMotionExperience):
        raise IntentMotionRejected("typed C1 experience required")
    if not isinstance(owner, LearningPreferenceState):
        raise IntentMotionRejected("existing S10 owner required")
    if experience.comparison is MotionComparison.UNKNOWN or experience.measured_total_m is None:
        raise IntentMotionRejected("UNKNOWN motion cannot become training feedback")
    if (
        owner.target_id != experience.forecast.target_id
        or owner.revision != experience.forecast.owner_revision
    ):
        raise IntentMotionRejected("stale/replayed or foreign learning snapshot")
    direction = {
        MotionComparison.SHORTER: FeedbackDirection.DECREASE,
        MotionComparison.LONGER: FeedbackDirection.INCREASE,
        MotionComparison.WITHIN_TOLERANCE: FeedbackDirection.HOLD,
    }[experience.comparison]
    feedback = LearningFeedback(
        feedback_id="intent-motion:" + experience.experience_id,
        target_id=owner.target_id,
        direction=direction,
        provenance=Provenance("intent-motion-dev", experience.experience_id),
        consequence_ref="s49-actions:" + ",".join(
            r.terminal.action_id for r in experience.action_receipts
        ),
    )
    proposal = propose_learning_update(owner, feedback, rule)
    return commit_learning_update(owner, proposal, authority, provenance=provenance)
