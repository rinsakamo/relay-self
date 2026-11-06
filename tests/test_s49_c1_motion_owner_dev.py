"""Original S49 owner/ActionSupervisor + C1/S10 next-Intent offline integration.

These are explicitly synthetic Mineflayer-shaped observations and outcomes;
no World process, physical issuer, LLM, or real training is executed here.
"""
from dataclasses import replace

import pytest

from adapters.mineflayer.bug0_intent_motion_learning import IntentMotionRejected
from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.s49_c1_motion_owner_dev import S49C1MotionDevJoin
from relay_self.action import ActionLifecycle
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution
from test_bug0_intent_motion_source_join import _s49_two_probe_shape
from test_s49_completed_decision_bridge import _synthetic_original_shape


def _joined_original_owner():
    _, _, (r,), (selected,), state = _s49_two_probe_shape()
    steps, _, _ = _synthetic_original_shape()
    step = steps[0]
    assert step.choice.probe_seq == selected.seq
    assert step.choice.provenance == selected.provenance
    p = Provenance("test", "synthetic-original-s49-supervisor")
    intent = IntentCommitment()
    intent.commit("escape-threat", objective="attempt physical escape", at_ns=1, provenance=p)
    executor = NormalSessionActionExecutor(selected.session_id, intent)
    owner = S49C1MotionDevJoin(
        intent, executor, state, self_id="self-a",
    )

    # The original S49 supervision contract is exercised with typed synthetic
    # steps, not a second Action issuer or an actual S15/Minecraft process.
    skill = SkillExecution.start(
        "dev-synthetic-skill", skill_id="escape-movement",
        intent_commitment=intent, at_ns=2, provenance=p,
    )
    proposed = ActionLifecycle.propose(
        step.action_request_id, skill_execution=skill,
        intent_commitment=intent, at_ns=3, provenance=p,
    )
    authorized = proposed.authorize(
        at_ns=4, provenance=p, authority="synthetic-supervisor-authority",
    )
    return owner, executor, intent, step, selected, r, authorized, p


def _record_synthetic_original_terminal(owner, executor, step, selected, receipt, authorized, p):
    forecast = owner.prepare_original_action(step, selected)
    issued = executor.supervisor.issue(
        authorized, at_ns=5, deadline_ns=50, provenance=p,
    )
    assert issued.action_id == step.action_request_id
    executor._dispatched.add(issued.action_id)
    terminal = executor.supervisor.record_outcome(
        issued.action_id, at_ns=6, provenance=p,
    )
    receipt = replace(receipt, terminal=terminal)
    owner.accept_original_terminal(step, selected, receipt)
    return forecast, receipt


def test_original_supervisor_terminal_one_experience_then_same_intent_owner_next_forecast():
    owner, executor, intent, step, selected, r, auth, p = _joined_original_owner()
    first, receipt = _record_synthetic_original_terminal(
        owner, executor, step, selected, r, auth, p,
    )
    assert first.owner_revision == 0
    assert first.predicted_total_m == 0.7
    assert owner.action_count == 1
    assert intent.current_intent.intent_id == "escape-threat"

    terminal = owner.close_original_intent()
    assert terminal.experience.forecast is first
    assert len(terminal.experience.action_receipts) == 1
    assert terminal.experience.decision_probes[0] is selected
    assert terminal.experience.measured_total_m == pytest.approx(0.31)
    assert terminal.experience.intent_goal_verified is False
    assert intent.current_intent is None
    assert terminal.learning.previous_state.value == 7
    assert terminal.learning.new_state.value == 6
    assert owner.retained_motion is terminal.learning.new_state
    assert owner.retained_motion.revision == 1
    assert len([e for e in intent.events if e.kind.value == "committed"]) == 1

    after = receipt.consequence.after_observation
    next_native = replace(
        after, seq=after.seq + 2, request_id="actual-next-decision-source-shape",
    )
    next_forecast = owner.start_next_original_intent(
        next_native, next_intent_id="next-escape-threat",
    )
    assert intent.current_intent.intent_id == "next-escape-threat"
    assert next_forecast.owner_revision == 1
    assert next_forecast.predicted_total_m == 0.6
    assert next_forecast.source_provenance == next_native.provenance
    assert len([e for e in intent.events if e.kind.value == "committed"]) == 2
    assert owner.next_forecast is next_forecast

    # Once an attempted experience is terminal, neither replay nor a copied
    # closed Action nor a second next-Intent source may update it again.
    with pytest.raises(IntentMotionRejected):
        owner.close_original_intent()
    with pytest.raises(IntentMotionRejected):
        owner.prepare_original_action(step, selected)
    with pytest.raises(IntentMotionRejected):
        owner.start_next_original_intent(
            replace(next_native, seq=next_native.seq + 2),
            next_intent_id="other-next",
        )
    assert owner.retained_motion.revision == 1


