"""#860 DEV generation tests. Filesystem fixtures; not a real running server."""
from __future__ import annotations

import json

import pytest

from relay_self.coordinated_checkpoint_dev import (
    AutosaveGate,
    CoordinatedCheckpointError,
    SelfSnapshotSource,
    capture_generation,
    latest_verified_generation,
    restore_generation,
    verify_generation,
)
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
    save_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance


def _fixtures(tmp_path):
    world = tmp_path / "world-source"
    world.mkdir()
    (world / "level.dat").write_bytes(b"synthetic-W100-world")
    (world / "entities").mkdir()
    (world / "entities" / "r.0.0.mca").write_bytes(b"Z1-uuid-a-alive")
    states = tmp_path / "self-states"
    states.mkdir()
    sources = []
    for sid in ("A", "B"):
        directory = states / sid
        directory.mkdir()
        cognition = directory / "cognition.json"
        save_persistent_cognition(
            cognition,
            PersistentCognition(
                identity=IdentitySpecification(
                    self_id=sid, directives=("Continue as self.",),
                    provenance=Provenance(source="test", reference=sid),
                ),
            ),
        )
        wal = directory / "wal.json"
        PhysicalActionJournal.create(wal, self_id=sid)
        sources.append(SelfSnapshotSource(sid, cognition, wal))
    store = tmp_path / "generations"
    store.mkdir()
    return world, store, tuple(sources)


def _capture(world, store, selves, sequence=1, **overrides):
    params = {
        "sequence": sequence, "expected_self_ids": ("A", "B"), "selves": selves,
        "world_id": "world-1", "branch_id": "original",
        "logical_tick": 100 + sequence,
        "tick_source_ref": "mock-operator:tick",
        "stopped_server_ref": "mock-operator:server-stopped",
        "quiesced_selves_ref": "mock-operator:all-selves-quiesced",
    }
    params.update(overrides)
    return capture_generation(world, store, **params)


def test_two_self_generation_recovers_only_committed_state(tmp_path):
    world, store, selves = _fixtures(tmp_path)
    generation = _capture(world, store, selves)
    result = verify_generation(generation)
    assert result["roster"] == ["A", "B"]
    assert result["atomic_capture_attested"] is False
    assert result["full_self_owner_restored"] is False
    assert latest_verified_generation(store) == generation

    # Post-checkpoint changes are not part of the restored future.
    (world / "entities" / "r.0.0.mca").write_bytes(b"Z1-is-dead-later")
    later = PersistentCognition(
        identity=IdentitySpecification(
            self_id="A", directives=("Lost post-checkpoint changes.",),
            provenance=Provenance(source="test", reference="future"),
        ),
    )
    save_persistent_cognition(selves[0].cognition_file, later)

    dest = tmp_path / "new-recovery"
    receipt = restore_generation(generation, dest, restore_id="rollback-1")
    assert receipt["self_ids"] == ["A", "B"]
    assert receipt["replay_performed"] is False
    assert receipt["physical_action_issue_authorized"] is False
    assert receipt["full_self_owner_restored"] is False
    assert (dest / "world" / "entities" / "r.0.0.mca").read_bytes() == b"Z1-uuid-a-alive"
    assert (dest / "selves" / "A" / "cognition.json").read_bytes() != (
        selves[0].cognition_file.read_bytes()
    )
    assert (dest / "world.restore.json").exists()
    assert (dest / "RESTORE_PREPARED.json").exists()


def test_missing_self_or_foreign_cognition_never_commits(tmp_path):
    world, store, selves = _fixtures(tmp_path)
    with pytest.raises(CoordinatedCheckpointError, match="missing or duplicate"):
        _capture(world, store, selves[:1])
    assert latest_verified_generation(store) is None

    # A's cognition must not be stored under B's durable identity.
    with pytest.raises(CoordinatedCheckpointError, match="foreign"):
        _capture(world, store, (selves[0], SelfSnapshotSource(
            "B", selves[0].cognition_file, selves[1].physical_wal_file,
        )))
    assert latest_verified_generation(store) is None
    assert not (store / "g-000000000001" / "COMMITTED.json").exists()


def test_incomplete_later_generation_falls_back_without_erasure(tmp_path):
    world, store, selves = _fixtures(tmp_path)
    prior = _capture(world, store, selves, sequence=1)
    # A corrupted or interrupted next generation is never eligible.
    bad = store / "g-000000000002"
    bad.mkdir()
    (bad / "COMMITTED.json").write_text('{"incomplete":true}')
    assert latest_verified_generation(store) == prior
    assert verify_generation(prior)["sequence"] == 1


