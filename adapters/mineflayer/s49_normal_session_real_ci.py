"""S49 physical feature gate: autonomous host L0 with two real Actions.

Disposable Mojang Java 1.21.8 and unmodified Mineflayer 4.39.0. The
experimenter changes only external World zombies; the persistent host loop,
not the staging coroutine, decides WAIT/MOVE and issues independently granted
Action through frozen S14/S15/S16. No language model or durable learned policy.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.b0_energy_bridge import (
    B0EnergyLedger,
    DashM0InvoiceDev,
)
from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.normal_action import (
    NormalActionAuthorization,
    NormalActionReceipt,
    NormalActionStage,
    NormalSessionActionExecutor,
    NormalWorldL0,
)
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerEntityHurt,
    MineflayerObservation,
)
from adapters.mineflayer.s31a_real_server_ci import (
    MINECRAFT_VERSION,
    MINEFLAYER_VERSION,
    S31ABlocked,
    _command,
    _correlated_observe,
    _fetch_official_server,
    _ready_server,
    _shutdown_server,
    _write_config,
)
from adapters.mineflayer.s34_native_world_cognition_ci import (
    _native_epoch_two,
    _native_threat,
    _new_session,
)
from adapters.mineflayer.s49_l0_observed_step_dev import (
    plan_next_l0_step_dev,
    plan_residual_after_second_s16_dev,
)
from adapters.mineflayer.self_action_evidence import capture_native_action_evidence
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.execution_binding import (
    ExecutionBinding,
    resolve_execution_binding,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant
from relay_self.world_conditioned_choice import WorldChoiceKind


class S49PhysicalFailure(RuntimeError):
    """The real native World did not support the claimed autonomous behavior."""


class NativeObservationOnly:
    """Adapter-local native frame filter; never manufactures observations.

    Mineflayer entity_hurt notifications may arrive unsolicited and do not
    themselves request the S44 entity-geometry policy. Every other unexpected
    protocol message remains fail-closed, with its exact type recorded.
    """

    def __init__(self, session: MineflayerProcessSession) -> None:
        self.session = session
        self.started = session.started
        self.ignored_hurt_frames = 0
        self.ignored_non_target_entities = 0
        self._admitted_zombie_entities: set[int] = set()
        self.ignored_duplicate_target_updates = 0

    async def receive(self):
        for _ in range(60):
            frame = await self.session.receive()
            if isinstance(frame, MineflayerObservation):
                if (
                    frame.kind == "entities"
                    and not any(e.name == "zombie" for e in frame.snapshot.nearby_entities)
                ):
                    # Other World entities do not trigger *zombie* control,
                    # but we do not infer that the World is otherwise safe.
                    self.ignored_non_target_entities += 1
                    continue
                if frame.kind == "entities":
                    zombies = [
                        e for e in frame.snapshot.nearby_entities if e.name == "zombie"
                    ]
                    if len(zombies) == 1:
                        if zombies[0].entity_id in self._admitted_zombie_entities:
                            # Same target event may recur when an unrelated
                            # native item changes. It is not a new stimulus.
                            self.ignored_duplicate_target_updates += 1
                            continue
                        self._admitted_zombie_entities.add(zombies[0].entity_id)
                return frame
            if isinstance(frame, MineflayerEntityHurt):
                self.ignored_hurt_frames += 1
                continue
            raise S49PhysicalFailure(
                f"unexpected native host frame {type(frame).__name__}: {frame!r}"
            )
        raise S49PhysicalFailure("non-observation native frame bound exhausted")


def source(tag: str) -> Provenance:
    return Provenance("s49-independent-operator", tag)


# Bounds apply to cooperative asyncio/process ports, not OS or storage failure.
_CLEANUP_STEP_TIMEOUT_S = 45.0
_CLEANUP_CANCEL_GRACE_S = 0.5


def _write_final_report(path: Path, report: dict[str, Any]) -> None:
    """Publish a complete snapshot by same-directory atomic replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    pending = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        pending.replace(path)
    finally:
        pending.unlink(missing_ok=True)


