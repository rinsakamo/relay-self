"""Q independent R2-0 committed Git provenance and bounded authority audit.

Uses exact R1 and R2-0 Git objects, never modifying a worktree or World.
This syntax/ancestry check does not prove a running World or approve R2 routing.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

from experiments.q_lane_git_anchor_custody_dev import (
    QGitCustodyHold,
    _assert_unmodified_parent_graph,
    _commit_id,
    _entries,
    _linear_custody_chain,
    _object,
    _regular,
    _run,
)
from experiments.q_lane_r1_u31_git_static_compat_dev import _inspect_static_shadow_source

R1_SHA = "06349c7a216b042511a90e05ad0196f4a7164378"
R2_SHA = "a8d1492a1e54f3f647109da183cf71179c7b5932"
R1_SHADOW = "src/relay_self/r1_owner_context_shadow_dev.py"
R2_HELPER = "src/relay_self/r2_present_responsibility_boundary_dev.py"
NEW = frozenset({
    R2_HELPER,
    "tests/test_r2_present_responsibility_boundary_dev.py",
    "docs/architecture/r2-0-original-owner-present-responsibility-dev.md",
})
ALLOWED = NEW | {R1_SHADOW}
EXPECTED_CODES = (
    "LEGACY_SOURCE_DIFFERS_FROM_R1_CURRENT",
    "LEGACY_SCHEMA_DIFFERS_FROM_R1_CURRENT",
    "LEGACY_SELF_OR_WORLD_SCOPE_MISMATCH",
    "LEGACY_NATIVE_PAPER_REVISION_MISMATCH",
    "LEGACY_OWNER_EPOCH_MISMATCH",
    "LEGACY_REGISTRY_REVISION_MISMATCH",
    "LEGACY_SCHEMA_SIGNAL_MISMATCH",
    "LEGACY_NEED_REFERENCE_MISMATCH",
    "LEGACY_ATTENTION_REFERENCE_MISMATCH",
)
DENY_CALLS = frozenset({
    "open", "exec", "eval", "compile", "__import__", "setattr", "delattr",
    "save_persistent_cognition", "retain_memory", "commit_memory_from_work",
    "start_skill", "complete_intent", "commit_intent", "issue_action",
    "submit", "send", "write_bytes", "write_text", "unlink", "mkdir",
    "fence_self", "run", "subprocess",
})


class QR20Hold(QGitCustodyHold):
    """Do not classify an R2-0 revision as independent CPU PASS."""


def _source_check(helper_bytes: bytes, shadow_bytes: bytes) -> None:
    if not helper_bytes or len(helper_bytes) > 100_000:
        raise QR20Hold("missing or oversized pure helper")
    try:
        tree = ast.parse(helper_bytes.decode("utf-8"))
        shadow = ast.parse(shadow_bytes.decode("utf-8"))
    except (UnicodeError, SyntaxError) as exc:
        raise QR20Hold("unparseable R2-0 code") from exc
    # Only the R2 helper owns the nine comparisons; the R1 diagnostic and
    # cached validity check must both call it, so they cannot drift separately.
    defs = {
        n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    if set(defs) != {"legacy_current_mismatch_codes"}:
        raise QR20Hold("new helper contains extra execution entrypoints")
    fn = defs["legacy_current_mismatch_codes"]
    if not isinstance(fn, ast.FunctionDef):
        raise QR20Hold("helper cannot be asynchronous")
    codes = next(
        (n.value for n in tree.body if isinstance(n, ast.Assign)
         and any(isinstance(t, ast.Name) and t.id == "R2_LEGACY_CURRENT_DIAGNOSTIC_CODES"
                 for t in n.targets)),
        None,
    )
    if not isinstance(codes, ast.Tuple) or tuple(
        n.value for n in codes.elts if isinstance(n, ast.Constant)
    ) != EXPECTED_CODES or len(codes.elts) != len(EXPECTED_CODES):
        raise QR20Hold("the nine original mismatch codes changed")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = (
                [x.name for x in node.names] if isinstance(node, ast.Import)
                else [node.module or ""] + [x.name for x in node.names]
            )
            if isinstance(node, ast.Import) or node.level != 0 or any(
                "physical" in n or "native_runner" in n or "llama" in n
                or n.startswith(("os", "socket", "subprocess", "torch", "threading"))
                for n in names
            ):
                raise QR20Hold("new helper imports execution authority")
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, (ast.Attribute, ast.Subscript)) for t in targets):
                raise QR20Hold("new helper writes foreign object or index")
        if isinstance(node, (ast.Delete, ast.Global, ast.Nonlocal, ast.With, ast.AsyncWith)):
            raise QR20Hold("new helper mutates external state")
        if isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
            if name in DENY_CALLS:
                raise QR20Hold("new helper calls an owner/issuer/writer")
    defs_shadow = {
        n.name: n for n in shadow.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    for name in ("compare_original_owner_r1_shadow", "r1_shadow_is_live"):
        if name not in defs_shadow:
            raise QR20Hold("original R1 public entrypoint removed")
        calls = [
            n for n in ast.walk(defs_shadow[name]) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "legacy_current_mismatch_codes"
        ]
        if len(calls) != 1:
            raise QR20Hold("R1 initial and cached check must each call the one pure helper")
    _inspect_static_shadow_source(shadow_bytes)


def inspect_r2_0_git(repo_root: Path) -> dict[str, object]:
    if not isinstance(repo_root, Path) or not repo_root.is_dir():
        raise QR20Hold("Git checkout missing")
    before_head = _run(repo_root, "rev-parse", "HEAD").decode("ascii").strip()
    _assert_unmodified_parent_graph(repo_root)
    before = _entries(repo_root, _commit_id(R1_SHA))
    after = _entries(repo_root, _commit_id(R2_SHA))
    if not NEW.isdisjoint(before) or R1_SHADOW not in before:
        raise QR20Hold("R1/R2-0 base path mismatch")
    chain = _linear_custody_chain(
        repo_root, ancestor=_commit_id(R1_SHA), descendant=_commit_id(R2_SHA),
    )
    for commit in chain:
        current = _entries(repo_root, commit)
        if (
            set(before) - set(current)
            or set(current) - set(before) - NEW
            or any(current.get(path) != blob for path, blob in before.items()
                   if path != R1_SHADOW)
            or current[R1_SHADOW][0] != before[R1_SHADOW][0]
        ):
            raise QR20Hold("R1 pre-existing runtime source changed outside Shadow")
    if (
        set(after) - set(before) != NEW
        or after[R1_SHADOW] == before[R1_SHADOW]
        or any(after[p][0] != "100644" for p in NEW)
    ):
        raise QR20Hold("R2-0 exact 4-path source boundary changed")
    for path in NEW:
        _object(repo_root, _regular(after, path))
    _source_check(
        _object(repo_root, _regular(after, R2_HELPER)),
        _object(repo_root, _regular(after, R1_SHADOW)),
    )
    if _run(repo_root, "rev-parse", "HEAD").decode("ascii").strip() != before_head:
        raise QR20Hold("inspector changed checked-out HEAD")
    return {
        "classification": "Q_R2_0_ACTUAL_PINNED_GIT_AND_STATIC_CPU_PASS",
        "r1_commit": R1_SHA, "r2_0_commit": R2_SHA,
        "linear_r2_0_commit_count": len(chain),
        "unmodified_r1_preexisting_path_count": len(before) - 1,
        "new_paths": sorted(NEW),
        "modified_paths": [R1_SHADOW],
        "original_owner_native_physical_wal_source_unchanged": True,
        "initial_and_cached_legacy_checks_shared": True,
        "original_u31_wsl_raw_readback_repeated": False,
        "r2_l1_input_switched": False,
        "physical_authorized": False,
        "qual_go": False, "science_run": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", required=True, type=Path)
    args = p.parse_args()
    try:
        result = inspect_r2_0_git(args.repo_root)
    except (QGitCustodyHold, ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({"classification": "Q_R2_0_GIT_STATIC_HOLD",
                          "reason": str(exc), "qual_go": False, "science_run": False},
                         sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
