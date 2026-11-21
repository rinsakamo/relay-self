"""Q1c strict Git-only chronology negatives; local synthetic Git, no real World."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from experiments.q_lane_git_anchor_custody_dev import (
    QGitCustodyHold,
    inspect_git_pre_s2_custody,
)

ANCHOR = "proof/s1-anchor.json"
S2 = "proof/s2-evidence.json"


def _cmd(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def _commit(root: Path, description: str) -> str:
    subprocess.run(
        ["git", "-C", str(root), "add", "-A"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "commit", "-qm", description],
        check=True, capture_output=True,
    )
    return _cmd(root, "rev-parse", "HEAD")


def _write(root: Path, rel: str, data: bytes) -> None:
    f = root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(data)


def _fixture(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    _cmd(root, "config", "user.name", "Q offline fixture")
    _cmd(root, "config", "user.email", "q@example.invalid")
    _write(root, "README.md", b"no source yet\n")
    baseline = _commit(root, "trusted root placeholder (not authenticated)")
    anchor = b'{"self":"A","s1":"terminal","world":"fixture"}\n'
    _write(root, ANCHOR, anchor)
    pre = _commit(root, "synthetic S1 anchor")
    s2 = b'{"self":"A","s2":"new action","world":"fixture"}\n'
    _write(root, S2, s2)
    post = _commit(root, "synthetic S2 evidence")
    kwargs = {
        "trusted_root_sha": baseline,
        "pre_s2_anchor_commit": pre,
        "post_s2_evidence_commit": post,
        "anchor_path": ANCHOR, "s2_path": S2,
        "expected_anchor_sha256": hashlib.sha256(anchor).hexdigest(),
        "expected_s2_sha256": hashlib.sha256(s2).hexdigest(),
    }
    return root, kwargs


def _verify(root, kwargs):
    return inspect_git_pre_s2_custody(root, **kwargs)


def test_q1c_read_only_git_dag_fixture_not_real_temporal_attestation(tmp_path):
    root, kwargs = _fixture(tmp_path)
    before_head = (root / ".git" / "HEAD").read_bytes()
    before_ref = _cmd(root, "rev-parse", "HEAD")
    before = {p.relative_to(root): (p.read_bytes(), p.stat().st_mtime_ns)
              for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}
    receipt = _verify(root, kwargs)
    assert receipt["committed_ancestor_order_verified"] is True
    assert receipt["post_anchor_commit_count"] == 1
    assert receipt["external_root_origin_authenticated"] is False
    assert receipt["anchor_producer_authenticated"] is False
    assert receipt["real_pre_s2_capture_time_verified"] is False
    assert receipt["original_wal_validated"] is False
    assert receipt["real_world_attested"] is False
    assert receipt["qual_go"] is False and receipt["science_run"] is False
    assert _cmd(root, "rev-parse", "HEAD") == before_ref
    assert (root / ".git" / "HEAD").read_bytes() == before_head
    after = {p.relative_to(root): (p.read_bytes(), p.stat().st_mtime_ns)
             for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}
    assert before == after


@pytest.mark.parametrize(("field", "value"), [
    ("trusted_root_sha", "0" * 40),
    ("pre_s2_anchor_commit", "0" * 40),
    ("post_s2_evidence_commit", "0" * 40),
    ("pre_s2_anchor_commit", "not-a-commit"),
    ("anchor_path", "../malicious"),
    ("s2_path", "/absolute/path"),
    ("anchor_path", "bad//double"),
    ("expected_anchor_sha256", "0" * 64),
    ("expected_s2_sha256", "0" * 64),
])
def test_q1c_scope_and_pins_are_fail_closed(tmp_path, field, value):
    root, kwargs = _fixture(tmp_path)
    kwargs[field] = value
    with pytest.raises(QGitCustodyHold):
        _verify(root, kwargs)


def test_q1c_stale_head_refuses_even_with_existing_commit(tmp_path):
    root, kwargs = _fixture(tmp_path)
    _write(root, "new.txt", b"new head\n")
    _commit(root, "advance HEAD")
    with pytest.raises(QGitCustodyHold, match="HEAD"):
        _verify(root, kwargs)


def test_q1c_anchor_must_precede_s2_and_be_distinct_commit(tmp_path):
    root, kwargs = _fixture(tmp_path)
    kwargs["pre_s2_anchor_commit"] = kwargs["post_s2_evidence_commit"]
    with pytest.raises(QGitCustodyHold):
        _verify(root, kwargs)
    root, kwargs = _fixture(tmp_path / "different")
    kwargs["pre_s2_anchor_commit"] = kwargs["trusted_root_sha"]
    with pytest.raises(QGitCustodyHold):
        _verify(root, kwargs)


def test_q1c_s2_existing_at_pre_anchor_is_refused(tmp_path):
    root, kwargs = _fixture(tmp_path)
    # The post-S2 commit itself cannot serve as the pre-S2 anchor.
    kwargs["pre_s2_anchor_commit"] = kwargs["post_s2_evidence_commit"]
    with pytest.raises(QGitCustodyHold):
        _verify(root, kwargs)


def test_q1c_stable_blob_across_intermediate_commits_allowed(tmp_path):
    root, kwargs = _fixture(tmp_path)
    parent_post = kwargs["post_s2_evidence_commit"]
    _cmd(root, "reset", "--hard", kwargs["pre_s2_anchor_commit"])
    _write(root, "docs/other.md", b"innocent middle commit\n")
    _commit(root, "unrelated intervening record")
    _write(root, S2, (root / S2).read_bytes() if (root / S2).exists() else
           b'{"self":"A","s2":"new action","world":"fixture"}\n')
    kwargs["post_s2_evidence_commit"] = _commit(root, "later S2")
    assert kwargs["post_s2_evidence_commit"] != parent_post
    receipt = _verify(root, kwargs)
    assert receipt["post_anchor_commit_count"] == 2


def test_q1c_intermediate_anchor_change_then_restore_still_hold(tmp_path):
    root, kwargs = _fixture(tmp_path)
    _cmd(root, "reset", "--hard", kwargs["pre_s2_anchor_commit"])
    original = (root / ANCHOR).read_bytes()
    _write(root, ANCHOR, b"attacker edits anchor\n")
    _commit(root, "tainted earlier anchor")
    _write(root, ANCHOR, original)
    _commit(root, "revert anchor mutation")
    _write(root, S2, b'{"self":"A","s2":"new action","world":"fixture"}\n')
    kwargs["post_s2_evidence_commit"] = _commit(root, "later S2 record")
    with pytest.raises(QGitCustodyHold, match="anchor disappeared or changed"):
        _verify(root, kwargs)


def test_q1c_post_commit_must_introduce_s2_not_only_restate(tmp_path):
    root, kwargs = _fixture(tmp_path)
    _write(root, "extra", b"new metadata")
    kwargs["post_s2_evidence_commit"] = _commit(root, "later metadata only")
    with pytest.raises(QGitCustodyHold, match="predates"):
        _verify(root, kwargs)


def test_q1c_original_anchor_symlink_is_not_admitted(tmp_path):
    root, kwargs = _fixture(tmp_path)
    _cmd(root, "reset", "--hard", kwargs["trusted_root_sha"])
    _write(root, "secret", b"not real")
    p = root / ANCHOR
    p.parent.mkdir(parents=True, exist_ok=True)
    p.symlink_to(root / "secret")
    kwargs["pre_s2_anchor_commit"] = _commit(root, "symlink placeholder")
    _write(root, S2, b'{"self":"A","s2":"new action","world":"fixture"}\n')
    kwargs["post_s2_evidence_commit"] = _commit(root, "s2")
    with pytest.raises(QGitCustodyHold, match="missing/symlinked"):
        _verify(root, kwargs)


def test_q1c_compromised_git_root_and_pins_do_not_authenticate_producer(tmp_path):
    """Demonstrates false trust if attacker controls whole Git history."""
    root, kwargs = _fixture(tmp_path)
    receipt = _verify(root, kwargs)
    assert receipt["committed_ancestor_order_verified"]
    assert receipt["external_root_origin_authenticated"] is False
    assert receipt["anchor_producer_authenticated"] is False
    assert receipt["real_pre_s2_capture_time_verified"] is False


def test_q1c_merge_history_rejected_even_when_files_and_sha_agree(tmp_path):
    root, kwargs = _fixture(tmp_path)
    pre = kwargs["pre_s2_anchor_commit"]
    _cmd(root, "checkout", "-q", "-b", "other", pre)
    _write(root, "another.txt", b"other source\n")
    _commit(root, "other source branch")
    _cmd(root, "checkout", "-q", "-b", "mainline", pre)
    _write(root, "own.txt", b"local source\n")
    _commit(root, "local source branch")
    subprocess.run(
        ["git", "-C", str(root), "merge", "--no-ff", "-m", "merge two branches", "other"],
        check=True, capture_output=True,
    )
    _write(root, S2, b'{"self":"A","s2":"new action","world":"fixture"}\n')
    kwargs["post_s2_evidence_commit"] = _commit(root, "S2 after merge")
    with pytest.raises(QGitCustodyHold, match="non-merge|custody branch"):
        _verify(root, kwargs)


def test_q1c_overlarge_anchor_object_is_not_loaded(tmp_path):
    root, kwargs = _fixture(tmp_path)
    _cmd(root, "reset", "--hard", kwargs["trusted_root_sha"])
    oversized = b"X" * (2 * 1024 * 1024 + 1)
    _write(root, ANCHOR, oversized)
    kwargs["pre_s2_anchor_commit"] = _commit(root, "oversized pre-anchor")
    kwargs["expected_anchor_sha256"] = hashlib.sha256(oversized).hexdigest()
    _write(root, S2, b'{"self":"A","s2":"new action","world":"fixture"}\n')
    kwargs["post_s2_evidence_commit"] = _commit(root, "later S2")
    with pytest.raises(QGitCustodyHold, match="oversized"):
        _verify(root, kwargs)
