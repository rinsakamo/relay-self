"""Cognitive selected EAT/ATTACK native witnesses reach PROPOSED, never ISSUE.

Synthetic Mineflayer/provider facts only. No original S49 or physical World.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.cognitive_physical_action_preflight import (
    propose_from_cognitive_readonly_evidence,
)
from experiments.cognitive_s49_readonly_handoff import S49ShadowRefusal
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.physical_action_port import (
    PhysicalActionPortRefusal,
    PhysicalCapability,
)
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution
from test_cognitive_minimal_minecraft_dev import bread, observation, zombie
from test_cognitive_s49_readonly_handoff import select


def original_selected_eat():
    start = observation(1, kind="inventory", inventory=(bread(),))
    prev = observation(2, inventory=(bread(),), request_id="pre-action-A")
    current = observation(3, inventory=(bread(),), request_id="pre-action-B")
    first_frame, current_frame, selected, owner = select(start, current)
    return first_frame, current_frame, selected, owner, prev, current


def _propose(
    first, current_frame, selected, owner, previous, current, *,
    cap=None, selected_intent_id="intent-A",
):
    provenance = Provenance("test-cognition", "commit-before-action")
    if owner.current_intent is None:
        owner.commit("intent-A", objective=selected.option.goal_id,
                     at_ns=1, provenance=provenance)
    skill = SkillExecution.start(
        "skill-EAT-1", skill_id=selected.option.skill_id,
        intent_commitment=owner, at_ns=2, provenance=provenance,
    )
    sup = ActionSupervisor()
    if cap is None:
        cap = PhysicalCapability("equip_item", 1, "hand", "FOOD", True)
    receipt = propose_from_cognitive_readonly_evidence(
        selected, original_frame=first, current_frame=current_frame,
        previous_probe=previous, current_probe=current,
        selected_intent_id=selected_intent_id,
        capability=cap, action_id="physical-equip-proposed-1",
        intent_owner=owner, skill_execution=skill, supervisor=sup,
        at_ns=3, provenance=provenance,
    )
    return receipt, sup, skill, owner


def test_real_shaped_eat_shadow_creates_only_existing_proposed_action():
    first, now, selected, owner, previous, current = original_selected_eat()
    receipt, supervisor, skill, owner = _propose(
        first, now, selected, owner, previous, current,
    )
    assert receipt.read_only_witness.skill_id == "EAT"
    assert receipt.read_only_witness.food_item == "bread"
    assert receipt.read_only_witness.food_slot == 9
    assert receipt.port_proposal.binding.target_ref == "inventory:bread"
    assert receipt.port_proposal.binding.capability_ref == "equip_item"
    assert receipt.port_proposal.binding.native_request_id == "pre-action-B"
    assert receipt.port_proposal.binding.native_source == current.provenance
    assert receipt.port_proposal.binding.intent_id == owner.current_intent.intent_id
    assert receipt.port_proposal.proposal.state is ActionState.PROPOSED
    assert receipt.port_proposal.proposal.skill_execution_id == skill.execution_id
    assert receipt.port_proposal.physical_issued is False
    assert receipt.port_proposal.physical_authorized is False
    assert receipt.port_proposal.preissue_persisted is False
    assert supervisor.recorded_actions == ()


@pytest.mark.parametrize("mutation", [
    "foreign_session", "reused_request_id", "changed_slot",
    "changed_target", "moved_body",
])
def test_shadow_refuses_to_project_stale_or_changed_native_food(mutation):
    first, now, selected, owner, previous, current = original_selected_eat()
    if mutation == "foreign_session":
        current = replace(current, session_id="another-world")
    elif mutation == "reused_request_id":
        current = replace(current, request_id=previous.request_id)
    elif mutation == "changed_slot":
        current = replace(current, snapshot=replace(
            current.snapshot, inventory=(replace(bread(), slot=11),),
        ))
    elif mutation == "changed_target":
        current = replace(current, snapshot=replace(
            current.snapshot, inventory=(),
        ))
    elif mutation == "moved_body":
        current = replace(current, snapshot=replace(
            current.snapshot,
            position=replace(current.snapshot.position, x=0.5),
        ))
    with pytest.raises(S49ShadowRefusal):
        _propose(first, now, selected, owner, previous, current)
    assert owner.current_intent.intent_id == "intent-A"


def test_primitive_capability_cannot_be_swapped_to_zombie_attack_for_eat():
    first, now, selected, owner, previous, current = original_selected_eat()
    cap = PhysicalCapability("attack_entity", 1, "hand", "ZOMBIE", True)
    with pytest.raises(PhysicalActionPortRefusal, match="physical capability"):
        _propose(first, now, selected, owner, previous, current, cap=cap)


def test_shadow_is_not_physical_authority_or_auto_intent_owner():
    first, now, selected, owner, previous, current = original_selected_eat()
    assert owner.current_intent is None
    assert owner.events == ()
    with pytest.raises(PhysicalActionPortRefusal, match="selected Intent"):
        _propose(
            first, now, selected, owner, previous, current,
            selected_intent_id="foreign-intent",
        )


def test_attack_selected_target_can_be_proposed_without_issuing_attack():
    start = observation(1, kind="entities", food=20, entities=(zombie(),))
    prev = observation(2, food=20, entities=(zombie(),), request_id="attack-A")
    cur = observation(3, food=20, entities=(zombie(),), request_id="attack-B")
    first, now, selected, owner = select(start, cur)
    cap = PhysicalCapability("attack_entity", 1, "hand", "ZOMBIE", True)
    receipt, supervisor, _, _ = _propose(
        first, now, selected, owner, prev, cur, cap=cap,
    )
    assert receipt.read_only_witness.target_entity_id == 7
    assert receipt.port_proposal.binding.target_ref == "entity:7"
    assert receipt.port_proposal.proposal.state is ActionState.PROPOSED
    assert receipt.port_proposal.physical_issued is False
    assert supervisor.recorded_actions == ()
