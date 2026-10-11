"""RSEE R1: read-only S/L/V environment selection, never an execution grant.

Reuse existing preflight, Golden host probes and pinned World verifier. This
adapter owns no process, lease, cognition, physical trial or evidence bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
from pathlib import Path
from typing import Any

from experiments.standard_env.golden_admission import verify_qualified_world
from experiments.standard_env.golden_host_gate import (
    LLAMA_SERVER_SHA256,
    _git_dirty,
    _git_head,
    _port_listeners,
)
from experiments.standard_env.node_runtime import verify_node_runtime
from experiments.standard_env.preflight import (
    PROFILE,
    REPO_ROOT,
    read_profile,
    verify_local,
)
from experiments.standard_env.world_binding import JAR_SHA256

ROOT = Path("/home/rinsa/.local/share/relay-self/rsee-1.0-20261011")
DEFAULT_GGUF = Path("/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf")
DEFAULT_LLAMA = Path("/home/rinsa/src/llama.cpp/build/bin/llama-server")
LANES = ("S", "L", "V")
SHA = re.compile(r"[0-9a-f]{64}\Z")
HEAD = re.compile(r"[0-9a-f]{40}\Z")
SCHEMA = "RSEE_R1_PROVENANCE_V1"


class SharedRuntimeRejected(ValueError):
    """Insufficient or inconsistent read-only environment evidence."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SharedRuntimeRejected(message)


def _digest(path: Path) -> str:
    with path.open("rb") as handle:
        digest = hashlib.sha256()
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_output(path: Path, repo: Path, base: Path) -> bool:
    """Fresh physical evidence destination, never inside a checkout or assets."""
    if not path.is_absolute() or path.exists() or path.is_symlink():
        return False
    if not path.parent.is_dir() or not stat.S_ISDIR(path.parent.lstat().st_mode):
        return False
    try:
        parts = [path.parent, *path.parent.parents]
        if any(parent.is_symlink() for parent in parts):
            return False
        actual_parent = path.parent.resolve(strict=True)
        checkout = repo.resolve(strict=True)
        runtime = base.resolve(strict=True)
        if actual_parent.is_relative_to(checkout):
            return False
        if actual_parent.is_relative_to(runtime):
            # Shared runtime data are immutable; only derived evidence is writable.
            evidence = (runtime / "evidence").resolve(strict=True)
            if not actual_parent.is_relative_to(evidence):
                return False
        return True
    except OSError:
        return False


def plan(lane: str, *, repo: Path = REPO_ROOT,
         base: Path = ROOT, profile_path: Path = PROFILE) -> dict[str, Any]:
    """Side-effect-free planning; source observations are not host qualification."""
    _require(lane in LANES, "unknown lane")
    profile, profile_sha = read_profile(profile_path)
    return {
        "classification": "RSEE_R1_PLAN_ONLY",
        "lane": lane,
        "environment_root": str(base),
        "profile_path": str(profile_path),
        "profile_sha256": profile_sha,
        "profile_qualification": profile["qualification"],
        "worktree": str(repo),
        "source_head": "UNKNOWN_NOT_READ_IN_PLAN",
        "python": str(base / "venv/bin/python"),
        "python_prefix": str(base / "venv"),
        "node_runtime_root": str(base / "npm-mineflayer-4.39.0"),
        "node_executable": "UNKNOWN_NOT_PROBED",
        "llama_server": str(DEFAULT_LLAMA),
        "llama_server_expected_sha256": LLAMA_SERVER_SHA256,
        "gguf": str(DEFAULT_GGUF),
        "gguf_expected_sha256": profile["llm"]["model_sha256"],
        "minecraft_jar": str(base / "minecraft-1.21.8.jar"),
        "minecraft_jar_expected_sha256": JAR_SHA256,
        "world_snapshot": str(base / "bootstrap-approved-20261011-once/snapshot"),
        "world_manifest": str(base / "bootstrap-approved-20261011-once/snapshot_manifest.json"),
        "initial_native": str(base / "bootstrap-approved-20261011-once/initial_native_observation.json"),
        "world_seed": 575,
        "minecraft_version": profile["minecraft"]["version"],
        "gpu_cuda_observation": "UNKNOWN",
        "lease_observation": "UNKNOWN",
        "resource_ownership": {
            "gpu_lease_key": profile["resource_key"],
            "lease_owner": "EXISTING_PRODUCT_OWNER_NOT_R",
            "model_process_owner": "EXISTING_SELF_OWNED_LLAMA",
            "minecraft_process_owner": "EXISTING_S49_WORLD_OWNER",
            "node_process_owner": "EXISTING_MINEFLAYER_SESSION_OWNER",
            "r_lane_owned_processes": 0,
            "stop_ack": "UNKNOWN",
            "slot_released": "UNKNOWN",
            "gpu_quiescent": "UNKNOWN",
            "vram_released": "UNKNOWN",
        },
        "execution_permission": "NOT_CONVEYED_BY_R1",
        "physical_execution_authorized": False,
        "science_qualified": False,
        "side_effects": "NONE",
    }