async def _cleanup_session(report, server, collector, session, staging, temp, stage_r,
                           raw_capture_root, cancellations):
    """Run each teardown step once; no failure can bypass a later resource.

    Only this task owns teardown. The caller supervises it through shield and
    retains cancellation, including repeated caller cancellation. wait() rather
    than wait_for() bounds even a coroutine which delays cancellation settlement.
    An unsettled task is explicitly unconfirmed; its exception is retrieved when
    it eventually ends. This cannot force arbitrary Python code to cooperate.
    """
    report["cleanup_steps"] = []

    def fault(field, exc):
        report[field] = f"{type(exc).__name__}: {exc}"
        if isinstance(exc, asyncio.CancelledError):
            cancellations.append(exc)

    def sync_step(field, call):
        try:
            return call()
        except (Exception, asyncio.CancelledError) as exc:
            fault(field, exc)
            return None

    async def step(field, awaitable, *, expected_cancel=False, timeout=10):
        task = asyncio.ensure_future(awaitable)
        done, _ = await asyncio.wait({task}, timeout=min(timeout, _CLEANUP_STEP_TIMEOUT_S))
        timed_out = not done
        if timed_out:
            fault(field, TimeoutError("cleanup deadline exceeded"))
            task.cancel()
            done, _ = await asyncio.wait({task}, timeout=_CLEANUP_CANCEL_GRACE_S)
        if not done:
            report[field + "_unconfirmed"] = True
            task.add_done_callback(lambda t: None if t.cancelled() else t.exception())
            return None
        try:
            value = task.result()
        except asyncio.CancelledError as exc:
            if not expected_cancel and not timed_out:
                fault(field, exc)
            return None
        except Exception as exc:
            fault(field + "_settlement_error" if timed_out else field, exc)
            return None
        report["cleanup_steps"].append(field.removesuffix("_error"))
        return value

    async def force_reap(process, prefix):
        if process is None:
            report[prefix + "_kill_error"] = "owned process unavailable; stop unconfirmed"
            return
        if process.returncode is None:
            sync_step(prefix + "_kill_error", process.kill)
            report[prefix + "_kill_attempted"] = True
        value = await step(prefix + "_reap_error", process.wait(), timeout=5)
        if type(value) is int and value == process.returncode:
            report[prefix + "_exit"] = value
        else:
            report[prefix + "_reap_unconfirmed"] = True

    async def confirm_exit(process, prefix):
        # A helper's claimed exit is not a receipt from the owned process.
        # Require the same process's wait, returncode and reported exit to agree.
        if process is None:
            report[prefix + "_reap_unconfirmed"] = True
            return
        value = await step(prefix + "_reap_error", process.wait(), timeout=5)
        if (type(value) is not int or type(process.returncode) is not int
                or value != process.returncode or value != report.get(prefix + "_exit")):
            report[prefix + "_reap_unconfirmed"] = True

    # host.run_session has returned/unwound before entering finally: no new
    # observation or Action work is scheduled here, and no receiver is added.
    if staging is not None:
        already_cancelled = staging.cancelled() or staging.cancelling() > 0
        staging.cancel()
        await step("stage_world_cleanup_error", staging,
                   expected_cancel=not already_cancelled, timeout=5)
    if stage_r is not None:
        value = sync_step("stage_r_cleanup_error", stage_r.summary)
        if value is not None:
            report["stage_r_owner"] = value
    if session is not None:
        value = await step("node_cleanup_error", session.shutdown(timeout_s=10), timeout=25)
        if type(value) is int:
            report["node_exit"] = value
            owned_node = getattr(session, "_process", None)
            if owned_node is None or owned_node.returncode != value:
                report["node_cleanup_error"] = "Node shutdown disagrees with owned process exit"
        if type(value) is not int and "node_cleanup_error" not in report:
            report["node_cleanup_error"] = "Node shutdown exit unconfirmed"
        if "node_cleanup_error" in report:
            value = await step("node_terminate_error", session.terminate())
            if type(value) is int:
                report["node_exit"] = value
            else:
                report.setdefault("node_terminate_error", "Node terminate exit unconfirmed")
                await force_reap(getattr(session, "_process", None), "node")
        await confirm_exit(getattr(session, "_process", None), "node")
        if raw_capture_root is not None:
            # terminate() can itself be cancelled before it seals the existing
            # W3 file. Seal that same capture as incomplete, without reading or
            # claiming an ACK/EOF. Normal shutdown's immutable seal is a no-op.
            if hasattr(session, "_seal_raw_capture"):
                sync_step("w3_seal_error", lambda: session._seal_raw_capture(
                    exit_code=report.get("node_exit"), reason="s49_cleanup_incomplete",
                ))
            value = sync_step("w3_receipt_error", lambda: session.raw_capture_receipt)
            report["w3_node_stdout_capture"] = value
    await step("server_cleanup_error", _shutdown_server(server, collector), timeout=45)
    if server is not None:
        if server.returncode is None:
            await force_reap(server, "server")
        if type(server.returncode) is int:
            report["server_exit"] = server.returncode
        await confirm_exit(server, "server")
    # The original helper may fail before reaching its collector branch or may
    # only request cancellation. Settle that same collector, never add a reader.
    if collector is not None:
        if not collector.done():
            collector.cancel()
        await step("collector_cleanup_error", collector, expected_cancel=True, timeout=5)
    if temp is not None:
        sync_step("temp_cleanup_error", temp.cleanup)



