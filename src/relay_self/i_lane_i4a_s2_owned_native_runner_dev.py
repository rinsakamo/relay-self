"""U15: Original B-owned Q4 S2 PLACE runner with an actual Native process.

This runner is NOT invoked by restored B/login and does NOT authorize a
World, an L1 decision, Paper causation, second action or QUAL/SCIENCE. Only
the existing Owner and existing PhysicalActionJournal may issue the parent;
the existing PhysicalIssueAdmission binds LOOK/START/STOP via its original
atomic Native sender. All physical side effects require explicit one-use
operator DEV opt-in and a live, bounded bridge-owned MineflayerProcessSession.
"""
from __future__ import annotations

import asyncio
import math
import os
import stat
import time
import uuid
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
from relay_self.i_lane_i4a_live_wal_anchor_dev import (
    finish_and_anchor_live_stage27_run,
    qualify_live_s2_readiness,
)
from relay_self.i_lane_i4a_s1_source_capture_dev import (
    I4AS1SourceCapture,
    freeze_original_s1_wal,
)
from relay_self.i_lane_i4a_s2_first_move_proposal_dev import (
    I4AS2FirstMoveProposal,
    propose_s2_first_original_place_move,
)
from relay_self.i_lane_i4a_s2_first_physical_reservation_dev import (
    I4AS2FirstReservationHold,
)
from relay_self.i_lane_i4a_s2_owner_handoff_dev import (
    begin_live_s2_owner_handoff,
    finish_live_s2_l1,
    prepare_live_s2_l1,
    submit_live_s2_l1,
)
from relay_self.i_lane_i4a_s2_run_boundary_dev import (
    attest_i4a_s2_empty_run_boundary,
)
from relay_self.owned_paper_world_dev import PaperTickReceipt
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.p0d_stage27_owned_move_intent_dev import Stage27OwnedMoveIntent
from relay_self.p0d_stage27c_l0_place_proposal_dev import Stage27L0PlaceProposal
from relay_self.p0d_stage27h_bounded_l0_move_dev import Stage27hBoundedMoveLoop
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalCapability
from relay_self.provenance import Provenance
from relay_self.q4_place_abort_dev import (
    Q4DevMotorBoundary,
    Q4DevOperatorPermit,
    run_q4_dev_place_with_motor_deadline,
)
from relay_self.q4_place_repeat_source_dev import Q4PlaceTerminalReadback
from relay_self.skill import SkillState


class I4AS2OwnedNativeHold(RuntimeError):
    """Original S2 / WAL / Native is not qualified for Q4 DEV movement."""


def require_i4a_s2_owned_native_source_audit(
    session: MineflayerProcessSession, path: Path,
) -> None:
    """Confirm the SINGLE original raw stdout capture spans all Q4 Actions.

    The parent isolated-World runner starts this capture once before first
    S2 Action and freezes it after the *second* Action (or emergency abort).
    Refuse missing/symlink/swapped files and detached child FD. No data from
    a caller-supplied JSON/receipt is sufficient for this check.
    """
    if (
        type(session) is not MineflayerProcessSession
        or not isinstance(path, Path) or not path.is_absolute()
        or path.is_symlink() or not path.is_file()
        or not path.parent.is_dir() or path.parent.is_symlink()
        or session._raw_source_audit_finished
        or type(session._raw_source_audit_fd) is not int
    ):
        raise I4AS2OwnedNativeHold("one original active Native stdout audit required")
    try:
        descriptor = os.fstat(session._raw_source_audit_fd)
        original = path.stat(follow_symlinks=False)
    except (OSError, ValueError) as exc:
        raise I4AS2OwnedNativeHold("original Native stdout file descriptor lost") from exc
    if (
        not stat.S_ISREG(descriptor.st_mode)
        or descriptor.st_dev != original.st_dev
        or descriptor.st_ino != original.st_ino
        or descriptor.st_nlink != 1
        or original.st_nlink != 1
        or descriptor.st_mode & 0o777 != 0o600
    ):
        raise I4AS2OwnedNativeHold(
            "Native stdout audit file swapped or no longer exclusive"
        )


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

    The parent World harness MUST start one exclusive original Native stdout
    audit before the first Action and keep that SAME capture active through
    both Q4 Actions; this runner checks its actual OS file descriptor.
    The harness freezes/fsyncs the audit after both Actions or an abort.
    Original Native output alone cannot authenticate Paper source. Native
    stdin/Paper/process exit/manifest remain caller-owned evidence tasks.
    Any exception after work creation enters original owned abort.
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

    require_i4a_s2_owned_native_source_audit(
        session, native_stdout_path,
    )

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

    # The OUTER same-World harness owns open/finalize of this single stdout
    # transcript; do NOT end it after Action 1, since Action 2 must reuse
    # this exact original Node/Paper session. If the Action aborts, the outer
    # harness must finally close/fsync + hash this unchanged raw capture.
    return await run_q4_dev_place_with_motor_deadline(
        bridge=bridge, self_id=self_id, action_id=candidate.action_id,
        issue_original=original_issue,
        operator_permit=operator_permit,
    )


