"""#851: causal reconstruction across World and two independent Self cuts.

All fixtures are synthetic; they do not authenticate Minecraft World saves,
Paper events or a real causal link to Mineflayer. Recovery never authorizes IO.
"""
from __future__ import annotations

from dataclasses import replace
from itertools import product

import pytest

from relay_self.causal_recovery import (
    ActionClaim,
    BeliefRecord,
    ReceivedMessage,
    RecoveryContractError,
    RecoveryVerdict,
    SelfCheckpoint,
    SentMessage,
    WalReceipt,
    WalState,
    WorldCheckpoint,
    WorldEntityState,
    WorldEvent,
    assess_reconstruction,
    project_physical_journal,
)
from relay_self.physical_action_journal import PhysicalActionJournal


# Use WorldEvent, not an adapter-native event. Every effect is a typed
# independent, hypothetical server+native causal join for an Action parent.
def _fixture():
    world = WorldCheckpoint(
        checkpoint_id="W110", world_id="minecraft-world-1",
        branch_id="branch-original", tick=110,
        atomic_capture_attested=True, event_coverage_through_tick=110,
        entity_states=(WorldEntityState("zombie-uuid-Z1", False),),
    )
    a = SelfCheckpoint(
        checkpoint_id="A-C105", self_id="A",
        world_id=world.world_id, branch_id=world.branch_id, tick=105,
        claims=(ActionClaim("attack-A", "entity:3", "zombie-uuid-Z1", 105),),
        beliefs=(BeliefRecord("zombie-uuid-Z1", 105, False, "native:105"),),
    )
    b = SelfCheckpoint(
        checkpoint_id="B-C98", self_id="B",
        world_id=world.world_id, branch_id=world.branch_id, tick=98,
        beliefs=(BeliefRecord("zombie-uuid-Z1", 98, True, "native:98"),),
    )
    journal = (
        WalReceipt(
            "A", "attack-A", "mineflayer-session-1", "entity:3",
            WalState.NATIVE_ATTACK_HURT_OBSERVED, "a" * 64,
        ),
    )
    event = WorldEvent(
        event_id="server-hurt-105", world_id=world.world_id,
        branch_id=world.branch_id, tick=105, actor_self_id="A",
        action_id="attack-A", native_session_id="mineflayer-session-1",
        target_uuid="zombie-uuid-Z1", entity_alive_after=False,
        native_source_ref="native:41/42", server_source_ref="server:tick105/uuidZ1",
        native_target_ref="entity:3",
    )
    return world, (a, b), journal, (event,)


def _decision(change):
    world, selves, wal, events = _fixture()
    return assess_reconstruction(world, selves, wal, events)


def test_w110_supports_a_c105_and_b_c98_without_same_tick_snapshots():
    world, selves, wal, events = _fixture()
    r = assess_reconstruction(world, selves, wal, events)
    assert r.verdict is RecoveryVerdict.CANDIDATE_REOBSERVE
    assert not r.physical_blockers
    assert not r.belief_conflicts
    assert r.action_issue_authorized is False
    assert "FRESH_WORLD_BODY_SCHEMA_OBSERVATION" in r.next_steps
    assert "INDEPENDENT_PHYSICAL_OWNER_FENCING_REQUIRED" in r.next_steps


def test_world_w100_while_a_c105_action_wal_ends_later_is_hold():
    world, selves, wal, events = _fixture()
    world = replace(world, checkpoint_id="W100", tick=100,
                    event_coverage_through_tick=100,
                    entity_states=(WorldEntityState("zombie-uuid-Z1", True),))
    decision = assess_reconstruction(world, selves, wal, events)
    assert decision.verdict is RecoveryVerdict.HOLD_PHYSICAL_RECONCILIATION
    assert any("newer than restored World" in x for x in decision.physical_blockers)
    assert any("after restored checkpoint" in x for x in decision.physical_blockers)


def test_other_actor_killed_same_target_cannot_certify_a_action():
    world, selves, wal, events = _fixture()
    events = (replace(events[0], actor_self_id="B", action_id="attack-B"),)
    out = assess_reconstruction(world, selves, wal, events)
    assert out.verdict is RecoveryVerdict.HOLD_PHYSICAL_RECONCILIATION
    assert any("lacks independent World effect" in x for x in out.physical_blockers)


def test_same_native_entity_id_wrong_uuid_not_causally_joined():
    world, selves, wal, events = _fixture()
    out = assess_reconstruction(world, selves, wal, (
        replace(events[0], target_uuid="zombie-uuid-Z2"),))
    assert out.verdict is RecoveryVerdict.HOLD_PHYSICAL_RECONCILIATION
    assert any("actor/UUID/cut mismatch" in x for x in out.physical_blockers)


