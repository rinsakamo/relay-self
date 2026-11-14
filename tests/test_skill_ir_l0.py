"""Offline-only IR/L0 contract tests: no native issue, Gemma or Minecraft."""
from __future__ import annotations

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
    QualifiedActionOutcome,
    QualifiedPredicate,
    SkillIR,
    SkillIRRefusal,
    SkillIRStep,
    StepKind,
    compile_skill_ir,
    start_l0_skill,
    step_l0_skill,
)


def setup():
    source = Provenance("mineflayer", "world-A:10")
    scope = ScopeRef("self-A", "world-A")
    readback = PhysicalReadback(
        scope, source, 10, "probe-10", ("inventory:bread",), True,
    )
    cap = PhysicalCapability("EAT", 1, "hand", "FOOD", True)
    ir = SkillIR(
        skill_id="EAT", version=1, goal_id="HUNGER_RELIEF",
        target_kind="FOOD", entry_step_id="check",
        steps=(
            SkillIRStep(
                "check", StepKind.CHECK, predicate_ref="food_available",
                on_true="eat", on_false="fail",
            ),
            SkillIRStep(
                "eat", StepKind.ACTION, capability_ref="EAT",
                capability_version=1, body_channel="hand",
                on_outcome="done", on_denied="fail",
            ),
            SkillIRStep("done", StepKind.SUCCEED),
            SkillIRStep("fail", StepKind.FAIL),
        ),
        provenance=Provenance("l2-hypothesis", "skill-candidate-17"),
    )
    compiled = compile_skill_ir(
        ir, trusted_capabilities=(cap,),
        trusted_predicates=frozenset({"food_available"}),
    )
    owner = IntentCommitment()
    p = Provenance("test-self", "owner")
    owner.commit("intent-1", objective="HUNGER_RELIEF", at_ns=1, provenance=p)
    skill = SkillExecution.start(
        "run-1", skill_id="EAT", intent_commitment=owner,
        at_ns=2, provenance=p,
    )
    sup = ActionSupervisor()
    cursor = start_l0_skill(
        compiled, scope=scope, intent_owner=owner,
        skill_execution=skill, target_ref="inventory:bread",
    )
    return ir, compiled, owner, skill, sup, cursor, readback, p


def tick(cursor, owner, skill, sup, readback, p, **kwargs):
    return step_l0_skill(
        cursor, intent_owner=owner, skill_execution=skill, supervisor=sup,
        readback=readback, at_ns=10, provenance=p, **kwargs,
    )


def test_sequential_eat_uses_existing_actionport_only_then_waits_for_terminal():
    ir, compiled, owner, skill, sup, cursor, rb, p = setup()
    initial = tick(cursor, owner, skill, sup, rb, p)
    assert initial.status == "YIELD_OBSERVATION"
    check = tick(
        cursor, owner, skill, sup, rb, p,
        predicate=QualifiedPredicate("food_available", rb, True),
    )
    assert check.status == "ADVANCED"
    assert check.cursor.step_id == "eat"
    with pytest.raises(SkillIRRefusal, match="stale"):
        tick(cursor, owner, skill, sup, rb, p)
    proposed = tick(
        check.cursor, owner, skill, sup, rb, p, action_id="one-eat",
    )
    assert proposed.status == "ACTION_PROPOSED"
    assert proposed.proposal is not None
    assert proposed.proposal.proposal.state is ActionState.PROPOSED
    assert proposed.proposal.physical_issued is False
    assert proposed.cursor.pending_action_id == "one-eat"
    assert sup.recorded_actions == ()
    assert tick(proposed.cursor, owner, skill, sup, rb, p).status == "AWAIT_PHYSICAL_OUTCOME"
    with pytest.raises(SkillIRRefusal, match="pending"):
        tick(proposed.cursor, owner, skill, sup, rb, p, action_id="second-eat")
    issued = proposed.proposal.proposal.authorize(
        at_ns=11, provenance=p, authority="test-external-only",
    )
    sup.issue(issued, at_ns=12, deadline_ns=30, provenance=p)
    assert tick(proposed.cursor, owner, skill, sup, rb, p).status == "AWAIT_PHYSICAL_OUTCOME"
    sup.record_outcome("one-eat", at_ns=13, provenance=p)
    assert tick(proposed.cursor, owner, skill, sup, rb, p).status == "AWAIT_QUALIFIED_OUTCOME"

    # Native receipt must be from the physical owner. A typed fake is just
    # test input, not production authentication or evidence of Minecraft EAT.
    after = PhysicalReadback(
        rb.scope, Provenance("mineflayer", "world-A:14"),
        14, "probe-14", (), True,
    )
    proof = QualifiedActionOutcome(
        "one-eat", rb.scope, 14, after.source, True, True,
    )
    done = tick(
        proposed.cursor, owner, skill, sup, after, p, outcome=proof,
    )
    assert done.status == "ADVANCED"
    assert done.cursor.step_id == "done"
    result = tick(done.cursor, owner, skill, sup, after, p)
    assert result.status == "SKILL_SUCCESS_CANDIDATE"
    assert result.cursor.stopped
    assert skill.state is SkillState.STARTED
    assert owner.current_intent.intent_id == "intent-1"
    with pytest.raises(SkillIRRefusal, match="stopped"):
        tick(result.cursor, owner, skill, sup, after, p)


