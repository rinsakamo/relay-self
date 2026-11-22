"""U15: Original B-owned Q4 S2 PLACE runner with an actual Native process.

This runner is NOT invoked by restored B/login and does NOT authorize a
World, an L1 decision, Paper causation, second action or QUAL/SCIENCE. Only
the existing Owner and existing PhysicalActionJournal may issue the parent;
the existing PhysicalIssueAdmission binds LOOK/START/STOP via its original
atomic Native sender. All physical side effects require explicit one-use
operator DEV opt-in and a live, bounded bridge-owned MineflayerProcessSession.
"""
from __future__ import annotations

import math
from contextlib import ExitStack
from pathlib import Path

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerObservation
from experiments.cognitive_physical_executor_dev import (
    PhysicalDevGrant,
    begin_physical_issue_dev,
    check_dev_issuer_preflight,
    check_physical_source_window,
)
from experiments.cognitive_physical_place_move_issue_dev import (
    Stage27PlaceMoveReceipt,
    complete_prepared_place_move_dev,
)
from relay_self.i_lane_i4a_s2_first_move_proposal_dev import I4AS2FirstMoveProposal
from relay_self.i_lane_i4a_s2_first_physical_reservation_dev import (
    I4AS2FirstReservationHold,
)
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.p0d_stage27_owned_move_intent_dev import Stage27OwnedMoveIntent
from relay_self.p0d_stage27c_l0_place_proposal_dev import Stage27L0PlaceProposal
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance
from relay_self.q4_place_abort_dev import (
    Q4DevMotorBoundary,
    Q4DevOperatorPermit,
    run_q4_dev_place_with_motor_deadline,
)


class I4AS2OwnedNativeHold(RuntimeError):
    """Original S2 / WAL / Native is not qualified for Q4 DEV movement."""


