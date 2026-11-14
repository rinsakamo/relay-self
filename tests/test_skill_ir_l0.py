"""#843 bounded Skill IR: CPU-only proposals/observations, never native issue."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.physical_action_port import PhysicalCapability, PhysicalReadback
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution, SkillState
from relay_self.skill_ir_l0 import (
    ActionStep,
    CheckStep,
    CompiledSkillIR,
    EndStep,
    L0SkillInterpreter,
    PredicateWitness,
    SkillIR,
    SkillIRRefusal,
    compile_skill_ir,
    parse_skill_ir_json,
)


def _base():
    scope = ScopeRef("self-test", "world-test")
    prov = Provenance("l2-candidate", "task-1:generation-1")
    ir = SkillIR(
        skill_id="EAT", version=1, origin_task_ref="task-1", generation=1,
        scope=scope, goal_id="HUNGER_RELIEF", target_kind="FOOD",
        target_ref="inventory:bread", provenance=prov,
        entry="check", steps=(
            CheckStep("check", "food_low", "eat", "no_food_needed", "unknown"),
            ActionStep("eat", "EAT", 1, "done"),
            EndStep("done", "SUCCESS_CANDIDATE"),
            EndStep("no_food_needed", "FAILURE_CANDIDATE"),
            EndStep("unknown", "UNRESOLVED"),
        ), max_actions=1, max_duration_ns=100,
    )
    caps = (PhysicalCapability("EAT", 1, "hand", "FOOD", True),)
    return ir, caps, frozenset({"food_low"})


def _owners():
    owner = IntentCommitment()
    prov = Provenance("self-test", "commit")
    owner.commit("intent-1", objective="HUNGER_RELIEF", at_ns=1, provenance=prov)
    skill = SkillExecution.start(
        "skill-execution-1", skill_id="EAT",
        intent_commitment=owner, at_ns=2, provenance=prov,
    )
    return owner, skill, ActionSupervisor(), prov


def _runner(ir=None, caps=None, predicates=None):
    base_ir, base_caps, base_preds = _base()
    program = compile_skill_ir(
        ir or base_ir, capabilities=caps or base_caps,
        predicate_refs=predicates or base_preds,
    )
    owner, skill, supervisor, prov = _owners()
    runner = L0SkillInterpreter(
        program, intent_owner=owner, skill_execution=skill,
        supervisor=supervisor, scope=program.ir.scope,
        admitted_version=program.ir.version,
        admitted_generation=program.ir.generation, started_ns=4,
    )
    return runner, owner, skill, supervisor, prov


def _witness(seq=10, *, scope=None, truth="TRUE", predicate="food_low",
             target="inventory:bread"):
    return PredicateWitness(
        scope or ScopeRef("self-test", "world-test"),
        target, predicate, truth, seq, f"probe-{seq}",
        Provenance("mineflayer", f"world-test:{seq}"),
    )


def _readback(seq=11):
    scope = ScopeRef("self-test", "world-test")
    return PhysicalReadback(
        scope, Provenance("mineflayer", f"world-test:{seq}"),
        seq, f"probe-{seq}", ("inventory:bread",), True,
    )


def _to_action(runner, *, now=5):
    assert runner.tick(now_ns=now).status == "NEED_OBSERVATION"
    assert runner.tick(now_ns=now + 1, witness=_witness()).status == "ADVANCED"
    decision = runner.tick(now_ns=now + 2)
    assert decision.status == "PROPOSE_ACTION"
    assert decision.capability_ref == "EAT"
    return decision


def _issue_and_outcome(runner, supervisor, prov, *, issue_ns=9, outcome_ns=10):
    receipt = runner.propose_pending(
        readback=_readback(), at_ns=issue_ns - 2, provenance=prov,
    )
    authorized = receipt.proposal.authorize(
        at_ns=issue_ns - 1, provenance=prov, authority="synthetic-dev-only",
    )
    supervisor.issue(authorized, at_ns=issue_ns, deadline_ns=100, provenance=prov)
    supervisor.record_outcome(
        receipt.proposal.action_id, at_ns=outcome_ns, provenance=prov,
    )
    return receipt


def test_compile_and_l0_propose_through_existing_actionport_no_native_issue():
    runner, owner, skill, supervisor, prov = _runner()
    instruction = _to_action(runner)
    assert instruction.action_id == "skill-execution-1-l0-1"
    receipt = runner.propose_pending(readback=_readback(), at_ns=7, provenance=prov)
    assert receipt.proposal.state is ActionState.PROPOSED
    assert receipt.binding.capability_ref == "EAT"
    assert receipt.binding.target_ref == "inventory:bread"
    assert receipt.physical_authorized is False
    assert receipt.physical_issued is False
    assert receipt.preissue_persisted is False
    assert supervisor.recorded_actions == ()
    assert skill.state is SkillState.STARTED
    assert owner.current_intent.intent_id == "intent-1"
    assert runner.tick(now_ns=8).status == "AWAIT_ACTION"
    with pytest.raises(SkillIRRefusal, match="unproposed"):
        runner.propose_pending(readback=_readback(), at_ns=8, provenance=prov)


def test_only_actual_supervisor_outcome_advances_and_never_ends_intent():
    runner, owner, skill, supervisor, prov = _runner()
    _to_action(runner)
    receipt = runner.propose_pending(readback=_readback(), at_ns=7, provenance=prov)
    assert runner.tick(now_ns=8).status == "AWAIT_ACTION"
    authorized = receipt.proposal.authorize(
        at_ns=8, provenance=prov, authority="fake",
    )
    supervisor.issue(authorized, at_ns=9, deadline_ns=50, provenance=prov)
    assert runner.tick(now_ns=9).status == "AWAIT_ACTION"
    supervisor.record_outcome(receipt.proposal.action_id, at_ns=10, provenance=prov)
    assert runner.tick(now_ns=10).status == "ADVANCED"
    terminal = runner.tick(now_ns=11)
    assert terminal.status == "TERMINAL_CANDIDATE"
    assert terminal.reason == "SUCCESS_CANDIDATE"
    assert skill.state is SkillState.STARTED
    assert owner.current_intent is not None
    assert runner.tick(now_ns=12).status == "STOP"


@pytest.mark.parametrize("state", ["UNKNOWN", "TIMEOUT"])
def test_ambiguous_native_action_stops_without_retry(state):
    runner, _, _, supervisor, prov = _runner()
    _to_action(runner)
    receipt = runner.propose_pending(readback=_readback(), at_ns=7, provenance=prov)
    supervisor.issue(
        receipt.proposal.authorize(at_ns=8, provenance=prov, authority="test"),
        at_ns=9, deadline_ns=10, provenance=prov,
    )
    if state == "UNKNOWN":
        supervisor.mark_unknown(receipt.proposal.action_id, at_ns=10, provenance=prov)
    else:
        supervisor.advance(at_ns=10, provenance=prov)
    refused = runner.tick(now_ns=10)
    assert refused.status == "STOP"
    assert refused.reason == "ACTION_NOT_OUTCOME"
    assert runner.pending_action_id == receipt.proposal.action_id
    assert runner.tick(now_ns=11).status == "STOP"


def test_true_false_unknown_check_branches_are_explicit():
    for truth, expected in (
        ("FALSE", "FAILURE_CANDIDATE"), ("UNKNOWN", "UNRESOLVED"),
    ):
        runner, *_ = _runner()
        assert runner.tick(now_ns=5, witness=_witness(truth=truth)).status == "ADVANCED"
        terminal = runner.tick(now_ns=6)
        assert terminal.status == "TERMINAL_CANDIDATE"
        assert terminal.reason == expected


@pytest.mark.parametrize("changed", [
    {"scope": ScopeRef("other-self", "world-test")},
    {"scope": ScopeRef("self-test", "foreign-world")},
    {"target_ref": "inventory:apple"},
    {"predicate_ref": "unknown_predicate"},
    {"seq": -1},
    {"source": Provenance("mineflayer", "world-test:999")},
    {"truth": "MAYBE"},
])
def test_unqualified_predicate_witness_fails_closed(changed):
    runner, *_ = _runner()
    witness = replace(_witness(), **changed)
    bad = runner.tick(now_ns=5, witness=witness)
    assert bad.status == "STOP"
    assert bad.reason == "UNQUALIFIED_OBSERVATION"


def test_replayed_sequence_in_later_check_is_rejected():
    ir, caps, preds = _base()
    ir = replace(ir, steps=(
        CheckStep("check", "food_low", "check2", "end", "end"),
        CheckStep("check2", "food_low", "end", "end", "end"),
        EndStep("end", "UNRESOLVED"),
    ))
    runner, *_ = _runner(ir, caps, preds)
    assert runner.tick(now_ns=5, witness=_witness(seq=10)).status == "ADVANCED"
    assert runner.tick(now_ns=6, witness=_witness(seq=10)).status == "STOP"


@pytest.mark.parametrize("mutate", [
    lambda ir: replace(ir, entry="missing"),
    lambda ir: replace(ir, max_actions=0),
    lambda ir: replace(ir, max_duration_ns=0),
    lambda ir: replace(ir, max_duration_ns=60_000_000_001),
    lambda ir: replace(ir, steps=ir.steps + (ir.steps[0],)),
    lambda ir: replace(ir, steps=ir.steps + (EndStep("hidden", "UNRESOLVED"),)),
    lambda ir: replace(ir, steps=(
        CheckStep("check", "food_low", "check", "check", "check"),
    )),
    lambda ir: replace(ir, steps=(ActionStep("check", "shell_exec", 1, "done"),
                                  EndStep("done", "SUCCESS_CANDIDATE"))),
    lambda ir: replace(ir, steps=(ActionStep("check", "EAT", 999, "done"),
                                  EndStep("done", "SUCCESS_CANDIDATE"))),
    lambda ir: replace(ir, steps=(EndStep("check", "EXECUTE_NATIVE"),)),
    lambda ir: replace(ir, steps=("print('shell')",)),
])
def test_static_rejects_unbounded_forged_or_unsupported_ir(mutate):
    ir, caps, preds = _base()
    with pytest.raises(SkillIRRefusal):
        compile_skill_ir(mutate(ir), capabilities=caps, predicate_refs=preds)


def test_missing_predicate_and_unavailable_capability_rejected():
    ir, caps, preds = _base()
    with pytest.raises(SkillIRRefusal):
        compile_skill_ir(ir, capabilities=caps, predicate_refs=frozenset())
    with pytest.raises(SkillIRRefusal):
        compile_skill_ir(
            ir, capabilities=(replace(caps[0], available=False),),
            predicate_refs=preds,
        )


def test_generation_version_and_scope_must_be_admitted():
    ir, caps, preds = _base()
    compiled = compile_skill_ir(ir, capabilities=caps, predicate_refs=preds)
    owner, skill, supervisor, _ = _owners()
    for version, generation, scope in (
        (2, 1, ir.scope), (1, 2, ir.scope),
        (1, 1, ScopeRef("foreign", "world-test")),
    ):
        with pytest.raises(SkillIRRefusal):
            L0SkillInterpreter(
                compiled, intent_owner=owner, skill_execution=skill,
                supervisor=supervisor, scope=scope,
                admitted_version=version, admitted_generation=generation,
                started_ns=4,
            )


def test_deadline_and_intent_reconsideration_refuse_future_actions():
    runner, owner, _, supervisor, prov = _runner()
    assert runner.tick(now_ns=105).status == "STOP"
    assert supervisor.recorded_actions == ()
    another, owner, _, supervisor, prov = _runner()
    owner.request_reconsideration(
        "intent-1", reason="hazard", at_ns=3, provenance=prov,
    )
    assert another.tick(now_ns=5).status == "STOP"
    assert supervisor.recorded_actions == ()


def test_skill_termination_invalidates_cursor_without_completing_intent():
    runner, owner, skill, supervisor, prov = _runner()
    skill.succeed(reason="external owner", at_ns=3, provenance=prov)
    assert runner.tick(now_ns=5).status == "STOP"
    assert owner.current_intent is not None
    assert supervisor.recorded_actions == ()


def test_no_repeat_if_proposal_was_lost_and_explicit_interrupt_is_local():
    runner, owner, skill, supervisor, prov = _runner()
    proposed = _to_action(runner)
    for tick in range(8, 12):
        awaiting = runner.tick(now_ns=tick)
        assert awaiting.status == "AWAIT_ACTION"
        assert awaiting.action_id == proposed.action_id
    assert runner.interrupt("emergency fast cue").status == "STOP"
    assert runner.tick(now_ns=13).status == "STOP"
    assert owner.current_intent is not None
    assert skill.state is SkillState.STARTED
    assert supervisor.recorded_actions == ()


def test_physical_readback_cannot_change_selected_target_or_be_stale():
    runner, _, _, supervisor, prov = _runner()
    _to_action(runner)
    bad = replace(_readback(seq=9), observed_target_refs=("inventory:apple",))
    with pytest.raises(SkillIRRefusal, match="stale"):
        runner.propose_pending(readback=bad, at_ns=7, provenance=prov)
    other = replace(_readback(), observed_target_refs=("inventory:apple",))
    with pytest.raises(ValueError, match="native source/Target"):
        runner.propose_pending(readback=other, at_ns=7, provenance=prov)
    assert supervisor.recorded_actions == ()


def test_two_sequential_action_steps_use_unique_ids_and_supervised_outcomes():
    ir, caps, preds = _base()
    ir = replace(ir, entry="one", max_actions=2, steps=(
        ActionStep("one", "EAT", 1, "two"),
        ActionStep("two", "EAT", 1, "end"),
        EndStep("end", "SUCCESS_CANDIDATE"),
    ))
    runner, owner, skill, supervisor, prov = _runner(ir, caps, preds)
    assert runner.tick(now_ns=5).status == "PROPOSE_ACTION"
    first = _issue_and_outcome(runner, supervisor, prov)
    assert runner.tick(now_ns=6).status == "ADVANCED"
    second_choice = runner.tick(now_ns=7)
    assert second_choice.status == "PROPOSE_ACTION"
    assert second_choice.action_id != first.proposal.action_id
    second = runner.propose_pending(
        readback=_readback(seq=12), at_ns=11, provenance=prov,
    )
    supervisor.issue(
        second.proposal.authorize(at_ns=12, provenance=prov, authority="test"),
        at_ns=13, deadline_ns=100, provenance=prov,
    )
    supervisor.record_outcome(second.proposal.action_id, at_ns=14, provenance=prov)
    assert runner.tick(now_ns=8).status == "ADVANCED"
    assert runner.tick(now_ns=9).status == "TERMINAL_CANDIDATE"
    assert len(supervisor.recorded_actions) == 2


def _json_ir() -> dict[str, object]:
    return {
        "skill_id": "EAT", "version": 1, "goal_id": "HUNGER_RELIEF",
        "target_kind": "FOOD", "target_ref": "inventory:bread",
        "entry": "start", "max_actions": 1, "max_duration_ns": 100,
        "steps": [
            {"kind": "ACTION", "step_id": "start", "capability_ref": "EAT",
             "capability_version": 1, "after_outcome": "end"},
            {"kind": "END", "step_id": "end", "result": "SUCCESS_CANDIDATE"},
        ],
    }


def test_json_parser_keeps_world_task_and_generation_outside_model_text():
    base_ir, caps, preds = _base()
    ir = parse_skill_ir_json(
        json.dumps(_json_ir()), scope=base_ir.scope,
        provenance=base_ir.provenance, origin_task_ref="task-external",
        generation=42,
    )
    assert ir.scope == base_ir.scope
    assert ir.origin_task_ref == "task-external"
    assert ir.generation == 42
    assert compile_skill_ir(ir, capabilities=caps, predicate_refs=preds).ir is ir


@pytest.mark.parametrize("bad_json", [
    '{"skill_id":"A","skill_id":"B"}',
    '{"steps":[{"kind":"END","kind":"ACTION"}]}',
    '{"x":NaN}',
    '{"x":Infinity}',
    '{"bad":true}',
    '[]',
    'not json',
])
def test_reject_malformed_or_duplicate_json(bad_json):
    ir, _, _ = _base()
    with pytest.raises(SkillIRRefusal):
        parse_skill_ir_json(
            bad_json, scope=ir.scope, provenance=ir.provenance,
            origin_task_ref="task", generation=1,
        )


@pytest.mark.parametrize("change", [
    {"scope": {"self_id": "foreign", "world_session_id": "bad"}},
    {"steps": [{"kind": "ACTION", "step_id": "start",
                "capability_ref": "arbitrary_shell", "capability_version": 1,
                "after_outcome": "end", "python": "os.system('x')"}]},
    {"steps": [{"kind": "EVAL", "code": "while True: ..."}]},
])
def test_json_model_cannot_supply_scope_python_code_or_new_step_kind(change):
    ir, _, _ = _base()
    payload = _json_ir() | change
    with pytest.raises(SkillIRRefusal):
        parse_skill_ir_json(
            json.dumps(payload), scope=ir.scope,
            provenance=ir.provenance, origin_task_ref="task", generation=1,
        )


def test_forged_compiled_ir_cannot_bypass_static_validation():
    ir, caps, preds = _base()
    unbounded = replace(
        ir, steps=(CheckStep("check", "food_low", "check", "check", "check"),),
    )
    program = CompiledSkillIR(unbounded, caps, preds)
    owner, skill, supervisor, _ = _owners()
    with pytest.raises(SkillIRRefusal, match="cyclic"):
        L0SkillInterpreter(
            program, intent_owner=owner, skill_execution=skill,
            supervisor=supervisor, scope=ir.scope,
            admitted_version=1, admitted_generation=1, started_ns=4,
        )
