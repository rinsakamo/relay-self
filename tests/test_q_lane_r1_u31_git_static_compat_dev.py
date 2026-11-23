"""Q R1 independent Git-static source audit: synthetic repos, no WSL/World."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from experiments.q_lane_git_anchor_custody_dev import QGitCustodyHold
from experiments.q_lane_r1_u31_git_static_compat_dev import (
    NEW_PATHS,
    QR1SourceHold,
    _inspect_static_shadow_source,
    inspect_r1_git_compatibility,
)

SOURCE = "src/relay_self/r1_owner_context_shadow_dev.py"
TEST = "tests/test_r1_owner_context_shadow_dev.py"
DOC = "docs/architecture/r1-u31-original-owner-context-shadow-dev.md"
SYNTHETIC = b'''"""Synthetic Q fixture; deliberately not real R1 code."""
from dataclasses import dataclass

@dataclass(frozen=True)
class R1ShadowComparison:
    l1_input_switched: bool = False
    physical_authorized: bool = False
    memory_adopted: bool = False

def compare_original_owner_r1_shadow():
    present = resident.read_present_cpu()
    current = read_original_owner_current()
    memory = retrieve_original_owner_memory()
    original = load_persistent_cognition()
    return present, current, memory, original

def r1_shadow_is_live():
    return context_is_live()
'''


def cmd(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def commit(repo: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(repo), "add", "-A"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", message],
                   check=True, capture_output=True)
    return cmd(repo, "rev-parse", "HEAD")


def write(repo: Path, path: str, data: bytes) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def fixture(tmp_path: Path, *, source: bytes = SYNTHETIC):
    root = tmp_path / "git"
    root.mkdir(parents=True)
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    cmd(root, "config", "user.name", "Q synthetic fixture")
    cmd(root, "config", "user.email", "q@example.invalid")
    write(root, "src/relay_self/physical_action_journal.py", b"unchanged U31 WAL\n")
    write(root, "src/relay_self/resident_cognitive_work_owner_dev.py", b"unchanged Owner\n")
    write(root, "docs/I-U31.md", b"reported world DEV evidence, not trusted input\n")
    baseline = commit(root, "synthetic U31 baseline; not independently authenticated")
    write(root, SOURCE, source)
    commit(root, "R1 source")
    write(root, TEST, b"# synthetic R1 hostile suite\n")
    commit(root, "R1 tests")
    write(root, DOC, b"# synthetic Shadow responsibility matrix\n")
    final = commit(root, "R1 documentation")
    return root, baseline, final


def inspect(root, baseline, final):
    return inspect_r1_git_compatibility(
        root, trusted_u31_i_sha=baseline, r1_head_sha=final,
    )


def test_q_r1_git_only_positive_is_explicitly_not_real_world(tmp_path):
    root, baseline, final = fixture(tmp_path)
    head_before = cmd(root, "rev-parse", "HEAD")
    files_before = {
        p.relative_to(root): p.read_bytes()
        for p in root.rglob("*") if p.is_file() and ".git" not in p.parts
    }
    receipt = inspect(root, baseline, final)
    assert receipt["classification"] == "Q_R1_U31_GIT_STATIC_COMPAT_CPU_OFFLINE_DEV"
    assert receipt["added_paths"] == sorted(NEW_PATHS)
    assert receipt["linear_r_only_commit_count"] == 3
    assert receipt["unchanged_u31_legacy_path_count"] == 3
    assert receipt["original_owner_physical_wal_code_unchanged"] is True
    assert receipt["r1_report_grant_defaults_false"] is True
    assert receipt["original_wsl_u31_raw_evidence_read"] is False
    assert receipt["independent_original_native_paper_custody_verified"] is False
    assert receipt["semantic_owner_admission_attested"] is False
    assert receipt["q_r1_real_world_attested"] is False
    assert receipt["r2_migration_approved"] is False
    assert receipt["qual_go"] is False
    assert receipt["science_run"] is False
    assert head_before == cmd(root, "rev-parse", "HEAD")
    assert files_before == {
        p.relative_to(root): p.read_bytes()
        for p in root.rglob("*") if p.is_file() and ".git" not in p.parts
    }


def test_q_r1_intermediate_owner_change_restored_later_still_hold(tmp_path):
    root, baseline, _ = fixture(tmp_path)
    physical = "src/relay_self/physical_action_journal.py"
    write(root, physical, b"modified original U31 WAL\n")
    commit(root, "tampered intermediate physical source")
    write(root, physical, b"unchanged U31 WAL\n")
    final = commit(root, "attempt to restore U31")
    with pytest.raises(QGitCustodyHold, match="altered"):
        inspect(root, baseline, final)


@pytest.mark.parametrize("bad_path", (
    "src/relay_self/physical_issue_admission_dev.py",
    "extra_r1_owner.py",
    "tests/test_unapproved.py",
))
def test_q_r1_new_unapproved_source_path_hold(tmp_path, bad_path):
    root, baseline, _ = fixture(tmp_path)
    write(root, bad_path, b"new code path\n")
    final = commit(root, "extra path outside R-only scope")
    with pytest.raises(QGitCustodyHold, match="altered"):
        inspect(root, baseline, final)


@pytest.mark.parametrize("bad_source", (
    SYNTHETIC + b"\ndef act():\n    owner.retained = None\n",
    SYNTHETIC + b"\ndef act():\n    bridge.owners['A'] = object()\n",
    SYNTHETIC + b"\ndef act():\n    submit('new model ticket')\n",
    SYNTHETIC + b"\nimport subprocess\n",
    SYNTHETIC + b"\nfrom relay_self.physical_issue_admission_dev import PhysicalIssueAdmission\n",
    SYNTHETIC.replace(b"l1_input_switched: bool = False",
                      b"l1_input_switched: bool = True"),
    SYNTHETIC.replace(b"def r1_shadow_is_live():", b"def removed_live_check():"),
))
def test_q_r1_static_authority_bypass_denied(bad_source):
    with pytest.raises(QR1SourceHold):
        _inspect_static_shadow_source(bad_source)


def test_q_r1_legacy_modified_in_final_hold(tmp_path):
    root, baseline, _ = fixture(tmp_path)
    write(root, "src/relay_self/resident_cognitive_work_owner_dev.py", b"new second owner\n")
    final = commit(root, "modified original cognition owner")
    with pytest.raises(QGitCustodyHold, match="altered"):
        inspect(root, baseline, final)


def test_q_r1_missing_shadow_file_refused(tmp_path):
    root, baseline, _ = fixture(tmp_path)
    (root / DOC).unlink()
    final = commit(root, "removed R1 source document")
    with pytest.raises(QGitCustodyHold, match="exactly"):
        inspect(root, baseline, final)


def test_q_r1_symlink_shadow_file_refused(tmp_path):
    root, baseline, _ = fixture(tmp_path)
    f = root / DOC
    f.unlink()
    f.symlink_to(root / TEST)
    final = commit(root, "attempt to smuggle R1 file symlink")
    with pytest.raises(QGitCustodyHold, match="symlinked|nonregular"):
        inspect(root, baseline, final)


def test_q_r1_merge_ancestry_refused(tmp_path):
    root, baseline, _ = fixture(tmp_path)
    primary = cmd(root, "symbolic-ref", "--short", "HEAD")
    cmd(root, "checkout", "-qb", "separate", baseline)
    write(root, "unrelated.txt", b"branch addition\n")
    commit(root, "side branch")
    cmd(root, "checkout", primary)
    subprocess.run(["git", "-C", str(root), "merge", "--no-ff", "-qm", "merge branch",
                    "separate"], check=True, capture_output=True)
    final = cmd(root, "rev-parse", "HEAD")
    with pytest.raises(QGitCustodyHold, match="linear"):
        inspect(root, baseline, final)


def test_q_r1_git_replace_parent_attack_cannot_hide_changed_source(tmp_path):
    root, baseline, _ = fixture(tmp_path)
    write(root, "src/relay_self/resident_cognitive_work_owner_dev.py", b"changed")
    tampered = commit(root, "poison original Owner")
    subprocess.run(["git", "-C", str(root), "replace", "--graft", tampered, baseline],
                   check=True, capture_output=True)
    with pytest.raises(QGitCustodyHold, match="altered"):
        inspect(root, baseline, tampered)


@pytest.mark.parametrize("bad", ("not-a-sha", "0" * 40))
def test_q_r1_unknown_commit_pins_hold(tmp_path, bad):
    root, baseline, final = fixture(tmp_path)
    with pytest.raises(QGitCustodyHold):
        inspect(root, bad, final)
    with pytest.raises(QGitCustodyHold):
        inspect(root, baseline, bad)