async def issue_i4a_s2_place_on_original_owned_native_dev(
    *,
    bridge: OwnedResidentPhysicalBridge,
    candidate: I4AS2FirstMoveProposal,
    previous_probe: MineflayerObservation,
    propose_grant: PhysicalDevGrant,
    issue_grant: PhysicalDevGrant,
    operator_permit: Q4DevOperatorPermit,
    native_stdout_path: Path,
    at_ns: int,
    provenance: Provenance,
    grant_real_world: bool = False,
    acknowledge_dev_unverified_principal: bool = False,
    evidence_timeout_s: float = 1.5,
    pulse_seconds: float = 0.15,
    settlement_probe_limit: int = 60,
) -> Stage27PlaceMoveReceipt:
    """Run exactly one original S2 PLACE under the existing physical issuer.

    The explicit native_stdout_path is an exclusive original Native JSONL
    capture. Its readback alone is not an authenticated Paper source. The
    caller is responsible for separately preserving original Paper events,
    host stdin and process exit, and must obtain an independent Q audit before
    claiming real Q4 World pass. Any exception after work creation is handled
    by the original bridge's Q4 stop/owned-process termination path.
    """
    if (
        not isinstance(bridge, OwnedResidentPhysicalBridge)
        or not isinstance(candidate, I4AS2FirstMoveProposal)
        or not isinstance(previous_probe, MineflayerObservation)
        or not isinstance(propose_grant, PhysicalDevGrant)
        or not isinstance(issue_grant, PhysicalDevGrant)
        or not isinstance(operator_permit, Q4DevOperatorPermit)
        or not isinstance(provenance, Provenance)
        or type(at_ns) is not int or at_ns < 0
        or type(grant_real_world) is not bool or not grant_real_world
        or type(acknowledge_dev_unverified_principal) is not bool
        or not acknowledge_dev_unverified_principal
        or type(settlement_probe_limit) is not int
        or not 16 <= settlement_probe_limit <= 256
        or type(pulse_seconds) not in (int, float)
        or not math.isfinite(pulse_seconds)
        or not 0.15 <= pulse_seconds <= 0.75
        or candidate.target_clearance_attested
        or candidate.physical_authorized or candidate.physical_issued
        or candidate.wal_modified
        or candidate.proposal.physical_authorized
        or candidate.proposal.physical_issued
        or candidate.proposal.preissue_persisted
    ):
        raise I4AS2OwnedNativeHold("original one-shot Q4 DEV candidate/grant absent")
    boundary = candidate.boundary
    owner = boundary.owner
    self_id = owner.self_id
    physical = bridge.physical
    lane = bridge.inference_lane
    session = bridge.sessions.get(self_id)
    # No user-injected Native process, subclassed scripted mock, second
    # original physical gate, imported synthetic S2 runner, or open World.
    if (
        bridge.owners.get(self_id) is not owner
        or session is None or type(session) is not MineflayerProcessSession
        or lane is None
        or physical is None or physical.observation_only
        or not physical.resident_mode or physical.closed
        or physical.current_native_sessions.get(self_id)
        != boundary.native_session_id
        or physical.resident_states.get(self_id) != "ONLINE"
        or candidate.source_probe is not owner.current_worldbody_observation
        or candidate.source_probe.session_id != boundary.native_session_id
        or previous_probe.session_id != boundary.native_session_id
        or operator_permit.self_id != self_id
        or operator_permit.native_session_id != boundary.native_session_id
        or candidate.proposal.binding.action_id != candidate.action_id
        or candidate.proposal.binding.intent_id != boundary.new_intent_id
        or candidate.proposal.binding.skill_execution_id != boundary.new_skill_id
        or candidate.source_probe.request_id != boundary.post_model_probe_id
        or candidate.source_probe.seq != boundary.post_model_probe_seq
    ):
        raise I4AS2OwnedNativeHold("real Native is not original B Owner-bound S2")
    # Only the real bridge-owned adapter can hold a live child PID and the
    # exact final-stdin atomic callback installed by original bridge.login.
    try:
        if (
            session.started.session_id != boundary.native_session_id
            or session.process_returncode is not None
            or session.owned_child_pid is None
            or not session.bounded_place_dev_mode
            or not callable(session._atomic_effect_sender)
            or not callable(session._effect_admission)
            or bridge.cognitive_work is not owner.cohort
            or lane.cognitive_work is not owner.cohort
        ):
            raise I4AS2OwnedNativeHold("original live bounded process hooks absent")
        bridge._check_world()
    except I4AS2OwnedNativeHold:
        raise
    except (AttributeError, RuntimeError, ValueError) as exc:
        raise I4AS2OwnedNativeHold("original live World/Native state unqualified") from exc

    if not isinstance(native_stdout_path, Path):
        raise I4AS2OwnedNativeHold("explicit new Native JSONL evidence path required")
    if (
        not native_stdout_path.is_absolute()
        or native_stdout_path.is_symlink()
        or not native_stdout_path.parent.is_dir()
        or native_stdout_path.parent.is_symlink()
    ):
        raise I4AS2OwnedNativeHold("fresh original Native evidence directory required")

    async def original_issue(motor: Q4DevMotorBoundary) -> Stage27PlaceMoveReceipt:
        with ExitStack() as retained_lease:
            # All steps below are the ORIGINAL participating B Owner issue
            # transaction; the corresponding native process is not injected.
            with physical.original_i4a_s2_first_wal_window(
                owner=owner, boundary=boundary, lane=lane,
                action_id=candidate.action_id,
                retained_lease_stack=retained_lease,
            ):
                journal = PhysicalActionJournal.restore(
                    owner.files.physical_wal_file, self_id=self_id,
                )
                journal.require_clear()
                if (
                    journal.digest != boundary.prefix_digest
                    or len(journal.records) != boundary.prefix_count
                    or tuple(row["action_id"] for row in journal.records)
                    != boundary.prefix_action_ids
                    or physical._original_place_s1.get(self_id) is None
                    or candidate.action_id in boundary.prefix_action_ids
                ):
                    raise I4AS2OwnedNativeHold("original S1 WAL/PLACE anchor absent")
                check_dev_issuer_preflight(
                    session, candidate.proposal, intent_owner=owner.intent,
                    skill_execution=owner.skills[boundary.new_skill_id],
                    supervisor=owner.supervisor, journal=journal, at_ns=at_ns,
                    provenance=provenance,
                    grant_real_world=grant_real_world,
                    acknowledge_dev_unverified_principal=(
                        acknowledge_dev_unverified_principal
                    ),
                    evidence_timeout_s=evidence_timeout_s,
                    refusal=I4AS2FirstReservationHold,
                )
                check_physical_source_window(
                    candidate.proposal, previous_probe, candidate.source_probe,
                    capability="MOVE", target_kind="DESTINATION",
                    refusal=I4AS2FirstReservationHold,
                )
                candidate.interpreter._require_cursor(
                    candidate.cursor, at_ns=at_ns,
                    intent_owner=owner.intent,
                    skill_execution=owner.skills[boundary.new_skill_id],
                )
                # Consumed BEFORE original durable WAL CAS. Failure means HOLD,
                # never resume an earlier PREPARED or retry this parent.
                physical.consume_original_i4a_s2_action_once(
                    owner=owner, boundary=boundary,
                    action_id=candidate.action_id,
                )
                begin_physical_issue_dev(
                    session, capability="MOVE", proposal=candidate.proposal,
                    current_probe=candidate.source_probe,
                    propose_grant=propose_grant, issue_grant=issue_grant,
                    intent_owner=owner.intent,
                    skill_execution=owner.skills[boundary.new_skill_id],
                    supervisor=owner.supervisor, journal=journal,
                    at_ns=at_ns, refusal=I4AS2FirstReservationHold,
                    place_invocation=candidate.ir.invocation,
                    place_motion=candidate.motion,
                    allow_prior_original_place_terminals=True,
                    i4a_s2_boundary=boundary, i4a_s2_owner=owner,
                    i4a_s2_physical=physical,
                )
                rows = journal.records
                if (
                    len(rows) != boundary.prefix_count + 1
                    or rows[-1]["action_id"] != candidate.action_id
                    or rows[-1]["status"] != "PREPARED_UNRESOLVED"
                    or not journal.unresolved
                ):
                    raise I4AS2OwnedNativeHold("original S2 PREPARED not sealed")

            # The same original lease extends through the async native
            # executor. Only THIS original B S1-bound method authorizes
            # LOOK/START/STOP, and the previous S1 source is reread there.
            l0 = Stage27L0PlaceProposal(
                self_id, boundary.world_epoch, boundary.native_session_id,
                candidate.source_probe.seq, candidate.invocation_ref,
                boundary.preset_ref, candidate.motion.target_contract_ref,
                boundary.new_intent_id, boundary.new_skill_id,
                candidate.action_id, candidate.ir, candidate.cursor,
                candidate.interpreter, candidate.proposal,
            )
            handoff = Stage27OwnedMoveIntent(
                self_id, boundary.native_session_id, boundary.world_epoch,
                boundary.decision_request_id, "1", candidate.source_probe.seq,
                boundary.new_intent_id, boundary.new_skill_id,
                boundary.invocation_ref, boundary.preset_ref, boundary.target_ref,
                "DESTINATION",
            )

            def bind_children(parent_action_id: str) -> None:
                physical.bind_original_place_children(
                    bridge=bridge, self_id=self_id,
                    native_session_id=boundary.native_session_id,
                    lease_action_id=candidate.action_id,
                    parent_action_id=parent_action_id, journal=journal,
                )

            return await complete_prepared_place_move_dev(
                session, proposal=candidate.proposal, l0=l0, handoff=handoff,
                motion=candidate.motion, current_probe=candidate.source_probe,
                owner=owner, journal=journal,
                invocation=candidate.ir.invocation, at_ns=at_ns,
                evidence_timeout_s=evidence_timeout_s,
                pulse_seconds=pulse_seconds,
                bind_native_children=bind_children,
                pre_native_evidence=None,
                settlement_probe_limit=settlement_probe_limit,
                precision_gait=None,
                motor_boundary=motor,
            )

    # Source custody starts before ANY original S2 Native effects, never
    # claims custody of earlier S1 or independently trusted Paper observations.
    session.start_raw_source_audit(native_stdout_path)
    try:
        return await run_q4_dev_place_with_motor_deadline(
            bridge=bridge, self_id=self_id, action_id=candidate.action_id,
            issue_original=original_issue,
            operator_permit=operator_permit,
        )
    finally:
        # Even a failed original issue retains raw Native stdout bytes.
        # If this fsync fails, the result is HOLD, never a certified PASS.
        session.finish_raw_source_audit()
