"""S49 physical feature gate: autonomous host L0 with two real Actions.

Disposable Mojang Java 1.21.8 and unmodified Mineflayer 4.39.0. The
experimenter changes only external World zombies; the persistent host loop,
not the staging coroutine, decides WAIT/MOVE and issues independently granted
Action through frozen S14/S15/S16. No language model or durable learned policy.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.l23_paper_live_assets import (
    L23PaperAssets,
    paper_marker,
    stage_paper_assets,
    verify_paper_assets,
    wait_paper_line,
)
from adapters.mineflayer.l23_paper_s7_settling import _paper_rows
from adapters.mineflayer.normal_action import (
    NormalActionAuthorization,
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
from relay_self.relay_engine import RelayEngine
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
    mp11_three_actions_dev: bool = False,
    mp11_g3_paper_assets: L23PaperAssets | None = None,
    l_mp11_live_prefix_dev: bool = False,
    l_mp11_live_l2_engine: RelayEngine | None = None,
    l_mp11_paper_eof_dev: bool = False,
) -> int:
    report: dict[str, Any] = {
        "milestone": "S49", "stage": "START", "status": "BLOCKED",
        "classification": "PENDING_REAL_NATIVE_EVIDENCE",
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "actual_native_actions": [],
        "decisions": [],
        "real_model_calls": 0,
        "learning_in_world": False,
        "retained_origin": "S19_FROZEN_SYNTHETIC_GOVERNED_REV1",
        "automatic_goal_selection": False,
        "auto_crash_recovery": False,
    }
    server = collector = session = staging = temp = None
    stage_r = None
    rc = 2
    cancellations: list[asyncio.CancelledError] = []
    try:
        if os.environ.get("S49_REAL_SERVER_CI") != "1" or os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("explicit S49 real server env and no Node shim required")
        if type(mp11_three_actions_dev) is not bool or (
            mp11_three_actions_dev and (
                os.environ.get("MP11_S49_THREE_ACTION_DEV") != "1"
                or stage_r_dev
                or raw_capture_root is None
            )
        ):
            raise S31ABlocked(
                "MP11 three original Actions require explicit DEV env, source capture "
                "and no Stage-R ownership mutation"
            )
        if mp11_three_actions_dev:
            report["mp11_g2"] = {
                "classification": "DEV_ONLY_ONE_WORLD_THREE_ORIGINAL_S49_ACTIONS",
                "action_budget": 3,
                "paper_s50_windows": 0,
                "l2_provider_calls": 0,
                "l2_selected_trials": 0,
                "l10_s10_s11_admissions": 0,
                "typed_s16_actions": [],
                "real_l2_autonomous_experiment": False,
            }
        if l_mp11_paper_eof_dev and (
            type(l_mp11_paper_eof_dev) is not bool
            or not l_mp11_live_prefix_dev
            or mp11_g3_paper_assets is None
            or os.environ.get("L_MP11_PAPER_EOF_DEV") != "1"
        ):
            raise S31ABlocked("future Paper EOF envelope must be explicitly predeclared")
        if l_mp11_paper_eof_dev:
            report["mp11_paper_eof_predeclared"] = True
        if l_mp11_live_l2_engine is not None and (
            not l_mp11_live_prefix_dev
            or os.environ.get("L_MP11_LIVE_L2_DEV") != "1"
        ):
            raise S31ABlocked(
                "live L2 OPEN must be separately opted in with prior source"
            )
        if l_mp11_live_prefix_dev and (
            mp11_g3_paper_assets is None
            or not mp11_three_actions_dev
            or os.environ.get("L_MP11_LIVE_PREFIX_DEV") != "1"
        ):
            raise S31ABlocked(
                "L MP11 live prefix requires explicit gated original G3 World"
            )
        if mp11_g3_paper_assets is not None:
            if (not mp11_three_actions_dev
                    or os.environ.get("MP11_G3_PAPER_THREE_WINDOWS_DEV") != "1"):
                raise S31ABlocked("MP11 G3 requires owner-bound G2 and extra Paper grant")
            from adapters.mineflayer.self_body_s50_l1_paper_local import (
                check_local_paper_config,
            )
            review = verify_paper_assets(mp11_g3_paper_assets)
            check_local_paper_config(
                mp11_g3_paper_assets.plugin_config, mp11_g3_paper_assets.config_sha256)
            config = mp11_g3_paper_assets.plugin_config.read_text(encoding="utf-8")
            flags = (
                "s50-mp11-multitrial-dev: true",
                "s50-ice-floor-dev: true",
                "s50-changed-body-condition-dev: false",
            )
            if any(config.count(flag) != 1 for flag in flags):
                raise S31ABlocked("MP11 G3 requires exact Paper multi-window isolated flags")
            report["mp11_g3"] = {
                "classification": "DEV_PAPER_THREE_WINDOWS_PREPARED",
                "paper_assets": review,
                "paper_markers": [],
                "prior_slope": 0.65,
                "model_source": "FIXED_OPERATOR_UNLEARNED_SHADOW_ONLY",
                "paper_windows_attested": 0,
                "l2_calls": 0,
                "learning_updates": 0,
            }
        if stage_r_dev and os.environ.get("S49_STAGE_R_DEV_ONLY") != "1":
            raise S31ABlocked("Stage R requires separate explicit DEV-only operator gate")
        report["stage"] = "PROVISION_DISPOSABLE_MOJANG_GAME"
        temp = tempfile.TemporaryDirectory(prefix="relay-self-s49-")
        root = Path(temp.name)
        if mp11_g3_paper_assets is None:
            report.update(await asyncio.to_thread(_fetch_official_server, root / "minecraft.jar"))
        else:
            report["mp11_g3"]["staged"] = await asyncio.to_thread(
                stage_paper_assets, mp11_g3_paper_assets, root,
            )
        _write_config(root)
        if l_mp11_paper_eof_dev:
            raw_paper_path = server_log.with_name(server_log.name + ".raw")
            report["mp11_paper_raw_stdout_path"] = str(raw_paper_path)
            server, collector, _ = await _ready_server(
                root, root / "minecraft.jar", server_log,
                raw_stdout_path=raw_paper_path,
            )
        else:
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
        live_l_prior = None
        live_l2 = None
        l2_stage_release = {}
        if l_mp11_live_l2_engine is not None:
            from adapters.mineflayer.l_mp11_live_l2_shadow import (
                BoundedLiveL2,
            )
            live_l2 = BoundedLiveL2(
                l_mp11_live_l2_engine, require_real_llama=True,
                timeout_s=45.0,
            )
            l2_stage_release = {1: asyncio.Event(), 2: asyncio.Event()}
            report["l_mp11_live_l2"] = live_l2.public_report()
        if l_mp11_live_prefix_dev:
            # Read-only L-owned diagnostic; never a model/action executor.
            # First physical Paper World/subject identity is fixed by original
            # pre-Action surface witness; defer typed ledger creation to it.
            report["l_mp11_live_prefix"] = {
                "status": "PREPARED_NOT_ATTESTED",
                "observations": [],
                "l2_open_calls": 0,
                "learning_admissions": 0,
                "action_issuers_added": 0,
            }
        _, committed, _, _, _, _ = await asyncio.to_thread(s19._epoch_one)
        retained = committed.new_state
        if retained.target_id != "risk_weight" or retained.revision != 1 or retained.value != 4:
            raise S49PhysicalFailure("frozen governed retained source changed")
        intent = IntentCommitment()
        intent.commit(
            "escape-threat", objective="escape near zombie", at_ns=1,
            provenance=source("committed-existing-intent"),
        )
        host = NormalWorldL0(
            sid, "escape-threat", retained,
            max_events=4 if mp11_three_actions_dev else 3,
            max_action_requests=3 if mp11_three_actions_dev else 2,
        )
        executor = NormalSessionActionExecutor(sid, intent)
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
        g3_previous_marker = None

        async def g3_paper_line(marker: str, *, kind: str, timeout_s: float = 5) -> None:
            if kind != "S50_MP11_NEXT_ACCEPT":
                raise S49PhysicalFailure("MP11 G3 unknown previous-window marker")
            loop = asyncio.get_running_loop()
            deadline = loop.time() + timeout_s
            while loop.time() < deadline:
                if server_log.is_file():
                    for line in server_log.read_text(errors="replace").splitlines():
                        if (f"S50_MP11_NEXT_ACCEPT prior_marker={marker} " in line
                                and "status=PRIOR_PAPER_WAIT_EIGHT_SEALED_NO_ACTION_AUTHORITY" in line):
                            return
                await asyncio.sleep(0.05)
            raise S49PhysicalFailure("no real Paper completed prior-window transition")

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
            nonlocal g3_previous_marker, live_l_prior
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
                action_ref="MOVE_BACKWARD",
                provenance=source(f"binding-{step.event_seq}"),
            )
            bound = resolve_execution_binding(
                values["admission"], values["control"], values["route"],
                intent, values["policies"][-2], binding,
                provenance=source(f"admitted-{step.event_seq}"),
            )
            if mp11_g3_paper_assets is not None:
                if server is None or server.stdin is None:
                    raise S49PhysicalFailure("G3 pre-Action Paper process unavailable")
                marker = paper_marker(step.action_request_id, sid)
                if g3_previous_marker is not None:
                    _command(server, f"relaydevmp11next {g3_previous_marker} {marker}")
                    await server.stdin.drain()
                    await g3_paper_line(g3_previous_marker, kind="S50_MP11_NEXT_ACCEPT")
                _command(server, f"relaydevphase {marker} PRE_FORWARD")
                await server.stdin.drain()
                await wait_paper_line(
                    server_log, marker=marker,
                    kind="M02_DEV_S50_PHASE", phase="PRE_FORWARD",
                )
                # Operator-frozen deliberately simple/cheap 0.65 model for
                # prequential source chronology, NOT a learned L1 improvement.
                ticket_sha = hashlib.sha256(
                    f"MP11-G3-UNLEARNED-FIXED-COEFF:{sid}:{marker}".encode()
                ).hexdigest()
                _command(server, f"relaydevlocalmodel {marker} 0.65 {ticket_sha}")
                await server.stdin.drain()
                await wait_paper_line(server_log, marker=marker, kind="S50_DEV_LOCAL_MODEL_ARM")
                _command(server, f"relaydevicefloor {marker} GRASS_BLOCK_5X5_READONLY")
                await server.stdin.drain()
                await wait_paper_line(server_log, marker=marker, kind="S50_DEV_SURFACE_LOCK")
            if stage_r is None and mp11_three_actions_dev:
                from adapters.mineflayer.self_body_s50_original_closure import (
                    SelfBodyS50ClosedOwnerLease,
                    observe_original_s49_selfbody_closure,
                )
                # One fresh existing S16 readonly lease PER original Action.
                # The same S49 executor and ActionSupervisor remain sole owner.
                typed = SelfBodyS50ClosedOwnerLease(
                    self_id="self", expected_action_id=step.action_request_id,
                )
                with observe_original_s49_selfbody_closure(typed):
                    receipt = await executor.execute(
                        session, step, bound, probe,
                        authorize(step, NormalActionStage.PROPOSE),
                        authorize(step, NormalActionStage.ISSUE),
                        correlate_native_probes_dev=True,
                    )
                status = typed.status()
                body = typed._body
                if (status["original_closures_seen"] != 1
                        or not status["typed_original_ready"]
                        or body is None or body.observation is None
                        or body.outcome is None
                        or body.session_id != sid
                        or body.observation.action_id != receipt.terminal.action_id):
                    raise S49PhysicalFailure(
                        "MP11 per-Action original typed S16 receipt was not observed"
                    )
                previous = report["mp11_g2"]["typed_s16_actions"]
                if (previous and (
                    body.observation.native_seq <= previous[-1]["native_seq"]
                    or previous[-1]["action_id"] == receipt.terminal.action_id
                )):
                    raise S49PhysicalFailure(
                        "MP11 replayed or non-increasing original native S16"
                    )
                previous.append({
                    "action_id": receipt.terminal.action_id,
                    "session_id": body.session_id,
                    "native_seq": body.observation.native_seq,
                    "native_ref": body.observation.source_ref,
                    "outcome": body.outcome.disposition.value,
                    "source_status": body.outcome.source_status,
                    "before_after_source_original": True,
                    "new_action_issuers": 0,
                })
                typed.close()
            elif stage_r is None:
                receipt = await executor.execute(
                    session, step, bound, probe,
                    authorize(step, NormalActionStage.PROPOSE),
                    authorize(step, NormalActionStage.ISSUE),
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
            if stage_r is not None:
                stage_r.seal_original_action(step, receipt)
            if mp11_g3_paper_assets is not None:
                assert server is not None and server.stdin is not None
                _command(server, f"relaydevphase {marker} POST_CLEAR")
                await server.stdin.drain()
                await wait_paper_line(
                    server_log, marker=marker,
                    kind="M02_DEV_S50_PHASE", phase="POST_CLEAR",
                )
                _command(server, f"relaydevwait {marker}")
                await server.stdin.drain()
                await wait_paper_line(server_log, marker=marker, kind="S50_DEV_WAIT_BEGIN")
                from adapters.mineflayer.self_body_s50_world_dev import (
                    wait_live_paper_window,
                )
                await wait_live_paper_window(server_log, marker=marker)
                if l_mp11_live_prefix_dev:
                    from adapters.mineflayer.l23_paper_s7_settling import (
                        _paper_rows,
                    )
                    from adapters.mineflayer.l_mp11_live_previous_action import (
                        LivePriorLedger,
                    )
                    if (server.returncode is not None
                            or session.process_returncode is not None):
                        raise S49PhysicalFailure(
                            "L live source not sampled from active Paper/native session"
                        )
                    original = server_log.read_bytes()
                    prefix = original[:original.rfind(b"\n") + 1]
                    locks = [
                        row for row in _paper_rows(
                            prefix, "S50_DEV_SURFACE_LOCK "
                        ) if row.get("marker_id") == marker
                    ]
                    if len(locks) != 1:
                        raise S49PhysicalFailure(
                            "L live source missing one original Paper surface witness"
                        )
                    lock = locks[0]
                    if live_l_prior is None:
                        live_l_prior = LivePriorLedger(
                            session_id=sid, world_uuid=lock["world"],
                            subject_uuid=lock["subject_uuid"],
                        )
                    typed_actions = report["mp11_g2"]["typed_s16_actions"]
                    latest = typed_actions[-1]
                    if latest["action_id"] != step.action_request_id:
                        raise S49PhysicalFailure("L live prefix wrong typed S16 owner")
                    witness = live_l_prior.accept_completed(
                        prefix, action_id=step.action_request_id,
                        marker_id=marker, native_s16_seq=latest["native_seq"],
                        native_outcome="S16_OUTCOME",
                    )
                    read_request = live_l_prior.model_request()
                    report["l_mp11_live_prefix"]["observations"].append({
                        "action_id": witness.action_id,
                        "native_s16_seq": witness.native_s16_seq,
                        "paper_first_tick": witness.paper_wait_ticks[0],
                        "paper_last_tick": witness.paper_wait_ticks[-1],
                        "paper_prefix_sha256": witness.paper_prefix_sha256,
                        "paper_prefix_length": witness.paper_prefix_length,
                        "l2_request_id": read_request.request_id,
                        "visible_previous_trials": len(live_l_prior.history),
                        "l2_calls": 0,
                        "source_status": witness.source_status,
                    })
                    report["l_mp11_live_prefix"]["status"] = (
                        "PROVISIONAL_LIVE_PREFIX_READ_ONLY"
                    )
                    if live_l2 is not None and len(live_l_prior.history) <= 2:
                        # Must finish after previous original S16+WAIT8 and
                        # BEFORE the owner stages the next known hazard.
                        # Model output is a shadow hypothesis, NOT a new test
                        # or input into the existing L0 Action selection.
                        try:
                            hypothesis = await live_l2.propose_after(
                                live_l_prior, freeze_root=report_path.parent,
                            )
                        finally:
                            report["l_mp11_live_l2"] = live_l2.public_report()
                        if not hypothesis.provider_source == "llama.cpp":
                            raise S49PhysicalFailure("not a real local L2 provider")
                        count = len(live_l2.proposals)
                        report["real_model_calls"] = count
                        report["mp11_g2"]["l2_provider_calls"] = count
                        report["mp11_g3"]["l2_calls"] = count
                        report["l_mp11_live_prefix"]["l2_open_calls"] = count
                        report["l_mp11_live_prefix"]["observations"][-1][
                            "l2_calls"
                        ] = 1
                        l2_stage_release[count].set()
                report["mp11_g3"]["paper_markers"].append(marker)
                g3_previous_marker = marker
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
                    receipt.consequence
                ),
            })

        async def stage_world():
            assert server is not None and server.stdin is not None
            if mp11_g3_paper_assets is not None:
                # Experimenter places real original player above a FLAT floor,
                # NOT an L2 instruction or an independent Self action.
                _command(server, "tp RelaySelf 0.5 -58 0.5 0 0")
                await server.stdin.drain()
                await asyncio.sleep(2)
            _command(server, "gamerule doMobSpawning false")
            await server.stdin.drain()
            await asyncio.sleep(2)
            stimulus = (
                ((10, 5), (2, 8), (2, 8), (2, 8))
                if mp11_three_actions_dev else ((10, 5), (2, 8), (2, 8))
            )
            for stage_i, (distance_m, hold) in enumerate(stimulus):
                if live_l2 is not None and stage_i in (2, 3):
                    # No experimenter stimulus is emitted while L2 is still
                    # reading the previous original closed Action. Abort on
                    # timeout; there is NO fallback to a fabricated proposal.
                    await asyncio.wait_for(
                        l2_stage_release[stage_i - 1].wait(), timeout=50,
                    )
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
            timeout=205 if live_l2 is not None else 95,
        )
        report["ignored_hurt_frames"] = observation_source.ignored_hurt_frames
        report["ignored_non_target_entities"] = observation_source.ignored_non_target_entities
        report["ignored_duplicate_target_updates"] = observation_source.ignored_duplicate_target_updates
        report["decisions"] = [{
            "event_seq": s.event_seq,
            "entity_id": s.choice.entity_id,
            "probe_seq": s.choice.probe_seq,
            "distance_m": s.choice.distance_m,
            "selected": s.choice.selection.value,
            "issued": s.asks_for_action,
        } for s in trace]
        expected_actions = 3 if mp11_three_actions_dev else 2
        expected_events = expected_actions + 1
        if (
            len(trace) != expected_events
            or [s.choice.selection.value for s in trace]
            != ["WAIT"] + ["MOVE_AWAY"] * expected_actions
            or len({s.choice.entity_id for s in trace}) != expected_events
            or len(report["actual_native_actions"]) != expected_actions
            or executor.supervisor.open_actions
            or any(
                executor.supervisor.get(step.action_request_id).state
                is not ActionState.OUTCOME
                for step in trace if step.asks_for_action
            )
            or trace[0].asks_for_action
            or host.action_requests != expected_actions
            or host.events != expected_events
        ):
            raise S49PhysicalFailure("bounded original L0 and S16 Action closure count mismatch")
        if mp11_g3_paper_assets is not None and (
            len(report["mp11_g3"]["paper_markers"]) != 3
            or len(set(report["mp11_g3"]["paper_markers"])) != 3
        ):
            raise S49PhysicalFailure("MP11 G3 failed to observe three live Paper windows")
        if mp11_three_actions_dev:
            typed = report["mp11_g2"]["typed_s16_actions"]
            if (len(typed) != expected_actions
                    or [x["action_id"] for x in typed]
                    != [x["action"] for x in report["actual_native_actions"]]
                    or len({x["native_ref"] for x in typed}) != expected_actions):
                raise S49PhysicalFailure("MP11 authentic original S16 3x source audit failed")
            report["mp11_g2"]["status"] = "THREE_TYPED_S16_ACTIONS_PROVISIONAL_BEFORE_CLEANUP"
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
            "DEV_ONLY_MP11_G2_ONE_WORLD_THREE_TYPED_S16_ACTIONS"
            if mp11_three_actions_dev else (
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
        if (mp11_g3_paper_assets is not None
                and report.get("status") == "PASS"):
            try:
                from adapters.mineflayer.self_body_s50_l2_mp11_paper_audit import (
                    audit_multi_trial_paper,
                )
                markers = tuple(report["mp11_g3"]["paper_markers"])
                raw = server_log.read_bytes()
                audit_bytes = raw
                if l_mp11_paper_eof_dev:
                    from dataclasses import asdict

                    from adapters.mineflayer.l_mp11_paper_eof_envelope import (
                        seal_after_shutdown,
                        verified_complete_lines,
                    )

                    raw = Path(report["mp11_paper_raw_stdout_path"]).read_bytes()
                    if raw != server_log.read_bytes():
                        raise S49PhysicalFailure("raw Paper bytes differ from live log view")
                    eof = asdict(seal_after_shutdown(
                        raw, predeclared=report.get("mp11_paper_eof_predeclared") is True,
                    ))
                    report["mp11_paper_eof"] = eof
                    audit_bytes = verified_complete_lines(
                        raw, eof, predeclared=True,
                    )
                locks = [
                    row for row in _paper_rows(raw, "S50_DEV_SURFACE_LOCK ")
                    if row.get("marker_id") in markers
                ]
                if (len(locks) != 3
                        or [r.get("marker_id") for r in locks] != list(markers)):
                    raise S49PhysicalFailure("no three unique real original Paper locks")
                uuid = locks[0]["world"]
                subject = locks[0]["subject_uuid"]
                review = audit_multi_trial_paper(
                    audit_bytes, action_markers=markers, world_uuid=uuid,
                    subject_uuid=subject,
                    surfaces=("GRASS_BLOCK",) * 3,
                )
                if (len(review) != 3
                        or len({x.paper_sha256 for x in review}) != 1):
                    raise S49PhysicalFailure("MP11 G3 actual Paper three-window chronology failure")
                report["mp11_g3"]["paper_windows_attested"] = len(review)
                report["mp11_g3"]["paper_world_uuid"] = uuid
                report["mp11_g3"]["subject_uuid"] = subject
                report["mp11_g3"]["original_sha256"] = hashlib.sha256(raw).hexdigest()
                report["mp11_g3"]["wait_ticks"] = [list(x.wait_ticks) for x in review]
                report["mp11_g3"]["motion_m"] = [list(x.wait_motion_m) for x in review]
                report["mp11_g3"]["source_status"] = (
                    "THREE_ORIGINAL_PAPER_CALLBACK_WINDOWS_AFTER_SERVER_SHUTDOWN"
                )
                report["classification"] = (
                    "DEV_ONLY_MP11_G3_THREE_S49_S16_PAPER_S50_WINDOWS_SAME_WORLD"
                )
            except Exception as exc:
                report["mp11_g3"]["paper_audit_error"] = f"{type(exc).__name__}: {exc}"
                report["status"] = "FAIL"
                report["classification"] = "MP11_G3_ORIGINAL_PAPER_NOT_QUALIFIED"
                rc = 1
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
            "DEV_ONLY_MP11_G2_ONE_WORLD_THREE_TYPED_S16_ACTIONS",
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
    parser.add_argument("--mp11-three-actions-dev", action="store_true")
    parser.add_argument("--l-mp11-live-prefix-dev", action="store_true")
    parser.add_argument("--l-mp11-paper-eof-dev", action="store_true")
    parser.add_argument("--l-mp11-live-l2-endpoint")
    parser.add_argument("--l-mp11-live-l2-model")
    parser.add_argument("--raw-capture-root", type=Path)
    parser.add_argument("--mp11-g3-paper-jar", type=Path)
    parser.add_argument("--mp11-g3-plugin-jar", type=Path)
    parser.add_argument("--mp11-g3-config", type=Path)
    args = parser.parse_args()
    scope = (args.mp11_g3_paper_jar, args.mp11_g3_plugin_jar, args.mp11_g3_config)
    if any(x is not None for x in scope) and not all(x is not None for x in scope):
        parser.error("MP11 G3 requires exact Paper jar, plugin jar and config")
    assets = None
    if all(x is not None for x in scope):
        def sha(path):
            assert path is not None
            return hashlib.sha256(path.read_bytes()).hexdigest()
        assets = L23PaperAssets(
            server_jar=args.mp11_g3_paper_jar,
            server_sha256=sha(args.mp11_g3_paper_jar),
            plugin_jar=args.mp11_g3_plugin_jar,
            plugin_sha256=sha(args.mp11_g3_plugin_jar),
            plugin_config=args.mp11_g3_config,
            config_sha256=sha(args.mp11_g3_config),
        )
    l2_engine = None
    if (args.l_mp11_live_l2_endpoint is None) != (
        args.l_mp11_live_l2_model is None
    ):
        parser.error("live L2 requires both the exact endpoint and model alias")
    if args.l_mp11_live_l2_endpoint is not None:
        from urllib.parse import urlsplit

        from adapters.mineflayer.l_mp11_live_l2_shadow import JournaledLiveLlamaProvider
        from relay_self.relay_engine import RelayEngine

        if not args.l_mp11_live_prefix_dev:
            parser.error("live L2 requires original per-Action Paper prefix mode")
        url = urlsplit(args.l_mp11_live_l2_endpoint)
        try:
            local_port = url.port
        except ValueError:
            parser.error("malformed live L2 port")
        if (
            url.scheme != "http"
            or url.hostname not in {"127.0.0.1", "localhost", "::1"}
            or local_port is None
            or url.path != "/v1/chat/completions"
            or url.username is not None
            or url.password is not None
            or url.query or url.fragment
            or not args.l_mp11_live_l2_model.strip()
        ):
            parser.error("only exact loopback llama.cpp endpoint and model allowed")
        l2_provider = JournaledLiveLlamaProvider(
            journal_root=args.report.parent,
            endpoint=args.l_mp11_live_l2_endpoint,
            model=args.l_mp11_live_l2_model,
            timeout=40.0,
        )
        l2_engine = RelayEngine(l2_provider)
    return asyncio.run(qualify(
        args.report, args.server_log,
        raw_capture_root=args.raw_capture_root,
        mp11_three_actions_dev=args.mp11_three_actions_dev,
        mp11_g3_paper_assets=assets,
        l_mp11_live_prefix_dev=args.l_mp11_live_prefix_dev,
        l_mp11_paper_eof_dev=args.l_mp11_paper_eof_dev,
        l_mp11_live_l2_engine=l2_engine,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
