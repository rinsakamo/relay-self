"""Original-S49-shaped two-probe precheck is a nonissuing typed witness.

The selected L1 target is never a new S49 grant, issuer, or durable fence.
All observations/providers here are synthetic; no Minecraft World is run.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.cognitive_minimal_minecraft_dev import native_schema_percept
from experiments.cognitive_s49_readonly_handoff import (
    S49ShadowRefusal,
    assess_s49_readonly_handoff,
)
from relay_self.cognitive_minimal_dev import (
    assemble_l1_select,
    cpu_schema_epoch,
    initial_patterns,
    resolve_l1_choice,
)
from relay_self.intent import IntentCommitment
from test_cognitive_minimal_minecraft_dev import (
    bread,
    engine_with_choice,
    observation,
    scenario,
    zombie,
)

SKILLS = frozenset({("EAT", 1), ("ATTACK", 1)})


def select(initial, last):
    owner = IntentCommitment()
    cfg = scenario()
    patterns = initial_patterns()
    first = cpu_schema_epoch(
        native_schema_percept(initial, cfg, self_id="self-A"),
        patterns, epoch=1, allowed_skills=SKILLS, hunger_threshold=10,
    )
    second = cpu_schema_epoch(
        native_schema_percept(last, cfg, self_id="self-A"),
        patterns, epoch=2, allowed_skills=SKILLS, hunger_threshold=10,
    )
    round_ = assemble_l1_select(first, intent_owner=owner)
    selected = resolve_l1_choice(
        round_, engine_with_choice("1")(round_.request),
        current_frame=second, intent_owner=owner,
        available_skills=SKILLS,
    )
    return first, second, selected, owner


def test_readonly_eat_witness_binds_two_probes_food_slot_and_original_l1_option():
    initial = observation(1, kind="inventory", inventory=(bread(),))
    earlier = observation(2, inventory=(bread(),), request_id="s49-a")
    later = observation(3, inventory=(bread(),), request_id="s49-b")
    first, current, selected, owner = select(initial, later)
    receipt = assess_s49_readonly_handoff(
        selected, original_frame=first, current_frame=current,
        previous_probe=earlier, current_probe=later,
    )
    assert receipt.skill_id == "EAT" and receipt.target_ref == "inventory:bread"
    assert (receipt.food_item, receipt.food_slot) == ("bread", 9)
    assert (receipt.previous_probe_request_id, receipt.current_probe_request_id) == (
        "s49-a", "s49-b",
    )
    assert receipt.current_source_ref == "session-1:3"
    assert receipt.original_s49_authorized is False
    assert receipt.physical_action_issued is False
    assert receipt.evidence_class.endswith("NOT_AUTHORIZED")
    assert owner.events == ()


@pytest.mark.parametrize("change", [
    "same_request", "missing_request", "foreign_world", "seq_gap",
    "kind", "dead", "drowning", "moved", "extra_mob", "truncated",
    "changed_slot", "stale_schema",
])
def test_readonly_eat_refuses_unqualified_witnesses(change):
    initial = observation(1, kind="inventory", inventory=(bread(),))
    earlier = observation(2, inventory=(bread(),), request_id="s49-a")
    later = observation(3, inventory=(bread(),), request_id="s49-b")
    first, current, selected, owner = select(initial, later)
    if change == "same_request":
        later = replace(later, request_id="s49-a")
    elif change == "missing_request":
        later = replace(later, request_id=None)
    elif change == "foreign_world":
        later = replace(later, session_id="another-session")
    elif change == "seq_gap":
        later = replace(later, seq=35)
    elif change == "kind":
        later = replace(later, kind="health", request_id=None)
    elif change == "dead":
        later = replace(later, snapshot=replace(later.snapshot, health=0))
    elif change == "drowning":
        later = replace(later, snapshot=replace(later.snapshot, oxygen_level=0))
    elif change == "moved":
        p = later.snapshot.position
        later = replace(later, snapshot=replace(
            later.snapshot, position=replace(p, x=p.x + .051),
        ))
    elif change == "extra_mob":
        mob = zombie(distance=9)
        later = replace(later, snapshot=replace(
            later.snapshot, nearby_entities=(mob,),
            nearby_entities_coverage=replace(
                later.snapshot.nearby_entities_coverage, candidate_count=1,
            ),
        ))
    elif change == "truncated":
        # Native snapshot requires a coherent full 16-entry window to be
        # allowed to declare truncated coverage (>16 candidate entities).
        saturated = tuple(zombie(entity_id=100 + n) for n in range(16))
        later = replace(later, snapshot=replace(
            later.snapshot, nearby_entities=saturated,
            nearby_entities_coverage=replace(
                later.snapshot.nearby_entities_coverage,
                candidate_count=17, truncated=True,
            ),
        ))
    elif change == "changed_slot":
        other = replace(bread(), slot=10)
        later = replace(later, snapshot=replace(
            later.snapshot, inventory=(other,),
        ))
    elif change == "stale_schema":
        first, current, selected, owner = select(initial, later)
        current = replace(current, source=earlier.provenance)
    with pytest.raises(S49ShadowRefusal):
        assess_s49_readonly_handoff(
            selected, original_frame=first, current_frame=current,
            previous_probe=earlier, current_probe=later,
        )
    assert owner.events == ()


def test_readonly_attack_witness_single_stable_zombie_no_s49_grant():
    initial = observation(1, kind="entities", food=20, entities=(zombie(),))
    earlier = observation(2, food=20, entities=(zombie(),), request_id="s49-a")
    later = observation(3, food=20, entities=(zombie(),), request_id="s49-b")
    first, current, selected, owner = select(initial, later)
    witness = assess_s49_readonly_handoff(
        selected, original_frame=first, current_frame=current,
        previous_probe=earlier, current_probe=later,
    )
    assert witness.skill_id == "ATTACK"
    assert witness.target_ref == "entity:7" and witness.target_entity_id == 7
    assert witness.food_item is None and witness.food_slot is None
    assert not witness.original_s49_authorized and not witness.physical_action_issued
    assert owner.current_intent is None


@pytest.mark.parametrize("change", [
    "far", "entity_moved", "other_entity", "two_entities", "body_moved",
    "truncated", "id_changed", "incompatible_target",
])
def test_readonly_attack_refuses_unstable_or_wrong_native_target(change):
    initial = observation(1, kind="entities", food=20, entities=(zombie(),))
    earlier = observation(2, food=20, entities=(zombie(),), request_id="s49-a")
    later = observation(3, food=20, entities=(zombie(),), request_id="s49-b")
    first, current, selected, owner = select(initial, later)
    if change == "far":
        later = replace(later, snapshot=replace(
            later.snapshot, nearby_entities=(zombie(distance=3),),
        ))
    elif change == "entity_moved":
        mob = zombie()
        moved = replace(mob, position=replace(mob.position, x=2.251))
        later = replace(later, snapshot=replace(
            later.snapshot, nearby_entities=(moved,),
        ))
    elif change == "other_entity":
        later = replace(later, snapshot=replace(
            later.snapshot, nearby_entities=(replace(zombie(), name="skeleton"),),
        ))
    elif change == "two_entities":
        later = replace(later, snapshot=replace(
            later.snapshot,
            nearby_entities=(zombie(), replace(zombie(), entity_id=8)),
            nearby_entities_coverage=replace(
                later.snapshot.nearby_entities_coverage, candidate_count=2,
            ),
        ))
    elif change == "body_moved":
        later = replace(later, snapshot=replace(
            later.snapshot, position=replace(later.snapshot.position, z=.051),
        ))
    elif change == "truncated":
        # Native snapshot requires a coherent full 16-entry window to be
        # allowed to declare truncated coverage (>16 candidate entities).
        saturated = tuple(zombie(entity_id=100 + n) for n in range(16))
        later = replace(later, snapshot=replace(
            later.snapshot, nearby_entities=saturated,
            nearby_entities_coverage=replace(
                later.snapshot.nearby_entities_coverage,
                candidate_count=17, truncated=True,
            ),
        ))
    elif change == "id_changed":
        later = replace(later, snapshot=replace(
            later.snapshot, nearby_entities=(zombie(entity_id=8),),
        ))
    elif change == "incompatible_target":
        selected = replace(selected, option=replace(
            selected.option, target_ref="entity:999",
        ))
    with pytest.raises(S49ShadowRefusal):
        assess_s49_readonly_handoff(
            selected, original_frame=first, current_frame=current,
            previous_probe=earlier, current_probe=later,
        )
    assert owner.events == ()
