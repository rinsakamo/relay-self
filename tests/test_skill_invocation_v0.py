"""Goal-independent initial ability + future L2 Skill arguments (CPU-only)."""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import MineflayerPosition as Position
from relay_self.cognitive_minimal_dev import Option, Selection
from relay_self.common_io import ScopeRef
from relay_self.initial_skill_ir import (
    FiniteSkillInterpreter,
    PhysicalSkillIR,
    SkillIRRefusal,
    SkillOrigin,
    compile_invoked_skill,
    initial_skill_definitions,
)
from relay_self.intent import IntentCommitment
from relay_self.physical_action_port import PhysicalCapability
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution
from relay_self.skill_invocation import (
    CORE_PARAMETERS,
    ArgumentKind,
    LearnedSkillProgram,
    SkillArgument,
    SkillBudget,
    SkillCallTemplate,
    SkillConstraints,
    SkillDefinition,
    SkillInvocation,
    SkillInvocationRefusal,
    SkillParameter,
    SkillTarget,
    bind_skill_invocation,
)
from relay_self.target_contract import (
    ArrivalCondition,
    ReferenceFrame,
    TargetContract,
    TargetKind,
)

SCOPE = ScopeRef("self-A", "world-A")
SOURCE = Provenance("selected-l1", "source-13")
PARAM_SOURCE = Provenance("l2-skill-candidate", "draft-only")


def declarations():
    return {x.skill_id: x for x in initial_skill_definitions()}


def call(
    skill_id="MOVE", *, goal="EXPLORE_WORLD", kind="DESTINATION",
    ref="destination:waypoint-1@abc", contract=None,
    constraints=None, budget=None, extras=(),
):
    d = declarations()[skill_id]
    t = SkillTarget(ref, kind, contract)
    invocation = SkillInvocation(
        SCOPE, d.skill_id, d.version, d.definition_ref, goal,
        t, constraints or SkillConstraints(),
        budget or SkillBudget(1, 3000, 4.0), SOURCE,
        extras,
    )
    return d, bind_skill_invocation(d, invocation)


def option_selection(invocation):
    opt = Option(
        invocation.goal_id, invocation.skill_id,
        invocation.skill_version, invocation.target.ref,
        invocation.target.kind, "learnable-goal-schema", "goal-matched-skill",
        invocation.target.contract,
    )
    return Selection("READY", opt, "selected and revalidated", invocation.scope)


def invoke_ir(definition, invocation):
    selection = option_selection(invocation)
    capability = PhysicalCapability(
        definition.capability_ref, definition.capability_version,
        "movement" if definition.skill_id == "MOVE" else "hand",
        invocation.target.kind, True,
    )
    return compile_invoked_skill(
        selection, definition=definition, target=invocation.target,
        constraints=invocation.constraints, budget=invocation.budget,
        arguments=invocation.arguments,
        provenance=invocation.provenance, capability=capability,
    )


def live_enemy_contract():
    return TargetContract(
        SCOPE, "ATTACK_FROM_REACH", "entity:zombie-31@rev-1",
        TargetKind.ENTITY_RANGE, ReferenceFrame.ENTITY_LIVE,
        Provenance("mineflayer", "observed-13"),
        ArrivalCondition(
            1.0, 2.5, .5, max_facing_error_rad=.2,
            require_line_of_sight=True,
        ),
        13, entity_id="zombie-31", max_entity_age_seq=2,
    )


def test_initial_abilities_have_typed_general_abi_but_rest_is_unmapped():
    definitions = declarations()
    assert tuple(definitions) == ("MOVE", "EAT", "ATTACK", "REST")
    assert all(d.parameters[:3] == CORE_PARAMETERS for d in definitions.values())
    assert all(d.origin == "INNATE" for d in definitions.values())
    assert all(not hasattr(d, "goal_id") for d in definitions.values())
    assert all(not hasattr(d, "target_kind") for d in definitions.values())
    assert definitions["MOVE"].capability_ref == "MOVE"
    assert definitions["REST"].capability_ref is None
    with pytest.raises(SkillIRRefusal, match="do not match"):
        d, invocation = call("REST", goal="RECOVER", kind="SELF", ref="self:current")
        compile_invoked_skill(
            option_selection(invocation), definition=d,
            target=invocation.target, constraints=invocation.constraints,
            budget=invocation.budget, provenance=SOURCE,
            capability=PhysicalCapability("clear_controls", 1, "movement", "SELF", True),
        )


