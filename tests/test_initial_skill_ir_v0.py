"""Offline-only contracts for initial Skill v0; no native process or World."""
from __future__ import annotations

from dataclasses import replace

import pytest

from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.cognitive_minimal_dev import (
    Option,
    Selection,
    Target,
    WorldPercept,
    cpu_schema_epoch,
    initial_patterns,
)
from relay_self.common_io import ScopeRef
from relay_self.initial_skill_ir import (
    ActionOutcomeWitness,
    FiniteSkillInterpreter,
    SkillIRRefusal,
    SkillOrigin,
    SkillStep,
    StepKind,
    compile_initial_skill,
    initial_skill_descriptors,
)
from relay_self.intent import IntentCommitment
from relay_self.physical_action_port import (
    PhysicalActionBinding,
    PhysicalActionPortRefusal,
    PhysicalCapability,
    PhysicalReadback,
)
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution, SkillState


def fixture(kind: str = "EAT"):
    scope = ScopeRef("self-A", "world-A")
    native = Provenance("mineflayer", "world-A:12")
    owner_source = Provenance("dev-owner", "selected-L1")
    if kind == "EAT":
        option = Option("HUNGER_RELIEF", "EAT", 1, "inventory:bread",
                        "FOOD", "homeostatic", "hunger-eat")
        cap = PhysicalCapability("EAT", 1, "hand", "FOOD", True)
    else:
        option = Option("DEFEND_SELF", "ATTACK", 1, "entity:31",
                        "ZOMBIE", "defensive", "defense-attack")
        cap = PhysicalCapability("attack_entity", 1, "hand", "ZOMBIE", True)
    selected = Selection("READY", option, "selected L1", scope)
    ir = compile_initial_skill(option, capability=cap)
    owner = IntentCommitment()
    owner.commit("intent-A", objective=option.goal_id,
                 at_ns=2, provenance=owner_source)
    skill = SkillExecution.start(
        "run-A", skill_id=option.skill_id, intent_commitment=owner,
        at_ns=3, provenance=owner_source,
    )
    binding = PhysicalActionBinding(
        scope=scope, intent_id="intent-A", goal_id=option.goal_id,
        skill_id=option.skill_id, skill_version=1,
        skill_execution_id="run-A", action_id="action-A",
        capability_ref=cap.capability_ref, capability_version=cap.version,
        body_channel=cap.body_channel, target_kind=option.target_kind,
        target_ref=option.target_ref, native_seq=12, native_request_id="probe-A",
        native_source=native,
    )
    readback = PhysicalReadback(
        scope, native, 12, "probe-A", (option.target_ref,), True,
    )
    return selected, ir, owner, skill, binding, cap, readback, owner_source


def started(kind: str = "EAT"):
    selection, ir, owner, skill, binding, cap, readback, source = fixture(kind)
    interpreter = FiniteSkillInterpreter()
    cursor = interpreter.begin(
        selection, ir=ir, intent_owner=owner, skill_execution=skill,
        registered_versions=frozenset({(ir.skill_id, ir.version)}),
        deadline_ns=100,
    )
    checked = interpreter.check_target(
        cursor, readback=readback, intent_owner=owner,
        skill_execution=skill, at_ns=4,
    )
    return (interpreter, checked.cursor, selection, ir, owner, skill,
            binding, cap, readback, source)


def proposed(kind: str = "EAT"):
    x = started(kind)
    interpreter, cursor, _, _, owner, skill, binding, cap, readback, source = x
    supervisor = ActionSupervisor()
    proposal = interpreter.propose(
        cursor, binding=binding, capability=cap, readback=readback,
        intent_owner=owner, skill_execution=skill, supervisor=supervisor,
        at_ns=5, provenance=source,
    )
    return x, supervisor, proposal


def issued_outcome(proposal, source):
    return (proposal.proposal.proposal
            .authorize(at_ns=6, provenance=source, authority="offline-fake")
            .issue(at_ns=7, deadline_ns=60, provenance=source)
            .record_outcome(at_ns=8, provenance=source))


def witness(binding, *, closed=True, correlated=True):
    return ActionOutcomeWitness(
        binding.scope, binding.action_id, binding.native_source,
        closed, correlated,
    )


