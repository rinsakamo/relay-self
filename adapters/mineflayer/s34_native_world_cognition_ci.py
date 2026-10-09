"""S34 genuine consecutive Action1/2/3, real Action1 governed feedback/retained update.

All three physical Actions execute through three separate genuine Mineflayer
sessions on ONE temporary real Minecraft server. Original S19's structured
external threat input and fixed policies remain fixture inputs; actual physical
motion feedback drives retained 3/rev0 -> 4/rev1. No autonomous scheduling.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import test_postmain_local_recovery_action as s23
import test_postmain_second_action_closure as s20
import test_postmain_skill_exit_routing as s22
import test_postmain_skill_terminal_closure as s21
import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import (
    WorldConsequenceStatus,
    build_mineflayer_command,
    execute_mineflayer_command,
)
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig, MineflayerObservation
from adapters.mineflayer.s31a_real_server_ci import (
    BOT_USERNAME,
    MINECRAFT_VERSION,
    MINEFLAYER_VERSION,
    SERVER_HOST,
    SERVER_PORT,
    S31ABlocked,
    _await_spawn,
    _command,
    _correlated_observe,
    _fetch_official_server,
    _ready_server,
    _shutdown_server,
    _verified_target,
    _write_config,
)
from relay_self.action import ActionState
from relay_self.action_outcome import record_interpreted_action_outcome
from relay_self.action_supervision import ActionSupervisor
from relay_self.postfailure_cognition import run_explicit_postfailure_epoch
from relay_self.second_epoch_action import require_fresh_second_consequence
from relay_self.source_native_world import project_source_native_threat


class S34EvidenceFailure(RuntimeError):
    """Refuse unqualified real source, Action/Skill owner or learning lineage."""


MAX_GOAL_DISTANCE_M = 4.0


@dataclass(frozen=True, slots=True)
class NativeThreat:
    """A native Mineflayer exact-ID target that passed complete geometry checks."""
    observation: MineflayerObservation
    entity_id: int
    distance_m: float
    request_id: str


def _native_threat(
    observation: MineflayerObservation, request_id: str,
    *, expected_entity_id: int | None = None,
) -> NativeThreat:
    if (
        not isinstance(observation, MineflayerObservation)
        or observation.kind != "probe"
        or observation.request_id != request_id
        or not request_id
        or observation.provenance.source != "mineflayer"
    ):
        raise S34EvidenceFailure("real correlated probe and exact request ID required")
    target = _verified_target(observation)
    if target is None:
        raise S34EvidenceFailure("zombie absent, threat proposition unsupported")
    if expected_entity_id is not None and target["entity_id"] != expected_entity_id:
        raise S34EvidenceFailure("zombie identity changed across sessions")
    coverage = observation.snapshot.nearby_entities_coverage
    if coverage.source_scope != "mineflayer_entity_registry" or coverage.max_distance != 16:
        raise S34EvidenceFailure("incomplete or unqualified native registry scope")
    if not 0 < target["distance_m"] <= 16:
        raise S34EvidenceFailure("out of native sensing range")
    return NativeThreat(
        observation=observation, entity_id=target["entity_id"],
        distance_m=target["distance_m"], request_id=request_id,
    )


async def _real_epoch_one(supervisor, adapter, native: NativeThreat):
    if native.observation.session_id != adapter.started.session_id:
        raise S34EvidenceFailure("initial World evidence session mismatch")
    if native.distance_m >= MAX_GOAL_DISTANCE_M:
        raise S34EvidenceFailure("not a real nearby threat: no SUPPORT assertion")
    p = s19.PropositionKey("entity", "zombie-1", "nearby")
    evidence = s19.BeliefEvidence(
        "E1",
        p,
        s19.EvidenceRelation.SUPPORT,
        native.observation.provenance,
    )
    attention = s19.select_attention(
        (
            s19.AttentionCandidate(
                "E1",
                "belief-evidence:E1",
                native.observation.provenance,
                focus_keys=("zombie-1",),
            ),
        ),
        s19.AttentionCriterion("focus-zombie", focus_key="zombie-1"),
    )
    assert attention.selected[0].candidate_id == "E1"

    belief = s19.assess_belief(
        (evidence,),
        s19.BeliefCriterion("zombie-nearby", p),
    )
    concept = s19.classify_concept(
        s19.concept_candidate_from_belief(
            belief,
            candidate_id="belief:zombie-nearby",
            payload_ref="transient:belief:zombie-nearby",
            provenance=s19.provenance("belief-to-concept"),
        ),
        s19.ConceptCriterion(
            criterion_id="supported-nearby",
            concept=s19.ConceptKey("spatial", "nearby_threat"),
            required_features=(
                s19.ConceptFeature("belief_status", "supported"),
                s19.ConceptFeature("proposition", p.canonical),
            ),
        ),
    )

    base = s19.prediction_state_from_concept(
        concept,
        state_id="threat:zombie-1",
        extra_variables=(s19.StateVariable("comparison_score", 99),),
        provenance=s19.provenance("concept-to-prediction"),
    )
    wait_prediction = s19.predict_transition(
        base,
        s19.TransitionRule(
            rule_id="wait",
            preconditions=(s19.StateVariable("concept", "spatial:nearby_threat"),),
            assignments=(s19.StateVariable("comparison_score", 8),),
            provenance=s19.provenance("wait"),
        ),
    )
    move_prediction = s19.predict_transition(
        base,
        s19.TransitionRule(
            rule_id="move-away",
            preconditions=(s19.StateVariable("concept", "spatial:nearby_threat"),),
            assignments=(s19.StateVariable("comparison_score", 3),),
            provenance=s19.provenance("move"),
        ),
    )
    plan = s19.select_plan(
        (
            s19.plan_candidate_from_prediction(
                wait_prediction,
                candidate_id="WAIT",
                feature_keys=("comparison_score",),
                provenance=s19.provenance("wait-plan"),
            ),
            s19.plan_candidate_from_prediction(
                move_prediction,
                candidate_id="MOVE_AWAY",
                feature_keys=("comparison_score",),
                provenance=s19.provenance("move-plan"),
            ),
        ),
        s19.PlanningCriterion(
            criterion_id="minimize-comparison-score",
            feature_key="comparison_score",
            direction=s19.PlanningDirection.MINIMIZE,
        ),
    )
    assert plan.selected is not None
    assert plan.selected.candidate_id == "MOVE_AWAY"

    repertoire = s19.HabitRepertoire(
        repertoire_id="survival-habits",
        revision=7,
        rules=(
            s19.HabitRule(
                habit_id="H1",
                cue_requirements=(
                    s19.CueFeature("concept", "spatial:nearby_threat"),
                ),
                candidate_ref="MOVE_AWAY",
                priority=10,
                provenance=s19.provenance("habit"),
            ),
        ),
        provenance=s19.provenance("repertoire"),
    )
    habit = s19.select_habit(
        repertoire,
        s19.HabitCue(
            cue_id="nearby-threat",
            features=(
                s19.CueFeature("concept", "spatial:nearby_threat"),
            ),
            provenance=s19.provenance("cue"),
        ),
    )
    assert habit.selected_candidate_ref == "MOVE_AWAY"

    route = s19.adjudicate_routes(
        plan,
        habit,
        s19.RouteCriterion(
            criterion_id="route-fail-closed",
            conflict_policy=s19.RouteConflictPolicy.FAIL_CLOSED,
        ),
        provenance=s19.provenance("route"),
    )
    assert route.status is s19.RouteDecisionStatus.AGREED
    control = s19.control_candidate_from_route_decision(route)
    assert control is not None

    intent = s19.IntentCommitment()
    intent.commit(
        "escape-threat",
        objective="escape the nearby threat",
        at_ns=1,
        provenance=s19.provenance("intent"),
    )
    admission_criterion = s19.ExecutionAdmissionCriterion(
        criterion_id="escape-threat-allow-list",
        policy=s19.AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
        required_intent_id="escape-threat",
        allowed_candidate_refs=("MOVE_AWAY",),
    )
    admission = s19.admit_control_candidate(
        control,
        route,
        intent,
        admission_criterion,
        provenance=s19.provenance("admission"),
    )
    assert admission.status is s19.AdmissionDecisionStatus.ADMITTED

    binding = s19.ExecutionBinding(
        binding_id="binding-move-away-1",
        candidate_ref="MOVE_AWAY",
        required_intent_id="escape-threat",
        skill_execution_id="skill-exec-escape-1",
        skill_ref="escape-movement",
        action_id="action-move-backward-1",
        action_ref="MOVE_BACKWARD",
        provenance=s19.provenance("binding"),
    )
    bound = s19.resolve_execution_binding(
        admission,
        control,
        route,
        intent,
        admission_criterion,
        binding,
        provenance=s19.provenance("resolve-binding"),
    )
    skill, proposed, binding_result = s19.start_and_propose_bound_execution(
        bound,
        intent,
        at_ns=10,
        provenance=s19.provenance("start-propose"),
    )
    assert skill.state is s19.SkillState.STARTED
    assert proposed.state is s19.ActionState.PROPOSED

    authorized = proposed.authorize(
        at_ns=11,
        provenance=s19.provenance("authorize"),
        authority="s18-explicit-authority",
    )
    issued = supervisor.issue(
        authorized,
        at_ns=12,
        deadline_ns=100,
        provenance=s19.provenance("issue"),
    )
    assert issued.state is s19.ActionState.ISSUED

    command = build_mineflayer_command(issued, binding_result)
    consequence = await execute_mineflayer_command(
        adapter, command, timeout_s=9,
        provenance=s19.provenance("s34-real-world1"),
    )
    if consequence.status is not WorldConsequenceStatus.EXECUTED:
        raise S34EvidenceFailure("real Action1 consequence not EXECUTED")
    outcome_interpretation = s19.interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        provenance=s19.provenance("outcome-interpretation"),
    )
    closed = s19.record_interpreted_action_outcome(
        supervisor,
        outcome_interpretation,
        at_ns=20,
    )
    assert closed.state is s19.ActionState.OUTCOME
    assert outcome_interpretation.reason_code == "observed_execution"

    feedback_criterion = s19.ActionFeedbackCriterion(
        criterion_id="risk-from-observed-move",
        target_id="risk_weight",
        required_action_id="action-move-backward-1",
        required_binding_id="binding-move-away-1",
        required_action_ref="MOVE_BACKWARD",
        required_action_state=s19.ActionState.OUTCOME,
        required_outcome_disposition=s19.ActionOutcomeDisposition.OUTCOME,
        required_outcome_reason="observed_execution",
        feedback_direction=s19.FeedbackDirection.INCREASE,
        provenance=s19.provenance("feedback-criterion"),
    )
    feedback_interpretation = s19.interpret_action_outcome_as_learning_feedback(
        closed,
        outcome_interpretation,
        feedback_criterion,
        provenance=s19.provenance("feedback"),
    )
    assert (
        feedback_interpretation.status
        is s19.LearningFeedbackInterpretationStatus.PRODUCED
    )
    assert feedback_interpretation.feedback is not None

    state = s19.LearningPreferenceState(
        target_id="risk_weight",
        value=3,
        minimum=0,
        maximum=10,
        revision=0,
        origin_provenance=s19.provenance("learning-origin"),
    )
    proposal = s19.propose_learning_update(
        state,
        feedback_interpretation.feedback,
        s19.LearningUpdateRule(
            rule_id="bounded-risk-step",
            version=1,
            step=1,
        ),
    )
    committed = s19.commit_learning_update(
        state,
        proposal,
        s19.LearningUpdateAuthority(
            authority_id="s18-learning-authority",
            target_id="risk_weight",
            provenance=s19.provenance("learning-authority"),
        ),
        provenance=s19.provenance("learning-commit"),
    )

    assert committed.previous_state.value == 3
    assert committed.previous_state.revision == 0
    assert committed.new_state.value == 4
    assert committed.new_state.revision == 1

    return committed, intent, closed, feedback_interpretation, consequence, issued, skill



def _native_epoch_two(supervisor, intent, owner_snapshot, supplied_snapshot, *, expected_revision, native: NativeThreat):
    if native.distance_m >= MAX_GOAL_DISTANCE_M:
        raise S34EvidenceFailure("no nearby second-epoch threat evidence")
    """Separate caller invocation: ATT/BLF/CNC/PRD/PLAN/ROUTE/fresh ADMISSION.

    A/B alternatives use identical deterministic policies and structured
    external evidence. Only the explicitly supplied owner-local snapshot
    changes; this apparatus does not install a learned utility policy.
    """
    outputs = {}
    criterion = s19.PlanningCriterion(
        criterion_id="s19-minimize-structured-comparison",
        feature_key="comparison_score",
        direction=s19.PlanningDirection.MINIMIZE,
    )
    admission_guard = s19.ExecutionAdmissionCriterion(
        criterion_id="s19-fresh-admission",
        policy=s19.AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
        required_intent_id="escape-threat",
        allowed_candidate_refs=("WAIT", "MOVE_AWAY"),
    )
    proposition = s19.PropositionKey("entity", "zombie-1", "nearby")
    evidence = s19.BeliefEvidence(
        "E1", proposition, s19.EvidenceRelation.SUPPORT, native.observation.provenance,
    )
    attention_input = s19.AttentionCandidate(
        "E1", "belief-evidence:E1", native.observation.provenance,
        focus_keys=("zombie-1",),
    )
    attention_criterion = s19.AttentionCriterion("focus-zombie", focus_key="zombie-1")
    belief_criterion = s19.BeliefCriterion("zombie-nearby", proposition)
    concept_criterion = s19.ConceptCriterion(
        criterion_id="supported-nearby",
        concept=s19.ConceptKey("spatial", "nearby_threat"),
        required_features=(
            s19.ConceptFeature("belief_status", "supported"),
            s19.ConceptFeature("proposition", proposition.canonical),
        ),
    )
    wait_rule = s19.TransitionRule(
        rule_id="s19-wait",
        preconditions=(s19.StateVariable("concept", "spatial:nearby_threat"),),
        assignments=(s19.StateVariable("action_kind", "wait"),),
        provenance=s19.provenance("s19-wait-rule"),
    )
    move_rule = s19.TransitionRule(
        rule_id="s19-move",
        preconditions=(s19.StateVariable("concept", "spatial:nearby_threat"),),
        assignments=(
            s19.StateVariable("action_kind", "move_away"),
            s19.StateVariable("comparison_score", 7),
        ),
        provenance=s19.provenance("s19-move-rule"),
    )
    route_criterion = s19.RouteCriterion("s19-plan-only", allow_single_source=True)
    outputs["external"] = (
        proposition, evidence, attention_input, attention_criterion,
        belief_criterion, concept_criterion,
    )
    outputs["policies"] = (
        wait_rule, move_rule, criterion, route_criterion, admission_guard,
        "wait_score_is_twice_retained_risk_weight",
    )

    def attention_step():
        outputs["attention"] = s19.select_attention(
            (attention_input,), attention_criterion,
        )
        return None

    def belief_step():
        assert outputs["attention"].selected[0].candidate_id == evidence.evidence_id
        outputs["belief"] = s19.assess_belief((evidence,), belief_criterion)
        return None

    def concept_step():
        outputs["concept"] = s19.classify_concept(
            s19.concept_candidate_from_belief(
                outputs["belief"],
                candidate_id="belief:zombie-nearby",
                payload_ref="transient:belief:zombie-nearby",
                provenance=s19.provenance("belief-to-concept"),
            ),
            concept_criterion,
        )
        return None

    def predict_wait_step():
        read = s19.read_retained_preference(
            owner_snapshot, supplied_snapshot,
            required_target_id="risk_weight",
            expected_revision=expected_revision,
            provenance=s19.provenance("epoch-two-retained-read"),
        )
        # The explicit caller comparison projection is fixed in both A/B
        # branches. PRD itself remains the *existing* stateless predictor.
        original = s19.prediction_state_from_concept(
            outputs["concept"],
            state_id="s19-threat-zombie-1",
            extra_variables=(
                s19.StateVariable("comparison_score", 2 * read.snapshot.value),
                s19.StateVariable("risk_weight", read.snapshot.value),
            ),
            provenance=s19.provenance("s19-concept-retained-to-prediction"),
        )
        record = read.last_update
        lineage_refs = (
            f"learning-target:{read.snapshot.target_id}",
            f"learning-revision:{read.revision}",
        )
        lineage_provenance = (read.origin_provenance, read.read_provenance)
        if record is not None:
            lineage_refs += (
                f"learning-feedback:{record.feedback_id}",
                f"learning-rule:{record.rule_id}:v{record.rule_version}",
                f"learning-authority:{record.authority_id}",
                f"learning-commit-revision:{record.committed_revision}",
            )
            lineage_provenance += (
                record.feedback_provenance,
                record.authority_provenance,
                record.update_provenance,
            )
        state = s19.replace(
            original,
            source_refs=(*original.source_refs, *lineage_refs),
            source_provenance=(*original.source_provenance, *lineage_provenance),
        )
        outputs["read"] = read
        outputs["prediction_input"] = state
        outputs["wait_prediction"] = s19.predict_transition(state, wait_rule)
        return None

    def predict_move_step():
        outputs["move_prediction"] = s19.predict_transition(
            outputs["prediction_input"], move_rule,
        )
        return None

    def plan_step():
        outputs["plan"] = s19.select_plan(
            (
                s19.plan_candidate_from_prediction(
                    outputs["wait_prediction"],
                    candidate_id="WAIT",
                    feature_keys=("comparison_score",),
                    provenance=s19.provenance("s19-wait-plan"),
                ),
                s19.plan_candidate_from_prediction(
                    outputs["move_prediction"],
                    candidate_id="MOVE_AWAY",
                    feature_keys=("comparison_score",),
                    provenance=s19.provenance("s19-move-plan"),
                ),
            ),
            criterion,
        )
        return None

    def route_step():
        outputs["route"] = s19.adjudicate_routes(
            outputs["plan"], None, route_criterion,
            provenance=s19.provenance("s19-route"),
        )
        outputs["control"] = s19.control_candidate_from_route_decision(outputs["route"])
        return None

    def admit_step():
        outputs["admission"] = s19.admit_control_candidate(
            outputs["control"], outputs["route"], intent, admission_guard,
            provenance=s19.provenance("s19-fresh-admission"),
        )
        return None

    work = (
        ("s19-att", "att.select", attention_step),
        ("s19-blf", "blf.assess", belief_step),
        ("s19-cnc", "cnc.classify", concept_step),
        ("s19-prd-wait", "prd.predict", predict_wait_step),
        ("s19-prd-move", "prd.predict", predict_move_step),
        ("s19-plan", "plan.select", plan_step),
        ("s19-route", "route.adjudicate", route_step),
        ("s19-admit", "execution.admit_candidate", admit_step),
    )
    items = tuple(
        s19.EpochWorkItem(work_id=w, operator_id=o, trigger_ref="caller:s19:second")
        for w, o, _ in work
    )
    bindings = tuple(
        s19.EpochBinding(work_id=w, operator_id=o, invoke=fn)
        for w, o, fn in work
    )
    plan = s19.compile_epoch_plan(
        s19.s17_capability_plan(
            enabled_ids=frozenset(
                ("ATT", "BLF", "CNC", "PRD", "PLAN", "ROUTE", "ADMISSION")
            )
        ),
        s19.S17_DESCRIPTOR_SET,
        due_items=items,
        bindings=bindings,
    )
    result = s19.coordinate_planned_epoch(
        supervisor, plan, bindings=bindings, at_ns=30,
        provenance=s19.provenance("epoch-two-explicit-invoke"),
    )
    return outputs, result




def _prepare_second_real(supervisor, commit, intent, closed1, feedback, native: NativeThreat):
    assert closed1 is supervisor.get(closed1.action_id)
    assert closed1.state is ActionState.OUTCOME
    assert commit.new_state.revision == 1

    values, second_epoch = _native_epoch_two(
        supervisor, intent, commit.new_state, commit.new_state,
        expected_revision=1, native=native,
    )
    assert second_epoch.cognition_requested is False
    assert values["external"][1].provenance == native.observation.provenance
    assert values["plan"].selected is not None
    assert values["plan"].selected.candidate_id == "MOVE_AWAY"
    assert values["admission"].status is s20.AdmissionDecisionStatus.ADMITTED

    binding = s20.ExecutionBinding(
        binding_id=s20.BINDING2,
        candidate_ref="MOVE_AWAY",
        required_intent_id="escape-threat",
        skill_execution_id=s20.SKILL2,
        skill_ref="escape-movement",
        action_id=s20.ACTION2,
        action_ref="MOVE_BACKWARD",
        provenance=s20.p("caller-action2-binding"),
    )
    lineage = s20.validate_second_epoch_lineage(
        supervisor, closed1, feedback, commit.new_state,
        values["prediction_input"], values["plan"], binding,
        provenance=s20.p("explicit-second-action-lineage"),
    )
    assert lineage.second_action_id == s20.ACTION2
    assert lineage.committed_revision == commit.new_state.revision
    assert lineage.first_feedback_id == commit.record.feedback_id

    # Still no Action 2 proposal, commitment, authorization or issue.
    admission_guard = values["policies"][-2]
    assert admission_guard == s20.ExecutionAdmissionCriterion(
        criterion_id="s19-fresh-admission",
        policy=s20.AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
        required_intent_id="escape-threat",
        allowed_candidate_refs=("WAIT", "MOVE_AWAY"),
    )
    bound = s20.resolve_execution_binding(
        values["admission"], values["control"], values["route"],
        intent, admission_guard, binding,
        provenance=s20.p("explicit-second-binding-resolution"),
    )
    # The Action/Skill owner transition records a reference to governed
    # ancestry; this reference does not authorize or issue the new Action.
    action_provenance = s20.p(
        f"{lineage.first_feedback_id}|rev:{lineage.committed_revision}|"
        f"{lineage.second_binding_id}|{lineage.second_action_id}"
    )
    skill2, proposed2, binding_result2 = s20.start_and_propose_bound_execution(
        bound, intent, at_ns=31, provenance=action_provenance,
    )
    assert proposed2.events[0].provenance == action_provenance
    assert skill2.state is s20.SkillState.STARTED
    assert proposed2.state is ActionState.PROPOSED
    return {
        "supervisor": supervisor, "commit": commit, "intent": intent,
        "closed1": closed1, "feedback": feedback, "values": values,
        "second_epoch": second_epoch, "lineage": lineage, "binding": binding,
        "bound": bound, "skill2": skill2, "proposed2": proposed2,
        "binding_result2": binding_result2,
    }




def _real_skill2_evidence(data, closed2, outcome, goal: NativeThreat, after_seq: int):
    if (
        goal.observation.session_id != outcome.session_id
        or goal.observation.seq <= after_seq
        or goal.observation.provenance == outcome.world_provenance
    ):
        raise S34EvidenceFailure("Skill2 goal probe not independent/fresh after Action2")
    status = (
        s21.SkillGoalStatus.VIOLATED
        if goal.distance_m < MAX_GOAL_DISTANCE_M
        else s21.SkillGoalStatus.SATISFIED
    )
    skill = data["skill2"]
    criterion = s21.SkillTerminalCriterion(
        criterion_id="s21-escape-distance",
        skill_id=skill.skill_id,
        goal_ref="escape-distance-observed",
        provenance=s20.p("skill-goal-criterion"),
    )
    evidence = s21.SkillGoalEvidence(
        criterion_id=criterion.criterion_id,
        skill_execution_id=skill.execution_id,
        intent_id=skill.intent_id,
        action_id=closed2.action_id,
        binding_id=outcome.binding_id,
        session_id=outcome.session_id,
        goal_ref=criterion.goal_ref,
        status=status,
        observed_at_ns=41,
        provenance=goal.observation.provenance,
    )
    authority = s21.SkillTerminalAuthority(
        authority_id="s21-skill-closure-authority",
        skill_execution_id=skill.execution_id,
        criterion_id=criterion.criterion_id,
        granted=True,
        provenance=s20.p("explicit-skill-closure-authority"),
    )
    return data, closed2, outcome, criterion, evidence, authority




def _real_skill2_exit(data, action, outcome, goal: NativeThreat, after_seq: int):
    data, action, outcome, criterion21, evidence21, authority21 = _real_skill2_evidence(
        data, action, outcome, goal, after_seq,
    )
    terminal = (
        s22.SkillState.FAILED
        if evidence21.status is s21.SkillGoalStatus.VIOLATED
        else s22.SkillState.SUCCEEDED
    )
    local = s22.LocalPathStatus.AVAILABLE
    impact = s22.IntentImpact.NOT_CHALLENGED
    if terminal is s22.SkillState.CANCELLED:
        closed = data["skill2"].cancel(
            reason="explicit-caller-cancel", at_ns=42,
            provenance=s21.s20.p("explicit-skill-cancel"),
        )
    else:
        assessment21 = s21._assess(data, action, outcome, criterion21, evidence21)
        closed = s21.commit_skill_terminal(
            assessment21, authority21, at_ns=42,
            provenance=s21.s20.p("explicit-skill-terminal"),
        )
    assert closed.state is terminal
    current = data["intent"].current_intent
    assert current is not None
    criterion = s22.SkillExitCriterion(
        criterion_id="s22-skill-exit",
        skill_id=closed.skill_id,
        intent_id=closed.intent_id,
        provenance=s21.s20.p("s22-bounded-criterion"),
    )
    evidence = s22.SkillExitEvidence(
        criterion_id=criterion.criterion_id,
        skill_execution_id=closed.execution_id,
        intent_id=closed.intent_id,
        terminal_state=closed.state,
        terminal_at_ns=closed.events[-1].at_ns,
        terminal_provenance=closed.events[-1].provenance,
        local_path=local,
        alternative_skill_id="alternate-escape-path" if local is s22.LocalPathStatus.AVAILABLE else None,
        intent_impact=impact,
        observed_at_ns=43,
        provenance=s21.s20.p("caller-local-feasibility-and-intent-impact"),
    )
    route = (
        s22.SkillExitRoute.LOCAL_RECOVERY_CANDIDATE
        if local is s22.LocalPathStatus.AVAILABLE
        else s22.SkillExitRoute.RECONSIDERATION_CANDIDATE
    )
    authority = s22.SkillExitAuthority(
        authority_id="s22-caller-handoff",
        criterion_id=criterion.criterion_id,
        intent_id=criterion.intent_id,
        route=route,
        granted=True,
        provenance=s21.s20.p("explicit-handoff-authorization"),
    )
    return data, closed, criterion, evidence, authority




def _real_recovery_prep(data, closed2, outcome2, goal: NativeThreat, after_seq: int):
    data, failed, exit_criterion, evidence, route_authority = _real_skill2_exit(
        data, closed2, outcome2, goal, after_seq,
    )
    assert failed.state is s23.SkillState.FAILED
    assessment = s23.assess_skill_exit(
        failed, data["intent"], exit_criterion, evidence,
    )
    assert assessment.route is s23.SkillExitRoute.LOCAL_RECOVERY_CANDIDATE
    recovery_skill = s23.start_explicit_local_recovery(
        assessment, route_authority,
        execution_id=s23.SKILL3, at_ns=45,
        provenance=s23.p("caller-new-skill-start"),
    )
    assert recovery_skill.state is s23.SkillState.STARTED
    assert data["intent"].pending_reconsideration is None

    # Explicit, separate S12 projection from caller-supplied existing PLAN,
    # then a new S13 policy and decision. No claim of fresh PRD cognition.
    reroute = s23.adjudicate_routes(
        data["values"]["plan"], None,
        s23.RouteCriterion("s23-explicit-recovery-route", allow_single_source=True),
        provenance=s23.p("recovery-route-adjudication"),
    )
    control = s23.control_candidate_from_route_decision(reroute)
    assert control is not None and control.candidate_ref == "MOVE_AWAY"
    criterion = s23.ExecutionAdmissionCriterion(
        criterion_id="s23-recovery-admission",
        policy=s23.AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
        required_intent_id="escape-threat",
        allowed_candidate_refs=("MOVE_AWAY",),
    )
    admission = s23.admit_control_candidate(
        control, reroute, data["intent"], criterion,
        provenance=s23.p("fresh-recovery-admission"),
    )
    assert admission.status is s23.AdmissionDecisionStatus.ADMITTED
    binding = s23.ExecutionBinding(
        binding_id=s23.BINDING3, candidate_ref="MOVE_AWAY",
        required_intent_id="escape-threat",
        skill_execution_id=s23.SKILL3, skill_ref="alternate-escape-path",
        action_id=s23.ACTION3, action_ref="MOVE_BACKWARD",
        provenance=s23.p("caller-recovery-binding"),
    )
    inputs = {
        "assessment": assessment, "route_authority": route_authority,
        "recovery_skill": recovery_skill, "previous_action": data["supervisor"].get(s20.ACTION2),
        "supervisor": data["supervisor"],
        "previous_admission": data["values"]["admission"],
        "new_admission": admission, "control": control, "route": reroute,
        "criterion": criterion, "binding": binding,
    }
    return data, failed, inputs



async def _observe_native_threat(
    session: MineflayerProcessSession,
    *,
    request_prefix: str,
    expected_entity_id: int | None = None,
    after_seq: int | None = None,
) -> NativeThreat:
    for attempt in range(5):
        await asyncio.sleep(2)
        request_id = f"{request_prefix}:{attempt:03d}"
        observation = await _correlated_observe(session, request_id)
        if (
            after_seq is not None
            and observation.seq <= after_seq
        ):
            raise S34EvidenceFailure("probe is not newer than source Action")
        native = _native_threat(
            observation, request_id, expected_entity_id=expected_entity_id,
        )
        return native
    raise S34EvidenceFailure("bounded native zombie observation unavailable")


async def _new_session() -> MineflayerProcessSession:
    session = await MineflayerProcessSession.launch(
        MineflayerLaunchConfig(
            host=SERVER_HOST, port=SERVER_PORT,
            username=BOT_USERNAME, version=MINECRAFT_VERSION,
        ),
        startup_timeout_s=12,
    )
    await _await_spawn(session)
    return session


def _summarize_action(consequence, closed):
    return {
        "action_id": closed.action_id,
        "state": closed.state.value,
        "world_status": consequence.status.value,
        "session_id": consequence.session_id,
        "before_seq": consequence.before_observation.seq,
        "dispatch_seq": consequence.dispatch_receipt.seq,
        "cleanup_seq": consequence.cleanup_receipt.seq,
        "after_seq": consequence.after_observation.seq,
        "movement_distance_m": consequence.movement_distance,
        "source_provenance": consequence.after_observation.provenance.reference,
    }


async def qualify(report_path: Path, server_log: Path) -> int:
    report: dict[str, Any] = {
        "milestone": "S34",
        "status": "BLOCKED",
        "stage": "START",
        "classification": "NOT_QUALIFIED",
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "session_count": 0,
        "real_actions": [],
        "action1_learning_source": "UNDETERMINED",
        "first_external_threat_input": "FROZEN_STRUCTURED_TEST_INPUT_NOT_REAL_SENSOR",
        "second_epoch_external_threat_input": "FROZEN_STRUCTURED_TEST_INPUT_NOT_REAL_SENSOR",
        "skill2_failure_goal_evidence": "CALLER_FIXED_VIOLATED_NOT_REAL_WORLD_GOAL_EVALUATION",
        "automatic_action4_issued": False,
        "autonomous_epoch_reentry": False,
        "cryptographic_world_attestation": False,
        "local_codex_s31b": "SKIPPED",
    }
    server = None
    collector = None
    tmp: tempfile.TemporaryDirectory[str] | None = None
    session: MineflayerProcessSession | None = None
    exit_code = 2
    try:
        if os.environ.get("S34_REAL_SERVER_CI") != "1":
            raise S31ABlocked("S34_REAL_SERVER_CI=1 required")
        if os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("Node test preload forbidden")
        report["stage"] = "OFFICIAL_SERVER_DOWNLOAD"
        tmp = tempfile.TemporaryDirectory(prefix="relay-self-s34-")
        root = Path(tmp.name)
        metadata = await asyncio.to_thread(
            _fetch_official_server, root / "minecraft-server.jar",
        )
        report.update(metadata)
        _write_config(root)
        report["stage"] = "JAVA_SERVER_START"
        server, collector, _ = await _ready_server(
            root, root / "minecraft-server.jar", server_log,
        )

        # 1: the S19 first structured threat input remains a bounded fixture.
        # Real MOVE_BACKWARD supplies physical Action1 outcome; it is NOT
        # replaced by the synthetic S19 FakeSession.
        report["stage"] = "ACTION1_REAL_AND_GOVERNED_LEARNING"
        session = await _new_session()
        supervisor = ActionSupervisor()
        commit, intent, closed1, feedback1, consequence1, issued1, skill1 = (
            await _real_epoch_one(supervisor, session)
        )
        if consequence1.session_id != session.started.session_id:
            raise S34EvidenceFailure("Action1 session mismatch")
        if (
            closed1.state is not ActionState.OUTCOME
            or supervisor.get(closed1.action_id) is not closed1
            or commit.previous_state.value != 3
            or commit.previous_state.revision != 0
            or commit.new_state.value != 4
            or commit.new_state.revision != 1
            or feedback1.feedback is None
        ):
            raise S34EvidenceFailure("Action1 real outcome/learning commit invalid")
        session_id1 = session.started.session_id
        report["real_actions"].append(_summarize_action(consequence1, closed1))
        report["action1_learning_source"] = "REAL_ACTION1_OUTCOME_TO_S19_FEEDBACK_COMMIT"
        report["retained"] = {
            "before_value": commit.previous_state.value,
            "before_revision": commit.previous_state.revision,
            "after_value": commit.new_state.value,
            "after_revision": commit.new_state.revision,
            "feedback_id": feedback1.feedback.feedback_id,
            "feedback_action_id": closed1.action_id,
        }
        await session.shutdown(timeout_s=10)
        if session.process_returncode != 0:
            raise S34EvidenceFailure("Action1 bridge did not close cleanly")
        report["session_count"] = 1
        session = None

        # 2: only NOW the actual learning owner snapshot may drive a new
        # explicit cognitive epoch and independent Action2 admission/issue.
        report["stage"] = "ACTION2_REAL_WITH_RETAINED_READ"
        data = _prepare_second_real(
            supervisor, commit, intent, closed1, feedback1,
        )
        if (
            data["lineage"].committed_revision != 1
            or data["values"]["plan"].selected.candidate_id != "MOVE_AWAY"
            or data["commit"] is not commit
            or data["closed1"] is not closed1
        ):
            raise S34EvidenceFailure("Action2 did not derive from real Action1 retention")
        _authorized2, issued2 = s20._issue_second(data)
        session = await _new_session()
        if session.started.session_id == session_id1:
            raise S34EvidenceFailure("Action2 reused Action1 session UUID")
        command2 = build_mineflayer_command(issued2, data["binding_result2"])
        consequence2 = await execute_mineflayer_command(
            session, command2, timeout_s=9,
            provenance=s20.p("s34-real-world2-consequence"),
        )
        if consequence2.status is not WorldConsequenceStatus.EXECUTED:
            raise S34EvidenceFailure("Action2 did not execute physical movement")
        require_fresh_second_consequence(
            supervisor, issued2, data["binding_result2"], consequence2,
            expected_session_id=session.started.session_id,
            first_session_id=session_id1,
            at_ns=40,
        )
        outcome2 = interpret_world_consequence(
            issued2, data["binding_result2"], consequence2,
            provenance=s20.p("s34-real-world2-outcome-interpretation"),
        )
        closed2 = record_interpreted_action_outcome(
            supervisor, outcome2, at_ns=40,
        )
        if supervisor.get(closed2.action_id) is not closed2:
            raise S34EvidenceFailure("Action2 supervisor did not own OUTCOME")
        session_id2 = session.started.session_id
        report["real_actions"].append(_summarize_action(consequence2, closed2))
        report["action2_retained_revision"] = data["lineage"].committed_revision
        await session.shutdown(timeout_s=10)
        if session.process_returncode != 0:
            raise S34EvidenceFailure("Action2 bridge did not close cleanly")
        report["session_count"] = 2
        session = None

        # 3: explicit separate Skill2 FAILED route comes from the existing
        # *caller-fixed* S21 goal-violation criterion. Although Action2 is
        # physical, the goal failure is not independently sensed from World.
        report["stage"] = "ACTION3_REAL_RECOVERY_AND_POST_ACTION_WORLD"
        data, failed_skill, inputs = _real_recovery_prep(
            data, closed2, outcome2,
        )
        proposed3, binding3, _handoff = s23._propose(inputs)
        _authorized3, issued3 = s23._issue(data, proposed3)
        session = await _new_session()
        if session.started.session_id in {session_id1, session_id2}:
            raise S34EvidenceFailure("Action3 session UUID not distinct")
        command3 = build_mineflayer_command(issued3, binding3)
        consequence3 = await execute_mineflayer_command(
            session, command3, timeout_s=9,
            provenance=s23.p("s34-real-world3-consequence"),
        )
        if consequence3.status is not WorldConsequenceStatus.EXECUTED:
            raise S34EvidenceFailure("Action3 not physically EXECUTED")
        outcome3 = interpret_world_consequence(
            issued3, binding3, consequence3,
            provenance=s23.p("s34-real-world3-outcome-interpretation"),
        )
        closed3 = record_interpreted_action_outcome(
            supervisor, outcome3, at_ns=60,
        )
        if (
            closed3.state is not ActionState.OUTCOME
            or supervisor.get(closed3.action_id) is not closed3
        ):
            raise S34EvidenceFailure("Action3 not supervised OUTCOME")
        report["real_actions"].append(_summarize_action(consequence3, closed3))
        report["session_count"] = 3
        report["stage"] = "FRESH_REAL_ZOMBIE_POST_ACTION3"
        _command(server, "gamerule doMobSpawning false")
        _command(server, "time set midnight")
        _command(
            server, "execute at RelaySelf run summon minecraft:zombie ~2 ~ ~ "
            "{NoAI:1b,Silent:1b,PersistenceRequired:1b}",
        )
        assert server.stdin is not None
        await server.stdin.drain()
        observed = None
        target = None
        for attempt in range(5):
            await asyncio.sleep(2)
            candidate = await _correlated_observe(
                session, f"s34-after-action3:{attempt:03d}",
            )
            target = _verified_target(candidate)
            if target is not None:
                observed = candidate
                break
        if observed is None or target is None:
            raise S34EvidenceFailure("actual new zombie not observed")
        if (
            observed.session_id != consequence3.session_id
            or consequence3.after_observation is None
            or observed.seq <= consequence3.after_observation.seq
        ):
            raise S34EvidenceFailure("fresh post-Action3 session lineage failed")
        report["target"] = target
        receipt = project_source_native_threat(
            supervisor, closed3, consequence3, observed,
            target_entity_id=target["entity_id"],
            target_name="zombie",
            observed_at_ns=65, inspected_at_ns=67, max_age_ns=5,
        )
        report["s27"] = {
            "evidence_id": receipt.evidence.evidence_id,
            "distance_cm": receipt.evidence.threat_clearance_cm,
            "parent_action": receipt.evidence.action_id,
            "parent_after_seq": receipt.parent_after_seq,
            "fresh_seq": observed.seq,
            "session_id": observed.session_id,
        }
        trace = run_explicit_postfailure_epoch(
            supervisor, closed3, consequence3,
            inputs["recovery_skill"], intent, commit.new_state,
            receipt.evidence, at_ns=70,
            provenance=s23.p("s34-explicit-third-epoch"),
        )
        report["s24"] = {
            "selected_candidate": trace.selected_candidate,
            "admission_status": trace.admission_status.value,
            "retained_revision": trace.retained_revision,
            "wait_score": trace.wait_score,
            "move_score": trace.move_score,
        }
        if (
            trace.selected_candidate != "WAIT"
            or trace.admission_status.value != "admitted"
            or trace.retained_revision != 1
            or len({a["session_id"] for a in report["real_actions"]}) != 3
            or supervisor.open_actions != ()
            or failed_skill.state.value != "failed"
            or inputs["recovery_skill"].state.value != "started"
            or skill1.state.value != "started"
        ):
            raise S34EvidenceFailure("3-action retained/Skill/World qualification failed")
        await session.shutdown(timeout_s=10)
        if session.process_returncode != 0:
            raise S34EvidenceFailure("Action3 bridge did not close cleanly")
        session = None
        report["stage"] = "SUCCESS"
        report["status"] = "PASS"
        report["classification"] = (
            "THREE_REAL_ACTIONS_REAL_ACTION1_LEARNING_WITH_FIXED_THREAT_INPUTS_QUALIFIED"
        )
        exit_code = 0
    except (S31ABlocked, OSError) as exc:
        report["status"] = "BLOCKED"
        report["error"] = str(exc)
        exit_code = 2
        print(f"S34 BLOCKED at {report['stage']}: {exc}", file=sys.stderr)
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 1
        print(f"S34 FAIL at {report['stage']}: {exc}", file=sys.stderr)
    finally:
        if session is not None:
            try:
                await session.shutdown(timeout_s=10)
            except Exception as exc:
                report["bridge_shutdown_error"] = str(exc)
                await session.terminate()
        try:
            await _shutdown_server(server, collector)
        except Exception as exc:
            report["server_shutdown_error"] = str(exc)
            exit_code = 1
        if server is not None:
            report["server_exit_code"] = server.returncode
        if tmp is not None:
            tmp.cleanup()
        if report["status"] == "PASS" and report.get("server_exit_code") != 0:
            report["status"] = "FAIL"
            report["classification"] = "TEARDOWN_FAILED_NOT_QUALIFIED"
            report["stage"] = "TEARDOWN"
            report["error"] = "server did not exit with zero"
            exit_code = 1
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("S34_REPORT=" + json.dumps(report, sort_keys=True))
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    args = parser.parse_args()
    return asyncio.run(qualify(args.report, args.server_log))


if __name__ == "__main__":
    raise SystemExit(main())
