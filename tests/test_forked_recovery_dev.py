"""#858 P0-C: actual file checkpoint pipeline + synthetic Self/ticket history.

Fixtures model filesystem files and typed DEV receipts only; NO real
Minecraft, Paper log authenticity, or autonomous simultaneous Self B.
"""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from relay_self.attack_world_join_dev import (
    AttackWalEvidence,
    NativeIdentityWitness,
    ServerAttackTicket,
    ServerDamageEvent,
    ServerDeathEvent,
)
from relay_self.causal_recovery import (
    ActionClaim,
    BeliefRecord,
    ReceivedMessage,
    SelfCheckpoint,
    SentMessage,
    WalReceipt,
    WalState,
)
from relay_self.forked_recovery_dev import (
    DerivedCognitiveCut,
    ForkRecoveryDevError,
    ForkRecoveryDevStatus,
    FreshForkObservation,
    SourceWorldCutWitness,
    joined_action_effect_dev,
    load_derived_cognitive_cut_dev,
    prepare_forked_recovery_dev,
    reproject_present_from_fresh_world_dev,
    write_derived_cognitive_cut_dev,
)
from relay_self.world_checkpoint_dev import (
    WorldCheckpointError,
    capture_stopped_world,
    restore_world_to_new_branch,
)

WORLD = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
ACTOR = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ZOMBIE = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
BRANCH = "history-alpha"
SESSION = "native-session-before"
ACTION = "attack-A"


def _history():
    w = AttackWalEvidence(
        "A", ACTION, SESSION, "entity:47", 55, 45, 57, 56, 58, "a" * 64,
    )
    n = NativeIdentityWitness(
        "A", ACTION, SESSION, "native:55", 55, 47, 45, ZOMBIE, ACTOR,
    )
    t = ServerAttackTicket(
        WORLD, BRANCH, ACTION, SESSION, "nonce-A", ACTOR,
        ZOMBIE, 948, "paper:ack948",
    )
    d = ServerDamageEvent(
        WORLD, BRANCH, "damage-1", 948, ZOMBIE, ACTOR,
        "ENTITY_ATTACK", 2.0, 0.0, "paper:damage-1", "nonce-A",
    )
    death = ServerDeathEvent(
        WORLD, BRANCH, "death-2", 948, ZOMBIE, ACTOR,
        "damage-1", "paper:death-2",
    )
    effect = joined_action_effect_dev(w, n, ticket=t, damage=d, death=death)
    return w, n, t, d, death, effect


def _self_cuts():
    a = DerivedCognitiveCut(
        SelfCheckpoint(
            checkpoint_id="C105", self_id="A", world_id=WORLD,
            branch_id=BRANCH, tick=105,
            claims=(ActionClaim(ACTION, "entity:47", ZOMBIE, 105),),
            beliefs=(BeliefRecord(ZOMBIE, 105, False, "paper:death-2"),),
        ), "original:Paper+native+A", "OBSERVATION_DERIVED",
    )
    b = DerivedCognitiveCut(
        SelfCheckpoint(
            checkpoint_id="C98", self_id="B", world_id=WORLD,
            branch_id=BRANCH, tick=98,
            beliefs=(BeliefRecord(ZOMBIE, 98, True, "pre-attack:probe"),),
        ), "synthetic:B-from-prior-percept-not-real-autonomous", "SIMULATED",
    )
    return a, b


def _make_checkpoint(tmp_path, label, *, alive, included):
    source = tmp_path / f"source-world-{label}"
    source.mkdir()
    (source / "level.dat").write_bytes(f"mock-nbt-{label}".encode())
    region = source / "entities"
    region.mkdir()
    (region / "r.0.0.mca").write_bytes(
        b"Zombie-alive-with-uuid" if alive else b"Zombie-dead-no-entity",
    )
    (source / "playerdata").mkdir()
    (source / "playerdata/player.dat").write_bytes(b"7 emerald")
    archive = tmp_path / f"archive-{label}"
    capture_stopped_world(
        source, archive, world_id=WORLD, branch_id=BRANCH,
        checkpoint_id=label, logical_tick=100 if label == "W100" else 110,
        tick_source_ref="DEV:model-not-server-clock",
        stopped_server_ref="DEV:model-no-server-run",
    )
    restored = tmp_path / f"restored-{label}"
    receipt = restore_world_to_new_branch(
        archive, restored, restore_id=f"restore-{label}",
    )
    cut = SourceWorldCutWitness(
        WORLD, BRANCH, label, ZOMBIE, alive,
        ("death-2",) if included else (),
        f"DEV:source-readback-{label}",
    )
    return archive, restored, receipt, cut