def test_catalog_has_four_but_only_rest_has_no_capability_mapping():
    catalog = initial_skill_descriptors()
    assert tuple(x.skill_id for x in catalog) == ("MOVE", "EAT", "ATTACK", "REST")
    assert next(x for x in catalog if x.skill_id == "ATTACK").status == (
        "NATIVE_ACK_HURT_DEV_ISSUER_EXISTS"
    )
    assert [x.status for x in catalog if x.skill_id in ("MOVE", "REST")] == [
        "NATIVE_BOUNDED_MOVE_DEV_ISSUER_EXISTS", "UNMAPPED",
    ]
    for skill_id in ("MOVE", "REST"):
        option = Option("GOAL", skill_id, 1, "target-A", "POSITION",
                        "homeostatic", "innate")
        with pytest.raises(SkillIRRefusal, match="no grounded"):
            compile_initial_skill(
                option, capability=PhysicalCapability(
                    "set_control", 1, "movement", "POSITION", True,
                ),
            )


def test_existing_schema_generates_goal_and_option_not_skill_issuer():
    scope = ScopeRef("self-A", "world-A")
    src = Provenance("mineflayer", "world-A:12")
    frame = cpu_schema_epoch(
        WorldPercept(
            scope, src, 12, 9, None,
            (Target("inventory:bread", "FOOD", src, "world-A", 12),
             Target("entity:31", "ZOMBIE", src, "world-A", 12)),
        ),
        initial_patterns(),
        allowed_skills=frozenset({("EAT", 1), ("ATTACK", 1)}),
        epoch=4,
    )
    assert {o.skill_id for o in frame.options} == {"EAT", "ATTACK"}
    assert {g.goal_id for g in frame.goals} == {"HUNGER_RELIEF", "DEFEND_SELF"}
    assert not hasattr(frame, "physical_issued")


@pytest.mark.parametrize("kind", ["EAT", "ATTACK"])
def test_ir_compiles_from_exact_selected_capability_without_issuance(kind):
    selection, ir, owner, skill, binding, cap, readback, source = fixture(kind)
    assert ir.steps == (
        SkillStep(StepKind.CHECK_TARGET),
        SkillStep(StepKind.ACTION, cap.capability_ref, cap.version),
    )
    before = owner.events
    interpreter, cursor, *_ = started(kind)
    assert cursor.index == 1
    assert cursor.pending_action_id is None
    assert owner.events == before
    assert skill.state is SkillState.STARTED
    assert ir.origin is SkillOrigin.INNATE
    assert binding.scope == selection.world_scope


@pytest.mark.parametrize("kind", ["EAT", "ATTACK"])
def test_nonissuing_port_proposal_and_evaluation_yield_not_skill_success(kind):
    x, supervisor, proposed_receipt = proposed(kind)
    interpreter, _, _, ir, owner, skill, binding, cap, readback, source = x
    assert proposed_receipt.status == "PROPOSED_NOT_ISSUED"
    assert proposed_receipt.proposal.proposal.state is ActionState.PROPOSED
    assert not proposed_receipt.proposal.physical_issued
    assert not proposed_receipt.proposal.preissue_persisted
    assert supervisor.recorded_actions == ()
    action = issued_outcome(proposed_receipt, source)
    accepted = interpreter.observe_action(
        proposed_receipt.cursor, action=action, witness=witness(binding),
        intent_owner=owner, skill_execution=skill, at_ns=9,
    )
    assert accepted.status == "YIELD_EVALUATION"
    assert accepted.cursor.index == len(ir.steps)
    assert skill.state is SkillState.STARTED
    assert owner.current_intent is not None
    assert owner.events[-1].kind.value == "committed"
    with pytest.raises(SkillIRRefusal):
        interpreter.propose(
            accepted.cursor, binding=replace(binding, action_id="next"),
            capability=cap, readback=readback,
            intent_owner=owner, skill_execution=skill,
            supervisor=supervisor, at_ns=10, provenance=source,
        )


def test_pre_issue_no_action_id_reuse_or_implicit_retarget():
    x, supervisor, proposed_receipt = proposed()
    interpreter, old_cursor, _, _, owner, skill, binding, cap, readback, source = x
    for cursor in (old_cursor, proposed_receipt.cursor):
        with pytest.raises(SkillIRRefusal):
            interpreter.propose(
                cursor, binding=binding, capability=cap,
                readback=readback, intent_owner=owner,
                skill_execution=skill, supervisor=supervisor,
                at_ns=6, provenance=source,
            )
    assert supervisor.recorded_actions == ()


