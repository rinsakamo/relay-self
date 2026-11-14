"""#843: common guarded DEV issuer envelope shared by EAT and ATTACK.

This module owns NO native WorldBody actions, food/Entity selection, skill
policy, WAL files, new Intent, or supervisor. The one existing Self-owned WAL
remains the physical authority, including restart STOP for unresolved effects.
Capability-specific preparation and consequence evidence stay at their ports.
All grants here are caller-provided DEV labels, NOT authenticated principals.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalActionBinding, PhysicalActionProposalReceipt
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution, SkillState


class PhysicalGrantStage(str, Enum):
    PROPOSE = "PROPOSE"
    ISSUE = "ISSUE"


@dataclass(frozen=True, slots=True)
class PhysicalDevGrant:
    """Scoped, unverified operator label, NOT an external authenticated grant."""

    stage: PhysicalGrantStage
    authority_id: str
    provenance: Provenance
    intent_id: str
    action_id: str
    session_id: str
    probe_seq: int
    probe_request_id: str
    selected_target_ref: str
    granted: bool


def check_physical_grants(
    binding: PhysicalActionBinding,
    propose: PhysicalDevGrant,
    issue: PhysicalDevGrant,
    *,
    refusal: type[ValueError] = ValueError,
) -> None:
    """Reject mismatched external authorization *claims*, no grants invented."""
    if (
        not isinstance(propose, PhysicalDevGrant)
        or not isinstance(issue, PhysicalDevGrant)
        or propose.stage is not PhysicalGrantStage.PROPOSE
        or issue.stage is not PhysicalGrantStage.ISSUE
        or not propose.granted or not issue.granted
        or not propose.authority_id or not issue.authority_id
        or propose.authority_id == issue.authority_id
        or not isinstance(propose.provenance, Provenance)
        or not isinstance(issue.provenance, Provenance)
        or propose.provenance == issue.provenance
        or propose.provenance.source == "mineflayer"
        or issue.provenance.source == "mineflayer"
    ):
        raise refusal("independent scoped external physical grants required")
    for grant in (propose, issue):
        if any((
            grant.intent_id != binding.intent_id,
            grant.action_id != binding.action_id,
            grant.session_id != binding.scope.world_session_id,
            grant.probe_seq != binding.native_seq,
            grant.probe_request_id != binding.native_request_id,
            grant.selected_target_ref != binding.target_ref,
        )):
            raise refusal("physical grant is foreign/stale/retargeted")


def check_physical_source_window(
    proposal: PhysicalActionProposalReceipt,
    previous: MineflayerObservation,
    current: MineflayerObservation,
    *,
    capability: str,
    target_kind: str,
    refusal: type[ValueError] = ValueError,
) -> None:
    """Common *native* contract; per-capability affordances checked separately."""
    if not isinstance(proposal, PhysicalActionProposalReceipt):
        raise refusal("physical ActionPort proposal required")
    b = proposal.binding
    if (
        proposal.proposal.state is not ActionState.PROPOSED
        or not proposal.proposal.is_current_snapshot
        or proposal.physical_authorized or proposal.physical_issued
        or proposal.preissue_persisted
        or proposal.proposal.action_id != b.action_id
        or proposal.proposal.intent_id != b.intent_id
        or proposal.proposal.skill_execution_id != b.skill_execution_id
        or b.skill_id != capability or b.skill_version != 1
        or b.capability_ref != capability or b.capability_version != 1
        or b.body_channel != "hand" or b.target_kind != target_kind
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,89}", b.action_id)
        or not isinstance(previous, MineflayerObservation)
        or not isinstance(current, MineflayerObservation)
        or previous.kind != "probe" or current.kind != "probe"
        or not previous.request_id or not current.request_id
        or previous.request_id == current.request_id
        or previous.session_id != b.scope.world_session_id
        or current.session_id != b.scope.world_session_id
        or not previous.seq < current.seq <= previous.seq + 32
        or current.seq != b.native_seq
        or current.request_id != b.native_request_id
        or current.provenance != b.native_source
    ):
        raise refusal(f"selected {capability}/native correlated window not current")


def check_dev_issuer_preflight(
    session: MineflayerProcessSession,
    proposal: PhysicalActionProposalReceipt,
    *,
    intent_owner: IntentCommitment,
    skill_execution: SkillExecution,
    supervisor: ActionSupervisor,
    journal: PhysicalActionJournal,
    at_ns: int,
    provenance: Provenance,
    grant_real_world: bool,
    acknowledge_dev_unverified_principal: bool,
    evidence_timeout_s: float,
    refusal: type[ValueError] = ValueError,
) -> None:
    if (
        type(grant_real_world) is not bool or not grant_real_world
        or type(acknowledge_dev_unverified_principal) is not bool
        or not acknowledge_dev_unverified_principal
        or not isinstance(session, MineflayerProcessSession)
        or session.process_returncode is not None
        or not isinstance(proposal, PhysicalActionProposalReceipt)
        or not isinstance(intent_owner, IntentCommitment)
        or not isinstance(skill_execution, SkillExecution)
        or not isinstance(supervisor, ActionSupervisor)
        or not isinstance(journal, PhysicalActionJournal)
        or type(at_ns) is not int or at_ns < 0
        or not isinstance(provenance, Provenance)
        or type(evidence_timeout_s) not in (int, float)
        or not 0 < evidence_timeout_s <= 30
    ):
        raise refusal("explicit single-owner DEV physical grant required")
    # Even a stale proposal can never convert persisted uncertainty into retry.
    journal.require_clear()


def begin_physical_issue_dev(
    session: MineflayerProcessSession,
    *,
    capability: str,
    proposal: PhysicalActionProposalReceipt,
    current_probe: MineflayerObservation,
    propose_grant: PhysicalDevGrant,
    issue_grant: PhysicalDevGrant,
    intent_owner: IntentCommitment,
    skill_execution: SkillExecution,
    supervisor: ActionSupervisor,
    journal: PhysicalActionJournal,
    at_ns: int,
    refusal: type[ValueError] = ValueError,
) -> None:
    """One owner, scoped grants, WAL-before-ISSUE; never sends native IO.

    Caller must already verify the capability-specific TWO-PROBE window.
    The dispatch is deliberately closed to EAT and ATTACK. No arbitrary
    model-provided callback can bypass the shared durable reservation.
    """
    if capability not in {"EAT", "ATTACK"}:
        raise refusal("unregistered physical issuer capability")
    journal.require_clear()
    b = proposal.binding
    check_physical_grants(b, propose_grant, issue_grant, refusal=refusal)
    owner = intent_owner.current_intent
    if (
        session.started.session_id != b.scope.world_session_id
        or journal._body["self_id"] != b.scope.self_id
        or owner is None or owner.intent_id != b.intent_id
        or owner.objective != b.goal_id
        or intent_owner.pending_reconsideration is not None
        or not skill_execution.is_current_snapshot
        or skill_execution.state is not SkillState.STARTED
        or skill_execution.execution_id != b.skill_execution_id
        or skill_execution.skill_id != b.skill_id
        or skill_execution.skill_id != capability
        or skill_execution.intent_id != b.intent_id
        or supervisor.open_actions or supervisor.recorded_actions
        or proposal.proposal.action_id != b.action_id
        or not proposal.proposal.is_current_snapshot
    ):
        raise refusal("physical owner/Skill/Intent no longer eligible")
    journal.require_clear()
    if (
        journal.records
        and journal.records[-1]["session_id"] == current_probe.session_id
        and journal.records[-1]["after_seq"] >= current_probe.seq
    ):
        raise refusal("previous physical Action source not yet advanced")
    if at_ns < max(intent_owner.last_at_ns or 0, skill_execution.events[-1].at_ns):
        raise refusal("physical time precedes selected owner/Skill")

    authorized = proposal.proposal.authorize(
        at_ns=at_ns, provenance=propose_grant.provenance,
        authority=propose_grant.authority_id,
    )
    # A failure here must preclude native effects. The same Self-owned ledger
    # enforces CAS, fsync, anti-replay and cross-restart unresolved STOP.
    if capability == "EAT":
        journal.prepare_eat(b, current_probe)
    else:
        journal.prepare_attack(b, current_probe)
    issued = supervisor.issue(
        authorized, at_ns=at_ns + 1, deadline_ns=at_ns + 1000,
        provenance=issue_grant.provenance,
    )
    assert supervisor.get(b.action_id) is issued


def finish_physical_issue_dev(
    *,
    action_id: str,
    after: MineflayerObservation,
    supervisor: ActionSupervisor,
    journal: PhysicalActionJournal,
    at_ns: int,
    close: Callable[[ActionLifecycle], None],
) -> ActionLifecycle:
    """Physical evidence/close is capability-owned; no semantic Skill success."""
    terminal = supervisor.record_outcome(
        action_id, at_ns=at_ns + 2, provenance=after.provenance,
    )
    close(terminal)
    journal.require_clear()
    return terminal


def mark_ambiguous_physical_dev(
    *,
    action_id: str,
    supervisor: ActionSupervisor,
    probe: MineflayerObservation,
    at_ns: int,
) -> None:
    """Never undo a durable reservation when a possibly applied effect fails."""
    if supervisor.get(action_id).state is ActionState.ISSUED:
        supervisor.mark_unknown(
            action_id, at_ns=at_ns + 2, provenance=probe.provenance,
        )
    # If in-memory OUTCOME preceded a failed journal close, the durable WAL
    # remains PREPARED_UNRESOLVED and wins on restore. No retry is possible.
