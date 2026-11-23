"""#855 P0-B offline DEV joins; all native/Paper examples here are synthetic."""
from __future__ import annotations

from dataclasses import replace

import pytest

from relay_self.attack_world_join_dev import (
    AttackWalEvidence,
    AttackWorldJoinError,
    AttackWorldJoinStatus,
    NativeIdentityWitness,
    ServerAttackTicket,
    ServerDamageEvent,
    ServerDeathEvent,
    attack_from_restored_wal,
    join_attack_world_dev,
)
from relay_self.physical_action_journal import PhysicalActionJournal

ACTOR = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ZOMBIE = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
OTHER = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


def _sample(*, death: bool = False):
    wal = AttackWalEvidence(
        "self-A", "attack-1", "native-session-A", "entity:125",
        10, 7, 13, 12, 14, "a" * 64,
    )
    native = NativeIdentityWitness(
        "self-A", "attack-1", "native-session-A", "native:session-A:seq10",
        10, 125, 7, ZOMBIE, ACTOR,
    )
    ticket = ServerAttackTicket(
        "minecraft-1", "branch-alpha", "attack-1", "native-session-A",
        "ticket-attack-1-one-shot", ACTOR, ZOMBIE, 101,
        "paper:ticket-armed-101",
    )
    damage = ServerDamageEvent(
        "minecraft-1", "branch-alpha", "damage-event-1", 102, ZOMBIE,
        ACTOR, "ENTITY_ATTACK", 20.0, 0.0 if death else 16.0,
        "paper:damage-event-1", "ticket-attack-1-one-shot",
    )
    deaths = (
        ServerDeathEvent(
            "minecraft-1", "branch-alpha", "zombie-death-1", 102,
            ZOMBIE, ACTOR, "damage-event-1", "paper:death-event-1",
        ),
    ) if death else ()
    return wal, native, ticket, damage, deaths


def _join(
    wal, native, ticket, damage_events, death_events=(),
    *, world_id="minecraft-1", branch_id="branch-alpha",
):
    return join_attack_world_dev(
        wal, native, world_id=world_id, branch_id=branch_id,
        ticket=ticket, damage_events=tuple(damage_events),
        death_events=tuple(death_events),
    )


def test_paper_damage_event_requires_independent_armed_ticket():
    wal, native, ticket, damage, deaths = _sample()
    out = _join(wal, native, ticket, (damage,), deaths)
    assert out.status is AttackWorldJoinStatus.DEV_ACTION_DAMAGE_CORRELATED
    assert out.parent_action_id == "attack-1"
    assert out.target_uuid == ZOMBIE
    assert out.world_damage_event_id == "damage-event-1"
    assert out.world_death_event_id is None
    assert out.action_issue_authorized is False
    assert out.exact_causality_attested is False
    assert "paper:damage-event-1" in out.sources


def test_same_damage_without_ticket_not_assigned_to_one_action():
    wal, native, _ticket, damage, _deaths = _sample()
    out = _join(wal, native, None, (replace(damage, ticket_nonce=None),))
    assert out.status is AttackWorldJoinStatus.DEV_SERVER_DAMAGE_UNJOINED
    assert out.action_issue_authorized is False
    assert out.exact_causality_attested is False


def test_ticket_with_direct_same_damage_death_event_correlates_death_not_only_hit():
    wal, native, ticket, damage, death = _sample(death=True)
    out = _join(wal, native, ticket, (damage,), death)
    assert out.status is AttackWorldJoinStatus.DEV_ACTION_DEATH_CORRELATED
    assert out.world_death_event_id == "zombie-death-1"
    assert out.exact_causality_attested is False


def test_death_without_explicit_damage_event_join_does_not_claim_kill():
    wal, native, ticket, damage, death = _sample(death=True)
    out = _join(
        wal, native, ticket, (damage,),
        (replace(death[0], causing_damage_event_id=None),),
    )
    assert out.status is AttackWorldJoinStatus.DEV_ACTION_DAMAGE_CORRELATED
    assert out.world_death_event_id is None


@pytest.mark.parametrize("kind", [
    "wrong-target-uuid", "wrong-actor-uuid", "wrong-cause", "wrong-ticket",
    "wrong-world", "wrong-branch", "before-ticket",
])
def test_foreign_server_damage_cannot_claim_action(kind):
    wal, native, ticket, damage, _ = _sample()
    if kind == "wrong-target-uuid":
        damage = replace(damage, victim_uuid=OTHER)
    elif kind == "wrong-actor-uuid":
        damage = replace(damage, attacker_uuid=OTHER)
    elif kind == "wrong-cause":
        damage = replace(damage, damage_cause="FALL")
    elif kind == "wrong-ticket":
        damage = replace(damage, ticket_nonce="not-armed-ticket")
    elif kind == "wrong-world":
        damage = replace(damage, world_id="other-world")
    elif kind == "wrong-branch":
        damage = replace(damage, branch_id="fork-restart")
    elif kind == "before-ticket":
        damage = replace(damage, tick=100)
    assert _join(wal, native, ticket, (damage,)).status is AttackWorldJoinStatus.HOLD_UNKNOWN