@pytest.mark.parametrize("change", [
    {"action_id": "action-forged", "target_ref": "inventory:apple"},
    {"goal_id": "OTHER_GOAL"},
    {"skill_version": 2},
    {"capability_ref": "set_control"},
    {"skill_execution_id": "old-run"},
    {"scope": ScopeRef("self-B", "world-A")},
    {"scope": ScopeRef("self-A", "world-B")},
])
def test_bound_l1_target_skill_owner_and_world_fences(change):
    interpreter, cursor, _, _, owner, skill, binding, cap, readback, source = started()
    with pytest.raises(SkillIRRefusal, match="binding differs"):
        interpreter.propose(
            cursor, binding=replace(binding, **change),
            capability=cap, readback=readback, intent_owner=owner,
            skill_execution=skill, supervisor=ActionSupervisor(),
            at_ns=5, provenance=source,
        )


def test_unsupported_capability_and_missing_target_do_not_create_action():
    selected, ir, owner, skill, binding, cap, readback, source = fixture()
    with pytest.raises(SkillIRRefusal, match="WorldBody"):
        compile_initial_skill(selected.option, capability=replace(cap, available=False))
    interpreter = FiniteSkillInterpreter()
    cursor = interpreter.begin(
        selected, ir=ir, intent_owner=owner, skill_execution=skill,
        registered_versions=frozenset({("EAT", 1)}), deadline_ns=100,
    )
    with pytest.raises(SkillIRRefusal, match="UNKNOWN"):
        interpreter.check_target(
            cursor, readback=replace(readback, observed_target_refs=()),
            intent_owner=owner, skill_execution=skill, at_ns=4,
        )
    with pytest.raises(SkillIRRefusal, match="UNKNOWN"):
        interpreter.check_target(
            cursor, readback=replace(readback, scope=ScopeRef("self-A", "world-B")),
            intent_owner=owner, skill_execution=skill, at_ns=4,
        )
    assert owner.current_intent is not None


@pytest.mark.parametrize("state", ["UNKNOWN", "TIMEOUT", "DENIED", "OUTCOME_MISSING",
                                   "OUTCOME_UNCLOSED", "OUTCOME_UNCORRELATED"])
def test_ambiguous_or_denied_outcome_never_advances_or_retries(state):
    x, supervisor, proposal = proposed()
    interpreter, _, _, _, owner, skill, binding, cap, readback, source = x
    action = proposal.proposal.proposal.authorize(
        at_ns=6, provenance=source, authority="offline-fake",
    ) if state != "DENIED" else proposal.proposal.proposal.deny(
        at_ns=6, provenance=source, authority="offline-fake",
    )
    if state != "DENIED":
        action = action.issue(at_ns=7, deadline_ns=60, provenance=source)
    if state == "UNKNOWN":
        action = action.mark_unknown(at_ns=8, provenance=source)
    elif state == "TIMEOUT":
        action = action.timeout(at_ns=61, provenance=source)
    elif state.startswith("OUTCOME"):
        action = action.record_outcome(at_ns=8, provenance=source)
    proof = {
        "OUTCOME_MISSING": None,
        "OUTCOME_UNCLOSED": witness(binding, closed=False),
        "OUTCOME_UNCORRELATED": witness(binding, correlated=False),
    }.get(state)
    result = interpreter.observe_action(
        proposal.cursor, action=action, witness=proof,
        intent_owner=owner, skill_execution=skill, at_ns=62,
    )
    assert result.status == ("NOT_EXECUTED" if state == "DENIED" else "STOP_UNKNOWN")
    assert result.cursor.blocked
    with pytest.raises(SkillIRRefusal):
        interpreter.propose(
            result.cursor, binding=replace(binding, action_id="retry"),
            capability=cap, readback=readback, intent_owner=owner,
            skill_execution=skill, supervisor=supervisor, at_ns=63,
            provenance=source,
        )


def test_waiting_proposed_or_issued_does_not_advance():
    x, _, proposal = proposed()
    interpreter, _, _, _, owner, skill, _, _, _, source = x
    initial = proposal.proposal.proposal
    receipt = interpreter.observe_action(
        proposal.cursor, action=initial, witness=None,
        intent_owner=owner, skill_execution=skill, at_ns=5,
    )
    assert receipt.status == "AWAITING_OUTCOME"
    issued = initial.authorize(
        at_ns=6, provenance=source, authority="offline-fake",
    ).issue(at_ns=7, deadline_ns=60, provenance=source)
    receipt = interpreter.observe_action(
        proposal.cursor, action=issued, witness=None,
        intent_owner=owner, skill_execution=skill, at_ns=8,
    )
    assert receipt.status == "AWAITING_OUTCOME"
    assert receipt.cursor is proposal.cursor