@pytest.mark.parametrize("case", [
    "no_original_supervisor", "terminal_copy", "wrong_receipt_source",
    "wrong_step_object", "wrong_probe_object", "reused_action",
])
def test_original_owner_cannot_accept_forged_or_replayed_action(case):
    owner, executor, _, step, selected, receipt, auth, p = _joined_original_owner()
    owner.prepare_original_action(step, selected)
    if case == "no_original_supervisor":
        with pytest.raises(IntentMotionRejected):
            owner.accept_original_terminal(step, selected, receipt)
        return
    issued = executor.supervisor.issue(
        auth, at_ns=5, deadline_ns=50, provenance=p,
    )
    executor._dispatched.add(issued.action_id)
    terminal = executor.supervisor.record_outcome(
        issued.action_id, at_ns=6, provenance=p,
    )
    receipt = replace(receipt, terminal=terminal)
    if case == "terminal_copy":
        receipt = replace(receipt, terminal=replace(terminal))
    elif case == "wrong_receipt_source":
        receipt = replace(receipt, source=Provenance("test", "foreign-source"))
    elif case == "wrong_step_object":
        step = replace(step)
    elif case == "wrong_probe_object":
        selected = replace(selected)
    elif case == "reused_action":
        # The same source/action cannot be replayed as a second closure.
        owner.accept_original_terminal(step, selected, receipt)
        with pytest.raises(IntentMotionRejected):
            owner.accept_original_terminal(step, selected, receipt)
        return
    with pytest.raises(IntentMotionRejected):
        owner.accept_original_terminal(step, selected, receipt)


@pytest.mark.parametrize("case", [
    "stale_next", "foreign_next", "uncorrelated_next", "same_intent",
])
def test_original_next_intent_source_and_history_fails_closed(case):
    owner, executor, intent, step, selected, receipt, auth, p = _joined_original_owner()
    _, receipt = _record_synthetic_original_terminal(
        owner, executor, step, selected, receipt, auth, p,
    )
    owner.close_original_intent()
    after = receipt.consequence.after_observation
    fresh = replace(
        after, seq=after.seq + 2, request_id="fresh-original-next",
    )
    next_id = "next-escape-threat"
    if case == "stale_next":
        fresh = replace(fresh, seq=after.seq)
    elif case == "foreign_next":
        fresh = replace(fresh, session_id="other-session")
    elif case == "uncorrelated_next":
        fresh = replace(fresh, request_id=None)
    elif case == "same_intent":
        next_id = "escape-threat"
    with pytest.raises(IntentMotionRejected):
        owner.start_next_original_intent(fresh, next_intent_id=next_id)
    assert intent.current_intent is None
    assert owner.retained_motion.revision == 1



def test_unified_c1_runner_missing_exclusive_gate_blocks_before_world(
    monkeypatch, tmp_path,
):
    """No grant or opt-in: cannot even provision a disposable World."""
    import asyncio
    import json

    from adapters.mineflayer.s49_normal_session_real_ci import qualify

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.delenv("S49_UNIFIED_C1_DEV_ONLY", raising=False)
    report_path = tmp_path / "blocked.json"
    rc = asyncio.run(qualify(
        report_path, tmp_path / "absent-server.log", unified_c1_dev=True,
    ))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert rc == 2
    assert report["status"] == "BLOCKED"
    assert report["stage"] == "START"
    assert "exclusive" in report["error"]
    assert report["actual_native_actions"] == []
    assert report["real_model_calls"] == 0
    assert report["learning_in_world"] is False
