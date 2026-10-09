"""S33 genuine consecutive Action1/2/3, real Action1 governed feedback/retained update.

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
from pathlib import Path
from typing import Any

import test_postmain_two_epoch_continuation as s19
import test_postmain_second_action_closure as s20
import test_postmain_skill_terminal_closure as s21
import test_postmain_skill_exit_routing as s22
import test_postmain_local_recovery_action as s23
from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import (
    WorldConsequenceStatus,
    build_mineflayer_command,
    execute_mineflayer_command,
)
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
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


class S33EvidenceFailure(RuntimeError):
    """Refuse unqualified real source, Action/Skill owner or learning lineage."""


async def _real_epoch_one(supervisor, adapter):
    p = s19.PropositionKey("entity", "zombie-1", "nearby")
    evidence = s19.BeliefEvidence(
        "E1",
        p,
        s19.EvidenceRelation.SUPPORT,
        s19.provenance("evidence"),
    )
    attention = s19.select_attention(
        (
            s19.AttentionCandidate(
                "E1",
                "belief-evidence:E1",
                s19.provenance("attention"),
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
            s19.provenance=s19.provenance("belief-to-concept"),
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
        s19.provenance=s19.provenance("concept-to-prediction"),
    )
    wait_prediction = s19.predict_transition(
        base,
        s19.TransitionRule(
            rule_id="wait",
            preconditions=(s19.StateVariable("concept", "spatial:nearby_threat"),),
            assignments=(s19.StateVariable("comparison_score", 8),),
            s19.provenance=s19.provenance("wait"),
        ),
    )
    move_prediction = s19.predict_transition(
        base,
        s19.TransitionRule(
            rule_id="move-away",
            preconditions=(s19.StateVariable("concept", "spatial:nearby_threat"),),
            assignments=(s19.StateVariable("comparison_score", 3),),
            s19.provenance=s19.provenance("move"),
        ),
    )
    plan = s19.select_plan(
        (
            s19.plan_candidate_from_prediction(
                wait_prediction,
                candidate_id="WAIT",
                feature_keys=("comparison_score",),
                s19.provenance=s19.provenance("wait-plan"),
            ),
            s19.plan_candidate_from_prediction(
                move_prediction,
                candidate_id="MOVE_AWAY",
                feature_keys=("comparison_score",),
                s19.provenance=s19.provenance("move-plan"),
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
                s19.provenance=s19.provenance("habit"),
            ),
        ),
        s19.provenance=s19.provenance("repertoire"),
    )
    habit = s19.select_habit(
        repertoire,
        s19.HabitCue(
            cue_id="nearby-threat",
            features=(
                s19.CueFeature("concept", "spatial:nearby_threat"),
            ),
            s19.provenance=s19.provenance("cue"),
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
        s19.provenance=s19.provenance("route"),
    )
    assert route.status is s19.RouteDecisionStatus.AGREED
    control = s19.control_candidate_from_route_decision(route)
    assert control is not None

    intent = s19.IntentCommitment()
    intent.commit(
        "escape-threat",
        objective="escape the nearby threat",
        at_ns=1,
        s19.provenance=s19.provenance("intent"),
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
        s19.provenance=s19.provenance("admission"),
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
        s19.provenance=s19.provenance("binding"),
    )
    bound = s19.resolve_execution_binding(
        admission,
        control,
        route,
        intent,
        admission_criterion,
        binding,
        s19.provenance=s19.provenance("resolve-binding"),
    )
    skill, proposed, binding_result = s19.start_and_propose_bound_execution(
        bound,
        intent,
        at_ns=10,
        s19.provenance=s19.provenance("start-propose"),
    )
    assert skill.state is s19.SkillState.STARTED
    assert proposed.state is s19.ActionState.PROPOSED

    authorized = proposed.authorize(
        at_ns=11,
        s19.provenance=s19.provenance("authorize"),
        authority="s18-explicit-authority",
    )
    issued = supervisor.issue(
        authorized,
        at_ns=12,
        deadline_ns=100,
        s19.provenance=s19.provenance("issue"),
    )
    assert issued.state is s19.ActionState.ISSUED

    command = build_mineflayer_command(issued, binding_result)
    consequence = await execute_mineflayer_command(
        adapter, command, timeout_s=9,
        provenance=s19.provenance("s33-real-world1"),
    )
    if consequence.status is not WorldConsequenceStatus.EXECUTED:
        raise S33EvidenceFailure("real Action1 consequence not EXECUTED")
    outcome_interpretation = s19.interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        s19.provenance=s19.provenance("outcome-interpretation"),
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
        s19.provenance=s19.provenance("feedback-criterion"),
    )
    feedback_interpretation = s19.interpret_action_outcome_as_learning_feedback(
        closed,
        outcome_interpretation,
        feedback_criterion,
        s19.provenance=s19.provenance("feedback"),
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
            s19.provenance=s19.provenance("learning-authority"),
        ),
        s19.provenance=s19.provenance("learning-commit"),
    )

    assert committed.previous_state.value == 3
    assert committed.previous_state.revision == 0
    assert committed.new_state.value == 4
    assert committed.new_state.revision == 1

    return committed, intent, closed, feedback_interpretation, consequence, issued, skill



def _prepare_second_real(supervisor, commit, intent, closed1, feedback):
    assert closed1 is supervisor.get(closed1.action_id)
    assert closed1.state is ActionState.OUTCOME
    assert commit.new_state.revision == 1

    values, second_epoch = s20.s19._epoch_two(
        supervisor, intent, commit.new_state, commit.new_state,
        expected_revision=1,
    )
    assert second_epoch.cognition_requested is False
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
    assert skill2.state is SkillState.STARTED
    assert proposed2.state is ActionState.PROPOSED
    return {
        "supervisor": supervisor, "commit": commit, "intent": intent,
        "closed1": closed1, "feedback": feedback, "values": values,
        "second_epoch": second_epoch, "lineage": lineage, "binding": binding,
        "bound": bound, "skill2": skill2, "proposed2": proposed2,
        "binding_result2": binding_result2,
    }




def _real_skill2_evidence(data, closed2, outcome, status=s21.SkillGoalStatus.VIOLATED):
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
        provenance=s20.p("independent-goal-evaluation"),
    )
    authority = s21.SkillTerminalAuthority(
        authority_id="s21-skill-closure-authority",
        skill_execution_id=skill.execution_id,
        criterion_id=criterion.criterion_id,
        granted=True,
        provenance=s20.p("explicit-skill-closure-authority"),
    )
    return data, closed2, outcome, criterion, evidence, authority




def _real_skill2_exit(data, action, outcome):
    data, action, outcome, criterion21, evidence21, authority21 = _real_skill2_evidence(
        data, action, outcome, s21.SkillGoalStatus.VIOLATED,
    )
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




def _real_recovery_prep(data, closed2, outcome2):
    data, failed, exit_criterion, evidence, route_authority = _real_skill2_exit(
        data, closed2, outcome2,
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