def _inputs(tmp_path, label="W110"):
    archive, restored, receipt, cut = _make_checkpoint(
        tmp_path, label, alive=label == "W100", included=label == "W110",
    )
    a, b = _self_cuts()
    wal = (WalReceipt(
        "A", ACTION, SESSION, "entity:47",
        WalState.NATIVE_ATTACK_HURT_OBSERVED, "a" * 64,
    ),)
    effect = _history()[-1]
    return archive, restored, receipt, cut, (a, b), wal, (effect,)


def _prepare(args):
    archive, restored, _receipt, cut, selves, wal, effects = args
    return prepare_forked_recovery_dev(
        archive, restored, cut=cut, selves=selves, wal=wal, effects=effects,
    )


def _fresh(prepared, alive, *, session="fresh-native-session", native_id=2):
    return FreshForkObservation(
        WORLD, prepared.new_branch_id, session, ZOMBIE, alive,
        f"new-native:{session}:probe-after-restore",
        native_id if alive else None,
    )


def test_w110_with_a105_b98_keeps_b_false_belief_as_memory(tmp_path):
    case = _inputs(tmp_path, "W110")
    plan = _prepare(case)
    assert plan.status is ForkRecoveryDevStatus.NEEDS_FRESH_WORLD_BODY
    assert plan.included_action_ids == (ACTION,)
    assert plan.remembered_postcut_action_ids == ()
    assert len(plan.retained_beliefs) == 2
    assert "A:" + ZOMBIE + ":105:DEAD" in plan.retained_beliefs
    assert "B:" + ZOMBIE + ":98:ALIVE" in plan.retained_beliefs
    assert plan.physical_action_issue_authorized is False
    after = reproject_present_from_fresh_world_dev(
        plan, _fresh(plan, False),
    )
    assert after.status is ForkRecoveryDevStatus.PRESENT_REPROJECTED_DEV
    assert after.present_target_alive is False
    assert after.physical_action_issue_authorized is False
    assert after.self_owner_restored is False


def test_w100_rollback_keeps_a105_dead_memory_but_present_alive(tmp_path):
    case = _inputs(tmp_path, "W100")
    plan = _prepare(case)
    assert plan.status is ForkRecoveryDevStatus.NEEDS_FRESH_WORLD_BODY
    assert plan.included_action_ids == ()
    assert plan.remembered_postcut_action_ids == (ACTION,)
    assert "A:" + ZOMBIE + ":105:DEAD" in plan.retained_beliefs
    after = reproject_present_from_fresh_world_dev(
        plan, _fresh(plan, True, native_id=47),
    )
    assert after.status is ForkRecoveryDevStatus.PRESENT_REPROJECTED_DEV
    assert after.present_target_alive is True
    assert after.remembered_postcut_action_ids == (ACTION,)
    assert after.physical_action_issue_authorized is False


def test_distinct_forks_dont_promote_original_event_as_replayed(tmp_path):
    w100 = _inputs(tmp_path, "W100")
    w110 = _inputs(tmp_path, "W110")
    p100 = _prepare(w100)
    p110 = _prepare(w110)
    assert p100.new_branch_id != p110.new_branch_id
    assert p100.source_branch_id == p110.source_branch_id == BRANCH
    assert p110.included_action_ids == (ACTION,)
    assert p100.included_action_ids == ()
    assert p100.physical_action_issue_authorized is False


def test_unknown_worldbody_cannot_claim_zombie_absence(tmp_path):
    plan = _prepare(_inputs(tmp_path, "W110"))
    after = reproject_present_from_fresh_world_dev(
        plan, _fresh(plan, None),
    )
    assert after.status is ForkRecoveryDevStatus.NEEDS_FRESH_WORLD_BODY
    assert after.present_target_alive is None


