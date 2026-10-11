"""Explicit ONE-shot RSEE disposable Minecraft World snapshot bootstrap.

No Self L0/Action or LLM is invoked. Running this module physically starts one
vanilla Java server and one Mineflayer bridge, ONLY with explicit CLI grants.
Offline imports/tests do not launch anything.
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
import struct
from dataclasses import asdict
from pathlib import Path
from typing import Any

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from adapters.mineflayer.s31a_real_server_ci import (
    BOT_USERNAME,
    MINECRAFT_VERSION,
    SERVER_HOST,
    SERVER_PORT,
    _await_spawn,
    _correlated_observe,
    _ready_server,
    _shutdown_server,
    _write_config,
)
from experiments.standard_env.world_binding import (
    _NBT,
    JAR_SHA256,
    LEVEL,
    MAX_LEVEL,
    SCHEMA,
    SEED,
    WorldBindingRejected,
    _hash_file,
    _regular,
    _seed_from_level,
    _world_files,
    verify_world_binding,
)

CONSENT = "RSEE-ONE-DISPOSABLE-WORLD-BOOTSTRAP"
OBSERVATION_SCHEMA = "RSEE_NATIVE_INITIAL_OBSERVATION_V1"
REPORT = "bootstrap_receipt.json"
MANIFEST = "manifest.json"
OBSERVATION = "initial-observation.json"


class BootstrapRejected(ValueError):
    """Reject unqualified World or absent explicit physical grant."""


def _json_write_new(path: Path, data: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True, ensure_ascii=False,
                  allow_nan=False)
        stream.write("\n")


def _native_nbt(path: Path) -> dict[str, Any]:
    source = _regular(path)
    try:
        with gzip.open(source, "rb") as inp:
            data = inp.read(MAX_LEVEL + 1)
        if len(data) > MAX_LEVEL:
            raise BootstrapRejected("native NBT decompressed size exceeded")
        reader = _NBT(data)
        if reader.number("B") != 10:
            raise BootstrapRejected("native NBT root must be TAG_Compound")
        reader.name()
        result = reader.value(10)
        if reader.pos != len(data) or not isinstance(result, dict):
            raise BootstrapRejected("native NBT trailing/invalid data")
        return result
    except (OSError, EOFError, UnicodeError, ValueError, struct.error) as exc:
        raise BootstrapRejected("native NBT unreadable") from exc


def _saved_native_details(world: Path) -> dict[str, Any]:
    level_path = world / "level.dat"
    if _seed_from_level(level_path) != SEED:
        raise BootstrapRejected("saved native seed differs from 575")
    data = _native_nbt(level_path).get("Data")
    if not isinstance(data, dict):
        raise BootstrapRejected("native level.dat Data absent")
    rules = data.get("GameRules")
    if (not isinstance(rules, dict) or not rules
            or any(not isinstance(k, str) or not isinstance(v, str)
                   for k, v in rules.items())):
        raise BootstrapRejected("native full GameRules not captured")
    for name in ("raining", "thundering", "Time", "DayTime"):
        if type(data.get(name)) is not int and name not in ("Time", "DayTime"):
            raise BootstrapRejected("native weather state missing")
        if name in ("Time", "DayTime") and not isinstance(data.get(name), int):
            raise BootstrapRejected("native time state missing")
    player_dir = world / "playerdata"
    if player_dir.is_symlink() or not player_dir.is_dir():
        raise BootstrapRejected("native playerdata missing")
    players = list(player_dir.glob("*.dat"))
    if len(players) != 1:
        raise BootstrapRejected("expected one and only one saved native player")
    player = _native_nbt(players[0])
    rotation, position = player.get("Rotation"), player.get("Pos")
    if (not isinstance(rotation, list) or len(rotation) != 2
            or not all(isinstance(v, (float, int)) and math.isfinite(v)
                       for v in rotation)
            or not isinstance(position, list) or len(position) != 3
            or not all(isinstance(v, (float, int)) and math.isfinite(v)
                       for v in position)):
        raise BootstrapRejected("saved native player pose incomplete")
    if not isinstance(player.get("Inventory"), list):
        raise BootstrapRejected("saved native player inventory incomplete")
    if not isinstance(player.get("Health"), (float, int)) or not isinstance(
        player.get("foodLevel"), int
    ):
        raise BootstrapRejected("saved native player health/food missing")
    return {
        "source": "STOPPED_VANILLA_NBT",
        "level_dat_sha256": _hash_file(level_path),
        "seed_tag_long": SEED,
        "gamerules": dict(sorted(rules.items())),
        "raining": bool(data["raining"]),
        "thundering": bool(data["thundering"]),
        "world_time": int(data["Time"]),
        "day_time": int(data["DayTime"]),
        "playerdata_file": players[0].relative_to(world).as_posix(),
        "playerdata_sha256": _hash_file(players[0]),
        "rotation": list(rotation),
        "position": list(position),
        "health": float(player["Health"]),
        "food": int(player["foodLevel"]),
        "inventory": player["Inventory"],
    }


def _build_observation(initial: Any, session_id: str, saved: dict) -> dict:
    if initial.kind != "probe" or initial.request_id != "rsee-bootstrap-initial:001":
        raise BootstrapRejected("uncorrelated original Mineflayer initial probe")
    snapshot = initial.snapshot
    if snapshot.time is None:
        raise BootstrapRejected("Mineflayer time missing in correlated probe")
    if not snapshot.nearby_entities_coverage or snapshot.nearby_entities_coverage.truncated:
        raise BootstrapRejected("native Mineflayer probe coverage truncated")
    pos = [snapshot.position.x, snapshot.position.y, snapshot.position.z]
    if any(not math.isfinite(v) for v in pos):
        raise BootstrapRejected("nonfinite native position")
    if any(abs(v - w) > 1.0 for v, w in zip(pos, saved["position"])):
        raise BootstrapRejected("probe and stopped native player position diverged")
    if abs(snapshot.health - saved["health"]) > 0.01 or abs(
        snapshot.food - saved["food"]
    ) > 0.01:
        raise BootstrapRejected("probe and stopped player health/food diverged")
    if snapshot.inventory or saved["inventory"]:
        # First standard World starts empty; don't silently normalize inventories.
        raise BootstrapRejected("initial inventory not empty in both representations")
    return {
        "schema": OBSERVATION_SCHEMA,
        "capture_type": "NATIVE_MINEFLAYER_CORRELATED_AND_STOPPED_VANILLA_NBT",
        "bootstrap_issued_game_actions": 0,
        "session_id": session_id,
        "initial_probe_id": initial.request_id,
        "initial_probe_sequence": initial.seq,
        "mineflayer_snapshot": asdict(snapshot),
        "saved_vanilla_state": saved,
        "provenance_limit": "ONE_SESSION_OPERATOR_OWNED_NOT_INDEPENDENTLY_AUDITED",
        "golden_run_permitted": False,
    }


def _snapshot_manifest(snapshot: Path, observation: Path) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "minecraft_version": MINECRAFT_VERSION,
        "level_name": LEVEL,
        "seed": SEED,
        "jar_sha256": JAR_SHA256,
        "initial_evidence_sha256": _hash_file(observation),
        "files": [
            {"path": path, "size": size, "sha256": digest}
            for path, size, digest in _world_files(snapshot)
        ],
    }


def _port_free() -> None:
    with socket.socket() as sock:
        try:
            sock.bind((SERVER_HOST, SERVER_PORT))
        except OSError as exc:
            raise BootstrapRejected("Minecraft loopback port 25565 is occupied") from exc


def _preflight(jar: Path, output: Path, consent: str, eula: bool) -> Path:
    if consent != CONSENT or eula is not True:
        raise BootstrapRejected("one-run grant and independent EULA assent required")
    if output.is_symlink() or not output.is_dir() or any(output.iterdir()):
        raise BootstrapRejected("new preexisting EMPTY evidence directory required")
    if os.environ.get("NODE_OPTIONS"):
        raise BootstrapRejected("Node shim not allowed")
    from adapters.mineflayer.self_owned_llama import (
        _preflight_mineflayer_dependencies,
        _preflight_python_world_imports,
    )
    from experiments.standard_env.preflight import _check_tools, read_profile
    profile, _ = read_profile()
    if _check_tools(profile):
        raise BootstrapRejected("RSEE host toolchain not qualified")
    _preflight_python_world_imports()
    _preflight_mineflayer_dependencies()
    verified = _regular(jar)
    if _hash_file(verified) != JAR_SHA256:
        raise BootstrapRejected("verified host jar SHA256 differs")
    _port_free()
    return verified


async def _run_once(jar: Path, output: Path) -> int:
    server = collector = session = None
    receipt: dict[str, Any] = {
        "schema": "RSEE_WORLD_BOOTSTRAP_ONCE_V1",
        "status": "BLOCKED",
        "classification": "BOOTSTRAP_UNCONFIRMED",
        "minecraft_launch_attempts": 0,
        "llm_model_launch_attempts": 0,
        "llm_posts": 0,
        "self_actions": 0,
        "snapshot_qualified": False,
    }
    game = output / "game"
    rc = 2
    initial = None
    stopped_cleanly = False
    try:
        game.mkdir(mode=0o700)
        shutil.copyfile(jar, game / "minecraft.jar")
        if _hash_file(game / "minecraft.jar") != JAR_SHA256:
            raise BootstrapRejected("jar copy mismatch")
        _write_config(game)
        properties = game / "server.properties"
        original = properties.read_text("utf-8")
        if "level-seed=" in original or f"level-name={LEVEL}\n" not in original:
            raise BootstrapRejected("unrecognized vanilla config")
        properties.write_text(original + f"level-seed={SEED}\n", encoding="utf-8")
        receipt["minecraft_launch_attempts"] = 1
        server, collector, _ = await _ready_server(
            game, game / "minecraft.jar", output / "minecraft_server.log",
        )
        session = await MineflayerProcessSession.launch(MineflayerLaunchConfig(
            host=SERVER_HOST, port=SERVER_PORT,
            username=BOT_USERNAME, version=MINECRAFT_VERSION,
        ), startup_timeout_s=12)
        spawned = await _await_spawn(session)
        receipt["spawn_seq"] = spawned.seq
        initial = await _correlated_observe(session, "rsee-bootstrap-initial:001")
        receipt["initial_probe_seq"] = initial.seq
        receipt["stage"] = "STOP_OWNED_BRIDGE_AND_SERVER"
        receipt["node_exit"] = await session.shutdown(timeout_s=10)
        if receipt["node_exit"] != 0:
            raise BootstrapRejected("Mineflayer did not cleanly shut down")
        await _shutdown_server(server, collector)
        receipt["server_exit"] = server.returncode
        if server.returncode != 0:
            raise BootstrapRejected("Minecraft server did not exit zero after stop")
        stopped_cleanly = True
        native_world = game / LEVEL
        saved = _saved_native_details(native_world)
        observation = _build_observation(initial, session.started.session_id, saved)
        _json_write_new(output / OBSERVATION, observation)
        target = output / "snapshot"
        # Source was stopped and is immutable for this one-run packaging.
        _world_files(native_world)
        shutil.copytree(native_world, target, symlinks=False)
        if _world_files(native_world) != _world_files(target):
            raise BootstrapRejected("post-stop snapshot bytes not identical")
        _json_write_new(output / MANIFEST, _snapshot_manifest(target, output / OBSERVATION))
        binding = verify_world_binding(
            game / "minecraft.jar", target,
            output / MANIFEST, output / OBSERVATION,
        )
        receipt.update({
            "status": "PASS",
            "classification": "STOPPED_WORLD_SNAPSHOT_BYTES_QUALIFIED_NOT_GOLDEN_GO",
            "snapshot_qualified": True,
            "jar_sha256": binding.jar_sha256,
            "manifest_sha256": binding.manifest_sha256,
            "initial_evidence_sha256": binding.initial_evidence_sha256,
            "snapshot_files": len(binding.files),
            "world_initially_generated": True,
            "minecraft_clean_exit_zero": True,
            "separate_golden_run_permission": False,
        })
        rc = 0
    except Exception as exc:
        receipt["status"] = "FAILED" if server is not None else "BLOCKED"
        receipt["error_type"] = type(exc).__name__
        receipt["stage"] = receipt.get("stage", "INITIAL_WORLD_NOT_QUALIFIED")
        rc = 1 if server is not None else 2
    finally:
        if session is not None and session.process_returncode is None:
            try:
                await session.terminate()
            except Exception as exc:
                receipt["node_cleanup_error"] = type(exc).__name__
                rc = 1
        if server is not None and not stopped_cleanly:
            try:
                await _shutdown_server(server, collector)
            except Exception as exc:
                receipt["server_cleanup_error"] = type(exc).__name__
                rc = 1
            receipt["server_exit"] = server.returncode
        if rc != 0:
            receipt["snapshot_qualified"] = False
            receipt["status"] = "FAILED" if receipt["minecraft_launch_attempts"] else "BLOCKED"
        _json_write_new(output / REPORT, receipt)
    return rc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ONE disposable Minecraft World bootstrap; NEVER Golden Run")
    parser.add_argument("--jar", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--accept-minecraft-eula", action="store_true")
    args = parser.parse_args(argv)
    try:
        jar = _preflight(args.jar, args.output_dir, args.confirm,
                         args.accept_minecraft_eula)
    except (BootstrapRejected, WorldBindingRejected, OSError, ValueError) as exc:
        print(json.dumps({
            "status": "BLOCKED", "reason": type(exc).__name__,
            "minecraft_launch_attempts": 0, "llm_posts": 0,
            "golden_run_ready": False,
        }, sort_keys=True))
        return 2
    return asyncio.run(_run_once(jar, args.output_dir))


if __name__ == "__main__":
    raise SystemExit(main())
