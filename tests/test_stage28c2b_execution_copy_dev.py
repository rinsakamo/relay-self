"""The recovered owner must only point at a separately verified copy."""
import pytest

from relay_self.stage28c2b_execution_copy_dev import (
    ExecutionCopyHold,
    create_execution_copy,
)
from test_stage28c2_recovered_resident_owner_dev import _context


def _copy(generation, restored, prepared, destination):
    return create_execution_copy(
        generation, restored, destination, expected_world_id="world-1",
        expected_source_branch_id="source",
        expected_committed_sha256=prepared.source_commit_sha256,
        expected_fork_branch_id=prepared.restored_branch_id,
    )


def test_copy_binds_original_recovered_owners_only_to_copy(tmp_path, monkeypatch):
    generation, restored, prepared = _context(tmp_path, monkeypatch)
    result = _copy(generation, restored, prepared, tmp_path / "execution")
    assert result.files
    assert result.recovered.physical.observation_only
    for sid, owner in result.recovered.owners.items():
        assert owner.files.cognition_file == result.directory / "selves" / sid / "cognition.json"
        assert owner.retained.identity.self_id == sid
        assert owner.cohort is result.recovered.cognitive_work
    assert (restored / "selves" / "A" / "cognition.json").read_bytes() == (
        result.directory / "selves" / "A" / "cognition.json"
    ).read_bytes()
    with pytest.raises(ExecutionCopyHold):
        _copy(generation, restored, prepared, result.directory)


def test_copy_rejects_source_symlink_and_overlap(tmp_path, monkeypatch):
    generation, restored, prepared = _context(tmp_path, monkeypatch)
    with pytest.raises(ExecutionCopyHold):
        _copy(generation, restored, prepared, restored / "nested")
    (restored / "foreign-link").symlink_to(generation, target_is_directory=True)
    with pytest.raises(ExecutionCopyHold, match="symlink"):
        _copy(generation, restored, prepared, tmp_path / "execution")


def test_copy_rejects_modified_cognition_without_binding(tmp_path, monkeypatch):
    generation, restored, prepared = _context(tmp_path, monkeypatch)
    (restored / "selves" / "B" / "cognition.json").write_bytes(b"corrupt")
    destination = tmp_path / "execution"
    with pytest.raises(ExecutionCopyHold):
        _copy(generation, restored, prepared, destination)
    assert destination.exists()
