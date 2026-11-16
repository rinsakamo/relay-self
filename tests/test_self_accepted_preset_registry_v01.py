"""Self-accepted parameter preset lifecycle + bounded pre-SystemOne shortlist.

Pure source-shaped synthetic CPU DEV; not a live owner, GPU, or native Action.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from relay_self.cognitive_minimal_dev import (
    MinimalCognitionError,
    Option,
    Origin,
    PatternKind,
    PatternRegistry,
    Predicate,
    PresetAcceptanceReceipt,
    SchemaPattern,
    Target,
    WorldPercept,
    accept_learned_pattern,
    accept_skill_parameter_preset,
    assemble_l1_select,
    cpu_schema_epoch,
    initial_move_pattern,
    initial_patterns,
    resolve_l1_choice,
    retire_skill_parameter_preset,
)
from relay_self.common_io import ScopeRef
from relay_self.initial_skill_ir import initial_skill_definitions
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.relay_engine import ProviderDecision, RelayEngine
from relay_self.skill_invocation import (
    ArgumentKind,
    SkillArgument,
    SkillBudget,
    SkillConstraints,
    SkillCostEstimate,
    SkillParameterPreset,
)

SCOPE = ScopeRef("self-A", "world-A")
SOURCE = Provenance("gateway", "native-13")
SKILLS = frozenset({("EAT", 1), ("ATTACK", 1), ("MOVE", 1)})
DEFINITIONS = {(d.skill_id, d.version): d for d in initial_skill_definitions()}


def make_preset(pattern_id: str, skill_id: str, *, preset_id: str = "Default",
                version: int = 1, budget: int = 1):
    definition = DEFINITIONS[(skill_id, 1)]
    return SkillParameterPreset(
        pattern_id, preset_id, version, definition.definition_ref,
        SkillConstraints((
            SkillArgument("only_if_available", ArgumentKind.FLAG, True),
        )),
        SkillBudget(budget, 2000, max_observations=4),
        Provenance("self-accepted-schema-preset", f"{pattern_id}-{preset_id}-{version}"),
        expected_cost=SkillCostEstimate(1, 500),
    )


def accepted(registry, preset, *, self_id="self-A", decision_id=None,
             definition=None, expected_revision=None, accepted_by_self=True):
    receipt = PresetAcceptanceReceipt(
        self_id, decision_id or f"accept-{registry.revision}-{preset.preset_ref}",
        preset.preset_ref, Provenance("self-owner", "acceptance-ledger"),
    )
    return accept_skill_parameter_preset(
        registry, preset, definition=definition or
        DEFINITIONS[("MOVE" if preset.pattern_id == "exploration-move"
                     else "ATTACK" if preset.pattern_id == "defense-attack"
                     else "EAT", 1)],
        receipt=receipt, accepted_by_self=accepted_by_self,
        expected_revision=(registry.revision if expected_revision is None
                           else expected_revision),
        available_skills=SKILLS,
    )


def percept(*, sequence=13, self_id="self-A", food=True,
            zombie=False, explore=False, source_name="gateway"):
    source = Provenance(source_name, f"native-{sequence}")
    targets = []
    if food:
        targets.append(Target("inventory:bread", "FOOD", source,
                              "world-A", sequence))
    if zombie:
        targets.append(Target("entity:7", "ZOMBIE", source,
                              "world-A", sequence))
    if explore:
        targets.append(Target("destination:stable", "DESTINATION",
                              Provenance("world-config", "waypoint-1"),
                              "world-A", sequence))
    return WorldPercept(ScopeRef(self_id, "world-A"), source, sequence,
                        hunger=8, fatigue_high=False,
                        targets=tuple(targets), exploration_need=explore)


def epoch(p, registry, *, n=1, fast_crisis=False):
    return cpu_schema_epoch(
        p, registry, allowed_skills=SKILLS, epoch=n,
        skill_definitions=DEFINITIONS, use_registered_presets=True,
        fast_crisis=fast_crisis,
    )


def select(frame, option=None):
    owner = IntentCommitment()
    round_ = assemble_l1_select(frame, intent_owner=owner)
    if option is None:
        option = next(x for _, x in round_.numbered if isinstance(x, Option))
    choice_id = next(n for n, x in round_.numbered if x is option)
    result = RelayEngine(
        lambda request, *, mode: ProviderDecision.resolved(choice_id),
    )(round_.request)
    return round_, result, owner


def test_unaccepted_preset_leaves_goal_unresolved_and_no_implicit_l1_parameters():
    registry = initial_patterns()
    frame = epoch(percept(), registry)
    assert [g.goal_id for g in frame.goals] == ["HUNGER_RELIEF"]
    assert frame.goals[0].unresolved
    assert frame.options == ()
    assert [x for _, x in assemble_l1_select(
        frame, intent_owner=IntentCommitment(),
    ).numbered] == ["ESCALATE_L2", "DEFER"]
    proposed = make_preset("hunger-eat", "EAT")
    with pytest.raises(MinimalCognitionError, match="unaccepted"):
        accepted(registry, proposed, accepted_by_self=False)
    assert registry.accepted_presets == ()


def test_self_accepted_registry_publishes_complete_invocation_and_revision():
    registry = initial_patterns()
    preset = make_preset("hunger-eat", "EAT")
    newer = accepted(registry, preset)
    assert registry.revision == 0 and registry.accepted_presets == ()
    assert newer.revision == 1 and len(newer.accepted_presets) == 1
    frame = epoch(percept(), newer)
    inv = frame.options[0].invocation
    assert inv is not None
    assert inv.parameter_preset_ref == preset.preset_ref
    assert inv.budget == preset.budget
    assert inv.expected_cost == preset.expected_cost
    assert inv.constraints == preset.constraints
    round_, result, owner = select(frame)
    chosen = resolve_l1_choice(
        round_, result, current_frame=epoch(percept(sequence=14), newer, n=2),
        intent_owner=owner, available_skills=SKILLS,
    )
    # A refreshed native observation is not a changed parameter preset.
    assert chosen.status == "READY"
    assert chosen.option.invocation.invocation_ref == inv.invocation_ref


def test_owner_cas_revision_and_monotonic_version_with_stale_l1_refusal():
    registry = initial_patterns()
    first = make_preset("hunger-eat", "EAT")
    v1 = accepted(registry, first)
    frame1 = epoch(percept(), v1)
    round_, result, owner = select(frame1)
    v2_preset = make_preset("hunger-eat", "EAT", version=2, budget=2)
    with pytest.raises(MinimalCognitionError, match="stale"):
        accepted(v1, v2_preset, expected_revision=0)
    with pytest.raises(MinimalCognitionError, match="advance"):
        accepted(v1, make_preset("hunger-eat", "EAT", version=4))
    v2 = accepted(v1, v2_preset)
    assert v1.accepted_presets[0].preset is first
    assert v2.accepted_presets[0].preset is v2_preset
    newer = epoch(percept(sequence=14), v2, n=2)
    assert resolve_l1_choice(
        round_, result, current_frame=newer, intent_owner=owner,
        available_skills=SKILLS,
    ).status == "REJECTED"
    with pytest.raises(MinimalCognitionError, match="replayed"):
        accepted(v2, make_preset("hunger-eat", "EAT", version=3),
                 decision_id=v2.accepted_presets[0].receipt.event_id)
    v3 = retire_skill_parameter_preset(
        v2, self_id="self-A", pattern_id="hunger-eat",
        preset_id="Default", accepted_by_self=True, expected_revision=v2.revision,
    )
    assert v3.accepted_presets == ()
    assert epoch(percept(), v3).options == ()


def test_other_self_receipt_never_becomes_this_self_skill():
    registry = accepted(initial_patterns(), make_preset("hunger-eat", "EAT"),
                        self_id="self-B")
    assert epoch(percept(), registry).options == ()
    assert len(epoch(percept(self_id="self-B"), registry).options) == 1


def test_foreign_or_malformed_acceptance_fails_closed_without_registry_update():
    registry = initial_patterns()
    p = make_preset("hunger-eat", "EAT")
    with pytest.raises(MinimalCognitionError, match="receipt"):
        accept_skill_parameter_preset(
            registry, p, definition=DEFINITIONS[("EAT", 1)],
            receipt=PresetAcceptanceReceipt(
                "self-A", "event-1", "skill-preset:v1@foreign", SOURCE,
            ), accepted_by_self=True, expected_revision=0,
            available_skills=SKILLS,
        )
    with pytest.raises(MinimalCognitionError, match="capability"):
        accepted(registry, p, definition=DEFINITIONS[("MOVE", 1)])
    with pytest.raises(MinimalCognitionError, match="required"):
        accepted(registry, replace(p, pattern_id="unknown"))
    with pytest.raises(MinimalCognitionError, match="stale"):
        retire_skill_parameter_preset(
            registry, self_id="self-A", pattern_id="hunger-eat",
            preset_id="Default", accepted_by_self=True, expected_revision=5,
        )


def many_hunger_patterns(count=42):
    src = Provenance("innate-schema", "synthetic-many")
    return PatternRegistry(0, tuple(
        SchemaPattern(
            f"hunger-{i:02d}", 1, "homeostatic", PatternKind.GOAL,
            Predicate.HUNGRY, f"GOAL_{i:02d}", "EAT", 1, "FOOD",
            Origin.INNATE, src,
        ) for i in range(count)
    ))


def accept_many(registry):
    for pattern in registry.patterns:
        registry = accepted(registry, make_preset(pattern.pattern_id, "EAT"))
    return registry


def test_fair_shortlist_never_first_eight_starves_late_registered_goals():
    registry = accept_many(many_hunger_patterns())
    seen = set()
    for n in range(1, 21):
        frame = epoch(percept(), registry, n=n)
        assert len(frame.options) <= 8
        assert len(frame.eligible_options) == 42
        seen.update(x.goal_id for x in frame.options)
    assert len(seen) == 42


def test_shortlist_rotation_does_not_make_still_eligible_l1_selection_stale():
    registry = accept_many(many_hunger_patterns(20))
    first = epoch(percept(), registry, n=1)
    round_, result, owner = select(first)
    newer = epoch(percept(sequence=14), registry, n=2)
    assert len(newer.options) == 8
    assert first.options[0] not in newer.options
    assert resolve_l1_choice(
        round_, result, current_frame=newer, intent_owner=owner,
        available_skills=SKILLS,
    ).status == "READY"
    # But changing the real source family still invalidates it.
    changed = epoch(percept(sequence=14, source_name="foreign-gateway"),
                    registry, n=2)
    assert resolve_l1_choice(
        round_, result, current_frame=changed, intent_owner=owner,
        available_skills=SKILLS,
    ).status == "REJECTED"


def test_emergency_last_and_exploration_reservation_without_crisis_mask():
    base = many_hunger_patterns(12)
    src = Provenance("innate-schema", "synthetic-extra")
    defense = SchemaPattern(
        "defense-attack", 1, "defensive", PatternKind.GOAL,
        Predicate.ZOMBIE_NEAR, "DEFEND_SELF", "ATTACK", 1, "ZOMBIE",
        Origin.INNATE, src,
    )
    registry = PatternRegistry(base.revision, base.patterns +
                               (defense, initial_move_pattern()))
    for p in registry.patterns:
        skill = p.skill_id
        registry = accepted(registry, make_preset(p.pattern_id, skill))
    p = percept(zombie=True, explore=True)
    frame = epoch(p, registry)
    assert len(frame.options) == 8
    assert any(o.goal_id == "DEFEND_SELF" for o in frame.options)
    assert any(o.schema_id == "exploration" for o in frame.options)
    assert len(frame.eligible_options) == 14
    masked = epoch(p, registry, fast_crisis=True)
    assert len(masked.options) == 8
    assert not any(o.schema_id == "exploration" for o in masked.options)
    assert all(o.schema_id != "exploration" for o in masked.eligible_options)


def test_multi_preset_one_target_rotation_never_exceeds_two_presented():
    base = initial_patterns()
    for i in range(7):
        base = accepted(base, make_preset(
            "hunger-eat", "EAT", preset_id=f"V{i}",
        ))
    for n in range(1, 9):
        frame = epoch(percept(), base, n=n)
        assert len(frame.eligible_options) == 7
        assert len(frame.options) <= 2
        assert all(o.invocation is not None for o in frame.options)
    refs = {
        o.invocation.parameter_preset_ref
        for n in range(1, 9) for o in epoch(percept(), base, n=n).options
    }
    assert len(refs) == 7


def test_registered_preset_receipt_survives_new_pattern_snapshot():
    r0 = accepted(initial_patterns(), make_preset("hunger-eat", "EAT"))
    learned = SchemaPattern(
        "hunger-new", 1, "homeostatic", PatternKind.GOAL,
        Predicate.HUNGRY, "HUNGER_LEARNED", "EAT", 1, "FOOD",
        Origin.LEARNED, Provenance("l2-proposal", "not-owner-grant"),
    )
    r1 = accept_learned_pattern(
        r0, learned, accepted_by_self=True,
        expected_revision=r0.revision, allowed_skills=SKILLS,
    )
    assert r1.accepted_presets == r0.accepted_presets
    assert epoch(percept(), r1).options[0].goal_id == "HUNGER_RELIEF"


def test_registry_never_expands_physical_action_capability():
    base = initial_patterns()
    p = make_preset("hunger-eat", "EAT")
    with pytest.raises(MinimalCognitionError, match="capability"):
        accept_skill_parameter_preset(
            base, p, definition=DEFINITIONS[("EAT", 1)],
            receipt=PresetAcceptanceReceipt(
                "self-A", "event-1", p.preset_ref, SOURCE,
            ), accepted_by_self=True, expected_revision=0,
            available_skills=frozenset(),
        )
    with pytest.raises(MinimalCognitionError, match="requires definitions"):
        cpu_schema_epoch(percept(), base, allowed_skills=SKILLS, epoch=1,
                         use_registered_presets=True)