def test_deadline_owner_release_and_restart_fail_closed():
    selection, ir, owner, skill, binding, cap, readback, source = fixture()
    first = FiniteSkillInterpreter()
    cursor = first.begin(
        selection, ir=ir, intent_owner=owner, skill_execution=skill,
        registered_versions=frozenset({("EAT", 1)}), deadline_ns=10,
    )
    with pytest.raises(SkillIRRefusal, match="deadline"):
        first.check_target(
            cursor, readback=readback, intent_owner=owner,
            skill_execution=skill, at_ns=10,
        )
    second = FiniteSkillInterpreter()
    with pytest.raises(SkillIRRefusal, match="stale, restarted"):
        second.check_target(
            cursor, readback=readback, intent_owner=owner,
            skill_execution=skill, at_ns=5,
        )
    owner.invalidate(
        "intent-A", reason="session lost", at_ns=5, provenance=source,
    )
    with pytest.raises(SkillIRRefusal, match="cancelled, released"):
        first.check_target(
            cursor, readback=readback, intent_owner=owner,
            skill_execution=skill, at_ns=6,
        )


def test_single_skill_cursor_cannot_create_second_parallel_run():
    selection, ir, owner, skill, *_ = fixture()
    interpreter = FiniteSkillInterpreter()
    interpreter.begin(
        selection, ir=ir, intent_owner=owner, skill_execution=skill,
        registered_versions=frozenset({("EAT", 1)}), deadline_ns=100,
    )
    with pytest.raises(SkillIRRefusal, match="already holds"):
        interpreter.begin(
            selection, ir=ir, intent_owner=owner, skill_execution=skill,
            registered_versions=frozenset({("EAT", 1)}), deadline_ns=100,
        )


def test_learned_ir_has_same_bounded_type_but_must_be_registered_by_owner():
    selection, ir, owner, skill, binding, cap, readback, source = fixture()
    learned = replace(
        ir, origin=SkillOrigin.LEARNED,
        provenance=Provenance("L2-proposal", "hypothetical"),
    )
    with pytest.raises(SkillIRRefusal, match="registered"):
        FiniteSkillInterpreter().begin(
            selection, ir=learned, intent_owner=owner, skill_execution=skill,
            registered_versions=frozenset(), deadline_ns=100,
        )
    cursor = FiniteSkillInterpreter().begin(
        selection, ir=learned, intent_owner=owner, skill_execution=skill,
        registered_versions=frozenset({("EAT", 1)}), deadline_ns=100,
    )
    assert cursor.skill_id == "EAT"
    for bad in (
        (), tuple(SkillStep(StepKind.CHECK_TARGET) for _ in range(9)),
        (SkillStep(StepKind.CHECK_TARGET),),
    ):
        with pytest.raises(SkillIRRefusal):
            replace(learned, steps=bad)
    with pytest.raises(SkillIRRefusal):
        SkillStep(StepKind.ACTION, "invented", 0)
    with pytest.raises(SkillIRRefusal):
        replace(learned, steps=(
            SkillStep(StepKind.ACTION, "EAT", 1),
        ) * 5)


def test_stale_skill_snapshot_rejected():
    selection, ir, owner, skill, binding, cap, readback, source = fixture()
    finished = skill.cancel(reason="interrupt", at_ns=4, provenance=source)
    assert finished.state is SkillState.CANCELLED
    with pytest.raises(SkillIRRefusal, match="Intent/Skill owner"):
        FiniteSkillInterpreter().begin(
            selection, ir=ir, intent_owner=owner, skill_execution=skill,
            registered_versions=frozenset({("EAT", 1)}), deadline_ns=100,
        )


def test_busy_physical_supervisor_blocks_l0_even_with_selected_skill():
    interpreter, cursor, _, _, owner, skill, binding, cap, readback, source = started()
    supervisor = ActionSupervisor()
    other = ActionLifecycle.propose(
        "other-physical", skill_execution=skill, intent_commitment=owner,
        at_ns=4, provenance=source,
    ).authorize(
        at_ns=5, provenance=source, authority="offline-fake",
    )
    supervisor.issue(other, at_ns=6, deadline_ns=80, provenance=source)
    with pytest.raises(PhysicalActionPortRefusal, match="issued Action"):
        interpreter.propose(
            cursor, binding=binding, capability=cap, readback=readback,
            intent_owner=owner, skill_execution=skill,
            supervisor=supervisor, at_ns=7, provenance=source,
        )
    assert cursor.index == 1
    assert cursor.pending_action_id is None


