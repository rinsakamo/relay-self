"""Stage N DEV-only live typed S49 Action closure evidence; NO new issuer.

A context-local callback receives the original *already terminal* Action,
existing S16 outcome interpretation, WorldConsequence and correlated probe.
Policy is predeclared independent of hindsight prediction match:
qualified MOVE_BACKWARD/observed_execution -> HOLD risk_weight.
Neither this observer nor the S17 Feedback grants S10 update authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from adapters.mineflayer.normal_action import NormalActionClosedReadback
from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.action import ActionState
from relay_self.action_feedback import (
    ActionFeedbackCriterion,
    LearningFeedbackInterpretationStatus,
    interpret_action_outcome_as_learning_feedback,
)
from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.learning import FeedbackDirection
from relay_self.provenance import Provenance


@dataclass(frozen=True, slots=True)
class StageNDeclaredPolicy:
    """DEV operator-specified criterion class, fixed BEFORE any native Action."""

    criterion_name: str = "actual-move-execution-only"
    target_id: str = "risk_weight"
    required_action_ref: str = "MOVE_BACKWARD"
    required_outcome_reason: str = "observed_execution"
    direction: FeedbackDirection = FeedbackDirection.HOLD

    def __post_init__(self) -> None:
        if (self.criterion_name != "actual-move-execution-only"
                or self.target_id != "risk_weight"
                or self.required_action_ref != "MOVE_BACKWARD"
                or self.required_outcome_reason != "observed_execution"
                or self.direction is not FeedbackDirection.HOLD):
            raise ValueError("Stage N fixed conservative HOLD criterion only")


class StageNNativeClosureObserver:
    """Only live source observability; the S49/S16/S17/S10 owners are unchanged."""

    def __init__(self, policy: StageNDeclaredPolicy) -> None:
        if not isinstance(policy, StageNDeclaredPolicy):
            raise TypeError("Stage N explicitly declared evaluation policy required")
        self.policy = policy
        self._session: str | None = None
        self._rows: list[dict[str, Any]] = []
        self._seen: set[str] = set()
        self._next_observations: list[dict[str, Any]] = []
        self._latest_native_seq: int | None = None
        self._observer_errors: list[str] = []

    def observe_existing_probe(self, reading: MineflayerObservation) -> None:
        """Record already received native probe, never issue another one."""
        if not isinstance(reading, MineflayerObservation):
            raise TypeError("exact native source probe required")
        prefix = f"s49-actual:{reading.session_id}:event-"
        if (reading.kind != "probe"
                or reading.provenance.source != "mineflayer"
                or not isinstance(reading.request_id, str)
                or not reading.request_id.startswith(prefix)
                or not reading.request_id[len(prefix):].isdecimal()):
            raise ValueError("original correlated S49 native probe required")
        if self._session is not None and self._session != reading.session_id:
            raise ValueError("foreign session in Stage N")
        if self._latest_native_seq is not None and reading.seq <= self._latest_native_seq:
            raise ValueError("replayed Stage N native probe")
        self._session = reading.session_id
        self._latest_native_seq = reading.seq
        for row in self._rows:
            if (row["source_session"] == reading.session_id
                    and reading.seq > row["after_native_seq"]
                    and row["action_id"] not in {
                        hit["after_action_id"] for hit in self._next_observations
                    }):
                self._next_observations.append({
                    "after_action_id": row["action_id"],
                    "next_native_seq": reading.seq,
                    "next_native_request_id": reading.request_id,
                    "same_native_session": True,
                    "action_issued_from_feedback": False,
                })

    def record_observer_error(self, phase: str, exc: Exception) -> None:
        """Capture optional observer failure while preserving S49 Action owner."""
        self._observer_errors.append(f"{phase}:{type(exc).__name__}")

    def observe_closed(self, witness: NormalActionClosedReadback) -> None:
        """Synchronous pure S17 classification from original typed closed Action."""
        if not isinstance(witness, NormalActionClosedReadback):
            raise TypeError("exact S49 Action readback type required")
        terminal, outcome = witness.terminal, witness.interpretation
        consequence, probe = witness.consequence, witness.original_probe
        sid = probe.session_id
        if (self._session is None or sid != self._session
                or consequence.session_id != sid
                or outcome.session_id != sid
                or terminal.action_id in self._seen):
            raise ValueError("replayed or foreign Action closure")
        prefix = "s49-native-move-"
        if not terminal.action_id.startswith(prefix):
            raise ValueError("closure not from existing S49 action identity")
        suffix = terminal.action_id[len(prefix):]
        if not suffix.isdecimal():
            raise ValueError("invalid original S49 event binding")
        if (probe.request_id != f"s49-actual:{sid}:event-{suffix}"
                or outcome.binding_id != f"s49-binding-{suffix}"
                or outcome.action_id != terminal.action_id
                or consequence.action_id != terminal.action_id
                or outcome.action_ref != self.policy.required_action_ref
                or terminal.state is not ActionState.OUTCOME
                or outcome.disposition is not ActionOutcomeDisposition.OUTCOME
                or outcome.reason_code != self.policy.required_outcome_reason
                or consequence.after_observation is None
                or consequence.after_observation.seq <= probe.seq
                or consequence.movement_distance is None
                or consequence.movement_distance < 0.05):
            raise ValueError("unqualified actual S49/S16 closure for Stage N")
        # Required exact IDs are instantiated only from authenticated source
        # lineage; the evaluation criteria and direction were PREDECLARED.
        criterion = ActionFeedbackCriterion(
            criterion_id=f"{self.policy.criterion_name}:{sid}:{suffix}",
            target_id=self.policy.target_id,
            required_action_id=terminal.action_id,
            required_binding_id=outcome.binding_id,
            required_action_ref=self.policy.required_action_ref,
            required_action_state=ActionState.OUTCOME,
            required_outcome_disposition=ActionOutcomeDisposition.OUTCOME,
            required_outcome_reason=self.policy.required_outcome_reason,
            feedback_direction=self.policy.direction,
            provenance=Provenance("stage-n-dev-predeclared", self.policy.criterion_name),
        )
        interpreted = interpret_action_outcome_as_learning_feedback(
            terminal, outcome, criterion,
            provenance=Provenance("stage-n-native-typed-closure",
                                  f"{sid}:{terminal.action_id}"),
        )
        if (interpreted.status is not LearningFeedbackInterpretationStatus.PRODUCED
                or interpreted.feedback is None
                or interpreted.feedback.direction is not FeedbackDirection.HOLD):
            raise ValueError("original typed Action failed predeclared S17")
        self._seen.add(terminal.action_id)
        self._rows.append({
            "action_id": terminal.action_id,
            "source_session": sid,
            "source_probe_seq": probe.seq,
            "source_probe_request_id": probe.request_id,
            "after_native_seq": consequence.after_observation.seq,
            "original_terminal": terminal.state.value,
            "original_outcome_reason": outcome.reason_code,
            "original_binding_id": outcome.binding_id,
            "source_movement_m": consequence.movement_distance,
            "s17_policy": self.policy.criterion_name,
            "s17_interpretation": interpreted.status.value,
            "feedback_id": interpreted.feedback.feedback_id,
            "feedback_direction": interpreted.feedback.direction.value,
            "s10_owner_authority_present": False,
            "s10_update_committed": False,
            "predicted_label_used_as_reward": False,
            "action_issued_by_stage_n": False,
        })

    def summary(self) -> dict[str, Any]:
        return {
            "kind": "stage_n_typed_s16_closed_readback",
            "classification": "DEV_ONLY_LIVE_S17_READ_ONLY",
            "source_session": self._session,
            "declared_policy": self.policy.criterion_name,
            "declared_feedback_direction": self.policy.direction.value,
            "typed_s17_feedback_count": len(self._rows),
            "source_closures": list(self._rows),
            "post_closure_source_observations": list(self._next_observations),
            "s10_authority_attested": False,
            "s10_learning_commits": 0,
            "real_next_epoch_learned_policy": False,
            "native_actions_added": 0,
            "observer_errors": list(self._observer_errors),
        }
