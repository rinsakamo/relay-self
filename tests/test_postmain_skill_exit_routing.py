"""S22 deterministic routing after S21 second Skill terminal closure."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_skill_terminal_closure as s21
from relay_self.intent import IntentEventKind, ReconsiderationDecision
from relay_self.skill import SkillState
from relay_self.skill_exit_routing import (
    IntentImpact,
    InvalidSkillExitAuthority,
    InvalidSkillExitEvidence,
    LocalPathStatus,
    SkillExitAuthority,
    SkillExitCriterion,
    SkillExitEvidence,
    SkillExitRoute,
    assess_skill_exit,
    request_explicit_reconsideration,
    start_explicit_local_recovery,
)

ROOT = Path(__file__).resolve().parents[1]


def _prepared(
    *,
    terminal=SkillState.FAILED,
    local=LocalPathStatus.AVAILABLE,
    impact=IntentImpact.NOT_CHALLENGED,
):
    data, action, outcome, criterion21, evidence21, authority21 = s21._prepared(
        s21.SkillGoalStatus.VIOLATED if terminal is SkillState.FAILED
        else s21.SkillGoalStatus.SATISFIED
    )
    if terminal is SkillState.CANCELLED:
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
    criterion = SkillExitCriterion(
        criterion_id="s22-skill-exit",
        skill_id=closed.skill_id,
        intent_id=closed.intent_id,
        provenance=s21.s20.p("s22-bounded-criterion"),
    )
    evidence = SkillExitEvidence(
        criterion_id=criterion.criterion_id,
        skill_execution_id=closed.execution_id,
        intent_id=closed.intent_id,
        terminal_state=closed.state,
        terminal_at_ns=closed.events[-1].at_ns,
        terminal_provenance=closed.events[-1].provenance,
        local_path=local,
        alternative_skill_id="alternate-escape-path" if local is LocalPathStatus.AVAILABLE else None,
        intent_impact=impact,
        observed_at_ns=43,
        provenance=s21.s20.p("caller-local-feasibility-and-intent-impact"),
    )
    route = (
        SkillExitRoute.LOCAL_RECOVERY_CANDIDATE
        if local is LocalPathStatus.AVAILABLE
        else SkillExitRoute.RECONSIDERATION_CANDIDATE
    )
    authority = SkillExitAuthority(
        authority_id="s22-caller-handoff",
        criterion_id=criterion.criterion_id,
        intent_id=criterion.intent_id,
        route=route,
        granted=True,
        provenance=s21.s20.p("explicit-handoff-authorization"),
    )
    return data, closed, criterion, evidence, authority


def _assess(data, skill, criterion, evidence):
    return assess_skill_exit(skill, data["intent"], criterion, evidence)


def test_failed_skill_local_recovery_preserves_intent_without_automatic_action():
    data, closed, criterion, evidence, authority = _prepared()
    events_before = data["intent"].events
    evaluated = _assess(data, closed, criterion, evidence)
    assert evaluated.route is SkillExitRoute.LOCAL_RECOVERY_CANDIDATE
    assert data["intent"].events == events_before  # selection is not commitment
    assert data["intent"].pending_reconsideration is None
    assert closed.state is SkillState.FAILED
    next_skill = start_explicit_local_recovery(
        evaluated, authority, execution_id="skill-exec-escape-recovery-3",
        at_ns=45, provenance=s21.s20.p("explicit-caller-local-start"),
    )
    assert next_skill.execution_id != closed.execution_id
    assert next_skill.skill_id == "alternate-escape-path"
    assert next_skill.state is SkillState.STARTED
    assert next_skill.intent_id == closed.intent_id
    assert data["intent"].events == events_before
    assert data["supervisor"].get(data["closed1"].action_id) is data["closed1"]
    assert data["supervisor"].get(s21.s20.ACTION2).state is s21.s20.ActionState.OUTCOME
    assert data["supervisor"].open_actions == ()
    assert data["commit"].new_state.revision == 1
    assert closed.is_terminal  # closed Skill stays terminal


def test_exhausted_local_path_and_material_intent_challenge_request_only():
    data, closed, criterion, evidence, authority = _prepared(
        local=LocalPathStatus.EXHAUSTED,
        impact=IntentImpact.MATERIALLY_CHALLENGED,
    )
    assessed = _assess(data, closed, criterion, evidence)
    assert assessed.route is SkillExitRoute.RECONSIDERATION_CANDIDATE
    previous = data["intent"].events
    assert data["intent"].pending_reconsideration is None
    event = request_explicit_reconsideration(
        assessed, authority, at_ns=45,
        provenance=s21.s20.p("explicit-admitted-reconsideration-request"),
    )
    assert event.kind is IntentEventKind.RECONSIDERATION_REQUESTED
    assert data["intent"].pending_reconsideration is event
    assert len(data["intent"].events) == len(previous) + 1
    assert data["intent"].current_intent.intent_id == closed.intent_id
    assert data["supervisor"].open_actions == ()
    assert data["commit"].new_state.revision == 1
    assert all(e.kind not in (IntentEventKind.COMPLETED, IntentEventKind.FAILED) for e in data["intent"].events)
    current = data["intent"].reconsider(
        closed.intent_id, decision=ReconsiderationDecision.CONTINUE,
        reason="separate caller chooses to continue", at_ns=46,
        provenance=s21.s20.p("separate-continue-judgment"),
    )
    assert current is not None and current.intent_id == closed.intent_id
    assert data["intent"].pending_reconsideration is None


def test_explicit_reconsideration_release_is_separate_from_request():
    data, closed, criterion, evidence, authority = _prepared(
        local=LocalPathStatus.EXHAUSTED,
        impact=IntentImpact.MATERIALLY_CHALLENGED,
    )
    assessment = _assess(data, closed, criterion, evidence)
    request_explicit_reconsideration(
        assessment, authority, at_ns=45,
        provenance=s21.s20.p("caller-reconsider"),
    )
    assert data["intent"].current_intent is not None
    assert data["intent"].reconsider(
        closed.intent_id, decision=ReconsiderationDecision.RELEASE,
        reason="independent decision", at_ns=46,
        provenance=s21.s20.p("caller-release"),
    ) is None
    assert data["intent"].current_intent is None


@pytest.mark.parametrize(
    "local,impact,expected",
    [
        (LocalPathStatus.AVAILABLE, IntentImpact.MATERIALLY_CHALLENGED,
         SkillExitRoute.HOLD_FOR_EVIDENCE),
        (LocalPathStatus.EXHAUSTED, IntentImpact.NOT_CHALLENGED,
         SkillExitRoute.HOLD_FOR_EVIDENCE),
        (LocalPathStatus.EXHAUSTED, IntentImpact.UNDETERMINED,
         SkillExitRoute.HOLD_FOR_EVIDENCE),
        (LocalPathStatus.UNDETERMINED, IntentImpact.MATERIALLY_CHALLENGED,
         SkillExitRoute.HOLD_FOR_EVIDENCE),
        (LocalPathStatus.UNDETERMINED, IntentImpact.UNDETERMINED,
         SkillExitRoute.HOLD_FOR_EVIDENCE),
        (LocalPathStatus.AVAILABLE, IntentImpact.NOT_CHALLENGED,
         SkillExitRoute.LOCAL_RECOVERY_CANDIDATE),
    ],
)
def test_failed_skill_does_not_automatically_replace_intent(local, impact, expected):
    data, closed, criterion, evidence, _authority = _prepared(
        local=local, impact=impact,
    )
    previous = data["intent"].events
    assessment = _assess(data, closed, criterion, evidence)
    assert assessment.route is expected
    assert data["intent"].events == previous
    assert data["intent"].pending_reconsideration is None


@pytest.mark.parametrize("terminal", [SkillState.SUCCEEDED, SkillState.CANCELLED])
def test_success_or_cancellation_never_implies_intent_terminal(terminal):
    data, closed, criterion, evidence, _authority = _prepared(
        terminal=terminal, local=LocalPathStatus.UNDETERMINED,
        impact=IntentImpact.UNDETERMINED,
    )
    assessed = _assess(data, closed, criterion, evidence)
    assert assessed.route is (
        SkillExitRoute.CONTINUE_INTENT_ONLY if terminal is SkillState.SUCCEEDED
        else SkillExitRoute.HOLD_FOR_EVIDENCE
    )
    assert data["intent"].current_intent.intent_id == closed.intent_id
    assert data["intent"].pending_reconsideration is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("criterion_id", "other-criterion"),
        ("skill_execution_id", "other-execution"),
        ("intent_id", "other-intent"),
        ("terminal_state", SkillState.SUCCEEDED),
        ("terminal_at_ns", 1),
        ("terminal_provenance", s21.s20.p("unrelated-terminal")),
        ("observed_at_ns", 41),
    ],
)
def test_invalid_exit_lineage_is_fail_closed(field, value):
    data, closed, criterion, evidence, _authority = _prepared()
    with pytest.raises(InvalidSkillExitEvidence):
        _assess(data, closed, criterion, replace(evidence, **{field: value}))
    assert data["intent"].pending_reconsideration is None


def test_missing_and_wrong_authority_refuse_local_start_and_intent_request():
    for local, impact, invoke in (
        (LocalPathStatus.AVAILABLE, IntentImpact.NOT_CHALLENGED, "start"),
        (LocalPathStatus.EXHAUSTED, IntentImpact.MATERIALLY_CHALLENGED, "request"),
    ):
        data, closed, criterion, evidence, authority = _prepared(local=local, impact=impact)
        assessment = _assess(data, closed, criterion, evidence)
        events = data["intent"].events
        wrong = (
            None,
            replace(authority, granted=False),
            replace(authority, criterion_id="wrong"),
            replace(authority, intent_id="wrong"),
            replace(
                authority,
                route=(
                    SkillExitRoute.RECONSIDERATION_CANDIDATE
                    if invoke == "start" else SkillExitRoute.LOCAL_RECOVERY_CANDIDATE
                ),
            ),
        )
        for item in wrong:
            with pytest.raises(InvalidSkillExitAuthority):
                if invoke == "start":
                    start_explicit_local_recovery(
                        assessment, item, execution_id="recovery-exec-3",
                        at_ns=45, provenance=s21.s20.p("denied-recovery"),
                    )
                else:
                    request_explicit_reconsideration(
                        assessment, item, at_ns=45,
                        provenance=s21.s20.p("denied-reconsideration"),
                    )
            assert data["intent"].events == events
            assert data["intent"].pending_reconsideration is None
            assert closed.is_current_snapshot


def test_forged_route_and_wrong_handoff_are_rejected():
    data, closed, criterion, evidence, authority = _prepared()
    assessment = _assess(data, closed, criterion, evidence)
    with pytest.raises(InvalidSkillExitEvidence):
        request_explicit_reconsideration(
            assessment, authority, at_ns=45,
            provenance=s21.s20.p("wrong-request"),
        )
    with pytest.raises(InvalidSkillExitEvidence):
        start_explicit_local_recovery(
            replace(assessment, route=SkillExitRoute.RECONSIDERATION_CANDIDATE),
            authority, execution_id="recovery-exec-3", at_ns=45,
            provenance=s21.s20.p("forged-assessment"),
        )
    assert data["intent"].pending_reconsideration is None


def test_intent_drift_rejects_both_handoffs():
    for local, impact in (
        (LocalPathStatus.AVAILABLE, IntentImpact.NOT_CHALLENGED),
        (LocalPathStatus.EXHAUSTED, IntentImpact.MATERIALLY_CHALLENGED),
    ):
        data, closed, criterion, evidence, authority = _prepared(local=local, impact=impact)
        assessment = _assess(data, closed, criterion, evidence)
        data["intent"].request_reconsideration(
            closed.intent_id, reason="independent owner change", at_ns=44,
            provenance=s21.s20.p("owner-changed"),
        )
        with pytest.raises(InvalidSkillExitEvidence):
            if local is LocalPathStatus.AVAILABLE:
                start_explicit_local_recovery(
                    assessment, authority, execution_id="recovery-exec-3",
                    at_ns=45, provenance=s21.s20.p("stale-recovery"),
                )
            else:
                request_explicit_reconsideration(
                    assessment, authority, at_ns=45,
                    provenance=s21.s20.p("stale-request"),
                )
        assert len(data["intent"].events) == len(assessment.intent_events) + 1


def test_reconsideration_replay_rejected_after_first_request():
    data, closed, criterion, evidence, authority = _prepared(
        local=LocalPathStatus.EXHAUSTED,
        impact=IntentImpact.MATERIALLY_CHALLENGED,
    )
    assessed = _assess(data, closed, criterion, evidence)
    request_explicit_reconsideration(
        assessed, authority, at_ns=45, provenance=s21.s20.p("once"),
    )
    events = data["intent"].events
    with pytest.raises(InvalidSkillExitEvidence):
        request_explicit_reconsideration(
            assessed, authority, at_ns=46, provenance=s21.s20.p("replayed"),
        )
    assert data["intent"].events == events


def test_missing_material_proof_cannot_request_reconsideration():
    data, closed, criterion, evidence, authority = _prepared(
        local=LocalPathStatus.EXHAUSTED,
        impact=IntentImpact.UNDETERMINED,
    )
    assessed = _assess(data, closed, criterion, evidence)
    assert assessed.route is SkillExitRoute.HOLD_FOR_EVIDENCE
    with pytest.raises(InvalidSkillExitEvidence):
        request_explicit_reconsideration(
            assessed, authority, at_ns=45,
            provenance=s21.s20.p("insufficient"),
        )
    assert data["intent"].pending_reconsideration is None


def test_early_handoff_time_fails_without_effect():
    data, closed, criterion, evidence, authority = _prepared()
    assessment = _assess(data, closed, criterion, evidence)
    with pytest.raises(InvalidSkillExitEvidence):
        start_explicit_local_recovery(
            assessment, authority, execution_id="recovery-exec-3",
            at_ns=42, provenance=s21.s20.p("too-early"),
        )
    assert data["intent"].pending_reconsideration is None


def test_s22_receipt_scope():
    receipt = json.loads(
        (ROOT / "docs/postmain-s22-receipt.json").read_text(encoding="utf-8"),
    )
    assert receipt["base_head"] == "04816df243e53af0349b14e478bf96d5ff52277a"
    assert receipt["classification"] == "EXPLICIT_SKILL_EXIT_LOCAL_RECOVERY_OR_RECONSIDERATION_QUALIFIED"
    assert receipt["automatic_reentry"] is False
    assert receipt["model_calls"] == 0
    assert receipt["field_minecraft"] == "NOT_RUN"
    assert receipt["intent_replacement_automatic"] is False
