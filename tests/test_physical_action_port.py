"""Physical ActionPort checks already-selected references without Action IO.

Synthetic source/owner fixtures only; no Minecraft/LLM/physical qualification.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.physical_action_port import (
    PhysicalActionBinding,
    PhysicalActionPortRefusal,
    PhysicalCapability,
    PhysicalReadback,
    propose_bound_physical_action,
)
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


def fixture():
    scope = ScopeRef("self-A", "world-A")
    native = Provenance("mineflayer", "world-A:12")
    binding = PhysicalActionBinding(
        scope=scope, intent_id="intent-A", goal_id="HUNGER_RELIEF",
        skill_id="EAT", skill_version=1,
        skill_execution_id="skill-eat-A", action_id="action-eat-A",
        capability_ref="consume_held", capability_version=1,
        body_channel="hand", target_kind="FOOD", target_ref="inventory:bread",
        native_seq=12, native_request_id="probe-A", native_source=native,
    )
    cap = PhysicalCapability(
        "consume_held", 1, "hand", "FOOD", True,
    )
    readback = PhysicalReadback(
        scope, native, 12, "probe-A", ("inventory:bread",), True,
    )
    owner = IntentCommitment()
    provenance = Provenance("dev-owner", "action-proposal")
    owner.commit("intent-A", objective="HUNGER_RELIEF", at_ns=2, provenance=provenance)
    skill = SkillExecution.start(
        "skill-eat-A", skill_id="EAT",
        intent_commitment=owner, at_ns=3, provenance=provenance,
    )
    supervisor = ActionSupervisor()
    return binding, cap, readback, owner, skill, supervisor, provenance


def propose(
    binding=None, cap=None, readback=None, owner=None, skill=None,
    supervisor=None, provenance=None, *,
    at_ns=4,
):
    base = fixture()
    vals = [
        binding if binding is not None else base[0],
        cap if cap is not None else base[1],
        readback if readback is not None else base[2],
        owner if owner is not None else base[3],
        skill if skill is not None else base[4],
        supervisor if supervisor is not None else base[5],
        provenance if provenance is not None else base[6],
    ]
    return propose_bound_physical_action(
        vals[0], capability=vals[1], readback=vals[2],
        intent_owner=vals[3], skill_execution=vals[4],
        supervisor=vals[5], at_ns=at_ns, provenance=vals[6],
    )


def test_existing_owner_yields_proposed_only_and_keeps_native_and_owner_unmodified():
    binding, cap, native, owner, skill, supervisor, provenance = fixture()
    events_before = owner.events
    receipt = propose_bound_physical_action(
        binding, capability=cap, readback=native,
        intent_owner=owner, skill_execution=skill,
        supervisor=supervisor, at_ns=4, provenance=provenance,
    )
    assert receipt.state == "PROPOSED_NOT_AUTHORIZED"
    assert receipt.proposal.state is ActionState.PROPOSED
    assert receipt.proposal.action_id == binding.action_id
    assert receipt.proposal.intent_id == binding.intent_id
    assert receipt.proposal.skill_execution_id == binding.skill_execution_id
    assert receipt.binding is binding
    assert receipt.physical_authorized is False
    assert receipt.physical_issued is False
    assert receipt.preissue_persisted is False
    assert receipt.proposal.is_current_snapshot
    assert owner.events == events_before
    assert supervisor.recorded_actions == ()
    assert supervisor.open_actions == ()
    assert supervisor.last_at_ns is None


@pytest.mark.parametrize("field,new_value", [
    ("intent_id", "intent-forged"),
    ("goal_id", "OTHER_GOAL"),
    ("skill_id", "MOVE"),
    ("skill_execution_id", "other-skill"),
    ("capability_ref", "attack_entity"),
    ("capability_version", 2),
    ("body_channel", "movement"),
    ("target_kind", "ZOMBIE"),
    ("target_ref", "inventory:apple"),
    ("native_seq", 11),
    ("native_request_id", "probe-B"),
    ("native_source", Provenance("mineflayer", "world-A:11")),
    ("scope", ScopeRef("foreign-self", "world-A")),
    ("scope", ScopeRef("self-A", "world-B")),
])
def test_selected_identity_and_source_cannot_be_retargeted(field, new_value):
    binding, cap, native, owner, skill, supervisor, provenance = fixture()
    changed = replace(binding, **{field: new_value})
    with pytest.raises(PhysicalActionPortRefusal):
        propose_bound_physical_action(
            changed, capability=cap, readback=native,
            intent_owner=owner, skill_execution=skill,
            supervisor=supervisor, at_ns=4, provenance=provenance,
        )
    assert owner.current_intent.intent_id == "intent-A"
    assert supervisor.recorded_actions == ()


@pytest.mark.parametrize("field,new_value", [
    ("capability_ref", "attack_entity"),
    ("version", 2),
    ("body_channel", "movement"),
    ("target_kind", "OTHER"),
    ("available", False),
])
def test_worldbody_capability_is_no_new_permission(field, new_value):
    binding, cap, native, owner, skill, supervisor, provenance = fixture()
    bad = replace(cap, **{field: new_value})
    with pytest.raises(PhysicalActionPortRefusal, match="physical capability"):
        propose_bound_physical_action(
            binding, capability=bad, readback=native, intent_owner=owner,
            skill_execution=skill, supervisor=supervisor,
            at_ns=4, provenance=provenance,
        )
    assert supervisor.recorded_actions == ()


@pytest.mark.parametrize("field,new_value", [
    ("scope", ScopeRef("self-B", "world-A")),
    ("scope", ScopeRef("self-A", "world-B")),
    ("source", Provenance("mineflayer", "world-A:13")),
    ("seq", 13),
    ("request_id", "probe-forged"),
    ("observed_target_refs", ("inventory:apple",)),
    ("observed_target_refs", ()),
    ("body_viable", False),
])
def test_source_target_and_body_state_must_still_match(field, new_value):
    binding, cap, native, owner, skill, supervisor, provenance = fixture()
    bad = replace(native, **{field: new_value})
    with pytest.raises(PhysicalActionPortRefusal, match="native source/Target"):
        propose_bound_physical_action(
            binding, capability=cap, readback=bad, intent_owner=owner,
            skill_execution=skill, supervisor=supervisor,
            at_ns=4, provenance=provenance,
        )
    assert supervisor.recorded_actions == ()


def test_no_intent_commit_is_not_silently_committed():
    binding, cap, native, _, skill, supervisor, provenance = fixture()
    empty = IntentCommitment()
    with pytest.raises(PhysicalActionPortRefusal, match="not current/committed"):
        propose_bound_physical_action(
            binding, capability=cap, readback=native, intent_owner=empty,
            skill_execution=skill, supervisor=supervisor,
            at_ns=4, provenance=provenance,
        )
    assert empty.events == ()


def test_intent_reconsideration_blocks_physical_proposal():
    binding, cap, native, owner, skill, supervisor, provenance = fixture()
    owner.request_reconsideration(
        "intent-A", reason="world changed", at_ns=4, provenance=provenance,
    )
    with pytest.raises(PhysicalActionPortRefusal, match="not current/committed"):
        propose_bound_physical_action(
            binding, capability=cap, readback=native, intent_owner=owner,
            skill_execution=skill, supervisor=supervisor,
            at_ns=5, provenance=provenance,
        )


def test_finished_or_stale_skill_cannot_propose_native_action():
    binding, cap, native, owner, skill, supervisor, provenance = fixture()
    finished = skill.succeed(reason="finished", at_ns=4, provenance=provenance)
    for value in (skill, finished):
        with pytest.raises(PhysicalActionPortRefusal, match="Skill execution"):
            propose_bound_physical_action(
                binding, capability=cap, readback=native, intent_owner=owner,
                skill_execution=value, supervisor=supervisor,
                at_ns=5, provenance=provenance,
            )


@pytest.mark.parametrize("busy", [True, False])
def test_supervisor_existing_action_blocks_busy_or_duplicate_even_after_terminal(busy):
    binding, cap, native, owner, skill, supervisor, provenance = fixture()
    original = ActionLifecycle.propose(
        "other-action" if busy else binding.action_id,
        skill_execution=skill, intent_commitment=owner,
        at_ns=3, provenance=provenance,
    )
    authorized = original.authorize(
        at_ns=4, provenance=provenance, authority="external-test-authority",
    )
    supervisor.issue(
        authorized, at_ns=5, deadline_ns=20, provenance=provenance,
    )
    if not busy:
        supervisor.record_outcome(original.action_id, at_ns=6, provenance=provenance)
    with pytest.raises(PhysicalActionPortRefusal, match=(
        "issued Action" if busy else "already supervised"
    )):
        propose_bound_physical_action(
            binding, capability=cap, readback=native, intent_owner=owner,
            skill_execution=skill, supervisor=supervisor,
            at_ns=7, provenance=provenance,
        )


def test_invalid_time_cannot_propose_before_committed_intent():
    binding, cap, native, owner, skill, supervisor, provenance = fixture()
    with pytest.raises(PhysicalActionPortRefusal, match="precedes Intent owner"):
        propose_bound_physical_action(
            binding, capability=cap, readback=native, intent_owner=owner,
            skill_execution=skill, supervisor=supervisor,
            at_ns=1, provenance=provenance,
        )


@pytest.mark.parametrize("change", [
    {"skill_version": 0}, {"capability_version": 0},
    {"native_seq": -1}, {"native_request_id": ""}, {"action_id": " "},
    {"scope": ScopeRef("self-A")},
])
def test_malformed_physical_binding_is_invalid(change):
    binding = fixture()[0]
    with pytest.raises(PhysicalActionPortRefusal):
        replace(binding, **change)


def test_invalid_readback_or_capability_is_invalid():
    _, cap, readback, *_ = fixture()
    for bad in (
        {"observed_target_refs": ("a", "a")},
        {"observed_target_refs": ["inventory:bread"]},
        {"body_viable": None},
        {"request_id": " "},
    ):
        with pytest.raises(PhysicalActionPortRefusal):
            replace(readback, **bad)
    with pytest.raises(PhysicalActionPortRefusal):
        replace(cap, available=1)