@pytest.mark.parametrize("goal,kind,ref", [
    ("EXPLORE_WORLD", "DESTINATION", "destination:waypoint-1@abc"),
    ("STEP_FORWARD", "RELATIVE_STEP", "relative:one-step"),
    ("COLLECT_ITEM", "PICKUP_ZONE", "item:rotten_flesh:zone"),
])
def test_one_innate_move_definition_supports_distinct_goals_and_target_kinds(
    goal, kind, ref,
):
    definition, invocation = call(goal=goal, kind=kind, ref=ref)
    ir = invoke_ir(definition, invocation)
    assert ir.skill_id == "MOVE" and ir.version == 1
    assert ir.goal_id == goal and ir.target_kind == kind
    assert ir.invocation == invocation
    assert ir.invocation.invocation_ref.startswith("skill-invocation:v1@")
    assert ir.origin is SkillOrigin.INNATE
    assert len(ir.steps) == 2
    # Neither the IR nor Invocation is native motor authority.
    assert not hasattr(invocation, "physical_authorized")
    assert not hasattr(ir, "physical_issued")


def test_target_contract_is_part_of_skill_call_not_ability_definition():
    c = live_enemy_contract()
    definition, invocation = call(
        goal="ATTACK_FROM_REACH", kind="ENTITY_RANGE", ref=c.target_ref,
        contract=c,
    )
    ir = invoke_ir(definition, invocation)
    assert ir.invocation.target.contract.contract_ref == c.contract_ref
    other = replace(c, condition=replace(c.condition, max_horizontal_m=2.0))
    another = replace(invocation, target=SkillTarget(c.target_ref, "ENTITY_RANGE", other))
    assert another.invocation_ref != invocation.invocation_ref
    assert definition.definition_ref == declarations()["MOVE"].definition_ref
    with pytest.raises(SkillInvocationRefusal, match="wrong Self/World/Goal"):
        replace(invocation, goal_id="EXPLORE_WORLD")


def test_invocation_revision_binds_goal_target_budget_constraints_and_extras():
    d, x = call()
    assert bind_skill_invocation(d, x) is x
    variants = (
        replace(x, goal_id="FLEE"),
        replace(x, target=SkillTarget("destination:another", "DESTINATION")),
        replace(x, budget=SkillBudget(2, 3000, 4.0)),
        replace(x, constraints=SkillConstraints((
            SkillArgument("avoid_danger", ArgumentKind.FLAG, True),
        ))),
    )
    assert all(changed.invocation_ref != x.invocation_ref for changed in variants)
    assert all(changed.definition_ref == x.definition_ref for changed in variants)
    assert x.invocation_ref == call()[1].invocation_ref
    # The same goal/target binds to exactly one representation of a number.
    assert replace(
        x, constraints=SkillConstraints((
            SkillArgument("speed_limit", ArgumentKind.NUMBER, 1),
        )),
    ).invocation_ref == replace(
        x, constraints=SkillConstraints((
            SkillArgument("speed_limit", ArgumentKind.NUMBER, 1.0),
        )),
    ).invocation_ref


