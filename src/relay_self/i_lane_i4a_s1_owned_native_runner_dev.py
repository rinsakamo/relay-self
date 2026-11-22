"""U18: execute first PLACE with the ORIGINAL resident B, Stage26 L1 and Stage27.

No new Owner, inference backend, ActionPort, Native writer, WAL or motor.
The outer disposable-World runner opens one original Native transcript before
calling this entry and retains the same process/transcript for U15 S2.
"""
from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.process_session import MineflayerProcessSession
from experiments.cognitive_physical_executor_dev import PhysicalDevGrant
from experiments.cognitive_physical_place_move_issue_dev import (
    Stage27PlaceMoveReceipt,
    issue_selected_place_move_dev,
)
from relay_self.checkpointed_cognitive_runtime_dev import StagedRecoveredCognition
from relay_self.i_lane_i4a_s2_owned_native_runner_dev import (
    I4AS2OwnedNativeHold,
    _adopt_u17_original_probe,
    _probe_from_original_owned_native,
    require_i4a_s2_owned_native_source_audit,
)
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.p0d_stage26_gemma_l1_dev import (
    finish_restored_preset_l1,
    prepare_restored_preset_l1,
    submit_restored_preset_l1,
)
from relay_self.p0d_stage27_owned_move_intent_dev import (
    begin_stage27_owned_move_intent,
)
from relay_self.p0d_stage27b_place_motion_dev import resolve_stage27_place_motion
from relay_self.p0d_stage27c_l0_place_proposal_dev import (
    propose_stage27c_original_place_move,
)
from relay_self.p0d_stage27h_bounded_l0_move_dev import Stage27hBoundedMoveLoop
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalActionBinding, PhysicalCapability
from relay_self.provenance import Provenance
from relay_self.q4_place_abort_dev import (
    Q4DevMotorBoundary,
    Q4DevOperatorPermit,
    run_q4_dev_place_with_motor_deadline,
)


@dataclass(frozen=True, slots=True)
class I4AS1OwnedNativeSettled:
    loop: Stage27hBoundedMoveLoop
    receipt: Stage27PlaceMoveReceipt
    forward_ms: float
    host_ms: float


