"""Disposable real Paper + one Mineflayer owner DASH apparatus (operator DEV).

This is NOT an original S49 authorized forward Action yet. Never present this
apparatus as S49 qualification, native P1 fatigue or M0 energy posting.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import socket
from pathlib import Path

from adapters.mineflayer.p1_dash_native_physics_dev import (
    install_dev_bridge,
    remove_dev_bridge,
)
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerLaunchConfig,
)
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
from adapters.mineflayer.s49_paper_world_first_dev import offline_uuid
from experiments.fatigue_p1 import FatigueProfile, initial_state
from experiments.p1_gait_dev import GaitTickDev, advance_gait_dev

CONFIRM = "P1-DASH-PAPER-EPHEMERAL-DEV"
PAPER_SHA = "8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e"
RUN_SECONDS = 0.65


class DashDevBlocked(RuntimeError):
    """Fail closed without proposing a new S Action."""


def _verified_file(path: Path, expected_sha: str) -> None:
    if (not path.is_file() or path.is_symlink()
            or len(expected_sha) != 64
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha):
        raise DashDevBlocked("pinned jar SHA mismatch or invalid file")


async def _expect_effect(
    session: MineflayerProcessSession, action: str,
) -> None:
    for _ in range(100):
        event = await asyncio.wait_for(session.receive(), timeout=10)
        if isinstance(event, MineflayerEffectResult):
            if event.action_id == action:
                if event.result != "applied":
                    raise DashDevBlocked(f"native effect refused: {action}")
                return
        elif type(event).__name__ in (
            "MineflayerConnectionEnd", "MineflayerCommandError",
            "MineflayerAdapterErrorMessage",
        ):
            raise DashDevBlocked(f"native bridge rejected: {type(event).__name__}")
    raise DashDevBlocked("missing native effect receipt")


async def _one_motor(
    session: MineflayerProcessSession, name: str,
) -> dict[str, object]:
    before = await _correlated_observe(session, f"p1-dev-{name}-before")
    try:
        await session.send_set_control(f"{name}-forward", control="forward", state=True)
        await _expect_effect(session, f"{name}-forward")
        await session.send_set_control(f"{name}-sprint", control="sprint", state=True)
        await _expect_effect(session, f"{name}-sprint")
        await asyncio.sleep(RUN_SECONDS)
    finally:
        await session.send_clear_controls(f"{name}-clear")
        await _expect_effect(session, f"{name}-clear")
    # A new observation is separate from the control acknowledgement.
    await asyncio.sleep(0.15)
    after = await _correlated_observe(session, f"p1-dev-{name}-after")
    delta_x = after.snapshot.position.x - before.snapshot.position.x
    delta_z = after.snapshot.position.z - before.snapshot.position.z
    distance = (delta_x * delta_x + delta_z * delta_z) ** 0.5
    if distance < 0.15 or after.seq <= before.seq:
        raise DashDevBlocked(f"{name}: no reliable actual native displacement")
    return {
        "before_native_seq": before.seq,
        "after_native_seq": after.seq,
        "native_horizontal_displacement_m": distance,
        "requested_host_hold_seconds": RUN_SECONDS,
        "host_hold_is_paper_tick_evidence": False,
        "native_original_s49_authorized": False,
    }


async def run(
    output: Path, paper: Path, paper_sha: str, plugin: Path, plugin_sha: str, *,
    confirmation: str,
) -> int:
    report: dict[str, object] = {
        "classification": "DEV_ONLY",
        "status": "BLOCKED",
        "native_s49_authorized": False,
        "new_action_grants": 0,
        "m0_ledger_posted": False,
        "p1_world_state_updated": False,
        "qualification_go": False,
        "science_go": False,
        "paper_world_started": False,
    }
    server = collector = session = None
    output_created = False
    dev_bridge = None
    try:
        if confirmation != CONFIRM:
            raise DashDevBlocked("explicit disposable DEV confirmation required")
        _verified_file(paper, paper_sha)
        _verified_file(plugin, plugin_sha)
        if paper_sha != PAPER_SHA or paper.resolve() == plugin.resolve():
            raise DashDevBlocked("unexpected Paper build or duplicate jar")
        if (not output.is_absolute() or output.exists()
                or not output.parent.is_dir() or output.is_symlink()
                or any(p.is_symlink() for p in output.parents)
                or os.environ.get("NODE_OPTIONS")):
            raise DashDevBlocked("fresh unshimmed isolated output required")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as check:
            check.bind((SERVER_HOST, SERVER_PORT))
        output.mkdir(mode=0o700)
        output_created = True
        root = output / "world"
        root.mkdir()
        _write_config(root)
        plugins = root / "plugins"
        plugins.mkdir()
        shutil.copyfile(plugin, plugins / "p1-dash-dev.jar")
        report["stage"] = "PAPER_START"
        server, collector, _ = await _ready_server(
            root, paper, output / "paper_server.log",
        )
        report["paper_world_started"] = True
        report["stage"] = "ONE_NATIVE_OWNER"
        dev_bridge = install_dev_bridge()
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(
                host=SERVER_HOST, port=SERVER_PORT,
                username=BOT_USERNAME, version=MINECRAFT_VERSION,
            ),
            startup_timeout_s=15,
            bridge_path=dev_bridge,
        )
        spawned = await _await_spawn(session)
        report["session_id"] = session.started.session_id
        report["spawn_native_seq"] = spawned.seq
        report["stage"] = "BASELINE_RUN"
        baseline = await _one_motor(session, "run")
        report["baseline"] = baseline
        # One operator DEV motor, no concurrent bridge control reader.
        report["stage"] = "DASH_ARM"
        _command(server, f"relaydashdev arm {offline_uuid(BOT_USERNAME)} 100 40")
        assert server.stdin is not None
        await server.stdin.drain()
        await asyncio.sleep(0.10)
        report["stage"] = "DASH_100_PERCENT"
        dash = await _one_motor(session, "dash")
        report["dash"] = dash
        _command(server, "relaydashdev off")
        await server.stdin.drain()
        await asyncio.sleep(0.20)
        log = (output / "paper_server.log").read_text(encoding="utf-8")
        relevant = [
            row for row in log.splitlines()
            if "RELAY_DASH_" in row
        ]
        (output / "paper_dash_rows.log").write_text(
            "\n".join(relevant) + "\n", encoding="utf-8",
        )
        if (not any("RELAY_DASH_ARM " in row for row in relevant)
                or not any("RELAY_DASH_APPLIED " in row for row in relevant)
                or not any("RELAY_DASH_DONE " in row
                           and "modifier_removed=true" in row for row in relevant)
                or any("RELAY_DASH_DENIED" in row for row in relevant)):
            raise DashDevBlocked("server did not attest modifier application and removal")
        ticks = []
        for row in relevant:
            if "RELAY_DASH_TICK tick=" in row:
                raw = row.split("RELAY_DASH_TICK tick=", 1)[1]
                ticks.append(int(raw.split()[0]))
        if len(ticks) < 2 or len(ticks) != len(set(ticks)):
            raise DashDevBlocked("insufficient or duplicated Paper active ticks")
        report["server_sprint_forward_observed_ticks"] = ticks
        # Server positions (not requested host duration) check real speed.
        paper_positions = []
        for row in relevant:
            if "RELAY_DASH_TICK tick=" not in row:
                continue
            raw = row.split("RELAY_DASH_TICK tick=", 1)[1]
            fields = dict(part.split("=", 1) for part in raw.split()
                          if "=" in part)
            paper_positions.append((int(raw.split()[0]),
                                    float(fields["x"]), float(fields["z"])))
        movement_per_tick = [
            ((x2 - x1)**2 + (z2 - z1)**2)**0.5
            for (t1, x1, z1), (t2, x2, z2)
            in zip(paper_positions, paper_positions[1:])
            if t2 == t1 + 1
        ]
        if len(movement_per_tick) < 5:
            raise DashDevBlocked("no five consecutive Paper movement tick intervals")
        sustained_speed_per_tick = sum(movement_per_tick[-5:]) / 5
        report["measured_paper_last_five_tick_avg_m"] = sustained_speed_per_tick
        report["nominal_vanilla_run_per_tick_m"] = 5.61 / 20
        report["speed_gain_configured"] = 0.5
        if sustained_speed_per_tick < 0.34:
            raise DashDevBlocked("DASH modifier did not yield faster server movement")
        report["actual_move_ratio"] = (
            dash["native_horizontal_displacement_m"]
            / baseline["native_horizontal_displacement_m"]
        )
        report["world_tick_whole_interval_attested"] = False
        # Shadow-only P1/M0, never the real physically admitted fatigue ledger.
        profile = FatigueProfile(enabled=True)
        shadow = initial_state(profile, str(report["session_id"]))
        shadow_charge = 0.0
        for _ in ticks:
            receipt = advance_gait_dev(
                profile, shadow,
                GaitTickDev(shadow.session_id, shadow.world_tick + 1,
                            "DASH", applied_dash_power=1.0,
                            available_extra_m0_energy=1.0),
            )
            shadow = receipt.after
            shadow_charge += receipt.added_m0_charge
        report["hypothetical_p1_fatigue"] = shadow.fatigue
        report["hypothetical_extra_m0_charge"] = shadow_charge
        report["paper_active_tick_is_full_tick_proof"] = False
        report["status"] = "PASS"
        return 0
    except BaseException as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return 2
    finally:
        if session is not None:
            try:
                await session.send_clear_controls("p1-dev-final-clear")
                await _expect_effect(session, "p1-dev-final-clear")
            except Exception as exc:
                report["final_clear_error"] = str(exc)
                report["status"] = "BLOCKED"
            try:
                report["node_exit"] = await session.shutdown(timeout_s=8)
            except Exception as exc:
                report["shutdown_error"] = str(exc)
                report["status"] = "BLOCKED"
                await session.terminate()
        if server is not None:
            try:
                _command(server, "relaydashdev off")
                assert server.stdin is not None
                await server.stdin.drain()
            except Exception as exc:
                report["paper_off_error"] = str(exc)
                report["status"] = "BLOCKED"
            try:
                await _shutdown_server(server, collector)
                report["paper_exit"] = server.returncode
            except Exception as exc:
                report["paper_shutdown_error"] = str(exc)
                report["status"] = "BLOCKED"
        if dev_bridge is not None:
            remove_dev_bridge(dev_bridge)
        if output_created:
            (output / "dash_dev_report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--paper", type=Path, required=True)
    parser.add_argument("--paper-sha", required=True)
    parser.add_argument("--plugin", type=Path, required=True)
    parser.add_argument("--plugin-sha", required=True)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    return asyncio.run(run(
        args.output, args.paper, args.paper_sha, args.plugin, args.plugin_sha,
        confirmation=args.confirm,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