@pytest.mark.parametrize("status", [
    WalState.PREPARED_UNRESOLVED,
    WalState.NATIVE_ATTACK_HURT_OBSERVED,
])
def test_unresolved_or_missing_wal_never_replays(status):
    world, selves, wal, events = _fixture()
    if status is WalState.NATIVE_ATTACK_HURT_OBSERVED:
        wal = ()
    else:
        wal = (replace(wal[0], status=status),)
    out = assess_reconstruction(world, selves, wal, events)
    assert out.verdict is RecoveryVerdict.HOLD_PHYSICAL_RECONCILIATION
    assert out.action_issue_authorized is False


def test_world_state_does_not_override_false_memory():
    world, (a, b), wal, events = _fixture()
    b = replace(b, checkpoint_id="B-C107", tick=107, beliefs=(
        BeliefRecord("zombie-uuid-Z1", 105, True, "B:unreliable-perception"),
    ))
    out = assess_reconstruction(world, (a, b), wal, events)
    assert out.verdict is RecoveryVerdict.CANDIDATE_REOBSERVE
    assert len(out.belief_conflicts) == 1
    assert "epistemic review" in out.belief_conflicts[0]


def test_distinct_uuid_respawns_after_killed_zombie_is_consistent():
    world, selves, wal, events = _fixture()
    world = replace(world, entity_states=(
        WorldEntityState("zombie-uuid-Z1", False),
        WorldEntityState("zombie-uuid-Z2", True),
    ))
    spawn = WorldEvent(
        "new-zombie-uuid", world.world_id, world.branch_id, 108,
        None, None, None, "zombie-uuid-Z2", True, None, "paper:spawn-Z2",
    )
    out = assess_reconstruction(world, selves, wal, (*events, spawn))
    assert out.verdict is RecoveryVerdict.CANDIDATE_REOBSERVE


def test_missing_send_from_other_self_holds_receiver_cut():
    world, (a, b), wal, events = _fixture()
    b = replace(b, checkpoint_id="B-C106", tick=106,
                received=(ReceivedMessage("A", "future-message", 106),))
    out = assess_reconstruction(world, (a, b), wal, events)
    assert out.verdict is RecoveryVerdict.HOLD_PHYSICAL_RECONCILIATION
    assert any("sender causal cut" in x for x in out.physical_blockers)


def test_message_send_before_receive_does_not_force_simultaneous_snapshots():
    world, (a, b), wal, events = _fixture()
    a = replace(a, sent=(SentMessage("m-1", 99),))
    b = replace(b, checkpoint_id="B-C108", tick=108,
                received=(ReceivedMessage("A", "m-1", 108),))
    out = assess_reconstruction(world, (a, b), wal, events)
    assert out.verdict is RecoveryVerdict.CANDIDATE_REOBSERVE


@pytest.mark.parametrize("reason", ["branch", "torn", "state", "other_event_branch"])
def test_hard_checkpoint_mismatch_rejected(reason):
    world, selves, wal, events = _fixture()
    if reason == "branch":
        world = replace(world, branch_id="rewound-fork")
    elif reason == "torn":
        world = replace(world, atomic_capture_attested=False)
    elif reason == "state":
        world = replace(world, entity_states=(WorldEntityState("zombie-uuid-Z1", True),))
    else:
        events = (replace(events[0], branch_id="other-branch"),)
    out = assess_reconstruction(world, selves, wal, events)
    assert out.verdict is RecoveryVerdict.REJECT_CHECKPOINT


def test_world_tick_not_comparable_across_forks_even_when_equal():
    world, selves, wal, events = _fixture()
    world = replace(world, branch_id="fork-2", checkpoint_id="W110-fork")
    decision = assess_reconstruction(world, selves, wal, events)
    assert decision.verdict is RecoveryVerdict.REJECT_CHECKPOINT


def test_incomplete_server_event_coverage_never_becomes_implicit_evidence():
    world, selves, wal, events = _fixture()
    world = replace(world, event_coverage_through_tick=109)
    out = assess_reconstruction(world, selves, wal, events)
    assert out.verdict is RecoveryVerdict.HOLD_PHYSICAL_RECONCILIATION


def test_source_qualified_join_is_not_native_or_paper_authentication():
    world, selves, wal, events = _fixture()
    with pytest.raises(RecoveryContractError):
        replace(events[0], native_source_ref=None)
    # Even correct typed refs are only an offline causal join candidate.
    out = assess_reconstruction(world, selves, wal, events)
    assert out.verdict is RecoveryVerdict.CANDIDATE_REOBSERVE
    assert out.action_issue_authorized is False