async def _probe_from_original_owned_native(
    session: MineflayerProcessSession,
) -> MineflayerObservation:
    """Observe via actual original Native stdin/stdout; no injected probe."""
    if (
        type(session) is not MineflayerProcessSession
        or session.process_returncode is not None
        or session._raw_source_audit_fd is None
        or session._raw_stdin_audit_fd is None
    ):
        raise I4AS2OwnedNativeHold("continuous original Native observation not available")
    request_id = "u17-q4-probe-" + uuid.uuid4().hex
    await asyncio.wait_for(session.send_observe(request_id), timeout=1.5)
    for _ in range(16):
        event = await asyncio.wait_for(session.receive(), timeout=1.5)
        if isinstance(event, MineflayerObservation) and (
            event.kind == "probe" and event.request_id == request_id
        ):
            return event
    raise I4AS2OwnedNativeHold("bounded original Native CURRENT did not arrive")


def _adopt_u17_original_probe(
    bridge: OwnedResidentPhysicalBridge,
    owner, observation: MineflayerObservation,
) -> None:
    """Use the EXISTING B Owner mutations, not a second WorldBody setter."""
    native_session = bridge.sessions[owner.self_id].started.session_id
    if (
        observation.session_id != native_session
        or observation.snapshot.time is None
        or observation.kind != "probe"
        or not observation.request_id
    ):
        raise I4AS2OwnedNativeHold("unbound current original Native observation")
    tick = (
        observation.snapshot.time.day * 24000
        + observation.snapshot.time.time_of_day
    )
    owner.observe_world_tick(session_id=native_session, world_tick=tick)
    owner.accept_rejoined_worldbody(
        observation, request_id=observation.request_id,
    )