def preflight(
    lane: str, *, expected_head: str, evidence_dir: Path,
    repo: Path = REPO_ROOT, base: Path = ROOT, profile_path: Path = PROFILE,
    gguf: Path = DEFAULT_GGUF, llama_server: Path = DEFAULT_LLAMA,
    node_runtime_root: Path | None = None, jar: Path | None = None,
    snapshot: Path | None = None, manifest: Path | None = None,
    initial_native: Path | None = None,
) -> dict[str, Any]:
    """Reuse owner-local offline validators without launching a new runtime."""
    _require(lane in LANES, "unknown lane")
    _require(bool(HEAD.fullmatch(expected_head)), "exact expected HEAD required")
    planned = plan(lane, repo=repo, base=base, profile_path=profile_path)
    node_root = node_runtime_root or base / "npm-mineflayer-4.39.0"
    jar_path = jar or base / "minecraft-1.21.8.jar"
    snapshot_path = snapshot or base / "bootstrap-approved-20261011-once/snapshot"
    manifest_path = manifest or base / "bootstrap-approved-20261011-once/snapshot_manifest.json"
    native_path = initial_native or base / "bootstrap-approved-20261011-once/initial_native_observation.json"
    errors: list[str] = []
    observed = _git_head(repo)
    if observed != expected_head:
        errors.append("EXACT_HEAD_MISMATCH")
    if _git_dirty(repo):
        errors.append("WORKTREE_TRACKED_DIRTY")
    if not _safe_output(evidence_dir, repo, base):
        errors.append("EVIDENCE_OUTPUT_UNSAFE_OR_ALREADY_EXISTS")
    if os.environ.get("NODE_OPTIONS") or os.environ.get("NODE_PATH"):
        errors.append("NODE_RUNTIME_OVERRIDE_PRESENT")
    if Path(sys.executable).absolute() != (base / "venv/bin/python").absolute():
        errors.append("NONCANONICAL_PYTHON_INTERPRETER")
    if Path(sys.prefix).resolve() != (base / "venv").resolve():
        errors.append("NONCANONICAL_PYTHON_PREFIX")
    if not node_root.is_absolute():
        errors.append("NONCANONICAL_NODE_ROOT")
    if node_root.absolute() != (base / "npm-mineflayer-4.39.0").absolute():
        errors.append("NONCANONICAL_NODE_ROOT")
    node_identity: dict[str, Any] = {}
    try:
        node_identity = verify_node_runtime(node_root, repo / "adapters/mineflayer")
    except (OSError, ValueError) as exc:
        errors.append("NODE_IDENTITY_UNVERIFIED:" + type(exc).__name__)
    actual_preflight = verify_local(
        profile_path,
        model=str(gguf),
        llama_server=str(llama_server),
        llama_sha256=LLAMA_SERVER_SHA256,
        minecraft_jar=str(jar_path),
        minecraft_sha256=JAR_SHA256,
        mineflayer_root=repo / "adapters/mineflayer",
        verify_product=True,
        node_runtime_root=node_root,
    )
    if actual_preflight["classification"] != "RSEE_LOCAL_FILES_VERIFIED_NOT_PHYSICALLY_QUALIFIED":
        errors.append("EXISTING_PREFLIGHT_BLOCKED")
    errors.extend("EXISTING_PREFLIGHT:" + item for item in actual_preflight["errors"])
    world: dict[str, Any] = {}
    try:
        bound = verify_qualified_world(jar_path, snapshot_path, manifest_path, native_path)
        world = {
            "jar_sha256": bound.jar_sha256,
            "manifest_sha256": bound.manifest_sha256,
            "native_initial_sha256": bound.initial_evidence_sha256,
            "snapshot_files": len(bound.files),
            "qualification_scope": "STOPPED_WORLD_BYTES_ONLY",
        }
    except (OSError, ValueError) as exc:
        errors.append("WORLD_BYTES_UNVERIFIED:" + type(exc).__name__)
    try:
        listeners = sorted({1234, 25565} & _port_listeners())
        if listeners:
            errors.append("MODEL_OR_WORLD_PORT_IN_USE_NO_R_OWNERSHIP")
    except (OSError, ValueError) as exc:
        listeners = "UNKNOWN"
        errors.append("PORT_OBSERVATION_UNAVAILABLE:" + type(exc).__name__)
    return {
        **planned,
        "classification": (
            "RSEE_R1_PREFLIGHT_BLOCKED" if errors
            else "RSEE_R1_FILES_READY_NOT_AUTHORIZED"
        ),
        "source_head": observed,
        "expected_head": expected_head,
        "worktree_tracked_clean": "WORKTREE_TRACKED_DIRTY" not in errors,
        "python_observed": sys.executable,
        "python_prefix_observed": sys.prefix,
        "node_executable_observed": shutil.which("node") or "UNKNOWN",
        "node_identity": node_identity,
        "preflight_classification": actual_preflight["classification"],
        "world_observation": world,
        "gpu_cuda_observation": "UNKNOWN",
        "port_listeners": listeners,
        "evidence_output": str(evidence_dir),
        "evidence_output_created": False,
        "errors": sorted(set(errors)),
        "physical_execution_authorized": False,
        "science_qualified": False,
        "side_effects": "NO_INSTALL_NO_SERVER_NO_WORLD_NO_MODEL",
    }