def test_two_self_claim_same_parent_action_is_not_one_physical_owner():
    world, (a, b), wal, events = _fixture()
    b = replace(b, checkpoint_id="B-C106", tick=106, claims=(
        ActionClaim("attack-A", "entity:3", "zombie-uuid-Z1", 106),
    ))
    out = assess_reconstruction(world, (a, b), wal, events)
    assert out.verdict is RecoveryVerdict.HOLD_PHYSICAL_RECONCILIATION


def test_duplicated_action_id_across_self_wals_is_refused():
    world, selves, wal, events = _fixture()
    other = replace(wal[0], self_id="B")
    with pytest.raises(RecoveryContractError, match="reused"):
        assess_reconstruction(world, selves, (*wal, other), events)


def test_world_action_from_current_self_without_wal_is_hold():
    world, selves, wal, events = _fixture()
    out = assess_reconstruction(world, selves, (), events)
    assert out.verdict is RecoveryVerdict.HOLD_PHYSICAL_RECONCILIATION


def test_event_from_external_actor_does_not_require_self_wal():
    world, selves, wal, events = _fixture()
    environment = WorldEvent(
        "server-external", world.world_id, world.branch_id, 109, "external-actor",
        "external-action", "external-session", "zombie-uuid-Z3", False,
        "other-native:2", "world:server:109", "entity:7",
    )
    out = assess_reconstruction(world, selves, wal, (*events, environment))
    assert out.verdict is RecoveryVerdict.CANDIDATE_REOBSERVE


def test_wal_projection_restores_owned_empty_history_without_mutation(tmp_path):
    path = tmp_path / "physical-wal.json"
    original = PhysicalActionJournal.create(path, self_id="A")
    digest = original.digest
    restored = PhysicalActionJournal.restore(path, self_id="A")
    assert project_physical_journal(restored, self_id="A") == ()
    assert restored.digest == digest
    with pytest.raises(RecoveryContractError, match="foreign"):
        project_physical_journal(restored, self_id="B")
    with pytest.raises(RecoveryContractError):
        project_physical_journal(object(), self_id="A")


def test_many_fault_combinations_never_authorize_issue_even_if_ticks_fit():
    # Fault toggles are a stress-test grid, *not* physical failure rates.
    base = _fixture()
    n = safe = 0
    for future, fork, torn, lost_wal, prepared, missing_event, missing_send in product(
        (False, True), repeat=7
    ):
        world, selves, wal, events = base
        a, b = selves
        if future:
            a = replace(a, checkpoint_id="A-C111", tick=111)
        if fork:
            world = replace(world, branch_id="other-historical-fork")
        if torn:
            world = replace(world, atomic_capture_attested=False)
        if lost_wal:
            wal = ()
        elif prepared:
            wal = (replace(wal[0], status=WalState.PREPARED_UNRESOLVED),)
        if missing_event:
            events = ()
        if missing_send:
            b = replace(b, checkpoint_id="B-C105", tick=105,
                        received=(ReceivedMessage("A", "not-sent", 104),))
        verdict = assess_reconstruction(world, (a, b), wal, events)
        assert verdict.action_issue_authorized is False
        if verdict.verdict is RecoveryVerdict.CANDIDATE_REOBSERVE:
            safe += 1
            assert not any((
                future, fork, torn, lost_wal, prepared, missing_event, missing_send
            ))
        n += 1
    assert (n, safe) == (128, 1)


def test_stale_native_entity_id_to_world_uuid_join_holds():
    world, selves, wal, events = _fixture()
    out = assess_reconstruction(world, selves, wal, (
        replace(events[0], native_target_ref="entity:77"),))
    assert out.verdict is RecoveryVerdict.HOLD_PHYSICAL_RECONCILIATION


def test_undeclared_uuid_mapping_cannot_recover_attack_claim():
    world, (a, b), wal, events = _fixture()
    a = replace(a, claims=(
        ActionClaim("attack-A", "entity:3", None, 105),
    ))
    out = assess_reconstruction(world, (a, b), wal, events)
    assert out.verdict is RecoveryVerdict.HOLD_PHYSICAL_RECONCILIATION
    assert any("ID to UUID join" in msg for msg in out.physical_blockers)


def test_world_event_without_native_target_ref_cannot_claim_source_join():
    _, _, _, events = _fixture()
    with pytest.raises(RecoveryContractError):
        replace(events[0], native_target_ref=None)
