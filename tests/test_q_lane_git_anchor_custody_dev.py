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
    with pytest.raises(QGitCustodyHold, match="predates|existed before final"):
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


def test_q1d_anchor_was_committed_earlier_than_declared_capture(tmp_path):
    """Earlier anchor byte history must not be relabeled as a later S1 cut."""
    root, kwargs = _fixture(tmp_path)
    _cmd(root, "reset", "--hard", kwargs["trusted_root_sha"])
    _write(root, ANCHOR, b'{"self":"A","s1":"terminal","world":"fixture"}\n')
    _commit(root, "first actual anchor")
    _write(root, "middle.txt", b"unrelated git activity\n")
    kwargs["pre_s2_anchor_commit"] = _commit(root, "later falsely claimed S1 cut")
    _write(root, S2, b'{"self":"A","s2":"new action","world":"fixture"}\n')
    kwargs["post_s2_evidence_commit"] = _commit(root, "S2 later")
    with pytest.raises(QGitCustodyHold, match="anchor existed before selected"):
        _verify(root, kwargs)


def test_q1d_s2_appeared_and_disappeared_before_declared_s1(tmp_path):
    """Root -> pre history must exclude ANY earlier S2 presence."""
    root, kwargs = _fixture(tmp_path)
    _cmd(root, "reset", "--hard", kwargs["trusted_root_sha"])
    _write(root, S2, b'{"self":"A","s2":"new action","world":"fixture"}\n')
    _commit(root, "earlier S2, attacker would like to hide this")
    (root / S2).unlink()
    _commit(root, "delete earlier S2")
    _write(root, ANCHOR, b'{"self":"A","s1":"terminal","world":"fixture"}\n')
    kwargs["pre_s2_anchor_commit"] = _commit(root, "later S1 anchor")
    _write(root, S2, b'{"self":"A","s2":"new action","world":"fixture"}\n')
    kwargs["post_s2_evidence_commit"] = _commit(root, "S2 reintroduced")
    with pytest.raises(QGitCustodyHold, match="S2 evidence appeared before S1"):
        _verify(root, kwargs)


def test_q1d_s2_appeared_and_disappeared_between_pre_and_post(tmp_path):
    """Checking only the immediately preceding commit misses an earlier S2."""
    root, kwargs = _fixture(tmp_path)
    _cmd(root, "reset", "--hard", kwargs["pre_s2_anchor_commit"])
    _write(root, S2, b'{"self":"A","s2":"new action","world":"fixture"}\n')
    _commit(root, "previously committed S2 before declared post")
    (root / S2).unlink()
    _commit(root, "hide S2 evidence in intermediate commit")
    _write(root, S2, b'{"self":"A","s2":"new action","world":"fixture"}\n')
    kwargs["post_s2_evidence_commit"] = _commit(root, "re-introduced late S2")
    with pytest.raises(QGitCustodyHold, match="S2 evidence existed before final"):
        _verify(root, kwargs)


def test_q1d_merge_history_before_anchor_cannot_be_laundered(tmp_path):
    root, kwargs = _fixture(tmp_path)
    original_root = kwargs["trusted_root_sha"]
    _cmd(root, "checkout", "-q", "-b", "branch-with-untrusted-history", original_root)
    _write(root, "alien.txt", b"branch A\n")
    _commit(root, "branch A")
    _cmd(root, "checkout", "-q", "-b", "root-to-pre", original_root)
    _write(root, "local.txt", b"branch B\n")
    _commit(root, "branch B")
    subprocess.run(
        ["git", "-C", str(root), "merge", "--no-ff", "-m", "merge B and A",
         "branch-with-untrusted-history"],
        check=True, capture_output=True,
    )
    _write(root, ANCHOR, b'{"self":"A","s1":"terminal","world":"fixture"}\n')
    kwargs["pre_s2_anchor_commit"] = _commit(root, "S1 after multi-parent history")
    _write(root, S2, b'{"self":"A","s2":"new action","world":"fixture"}\n')
    kwargs["post_s2_evidence_commit"] = _commit(root, "later S2")
    with pytest.raises(QGitCustodyHold, match="linear non-merge"):
        _verify(root, kwargs)


def test_q1d_pre_anchor_history_is_bounded(tmp_path, monkeypatch):
    from experiments import q_lane_git_anchor_custody_dev as custody

    root, kwargs = _fixture(tmp_path)
    _cmd(root, "reset", "--hard", kwargs["trusted_root_sha"])
    _write(root, "first.txt", b"intermediate\n")
    _commit(root, "root-to-pre intermediate")
    _write(root, ANCHOR, b'{"self":"A","s1":"terminal","world":"fixture"}\n')
    kwargs["pre_s2_anchor_commit"] = _commit(root, "S1 anchor")
    _write(root, S2, b'{"self":"A","s2":"new action","world":"fixture"}\n')
    kwargs["post_s2_evidence_commit"] = _commit(root, "S2")
    monkeypatch.setattr(custody, "_MAX_COMMITS", 1)
    with pytest.raises(QGitCustodyHold, match="bounded linear source custody"):
        _verify(root, kwargs)


def test_q1d_head_ref_changes_during_inspection_fail_closed(tmp_path, monkeypatch):
    from experiments import q_lane_git_anchor_custody_dev as custody

    root, kwargs = _fixture(tmp_path)
    original_run = custody._run
    observations = 0

    def reroute_head(*args):
        nonlocal observations
        if len(args) >= 3 and args[1:] == ("rev-parse", "HEAD"):
            observations += 1
            if observations == 2:
                return b"f" * 40 + b"\n"
        return original_run(*args)

    monkeypatch.setattr(custody, "_run", reroute_head)
    with pytest.raises(QGitCustodyHold, match="HEAD changed during"):
        _verify(root, kwargs)
    assert observations == 2


