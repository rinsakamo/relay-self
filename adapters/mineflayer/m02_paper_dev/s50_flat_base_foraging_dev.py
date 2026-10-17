"""One archived superflat World BASE_ON forage DEV; not V8 SCIENCE.

Reuses S31A, native L0, S50 MOVE and S51 EAT Action owners unchanged.
Never modifies source archive, never treats DEV as QUALIFICATION.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import socket
import subprocess
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.m02_paper_dev import s50_flat_ground_dev as flat
from adapters.mineflayer.m02_paper_dev import s51_paper_physics_dev as owner
from adapters.mineflayer.m02_paper_dev.paper_foraging_dev import paper_ground_forage
from adapters.mineflayer.m02_paper_dev.v7_paired_config import ARMS, TEMPLATE, render_arm
from adapters.mineflayer.m02_paper_dev.v8_stopped_world_clone_dev import (
    PAPER_JAR_SHA256,
    need,
    sha,
    world_index,
)
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from adapters.mineflayer.s31a_real_server_ci import (
    _await_spawn,
    _command,
    _correlated_observe,
    _ready_server,
    _shutdown_server,
)
from adapters.mineflayer.s51_eat_real_ci import _recording_session_type

CONFIRM = "S50-FLAT-BASE-ON-ONE-WORLD-DEV-ONLY"
ARM = "BASE_ON"
LEVEL_SHA = "1cd714e9607a8015ca37918f11717ab92f2e0d44718c439d7d83a9a36dac1845"
PLUGIN_SHA = "d620935f6f03f3239cebbef0b931ba97482f596e5457feec9b680fe2e14da486"
FLAT_SOURCE = "flat-source/server/world"


def write(path: Path, data: dict | list) -> None:
    with path.open("x", encoding="utf-8") as out:
        out.write(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")


def preflight(archive: Path, paper: Path, plugin: Path, plugin_sha: str,
              output: Path, confirm: str) -> list[dict]:
    need(confirm == CONFIRM, "fresh FLAT BASE_ON DEV confirmation required")
    need(output.is_absolute() and not output.exists()
         and output.parent.is_dir() and not output.parent.is_symlink(),
         "new isolated absolute output required")
    owner._fresh_asset(paper, PAPER_JAR_SHA256)
    need(plugin_sha == PLUGIN_SHA, "plugin is not pinned to V8 DEV source")
    owner._fresh_asset(plugin, PLUGIN_SHA)
    original = archive / FLAT_SOURCE
    expected = world_index(original)
    need(sha(original / "level.dat") == LEVEL_SHA,
         "not the recorded unmodified superflat World")
    receipt = json.loads((archive / "flat-source/flat_dev_receipt.json").read_text())
    need(receipt["status"] == "FLAT_GROUND_NATIVE_WITNESSED_DEV_ONLY"
         and receipt["classification"] == flat.CLASSIFICATION
         and receipt["native_surface_witnesses"] == 25
         and receipt["native_missing_markers"] == []
         and receipt["requested_seed"] == flat.FLAT_DEV_SEED
         and receipt["java_exit"] == 0
         and receipt["mineflayer_sessions"] == 0
         and receipt["stopped_world_index"] == expected,
         "archived FLAT Paper native ground not attested")
    log = (archive / "flat-source/paper_console.log").read_text()
    need(len(flat.extract_native_witnesses(log)) == 25,
         "original native grass and clearance markers missing")
    properties = (archive / "flat-source/server/server.properties").read_bytes()
    need(b"level-seed=63101" in properties and b"level-type=" in properties
         and b"flat" in properties and b"normal" not in properties,
         "archived World profile was not superflat")
    source = original.resolve()
    dest = output.resolve(strict=False)
    need(dest != source and dest not in source.parents
         and source not in dest.parents and dest not in archive.resolve().parents
         and archive.resolve() not in dest.parents,
         "source and output overlap")
    need(not os.environ.get("NODE_OPTIONS"), "NODE_OPTIONS forbidden")
    subprocess.run(["node", "-e",
                    "require.resolve('mineflayer');require.resolve('minecraft-protocol')"],
                   cwd=Path(__file__).resolve().parents[1], check=True)
    return expected


async def marker(server, log: Path, name: str) -> dict:
    _command(server, "relaydevsnapshot " + name)
    await server.stdin.drain()
    for _ in range(100):
        found = [x.split("S_V8_DEV_SNAPSHOT ", 1)[1] for x in log.read_text().splitlines()
                 if "S_V8_DEV_SNAPSHOT marker_id=" + name + " " in x]
        need(len(found) <= 1, "duplicate native start marker")
        if found:
            fields = dict(x.split("=", 1) for x in found[0].split())
            need(fields["seed"] == str(flat.FLAT_DEV_SEED),
                 "native FLAT World seed mismatch")
            return fields
        await asyncio.sleep(.05)
    raise RuntimeError("server-side native snapshot not acknowledged")


def source_rows(log: Path, prefix: str) -> list[dict]:
    return [dict(x.split("=", 1) for x in line.split(prefix, 1)[1].split())
            for line in log.read_text().splitlines() if prefix in line]


async def arm_run(archive: Path, output: Path, arm: str, paper: Path,
                  plugin: Path, expected: list[dict]) -> dict:
    root = output / arm
    root.mkdir()
    world = root / "server"
    world.mkdir()
    report = {"mode": "FLAT_DEV_ONLY", "arm": arm, "attempt": 1,
              "status": "INCOMPLETE", "java_launch_attempts": 0, "node_launch_attempts": 0,
              "L1": "OFF", "L2": "OFF", "science_trials": 0,
              "engineering_qualified": False, "food_acquisition_autonomous": False,
              "strict_player_collect_causality": "UNKNOWN",
              "food_fixture": {"item": "cooked_beef", "count": 1,
                               "placement": "RELATIVE_TO_NATIVE_BODY",
                               "surface": "FLAT_GRASS_Y_MINUS_61"}}
    server = collector = session = None
    native = commands = None
    log = root / "paper_server.log"
    try:
        need(owner._port_free(), "port occupied between sequential arms")
        source = archive / FLAT_SOURCE
        need(world_index(source) == expected, "source drift before arm")
        shutil.copytree(source, world / "world")
        need(world_index(world / "world") == expected, "running copy byte mismatch")
        write(root / "initial_world_index.json", expected)
        jar = world / "paper-1.21.8.jar"
        shutil.copyfile(paper, jar)
        (world / "eula.txt").write_text("eula=true\n")
        (world / "server.properties").write_bytes(flat.properties())
        plugin_dir = world / "plugins/RelayMetabolismDev"
        plugin_dir.mkdir(parents=True)
        shutil.copyfile(plugin, world / "plugins/relay-metabolism-paper-dev.jar")
        config = render_arm(TEMPLATE.read_bytes(), arm)
        (plugin_dir / "config.yml").write_bytes(config)
        report.update({"paper_sha256": sha(jar), "plugin_sha256": sha(plugin),
                       "config_sha256": sha(plugin_dir / "config.yml"),
                       "basal_multiplier": ARMS[arm][0], "walk_multiplier": ARMS[arm][1],
                       "initial_copy_matches_archive": True})
        write(root / "pre_java.json", report)
        report["java_launch_attempts"] = 1
        server, collector, _ = await _ready_server(world, jar, log)
        report["java_pid"] = server.pid
        # Same explicit runtime spawn rule for all arms; terrain remains original.
        _command(server, "gamerule spawnRadius 0")
        _command(server, "gamerule doMobSpawning false")
        await server.stdin.drain()
        native = (root / "original_native.jsonl").open("xb")
        commands = (root / "owner_commands.jsonl").open("xb")
        report["node_launch_attempts"] = 1
        session = await _recording_session_type(native, commands).launch(
            MineflayerLaunchConfig(host="127.0.0.1", port=25565,
                                   username="RelaySelf", version="1.21.8"),
            startup_timeout_s=20)
        report["node_pid"] = session._process.pid
        report["session_id"] = session.started.session_id
        spawn = await _await_spawn(session)
        report["native_spawn"] = asdict(spawn)
        report["initial_server_marker"] = await marker(server, log, "INITIAL_" + arm)
        probe = await _correlated_observe(session, "v8-initial-" + arm)
        report["initial_probe"] = asdict(probe)
        progress = {}
        report["foraging"] = progress
        # Journal actual existing S Action issuance without replacing its owner.
        def issue(*args, **kwargs):
            issued = owner._issue(*args, **kwargs)
            with (root / "issued_actions.jsonl").open("a") as out:
                out.write(json.dumps(asdict(issued)) + "\n")
            return issued
        report["stage"] = "L0_SEEK_MOVE_PICKUP"
        await paper_ground_forage(session, server, issuer=issue, provenance=owner._p,
                                  trace=progress, fixed_food_position=None)
        report["pre_eat_server_marker"] = await marker(server, log, "PRE_EAT_" + arm)
        report["stage"] = "S51_EAT"
        report["eating"] = await owner._native_steak(session, server, issuer=issue, preowned=True)
        report["final_probe"] = asdict(await _correlated_observe(session, "v8-final-" + arm))
        report["status"] = "PASS"
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if server is not None and session is not None:
            try:
                report["terminal_server_marker"] = await marker(server, log, "TERMINAL_" + arm)
            except Exception as exc:
                report["terminal_marker_error"] = repr(exc)
        if session is not None:
            try:
                report["node_exit"] = await session.shutdown(timeout_s=12)
            except Exception as exc:
                report["node_cleanup_error"] = repr(exc)
                await session.terminate()
        if server is not None:
            await _shutdown_server(server, collector)
            report["java_exit"] = server.returncode
        for stream in (native, commands):
            if stream is not None:
                stream.close()
        report["port_released"] = owner._port_free()
        try:
            with socket.socket() as witness:
                witness.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                witness.bind(("127.0.0.1", 25565))
            report["port_rebind_witness"] = True
        except OSError:
            report["port_rebind_witness"] = False
        for kind in ("java", "node"):
            pid = report.get(kind + "_pid")
            report[kind + "_pid_absent"] = pid is not None and not Path(f"/proc/{pid}").exists()
        raw = root / "original_native.jsonl"
        frames = [json.loads(x) for x in raw.read_text().splitlines()] if raw.exists() else []
        report["shutdown_ack"] = any(x.get("type") == "shutdown_ack" for x in frames)
        report["connection_end"] = any(x.get("type") == "connection_end" for x in frames)
        if log.exists():
            content = log.read_text()
            report["java_stop_saved"] = "All dimensions are saved" in content
            basal = source_rows(log, "M02_DEV_BASAL_WRITE ")
            motion = source_rows(log, "M02_DEV_MOTION ")
            report["metabolism_source"] = {
                "basal_logged_rows": len(basal),
                "basal_logged_requested": sum(float(x["requested"]) for x in basal),
                "motion_logged_rows": len(motion),
                "motion_blocks": sum(float(x["blocks"]) for x in motion),
                "motion_billed": sum(float(x["billed"]) for x in motion),
                "basal_log_cap": 500, "motion_log_cap": 300,
                "continuous_path_attested": False}
        if (world / "world/level.dat").exists():
            write(root / "saved_world_index.json", world_index(world / "world"))
        report["original_unchanged"] = world_index(archive / FLAT_SOURCE) == expected
        cleanup = all(report.get(x) for x in (
            "port_released", "port_rebind_witness", "java_pid_absent", "node_pid_absent",
            "shutdown_ack", "connection_end", "java_stop_saved", "original_unchanged"))
        report["cleanup_complete"] = cleanup and report.get("java_exit") == report.get("node_exit") == 0
        if not report["cleanup_complete"]:
            report["status"] = "FAIL"
        write(root / "report.json", report)
        hashes = {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob("*"))
                  if p.is_file() and not any(
                      p.is_relative_to(world / sub) for sub in
                      ("cache", "libraries", "versions"))
                  and p != world / "paper-1.21.8.jar"}
        write(root / "sha256.json", hashes)
    return report


async def run(args) -> int:
    expected = preflight(args.archive, args.paper_jar, args.plugin_jar,
                         args.plugin_sha256, args.output, args.confirm)
    args.output.mkdir()
    report = await arm_run(args.archive, args.output, ARM, args.paper_jar,
                           args.plugin_jar, expected)
    need(owner._port_free(), "BASE_ON physical source listener still occupied")
    result = {
        "classification": "S50_FLAT_BASE_ON_L0_FORENSIC_DEV_ONLY",
        "mode": "FLAT_DEV_ONLY",
        "arm": ARM, "behavioral_status": report["status"],
        "initial_original_bytes_retained": world_index(args.archive / FLAT_SOURCE)
                                            == expected,
        "initial_native_marker": report.get("initial_server_marker"),
        "foraging": report.get("foraging"),
        "pickup_source_consistent": report.get("foraging", {}).get("status")
                                     == "PICKUP_SOURCE_CONSISTENT",
        "s51_eat_completed": report.get("eating") is not None,
        "java_started_once": report.get("java_launch_attempts") == 1,
        "node_started_once": report.get("node_launch_attempts") == 1,
        "cleanup_complete": report.get("cleanup_complete", False),
        "R_independent_review": "PENDING",
        "natural_V8_world_unchanged": True, "retries": 0,
        "science_trials": 0, "engineering_qualified": False,
        "science_go": False, "production_go": False,
    }
    write(args.output / "summary.json", result)
    print(json.dumps(result, allow_nan=False, sort_keys=True))
    return 0 if result["cleanup_complete"] else 2


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for field in ("archive", "paper-jar", "plugin-jar", "output"):
        p.add_argument("--" + field, type=Path, required=True)
    p.add_argument("--plugin-sha256", required=True)
    p.add_argument("--confirm", required=True)
    return asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
