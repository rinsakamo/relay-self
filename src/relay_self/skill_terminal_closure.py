"""S21: evidence-gated Skill terminal closure over existing Skill owner.

An Action OUTCOME is not a Skill result. This module assesses explicitly
supplied, criterion-scoped goal evidence; only SkillExecution owns the terminal
transition. The caller supplies and vouches for evidence and authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_outcome import ActionOutcomeDisposition, ActionOutcomeInterpretation
from relay_self.action_supervision import ActionSupervisor
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution, SkillState


class InvalidSkillTerminalEvidence(ValueError):
    """Goal evidence or current owner lineage is absent or mismatched."""


class InvalidSkillTerminalAuthority(ValueError):
    """Terminal commitment lacks matching, explicitly granted authority."""


class SkillGoalStatus(str, Enum):
    SATISFIED = "satisfied"
    VIOLATED = "violated"
    UNDETERMINED = "undetermined"


class SkillTerminalDisposition(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNDETERMINED = "undetermined"


@dataclass(frozen=True, slots=True)
class SkillTerminalCriterion:
    criterion_id: str
    skill_id: str
    goal_ref: str
    provenance: Provenance

    def __post_init__(self) -> None:
        for name in ("criterion_id", "skill_id", "goal_ref"):
            _identifier(name, getattr(self, name))
        _provenance(self.provenance)


@dataclass(frozen=True, slots=True)
class SkillGoalEvidence:
    """Explicit external/caller goal evaluation, NOT an Action result."""

    criterion_id: str
    skill_execution_id: str
    intent_id: str
    action_id: str
    binding_id: str
    session_id: str
    goal_ref: str
    status: SkillGoalStatus
    observed_at_ns: int
    provenance: Provenance

    def __post_init__(self) -> None:
        for name in (
            "criterion_id", "skill_execution_id", "intent_id", "action_id",
            "binding_id", "session_id", "goal_ref",
        ):
            _identifier(name, getattr(self, name))
        if not isinstance(self.status, SkillGoalStatus):
            raise InvalidSkillTerminalEvidence("status must be SkillGoalStatus")
        _time(self.observed_at_ns)
        _provenance(self.provenance)


@dataclass(frozen=True, slots=True)
class SkillTerminalAuthority:
    authority_id: str
    skill_execution_id: str
    criterion_id: str
    granted: bool
    provenance: Provenance

    def __post_init__(self) -> None:
        for name in ("authority_id", "skill_execution_id", "criterion_id"):
            _identifier(name, getattr(self, name))
        if type(self.granted) is not bool:
            raise InvalidSkillTerminalAuthority("granted must be bool")
        _provenance(self.provenance)


@dataclass(frozen=True, slots=True)
class SkillTerminalAssessment:
    """Transient verdict retaining exact snapshots for a guarded later commit."""

    skill: SkillExecution
    action: ActionLifecycle
    supervisor: ActionSupervisor
    interpretation: ActionOutcomeInterpretation
    criterion: SkillTerminalCriterion
    evidence: SkillGoalEvidence
    disposition: SkillTerminalDisposition


def assess_skill_terminal(
    skill: SkillExecution,
    supervisor: ActionSupervisor,
    action: ActionLifecycle,
    interpretation: ActionOutcomeInterpretation,
    criterion: SkillTerminalCriterion,
    evidence: SkillGoalEvidence,
) -> SkillTerminalAssessment:
    """Check exact supervised Action lineage and independent goal evidence.

    A known Action outcome is not itself a claim of goal achievement.
    UNKNOWN Action or undetermined goal evidence cannot close the Skill.
    """
    if not isinstance(skill, SkillExecution) or not skill.is_current_snapshot:
        raise InvalidSkillTerminalEvidence("Skill must be current owner snapshot")
    if skill.state is not SkillState.STARTED:
        raise InvalidSkillTerminalEvidence("Skill must still be STARTED")
    if not isinstance(supervisor, ActionSupervisor):
        raise InvalidSkillTerminalEvidence("requires existing ActionSupervisor")
    if not isinstance(action, ActionLifecycle) or not action.is_current_snapshot:
        raise InvalidSkillTerminalEvidence("Action must be current snapshot")
    if supervisor.get(action.action_id) is not action:
        raise InvalidSkillTerminalEvidence("Action is not supervisor current snapshot")
    if action.state not in (ActionState.OUTCOME, ActionState.UNKNOWN):
        raise InvalidSkillTerminalEvidence("Action must have a recorded terminal result")
    if not isinstance(interpretation, ActionOutcomeInterpretation):
        raise InvalidSkillTerminalEvidence("requires typed Action outcome interpretation")
    if not isinstance(criterion, SkillTerminalCriterion):
        raise InvalidSkillTerminalEvidence("requires explicit Skill terminal criterion")
    if not isinstance(evidence, SkillGoalEvidence):
        raise InvalidSkillTerminalEvidence("requires independent typed goal evidence")
    if (
        skill.execution_id != action.skill_execution_id
        or skill.intent_id != action.intent_id
        or skill.skill_id != criterion.skill_id
        or criterion.criterion_id != evidence.criterion_id
        or criterion.goal_ref != evidence.goal_ref
        or evidence.skill_execution_id != skill.execution_id
        or evidence.intent_id != skill.intent_id
        or evidence.action_id != action.action_id
    ):
        raise InvalidSkillTerminalEvidence("Skill/Action/criterion identity mismatch")
    if (
        interpretation.action_id != action.action_id
        or interpretation.skill_execution_id != skill.execution_id
        or interpretation.intent_id != skill.intent_id
        or interpretation.binding_id != evidence.binding_id
        or interpretation.session_id != evidence.session_id
        or action.events[-1].provenance != interpretation.world_provenance
    ):
        raise InvalidSkillTerminalEvidence("Action outcome / goal lineage mismatch")
    if evidence.observed_at_ns < action.events[-1].at_ns:
        raise InvalidSkillTerminalEvidence("goal evidence predates terminal Action")
    if evidence.provenance == interpretation.world_provenance:
        raise InvalidSkillTerminalEvidence("goal evaluation needs separate provenance")
    if action.state is ActionState.OUTCOME:
        if interpretation.disposition is not ActionOutcomeDisposition.OUTCOME:
            raise InvalidSkillTerminalEvidence("Action interpretation contradicts owner")
        if evidence.status is SkillGoalStatus.SATISFIED:
            disposition = SkillTerminalDisposition.SUCCEEDED
        elif evidence.status is SkillGoalStatus.VIOLATED:
            disposition = SkillTerminalDisposition.FAILED
        else:
            disposition = SkillTerminalDisposition.UNDETERMINED
    else:
        if interpretation.disposition is not ActionOutcomeDisposition.UNKNOWN:
            raise InvalidSkillTerminalEvidence("UNKNOWN Action requires UNKNOWN interpretation")
        disposition = SkillTerminalDisposition.UNDETERMINED
    return SkillTerminalAssessment(
        skill=skill,
        action=action,
        supervisor=supervisor,
        interpretation=interpretation,
        criterion=criterion,
        evidence=evidence,
        disposition=disposition,
    )


def commit_skill_terminal(
    assessment: SkillTerminalAssessment,
    authority: SkillTerminalAuthority | None,
    *,
    at_ns: int,
    provenance: Provenance,
) -> SkillExecution:
    """Apply a decisive verdict through SkillExecution, never Action/Intent."""
    if not isinstance(assessment, SkillTerminalAssessment):
        raise InvalidSkillTerminalEvidence("requires typed Skill assessment")
    _time(at_ns)
    _provenance(provenance)
    if assessment.disposition is SkillTerminalDisposition.UNDETERMINED:
        raise InvalidSkillTerminalEvidence("undetermined evidence cannot close Skill")
    # Reassess currentness and exact lineage before any owner transition. This
    # also prevents directly fabricated assessments from bypassing the guard.
    fresh = assess_skill_terminal(
        assessment.skill, assessment.supervisor, assessment.action,
        assessment.interpretation, assessment.criterion, assessment.evidence,
    )
    if fresh.disposition is not assessment.disposition:
        raise InvalidSkillTerminalEvidence("assessment verdict is not reproducible")
    if at_ns < max(fresh.evidence.observed_at_ns, fresh.action.events[-1].at_ns):
        raise InvalidSkillTerminalEvidence("terminal time precedes evidence")
    if not isinstance(authority, SkillTerminalAuthority) or not authority.granted:
        raise InvalidSkillTerminalAuthority("explicit granted authority is required")
    if (
        authority.skill_execution_id != fresh.skill.execution_id
        or authority.criterion_id != fresh.criterion.criterion_id
    ):
        raise InvalidSkillTerminalAuthority("authority is for a different Skill/criterion")
    reason = (
        f"criterion:{fresh.criterion.criterion_id}"
        f"|goal:{fresh.criterion.goal_ref}"
        f"|action:{fresh.action.action_id}"
        f"|evidence:{fresh.evidence.provenance.reference}"
        f"|authority:{authority.authority_id}"
    )
    if fresh.disposition is SkillTerminalDisposition.SUCCEEDED:
        return fresh.skill.succeed(reason=reason, at_ns=at_ns, provenance=provenance)
    if fresh.disposition is SkillTerminalDisposition.FAILED:
        return fresh.skill.fail(reason=reason, at_ns=at_ns, provenance=provenance)
    raise InvalidSkillTerminalEvidence("unsupported terminal disposition")


def _identifier(name: str, value: object) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or any(c.isspace() for c in value)
    ):
        raise InvalidSkillTerminalEvidence(f"{name} must be one structured identifier")


def _time(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidSkillTerminalEvidence("time must be a nonnegative integer")


def _provenance(value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidSkillTerminalEvidence("provenance must be typed Provenance")
