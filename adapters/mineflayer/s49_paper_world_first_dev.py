"""Explicit disposable S49/Paper/P1 DEV runner: one original S49 owner.

Opt-in adapter around the ORIGINAL S49 qualify() and its existing cleanup.
Only the server asset/config and read-only post-Action observer are replaced.
R qualification, V science, and production P1 state are never updated.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import socket
import time
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

from adapters.mineflayer import normal_action as native_action_owner
from adapters.mineflayer import s49_normal_session_real_ci as original
from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import _fresh_asset
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.s31a_real_server_ci import BOT_USERNAME
from adapters.mineflayer.s49_motor_clock_review_dev import review_native_motor_clock_dev
from adapters.mineflayer.s49_native_motor_clock_dev import (
    instrument_native_bridge_dev,
    remove_native_bridge_dev,
)
from adapters.mineflayer.s49_p1_fifth_epoch_dev import (
    compose_third_move_native_dev,
    project_fifth_l0_view_dev,
)
from adapters.mineflayer.s49_p1_l0_capability_dev import compare_body_capability_l0_dev
from adapters.mineflayer.s49_p1_l0_fresh_pair_dev import review_postwait_fresh_l0_input_dev
from adapters.mineflayer.s49_p1_l0_gait_candidate_dev import (
    evaluate_fatigue_aware_fresh_candidate_dev,
)
from adapters.mineflayer.s49_p1_l0_near_decide_dev import decide_bounded_near_move_dev
from adapters.mineflayer.s49_p1_l0_sensitivity_dev import compare_p1_knockdown_dev
from adapters.mineflayer.s49_p1_l0_shadow_dev import preview_postwait_l0_dev
from adapters.mineflayer.s49_p1_motor_budget_dev import propose_issued_motor_budget_dev
from adapters.mineflayer.s49_p1_physical_pair_dev import (
    BASELINE,
    STRESS,
    evaluate_sixth_motor_sensitivity_dev,
)
from adapters.mineflayer.s49_p1_postwait_native_dev import (
    compose_postwait_native_self_world_dev,
)
from adapters.mineflayer.s49_p1_same_native_gait_dev import (
    compare_fifth_p1_gait_dev,
)
from adapters.mineflayer.s49_p1_self_body_dev import (
    compose_s49_p1_dev_self_body,
    compose_s49_p1_postwait_native_dev,
)
from adapters.mineflayer.s49_selfbody_motion_feedback_dev import (
    SelfBodyMotionState,
    apply_to_next_issued,
    propose_motion_correction,
)
from adapters.mineflayer.self_action_evidence import capture_native_action_evidence
from experiments.fatigue_p1 import FatigueProfile
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant

OBSERVER_CONFIG = Path(__file__).parent / "s49_paper_wait_observer_dev" / (
    "src/main/resources/config.yml"
)
CONFIRM = "S49-P1-DEV-DISPOSABLE-PAPER-WORLD"
SCHEMA = "S49_PAPER_WORLD_FIRST_DEV_V1"


class S49PaperDevBlocked(RuntimeError):
    """Invalid or unsafe disposable Paper development run."""


def offline_uuid(player: str) -> str:
    """Java UUID.nameUUIDFromBytes('OfflinePlayer:' + name) for an offline bot."""
    if player != BOT_USERNAME:
        raise S49PaperDevBlocked("unexpected player identity")
    data = bytearray(hashlib.md5(("OfflinePlayer:" + player).encode()).digest())
    data[6] = (data[6] & 0x0f) | 0x30
    data[8] = (data[8] & 0x3f) | 0x80
    return str(UUID(bytes=bytes(data)))


def _fresh_output(directory: Path) -> None:
    if (not directory.is_absolute() or directory.exists()
            or not directory.parent.is_dir()
            or directory.is_symlink()
            or any(p.is_symlink() for p in directory.parents)
            or any((p / ".git").exists() for p in directory.parents)
            or os.environ.get("NODE_OPTIONS")):
        raise S49PaperDevBlocked("fresh isolated output and unshimmed Node required")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 25565))
    directory.mkdir(mode=0o700)


async def _await_complete(paper_log: Path, offset: int, *, timeout: float = 15) -> str:
    """Poll the already-owned Paper console file, without adding a new reader."""
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if paper_log.is_file() and not paper_log.is_symlink():
            with paper_log.open("rb") as stream:
                stream.seek(offset)
                raw = stream.read(65537)
            if len(raw) > 65536:
                raise S49PaperDevBlocked("Paper observer output window too large")
            window = raw.decode("utf-8")
            if "S49_OBSERVER_DENIED" in window or "S49_DEV_BACK_WAIT_ABORT" in window:
                raise S49PaperDevBlocked("Paper observer denied or aborted")
            if "S49_OBSERVER_COMPLETE " in window:
                return window
        await asyncio.sleep(0.15)
    raise S49PaperDevBlocked("Paper observer never completed eight ticks")


async def run(
    output_dir: Path, paper_jar: Path, paper_sha: str,
    observer_jar: Path, observer_sha: str, *, confirmation: str,
    fresh_target_distance: int = 2,
    actual_next_epoch: bool = False,
    actual_fifth_epoch: bool = False,
    compare_fifth_gait: bool = False,
    actual_sixth_motor: bool = False,
    motor_scenario: str = BASELINE,
    selfbody_motion_feedback: bool = False,
    motor_clock_dev: bool = False,
) -> int:
    """One new Paper World, original S49 two MOVE actions, one post-WAIT sample."""
    report = {
        "schema": SCHEMA,
        "classification": "DEV_ONLY",
        "status": "BLOCKED",
        "world_status": "NOT_RUN",
        "qualification_go": False,
        "science_go": False,
        "p1_production_state_updated": False,
        "actual_original_s49_next_epoch": actual_next_epoch,
        "actual_original_s49_fifth_epoch": actual_fifth_epoch,
        "compare_fifth_gait": compare_fifth_gait,
        "actual_sixth_motor": actual_sixth_motor,
        "motor_scenario": motor_scenario,
        "selfbody_motion_feedback": selfbody_motion_feedback,
        "motor_clock_dev": motor_clock_dev,
    }
    created = False
    dev_bridge = None
    try:
        if confirmation != CONFIRM:
            raise S49PaperDevBlocked("explicit disposable DEV confirmation required")
        if type(fresh_target_distance) is not int or fresh_target_distance not in (2, 10):
            raise S49PaperDevBlocked("fresh DEV threat distance must be exactly 2 or 10 blocks")
        if actual_fifth_epoch and (not actual_next_epoch or fresh_target_distance != 2):
            raise S49PaperDevBlocked("fifth DEV epoch requires fourth original MOVE")
        if compare_fifth_gait and not actual_fifth_epoch:
            raise S49PaperDevBlocked("same-native P1 gait review needs fifth original L0")
        if actual_sixth_motor and (not actual_fifth_epoch or not compare_fifth_gait):
            raise S49PaperDevBlocked("physical DEV P1 motor requires same fifth comparison")
        if motor_scenario not in (BASELINE, STRESS) or (
            motor_scenario == STRESS and not actual_sixth_motor
        ):
            raise S49PaperDevBlocked("stress sensitivity requires original sixth DEV Action")
        if selfbody_motion_feedback and (
            not actual_sixth_motor or motor_scenario != BASELINE
        ):
            raise S49PaperDevBlocked(
                "SelfBody Motion Feedback requires original sixth DEV baseline Action"
            )
        if motor_clock_dev and not selfbody_motion_feedback:
            raise S49PaperDevBlocked(
                "passive motor clock requires original SelfBody closed-loop"
            )
        paper_jar = _fresh_asset(paper_jar, paper_sha)
        observer_jar = _fresh_asset(observer_jar, observer_sha)
        if paper_jar.resolve() == observer_jar.resolve():
            raise S49PaperDevBlocked("server and plugin must be separate JARs")
        _fresh_output(output_dir)
        created = True
        if motor_clock_dev:
            dev_bridge = instrument_native_bridge_dev(
                output_dir / "native_motor_clock_dev.jsonl",
            )
        report.update(
            paper_jar_sha256=paper_sha,
            observer_jar_sha256=observer_sha,
            observer_mode="POST_ACTION_ONE_SHOT_DEFAULT_OFF_OUTSIDE_THIS_DEV",
        )
        paper_log = output_dir / "paper_server.log"
        original_report = output_dir / "original_s49_report.json"
        observed = {
            "server": None, "window": None, "count": 0, "postwait": None,
            "fresh_event": None, "fresh_probe": None,
            "next_l0_probe": None, "native_cleared_seq": None,
            "third_action": None, "third_move_probe": None,
            "third_move_model": None, "third_move_body": None,
            "fifth_l0_probe": None, "fifth_l0_view": None,
            "fifth_gait_compare": None,
            "original_session": None, "sixth_l0_probe": None,
            "sixth_clear_seq": None, "actual_sixth_motor_command": None,
            "sixth_motor_sensitivity": None,
            "motion_state": None, "motion_correction": None,
            "motion_pre_sixth": None,
            "third_clear_seq": None,
            "fresh_trace": [],
        }
        # This mutable list is retained even if original qualify() stops:
        # failed World DEV runs preserve the observer's bounded event diagnostics.
        report["postwait_fresh_event_trace_dev"] = observed["fresh_trace"]
        unpatched_config = original._write_config
        unpatched_ready = original._ready_server
        original_executor = original.NormalSessionActionExecutor
        original_native_execute = native_action_owner.execute_mineflayer_command

        def paper_fetch(target: Path) -> dict:
            shutil.copyfile(paper_jar, target)
            return {"runtime": "PAPER_1_21_8_DISPOSABLE_DEV",
                    "paper_asset_sha256": paper_sha}

        def paper_config(root: Path) -> None:
            unpatched_config(root)
            plugin_dir = root / "plugins"
            plugin_dir.mkdir(exist_ok=False)
            shutil.copyfile(observer_jar, plugin_dir / "s49-wait-observer-dev.jar")
            config_dir = plugin_dir / "RelayS49WaitObserverDev"
            config_dir.mkdir()
            config = OBSERVER_CONFIG.read_text(encoding="utf-8")
            if (config.count("enabled: false") != 1
                    or config.count("expected-player-name: RelaySelf") != 1):
                raise S49PaperDevBlocked("unexpected Paper observer config")
            (config_dir / "config.yml").write_text(
                config.replace("enabled: false", "enabled: true"),
                encoding="utf-8",
            )

        async def paper_ready(*args):
            result = await unpatched_ready(*args)
            observed["server"] = result[0]
            report["world_status"] = "PAPER_SERVER_STARTED"
            return result

        class OriginalS49WithPassivePaperDEV(original_executor):
            async def execute(self, *args, **kwargs):
                receipt = await super().execute(*args, **kwargs)
                observed["count"] += 1
                if selfbody_motion_feedback:
                    previous = observed["motion_state"]
                    if previous is None:
                        previous = SelfBodyMotionState(self.session_id)
                    if (previous.session_id != self.session_id
                            or self.supervisor.open_actions
                            or observed["count"] > 4):
                        raise S49PaperDevBlocked("SelfBody Motion lacks sole closed S49 owner")
                    requested = (
                        observed["actual_sixth_motor_command"]["actual_issued_duration_s"]
                        if observed["count"] == 4 else 0.2
                    )
                    observed["motion_state"] = previous.observe_closed(
                        receipt.consequence, requested_duration_s=requested,
                    )
                if observed["count"] == 3 and actual_fifth_epoch:
                    # Third Action was issued by ORIGINAL S49 in its fourth
                    # L0 epoch, with existing S14/S16 gates and executor.
                    if (not args or args[0].started.session_id != self.session_id
                            or self.supervisor.open_actions
                            or observed["postwait"] is None):
                        raise S49PaperDevBlocked("third Action not closed on original owner")
                    evidence = capture_native_action_evidence(receipt.consequence)
                    third = {
                        "action": receipt.terminal.action_id,
                        "source": self.session_id,
                        "terminal": receipt.terminal.state.value,
                        "movement_m": receipt.consequence.movement_distance,
                        "execution_evidence": evidence,
                    }
                    observed["third_action"] = third
                    observed["third_move_probe"] = await original._correlated_observe(
                        args[0],
                        f"s49-third-move:{self.session_id}:{third['action']}",
                    )
                    model, projected = compose_third_move_native_dev(
                        third, observed["third_move_probe"],
                        previous_wait_native_seq=observed["postwait"].seq,
                    )
                    observed["third_move_model"] = model
                    observed["third_move_body"] = projected
                    server = observed["server"]
                    if server is None or server.stdin is None:
                        raise S49PaperDevBlocked("third Action lost original Paper owner")
                    # Clear the previous target, confirmed by the sole native
                    # receiver while host.run_session awaits this Action.
                    original._command(server, "kill @e[type=minecraft:zombie]")
                    await server.stdin.drain()
                    clear_deadline = time.monotonic() + 12.0
                    for _ in range(100):
                        remaining = clear_deadline - time.monotonic()
                        if remaining <= 0:
                            break
                        try:
                            frame = await asyncio.wait_for(
                                args[0].receive(), timeout=remaining,
                            )
                        except TimeoutError:
                            break
                        if not isinstance(frame, original.MineflayerObservation):
                            if isinstance(frame, original.MineflayerEntityHurt):
                                continue
                            raise S49PaperDevBlocked("unexpected native third clear frame")
                        zombies = [e for e in frame.snapshot.nearby_entities
                                   if e.name == "zombie"]
                        observed["fresh_trace"].append({
                            "stage": "THIRD_CLEAR_OLD", "seq": frame.seq,
                            "kind": frame.kind,
                            "zombie_ids": [e.entity_id for e in zombies],
                        })
                        if (frame.seq > observed["third_move_probe"].seq
                                and not zombies
                                and not frame.snapshot.nearby_entities_coverage.truncated):
                            observed["third_clear_seq"] = frame.seq
                            break
                    if observed["third_clear_seq"] is None:
                        raise S49PaperDevBlocked("third MOVE old zombie not natively cleared")
                    # Only environment staging: L0 remains the sole issuer.
                    original._command(
                        server, "execute at RelaySelf run summon minecraft:zombie "
                        "~10 ~ ~ {NoAI:1b,Silent:1b,PersistenceRequired:1b,"
                        "Invulnerable:1b}",
                    )
                    await server.stdin.drain()
                    return receipt
                if observed["count"] != 2:
                    return receipt
                if actual_sixth_motor:
                    if not args or args[0].started.session_id != self.session_id:
                        raise S49PaperDevBlocked("sixth motor DEV missing original session owner")
                    observed["original_session"] = args[0]
                # The original S16 receipts are already completed; this
                # callback does not issue another Minecraft native Action.
                capture_native_action_evidence(receipt.consequence)
                server = observed["server"]
                if server is None or server.stdin is None:
                    raise S49PaperDevBlocked("original S49 server no longer owned")
                # Native clear ACK is not a server-effective release tick.
                # Give the server time to settle before the independent
                # Paper idle observation; the delay itself admits no ticks.
                await asyncio.sleep(0.5)
                offset = paper_log.stat().st_size if paper_log.exists() else 0
                original._command(
                    server, "relays49observe "
                    + receipt.terminal.action_id + " "
                    + self.session_id + " " + offline_uuid(BOT_USERNAME),
                )
                await server.stdin.drain()
                observed["window"] = await _await_complete(paper_log, offset)
                (output_dir / "paper_observer_window.log").write_text(
                    observed["window"], encoding="utf-8",
                )
                # The original host awaits on_action_request → executor.execute;
                # it cannot also receive on this same session until we return.
                # Use the SAME original session and its existing correlated
                # probe helper. No second receiver/task, issuer or Action.
                if (not args or args[0].started.session_id != self.session_id
                        or self.supervisor.open_actions):
                    raise S49PaperDevBlocked(
                        "post-WAIT native read requires closed original owner"
                    )
                request_id = (
                    f"s49-postwait:{self.session_id}:{receipt.terminal.action_id}"
                )
                observed["postwait"] = await original._correlated_observe(
                    args[0], request_id,
                )
                # DEV-only STAGING: after (never during) the Paper WAIT
                # window, cause one new external World entity event. No
                # second reader, Self Action or original L0 permission.
                pre = observed["postwait"]
                prior_zombies = {
                    e.entity_id for e in pre.snapshot.nearby_entities
                    if e.name == "zombie"
                }
                original._command(server, "kill @e[type=minecraft:zombie]")
                await server.stdin.drain()
                # Two-phase external World stimulus: a Paper "Killed"
                # console line does not prove Mineflayer's entity registry
                # has dropped the old target yet. First wait until the
                # original single JSONL reader OBSERVES no zombie, then
                # summon. Previous run showed overlapping 2-zombie
                # entitySpawn before the stale entity disappeared.
                clear_deadline = time.monotonic() + 12.0
                cleared_seq = None
                for _ in range(100):
                    remaining = clear_deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    try:
                        frame = await asyncio.wait_for(
                            args[0].receive(), timeout=remaining,
                        )
                    except TimeoutError:
                        break
                    if not isinstance(frame, original.MineflayerObservation):
                        if isinstance(frame, original.MineflayerEntityHurt):
                            continue
                        raise S49PaperDevBlocked("unexpected native clear frame")
                    zombies = [
                        e for e in frame.snapshot.nearby_entities
                        if e.name == "zombie"
                    ]
                    observed["fresh_trace"].append({
                        "stage": "CLEAR_OLD", "seq": frame.seq,
                        "kind": frame.kind,
                        "zombie_ids": [e.entity_id for e in zombies],
                    })
                    if (frame.seq > pre.seq and not zombies
                            and not frame.snapshot.nearby_entities_coverage.truncated):
                        cleared_seq = frame.seq
                        break
                if cleared_seq is None:
                    raise S49PaperDevBlocked("old zombie never cleared from native source")

                # Only after native clear is observed may a new single
                # stimulus be issued by the external DEV World operator.
                original._command(
                    server,
                    "execute at RelaySelf run summon minecraft:zombie "
                    f"~{fresh_target_distance} ~ ~ "
                    "{NoAI:1b,Silent:1b,PersistenceRequired:1b,"
                    "Invulnerable:1b}",
                )
                await server.stdin.drain()
                if actual_next_epoch:
                    # The original host.run_session is suspended in this
                    # Action callback. Do NOT consume the fresh event here:
                    # return control to that SAME host's fourth epoch.
                    observed["native_cleared_seq"] = cleared_seq
                    return receipt
                deadline = time.monotonic() + 12.0
                for _ in range(100):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    try:
                        frame = await asyncio.wait_for(
                            args[0].receive(), timeout=remaining,
                        )
                    except TimeoutError:
                        observed["fresh_trace"].append({
                            "stage": "SPAWN_NEW", "status": "SOURCE_WAIT_TIMED_OUT",
                        })
                        break
                    if not isinstance(frame, original.MineflayerObservation):
                        if isinstance(frame, original.MineflayerEntityHurt):
                            continue
                        raise S49PaperDevBlocked("unexpected post-WAIT native frame")
                    zombies = [
                        e for e in frame.snapshot.nearby_entities
                        if e.name == "zombie"
                    ]
                    observed["fresh_trace"].append({
                        "stage": "SPAWN_NEW", "seq": frame.seq,
                        "kind": frame.kind,
                        "zombie_ids": [e.entity_id for e in zombies],
                    })
                    if frame.seq <= cleared_seq or frame.kind != "entities":
                        continue
                    if (len(zombies) == 1
                            and zombies[0].entity_id not in prior_zombies
                            and not frame.snapshot.nearby_entities_coverage.truncated):
                        observed["fresh_event"] = frame
                        break
                if observed["fresh_event"] is None:
                    raise S49PaperDevBlocked("no fresh single-target native event after WAIT")
                fresh_req = (
                    f"s49-postwait-event:{self.session_id}:"
                    f"{observed['fresh_event'].seq}"
                )
                observed["fresh_probe"] = await original._correlated_observe(
                    args[0], fresh_req,
                )
                return receipt

        async def scoped_native_motor_execute(session, command, *,
                                               timeout_s, provenance):
            # Hook the ORIGINAL S49 executor's S15 transport, after the
            # original Action issue and all existing S14/S16 authorization.
            # No additional Action issuer, reader, grant or process.
            if actual_sixth_motor and observed["sixth_l0_probe"] is not None:
                probe = observed["sixth_l0_probe"]
                gait = observed["fifth_gait_compare"]
                if (observed["actual_sixth_motor_command"] is not None
                        or not isinstance(gait, dict)
                        or session is not observed["original_session"]
                        or probe.session_id != session.started.session_id
                        or probe.request_id is None
                        or not probe.request_id.startswith(
                            f"s49-actual:{probe.session_id}:event-"
                        )
                        or command.action_id != (
                            f"s49-native-move-{probe.request_id.rsplit('-', 1)[-1]}"
                        )
                        or gait["third_original_action_id"]
                        != observed["third_move_model"].third_action_id
                        or gait["candidate_executed"] is not False
                        or gait["source_bound_tick"] is not None
                        or gait["new_grants"] != 0
                        or command.duration_s != gait["baseline_nominal_command_duration_s"]):
                    raise S49PaperDevBlocked("sixth DEV motor timing not bound to original issued Action")
                sensitivity = evaluate_sixth_motor_sensitivity_dev(
                    observed["third_move_model"], gait, motor_scenario,
                )
                if (sensitivity["third_action_id"] != gait["third_original_action_id"]
                        or sensitivity["fifth_native_seq"] != gait["fifth_native_seq"]
                        or sensitivity["action_permission"] is not False
                        or observed["sixth_motor_sensitivity"] is not None):
                    raise S49PaperDevBlocked("sensitivity cannot authorize or alias action")
                proposal = propose_issued_motor_budget_dev(
                    sensitivity,
                    session_id=probe.session_id,
                    sixth_native_seq=probe.seq,
                    issued_action_id=command.action_id,
                )
                adapted_duration = proposal.candidate_duration_s
                command = proposal.apply_to_issued(command)
                if selfbody_motion_feedback:
                    state = observed["motion_state"]
                    if (not isinstance(state, SelfBodyMotionState)
                            or len(state.samples) != 3
                            or state.samples[-1].action_id
                            != observed["third_move_model"].third_action_id
                            or observed["motion_correction"] is not None):
                        raise S49PaperDevBlocked(
                            "SelfBody model must be updated after three closed native MOVEs"
                        )
                    correction = propose_motion_correction(
                        state,
                        current_native_seq=probe.seq,
                        baseline_duration_s=adapted_duration,
                    )
                    command = apply_to_next_issued(
                        correction, command,
                        current_session_id=probe.session_id,
                        current_native_seq=probe.seq,
                    )
                    observed["motion_pre_sixth"] = state
                    observed["motion_correction"] = correction
                observed["sixth_motor_sensitivity"] = sensitivity
                observed["actual_sixth_motor_command"] = {
                    "status": "DEV_ORIGINAL_S49_ISSUED_ACTION_MOTOR_DURATION_CHANGED",
                    "action_id": command.action_id,
                    "native_session_id": probe.session_id,
                    "same_original_native_probe_seq": probe.seq,
                    "p1_model_source_fifth_seq": gait["fifth_native_seq"],
                    "model_held_without_new_wait_recovery": True,
                    "unmodified_original_action_duration_s": proposal.nominal_duration_s,
                    "dev_model_conditioned_duration_s": adapted_duration,
                    "actual_issued_duration_s": command.duration_s,
                    "selfbody_motion_feedback_applied": selfbody_motion_feedback,
                    "dev_motor_sensitivity_scenario": motor_scenario,
                    "dev_motor_sensitivity_profile_sha256":
                        sensitivity["hypothetical_profile_sha256"],
                    "new_action_issuer": False,
                    "new_grant": False,
                    "r_qualified_fatigue": False,
                }
            return await original_native_execute(
                session, command, timeout_s=timeout_s, provenance=provenance,
            )

        # Opt-in candidate changes qualify()'s DEV-only bounded epoch
        # contract, NEVER the original S14/S16 issuer or cleanup.
        async def observe_original_next_probe(reading):
            if (observed["postwait"] is not None
                    and reading.seq > observed["postwait"].seq):
                if (actual_sixth_motor
                        and observed["fifth_l0_view"] is not None
                        and reading.seq > observed["fifth_l0_probe"].seq):
                    if observed["sixth_l0_probe"] is not None:
                        raise S49PaperDevBlocked("multiple sixth native L0 probes")
                    observed["sixth_l0_probe"] = reading
                elif (actual_fifth_epoch
                        and observed["third_move_model"] is not None
                        and reading.seq > observed["third_move_probe"].seq):
                    if observed["fifth_l0_view"] is not None:
                        raise S49PaperDevBlocked("multiple original fifth L0 probes")
                    observed["fifth_l0_probe"] = reading
                    # This passive SelfBody/SelfWorld construction occurs
                    # BEFORE original L0._check/decide, no Action control.
                    observed["fifth_l0_view"] = project_fifth_l0_view_dev(
                        observed["third_move_model"], reading,
                    )
                    if compare_fifth_gait:
                        observed["fifth_gait_compare"] = compare_fifth_p1_gait_dev(
                            observed["third_move_model"], reading,
                        )
                    if actual_sixth_motor:
                        # Explicit disposable DEV external World staging at
                        # original fifth probe while sole L0 host is suspended.
                        # No second receive owner and no extra Action.
                        server = observed["server"]
                        source = observed["original_session"]
                        if (server is None or server.stdin is None
                                or source is None or source.started.session_id
                                != reading.session_id):
                            raise S49PaperDevBlocked("sixth staging lost sole native owner")
                        original._command(server, "kill @e[type=minecraft:zombie]")
                        await server.stdin.drain()
                        deadline = time.monotonic() + 12.0
                        for _ in range(100):
                            remaining = deadline - time.monotonic()
                            if remaining <= 0:
                                break
                            try:
                                frame = await asyncio.wait_for(
                                    source.receive(), timeout=remaining,
                                )
                            except TimeoutError:
                                break
                            if not isinstance(frame, original.MineflayerObservation):
                                if isinstance(frame, original.MineflayerEntityHurt):
                                    continue
                                raise S49PaperDevBlocked("unexpected sixth clear native frame")
                            zombies = [
                                e for e in frame.snapshot.nearby_entities
                                if e.name == "zombie"
                            ]
                            observed["fresh_trace"].append({
                                "stage": "FIFTH_CLEAR_OLD", "seq": frame.seq,
                                "kind": frame.kind,
                                "zombie_ids": [e.entity_id for e in zombies],
                            })
                            if (frame.seq > reading.seq and not zombies
                                    and not frame.snapshot.nearby_entities_coverage.truncated):
                                observed["sixth_clear_seq"] = frame.seq
                                break
                        if observed["sixth_clear_seq"] is None:
                            raise S49PaperDevBlocked("fifth WAIT zombie not natively cleared")
                        original._command(
                            server, "execute at RelaySelf run summon minecraft:zombie "
                            "~2 ~ ~ {NoAI:1b,Silent:1b,PersistenceRequired:1b,"
                            "Invulnerable:1b}",
                        )
                        await server.stdin.drain()
                else:
                    if observed["next_l0_probe"] is not None:
                        raise S49PaperDevBlocked("multiple next-epoch native probes")
                    observed["next_l0_probe"] = reading

        uninstrumented_launch = MineflayerProcessSession.launch

        async def one_existing_session_with_dev_bridge(config, **kwargs):
            if dev_bridge is None or "bridge_path" in kwargs:
                raise S49PaperDevBlocked("DEV clock bridge requires original one-session launch")
            return await uninstrumented_launch(
                config, bridge_path=dev_bridge, **kwargs,
            )

        with (patch.dict(os.environ, {
                "S49_REAL_SERVER_CI": "1",
                **({"S49_NEXT_EPOCH_DEV_ONLY": "1"} if actual_next_epoch else {}),
                **({"S49_FIFTH_EPOCH_DEV_ONLY": "1"} if actual_fifth_epoch else {}),
                **({"S49_SIXTH_EPOCH_DEV_ONLY": "1"} if actual_sixth_motor else {}),
              }),
              (patch.object(MineflayerProcessSession, "launch",
                            one_existing_session_with_dev_bridge)
               if motor_clock_dev else nullcontext()),
              patch.object(original, "_fetch_official_server", paper_fetch),
              patch.object(original, "_write_config", paper_config),
              patch.object(original, "_ready_server", paper_ready),
              patch.object(original, "NormalSessionActionExecutor",
                           OriginalS49WithPassivePaperDEV),
              patch.object(native_action_owner, "execute_mineflayer_command",
                           scoped_native_motor_execute)):
            rc = await original.qualify(
                original_report, paper_log,
                **({
                    "dev_next_epoch": (
                        "MOVE_AWAY" if fresh_target_distance == 2 else "WAIT"
                    ),
                    "live_probe": observe_original_next_probe,
                    **({"dev_fifth_epoch": "WAIT"} if actual_fifth_epoch else {}),
                    **({"dev_sixth_epoch": "MOVE_AWAY"} if actual_sixth_motor else {}),
                } if actual_next_epoch else {}),
            )
        report["original_s49_rc"] = rc
        report["postwait_fresh_target_distance_m"] = fresh_target_distance
        report["original_s49_action_count"] = observed["count"]
        report["world_status"] = "CLOSED_WITH_ORIGINAL_S49_CLEANUP"
        if (rc != 0
                or observed["count"] != (
                    2 + (actual_next_epoch and fresh_target_distance == 2)
                    + actual_sixth_motor
                )
                or observed["window"] is None):
            raise S49PaperDevBlocked("original S49 or Paper observer did not complete")
        source = json.loads(original_report.read_text(encoding="utf-8"))
        if (source.get("node_exit") != 0 or source.get("server_exit") != 0):
            raise S49PaperDevBlocked("original Java/Node cleanup not successful")
        if actual_next_epoch:
            # The last (possibly third) native Action is AFTER the Paper
            # window. For its P1 replay, use only the original two closed
            # Actions that preceded the observation: never rewrite the
            # persisted original report or silently credit an extra MOVE.
            p1_source = dict(source)
            p1_source["actual_native_actions"] = source["actual_native_actions"][:2]
            handoff, p1 = compose_s49_p1_dev_self_body(
                p1_source, observed["window"],
                expected_player_uuid=offline_uuid(BOT_USERNAME),
                profile=FatigueProfile(enabled=True, initial=0.0),
            )
            if observed["postwait"] is None:
                raise S49PaperDevBlocked("missing Paper-complete native body source")
            body, native_after_wait = compose_s49_p1_postwait_native_dev(
                handoff, p1, p1_source["actual_native_actions"][-1],
                observed["postwait"],
                expected_request_id=(
                    f"s49-postwait:{source['session_id']}:{p1['action_id']}"
                ),
            )
            world_body = compose_postwait_native_self_world_dev(
                body, observed["postwait"],
            )
            native = observed["next_l0_probe"]
            choices = source.get("decisions")
            pairs = source.get("source_pair_trace")
            witness = source.get("dev_original_next_epoch")
            expected_choice = (
                "MOVE_AWAY" if fresh_target_distance == 2 else "WAIT"
            )
            expected_epochs = (
                6 if actual_sixth_motor else 5 if actual_fifth_epoch else 4
            )
            if (native is None
                    or observed["native_cleared_seq"] is None
                    or not isinstance(choices, list) or len(choices) != expected_epochs
                    or not isinstance(pairs, list) or len(pairs) != expected_epochs
                    or not isinstance(witness, dict)
                    or witness.get("actual_original_host_decide") is not True
                    or witness.get("same_host_events") != expected_epochs
                    or witness.get("next_choice") != expected_choice
                    or witness.get("next_event_seq") != choices[3]["event_seq"]
                    or witness.get("next_probe_seq") != choices[3]["probe_seq"]
                    or witness.get("next_probe_seq") != native.seq
                    or witness.get("next_event_seq") != pairs[3]["event_seq"]
                    or witness.get("next_probe_seq") != pairs[3]["probe_seq"]
                    or witness.get("next_event_seq") <= observed["native_cleared_seq"]
                    or native.session_id != source["session_id"]
                    or native.kind != "probe"
                    or native.request_id != (
                        f"s49-actual:{source['session_id']}:"
                        f"event-{witness['next_event_seq']}"
                    )
                    or choices[3]["selected"] != expected_choice
                    or choices[3]["issued"] != (expected_choice == "MOVE_AWAY")
                    or witness["same_host_action_requests"]
                    != (4 if actual_sixth_motor
                        else 3 if expected_choice == "MOVE_AWAY" else 2)
                    or len(source["actual_native_actions"])
                    != (4 if actual_sixth_motor
                        else 3 if expected_choice == "MOVE_AWAY" else 2)
                    or body.observation is None
                    or body.observation.native_seq != observed["postwait"].seq
                    or world_body["world_body_same_object"] is not True
                    or native_after_wait["p1_dev_origin"] != "hypothesis"
                    or p1["dev_fatigue_mode"] != "MOVE_DISTANCE"
                    or p1["dev_fatigue_recovered"] <= 0
                    or p1["source_bound_tick"] is not None
                    or p1["wait_ticks_admitted"] != 0):
                raise S49PaperDevBlocked("original fourth L0 epoch not source-proven")
            if actual_fifth_epoch:
                third_model = observed["third_move_model"]
                third_view = observed["third_move_body"]
                fifth_view = observed["fifth_l0_view"]
                fifth_native = observed["fifth_l0_probe"]
                fifth_receipt = source["actual_native_actions"][2]
                fifth = source.get("dev_original_fifth_epoch")
                if (third_model is None or third_view is None
                        or fifth_view is None or fifth_native is None
                        or not isinstance(fifth, dict)
                        or p1["dev_fatigue_after"] != 0
                        or third_view["p1_model_fatigue_before"] != 0
                        or third_model.model_profile_sha256 != p1["p1_profile_sha256"]
                        or third_model.third_action_id != fifth_receipt["action"]
                        or third_model.move_distance_m != fifth_receipt["movement_m"]
                        or observed["third_action"] != {
                            key: fifth_receipt[key]
                            for key in (
                                "action", "source", "terminal",
                                "movement_m", "execution_evidence"
                            )
                        }
                        or observed["third_clear_seq"] is None
                        or fifth["same_host_events"] != expected_epochs
                        or fifth["same_host_action_requests"]
                        != (4 if actual_sixth_motor else 3)
                        or fifth["next_choice"] != "WAIT"
                        or fifth["next_action_issued"] is not False
                        or fifth["next_event_seq"] != choices[4]["event_seq"]
                        or fifth["next_probe_seq"] != choices[4]["probe_seq"]
                        or fifth["next_event_seq"] != pairs[4]["event_seq"]
                        or fifth["next_probe_seq"] != pairs[4]["probe_seq"]
                        or fifth["next_probe_seq"] != fifth_native.seq
                        or fifth["next_event_seq"] <= observed["third_clear_seq"]
                        or fifth["next_event_seq"] <= third_model.third_after_probe.seq
                        or fifth_view["native_seq"] != fifth_native.seq
                        or fifth_view["p1_model_fatigue"] != third_model.model_fatigue
                        or fifth_view["p1_model_sensor_pct"]
                        != third_view["p1_model_sensor_pct"]
                        or fifth_view["projection_before_original_l0_decide"] is not True
                        or choices[4]["issued"] is not False
                        or len(source["actual_native_actions"])
                        != (4 if actual_sixth_motor else 3)
                        or fifth["p1_as_action_authority"] is not False):
                    raise S49PaperDevBlocked("fifth original epoch/P1 join rejected")
                if compare_fifth_gait:
                    gait = observed["fifth_gait_compare"]
                    if (not isinstance(gait, dict)
                            or gait["fifth_native_seq"] != fifth_native.seq
                            or gait["fifth_native_request_id"] != fifth_native.request_id
                            or gait["third_original_action_id"] != third_model.third_action_id
                            or gait["same_native_world_input"] is not True
                            or gait["baseline_nominal_command_duration_s"]
                            <= gait["fatigue_aware_candidate_duration_s"]
                            or gait["candidate_executed"] is not False
                            or gait["new_grants"] != 0):
                        raise S49PaperDevBlocked("fifth same-native gait model comparison invalid")
                if actual_sixth_motor:
                    six = source.get("dev_original_sixth_epoch")
                    physical = observed["actual_sixth_motor_command"]
                    last = source["actual_native_actions"][-1]
                    sixth_probe = observed["sixth_l0_probe"]
                    gait = observed["fifth_gait_compare"]
                    if (not isinstance(six, dict)
                            or not isinstance(physical, dict)
                            or not isinstance(sixth_probe, original.MineflayerObservation)
                            or observed["sixth_clear_seq"] is None
                            or six.get("actual_original_host_decide") is not True
                            or six.get("same_host_events") != 6
                            or six.get("same_host_action_requests") != 4
                            or six.get("selected") != "MOVE_AWAY"
                            or six.get("action_issued") is not True
                            or six.get("event_seq") != choices[5]["event_seq"]
                            or six.get("probe_seq") != choices[5]["probe_seq"]
                            or six.get("probe_seq") != sixth_probe.seq
                            or six.get("event_seq") <= observed["sixth_clear_seq"]
                            or last.get("event_seq") != six["event_seq"]
                            or last.get("probe_seq") != six["probe_seq"]
                            or last.get("action") != physical["action_id"]
                            or last.get("terminal") != "outcome"
                            or last.get("movement_m", 0) < 0.05
                            or physical["native_session_id"] != source["session_id"]
                            or physical["same_original_native_probe_seq"]
                            != sixth_probe.seq
                            or physical["p1_model_source_fifth_seq"]
                            != gait["fifth_native_seq"]
                            or physical["dev_model_conditioned_duration_s"]
                            != observed["sixth_motor_sensitivity"]["duration_s"]
                            or physical["dev_motor_sensitivity_scenario"] != motor_scenario
                            or physical["dev_motor_sensitivity_profile_sha256"]
                            != observed["sixth_motor_sensitivity"]["hypothetical_profile_sha256"]
                            or physical["unmodified_original_action_duration_s"]
                            != gait["baseline_nominal_command_duration_s"]
                            or physical["new_action_issuer"] is not False
                            or physical["r_qualified_fatigue"] is not False):
                        raise S49PaperDevBlocked("sixth original Action motor DEV evidence mismatch")
                    if selfbody_motion_feedback:
                        pre = observed["motion_pre_sixth"]
                        correction = observed["motion_correction"]
                        after = observed["motion_state"]
                        if (not isinstance(pre, SelfBodyMotionState)
                                or correction is None
                                or not isinstance(after, SelfBodyMotionState)
                                or len(pre.samples) != 3
                                or len(after.samples) != 4
                                or after.samples[-1].action_id != last["action"]
                                or after.samples[-1].observed_displacement_m
                                != last["movement_m"]
                                or after.samples[-1].requested_duration_s
                                != physical["actual_issued_duration_s"]
                                or physical["actual_issued_duration_s"]
                                != correction.proposed_duration_s
                                or physical["selfbody_motion_feedback_applied"] is not True
                                or correction.source_action_id
                                != source["actual_native_actions"][2]["action"]):
                            raise S49PaperDevBlocked(
                                "SelfBody closed-loop actual Action result not source-bound"
                            )
                        report["selfbody_motion_feedback_dev"] = {
                            "status": "DEV_REAL_S49_SELF_BODY_MOTION_CLOSED_LOOP",
                            "before_sixth_samples": [
                                sample.as_report() for sample in pre.samples
                            ],
                            "sixth_proposal": correction.as_report(),
                            "sixth_closed_sample": after.samples[-1].as_report(),
                            "model_sample_count_after": len(after.samples),
                            "observed_target_error_m":
                                last["movement_m"] - correction.goal_distance_m,
                            "original_s49_l0_goal_was_0_45m": False,
                            "original_action_issuer_unchanged": True,
                            "same_native_receiver": True,
                            "world_tick_count_attested": False,
                            "fatigue_native_sensor": False,
                            "s10_updates": 0,
                            "qualification_go": False,
                            "science_go": False,
                        }
                    if motor_clock_dev:
                        review = review_native_motor_clock_dev(
                            output_dir / "native_motor_clock_dev.jsonl",
                            paper_log, source,
                            report["selfbody_motion_feedback_dev"],
                        )
                        report["motor_clock_observation_dev"] = review
                    report.update(
                        status="PASS",
                        classification="DEV_WORLD_SIXTH_ORIGINAL_S49_P1_MOTOR_TIMING_APPLIED",
                        original_s49_session_id=source["session_id"],
                        world_status="DISPOSABLE_PAPER_COMPLETED_AND_CLEANED",
                        original_s49_action_count=observed["count"],
                        p1=p1,
                        third_move_p1_self_body_dev=third_view,
                        fifth_l0_self_world_body_dev=fifth_view,
                        fifth_l0_p1_gait_compare_dev=gait,
                        original_sixth_l0_dev=six,
                        sixth_motor_sensitivity_dev=observed["sixth_motor_sensitivity"],
                        sixth_motor_action_dev={
                            **physical,
                            "observed_distance_m": last["movement_m"],
                            "command_duration_modified": True,
                            "observed_distance_causal_change_attested": False,
                            "hypothesis_held_across_unattested_world_ticks": True,
                            "original_s14_s16_authorization": True,
                            "qualification_go": False,
                            "science_go": False,
                        },
                    )
                    report["p1"]["world_run_verified"] = True
                    return 0
                report.update(
                    status="PASS",
                    classification="DEV_WORLD_ORIGINAL_S49_FIFTH_WAIT_THIRD_P1_MODEL",
                    world_status="DISPOSABLE_PAPER_COMPLETED_AND_CLEANED",
                    original_s49_session_id=source["session_id"],
                    original_s49_action_count=observed["count"],
                    p1=p1,
                    third_move_p1_self_body_dev=third_view,
                    fifth_l0_self_world_body_dev=fifth_view,
                    fifth_l0_p1_gait_compare_dev=observed["fifth_gait_compare"],
                    original_fourth_l0_dev=witness,
                    original_fifth_l0_dev={
                        **fifth, "status": "DEV_SAME_ORIGINAL_HOST_FIFTH_NATIVE_WAIT",
                        "third_actual_action_outcome": True,
                        "third_move_p1_model_only": True,
                        "original_l0_policy_uses_p1": False,
                        "p1_new_action_authority": False,
                        "source_bound_tick": None,
                        "wait_ticks_admitted": 0,
                        "qualification_go": False,
                        "science_go": False,
                    },
                )
                report["p1"]["world_run_verified"] = True
                return 0
            report.update(
                status="PASS",
                classification="DEV_WORLD_ORIGINAL_S49_NEXT_EPOCH_" + expected_choice,
                world_status="DISPOSABLE_PAPER_COMPLETED_AND_CLEANED",
                original_s49_session_id=source["session_id"],
                original_s49_action_count=observed["count"],
                p1=p1,
                next_cognition_native_dev=native_after_wait,
                next_self_world_dev=world_body,
                original_next_l0_dev={
                    "status": "DEV_SAME_ORIGINAL_HOST_ACTUAL_L0_DECIDE",
                    **witness,
                    "event_seq": witness["next_event_seq"],
                    "native_probe_seq": native.seq,
                    "native_probe_request_id": native.request_id,
                    "p1_model_origin": "hypothesis",
                    "p1_hypothesis_used_as_action_grant": False,
                    "paper_full_tick_attestation": False,
                    "source_bound_tick": None,
                    "wait_ticks_admitted": 0,
                    "r_qualification": False,
                    "science": False,
                },
            )
            report["p1"]["world_run_verified"] = True
            return 0
        # No arbitrary initial fatigue. The last original S49 MOVE's
        # verified geometric distance drives P1's MOVE debit. The gap to
        # Paper BEGIN remains unmodeled, not silently filled with WAIT.
        self_body_handoff, p1 = compose_s49_p1_dev_self_body(
            source, observed["window"], expected_player_uuid=offline_uuid(BOT_USERNAME),
            profile=FatigueProfile(enabled=True, initial=0.0),
        )
        # A *model hypothesis* for next Cognition, not a new native Present,
        # true fatigue reading, actuator grant or persisted resource state.
        next_cognition = self_body_handoff.next_cognition_readback()
        if observed["postwait"] is None:
            raise S49PaperDevBlocked("no original-session post-WAIT native probe")
        actual_next_body, actual_next_cognition = compose_s49_p1_postwait_native_dev(
            self_body_handoff, p1,
            source["actual_native_actions"][-1],
            observed["postwait"],
            expected_request_id=(
                f"s49-postwait:{source['session_id']}:{p1['action_id']}"
            ),
        )
        if (actual_next_body.observation is None
                or actual_next_cognition["extra_native_probes"] != 1):
            raise S49PaperDevBlocked("native next cognition Present missing")
        world_body_join = compose_postwait_native_self_world_dev(
            actual_next_body, observed["postwait"],
        )
        if (not world_body_join["world_body_same_object"]
                or world_body_join["native_seq"] != actual_next_cognition["native_seq"]
                or world_body_join["native_request_id"]
                != actual_next_cognition["native_request_id"]
                or world_body_join["p1_model_sensor_pct"]
                != actual_next_cognition["p1_dev_hypothesis_sensor_pct"]):
            raise S49PaperDevBlocked("postwait SelfWorld/SelfBody source mismatch")
        # Reuse the same frozen synthetic S19 owner used by the original
        # S49 runner. This replays a read-only S42 choice from the one
        # already obtained native probe; there is NO entities-event pair,
        # independent Action grant or actual ReactiveL0.decide().
        _, frozen_commit, _, _, _, _ = await asyncio.to_thread(original.s19._epoch_one)
        shadow_l0 = preview_postwait_l0_dev(
            actual_next_body, observed["postwait"],
            self_body_handoff, p1,
            FatigueProfile(enabled=True, initial=0.0),
            frozen_commit.new_state,
        )
        if (shadow_l0["fresh_action_grant_issued"] is not False
                or shadow_l0["actual_reactive_l0_decide_called"] is not False
                or shadow_l0["native_seq"] != actual_next_cognition["native_seq"]
                or shadow_l0["after_wait_p1_model_efficiency_pct"]
                != actual_next_cognition["p1_dev_hypothesis_capability_pct"]):
            raise S49PaperDevBlocked("next-epoch L0 shadow source mismatch")
        # A bounded optional Cognition comparison, not a second L0 route
        # or a physical MOVE command. Same native probe; after-MOVE value is
        # explicitly counterfactual to the actual post-WAIT World geometry.
        capability_choice = compare_body_capability_l0_dev(
            actual_next_body, observed["postwait"],
            self_body_handoff, p1,
            FatigueProfile(enabled=True, initial=0.0),
            frozen_commit.new_state,
        )
        if (capability_choice["native_seq"] != shadow_l0["native_seq"]
                or capability_choice["s42_selection_unchanged"]
                != shadow_l0["original_s42_selection"]
                or capability_choice["new_action_grant_issued"] is not False
                or capability_choice["actual_native_actions_added"] != 0):
            raise S49PaperDevBlocked("post-WAIT capability candidate source mismatch")
        # Same original native/Paper source under a second, explicitly
        # uncalibrated fatigue rate. This is DEV sensitivity, not another
        # World session, model authority, or action issuer.
        rate_sensitivity = compare_p1_knockdown_dev(
            source, observed["window"], observed["postwait"],
            expected_player_uuid=offline_uuid(BOT_USERNAME),
            retained=frozen_commit.new_state,
        )
        if (rate_sensitivity["native_seq"] != capability_choice["native_seq"]
                or rate_sensitivity["s42_original_selection"]
                != capability_choice["s42_selection_unchanged"]
                or rate_sensitivity["baseline_l0_capability_candidate"]
                != capability_choice["after_wait_on_actual_postwait_world_model"]
                or rate_sensitivity["stress_fatigue_after_wait"]
                <= rate_sensitivity["baseline_fatigue_after_wait"]
                or rate_sensitivity["new_action_issuers"] != 0
                or rate_sensitivity["real_action_count_added"] != 0):
            raise S49PaperDevBlocked("same-World fatigue knockdown not source bound")
        if observed["fresh_event"] is None or observed["fresh_probe"] is None:
            raise S49PaperDevBlocked("post-WAIT native L0 pair absent")
        _, original_owner, _, _, _, _ = await asyncio.to_thread(original.s19._epoch_one)
        fresh_pair = review_postwait_fresh_l0_input_dev(
            observed["fresh_event"], observed["fresh_probe"],
            prior_postwait_probe=observed["postwait"],
            body=actual_next_body,
            handoff=self_body_handoff,
            p1_reviewed=p1,
            profile=FatigueProfile(enabled=True, initial=0.0),
            retained=original_owner.new_state,
        )
        if (fresh_pair["fresh_event_seq"] <= actual_next_cognition["native_seq"]
                or fresh_pair["fresh_probe_seq"] <= fresh_pair["fresh_event_seq"]
                or fresh_pair["original_l0_decide_called"] is not False
                or fresh_pair["new_action_issued"] is not False
                or fresh_pair["bounded_dev_shadow_l0_action_requests"] != 0
                or fresh_pair["bounded_dev_shadow_l0_decide_called"]
                != (fresh_pair["fresh_s42_selection"] == "WAIT")
                or (fresh_target_distance == 10
                    and fresh_pair["fresh_s42_selection"] != "WAIT")
                or (fresh_target_distance == 2
                    and fresh_pair["fresh_s42_selection"] != "MOVE_AWAY")):
            raise S49PaperDevBlocked("post-WAIT fresh native L0 source invalid")
        # A logical one-use DEV shadow grant from this explicit operator
        # wrapper; NOT an S49 NormalActionAuthorization. No native physical
        # MOVE is dispatched and the original completed host remains closed.
        near_request = None
        if fresh_target_distance == 2:
            fresh_event = observed["fresh_event"]
            fresh_probe = observed["fresh_probe"]
            shadow_grant = L0ActionGrant(
                authority_id=(
                    f"dev-shadow-only:{source['session_id']}:{fresh_event.seq}"
                ),
                action_id=(
                    f"dev-shadow-no-dispatch:{source['session_id']}:{fresh_event.seq}"
                ),
                intent_id="escape-threat",
                session_id=source["session_id"],
                event_seq=fresh_event.seq,
                probe_seq=fresh_probe.seq,
                entity_id=fresh_pair["fresh_zombie_entity_id"],
                granted=True,
                provenance=Provenance(
                    "dev-independent-shadow-only-not-s49-issuer",
                    f"{source['session_id']}:event-{fresh_event.seq}:operator-scoped-dev",
                ),
            )
            near_request = decide_bounded_near_move_dev(
                fresh_event, fresh_probe,
                prior_postwait_probe=observed["postwait"],
                body=actual_next_body,
                handoff=self_body_handoff,
                p1_reviewed=p1,
                profile=FatigueProfile(enabled=True, initial=0.0),
                retained=original_owner.new_state,
                operator_shadow_grant=shadow_grant,
            )
            if (near_request["fresh_event_seq"] != fresh_pair["fresh_event_seq"]
                    or near_request["fresh_probe_seq"] != fresh_pair["fresh_probe_seq"]
                    or near_request["normal_action_executor_called"] is not False
                    or near_request["physical_action_issued"] is not False
                    or near_request["bounded_dev_l0_action_requests"] != 1):
                raise S49PaperDevBlocked("bounded near request source/authority mismatch")
        # Optional DEV-only cognition candidate: revalidate BOTH P1
        # model profiles against the SAME real fresh native event/probe.
        # No original L0.decide(), grant, or additional physical Action.
        gait_candidate = evaluate_fatigue_aware_fresh_candidate_dev(
            source, observed["window"], observed["postwait"],
            observed["fresh_event"], observed["fresh_probe"],
            expected_player_uuid=offline_uuid(BOT_USERNAME),
            retained=original_owner.new_state,
        )
        if (gait_candidate["fresh_event_seq"] != fresh_pair["fresh_event_seq"]
                or gait_candidate["fresh_probe_seq"] != fresh_pair["fresh_probe_seq"]
                or gait_candidate["fresh_s42_selection_unchanged"]
                != fresh_pair["fresh_s42_selection"]
                or gait_candidate["new_action_issued"] is not False
                or gait_candidate["new_action_grant_issued"] is not False):
            raise S49PaperDevBlocked("same-world gait candidate source mismatch")
        if (p1["dev_fatigue_recovered"] <= 0
                or p1["dev_fatigue_before"] <= 0
                or p1["dev_move"] is None
                or p1["dev_move"]["fatigue_accumulated"] <= 0):
            raise S49PaperDevBlocked("last MOVE distance did not produce P1 DEV debit/recovery")
        report.update(
            status="PASS",
            classification="DEV_WORLD_OBSERVED_MOVE_DISTANCE_TO_WAIT_P1_MODEL",
            original_s49_session_id=source["session_id"],
            world_status="DISPOSABLE_PAPER_COMPLETED_AND_CLEANED",
            p1=p1,
            self_body_dev=next_cognition,
            next_cognition_native_dev=actual_next_cognition,
            next_self_world_dev=world_body_join,
            next_l0_shadow_dev=shadow_l0,
            next_l0_capability_dev=capability_choice,
            next_l0_sensitivity_dev=rate_sensitivity,
            next_l0_fresh_pair_dev=fresh_pair,
            next_l0_gait_candidate_dev=gait_candidate,
            next_l0_near_decide_dev=near_request,
        )
        report["p1"]["world_run_verified"] = True
        report["p1"]["status"] = "DEV_WORLD_OBSERVED_MOVE_DISTANCE_WAIT_REPLAY"
        return 0
    except asyncio.CancelledError:
        report["status"] = "CANCELLED"
        raise
    except (Exception, OSError) as exc:
        report.update(status="BLOCKED_OR_FAILED",
                      reason=f"{type(exc).__name__}: {exc}")
        return 2
    finally:
        if dev_bridge is not None:
            remove_native_bridge_dev(dev_bridge)
        if created:
            # Reuse original S49's own process cleanup; never perform
            # second terminate/reap on a process owned by qualify().
            with (output_dir / "world_first_dev_report.json").open("x") as stream:
                json.dump(report, stream, sort_keys=True, indent=2)
                stream.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="S49 original / Paper / P1 disposable DEV")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--paper-jar", type=Path, required=True)
    parser.add_argument("--paper-sha256", required=True)
    parser.add_argument("--observer-jar", type=Path, required=True)
    parser.add_argument("--observer-sha256", required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument(
        "--fresh-target-distance", type=int, choices=(2, 10), default=2,
        help="Post-WAIT external DEV zombie stimulus in blocks; only 2 or 10",
    )
    parser.add_argument(
        "--actual-next-epoch", action="store_true",
        help="Explicit DEV-only fourth native decision on the ORIGINAL S49 host",
    )
    parser.add_argument(
        "--actual-fifth-epoch", action="store_true",
        help="Explicit DEV-only fifth native WAIT after original third MOVE",
    )
    parser.add_argument(
        "--compare-fifth-gait", action="store_true",
        help="DEV only same-native P1 gait candidate, no Action modification",
    )
    parser.add_argument(
        "--actual-sixth-motor", action="store_true",
        help="DEV only sixth original authorized MOVE with bounded model-conditioned duration",
    )
    parser.add_argument(
        "--motor-scenario", choices=(BASELINE, STRESS), default=BASELINE,
        help="DEV-only sixth motor model; stress is not physical calibration",
    )
    parser.add_argument(
        "--selfbody-motion-feedback", action="store_true",
        help="DEV only: three completed S49 MOVE outcomes update SelfBody and bound sixth duration",
    )
    parser.add_argument(
        "--motor-clock-dev", action="store_true",
        help="DEV only: read-only per-Action Node ON/OFF and client physicsTick in one generated bridge",
    )
    args = parser.parse_args(argv)
    return asyncio.run(run(
        args.output_dir, args.paper_jar, args.paper_sha256,
        args.observer_jar, args.observer_sha256,
        confirmation=args.confirm,
        fresh_target_distance=args.fresh_target_distance,
        actual_next_epoch=args.actual_next_epoch,
        actual_fifth_epoch=args.actual_fifth_epoch,
        compare_fifth_gait=args.compare_fifth_gait,
        actual_sixth_motor=args.actual_sixth_motor,
        motor_scenario=args.motor_scenario,
        selfbody_motion_feedback=args.selfbody_motion_feedback,
        motor_clock_dev=args.motor_clock_dev,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
