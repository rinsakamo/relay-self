"""RSEE one-shot *Minecraft-only* initial World bootstrap.

Never launches an LLM, never issues a Self Action, and is default-deny.
Native acquisition needs independent operator permission + Minecraft EULA.
Offline CI mocks Java/Node; no physical qualification is implied by tests.
"""
from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import math
import os
import shutil
import socket
import stat
import sys
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from adapters.mineflayer.s31a_real_server_ci import (
    BOT_USERNAME,
    MINECRAFT_VERSION,
    SERVER_HOST,
    SERVER_PORT,
    _await_spawn,
    _command,
    _correlated_observe,
    _ready_server,
    _shutdown_server,
    _write_config,
)
from experiments.standard_env.world_binding import (
    JAR_SHA256,
    LEVEL,
    MAX_LEVEL,
    SCHEMA,
    SEED,
    VERSION,
    WorldBindingRejected,
    _hash_file,
    _regular,
    _world_files,
    verify_world_binding,
    _NBT,
)

class BootstrapRejected(ValueError):
    """Bootstrap admission or physically acquired World cannot be qualified."""


def _parse_native_nbt(path: Path) -> dict:
    """Parse existing Mojang gzip NBT, strict bounding, no synthetic values."""
    path = _regular(path)
    with gzip.open(path, "rb") as stream:
        raw = stream.read(MAX_LEVEL + 1)
    if len(raw) > MAX_LEVEL:
        raise BootstrapRejected("native NBT decompression bound exceeded")
    dec = _NBT(raw)
    if dec.number("B") != 10:
        raise BootstrapRejected("native NBT root not compound")
    dec.name()
    result = dec.value(10)
    if dec.pos != len(raw) or type(result) is not dict:
        raise BootstrapRejected("native NBT remainder invalid")
    return result


def _saved_state(snapshot: Path) -> dict:
    """Interpret the saved *stopped* World + one player's native NBT."""
    data = _parse_native_nbt(snapshot / "level.dat")["Data"]
    rules = data["GameRules"]
    expected = {
        "doDaylightCycle": "false",
        "doWeatherCycle": "false",
        "doMobSpawning": "false",
    }
    if type(rules) is not dict or any(rules.get(k) != v for k, v in expected.items()):
        raise BootstrapRejected("stored World gamerules do not match frozen bootstrap")
    if (not isinstance(data.get("DayTime"), int)
            or int(data["DayTime"]) % 24000 != 18000
            or data.get("raining") != 0 or data.get("thundering") != 0):
        raise BootstrapRejected("stored time/weather mismatch")
    # The dedicated server must persist exactly the one connected bot's
    # playerdata. No inference from Mineflayer's initial frame alone.
    player_dir = snapshot / "playerdata"
    if player_dir.is_symlink() or not player_dir.is_dir():
        raise BootstrapRejected("no native saved playerdata directory")
    players = list(player_dir.iterdir())
    if (len(players) != 1 or players[0].is_symlink()
            or players[0].suffix != ".dat"):
        raise BootstrapRejected("expected exactly one stored playerdata NBT")
    player = _parse_native_nbt(players[0])
    rotation = player.get("Rotation")
    pos = player.get("Pos")
    if (type(rotation) is not list or len(rotation) != 2
            or type(pos) is not list or len(pos) != 3
            or not all(type(x) is float and math.isfinite(x)
                       for x in [*rotation, *pos])):
        raise BootstrapRejected("saved native yaw/pitch/position unavailable")
    if (not isinstance(player.get("Inventory"), list)
            or not isinstance(player.get("Health"), (float, int))
            or type(player.get("foodLevel")) is not int):
        raise BootstrapRejected("saved native inventory/health/food unavailable")
    return {
        "stored_world": {
            "day_time": int(data["DayTime"]),
            "raining": int(data["raining"]),
            "thundering": int(data["thundering"]),
            "gamerules_qualified_subset": expected,
            "full_gamerules": rules,
        },
        "stored_player": {
            "playerdata_file": players[0].name,
            "playerdata_sha256": _hash_file(players[0]),
            "position": [float(x) for x in pos],
            "rotation_yaw_pitch": [float(x) for x in rotation],
            "health": float(player["Health"]),
            "food": int(player["foodLevel"]),
            "inventory": player["Inventory"],
        },
    }