@pytest.mark.parametrize("bad", ["foreign-branch", "foreign-world", "wrong-checkpoint"])
def test_cut_with_wrong_source_archive_identity_rejected(tmp_path, bad):
    case = list(_inputs(tmp_path))
    cut = case[3]
    if bad == "foreign-branch":
        cut = replace(cut, source_branch_id="different-branch")
    elif bad == "foreign-world":
        cut = replace(cut, world_id="different-world")
    else:
        cut = replace(cut, checkpoint_id="W999")
    case[3] = cut
    assert _prepare(case).status is ForkRecoveryDevStatus.REJECT_WORLD_CUT


def test_world_w110_alive_conflicts_with_included_lethal_event(tmp_path):
    case = list(_inputs(tmp_path))
    case[3] = replace(case[3], target_alive_at_capture=True)
    assert _prepare(case).status is ForkRecoveryDevStatus.REJECT_WORLD_CUT


def test_unknown_cut_event_id_holds(tmp_path):
    case = list(_inputs(tmp_path))
    case[3] = replace(case[3], included_effect_event_ids=("unknown-death",))
    assert _prepare(case).status is ForkRecoveryDevStatus.HOLD_PHYSICAL_RECONCILIATION


@pytest.mark.parametrize("failure", [
    "missing-WAL", "PREPARED", "other-self", "wrong-target",
    "missing-effect", "actor-not-self",
])
def test_missing_or_unresolved_source_action_never_reissues(tmp_path, failure):
    case = list(_inputs(tmp_path))
    if failure == "missing-WAL":
        case[5] = ()
    elif failure == "PREPARED":
        case[5] = (replace(case[5][0], status=WalState.PREPARED_UNRESOLVED),)
    elif failure == "other-self":
        case[5] = (replace(case[5][0], self_id="B"),)
    elif failure == "wrong-target":
        case[5] = (replace(case[5][0], native_target_ref="entity:2"),)
    elif failure == "missing-effect":
        case[6] = ()
    else:
        case[6] = (replace(case[6][0], actor_self_id="B"),)
    out = _prepare(case)
    assert out.status is ForkRecoveryDevStatus.HOLD_PHYSICAL_RECONCILIATION
    assert out.physical_action_issue_authorized is False


def test_other_wal_digest_cannot_be_joined_into_source_event(tmp_path):
    case = list(_inputs(tmp_path))
    case[5] = (replace(case[5][0], journal_sha256="b" * 64),)
    result = _prepare(case)
    assert result.status is ForkRecoveryDevStatus.HOLD_PHYSICAL_RECONCILIATION
    assert result.physical_action_issue_authorized is False


def test_eat_terminal_cannot_masquerade_as_attack_source_wal(tmp_path):
    case = list(_inputs(tmp_path))
    case[5] = (replace(case[5][0], status=WalState.NATIVE_EAT_OUTCOME),)
    result = _prepare(case)
    assert result.status is ForkRecoveryDevStatus.HOLD_PHYSICAL_RECONCILIATION
    assert result.physical_action_issue_authorized is False


def test_derived_a_and_b_cognitive_cuts_are_independent_files(tmp_path):
    a, b = _self_cuts()
    path_a = tmp_path / "Self-A-C105.json"
    path_b = tmp_path / "Self-B-C98.json"
    write_derived_cognitive_cut_dev(path_a, a)
    write_derived_cognitive_cut_dev(path_b, b)
    assert load_derived_cognitive_cut_dev(path_a) == a
    assert load_derived_cognitive_cut_dev(path_b) == b
    assert path_a.read_bytes() != path_b.read_bytes()
    with pytest.raises(ForkRecoveryDevError):
        write_derived_cognitive_cut_dev(path_a, a)
    assert load_derived_cognitive_cut_dev(path_b).checkpoint.self_id == "B"


