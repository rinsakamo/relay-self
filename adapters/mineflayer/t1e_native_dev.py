"""Bounded disposable T1e physical DEV probe, never R/V qualification.

Reuse the original S49 physical executor and S51 explicit operator Action
issuer. No autonomous policy claim: these are independently issued fixed
MOVE_BACKWARD fixtures. One native receiver; fixture task writes only the
owned Paper console, never player controls. Lost ACK is a labelled consumer
fault: original bytes remain intact. No TPS actuator or model is invoked.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import shutil
import socket
import subprocess
import time
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.execution import MineflayerCommand, execute_mineflayer_command
from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import _issue, _p
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerLaunchConfig,
    MineflayerPaperL0Shadow,
    MineflayerPaperSnapshot,
)
from adapters.mineflayer.s31a_real_server_ci import (
    _await_spawn,
    _command,
    _correlated_observe,
    _ready_server,
    _shutdown_server,
    _write_config,
)
from adapters.mineflayer.s51_eat_real_ci import _recording_session_type
from relay_self.action_supervision import ActionSupervisor

CONFIRM = "T1E-DISPOSABLE-DEV-ONLY"
CASES = ("normal", "low_health", "hostile", "unknown", "lost_ack")
TICK_CASES = ("t1f_observe", "t1f_loop", "t2_loop")


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def sha(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def rows(log, prefix):
    return [dict(p.split("=", 1) for p in line.split(prefix, 1)[1].split())
            for line in log.read_text().splitlines() if prefix in line]


def measure(root, report):
    """Read original journals; same-domain differences only, no R promotion."""
    def journal(name):
        path = root / name
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    node = journal("node_timing.jsonl")
    commands = journal("commands.jsonl")
    dispatches = [r for r in node if r["type"] == "effect_result" and r["effect"] == "set_control"]
    clears = [r for r in node if r["type"] == "effect_result" and r["effect"] == "clear_controls"]
    shadows = [r for r in node if r["type"] == "paper_l0_shadow"]
    sent = rows(root / "paper.log", "PAPER_DEV_TIME_SAMPLE ")
    received = [r for r in node if r["type"] == "paper_tick_sample"]
    sent_ticks = {r["server_tick"] for r in sent}
    checked_ticks = {r["paper_server_tick"] for r in shadows}
    active = [r for r in shadows if dispatches and clears
              and dispatches[0]["seq"] < r["seq"] < clears[0]["seq"]]
    hazards = [r for r in active if r["assessment"] != "NO_KNOWN_URGENT_SIGNAL"]
    metrics = {
        "paper_sent_ticks": len(sent), "node_received_ticks": len(received),
        "node_emitted_shadow_ticks": len(shadows), "active_shadow_ticks": len(active),
        "paper_ticks_without_emitted_l0": sorted(sent_ticks - checked_ticks, key=int),
        "fresh_world_tick_attested": False,
        "set_control_sends": sum(r.get("effect") == "set_control" for r in commands),
        "clear_control_sends": sum(r.get("effect") == "clear_controls" for r in commands),
        "clear_ack_applied_at_node": len(clears) == 1 and clears[0]["result"] == "applied",
        "node_shadow_emit_to_clear_applied_ms": None,
        "python_danger_receive_to_clear_send_ms": None,
        "python_danger_receive_to_clear_ack_ms": None,
    }
    if len(sent) >= 2:
        metrics["paper_effective_tps"] = ((len(sent) - 1) * 1e9 /
                                          (int(sent[-1]["wall_nanos"]) - int(sent[0]["wall_nanos"])))
    if hazards:
        metrics["active_danger_assessment"] = hazards[0]["assessment"]
        metrics["node_shadow_emit_to_clear_applied_ms"] = (
            int(clears[0]["node_monotonic_ns"]) - int(hazards[0]["node_monotonic_ns"])) / 1e6
    for target, field in (("send", "clear_send_python_ns"), ("ack", "clear_ack_received_python_ns")):
        if field in report and "danger_received_python_ns" in report:
            metrics[f"python_danger_receive_to_clear_{target}_ms"] = (
                report[field] - report["danger_received_python_ns"]) / 1e6
    return metrics


async def run_case(args, case):
    t1f = case.startswith(("t1f_", "t2_"))
    root = args.output / case
    root.mkdir()
    world = root / "server"
    world.mkdir()
    for name in ("cache", "libraries", "versions"):
        if args.bootstrap and (args.bootstrap / name).is_dir():
            shutil.copytree(args.bootstrap / name, world / name)
    shutil.copy2(args.paper, world / "paper.jar")
    _write_config(world)
    properties = (world / "server.properties").read_text().replace(
        "gamemode=creative", "gamemode=survival")
    (world / "server.properties").write_text(properties + "generate-structures=false\n")
    plugins = world / "plugins/RelayMetabolismDev"
    plugins.mkdir(parents=True)
    shutil.copy2(args.plugin, world / "plugins/relay-metabolism-dev.jar")
    template = Path(__file__).parent / "m02_paper_dev/src/main/resources/config.yml"
    config = template.read_text().replace("dev-enabled: false", "dev-enabled: true").replace(
        "adaptive-tick-observer-dev: false", "adaptive-tick-observer-dev: true")
    if t1f:
        config = config.replace("t1f-snapshot-dev: false", "t1f-snapshot-dev: true")
    (plugins / "config.yml").write_text(config)
    log = root / "paper.log"
    report = {"case": case, "status": "INCOMPLETE", "mode": "DEV_ONLY",
              "qualification": False, "science": False, "target_tps": 20,
              "action_source": "EXPLICIT_OPERATOR_FIXED_MOVE_NOT_AUTONOMOUS_POLICY",
              "fixture_duration_s": 0.2 if case == "normal" else 1.0,
              "paper_sha256": sha(args.paper), "plugin_sha256": sha(args.plugin)}
    server = collector = session = fixture = None
    native = commands = timing = None
    try:
        server, collector, _ = await _ready_server(world, world / "paper.jar", log)
        report["java_pid"] = server.pid
        for command in ("gamerule doMobSpawning false", "gamerule spawnRadius 0",
                        "gamerule naturalRegeneration false", "time set day"):
            _command(server, command)
        await server.stdin.drain()
        native = (root / "native.jsonl").open("xb")
        commands = (root / "commands.jsonl").open("xb")
        timing = (root / "python_timing.jsonl").open("x")
        base = _recording_session_type(native, commands)

        async def stage():
            await asyncio.sleep(0.07)
            report["fixture_python_ns"] = time.monotonic_ns()
            if case in ("low_health", "lost_ack"):
                _command(server, "damage RelaySelf 15 minecraft:generic")
            elif case == "hostile":
                _command(server, 'execute at RelaySelf run summon zombie ~ ~ ~2 '
                         '{NoAI:1b,Silent:1b,Invulnerable:1b}')
            elif case == "unknown":
                for _ in range(130):
                    _command(server, 'execute at RelaySelf run summon armor_stand ~ ~ ~ '
                             '{Marker:1b,Invisible:1b,NoGravity:1b}')
            await server.stdin.drain()

        class MeasuredSession(base):
            tick_owner = None
            latest_paper = None
            paper_frames = None

            async def receive(self):
                while True:
                    message = await super().receive()
                    now = time.monotonic_ns()
                    if isinstance(message, MineflayerPaperSnapshot):
                        self.latest_paper = message
                        if self.paper_frames is None:
                            self.paper_frames = []
                        self.paper_frames.append(message)
                        if self.tick_owner is not None:
                            self.tick_owner.observe(message)
                    timing.write(json.dumps({"python_monotonic_ns": now,
                                             "message": asdict(message)}) + "\n")
                    timing.flush()
                    if (isinstance(message, MineflayerPaperL0Shadow)
                            and "dispatch_python_ns" in report and "clear_send_python_ns" not in report):
                        if message.assessment != "NO_KNOWN_URGENT_SIGNAL":
                            report.setdefault("danger_received_python_ns", now)
                            report.setdefault("danger_assessment", message.assessment)
                            report.setdefault("danger_tick", message.paper_server_tick)
                    if isinstance(message, MineflayerEffectResult) and message.effect == "clear_controls":
                        report["clear_ack_received_python_ns"] = now
                        if case == "lost_ack":
                            report["ack_fault"] = "DROP_AT_PYTHON_CONSUMER_ORIGINAL_RAW_RETAINED"
                            continue
                    return message

            async def send_set_control(self, *a, **kw):
                nonlocal fixture
                report["dispatch_python_ns"] = time.monotonic_ns()
                await super().send_set_control(*a, **kw)
                if case != "normal":
                    fixture = asyncio.create_task(stage())

            async def send_clear_controls(self, *a, **kw):
                report["clear_send_python_ns"] = time.monotonic_ns()
                await super().send_clear_controls(*a, **kw)

        os.environ["RELAYSELF_PAPER_TICK_DEV"] = "1"
        os.environ["RELAYSELF_PAPER_TICK_TRACE_DEV"] = str(root / "node_timing.jsonl")
        if t1f:
            os.environ["RELAYSELF_T1F_DEV"] = "1"
        else:
            os.environ.pop("RELAYSELF_T1F_DEV", None)
        session = await MeasuredSession.launch(
            MineflayerLaunchConfig(host="127.0.0.1", port=25565,
                                   username="RelaySelf", version="1.21.8"),
            startup_timeout_s=25)
        report["node_pid"] = session._process.pid
        report["session_id"] = session.started.session_id
        await _await_spawn(session)
        _command(server, "tp RelaySelf 0.5 -60 0.5 0 0")
        await server.stdin.drain()
        await asyncio.sleep(0.8)
        probe = await _correlated_observe(session, "t1e-initial")
        report["initial_probe"] = asdict(probe)
        if t1f:
            from adapters.mineflayer.t1f_continuation_dev import run_continuation
            await run_continuation(session, server, report, root, observe_only=case == "t1f_observe",
                                   accounting=case == "t2_loop",
                                   normal_epochs=args.loop_moves)
            return report
        supervisor = ActionSupervisor()
        issued = _issue(supervisor, "t1e-" + case, "fixed-dev-move", "t1e-move-intent",
                        "bounded MOVE_BACKWARD in disposable DEV", time_base=10)
        report["issued_action"] = asdict(issued)
        command = MineflayerCommand(
            action_id=issued.action_id, binding_id="t1e-explicit-dev-binding",
            action_ref="MOVE_BACKWARD", effect="set_control", control="back", state=True,
            duration_s=report["fixture_duration_s"], cleanup_action_id=issued.action_id + "-clear")
        result = await execute_mineflayer_command(
            session, command, timeout_s=0.5, provenance=_p("t1e-physical"), l0_interrupt_dev=True)
        report["consequence"] = asdict(result)
        # Use the existing supervisor even for this fixed operator fixture.
        close = supervisor.record_outcome if result.status.value == "executed" else supervisor.mark_unknown
        report["terminal_action"] = asdict(close(
            issued.action_id, at_ns=15, provenance=_p("dev-terminal")))
        _command(server, "relaydevsnapshot POST_CLEAR")
        await server.stdin.drain()
        await asyncio.sleep(0.8)
        report["final_probe"] = asdict(await _correlated_observe(session, "t1e-final"))
        marker = [r for r in rows(log, "S_V8_DEV_SNAPSHOT ") if r["marker_id"] == "POST_CLEAR"]
        if len(marker) != 1:
            raise RuntimeError("missing post-clear Paper marker")
        report["post_clear_marker"] = marker[0]
        subsequent = [r for r in rows(log, "PAPER_DEV_MOTOR_SAMPLE ")
                      if int(r["server_tick"]) > int(marker[0]["server_tick"])]
        report["paper_post_clear_samples"] = subsequent
        last = subsequent[-8:]
        consecutive = len(last) == 8 and all(int(b["server_tick"]) == int(a["server_tick"]) + 1
                                            for a, b in zip(last, last[1:]))
        idle = bool(last) and all(r[k] == "false" for r in last for k in
                                 ("forward", "backward", "left", "right", "jump", "sneak", "sprint"))
        distance = max((math.dist(tuple(float(r[k]) for k in ("x", "y", "z")),
                                  tuple(float(last[0][k]) for k in ("x", "y", "z")))
                        for r in last), default=None)
        report["settled_last_eight"] = {"consecutive": consecutive, "input_idle": idle,
                                       "max_pose_delta_m": distance}
        expected = (result.status.value == "executed" if case == "normal" else
                    result.status.value == "failed" and report.get("danger_assessment") == {
                        "low_health": "LOW_HEALTH", "hostile": "KNOWN_NEAR_HOSTILE",
                        "unknown": "UNKNOWN", "lost_ack": "LOW_HEALTH"}[case])
        clear_ok = result.cleanup_receipt is not None and result.cleanup_receipt.result == "applied"
        if case == "lost_ack":
            clear_ok = result.cleanup_receipt is None and report.get("ack_fault") is not None
        report["status"] = "PASS" if (expected and clear_ok and consecutive and idle
                                       and distance is not None and distance < 1e-6) else "FAIL"
    except Exception as exc:
        report.update(status="FAIL", error=f"{type(exc).__name__}: {exc}")
    finally:
        if fixture is not None:
            await fixture
        if t1f and session is not None and session.tick_owner is not None:
            write(root / "t2_ticks.json", session.tick_owner.rows)
        if session is not None:
            try:
                report["node_exit"] = await session.shutdown(timeout_s=12)
            except Exception as exc:
                report["node_cleanup_error"] = repr(exc)
                await session.terminate()
        await _shutdown_server(server, collector)
        if server is not None:
            report["java_exit"] = server.returncode
        for out in (native, commands, timing):
            if out:
                out.close()
        for kind in ("java", "node"):
            pid = report.get(kind + "_pid")
            report[kind + "_pid_absent"] = pid is not None and not Path(f"/proc/{pid}").exists()
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", 25565))
                report["port_rebind"] = True
            except OSError:
                report["port_rebind"] = False
        report["cleanup_complete"] = (report.get("java_exit") == report.get("node_exit") == 0
                                      and report["java_pid_absent"] and report["node_pid_absent"]
                                      and report["port_rebind"])
        if not report["cleanup_complete"]:
            report["status"] = "FAIL"
        report["metrics"] = measure(root, report)
        if not t1f and (report["metrics"]["set_control_sends"] != 1
                or report["metrics"]["clear_control_sends"] != 1):
            report["status"] = "FAIL"
        write(root / "report.json", report)
        write(root / "source_hashes.json", {p.name: sha(p) for p in root.iterdir()
                                           if p.is_file() and p.name != "source_hashes.json"})
        print(json.dumps({k: report.get(k) for k in
                          ("case", "status", "error", "danger_assessment", "cleanup_complete")}), flush=True)
    return report


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--paper", type=Path, required=True)
    parser.add_argument("--plugin", type=Path, required=True)
    parser.add_argument("--bootstrap", type=Path)
    parser.add_argument("--confirm", required=True, choices=[CONFIRM])
    parser.add_argument("--loop-moves", type=int, choices=range(2, 33), default=2)
    parser.add_argument("--cases", nargs="+", choices=CASES + TICK_CASES, default=list(CASES))
    args = parser.parse_args()
    if not args.output.is_absolute() or args.output.exists() or os.environ.get("NODE_OPTIONS"):
        parser.error("fresh absolute output and no Node shim required")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 25565))
    args.output.mkdir()
    write(args.output / "subject.json", {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "diff": subprocess.check_output(["git", "diff"], text=True),
        "runner_sha256": sha(Path(__file__)), "python": subprocess.check_output(
            [os.sys.executable, "--version"], text=True).strip(),
        "node": subprocess.check_output(["node", "--version"], text=True).strip(),
    })
    reports = [await run_case(args, case) for case in args.cases]
    write(args.output / "summary.json", reports)
    return int(any(r["status"] != "PASS" for r in reports))


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
