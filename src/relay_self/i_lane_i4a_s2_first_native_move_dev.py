"""I4a DEV: first S2 PLACE using original prepared/native/settling issuer.

Synthetic-only evidence: no real World/Gemma or C T2. An earlier PREPARED
is never resumed. Same original lease spans this fresh WAL reserve and native.
"""
from __future__ import annotations

from contextlib import ExitStack

from experiments.cognitive_physical_place_move_issue_dev import (
    Stage27PlaceMoveReceipt,
    complete_prepared_place_move_dev,
)

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerObservation
from experiments.cognitive_physical_executor_dev import PhysicalDevGrant
from relay_self.i_lane_i4a_s2_first_move_proposal_dev import I4AS2FirstMoveProposal
from relay_self.i_lane_i4a_s2_first_physical_reservation_dev import (
    I4AS2FirstReservationHold,
    require_i4a_offline_scripted_native,
    reserve_s2_first_original_move_synthetic_dev,
)
from relay_self.p0d_stage27_owned_move_intent_dev import Stage27OwnedMoveIntent
from relay_self.p0d_stage27c_l0_place_proposal_dev import Stage27L0PlaceProposal
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane


async def issue_s2_first_original_place_move_synthetic_dev(
    session: MineflayerProcessSession,
    candidate: I4AS2FirstMoveProposal,
    *,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    previous_probe: MineflayerObservation,
    propose_grant: PhysicalDevGrant,
    issue_grant: PhysicalDevGrant,
    at_ns: int,
    provenance: Provenance,
    grant_real_world: bool,
    acknowledge_dev_unverified_principal: bool,
    evidence_timeout_s: float = 1.5,
    pulse_seconds: float = 0.15,
    settlement_probe_limit: int | None = None,
) -> Stage27PlaceMoveReceipt:
    """Reserve once, run original native effects, then close original WAL.

    The cognitive and physical admission locks are released before awaits.
    The original physical lease is retained until STOP/settling finishes.
    """
    require_i4a_offline_scripted_native(session)
    if (
        not isinstance(candidate, I4AS2FirstMoveProposal)
        or candidate.physical_authorized or candidate.physical_issued
        or candidate.wal_modified or candidate.target_clearance_attested
    ):
        raise I4AS2FirstReservationHold("fresh original S2 proposal required")
    boundary = candidate.boundary
    owner = boundary.owner
    with ExitStack() as lease_stack:
        prepared = reserve_s2_first_original_move_synthetic_dev(
            session, candidate, physical=physical, lane=lane,
            previous_probe=previous_probe, propose_grant=propose_grant,
            issue_grant=issue_grant, at_ns=at_ns, provenance=provenance,
            grant_real_world=grant_real_world,
            acknowledge_dev_unverified_principal=acknowledge_dev_unverified_principal,
            evidence_timeout_s=evidence_timeout_s,
            retained_lease_stack=lease_stack,
        )
        if (
            not prepared.issue_lease_active
            or prepared.action_id != candidate.action_id
            or physical.active_action_ids != (candidate.action_id,)
        ):
            raise I4AS2FirstReservationHold("original S2 native lease not retained")
        journal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        if (
            journal.digest != prepared.prepared_wal_sha256
            or not journal.unresolved
            or len(journal.records) != boundary.prefix_count + 1
        ):
            raise I4AS2FirstReservationHold("fsynced S2 parent changed after PREPARED")
        l0 = Stage27L0PlaceProposal(
            owner.self_id, boundary.world_epoch, boundary.native_session_id,
            candidate.source_probe.seq, candidate.invocation_ref,
            boundary.preset_ref, candidate.motion.target_contract_ref,
            boundary.new_intent_id, boundary.new_skill_id,
            candidate.action_id, candidate.ir, candidate.cursor,
            candidate.interpreter, candidate.proposal,
        )
        handoff = Stage27OwnedMoveIntent(
            owner.self_id, boundary.native_session_id, boundary.world_epoch,
            boundary.decision_request_id, "1", candidate.source_probe.seq,
            boundary.new_intent_id, boundary.new_skill_id,
            boundary.invocation_ref, boundary.preset_ref, boundary.target_ref,
            "DESTINATION",
        )

        def bind_child(parent: str) -> None:
            physical.bind_native_children(
                self_id=owner.self_id,
                native_session_id=boundary.native_session_id,
                lease_action_id=candidate.action_id,
                parent_action_id=parent, family="MOVE_PLACE",
                journal=journal,
            )

        return await complete_prepared_place_move_dev(
            session, proposal=candidate.proposal,
            l0=l0, handoff=handoff, motion=candidate.motion,
            current_probe=candidate.source_probe, owner=owner,
            journal=journal, invocation=candidate.ir.invocation,
            at_ns=at_ns, evidence_timeout_s=evidence_timeout_s,
            pulse_seconds=pulse_seconds, bind_native_children=bind_child,
            pre_native_evidence=None,
            settlement_probe_limit=settlement_probe_limit,
            precision_gait=None,
        )
