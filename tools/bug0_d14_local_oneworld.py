"""D14 R5: one fresh LocalCodex/WSL World, never a GitHub Actions loop.

This entry is a bounded *local execution wrapper* around the existing
natural R4 run and original S49. It does not create a physical issuer,
change Paper physics, infer S16 outcomes, or retry a World.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adapters.mineflayer.s49_p1_paper_server import PAPER_1218_SHA256, PAPER_1218_SIZE
from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence
from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence
from tools.bug0_d14_natural_active_post import audit_active
from tools.bug0_d14_natural_life import R4_GRANT, R6_GRANT, NaturalLifeLoop
from tools.bug0_d14_natural_world import (
    PLUGIN_NAME,
    R3_ENV,
    R7_EVIDENCE_GRANT,
    marker_kind,
    run,
)
from tools.bug0_d14_r7_evidence_post import inspect_r7_source_only

R5_GRANT = "D14_R5_LOCAL_ONEWORLD_ONLY"
MIN_WATCHDOG = 600
MAX_WATCHDOG = 7200
DEFAULT_WATCHDOG = 3600
EXPECTED_PORT = 25565


class D14LocalRejected(RuntimeError):
    """Refuse dirty checkout, replayed evidence or unverified runtime."""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def _write_json_once(path: Path, obj: dict[str, Any]) -> None:
    with path.open("x", encoding="utf8") as stream:
        json.dump(obj, stream, sort_keys=True, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def validate_watchdog(seconds: object) -> int:
    if type(seconds) is not int or not MIN_WATCHDOG <= seconds <= MAX_WATCHDOG:
        raise D14LocalRejected("BOUNDED_LOCAL_WATCHDOG_600_TO_7200_SECONDS_REQUIRED")
    return seconds


def validate_local_checkout(repo: Path, exact_head: str) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", exact_head) is None:
        raise D14LocalRejected("EXACT_40_HEX_GIT_HEAD_REQUIRED")
    root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout.strip()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout
    if Path(root).resolve() != repo.resolve() or head != exact_head or dirty:
        raise D14LocalRejected("WRONG_HEAD_OR_UNCOMMITTED_LOCALCODEX_CHANGES")


def validate_local_sources(
    *, repo: Path, output_dir: Path, paper: Path, plugin: Path,
    exact_head: str, watchdog: int, environment: dict[str, str],
    check_checkout: bool = True, check_port: bool = True,
) -> dict[str, Any]:
    """All checks occur *before* creating evidence or a Minecraft World."""
    validate_watchdog(watchdog)
    if any(environment.get(key) != "1" for key in (*R3_ENV, R4_GRANT, R5_GRANT)):
        raise D14LocalRejected("R3_R4_AND_LOCAL_R5_ONE_WORLD_GRANTS_REQUIRED")
    if environment.get("NODE_OPTIONS") is not None:
        raise D14LocalRejected("NODE_OPTIONS_INJECTION_REFUSED")
    if environment.get(R7_EVIDENCE_GRANT) == "1" and (
        environment.get(R6_GRANT) != "1"
        or environment.get("D7_PASSIVE_CONTROLS_WORLD_ONLY") != "1"
    ):
        raise D14LocalRejected("R7_SOURCE_CAPTURE_REQUIRES_R6_AND_S50_DEV_GRANTS")
    repo = repo.resolve(strict=True)
    if check_checkout:
        validate_local_checkout(repo, exact_head)
    if output_dir.is_symlink() or output_dir.exists():
        raise D14LocalRejected("EVIDENCE_DIRECTORY_MUST_NOT_ALREADY_EXIST")
    if not output_dir.parent.is_dir() or output_dir.parent.is_symlink():
        raise D14LocalRejected("EVIDENCE_PARENT_MUST_BE_EXISTING_REAL_DIRECTORY")
    dest = output_dir.resolve(strict=False)
    if dest == repo or repo in dest.parents:
        raise D14LocalRejected("EVIDENCE_MUST_BE_OUTSIDE_REPOSITORY")
    if (
        not paper.is_file() or paper.is_symlink()
        or paper.stat().st_size != PAPER_1218_SIZE
        or _sha256(paper) != PAPER_1218_SHA256
    ):
        raise D14LocalRejected("PINNED_PAPER_1218_SOURCE_INVALID")
    if (
        not plugin.is_file() or plugin.is_symlink()
        or plugin.name != PLUGIN_NAME
        or re.fullmatch(r"[0-9a-f]{64}", environment.get("D14_R3_RESPAWN_SHA256", ""))
            is None
        or _sha256(plugin) != environment["D14_R3_RESPAWN_SHA256"]
    ):
        raise D14LocalRejected("PINNED_RESPAWN_PLUGIN_SOURCE_INVALID")
    if (
        Path(environment.get("D14_R3_PAPER_JAR", "")).resolve() != paper.resolve()
        or Path(environment.get("D14_R3_RESPAWN_JAR", "")).resolve()
            != plugin.resolve()
    ):
        raise D14LocalRejected("RUNNER_JAR_ENV_AND_VALIDATED_PATH_DIFFER")
    if check_port:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", EXPECTED_PORT)) == 0:
                raise D14LocalRejected("LOCAL_MINECRAFT_PORT_ALREADY_OCCUPIED")
    return {
        "source_head": exact_head,
        "paper_sha256": PAPER_1218_SHA256,
        "plugin_sha256": environment["D14_R3_RESPAWN_SHA256"],
        "max_wall_seconds": watchdog,
        "run_scope": "ONE_LOCAL_WORLD_NO_AUTO_RETRY",
        "world_rules": "NATURAL_SURVIVAL_MANAGED_ZOMBIE_600_TICKS",
        "physical_issuer": "ORIGINAL_S49_ONLY",
        "classification": "DEV_ONLY_QUALIFICATION_NO_GO_SCIENCE_NOT_RUN",
        "r6_original_s49_motion_opt_in": environment.get(R6_GRANT) == "1",
        "r7_source_capture_opt_in": environment.get(R7_EVIDENCE_GRANT) == "1",
    }


def source_only_partial(evidence: Path) -> dict[str, Any]:
    """Read actual retained originals; NEVER turn an incomplete run into PASS."""
    paper = evidence / "paper_original.log"
    journal = evidence / "d14_natural_events.jsonl"
    fence_path = evidence / "original_s49_nonmotion_fence.json"
    report_path = evidence / "report.json"
    lines = paper.read_text(encoding="utf8", errors="replace").splitlines() if paper.exists() else []
    kinds = [marker_kind(line) for line in lines]
    source = {
        "status": "PARTIAL_SOURCE_ONLY_NOT_QUALIFIED",
        "paper_original_present": paper.is_file(),
        "paper_start_markers": kinds.count("START"),
        "paper_limit_markers": kinds.count("LIMIT"),
        "paper_early_terminals": kinds.count("TERMINAL"),
        "paper_world_fault_markers": kinds.count("WORLD_FAULT"),
        "paper_checkpoints": kinds.count("SAMPLE"),
        "paper_zombie_deaths": kinds.count("ZOMBIE_DEATH"),
        "paper_zombie_respawns": kinds.count("ZOMBIE_RESPAWN"),
        "journal_present": journal.is_file(),
        "report_present": report_path.is_file(),
        "original_nonmotion_fence_present": fence_path.is_file(),
        "learned_skill_proven": False,
        "long_run_survival_proven": False,
    }
    if journal.is_file():
        event_counts: dict[str, int] = {}
        parse_error = False
        for line in journal.read_text(encoding="utf8", errors="replace").splitlines():
            try:
                event = json.loads(line)
                kind = event.get("kind")
                if type(kind) is not str:
                    raise ValueError("missing source kind")
                event_counts[kind] = event_counts.get(kind, 0) + 1
            except (json.JSONDecodeError, ValueError):
                parse_error = True
        source["derivative_event_counts"] = event_counts
        source["derivative_has_invalid_records"] = parse_error
    if report_path.is_file():
        try:
            report = json.loads(report_path.read_text(encoding="utf8"))
            source["original_report_status"] = report.get("status")
            source["original_report_failure"] = report.get("failure")
            source["reported_action_count_unattested"] = report.get("new_s49_actions")
            source["reported_experience_count_unattested"] = report.get("c1_intent_experiences")
        except (OSError, ValueError):
            source["report_unreadable"] = True
    if fence_path.is_file():
        try:
            fence = OriginalS49NonMotionFence.restore(
                fence_path, self_id="s49-original-self",
            )
            source["original_nonmotion_records"] = len(fence.actions)
            source["original_nonmotion_unresolved"] = fence.unresolved
            source["original_nonmotion_fence_sha256"] = fence.sha256
        except (OSError, ValueError) as exc:
            source["original_nonmotion_fence_read_failure"] = type(exc).__name__
    motion_path = evidence / "original_s49_motion_fence.json"
    source["r7_raw_node_stdout_present"] = (
        evidence / "w3-node-stdout.raw.jsonl"
    ).is_file()
    source["r7_s50_same_client_readback_present"] = (
        evidence / "r7-s50-client-readback.jsonl"
    ).is_file()
    source["original_motion_fence_present"] = motion_path.is_file()
    if motion_path.is_file():
        try:
            motion = OriginalS49PhysicalFence.restore(
                motion_path, self_id="s49-original-self",
            )
            source["original_motion_records"] = len(motion.actions)
            source["original_motion_unresolved"] = motion.unresolved
            source["original_motion_fence_sha256"] = motion.sha256
        except (OSError, ValueError) as exc:
            source["original_motion_fence_read_failure"] = type(exc).__name__
    return source


def write_manifest_once(evidence: Path) -> None:
    """Fsync a simple immutable manifest even on run failure/interruption."""
    rows: list[str] = []
    for path in sorted(evidence.iterdir(), key=lambda f: f.name):
        if path.name == "SHA256SUMS.txt":
            continue
        if path.is_symlink() or not path.is_file():
            raise D14LocalRejected("EVIDENCE_SYMLINK_OR_NONFILE_REFUSED")
        rows.append(f"{_sha256(path)}  {path.name}\n")
    with (evidence / "SHA256SUMS.txt").open("x", encoding="utf8") as stream:
        stream.writelines(rows)
        stream.flush()
        os.fsync(stream.fileno())


def validate_manifest(evidence: Path) -> bool:
    manifest = evidence / "SHA256SUMS.txt"
    if not manifest.is_file() or manifest.is_symlink():
        return False
    lines = manifest.read_text(encoding="utf8").splitlines()
    verified = set()
    for line in lines:
        found = re.fullmatch(r"([0-9a-f]{64})  ([^/\\]+)", line)
        if found is None or found[2] in verified or found[2] == manifest.name:
            return False
        candidate = evidence / found[2]
        if not candidate.is_file() or candidate.is_symlink() or _sha256(candidate) != found[1]:
            return False
        verified.add(found[2])
    return verified == {
        path.name for path in evidence.iterdir() if path.name != manifest.name
    }


async def run_local(
    *, repo: Path, output_dir: Path, paper: Path, plugin: Path,
    exact_head: str, watchdog: int = DEFAULT_WATCHDOG,
) -> int:
    metadata = validate_local_sources(
        repo=repo, output_dir=output_dir, paper=paper, plugin=plugin,
        exact_head=exact_head, watchdog=watchdog, environment=dict(os.environ),
    )
    output_dir.mkdir(mode=0o700, exist_ok=False)
    metadata["local_started_utc"] = datetime.now(timezone.utc).isoformat()
    _write_json_once(output_dir / "local_run_source.json", metadata)
    rc = 2
    try:
        rc = await run(
            output_dir / "report.json",
            output_dir / "paper_original.log",
            output_dir / "d14_natural_events.jsonl",
            life_factory=NaturalLifeLoop, max_wall_seconds=watchdog,
        )
        if rc == 0:
            # Completely separate from the live run. A failed audit cannot
            # rewrite original S49/Paper records or become a PASS.
            try:
                report = json.loads((output_dir / "report.json").read_text(encoding="utf8"))
                fence = OriginalS49NonMotionFence.restore(
                    output_dir / "original_s49_nonmotion_fence.json",
                    self_id="s49-original-self",
                )
                paper_log = output_dir / "paper_original.log"
                derivative = output_dir / "d14_natural_events.jsonl"
                motion_fence = (
                    OriginalS49PhysicalFence.restore(
                        output_dir / "original_s49_motion_fence.json",
                        self_id="s49-original-self",
                    )
                    if os.environ.get(R6_GRANT) == "1" else None
                )
                independent = audit_active(
                    report,
                    paper_log.read_bytes().decode("utf8"),
                    derivative.read_text(encoding="utf8"),
                    fence,
                    original_sha=_sha256(paper_log),
                    derivative_sha=_sha256(derivative),
                    motion_fence=motion_fence,
                )
                _write_json_once(output_dir / "independent_audit.json", independent)
            except Exception as exc:
                rc = 2
                _write_json_once(output_dir / "independent_audit_error.json", {
                    "status": "FAIL",
                    "reason": f"{type(exc).__name__}: {exc}",
                    "original_report_mutated": False,
                })
    finally:
        # This read-only fallback has no qualification or outcome-changing
        # authority. It records original failure/partial evidence as observed.
        try:
            partial = source_only_partial(output_dir)
            _write_json_once(output_dir / "local_partial_source_only.json", partial)
        finally:
            if metadata["r7_source_capture_opt_in"]:
                try:
                    post = inspect_r7_source_only(output_dir)
                    _write_json_once(output_dir / "r7_source_forensics.json", post)
                except Exception as exc:
                    _write_json_once(output_dir / "r7_source_forensics_error.json", {
                        "status": "PARTIAL_SOURCE_ONLY_NOT_QUALIFIED",
                        "error": f"{type(exc).__name__}: {exc}",
                        "physical_result_unresolved": "UNKNOWN",
                        "physical_stop_attested": False,
                        "original_fence_mutated": False,
                    })
            write_manifest_once(output_dir)
    return rc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--expect-head", required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--paper-jar", type=Path, required=True)
    parser.add_argument("--plugin-jar", type=Path, required=True)
    parser.add_argument("--max-wall-seconds", type=int, default=DEFAULT_WATCHDOG)
    args = parser.parse_args()
    try:
        result = asyncio.run(run_local(
            repo=args.repo, output_dir=args.evidence_dir,
            paper=args.paper_jar, plugin=args.plugin_jar,
            exact_head=args.expect_head, watchdog=args.max_wall_seconds,
        ))
    except KeyboardInterrupt:
        # No restart. Evidence is already finalized by run_local's finally
        # if cancellation reached the run, or remains an unqualified partial.
        raise SystemExit(130) from None
    raise SystemExit(result)


if __name__ == "__main__":
    main()