@pytest.mark.parametrize("kind", [
    "session", "self", "action", "target-runtime-id", "actor-runtime-id",
    "probe-seq", "target-uuid-respawn",
])
def test_native_mapping_is_session_and_source_qualified(kind):
    wal, native, ticket, damage, _ = _sample()
    if kind == "session":
        native = replace(native, session_id="other-native-session")
    elif kind == "self":
        native = replace(native, self_id="self-B")
    elif kind == "action":
        native = replace(native, action_id="attack-other")
    elif kind == "target-runtime-id":
        native = replace(native, runtime_target_entity_id=2)
    elif kind == "actor-runtime-id":
        native = replace(native, runtime_actor_entity_id=55)
    elif kind == "probe-seq":
        native = replace(native, probe_seq=9)
    else:
        # After rollback entity:125 can designate another UUID. No reuse.
        native = replace(native, target_uuid=OTHER)
    assert _join(wal, native, ticket, (damage,)).status is AttackWorldJoinStatus.HOLD_UNKNOWN


@pytest.mark.parametrize("kind", [
    "action", "native-session", "target-uuid", "actor-uuid",
    "other-branch", "other-world",
])
def test_server_one_shot_ticket_must_match_binding(kind):
    wal, native, ticket, damage, _ = _sample()
    if kind == "action":
        ticket = replace(ticket, action_id="other-action")
    elif kind == "native-session":
        ticket = replace(ticket, native_session_id="other-session")
    elif kind == "target-uuid":
        ticket = replace(ticket, target_uuid=OTHER)
    elif kind == "actor-uuid":
        ticket = replace(ticket, actor_uuid=OTHER)
    elif kind == "other-branch":
        ticket = replace(ticket, branch_id="fork-other")
    else:
        ticket = replace(ticket, world_id="other-world")
    assert _join(wal, native, ticket, (damage,)).status is AttackWorldJoinStatus.HOLD_UNKNOWN


def test_duplicate_same_ticket_events_ambiguous():
    wal, native, ticket, damage, _ = _sample()
    duplicated = replace(damage, event_id="damage-event-2", tick=103)
    result = _join(wal, native, ticket, (damage, duplicated))
    assert result.status is AttackWorldJoinStatus.HOLD_UNKNOWN
    assert result.world_damage_event_id is None


def test_duplicate_server_event_ids_are_refused():
    wal, native, ticket, damage, _ = _sample()
    with pytest.raises(AttackWorldJoinError, match="duplicated"):
        _join(wal, native, ticket, (damage, damage))


def test_death_claim_with_nonlethal_damage_cannot_be_a_kill():
    wal, native, ticket, damage, _ = _sample(death=False)
    death = ServerDeathEvent(
        "minecraft-1", "branch-alpha", "impossible-death", 102, ZOMBIE,
        ACTOR, "damage-event-1", "paper:impossible-death",
    )
    out = _join(wal, native, ticket, (damage,), (death,))
    assert out.status is AttackWorldJoinStatus.HOLD_UNKNOWN


def test_two_deaths_from_same_damage_are_ambiguous():
    wal, native, ticket, damage, death = _sample(death=True)
    second = replace(death[0], event_id="zombie-death-2", tick=103)
    out = _join(wal, native, ticket, (damage,), (death[0], second))
    assert out.status is AttackWorldJoinStatus.HOLD_UNKNOWN


def test_server_native_sources_must_not_be_identical():
    wal, native, ticket, damage, _ = _sample()
    damage = replace(damage, server_source_ref=native.source_ref)
    out = _join(wal, native, ticket, (damage,))
    assert out.status is AttackWorldJoinStatus.HOLD_UNKNOWN
    out = _join(wal, native, None, (replace(damage, ticket_nonce=None),))
    assert out.status is AttackWorldJoinStatus.HOLD_UNKNOWN


def test_missing_native_identity_witness_holds_without_ticket_or_world():
    wal, _native, ticket, damage, _ = _sample()
    out = _join(wal, None, ticket, (damage,))
    assert out.status is AttackWorldJoinStatus.HOLD_UNKNOWN
    assert out.target_uuid is None
    assert out.action_issue_authorized is False


def test_unresolved_or_missing_wal_rejected_by_actual_physical_adapter(tmp_path):
    # No destructive or fake terminal WAL construction. An empty real journal
    # has no terminal ATTACK action, so cannot be promoted by an event.
    path = tmp_path / "physical-wal.json"
    j = PhysicalActionJournal.create(path, self_id="self-A")
    read = PhysicalActionJournal.restore(path, self_id="self-A")
    old = path.read_bytes()
    with pytest.raises(AttackWorldJoinError, match="exact existing ATTACK WAL"):
        attack_from_restored_wal(read, self_id="self-A", action_id="attack-1")
    with pytest.raises(AttackWorldJoinError, match="foreign"):
        attack_from_restored_wal(read, self_id="self-B", action_id="attack-1")
    assert path.read_bytes() == old
    assert j.digest == read.digest


def test_invalid_health_and_noncannonical_identity_refused():
    _wal, native, ticket, damage, _ = _sample()
    with pytest.raises(AttackWorldJoinError):
        replace(native, target_uuid="not-a-uuid")
    with pytest.raises(AttackWorldJoinError):
        replace(ticket, actor_uuid="AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA")
    with pytest.raises(AttackWorldJoinError):
        replace(damage, health_before=20.0, health_after=20.0)
    with pytest.raises(AttackWorldJoinError):
        replace(damage, health_before=True)
