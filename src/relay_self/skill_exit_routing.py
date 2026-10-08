"""S22: bounded Skill-exit routing, without automatic Intent replacement.

Terminal Skill evidence does not itself authorize a new Skill or reconsideration.
Both handoffs are explicitly caller invoked and scoped. This module owns no
durable semantic state, execution loop, or second Intent lifecycle.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.intent import IntentCommitment, IntentEvent
from relay_self.provenance import Provenance
from relay_self.skill import SKILL_TERMINAL_STATES, SkillExecution, SkillState


class InvalidSkillExitEvidence(ValueError):
    """The caller's terminal Skill or context evidence does not match owners."""


class InvalidSkillExitAuthority(ValueError):
    """The caller did not grant the exact proposed handoff."""


class LocalPathStatus(str, Enum):
    AVAILABLE = "available"
    EXHAUSTED = "exhausted"
    UNDETERMINED = "undetermined"


class IntentImpact(str, Enum):
    NOT_CHALLENGED = "not_challenged"
    MATERIALLY_CHALLENGED = "materially_challenged"
    UNDETERMINED = "undetermined"


class SkillExitRoute(str, Enum):
    CONTINUE_INTENT_ONLY = "continue_intent_only"
    LOCAL_RECOVERY_CANDIDATE = "local_recovery_candidate"
    RECONSIDERATION_CANDIDATE = "reconsideration_candidate"
    HOLD_FOR_EVIDENCE = "hold_for_evidence"


@dataclass(frozen=True, slots=True)
class SkillExitCriterion:
    criterion_id: str
    skill_id: str
    intent_id: str
    provenance: Provenance

    def __post_init__(self) -> None:
        for field in ("criterion_id", "skill_id", "intent_id"):
            _name(field, getattr(self, field))
        _provenance(self.provenance)


@dataclass(frozen=True, slots=True)
class SkillExitEvidence:
    """Caller-evaluated feasibility and intent impact, not World truth."""

    criterion_id: str
    skill_execution_id: str
    intent_id: str
    terminal_state: SkillState
    terminal_at_ns: int
    terminal_provenance: Provenance
    local_path: LocalPathStatus
    alternative_skill_id: str | None
    intent_impact: IntentImpact
    observed_at_ns: int
    provenance: Provenance

    def __post_init__(self) -> None:
        for field in ("criterion_id", "skill_execution_id", "intent_id"):
            _name(field, getattr(self, field))
        if not isinstance(self.terminal_state, SkillState):
            raise InvalidSkillExitEvidence("terminal_state must be SkillState")
        _time(self.terminal_at_ns)
        _time(self.observed_at_ns)
        _provenance(self.terminal_provenance)
        _provenance(self.provenance)
        if not isinstance(self.local_path, LocalPathStatus):
            raise InvalidSkillExitEvidence("local_path must be LocalPathStatus")
        if not isinstance(self.intent_impact, IntentImpact):
            raise InvalidSkillExitEvidence("intent_impact must be IntentImpact")
        if self.local_path is LocalPathStatus.AVAILABLE:
            _name("alternative_skill_id", self.alternative_skill_id)
        elif self.alternative_skill_id is not None:
            raise InvalidSkillExitEvidence("non-available path cannot name an alternative")


@dataclass(frozen=True, slots=True)
class SkillExitAuthority:
    authority_id: str
    criterion_id: str
    intent_id: str
    route: SkillExitRoute
    granted: bool
    provenance: Provenance

    def __post_init__(self) -> None:
        for field in ("authority_id", "criterion_id", "intent_id"):
            _name(field, getattr(self, field))
        if not isinstance(self.route, SkillExitRoute):
            raise InvalidSkillExitAuthority("route must be SkillExitRoute")
        if type(self.granted) is not bool:
            raise InvalidSkillExitAuthority("granted must be bool")
        _provenance(self.provenance)


@dataclass(frozen=True, slots=True)
class SkillExitAssessment:
    """Read-only route with an exact Intent event history checkpoint."""

    skill: SkillExecution
    intent: IntentCommitment
    intent_events: tuple[IntentEvent, ...]
    criterion: SkillExitCriterion
    evidence: SkillExitEvidence
    route: SkillExitRoute


