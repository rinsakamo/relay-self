"""I4a DEV-only *synthetic*: first S2 original issuer WAL PREPARED reservation.

Uses the EXISTING original begin_physical_issue_dev; no new Action author,
issuer, WAL, child permission or native effect. This is deliberately a
one-shot, terminal-unresolved *test* bridge, NOT a real-World motor runner:
without an original LOOK/start/STOP+settlement driver, PREPARED must HOLD.
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerObservation
from experiments.cognitive_physical_executor_dev import (
    PhysicalDevGrant,
    begin_physical_issue_dev,
    check_dev_issuer_preflight,
    check_physical_source_window,
)
from relay_self.action import ActionState
from relay_self.i_lane_i4a_s2_first_move_proposal_dev import I4AS2FirstMoveProposal
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane


class I4AS2FirstReservationHold(ValueError):
    """Original physical WAL / S2 owner / independent DEV grant not qualified."""


def require_i4a_offline_scripted_native(
    session: MineflayerProcessSession,
) -> None:
    """Reject process-backed native sessions from the synthetic S2 API.

    This deliberately supports the existing scripted Mineflayer subclasses
    used by CPU/offline tests. A real MineflayerProcessSession, including a
    subclass carrying a live process/decoder, has NO authority here. A
    future real trial must use a separate source-qualified real runner with
    independently verified Paper/world evidence, not this test adapter.
    """
    if not isinstance(session, MineflayerProcessSession) or (
        type(session) is MineflayerProcessSession
    ):
        raise I4AS2FirstReservationHold(
            "S2 synthetic issuer rejects process-backed/native live session"
        )
    # A subclass may keep runtime resources in slots or class attributes,
    # not its instance __dict__. Do not mistake those for a scripted source.
    # This guards accidental real-process routing, not arbitrary forged Python.
    missing = object()
    try:
        own_fields = getattr(session, "__dict__", {})
        process_backed = (
            not isinstance(own_fields, dict)
            or "_process" in own_fields
            or "_decoder" in own_fields
            or getattr(session, "_process", missing) is not missing
            or getattr(session, "_decoder", missing) is not missing
            or getattr(session, "_effect_admission", None) is not None
        )
    except Exception:
        # Descriptor inspection failure must not grant synthetic admission.
        process_backed = True
    if process_backed:
        raise I4AS2FirstReservationHold(
            "S2 synthetic issuer rejects process-backed/native live session"
        )


@dataclass(frozen=True, slots=True)
class I4AS2SyntheticPrepared:
    """Evidence that the first new S2 Action is *unresolved*, not executed."""

    action_id: str
    self_id: str
    old_prefix_count: int
    old_prefix_sha256: str
    prepared_wal_sha256: str
    prepared_row_count: int
    new_skill_execution_id: str
    new_intent_id: str
    parent_action_state: str = "ISSUED_NO_NATIVE_EFFECT"
    status: str = "PREPARED_UNRESOLVED"
    native_effect_issued: bool = False
    issue_lease_active: bool = False
    resumption_authorized: bool = False


def reserve_s2_first_original_move_synthetic_dev(
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
    retained_lease_stack: ExitStack | None = None,
) -> I4AS2SyntheticPrepared:
    """One synchronous Owner→admission lease→canonical WAL PREPARED transition.

    This must never be called as a real-world Action runner. No native IO is
    performed; the new WAL remains unresolved and is NOT recoverable/retriable
    by any path in this PR. Independent scoped DEV grants remain mandatory.
    """
    # Fail before any WAL lock, lease or supervisor issue for a real process.
    require_i4a_offline_scripted_native(session)
    if (
        not isinstance(candidate, I4AS2FirstMoveProposal)
        or not isinstance(physical, PhysicalIssueAdmission)
        or not isinstance(lane, ResidentLlamaInferenceLane)
        or not isinstance(previous_probe, MineflayerObservation)
        or not isinstance(provenance, Provenance)
        or type(at_ns) is not int or at_ns < 0
        or candidate.physical_authorized or candidate.physical_issued
        or candidate.wal_modified or candidate.target_clearance_attested
        or candidate.proposal.physical_authorized
        or candidate.proposal.physical_issued
        or candidate.proposal.preissue_persisted
        or candidate.action_id != candidate.proposal.binding.action_id
        or candidate.proposal.binding.skill_execution_id
        != candidate.boundary.new_skill_id
        or candidate.proposal.binding.intent_id != candidate.boundary.new_intent_id
        or session.started.session_id != candidate.boundary.native_session_id
        or candidate.source_probe.session_id != session.started.session_id
    ):
        raise I4AS2FirstReservationHold("original non-issuing S2 candidate invalid")
    owner = candidate.boundary.owner
    boundary = candidate.boundary
    with physical.original_i4a_s2_first_wal_window(
        owner=owner, boundary=boundary, lane=lane, action_id=candidate.action_id,
        retained_lease_stack=retained_lease_stack,
    ):
        journal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        journal.require_clear()
        if (
            journal.digest != boundary.prefix_digest
            or len(journal.records) != boundary.prefix_count
            or any(
                row["action_id"] != old_id
                for row, old_id in zip(
                    journal.records, boundary.prefix_action_ids, strict=True,
                )
            )
            or owner.supervisor.open_actions
        ):
            raise I4AS2FirstReservationHold("original S1 historical WAL not certified")
        check_dev_issuer_preflight(
            session, candidate.proposal, intent_owner=owner.intent,
            skill_execution=owner.skills[boundary.new_skill_id],
            supervisor=owner.supervisor, journal=journal,
            at_ns=at_ns, provenance=provenance,
            grant_real_world=grant_real_world,
            acknowledge_dev_unverified_principal=acknowledge_dev_unverified_principal,
            evidence_timeout_s=evidence_timeout_s,
            refusal=I4AS2FirstReservationHold,
        )
        check_physical_source_window(
            candidate.proposal, previous_probe, candidate.source_probe,
            capability="MOVE", target_kind="DESTINATION",
            refusal=I4AS2FirstReservationHold,
        )
        # Re-check the original immutable cursor. The proposal itself is
        # not a grant. All mutations below are the ORIGINAL issuer's code.
        candidate.interpreter._require_cursor(
            candidate.cursor, at_ns=at_ns,
            intent_owner=owner.intent,
            skill_execution=owner.skills[boundary.new_skill_id],
        )
        # Consume the parent identity before the canonical WAL CAS. If the
        # original issuer later fails, the conservative result is STOP/HOLD,
        # not a new lease with the same PREPARED parent.
        physical.consume_original_i4a_s2_action_once(
            owner=owner, boundary=boundary, action_id=candidate.action_id,
        )
        begin_physical_issue_dev(
            session, capability="MOVE", proposal=candidate.proposal,
            current_probe=candidate.source_probe,
            propose_grant=propose_grant, issue_grant=issue_grant,
            intent_owner=owner.intent,
            skill_execution=owner.skills[boundary.new_skill_id],
            supervisor=owner.supervisor, journal=journal, at_ns=at_ns,
            refusal=I4AS2FirstReservationHold,
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
            or rows[-1]["skill_execution_id"] != boundary.new_skill_id
            or rows[-1]["intent_id"] != boundary.new_intent_id
            or not journal.unresolved
            or owner.supervisor.get(candidate.action_id).state is not ActionState.ISSUED
        ):
            # A partial error after PREPARED does not roll back WAL or license
            # another physical effect. Preserve original uncertainty.
            raise I4AS2FirstReservationHold("original S2 journal issue uncertain")
        # Deliberately NO bind_native_children. The original lease ends after
        # this synchronous transaction; no effect can be sent by this helper.
        return I4AS2SyntheticPrepared(
            candidate.action_id, owner.self_id, boundary.prefix_count,
            boundary.prefix_digest, journal.digest, len(rows),
            boundary.new_skill_id, boundary.new_intent_id,
            issue_lease_active=retained_lease_stack is not None,
        )