async def issue_original_s1_place_on_owned_native_dev(
    *, bridge: OwnedResidentPhysicalBridge,
    restored: StagedRecoveredCognition,
    native_stdout_path: Path,
    grant_for_action: Callable[
        [PhysicalActionBinding], tuple[PhysicalDevGrant, PhysicalDevGrant],
    ],
    operator_permit: Q4DevOperatorPermit,
    provenance: Provenance,
    inject_stop_failure: bool = False,
) -> I4AS1OwnedNativeSettled:
    """Real Original B: Native probe -> actual L1 -> Intent/Skill -> PLACE S1.

    This is an actual call chain, not a caller-injected S1/ACK/Owner receipt.
    The model is the original bounded lane; the scoped operator grant labels
    never authorize an Action without the existing physical lease and WAL.
    """
    if (
        type(bridge) is not OwnedResidentPhysicalBridge
        or not isinstance(restored, StagedRecoveredCognition)
        or restored.self_id != "B"
        or not isinstance(native_stdout_path, Path)
        or not native_stdout_path.is_absolute()
        or not callable(grant_for_action)
        or not isinstance(operator_permit, Q4DevOperatorPermit)
        or not isinstance(provenance, Provenance)
        or type(inject_stop_failure) is not bool
    ):
        raise I4AS2OwnedNativeHold("real Original B restored source/DEV grant required")
    owner = bridge.owners.get("B")
    session = bridge.sessions.get("B")
    lane = bridge.inference_lane
    physical = bridge.physical
    if (
        type(session) is not MineflayerProcessSession
        or owner is None or lane is None or bridge.cognitive_work is None
        or owner.cohort is not bridge.cognitive_work
        or lane.cognitive_work is not bridge.cognitive_work
        or session.process_returncode is not None
        or session.owned_child_pid is None
        or not session.bounded_place_dev_mode
        or owner.native_session_id != session.started.session_id
        or physical.current_native_sessions.get("B") != session.started.session_id
        or physical.resident_states.get("B") != "ONLINE"
        or physical.observation_only
        or physical._original_place_s1.get("B") is None
        or not callable(session._atomic_effect_sender)
        or owner.intent.current_intent is not None
        or owner.supervisor.recorded_actions
        or operator_permit.self_id != "B"
        or operator_permit.native_session_id != session.started.session_id
    ):
        raise I4AS2OwnedNativeHold("Original B S1 issuer/World Session unqualified")
    bridge._check_world()
    require_i4a_s2_owned_native_source_audit(session, native_stdout_path)
    journal = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id="B",
    )
    journal.require_clear()
    if journal.records:
        raise I4AS2OwnedNativeHold("S1 cannot resume any prior physical Action")

    # Genuine original model, never a substitute fixed number. Fresh WorldBody
    # after model output, and Stage26's real HTTP/slot provenance are required.
    first = await _probe_from_original_owned_native(session)
    _adopt_u17_original_probe(bridge, owner, first)
    prepared = prepare_restored_preset_l1(
        self_id="B", restored=restored, first=first,
        owner=owner, lane=lane,
    )
    ticket = submit_restored_preset_l1(prepared, lane=lane)
    witness, current = await finish_restored_preset_l1(
        prepared, ticket=ticket, lane=lane,
        fresh_probe=lambda: _probe_from_original_owned_native(session),
    )
    _adopt_u17_original_probe(bridge, owner, current)
    at_ns = time.monotonic_ns()
    handoff = begin_stage27_owned_move_intent(
        prepared, ticket=ticket, witness=witness, refreshed=current,
        lane=lane, physical=physical, actor_self_id="B",
        at_ns=at_ns, provenance=provenance,
    )
    loop = Stage27hBoundedMoveLoop(
        prepared, handoff, owner=owner, physical=physical,
        world_epoch=prepared.world_epoch, start_ns=at_ns,
    )
    status = loop.pre_action(current, now_ns=time.monotonic_ns())
    if status.status != "L0_CONTINUE_MOVE":
        raise I4AS2OwnedNativeHold("actual original L1 MOVE did not yield S1 Action")
    motion = resolve_stage27_place_motion(
        prepared, handoff, current, owner=owner,
        physical=physical, world_epoch=prepared.world_epoch,
    )
    l0 = propose_stage27c_original_place_move(
        prepared, handoff, motion, current, owner=owner,
        physical=physical, world_epoch=prepared.world_epoch,
        capability=PhysicalCapability("MOVE", 1, "locomotion", "DESTINATION", True),
        at_ns=time.monotonic_ns(), provenance=provenance,
    )
    # Pessimistically reserve actual STOP observation budget before WAL
    # PREPARED. An uncertain action can never release these slots or retry.
    loop.reserve_settling_observations(source_probe=current)
    grants = grant_for_action(l0.proposal.binding)
    if (
        type(grants) is not tuple or len(grants) != 2
        or not all(isinstance(g, PhysicalDevGrant) for g in grants)
    ):
        raise I4AS2OwnedNativeHold("two original scoped S1 operator labels required")
    propose_grant, issue_grant = grants
    if inject_stop_failure:
        # Same original owned Native adapter; no other STOP or effect sender.
        # Failure occurs only when the Stage27 executor reaches its first STOP
        # after genuine START ACK. The existing Q4 watchdog owns termination.
        session.arm_q4_stop_failure_once_dev(l0.action_id + "-stop")
    start_stop_ms: list[tuple[float, float]] = []

    async def original_issue(motor: Q4DevMotorBoundary) -> Stage27PlaceMoveReceipt:
        with physical.lease(
            self_id="B", native_session_id=session.started.session_id,
            action_id=l0.action_id, effect_family="MOVE_PLACE",
        ):
            def bind_children(parent: str) -> None:
                physical.bind_original_place_children(
                    bridge=bridge, self_id="B",
                    native_session_id=session.started.session_id,
                    lease_action_id=l0.action_id,
                    parent_action_id=parent, journal=journal,
                )

            receipt = await issue_selected_place_move_dev(
                session, proposal=l0.proposal, l0=l0, prepared=prepared,
                handoff=handoff, motion=motion, previous_probe=first,
                current_probe=current, owner=owner, physical=physical,
                propose_grant=propose_grant, issue_grant=issue_grant,
                journal=journal, at_ns=time.monotonic_ns(),
                provenance=provenance, grant_real_world=True,
                acknowledge_dev_unverified_principal=True,
                evidence_timeout_s=12.0, pulse_seconds=0.15,
                bind_native_children=bind_children,
                allow_prior_terminal_place_actions=False,
                settlement_probe_limit=60, precision_gait="WALK",
                motor_boundary=motor,
            )
            start_stop_ms.append(motor.original_motor_times_ms())
            return receipt

    result = await run_q4_dev_place_with_motor_deadline(
        bridge=bridge, self_id="B", action_id=l0.action_id,
        issue_original=original_issue, operator_permit=operator_permit,
    )
    if len(start_stop_ms) != 1:
        raise I4AS2OwnedNativeHold("original S1 monotonic motor source missing")
    forward_ms, host_ms = start_stop_ms[0]
    if (
        not all(math.isfinite(x) for x in (forward_ms, host_ms))
        or not 0 <= forward_ms <= 800
        or not forward_ms <= host_ms <= 2000
    ):
        raise I4AS2OwnedNativeHold("original S1 bounded forward/STOP time invalid")
    loop.observe_terminal_action(
        result, source_probe=current, now_ns=time.monotonic_ns(),
    )
    if loop.terminal_status is None:
        loop.yield_one_settled_action_for_q4_dev()
    return I4AS1OwnedNativeSettled(loop, result, forward_ms, host_ms)