def test_learned_two_action_finite_progress_requires_new_native_source():
    selection, ir, owner, skill, binding, cap, readback, source = fixture()
    ir = replace(
        ir, origin=SkillOrigin.LEARNED,
        steps=(
            SkillStep(StepKind.CHECK_TARGET),
            SkillStep(StepKind.ACTION, "EAT", 1),
            SkillStep(StepKind.CHECK_TARGET),
            SkillStep(StepKind.ACTION, "EAT", 1),
        ),
    )
    engine = FiniteSkillInterpreter()
    cursor = engine.begin(
        selection, ir=ir, intent_owner=owner, skill_execution=skill,
        registered_versions=frozenset({("EAT", 1)}), deadline_ns=100,
    )
    cursor = engine.check_target(
        cursor, readback=readback, intent_owner=owner,
        skill_execution=skill, at_ns=4,
    ).cursor
    first = engine.propose(
        cursor, binding=binding, capability=cap, readback=readback,
        intent_owner=owner, skill_execution=skill,
        supervisor=ActionSupervisor(), at_ns=5, provenance=source,
    )
    result = engine.observe_action(
        first.cursor, action=issued_outcome(first, source),
        witness=witness(binding), intent_owner=owner,
        skill_execution=skill, at_ns=9,
    )
    assert result.status == "NEXT_STEP"
    readback2 = replace(
        readback, source=Provenance("mineflayer", "world-A:20"),
        seq=20, request_id="probe-B",
    )
    cursor = engine.check_target(
        result.cursor, readback=readback2, intent_owner=owner,
        skill_execution=skill, at_ns=10,
    ).cursor
    new_binding = replace(
        binding, action_id="action-B", native_seq=20,
        native_request_id="probe-B", native_source=readback2.source,
    )
    second = engine.propose(
        cursor, binding=new_binding, capability=cap, readback=readback2,
        intent_owner=owner, skill_execution=skill,
        supervisor=ActionSupervisor(), at_ns=11, provenance=source,
    )
    assert second.status == "PROPOSED_NOT_ISSUED"
    assert second.cursor.action_count == 2
    assert second.cursor.pending_native_source == readback2.source
    assert owner.current_intent is not None


def test_world_source_and_typed_outcome_witness_reject_forgery():
    x, _, proposal = proposed()
    engine, _, _, _, owner, skill, binding, _, _, source = x
    action = issued_outcome(proposal, source)
    with pytest.raises(SkillIRRefusal, match="malformed"):
        replace(witness(binding), journal_closed="yes")
    with pytest.raises(SkillIRRefusal, match="malformed"):
        replace(witness(binding), effect_correlated=1)
    result = engine.observe_action(
        proposal.cursor, action=action,
        witness=replace(
            witness(binding), native_source=Provenance("mineflayer", "world-A:99"),
        ),
        intent_owner=owner, skill_execution=skill, at_ns=9,
    )
    assert result.status == "STOP_UNKNOWN"
    assert result.cursor.blocked


def test_parameterized_skill_is_readable_by_l0_but_cannot_propose_unadmitted_action():
    from relay_self.initial_skill_ir import (
        compile_invoked_skill,
        initial_skill_definitions,
    )
    from relay_self.skill_invocation import (
        SkillBudget,
        SkillConstraints,
        SkillTarget,
    )

    selection, _, owner, skill, binding, cap, readback, source = fixture("EAT")
    definition = next(
        d for d in initial_skill_definitions() if d.skill_id == "EAT"
    )
    ir = compile_invoked_skill(
        selection, definition=definition,
        target=SkillTarget(selection.option.target_ref, selection.option.target_kind),
        constraints=SkillConstraints(),
        budget=SkillBudget(1, 1000),
        provenance=source, capability=cap,
    )
    interpreter = FiniteSkillInterpreter()
    cursor = interpreter.begin(
        selection, ir=ir, intent_owner=owner,
        skill_execution=skill, registered_versions=frozenset({("EAT", 1)}),
        deadline_ns=100,
    )
    assert cursor.invocation_ref == ir.invocation.invocation_ref
    checked = interpreter.check_target(
        cursor, readback=readback, intent_owner=owner,
        skill_execution=skill, at_ns=4,
    )
    assert checked.status == "CHECK_PASSED_NOT_AUTHORIZED"
    supervisor = ActionSupervisor()
    with pytest.raises(SkillIRRefusal, match="parameterized physical issuer"):
        interpreter.propose(
            checked.cursor, binding=binding, capability=cap,
            readback=readback, intent_owner=owner,
            skill_execution=skill, supervisor=supervisor,
            at_ns=5, provenance=source,
        )
    assert supervisor.recorded_actions == ()
    assert supervisor.open_actions == ()
    assert interpreter._current is checked.cursor
    assert owner.current_intent is not None
