"""Q1c read-only Git ancestry custody of a PRE-S2 anchor and later S2 file.

This is NOT a cryptographic signature, independently vouched producer identity,
physical time-stamp, live native/Paper source or true S1->S2 authorization.
Git commit DAG ordering is the only temporal ordering this inspector knows.
It does not create commits, snapshots, trusted pins or any original evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


class QGitCustodyHold(ValueError):
    """The claimed historical anchor / S2 Git object chain is not qualified."""


_SHA = re.compile(r"[0-9a-f]{40}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PATH = re.compile(r"[A-Za-z0-9_.\-/]+\Z")
_MAX_OBJECT = 2 * 1024 * 1024
_MAX_COMMITS = 128


def _commit_id(value: object) -> str:
    if type(value) is not str or _SHA.fullmatch(value) is None:
        raise QGitCustodyHold("exact committed Git SHA required")
    return value


def _path(value: object) -> str:
    if (
        type(value) is not str or _PATH.fullmatch(value) is None
        or value.startswith("/") or "//" in value
        or any(segment in (".", "..", "") for segment in value.split("/"))
    ):
        raise QGitCustodyHold("bounded relative Git artifact path required")
    return value


def _run(root: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False, capture_output=True, timeout=20,
            env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise QGitCustodyHold("Git read-only inspection unavailable") from exc
    if result.returncode != 0:
        raise QGitCustodyHold("requested immutable Git object/ancestry unavailable")
    return result.stdout


def _assert_unmodified_parent_graph(root: Path) -> None:
    """Fail closed on Git grafts; ignore object replacement in all reads.

    GIT_NO_REPLACE_OBJECTS blocks refs/replace, including environment-selected
    replacement namespaces. Legacy info/grafts rewrites parent history too,
    even with replacement disabled, so any nonempty graft file is a HOLD.
    This is only a local DAG integrity gate, not Git producer authentication.
    """
    try:
        path = _run(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
        graft = Path(path.decode("utf-8").strip()) / "info" / "grafts"
        if graft.is_symlink() or (graft.is_file() and graft.stat().st_size):
            raise QGitCustodyHold("legacy Git grafts can rewrite historical parent custody")
    except (UnicodeError, OSError) as exc:
        raise QGitCustodyHold("Git graft path cannot be independently inspected") from exc


def _entries(root: Path, commit: str) -> dict[str, tuple[str, str]]:
    entries: dict[str, tuple[str, str]] = {}
    raw = _run(root, "ls-tree", "-rz", "--full-tree", commit)
    for item in raw.split(b"\0"):
        if not item:
            continue
        try:
            head, path = item.split(b"\t", 1)
            mode, kind, blob = head.split(b" ", 2)
            label = path.decode("utf-8")
            if kind != b"blob" or len(blob) != 40:
                raise ValueError("not a standard file")
        except (UnicodeError, ValueError) as exc:
            raise QGitCustodyHold("ambiguous/non-file Git tree entry") from exc
        if label in entries:
            raise QGitCustodyHold("duplicate Git tree file path")
        entries[label] = (mode.decode("ascii"), blob.decode("ascii"))
    return entries


def _regular(entries: dict[str, tuple[str, str]], path: str) -> str:
    mode, blob = entries.get(path, ("", ""))
    if mode not in ("100644", "100755") or _SHA.fullmatch(blob) is None:
        raise QGitCustodyHold("required committed artifact missing/symlinked")
    return blob


def _any_path_has_blob(entries: dict[str, tuple[str, str]], blob: str) -> bool:
    """Detect an earlier byte-identical evidence object hidden under any path.

    Git object hashes identify the same byte sequence even after moving or
    copying it to a different file. Path-only birth checks are insufficient.
    """
    return any(seen_blob == blob for _mode, seen_blob in entries.values())


def _object(root: Path, sha: str) -> bytes:
    length = _run(root, "cat-file", "-s", sha)
    try:
        size = int(length)
    except ValueError as exc:
        raise QGitCustodyHold("Git source object length unavailable") from exc
    if not 0 < size <= _MAX_OBJECT:
        raise QGitCustodyHold("oversized or empty Git source object")
    raw = _run(root, "cat-file", "blob", sha)
    if len(raw) != size:
        raise QGitCustodyHold("Git source object changed during read")
    return raw


def _single_parent(root: Path, commit: str) -> str:
    parents = _run(root, "rev-list", "--parents", "-n", "1", commit).decode("ascii").split()
    if len(parents) != 2 or parents[0] != commit:
        raise QGitCustodyHold("linear non-merge history required for source custody")
    return parents[1]


def _linear_custody_chain(root: Path, *, ancestor: str, descendant: str) -> list[str]:
    """Return a bounded, unmerged first-parent chain AFTER ancestor.

    A Git ancestor check alone permits side branches and merges. Require that
    every commit on the admitted chain has exactly one parent and that it
    reaches the expected earlier commit without silently skipping history.
    """
    current = descendant
    reverse: list[str] = []
    while current != ancestor:
        if len(reverse) >= _MAX_COMMITS:
            raise QGitCustodyHold("bounded linear source custody chain required")
        reverse.append(current)
        current = _single_parent(root, current)
    if not reverse:
        raise QGitCustodyHold("distinct start and end commits required")
    return list(reversed(reverse))


def inspect_git_pre_s2_custody(
    repo_root: Path, *, trusted_root_sha: str, pre_s2_anchor_commit: str,
    post_s2_evidence_commit: str, anchor_path: str, s2_path: str,
    expected_anchor_sha256: str, expected_s2_sha256: str,
) -> dict[str, object]:
    """Require an intact in-Git anchor before a later committed S2 artifact.

    The caller must independently establish Git remote identity and trusted
    root/pins; this function does not claim it can authenticate that origin.
    """
    if not isinstance(repo_root, Path) or not repo_root.is_dir():
        raise QGitCustodyHold("Git repository root unavailable")
    _assert_unmodified_parent_graph(repo_root)
    root = _commit_id(trusted_root_sha)
    pre = _commit_id(pre_s2_anchor_commit)
    post = _commit_id(post_s2_evidence_commit)
    anchor_name, s2_name = _path(anchor_path), _path(s2_path)
    if (
        len({root, pre, post}) != 3 or anchor_name == s2_name
        or type(expected_anchor_sha256) is not str
        or _SHA256.fullmatch(expected_anchor_sha256) is None
        or type(expected_s2_sha256) is not str
        or _SHA256.fullmatch(expected_s2_sha256) is None
    ):
        raise QGitCustodyHold("distinct exact pre/post commits and external SHA pins required")
    if _run(repo_root, "rev-parse", "HEAD").decode("ascii").strip() != post:
        raise QGitCustodyHold("exact post-S2 evidence HEAD is not checked out")
    _run(repo_root, "merge-base", "--is-ancestor", root, pre)
    _run(repo_root, "merge-base", "--is-ancestor", pre, post)

    original = _entries(repo_root, root)
    initial = _entries(repo_root, pre)
    final = _entries(repo_root, post)
    if anchor_name in original or s2_name in original or s2_name in initial:
        raise QGitCustodyHold("trusted root/pre-S2 commit already contains later evidence")
    anchor_blob = _regular(initial, anchor_name)
    s2_blob = _regular(final, s2_name)
    if (
        _any_path_has_blob(original, anchor_blob)
        or _any_path_has_blob(original, s2_blob)
        or _any_path_has_blob(initial, s2_blob)
    ):
        raise QGitCustodyHold("source bytes existed in earlier root/pre-anchor tree")
    if _regular(final, anchor_name) != anchor_blob:
        raise QGitCustodyHold("historical anchor blob changed in S2 evidence commit")
    # The selected PRE commit must INTRODUCE the anchor, not simply contain
    # an old anchor introduced earlier and renamed as the alleged capture
    # point. Likewise no S2 evidence may appear and disappear before S1.
    before_chain = _linear_custody_chain(
        repo_root, ancestor=root, descendant=pre,
    )
    for sha in before_chain[:-1]:
        old = _entries(repo_root, sha)
        if anchor_name in old or _any_path_has_blob(old, anchor_blob):
            raise QGitCustodyHold("pre-S2 anchor existed before selected anchor commit")
        if s2_name in old or _any_path_has_blob(old, s2_blob):
            raise QGitCustodyHold("S2 evidence appeared before S1 anchor commit")
    # Preserve the exact anchor blob through EVERY commit after capture.
    # Reject an S2 file added, removed, and re-added at the final commit.
    chain = _linear_custody_chain(repo_root, ancestor=pre, descendant=post)
    for sha in chain:
        current = _entries(repo_root, sha)
        if _regular(current, anchor_name) != anchor_blob:
            raise QGitCustodyHold("pre-S2 anchor disappeared or changed in custody chain")
        if sha != post and (
            s2_name in current or _any_path_has_blob(current, s2_blob)
        ):
            raise QGitCustodyHold("S2 evidence existed before final evidence commit")
    previous = _entries(repo_root, _single_parent(repo_root, post))
    if s2_name in previous:
        raise QGitCustodyHold("S2 evidence file predates supposed post-S2 commit")
    if hashlib.sha256(_object(repo_root, anchor_blob)).hexdigest() != expected_anchor_sha256:
        raise QGitCustodyHold("pre-S2 anchor blob differs from caller-held SHA pin")
    if hashlib.sha256(_object(repo_root, s2_blob)).hexdigest() != expected_s2_sha256:
        raise QGitCustodyHold("S2 evidence blob differs from caller-held SHA pin")
    if _run(repo_root, "rev-parse", "HEAD").decode("ascii").strip() != post:
        raise QGitCustodyHold("exact HEAD changed during read-only custody inspection")
    return {
        "classification": "Q1C_GIT_DAG_PRE_S2_BLOB_CUSTODY_CPU_OFFLINE_DEV",
        "trusted_root_sha": root,
        "pre_s2_anchor_commit": pre,
        "post_s2_evidence_commit": post,
        "anchor_path": anchor_name,
        "anchor_sha256": expected_anchor_sha256,
        "s2_path": s2_name,
        "s2_sha256": expected_s2_sha256,
        "pre_anchor_commit_count": len(before_chain),
        "post_anchor_commit_count": len(chain),
        "anchor_first_introduced_at_selected_commit": True,
        "s2_first_introduced_at_selected_commit": True,
        "byte_identical_aliases_before_selected_commits_absent": True,
        "committed_ancestor_order_verified": True,
        "git_object_sha256_consistent": True,
        "external_root_origin_authenticated": False,
        "anchor_producer_authenticated": False,
        "real_pre_s2_capture_time_verified": False,
        "owner_checkpoint_semantics_verified": False,
        "original_wal_validated": False,
        "real_world_attested": False,
        "qual_go": False,
        "science_run": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--trusted-root-sha", required=True)
    parser.add_argument("--pre-s2-anchor-commit", required=True)
    parser.add_argument("--post-s2-evidence-commit", required=True)
    parser.add_argument("--anchor-path", required=True)
    parser.add_argument("--s2-path", required=True)
    parser.add_argument("--expected-anchor-sha256", required=True)
    parser.add_argument("--expected-s2-sha256", required=True)
    args = parser.parse_args()
    try:
        receipt = inspect_git_pre_s2_custody(
            args.repo_root, trusted_root_sha=args.trusted_root_sha,
            pre_s2_anchor_commit=args.pre_s2_anchor_commit,
            post_s2_evidence_commit=args.post_s2_evidence_commit,
            anchor_path=args.anchor_path, s2_path=args.s2_path,
            expected_anchor_sha256=args.expected_anchor_sha256,
            expected_s2_sha256=args.expected_s2_sha256,
        )
    except (QGitCustodyHold, OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({"classification": "Q1C_GIT_CUSTODY_HOLD", "reason": str(exc)}))
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