async def continue_original_s1_to_s2_owned_native_dev(
    *, bridge: OwnedResidentPhysicalBridge,
    s1_loop: Stage27hBoundedMoveLoop,
    s1_receipt: Stage27PlaceMoveReceipt,
    paper_stop: PaperTickReceipt,
    paper_first: PaperTickReceipt,
    paper_settled: PaperTickReceipt,
    native_stdout_path: Path,
    evidence_dir: Path,
    propose_grant: PhysicalDevGrant,
    issue_grant: PhysicalDevGrant,
    operator_permit: Q4DevOperatorPermit,
    provenance: Provenance,
    s1_forward_ms: float,
    s1_host_ms: float,
) -> tuple[I4AS1SourceCapture, Stage27PlaceMoveReceipt]:
    """U17: actual S1 terminal -> original B fresh L1 -> original S2 motor.

    The S1 loop MUST already have been executed by the original Stage27h
    physical issuer and returned the actual terminal receipt in this same
    bridge-owned Native process. No callback may inject a synthetic L1,
    Native or Owner. Original WAL remains the sole physical ledger.

    The outer disposable World harness owns opening ONE stdout and ONE stdin
    capture before S1, capturing actual Paper positions/host motor timestamps,
    and freezing both after the second Action or original owned abort.
    This function does not attest that those external World producers ran.
    """
    if (
        type(bridge) is not OwnedResidentPhysicalBridge
        or not isinstance(s1_loop, Stage27hBoundedMoveLoop)
        or not isinstance(s1_receipt, Stage27PlaceMoveReceipt)
        or not all(isinstance(x, PaperTickReceipt) for x in (
            paper_stop, paper_first, paper_settled,
        ))
        or not isinstance(native_stdout_path, Path)
        or not isinstance(evidence_dir, Path)
        or not evidence_dir.is_absolute() or not evidence_dir.is_dir()
        or not isinstance(propose_grant, PhysicalDevGrant)
        or not isinstance(issue_grant, PhysicalDevGrant)
        or not isinstance(operator_permit, Q4DevOperatorPermit)
        or not isinstance(provenance, Provenance)
        or type(s1_forward_ms) not in (int, float)
        or type(s1_host_ms) not in (int, float)
        or not math.isfinite(s1_forward_ms) or not math.isfinite(s1_host_ms)
        or not 0 <= s1_forward_ms <= 800
        or not s1_forward_ms <= s1_host_ms <= 2000
    ):
        raise I4AS2OwnedNativeHold("real original S1-to-S2 input not qualified")
    owner = s1_loop.owner
    self_id = owner.self_id
    session = bridge.sessions.get(self_id)
    lane = bridge.inference_lane
    if (
        lane is None or bridge.cognitive_work is None
        or s1_loop.physical is not bridge.physical
        or bridge.owners.get(self_id) is not owner
        or owner.cohort is not bridge.cognitive_work
        or type(session) is not MineflayerProcessSession
        or session.started.session_id != s1_loop.prepared.native_session
        or session.process_returncode is not None
        or s1_loop.action_count != 1
        or s1_loop.terminal_status is None
        or s1_loop.last_action_id != s1_receipt.action_id
        or s1_loop.last_wal_digest != s1_receipt.journal_sha256
        or s1_receipt.journal_status != "NATIVE_PLACE_MOVE_SETTLED"
        or s1_receipt.native_session_id != session.started.session_id
        or not session.bounded_place_dev_mode
        or not isinstance(session._raw_stdin_audit_path, Path)
    ):
        raise I4AS2OwnedNativeHold("S1 was not original live settled single MOVE")
    require_i4a_s2_owned_native_source_audit(
        session, native_stdout_path,
    )
    original_s1_proof = Q4PlaceTerminalReadback(
        s1_receipt.look_ack, s1_receipt.start_ack, s1_receipt.stop_ack,
        s1_receipt.initial_stop_probe, s1_receipt.first_stable_probe,
        s1_receipt.settled_probe,
        paper_stop, paper_first, paper_settled,
        float(s1_forward_ms), float(s1_host_ms),
    )
    # A genuine prior S1 terminal Owner transition precedes any fresh L1.
    # Do not derive successful Goal completion from the MOVE displacement.
    anchor = finish_and_anchor_live_stage27_run(
        s1_loop, lane=lane, outcome=SkillState.CANCELLED,
        reason="U17 bounded single S1 MOVE: evaluate fresh intent",
        at_ns=time.monotonic_ns(), provenance=provenance,
    )
    capture = freeze_original_s1_wal(
        owner, physical=bridge.physical, lane=lane,
        anchor=anchor, evidence_dir=evidence_dir,
    )
    bridge.physical.rearm_original_place_after_q4_owned_native_dev(
        bridge=bridge, self_id=self_id, evidence=original_s1_proof,
        native_stdout_path=native_stdout_path,
    )
    first = await _probe_from_original_owned_native(session)
    _adopt_u17_original_probe(bridge, owner, first)
    readiness = qualify_live_s2_readiness(
        owner, physical=bridge.physical, lane=lane,
        anchor=anchor, first_probe=first,
    )
    prepared = prepare_live_s2_l1(
        owner, physical=bridge.physical, lane=lane,
        readiness=readiness, first_probe=first,
    )
    ticket = submit_live_s2_l1(prepared)
    witness = await finish_live_s2_l1(
        prepared, ticket=ticket,
        post_model_probe=lambda: _probe_from_original_owned_native(session),
    )
    _adopt_u17_original_probe(bridge, owner, witness.after_probe)
    handoff = begin_live_s2_owner_handoff(
        witness, at_ns=time.monotonic_ns(), provenance=provenance,
    )
    boundary = attest_i4a_s2_empty_run_boundary(witness, handoff)
    candidate = propose_s2_first_original_place_move(
        boundary, witness, physical=bridge.physical, lane=lane,
        native=witness.after_probe,
        capability=PhysicalCapability("MOVE", 1, "locomotion", "DESTINATION", True),
        at_ns=time.monotonic_ns(), provenance=provenance,
    )
    s2_receipt = await issue_i4a_s2_place_on_original_owned_native_dev(
        bridge=bridge, candidate=candidate, previous_probe=first,
        propose_grant=propose_grant, issue_grant=issue_grant,
        operator_permit=operator_permit, native_stdout_path=native_stdout_path,
        at_ns=time.monotonic_ns(), provenance=provenance,
        grant_real_world=True,
        acknowledge_dev_unverified_principal=True,
        pulse_seconds=0.15, settlement_probe_limit=60,
    )
    return capture, s2_receipt
