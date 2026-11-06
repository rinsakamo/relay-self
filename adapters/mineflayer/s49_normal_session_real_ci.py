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
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.normal_action import (
    NormalActionAuthorization,
    NormalActionStage,
    NormalSessionActionExecutor,
    NormalWorldL0,
    assess_normal_eating_observation,
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
from adapters.mineflayer.s49_completed_decision_bridge import (
    S49OriginalCompletedBatch,
    bounded_original_s49_completion_row,
    read_original_s49_completions,
)
from adapters.mineflayer.self_action_evidence import capture_native_action_evidence
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.eat_hunger import EatCursor
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


class Bug0FoodLoopDevCompleted(Exception):
    """Bounded S49 native food loop closed, with original cleanup remaining."""



def read_only_bug0_eat_window(
    cursor: EatCursor, probe: MineflayerObservation,
) -> dict[str, object]:
    """Only project an existing native probe, never issue or grant EAT.

    The status describes a bounded source view, not global safety. It cannot
    replace an independent operator's PROPOSE / ISSUE authorization.
    """
    risk = assess_normal_eating_observation(probe)
    choice = cursor.choose(probe)
    return {
        "session_id": probe.session_id,
        "probe_seq": probe.seq,
        "probe_request_id": probe.request_id,
        "source_ref": probe.provenance.reference,
        "food_before": choice.food_before,
        "food_status": choice.status.value,
        "candidate_item": choice.item_name,
        "candidate_slot": choice.item_slot,
        "risk_status": risk.value,
        "nearby_observed": len(probe.snapshot.nearby_entities),
        "source_coverage_truncated": probe.snapshot.nearby_entities_coverage.truncated,
        "action_issued": False,
        "grant_requested": False,
        "learning_written": False,
    }


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
    completed_l0: Callable[[S49OriginalCompletedBatch], None] | None = None,
    completed_l0_dev: bool = False,
    stage_r_dev: bool = False,
    raw_capture_root: Path | None = None,
    bug0_eat_shadow: bool = False,
    bug0_food_loop_dev: bool = False,
    bug0_food_refusal_dev: bool = False,
    bug0_unified_survival_dev: bool = False,
    bug0_attack_dev: bool = False,
    bug0_attack_health_dev: bool = False,
    bug0_rest_dev: bool = False,
    bug0_attack_rest_dev: bool = False,
    bug0_p1_paper_dev: bool = False,
    bug0_p1_prospective_rest_dev: bool = False,
    bug0_p1_margin_dev: bool = False,
    worldbody_dev: bool = False,
    worldbody_retest_dev: bool = False,
    unified_c1_dev: bool = False,
    unified_c1_two_intents_dev: bool = False,
    unified_c1_journal_dev: bool = False,
    unified_c1_physical_fence_dev: bool = False,
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
    motion_dev = None
    journal_dev = None
    physical_fence_dev = None
    rc = 2
    cancellations: list[asyncio.CancelledError] = []
    worldbody_active = worldbody_dev or worldbody_retest_dev
    try:
        if os.environ.get("S49_REAL_SERVER_CI") != "1" or os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("explicit S49 real server env and no Node shim required")
        if stage_r_dev and os.environ.get("S49_STAGE_R_DEV_ONLY") != "1":
            raise S31ABlocked("Stage R requires separate explicit DEV-only operator gate")
        if type(completed_l0_dev) is not bool or (
            completed_l0_dev
            and os.environ.get("S49_COMPLETED_L0_DEV_ONLY") != "1"
        ):
            raise S31ABlocked("S49 completed L0 DEV readback requires explicit gate")
        if type(bug0_eat_shadow) is not bool or (
            bug0_eat_shadow and os.environ.get("S49_BUG0_EAT_SHADOW_DEV_ONLY") != "1"
        ):
            raise S31ABlocked("Bug-0 read-only EAT shadow needs explicit DEV gate")
        if (
            type(bug0_food_loop_dev) is not bool
            or (bug0_food_loop_dev and (
                os.environ.get("S49_BUG0_FOOD_LOOP_DEV_ONLY") != "1"
                or stage_r_dev or completed_l0_dev or completed_l0 is not None
                or bug0_eat_shadow or live_probe is not None
            ))
        ):
            raise S31ABlocked("S49 food L0 DEV requires separate exclusive gate")
        if (
            type(bug0_food_refusal_dev) is not bool
            or (bug0_food_refusal_dev and (
                os.environ.get("S49_BUG0_FOOD_REFUSAL_DEV_ONLY") != "1"
                or bug0_food_loop_dev or stage_r_dev or completed_l0_dev
                or completed_l0 is not None or bug0_eat_shadow
                or live_probe is not None
            ))
        ):
            raise S31ABlocked("S49 native refusal matrix needs exclusive DEV gate")
        if (
            type(bug0_unified_survival_dev) is not bool
            or (bug0_unified_survival_dev and (
                os.environ.get("S49_BUG0_UNIFIED_SURVIVAL_DEV_ONLY") != "1"
                or bug0_food_loop_dev or bug0_food_refusal_dev
                or bug0_eat_shadow or stage_r_dev or completed_l0_dev
                or completed_l0 is not None or live_probe is not None
            ))
        ):
            raise S31ABlocked("unified EAT/MOVE requires exclusive S49 DEV gate")
        if (
            type(bug0_attack_dev) is not bool
            or (bug0_attack_dev and (
                os.environ.get("S49_BUG0_ATTACK_DEV_ONLY") != "1"
                or bug0_food_loop_dev or bug0_food_refusal_dev
                or bug0_unified_survival_dev or bug0_eat_shadow
                or stage_r_dev or completed_l0_dev
                or completed_l0 is not None or live_probe is not None
            ))
        ):
            raise S31ABlocked("original S49 ATTACK needs exclusive DEV gate")
        if (
            type(bug0_attack_health_dev) is not bool
            or (bug0_attack_health_dev and (
                os.environ.get("S49_BUG0_ATTACK_HEALTH_DEV_ONLY") != "1"
                or bug0_attack_dev or bug0_food_loop_dev
                or bug0_food_refusal_dev or bug0_unified_survival_dev
                or bug0_eat_shadow or stage_r_dev or completed_l0_dev
                or completed_l0 is not None or live_probe is not None
            ))
        ):
            raise S31ABlocked("original ATTACK Paper health check requires exclusive DEV gate")
        if (
            type(bug0_rest_dev) is not bool
            or (bug0_rest_dev and (
                os.environ.get("S49_BUG0_REST_DEV_ONLY") != "1"
                or bug0_attack_health_dev or bug0_attack_dev
                or bug0_food_loop_dev or bug0_food_refusal_dev
                or bug0_unified_survival_dev or bug0_eat_shadow
                or stage_r_dev or completed_l0_dev
                or completed_l0 is not None or live_probe is not None
            ))
        ):
            raise S31ABlocked("original S49 REST requires exclusive DEV gate")
        if (
            type(bug0_attack_rest_dev) is not bool
            or (bug0_attack_rest_dev and (
                os.environ.get("S49_BUG0_ATTACK_REST_DEV_ONLY") != "1"
                or bug0_rest_dev or bug0_attack_health_dev
                or bug0_attack_dev or bug0_food_loop_dev
                or bug0_food_refusal_dev or bug0_unified_survival_dev
                or bug0_eat_shadow or stage_r_dev or completed_l0_dev
                or completed_l0 is not None or live_probe is not None
            ))
        ):
            raise S31ABlocked("ATTACK to REST needs exclusive original S49 DEV gate")
        if (
            type(bug0_p1_paper_dev) is not bool
            or (bug0_p1_paper_dev and (
                os.environ.get("S49_BUG0_P1_PAPER_DEV_ONLY") != "1"
                or bug0_p1_prospective_rest_dev or bug0_p1_margin_dev
                or worldbody_active or bug0_rest_dev or bug0_attack_rest_dev
                or bug0_attack_health_dev or bug0_attack_dev
                or bug0_food_loop_dev or bug0_food_refusal_dev
                or bug0_unified_survival_dev or bug0_eat_shadow
                or stage_r_dev or completed_l0_dev
                or completed_l0 is not None or live_probe is not None
            ))
        ):
            raise S31ABlocked("S49 P1 Paper requires exclusive original DEV gate")
        if (
            type(bug0_p1_prospective_rest_dev) is not bool
            or (bug0_p1_prospective_rest_dev and (
                os.environ.get("S49_BUG0_P1_PAPER_DEV_ONLY") != "1"
                or os.environ.get("S49_BUG0_P1_PROSPECTIVE_REST_ONLY") != "1"
                or not os.environ.get("S49_P1_ORIGINAL_CHECKOUT", "").startswith("/")
                or bug0_p1_paper_dev or bug0_p1_margin_dev
                or worldbody_active or bug0_rest_dev or bug0_attack_rest_dev or bug0_attack_health_dev
                or bug0_attack_dev or bug0_food_loop_dev
                or bug0_food_refusal_dev or bug0_unified_survival_dev
                or bug0_eat_shadow or stage_r_dev or completed_l0_dev
                or completed_l0 is not None or live_probe is not None
            ))
        ):
            raise S31ABlocked(
                "S49 prospective P1 REST needs pinned owner and exclusive DEV gate"
            )
        if (
            type(bug0_p1_margin_dev) is not bool
            or (bug0_p1_margin_dev and (
                os.environ.get("S49_BUG0_P1_PAPER_DEV_ONLY") != "1"
                or os.environ.get("S49_BUG0_P1_MARGIN_DEV_ONLY") != "1"
                or not os.environ.get("S49_P1_ORIGINAL_CHECKOUT", "").startswith("/")
                or bug0_p1_paper_dev or bug0_p1_prospective_rest_dev
                or worldbody_active or bug0_rest_dev or bug0_attack_rest_dev
                or bug0_attack_health_dev or bug0_attack_dev
                or bug0_unified_survival_dev or bug0_eat_shadow
                or bug0_food_loop_dev or bug0_food_refusal_dev
                or stage_r_dev or completed_l0_dev
                or completed_l0 is not None or live_probe is not None
            ))
        ):
            raise S31ABlocked("exclusive S49 P1 margin DEV gate required")
        if (
            type(worldbody_dev) is not bool
            or type(worldbody_retest_dev) is not bool
            or (worldbody_dev and worldbody_retest_dev)
            or (worldbody_retest_dev
                and os.environ.get("S49_WORLDBODY_RETEST_DEV_ONLY") != "1")
            or (worldbody_active and (
                os.environ.get("S49_WORLDBODY_DEV_ONLY") != "1"
                or bug0_p1_paper_dev or bug0_p1_prospective_rest_dev
                or bug0_p1_margin_dev or bug0_attack_rest_dev
                or bug0_rest_dev or bug0_attack_health_dev
                or bug0_attack_dev or bug0_eat_shadow
                or bug0_food_loop_dev or bug0_food_refusal_dev
                or bug0_unified_survival_dev or stage_r_dev or completed_l0_dev
                or completed_l0 is not None or live_probe is not None
            ))
        ):
            raise S31ABlocked(
                "one original S49 WorldBody owner and exclusive DEV World gate required"
            )
        if (
            type(unified_c1_physical_fence_dev) is not bool
            or (unified_c1_physical_fence_dev and (
                not unified_c1_dev or not unified_c1_two_intents_dev
                or not unified_c1_journal_dev
                or os.environ.get("S49_C1_PHYSICAL_FENCE_DEV_ONLY") != "1"
            ))
        ):
            raise S31ABlocked(
                "C1 pre-ISSUE physical fence requires separate DEV-only grant"
            )
        if (
            type(unified_c1_journal_dev) is not bool
            or (unified_c1_journal_dev and (
                not unified_c1_dev or not unified_c1_two_intents_dev
                or os.environ.get("S49_C1_JOURNAL_DEV_ONLY") != "1"
            ))
        ):
            raise S31ABlocked(
                "C1 durable journal requires exclusive S49 2-Intent DEV gate"
            )
        if (
            type(unified_c1_two_intents_dev) is not bool
            or (unified_c1_two_intents_dev and (
                not unified_c1_dev
                or os.environ.get("S49_UNIFIED_C1_TWO_INTENTS_DEV_ONLY") != "1"
            ))
        ):
            raise S31ABlocked(
                "C1 second original Intent requires independent exclusive DEV epoch gate"
            )
        if (
            type(unified_c1_dev) is not bool
            or (unified_c1_dev and (
                os.environ.get("S49_UNIFIED_C1_DEV_ONLY") != "1"
                or stage_r_dev or completed_l0_dev or completed_l0 is not None
                or live_probe is not None or worldbody_active
                or bug0_eat_shadow or bug0_food_loop_dev
                or bug0_food_refusal_dev or bug0_unified_survival_dev
                or bug0_attack_dev or bug0_attack_health_dev
                or bug0_rest_dev or bug0_attack_rest_dev
                or bug0_p1_paper_dev or bug0_p1_prospective_rest_dev
                or bug0_p1_margin_dev
            ))
        ):
            raise S31ABlocked(
                "C1/S10 original S49 DEV requires a separate exclusive runner gate"
            )
        if unified_c1_physical_fence_dev:
            from relay_self.c1_physical_action_fence import (
                OriginalS49PhysicalFence,
            )

            fence_path = report_path.parent / "c1_physical_action_fence.json"
            if fence_path.exists():
                physical_fence_dev = OriginalS49PhysicalFence.restore(
                    fence_path, self_id="s49-original-self",
                )
                report["physical_fence_restored_before_world"] = True
            else:
                physical_fence_dev = OriginalS49PhysicalFence.create(
                    fence_path, self_id="s49-original-self",
                )
                report["physical_fence_restored_before_world"] = False
            # Fail BEFORE provisioning any World when a previous attempt
            # was only PREPARED and may have been physically dispatched.
            physical_fence_dev.require_clear()
            report["physical_fence_unresolved_before_world"] = False
            report["physical_fence_prior_actions"] = len(physical_fence_dev.actions)
        report["stage"] = "PROVISION_DISPOSABLE_MOJANG_GAME"
        temp = tempfile.TemporaryDirectory(prefix="relay-self-s49-")
        root = Path(temp.name)
        if worldbody_active:
            from adapters.mineflayer.worldbody_paper_server import (
                stage_fixed_worldbody,
            )

            report.update(await asyncio.to_thread(stage_fixed_worldbody, root))
        elif bug0_p1_paper_dev or bug0_p1_prospective_rest_dev or bug0_p1_margin_dev:
            from adapters.mineflayer.s49_p1_paper_server import stage_paper_dev

            report.update(await asyncio.to_thread(stage_paper_dev, root))
        else:
            report.update(await asyncio.to_thread(
                _fetch_official_server, root / "minecraft.jar",
            ))
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
        _, committed, _, _, _, _ = await asyncio.to_thread(s19._epoch_one)
        retained = committed.new_state
        if retained.target_id != "risk_weight" or retained.revision != 1 or retained.value != 4:
            raise S49PhysicalFailure("frozen governed retained source changed")
        intent = IntentCommitment()
        intent_name = (
            "eat-when-hungry" if (bug0_food_loop_dev or bug0_food_refusal_dev)
            else "rest-observe" if bug0_rest_dev else "escape-threat"
        )
        intent.commit(
            intent_name,
            objective=(
                "one native EAT and post-EAT L0 WAIT"
                if (bug0_food_loop_dev or bug0_food_refusal_dev)
                else "one REST intent and bounded stationary native observation"
                if bug0_rest_dev else "escape near zombie"
            ),
            at_ns=1, provenance=source("committed-existing-intent"),
        )
        host = NormalWorldL0(
            sid, intent_name, retained, max_events=3, max_action_requests=2,
        )
        executor = NormalSessionActionExecutor(sid, intent)
        if unified_c1_dev:
            from adapters.mineflayer.s49_c1_motion_owner_dev import (
                S49C1MotionDevJoin,
            )
            from relay_self.learning import LearningPreferenceState

            # This S10 owner is separate from L0's frozen risk_weight.
            motion_state = LearningPreferenceState(
                "motion_decimeters", 7, 0, 10, 0,
                source("unified-c1-seeded-motion-model"),
            )
            if unified_c1_journal_dev:
                from relay_self.c1_motion_journal import C1MotionJournal

                journal_path = report_path.parent / "c1_motion_journal.json"
                if journal_path.exists():
                    # A prior persisted S10 state is never silently reseeded.
                    journal_dev = C1MotionJournal.restore(
                        journal_path, self_id="s49-original-self",
                    )
                    report["c1_journal_restored_before_world"] = True
                else:
                    journal_dev = C1MotionJournal.create(
                        journal_path, self_id="s49-original-self",
                        seed=motion_state,
                    )
                    report["c1_journal_restored_before_world"] = False
                motion_state = journal_dev.state
                journal_prior_ids = journal_dev.experience_ids
                report["c1_journal_prior_experiences"] = len(journal_prior_ids)
                report["c1_journal_source"] = "ORIGINAL_S49_S10_OWNER_ATOMIC_LOCAL_SNAPSHOT"
                report["c1_journal_before_revision"] = motion_state.revision
            motion_dev = S49C1MotionDevJoin(
                intent, executor, motion_state,
                self_id="s49-original-self", journal=journal_dev,
            )
            report["unified_c1_dev_enabled"] = True
            report["unified_c1_physical_grant_inferred"] = False
            report["unified_c1_two_intents_dev_enabled"] = (
                unified_c1_two_intents_dev
            )
        active_motion_dev = motion_dev
        successor_join = None
        next_c1 = None
        eat_cursor = EatCursor(sid) if bug0_eat_shadow else None
        if bug0_p1_paper_dev or bug0_p1_prospective_rest_dev or bug0_p1_margin_dev:
            from adapters.mineflayer.s49_p1_paper_dev import run_s49_p1_paper_dev

            if bug0_p1_margin_dev:
                await run_s49_p1_paper_dev(
                    session, server, executor, report, server_log,
                    prospective_rest_dev=True, margin_choice_dev=True,
                    p1_checkout=Path(os.environ["S49_P1_ORIGINAL_CHECKOUT"]),
                )
            elif bug0_p1_prospective_rest_dev:
                await run_s49_p1_paper_dev(
                    session, server, executor, report, server_log,
                    prospective_rest_dev=True,
                    p1_checkout=Path(os.environ["S49_P1_ORIGINAL_CHECKOUT"]),
                )
            else:
                await run_s49_p1_paper_dev(
                    session, server, executor, report, server_log,
                )
            report["status"] = "PASS"
            report["classification"] = (
                "DEV_ONLY_S49_P1_MARGIN_SENSOR_NATIVE_CHOICE"
                if bug0_p1_margin_dev
                else "DEV_ONLY_S49_P1_EXPERIMENTAL_SENSOR_PROSPECTIVE_REST"
                if bug0_p1_prospective_rest_dev
                else "DEV_ONLY_S49_PAPER_FIGHT_TICK_AND_REST_CALLBACK_SOURCE"
            )
            rc = 0
            raise Bug0FoodLoopDevCompleted
        if bug0_attack_rest_dev:
            from adapters.mineflayer.s49_attack_then_rest_dev import (
                run_s49_attack_then_rest_dev,
            )
            await run_s49_attack_then_rest_dev(
                session, server, executor, report, health_log=server_log,
            )
            report["status"] = "PASS"
            report["classification"] = "DEV_ONLY_S49_ONE_ATTACK_THEN_REST_NATIVE_SAMPLES"
            rc = 0
            raise Bug0FoodLoopDevCompleted
        if bug0_rest_dev:
            from adapters.mineflayer.s49_rest_dev import run_s49_rest_dev

            await run_s49_rest_dev(session, server, executor, report)
            report["status"] = "PASS"
            report["classification"] = "DEV_ONLY_S49_REST_INTENT_STATIONARY_SAMPLES"
            rc = 0
            raise Bug0FoodLoopDevCompleted
        if bug0_attack_dev or bug0_attack_health_dev:
            # Original S49 session/executor/supervisor is the ONLY Action owner.
            # The transport callback has no independent issuer or grant.
            from adapters.mineflayer.s49_attack_dev import run_s49_attack_dev

            await run_s49_attack_dev(
                session, server, executor, report,
                health_log=server_log if bug0_attack_health_dev else None,
            )
            report["status"] = "PASS"
            report["classification"] = (
                "DEV_ONLY_S49_ATTACK_PAPER_HEALTH_DROP"
                if bug0_attack_health_dev
                and report.get("attack_server_health_drop_observed") is True
                else "DEV_ONLY_S49_ATTACK_PAPER_NO_HEALTH_DROP"
                if bug0_attack_health_dev
                else "DEV_ONLY_S49_SUPERVISED_ATTACK_EFFECT_APPLIED"
            )
            report["stage"] = "BUG0_S49_ATTACK_EFFECT_CLOSED"
            rc = 0
            raise Bug0FoodLoopDevCompleted
        unified_policy = None
        unified_probe_choice = {}
        if bug0_unified_survival_dev:
            # Reuse original S49 native session and EXACT same executor.
            # The shared priority policy selects EAT; after its terminal
            # the original zombie World L0 can issue admitted MOVE Actions.
            from adapters.mineflayer.s49_food_loop_dev import run_s49_food_loop

            unified_policy = await run_s49_food_loop(
                session, server, executor, report,
            )
            if (
                executor._count != 1 or executor.supervisor.open_actions
                or report.get("action_terminal") != "outcome"
            ):
                raise S49PhysicalFailure("unified owner did not close EAT first")
            # REST is an intent-only selection, not another physical Action.
            # An original P1 authenticated WAIT tick is still missing.
            resting_probe = await _correlated_observe(
                session, f"s49-unified-rest-candidate-{sid}",
            )
            resting = unified_policy.decide(
                resting_probe, rest_requested=True,
            )
            report["unified_rest_candidate"] = {
                "selected": resting.selected, "preferred": resting.preferred,
                "reason": resting.reason, "probe_seq": resting.probe_seq,
                "issued": False, "energy_recovered_attested": False,
                "p1_fatigue_recovery_attested": False,
            }
            if (
                resting.selected != "REST" or resting.preferred != "REST"
                or executor._count != 1 or executor.supervisor.open_actions
            ):
                raise S49PhysicalFailure("REST candidate changed original Action owner")
            report["unified_priority_trace"] = []
        if bug0_food_loop_dev:
            # The S49 original launcher/session/executor owns this DEV branch;
            # S51 is a delegate only. The zombie-only normal loop is unchanged.
            from adapters.mineflayer.s49_food_loop_dev import run_s49_food_loop

            await run_s49_food_loop(session, server, executor, report)
            report["status"] = "PASS"
            report["classification"] = "DEV_ONLY_S49_FOOD_L0_EAT_WAIT_OUTCOME"
            report["stage"] = "BUG0_S49_FOOD_L0_CLOSED"
            rc = 0
            raise Bug0FoodLoopDevCompleted
        if bug0_food_refusal_dev:
            from adapters.mineflayer.s49_food_refusal_dev import (
                run_s49_food_refusal_matrix,
            )

            await run_s49_food_refusal_matrix(session, server, executor, report)
            report["status"] = "PASS"
            report["classification"] = "DEV_ONLY_S49_FOOD_REFUSAL_NATIVE_3_CONDITIONS"
            report["stage"] = "BUG0_S49_REFUSAL_CLOSED"
            rc = 0
            raise Bug0FoodLoopDevCompleted
        if eat_cursor is not None:
            report["bug0_eat_shadow"] = []
            report["bug0_eat_shadow_only"] = True
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
        # Exact S16 Action receipts, captured only AFTER the original executor
        # has completed and checked its terminal outcome. Optional diagnostic.
        closed_receipts = {}
        worldbody_experiences = []

        async def reprobe(frame):
            request_id = f"s49-actual:{sid}:event-{frame.seq}"
            reading = await _correlated_observe(session, request_id)
            probes[reading.seq] = reading
            if unified_policy is not None:
                candidate = unified_policy.decide(reading)
                unified_probe_choice[reading.seq] = candidate
                report["unified_priority_trace"].append({
                    "probe_seq": reading.seq,
                    "selected": candidate.selected,
                    "preferred": candidate.preferred,
                    "fallback": candidate.fallback,
                    "reason": candidate.reason,
                    "food": candidate.food,
                    "issued": False,
                })
            if eat_cursor is not None:
                report["bug0_eat_shadow"].append(
                    read_only_bug0_eat_window(eat_cursor, reading)
                )
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
            current = intent.current_intent
            if (
                current is None
                or current.intent_id not in (
                    ("escape-threat", "next-escape-threat")
                    if unified_c1_two_intents_dev else ("escape-threat",)
                )
            ):
                raise S49PhysicalFailure("original S49 Intent owner absent or changed")
            if choice.selection is not WorldChoiceKind.MOVE_AWAY:
                raise S49PhysicalFailure("WAIT attempted to request Action")
            return L0ActionGrant(
                authority_id=f"s49-preconfigured-escape-{event_seq}",
                action_id=f"s49-native-move-{event_seq}",
                intent_id=current.intent_id, session_id=sid,
                event_seq=event_seq, probe_seq=choice.probe_seq,
                entity_id=choice.entity_id, granted=True,
                provenance=source(f"l0-request-{event_seq}"),
            )

        def authorize(step, stage):
            if step.grant is None or intent.current_intent is None:
                raise S49PhysicalFailure("missing original current Intent/Action grant")
            return NormalActionAuthorization(
                stage=stage, authority_id=f"s49-{stage.value.lower()}-{step.event_seq}",
                intent_id=step.grant.intent_id, session_id=sid,
                action_id=step.action_request_id, event_seq=step.event_seq,
                probe_seq=step.choice.probe_seq, entity_id=step.choice.entity_id,
                granted=True,
                provenance=source(f"independent-{stage.value.lower()}-{step.event_seq}"),
            )

        async def on_action(step):
            probe = probes[step.choice.probe_seq]
            if unified_policy is not None:
                # The single shared native decision gate must have suppressed
                # EAT and preferred defense, before frozen S14 admission.
                joint = unified_probe_choice.get(probe.seq)
                if (
                    joint is None or joint.selected != "DEFER"
                    or joint.preferred != "MOVE_AWAY"
                    or joint.fallback != "ATTACK"
                    or step.choice.selection is not WorldChoiceKind.MOVE_AWAY
                    or executor.supervisor.open_actions
                    or executor._count not in (1, 2)
                ):
                    raise S49PhysicalFailure(
                        "shared food/move priority did not admit original defense"
                    )
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
                required_intent_id=step.grant.intent_id,
            )
            if (
                epoch.cognition_requested
                or values["plan"].selected is None
                or values["plan"].selected.candidate_id != "MOVE_AWAY"
                or values["admission"].status.value != "admitted"
                or values["policies"][-2].required_intent_id
                != step.grant.intent_id
            ):
                raise S49PhysicalFailure("full S14 native admission was not independently satisfied")
            binding = ExecutionBinding(
                binding_id=f"s49-binding-{step.event_seq}",
                candidate_ref="MOVE_AWAY",
                required_intent_id=step.grant.intent_id,
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
            if active_motion_dev is not None:
                # Exact original owner/selection source before S15 dispatch.
                action_forecast = active_motion_dev.prepare_original_action(
                    step, probe,
                )
                if successor_join is not None and active_motion_dev is successor_join:
                    if (
                        next_c1 is None
                        or action_forecast.intent_id != next_c1.intent_id
                        or action_forecast.owner_revision != next_c1.owner_revision
                        or action_forecast.predicted_total_m != next_c1.predicted_total_m
                        or action_forecast.source_probe_seq <= next_c1.source_probe_seq
                    ):
                        raise S49PhysicalFailure(
                            "second original S49 Action did not consume current S10 owner"
                        )
            if stage_r is None:
                # Original S49 executor invokes this callback AFTER checking
                # both grants but BEFORE supervisor ISSUE / any adapter IO.
                def reserve_original_before_issue() -> None:
                    assert step.grant is not None
                    if physical_fence_dev is not None:
                        physical_fence_dev.prepare(
                            session_id=sid, intent_id=step.grant.intent_id,
                            action_id=step.action_request_id, probe=probe,
                        )

                receipt = await executor.execute(
                    session, step, bound, probe,
                    authorize(step, NormalActionStage.PROPOSE),
                    authorize(step, NormalActionStage.ISSUE),
                    pre_issue_reservation=(
                        reserve_original_before_issue
                        if physical_fence_dev is not None else None
                    ),
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
            if active_motion_dev is not None:
                # Read only ORIGINAL S16 terminal from SAME executor supervisor.
                active_motion_dev.accept_original_terminal(step, probe, receipt)
            if physical_fence_dev is not None:
                # Seal ONLY a verified original S16 outcome; an interrupted
                # Action leaves PREPARED/UNKNOWN and blocks a future World.
                physical_fence_dev.close(
                    receipt, probe, original_supervisor=executor.supervisor,
                )
            if eat_cursor is not None:
                # Diagnostic only: the original S15 cleanup ACK and S16 terminal
                # cannot establish effective physical STOP or release EAT.
                read = executor.read_only_post_move_eat_boundary(receipt)
                report.setdefault("bug0_post_move_eat_boundary", []).append({
                    "session_id": read.session_id,
                    "action_id": read.action_id,
                    "s16_terminal": read.s16_terminal,
                    "s15_clear_ack_applied": read.s15_clear_ack_applied,
                    "clear_ack_seq": read.clear_ack_seq,
                    "after_probe_seq": read.after_probe_seq,
                    "source_ref": read.readback_source.reference,
                    "settling_status": read.settling_status,
                    "physically_stopped_proven": read.physically_stopped_proven,
                    "eat_issuance_authorized": read.eat_issuance_authorized,
                })
            if stage_r is not None:
                stage_r.seal_original_action(step, receipt)
            if worldbody_active:
                # Only original native S16 + SelfBody Present, NEVER server
                # WorldBody truth, model fatigue, or operator log.
                from adapters.mineflayer.worldbody_direct_selfbody import (
                    direct_move_experience,
                )

                # S15's internal after observation lacks a request_id.
                # Obtain a NEW original session-correlated native Present;
                # never relabel the uncorrelated S15 packet as SelfBody truth.
                correlated = await _correlated_observe(
                    session, f"worldbody-direct-{sid}-{receipt.terminal.action_id}"
                )
                worldbody_experiences.append(
                    direct_move_experience(receipt, correlated)
                )
            if completed_l0 is not None or completed_l0_dev:
                closed_receipts[step.action_request_id] = receipt
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
            _command(server, "gamerule doMobSpawning false")
            await server.stdin.drain()
            await asyncio.sleep(2)
            for distance_m, hold in ((10, 5), (2, 8), (2, 8)):
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
        if (
            len(trace) != 3
            or [s.choice.selection.value for s in trace]
            != ["WAIT", "MOVE_AWAY", "MOVE_AWAY"]
            or len({s.choice.entity_id for s in trace}) != 3
            or len(report["actual_native_actions"])
            != (3 if unified_policy is not None else 2)
            or executor.supervisor.open_actions
            or executor.supervisor.get(trace[1].action_request_id).state is not ActionState.OUTCOME
            or executor.supervisor.get(trace[2].action_request_id).state is not ActionState.OUTCOME
            or trace[0].asks_for_action
            or host.action_requests != 2
            or host.events != 3
        ):
            raise S49PhysicalFailure("not three unattended decisions and two real closures")
        if motion_dev is not None:
            # The original S49 owner, not a diagnostic observer, ends the
            # attempted Intent after all existing S16 Actions have closed.
            # Follow-up remains read-only: no second L0 decision or Action.
            terminal_c1 = motion_dev.close_original_intent()
            next_native = await _correlated_observe(
                session, f"s49-c1-next-intent-{sid}"
            )
            next_c1 = motion_dev.start_next_original_intent(
                next_native, next_intent_id="next-escape-threat",
            )
            report["unified_c1_original_owner"] = {
                "original_intent_id": terminal_c1.experience.forecast.intent_id,
                "original_intent_terminal": terminal_c1.experience.terminal_kind.value,
                "external_goal_verified": terminal_c1.experience.intent_goal_verified,
                "experience_id": terminal_c1.experience.experience_id,
                "action_ids": [
                    r.terminal.action_id
                    for r in terminal_c1.experience.action_receipts
                ],
                "decision_probe_seq": [
                    p.seq for p in terminal_c1.experience.decision_probes
                ],
                "s15_before_seq": [
                    r.consequence.before_observation.seq
                    for r in terminal_c1.experience.action_receipts
                ],
                "motion_comparison": terminal_c1.experience.comparison.value,
                "measured_total_m": terminal_c1.experience.measured_total_m,
                "retained_revision": motion_dev.retained_motion.revision,
                "retained_value": motion_dev.retained_motion.value,
                "next_intent_id": next_c1.intent_id,
                "next_source_seq": next_c1.source_probe_seq,
                "next_forecast_m": next_c1.predicted_total_m,
                "next_consumed_revision": next_c1.owner_revision,
                "next_l0_action_issued": False,
                "learned_decision_policy": False,
                "durable_replay_journal": journal_dev is not None,
                "independent_source_attestation": False,
            }
            report["learning_in_world"] = terminal_c1.learning is not None
            if unified_c1_two_intents_dev:
                if (
                    staging is None or executor.supervisor.open_actions
                    or next_c1.owner_revision != motion_dev.retained_motion.revision
                    or intent.current_intent is None
                    or intent.current_intent.intent_id != next_c1.intent_id
                ):
                    raise S49PhysicalFailure(
                        "no original Intent handoff for a second S49 Action"
                    )
                # First external World stimulation must fully finish before
                # the next target appears; no additional Action issuer.
                await asyncio.wait_for(staging, timeout=20)
                successor_join = S49C1MotionDevJoin(
                    intent, executor, motion_dev.retained_motion,
                    self_id=motion_dev.self_id, journal=journal_dev,
                )
                active_motion_dev = successor_join
                next_host = NormalWorldL0(
                    sid, next_c1.intent_id, retained,
                    max_events=1, max_action_requests=1,
                )
                # Same disposable World, session, Intent and executor. The
                # operator controls only the external World target stimulus.
                _command(server, "kill @e[type=minecraft:zombie]")
                await server.stdin.drain()
                await asyncio.sleep(2)
                _command(
                    server,
                    "execute at RelaySelf run summon minecraft:zombie ~2 ~ ~ "
                    "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}",
                )
                await server.stdin.drain()
                next_trace = await asyncio.wait_for(
                    next_host.run_session(
                        observation_source, probe=reprobe, grant=decide_grant,
                        on_action_request=on_action, max_frames=90,
                    ),
                    timeout=40,
                )
                if (
                    len(next_trace) != 1
                    or next_trace[0].choice.selection
                    is not WorldChoiceKind.MOVE_AWAY
                    or not next_trace[0].asks_for_action
                    or next_host.events != 1 or next_host.action_requests != 1
                    or successor_join.action_count != 1
                    or executor.supervisor.open_actions
                    or executor._count != 3
                    or len(report["actual_native_actions"]) != 3
                    or next_trace[0].choice.probe_seq <= next_c1.source_probe_seq
                ):
                    raise S49PhysicalFailure(
                        "second original L0 Intent did not close one real Action"
                    )
                second_terminal = successor_join.close_original_intent()
                report["unified_c1_original_owner"]["next_l0_action_issued"] = True
                if journal_dev is not None:
                    from relay_self.c1_motion_journal import C1MotionJournal

                    recovered = C1MotionJournal.restore(
                        journal_dev.path, self_id=motion_dev.self_id,
                    )
                    if (
                        recovered.state != successor_join.retained_motion
                        or recovered.sha256 != journal_dev.sha256
                        or recovered.experience_ids != (
                            *journal_prior_ids,
                            terminal_c1.experience.experience_id,
                            second_terminal.experience.experience_id,
                        )
                    ):
                        raise S49PhysicalFailure(
                            "C1 journal restart could not reproduce exact S10 owner"
                        )
                    report["c1_journal"] = {
                        "schema": 1, "path": journal_dev.path.name,
                        "sha256": recovered.sha256,
                        "experience_ids": list(recovered.experience_ids),
                        "prior_experience_count": len(journal_prior_ids),
                        "retained_revision": recovered.state.revision,
                        "retained_value": recovered.state.value,
                        "fresh_restore_equal_to_original_owner": True,
                        "new_physical_action_after_restore": False,
                        "general_persistent_cognition_migrated": False,
                        "physical_action_write_ahead_fence": False,
                    }
                if physical_fence_dev is not None:
                    from relay_self.c1_physical_action_fence import (
                        OriginalS49PhysicalFence,
                    )

                    restored_fence = OriginalS49PhysicalFence.restore(
                        physical_fence_dev.path,
                        self_id="s49-original-self",
                    )
                    actual_ids = [
                        a["action"] for a in report["actual_native_actions"]
                    ]
                    if (
                        restored_fence.unresolved
                        or restored_fence.sha256 != physical_fence_dev.sha256
                        or len(actual_ids) != 3
                        or [x["action_id"] for x in restored_fence.actions][-3:]
                        != actual_ids
                        or any(
                            x["status"] != "S16_OUTCOME"
                            for x in restored_fence.actions[-3:]
                        )
                    ):
                        raise S49PhysicalFailure(
                            "physical pre-ISSUE fence did not retain 3 exact S16 closures"
                        )
                    report["c1_physical_fence"] = {
                        "path": physical_fence_dev.path.name,
                        "sha256": restored_fence.sha256,
                        "action_ids": actual_ids,
                        "prior_action_count": report["physical_fence_prior_actions"],
                        "all_current_s16_outcomes": True,
                        "unresolved": False,
                        "new_action_after_recovery": False,
                        "physical_exactly_once_attested": False,
                        "independent_world_truth_attested": False,
                    }
                report["unified_c1_second_original_owner"] = {
                    "intent_id": next_c1.intent_id,
                    "original_l0_event_seq": next_trace[0].event_seq,
                    "original_l0_probe_seq": next_trace[0].choice.probe_seq,
                    "pre_action_s10_revision": (
                        second_terminal.experience.forecast.owner_revision
                    ),
                    "pre_action_forecast_m": (
                        second_terminal.experience.forecast.predicted_total_m
                    ),
                    "prior_next_intent_read_revision": next_c1.owner_revision,
                    "prior_next_intent_read_forecast_m": next_c1.predicted_total_m,
                    "one_physical_action_id": (
                        second_terminal.experience.action_receipts[0].terminal.action_id
                    ),
                    "one_action_s16_state": (
                        second_terminal.experience.action_receipts[0].terminal.state.value
                    ),
                    "experience_id": second_terminal.experience.experience_id,
                    "measured_total_m": second_terminal.experience.measured_total_m,
                    "motion_comparison": second_terminal.experience.comparison.value,
                    "terminal_kind": second_terminal.experience.terminal_kind.value,
                    "new_s10_revision": successor_join.retained_motion.revision,
                    "new_s10_value": successor_join.retained_motion.value,
                    "external_goal_verified": False,
                    "same_original_intent_owner": successor_join.intent is intent,
                    "same_original_action_executor": successor_join.executor is executor,
                    "learned_decision_policy": False,
                    "independently_attested_world_truth": False,
                    "durable_journal": journal_dev is not None,
                }
        if worldbody_active:
            from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0
            from adapters.mineflayer.s49_rest_dev import inspect_rest_native_samples
            from adapters.mineflayer.worldbody_direct_selfbody import (
                rest_from_observed_motor_output,
            )

            if (
                len(worldbody_experiences) != 2
                or len(report["actual_native_actions"]) != 2
                or executor._count != 2 or executor.supervisor.open_actions
            ):
                raise S49PhysicalFailure("WorldBody needs two original S16 MOVE outcomes")
            decision = rest_from_observed_motor_output(*worldbody_experiences)
            report["worldbody_direct_motor_observations"] = [{
                "session_id": x.session_id,
                "action_id": x.action_id,
                "native_seq": x.native_seq,
                "action_distance_m": x.action_distance_m,
                "source_ref": x.source_ref,
                "observed_fields": list(x.observed_fields),
                "hidden_worldbody_fatigue_accessed": False,
                "worldbody_rate_accessed": False,
            } for x in worldbody_experiences]
            report["worldbody_direct_rest_request"] = {
                "session_id": decision.session_id,
                "first_action_id": decision.first_action_id,
                "last_action_id": decision.last_action_id,
                "first_move_m": decision.first_move_m,
                "last_move_m": decision.last_move_m,
                "output_ratio": decision.output_ratio,
                "rest_requested": decision.rest_requested,
                "reason": decision.reason,
                "worldbody_truth_accessed": False,
            }
            report["worldbody_true_fatigue_received_by_self"] = False
            report["worldbody_physics_write_from_self"] = False
            report["stage"] = "WORLDBODY_POST_MOVE_L0_AND_REST"
            # Do not /kill: zombie drops and XP would contaminate a
            # source-qualified empty/resting native Present.
            _command(
                server,
                "execute at RelaySelf run tp @e[type=!minecraft:player] ~100 ~ ~",
            )
            await server.stdin.drain()
            await asyncio.sleep(2.0)
            baseline = await _correlated_observe(
                session, f"worldbody-rest-{sid}-baseline"
            )
            rest_choice = S49BasicPriorityL0(sid).decide(
                baseline, rest_requested=decision.rest_requested,
            )
            report["worldbody_postmove_l0_choice"] = {
                "selected": rest_choice.selected,
                "reason": rest_choice.reason,
                "preferred": rest_choice.preferred,
                "probe_seq": rest_choice.probe_seq,
                "native_source_ref": baseline.provenance.reference,
                "rest_action_issued": rest_choice.action_issued,
            }
            if (
                not decision.rest_requested or rest_choice.selected != "REST"
                or rest_choice.action_issued or rest_choice.permission_granted
            ):
                raise S49PhysicalFailure(
                    "physical motor loss not observed or original L0 REST declined"
                )
            stationary = [baseline]
            for index in range(8):
                await asyncio.sleep(4.0)
                stationary.append(await _correlated_observe(
                    session, f"worldbody-rest-{sid}-{index:02d}",
                ))
            report["worldbody_rest_native_observation"] = (
                inspect_rest_native_samples(stationary, session_id=sid)
            )
            report["worldbody_rest_action_count"] = 0
            report["worldbody_physics_verified_from_server_log"] = False
            report["worldbody_rest_choice_is_not_physical_recovery_proof"] = True
            if worldbody_retest_dev:
                # Same original live L0 cursor and SAME ActionSupervisor, with
                # one explicitly gated extra event / extra independent Action
                # authorization. Never re-issue a failed or unknown MOVE.
                from adapters.mineflayer.worldbody_direct_selfbody import (
                    check_post_rest_motor_output,
                )

                if (
                    host.events != 3 or host.action_requests != 2
                    or executor._count != 2 or executor.supervisor.open_actions
                    or len(worldbody_experiences) != 2
                    or len(report["worldbody_rest_native_observation"]["samples"]) != 9
                ):
                    raise S49PhysicalFailure(
                        "no safe two-S16 original REST prefix for retest"
                    )
                rest_last_seq = stationary[-1].seq
                host.extend_after_worldbody_rest_dev(token=object())
                report["stage"] = "WORLDBODY_REST_THEN_SAME_S49_THIRD_MOVE"
                # Operator stages a NEW independent zombie threat to request
                # a normal S49 MOVE after REST. No manual MOVE is sent;
                # original L0 and S14/S15/S16 must independently authorize it.
                _command(
                    server,
                    "execute at RelaySelf run summon minecraft:zombie ~2 ~ ~ "
                    "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}",
                )
                await server.stdin.drain()
                third_steps = await asyncio.wait_for(
                    host.run_session(
                        observation_source, probe=reprobe, grant=decide_grant,
                        on_action_request=on_action, max_frames=140,
                    ),
                    timeout=38,
                )
                if (
                    len(third_steps) != 1
                    or third_steps[0].choice.selection is not WorldChoiceKind.MOVE_AWAY
                    or not third_steps[0].asks_for_action
                    or third_steps[0].event_seq <= trace[-1].event_seq
                    or third_steps[0].choice.entity_id in {
                        old.choice.entity_id for old in trace
                    }
                    or host.events != 4 or host.action_requests != 3
                    or len(worldbody_experiences) != 3
                    or len(report["actual_native_actions"]) != 3
                    or executor._count != 3 or executor.supervisor.open_actions
                    or report["actual_native_actions"][-1]["terminal"] != "outcome"
                ):
                    raise S49PhysicalFailure(
                        "no freshly authorized third original S49 MOVE after REST"
                    )
                report["decisions"].append({
                    "event_seq": third_steps[0].event_seq,
                    "entity_id": third_steps[0].choice.entity_id,
                    "probe_seq": third_steps[0].choice.probe_seq,
                    "distance_m": third_steps[0].choice.distance_m,
                    "selected": third_steps[0].choice.selection.value,
                    "issued": third_steps[0].asks_for_action,
                })
                recovered = check_post_rest_motor_output(
                    *worldbody_experiences,
                    final_rest_probe_seq=rest_last_seq,
                )
                report["worldbody_post_rest_retest"] = {
                    "session_id": recovered.session_id,
                    "pre_rest_first_action": recovered.pre_rest_first_action,
                    "pre_rest_exhausted_action": recovered.pre_rest_exhausted_action,
                    "post_rest_action": recovered.post_rest_action,
                    "pre_rest_first_m": recovered.pre_rest_first_m,
                    "pre_rest_exhausted_m": recovered.pre_rest_exhausted_m,
                    "post_rest_m": recovered.post_rest_m,
                    "recovery_over_exhausted_ratio": (
                        recovered.recovery_over_exhausted_ratio
                    ),
                    "recovery_over_first_ratio": recovered.recovery_over_first_ratio,
                    "regained_motor_output": recovered.regained_motor_output,
                    "source_refs": list(recovered.source_refs),
                    "final_rest_probe_seq": rest_last_seq,
                    "worldbody_truth_accessed": recovered.worldbody_truth_accessed,
                    "server_internal_recovery_used_by_l0": False,
                    "three_separate_original_s16_move_outcomes": True,
                    "post_rest_world_rule_unchanged": True,
                }
                if not recovered.regained_motor_output:
                    raise S49PhysicalFailure(
                        "post REST third original S16 MOVE did not regain output"
                    )
        if unified_policy is not None:
            actions = report["actual_native_actions"]
            if (
                actions[0].get("kind") != "EAT"
                or actions[0].get("terminal") != "outcome"
                or actions[1].get("terminal") != "outcome"
                or actions[2].get("terminal") != "outcome"
                or executor._count != 3 or executor.supervisor.open_actions
                or executor._post_move_settling_unqualified is not True
                or len(report["unified_priority_trace"]) != 3
                or [
                    x["preferred"] for x in report["unified_priority_trace"]
                ] != [None, "MOVE_AWAY", "MOVE_AWAY"]
            ):
                raise S49PhysicalFailure(
                    "original S49 EAT->MOVE->MOVE or STOP safety missing"
                )
            report["unified_actual_action_order"] = ["EAT", "MOVE_AWAY", "MOVE_AWAY"]
            report["post_move_eat_fenced"] = True
            report["rest_physical_execution"] = "NOT_RUN"
            report["attack_physical_execution"] = "NOT_RUN"
            report["independent_eat_grant_attested"] = False
            report["source_independently_attested"] = False
            report["learning_in_world"] = False
            report["m_energy_credited"] = False
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
        if completed_l0 is not None or completed_l0_dev:
            # S49 has already obtained every original L0Step and S16 terminal.
            # This is not an S42 DecisionEpochResult or a B0/L8 epoch.
            # Readback errors cannot veto the original physical Action.
            try:
                batch = read_original_s49_completions(
                    tuple(trace), probes, closed_receipts,
                )
                if completed_l0_dev:
                    report["original_completion_readback"] = (
                        bounded_original_s49_completion_row(batch)
                    )
                if completed_l0 is not None:
                    completed_l0(batch)
                report["original_completion_observer"] = "CALLBACK_RETURNED"
            except Exception:
                report["original_completion_observer"] = "OBSERVER_ERROR"
        report["status"] = "PASS"
        report["classification"] = (
            "DEV_ONLY_S49_C1_PREISSUE_FENCE_TWO_INTENTS"
            if unified_c1_physical_fence_dev
            else "DEV_ONLY_S49_C1_DURABLE_TWO_INTENT_S10_RESTART_READ"
            if unified_c1_journal_dev
            else "DEV_ONLY_S49_C1_S10_TWO_ORIGINAL_INTENT_ACTION_EXPERIENCES"
            if unified_c1_two_intents_dev
            else "DEV_ONLY_S49_C1_S10_NEXT_ORIGINAL_FORECAST_NOT_NEXT_ACTION"
            if motion_dev is not None
            else "DEV_ONLY_WORLDBODY_ORIGINAL_S49_POST_REST_THIRD_MOTOR_OUTCOME"
            if worldbody_retest_dev
            else "DEV_ONLY_WORLDBODY_FIXED_PHYSICS_DIRECT_S16_REST"
            if worldbody_dev
            else "DEV_ONLY_S49_SINGLE_OWNER_EAT_THEN_TWO_MOVES"
            if unified_policy is not None
            else "DEV_ONLY_S49_SINGLE_WRITER_HOLD_REV2"
            if stage_r is not None
            else "REAL_ONE_SESSION_L0_WAIT_TWO_AUTHORIZED_MOVES_QUALIFIED"
        )
        report["stage"] = "CLOSED"
        rc = 0
    except Bug0FoodLoopDevCompleted:
        pass
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
    parser.add_argument("--completed-l0-dev", action="store_true")
    parser.add_argument("--bug0-eat-shadow", action="store_true")
    parser.add_argument("--bug0-food-loop-dev", action="store_true")
    parser.add_argument("--bug0-food-refusal-dev", action="store_true")
    parser.add_argument("--bug0-unified-survival-dev", action="store_true")
    parser.add_argument("--bug0-attack-dev", action="store_true")
    parser.add_argument("--bug0-attack-health-dev", action="store_true")
    parser.add_argument("--bug0-rest-dev", action="store_true")
    parser.add_argument("--bug0-attack-rest-dev", action="store_true")
    parser.add_argument("--bug0-p1-paper-dev", action="store_true")
    parser.add_argument("--bug0-p1-prospective-rest-dev", action="store_true")
    parser.add_argument("--bug0-p1-margin-dev", action="store_true")
    parser.add_argument("--worldbody-dev", action="store_true")
    parser.add_argument("--worldbody-retest-dev", action="store_true")
    parser.add_argument("--unified-c1-dev", action="store_true")
    parser.add_argument("--unified-c1-two-intents-dev", action="store_true")
    parser.add_argument("--unified-c1-journal-dev", action="store_true")
    parser.add_argument("--unified-c1-physical-fence-dev", action="store_true")
    args = parser.parse_args()
    return asyncio.run(qualify(
        args.report, args.server_log, completed_l0_dev=args.completed_l0_dev,
        bug0_eat_shadow=args.bug0_eat_shadow,
        bug0_food_loop_dev=args.bug0_food_loop_dev,
        bug0_food_refusal_dev=args.bug0_food_refusal_dev,
        bug0_unified_survival_dev=args.bug0_unified_survival_dev,
        bug0_attack_dev=args.bug0_attack_dev,
        bug0_attack_health_dev=args.bug0_attack_health_dev,
        bug0_rest_dev=args.bug0_rest_dev,
        bug0_attack_rest_dev=args.bug0_attack_rest_dev,
        bug0_p1_paper_dev=args.bug0_p1_paper_dev,
        bug0_p1_prospective_rest_dev=args.bug0_p1_prospective_rest_dev,
        bug0_p1_margin_dev=args.bug0_p1_margin_dev,
        worldbody_dev=args.worldbody_dev,
        worldbody_retest_dev=args.worldbody_retest_dev,
        unified_c1_dev=args.unified_c1_dev,
        unified_c1_two_intents_dev=args.unified_c1_two_intents_dev,
        unified_c1_journal_dev=args.unified_c1_journal_dev,
        unified_c1_physical_fence_dev=args.unified_c1_physical_fence_dev,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