def test_physical_skill_ir_keeps_exact_invocation_at_interpreter_begin():
    d, x = call()
    ir = invoke_ir(d, x)
    selection = option_selection(x)
    owner = IntentCommitment()
    owner.commit("intent-A", objective=x.goal_id, at_ns=2, provenance=SOURCE)
    skill = SkillExecution.start(
        "skill-run-A", skill_id="MOVE",
        intent_commitment=owner, at_ns=3, provenance=SOURCE,
    )
    interpreter = FiniteSkillInterpreter()
    cur = interpreter.begin(
        selection, ir=ir, intent_owner=owner,
        skill_execution=skill, registered_versions=frozenset({("MOVE", 1)}),
        deadline_ns=100,
    )
    assert cur.invocation_ref == x.invocation_ref
    assert cur.pending_action_id is None
    assert owner.current_intent is not None
    assert interpreter._ir is ir
    # Same destination ID but a different ArrivalContract cannot silently run.
    foreign = Selection(
        "READY", replace(selection.option, target_ref="destination:changed"),
        "forged", SCOPE,
    )
    with pytest.raises(SkillIRRefusal, match="selected Target"):
        FiniteSkillInterpreter().begin(
            foreign, ir=ir, intent_owner=owner, skill_execution=skill,
            registered_versions=frozenset({("MOVE", 1)}), deadline_ns=100,
        )
    with pytest.raises(SkillIRRefusal, match="registered"):
        FiniteSkillInterpreter().begin(
            selection, ir=ir, intent_owner=owner, skill_execution=skill,
            registered_versions=frozenset(), deadline_ns=100,
        )
    with pytest.raises(SkillIRRefusal, match="compiled Skill"):
        replace(ir, invocation=replace(x, goal_id="OTHER_GOAL"))


def test_registered_learned_definition_uses_same_invocation_and_ir_schema():
    learned = SkillDefinition(
        "MOVE_PRECISE", 1, "LEARNED", PARAM_SOURCE,
        capability_ref="MOVE", capability_version=1,
    )
    original = declarations()["MOVE"]
    original_invocation = call()[1]
    learned_call = replace(
        original_invocation, skill_id="MOVE_PRECISE",
        definition_ref=learned.definition_ref,
    )
    bound = bind_skill_invocation(learned, learned_call)
    assert bound.goal_id == original_invocation.goal_id
    ir = invoke_ir(learned, bound)
    assert isinstance(ir, PhysicalSkillIR)
    assert ir.origin is SkillOrigin.LEARNED
    assert ir.invocation.invocation_ref != original_invocation.invocation_ref
    assert original.definition_ref != learned.definition_ref
    # Physical execution still requires separately registered version in L0
    # and matching owner/port; this test does not open the Action channel.


def test_l2_composite_move_then_attack_can_forward_different_typed_targets():
    learned = SkillDefinition(
        "APPROACH_AND_ATTACK", 1, "LEARNED", PARAM_SOURCE,
        parameters=CORE_PARAMETERS + (
            SkillParameter("approach_target", ArgumentKind.TARGET),
        ),
    )
    program = LearnedSkillProgram(
        learned,
        (
            SkillCallTemplate("MOVE", 1, (
                ("target", "approach_target"),
                ("constraints", "constraints"), ("budget", "budget"),
            )),
            SkillCallTemplate("ATTACK", 1),
        ),
        PARAM_SOURCE,
    )
    program.validate_calls(initial_skill_definitions())
    c = live_enemy_contract()
    approach = SkillTarget(c.target_ref, "ENTITY_RANGE", c)
    invocation = SkillInvocation(
        SCOPE, learned.skill_id, 1, learned.definition_ref,
        c.goal_id, SkillTarget("entity:31", "ZOMBIE"),
        SkillConstraints(), SkillBudget(2, 5000),
        SOURCE, (SkillArgument("approach_target", ArgumentKind.TARGET, approach),),
    )
    assert bind_skill_invocation(learned, invocation) is invocation
    assert invocation.invocation_ref
    # Hypothetical program only: does not execute either native action.
    assert not hasattr(program, "execute")


@pytest.mark.parametrize("invalid", [
    lambda d: replace(d, parameters=CORE_PARAMETERS[:2]),
    lambda d: replace(d, parameters=CORE_PARAMETERS + (CORE_PARAMETERS[0],)),
    lambda d: replace(d, capability_ref="MOVE", capability_version=None),
    lambda d: replace(d, version=0),
    lambda d: replace(d, origin="AUTO_AUTHORIZED"),
    lambda d: replace(d, parameters=CORE_PARAMETERS + (
        SkillParameter("next_target", ArgumentKind.TARGET),
    ) * 10),
])
def test_bad_skill_definition_abi_refused(invalid):
    d = declarations()["MOVE"]
    with pytest.raises(SkillInvocationRefusal):
        invalid(d)


