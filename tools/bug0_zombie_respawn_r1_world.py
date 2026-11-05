"""One authorized disposable Paper R1: operator-caused death -> real 600 ticks.

This is a World-environment diagnostic, NOT S49 ATTACK or autonomous hunting.
Only the existing Mineflayer process reads native observations. No Self
Action/LLM/learning/WorldBody true-state input is created.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s31a_real_server_ci import (
    _command,
    _ready_server,
    _shutdown_server,
    _write_config,
)
from adapters.mineflayer.s34_native_world_cognition_ci import _new_session
from adapters.mineflayer.s49_p1_paper_server import PAPER_1218_SHA256, PAPER_1218_SIZE

PLUGIN_NAME = "relay-zombie-respawn-dev-0.1.0-dev.jar"
CONFIG = "dev-enabled: true\ntarget-player: RelaySelf\n"


class RespawnR1Rejected(RuntimeError):
    pass


def _qualified_file(name: str, *, sha: str | None = None, size: int | None = None) -> Path:
    raw = os.environ.get(name)
    if not raw:
        raise RespawnR1Rejected(f"missing artifact {name}")
    path = Path(raw)
    if (
        not path.is_absolute() or not path.is_file() or path.is_symlink()
        or any(parent.is_symlink() for parent in path.parents)
    ):
        raise RespawnR1Rejected("immutable absolute regular file required")
    if size is not None and path.stat().st_size != size:
        raise RespawnR1Rejected("pinned Paper size mismatch")
    if sha is not None and hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise RespawnR1Rejected("pinned file sha256 mismatch")
    return path


async def _wait_original(log: Path, marker: str, *, budget_s: float) -> str:
    started = time.monotonic()
    while time.monotonic() - started < budget_s:
        if log.is_file():
            rows = [x for x in log.read_text(encoding="utf-8").splitlines() if marker in x]
            if len(rows) == 1:
                return rows[0]
            if len(rows) > 1:
                raise RespawnR1Rejected(f"duplicate original Paper marker {marker}")
            if "RSELF_RESPAWN_FAULT" in log.read_text(encoding="utf-8"):
                raise RespawnR1Rejected("Paper state machine reported a source fault")
        await asyncio.sleep(0.25)
    raise RespawnR1Rejected(f"missing original Paper marker {marker}")


async def _native_probe(session, request_id: str) -> dict:
    """Source-bound, limited read-only probes while native entity registry settles.

    This does NOT retry an Action/World. Every sample has a distinct original
    native request ID; incomplete or ambiguous coverage is retained as negative
    evidence rather than relabelled a zombie sighting.
    """
    unready: list[dict] = []
    for attempt in range(1, 11):
        fresh_request = f"{request_id}-{attempt}"
        await session.send_observe(fresh_request)
        for _ in range(120):
            frame = await asyncio.wait_for(session.receive(), timeout=6)
            if not (
                isinstance(frame, MineflayerObservation)
                and frame.kind == "probe"
                and frame.request_id == fresh_request
            ):
                continue
            coverage = frame.snapshot.nearby_entities_coverage
            z = [e for e in frame.snapshot.nearby_entities if e.name == "zombie"]
            source = {
                "native_seq": frame.seq,
                "request_id": fresh_request,
                "zombie_count": len(z),
                "candidate_count": coverage.candidate_count,
                "truncated": coverage.truncated,
                "entity_names": [
                    {"name": e.name, "type": e.entity_type, "id": e.entity_id}
                    for e in frame.snapshot.nearby_entities
                ],
            }
            if not coverage.truncated and len(z) == 1:
                return {
                    "session_id": frame.session_id,
                    "seq": frame.seq,
                    "request_id": fresh_request,
                    "zombie_entity_id": z[0].entity_id,
                    "zombie_distance": z[0].distance,
                    "native_source": frame.provenance.reference,
                    "candidate_count": coverage.candidate_count,
                    "read_attempt": attempt,
                    "unready_native_samples": unready,
                }
            unready.append(source)
            break
        else:
            raise RespawnR1Rejected("bounded native response read failed")
        await asyncio.sleep(0.6)
    raise RespawnR1Rejected(
        "no qualified native zombie after 10 fresh read-only probes: "
        + json.dumps(unready, sort_keys=True)
    )


async def run(report_path: Path, log_path: Path) -> int:
    report: dict[str, object] = {
        "stage": "START",
        "status": "BLOCKED",
        "classification": "WORLD_NOT_RUN",
        "operator_kill": True,
        "original_s49_actions": 0,
        "self_granted_actions": 0,
        "learning": False,
        "worldbody_private_truth_supplied_to_self": False,
    }
    server = collector = session = tmp = None
    rc = 2
    try:
        if (
            os.environ.get("S49_REAL_SERVER_CI") != "1"
            or os.environ.get("BUG0_ZOMBIE_RESPAWN_R1_DEV_ONLY") != "1"
            or os.environ.get("NODE_OPTIONS")
        ):
            raise RespawnR1Rejected("exclusive one-World/one-native-session grant absent")
        paper = _qualified_file(
            "BUG0_RESPAWN_PAPER_JAR",
            sha=PAPER_1218_SHA256, size=PAPER_1218_SIZE,
        )
        plugin_sha = os.environ.get("BUG0_RESPAWN_PLUGIN_SHA256", "")
        if len(plugin_sha) != 64 or any(x not in "0123456789abcdef" for x in plugin_sha):
            raise RespawnR1Rejected("explicit pinned plugin digest required")
        plugin = _qualified_file("BUG0_RESPAWN_PLUGIN_JAR", sha=plugin_sha)
        if plugin.name != PLUGIN_NAME or plugin == paper:
            raise RespawnR1Rejected("unexpected Paper plugin artifact")
        report["paper_sha256"] = PAPER_1218_SHA256
        report["plugin_sha256"] = plugin_sha
        tmp = tempfile.TemporaryDirectory(prefix="bug0-zombie-respawn-r1-")
        root = Path(tmp.name)
        _write_config(root)
        shutil.copyfile(paper, root / "minecraft.jar")
        plugindir = root / "plugins"
        plugindir.mkdir()
        shutil.copyfile(plugin, plugindir / plugin.name)
        cfg = plugindir / "RelayZombieRespawnDev"
        cfg.mkdir()
        (cfg / "config.yml").write_text(CONFIG, encoding="utf-8")

        report["stage"] = "PAPER_START"
        server, collector, _ = await _ready_server(root, root / "minecraft.jar", log_path)
        report["real_paper_started"] = True
        _command(server, "gamerule doMobSpawning false")
        await server.stdin.drain()
        await asyncio.sleep(1)

        report["stage"] = "ORIGINAL_NATIVE_JOIN"
        session = await _new_session()
        report["session_id"] = session.started.session_id
        report["paper_initial"] = await _wait_original(
            log_path, "RSELF_RESPAWN_INITIAL world=", budget_s=12,
        )
        report["native_initial"] = await _native_probe(session, "r1-initial")

        report["stage"] = "OPERATOR_CAUSED_DEATH"
        _command(server, "kill @e[type=minecraft:zombie,limit=1]")
        await server.stdin.drain()
        report["paper_death"] = await _wait_original(
            log_path, "RSELF_RESPAWN_DEATH world=", budget_s=12,
        )

        report["stage"] = "WAIT_600_PAPER_WORLD_TICKS"
        report["paper_respawn"] = await _wait_original(
            log_path, "RSELF_RESPAWN_SPAWN world=", budget_s=80,
        )
        report["native_respawn"] = await _native_probe(session, "r1-after-respawn")
        if (
            report["native_initial"]["session_id"] != report["native_respawn"]["session_id"]
            or report["native_initial"]["zombie_entity_id"]
                == report["native_respawn"]["zombie_entity_id"]
            or report["native_initial"]["seq"] >= report["native_respawn"]["seq"]
        ):
            raise RespawnR1Rejected("native new-entity event not source-ordered")
        report["stage"] = "R1_NATIVE_COMPLETE"
        report["status"] = "PASS_DEV"
        report["classification"] = "OPERATOR_KILL_WORLD_RESPAWN_R1_PASS"
        rc = 0
    except Exception as exc:
        report["failure"] = f"{type(exc).__name__}: {exc}"
        report["status"] = "FAIL"
        report["classification"] = "R1_WORLD_UNQUALIFIED"
    finally:
        if session is not None:
            try:
                report["node_exit"] = await session.shutdown(timeout_s=10)
            except Exception as exc:
                report["node_cleanup_error"] = f"{type(exc).__name__}: {exc}"
                try:
                    report["node_exit"] = await session.terminate()
                except Exception as second:
                    report["node_terminate_error"] = repr(second)
        if server is not None:
            try:
                await _shutdown_server(server, collector)
                report["java_exit"] = server.returncode
            except Exception as exc:
                report["server_cleanup_error"] = f"{type(exc).__name__}: {exc}"
                if server.returncode is None:
                    server.kill()
                    await server.wait()
                report["java_exit"] = server.returncode
        if tmp is not None:
            tmp.cleanup()
        if any(k.endswith("_error") for k in report) or report.get("node_exit") != 0 or report.get("java_exit") != 0:
            rc = 2
            report["status"] = "FAIL"
            report["classification"] = "R1_CLEANUP_UNQUALIFIED"
        report["cleanup_finished"] = True
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return rc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--server-log", type=Path, required=True)
    args = p.parse_args()
    raise SystemExit(asyncio.run(run(args.report, args.server_log)))


if __name__ == "__main__":
    main()
