"""#853 stopped-world checkpoint: filesystem-only DEV, no Minecraft runtime."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from relay_self.world_checkpoint_dev import (
    WorldCheckpointError,
    capture_stopped_world,
    restore_world_to_new_branch,
    verify_restored_world,
    verify_world_checkpoint,
)


def _world(tmp_path: Path) -> Path:
    root = tmp_path / "server-world"
    root.mkdir()
    contents = {
        "level.dat": b"NBT-IN-MODEL-ONLY: Time=204",
        "session.lock": b"legacy-lock-file-bytes",
        "region/r.0.0.mca": b"diamond-block-at-0-100-0",
        "entities/r.0.0.mca": b"Z1-UUID-record",
        "poi/r.0.0.mca": b"POI",
        "playerdata/00000000-0000-0000-0000-000000000001.dat": b"player-inventory",
        "DIM-1/region/r.0.0.mca": b"nether",
        "DIM1/entities/r.0.0.mca": b"end",
    }
    for rel, value in contents.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    return root


def _capture(source: Path, archive: Path, **overrides):
    kw = {
        "world_id": "minecraft-w1", "branch_id": "history-alpha",
        "checkpoint_id": "W100", "logical_tick": 204,
        "tick_source_ref": "server-log:gametime204",
        "stopped_server_ref": "controlled-server-exit0-and-saved",
    }
    kw.update(overrides)
    return capture_stopped_world(source, archive, **kw)


def test_capture_manifest_sha256_and_restore_custody(tmp_path):
    source = _world(tmp_path)
    archive = tmp_path / "checkpoint-W100"
    manifest = _capture(source, archive)
    assert manifest["state"] == "CAPTURED_STOPPED_WORLD_FILES_DEV"
    assert manifest["world_effect_coverage_attested"] is False
    assert manifest["stop_attestation_is_external"] is True
    assert verify_world_checkpoint(archive) == manifest
    assert len(manifest["files"]) == 8
    assert (archive / "world" / "playerdata/00000000-0000-0000-0000-000000000001.dat").is_file()
    initial = (source / "region/r.0.0.mca").read_bytes()
    source.joinpath("region/r.0.0.mca").write_bytes(b"gold-block-at-0-100-0")
    restored = tmp_path / "new-dev-world"
    receipt = restore_world_to_new_branch(archive, restored, restore_id="restore-r1")
    assert restored.joinpath("region/r.0.0.mca").read_bytes() == initial
    assert restored.joinpath("playerdata/00000000-0000-0000-0000-000000000001.dat").read_bytes() == b"player-inventory"
    assert source.joinpath("region/r.0.0.mca").read_bytes() == b"gold-block-at-0-100-0"
    assert receipt["new_branch_id"].startswith("fork-")
    assert receipt["new_branch_id"] != "history-alpha"
    assert receipt["source_declared_logical_tick"] == 204
    assert receipt["world_effect_coverage_attested"] is False
    assert receipt["physical_action_authorized"] is False
    assert receipt["semantic_owner_restored"] is False
    assert json.loads((tmp_path / "new-dev-world.restore.json").read_bytes()) == receipt
    assert verify_world_checkpoint(archive) == manifest


def test_restoring_twice_creates_distinct_branches_without_archive_mutation(tmp_path):
    source = _world(tmp_path)
    archive = tmp_path / "checkpoint-W100"
    _capture(source, archive)
    original = (archive / "manifest.json").read_bytes()
    first = restore_world_to_new_branch(archive, tmp_path / "fork-one", restore_id="r1")
    second = restore_world_to_new_branch(archive, tmp_path / "fork-two", restore_id="r2")
    assert first["new_branch_id"] != second["new_branch_id"]
    assert (archive / "manifest.json").read_bytes() == original


@pytest.mark.parametrize("kind", ["modified", "missing", "extra", "symlink"])
def test_corrupt_checkpoint_refused_before_restore(tmp_path, kind):
    source = _world(tmp_path)
    archive = tmp_path / "W100"
    _capture(source, archive)
    target = archive / "world" / "entities/r.0.0.mca"
    if kind == "modified":
        target.write_bytes(b"bad")
    elif kind == "missing":
        target.unlink()
    elif kind == "extra":
        (archive / "world" / "rogue.txt").write_bytes(b"added")
    else:
        target.unlink()
        target.symlink_to(archive / "world" / "level.dat")
    with pytest.raises(WorldCheckpointError):
        verify_world_checkpoint(archive)
    with pytest.raises(WorldCheckpointError):
        restore_world_to_new_branch(archive, tmp_path / "should-not-exist", restore_id="r1")
    assert not (tmp_path / "should-not-exist").exists()


@pytest.mark.parametrize("kind", ["manifest", "sha256sums", "unknown_key", "traversal"])
def test_corrupt_manifest_or_sidecar_is_refused(tmp_path, kind):
    source = _world(tmp_path)
    archive = tmp_path / "W100"
    _capture(source, archive)
    if kind == "manifest":
        (archive / "manifest.json").write_text("not json")
    elif kind == "sha256sums":
        (archive / "SHA256SUMS").write_text("0" * 64)
    else:
        payload = json.loads((archive / "manifest.json").read_bytes())
        if kind == "unknown_key":
            payload["allow_unverified_restore"] = True
        else:
            payload["files"][0]["path"] = "../escape"
        (archive / "manifest.json").write_text(json.dumps(payload))
    with pytest.raises(WorldCheckpointError):
        verify_world_checkpoint(archive)


def test_source_world_missing_level_dat_is_refused_without_creating_archive(tmp_path):
    source = tmp_path / "empty-world"
    source.mkdir()
    (source / "region").mkdir()
    (source / "region/r.0.0.mca").write_bytes(b"only-chunk")
    archive = tmp_path / "invalid-capture"
    with pytest.raises(WorldCheckpointError):
        _capture(source, archive)
    assert not archive.exists()


def test_symlink_in_source_tree_is_refused(tmp_path):
    source = _world(tmp_path)
    (source / "poi/evil").symlink_to(source / "level.dat")
    with pytest.raises(WorldCheckpointError):
        _capture(source, tmp_path / "never-archive")
    assert not (tmp_path / "never-archive").exists()


def test_source_special_file_refused(tmp_path):
    source = _world(tmp_path)
    import os
    os.mkfifo(source / "not-a-regular-file")
    with pytest.raises(WorldCheckpointError):
        _capture(source, tmp_path / "no-snapshot")


def test_missing_stop_attestation_and_invalid_tick_refused(tmp_path):
    source = _world(tmp_path)
    with pytest.raises(WorldCheckpointError):
        _capture(source, tmp_path / "bad-stop", stopped_server_ref="")
    with pytest.raises(WorldCheckpointError):
        _capture(source, tmp_path / "bad-tick", logical_tick=True)
    with pytest.raises(WorldCheckpointError):
        _capture(source, tmp_path / "bad-time", tick_source_ref="")


def test_capture_must_not_reuse_existing_directory(tmp_path):
    source = _world(tmp_path)
    archive = tmp_path / "W100"
    archive.mkdir()
    with pytest.raises(WorldCheckpointError):
        _capture(source, archive)
    assert list(archive.iterdir()) == []


@pytest.mark.parametrize("place", ["inside-world", "inside-archive", "existing-restore"])
def test_capture_restore_paths_never_overlap_or_overwrite(tmp_path, place):
    source = _world(tmp_path)
    archive = tmp_path / "W100"
    if place == "inside-world":
        with pytest.raises(WorldCheckpointError):
            _capture(source, source / "nested-archive")
        return
    _capture(source, archive)
    if place == "inside-archive":
        with pytest.raises(WorldCheckpointError):
            restore_world_to_new_branch(archive, archive / "nested", restore_id="r1")
    else:
        existing = tmp_path / "running-world-not-touched"
        existing.mkdir()
        (existing / "keep.bin").write_bytes(b"do-not-edit")
        with pytest.raises(WorldCheckpointError):
            restore_world_to_new_branch(archive, existing, restore_id="r1")
        assert (existing / "keep.bin").read_bytes() == b"do-not-edit"


def test_archive_with_extra_top_level_file_rejected(tmp_path):
    source = _world(tmp_path)
    archive = tmp_path / "W100"
    _capture(source, archive)
    (archive / "extra").write_bytes(b"untrusted")
    with pytest.raises(WorldCheckpointError):
        verify_world_checkpoint(archive)


def test_source_change_during_capture_leaves_unfinished_archive(tmp_path, monkeypatch):
    import relay_self.world_checkpoint_dev as m

    source = _world(tmp_path)
    archive = tmp_path / "W100"
    original = m._copy_hashed
    triggered = [False]

    def mutate_after_copy(a, b):
        out = original(a, b)
        if a.name == "level.dat" and a.is_relative_to(source) and not triggered[0]:
            source.joinpath("level.dat").write_bytes(b"changed-mid-capture")
            triggered[0] = True
        return out

    monkeypatch.setattr(m, "_copy_hashed", mutate_after_copy)
    with pytest.raises(WorldCheckpointError):
        _capture(source, archive)
    assert archive.is_dir()
    assert not (archive / "manifest.json").exists()
    with pytest.raises(WorldCheckpointError):
        verify_world_checkpoint(archive)


def test_no_wal_or_self_owner_touched_by_stopped_world_copy(tmp_path):
    source = _world(tmp_path)
    wal = tmp_path / "physical-wal.json"
    wal.write_bytes(b"PREPARED_UNRESOLVED-do-not-change")
    archive = tmp_path / "W100"
    _capture(source, archive)
    restore_world_to_new_branch(archive, tmp_path / "W100-reopened", restore_id="r1")
    assert wal.read_bytes() == b"PREPARED_UNRESOLVED-do-not-change"


def test_copy_declaration_cannot_claim_server_event_coverage(tmp_path):
    source = _world(tmp_path)
    archive = tmp_path / "W100"
    _capture(source, archive)
    payload = json.loads((archive / "manifest.json").read_bytes())
    payload["world_effect_coverage_attested"] = True
    (archive / "manifest.json").write_text(json.dumps(payload))
    with pytest.raises(WorldCheckpointError):
        verify_world_checkpoint(archive)



def test_prelaunch_restored_world_and_branch_receipt_verify(tmp_path):
    source = _world(tmp_path)
    archive = tmp_path / "W100"
    _capture(source, archive)
    destination = tmp_path / "restored-world"
    receipt = restore_world_to_new_branch(archive, destination, restore_id="r1")
    assert verify_restored_world(archive, destination) == receipt
    assert receipt["new_branch_id"] != receipt["source_branch_id"]


@pytest.mark.parametrize("damage", ["changed-file", "extra-file", "missing-receipt", "wrong-branch", "fake-grant"])
def test_prelaunch_restored_world_gate_rejects_tampering(tmp_path, damage):
    source = _world(tmp_path)
    archive = tmp_path / "W100"
    _capture(source, archive)
    destination = tmp_path / "restored-world"
    restore_world_to_new_branch(archive, destination, restore_id="r1")
    receipt_file = tmp_path / "restored-world.restore.json"
    if damage == "changed-file":
        (destination / "level.dat").write_bytes(b"tampered")
    elif damage == "extra-file":
        (destination / "extra.json").write_bytes(b"unexpected")
    elif damage == "missing-receipt":
        receipt_file.unlink()
    else:
        data = json.loads(receipt_file.read_bytes())
        if damage == "wrong-branch":
            data["new_branch_id"] = data["source_branch_id"]
        else:
            data["physical_action_authorized"] = True
        receipt_file.write_text(json.dumps(data))
    with pytest.raises(WorldCheckpointError):
        verify_restored_world(archive, destination)



def _manifest_pin(archive: Path) -> str:
    return hashlib.sha256((archive / "manifest.json").read_bytes()).hexdigest()


def test_optional_manifest_pin_rejects_metadata_rewrite_without_blocking_dev(tmp_path):
    """DEV intentionally trusts operator metadata unless independent pin supplied."""
    source = _world(tmp_path)
    archive = tmp_path / "W100"
    _capture(source, archive)
    original_pin = _manifest_pin(archive)
    assert verify_world_checkpoint(
        archive, expected_manifest_sha256=original_pin
    )["declared_logical_tick"] == 204

    body = json.loads((archive / "manifest.json").read_bytes())
    body["declared_logical_tick"] = 205
    (archive / "manifest.json").write_text(json.dumps(body))
    assert verify_world_checkpoint(archive)["declared_logical_tick"] == 205
    with pytest.raises(WorldCheckpointError, match="externally pinned SHA256"):
        verify_world_checkpoint(archive, expected_manifest_sha256=original_pin)
    with pytest.raises(WorldCheckpointError, match="externally pinned SHA256"):
        restore_world_to_new_branch(
            archive, tmp_path / "pinned-restore-must-not-start",
            restore_id="r2", expected_manifest_sha256=original_pin,
        )
    assert not (tmp_path / "pinned-restore-must-not-start").exists()
    # Weak operator-trust mode is explicitly still available in isolated DEV.
    receipt = restore_world_to_new_branch(
        archive, tmp_path / "unpinned-dev-restore", restore_id="r1",
    )
    assert receipt["source_declared_logical_tick"] == 205
    with pytest.raises(WorldCheckpointError, match="externally pinned SHA256"):
        verify_restored_world(
            archive, tmp_path / "unpinned-dev-restore",
            expected_manifest_sha256=original_pin,
        )


@pytest.mark.parametrize("pin", ["", "0" * 63, "G" * 64, "g" * 64])
def test_bad_optional_manifest_pin_rejected(tmp_path, pin):
    source = _world(tmp_path)
    archive = tmp_path / "W100"
    _capture(source, archive)
    with pytest.raises(WorldCheckpointError, match="lowercase hex"):
        verify_world_checkpoint(archive, expected_manifest_sha256=pin)


def test_optional_pinned_round_trip_restores_original_dev_behavior(tmp_path):
    source = _world(tmp_path)
    archive = tmp_path / "W100"
    _capture(source, archive)
    pin = _manifest_pin(archive)
    manifest = verify_world_checkpoint(archive, expected_manifest_sha256=pin)
    restored = tmp_path / "fork-restored"
    receipt = restore_world_to_new_branch(
        archive, restored, restore_id="r1", expected_manifest_sha256=pin,
    )
    assert verify_restored_world(
        archive, restored, expected_manifest_sha256=pin,
    ) == receipt
    assert manifest["declared_logical_tick"] == 204
    assert receipt["physical_action_authorized"] is False



def test_paper_companion_without_level_dat_uses_explicit_role_and_restores(tmp_path):
    """Paper Nether/End siblings need not contain the overworld's level.dat."""
    source = tmp_path / "world_nether"
    source.mkdir()
    (source / "DIM-1").mkdir()
    (source / "DIM-1" / "region").mkdir()
    (source / "DIM-1" / "region" / "r.0.0.mca").write_bytes(b"native-nether")
    with pytest.raises(WorldCheckpointError, match="level.dat"):
        _capture(source, tmp_path / "ordinary")
    archive = tmp_path / "typed-companion"
    record = _capture(source, archive, paper_companion=True)
    assert record["schema"] == 2
    assert record["world_file_role"] == "PAPER_COMPANION"
    assert verify_world_checkpoint(archive) == record
    restored = tmp_path / "restored-nether"
    receipt = restore_world_to_new_branch(
        archive, restored, restore_id="restore-paper-nether",
    )
    assert receipt["physical_action_authorized"] is False
    assert (restored / "DIM-1" / "region" / "r.0.0.mca").read_bytes() == b"native-nether"
    assert verify_restored_world(archive, restored) == receipt


