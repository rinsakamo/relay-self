"""One real disposable D2: operator killed real zombie -> vanilla loot -> pickup.

This World source test is not a Self ATTACK, MOVE, PICKUP Skill, or EAT. It
joins original Paper death, ItemSpawn, EntityPickup, native inventory and
original 600-tick zombie respawn in one session without modifying the rules.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path

from adapters.mineflayer.s31a_real_server_ci import (
    _command,
    _correlated_observe,
    _ready_server,
    _shutdown_server,
    _write_config,
)
from adapters.mineflayer.s34_native_world_cognition_ci import _new_session
from adapters.mineflayer.s49_p1_paper_server import PAPER_1218_SHA256, PAPER_1218_SIZE
from tools.bug0_pickup_d1_world import _artifact, _inventory, _original_marker
from tools.bug0_zombie_respawn_r1_world import _native_probe

RESPAWN_JAR = "relay-zombie-respawn-dev-0.1.0-dev.jar"
WITNESS_JAR = "relay-zombie-drop-witness-dev-0.1.0-dev.jar"
CONFIG = "dev-enabled: true\ntarget-player: RelaySelf\n"


class NaturalDropD2WorldRejected(RuntimeError):
    pass


async def qualify(report_path: Path, server_log: Path) -> int:
    report: dict[str, object] = {
        "stage": "START",
        "status": "BLOCKED",
        "classification": "D2_WORLD_NOT_RUN",
        "zombie_kill_principal": "OPERATOR_CONSOLE_ONLY",
        "item_origin": "ACTUAL_PAPER_ZOMBIE_DEATH_EVENT",
        "operator_positioned_zombie": True,
        "original_s49_actions": 0,
        "self_move_issued": False,
        "self_eat_issued": False,
        "self_attack_issued": False,
        "learning": False,
    }
    server = collector = session = temp = None
    rc = 2
    try:
        if (
            os.environ.get("S49_REAL_SERVER_CI") != "1"
            or os.environ.get("BUG0_D2_REAL_WORLD_ONCE") != "1"
            or os.environ.get("NODE_OPTIONS")
        ):
            raise NaturalDropD2WorldRejected("single-use D2 Paper grant absent")
        paper = _artifact(
            "BUG0_D2_PAPER_JAR", sha=PAPER_1218_SHA256, size=PAPER_1218_SIZE,
        )
        respawn = _artifact(
            "BUG0_D2_RESPAWN_JAR", sha=os.environ.get("BUG0_D2_RESPAWN_SHA256", ""),
        )
        witness = _artifact(
            "BUG0_D2_WITNESS_JAR", sha=os.environ.get("BUG0_D2_WITNESS_SHA256", ""),
        )
        if (
            respawn.name != RESPAWN_JAR or witness.name != WITNESS_JAR
            or len({paper, respawn, witness}) != 3
        ):
            raise NaturalDropD2WorldRejected("unexpected Paper/plugin identities")
        report["paper_sha256"] = PAPER_1218_SHA256
        report["respawn_plugin_sha256"] = os.environ["BUG0_D2_RESPAWN_SHA256"]
        report["witness_plugin_sha256"] = os.environ["BUG0_D2_WITNESS_SHA256"]

        temp = tempfile.TemporaryDirectory(prefix="bug0-d2-zombie-natural-drop-")
        root = Path(temp.name)
        _write_config(root)
        shutil.copyfile(paper, root / "minecraft.jar")
        plugin_dir = root / "plugins"
        plugin_dir.mkdir()
        for jar, plugin_name in (
            (respawn, "RelayZombieRespawnDev"),
            (witness, "RelayZombieDropWitnessDev"),
        ):
            shutil.copyfile(jar, plugin_dir / jar.name)
            cfg = plugin_dir / plugin_name
            cfg.mkdir()
            (cfg / "config.yml").write_text(CONFIG, encoding="utf8")

        report["stage"] = "PAPER_START"
        server, collector, _ = await _ready_server(root, root / "minecraft.jar", server_log)
        report["real_paper"] = True
        for command in (
            "gamerule doMobSpawning false",
            "gamerule doMobLoot true",
            "gamemode survival RelaySelf",
        ):
            _command(server, command)
        await server.stdin.drain()

        report["stage"] = "ONE_NATIVE_SELF_SOURCE"
        session = await _new_session()
        report["session_id"] = session.started.session_id
        await _original_marker(server_log, "RSELF_NATURAL_DROP_READY", budget=10)
        await _original_marker(server_log, "RSELF_RESPAWN_READY", budget=10)
        report["paper_initial"] = await _original_marker(
            server_log, "RSELF_RESPAWN_INITIAL world=", budget=15,
        )
        report["native_initial"] = await _native_probe(session, "d2-initial")
        before = await _correlated_observe(session, "d2-before-native-inventory")
        report["native_before"] = _inventory(before)
        if (
            before.snapshot.health <= 0
            or report["native_before"]["rotten_flesh"] != 0
        ):
            raise NaturalDropD2WorldRejected("unqualified pre-death native inventory")
        # Exactly one fixture-specific operator teleport and operator kill.
        # Self does not receive a movement/kill Action, skill or authority.
        report["stage"] = "OPERATOR_POSITION_AND_KILL"
        commands = (
            "execute at RelaySelf run tp "
            "@e[type=minecraft:zombie,limit=1] ~ ~ ~",
            "kill @e[type=minecraft:zombie,limit=1]",
        )
        report["operator_console_commands"] = list(commands)
        for command in commands:
            _command(server, command)
        await server.stdin.drain()

        report["paper_respawn_death"] = await _original_marker(
            server_log, "RSELF_RESPAWN_DEATH world=", budget=12,
        )
        report["paper_loot_death"] = await _original_marker(
            server_log, "RSELF_NATURAL_DROP_DEATH world=", budget=12,
        )
        try:
            amount = int(
                report["paper_loot_death"].split("rotten_count=")[1].split()[0]
            )
        except (IndexError, ValueError) as exc:
            raise NaturalDropD2WorldRejected("actual Paper loot count absent") from exc
        report["real_vanilla_loot_count"] = amount
        if not 1 <= amount <= 2:
            raise NaturalDropD2WorldRejected(
                "vanilla zero or out-of-scope loot: not restaged, not invented"
            )
        report["stage"] = "PAPER_ITEM_ENTITY_AND_REAL_PICKUP"
        report["paper_item_spawn"] = await _original_marker(
            server_log, "RSELF_NATURAL_DROP_SPAWN world=", budget=12,
        )
        report["paper_item_pickup"] = await _original_marker(
            server_log, "RSELF_NATURAL_DROP_PICKUP world=", budget=18,
        )

        report["stage"] = "NATIVE_LOOT_INVENTORY_GAIN"
        samples = []
        after = None
        for attempt in range(1, 13):
            read = await _correlated_observe(
                session, f"d2-natural-drop-after-{attempt:02d}",
            )
            current = _inventory(read)
            if (
                current["session_id"] == report["session_id"]
                and current["seq"] > report["native_before"]["seq"]
                and current["health"] > 0
                and current["rotten_flesh"] == amount
            ):
                after = current
                report["native_after"] = after
                report["native_after_attempt"] = attempt
                break
            samples.append(current)
            await asyncio.sleep(0.4)
        report["unqualified_native_after"] = samples
        if after is None:
            raise NaturalDropD2WorldRejected(
                "Paper natural loot collected but native inventory unqualified"
            )

        report["stage"] = "PAPER_REAL_600TICK_RESPAWN"
        report["paper_respawn"] = await _original_marker(
            server_log, "RSELF_RESPAWN_SPAWN world=", budget=85,
        )
        report["native_respawn"] = await _native_probe(session, "d2-respawn")
        if (
            report["native_initial"]["session_id"]
            != report["native_respawn"]["session_id"]
            or report["native_initial"]["zombie_entity_id"]
            == report["native_respawn"]["zombie_entity_id"]
        ):
            raise NaturalDropD2WorldRejected(
                "new World generation not reflected in native source"
            )
        report["stage"] = "D2_SOURCE_CLOSED"
        report["classification"] = "D2_OPERATOR_KILLED_REAL_ZOMBIE_NATURAL_DROP"
        report["status"] = "PASS_DEV"
        rc = 0
    except Exception as exc:
        report["status"] = "FAIL"
        report["classification"] = "D2_UNQUALIFIED_OR_RANDOM_ZERO_LOOT"
        report["failure"] = f"{type(exc).__name__}: {exc}"
    finally:
        if session is not None:
            try:
                report["node_exit"] = await session.shutdown(timeout_s=10)
            except Exception as exc:
                report["node_cleanup_error"] = repr(exc)
                try:
                    report["node_exit"] = await session.terminate()
                except Exception as second:
                    report["node_terminate_error"] = repr(second)
        if server is not None:
            try:
                await _shutdown_server(server, collector)
                report["java_exit"] = server.returncode
            except Exception as exc:
                report["java_cleanup_error"] = repr(exc)
                if server.returncode is None:
                    server.kill()
                    await server.wait()
                report["java_exit"] = server.returncode
        if temp is not None:
            temp.cleanup()
        if (
            report.get("java_exit") != 0 or report.get("node_exit") != 0
            or any(k.endswith("_error") for k in report)
        ):
            report["status"] = "FAIL"
            report["classification"] = "D2_CLEANUP_UNQUALIFIED"
            rc = 2
        report["cleanup_done"] = True
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                               encoding="utf8")
    return rc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--server-log", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(qualify(args.report, args.server_log)))


if __name__ == "__main__":
    main()