@pytest.mark.parametrize("invalid", [
    lambda x: replace(x, scope=ScopeRef("self-A", None)),
    lambda x: replace(x, definition_ref=""),
    lambda x: replace(x, arguments=(SkillArgument("target", ArgumentKind.NUMBER, 1),)),
    lambda x: replace(x, arguments=(SkillArgument("extra", ArgumentKind.NUMBER, 1),) * 2),
    lambda x: replace(x, budget=SkillBudget(0, 1)),
    lambda x: replace(x, budget=SkillBudget(65, 1000)),
    lambda x: replace(x, budget=SkillBudget(1, 0)),
    lambda x: replace(x, budget=SkillBudget(1, 1, float("nan"))),
])
def test_malformed_or_unbounded_skill_call_rejected(invalid):
    d, x = call()
    with pytest.raises(SkillInvocationRefusal):
        invalid(x)


@pytest.mark.parametrize("argument", [
    lambda: SkillArgument("x", ArgumentKind.NUMBER, float("inf")),
    lambda: SkillArgument("x", ArgumentKind.NUMBER, True),
    lambda: SkillArgument("x", ArgumentKind.FLAG, 1),
    lambda: SkillArgument("x", ArgumentKind.POSITION, "1,2,3"),
    lambda: SkillArgument("x", ArgumentKind.TARGET, "entity:31"),
    lambda: SkillArgument("x", ArgumentKind.REFERENCE, ""),
    lambda: SkillArgument("x", ArgumentKind.SYMBOL, "arbitrary python()"),
    lambda: SkillArgument("../../escape", ArgumentKind.NUMBER, 2),
])
def test_untyped_or_unbounded_generated_arguments_refused(argument):
    with pytest.raises(SkillInvocationRefusal):
        argument()


def test_invalid_extra_arg_or_definition_revision_never_binds():
    d, x = call()
    with pytest.raises(SkillInvocationRefusal, match="undeclared"):
        bind_skill_invocation(
            d, replace(x, arguments=(SkillArgument("junk", ArgumentKind.FLAG, True),)),
        )
    with pytest.raises(SkillInvocationRefusal, match="ABI"):
        bind_skill_invocation(d, replace(x, definition_ref="changed"))
    # Position decoder rejects invalid Minecraft coordinates even before
    # the generic invocation can be constructed.
    from adapters.mineflayer.python_protocol import MineflayerAdapterProtocolError

    with pytest.raises(MineflayerAdapterProtocolError):
        Position(float("inf"), 64, 0)


@pytest.mark.parametrize("steps", [
    (SkillCallTemplate("UNKNOWN", 1),),
    (SkillCallTemplate("APPROACH_AND_ATTACK", 1),),
    (SkillCallTemplate("MOVE", 1, (("target", "budget"),
                                   ("constraints", "constraints"),
                                   ("budget", "budget"))),),
    (SkillCallTemplate("MOVE", 1, (("target", "target"),
                                   ("constraints", "budget"),
                                   ("budget", "constraints"))),),
])
def test_l2_composition_rejects_unknown_recursive_or_bad_arg_mapping(steps):
    d = SkillDefinition("APPROACH_AND_ATTACK", 1, "LEARNED", PARAM_SOURCE)
    program = LearnedSkillProgram(d, steps, PARAM_SOURCE)
    with pytest.raises(SkillInvocationRefusal):
        program.validate_calls(initial_skill_definitions())


def test_missing_extra_learned_parameter_blocks_invocation():
    extra = SkillParameter("approach_target", ArgumentKind.TARGET)
    d = SkillDefinition(
        "APPROACH_AND_ATTACK", 1, "LEARNED", PARAM_SOURCE,
        parameters=CORE_PARAMETERS + (extra,),
    )
    prototype = SkillInvocation(
        SCOPE, d.skill_id, 1, d.definition_ref, "ATTACK_FROM_REACH",
        SkillTarget("entity:31", "ZOMBIE"),
        SkillConstraints(), SkillBudget(2, 5000), SOURCE,
    )
    with pytest.raises(SkillInvocationRefusal, match="missing"):
        bind_skill_invocation(d, prototype)