@pytest.mark.parametrize("which", ["world", "self", "marker", "unexpected"])
def test_corrupt_committed_generation_refused(tmp_path, which):
    world, store, selves = _fixtures(tmp_path)
    generation = _capture(world, store, selves)
    if which == "world":
        (generation / "world" / "world" / "level.dat").write_bytes(b"changed")
    elif which == "self":
        (generation / "selves" / "B" / "cognition.json").write_bytes(b"changed")
    elif which == "marker":
        (generation / "COMMITTED.json").write_text("no longer JSON")
    else:
        (generation / "rogue").write_bytes(b"untracked")
    with pytest.raises((CoordinatedCheckpointError, ValueError)):
        verify_generation(generation)
    assert latest_verified_generation(store) is None
    with pytest.raises((CoordinatedCheckpointError, ValueError)):
        restore_generation(generation, tmp_path / "no-restore", restore_id="r2")


def test_autosave_gate_sixty_seconds_and_failed_capture_not_committed(tmp_path):
    world, store, selves = _fixtures(tmp_path)
    gate = AutosaveGate()
    first = gate.run_if_due(
        100.0, lambda: _capture(world, store, selves, sequence=1),
    )
    assert first == store / "g-000000000001"
    assert gate.run_if_due(159.99, lambda: None) is None
    assert gate.due(160.0)

    def failure():
        raise RuntimeError("server did not stop")

    with pytest.raises(RuntimeError):
        gate.run_if_due(160.0, failure)
    assert gate.last_success_monotonic == 100.0
    second = gate.run_if_due(
        160.0, lambda: _capture(world, store, selves, sequence=2),
    )
    assert second == store / "g-000000000002"
    assert not gate.due(219.9)
    with pytest.raises(CoordinatedCheckpointError):
        gate.run_if_due(220.0, lambda: store / "g-000000000003")
    assert gate.last_success_monotonic == 160.0
    assert latest_verified_generation(store) == second


def test_paper_full_dimension_generation_rollback_same_branch(tmp_path):
    world, store, selves = _fixtures(tmp_path)
    paper_world = world.with_name("world")
    world.rename(paper_world)
    for name in ("world_nether", "world_the_end"):
        dimension = paper_world.parent / name
        dimension.mkdir()
        # Real Paper companions may have region/ files without level.dat.
        (dimension / "region").mkdir()
        (dimension / "region" / "r.0.0.mca").write_bytes(
            b"checkpoint-" + name.encode()
        )
    with pytest.raises(CoordinatedCheckpointError, match="omitted"):
        _capture(paper_world, store, selves)
    assert latest_verified_generation(store) is None

    saved = _capture(paper_world, store, selves, paper_layout=True)
    manifest = verify_generation(saved)
    assert manifest["schema"] == 2
    assert set(manifest["paper_dimensions"]) == {"world_nether", "world_the_end"}
    for name in manifest["paper_dimensions"]:
        (paper_world.parent / name / "region" / "r.0.0.mca").write_bytes(b"post-cut")

    recovered = tmp_path / "new-paper-branch"
    receipt = restore_generation(saved, recovered, restore_id="paper-rollback")
    for name in ("world_nether", "world_the_end"):
        assert (recovered / name / "region" / "r.0.0.mca").read_bytes() == (
            b"checkpoint-" + name.encode()
        )
        sidecar = json.loads((recovered / f"{name}.restore.json").read_bytes())
        assert sidecar["new_branch_id"] == receipt["fork_branch_id"]
    assert latest_verified_generation(store) == saved


@pytest.mark.parametrize("fault", ["missing", "changed", "link", "unknown"])
def test_paper_dimension_loss_cannot_be_adopted(tmp_path, fault):
    world, store, selves = _fixtures(tmp_path)
    paper_world = world.with_name("world")
    world.rename(paper_world)
    nether = paper_world.parent / "world_nether"
    nether.mkdir()
    (nether / "level.dat").write_bytes(b"nether-stopped")
    saved = _capture(paper_world, store, selves, paper_layout=True)
    target = saved / "paper-dimensions" / "world_nether"
    if fault == "missing":
        (target / "world" / "level.dat").unlink()
    elif fault == "changed":
        (target / "world" / "level.dat").write_bytes(b"tamper")
    elif fault == "link":
        (target / "world" / "level.dat").unlink()
        (target / "world" / "level.dat").symlink_to(paper_world / "level.dat")
    else:
        (saved / "paper-dimensions" / "unknown").mkdir()
    with pytest.raises((CoordinatedCheckpointError, ValueError)):
        verify_generation(saved)
    assert latest_verified_generation(store) is None
    with pytest.raises((CoordinatedCheckpointError, ValueError)):
        restore_generation(saved, tmp_path / "refused", restore_id="refuse")
    assert not (tmp_path / "refused").exists()


def test_paper_dimension_incomplete_capture_does_not_commit(tmp_path):
    world, store, selves = _fixtures(tmp_path)
    paper_world = world.with_name("world")
    world.rename(paper_world)
    nether = paper_world.parent / "world_nether"
    nether.mkdir()
    # A directory with no data files is incomplete; a populated Paper
    # sibling without level.dat is now a valid role-qualified archive.
    (nether / "region").mkdir()
    with pytest.raises(ValueError, match="empty Paper companion"):
        _capture(paper_world, store, selves, paper_layout=True)
    assert latest_verified_generation(store) is None
    assert not (store / "g-000000000001" / "COMMITTED.json").exists()
