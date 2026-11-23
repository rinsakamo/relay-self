"""Independent DEV Skill/Goal evaluation after a fenced physical Action.

Pure assessment is read-only. Opt-in application uses existing SkillExecution
and IntentCommitment transitions; it never issues WorldBody actions, retries a
native command, assigns new goals, installs learning or claims Paper damage.
ATTACK's successful local hit is NOT proof that DEFEND_SELF is satisfied.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.python_protocol import MineflayerObservation
from experiments.cognitive_physical_attack_runner import CognitivePhysicalAttackResult
from experiments.cognitive_physical_eat_runner import CognitivePhysicalEatResult
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.cognitive_minimal_dev import Selection
from relay_self.intent import IntentCommitment
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.skill import SkillExecution, SkillState


class SemanticEvaluationRefusal(ValueError):
    """Source, lifecycle or physical history is not safe to evaluate."""


class SkillEvidence(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNKNOWN = "UNKNOWN"


class GoalEvidence(str, Enum):
    SATISFIED = "SATISFIED"
    ACTIVE = "ACTIVE"
    UNKNOWN = "UNKNOWN"


PhysicalResult = CognitivePhysicalEatResult | CognitivePhysicalAttackResult


@dataclass(frozen=True, slots=True)
class SemanticAssessment:
    """Evidence for one innate Skill and its *separate* selected Goal."""

    self_id: str
    session_id: str
    intent_id: str
    skill_execution_id: str
    action_id: str
    skill_id: str
    goal_id: str
    target_ref: str
    native_after_seq: int
    evaluation_probe_seq: int
    evaluation_request_id: str
    evaluation_source_ref: str
    skill_evidence: SkillEvidence
    goal_evidence: GoalEvidence
    skill_reason: str
    goal_reason: str
    independent_paper_damage_attested: bool = False
    memory_published: bool = False
    qualifying_real_world: bool = False


@dataclass(frozen=True, slots=True)
class SemanticApplication:
    """New existing-lifecycle snapshot only; no inferred completion."""

    skill_state: str
    intent_state: str
    skill_transition_applied: bool
    intent_transition_applied: bool
    memory_published: bool = False


def evaluate_semantic_outcome_dev(
    result: PhysicalResult,
    selection: Selection,
    *,
    post_goal_probe: MineflayerObservation,
    journal: PhysicalActionJournal,
    supervisor: ActionSupervisor,
    hunger_threshold: float,
) -> SemanticAssessment:
    """Require a fresh, source-qualified read-only observation AFTER Action.

    A single child ACK or L0 terminal candidate is never sufficient alone.
    This evaluator uses the existing trusted WAL plus capability-specific
    postcondition witnesses but does not grant physical or memory authority.
    """
    if (
        not isinstance(result, (CognitivePhysicalEatResult, CognitivePhysicalAttackResult))
        or not isinstance(selection, Selection)
        or selection.status != "READY"
        or selection.option is None
        or selection.world_scope is None
        or not isinstance(post_goal_probe, MineflayerObservation)
        or not isinstance(journal, PhysicalActionJournal)
        or not isinstance(supervisor, ActionSupervisor)
        or type(hunger_threshold) not in (int, float)
        or not math.isfinite(hunger_threshold)
        or not 0 <= hunger_threshold <= 20
    ):
        raise SemanticEvaluationRefusal("typed selected evaluation and threshold required")
    option = selection.option
    scope = selection.world_scope
    skill = result.skill_execution_snapshot
    if (
        not isinstance(skill, SkillExecution)
        or not skill.is_current_snapshot
        or skill.state is not SkillState.STARTED
        or skill.execution_id != result.skill_execution_id
        or skill.intent_id != result.intent_id
        or skill.skill_id != option.skill_id
        or result.selected_target_ref != option.target_ref
        or scope.world_session_id is None
        or journal._body["self_id"] != scope.self_id
        or not result.l0_trace
        or tuple(x.status for x in result.l0_trace) != (
            "PROPOSE_ACTION", "AWAIT_ACTION", "ADVANCED", "TERMINAL_CANDIDATE"
        )
        or result.action_id != result.action.terminal.action_id
        or result.intent_id != result.action.terminal.intent_id
        or result.skill_execution_id != result.action.terminal.skill_execution_id
        or journal.digest != result.journal_sha256
    ):
        raise SemanticEvaluationRefusal("selected current Skill/L0/physical history mismatch")
    journal.require_clear()
    records = journal.records
    if not records or records[-1]["action_id"] != result.action_id:
        raise SemanticEvaluationRefusal("exact terminal WAL record required")
    row = records[-1]
    terminal = supervisor.get(result.action_id)
    if (
        terminal is not result.action.terminal
        or terminal.state is not ActionState.OUTCOME
        or not terminal.is_current_snapshot
        or row["session_id"] != scope.world_session_id
        or row["intent_id"] != result.intent_id
        or row["skill_execution_id"] != result.skill_execution_id
        or row["target_ref"] != option.target_ref
    ):
        raise SemanticEvaluationRefusal("Action OUTCOME not current/owned")
    after = result.action.after
    if (
        after.kind != "probe" or not after.request_id
        or after.session_id != scope.world_session_id
        or row["after_seq"] != after.seq
        or post_goal_probe.kind != "probe" or not post_goal_probe.request_id
        or post_goal_probe.request_id == after.request_id
        or post_goal_probe.session_id != after.session_id
        or post_goal_probe.seq <= after.seq
        or post_goal_probe.provenance.source != "mineflayer"
        or post_goal_probe.snapshot.health <= 0
        or post_goal_probe.snapshot.oxygen_level == 0
    ):
        raise SemanticEvaluationRefusal(
            "fresh same-session viable post-Action evaluation probe required"
        )

    if isinstance(result, CognitivePhysicalEatResult):
        a = result.action
        if (
            option.goal_id != "HUNGER_RELIEF"
            or option.skill_id != "EAT" or option.skill_version != 1
            or option.target_kind != "FOOD"
            or option.target_ref != f"inventory:{a.item}"
            or row["capability"] != "EAT"
            or row["status"] != "NATIVE_EAT_OUTCOME"
            or row["effect_seqs"] != [a.equip.seq, a.consume.seq]
            or a.equip.result != "applied" or a.consume.result != "applied"
            or a.equip.action_id != result.action_id + "-equip"
            or a.consume.action_id != result.action_id + "-consume"
            or a.equip.session_id != after.session_id
            or a.consume.session_id != after.session_id
            or not row["food_before"] < row["food_after"]
            or not a.food_before < a.food_after
            or not a.item_count_after < a.item_count_before
            or row["count_after"] != a.item_count_after
            or row["count_before"] != a.item_count_before
        ):
            raise SemanticEvaluationRefusal("EAT local physical consequence not bound")
        skill_reason = "EAT_FOOD_INCREASE_AND_ITEM_CONSUMED"
        if post_goal_probe.snapshot.food > hunger_threshold:
            goal_evidence = GoalEvidence.SATISFIED
            goal_reason = "HUNGER_PREDICATE_NO_LONGER_TRIGGERED"
        else:
            goal_evidence = GoalEvidence.ACTIVE
            goal_reason = "HUNGER_PREDICATE_STILL_ACTIVE"
    else:
        a = result.action
        if (
            option.goal_id != "DEFEND_SELF"
            or option.skill_id != "ATTACK" or option.skill_version != 1
            or option.target_kind != "ZOMBIE"
            or option.target_ref != f"entity:{a.entity_id}"
            or row["capability"] != "ATTACK"
            or row["status"] != "NATIVE_ATTACK_HURT_OBSERVED"
            or row["effect_seqs"] != [a.ack.seq]
            or row["hurt_seq"] != a.hurt.seq
            or row["target_entity_id"] != a.entity_id
            or a.ack.result != "applied" or a.ack.effect != "attack_entity"
            or a.ack.action_id != result.action_id + "-attack"
            or a.ack.session_id != after.session_id
            or a.hurt.session_id != after.session_id
            or a.hurt.entity_id != a.entity_id
            or a.hurt.source_entity_id is None
            or a.hurt.source_entity_id != a.hurt.actor_entity_id
            or row["source_entity_id"] != a.hurt.source_entity_id
            or row["actor_entity_id"] != a.hurt.actor_entity_id
        ):
            raise SemanticEvaluationRefusal("ATTACK local attributed hurt not bound")
        skill_reason = "ATTACK_SOURCE_ATTRIBUTED_HURT_OBSERVED"
        coverage = post_goal_probe.snapshot.nearby_entities_coverage
        if coverage.truncated:
            goal_evidence = GoalEvidence.UNKNOWN
            goal_reason = "DEFENSE_ENTITY_COVERAGE_TRUNCATED"
        elif any(e.name == "zombie" for e in post_goal_probe.snapshot.nearby_entities):
            goal_evidence = GoalEvidence.ACTIVE
            goal_reason = "ZOMBIE_THREAT_STILL_OBSERVED"
        else:
            # Disappearance from an adapter's 16m registry is not an
            # independent source-bound proof that Self is safe.
            goal_evidence = GoalEvidence.UNKNOWN
            goal_reason = "THREAT_NOT_OBSERVED_BUT_SAFETY_NOT_ATTESTED"

    return SemanticAssessment(
        self_id=scope.self_id, session_id=after.session_id,
        intent_id=result.intent_id, skill_execution_id=result.skill_execution_id,
        action_id=result.action_id, skill_id=option.skill_id,
        goal_id=option.goal_id, target_ref=option.target_ref,
        native_after_seq=after.seq,
        evaluation_probe_seq=post_goal_probe.seq,
        evaluation_request_id=post_goal_probe.request_id,
        evaluation_source_ref=post_goal_probe.provenance.reference,
        skill_evidence=SkillEvidence.SUPPORTED,
        goal_evidence=goal_evidence, skill_reason=skill_reason,
        goal_reason=goal_reason,
    )


def apply_semantic_outcome_dev(
    assessment: SemanticAssessment,
    result: PhysicalResult,
    selection: Selection,
    *,
    post_goal_probe: MineflayerObservation,
    journal: PhysicalActionJournal,
    supervisor: ActionSupervisor,
    intent_owner: IntentCommitment,
    hunger_threshold: float,
) -> SemanticApplication:
    """Explicit one-shot transition using existing owners; never a new owner.

    The immutable assessment is re-derived immediately to prevent a forged
    SATISFIED verdict from completing an Intent or replaying a stale Skill.
    """
    if not isinstance(assessment, SemanticAssessment):
        raise SemanticEvaluationRefusal("typed assessment required")
    actual = evaluate_semantic_outcome_dev(
        result, selection, post_goal_probe=post_goal_probe,
        journal=journal, supervisor=supervisor,
        hunger_threshold=hunger_threshold,
    )
    if assessment != actual or not isinstance(intent_owner, IntentCommitment):
        raise SemanticEvaluationRefusal("assessment changed or Intent owner missing")
    skill = result.skill_execution_snapshot
    assert skill is not None
    owner = intent_owner.current_intent
    if (
        owner is None or owner.intent_id != assessment.intent_id
        or owner.objective != assessment.goal_id
        or intent_owner.pending_reconsideration is not None
        or supervisor.open_actions
        or skill.state is not SkillState.STARTED
        or not skill.is_current_snapshot
    ):
        raise SemanticEvaluationRefusal("selected owner changed before semantic apply")
    at_ns = max(
        supervisor.last_at_ns or 0,
        intent_owner.last_at_ns or 0,
        skill.events[-1].at_ns,
    ) + 1
    # Skill success is local to *one innate action* with attested physical
    # effect; NOT equivalent to achieving the broader Goal.
    if assessment.skill_evidence is SkillEvidence.SUPPORTED:
        skill = skill.succeed(
            reason=assessment.skill_reason,
            at_ns=at_ns, provenance=post_goal_probe.provenance,
        )
    else:
        raise SemanticEvaluationRefusal("unsupported Skill cannot be completed")
    # A lingering threat or hunger predicate keeps the Intent committed.
    if assessment.goal_evidence is GoalEvidence.SATISFIED:
        intent_owner.complete(
            assessment.intent_id, reason=assessment.goal_reason,
            at_ns=at_ns + 1, provenance=post_goal_probe.provenance,
        )
    return SemanticApplication(
        skill_state=skill.state.value,
        intent_state=(
            "committed" if intent_owner.current_intent is not None
            else "completed"
        ),
        skill_transition_applied=True,
        intent_transition_applied=(
            assessment.goal_evidence is GoalEvidence.SATISFIED
        ),
    )