def assess_skill_exit(
    skill: SkillExecution,
    intent: IntentCommitment,
    criterion: SkillExitCriterion,
    evidence: SkillExitEvidence,
) -> SkillExitAssessment:
    """Classify this one closed Skill, without mutating any owner.

    Intent-level reconsideration requires both no known local path and an
    independent explicit material challenge to the committed objective.
    """
    if not isinstance(skill, SkillExecution) or not skill.is_current_snapshot:
        raise InvalidSkillExitEvidence("Skill must be current snapshot")
    if skill.state not in SKILL_TERMINAL_STATES:
        raise InvalidSkillExitEvidence("Skill must have explicit terminal state")
    if not isinstance(intent, IntentCommitment):
        raise InvalidSkillExitEvidence("requires existing IntentCommitment owner")
    if not isinstance(criterion, SkillExitCriterion):
        raise InvalidSkillExitEvidence("requires typed SkillExitCriterion")
    if not isinstance(evidence, SkillExitEvidence):
        raise InvalidSkillExitEvidence("requires typed SkillExitEvidence")
    current = intent.current_intent
    if current is None:
        raise InvalidSkillExitEvidence("no Current Intent to preserve or reconsider")
    terminal = skill.events[-1]
    if (
        skill.intent_id != current.intent_id
        or criterion.intent_id != current.intent_id
        or evidence.intent_id != current.intent_id
        or skill.skill_id != criterion.skill_id
        or evidence.skill_execution_id != skill.execution_id
        or evidence.criterion_id != criterion.criterion_id
        or evidence.terminal_state is not skill.state
        or evidence.terminal_at_ns != terminal.at_ns
        or evidence.terminal_provenance != terminal.provenance
        or evidence.observed_at_ns < terminal.at_ns
    ):
        raise InvalidSkillExitEvidence("Skill/Intent/terminal evidence lineage mismatch")
    if evidence.provenance == terminal.provenance:
        raise InvalidSkillExitEvidence("separate caller feasibility evidence is required")
    if (
        evidence.alternative_skill_id is not None
        and evidence.alternative_skill_id == skill.skill_id
    ):
        raise InvalidSkillExitEvidence("local recovery must name a different Skill")
    if skill.state is SkillState.SUCCEEDED:
        # Skill success never automatically completes the Current Intent.
        route = SkillExitRoute.CONTINUE_INTENT_ONLY
    elif skill.state is SkillState.CANCELLED:
        # Cancellation could be externally motivated: no failure inference.
        route = SkillExitRoute.HOLD_FOR_EVIDENCE
    elif (
        evidence.local_path is LocalPathStatus.AVAILABLE
        and evidence.intent_impact is IntentImpact.NOT_CHALLENGED
    ):
        route = SkillExitRoute.LOCAL_RECOVERY_CANDIDATE
    elif (
        evidence.local_path is LocalPathStatus.EXHAUSTED
        and evidence.intent_impact is IntentImpact.MATERIALLY_CHALLENGED
    ):
        route = SkillExitRoute.RECONSIDERATION_CANDIDATE
    else:
        route = SkillExitRoute.HOLD_FOR_EVIDENCE
    return SkillExitAssessment(
        skill=skill, intent=intent, intent_events=intent.events,
        criterion=criterion, evidence=evidence, route=route,
    )


def start_explicit_local_recovery(
    assessment: SkillExitAssessment,
    authority: SkillExitAuthority | None,
    *,
    execution_id: str,
    at_ns: int,
    provenance: Provenance,
) -> SkillExecution:
    """Caller-authorized separate Skill start; never selects or issues Action."""
    fresh = _revalidate(assessment, SkillExitRoute.LOCAL_RECOVERY_CANDIDATE)
    _authority(fresh, authority)
    _time(at_ns)
    _provenance(provenance)
    _name("execution_id", execution_id)
    if execution_id == fresh.skill.execution_id:
        raise InvalidSkillExitEvidence("recovery Skill execution needs new identity")
    if at_ns < fresh.evidence.observed_at_ns:
        raise InvalidSkillExitEvidence("recovery start predates feasibility evidence")
    if fresh.intent.pending_reconsideration is not None:
        raise InvalidSkillExitEvidence("pending reconsideration blocks local recovery")
    assert fresh.evidence.alternative_skill_id is not None
    return SkillExecution.start(
        execution_id,
        skill_id=fresh.evidence.alternative_skill_id,
        intent_commitment=fresh.intent,
        at_ns=at_ns,
        provenance=provenance,
    )


def request_explicit_reconsideration(
    assessment: SkillExitAssessment,
    authority: SkillExitAuthority | None,
    *,
    at_ns: int,
    provenance: Provenance,
) -> IntentEvent:
    """Caller-admitted request through existing Intent owner, not release."""
    fresh = _revalidate(assessment, SkillExitRoute.RECONSIDERATION_CANDIDATE)
    _authority(fresh, authority)
    _time(at_ns)
    _provenance(provenance)
    if at_ns < fresh.evidence.observed_at_ns:
        raise InvalidSkillExitEvidence("request predates intent challenge evidence")
    reason = (
        f"criterion:{fresh.criterion.criterion_id}"
        f"|failed_skill:{fresh.skill.execution_id}"
        f"|source:{fresh.evidence.provenance.reference}"
        f"|authority:{authority.authority_id}"
    )
    return fresh.intent.request_reconsideration(
        fresh.skill.intent_id, reason=reason, at_ns=at_ns, provenance=provenance,
    )


def _revalidate(
    assessment: SkillExitAssessment,
    required: SkillExitRoute,
) -> SkillExitAssessment:
    if not isinstance(assessment, SkillExitAssessment):
        raise InvalidSkillExitEvidence("requires typed SkillExitAssessment")
    if assessment.intent.events != assessment.intent_events:
        raise InvalidSkillExitEvidence("Intent owner changed since assessment")
    fresh = assess_skill_exit(
        assessment.skill, assessment.intent,
        assessment.criterion, assessment.evidence,
    )
    if fresh.route is not assessment.route or fresh.route is not required:
        raise InvalidSkillExitEvidence("handoff not justified by current evidence")
    return fresh


def _authority(assessment: SkillExitAssessment, authority: SkillExitAuthority | None) -> None:
    if not isinstance(authority, SkillExitAuthority) or not authority.granted:
        raise InvalidSkillExitAuthority("explicit granted authority required")
    if (
        authority.criterion_id != assessment.criterion.criterion_id
        or authority.intent_id != assessment.skill.intent_id
        or authority.route is not assessment.route
    ):
        raise InvalidSkillExitAuthority("authority does not match requested handoff")


def _name(field: str, value: object) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or any(c.isspace() for c in value)
    ):
        raise InvalidSkillExitEvidence(f"{field} must be a structured identifier")


def _time(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidSkillExitEvidence("time must be nonnegative integer")


def _provenance(value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidSkillExitEvidence("provenance must be typed Provenance")
