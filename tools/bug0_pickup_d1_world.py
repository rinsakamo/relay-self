"""D1 World-only real item pickup: operator staged meat, Paper + native readback.

Never label an operator-created item as zombie loot or Self MOVE/PICKUP Skill.
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
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.loot_pickup_readback import (
    LootPickupReadbackRejected,
    read_rotten_flesh_gain,
)
from adapters.mineflayer.s31a_real_server_ci import (
    _command,
    _correlated_observe,
    _ready_server,
    _shutdown_server,
    _write_config,
)
from adapters.mineflayer.s34_native_world_cognition_ci import _new_session
from adapters.mineflayer.s49_p1_paper_server import (
    PAPER_1218_SHA256,
    PAPER_1218_SIZE,
)

PLUGIN_NAME = "relay-loot-pickup-dev-0.1.0-dev.jar"
PLUGIN_CONFIG = "dev-enabled: true\ntarget-player: RelaySelf\n"


class PickupD1Rejected(RuntimeError):
    pass


def _artifact(name: str, *, sha: str, size: int | None = None) -> Path:
    pathstr = os.environ.get(name)
    if (
        not pathstr or len(sha) != 64
        or any(x not in "0123456789abcdef" for x in sha)
    ):
        raise PickupD1Rejected("exact artifact name and sha256 required")
    path = Path(pathstr)
    if (
        not path.is_absolute() or not path.is_file() or path.is_symlink()
        or any(p.is_symlink() for p in path.parents)
        or (size is not None and path.stat().st_size != size)
        or hashlib.sha256(path.read_bytes()).hexdigest() != sha
    ):
        raise PickupD1Rejected("wrong, missing or mutable artifact")
    return path


async def _original_marker(path: Path, marker: str, *, budget: float = 15) -> str:
    deadline = time.monotonic() + budget
    while time.monotonic() < deadline:
        if path.exists():
            log = path.read_text(encoding="utf-8")
            if "[ERROR]" in log and "RelayPickupFixtureDev" in log:
                raise PickupD1Rejected("Paper pickup server error")
            hits = [row for row in log.splitlines() if marker in row]
            if len(hits) == 1:
                return hits[0]
            if len(hits) > 1:
                raise PickupD1Rejected("duplicate Paper source marker")
        await asyncio.sleep(0.25)
    raise PickupD1Rejected(f"Paper original marker absent: {marker}")


def _inventory(read) -> dict:
    return {
        "session_id": read.session_id,
        "seq": read.seq,
        "request_id": read.request_id,
        "provenance": read.provenance.reference,
        "rotten_flesh": sum(
            i.count for i in read.snapshot.inventory
            if i.name == "rotten_flesh"
        ),
        "all_items": [
            {"name": i.name, "slot": i.slot, "count": i.count}
            for i in read.snapshot.inventory
        ],
        "health": read.snapshot.health,
    }


async def qualify(
    report_path: Path, server_log: Path, *, post_staged_move_dev=None,
) -> int:
    report: dict[str, object] = {
        "status": "BLOCKED",
        "stage": "START",
        "classification": "D1_WORLD_NOT_RUN",
        "item_origin": "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP",
        "original_s49_actions": 0,
        "self_action_issued": False,
        "self_granted_inventory": False,
        "zombie_kill_attested": False,
        "real_model_calls": 0,
        "learning_updated": False,
    }
    temp = server = collector = session = None
    rc = 2
    try:
        if (
            os.environ.get("S49_REAL_SERVER_CI") != "1"
            or os.environ.get("BUG0_PICKUP_D1_DEV_ONLY") != "1"
            or os.environ.get("NODE_OPTIONS")
        ):
            raise PickupD1Rejected("one-shot read-only D1 World grant absent")
        if post_staged_move_dev is not None and (
            os.environ.get("D6_STAGED_LOOT_MOVE_WORLD_ONLY") != "1"
            or not callable(post_staged_move_dev)
        ):
            raise PickupD1Rejected("explicit D6 staged MOVE one-world grant absent")
        paper = _artifact(
            "BUG0_PICKUP_PAPER_JAR",
            sha=PAPER_1218_SHA256, size=PAPER_1218_SIZE,
        )
        jar = _artifact(
            "BUG0_PICKUP_PLUGIN_JAR",
            sha=os.environ.get("BUG0_PICKUP_PLUGIN_SHA256", ""),
        )
        if jar.name != PLUGIN_NAME or paper == jar:
            raise PickupD1Rejected("unexpected plugin filename")
        report["pinned_paper_sha256"] = PAPER_1218_SHA256
        report["plugin_sha256"] = os.environ["BUG0_PICKUP_PLUGIN_SHA256"]
        temp = tempfile.TemporaryDirectory(prefix="bug0-pickup-d1-")
        root = Path(temp.name)
        _write_config(root)
        shutil.copyfile(paper, root / "minecraft.jar")
        plugins = root / "plugins"
        plugins.mkdir()
        shutil.copyfile(jar, plugins / jar.name)
        cfg = plugins / "RelayPickupFixtureDev"
        cfg.mkdir()
        (cfg / "config.yml").write_text(PLUGIN_CONFIG, encoding="utf8")

        report["stage"] = "PAPER_START"
        server, collector, _ = await _ready_server(
            root, root / "minecraft.jar", server_log,
        )
        report["real_paper"] = True
        _command(server, "gamerule doMobSpawning false")
        await server.stdin.drain()

        report["stage"] = "ORIGINAL_NATIVE_SESSION"
        session = await _new_session(
            w4_native_orientation_dev=post_staged_move_dev is not None,
        )
        report["session_id"] = session.started.session_id
        _command(server, "gamemode survival RelaySelf")
        await server.stdin.drain()
        await asyncio.sleep(0.7)
        report["paper_ready"] = await _original_marker(
            server_log, "RSELF_LOOT_READY item=rotten_flesh", budget=8,
        )
        before = await _correlated_observe(session, "pickup-d1-before")
        report["native_before"] = _inventory(before)
        if (
            before.snapshot.health <= 0
            or report["native_before"]["rotten_flesh"] != 0
            or before.snapshot.nearby_entities_coverage.truncated
        ):
            raise PickupD1Rejected("baseline native inventory or health unqualified")

        report["stage"] = "OPERATOR_GROUND_ITEM_STAGE"
        _command(
            server,
            "rselfstagefood back" if post_staged_move_dev is not None
            else "rselfstagefood",
        )
        await server.stdin.drain()
        report["paper_staged"] = await _original_marker(
            server_log, "RSELF_LOOT_STAGED world=", budget=8,
        )
        if post_staged_move_dev is not None:
            report["stage"] = "D6_ORIGINAL_S49_MOVE_TO_OPERATOR_ITEM"
            await post_staged_move_dev(session, report, server_log)
        report["stage"] = "WAIT_REAL_PAPER_PICKUP"
        report["paper_pickup"] = await _original_marker(
            server_log, "RSELF_LOOT_PICKED world=", budget=15,
        )

        report["stage"] = "NATIVE_PICKED_INVENTORY"
        failures = []
        receipt = None
        for attempt in range(1, 13):
            after = await _correlated_observe(
                session, f"pickup-d1-after-{attempt:02d}",
            )
            try:
                receipt = read_rotten_flesh_gain(before, after)
                report["native_after"] = _inventory(after)
                report["native_pickup_gain"] = asdict(receipt)
                report["native_after_attempt"] = attempt
                break
            except LootPickupReadbackRejected as exc:
                failures.append({
                    "seq": after.seq,
                    "request_id": after.request_id,
                    "snapshot": _inventory(after),
                    "failure": str(exc),
                })
                await asyncio.sleep(0.5)
        report["unqualified_native_after"] = failures
        if receipt is None:
            raise PickupD1Rejected("real pickup not reflected in native inventory")

        report["status"] = "PASS_DEV"
        report["stage"] = "PAPER_NATIVE_PICKUP_CLOSED"
        if post_staged_move_dev is not None:
            if (
                type(report.get("original_s49_actions")) is not int
                or report["original_s49_actions"] < 1
                or report.get("self_action_issued") is not True
                or not report.get("d6_original_s49_move_actions")
            ):
                raise PickupD1Rejected("D6 same original S49 physical MOVE not proven")
            report["classification"] = "D6_OPERATOR_STAGED_S49_MOVE_PICKUP_PASS"
        else:
            report["classification"] = "D1_OPERATOR_STAGED_PAPER_PICKUP_NATIVE_GAIN"
        rc = 0
    except Exception as exc:
        report["status"] = "FAIL"
        report["classification"] = (
            "D6_OPERATOR_STAGED_LOOT_MOVE_UNQUALIFIED"
            if post_staged_move_dev is not None else "D1_PICKUP_SOURCE_UNQUALIFIED"
        )
        report["failure"] = f"{type(exc).__name__}: {exc}"
    finally:
        if session is not None:
            try:
                report["node_exit"] = await session.shutdown(timeout_s=10)
            except Exception as exc:
                report["node_cleanup_error"] = repr(exc)
                try:
                    report["node_exit"] = await session.terminate()
                except Exception as exc2:
                    report["node_terminate_error"] = repr(exc2)
        if server is not None:
            try:
                await _shutdown_server(server, collector)
                report["java_exit"] = server.returncode
            except Exception as exc:
                report["server_cleanup_error"] = repr(exc)
                if server.returncode is None:
                    server.kill()
                    await server.wait()
                report["java_exit"] = server.returncode
        if temp is not None:
            temp.cleanup()
        if (
            any(k.endswith("_error") for k in report)
            or report.get("node_exit") != 0
            or report.get("java_exit") != 0
        ):
            report["status"] = "FAIL"
            report["classification"] = "D1_CLEANUP_UNQUALIFIED"
            rc = 2
        report["cleanup_done"] = True
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return rc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--server-log", required=True, type=Path)
    a = p.parse_args()
    raise SystemExit(asyncio.run(qualify(a.report, a.server_log)))


if __name__ == "__main__":
    main()
