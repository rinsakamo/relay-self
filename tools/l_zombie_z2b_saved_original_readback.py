"""Read-only replay of saved Z2b originals; never launch a model or World.

CI validates archived bytes and arithmetic only. Historical local /proc and
cleanup receipts cannot attest a current physical runtime from CI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.l_zombie_z2b_paper_policy_audit import audit_prepared_l2_world
from tools.l_zombie_z2b_prepare_gemma import verify_prepared_archive


def readback(root: Path) -> dict:
    root = root.absolute()
    manifest = json.loads((root / "SHA256SUMS.json").read_text())
    for relative, expected in manifest.items():
        path = root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("unsafe archived path")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"saved original SHA mismatch: {relative}")
    prior_a, = (root / "priors/z1b").rglob("paper-console-original.raw")
    prior_b, = (root / "priors/z2a").rglob("paper-console-original.raw")
    paper, = (root / "world-evidence").rglob("paper-console-original.raw")
    prepared = verify_prepared_archive(
        prepared_root=root / "gemma-preparation",
        z1b_original=prior_a, z2a_original=prior_b,
    )
    result = audit_prepared_l2_world(
        paper.read_bytes(), sha256=hashlib.sha256(paper.read_bytes()).hexdigest(),
        marker="z1-source-1", session="z1-client-1", prepared=prepared,
    )
    result["model_original_wire_cryptographically_joined_by_this_parser"] = True
    saved = json.loads((root / "independent-prepared-world-audit.json").read_text())
    if json.loads(json.dumps(result)) != saved:
        raise ValueError("saved independent report differs from original replay")
    identity = json.loads((root / "model-process-identity.json").read_text())
    if "/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf" not in identity["maps"]:
        raise ValueError("historical GGUF mapping missing")
    model_sha = json.loads((root / "model-files.sha256.json").read_text())
    if model_sha["/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf"] != (
        "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
    ):
        raise ValueError("historical model SHA differs")
    slots = json.loads((root / "slots.json").read_text())
    if len(slots) != 1 or slots[0]["n_ctx"] != 8192:
        raise ValueError("historical context/slot differs")
    if "build 10874" not in (root / "llama-version.txt").read_text():
        raise ValueError("historical build differs")
    custody = json.loads((root / "independent-custody-cleanup.json").read_text())
    for key in (
        "java_node_model_pid_absent", "ports_8080_25565_released", "world_deleted",
        "prior_all_files_unchanged", "protected_main_checkout_unchanged",
        "java_paper_plugin_custody", "gemma_response_before_world_start",
    ):
        if custody[key] is not True:
            raise ValueError(f"historical custody receipt failed: {key}")
    return {
        "classification": "SAVED_Z2B_ORIGINAL_REPLAY_PASS_NOT_LIVE_ATTESTATION",
        "archived_files_checked": len(manifest),
        "prepared_policy_error_m": result["prepared_policy_error_m"],
        "new_model_calls": 0, "new_worlds": 0,
        "client_tick_join": "CLIENT_TICK_JOIN_UNATTESTED",
        "qualification": "QUALIFICATION_NO_GO", "science": "SCIENCE_NOT_RUN",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(readback(args.evidence_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