def _admit(jar: Path, output_dir: Path, *, authorized: bool, eula: bool) -> Path:
    # No filesystem changes, socket/process starts, or EULA acceptance until
    # both separate affirmative grants have been supplied for this run.
    if authorized is not True or eula is not True:
        raise BootstrapRejected("independent physical bootstrap and EULA assent required")
    if output_dir.exists() or output_dir.is_symlink():
        raise BootstrapRejected("output directory must not exist")
    if (output_dir.parent.is_symlink() or not output_dir.parent.is_dir()
            or not stat.S_ISDIR(output_dir.parent.lstat().st_mode)):
        raise BootstrapRejected("output parent must be existing regular directory")
    if os.environ.get("NODE_OPTIONS"):
        raise BootstrapRejected("NODE_OPTIONS substitutions forbidden")
    if not shutil.which("java") or not shutil.which("node"):
        raise BootstrapRejected("Java21 and Node22 required")
    if _hash_file(_regular(jar)) != JAR_SHA256:
        raise BootstrapRejected("exact #580 Mojang jar SHA256 mismatch")
    # Confirm S49's original bridge-context actual imports before Java.
    from adapters.mineflayer.self_owned_llama import _preflight_mineflayer_dependencies

    _preflight_mineflayer_dependencies()
    with socket.socket() as sock:
        try:
            sock.bind((SERVER_HOST, SERVER_PORT))
        except OSError as exc:
            raise BootstrapRejected("Minecraft port already owned") from exc
    return jar.resolve(strict=True)