def test_false_check_fails_without_proposing_or_issuing():
    _, _, owner, skill, sup, cursor, rb, p = setup()
    decision = tick(
        cursor, owner, skill, sup, rb, p,
        predicate=QualifiedPredicate("food_available", rb, False),
    )
    result = tick(decision.cursor, owner, skill, sup, rb, p)
    assert result.status == "SKILL_FAILURE_CANDIDATE"
    assert sup.recorded_actions == ()
    assert result.proposal is None


@pytest.mark.parametrize("failure", [
    "foreign_session", "missing_target", "dead_body", "foreign_predicate",
])
def test_readback_and_predicate_fail_closed(failure):
    _, _, owner, skill, sup, cursor, rb, p = setup()
    changed = {
        "foreign_session": replace(rb, scope=ScopeRef("self-A", "world-B")),
        "missing_target": replace(rb, observed_target_refs=()),
        "dead_body": replace(rb, body_viable=False),
        "foreign_predicate": rb,
    }[failure]
    verdict = QualifiedPredicate(
        "wrong" if failure == "foreign_predicate" else "food_available",
        changed, True,
    )
    with pytest.raises(SkillIRRefusal):
        tick(cursor, owner, skill, sup, changed, p, predicate=verdict)


@pytest.mark.parametrize("proof_change", [
    {"action_id": "other"},
    {"scope": ScopeRef("self-A", "world-other")},
    {"native_seq": 10},
    {"durable_closed": False},
    {"consequence_attested": False},
])
def test_unqualified_physical_success_never_advances(proof_change):
    _, _, owner, skill, sup, cursor, rb, p = setup()
    check = tick(
        cursor, owner, skill, sup, rb, p,
        predicate=QualifiedPredicate("food_available", rb, True),
    )
    proposed = tick(check.cursor, owner, skill, sup, rb, p, action_id="eat-one")
    sup.issue(
        proposed.proposal.proposal.authorize(
            at_ns=11, provenance=p, authority="test-only",
        ),
        at_ns=12, deadline_ns=20, provenance=p,
    )
    sup.record_outcome("eat-one", at_ns=13, provenance=p)
    after = PhysicalReadback(
        rb.scope, Provenance("mineflayer", "world-A:14"), 14, "p14", (), True,
    )
    proof = replace(
        QualifiedActionOutcome("eat-one", rb.scope, 14, after.source, True, True),
        **proof_change,
    )
    decision = tick(
        proposed.cursor, owner, skill, sup, after, p, outcome=proof,
    )
    assert decision.status == "STOP_UNKNOWN"
    assert decision.cursor.stopped


@pytest.mark.parametrize("terminal_state", ["unknown", "timeout"])
def test_supervisor_uncertain_physical_state_never_reissues(terminal_state):
    _, _, owner, skill, sup, cursor, rb, p = setup()
    checked = tick(
        cursor, owner, skill, sup, rb, p,
        predicate=QualifiedPredicate("food_available", rb, True),
    )
    proposed = tick(checked.cursor, owner, skill, sup, rb, p, action_id="eat-one")
    sup.issue(
        proposed.proposal.proposal.authorize(
            at_ns=11, provenance=p, authority="test-only",
        ),
        at_ns=12, deadline_ns=20, provenance=p,
    )
    if terminal_state == "unknown":
        sup.mark_unknown("eat-one", at_ns=13, provenance=p)
    else:
        sup.advance(at_ns=21, provenance=p)
    result = tick(proposed.cursor, owner, skill, sup, rb, p)
    assert result.status == "STOP_UNKNOWN"
    assert result.cursor.stopped
    with pytest.raises(SkillIRRefusal):
        tick(result.cursor, owner, skill, sup, rb, p, action_id="eat-two")