def test_extra_or_invalid_cognitive_checkpoint_does_not_get_owner_authority(tmp_path):
    a, _ = _self_cuts()
    path = tmp_path / "Self-A.json"
    write_derived_cognitive_cut_dev(path, a)
    payload = json.loads(path.read_bytes())
    payload["checkpoint"]["branch_id"] = "foreign"
    path.write_text(json.dumps(payload))
    restored = load_derived_cognitive_cut_dev(path)
    assert restored.checkpoint.branch_id == "foreign"
    case = list(_inputs(tmp_path, "W110"))
    case[4] = (restored, case[4][1])
    assert _prepare(case).status is ForkRecoveryDevStatus.REJECT_WORLD_CUT
    payload["fake_physical_grant"] = True
    path.write_text(json.dumps(payload))
    with pytest.raises(ForkRecoveryDevError):
        load_derived_cognitive_cut_dev(path)


def test_fresh_session_must_not_be_original_native_session(tmp_path):
    plan = _prepare(_inputs(tmp_path, "W100"))
    res = reproject_present_from_fresh_world_dev(
        plan, _fresh(plan, True, session=SESSION, native_id=47),
    )
    assert res.status is ForkRecoveryDevStatus.HOLD_PHYSICAL_RECONCILIATION
    assert res.physical_action_issue_authorized is False


def test_fresh_world_observation_from_other_fork_does_not_reproject(tmp_path):
    plan = _prepare(_inputs(tmp_path, "W110"))
    fresh = replace(_fresh(plan, False), new_branch_id="fork-unrelated")
    result = reproject_present_from_fresh_world_dev(
        plan, fresh,
    )
    assert result.status is ForkRecoveryDevStatus.HOLD_PHYSICAL_RECONCILIATION


def test_fresh_observation_disagrees_with_saved_checkpoint_holds(tmp_path):
    plan = _prepare(_inputs(tmp_path, "W110"))
    out = reproject_present_from_fresh_world_dev(
        plan, _fresh(plan, True),
    )
    assert out.status is ForkRecoveryDevStatus.HOLD_PHYSICAL_RECONCILIATION


def test_missing_message_send_from_self_b_causal_cut_holds(tmp_path):
    case = list(_inputs(tmp_path))
    a, b = case[4]
    a = replace(a, checkpoint=replace(
        a.checkpoint, received=(ReceivedMessage("B", "m1", 104),),
    ))
    case[4] = (a, b)
    assert _prepare(case).status is ForkRecoveryDevStatus.HOLD_PHYSICAL_RECONCILIATION
    b = replace(b, checkpoint=replace(
        b.checkpoint, sent=(SentMessage("m1", 97),),
    ))
    case[4] = (a, b)
    assert _prepare(case).status is ForkRecoveryDevStatus.NEEDS_FRESH_WORLD_BODY


def test_archive_mutation_stops_prelaunch_reconstruction(tmp_path):
    case = _inputs(tmp_path)
    (case[0] / "world" / "level.dat").write_bytes(b"changed")
    with pytest.raises(WorldCheckpointError):
        _prepare(case)


def test_paper_ticket_death_must_actually_be_linked_not_implied():
    w, n, t, d, death, _effect = _history()
    with pytest.raises(ForkRecoveryDevError):
        joined_action_effect_dev(
            w, n, ticket=t, damage=d,
            death=replace(death, causing_damage_event_id=None),
        )


def test_unproven_source_death_cannot_be_generated_from_damage_only():
    w, n, t, d, _death, _effect = _history()
    out = joined_action_effect_dev(w, n, ticket=t, damage=replace(
        d, health_after=0.0,
    ))
    assert out.target_alive_after is None
    assert out.event_id == "damage-1"



