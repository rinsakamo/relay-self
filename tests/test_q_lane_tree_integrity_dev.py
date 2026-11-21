"""Q tree guard tests: intentionally tiny local Git repos, no product execution."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from experiments.q_lane_tree_integrity_dev import (
    QTreeHold,
    inspect_tree_integrity,
)

_REQUIRED = (
    ".github/workflows/ci.yml",
    "experiments/cognitive_physical_move_issue_dev.py",
    "src/relay_self/owned_resident_physical_bridge_dev.py",
    "src/relay_self/physical_action_journal.py",
    "src/relay_self/physical_issue_admission_dev.py",
)


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def _commit(root: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(root), "commit", "-m", message],
        check=True, capture_output=True,
    )
    return _git(root, "rev-parse", "HEAD")


def _fixture(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    _git(root, "config", "user.name", "Q Tester")
    _git(root, "config", "user.email", "q@example.invalid")
    for rel in (*_REQUIRED, "docs/old-contract.md", "tests/old_test.py"):
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("original\n")
    return root, _commit(root, "original protected source")


def test_q_tree_accepts_narrow_additive_change_without_writing_repo(tmp_path):
    root, base = _fixture(tmp_path)
    newer = root / "docs" / "verification" / "new.md"
    newer.parent.mkdir(parents=True)
    newer.write_text("audit\n")
    head = _commit(root, "add Q-only report")
    original_head = _git(root, "rev-parse", "HEAD")
    before = {p.relative_to(root): (p.read_bytes(), p.stat().st_mtime_ns)
              for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}
    verdict = inspect_tree_integrity(root, base_sha=base, expected_head=head)
    assert verdict["removed_files"] == 0
    assert verdict["base_files"] == 7
    assert verdict["head_files"] == 8
    assert verdict["git_repository_origin_authenticated"] is False
    assert verdict["real_world_attested"] is False
    assert _git(root, "rev-parse", "HEAD") == original_head
    after = {p.relative_to(root): (p.read_bytes(), p.stat().st_mtime_ns)
             for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}
    assert before == after


def test_q_tree_rejects_three_file_accidental_tree_collapse(tmp_path):
    root, base = _fixture(tmp_path)
    for rel in (*_REQUIRED, "docs/old-contract.md", "tests/old_test.py"):
        (root / rel).unlink()
    for rel in ("docs/experiments/preworld.md", "experiments/preworld.py",
                "tests/test_preworld.py"):
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("new-only\n")
    head = _commit(root, "accidental replacement")
    with pytest.raises(QTreeHold, match="removed=7"):
        inspect_tree_integrity(root, base_sha=base, expected_head=head)


def test_q_tree_rejects_subtle_history_loss_even_if_protected_files_stay(tmp_path):
    root, base = _fixture(tmp_path)
    (root / "docs" / "old-contract.md").unlink()
    head = _commit(root, "unapproved historical deletion")
    with pytest.raises(QTreeHold, match="removed=1"):
        inspect_tree_integrity(root, base_sha=base, expected_head=head)


def test_q_tree_rejects_protected_file_as_symlink(tmp_path):
    root, base = _fixture(tmp_path)
    protected = root / _REQUIRED[0]
    protected.unlink()
    protected.symlink_to(root / "docs" / "old-contract.md")
    head = _commit(root, "protected symlink")
    with pytest.raises(QTreeHold, match="invalid_protected_modes"):
        inspect_tree_integrity(root, base_sha=base, expected_head=head)


def test_q_tree_rejects_unpinned_or_wrong_head_and_foreign_base(tmp_path):
    root, base = _fixture(tmp_path)
    f = root / "new.txt"
    f.write_text("new")
    head = _commit(root, "some delta")
    for wrong in ("0" * 40, "", base):
        with pytest.raises(QTreeHold):
            inspect_tree_integrity(root, base_sha=base, expected_head=wrong)
    with pytest.raises(QTreeHold):
        inspect_tree_integrity(root, base_sha="0" * 40, expected_head=head)
    with pytest.raises(QTreeHold):
        inspect_tree_integrity(root, base_sha=base, expected_head=head,
                               protected_paths=("relative/../escape",))


def test_q_tree_holds_deleted_source_without_writing(tmp_path):
    root, base = _fixture(tmp_path)
    (root / "tests" / "old_test.py").unlink()
    head = _commit(root, "accidental missing file")
    with pytest.raises(QTreeHold):
        inspect_tree_integrity(root, base_sha=base, expected_head=head)