def _seal_stopped_world(out: Path, original_jar: Path, probe, spawn, report: dict) -> dict:
    """Seal ONLY after Java + Node have both exited with code 0."""
    root = out / "server"
    world = root / LEVEL
    if not world.is_dir() or world.is_symlink():
        raise BootstrapRejected("stopped Minecraft World did not exist")
    state = _saved_state(world)
    snap = out / "snapshot"
    if snap.exists() or snap.is_symlink():
        raise BootstrapRejected("snapshot destination was not fresh")
    shutil.copytree(world, snap, symlinks=False)
    if _world_files(world) != _world_files(snap):
        raise BootstrapRejected("World files changed while sealing")
    sidecar = out / "initial_native_observation.json"
    sidecar.write_text(json.dumps({
        "schema": "RSEE_BOOTSTRAP_NATIVE_INITIAL_V1",
        "classification": "NATIVE_CAPTURED_STOPPED_BYTES_NOT_SCIENCE_RESULT",
        "initial_spawn": asdict(spawn),
        "initial_probe": asdict(probe),
        "native_stopped_state": state,
        "native_source": "Mineflayer correlated probe + vanilla stopped NBT",
        "java_clean_exit_observed": report["java_clean_exit_observed"],
        "bridge_clean_exit_observed": report["bridge_clean_exit_observed"],
        "stop_ack_inferred": False,
    }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    manifest = out / "snapshot_manifest.json"
    manifest.write_text(json.dumps({
        "schema": SCHEMA,
        "minecraft_version": VERSION, "level_name": LEVEL, "seed": SEED,
        "jar_sha256": _hash_file(original_jar),
        "initial_evidence_sha256": _hash_file(sidecar),
        "files": [
            {"path": name, "size": size, "sha256": sha}
            for name, size, sha in _world_files(snap)
        ],
    }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    binding = verify_world_binding(original_jar, snap, manifest, sidecar)
    return {
        "manifest_sha256": binding.manifest_sha256,
        "native_initial_sha256": binding.initial_evidence_sha256,
        "native_level_seed": SEED,
        "files": len(binding.files),
        "stopped_world_byte_binding_verified": True,
        "physical_bootstrap_performed": True,
        "golden_run_performed": False,
        "stop_ack_inferred": False,
    }


async def _execute(jar: Path, output_dir: Path) -> int:
    """Exactly one disposable Java and one real Mineflayer process."""
    from adapters.mineflayer.s31a_real_server_ci import _write_config

    root = output_dir / "server"
    root.mkdir()
    shutil.copyfile(jar, root / "minecraft.jar")
    if _hash_file(root / "minecraft.jar") != JAR_SHA256:
        raise BootstrapRejected("staged jar mismatch before Java")
    _write_config(root)
    config = root / "server.properties"
    text = config.read_text("utf-8")
    if "level-seed=" in text or "level-name=" + LEVEL + "\n" not in text:
        raise BootstrapRejected("S31A inherited Minecraft configuration drifted")
    config.write_text(text + f"level-seed={SEED}\n", encoding="utf-8")

    report: dict = {
        "status": "FAIL_CLOSED",
        "stage": "PRE_SERVER", "java_launch_count": 0,
        "bridge_launch_count": 0, "llm_post": 0, "self_actions": 0,
        "golden_run": "NOT_RUN",
        "java_clean_exit_observed": False,
        "bridge_clean_exit_observed": False,
    }
    server = collector = session = spawn = probe = None
    success = False
    try:
        report["stage"] = "SERVER_START"
        report["java_launch_count"] = 1
        server, collector, _ = await _ready_server(
            root, root / "minecraft.jar", output_dir / "minecraft_server.log",
        )
        report["stage"] = "FREEZE_RULES"
        for command in (
            "gamerule doDaylightCycle false",
            "gamerule doWeatherCycle false",
            "gamerule doMobSpawning false",
            "time set midnight",
            "weather clear 1000000",
        ):
            _command(server, command)
        assert server.stdin is not None
        await server.stdin.drain()
        report["stage"] = "ONE_MINEFLAYER_PROBE"
        report["bridge_launch_count"] = 1
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(
                host=SERVER_HOST, port=SERVER_PORT,
                username=BOT_USERNAME, version=MINECRAFT_VERSION,
            ),
            startup_timeout_s=12,
        )
        spawn = await _await_spawn(session)
        probe = await _correlated_observe(session, "rsee-bootstrap:initial:001")
        if spawn.session_id != probe.session_id or probe.seq <= spawn.seq:
            raise BootstrapRejected("initial native frame relation invalid")
        report["observed_session_id"] = probe.session_id
        report["initial_probe_seq"] = probe.seq
        success = True
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error_stage"] = report["stage"]
    finally:
        if session is not None:
            try:
                exit_code = await session.shutdown(timeout_s=10)
                report["bridge_exit"] = exit_code
                report["bridge_clean_exit_observed"] = exit_code == 0
            except Exception as exc:
                report["bridge_cleanup_error"] = type(exc).__name__
                await session.terminate()
        try:
            if server is not None:
                await _shutdown_server(server, collector)
                report["java_exit"] = server.returncode
                report["java_clean_exit_observed"] = server.returncode == 0
        except Exception as exc:
            report["java_cleanup_error"] = type(exc).__name__
        # Do not erase the physical World on failure. No retry or fresh reset.
        if (success and report["java_clean_exit_observed"]
                and report["bridge_clean_exit_observed"]):
            try:
                report["stage"] = "SEAL_STOPPED_WORLD"
                report["sealed"] = _seal_stopped_world(
                    output_dir, jar, probe, spawn, report,
                )
                report["status"] = "STOPPED_WORLD_BYTES_SEALED_PHYSICAL_AUDIT_PENDING"
            except (OSError, KeyError, TypeError, ValueError, WorldBindingRejected) as exc:
                report["status"] = "WORLD_SEAL_FAILED"
                report["seal_error_type"] = type(exc).__name__
        else:
            report["status"] = "BOOTSTRAP_TERMINAL_UNQUALIFIED"
        (output_dir / "bootstrap_receipt.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
    return 0 if report["status"] == "STOPPED_WORLD_BYTES_SEALED_PHYSICAL_AUDIT_PENDING" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RSEE Minecraft-only one-shot initial World bootstrap")
    parser.add_argument("--jar", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--authorize-world-bootstrap-once", action="store_true")
    parser.add_argument("--minecraft-eula-accepted", action="store_true")
    args = parser.parse_args(argv)
    try:
        jar = _admit(
            args.jar, args.output_dir,
            authorized=args.authorize_world_bootstrap_once,
            eula=args.minecraft_eula_accepted,
        )
        args.output_dir.mkdir()
        return asyncio.run(_execute(jar, args.output_dir))
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({
            "classification": "RSEE_BOOTSTRAP_BLOCKED_NO_NEW_PROCESS",
            "reason": type(exc).__name__,
            "golden_run": "NOT_RUN",
        }, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