async def qualify(
    report_path: Path, server_log: Path, *,
    live_probe: Callable[[MineflayerObservation], Awaitable[None]] | None = None,
    stage_r_dev: bool = False,
    raw_capture_root: Path | None = None,
    dev_next_epoch: str | None = None,
    dev_fifth_epoch: str | None = None,
    dev_sixth_epoch: str | None = None,
    dev_forward_motor: bool = False,
    dev_sprint_motor: bool = False,
    dev_m0_dash_invoice: Callable[[NormalActionReceipt], DashM0InvoiceDev | None] | None = None,
    dev_m0_action_move_step: bool = False,
    dev_l0_next_step_m: float | None = None,
    dev_l0_residual_third_dev: bool = False,
    dev_l0_walk_third_dev: bool = False,
    dev_l0_goal_wait_dev: bool = False,
    dev_inter_action_owner_gap: bool = False,
    dev_inter_action_owner_paper_fence: (
        Callable[[str, str, str], Awaitable[None]] | None
    ) = None,
) -> int:
    report: dict[str, Any] = {
        "milestone": "S49", "stage": "START", "status": "BLOCKED",
        "classification": "PENDING_REAL_NATIVE_EVIDENCE",
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "actual_native_actions": [],
        "dev_forward_motor": dev_forward_motor,
        "dev_sprint_motor": dev_sprint_motor,
        "dev_m0_dash_owner": dev_m0_dash_invoice is not None,
        "dev_m0_action_move_step": dev_m0_action_move_step,
        "dev_l0_observed_next_step_m": dev_l0_next_step_m,
        "dev_l0_residual_third_dev": dev_l0_residual_third_dev,
        "dev_l0_walk_third_dev": dev_l0_walk_third_dev,
        "dev_l0_goal_wait_dev": dev_l0_goal_wait_dev,
        "dev_inter_action_owner_gap": dev_inter_action_owner_gap,
        "decisions": [],
        "real_model_calls": 0,
        "learning_in_world": False,
        "retained_origin": "S19_FROZEN_SYNTHETIC_GOVERNED_REV1",
        "automatic_goal_selection": False,
        "auto_crash_recovery": False,
    }
    server = collector = session = staging = temp = None
    stage_r = None
    dev_m0_owner = None
    rc = 2
    cancellations: list[asyncio.CancelledError] = []
    try:
        if os.environ.get("S49_REAL_SERVER_CI") != "1" or os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("explicit S49 real server env and no Node shim required")
        if (
            dev_inter_action_owner_paper_fence is not None
            and (not dev_inter_action_owner_gap
                 or not callable(dev_inter_action_owner_paper_fence)
                 or os.environ.get("S49_CAUSAL_OWNER_PAPER_FENCE_DEV_ONLY") != "1")
        ):
            raise S31ABlocked("original owner Paper fence requires exact DEV opt-in")
        if type(dev_inter_action_owner_gap) is not bool or (
            dev_inter_action_owner_gap and (
                not dev_sprint_motor
                or not dev_m0_action_move_step
                or os.environ.get("S49_INTER_ACTION_OWNER_GAP_DEV_ONLY") != "1"
            )
        ):
            raise S31ABlocked("original S49 no-issued-Action owner proof requires DEV opt-in")
        if type(dev_m0_action_move_step) is not bool or (
            dev_m0_action_move_step and (
                dev_m0_dash_invoice is None
                or os.environ.get("S49_M0_ACTION_STEP_DEV_ONLY") != "1"
            )
        ):
            raise S31ABlocked("action-level M0 MOVE requires separate original DEV owner gate")
        if dev_m0_dash_invoice is not None and (
            not callable(dev_m0_dash_invoice)
            or not dev_sprint_motor
            or os.environ.get("S49_M0_DASH_DEBIT_DEV_ONLY") != "1"
        ):
            raise S31ABlocked("M0 extra debit requires exact original S49 sprint DEV gate")
        if (
            type(dev_l0_walk_third_dev) is not bool
            or type(dev_l0_goal_wait_dev) is not bool
            or (dev_l0_walk_third_dev and (
                not dev_l0_residual_third_dev
                or os.environ.get("S49_L0_WALK_THIRD_DEV_ONLY") != "1"
            ))
            or (dev_l0_goal_wait_dev and (
                dev_l0_residual_third_dev
                or dev_l0_walk_third_dev
                or dev_l0_next_step_m is None
                or dev_next_epoch != "WAIT"
                or dev_m0_dash_invoice is not None
                or dev_m0_action_move_step
                or os.environ.get("S49_L0_GOAL_WAIT_DEV_ONLY") != "1"
            ))
        ):
            raise S31ABlocked("WALK/WAIT requires separate original L0 opt-in")
        if type(dev_l0_residual_third_dev) is not bool or (
            dev_l0_residual_third_dev and (
            dev_l0_next_step_m is None
            or dev_next_epoch != "MOVE_AWAY"
            or dev_m0_dash_invoice is not None
            or dev_m0_action_move_step
            or os.environ.get("S49_L0_RESIDUAL_THIRD_DEV_ONLY") != "1"
        )):
            raise S31ABlocked("third original Action needs isolated feedback owner gate")
        if dev_l0_next_step_m is not None and (
            type(dev_l0_next_step_m) not in (int, float)
            or not 0.30 <= dev_l0_next_step_m <= 2.50
            or not dev_sprint_motor or not dev_forward_motor
            or stage_r_dev
            or (dev_next_epoch is not None and not (
                dev_l0_residual_third_dev or dev_l0_goal_wait_dev
            ))
            or dev_fifth_epoch is not None or dev_sixth_epoch is not None
            or os.environ.get("S49_L0_OBSERVED_FEEDBACK_DEV_ONLY") != "1"
        ):
            raise S31ABlocked("native S16 feedback requires isolated original S49 DEV")
        if type(dev_sprint_motor) is not bool or (
            dev_sprint_motor and (
                not dev_forward_motor
                or os.environ.get("S49_SPRINT_MOTOR_DEV_ONLY") != "1"
            )
        ):
            raise S31ABlocked("sprint requires same original forward DEV gate")
        if type(dev_forward_motor) is not bool or (
            dev_forward_motor and (
                os.environ.get("S49_FORWARD_MOTOR_DEV_ONLY") != "1"
                or stage_r_dev
                or (dev_next_epoch is not None and not (
                dev_l0_residual_third_dev or dev_l0_goal_wait_dev
            ))
                or dev_fifth_epoch is not None or dev_sixth_epoch is not None
            )
        ):
            raise S31ABlocked("forward motor requires isolated explicit DEV gate")
        if stage_r_dev and os.environ.get("S49_STAGE_R_DEV_ONLY") != "1":
            raise S31ABlocked("Stage R requires separate explicit DEV-only operator gate")
        if dev_next_epoch is not None and (
            os.environ.get("S49_NEXT_EPOCH_DEV_ONLY") != "1"
            or stage_r_dev
            or dev_next_epoch not in ("WAIT", "MOVE_AWAY")
        ):
            raise S31ABlocked("extra original L0 epoch requires explicit isolated DEV gate")
        if dev_fifth_epoch is not None and (
            dev_fifth_epoch != "WAIT"
            or dev_next_epoch != "MOVE_AWAY"
            or os.environ.get("S49_FIFTH_EPOCH_DEV_ONLY") != "1"
        ):
            raise S31ABlocked("fifth original L0 WAIT requires a fourth authorized MOVE DEV")
        if dev_sixth_epoch is not None and (
            dev_sixth_epoch != "MOVE_AWAY"
            or dev_fifth_epoch != "WAIT"
            or os.environ.get("S49_SIXTH_EPOCH_DEV_ONLY") != "1"
        ):
            raise S31ABlocked("sixth original L0 MOVE requires fifth native WAIT DEV")
        report["stage"] = "PROVISION_DISPOSABLE_MOJANG_GAME"
        temp = tempfile.TemporaryDirectory(prefix="relay-self-s49-")
        root = Path(temp.name)
        report.update(await asyncio.to_thread(_fetch_official_server, root / "minecraft.jar"))
        _write_config(root)
        server, collector, _ = await _ready_server(
            root, root / "minecraft.jar", server_log,
        )
        report["stage"] = "AUTHENTIC_NATIVE_SELF_SESSION"
        session = await (
            _new_session() if raw_capture_root is None
            else _new_session(raw_capture_root=raw_capture_root)
        )
        sid = session.started.session_id
        report["session_id"] = sid
        if dev_m0_dash_invoice is not None:
            # The ORIGINAL S49 owner creates ONE existing B0 M0 owner;
            # wrapper/transport code can neither mint nor mutate energy.
            dev_m0_owner = B0EnergyLedger(sid, dev_dash_extra_debit=True)
            report["dev_m0_dash_energy_initial"] = dev_m0_owner.body.energy
        _, committed, _, _, _, _ = await asyncio.to_thread(s19._epoch_one)
        retained = committed.new_state
        if retained.target_id != "risk_weight" or retained.revision != 1 or retained.value != 4:
            raise S49PhysicalFailure("frozen governed retained source changed")
        intent = IntentCommitment()
        intent.commit(
            "escape-threat", objective="escape near zombie", at_ns=1,
            provenance=source("committed-existing-intent"),
        )
        # DEV opt-in enlarges the SAME original host; there is never a
        # second L0, receiver, issuer or Action executor.
        host = NormalWorldL0(
            sid, "escape-threat", retained,
            max_events=(6 if dev_sixth_epoch is not None
                        else 5 if dev_fifth_epoch is not None
                        else 4 if dev_next_epoch is not None else 3),
            max_action_requests=(
                (4 if dev_sixth_epoch == "MOVE_AWAY"
                 else 3 if dev_next_epoch == "MOVE_AWAY" else 2)
            ),
        )
        executor = NormalSessionActionExecutor(
            sid, intent, dev_forward_motor=dev_forward_motor,
            dev_sprint_motor=dev_sprint_motor,
            dev_walk_third=dev_l0_walk_third_dev,
        )
        if stage_r_dev:
            # Explicit S49-owned extension; never install a read-only
            # observer as a new Action issuer or as an S10 authority.
            from adapters.mineflayer.self_world_stage_r_owner import (
                StageRDevOperatorLearningIssuer,
                StageRDevSingleWriter,
            )

            # The original S49 operator issues a separate single-use S10
            # DEV grant; S17 feedback and the commit owner cannot mint it.
            learning_issuer = StageRDevOperatorLearningIssuer(host, executor, intent)
            stage_r = StageRDevSingleWriter(host, executor, intent, learning_issuer)
            report["stage_r_dev_enabled"] = True
        probes = {}
        # No new Action issuer: only a gated readback of THIS original host
        # and its original NormalSessionActionExecutor before/after issue.
        owner_gap_end_first: dict[str, Any] | None = None
        first_feedback_receipt: NormalActionReceipt | None = None
        second_feedback_receipt: NormalActionReceipt | None = None

        async def reprobe(frame):
            request_id = f"s49-actual:{sid}:event-{frame.seq}"
            reading = await _correlated_observe(session, request_id)
            probes[reading.seq] = reading
            if stage_r is not None:
                # Single writer commits only after prior terminal and this
                # NEW original-session native probe, before next L0._check.
                stage_r.observe_original_probe(reading)
            if live_probe is not None:
                # Product-only observer sees an already received native probe.
                # Original S49 L0 selection, Action ownership and receipt
                # collection run exactly as before and never await L2 inference.
                await live_probe(reading)
            report.setdefault("source_pair_trace", []).append({
                "event_seq": frame.seq,
                "event_kind": frame.kind,
                "event_entities": [
                    {"name": e.name, "id": e.entity_id, "d": e.distance}
                    for e in frame.snapshot.nearby_entities
                ],
                "probe_seq": reading.seq,
                "probe_entities": [
                    {"name": e.name, "id": e.entity_id, "d": e.distance}
                    for e in reading.snapshot.nearby_entities
                ],
            })
            return reading

        def decide_grant(choice, event_seq):
            if choice.selection is not WorldChoiceKind.MOVE_AWAY:
                raise S49PhysicalFailure("WAIT attempted to request Action")
            return L0ActionGrant(
                authority_id=f"s49-preconfigured-escape-{event_seq}",
                action_id=f"s49-native-move-{event_seq}",
                intent_id="escape-threat", session_id=sid,
                event_seq=event_seq, probe_seq=choice.probe_seq,
                entity_id=choice.entity_id, granted=True,
                provenance=source(f"l0-request-{event_seq}"),
            )

        def authorize(step, stage):
            return NormalActionAuthorization(
                stage=stage, authority_id=f"s49-{stage.value.lower()}-{step.event_seq}",
                intent_id="escape-threat", session_id=sid,
                action_id=step.action_request_id, event_seq=step.event_seq,
                probe_seq=step.choice.probe_seq, entity_id=step.choice.entity_id,
                granted=True,
                provenance=source(f"independent-{stage.value.lower()}-{step.event_seq}"),
            )

        async def on_action(step):
            nonlocal owner_gap_end_first, first_feedback_receipt, second_feedback_receipt
            if dev_inter_action_owner_gap and owner_gap_end_first is not None:
                if len(report["actual_native_actions"]) != 1:
                    raise S49PhysicalFailure("original owner gap ambiguous Action count")
                prior_id = report["actual_native_actions"][0]["action"]
                if (
                    executor._count != 1
                    or executor._dispatched != {prior_id}
                    or executor.supervisor.open_actions
                    or step.action_request_id == prior_id
                ):
                    raise S49PhysicalFailure("original owner issued Action during claimed gap")
                started = time.monotonic_ns()
                if started <= owner_gap_end_first["host_first_outcome_monotonic_ns"]:
                    raise S49PhysicalFailure("nonmonotonic native original owner gap")
                report["dev_inter_action_original_owner_gap"] = {
                    **owner_gap_end_first,
                    "second_requested_action_id": step.action_request_id,
                    "host_next_action_request_monotonic_ns": started,
                    "elapsed_owner_local_monotonic_ns": (
                        started - owner_gap_end_first["host_first_outcome_monotonic_ns"]
                    ),
                    "same_original_S49_executor": True,
                    "native_action_count_at_next_request": 1,
                    "native_dispatched_action_ids": [prior_id],
                    "native_open_actions_at_next_request": 0,
                    "all_actions_globally_absent_attested": False,
                    "paper_world_tick_bound_attested": False,
                    "node_control_epoch_aligned_attested": False,
                    "WAIT_admitted": False,
                    "P1_recovery_posted": False,
                    "M0_posted": False,
                }
                owner_gap_end_first = None
                if dev_inter_action_owner_paper_fence is not None:
                    # The original second Action has not been issued. The
                    # Paper console must record END BEFORE this coroutine
                    # resumes to grant and issue through original S14/S15.
                    await dev_inter_action_owner_paper_fence(
                        "END", prior_id, step.action_request_id,
                    )
                    if (
                        executor._count != 1
                        or executor._dispatched != {prior_id}
                        or executor.supervisor.open_actions
                    ):
                        raise S49PhysicalFailure(
                            "original issuer changed while waiting for Paper END"
                        )
                    report["dev_inter_action_original_owner_gap"][
                        "causal_paper_end_received_before_original_second_issue"
                    ] = True
            probe = probes[step.choice.probe_seq]
            native = _native_threat(
                probe, probe.request_id, expected_entity_id=step.choice.entity_id,
            )
            if native.distance_m >= 4:
                raise S49PhysicalFailure("actual Action without a close zombie")
            owner = (
                stage_r.require_joint_admission_owner(step)
                if stage_r is not None else retained
            )
            values, epoch = _native_epoch_two(
                ActionSupervisor(), intent, owner, owner,
                expected_revision=owner.revision, native=native,
            )
            if (
                epoch.cognition_requested
                or values["plan"].selected is None
                or values["plan"].selected.candidate_id != "MOVE_AWAY"
                or values["admission"].status.value != "admitted"
            ):
                raise S49PhysicalFailure("full S14 native admission was not independently satisfied")
            binding = ExecutionBinding(
                binding_id=f"s49-binding-{step.event_seq}",
                candidate_ref="MOVE_AWAY", required_intent_id="escape-threat",
                skill_execution_id=f"s49-skill-{step.event_seq}",
                skill_ref="escape-movement", action_id=step.action_request_id,
                action_ref=(
                    "MOVE_FORWARD" if dev_l0_walk_third_dev and executor._count == 2
                    else "MOVE_FORWARD_SPRINT_DEV" if dev_sprint_motor
                    else "MOVE_FORWARD" if dev_forward_motor else "MOVE_BACKWARD"
                ),
                provenance=source(f"binding-{step.event_seq}"),
            )
            bound = resolve_execution_binding(
                values["admission"], values["control"], values["route"],
                intent, values["policies"][-2], binding,
                provenance=source(f"admitted-{step.event_seq}"),
            )
            feedback_duration: float | None = None
            if dev_l0_next_step_m is not None and first_feedback_receipt is not None:
                if second_feedback_receipt is None:
                    plan = plan_next_l0_step_dev(
                        first_feedback_receipt.consequence,
                        next_step_m=dev_l0_next_step_m,
                        current_threat_distance_m=native.distance_m,
                    )
                    if (
                        len(report["actual_native_actions"]) != 1
                        or plan.session_id != sid
                        or plan.first_action_id != first_feedback_receipt.terminal.action_id
                        or executor._count != 1
                        or executor.supervisor.open_actions
                    ):
                        raise S49PhysicalFailure("stale or duplicate S16 feedback source")
                    feedback_duration = plan.requested_duration_s
                    report["dev_l0_observed_feedback"] = {
                        **asdict(plan), "second_action_id": step.action_request_id,
                        "same_original_S49_issuer": True,
                        "new_native_reader": False,
                    }
                elif dev_l0_residual_third_dev:
                    second = report.get("dev_l0_observed_feedback")
                    if (
                        not isinstance(second, dict)
                        or second.get("second_action_id")
                           != second_feedback_receipt.terminal.action_id
                        or second.get("second_actual_outcome") != "outcome"
                        or executor._count != 2
                        or len(report["actual_native_actions"]) != 2
                        or executor.supervisor.open_actions
                    ):
                        raise S49PhysicalFailure("third original feedback authority stale")
                    third_plan = plan_residual_after_second_s16_dev(
                        second_feedback_receipt.consequence,
                        second_input_s=second["second_input_duration_s"],
                        total_target_m=dev_l0_next_step_m,
                        current_threat_distance_m=native.distance_m,
                    )
                    # An independent L0 Action request already exists:
                    # STOP must NOT be silently converted into a new issue.
                    if third_plan.proposed_duration_s is None:
                        raise S49PhysicalFailure(
                            "third L0 requested action despite STOP/danger feedback"
                        )
                    feedback_duration = third_plan.proposed_duration_s
                    report["dev_l0_residual_third"] = {
                        **asdict(third_plan),
                        "third_action_id": step.action_request_id,
                        "third_gait": "WALK" if dev_l0_walk_third_dev else "SPRINT",
                        "original_sole_action_issuer": True,
                        "new_packet_reader": False,
                    }
                else:
                    raise S49PhysicalFailure("unexpected third original feedback request")
            if stage_r is None:
                receipt = await executor.execute(
                    session, step, bound, probe,
                    authorize(step, NormalActionStage.PROPOSE),
                    authorize(step, NormalActionStage.ISSUE),
                    **({"dev_next_duration_s": feedback_duration}
                       if feedback_duration is not None else {}),
                )
            else:
                from adapters.mineflayer.normal_action import (
                    observe_closed_native_actions,
                )

                # Original sole Action issuer, after full S14 admission.
                # Terminal callback is NOT permission. A separate S49 DEV
                # owner examines it, and commits only on later native probe.
                with observe_closed_native_actions(stage_r.observe_original_closed):
                    receipt = await executor.execute(
                        session, step, bound, probe,
                        authorize(step, NormalActionStage.PROPOSE),
                        authorize(step, NormalActionStage.ISSUE),
                    )
            if (
                receipt.terminal.state is not ActionState.OUTCOME
                or receipt.consequence.status is not WorldConsequenceStatus.EXECUTED
                or receipt.consequence.movement_distance is None
                or receipt.consequence.movement_distance < 0.05
            ):
                raise S49PhysicalFailure("World movement or existing S16 OUTCOME absent")
            if dev_l0_next_step_m is not None:
                if first_feedback_receipt is None:
                    if report["actual_native_actions"] or executor._count != 1:
                        raise S49PhysicalFailure("feedback first original outcome ambiguous")
                    first_feedback_receipt = receipt
                elif second_feedback_receipt is None:
                    if (
                        executor._count != 2
                        or not isinstance(report.get("dev_l0_observed_feedback"), dict)
                        or receipt.terminal.action_id
                           != report["dev_l0_observed_feedback"]["second_action_id"]
                    ):
                        raise S49PhysicalFailure("feedback second original S16 not observed")
                    second_feedback_receipt = receipt
                    report["dev_l0_observed_feedback"].update({
                        "second_actual_s16_m": receipt.consequence.movement_distance,
                        "absolute_second_step_error_m": abs(
                            receipt.consequence.movement_distance - dev_l0_next_step_m
                        ),
                        "second_actual_outcome": receipt.terminal.state.value,
                        "second_input_duration_s": (
                            feedback_duration if feedback_duration is not None else 0.60
                        ),
                        "goal_reached_attested": False,
                        "world_tick_phase_matched": False,
                    })
                    if dev_l0_goal_wait_dev:
                        stop_plan = plan_residual_after_second_s16_dev(
                            receipt.consequence,
                            second_input_s=(
                                feedback_duration if feedback_duration is not None
                                else 0.60
                            ),
                            total_target_m=dev_l0_next_step_m,
                            current_threat_distance_m=2.0,
                            tolerance_m=0.20,
                        )
                        if stop_plan.decision != "STOP_AVOID_OVERSHOOT":
                            raise S49PhysicalFailure(
                                "native second S16 outside WAIT deadband"
                            )
                        host.bind_s16_stop_dev(
                            session_id=sid,
                            second_action_id=receipt.terminal.action_id,
                            residual_m=stop_plan.residual_m,
                            tolerance_m=0.20,
                        )
                        report["dev_l0_goal_wait"] = {
                            **asdict(stop_plan),
                            "original_l0_armed": True,
                            "native_event_wait_not_yet_observed": True,
                            "same_original_l0": True,
                        }
                elif dev_l0_residual_third_dev:
                    third = report.get("dev_l0_residual_third")
                    if (
                        executor._count != 3
                        or not isinstance(third, dict)
                        or third.get("third_action_id") != receipt.terminal.action_id
                    ):
                        raise S49PhysicalFailure("third original S16 owner mismatch")
                    actual = (second_feedback_receipt.consequence.movement_distance
                              + receipt.consequence.movement_distance)
                    report["dev_l0_residual_third"].update({
                        "third_actual_s16_m": receipt.consequence.movement_distance,
                        "second_plus_third_s16_m": actual,
                        "second_plus_third_error_m": abs(actual-dev_l0_next_step_m),
                        "original_second_only_error_m": abs(
                            second_feedback_receipt.consequence.movement_distance
                            - dev_l0_next_step_m
                        ),
                        "third_terminal_state": receipt.terminal.state.value,
                        "same_original_S49_executor": True,
                        "cross_world_goal_reached_attested": False,
                    })
            if stage_r is not None:
                stage_r.seal_original_action(step, receipt)
            if dev_m0_owner is not None:
                invoice = dev_m0_dash_invoice(receipt)
                proof = capture_native_action_evidence(
                    receipt.consequence, allow_dev_forward=True,
                    allow_dev_sprint=True,
                )
                if dev_m0_action_move_step:
                    transaction = dev_m0_owner.post_s49_move_step_dev(
                        receipt, invoice, native_evidence=proof,
                    )
                    report.setdefault("dev_m0_action_move_postings", []).append(
                        asdict(transaction),
                    )
                    report["dev_m0_dash_energy_remaining"] = dev_m0_owner.body.energy
                    if invoice is None:
                        report.setdefault("dev_m0_dash_unboosted_actions", []).append(
                            receipt.terminal.action_id,
                        )
                elif invoice is not None:
                    posted = dev_m0_owner.post_dash_extra_dev(
                        receipt, invoice, native_evidence=proof,
                    )
                    report.setdefault("dev_m0_dash_postings", []).append(asdict(posted))
                    report["dev_m0_dash_energy_remaining"] = dev_m0_owner.body.energy
                else:
                    report.setdefault("dev_m0_dash_unboosted_actions", []).append(
                        receipt.terminal.action_id,
                    )
            if dev_inter_action_owner_gap and not report["actual_native_actions"]:
                if (
                    executor._count != 1
                    or executor._dispatched != {receipt.terminal.action_id}
                    or executor.supervisor.open_actions
                ):
                    raise S49PhysicalFailure("first original OUTCOME not a closed Action")
                owner_gap_end_first = {
                    "classification": "S49_ORIGINAL_EXECUTOR_NO_ISSUE_GAP_DEV_ONLY",
                    "session_id": sid,
                    "first_terminal_action_id": receipt.terminal.action_id,
                    "host_first_outcome_monotonic_ns": time.monotonic_ns(),
                    "first_terminal_outcome": True,
                    "native_action_count_at_first_terminal": 1,
                    "native_open_actions_at_first_terminal": 0,
                }
            report["actual_native_actions"].append({
                "action": receipt.terminal.action_id,
                "terminal": receipt.terminal.state.value,
                "source": receipt.consequence.session_id,
                "movement_m": receipt.consequence.movement_distance,
                "event_seq": step.event_seq,
                "probe_seq": step.choice.probe_seq,
                # Decoded original before/after observations and exact effect
                # receipts, captured BEFORE the immutable consequence is lost.
                # Legacy reports have no such field and remain EVIDENCE_PARTIAL.
                "execution_evidence": capture_native_action_evidence(
                    receipt.consequence, allow_dev_forward=dev_forward_motor,
                    allow_dev_sprint=dev_sprint_motor,
                ),
            })
            if (
                dev_inter_action_owner_paper_fence is not None
                and len(report["actual_native_actions"]) == 1
            ):
                # Original first S16 terminal + M0 state are complete.
                # Await Paper START delivery: causal start after native
                # clear and original Action release, no new Action owner.
                await dev_inter_action_owner_paper_fence(
                    "START", receipt.terminal.action_id, "NONE",
                )
                if (
                    executor._count != 1
                    or executor._dispatched != {receipt.terminal.action_id}
                    or executor.supervisor.open_actions
                ):
                    raise S49PhysicalFailure(
                        "original issuer changed while awaiting Paper START"
                    )
                # The original gap report is constructed only when the
                # second Action request arrives. Preserve first fence proof
                # in the pending owner-local record until that moment.
                if owner_gap_end_first is None:
                    raise S49PhysicalFailure("original first owner gap missing after START")
                owner_gap_end_first[
                    "causal_paper_start_received_after_first_outcome"
                ] = True

        async def stage_world():
            assert server is not None and server.stdin is not None
            _command(server, "gamerule doMobSpawning false")
            await server.stdin.drain()
            await asyncio.sleep(2)
            # This original host needs four genuine native entity epochs:
            # WAIT and three independently authorized MOVE requests. Only
            # this isolated DEV input supplies the additional fourth stimulus.
            world_epochs = [(10, 5), (2, 8), (2, 8)]
            if dev_l0_residual_third_dev or dev_l0_goal_wait_dev:
                world_epochs.append((2, 8))
            for distance_m, hold in world_epochs:
                _command(server, "kill @e[type=minecraft:zombie]")
                await server.stdin.drain()
                await asyncio.sleep(2)
                _command(
                    server,
                    f"execute at RelaySelf run summon minecraft:zombie ~{distance_m} ~ ~ "
                    "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}",
                )
                await server.stdin.drain()
                await asyncio.sleep(hold)

        report["stage"] = "UNATTENDED_NATIVE_EVENT_LOOP"
        staging = asyncio.create_task(stage_world())
        observation_source = NativeObservationOnly(session)
        trace = await asyncio.wait_for(
            host.run_session(
                observation_source, probe=reprobe, grant=decide_grant,
                on_action_request=on_action, max_frames=320,
            ),
            timeout=95,
        )
        if dev_inter_action_owner_gap:
            owner = report.get("dev_inter_action_original_owner_gap")
            ids = [a["action"] for a in report["actual_native_actions"]]
            if (
                dev_inter_action_owner_paper_fence is not None
                and (owner is None
                     or owner.get("causal_paper_start_received_after_first_outcome")
                        is not True
                     or owner.get("causal_paper_end_received_before_original_second_issue")
                        is not True)
            ):
                raise S49PhysicalFailure("original owner causal Paper fences incomplete")
            if (
                owner is None or owner_gap_end_first is not None
                or len(ids) != 2
                or owner["first_terminal_action_id"] != ids[0]
                or owner["second_requested_action_id"] != ids[1]
                or executor._count != 2
                or executor._dispatched != set(ids)
                or executor.supervisor.open_actions
            ):
                raise S49PhysicalFailure("DEV original S49 owner gap unclosed")
            owner["native_action_count_after_second_terminal"] = 2
            owner["native_open_actions_after_second_terminal"] = 0
        report["ignored_hurt_frames"] = observation_source.ignored_hurt_frames
        report["ignored_non_target_entities"] = observation_source.ignored_non_target_entities
        report["ignored_duplicate_target_updates"] = observation_source.ignored_duplicate_target_updates
        if dev_m0_owner is not None:
            expected_transactions = (
                report.get("dev_m0_action_move_postings", [])
                if dev_m0_action_move_step
                else report.get("dev_m0_dash_postings", [])
            )
            expected_ticks = 2 if dev_m0_action_move_step else 1
            if (len(expected_transactions) != expected_ticks
                    or len(report.get("dev_m0_dash_unboosted_actions", [])) != 1
                    or dev_m0_owner.body.tick != expected_ticks
                    or dev_m0_owner.body.meals != 0
                    or dev_m0_owner.body.terminal):
                raise S49PhysicalFailure("DEV M0 original owner posting count/terminal mismatch")
            report["dev_m0_dash_m0_tick"] = dev_m0_owner.body.tick
        report["decisions"] = [{
            "event_seq": s.event_seq,
            "entity_id": s.choice.entity_id,
            "probe_seq": s.choice.probe_seq,
            "distance_m": s.choice.distance_m,
            "selected": s.choice.selection.value,
            "issued": s.asks_for_action,
        } for s in trace]
        expected_choices = ["WAIT", "MOVE_AWAY", "MOVE_AWAY"]
        if dev_next_epoch is not None:
            expected_choices.append(dev_next_epoch)
        if dev_fifth_epoch is not None:
            expected_choices.append(dev_fifth_epoch)
        if dev_sixth_epoch is not None:
            expected_choices.append(dev_sixth_epoch)
        expected_actions = (2 + (dev_next_epoch == "MOVE_AWAY")
                            + (dev_sixth_epoch == "MOVE_AWAY"))
        if (
            len(trace) != len(expected_choices)
            or [s.choice.selection.value for s in trace] != expected_choices
            or len({s.choice.entity_id for s in trace}) != len(expected_choices)
            or len(report["actual_native_actions"]) != expected_actions
            or executor.supervisor.open_actions
            or executor.supervisor.get(trace[1].action_request_id).state is not ActionState.OUTCOME
            or executor.supervisor.get(trace[2].action_request_id).state is not ActionState.OUTCOME
            or trace[0].asks_for_action
            or host.action_requests != expected_actions
            or host.events != len(expected_choices)
            or (
                dev_next_epoch == "MOVE_AWAY"
                and (
                    not trace[3].asks_for_action
                    or executor.supervisor.get(trace[3].action_request_id).state
                    is not ActionState.OUTCOME
                )
            )
            or (dev_next_epoch == "WAIT" and trace[3].asks_for_action)
            or (dev_fifth_epoch == "WAIT" and trace[4].asks_for_action)
            or (
                dev_sixth_epoch == "MOVE_AWAY"
                and (
                    not trace[5].asks_for_action
                    or executor.supervisor.get(trace[5].action_request_id).state
                    is not ActionState.OUTCOME
                )
            )
        ):
            raise S49PhysicalFailure("original S49 bounded epoch/Action terminal mismatch")
        if dev_l0_goal_wait_dev:
            if (
                len(trace) != 4
                or trace[3].choice.selection is not WorldChoiceKind.WAIT
                or trace[3].asks_for_action
                or trace[3].choice.criterion_id
                   != "s49-closed-s16-relative-step-stop-dev"
                or executor._count != 2
                or host._s16_stop_source is None
            ):
                raise S49PhysicalFailure("original L0 failed to select real WAIT")
            report["dev_l0_goal_wait"].update({
                "native_event_wait_not_yet_observed": False,
                "fourth_native_event_seq": trace[3].event_seq,
                "fourth_native_probe_seq": trace[3].choice.probe_seq,
                "actual_l0_choice": trace[3].choice.selection.value,
                "fourth_action_issued": False,
                "original_action_count": len(report["actual_native_actions"]),
            })
        if dev_next_epoch is not None:
            report["dev_original_next_epoch"] = {
                "actual_original_host_decide": True,
                "same_host_events": host.events,
                "same_host_action_requests": host.action_requests,
                "next_event_seq": trace[3].event_seq,
                "next_probe_seq": trace[3].choice.probe_seq,
                "next_choice": trace[3].choice.selection.value,
                "next_action_issued": trace[3].asks_for_action,
                "new_l0_owner": False,
                "new_native_reader": False,
                "p1_as_action_authority": False,
            }
        if dev_fifth_epoch is not None:
            report["dev_original_fifth_epoch"] = {
                "actual_original_host_decide": True,
                "same_host_events": host.events,
                "same_host_action_requests": host.action_requests,
                "next_event_seq": trace[4].event_seq,
                "next_probe_seq": trace[4].choice.probe_seq,
                "next_choice": trace[4].choice.selection.value,
                "next_action_issued": trace[4].asks_for_action,
                "same_original_host": True,
                "additional_native_reader": False,
                "p1_as_action_authority": False,
            }
        if dev_sixth_epoch is not None:
            report["dev_original_sixth_epoch"] = {
                "actual_original_host_decide": True,
                "same_host_events": host.events,
                "same_host_action_requests": host.action_requests,
                "event_seq": trace[5].event_seq,
                "probe_seq": trace[5].choice.probe_seq,
                "selected": trace[5].choice.selection.value,
                "action_issued": trace[5].asks_for_action,
                "new_action_issuer": False,
                "new_native_receiver": False,
                "p1_as_action_authority": False,
            }
        if stage_r is not None:
            report["stage_r_decision_revisions"] = [
                {"event_seq": step.event_seq,
                 "retained_revision": step.choice.retained_revision,
                 "retained_value": step.choice.retained_value,
                 "selected": step.choice.selection.value}
                for step in trace
            ]
            if [step.choice.retained_revision for step in trace] != [1, 1, 2]:
                raise S49PhysicalFailure("Stage R owner did not bind next L0 epoch")
            if (
                stage_r.committed is None
                or stage_r.current is not host.retained
                or stage_r.current.revision != 2
                or stage_r.current.value != 4
            ):
                raise S49PhysicalFailure("no authentic Stage R single-writer commit")
            report["stage_r_owner"] = stage_r.summary()
            report["learning_in_world"] = True  # HOLD revision, NOT gain
        report["status"] = "PASS"
        report["classification"] = (
            "DEV_ONLY_S49_CLOSED_S16_GOAL_WAIT_NO_THIRD_ACTION"
            if dev_l0_goal_wait_dev else
            "DEV_ONLY_S49_S16_RESIDUAL_THIRD_WALK_ORIGINAL_OWNER"
            if dev_l0_walk_third_dev else
            "DEV_ONLY_S49_S16_RESIDUAL_THIRD_ORIGINAL_OWNER"
            if dev_l0_residual_third_dev else
            "DEV_ONLY_S49_FORWARD_SPRINT_MOTOR_UNCALIBRATED"
            if dev_sprint_motor else
            "DEV_ONLY_S49_FORWARD_MOTOR_NOT_DIRECTIONALLY_QUALIFIED"
            if dev_forward_motor else
            "DEV_ONLY_S49_SIXTH_MOTOR_DEV_AFTER_FIFTH_WAIT"
            if dev_sixth_epoch is not None
            else "DEV_ONLY_S49_ORIGINAL_FIFTH_WAIT_AFTER_THIRD_MOVE"
            if dev_fifth_epoch is not None
            else "DEV_ONLY_S49_ORIGINAL_NEXT_EPOCH_" + dev_next_epoch
            if dev_next_epoch is not None
            else (
                "DEV_ONLY_S49_SINGLE_WRITER_HOLD_REV2"
                if stage_r is not None
                else "REAL_ONE_SESSION_L0_WAIT_TWO_AUTHORIZED_MOVES_QUALIFIED"
            )
        )
        report["stage"] = "CLOSED"
        rc = 0
    except asyncio.CancelledError as exc:
        cancellations.append(exc)
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        if getattr(exc, "startup_cleanup_unconfirmed", None) is not None:
            report["startup_cleanup_unconfirmed"] = exc.startup_cleanup_unconfirmed
        rc = 1
    except (S31ABlocked, OSError) as exc:
        report["status"] = "BLOCKED"
        report["error"] = f"{type(exc).__name__}: {exc}"
        if getattr(exc, "startup_cleanup_unconfirmed", None) is not None:
            report["startup_cleanup_unconfirmed"] = exc.startup_cleanup_unconfirmed
        print("S49 BLOCKED: " + str(exc), file=sys.stderr)
        rc = 2
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        if getattr(exc, "startup_cleanup_unconfirmed", None) is not None:
            report["startup_cleanup_unconfirmed"] = exc.startup_cleanup_unconfirmed
        print("S49 FAIL: " + str(exc), file=sys.stderr)
        rc = 1
    finally:
        cleanup = asyncio.create_task(_cleanup_session(
            report, server, collector, session, staging, temp, stage_r,
            raw_capture_root, cancellations,
        ))
        # Shield alone would leave an unsupervised task on caller cancellation.
        # Keep awaiting this exact task; never clear the caller's cancellation
        # state with uncancel(), never start another teardown or another Action.
        while not cleanup.done():
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError as exc:
                cancellations.append(exc)
            except Exception:
                break  # Retrieve and report the supervisor fault below.
        try:
            cleanup.result()
        except (Exception, asyncio.CancelledError) as exc:
            report["cleanup_supervisor_error"] = f"{type(exc).__name__}: {exc}"
            if isinstance(exc, asyncio.CancelledError):
                cancellations.append(exc)
        if cancellations:
            report["cancellation_count"] = len(cancellations)
            report["first_cancellation"] = str(cancellations[0])
            report["status"] = "FAIL"
            report["classification"] = "S49_SESSION_NOT_QUALIFIED"
            rc = 1
        # Action closure was provisional: qualify the WHOLE session only
        # after all cleanup results have been recorded. Never leave an
        # otherwise-stale QUALIFIED classification on a failed run.
        if report["status"] == "PASS":
            cleanup_faults = [
                field for field in report
                if field.endswith(("_error", "_unconfirmed"))
            ]
            if session is None or (
                type(report.get("node_exit")) is not int
                or report["node_exit"] != 0
            ):
                cleanup_faults.append("node_exit")
            if server is None or (
                type(report.get("server_exit")) is not int
                or report["server_exit"] != 0
            ):
                cleanup_faults.append("server_exit")
            if raw_capture_root is not None:
                w3 = report.get("w3_node_stdout_capture")
                if (
                    type(w3) is not dict
                    or w3.get("status") != "COMPLETE_NODE_STDOUT"
                    or w3.get("session_id") != report.get("session_id")
                    or w3.get("eof_observed") is not True
                    or type(w3.get("shutdown_ack_count")) is not int
                    or w3["shutdown_ack_count"] != 1
                    or type(w3.get("process_exit_code")) is not int
                    or w3["process_exit_code"] != 0
                    or w3.get("capture_fault") is not None
                ):
                    cleanup_faults.append("w3_node_stdout_capture")
            if cleanup_faults:
                report["status"] = "FAIL"
                report["classification"] = "S49_SESSION_NOT_QUALIFIED"
                report["error"] = (
                    "S49 cleanup not qualified: " + ", ".join(cleanup_faults)
                )
                rc = 1
        elif report.get("classification") in (
            "REAL_ONE_SESSION_L0_WAIT_TWO_AUTHORIZED_MOVES_QUALIFIED",
            "DEV_ONLY_S49_SINGLE_WRITER_HOLD_REV2",
            "DEV_ONLY_S49_ORIGINAL_NEXT_EPOCH_WAIT",
            "DEV_ONLY_S49_ORIGINAL_NEXT_EPOCH_MOVE_AWAY",
            "DEV_ONLY_S49_ORIGINAL_FIFTH_WAIT_AFTER_THIRD_MOVE",
            "DEV_ONLY_S49_SIXTH_MOTOR_DEV_AFTER_FIFTH_WAIT",
            "DEV_ONLY_S49_FORWARD_MOTOR_NOT_DIRECTIONALLY_QUALIFIED",
            "DEV_ONLY_S49_FORWARD_SPRINT_MOTOR_UNCALIBRATED",
            "DEV_ONLY_S49_S16_RESIDUAL_THIRD_ORIGINAL_OWNER",
            "DEV_ONLY_S49_S16_RESIDUAL_THIRD_WALK_ORIGINAL_OWNER",
            "DEV_ONLY_S49_CLOSED_S16_GOAL_WAIT_NO_THIRD_ACTION",
        ):
            # No pre-existing FAILURE/BLOCKED is allowed to retain the
            # provisional qualified label, nor be upgraded to PASS.
            report["classification"] = "S49_SESSION_NOT_QUALIFIED"
        # No await between the final verdict and atomic publication, so a
        # caller cancellation cannot race a provisional PASS snapshot.
        try:
            _write_final_report(report_path, report)
        except (Exception, asyncio.CancelledError) as exc:
            report["status"] = "FAIL"
            report["classification"] = "S49_SESSION_NOT_QUALIFIED"
            report["report_write_error"] = f"{type(exc).__name__}: {exc}"
            print("S49_REPORT_WRITE_FAILED=" + json.dumps(report, sort_keys=True), file=sys.stderr)
            if cancellations:
                raise cancellations[0] from exc
            raise
        print("S49_REPORT=" + json.dumps(report, sort_keys=True))
        if cancellations:
            raise cancellations[0]
    return rc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--dev-forward-motor", action="store_true",
                        help="isolated DEV MOVE_FORWARD motor, not DASH or escape qualification")
    parser.add_argument("--dev-sprint-motor", action="store_true",
                        help="original issued Action with forward+sprint DEV effect")
    args = parser.parse_args()
    return asyncio.run(qualify(
        args.report, args.server_log, dev_forward_motor=args.dev_forward_motor,
        dev_sprint_motor=args.dev_sprint_motor,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
