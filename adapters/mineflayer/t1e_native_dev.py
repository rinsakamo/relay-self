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
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerEffectResult,
    MineflayerLaunchConfig,
    MineflayerPaperL0Shadow,
    MineflayerPaperSnapshot,
    MineflayerShutdownAck,
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
TICK_CASES = ("t1f_observe", "t1f_loop", "t2_loop", "t2_disconnect_move",
              "t2_disconnect_boundary", "t2_disconnect_wait", "t2_lost_ack",
              "t2_delayed_ack", "t2_old_effect", "t1h_stop_move",
              "t1h_pre_stop", "t1h_lost_ack", "t1h_delayed_ack",
              "t1h_disconnect", "t1h_paper_short", "t1h_input_residual",
              "t1h_motion_residual", "t1h_stale_ack", "t1h_double_ack",
              "t1h_disconnect_after_idle", "t1i_stop_loop", "t1i_stop_eat",
              "t1j_resume_move", "t1k_stop_resume_twice",
              "t1k_fault_before_send", "t1k_fault_set_ack", "t1k_fault_clear_ack",
              "t1l_source_soak", "t1m_source_soak")


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
    snapshots = [r for r in node if r["type"] == "paper_snapshot"]
    if snapshots:
        sent = rows(root / "paper.log", "PAPER_DEV_TIME_SAMPLE ")
        sent_ticks = {int(r["server_tick"]) for r in sent}
        received_ticks = {r["data"]["snapshot"]["tick"] for r in snapshots}
        return {
            "schema": "T1F_PAPER_SNAPSHOT_DEV_NOT_LEGACY_CACHE_SHADOW",
            "paper_sent_ticks": len(sent), "node_received_ticks": len(snapshots),
            "node_admitted_ticks": sum(r["data"]["status"] == "ADMITTED" for r in snapshots),
            "paper_ticks_without_node_snapshot": sorted(sent_ticks - received_ticks),
            "set_control_sends": sum(r.get("effect") == "set_control" for r in commands),
            "clear_control_sends": sum(r.get("effect") == "clear_controls" for r in commands),
            "paper_to_node_exact_delay": "UNKNOWN",
            "qualification": False,
        }
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
    t1f = case.startswith(("t1f_", "t2_", "t1h_", "t1i_", "t1j_", "t1k_", "t1l_", "t1m_"))
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
    if case == "t1m_source_soak":
        config = config.replace("t1m-timing-dev: false", "t1m-timing-dev: true")
    (plugins / "config.yml").write_text(config)
    log = root / "paper.log"
    report = {"case": case, "status": "INCOMPLETE", "mode": "DEV_ONLY",
              "qualification": False, "science": False, "target_tps": 20,
              "action_source": "EXPLICIT_OPERATOR_FIXED_MOVE_NOT_AUTONOMOUS_POLICY",
              "eat_stop_stage": args.eat_stop_stage,
              "fixture_duration_s": 0.2 if case == "normal" else 1.0,
              "paper_sha256": sha(args.paper), "plugin_sha256": sha(args.plugin)}
    server = collector = session = fixture = None
    native = commands = timing = None
    try:
        server, collector, _ = await _ready_server(world, world / "paper.jar", log)
        report["java_pid"] = server.pid
        report["java_starttime"] = Path(f"/proc/{server.pid}/stat").read_text().split()[21]
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
            consume_tick_accounting = True
            source_lost = False
            previous_clear = None
            deferred_effect = None

            def request_t1i_stop(self, stop_id, **kwargs):
                self.t1i_stop_owner.request(stop_id, **kwargs)
                self.consume_tick_accounting = False
                self.tick_owner.failed = True
                report["stop_requested_python_ns"] = time.monotonic_ns()
                report["accounting_at_stop"] = {
                    "ticks": len(self.tick_owner.rows),
                    "credit_count": self.tick_owner.energy.credit_count,
                    "energy": asdict(self.tick_owner.energy.body),
                    "fatigue": asdict(self.tick_owner.fatigue),
                }

            async def inject_disconnect(self, boundary):
                if "fault_injection" in report:
                    return
                report["fault_injection"] = {"kind": boundary, "python_ns": time.monotonic_ns(),
                    "accounted_ticks": len(self.tick_owner.rows),
                    "action": self.tick_owner.active_action}
                _command(server, 'kick RelaySelf T1g disposable DEV disconnect')
                await server.stdin.drain()

            async def boundary_fault(self):
                if case == "t2_disconnect_boundary" and "fault_injection" not in report:
                    await self.inject_disconnect("AFTER_TERMINAL_CLEAR_BEFORE_NEXT_ACTION")
                    # Drain queued old observations through the sole reader until
                    # actual terminal evidence; none may grant another Action.
                    from adapters.mineflayer.t1f_continuation_dev import next_tick
                    async with asyncio.timeout(3):
                        while True:
                            await next_tick(self)

            async def receive(self):
                if self.deferred_effect is not None:
                    message, self.deferred_effect = self.deferred_effect, None
                    return message
                while True:
                    try:
                        message = await super().receive()
                    except Exception:
                        if t1f:
                            from adapters.mineflayer.t1f_continuation_dev import _latch_source_loss
                            _latch_source_loss(self)
                        raise
                    now = time.monotonic_ns()
                    if (case == "t1i_stop_eat" and isinstance(message, MineflayerEffectResult)
                            and message.effect == "consume_held"):
                        report.setdefault("eat_native_receipts", []).append(asdict(message))
                        if args.eat_stop_stage == "after_receipt":
                            self.request_t1i_stop("t1i-eat-stop", active_action_id=self.t1i_eat_action_id)
                    if (case == "t1i_stop_eat" and args.eat_stop_stage == "after_observe"
                            and getattr(message, "request_id", "")
                            and message.request_id.startswith("t2-native-meal-after-eating")):
                        self.request_t1i_stop("t1i-eat-stop", active_action_id=self.t1i_eat_action_id)
                    if t1f and isinstance(message, (MineflayerConnectionEnd,
                            MineflayerAdapterErrorMessage, MineflayerCommandError,
                            MineflayerShutdownAck)):
                        from adapters.mineflayer.t1f_continuation_dev import _latch_source_loss
                        _latch_source_loss(self)
                        report.setdefault("source_loss", {"type": type(message).__name__,
                            "seq": message.seq, "python_ns": now,
                            "accounted_ticks": len(self.tick_owner.rows) if self.tick_owner else 0})
                    if isinstance(message, MineflayerPaperSnapshot) and self.consume_tick_accounting:
                        self.latest_paper = message
                        if self.paper_frames is None:
                            self.paper_frames = []
                        self.paper_frames.append(message)
                        if self.tick_owner is not None:
                            self.tick_owner.observe(message)
                            if (case == "t2_disconnect_wait" and self.tick_owner.rows
                                    and self.tick_owner.rows[-1]["activity"] == "WAIT_DEV"):
                                await self.inject_disconnect("DURING_OBSERVED_WAIT_DEV")
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
                        self.previous_clear = message
                        report["clear_ack_received_python_ns"] = now
                        if (case in ("lost_ack", "t2_lost_ack", "t1h_lost_ack")
                                or (case == "t1k_fault_clear_ack"
                                    and message.action_id.startswith("t1j-"))):
                            report["ack_fault"] = "DROP_AT_PYTHON_CONSUMER_ORIGINAL_RAW_RETAINED"
                            report.setdefault("dropped_clear_receipts", []).append(asdict(message))
                            continue
                        if case in ("t2_delayed_ack", "t1h_delayed_ack") and "ack_fault" not in report:
                            report["ack_fault"] = "DELAY_0.7S_AT_CONSUMER_RAW_RETAINED"
                            await asyncio.sleep(.7)
                    if (case == "t2_disconnect_move" and isinstance(message, MineflayerEffectResult)
                            and message.effect == "set_control" and message.result == "applied"):
                        await self.inject_disconnect("AFTER_SET_CONTROL_APPLIED")
                    if (case == "t2_old_effect" and self.previous_clear is not None
                            and isinstance(message, MineflayerEffectResult)
                            and message.effect == "set_control" and "ack_fault" not in report):
                        # Consumer replay only: original wire bytes are retained,
                        # and no second Motor effect is sent to Minecraft.
                        report["ack_fault"] = "REPLAY_PREVIOUS_EPOCH_CLEAR_BEFORE_CURRENT_DISPATCH_ACK"
                        report["replayed_effect"] = asdict(self.previous_clear)
                        self.deferred_effect = message
                        return self.previous_clear
                    return message

            async def send_set_control(self, *a, **kw):
                nonlocal fixture
                resume_grant = getattr(self, "t1j_resume_permission", None)
                fresh_owner = getattr(self, "t1j_new_stop_owner", None)
                prior_sends = getattr(self, "t1k_resume_sent_ids", None)
                if prior_sends is None:
                    prior_sends = self.t1k_resume_sent_ids = set()
                authorized_resume_send = (
                    case.startswith(("t1j_", "t1k_")) and resume_grant is not None
                    and fresh_owner is not None and fresh_owner.allows_action
                    and a and a[0] == resume_grant.next_action_id
                    and a[0] not in prior_sends
                )
                if (self.source_lost or (self.tick_owner and self.tick_owner.failed)
                        or (getattr(self, "t1h_stop_owner", None) is not None
                            and not self.t1h_stop_owner.allows_action)
                        or (getattr(self, "t1i_stop_owner", None) is not None
                            and not self.t1i_stop_owner.allows_action
                            and not authorized_resume_send)):
                    raise RuntimeError("T1g/T1j lost source or STOP forbids Action effect")
                if authorized_resume_send:
                    # Exactly one physical writer/Action ID after one consumed
                    # explicit reauthorization; never re-send on ACK loss.
                    prior_sends.add(a[0])
                    attempt = self.t1j_resume_attempt
                    attempt.update(motor_send_attempted=True,
                                   motor_send_python_ns=time.monotonic_ns())
                report["dispatch_python_ns"] = time.monotonic_ns()
                await super().send_set_control(*a, **kw)
                if case in ("t1i_stop_loop", "t1j_resume_move",
                             "t1k_stop_resume_twice", "t1k_fault_before_send",
                             "t1k_fault_set_ack", "t1k_fault_clear_ack") and (
                    getattr(self, "t1i_stop_arm_action_id", None) == a[0]
                ):
                    async def t1i_stop_move():
                        await asyncio.sleep(.08)
                        self.request_t1i_stop(
                            "t1i-multi-epoch-stop", active_action_id=a[0],
                            expected_clear_action_id=a[0] + "-clear",
                        )
                    fixture = asyncio.create_task(t1i_stop_move())
                elif case == "t1k_stop_resume_twice" and (
                    getattr(self, "t1k_interrupt_action_id", None) == a[0]
                ):
                    async def t1k_second_stop():
                        await asyncio.sleep(.08)
                        self.t1j_new_stop_owner.request(
                            "t1k-second-stop", active_action_id=a[0],
                            expected_clear_action_id=a[0] + "-clear",
                        )
                        # Freeze new ledger but retain native receive custody.
                        self.consume_tick_accounting = False
                        self.tick_owner.failed = True
                        report["t1k_second_stop_requested"] = True
                        report["t1k_second_stop_requested_python_ns"] = time.monotonic_ns()
                        report["t1k_accounting_at_second_stop"] = {
                            "ticks": len(self.tick_owner.rows),
                            "energy": asdict(self.tick_owner.energy.body),
                            "fatigue": asdict(self.tick_owner.fatigue),
                            "credit_ids": sorted(self.tick_owner.energy._credits),
                            "world_tick": self.tick_owner.previous.data["snapshot"]["world_tick"],
                            "unknown_action_id": a[0],
                        }
                    fixture = asyncio.create_task(t1k_second_stop())
                elif case == "t1k_fault_set_ack" and authorized_resume_send:
                    async def disconnect_after_resume_set():
                        await asyncio.sleep(.08)
                        await self.inject_disconnect("T1K_AFTER_RESUME_SET_SEND")
                    fixture = asyncio.create_task(disconnect_after_resume_set())
                elif case.startswith("t1h_"):
                    # Host owner requests STOP; only original S49 writes Motor.
                    async def request_owner_stop():
                        await asyncio.sleep(0.08)
                        report["stop_requested_python_ns"] = time.monotonic_ns()
                        self.t1h_stop_owner.request(
                            "t1h-operator-stop",
                            active_action_id=self.t1h_active_action_id,
                            expected_clear_action_id=self.t1h_active_action_id + "-clear",
                        )
                    fixture = asyncio.create_task(request_owner_stop())
                elif not case.startswith(("t1i_", "t1j_", "t1k_")) and case != "normal":
                    fixture = asyncio.create_task(stage())

            async def send_equip_item(self, *a, **kw):
                if case == "t1i_stop_eat" and args.eat_stop_stage == "before_equip":
                    self.request_t1i_stop("t1i-eat-stop", active_action_id=self.t1i_eat_action_id)
                if getattr(self, "t1i_stop_owner", None) is not None and (
                    not self.t1i_stop_owner.allows_action
                    or self.source_lost
                ):
                    from adapters.mineflayer.eat_execution import EatingExecutionRejected
                    raise EatingExecutionRejected("T1i owner STOP: equip IO refused")
                await super().send_equip_item(*a, **kw)
                if case == "t1i_stop_eat" and args.eat_stop_stage == "after_equip":
                    self.request_t1i_stop("t1i-eat-stop", active_action_id=self.t1i_eat_action_id)

            async def send_consume_held(self, *a, **kw):
                nonlocal fixture
                if getattr(self, "t1i_stop_owner", None) is not None and (
                    not self.t1i_stop_owner.allows_action
                    or self.source_lost
                ):
                    from adapters.mineflayer.eat_execution import EatingExecutionRejected
                    raise EatingExecutionRejected("T1i owner STOP: consume IO refused")
                await super().send_consume_held(*a, **kw)
                if case == "t1i_stop_eat" and args.eat_stop_stage in ("consume_send", "consume_wait") and (
                    getattr(self, "t1i_eat_action_id", None) is not None
                    and a[0] == self.t1i_eat_action_id + "-consume"
                ):
                    async def t1i_stop_eating():
                        await asyncio.sleep(.08 if args.eat_stop_stage == "consume_wait" else 0)
                        self.request_t1i_stop(
                            "t1i-eat-stop", active_action_id=self.t1i_eat_action_id,
                        )
                    fixture = asyncio.create_task(t1i_stop_eating())

            async def send_clear_controls(self, *a, **kw):
                report["clear_send_python_ns"] = time.monotonic_ns()
                await super().send_clear_controls(*a, **kw)

        os.environ.pop("RELAYSELF_T1H_CLEAR_FAULT_DEV", None)
        if case == "t1h_input_residual":
            os.environ["RELAYSELF_T1H_CLEAR_FAULT_DEV"] = CONFIRM
            report["motor_fault"] = "DEV_CLEAR_NOOP_STUCK_SNEAK_FALSE_APPLIED_ACK"
        os.environ["RELAYSELF_PAPER_TICK_DEV"] = "1"
        os.environ["RELAYSELF_PAPER_TICK_TRACE_DEV"] = str(root / "node_timing.jsonl")
        if case == "t1m_source_soak":
            os.environ["RELAYSELF_T1M_TRACE_DEV"] = str(root / "t1m_node_timing.jsonl")
        else:
            os.environ.pop("RELAYSELF_T1M_TRACE_DEV", None)
        if t1f:
            os.environ["RELAYSELF_T1F_DEV"] = "1"
        else:
            os.environ.pop("RELAYSELF_T1F_DEV", None)
        session = await MeasuredSession.launch(
            MineflayerLaunchConfig(host="127.0.0.1", port=25565,
                                   username="RelaySelf", version="1.21.8"),
            startup_timeout_s=25)
        report["node_pid"] = session._process.pid
        report["node_starttime"] = Path(f"/proc/{session._process.pid}/stat").read_text().split()[21]
        report["session_id"] = session.started.session_id
        await _await_spawn(session)
        if case in ("t1l_source_soak", "t1m_source_soak"):
            # Start the sole source/ledger owner immediately: no legacy MOVE
            # fixture teleport, 0.8s sleep or barrier may discard startup ticks.
            from adapters.mineflayer.t1l_source_soak_dev import run_source_soak
            report.update(action_source="SOURCE_ONLY_NO_MOTOR_ACTION", model_calls=0,
                          tps_actuator=False)
            await run_source_soak(session, report, accounted_ticks=args.soak_ticks,
                                  checkpoint_path=root / "checkpoints")
            return report
        _command(server, "tp RelaySelf 0.5 -60 0.5 0 0")
        await server.stdin.drain()
        await asyncio.sleep(0.8)
        probe = await _correlated_observe(session, "t1e-initial")
        report["initial_probe"] = asdict(probe)
        if case.startswith("t1h_"):
            from adapters.mineflayer.t1h_native_stop_dev import run_stop_move_dev
            await run_stop_move_dev(session, server, report, root)
            return report
        if t1f:
            from adapters.mineflayer.t1f_continuation_dev import run_continuation
            stop_mode = ("MOVE" if case in (
                             "t1i_stop_loop", "t1j_resume_move",
                             "t1k_stop_resume_twice", "t1k_fault_before_send",
                             "t1k_fault_set_ack", "t1k_fault_clear_ack",
                         ) else
                         "EAT" if case == "t1i_stop_eat" else None)
            stop_owner = None
            if stop_mode:
                from adapters.mineflayer.t1h_stop_owner_dev import S49DevStopOwner
                stop_owner = S49DevStopOwner(session.started.session_id)
                session.t1i_stop_owner = stop_owner
            if case.startswith(("t1j_", "t1k_")):
                session.t1j_reauthorization = (
                    "DEV_EXPLICIT_OPERATOR_REAUTHORIZE"
                    if args.t1j_reauthorize == "T1J-DEV-EXPLICIT-REAUTHORIZE-ONCE"
                    else None
                )
            if case.startswith("t1k_"):
                if case == "t1k_stop_resume_twice":
                    from adapters.mineflayer.t1k_resume_lineage_dev import T1kStopResumeLineage
                    session.t1k_lineage = T1kStopResumeLineage(session.started.session_id)
                session.t1k_second_reauthorization = (
                    "DEV_EXPLICIT_OPERATOR_REAUTHORIZE"
                    if args.t1k_second_reauthorize
                    == "T1K-DEV-EXPLICIT-SECOND-REAUTHORIZE-ONCE"
                    else None
                )
                session.t1k_server = server
                session.t1k_paper_log = root / "paper.log"
                session.t1k_fault = (
                    "BEFORE_RESUME_SEND"
                    if case == "t1k_fault_before_send" else None
                )
            await run_continuation(
                session, server, report, root,
                observe_only=case == "t1f_observe",
                accounting=case.startswith(("t2_", "t1i_", "t1j_", "t1k_")),
                normal_epochs=args.loop_moves,
                stop_owner=stop_owner, stop_mode=stop_mode,
                resume_mode=case.startswith(("t1j_", "t1k_")),
                multi_resume_mode=(case == "t1k_stop_resume_twice"),
            )
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
            try:
                await fixture
            except Exception as exc:
                report.update(status="FAIL", fixture_error=f"{type(exc).__name__}: {exc}")
        if t1f and session is not None:
            session.consume_tick_accounting = False
            if session.tick_owner is not None:
                write(root / "t2_ticks.json", session.tick_owner.rows)
                owner = session.tick_owner
                report["t2_final"] = {"ticks": len(owner.rows), "latched": owner.failed,
                    "energy": asdict(owner.energy.body),
                    "fatigue": asdict(owner.fatigue) if owner.fatigue else None,
                    "active_action": owner.active_action,
                    "credit_count": owner.energy.credit_count,
                    "P1_qualified_WAIT": False}
        if session is not None:
            try:
                report["node_exit"] = await session.shutdown(timeout_s=12)
            except Exception as exc:
                report["node_cleanup_error"] = repr(exc)
                report["node_exit"] = await session.terminate()
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
        report["process_reap_complete"] = (report["java_pid_absent"] and report["node_pid_absent"]
                                           and report["port_rebind"]
                                           and report.get("java_exit") is not None
                                           and report.get("node_exit") is not None)
        report["cleanup_complete"] = (report.get("java_exit") == report.get("node_exit") == 0
                                      and report["java_pid_absent"] and report["node_pid_absent"]
                                      and report["port_rebind"])
        if t1f:
            # Read the ORIGINAL bridge stream after the single shutdown owner
            # drains it. Node shutdown_ack is NOT S49 high-level STOP ACK, and
            # exit=0 is not enough when the native terminal trail is incomplete.
            from adapters.mineflayer.t1g_terminal_liveness_dev import audit_bridge_terminal
            try:
                if "session_id" not in report or not (root / "native.jsonl").is_file():
                    raise ValueError("original native terminal source absent")
                journal = [json.loads(line) for line in
                           (root / "native.jsonl").read_text().splitlines()]
                report["terminal_transport"] = asdict(audit_bridge_terminal(
                    journal, session_id=report["session_id"],
                ))
                if not report["terminal_transport"]["bridge_transport_closed"]:
                    report["cleanup_complete"] = False
            except (ValueError, TypeError, KeyError, UnicodeError) as exc:
                report["terminal_transport_error"] = f"{type(exc).__name__}: {exc}"
                report["cleanup_complete"] = False
        if case.startswith("t1h_") and report.get("status") == (
            "T1H_EXPECTATION_MET_AWAITING_RESOURCE_SHUTDOWN"
        ):
            # Positive ACK or expected refusal was evaluated while Paper lived.
            # Normal transport custody remains a separate condition.
            report["status"] = "PASS" if report["cleanup_complete"] else "FAIL"
        if not report["cleanup_complete"]:
            report["status"] = "FAIL"
        report["metrics"] = measure(root, report)
        if case in ("t1l_source_soak", "t1m_source_soak"):
            from adapters.mineflayer.t1l_source_diagnostic_dev import analyze_paper_records
            original_native = ([json.loads(line) for line in
                                (root / "native.jsonl").read_text().splitlines()]
                               if (root / "native.jsonl").exists() else [])
            diagnostic = analyze_paper_records(
                original_native, session_id=report.get("session_id"),
            )
            report["t1l_source_diagnostic"] = diagnostic
            t1l = report.get("t1l", {})
            issued_commands = [json.loads(line) for line in
                               (root / "commands.jsonl").read_text().splitlines()] if (
                                   root / "commands.jsonl").exists() else []
            report["t1l_effect_sends"] = sum(c.get("type") == "effect" for c in issued_commands)
            if (report["t1l_effect_sends"] != 0 or not diagnostic["source_continuous"]
                    or diagnostic["statuses"].get("ADMITTED", 0)
                       != diagnostic["paper_frames"]
                    or t1l.get("accounted_ticks") != args.soak_ticks
                    or not t1l.get("accounted_world_ticks_consecutive")
                    or report["metrics"]["set_control_sends"] != 0
                    or report["metrics"]["clear_control_sends"] != 0
                    or not report["cleanup_complete"]):
                report["status"] = "FAIL"
        if case == "t1m_source_soak":
            from adapters.mineflayer.t1m_timing_join_dev import analyze_t1m_timing
            report["t1m_physical_source_status"] = report["status"]
            try:
                original_native = [json.loads(line) for line in
                                   (root / "native.jsonl").read_text().splitlines()]
                sidecar = [json.loads(line) for line in
                           (root / "t1m_node_timing.jsonl").read_text().splitlines()]
                report["t1m_timing"] = analyze_t1m_timing(
                    (root / "paper.log").read_text().splitlines(),
                    sidecar, original_native,
                )
            except (OSError, ValueError, TypeError, KeyError) as error:
                # Preserve physical source and cleanup results even if diagnostic
                # originals are missing/corrupt. Never synthesize a sidecar.
                report["t1m_timing"] = {
                    "matched_positive_jvm_samples": 0,
                    "source_integrity_violations": ["diagnostic_original_unreadable"],
                    "diagnostic_error": str(error),
                }
            if (not report["t1m_timing"]["matched_positive_jvm_samples"]
                    or report["t1m_timing"]["source_integrity_violations"]):
                report["status"] = "FAIL"
        if case.startswith("t1k_fault_"):
            from adapters.mineflayer.t1k_fault_audit_dev import audit_fault_dev
            cmds = [json.loads(line) for line in
                    (root / "commands.jsonl").read_text().splitlines()]
            raw = [json.loads(line) for line in
                   (root / "native.jsonl").read_text().splitlines()]
            report["t1k_fault_audit"] = audit_fault_dev(case, cmds, raw, report)
        if case == "t1k_stop_resume_twice":
            details = report.get("t1k", {})
            if session is not None and hasattr(session, "t1k_lineage"):
                details["lineage"] = session.t1k_lineage.summary()
            first, second = details.get("first", {}), details.get("second", {})
            cmds = [json.loads(line) for line in
                    (root / "commands.jsonl").read_text().splitlines()]
            effect_ids = [x["action_id"] for x in cmds if x.get("type") == "effect"]
            move_ids = [x["action_id"] for x in cmds if x.get("effect") == "set_control"]
            clear_ids = [x["action_id"] for x in cmds if x.get("effect") == "clear_controls"]
            details["generation_audit"] = {
                "first_resume": first.get("new_action", {}).get("action_id"),
                "second_resume": second.get("new_action", {}).get("action_id"),
                "distinct_resume_ids": (first.get("permit", {}).get("resume_id")
                                        != second.get("permit", {}).get("resume_id")),
                "original_stop_latched": first.get("old_owner_still_latched"),
                "intermediate_stop_latched": second.get("old_owner_still_latched"),
                "each_resume_motor_once": all(move_ids.count(x) == 1 for x in (
                    first.get("new_action", {}).get("action_id"),
                    second.get("new_action", {}).get("action_id"))),
                "all_effect_ids_unique": len(effect_ids) == len(set(effect_ids)),
                "motor_sends": len(move_ids), "clear_sends": len(clear_ids),
            }
            if (not first.get("stop_ack_dev")
                    or first.get("consequence", {}).get("status") != "failed"
                    or first.get("terminal", {}).get("state") != "unknown"
                    or second.get("consequence", {}).get("status") != "executed"
                    or second.get("terminal", {}).get("state") != "outcome"
                    or not all(details["generation_audit"][x] for x in (
                        "distinct_resume_ids", "original_stop_latched",
                        "intermediate_stop_latched", "each_resume_motor_once",
                        "all_effect_ids_unique"))
                    or not details.get("lineage", {}).get("old_owners_still_latched")
                    or details.get("lineage", {}).get("generations") != 2
                    or details.get("lineage", {}).get("failed") is not False
                    or len(move_ids) != args.loop_moves + 3
                    or len(clear_ids) != args.loop_moves + 3
                    or not report["cleanup_complete"]):
                report["status"] = "FAIL"
        if case == "t1j_resume_move":
            detail = report.get("t1j", {})
            cmds = [json.loads(line) for line in
                    (root / "commands.jsonl").read_text().splitlines()]
            motor = [x for x in cmds if x.get("effect") == "set_control"]
            clears = [x for x in cmds if x.get("effect") == "clear_controls"]
            if (not detail or not detail.get("old_owner_still_latched")
                    or not detail.get("new_owner_is_distinct")
                    or detail.get("consequence", {}).get("status") != "executed"
                    or len(motor) != args.loop_moves + 2
                    or len(clears) != args.loop_moves + 2
                    or len({x["action_id"] for x in cmds if x.get("type") == "effect"})
                       != len([x for x in cmds if x.get("type") == "effect"])
                    or detail.get("permit", {}).get("unobserved_world_ticks", 0) < 1
                    or detail.get("historical_m0_p1_retroactively_filled") is not False):
                report["status"] = "FAIL"
        if case.startswith("t1i_"):
            detail = report.get("t1i", {})
            sends = report["metrics"]["set_control_sends"]
            clears = report["metrics"]["clear_control_sends"]
            expected_moves = args.loop_moves + (1 if case == "t1i_stop_loop" else 0)
            original_commands = [json.loads(line) for line in
                                 (root / "commands.jsonl").read_text().splitlines()]
            effect_ids = [c["action_id"] for c in original_commands if c["type"] == "effect"]
            report["effect_id_duplicates"] = len(effect_ids) - len(set(effect_ids))
            report["consume_sends"] = sum(c.get("effect") == "consume_held" for c in original_commands)
            frozen = report.get("accounting_at_stop", {})
            final = report.get("t2_final", {})
            report["accounting_frozen_after_stop"] = bool(frozen) and all(
                frozen[k] == final.get(k) for k in ("ticks", "credit_count", "energy", "fatigue"))
            if (report["effect_id_duplicates"] or report["consume_sends"] > 1
                    or not report["accounting_frozen_after_stop"]):
                report["status"] = "FAIL"
            if (not detail.get("stop_requested")
                    or sends != expected_moves or clears != expected_moves
                    or len([e for e in report.get("epochs", [])
                            if e.get("consequence", {}).get("status") == "executed"])
                        != args.loop_moves
                    or (case == "t1i_stop_loop" and
                        (not detail.get("stop_ack_dev")
                         or detail.get("action_status") != "failed"))
                    or (case == "t1i_stop_eat" and
                        (detail.get("stop_ack_dev") is not None
                         or detail.get("meal_credit_issued") is not False
                         or report.get("t2_final", {}).get("credit_count", 0) != 0))):
                report["status"] = "FAIL"
        if case.startswith("t1h_"):
            positive = case in ("t1h_stop_move", "t1h_double_ack")
            detail = report.get("t1h", {})
            if ((positive and "stop_ack_dev" not in detail)
                    or (not positive and not detail.get("negative_control_pass"))):
                report["status"] = "FAIL"
            expected_count = 0 if case == "t1h_pre_stop" else 1
            if (report["metrics"]["set_control_sends"] != expected_count
                    or report["metrics"]["clear_control_sends"] != expected_count):
                report["status"] = "FAIL"
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
    parser.add_argument("--soak-ticks", type=int, choices=range(100, 2001),
                        default=1200,
                        help="T1l bounded Paper source/accounting ticks, no actions")
    parser.add_argument("--t1j-reauthorize", choices=[
        "T1J-DEV-EXPLICIT-REAUTHORIZE-ONCE",
    ], help="Separate explicit operator grant for exactly one post-STOP T1j MOVE")
    parser.add_argument("--t1k-second-reauthorize", choices=[
        "T1K-DEV-EXPLICIT-SECOND-REAUTHORIZE-ONCE",
    ], help="Separate additional permit for a second STOP/Resume generation")
    parser.add_argument("--eat-stop-stage", default="consume_wait", choices=(
        "before_equip", "after_equip", "consume_send", "consume_wait", "after_receipt", "after_observe"))
    parser.add_argument("--cases", nargs="+", choices=CASES + TICK_CASES, default=list(CASES))
    args = parser.parse_args()
    if not args.output.is_absolute() or args.output.exists() or os.environ.get("NODE_OPTIONS"):
        parser.error("fresh absolute output and no Node shim required")
    resume_cases = [c for c in args.cases if c.startswith(("t1j_", "t1k_"))]
    if (bool(resume_cases) !=
            (args.t1j_reauthorize == "T1J-DEV-EXPLICIT-REAUTHORIZE-ONCE")):
        parser.error("T1j/T1k first reauthorization requires separate opt-in")
    if ((("t1k_stop_resume_twice" in args.cases) !=
         (args.t1k_second_reauthorize
          == "T1K-DEV-EXPLICIT-SECOND-REAUTHORIZE-ONCE"))):
        parser.error("T1k second-generation authorization must be explicit")
    if len(resume_cases) != len(set(resume_cases)) or len(resume_cases) > 1:
        parser.error("One bounded resume case per DEV invocation")
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
