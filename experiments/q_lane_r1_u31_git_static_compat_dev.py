"""Q independent Git-tree / static-source read-only audit for R1 on U31.

This can prove a bounded, unchanged committed U31 code baseline and reject
obvious authority-bearing R1 additions. It cannot authenticate real Paper,
Native, model, original Owner, GPU, WAL effects or WSL evidence bytes.
All Git object ancestry/pins are caller-supplied unless externally attested.
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

U31_I_SHA = "d3034026a8eea3d2d4927527f5bc0d6ad0455457"
R1_SHA = "fd2c6862fcb1a7e71211a96d89c287ab3c689677"
Q_SHA = "450734c54e1432ec70a8206952779b5ad82796d8"

NEW_PATHS = frozenset({
    "src/relay_self/r1_owner_context_shadow_dev.py",
    "tests/test_r1_owner_context_shadow_dev.py",
    "docs/architecture/r1-u31-original-owner-context-shadow-dev.md",
})
SOURCE = "src/relay_self/r1_owner_context_shadow_dev.py"
REQUIRED_ENTRYPOINTS = frozenset({
    "compare_original_owner_r1_shadow", "r1_shadow_is_live",
})
REQUIRED_READS = frozenset({
    "read_present_cpu", "read_original_owner_current", "retrieve_original_owner_memory",
    "context_is_live", "load_persistent_cognition",
})
FORBIDDEN_IMPORT_HEADS = frozenset({
    "subprocess", "os", "socket", "ctypes", "importlib", "multiprocessing",
    "asyncio", "threading", "torch",
})
FORBIDDEN_ACTION_CALLS = frozenset({
    "open", "exec", "eval", "compile", "__import__", "setattr", "delattr",
    "save_persistent_cognition", "commit_issuer_adoption", "commit_coverage",
    "retain_memory", "complete_intent", "commit_intent", "start_skill",
    "finish_reviewed_skill", "issue_original_adoption_once", "submit",
    "prepare_place_move", "close_place_move", "fence_self", "send",
    "send_command", "start", "stop", "run", "unlink", "mkdir", "write_bytes",
    "write_text", "replace_file", "open_gpu_ticket",
})


class QR1SourceHold(QGitCustodyHold):
    """R1 Git source/ownership boundary not established; never allow R2."""


def _inspect_static_shadow_source(content: bytes) -> dict[str, object]:
    if not content or len(content) > 256_000:
        raise QR1SourceHold("missing/oversized source cannot be statically audited")
    try:
        tree = ast.parse(content.decode("utf-8"))
    except (UnicodeError, SyntaxError) as exc:
        raise QR1SourceHold("invalid R1 committed Python module") from exc

    declared = {
        n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
    if not REQUIRED_ENTRYPOINTS.issubset(declared) or "R1ShadowComparison" not in classes:
        raise QR1SourceHold("R1 expected read-only entrypoints/result are missing")
    observed_reads: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = {alias.name.split(".", 1)[0] for alias in node.names}
            if roots & FORBIDDEN_IMPORT_HEADS:
                raise QR1SourceHold("unexpected I/O or scheduler import in R1 shadow")
        elif isinstance(node, ast.ImportFrom):
            name = node.module or ""
            if (
                name.split(".", 1)[0] in FORBIDDEN_IMPORT_HEADS
                or any(token in name for token in (
                    "physical_issue", "physical_action", "llama", "gpu_lane",
                    "native_runner", "owned_native", "action_port",
                ))
                or node.level != 0
                or any(alias.name == "*" for alias in node.names)
            ):
                raise QR1SourceHold("shadow imports execution or wildcard authority")
        elif isinstance(node, ast.Call):
            callee = node.func
            name = (callee.id if isinstance(callee, ast.Name)
                    else callee.attr if isinstance(callee, ast.Attribute) else "")
            if name in FORBIDDEN_ACTION_CALLS:
                raise QR1SourceHold("R1 imports/calls a write, GPU or physical function")
            if name in REQUIRED_READS:
                observed_reads.add(name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            # R1 may construct local diagnostics; not assign directly to
            # Owner/Resident/Bridge/provenance attributes or array indexes.
            targets = (node.targets if isinstance(node, ast.Assign)
                       else [node.target])
            if any(isinstance(t, (ast.Attribute, ast.Subscript)) for t in targets):
                raise QR1SourceHold("R1 writes an object field or indexed state")
        elif isinstance(node, (ast.Delete, ast.Global, ast.Nonlocal, ast.ImportFrom)):
            if isinstance(node, (ast.Delete, ast.Global, ast.Nonlocal)):
                raise QR1SourceHold("R1 modifies external/global state")
    if not REQUIRED_READS.issubset(observed_reads):
        raise QR1SourceHold("R1 does not directly use the original read-only source APIs")
    result_cls = classes["R1ShadowComparison"]
    fields = {
        stmt.target.id: stmt.value
        for stmt in result_cls.body
        if isinstance(stmt, ast.AnnAssign)
        and isinstance(stmt.target, ast.Name)
        and stmt.value is not None
    }
    grants = ("l1_input_switched", "physical_authorized", "memory_adopted")
    if any(
        name not in fields or not isinstance(fields[name], ast.Constant)
        or fields[name].value is not False for name in grants
    ):
        raise QR1SourceHold("typed R1 report no-authority defaults were weakened")
    return {
        "shadow_expected_entrypoints_present": True,
        "original_read_only_apis_referenced": True,
        "no_obvious_new_writer_or_issuer_import": True,
        "no_direct_object_state_assignment": True,
        "r1_report_grant_defaults_false": True,
        # This is a syntax-level negative check, NOT an ownership proof.
        "semantic_owner_admission_attested": False,
    }


def inspect_r1_git_compatibility(
    repo_root: Path, *, trusted_u31_i_sha: str, r1_head_sha: str,
) -> dict[str, object]:
    """Read *committed Git objects only*, never checkout, mutate or run a World.

    Both commit IDs are *external inputs* to this verifier. Callers must pin
    them against independently trusted GitHub/worktree identities. A PASS
    does not prove who produced the commits or when real events occurred.
    """
    if type(repo_root) is not Path or not repo_root.is_dir():
        raise QR1SourceHold("original Git object directory unavailable")
    original = _commit_id(trusted_u31_i_sha)
    shadow = _commit_id(r1_head_sha)
    if original == shadow:
        raise QR1SourceHold("R1 must be a distinct committed descendant")
    _assert_unmodified_parent_graph(repo_root)
    before_head = _run(repo_root, "rev-parse", "HEAD").decode("ascii").strip()
    before_original = _entries(repo_root, original)
    after = _entries(repo_root, shadow)
    if not NEW_PATHS.isdisjoint(before_original):
        raise QR1SourceHold("claimed R1-only file already exists at U31 baseline")
    chain = _linear_custody_chain(
        repo_root, ancestor=original, descendant=shadow,
    )
    # Even a temporarily modified, later restored U31 Motor/Owner/WAL file
    # must not pass as an entirely read-only R1 refactoring history.
    for commit in chain:
        entries = _entries(repo_root, commit)
        if (
            set(before_original) - set(entries)
            or any(entries.get(path) != blob for path, blob in before_original.items())
            or set(entries) - set(before_original) - NEW_PATHS
        ):
            raise QR1SourceHold("U31 Original source altered during R1 Git ancestry")
    if set(after) - set(before_original) != NEW_PATHS:
        raise QR1SourceHold("R1 did not add exactly the authorized three files")
    source = _object(repo_root, _regular(after, SOURCE))
    for path in NEW_PATHS:
        if after[path][0] != "100644":
            raise QR1SourceHold("R1 addition is executable, symlinked or nonregular")
        _object(repo_root, _regular(after, path))
    static = _inspect_static_shadow_source(source)
    after_head = _run(repo_root, "rev-parse", "HEAD").decode("ascii").strip()
    if before_head != after_head:
        raise QR1SourceHold("Git inspected HEAD changed during read-only audit")
    return {
        "classification": "Q_R1_U31_GIT_STATIC_COMPAT_CPU_OFFLINE_DEV",
        "u31_i_commit": original,
        "r1_commit": shadow,
        "q_baseline_commit": Q_SHA,
        "linear_r_only_commit_count": len(chain),
        "unchanged_u31_legacy_path_count": len(before_original),
        "added_paths": sorted(NEW_PATHS),
        "original_owner_physical_wal_code_unchanged": True,
        "intermediate_git_source_drift_absent": True,
        **static,
        "original_wsl_u31_raw_evidence_read": False,
        "independent_original_native_paper_custody_verified": False,
        "q_r1_real_world_attested": False,
        "r1_product_runtime_switched": False,
        "r2_migration_approved": False,
        "qual_go": False,
        "science_run": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = inspect_r1_git_compatibility(
            args.repo_root, trusted_u31_i_sha=U31_I_SHA, r1_head_sha=R1_SHA,
        )
    except QGitCustodyHold as exc:
        print(json.dumps({"classification": "Q_R1_U31_GIT_COMPAT_HOLD",
                          "reason": str(exc), "qual_go": False, "science_run": False},
                         sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