def read_only_receipt_index(references: dict[str, Path]) -> dict[str, str]:
    """Hash existing raw receipts without editing them or inventing missing ones."""
    result: dict[str, str] = {}
    for name, path in sorted(references.items()):
        _require(isinstance(name, str) and bool(name), "receipt name required")
        _require(isinstance(path, Path) and path.is_absolute(), "absolute raw receipt required")
        _require(not path.is_symlink() and path.is_file(), "original receipt missing or symlinked")
        _require(stat.S_ISREG(path.lstat().st_mode), "nonregular receipt rejected")
        result[str(path)] = _digest(path)
    return result


def validate_evidence(record: dict[str, Any], *, verify_receipts: bool = False) -> None:
    """Validate a provenance envelope only, never certify Action or science."""
    fields = {
        "schema", "lane", "source_head", "environment_profile_sha256",
        "source_session", "world_identity", "model_identity",
        "original_receipt_refs", "action_outcome_refs",
        "cleanup_observations", "terminal_classification",
        "evidence_sha256_index", "physical_execution_authorized",
        "science_qualified", "timeline_is_physical_proof",
    }
    _require(type(record) is dict and set(record) == fields, "evidence fields not exact")
    _require(record["schema"] == SCHEMA and record["lane"] in LANES, "evidence schema/lane invalid")
    _require(isinstance(record["source_head"], str)
             and bool(HEAD.fullmatch(record["source_head"])), "source HEAD missing")
    _require(isinstance(record["environment_profile_sha256"], str)
             and bool(SHA.fullmatch(record["environment_profile_sha256"])), "profile SHA missing")
    _require(isinstance(record["terminal_classification"], str)
             and bool(record["terminal_classification"].strip()), "first terminal required")
    _require(record["physical_execution_authorized"] is False
             and record["science_qualified"] is False
             and record["timeline_is_physical_proof"] is False,
             "R1 evidence may not convey grants, science or timeline proof")
    _require(isinstance(record["source_session"], (str, type(None)))
             and isinstance(record["world_identity"], (dict, type(None)))
             and isinstance(record["model_identity"], (dict, type(None))),
             "unknown identity must be null, not fabricated")
    _require(type(record["original_receipt_refs"]) is list
             and type(record["action_outcome_refs"]) is list
             and type(record["cleanup_observations"]) is dict
             and type(record["evidence_sha256_index"]) is dict, "evidence provenance shape invalid")
    index = record["evidence_sha256_index"]
    _require(all(isinstance(p, str) and Path(p).is_absolute()
                 and isinstance(s, str) and SHA.fullmatch(s)
                 for p, s in index.items()), "SHA256 index invalid")
    all_refs = record["original_receipt_refs"] + record["action_outcome_refs"]
    for ref in all_refs:
        _require(type(ref) is dict and set(ref) == {"path", "sha256"}
                 and ref["path"] in index and index[ref["path"]] == ref["sha256"],
                 "original Action/receipt reference missing in index")
    if verify_receipts:
        _require(read_only_receipt_index({str(i): Path(p) for i, p in enumerate(index)}) == index,
                 "source receipt bytes differ from SHA256 index")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", choices=LANES, required=True)
    parser.add_argument("--verify-local", action="store_true")
    parser.add_argument("--expected-head")
    parser.add_argument("--new-evidence-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.verify_local:
            _require(bool(args.expected_head and args.new_evidence_dir),
                     "--verify-local requires HEAD and fresh evidence destination")
            result = preflight(
                args.lane, expected_head=args.expected_head,
                evidence_dir=args.new_evidence_dir,
            )
        else:
            _require(args.expected_head is None and args.new_evidence_dir is None,
                     "host verification inputs require --verify-local")
            result = plan(args.lane)
    except (OSError, ValueError) as exc:
        result = {
            "classification": "RSEE_R1_PREFLIGHT_BLOCKED",
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "physical_execution_authorized": False,
            "science_qualified": False,
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result["classification"] in {
        "RSEE_R1_PLAN_ONLY", "RSEE_R1_FILES_READY_NOT_AUTHORIZED",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
