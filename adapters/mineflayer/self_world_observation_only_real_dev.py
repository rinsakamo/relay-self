"""W4 explicit DEV-only real Minecraft observation: ZERO Self Actions.

No external grant infrastructure: user-operated --confirm, clean exact HEAD,
operator-pinned JAR and exclusive disposable directories. This is DEVELOPMENT,
not QUALIFICATION/SCIENCE; default S49 and Action/learning owners are untouched.
No module import starts a process, opens a socket or creates files.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import secrets
import shutil
import sys
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from adapters.mineflayer.s31a_real_server_ci import (
    _await_spawn,
    _command,
    _correlated_observe,
    _ready_server,
    _write_config,
)
from adapters.mineflayer.self_world_observation_only_close import (
    close_observation_only_dev,
)
from adapters.mineflayer.self_world_observation_only_dev import (
    ObservationOnlyDevSession,
    _bounded_observation_wait,
    review_observation_only_dev_offline,
    wait_for_observation_raw_world_marker,
)
from adapters.mineflayer.self_world_observation_only_entry import (
    _check_original_path,
    inventory_observation_only_entry,
)
from adapters.mineflayer.self_world_observation_only_lifetime import (
    join_observation_only_local_lifetime,
)
from adapters.mineflayer.self_world_observation_only_native_boundary import (
    _loopback_port_can_bind,
    _read_proc_starttime,
    audit_observation_only_local_disposal,
    capture_original_native_pid,
)
from adapters.mineflayer.self_world_stage_w4_logtap import (
    _tail_bytes,
    capture_w4_collector_cursor,
)
from adapters.mineflayer.startup_process_ownership import StartupCleanupUnconfirmed, _supervise

_CONFIRM = "DEV_OBSERVATION_ONLY"


class ObservationDevRunBlocked(ValueError):
    """DEV-specific fixed-head, isolation, or cleanup requirement failed."""


def _run_precheck(
    *, confirm: str, expected_head: str, expected_jar_sha256: str,
    repository: Path, jar: Path, world_parent: Path, evidence_parent: Path,
    run_id: str,
) -> None:
    if confirm != _CONFIRM:
        raise ObservationDevRunBlocked("explicit --confirm DEV_OBSERVATION_ONLY required")
    if not re.fullmatch(r"[0-9a-f]{16}", run_id):
        raise ObservationDevRunBlocked("16-hex unique run ID required")
    if (
        not isinstance(repository, Path) or not repository.is_absolute()
        or not isinstance(jar, Path) or not jar.is_absolute()
        or not isinstance(world_parent, Path) or not world_parent.is_absolute()
        or not isinstance(evidence_parent, Path) or not evidence_parent.is_absolute()
        or not re.fullmatch(r"[0-9a-f]{40}", expected_head)
        or not re.fullmatch(r"[0-9a-f]{64}", expected_jar_sha256)
        or world_parent == evidence_parent
        or world_parent.is_relative_to(repository)
        or evidence_parent.is_relative_to(repository)
        or repository.is_relative_to(world_parent)
        or repository.is_relative_to(evidence_parent)
        or world_parent.is_relative_to(evidence_parent)
        or evidence_parent.is_relative_to(world_parent)
        or jar.is_relative_to(world_parent)
        or jar.is_relative_to(evidence_parent)
    ):
        raise ObservationDevRunBlocked("distinct absolute external roots and pins required")
    for root in (repository, world_parent, evidence_parent):
        _check_original_path(root, directory=True)
        if root != root.resolve():
            raise ObservationDevRunBlocked("canonical paths without dot components required")
    if sys.platform != "linux":
        raise ObservationDevRunBlocked("local Linux/WSL2 DEV-only launcher")


def _write_report(path: Path, value: dict) -> None:
    """Durably replace a report in its one fresh evidence directory."""
    fd, name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    pending = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        pending.replace(path)
    finally:
        pending.unlink(missing_ok=True)


def _delete_disposable_root(
    root: Path, parent: Path, *, run_id: str, identity: tuple[int, int],
) -> None:
    """Never delete an unowned path or follow a replaced symlink."""
    if (
        root.parent != parent
        or root.name != f"w4-observe-{run_id}"
        or root.is_symlink()
        or not root.is_dir()
        or (root.stat().st_dev, root.stat().st_ino) != identity
    ):
        raise ObservationDevRunBlocked("World root ownership changed before disposal")
    _check_original_path(parent, directory=True)
    shutil.rmtree(root)


async def run_observation_only_real_dev(
    *, confirm: str, expected_head: str, expected_jar_sha256: str,
    repository: Path, jar: Path, world_parent: Path, evidence_parent: Path,
    run_id: str,
) -> dict:
    """One optional real DEV session. The only World command is read-only time.

    A cancelled session is still supervised through same-owner teardown.
    The real World must not be called qualified even if local checks succeed.
    """
    _run_precheck(
        confirm=confirm, expected_head=expected_head,
        expected_jar_sha256=expected_jar_sha256, repository=repository,
        jar=jar, world_parent=world_parent, evidence_parent=evidence_parent,
        run_id=run_id,
    )
    world_root = world_parent / f"w4-observe-{run_id}"
    evidence_root = evidence_parent / f"w4-observe-{run_id}"
    # EEXIST is a hard refusal: this is not a resumable or replayed run.
    evidence_root.mkdir(mode=0o700)
    report = {
        "schema": "W4_OBSERVATION_ONLY_REAL_DEV_V1",
        "head": expected_head, "run_id": run_id,
        "status": "BLOCKED", "classification": "PREWORLD_BLOCKED",
        "scope": "DEV_ONLY_NOT_QUALIFIED",
        "stage": "PREWORLD", "server_pid": None, "node_pid": None,
        "action_count": 0, "outcome_count": 0, "s10_update_count": 0,
        "qualification_approved": False, "science_qualified": False,
        "external_grant_qualified": False,
        "verdict": "PREWORLD_BLOCKED",
        "started_utc": datetime.now(timezone.utc).isoformat(),
    }
    _write_report(evidence_root / "report.json", report)
    java = collector = session = java_id = node_id = inventory = None
    close = None
    failure: BaseException | None = None
    world_identity = None
    try:
        world_root.mkdir(mode=0o700)
        info = world_root.stat()
        world_identity = (info.st_dev, info.st_ino)
        inventory = inventory_observation_only_entry(
            repository=repository, expected_head=expected_head,
            server_jar=jar, expected_server_sha256=expected_jar_sha256,
            disposable_root=world_root,
        )
        report["inventory"] = asdict(inventory)
        if not _loopback_port_can_bind(25565):
            raise ObservationDevRunBlocked("Minecraft loopback port already occupied")
        _write_config(world_root)
        report["stage"] = "JAVA_STARTUP"
        java_log = evidence_root / "java-collector.log"
        java_raw = evidence_root / "java-collector.raw"
        java, collector, _ = await _ready_server(
            world_root, jar, java_log, raw_stdout_path=java_raw,
        )
        java_id = capture_original_native_pid(java)
        report["server_pid"] = java_id.pid
        report["java_identity"] = asdict(java_id)
        report["java_ready_utc"] = datetime.now(timezone.utc).isoformat()
        report["stage"] = "NODE_SPAWN"
        session = await ObservationOnlyDevSession.launch(
            MineflayerLaunchConfig(
                host="127.0.0.1", port=25565,
                username="RelaySelf", version="1.21.8",
            ),
            bridge_path=repository / "adapters" / "mineflayer" / "bridge.mjs",
            raw_capture_root=evidence_root,
            startup_timeout_s=15,
        )
        node_id = capture_original_native_pid(session._process)
        report["node_pid"] = node_id.pid
        report["node_identity"] = asdict(node_id)
        report["node_started_utc"] = datetime.now(timezone.utc).isoformat()
        report["adapter_started"] = asdict(session.started)
        spawn = await _await_spawn(session)
        report["spawn"] = asdict(spawn)
        report["stage"] = "PRE_OBSERVATION"
        before_id = f"w4-before-{run_id}"
        after_id = f"w4-after-{run_id}"
        before = await _correlated_observe(session, before_id)
        report["before"] = asdict(before)
        # The original sole Java stdout collector already owns the raw file.
        cursor = capture_w4_collector_cursor(java_raw)
        report["stage"] = "JAVA_READ_ONLY_MARKER"
        _command(java, "time query gametime")
        assert java.stdin is not None
        await _bounded_observation_wait(
            java.stdin.drain(), timeout_s=5, name="Java marker command drain",
        )
        marker = await wait_for_observation_raw_world_marker(cursor, timeout_s=10)
        raw_bytes = _tail_bytes(cursor, marker.raw_start_byte)
        marker_line = raw_bytes[:marker.raw_end_byte - marker.raw_start_byte]
        if hashlib.sha256(marker_line).hexdigest() != marker.raw_sha256:
            raise ObservationDevRunBlocked("original Java collector marker changed")
        report["stage"] = "POST_OBSERVATION"
        after = await _correlated_observe(session, after_id)
        report["after"] = asdict(after)
        readback = review_observation_only_dev_offline(
            started=session.started, spawn=spawn, before=before, after=after,
            before_request=before_id, after_request=after_id,
            raw_marker_line=marker_line, marker_sha256=marker.raw_sha256,
            marker_after_before=True, after_marker=True,
        )
        report["readback"] = asdict(readback)
        report["marker"] = asdict(marker)
        report["stage"] = "SHUTDOWN"
    except BaseException as exc:
        failure = exc
        report["status"] = "BLOCKED"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["startup_cleanup_unconfirmed"] = getattr(
            exc, "startup_cleanup_unconfirmed", None,
        ) or (str(exc) if isinstance(exc, StartupCleanupUnconfirmed) else None)
    finally:
        async def finish() -> None:
            nonlocal close
            if java is not None:
                try:
                    close = await close_observation_only_dev(
                        server=java, collector=collector, session=session,
                        timeout_s=12,
                    )
                    report["close"] = close
                except BaseException as exc:
                    report["cleanup_error"] = f"{type(exc).__name__}: {exc}"
            # Only dispose after native returncode and collector settlement:
            # a potentially live Java/Node process must never be ignored.
            node_reaped = (
                session is not None and
                type(session.process_returncode) is int
            )
            java_reaped = java is not None and type(java.returncode) is int
            identities = [item for item in (java_id, node_id) if item is not None]
            try:
                report["pid_absent"] = {
                    str(item.pid): _read_proc_starttime(item.pid) is None for item in identities
                }
                report["port_released"] = _loopback_port_can_bind(25565)
            except BaseException as exc:
                report["native_inspection_error"] = f"{type(exc).__name__}: {exc}"
            collector_ok = (
                collector is not None and collector.done() and not collector.cancelled()
                and collector.exception() is None
            )
            report["collector_settled_normally"] = collector_ok
            native_absent = (
                len(identities) == int(java is not None) + int(session is not None)
                and all(report.get("pid_absent", {}).values())
                and "native_inspection_error" not in report
            )
            cleanup_known = (
                (java is None or java_reaped)
                and (session is None or node_reaped)
                and (collector is None or collector_ok)
                and native_absent
                and not report.get("startup_cleanup_unconfirmed")
                and "cleanup_error" not in report
                and not any(
                    "reap_" in error or "Unconfirmed" in error or "collector_" in error
                    for error in (close or {}).get("errors", [])
                )
            )
            report["cleanup_confirmed"] = cleanup_known
            if cleanup_known and world_identity is not None:
                try:
                    _delete_disposable_root(
                        world_root, world_parent, run_id=run_id, identity=world_identity,
                    )
                    report["world_root_removed"] = True
                except BaseException as exc:
                    report["world_disposal_error"] = f"{type(exc).__name__}: {exc}"
            else:
                report["world_root_removed"] = False
            if (
                failure is None and close is not None
                and report.get("world_root_removed") is True
                and inventory is not None and node_id is not None and java_id is not None
                and close.get("classification") == "LOCAL_PRODUCER_CLOSE_ONLY"
            ):
                try:
                    lifetime = join_observation_only_local_lifetime(
                        inventory=inventory, readback=readback,
                        marker=marker, close=close, node_raw_root=evidence_root,
                    )
                    report["local_lifetime"] = asdict(lifetime)
                    disposed = audit_observation_only_local_disposal(
                        java_before=java_id, node_before=node_id,
                        close=close, local_lifetime=lifetime,
                        disposable_world_root=world_root,
                        world_parent=world_parent, port=25565,
                    )
                    report["local_disposal"] = asdict(disposed)
                    report["status"] = "PASS"
                    report["stage"] = "DEV_COMPLETE"
                    report["classification"] = "DEV_LOCAL_OBSERVATION_ONLY"
                    report["verdict"] = "DEV_LOCAL_OBSERVATION_ONLY_PASS"
                except BaseException as exc:
                    report["audit_error"] = f"{type(exc).__name__}: {exc}"
            if report["status"] != "PASS":
                if not cleanup_known or report.get("world_disposal_error"):
                    report["verdict"] = "CLEANUP_UNCONFIRMED"
                elif report["stage"] != "PREWORLD":
                    report["verdict"] = "DEV_OBSERVATION_ONLY_BLOCKED"
            report["finished_utc"] = datetime.now(timezone.utc).isoformat()
            report["classification"] = report["verdict"]
            # Every run creates its own permanent evidence directory.
            try:
                _write_report(evidence_root / "report.json", report)
            except BaseException as exc:
                report["report_write_error"] = f"{type(exc).__name__}: {exc}"
                report["status"] = "BLOCKED"
                report["classification"] = "DEV_OBSERVATION_ONLY_BLOCKED"
        await _supervise(finish())
    if failure is not None and isinstance(failure, asyncio.CancelledError):
        raise failure
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Explicit disposable Minecraft observation-only DEV; no Actions",
    )
    parser.add_argument("--confirm", required=True, choices=[_CONFIRM])
    parser.add_argument("--head", required=True)
    parser.add_argument("--server-jar", type=Path, required=True)
    parser.add_argument("--server-sha256", required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--world-parent", type=Path, required=True)
    parser.add_argument("--evidence-parent", type=Path, required=True)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)
    run_id = args.run_id or secrets.token_hex(8)
    try:
        result = asyncio.run(run_observation_only_real_dev(
            confirm=args.confirm, expected_head=args.head,
            expected_jar_sha256=args.server_sha256,
            repository=args.repository, jar=args.server_jar,
            world_parent=args.world_parent,
            evidence_parent=args.evidence_parent,
            run_id=run_id,
        ))
    except (OSError, ValueError) as exc:
        print(f"W4 observation DEV BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": result["status"], "classification": result["classification"],
        "run_id": result["run_id"], "stage": result["stage"],
        "server_pid": result["server_pid"], "node_pid": result["node_pid"],
    }, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
