"""I1+C+I4a real-chain PRE_WORLD entrypoint: inspect only, never boot.

This is deliberately not the existing I4a synthetic S2 issuer and grants no
real-world, native, GPU, or Physical privilege. The real S2 issuer and
independent S1/S2/T1/T2 source witnesses do not exist in this integration
yet; no combination of CLI flags can turn this into a running World.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


class I1CI4APreWorldHold(RuntimeError):
    """Original HEAD/source prerequisite absent; no World may be started."""


_REQUIRED_SOURCE = (
    "src/relay_self/i_lane_i1_normal_runtime_dev.py",
    "src/relay_self/i_lane_i4a_s2_first_native_move_dev.py",
    "src/relay_self/i_lane_i4a_s2_first_physical_reservation_dev.py",
    "src/relay_self/i_lane_i4a_s2_run_boundary_dev.py",
    "src/relay_self/i_lane_i4a_live_wal_anchor_dev.py",
    "src/relay_self/i_lane_i4a_s1_source_capture_dev.py",
    "src/relay_self/i_lane_i4a_s1_native_source_audit_dev.py",
    "src/relay_self/i_lane_i4a_s1_native_command_audit_dev.py",
    "src/relay_self/c_lane_l1_evaluation_engine_dev.py",
    "src/relay_self/physical_issue_admission_dev.py",
    "src/relay_self/physical_action_journal.py",
    "src/relay_self/paper_tick_witness_dev.py",
    "src/relay_self/world_resident_lifecycle_dev.py",
    "src/relay_self/self_owner_checkpoint_dev.py",
    "src/relay_self/checkpointed_cognitive_runtime_dev.py",
    "adapters/mineflayer/process_session.py",
    "adapters/llama_cpp/relay_engine.py",
)

# Each must have an independent, runtime-grounded source, not a synthetic flag.
_UNMET_LIVE_ADMISSIONS = (
    "live_original_s2_issuer_not_integrated",
    "s1_s2_authenticated_wal_boundary_not_real_world_attested",
    "native_paper_same_world_source_not_live_attested",
    "gpu_pid_gguf_single_slot_not_live_attested",
    "peer_self_and_independent_t1_t2_not_live_attested",
)


@dataclass(frozen=True, slots=True)
class I1CI4APreWorldReceipt:
    classification: str
    integration_head: str
    source_sha256: dict[str, str]
    blockers: tuple[str, ...]
    world_started: bool = False
    model_posts: int = 0
    physical_actions: int = 0
    live_admission: bool = False


def inspect_i1_c_i4a_preworld(
    *, repo_root: Path, expected_head: str,
) -> I1CI4APreWorldReceipt:
    """Read-only exact-HEAD prerequisite inventory, NEVER a launch permit.

    The file hashes establish local code identity only. They do not attest
    Native/Paper, a model POST, WAL provenance, or the next S2 Action.
    """
    if (
        not isinstance(repo_root, Path)
        or not repo_root.is_dir()
        or not isinstance(expected_head, str)
        or re.fullmatch(r"[0-9a-f]{40}", expected_head) is None
    ):
        raise I1CI4APreWorldHold("PRE_WORLD exact repo and commit required")
    try:
        git = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise I1CI4APreWorldHold("original source HEAD unavailable") from exc
    if git.returncode != 0 or git.stdout.strip() != expected_head:
        raise I1CI4APreWorldHold("original integration HEAD changed or unauthenticated")
    # HEAD alone is insufficient: a same-HEAD dirty or untracked source must
    # not be reported as the original integration code.
    try:
        tracked = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "--error-unmatch",
             "--", *_REQUIRED_SOURCE],
            capture_output=True, text=True, check=False, timeout=10,
        )
        clean = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--quiet", "HEAD",
             "--", *_REQUIRED_SOURCE],
            capture_output=True, text=True, check=False, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise I1CI4APreWorldHold("original source working tree unavailable") from exc
    if tracked.returncode != 0 or clean.returncode != 0:
        raise I1CI4APreWorldHold("original source not tracked and clean at HEAD")
    source: dict[str, str] = {}
    for rel in _REQUIRED_SOURCE:
        item = repo_root / rel
        # No symlinked intermediary can silently substitute inspected source.
        cursor = item
        while cursor != repo_root:
            if cursor.is_symlink():
                raise I1CI4APreWorldHold("source has symlinked ancestor")
            cursor = cursor.parent
        if not item.is_file():
            raise I1CI4APreWorldHold("original I1/C/I4a source file unavailable")
        try:
            current_bytes = item.read_bytes()
            committed = subprocess.run(
                ["git", "-C", str(repo_root), "cat-file", "blob", f"HEAD:{rel}"],
                capture_output=True, check=False, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise I1CI4APreWorldHold("committed source blob unavailable") from exc
        # git diff --quiet can be fooled by assume-unchanged / skip-worktree.
        # Compare actual bytes to the *committed* blob, not the Git index.
        if committed.returncode != 0 or committed.stdout != current_bytes:
            raise I1CI4APreWorldHold("committed source blob differs from working tree")
        source[rel] = hashlib.sha256(current_bytes).hexdigest()
    return I1CI4APreWorldReceipt(
        "I1_C_I4A_PRE_WORLD_HOLD",
        expected_head, source, _UNMET_LIVE_ADMISSIONS,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="I1+C+I4a PRE_WORLD code inspection; no launch")
    p.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--expected-head", required=True)
    p.add_argument("--world-dir", type=Path)
    p.add_argument("--real-world-dev-grant", action="store_true")
    p.add_argument("--accepted-eula", action="store_true")
    args = p.parse_args(argv)
    try:
        receipt = inspect_i1_c_i4a_preworld(
            repo_root=args.repo_root, expected_head=args.expected_head,
        )
    except I1CI4APreWorldHold as exc:
        print(f"I1_C_I4A_PRE_WORLD_HOLD: {exc}", file=sys.stderr)
        return 2
    # Grants/EULA consent are acknowledged, but this entrypoint has no launch
    # path even if provided. world-dir is intentionally never created/touched.
    print(json.dumps(asdict(receipt), sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
