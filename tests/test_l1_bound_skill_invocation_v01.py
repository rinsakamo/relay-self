"""L1 selects a complete immutable Invocation, never computes parameters.

Synthetic CPU-only DEV fixtures. Neither an ActionPort nor a native issuer runs.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from relay_self.cognitive_minimal_dev import (
    MinimalCognitionError,
    Option,
    Target,
    WorldPercept,
    assemble_l1_select,
    cpu_schema_epoch,
    initial_patterns,
    resolve_l1_choice,
)
from relay_self.common_io import ScopeRef
from relay_self.initial_skill_ir import (
    FiniteSkillInterpreter,
    SkillIRRefusal,
    compile_invoked_skill,
    initial_skill_definitions,
)
from relay_self.intent import IntentCommitment
from relay_self.physical_action_port import PhysicalCapability
from relay_self.provenance import Provenance
from relay_self.relay_engine import ProviderDecision, RelayEngine
from relay_self.skill import SkillExecution
from relay_self.skill_invocation import (
    ArgumentKind,
    SkillArgument,
    SkillBudget,
    SkillConstraints,
    SkillCostEstimate,
    SkillInvocationRefusal,
    SkillParameterPreset,
)

SCOPE = ScopeRef("self-A", "world-A")
SOURCE = Provenance("mineflayer", "seq-13")
SKILLS = frozenset({("EAT", 1), ("ATTACK", 1)})


def registry_and_preset():
    registry = initial_patterns()
    definitions = {(d.skill_id, d.version): d for d in initial_skill_definitions()}
    d = definitions[("EAT", 1)]
    preset = SkillParameterPreset(
        "hunger-eat", "DefaultEat", 1, d.definition_ref,
        SkillConstraints((
            SkillArgument("requires_food", ArgumentKind.FLAG, True),
        )),
        SkillBudget(1, 1800, max_observations=4),
        Provenance("innate-parameter-preset", "eat-v1"),
        expected_cost=SkillCostEstimate(1, 800),
    )
    return registry, definitions, preset


def make_percept(*, target_ref="inventory:bread", source=SOURCE):
    return WorldPercept(
        SCOPE, source, 13, hunger=10, fatigue_high=False,
        targets=(Target(target_ref, "FOOD", source, "world-A", 13),),
    )


def frame_with(registry, definitions, presets, *, target_ref="inventory:bread",
               source=SOURCE):
    return cpu_schema_epoch(
        make_percept(target_ref=target_ref, source=source),
        registry, allowed_skills=SKILLS, epoch=3,
        skill_definitions=definitions, parameter_presets=presets,
    )


def selected(frame):
    owner = IntentCommitment()
    round_ = assemble_l1_select(frame, intent_owner=owner)
    assert [choice for _, choice in round_.numbered if not isinstance(choice, str)]
    choice_id = next(n for n, item in round_.numbered
                     if isinstance(item, Option) and item.skill_id == "EAT")
    result = RelayEngine(
        lambda req, *, mode: ProviderDecision.resolved(choice_id),
    )(round_.request)
    return round_, result, owner


def test_l1_gets_completed_invocation_and_returns_only_option_id():
    registry, definitions, preset = registry_and_preset()
    frame = frame_with(registry, definitions, {"hunger-eat": preset})
    assert len(frame.options) == 1
    option = frame.options[0]
    inv = option.invocation
    assert inv is not None
    assert inv.parameter_preset_ref == preset.preset_ref
    assert inv.definition_ref == definitions[("EAT", 1)].definition_ref
    assert inv.target.ref == "inventory:bread"
    assert inv.constraints == preset.constraints
    assert inv.budget == preset.budget
    assert inv.expected_cost == preset.expected_cost
    round_, result, owner = selected(frame)
    assert any(preset.preset_ref in c.description
               for c in round_.request.choices)
    selection = resolve_l1_choice(
        round_, result, current_frame=frame,
        intent_owner=owner, available_skills=SKILLS,
    )
    assert selection.status == "READY"
    assert selection.option is option
    assert selection.option.invocation is inv


def test_missing_or_unaccepted_preset_retains_need_but_not_executable_l1_option():
    registry, definitions, preset = registry_and_preset()
    frame = frame_with(registry, definitions, {})
    assert len(frame.goals) == 1
    assert frame.goals[0].unresolved
    assert frame.options == ()
    round_ = assemble_l1_select(frame, intent_owner=IntentCommitment())
    assert [x for _, x in round_.numbered] == ["ESCALATE_L2", "DEFER"]
    # A future L2-generated, unaccepted preset must NOT appear merely
    # because it was proposed. Only the explicit accepted map admits it.
    assert preset.preset_ref not in str(round_.request)


@pytest.mark.parametrize("change", [
    lambda p: replace(p, budget=SkillBudget(2, 1800)),
    lambda p: replace(p, constraints=SkillConstraints()),
    lambda p: replace(p, expected_cost=SkillCostEstimate(1, 900)),
    lambda p: replace(p, version=2),
])
def test_preset_revision_after_l1_selection_invalidates_old_option(change):
    registry, definitions, preset = registry_and_preset()
    frame = frame_with(registry, definitions, {"hunger-eat": preset})
    round_, result, owner = selected(frame)
    newer = frame_with(registry, definitions, {"hunger-eat": change(preset)})
    assert newer.options[0].invocation != frame.options[0].invocation
    selection = resolve_l1_choice(
        round_, result, current_frame=newer,
        intent_owner=owner, available_skills=SKILLS,
    )
    assert selection.status == "REJECTED"
    assert owner.current_intent is None


def test_target_or_world_source_change_after_selection_refuses_old_call():
    registry, definitions, preset = registry_and_preset()
    frame = frame_with(registry, definitions, {"hunger-eat": preset})
    round_, result, owner = selected(frame)
    for newer in (
        frame_with(registry, definitions, {"hunger-eat": preset},
                   target_ref="inventory:apple"),
        frame_with(registry, definitions, {"hunger-eat": preset},
                   source=Provenance("mineflayer", "seq-14")),
    ):
        assert resolve_l1_choice(
            round_, result, current_frame=newer, intent_owner=owner,
            available_skills=SKILLS,
        ).status == "REJECTED"


def test_foreign_definition_or_pattern_preset_refuses_before_l1():
    registry, definitions, preset = registry_and_preset()
    with pytest.raises(MinimalCognitionError, match="foreign parameter preset"):
        frame_with(registry, definitions, {
            "hunger-eat": replace(preset, pattern_id="defense-attack"),
        })
    with pytest.raises(MinimalCognitionError, match="invalid registered"):
        frame_with(registry, definitions, {
            "hunger-eat": replace(preset, definition_ref="foreign-definition"),
        })
    with pytest.raises(MinimalCognitionError, match="paired"):
        cpu_schema_epoch(make_percept(), registry, allowed_skills=SKILLS,
                         epoch=3, skill_definitions=definitions)


def test_l0_cannot_recreate_or_substitute_parameters_after_l1_select():
    registry, definitions, preset = registry_and_preset()
    frame = frame_with(registry, definitions, {"hunger-eat": preset})
    round_, result, owner = selected(frame)
    selection = resolve_l1_choice(
        round_, result, current_frame=frame, intent_owner=owner,
        available_skills=SKILLS,
    )
    assert selection.option is not None
    inv = selection.option.invocation
    assert inv is not None
    definition = definitions[("EAT", 1)]
    capability = PhysicalCapability("EAT", 1, "hand", "FOOD", True)
    ir = compile_invoked_skill(
        selection, definition=definition, target=inv.target,
        constraints=inv.constraints, budget=inv.budget,
        arguments=inv.arguments, provenance=inv.provenance, capability=capability,
    )
    assert ir.invocation is inv
    for altered in (
        {"budget": SkillBudget(2, 1800)},
        {"constraints": SkillConstraints()},
        {"provenance": Provenance("altered", "source")},
    ):
        kwargs = {
            "definition": definition, "target": inv.target,
            "constraints": inv.constraints, "budget": inv.budget,
            "arguments": inv.arguments, "provenance": inv.provenance,
            "capability": capability,
        }
        kwargs.update(altered)
        with pytest.raises(SkillIRRefusal, match="compiled parameters"):
            compile_invoked_skill(selection, **kwargs)
    owner.commit("intent-A", objective=inv.goal_id, at_ns=2,
                 provenance=SOURCE)
    skill = SkillExecution.start(
        "skill-run-A", skill_id="EAT",
        intent_commitment=owner, at_ns=3, provenance=SOURCE,
    )
    correct = FiniteSkillInterpreter().begin(
        selection, ir=ir, intent_owner=owner, skill_execution=skill,
        registered_versions=frozenset({("EAT", 1)}), deadline_ns=100,
    )
    assert correct.invocation_ref == inv.invocation_ref
    # A different IR with the same Goal/Skill/Target cannot replace the
    # selected invocation simply by presenting a valid definition.
    tampered_ir = replace(ir, invocation=replace(
        inv, budget=SkillBudget(2, 1800),
    ))
    with pytest.raises(SkillIRRefusal, match="L0 IR differs"):
        FiniteSkillInterpreter().begin(
            selection, ir=tampered_ir, intent_owner=owner, skill_execution=skill,
            registered_versions=frozenset({("EAT", 1)}), deadline_ns=100,
        )


def test_invalid_prediction_and_unbounded_budget_fail_without_authority():
    _, _, preset = registry_and_preset()
    with pytest.raises(SkillInvocationRefusal):
        SkillCostEstimate(-1, 50)
    with pytest.raises(SkillInvocationRefusal):
        replace(preset, budget=SkillBudget(65, 1000))
    with pytest.raises(SkillInvocationRefusal):
        replace(preset, expected_cost=SkillCostEstimate(1, float("nan")))
