"""Isolated Paper superflat terrain DEV; distinct from V8 natural-world science.

One disposable Java-only run with a source-side native ground/air witness.
No Mineflayer, Self, L0, food, plugin, human-evaluated trial or grant.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import socket
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.v8_stopped_world_clone_dev import (
    PAPER_JAR_SHA256,
    need,
    sha,
    world_index,
)

CONFIRM = "S50-FLAT-GROUND-DIAGNOSTIC-DEV-ONLY"
FLAT_DEV_SEED = 63101  # Intentionally not in the V8 natural-world seed roster.
GROUND_Y = -61  # Paper 1.21.8 default minecraft:flat preset grass block.
PLAYER_FEET_Y = GROUND_Y + 1
GROUND_POINTS = tuple((x, z) for x in (-4, -2, 0, 2, 4)
                      for z in (-4, -2, 0, 2, 4))
CLASSIFICATION = "S50_FLAT_PAPER_NATIVE_SURFACE_DEV_ONLY_NOT_QUALIFIED"


def properties() -> bytes:
    """A separate normal-free world profile; no edits to V8 natural properties."""
    settings = {
        "server-ip": "127.0.0.1",
        "server-port": "25565",
        "online-mode": "false",
        "enforce-secure-profile": "false",
        "level-name": "world",
        "level-type": "minecraft:flat",
        "level-seed": str(FLAT_DEV_SEED),
        "generate-structures": "false",
        "difficulty": "hard",
        "gamemode": "survival",
        "force-gamemode": "true",
        "max-players": "1",
        "spawn-protection": "0",
        "spawn-monsters": "false",
        "spawn-animals": "false",
        "spawn-npcs": "false",
        "simulation-distance": "4",
        "view-distance": "4",
        "enable-rcon": "false",
        "white-list": "false",
        "motd": "RelaySelf isolated flat ground DEV — not V8 SCIENCE",
    }
    return "".join(f"{k}={v}\n" for k, v in settings.items()).encode("utf-8")


def native_surface_commands() -> tuple[tuple[str, str], ...]:
    """Proof commands are executed BY Paper, not inferred from config/fixtures.

    Check native grass-block floor and two clear air blocks at each lattice
    point, including the expected initial spawn and +X food approach corridor.
    A separate future Mineflayer step must still verify the actual bot pose.
    """
    commands = []
    for x, z in GROUND_POINTS:
        marker = f"S50_FLAT_DEV_GROUND_X{x}_Z{z}"
        cmd = (
            "execute in minecraft:overworld "
            f"if block {x} {GROUND_Y} {z} minecraft:grass_block "
            f"if block {x} {PLAYER_FEET_Y} {z} minecraft:air "
            f"if block {x} {PLAYER_FEET_Y + 1} {z} minecraft:air "
            f"run say {marker}"
        )
        commands.append((marker, cmd))
    return tuple(commands)


def extract_native_witnesses(log: str) -> set[str]:
    """Each server marker is distinct; command strings alone do not attest it."""
    found = set()
    for line in log.splitlines():
        for marker, _ in native_surface_commands():
            if f"[Server] {marker}" in line:
                found.add(marker)
    return found


def preflight(paper: Path, output: Path, confirm: str) -> None:
    need(confirm == CONFIRM, "explicit FLAT DEV confirmation required")
    need(paper.is_absolute() and paper.is_file() and not paper.is_symlink()
         and sha(paper) == PAPER_JAR_SHA256,
         "official pinned Paper 1.21.8 SHA256 required")
    need(output.is_absolute() and not output.exists()
         and output.parent.is_dir() and not output.parent.is_symlink()
         and not any(x.is_symlink() for x in output.parents),
         "new isolated absolute FLAT DEV directory required")
    resolved = output.resolve(strict=False)
    need(resolved != paper.resolve() and resolved not in paper.parents
         and paper.resolve() not in resolved.parents,
         "Paper source and output must be disjoint")
    with socket.socket() as sock:
        sock.settimeout(0.5)
        need(sock.connect_ex(("127.0.0.1", 25565)) != 0,
             "Minecraft loopback port already occupied")


async def run(paper: Path, output: Path, confirm: str) -> dict:
    """Create a real world and native geometric witness, then stop and retain."""
    from adapters.mineflayer.s31a_real_server_ci import (
        _command,
        _ready_server,
        _shutdown_server,
    )

    preflight(paper, output, confirm)
    output.mkdir(mode=0o700)
    server_root = output / "server"
    server_root.mkdir()
    jar = server_root / "paper-1.21.8.jar"
    shutil.copyfile(paper, jar)
    props = properties()
    (server_root / "eula.txt").write_text("eula=true\n", encoding="ascii")
    (server_root / "server.properties").write_bytes(props)
    report = {
        "classification": CLASSIFICATION,
        "mode": "FLAT_DEV_ONLY",
        "requested_seed": FLAT_DEV_SEED,
        "world_profile": "minecraft:flat",
        "source_paper_sha256": sha(jar),
        "server_properties_sha256": hashlib.sha256(props).hexdigest(),
        "java_launch_attempts": 0, "java_pid": None,
        "minecraft_world_started": False,
        "native_surface_witnesses": 0,
        "expected_native_surface_witnesses": len(GROUND_POINTS),
        "food_placed": False, "mineflayer_sessions": 0,
        "action_outcomes": 0, "natural_v8_world_modified": False,
        "v8_science_trials": 0, "engineering_qualified": False,
        "science_go": False, "production_go": False,
        "status": "INCOMPLETE",
    }
    server = collector = None
    log = output / "paper_console.log"
    try:
        report["java_launch_attempts"] = 1
        server, collector, _ = await _ready_server(server_root, jar, log)
        report["java_pid"] = server.pid
        report["minecraft_world_started"] = True
        _command(server, "gamerule spawnRadius 0")
        _command(server, "gamerule doMobSpawning false")
        _command(server, f"setworldspawn 0 {PLAYER_FEET_Y} 0")
        for _, cmd in native_surface_commands():
            _command(server, cmd)
        assert server.stdin is not None
        await server.stdin.drain()
        for _ in range(200):
            await asyncio.sleep(0.1)
            found = extract_native_witnesses(
                log.read_text(encoding="utf-8", errors="replace"))
            if len(found) == len(GROUND_POINTS):
                break
        found = extract_native_witnesses(
            log.read_text(encoding="utf-8", errors="replace"))
        report["native_surface_witnesses"] = len(found)
        report["native_missing_markers"] = sorted(
            set(marker for marker, _ in native_surface_commands()) - found)
        need(len(found) == len(GROUND_POINTS),
             "real Paper did not attest entire flat terrain and clear air")
        report["status"] = "FLAT_GROUND_NATIVE_WITNESSED_DEV_ONLY"
    except Exception as exc:
        report["status"] = "FAILED_OR_INCOMPLETE"
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        await _shutdown_server(server, collector)
        report["java_exit"] = server.returncode if server is not None else None
        with socket.socket() as sock:
            report["port_released"] = (
                sock.connect_ex(("127.0.0.1", 25565)) != 0)
        if (server_root / "world").exists():
            try:
                report["stopped_world_index"] = world_index(server_root / "world")
            except Exception as exc:
                report["world_index_error"] = repr(exc)
        if (report["status"] == "FLAT_GROUND_NATIVE_WITNESSED_DEV_ONLY"
                and (report["java_exit"] != 0 or not report["port_released"]
                     or "stopped_world_index" not in report)):
            report["status"] = "FAILED_OR_INCOMPLETE"
        (output / "flat_dev_receipt.json").write_text(
            json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--paper-jar", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--confirm", required=True)
    args = p.parse_args()
    try:
        report = asyncio.run(run(args.paper_jar, args.output, args.confirm))
        code = 0 if report["status"] == "FLAT_GROUND_NATIVE_WITNESSED_DEV_ONLY" else 2
    except (ValueError, OSError) as exc:
        code = 2
        report = {"classification": "S50_FLAT_DEV_PREFLIGHT_REJECTED",
                  "error": f"{type(exc).__name__}: {exc}",
                  "science_go": False, "v8_science_trials": 0}
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
