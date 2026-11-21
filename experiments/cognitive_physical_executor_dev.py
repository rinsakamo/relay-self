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
        or b.body_channel != (
            "locomotion" if capability == "MOVE" else "hand"
        ) or b.target_kind != target_kind
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
    place_invocation: object | None = None,
    place_motion: object | None = None,
    allow_prior_original_place_terminals: bool = False,
    place_gait_mode: str | None = None,
    i4a_s2_boundary: object | None = None,
    i4a_s2_owner: object | None = None,
    i4a_s2_physical: object | None = None,
) -> None:
    """One owner, scoped grants, WAL-before-ISSUE; never sends native IO.

    Caller must already verify the capability-specific TWO-PROBE window.
    Dispatch is closed to EAT, ATTACK and selected bounded MOVE.
    No arbitrary model-provided callback can bypass the durable reservation.
    """
    if capability not in {"EAT", "ATTACK", "MOVE"}:
        raise refusal("unregistered physical issuer capability")
    journal.require_clear()
    b = proposal.binding
    if (
        b.skill_id != capability or b.skill_version != 1
        or b.capability_ref != capability or b.capability_version != 1
    ):
        raise refusal("physical issuer cannot change selected capability")
    check_physical_grants(b, propose_grant, issue_grant, refusal=refusal)
    # Stage27h only: a second original MOVE child may follow *fully closed*
    # preceding children of the SAME original Invocation/Intent/Skill/Target.
    # Default Stage27g and EAT/ATTACK/RELATIVE still reject ANY history.
    prior_actions = supervisor.recorded_actions
    if place_gait_mode not in (None, "WALK", "SNEAK"):
        raise refusal("unsupported original PLACE gait selection")
    if allow_prior_original_place_terminals:
        from relay_self.skill_invocation import SkillInvocation

        if (
            type(allow_prior_original_place_terminals) is not bool
            or capability != "MOVE"
            or not isinstance(place_invocation, SkillInvocation)
            or place_invocation.target.contract is None
            or place_motion is None
            or not prior_actions
            or len(prior_actions) != len(journal.records)
            or len(prior_actions) >= place_invocation.budget.max_actions
            or place_invocation.budget.max_actions > 4
            or b.action_id in {a.action_id for a in prior_actions}
        ):
            raise refusal("original L0 multi-Action terminal history not admissible")
        rows = journal.records
        if (
            {a.action_id for a in prior_actions}
            != {row["action_id"] for row in rows}
            or any(
                a.state is not ActionState.OUTCOME or not a.is_current_snapshot
                or a.intent_id != b.intent_id
                or a.skill_execution_id != b.skill_execution_id
                for a in prior_actions
            )
            or any(
                row["capability"] != "MOVE_PLACE"
                or row["status"] != "NATIVE_PLACE_MOVE_SETTLED"
                or row["session_id"] != b.scope.world_session_id
                or row["intent_id"] != b.intent_id
                or row["skill_execution_id"] != b.skill_execution_id
                or row["target_ref"] != b.target_ref
                or row["invocation_ref"] != place_invocation.invocation_ref
                or row["preset_ref"] != place_invocation.parameter_preset_ref
                or row["target_contract_ref"]
                != place_invocation.target.contract.contract_ref
                or row["after_seq"] is None
                or row["after_seq"] >= current_probe.seq
                for row in rows
            )
            or place_invocation.budget.max_distance_m is None
            or sum(row["displacement_m"] for row in rows)
            >= place_invocation.budget.max_distance_m
        ):
            raise refusal("original closed multi-MOVE lineage altered or exhausted")
    elif i4a_s2_boundary is not None:
        # This opt-in first S2 Action may follow an *authenticated* terminal
        # S1 prefix only. It requires the SAME participating original Owner,
        # PhysicalAdmission and a live atomic issue window. No arbitrary
        # prefix offset or boolean bypasses the complete canonical journal.
        from relay_self.checkpointed_cognitive_runtime_dev import (
            CheckpointedCognitiveOwner,
        )
        from relay_self.i_lane_i4a_s2_run_boundary_dev import I4AS2EmptyRunBoundary
        from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
        from relay_self.skill_invocation import SkillInvocation

        boundary = i4a_s2_boundary
        original_owner = i4a_s2_owner
        physical = i4a_s2_physical
        if (
            not isinstance(boundary, I4AS2EmptyRunBoundary)
            or not isinstance(original_owner, CheckpointedCognitiveOwner)
            or not isinstance(physical, PhysicalIssueAdmission)
            or boundary.owner is not original_owner
            or boundary.new_action_authorized
            or original_owner.cohort is None
            or original_owner.intent is not intent_owner
            or original_owner.supervisor is not supervisor
            or original_owner.skills.get(boundary.new_skill_id) is not skill_execution
            or original_owner.files.physical_wal_file.resolve() != journal.path.resolve()
            or original_owner.native_session_id != boundary.native_session_id
            or original_owner.current_worldbody_observation is not current_probe
            or getattr(original_owner, "_i4a_s2_empty_run_boundary", None)
            is not boundary
            or getattr(original_owner, "_i4a_live_wal_anchor", None)
            is not boundary.anchor
            or capability != "MOVE"
            or not isinstance(place_invocation, SkillInvocation)
            or place_invocation.target.contract is None
            or place_invocation.invocation_ref != boundary.invocation_ref
            or place_invocation.parameter_preset_ref != boundary.preset_ref
            or place_invocation.target.ref != boundary.target_ref
            or place_motion is None
            or b.intent_id != boundary.new_intent_id
            or b.skill_execution_id != boundary.new_skill_id
            or b.target_ref != boundary.target_ref
            or b.scope.self_id != boundary.self_id
            or b.scope.world_session_id != boundary.native_session_id
            or len(prior_actions) != boundary.prefix_count
            or len(journal.records) != boundary.prefix_count
            or journal.digest != boundary.prefix_digest
            or tuple(row["action_id"] for row in journal.records)
            != boundary.prefix_action_ids
            or {a.action_id for a in prior_actions}
            != set(boundary.prefix_action_ids)
            or any(
                a.state is not ActionState.OUTCOME or not a.is_current_snapshot
                or a.intent_id != boundary.old_intent_id
                or a.skill_execution_id != boundary.old_skill_id
                for a in prior_actions
            )
            or any(
                row["capability"] != "MOVE_PLACE"
                or row["status"] != "NATIVE_PLACE_MOVE_SETTLED"
                or row["intent_id"] != boundary.old_intent_id
                or row["skill_execution_id"] != boundary.old_skill_id
                or row["session_id"] != boundary.native_session_id
                or row["after_seq"] is None
                or row["after_seq"] >= current_probe.seq
                for row in journal.records
            )
        ):
            raise refusal("certified S2 physical issuer full-prefix history invalid")
        # No alternate principal can invoke this mode using a typed copy.
        physical.require_original_i4a_s2_wal_window(
            owner=original_owner, boundary=boundary, action_id=b.action_id,
        )
    elif type(allow_prior_original_place_terminals) is not bool:
        raise refusal("typed multi-Action issuer mode required")
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
        or supervisor.open_actions
        or (supervisor.recorded_actions and not (
            allow_prior_original_place_terminals or i4a_s2_boundary is not None
        ))
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
    if at_ns < max(
        intent_owner.last_at_ns or 0,
        skill_execution.events[-1].at_ns,
        supervisor.last_at_ns or 0,
    ):
        raise refusal("physical time precedes selected owner/Skill")

    authorized = proposal.proposal.authorize(
        at_ns=at_ns, provenance=propose_grant.provenance,
        authority=propose_grant.authority_id,
    )
    # A failure here must preclude native effects. The same Self-owned ledger
    # enforces CAS, fsync, anti-replay and cross-restart unresolved STOP.
    if capability == "EAT":
        journal.prepare_eat(b, current_probe)
    elif capability == "ATTACK":
        journal.prepare_attack(b, current_probe)
    else:
        if place_invocation is None and place_motion is None:
            journal.prepare_move(b, current_probe)
        elif place_invocation is not None and place_motion is not None:
            journal.prepare_place_move(
                b, current_probe, place_invocation, place_motion,
                precision_gait=place_gait_mode,
            )
        else:
            raise refusal("partial PLACE original issuer plan is invalid")
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
