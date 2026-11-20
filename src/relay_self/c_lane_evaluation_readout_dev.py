"""Read-only, source-bound representation of a five-axis L1 evaluation.

This module does not submit model requests or authenticate source evidence. The
caller must qualify the original owner, WAL, GPU receipts and native CURRENT.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.relay_engine import BoundedChoice, DecisionStatus


class EvaluationAxis(str, Enum):
    GOAL_PROGRESS = "goal_progress"
    SKILL_EFFECTIVENESS = "skill_effectiveness"
    INFORMATION_GAIN = "information_gain"
    APPLICABILITY_FAILURE = "applicability_failure"
    EVIDENCE_UNCERTAINTY = "evidence_uncertainty"


class AxisStatus(str, Enum):
    RESOLVED = "resolved"
    UNKNOWN = "unknown"
    UNRESOLVED = "unresolved"
    CANCELLED = "cancelled"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class EvaluationCandidate:
    choice: BoundedChoice
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.choice, BoundedChoice):
            raise ValueError("bounded choice required")
        if not isinstance(self.evidence_refs, tuple) or not all(
            isinstance(ref, str) and ref.strip() for ref in self.evidence_refs
        ):
            raise ValueError("invalid evidence references")


@dataclass(frozen=True, slots=True)
class EvaluationStep:
    axis: EvaluationAxis
    candidates: tuple[EvaluationCandidate, ...]
    unknown_choice_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.axis, EvaluationAxis) or not isinstance(self.candidates, tuple):
            raise ValueError("typed axis and candidates required")
        if len(self.candidates) < 2 or not all(
            isinstance(c, EvaluationCandidate) for c in self.candidates
        ):
            raise ValueError("at least two typed candidates required")
        ids = [c.choice.choice_id for c in self.candidates]
        if len(set(ids)) != len(ids) or self.unknown_choice_id not in ids:
            raise ValueError("unique choices and an UNKNOWN choice required")
        if any(not c.evidence_refs for c in self.candidates
               if c.choice.choice_id != self.unknown_choice_id):
            raise ValueError("substantive candidates require evidence references")


@dataclass(frozen=True, slots=True)
class AxisReadout:
    axis: EvaluationAxis
    choice_id: str | None
    selected_description: str | None
    evidence_refs: tuple[str, ...]
    status: AxisStatus

    def __post_init__(self) -> None:
        if not isinstance(self.axis, EvaluationAxis) or not isinstance(self.status, AxisStatus):
            raise ValueError("typed axis and status required")
        if self.status in (AxisStatus.RESOLVED, AxisStatus.UNKNOWN):
            if not self.choice_id or not self.selected_description:
                raise ValueError("selected status requires original choice")
            if self.status is AxisStatus.RESOLVED and not self.evidence_refs:
                raise ValueError("resolved choice requires evidence")
        elif self.choice_id is not None or self.selected_description is not None or self.evidence_refs:
            raise ValueError("unusable result cannot select a candidate")

    @property
    def unresolved(self) -> bool:
        return self.status is AxisStatus.UNRESOLVED


def interpret_evaluation_step(
    step: EvaluationStep, *, status: DecisionStatus, choice_id: str | None,
) -> AxisReadout:
    """Bind a model selection to its offered text and source references.

    UNKNOWN and unresolved output remain distinct from success or failure.
    This is a readout of the offered candidate, not proof of model reasoning.
    """
    if not isinstance(step, EvaluationStep) or not isinstance(status, DecisionStatus):
        raise ValueError("typed evaluation step and decision status required")
    if status is DecisionStatus.UNRESOLVED:
        if choice_id is not None:
            raise ValueError("unresolved output cannot select a candidate")
        return AxisReadout(step.axis, None, None, (), AxisStatus.UNRESOLVED)
    matches = [candidate for candidate in step.candidates
               if candidate.choice.choice_id == choice_id]
    if len(matches) != 1:
        raise ValueError("model selected an unoffered candidate")
    selected = matches[0]
    return AxisReadout(
        step.axis, selected.choice.choice_id, selected.choice.description,
        selected.evidence_refs, (AxisStatus.UNKNOWN if selected.choice.choice_id
                                 == step.unknown_choice_id else AxisStatus.RESOLVED),
    )


@dataclass(frozen=True, slots=True)
class EvaluationReadout:
    task_id: str
    self_id: str
    world_id: str
    world_epoch: int
    skill_execution_id: str
    action_ids: tuple[str, ...]
    wal_sha256: str
    axes: tuple[AxisReadout, ...]

    @property
    def complete(self) -> bool:
        return all(a.status in (AxisStatus.RESOLVED, AxisStatus.UNKNOWN) for a in self.axes)

    def __post_init__(self) -> None:
        if any(not isinstance(v, str) or not v.strip() for v in (
            self.task_id, self.self_id, self.world_id, self.skill_execution_id,
        )):
            raise ValueError("evaluation scope required")
        if type(self.world_epoch) is not int or self.world_epoch < 0:
            raise ValueError("invalid world epoch")
        if (not isinstance(self.action_ids, tuple) or not self.action_ids
                or any(not isinstance(v, str) or not v.strip() for v in self.action_ids)
                or len(set(self.action_ids)) != len(self.action_ids)):
            raise ValueError("unique executed action IDs required")
        if (not isinstance(self.wal_sha256, str) or len(self.wal_sha256) != 64
                or any(c not in "0123456789abcdef" for c in self.wal_sha256)):
            raise ValueError("WAL SHA256 required")
        if (not isinstance(self.axes, tuple) or len(self.axes) != len(EvaluationAxis)
                or not all(isinstance(a, AxisReadout) for a in self.axes)
                or {a.axis for a in self.axes} != set(EvaluationAxis)):
            raise ValueError("exactly one readout per evaluation axis required")
