"""#860 DEV World resident Self / World-only source invariants, no real Minecraft."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from relay_self.owned_paper_world_dev import OwnedPaperWorld, PaperTickReceipt
from relay_self.owned_paper_world_switch_dev import (
    OwnedPaperWorldSwitcher,
    WorldOwnershipSwitchError,
)
from relay_self.world_only_owned_checkpoint_dev import (
    WorldOnlyCheckpointError,
    WorldOnlyOwnedPaperCheckpoint,
    verify_world_only_generation,
)
from relay_self.world_resident_lifecycle_dev import (
    LogoutFenceEvidence,
    NativeLoginEvidence,
    Presence,
    ResidentLifecycleError,
    WorldInstallationEvidence,
    WorldLifetime,
    WorldOnlyQuiescenceEvidence,
    WorldResidentLifecycle,
)


def _fake_quiescence(life: WorldResidentLifecycle) -> WorldOnlyQuiescenceEvidence:
    """Simulated ORIGINAL issuer receipt; never evidence of real Paper safety."""
    return WorldOnlyQuiescenceEvidence(
        world_epoch=life.world.epoch,
        checked_self_ids=life.self_roster,
        source_ref="synthetic:original-issuer-retired",
        original_physical_issuer_closed=True,
        native_sessions_absent=True,
        no_unresolved_physical_actions=True,
        all_gpu_epochs_retired=True,
        pending_peer_messages_empty=True,
    )


def _names(count: int) -> tuple[str, ...]:
    return tuple(f"S{i:03d}" for i in range(count))


def _resident(count: int, *, epoch: int = 4):
    names = _names(count)
    world = WorldLifetime("world-alpha", "source", "paper-A", epoch, 100)
    life = WorldResidentLifecycle(
        world=world,
        persisted_self_refs={sid: f"retained:{sid}:C98" for sid in names},
    )
    return life, names


def _login(life: WorldResidentLifecycle, sid: str, *, native=None):
    ticket = life.begin_login(sid)
    evidence = NativeLoginEvidence(
        sid, ticket.login_seq, ticket.world.world_id, ticket.world.branch_id,
        ticket.world.paper_session_id, ticket.world.epoch,
        native or f"native-fresh-{sid}-{ticket.login_seq}",
        life.world.world_tick,
        f"native-probe:{sid}:{ticket.login_seq}",
        True, True, True, True, True,
    )
    return ticket, life.complete_login(ticket, evidence)


def _retire(life: WorldResidentLifecycle, sid: str, **overrides):
    view = life.view(sid)
    base = dict(
        self_id=sid, world_epoch=view.world_epoch,
        native_session_id=view.native_session_id,
        source_ref=f"canonical-issuer:{sid}",
        persisted_cognition_ref=f"retained:{sid}:C109",
        physical_issuer_revoked=True, no_physical_inflight=True,
        physical_wal_clear=True, native_terminated=True,
        stale_gpu_fenced=True, peer_transport_drained=True,
    )
    base.update(overrides)
    return LogoutFenceEvidence(**base)


@pytest.mark.parametrize("count", [2, 10, 100])
def test_individual_failure_keeps_all_other_self_online_and_world_ticking(count):
    life, names = _resident(count)
    for sid in names:
        _login(life, sid)
    assert not life.can_world_only_checkpoint()
    first = names[0]
    quarantined = life.fail_self(first)
    assert quarantined.status is Presence.QUARANTINED
    assert not life.can_world_only_checkpoint()
    assert all(life.view(sid).status is Presence.ONLINE for sid in names[1:])
    world = life.world_tick(
        paper_session_id="paper-A", tick=140,
        source_ref="owned-paper-tick:140",
    )
    assert world.world_tick == 140
    with pytest.raises(ResidentLifecycleError, match="offline"):
        life.begin_login(first)
    with pytest.raises(ResidentLifecycleError, match="safely offline"):
        life.begin_world_transition()
    retired = life.finish_logout(first, _retire(life, first))
    assert retired.status is Presence.OFFLINE
    assert retired.persisted_cognition_ref.endswith("C109")
    assert all(life.view(sid).status is Presence.ONLINE for sid in names[1:])
    for sid in names[1:]:
        life.begin_logout(sid)
        life.finish_logout(sid, _retire(life, sid))
    assert life.can_world_only_checkpoint()
    assert life.self_roster == names


@pytest.mark.parametrize("count", [0, 2, 10, 100])
def test_world_replacement_changes_branch_and_session_not_self_identity(count):
    life, names = _resident(count)
    before = life.world
    assert life.can_world_only_checkpoint()
    assert life.begin_world_transition() == before
    new = WorldLifetime("new-world", "new-branch", "paper-new", 5, 0)
    got = life.install_world(WorldInstallationEvidence(
        before, new, "owned-paper:new-world-integrity",
        True, True, True, True,
    ))
    assert got == new
    assert life.self_roster == names
    for sid in names:
        older = life.view(sid)
        assert older.persisted_cognition_ref == f"retained:{sid}:C98"
        assert older.worldbody_reobservation_required
        assert older.native_session_id is None
    life.world_tick(paper_session_id="paper-new", tick=8,
                    source_ref="paper-new:tick-8")
    for sid in names[:3]:
        ticket, joined = _login(life, sid)
        assert joined.status is Presence.ONLINE
        assert joined.last_observed_world is not None
        assert joined.last_observed_world.world_id == "new-world"
        assert joined.last_observed_world.world_tick == 8
        assert ticket.persisted_cognition_ref == f"retained:{sid}:C98"
        assert not joined.action_issue_authorized


def test_stale_login_ticket_and_old_worldbody_probes_never_authorize():
    life, names = _resident(2)
    ticket = life.begin_login(names[0])
    life.world_tick(paper_session_id="paper-A", tick=120,
                    source_ref="paper-source:120")
    old_clock = NativeLoginEvidence(
        names[0], ticket.login_seq, "world-alpha", "source",
        "paper-A", ticket.world.epoch, "native-unknown",
        110, "old-native-probe", True, True, True, True, True,
    )
    with pytest.raises(ResidentLifecycleError, match="login source"):
        life.complete_login(ticket, old_clock)
    altered = NativeLoginEvidence(
        names[0], ticket.login_seq, "world-alpha", "source",
        "paper-old", ticket.world.epoch, "native-unknown",
        120, "foreign-session", True, True, True, True, True,
    )
    with pytest.raises(ResidentLifecycleError, match="login source"):
        life.complete_login(ticket, altered)
    future = NativeLoginEvidence(
        names[0], ticket.login_seq, "world-alpha", "source",
        "paper-A", ticket.world.epoch, "native-valid",
        121, "current-native", True, True, True, True, True,
        action_issue_authorized=True,
    )
    with pytest.raises(ResidentLifecycleError, match="login source"):
        life.complete_login(ticket, future)
    assert life.view(names[0]).status is Presence.LOGIN_PENDING


@pytest.mark.parametrize(
    "bad",
    [
        {"physical_issuer_revoked": False},
        {"no_physical_inflight": False},
        {"physical_wal_clear": False},
        {"native_terminated": False},
        {"stale_gpu_fenced": False},
        {"peer_transport_drained": False},
        {"action_issue_authorized": True},
        {"world_epoch": 3},
        {"native_session_id": "old-native"},
    ],
)
def test_failed_logout_must_quarantine_one_self_only(bad):
    life, names = _resident(2)
    _login(life, names[0])
    _login(life, names[1])
    life.begin_logout(names[0])
    with pytest.raises(ResidentLifecycleError, match="quarantine"):
        life.finish_logout(names[0], _retire(life, names[0], **bad))
    assert life.view(names[0]).status is Presence.QUARANTINED
    assert life.view(names[1]).status is Presence.ONLINE
    assert life.world_tick(
        paper_session_id="paper-A", tick=130, source_ref="paper-source:130",
    ).world_tick == 130
    with pytest.raises(ResidentLifecycleError):
        life.begin_world_transition()


def test_wrong_world_swap_sources_poison_world_but_preserve_self_history():
    life, names = _resident(2)
    original = life.world
    life.begin_world_transition()
    bad = WorldInstallationEvidence(
        original,
        WorldLifetime("new-world", "source", original.paper_session_id, 5, 0),
        "forged-new-paper", True, True, True, True,
    )
    with pytest.raises(ResidentLifecycleError, match="HOLD"):
        life.install_world(bad)
    assert life.world_held
    assert life.world == original
    assert life.view(names[0]).persisted_cognition_ref == "retained:S000:C98"
    with pytest.raises(ResidentLifecycleError):
        life.world_tick(paper_session_id="paper-A", tick=130,
                        source_ref="paper-source")
    with pytest.raises(ResidentLifecycleError):
        life.begin_login(names[0])


def _fake_paper(
    root: Path, *, good_save=True, companions=False,
    world_id="world-alpha", branch_id="source",
):
    server = root / "server"
    server.mkdir()
    world = server / "world"
    world.mkdir()
    (world / "level.dat").write_bytes(b"FAKE-PAPER-level")
    (world / "region").mkdir()
    (world / "region" / "r.0.0.mca").write_bytes(b"fake-world-tick")
    if companions:
        for dimension in ("world_nether", "world_the_end"):
            other = server / dimension
            other.mkdir()
            (other / "region").mkdir()
            (other / "region" / "r.0.0.mca").write_bytes(
                b"fake-companion-world"
            )
    evidence = root / "evidence"
    evidence.mkdir()
    script = root / "fake-paper.py"
    script.write_text(
        "import sys\n"
        "print('Done (0.1s)', flush=True)\n"
        "for line in sys.stdin:\n"
        "    if line.strip() == 'save-all flush':\n"
        + ("        print('Saved the game', flush=True)\n"
           if good_save else "        pass\n")
        + "    if line.strip() == 'stop':\n"
        "        print('Stopping server', flush=True)\n"
        "        sys.exit(0)\n",
        encoding="utf-8",
    )
    tick_counter = [0]

    def tick_source(sid):
        tick_counter[0] += 1
        return PaperTickReceipt(sid, 100 + tick_counter[0] * 10,
                                "fake-paper:tick:" + str(tick_counter[0]))

    adapter = OwnedPaperWorld(
        server_dir=server, world_dir=world, evidence_dir=evidence,
        command=(sys.executable, "-u", str(script)),
        world_id=world_id, branch_id=branch_id,
        tick_readback=tick_source, timeout_seconds=2.0,
    )
    return adapter


@pytest.mark.parametrize("count", [0, 2, 100])
@pytest.mark.parametrize("companions", [False, True])
def test_world_only_owned_paper_two_cycles_without_any_self_snapshot(
    tmp_path, count, companions,
):
    adapter = _fake_paper(tmp_path, companions=companions)
    current_session = adapter.start_owned()
    life = WorldResidentLifecycle(
        world=WorldLifetime("world-alpha", "source", current_session, 0, 0),
        persisted_self_refs={s: "canonical-cognition:" + s for s in _names(count)},
    )
    store = tmp_path / "store"
    store.mkdir()
    runner = WorldOnlyOwnedPaperCheckpoint(
        lifecycle=life, owned_paper=adapter, store=store,
        issuer_quiescence=lambda: _fake_quiescence(life),
    )
    try:
        first = runner.cycle()
        assert first.old_world.paper_session_id == current_session
        assert first.saved_world_tick == 110
        assert first.new_world.epoch == 1
        assert first.new_world.paper_session_id != current_session
        assert verify_world_only_generation(first.checkpoint_dir)["owner_self_count"] == 0
        assert not (first.checkpoint_dir / "selves").exists()
        assert life.self_roster == _names(count)
        for sid in life.self_roster:
            assert life.view(sid).persisted_cognition_ref == "canonical-cognition:" + sid
        second = runner.cycle()
        assert second.new_world.epoch == 2
        assert second.saved_world_tick == 120
        assert life.can_world_only_checkpoint()
        assert len(list(store.glob("world-only-*/WORLD_ONLY_COMMITTED.json"))) == 2
        if companions:
            assert set(verify_world_only_generation(second.checkpoint_dir)["paper_dimensions"]) == {
                "world_nether", "world_the_end",
            }
    finally:
        if adapter.owned_session_id is not None and not adapter.held_uncertain:
            adapter.stop_and_save()


def test_world_only_cannot_checkpoint_while_any_self_online(tmp_path):
    adapter = _fake_paper(tmp_path)
    current = adapter.start_owned()
    life = WorldResidentLifecycle(
        world=WorldLifetime("world-alpha", "source", current, 0, 0),
        persisted_self_refs={"A": "retained-A", "B": "retained-B"},
    )
    _login(life, "A")
    store = tmp_path / "store"
    store.mkdir()
    runner = WorldOnlyOwnedPaperCheckpoint(
        lifecycle=life, owned_paper=adapter, store=store,
        issuer_quiescence=lambda: _fake_quiescence(life),
    )
    try:
        with pytest.raises(WorldOnlyCheckpointError, match="offline"):
            runner.cycle()
        assert adapter.owned_session_id == current
        assert not list(store.iterdir())
    finally:
        adapter.stop_and_save()


def test_world_only_corrupted_commit_cannot_verify(tmp_path):
    adapter = _fake_paper(tmp_path)
    session = adapter.start_owned()
    life = WorldResidentLifecycle(
        world=WorldLifetime("world-alpha", "source", session, 0, 0),
        persisted_self_refs={},
    )
    store = tmp_path / "store"
    store.mkdir()
    runner = WorldOnlyOwnedPaperCheckpoint(
        lifecycle=life, owned_paper=adapter, store=store,
        issuer_quiescence=lambda: _fake_quiescence(life),
    )
    try:
        result = runner.cycle()
        assert verify_world_only_generation(result.checkpoint_dir)["declared_tick"] == 110
        marker = result.checkpoint_dir / "WORLD_ONLY_COMMITTED.json"
        body = json.loads(marker.read_bytes())
        body["owner_self_count"] = 1
        marker.write_text(json.dumps(body), encoding="utf-8")
        with pytest.raises(WorldOnlyCheckpointError, match="schema"):
            verify_world_only_generation(result.checkpoint_dir)
    finally:
        if adapter.owned_session_id is not None:
            adapter.stop_and_save()


def test_world_only_failed_owned_paper_flush_globally_holds_no_false_commit(tmp_path):
    adapter = _fake_paper(tmp_path, good_save=False)
    session = adapter.start_owned()
    life = WorldResidentLifecycle(
        world=WorldLifetime("world-alpha", "source", session, 0, 0),
        persisted_self_refs={"A": "retained-A"},
    )
    store = tmp_path / "store"
    store.mkdir()
    runner = WorldOnlyOwnedPaperCheckpoint(
        lifecycle=life, owned_paper=adapter, store=store,
        issuer_quiescence=lambda: _fake_quiescence(life),
    )
    with pytest.raises(Exception, match="flush completion"):
        runner.cycle()
    assert runner.held_after_failure and life.world_held
    assert not list(store.iterdir())
    assert life.view("A").status is Presence.OFFLINE
    assert adapter.held_uncertain


def test_old_paper_tick_after_world_swap_is_not_a_new_world_event():
    life, _ = _resident(0)
    old = life.begin_world_transition()
    life.install_world(WorldInstallationEvidence(
        old, WorldLifetime("other", "branch", "new-owned", 5, 0),
        "Paper-new-session", True, True, True, True,
    ))
    with pytest.raises(ResidentLifecycleError, match="foreign"):
        life.world_tick(paper_session_id="paper-A", tick=99999,
                        source_ref="stale-session")
    assert life.world.world_tick == 0



def _prepared_world_swap(tmp_path: Path, *, candidate_companions=True):
    """Two separately owned OS fake-Paper roots; NEW must be stopped & pinned."""
    old_dir = tmp_path / "old"
    new_dir = tmp_path / "new"
    old_dir.mkdir()
    new_dir.mkdir()
    old = _fake_paper(old_dir)
    old_session = old.start_owned()
    candidate = _fake_paper(
        new_dir, world_id="world-beta", branch_id="new-branch",
        companions=candidate_companions,
    )
    candidate_session = candidate.start_owned()
    candidate_life = WorldResidentLifecycle(
        world=WorldLifetime(
            "world-beta", "new-branch", candidate_session, 0, 0,
        ),
        persisted_self_refs={},
    )
    store = new_dir / "candidate-store"
    store.mkdir()
    checkpoint = WorldOnlyOwnedPaperCheckpoint(
        lifecycle=candidate_life, owned_paper=candidate, store=store,
        issuer_quiescence=lambda: _fake_quiescence(candidate_life),
    ).cycle()
    candidate.stop_and_save()  # Re-check candidate source as STOPPED bytes.
    pin = hashlib.sha256(
        (checkpoint.checkpoint_dir / "WORLD_ONLY_COMMITTED.json").read_bytes()
    ).hexdigest()
    old_life = WorldResidentLifecycle(
        world=WorldLifetime(
            "world-alpha", "source", old_session, 0, 0,
        ),
        persisted_self_refs={"A": "retained:A", "B": "retained:B"},
    )
    switcher = OwnedPaperWorldSwitcher(
        lifecycle=old_life, previous_paper=old,
        candidate_paper=candidate,
        issuer_quiescence=lambda: _fake_quiescence(old_life),
    )
    return old_life, switcher, old, candidate, checkpoint.checkpoint_dir, pin


@pytest.mark.parametrize("companions", [False, True])
def test_switch_from_owned_old_paper_to_pinned_different_world(
    tmp_path, companions,
):
    life, switcher, old, new, candidate_archive, pin = _prepared_world_swap(
        tmp_path, candidate_companions=companions,
    )
    first_session = life.world.paper_session_id
    result = switcher.switch_to_preverified_world(
        candidate_generation=candidate_archive,
        expected_commit_sha256=pin,
    )
    try:
        assert result.from_world.world_id == "world-alpha"
        assert result.to_world.world_id == "world-beta"
        assert result.to_world.branch_id == "new-branch"
        assert result.to_world.epoch == 1
        assert result.to_world.paper_session_id != first_session
        assert result.to_world.paper_session_id == new.owned_session_id
        assert old.owned_session_id is None
        assert result.new_paper_readback_ref.startswith("fake-paper")
        assert not result.previous_self_issued_actions_replayed
        assert not result.body_state_transferred
        assert not result.self_cognition_rewritten
        for sid in ("A", "B"):
            assert life.view(sid).persisted_cognition_ref == f"retained:{sid}"
            assert life.view(sid).status is Presence.OFFLINE
            assert life.view(sid).worldbody_reobservation_required
        # Different World tick baseline is not an old self's observation.
        with pytest.raises(ResidentLifecycleError, match="foreign"):
            life.world_tick(paper_session_id=first_session, tick=99999,
                            source_ref="old-paper")
        _, login = _login(life, "A")
        assert login.status is Presence.ONLINE
        assert login.last_observed_world is not None
        assert login.last_observed_world.world_id == "world-beta"
    finally:
        if new.owned_session_id is not None:
            new.stop_and_save()


def test_world_candidate_wrong_external_pin_cannot_stop_previous_world(tmp_path):
    life, switcher, old, new, archive, pin = _prepared_world_swap(tmp_path)
    try:
        with pytest.raises(WorldOwnershipSwitchError, match="pin mismatch"):
            switcher.switch_to_preverified_world(
                candidate_generation=archive,
                expected_commit_sha256="0" * 64 if pin != "0" * 64 else "1" * 64,
            )
        assert old.owned_session_id == life.world.paper_session_id
        assert not life.world_held
        assert not switcher.held_after_failure
    finally:
        old.stop_and_save()


def test_world_candidate_mutated_region_refused_before_old_paper_stop(tmp_path):
    life, switcher, old, new, archive, pin = _prepared_world_swap(tmp_path)
    try:
        (new.world_dir / "region" / "r.0.0.mca").write_bytes(b"tampered")
        with pytest.raises(WorldOwnershipSwitchError, match="files differ"):
            switcher.switch_to_preverified_world(
                candidate_generation=archive, expected_commit_sha256=pin,
            )
        assert old.owned_session_id == life.world.paper_session_id
        assert not life.world_held
    finally:
        old.stop_and_save()


@pytest.mark.parametrize("state", ["online", "quarantine"])
def test_world_swap_refused_with_active_or_unresolved_self(tmp_path, state):
    life, switcher, old, new, archive, pin = _prepared_world_swap(tmp_path)
    _login(life, "A")
    if state == "quarantine":
        life.fail_self("A")
    try:
        with pytest.raises(WorldOwnershipSwitchError, match="online roster"):
            switcher.switch_to_preverified_world(
                candidate_generation=archive, expected_commit_sha256=pin,
            )
        assert old.owned_session_id == life.world.paper_session_id
    finally:
        old.stop_and_save()



@pytest.mark.parametrize("failure", ["open_issuer", "stale_epoch", "pending_action"])
def test_world_only_requires_original_issuer_proof_not_presence_only(
    tmp_path, failure,
):
    adapter = _fake_paper(tmp_path)
    session = adapter.start_owned()
    life = WorldResidentLifecycle(
        world=WorldLifetime("world-alpha", "source", session, 0, 0),
        persisted_self_refs={"A": "retained-A"},
    )
    good = _fake_quiescence(life)
    changes = {
        "open_issuer": {"original_physical_issuer_closed": False},
        "stale_epoch": {"world_epoch": 123},
        "pending_action": {"no_unresolved_physical_actions": False},
    }
    from dataclasses import replace
    fake = replace(good, **changes[failure])
    store = tmp_path / "store"
    store.mkdir()
    runner = WorldOnlyOwnedPaperCheckpoint(
        lifecycle=life, owned_paper=adapter, store=store,
        issuer_quiescence=lambda: fake,
    )
    try:
        with pytest.raises(ResidentLifecycleError, match="issuer retirement"):
            runner.cycle()
        assert adapter.owned_session_id == session
        assert not life.world_held
        assert not list(store.iterdir())
    finally:
        adapter.stop_and_save()


def test_world_swap_presence_only_cannot_override_live_original_issuer(tmp_path):
    from dataclasses import replace

    life, switcher, old, new, archive, pin = _prepared_world_swap(tmp_path)
    claimed = replace(
        _fake_quiescence(life),
        native_sessions_absent=False,
    )
    switcher.issuer_quiescence = lambda: claimed
    try:
        with pytest.raises(ResidentLifecycleError, match="issuer retirement"):
            switcher.switch_to_preverified_world(
                candidate_generation=archive, expected_commit_sha256=pin,
            )
        assert old.owned_session_id == life.world.paper_session_id
        assert not life.world_held
    finally:
        old.stop_and_save()
