"""Stage28c1: original Stage28b typed Paper World + A/B inert source restore."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from experiments import stage28c1_pinned_inert_restore_dev as cli
from relay_self import stage28c1_inert_restore_dev as stage28c
from relay_self.coordinated_checkpoint_dev import restore_generation
from relay_self.world_checkpoint_dev import verify_restored_world
from test_stage28b_retired_typed_cut_dev import _setup


def _source(tmp_path: Path, monkeypatch):
    bridge, paper, store, evidence = _setup(tmp_path, monkeypatch)
    # A real Paper world consists of its Overworld and these two siblings.
    for name in ("world_nether", "world_the_end"):
        dimension = tmp_path / name
        dimension.mkdir()
        (dimension / "region").mkdir()
        (dimension / "region" / "r.0.0.mca").write_bytes(
            ("world-original:" + name).encode(),
        )
    result = stage28c_input_cut(bridge, paper, store, evidence)
    return result.generation


def stage28c_input_cut(bridge, paper, store, evidence):
    from relay_self.stage28b_retired_resident_typed_cut_dev import (
        capture_retired_resident_typed_world,
    )

    return capture_retired_resident_typed_world(
        bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
    )


def _inspect(generation: Path):
    return stage28c.inspect_stage28c_source(
        generation, expected_world_id="world-1",
        expected_source_branch_id="source",
    )


def _prepare(generation: Path, destination: Path, *, digest: str | None = None):
    return stage28c.prepare_stage28c_inert_restore(
        generation, destination,
        expected_world_id="world-1",
        expected_source_branch_id="source",
        expected_committed_sha256=digest or _inspect(generation).committed_sha256,
        restore_id="stage28c1-one-new-fork",
    )


def test_stage28c1_inspect_original_typed_three_dimensions_readonly(tmp_path, monkeypatch):
    generation = _source(tmp_path, monkeypatch)
    files_before = tuple(sorted(p.relative_to(generation) for p in generation.rglob("*")))
    inspected = _inspect(generation)
    assert inspected.generation_id == "g-000000000000"
    assert inspected.world_id == "world-1"
    assert inspected.roster == ("A", "B")
    assert inspected.self_cut_ticks == (("A", 105), ("B", 105))
    assert inspected.declared_world_tick == 110
    assert inspected.paper_dimensions == ("world_nether", "world_the_end")
    assert inspected.committed_sha256 == hashlib.sha256(
        (generation / "COMMITTED.json").read_bytes(),
    ).hexdigest()
    assert inspected.full_cognition_restored is False
    assert inspected.physical_action_issue_authorized is False
    assert files_before == tuple(
        sorted(p.relative_to(generation) for p in generation.rglob("*"))
    )


def test_stage28c1_one_fork_restores_world_dimensions_and_inert_owners(
    tmp_path, monkeypatch,
):
    generation = _source(tmp_path, monkeypatch)
    original_commit = (generation / "COMMITTED.json").read_bytes()
    destination = tmp_path / "fresh-restoration"
    result = _prepare(generation, destination)
    assert result.generation_id == "g-000000000000"
    assert result.roster == ("A", "B")
    assert result.world_id == "world-1"
    assert result.restored_branch_id.startswith("fork-")
    assert result.restored_branch_id != "source"
    assert result.paper_dimensions == ("world_nether", "world_the_end")
    assert result.self_pattern_revisions == (("A", 0), ("B", 0))
    assert result.fresh_worldbody_required
    assert result.old_native_session_reuse_forbidden
    assert result.old_l1_decision_reusable is False
    assert result.old_skill_resume_authorized is False
    assert result.old_peer_redelivery_authorized is False
    assert result.l1_reevaluation_eligible is False
    assert result.physical_action_issue_authorized is False
    assert result.new_paper_session_attested is False
    for dim in ("world", "world_nether", "world_the_end"):
        archive = (
            generation / "world" if dim == "world"
            else generation / "paper-dimensions" / dim
        )
        proof = verify_restored_world(archive, destination / dim)
        assert proof["new_branch_id"] == result.restored_branch_id
        assert proof["physical_action_authorized"] is False
    for sid in ("A", "B"):
        for name in ("owner-state.json", "physical-wal.json", "cognition.json"):
            assert (
                generation / "selves" / sid / name
            ).read_bytes() == (
                destination / "selves" / sid / name
            ).read_bytes()
    assert (generation / "COMMITTED.json").read_bytes() == original_commit
    assert not (destination / "world" / "level.dat").is_symlink()
    with pytest.raises(stage28c.Stage28cRestoreHold, match="new directory"):
        _prepare(generation, destination)


@pytest.mark.parametrize("failure", [
    "wrong-world", "wrong-branch", "wrong-commit", "wrong-generation",
    "missing-dimension", "source-world-drift",
])
def test_stage28c1_source_mismatch_refuses_before_creating_destination(
    tmp_path, monkeypatch, failure,
):
    generation = _source(tmp_path, monkeypatch)
    destination = tmp_path / "never-created-fork"
    opts = {
        "expected_world_id": "world-1",
        "expected_source_branch_id": "source",
        "expected_committed_sha256": _inspect(generation).committed_sha256,
        "restore_id": "one",
    }
    if failure == "wrong-world":
        opts["expected_world_id"] = "foreign-world"
    elif failure == "wrong-branch":
        opts["expected_source_branch_id"] = "foreign-branch"
    elif failure == "wrong-commit":
        opts["expected_committed_sha256"] = "0" * 64
    elif failure == "wrong-generation":
        opts["expected_generation_id"] = "g-000000000001"
    elif failure == "missing-dimension":
        # The COMMITTED file's physical companion archive disappeared.
        (generation / "paper-dimensions" / "world_nether" / "manifest.json").unlink()
    else:
        (generation / "world" / "world" / "level.dat").write_bytes(b"world-tampered")
    with pytest.raises(stage28c.Stage28cRestoreHold):
        stage28c.prepare_stage28c_inert_restore(
            generation, destination, **opts,
        )
    assert not destination.exists()


def test_stage28c1_world_only_cannot_recover_cognition(tmp_path):
    source = tmp_path / "g-000000000000"
    source.mkdir()
    (source / "WORLD_ONLY_COMMITTED.json").write_text("{}")
    with pytest.raises(stage28c.Stage28cRestoreHold):
        stage28c.inspect_stage28c_source(
            source, expected_world_id="world-1",
            expected_source_branch_id="source",
        )


def test_stage28c1_reject_destination_inside_source_without_mutation(
    tmp_path, monkeypatch,
):
    generation = _source(tmp_path, monkeypatch)
    target = generation / "forbidden-fork"
    with pytest.raises(stage28c.Stage28cRestoreHold, match="outside immutable"):
        _prepare(generation, target)
    assert not target.exists()


def test_stage28c1_corrupt_new_companion_receipt_holds_not_retries(
    tmp_path, monkeypatch,
):
    generation = _source(tmp_path, monkeypatch)
    destination = tmp_path / "bad-restore"
    original = restore_generation

    def corrupt_companion(src, dst, *, restore_id):
        value = original(src, dst, restore_id=restore_id)
        sidecar = dst / "world_nether.restore.json"
        metadata = json.loads(sidecar.read_bytes())
        metadata["new_branch_id"] = "fork-00000000-0000-4000-8000-000000000000"
        sidecar.write_text(json.dumps(metadata))
        return value

    with patch.object(stage28c, "restore_generation", corrupt_companion):
        with pytest.raises(stage28c.Stage28cRestoreHold):
            _prepare(generation, destination)
    assert destination.exists()
    assert (destination / "world_nether.restore.json").exists()
    assert (generation / "COMMITTED.json").is_file()


def test_stage28c1_cli_inspect_never_invokes_restore(tmp_path, monkeypatch, capsys):
    generation = _source(tmp_path, monkeypatch)
    monkeypatch.setattr(stage28c, "restore_generation", lambda *_args, **_kwargs: (
        pytest.fail("inspect-only triggered restore")
    ))
    monkeypatch.setattr(sys, "argv", [
        "stage28c1", "--generation", str(generation),
        "--expected-world-id", "world-1",
        "--expected-source-branch-id", "source",
        "--inspect-only",
    ])
    assert cli.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["source"]["committed_sha256"] == _inspect(generation).committed_sha256
    assert payload["model_post"] is False
    assert payload["new_paper_started"] is False


def test_stage28c1_cli_one_shot_requires_explicit_source_commit_pin(
    tmp_path, monkeypatch,
):
    generation = _source(tmp_path, monkeypatch)
    dest = tmp_path / "no-restore"
    monkeypatch.setattr(sys, "argv", [
        "stage28c1", "--generation", str(generation),
        "--expected-world-id", "world-1",
        "--expected-source-branch-id", "source",
        "--destination", str(dest), "--restore-id", "test",
        "--prepare-once",
    ])
    assert cli.main() == 2
    assert not dest.exists()


def test_stage28c1_cli_one_shot_returns_inert_receipt(
    tmp_path, monkeypatch, capsys,
):
    generation = _source(tmp_path, monkeypatch)
    dest = tmp_path / "one-restore"
    monkeypatch.setattr(sys, "argv", [
        "stage28c1", "--generation", str(generation),
        "--expected-world-id", "world-1",
        "--expected-source-branch-id", "source",
        "--destination", str(dest),
        "--source-committed-sha256", _inspect(generation).committed_sha256,
        "--restore-id", "once", "--prepare-once",
    ])
    assert cli.main() == 0
    data = json.loads(capsys.readouterr().out)
    assert data["classification"] == "STAGE28C1_INERT_TYPED_WORLD_SELF_RESTORE_DEV"
    assert data["receipt"]["physical_action_issue_authorized"] is False
    assert data["native_joined"] is False
    assert data["new_paper_started"] is False
    assert data["model_post"] is False