def test_partial_child_map_is_rejected_before_any_program_validation():
    with pytest.raises(SkillInvocationRefusal, match="finite typed"):
        SkillCallTemplate(
            "MOVE", 1,
            (("target", "target"), ("budget", "budget")),
        )


def test_learned_skill_can_call_other_registered_learned_skill_as_acyclic_dag():
    # A learned Skill composed of another learned Skill must not be forbidden
    # purely because the child wasn't innate. It is still data-only.
    approach = SkillDefinition(
        "APPROACH", 1, "LEARNED", PARAM_SOURCE,
        parameters=CORE_PARAMETERS + (
            SkillParameter("approach_target", ArgumentKind.TARGET),
        ),
    )
    combo = SkillDefinition(
        "APPROACH_AND_ATTACK", 1, "LEARNED", PARAM_SOURCE,
        parameters=CORE_PARAMETERS + (
            SkillParameter("approach_target", ArgumentKind.TARGET),
        ),
    )
    forward = (
        ("target", "target"), ("constraints", "constraints"),
        ("budget", "budget"), ("approach_target", "approach_target"),
    )
    nested = LearnedSkillProgram(
        approach, (SkillCallTemplate(
            "MOVE", 1, (
                ("target", "approach_target"), ("constraints", "constraints"),
                ("budget", "budget"),
            ),
        ),), PARAM_SOURCE,
    )
    composite = LearnedSkillProgram(
        combo, (
            SkillCallTemplate("APPROACH", 1, forward),
            SkillCallTemplate("ATTACK", 1),
        ), PARAM_SOURCE,
    )
    registry = initial_skill_definitions() + (approach, combo)
    composite.validate_calls(registry, learned_programs=(nested,))
    with pytest.raises(SkillInvocationRefusal, match="learned child program"):
        composite.validate_calls(registry)
    # Replace the child body with a back-edge to the parent:
    # expansion must reject a cycle, even with matched parameter types.
    cycle = LearnedSkillProgram(
        approach, (SkillCallTemplate("APPROACH_AND_ATTACK", 1, forward),),
        PARAM_SOURCE,
    )
    with pytest.raises(SkillInvocationRefusal, match="recursive"):
        composite.validate_calls(registry, learned_programs=(cycle,))


def test_extra_target_contract_must_match_parent_goal_and_world():
    root = SkillDefinition(
        "COMPOSITE", 1, "LEARNED", PARAM_SOURCE,
        parameters=CORE_PARAMETERS + (
            SkillParameter("secondary_target", ArgumentKind.TARGET),
        ),
    )
    foreign_goal_contract = live_enemy_contract()
    base = SkillInvocation(
        SCOPE, root.skill_id, 1, root.definition_ref,
        "EXPLORE_WORLD", SkillTarget("destination:a", "DESTINATION"),
        SkillConstraints(), SkillBudget(2, 4000), SOURCE,
    )
    with pytest.raises(SkillInvocationRefusal, match="foreign extra target"):
        replace(base, arguments=(
            SkillArgument("secondary_target", ArgumentKind.TARGET,
                          SkillTarget(foreign_goal_contract.target_ref, "ENTITY_RANGE",
                                      foreign_goal_contract)),
        ))


def test_learned_long_term_budget_is_representable_but_does_not_raise_issuer_limit():
    d, x = call()
    longer = replace(x, budget=SkillBudget(
        max_actions=32,
        max_duration_ms=600000,
        max_distance_m=4000,
        max_observations=1024,
    ))
    assert bind_skill_invocation(d, longer) is longer
    assert longer.invocation_ref != x.invocation_ref
    # An ABI request is not evidence of runtime authority.
    ir = invoke_ir(d, longer)
    assert len(ir.steps) == 2
    assert ir.invocation.budget.max_actions == 32
    assert len(ir.steps) <= 8
    assert ir.invocation.budget.max_duration_ms == 600000
    assert not hasattr(ir, "physical_authorized")