@pytest.mark.parametrize("bad_role", ["OVERWORLD", None, True])
def test_paper_companion_manifest_role_tamper_rejected(tmp_path, bad_role):
    source = tmp_path / "world_the_end"
    source.mkdir()
    (source / "DIM1").mkdir()
    (source / "DIM1" / "entities").mkdir()
    (source / "DIM1" / "entities" / "r.0.0.mca").write_bytes(b"end")
    archive = tmp_path / "end-archive"
    _capture(source, archive, paper_companion=True)
    marker = archive / "manifest.json"
    record = json.loads(marker.read_text())
    record["world_file_role"] = bad_role
    marker.write_text(json.dumps(record))
    with pytest.raises(WorldCheckpointError, match="schema"):
        verify_world_checkpoint(archive)
    with pytest.raises(WorldCheckpointError):
        restore_world_to_new_branch(
            archive, tmp_path / "untrusted-restored-end", restore_id="bad",
        )
    assert not (tmp_path / "untrusted-restored-end").exists()


def test_empty_paper_companion_refused_before_archive_creation(tmp_path):
    empty = tmp_path / "world_nether"
    empty.mkdir()
    with pytest.raises(WorldCheckpointError, match="empty Paper"):
        _capture(empty, tmp_path / "no-archive", paper_companion=True)
    assert not (tmp_path / "no-archive").exists()
