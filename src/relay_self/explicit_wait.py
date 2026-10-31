"""S25: caller-scoped WAIT is a non-Action hold, not authorization or scheduling.

A frozen S24 WAIT result may be acknowledged by an explicit caller. A *new*
caller-owned observation and a separate scoped authority can trigger one
explicit S24 reevaluation. No timer, scheduler, World listener, action, or
durable semantic owner is installed.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.execution_admission import AdmissionDecisionStatus
from relay_self.intent import IntentCommitment, IntentEvent
from relay_self.learning import LearningPreferenceState
from relay_self.postfailure_cognition import (
    PostFailureEpochTrace,
    PostFailureWorldEvidence,
    run_explicit_postfailure_epoch,
)
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution, SkillState


class InvalidWaitGate(ValueError):
    """Exact WAIT context, freshness, or caller authority is invalid."""


class WaitAuthorityScope(str, Enum):
    ACKNOWLEDGE = "acknowledge"
    REEVALUATE = "reevaluate"


@dataclass(frozen=True, slots=True)
class WaitGateAuthority:
    authority_id: str
    scope: WaitAuthorityScope
    intent_id: str
    evidence_id: str
    granted: bool
    provenance: Provenance

    def __post_init__(self) -> None:
        for key in ("authority_id", "intent_id", "evidence_id"):
            _identifier(key, getattr(self, key))
        if not isinstance(self.scope, WaitAuthorityScope):
            raise InvalidWaitGate("authority scope is not typed")
        if type(self.granted) is not bool:
            raise InvalidWaitGate("authority granted must be bool")
        _provenance(self.provenance)


@dataclass(frozen=True, slots=True)
class ExplicitWaitGate:
    """Caller-held read-only receipt, NOT a new wait-state semantic owner."""

    trace: PostFailureEpochTrace
    supervisor: ActionSupervisor
    action3: ActionLifecycle
    consequence3: WorldConsequence
    recovery_skill: SkillExecution
    intent: IntentCommitment
    intent_events: tuple[IntentEvent, ...]
    retained_snapshot: LearningPreferenceState
    armed_at_ns: int
    expires_at_ns: int
    acknowledgement_authority_id: str
    provenance: Provenance


@dataclass(frozen=True, slots=True)
class ExplicitWaitReevaluation:
    """New cognition result only; no Action/Skill/Intent transition."""

    original: ExplicitWaitGate
    new_evidence: PostFailureWorldEvidence
    reevaluation_authority_id: str
    result: PostFailureEpochTrace


_EXPECTED_STAGES = (
    "s24-att", "s24-blf", "s24-cnc", "s24-prd-wait",
    "s24-prd-move", "s24-plan", "s24-route", "s24-admit",
)


def acknowledge_explicit_wait(
    trace: PostFailureEpochTrace,
    supervisor: ActionSupervisor,
    action3: ActionLifecycle,
    consequence3: WorldConsequence,
    recovery_skill: SkillExecution,
    intent: IntentCommitment,
    retained_snapshot: LearningPreferenceState,
    authority: WaitGateAuthority | None,
    *,
    at_ns: int,
    expires_at_ns: int,
    provenance: Provenance,
) -> ExplicitWaitGate:
    """Read-only acknowledgement of one already ADMITTED S24 WAIT decision."""
    _time(at_ns)
    _time(expires_at_ns)
    _provenance(provenance)
    if expires_at_ns <= at_ns:
        raise InvalidWaitGate("WAIT expiration must be later than acknowledgement")
    if not isinstance(trace, PostFailureEpochTrace):
        raise InvalidWaitGate("requires S24 typed cognitive trace")
    if trace.selected_candidate != "WAIT":
        raise InvalidWaitGate("WAIT acknowledgement cannot absorb MOVE_AWAY")
    if (
        trace.admission_status is not AdmissionDecisionStatus.ADMITTED
        or trace.wait_score >= trace.move_score
        or trace.stage_ids != _EXPECTED_STAGES
        or trace.epoch.cognition_requested
        or trace.epoch.timed_out_actions
        or trace.world_evidence.provenance not in trace.source_provenance
    ):
        raise InvalidWaitGate("S24 WAIT cognition/admission lineage not qualified")
    if not isinstance(supervisor, ActionSupervisor) or supervisor.open_actions:
        raise InvalidWaitGate("existing ActionSupervisor must have no open Actions")
    if not isinstance(action3, ActionLifecycle) or not action3.is_current_snapshot:
        raise InvalidWaitGate("Action3 must be current")
    if action3.state is not ActionState.OUTCOME or supervisor.get(action3.action_id) is not action3:
        raise InvalidWaitGate("requires supervised terminal Action3 OUTCOME")
    if not isinstance(consequence3, WorldConsequence):
        raise InvalidWaitGate("requires typed WorldConsequence")
    if consequence3.status is not WorldConsequenceStatus.EXECUTED:
        raise InvalidWaitGate("requires executed WorldConsequence")
    if not isinstance(recovery_skill, SkillExecution):
        raise InvalidWaitGate("requires recovery Skill")
    if not recovery_skill.is_current_snapshot or recovery_skill.state is not SkillState.STARTED:
        raise InvalidWaitGate("recovery Skill must be current STARTED")
    if not isinstance(intent, IntentCommitment):
        raise InvalidWaitGate("requires existing Intent owner")
    current = intent.current_intent
    if current is None or intent.pending_reconsideration is not None:
        raise InvalidWaitGate("Current Intent must be active")
    if (
        action3.skill_execution_id != recovery_skill.execution_id
        or action3.intent_id != current.intent_id
        or recovery_skill.intent_id != current.intent_id
        or trace.world_evidence.action_id != action3.action_id
        or trace.world_evidence.binding_id != consequence3.binding_id
        or trace.world_evidence.session_id != consequence3.session_id
        or trace.world_evidence.consequence_provenance != consequence3.provenance
        or action3.events[-1].provenance != consequence3.provenance
    ):
        raise InvalidWaitGate("Action/Skill/World evidence lineage mismatch")
    if not isinstance(retained_snapshot, LearningPreferenceState):
        raise InvalidWaitGate("requires exact retained snapshot")
    if (
        retained_snapshot.target_id != "risk_weight"
        or retained_snapshot.revision != 1
        or retained_snapshot.value != 4
        or trace.retained_revision != retained_snapshot.revision
    ):
        raise InvalidWaitGate("S19 retained rev1/value4 not preserved")
    if at_ns < trace.world_evidence.observed_at_ns:
        raise InvalidWaitGate("acknowledgement predates observed evidence")
    if supervisor.last_at_ns is None or at_ns < supervisor.last_at_ns:
        raise InvalidWaitGate("acknowledgement predates S24 epoch")
    _authorize(authority, WaitAuthorityScope.ACKNOWLEDGE, current.intent_id, trace.world_evidence.evidence_id)
    return ExplicitWaitGate(
        trace=trace, supervisor=supervisor, action3=action3,
        consequence3=consequence3, recovery_skill=recovery_skill,
        intent=intent, intent_events=intent.events,
        retained_snapshot=retained_snapshot,
        armed_at_ns=at_ns, expires_at_ns=expires_at_ns,
        acknowledgement_authority_id=authority.authority_id,
        provenance=provenance,
    )


def reevaluate_explicit_wait(
    gate: ExplicitWaitGate,
    evidence: PostFailureWorldEvidence,
    authority: WaitGateAuthority | None,
    *,
    at_ns: int,
    provenance: Provenance,
) -> ExplicitWaitReevaluation:
    """One explicit recheck from fresh evidence, without Action authorization.

    No recheck occurs merely when the deadline passes or an evidence object
    exists. The caller must invoke this function with separate route authority.
    """
    if not isinstance(gate, ExplicitWaitGate):
        raise InvalidWaitGate("requires typed WAIT acknowledgement")
    if not isinstance(evidence, PostFailureWorldEvidence):
        raise InvalidWaitGate("requires new typed observation")
    _time(at_ns)
    _provenance(provenance)
    if at_ns > gate.expires_at_ns:
        raise InvalidWaitGate("WAIT receipt expired; explicit fresh decision required")
    if gate.intent.events != gate.intent_events:
        raise InvalidWaitGate("Current Intent event history drifted")
    if gate.supervisor.open_actions:
        raise InvalidWaitGate("Action was issued after WAIT was acknowledged")
    if not gate.action3.is_current_snapshot or gate.supervisor.get(gate.action3.action_id) is not gate.action3:
        raise InvalidWaitGate("Action3 no longer current")
    if not gate.recovery_skill.is_current_snapshot:
        raise InvalidWaitGate("recovery Skill is stale")
    if gate.retained_snapshot.revision != gate.trace.retained_revision:
        raise InvalidWaitGate("retained revision drifted")
    old = gate.trace.world_evidence
    if (
        evidence.action_id != old.action_id
        or evidence.binding_id != old.binding_id
        or evidence.session_id != old.session_id
        or evidence.consequence_provenance != old.consequence_provenance
        or evidence.evidence_id == old.evidence_id
        or evidence.provenance == old.provenance
        or evidence.observed_at_ns <= gate.armed_at_ns
        or evidence.observed_at_ns > at_ns
        or evidence.observed_at_ns > gate.expires_at_ns
    ):
        raise InvalidWaitGate("no fresh same-lineage World observation within WAIT window")
    if gate.supervisor.last_at_ns is not None and at_ns < gate.supervisor.last_at_ns:
        raise InvalidWaitGate("reevaluation predates supervisor clock")
    current = gate.intent.current_intent
    if current is None or gate.intent.pending_reconsideration is not None:
        raise InvalidWaitGate("Current Intent not active")
    if current.intent_id != gate.action3.intent_id:
        raise InvalidWaitGate("Intent owner changed")
    _authorize(authority, WaitAuthorityScope.REEVALUATE, current.intent_id, evidence.evidence_id)
    if authority.authority_id == gate.acknowledgement_authority_id:
        raise InvalidWaitGate("reevaluation must have separate caller authority")
    fresh = run_explicit_postfailure_epoch(
        gate.supervisor, gate.action3, gate.consequence3,
        gate.recovery_skill, gate.intent, gate.retained_snapshot, evidence,
        at_ns=at_ns, provenance=provenance,
    )
    if fresh.retained_revision != gate.trace.retained_revision:
        raise InvalidWaitGate("reevaluation changed retained revision")
    return ExplicitWaitReevaluation(
        original=gate, new_evidence=evidence,
        reevaluation_authority_id=authority.authority_id, result=fresh,
    )


def _authorize(
    authority: WaitGateAuthority | None,
    scope: WaitAuthorityScope,
    intent_id: str,
    evidence_id: str,
) -> None:
    if not isinstance(authority, WaitGateAuthority) or not authority.granted:
        raise InvalidWaitGate("requires explicit granted caller authority")
    if (
        authority.scope is not scope
        or authority.intent_id != intent_id
        or authority.evidence_id != evidence_id
    ):
        raise InvalidWaitGate("caller authority scope / identity mismatch")


def _identifier(field: str, value: object) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or any(c.isspace() for c in value)
    ):
        raise InvalidWaitGate(f"{field} must be a structured identifier")


def _time(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidWaitGate("time must be nonnegative integer")


def _provenance(value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidWaitGate("provenance must be typed Provenance")