def test_q1d_hidden_anchor_blob_alias_before_declared_birth_is_rejected(tmp_path):
    root, kwargs = _fixture(tmp_path)
    _cmd(root, "reset", "--hard", kwargs["trusted_root_sha"])
    anchor_data = b'{"self":"A","s1":"terminal","world":"fixture"}\n'
    _write(root, "hidden/prior-anchor-bytes.data", anchor_data)
    _commit(root, "prior byte-identical S1 source using other path")
    _write(root, ANCHOR, anchor_data)
    kwargs["pre_s2_anchor_commit"] = _commit(root, "later claimed S1 birth")
    _write(root, S2, b'{"self":"A","s2":"new action","world":"fixture"}\n')
    kwargs["post_s2_evidence_commit"] = _commit(root, "later S2")
    with pytest.raises(QGitCustodyHold, match="anchor existed before selected"):
        _verify(root, kwargs)


def test_q1d_hidden_s2_bytes_at_pre_anchor_are_rejected(tmp_path):
    root, kwargs = _fixture(tmp_path)
    _cmd(root, "reset", "--hard", kwargs["trusted_root_sha"])
    anchor_data = b'{"self":"A","s1":"terminal","world":"fixture"}\n'
    s2_data = b'{"self":"A","s2":"new action","world":"fixture"}\n'
    _write(root, ANCHOR, anchor_data)
    _write(root, "hidden/s2-under-other-name.data", s2_data)
    kwargs["pre_s2_anchor_commit"] = _commit(root, "pre stage hides later S2")
    (root / "hidden/s2-under-other-name.data").unlink()
    _commit(root, "drop hidden S2")
    _write(root, S2, s2_data)
    kwargs["post_s2_evidence_commit"] = _commit(root, "visible later S2")
    with pytest.raises(QGitCustodyHold, match="source bytes existed in earlier"):
        _verify(root, kwargs)


def test_q1d_transient_renamed_s2_blob_after_anchor_is_rejected(tmp_path):
    root, kwargs = _fixture(tmp_path)
    _cmd(root, "reset", "--hard", kwargs["pre_s2_anchor_commit"])
    s2_data = b'{"self":"A","s2":"new action","world":"fixture"}\n'
    _write(root, "hidden/pre-final-s2.data", s2_data)
    _commit(root, "S2 data existed under different path")
    (root / "hidden/pre-final-s2.data").unlink()
    _commit(root, "remove previous S2 alias")
    _write(root, S2, s2_data)
    kwargs["post_s2_evidence_commit"] = _commit(root, "S2 at final asserted path")
    with pytest.raises(QGitCustodyHold, match="S2 evidence existed before final"):
        _verify(root, kwargs)


def test_q1k_replacement_ref_cannot_launder_git_parent_history(tmp_path, monkeypatch):
    """Replacing an original merge parent with an invented linear history
    cannot cause the Q verifier to admit the forged replacement graph."""
    root, kwargs = _fixture(tmp_path)
    pre = kwargs["pre_s2_anchor_commit"]
    _cmd(root, "checkout", "-q", "-b", "q1k-side", pre)
    _write(root, "side.txt", b"side history\n")
    _commit(root, "side")
    _cmd(root, "checkout", "-q", "-b", "q1k-main", pre)
    _write(root, "main.txt", b"main history\n")
    _commit(root, "main")
    subprocess.run(
        ["git", "-C", str(root), "merge", "--no-ff", "-m", "merge", "q1k-side"],
        check=True, capture_output=True,
    )
    merge = _cmd(root, "rev-parse", "HEAD")
    _write(root, S2, b'{"self":"A","s2":"new action","world":"fixture"}\n')
    kwargs["post_s2_evidence_commit"] = _commit(root, "S2 after real merge")
    # An attacker can create a refs/replace object that conceals the merge
    # and makes ordinary rev-list report a single parent for its same SHA.
    _cmd(root, "replace", "--graft", merge, pre)
    assert len(_cmd(root, "rev-list", "--parents", "-n", "1", merge).split()) == 2
    monkeypatch.setenv("GIT_REPLACE_REF_BASE", "refs/replace")
    with pytest.raises(QGitCustodyHold, match="linear non-merge"):
        _verify(root, kwargs)


def test_q1k_legacy_info_grafts_always_hold(tmp_path):
    root, kwargs = _fixture(tmp_path)
    git_dir = Path(_cmd(root, "rev-parse", "--absolute-git-dir"))
    graft = git_dir / "info" / "grafts"
    graft.parent.mkdir(exist_ok=True)
    graft.write_text(
        f"{kwargs['post_s2_evidence_commit']} {kwargs['pre_s2_anchor_commit']}\n",
    )
    with pytest.raises(QGitCustodyHold, match="grafts"):
        _verify(root, kwargs)


def test_q1k_empty_graft_file_is_not_a_parent_rewrite(tmp_path):
    root, kwargs = _fixture(tmp_path)
    git_dir = Path(_cmd(root, "rev-parse", "--absolute-git-dir"))
    graft = git_dir / "info" / "grafts"
    graft.parent.mkdir(exist_ok=True)
    graft.write_bytes(b"")
    assert _verify(root, kwargs)["committed_ancestor_order_verified"] is True


def test_q1k_symlinked_graft_path_hold(tmp_path):
    root, kwargs = _fixture(tmp_path)
    git_dir = Path(_cmd(root, "rev-parse", "--absolute-git-dir"))
    graft = git_dir / "info" / "grafts"
    graft.parent.mkdir(exist_ok=True)
    target = tmp_path / "forged-grafts"
    target.write_text("")
    graft.symlink_to(target)
    with pytest.raises(QGitCustodyHold, match="grafts"):
        _verify(root, kwargs)