def test_owner_reconsideration_or_terminal_skill_blocks_further_steps():
    _, _, owner, skill, sup, cursor, rb, p = setup()
    owner.request_reconsideration(
        "intent-1", reason="reconsider", at_ns=3, provenance=p,
    )
    with pytest.raises(SkillIRRefusal, match="Intent/Skill"):
        tick(cursor, owner, skill, sup, rb, p)
    _, _, owner, skill, sup, cursor, rb, p = setup()
    finished = skill.succeed(reason="terminal", at_ns=3, provenance=p)
    for current in (skill, finished):
        with pytest.raises(SkillIRRefusal, match="Intent/Skill"):
            tick(cursor, owner, current, sup, rb, p)


def test_unknown_predicate_yields_without_treating_unknown_as_false():
    _, _, owner, skill, sup, cursor, rb, p = setup()
    result = tick(
        cursor, owner, skill, sup, rb, p,
        predicate=QualifiedPredicate("food_available", rb, None),
    )
    assert result.status == "YIELD_OBSERVATION"
    assert result.cursor is cursor


@pytest.mark.parametrize("mutate,pattern", [
    (lambda ir: replace(ir, steps=(ir.steps[0], ir.steps[0], *ir.steps[2:])), "duplicate"),
    (lambda ir: replace(ir, steps=(
        replace(ir.steps[0], on_true="missing"), *ir.steps[1:],
    )), "target missing"),
    (lambda ir: replace(ir, steps=(
        replace(ir.steps[1], on_outcome="check"), *ir.steps[:1], *ir.steps[2:],
    )), "cycles"),
    (lambda ir: replace(ir, max_steps=1), "budget"),
    (lambda ir: replace(ir, max_actions=0), "budgets"),
    (lambda ir: replace(ir, steps=(
        replace(ir.steps[1], capability_ref="native_spawn_admin"),
        *ir.steps[:1], *ir.steps[2:],
    )), "capability"),
])
def test_compile_rejects_invalid_ir(mutate, pattern):
    ir, compiled, *_ = setup()
    with pytest.raises(SkillIRRefusal, match=pattern):
        compile_skill_ir(
            mutate(ir),
            trusted_capabilities=compiled.capabilities,
            trusted_predicates=compiled.predicates,
        )


def test_compile_refuses_unknown_predicates_and_false_or_wrong_capability():
    ir, compiled, *_ = setup()
    with pytest.raises(SkillIRRefusal, match="predicate"):
        compile_skill_ir(
            ir, trusted_capabilities=compiled.capabilities,
            trusted_predicates=frozenset(),
        )
    for cap in (
        replace(compiled.capabilities[0], available=False),
        replace(compiled.capabilities[0], body_channel="movement"),
        replace(compiled.capabilities[0], target_kind="ZOMBIE"),
    ):
        with pytest.raises(SkillIRRefusal, match="capability"):
            compile_skill_ir(
                ir, trusted_capabilities=(cap,),
                trusted_predicates=compiled.predicates,
            )


def test_action_proposal_refuses_foreign_capability_or_reselected_target():
    _, compiled, owner, skill, sup, cursor, rb, p = setup()
    checked = tick(
        cursor, owner, skill, sup, rb, p,
        predicate=QualifiedPredicate("food_available", rb, True),
    )
    with pytest.raises(SkillIRRefusal, match="Target"):
        tick(
            checked.cursor, owner, skill, sup,
            replace(rb, observed_target_refs=("inventory:apple",)), p,
            action_id="eat-one",
        )
    # Same checked cursor is usable after pre-issue refusal.
    okay = tick(checked.cursor, owner, skill, sup, rb, p, action_id="eat-one")
    assert okay.proposal.binding.target_ref == "inventory:bread"


def test_step_kind_rejects_extra_fields_and_unbounded_ir():
    with pytest.raises(SkillIRRefusal):
        SkillIRStep("bad", StepKind.SUCCEED, capability_ref="attack_entity")
    with pytest.raises(SkillIRRefusal):
        SkillIRStep("bad", StepKind.ACTION, capability_ref="EAT")
    ir, *_ = setup()
    with pytest.raises(SkillIRRefusal):
        replace(ir, max_actions=11)
    with pytest.raises(SkillIRRefusal):
        replace(ir, steps=list(ir.steps))
