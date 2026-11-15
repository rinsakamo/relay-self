"""#860 P0-D DEV: operator-gated genuine Paper + two Mineflayer process smoke.

This is a *native body* trial. It never creates an L1/L2 Self, restores
cognition/WAL, issues MOVE/EAT/ATTACK, or claims 60-second autosave.
Own only brand-new, disposable, localhost Paper and Mineflayer processes.
On uncertainty leave Paper for operator inspection; never replay effects.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from experiments.p0d_real_paper_smoke_dev import (
    PAPER_1218_60_SHA256,
    RealPaperSmokeRefusal,
    _bootstrap_paper,
    _free_local_port,
    _world_manifest,
    _world_uuid,
    _write_bytes_new,
    file_sha256,
    prepare_assets,
)
from relay_self.checkpoint_stop_neutralization_dev import (
    prepare_stop_before_autosave,
)
from relay_self.owned_native_rejoin_cohort_dev import OwnedNativeRejoinCohort
from relay_self.owned_paper_world_dev import OwnedPaperWorld
from relay_self.paper_tick_witness_dev import PaperMainThreadTickReader
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission


class TwoNativePaperRefusal(RuntimeError):
    """A bounded two-process proof is absent, so no promotion is allowed."""


def two_native_server_properties(port: int) -> str:
    """Offline authentication is restricted to a disposable LOOPBACK server."""
    if type(port) is not int or not 1024 <= port <= 65535:
        raise TwoNativePaperRefusal("local Paper TCP port outside bounded range")
    return (
        "level-name=world\n"
        "server-ip=127.0.0.1\n"
        f"server-port={port}\n"
        "online-mode=false\n"
        "enforce-secure-profile=false\n"
        "enable-rcon=false\n"
        "enable-query=false\n"
        "enable-command-block=false\n"
        "white-list=false\n"
        "max-players=2\n"
        "view-distance=2\n"
        "simulation-distance=2\n"
        "max-world-size=5000\n"
        "spawn-protection=0\n"
        "generate-structures=false\n"
        "difficulty=peaceful\n"
        "gamemode=creative\n"
        "pvp=false\n"
        "network-compression-threshold=256\n"
    )


def _verify_local_runtime(java: str, node: str) -> None:
    """Check runtime and locked adapter before creating any disposable World."""
    for name, executable, required in (
        ("java", java, "21"),
        ("node", node, "22"),
    ):
        if type(executable) is not str or not executable.strip():
            raise TwoNativePaperRefusal(f"explicit {name} executable required")
        try:
            proc = subprocess.run(
                [executable, "-version" if name == "java" else "--version"],
                capture_output=True, text=True, check=True, timeout=8,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise TwoNativePaperRefusal(f"{name} executable unavailable") from exc
        version = (proc.stdout + "\n" + proc.stderr).strip()
        import re

        if not re.search(rf"(?:^|[^0-9])v?{required}(?:\.|\b)", version):
            raise TwoNativePaperRefusal(f"{name} major version must be {required}")
    bridge = Path(__file__).resolve().parents[1] / "adapters" / "mineflayer"
    package = bridge / "node_modules" / "mineflayer" / "package.json"
    if package.is_symlink() or not package.is_file():
        raise TwoNativePaperRefusal(
            "locked mineflayer dependencies absent; npm ci --prefix adapters/mineflayer"
        )
    try:
        version = json.loads(package.read_text(encoding="utf-8"))["version"]
    except (ValueError, KeyError) as exc:
        raise TwoNativePaperRefusal("unreadable locked mineflayer version") from exc
    if version != "4.39.0":
        raise TwoNativePaperRefusal("only locked Mineflayer 4.39.0 allowed")


def preflight_two_native(
    *, paper_jar: Path, paper_sha256: str,
    plugin_jar: Path, plugin_sha256: str,
    scratch_parent: Path, accepted_eula: bool,
    java: str, node: str, timeout_s: float, heap_mb: int,
    check_native_runtime: bool = True,
) -> tuple[Path, Path, Path]:
    """Validate before creating directories, launching, or accepting an EULA."""
    if (
        type(timeout_s) not in (int, float) or not math.isfinite(timeout_s)
        or not 30 <= timeout_s <= 180
        or type(heap_mb) is not int or not 1024 <= heap_mb <= 8192
    ):
        raise TwoNativePaperRefusal("bounded Paper time and heap required")
    paper, plugin, scratch = prepare_assets(
        paper_jar=paper_jar, paper_sha256=paper_sha256,
        plugin_jar=plugin_jar, plugin_sha256=plugin_sha256,
        scratch_parent=scratch_parent, accepted_eula=accepted_eula,
    )
    if paper_sha256 != PAPER_1218_60_SHA256:
        raise TwoNativePaperRefusal(
            "only pinned official Paper 1.21.8 build 60 may launch two native Self"
        )
    if check_native_runtime:
        _verify_local_runtime(java, node)
    return paper, plugin, scratch


def _require_real_two_actor_paper_log(
    owner: OwnedPaperWorld, paper_session: str,
    configs: dict[str, MineflayerLaunchConfig],
) -> str:
    log = owner.read_owned_log(paper_session)
    for config in configs.values():
        marker = (config.username + " joined the game").encode()
        if marker not in log:
            raise TwoNativePaperRefusal(
                "both native player join events not corroborated by owned Paper log"
            )
    return file_sha256(owner.evidence_dir / (paper_session + ".log"))


async def run_native_two_cycle_smoke(
    *, owner: OwnedPaperWorld, native: OwnedNativeRejoinCohort,
    physical: PhysicalIssueAdmission, world_root: Path,
    world_dir: Path, stop_audit_dir: Path, evidence_dir: Path,
    world_id: str, timeout_s: float,
) -> list[dict[str, object]]:
    """Two physical STOP/save windows; no cognitive owner or replay machinery.

    The previous physical gate is released only after both new processes
    proved spawn+probe and rotated. The only permitted subsequent command is
    the next supervised STOP. This does not attest cognitive release safety.
    """
    try:
        return await _execute_native_two_cycle_smoke(
            owner=owner, native=native, physical=physical,
            world_root=world_root, world_dir=world_dir,
            stop_audit_dir=stop_audit_dir, evidence_dir=evidence_dir,
            world_id=world_id, timeout_s=timeout_s,
        )
    except BaseException:
        physical.hold_for_operator()
        raise


async def _execute_native_two_cycle_smoke(
    *, owner: OwnedPaperWorld, native: OwnedNativeRejoinCohort,
    physical: PhysicalIssueAdmission, world_root: Path,
    world_dir: Path, stop_audit_dir: Path, evidence_dir: Path,
    world_id: str, timeout_s: float,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    paper_session = owner.owned_session_id
    if paper_session is None or physical.closed:
        raise TwoNativePaperRefusal("live owned Paper and open native cohort required")
    if tuple(sorted(native.sessions)) != physical.self_roster:
        raise TwoNativePaperRefusal("native cohort must match both physical owners")
    _require_real_two_actor_paper_log(owner, paper_session, native.configs)
    for cycle in range(2):
        native_ids = {
            sid: session.started.session_id for sid, session in native.sessions.items()
        }
        ready = await prepare_stop_before_autosave(
            physical, participants=native.participants_now(),
            audit_dir=stop_audit_dir, timeout_s=min(60.0, timeout_s / 2),
        )
        if ready.verified_self_ids != physical.self_roster:
            raise TwoNativePaperRefusal("full native STOP cohort missing")
        fence = physical.close()
        if ready.fence_ref != fence.fence_ref:
            raise TwoNativePaperRefusal("STOP proof and physical fence refs differ")
        stopped = owner.stop_and_save()
        if (
            stopped.old_server_session_id != paper_session
            or stopped.world_id != world_id
            or stopped.process_exit_code != 0
            or not stopped.tick_source_ref.startswith("paper-main-thread:p0d:")
            or not stopped.all_dimensions_saved
        ):
            raise TwoNativePaperRefusal("native STOP does not match saved Paper process")
        if _world_uuid(world_dir) != world_id:
            raise TwoNativePaperRefusal("Paper World UUID changed during native stop")
        manifests = _world_manifest(world_root)
        snapshot = evidence_dir / f"native-cycle-{cycle + 1}-world"
        snapshot.mkdir(mode=0o700)
        for dimension in ("world", "world_nether", "world_the_end"):
            src = world_root / dimension
            if src.is_dir():
                shutil.copytree(src, snapshot / dimension, symlinks=True)
        if _world_manifest(snapshot) != manifests:
            raise TwoNativePaperRefusal("complete stopped World SHA256 copy mismatch")
        item: dict[str, object] = {
            "cycle": cycle + 1,
            "paper_session_id": paper_session,
            "self_native_sessions": native_ids,
            "stop_fence_ref": ready.fence_ref,
            "stop_verified_receipts": {
                str(p.relative_to(evidence_dir)): file_sha256(p)
                for p in ready.receipt_files
            },
            "paper_tick": stopped.logical_tick,
            "paper_tick_ref": stopped.tick_source_ref,
            "paper_log_ref": stopped.stopped_server_ref,
            "world_files_sha256": manifests,
            "world_snapshot": str(snapshot),
            "same_world_uuid": True,
            "native_issue_authorized_by_smoke": False,
            "cognitive_state_saved": False,
        }
        results.append(item)
        if cycle == 0:
            restarted = owner.restart_same_source_world()
            paper_session = restarted.new_server_session_id
            if (
                paper_session == stopped.old_server_session_id
                or not restarted.server_started
                or restarted.world_id != world_id
            ):
                raise TwoNativePaperRefusal("new Paper process session absent")
            rejoin: dict[str, str] = {}
            for sid in sorted(native.sessions):
                fresh = await asyncio.wait_for(
                    native.prepare_rejoin(sid, paper_session, native_ids[sid]),
                    timeout=min(60.0, timeout_s / 2),
                )
                receipt = native.prepared_receipt(sid, paper_session, native_ids[sid])
                if fresh != receipt.new_native_session_id:
                    raise TwoNativePaperRefusal("fresh native process source mismatch")
                rejoin[sid] = fresh
            item["rejoined_paper_session_id"] = paper_session
            item["native_rejoined_sessions"] = rejoin
            item["paper_rejoin_log_sha256"] = _require_real_two_actor_paper_log(
                owner, paper_session, native.configs,
            )
            for sid, fresh in sorted(rejoin.items()):
                physical.rotate_native_session(
                    fence_ref=fence.fence_ref, self_id=sid,
                    old_session_id=native_ids[sid], new_session_id=fresh,
                )
            physical.release(fence.fence_ref)
            if (
                physical.current_native_sessions != rejoin
                or physical.closed
            ):
                raise TwoNativePaperRefusal("full native-only rebind was not admitted")
    if (
        len(results) != 2
        or results[0]["paper_session_id"] == results[1]["paper_session_id"]
        or results[0]["self_native_sessions"] == results[1]["self_native_sessions"]
        or results[0]["paper_tick_ref"] == results[1]["paper_tick_ref"]
        or owner.owned_session_id is not None
    ):
        raise TwoNativePaperRefusal("second Paper and native two-Self cycle not distinct")
    return results


async def run_real_two_native(
    *, paper_jar: Path, paper_sha256: str, plugin_jar: Path,
    plugin_sha256: str, scratch_parent: Path, accepted_eula: bool,
    java: str = "java", node: str = "node",
    timeout_s: float = 120.0, heap_mb: int = 1536,
) -> Path:
    """Only actual two-session Paper+STOP/save smoke may return a PASS audit."""
    paper, plugin, scratch = preflight_two_native(
        paper_jar=paper_jar, paper_sha256=paper_sha256,
        plugin_jar=plugin_jar, plugin_sha256=plugin_sha256,
        scratch_parent=scratch_parent, accepted_eula=accepted_eula,
        java=java, node=node, timeout_s=timeout_s, heap_mb=heap_mb,
    )
    root = Path(tempfile.mkdtemp(prefix="p0d-real-two-native-", dir=scratch))
    os.chmod(root, 0o700)
    evidence = root / "evidence"
    evidence.mkdir(mode=0o700)
    stop_audit = evidence / "stop"
    stop_audit.mkdir(mode=0o700)
    plugins = root / "plugins"
    plugins.mkdir(mode=0o700)
    shutil.copyfile(paper, root / "paper.jar")
    shutil.copyfile(plugin, plugins / "P0BRecorder.jar")
    _write_bytes_new(root / "eula.txt", b"eula=true\n")
    port = _free_local_port()
    _write_bytes_new(
        root / "server.properties", two_native_server_properties(port).encode(),
    )
    launch = (
        java, "-Xms512M", f"-Xmx{heap_mb}M",
        "-jar", str(root / "paper.jar"), "--nogui",
    )
    report = evidence / "two-native-result.json"
    audit: dict[str, object] = {
        "schema": 1,
        "classification": "HOLD",
        "paper_sha256": paper_sha256,
        "plugin_sha256": plugin_sha256,
        "world_dir": str(root),
        "operator_eula_accepted": True,
        "server_bind": "127.0.0.1",
        "server_port": port,
        "native_usernames": ["RelayA", "RelayB"],
        "native_auth": "offline-localhost-only",
        "real_two_native_sessions": False,
        "real_complete_self_cognition": False,
        "real_60s_autosave": False,
        "real_crash_rollback": False,
        "physical_history_replay": False,
        "steps": [],
    }
    owner: OwnedPaperWorld | None = None
    native: OwnedNativeRejoinCohort | None = None
    opened: dict[str, MineflayerProcessSession] = {}
    physical: PhysicalIssueAdmission | None = None
    try:
        bootstrap = _bootstrap_paper(
            world_root=root, launch=launch, timeout_s=timeout_s,
        )
        audit["bootstrap_log_sha256"] = file_sha256(bootstrap)
        world_dir = root / "world"
        world_id = _world_uuid(world_dir)
        audit["world_uuid"] = world_id
        holder: dict[str, OwnedPaperWorld] = {}
        witness = PaperMainThreadTickReader(
            spool_dir=plugins / "P0BRecorder" / "p0d-ticks",
            expected_world_uuid=world_id,
            read_owned_log=lambda session: holder["world"].read_owned_log(session),
            timeout_seconds=min(15.0, timeout_s / 3),
        )
        owner = OwnedPaperWorld(
            server_dir=root, world_dir=world_dir, evidence_dir=evidence,
            command=launch, world_id=world_id,
            branch_id="p0d-native-only-no-cognitive-generation",
            tick_readback=witness, timeout_seconds=timeout_s,
        )
        holder["world"] = owner
        owner.start_owned()
        configs = {
            sid: MineflayerLaunchConfig(
                host="127.0.0.1", port=port,
                username="Relay" + sid, version="1.21.8",
            ) for sid in ("A", "B")
        }
        for sid, config in sorted(configs.items()):
            opened[sid] = await MineflayerProcessSession.launch(
                config, node_executable=node,
                startup_timeout_s=min(30.0, timeout_s / 3),
            )
        physical = PhysicalIssueAdmission(
            {sid: session.started.session_id for sid, session in opened.items()},
            require_neutral_stop=True,
        )

        async def launch_native(config: MineflayerLaunchConfig) -> MineflayerProcessSession:
            return await MineflayerProcessSession.launch(
                config, node_executable=node,
                startup_timeout_s=min(30.0, timeout_s / 3),
            )

        native = OwnedNativeRejoinCohort(
            sessions=opened, configs=configs, physical=physical,
            launch=launch_native, probe_timeout_s=min(30.0, timeout_s / 3),
        )
        initial = await native.verify_initial_cohort()
        if set(initial) != {"A", "B"}:
            raise TwoNativePaperRefusal("not both real native Self processes verified")
        audit["initial_spawn_probe"] = {
            sid: {"spawn_seq": record[0], "probe_seq": record[1], "request_id": record[2]}
            for sid, record in initial.items()
        }
        audit["steps"] = await run_native_two_cycle_smoke(
            owner=owner, native=native, physical=physical,
            world_root=root, world_dir=world_dir,
            stop_audit_dir=stop_audit, evidence_dir=evidence,
            world_id=world_id, timeout_s=timeout_s,
        )
        audit["real_two_native_sessions"] = True
        audit["classification"] = "REAL_PAPER_TWO_NATIVE_STOP_SAVE_REJOIN_SMOKE_DEV"
    except BaseException as exc:
        audit["reason"] = f"{type(exc).__name__}: {exc}"
        if physical is not None:
            physical.hold_for_operator()
        raise
    finally:
        if native is not None:
            opened.update(native.sessions)
        for session in {id(s): s for s in opened.values()}.values():
            try:
                if session.process_returncode is None:
                    await asyncio.wait_for(session.terminate(), timeout=8.0)
            except BaseException:
                audit["native_cleanup_uncertain"] = True
                audit["classification"] = "HOLD"
        _write_bytes_new(
            report, (json.dumps(audit, indent=2, sort_keys=True) + "\n").encode(),
        )
        print(f"P0D_TWO_NATIVE_AUDIT={report}", file=sys.stderr, flush=True)
        if owner is not None and owner.owned_session_id is not None:
            print(
                "P0D_HOLD: an owned disposable Paper process may still be running. "
                "Inspect saved PID/log before manual shutdown; no automatic retry.",
                file=sys.stderr, flush=True,
            )
    if audit["classification"] != "REAL_PAPER_TWO_NATIVE_STOP_SAVE_REJOIN_SMOKE_DEV":
        raise TwoNativePaperRefusal("owned native process cleanup uncertain; HOLD")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-jar", type=Path, required=True)
    parser.add_argument("--paper-sha256", required=True)
    parser.add_argument("--plugin-jar", type=Path, required=True)
    parser.add_argument("--plugin-sha256", required=True)
    parser.add_argument("--scratch-parent", type=Path, required=True)
    parser.add_argument(
        "--eula-accepted", action="store_true",
        help="explicit operator acceptance; never touch an existing server",
    )
    parser.add_argument("--java", default="java")
    parser.add_argument("--node", default="node")
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--heap-mb", type=int, default=1536)
    args = parser.parse_args()
    try:
        path = asyncio.run(run_real_two_native(
            paper_jar=args.paper_jar, paper_sha256=args.paper_sha256,
            plugin_jar=args.plugin_jar, plugin_sha256=args.plugin_sha256,
            scratch_parent=args.scratch_parent, accepted_eula=args.eula_accepted,
            java=args.java, node=args.node, timeout_s=args.timeout_s,
            heap_mb=args.heap_mb,
        ))
    except (
        TwoNativePaperRefusal, RealPaperSmokeRefusal, OSError, ValueError,
        RuntimeError, zipfile.BadZipFile,
    ) as exc:
        print(f"P0D_TWO_NATIVE_HOLD: {exc}", file=sys.stderr, flush=True)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