def test_two_phase_cli_postlaunch_only_needs_saved_plan_and_fresh_source(tmp_path):
    """Postlaunch never re-verifies a World directory that Minecraft may mutate."""
    from dataclasses import asdict

    from experiments.audit_forked_recovery_dev import _write_new, postlaunch

    plan = _prepare(_inputs(tmp_path, "W100"))
    saved = tmp_path / "prelaunch.json"
    _write_new(saved, plan)
    fresh = _fresh(plan, True, session="new-live-world-session", native_id=2)
    source = tmp_path / "fresh.json"
    source.write_text(json.dumps(asdict(fresh)))
    target = tmp_path / "postlaunch.json"
    outcome = postlaunch(saved, source, target)
    assert outcome.status is ForkRecoveryDevStatus.PRESENT_REPROJECTED_DEV
    assert target.is_file()
    assert outcome.physical_action_issue_authorized is False
    assert outcome.remembered_postcut_action_ids == (ACTION,)
    assert json.loads(target.read_text())["decision"]["self_owner_restored"] is False


def test_cli_prelaunch_real_empty_owned_wal_does_not_fabricate_action_effect(tmp_path):
    """An absent actual WAL Action must HOLD even with a narrative ticket record."""
    from dataclasses import asdict

    from experiments.audit_forked_recovery_dev import prelaunch
    from relay_self.physical_action_journal import PhysicalActionJournal

    archive, restored, _receipt, cut, selves, _wal, _effects = _inputs(tmp_path, "W110")
    cutfile = tmp_path / "source-cut.json"
    cutfile.write_text(json.dumps(asdict(cut)))
    selfpaths = []
    for c in selves:
        path = tmp_path / f"{c.checkpoint.self_id}-cut.json"
        write_derived_cognitive_cut_dev(path, c)
        selfpaths.append(path)
    walfile = tmp_path / "fresh-empty-real-wal.json"
    PhysicalActionJournal.create(walfile, self_id="A")
    eventfile = tmp_path / "ticket-events.json"
    eventfile.write_text(json.dumps({
        "self_id": "A", "action_id": ACTION, "world_id": WORLD,
        "branch_id": BRANCH, "native_identity": None,
        "server_attack_ticket": None, "server_damage_events": [],
        "server_death_events": [],
    }))
    outfile = tmp_path / "prelaunch-result.json"
    result = prelaunch(
        archive, restored, cutfile, selfpaths, walfile, eventfile, outfile,
    )
    assert result.status is ForkRecoveryDevStatus.HOLD_PHYSICAL_RECONCILIATION
    assert result.physical_action_issue_authorized is False
    assert outfile.exists()


def test_postlaunch_refuses_forged_authority_in_stored_prelaunch_plan(tmp_path):
    from experiments.audit_forked_recovery_dev import _write_new, postlaunch

    plan = _prepare(_inputs(tmp_path, "W100"))
    source = tmp_path / "prelaunch.json"
    _write_new(source, plan)
    body = json.loads(source.read_text())
    body["decision"]["physical_action_issue_authorized"] = True
    source.write_text(json.dumps(body))
    fresh = tmp_path / "fresh.json"
    fresh.write_text(json.dumps({
        "world_id": WORLD, "new_branch_id": plan.new_branch_id,
        "native_session_id": "new", "target_uuid": ZOMBIE,
        "observed_target_alive": True, "source_ref": "mineflayer:new",
        "runtime_target_entity_id": 2,
    }))
    with pytest.raises(ForkRecoveryDevError, match="cannot assert physical authority"):
        postlaunch(source, fresh, tmp_path / "should-not-exist.json")
    assert not (tmp_path / "should-not-exist.json").exists()



def test_mixing_world_checkpoint_from_another_world_with_p0b_event_rejected(tmp_path):
    """Prior P0-A and P0-B evidence from different Minecraft Worlds cannot be joined."""
    case = list(_inputs(tmp_path, "W110"))
    case[6] = (replace(
        case[6][0], world_id="a-different-real-world-uuid",
    ),)
    result = _prepare(case)
    assert result.status is ForkRecoveryDevStatus.REJECT_WORLD_CUT
    assert result.physical_action_issue_authorized is False


def test_mixing_self_b_from_foreign_world_rejected_even_if_belief_agrees(tmp_path):
    case = list(_inputs(tmp_path, "W100"))
    a, b = case[4]
    b = replace(b, checkpoint=replace(
        b.checkpoint, world_id="other-independent-world",
    ))
    case[4] = (a, b)
    out = _prepare(case)
    assert out.status is ForkRecoveryDevStatus.REJECT_WORLD_CUT
