"""I6 read-only native-S15/S16/S17 shape vs foreign B16 source interlock.

Existing S15/S16/S17 test-double receipts can form one typed Action-feedback
lineage. B16 five-trial simulator witnesses do not share that World or Action
space; even shape-valid receipts are NOT authentic physical Minecraft evidence.
No Action, Learning, S11 acquisition, L2 or real-world side effect is issued.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.execution import (
    MOVE_BACKWARD_ACTION_REF,
    MineflayerCommand,
    WorldConsequence,
    WorldConsequenceStatus,
)
from experiments.ac_b_b16_quorum import BatchLedger, N_TRIALS
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_feedback import (
    ActionFeedbackCriterion,
    LearningFeedbackInterpretation,
    LearningFeedbackInterpretationStatus,
    interpret_action_outcome_as_learning_feedback,
)
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    ActionOutcomeInterpretation,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.execution_binding import ExecutionBindingResult

MANIFEST = Path(__file__).with_name("ac_integration_i6_manifest.json")
FROZEN_SHA256 = "a22366faf1852bc3157589070f26d48ab109947210ecfbe9e40f6654039dbab1"


class I6Rejected(ValueError):
    """Source or owner conformance failed, no promotion permitted."""


class I6PromotionDenied(I6Rejected):
    """No verified physical or product-level source/grant in this experiment."""


@dataclass(frozen=True, slots=True)
class NativeShape:
    issued: ActionLifecycle
    command: MineflayerCommand
    binding: ExecutionBindingResult
    consequence: WorldConsequence
    outcome: ActionOutcomeInterpretation
    closed: ActionLifecycle
    supervisor: ActionSupervisor
    criterion: ActionFeedbackCriterion
    feedback: LearningFeedbackInterpretation


@dataclass(frozen=True, slots=True)
class I6Verdict:
    classification: str
    native_action_id: str
    native_shaped_session: str
    native_s17_target: str
    b16_foreign_session: str
    b16_source_pairs: int
    syntactic_native_lineage: bool = True
    foreign_simulator_ledger_well_typed: bool = True
    shared_causal_world: bool = False
    native_competing_action_witnesses: bool = False
    native_goal_success_signed: bool = False
    physical_source_attested: bool = False
    production_s11_grant: bool = False
    durable_replay_ledger: bool = False
    matched_native_cost_gain: bool = False
    production_go: bool = False


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in pairs:
        if key in output:
            raise I6Rejected("duplicate frozen manifest key")
        output[key] = value
    return output


def read_manifest() -> dict[str, object]:
    try:
        value = json.loads(
            MANIFEST.read_text(encoding="utf-8"),
            object_pairs_hook=_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(
                I6Rejected("nonfinite frozen manifest")
            ),
        )
        canonical = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (OSError, ValueError, TypeError) as exc:
        raise I6Rejected("frozen manifest invalid or unreadable") from exc
    if hashlib.sha256(canonical).hexdigest() != FROZEN_SHA256:
        raise I6Rejected("frozen I6 prospective manifest drift")
    if (
        value["issue"] != 529
        or value["base_i5"] != "7637f2369b4fa7fcf72abadd4fb378612d780612"
        or value["native_s15_action_refs"] != ["MOVE_BACKWARD"]
        or value["native_source_fixture"] != "S17_DETERMINISTIC_TEST_DOUBLE"
        or value["physical_source_attested"] is not False
        or value["true_native_s15_competing_actions"] is not False
        or value["s11_production_grant"] is not False
        or value["c15_spatial_label_signed"] is not False
        or value["production_go"] is not False
    ):
        raise I6Rejected("foreign physical or authority claim embedded in I6")
    return value


def adjudicate_i6(
    native: NativeShape,
    caller_source_consequence: WorldConsequence,
    caller_current_closed: ActionLifecycle,
    caller_current_feedback: LearningFeedbackInterpretation,
    b16: BatchLedger,
    caller_current_b16: BatchLedger,
    *,
    requested_mode: str = "offline",
) -> I6Verdict:
    """Read existing exact typed source identities but NEVER admit a native join.

    Caller-supplied owner roots establish only within-fixture identity, not a
    verified Minecraft process. No real native actions run in this function.
    """
    m = read_manifest()
    if requested_mode != "offline":
        raise I6PromotionDenied("no physical, production, Action, L2 or Habit grant")
    if not isinstance(native, NativeShape):
        raise I6Rejected("typed S15/S16/S17 NativeShape required")
    if not isinstance(b16, BatchLedger) or b16 is not caller_current_b16:
        raise I6Rejected("exact caller-current B16 source ledger required")
    if b16.session not in m["b16_source_sessions"]:
        raise I6Rejected("foreign B16 session is not from frozen B16 lineage")
    if (
        b16.revision != 0
        or len(b16.trials) != N_TRIALS
        or len(b16.evidence_ids) != 10
        or b16.world.session != b16.session
        or b16.world.revision != b16.revision
    ):
        raise I6Rejected("B16 must have ten exact alternate-action source receipts")
    b16.assert_current()

    x = native
    if (
        not isinstance(x.issued, ActionLifecycle)
        or not isinstance(x.command, MineflayerCommand)
        or not isinstance(x.binding, ExecutionBindingResult)
        or not isinstance(x.consequence, WorldConsequence)
        or not isinstance(x.outcome, ActionOutcomeInterpretation)
        or not isinstance(x.closed, ActionLifecycle)
        or not isinstance(x.supervisor, ActionSupervisor)
        or not isinstance(x.criterion, ActionFeedbackCriterion)
        or not isinstance(x.feedback, LearningFeedbackInterpretation)
        or x.consequence is not caller_source_consequence
        or x.closed is not caller_current_closed
        or x.feedback is not caller_current_feedback
    ):
        raise I6Rejected("exact source/owner typed identity not supplied")
    if (
        x.supervisor.get(x.closed.action_id) is not x.closed
        or x.supervisor.open_actions
        or not x.closed.is_current_snapshot
        or x.issued.state is not ActionState.ISSUED
        or x.closed.state is not ActionState.OUTCOME
        or x.issued.is_current_snapshot
        or x.issued.events != x.closed.events[:-1]
        or x.closed.events[-1].provenance != x.consequence.provenance
    ):
        raise I6Rejected("Action issuer historical/current owner lineage mismatch")
    if (
        x.command.action_ref != MOVE_BACKWARD_ACTION_REF
        or x.command.action_ref != x.binding.action_ref
        or x.command.binding_id != x.binding.binding_id
        or x.command.action_id != x.issued.action_id
        or x.binding.action_id != x.issued.action_id
        or x.closed.action_id != x.issued.action_id
        or x.issued.skill_execution_id != x.binding.skill_execution_id
        or x.closed.intent_id != x.binding.intent_id
        or x.consequence.action_id != x.command.action_id
        or x.consequence.binding_id != x.command.binding_id
        or x.consequence.action_ref != x.command.action_ref
        or x.consequence.status is not WorldConsequenceStatus.EXECUTED
        or x.consequence.before_observation is None
        or x.consequence.after_observation is None
        or x.consequence.dispatch_receipt is None
        or x.consequence.cleanup_receipt is None
        or x.consequence.before_observation.session_id != x.consequence.session_id
        or x.consequence.after_observation.session_id != x.consequence.session_id
        or x.consequence.before_observation.seq
        >= x.consequence.after_observation.seq
    ):
        raise I6Rejected("S15 exact action and S16 completed source invalid")

    if (
        x.outcome.action_id != x.consequence.action_id
        or x.outcome.binding_id != x.consequence.binding_id
        or x.outcome.action_ref != x.consequence.action_ref
        or x.outcome.session_id != x.consequence.session_id
        or x.outcome.world_provenance != x.consequence.provenance
        or x.outcome.disposition is not ActionOutcomeDisposition.OUTCOME
        or x.outcome.reason_code != "observed_execution"
        or x.feedback.status is not LearningFeedbackInterpretationStatus.PRODUCED
        or x.feedback.feedback is None
        or x.feedback.criterion_id != x.criterion.criterion_id
        or x.feedback.target_id != x.criterion.target_id
        or x.feedback.target_id != m["native_shaped_s17_target"]
        or x.feedback.world_provenance != x.consequence.provenance
        or x.feedback.action_outcome_provenance != x.outcome.provenance
    ):
        raise I6Rejected("S16 interpretation/S17 criterion feedback disconnected")

    # S17's existing pure interpreter independently checks exact criterion
    # semantics without introducing new Action/Learning owner transitions.
    restored = interpret_action_outcome_as_learning_feedback(
        x.closed, x.outcome, x.criterion,
        provenance=x.feedback.provenance,
    )
    if restored != x.feedback:
        raise I6Rejected("S17 feedback differs from existing native interpreter")
    if b16.session == x.consequence.session_id:
        raise I6Rejected("foreign B16 IDs cannot be relabeled as native source")
    return I6Verdict(
        classification=m["classification"],
        native_action_id=x.closed.action_id,
        native_shaped_session=x.consequence.session_id,
        native_s17_target=x.feedback.target_id,
        b16_foreign_session=b16.session,
        b16_source_pairs=len(b16.trials),
    )
