"""#841: owner-neutral Present/Schema -> L1 cognitive work selection seam.

A CPU-constructed selection task prevents recursive task selection. The L1
answer is a *candidate for Self owner review*, never a Goal/Intent/Action.
This module does not run an LLM, grant GPU, install L0, or write memory.
"""

from __future__ import annotations

from dataclasses import dataclass

from relay_self.cognitive_profile_contract import OriginKind
from relay_self.common_io import (
    Clock,
    CognitionResultReceipt,
    CognitiveTask,
    CommonEnvelope,
    Profile,
    ProfileDecision,
    TaskRequirement,
    result_is_current,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
)
from relay_self.three_self_present import PresentFrame

NO_NEW_WORK = "__NO_NEW_WORK__"


class WorkSelectionError(ValueError):
    """Invalid or stale proposed cognitive work; no owner mutation occurred."""


@dataclass(frozen=True, slots=True)
class CognitiveWorkCandidate:
    """Owner-supplied possible work, *not* an adopted Goal or selected Action.

    origin_kind=None means origin_ref points to a qualified Present Schema
    signal event. Otherwise it points to an already-active owner object.
    """

    candidate_ref: str
    description: str
    origin_ref: str
    requirement: TaskRequirement
    provenance: Provenance
    origin_kind: OriginKind | None = None

    def __post_init__(self) -> None:
        for key in ("candidate_ref", "description", "origin_ref"):
            _text(key, getattr(self, key))
        if self.candidate_ref == NO_NEW_WORK:
            raise WorkSelectionError("reserved no-work choice cannot be supplied")
        if not isinstance(self.requirement, TaskRequirement):
            raise WorkSelectionError("work requirement must be TaskRequirement")
        if self.requirement is TaskRequirement.FAST_REACTION:
            raise WorkSelectionError("native L0 FastCue cannot be selected by L1")
        if self.origin_kind is not None and not isinstance(self.origin_kind, OriginKind):
            raise WorkSelectionError("invalid origin kind")
        if not isinstance(self.provenance, Provenance):
            raise WorkSelectionError("candidate requires source provenance")


@dataclass(frozen=True, slots=True)
class WorkSelectionRound:
    """Transient CPU-created meta task; it owns no semantic Goal or Intent."""

    task: CognitiveTask
    request: BoundedChoiceRequest
    candidates: tuple[CognitiveWorkCandidate, ...]
    present_revision: int
    registry_revision: int
    owner_revision: int

    def __post_init__(self) -> None:
        if self.task.requirement is not TaskRequirement.SELECT_FINITE:
            raise WorkSelectionError("selection task must be finite")
        if self.task.question_ref is not None or self.task.intent_ref is not None:
            raise WorkSelectionError("meta task cannot forge an adopted origin")
        if self.request.request_id != self.task.task_ref:
            raise WorkSelectionError("selection request/task mismatch")
        if self.request.choices != self.task.choices or self.request.think_allowed:
            raise WorkSelectionError("L1 choices mismatch or hidden THINK enabled")
        for key in ("present_revision", "registry_revision", "owner_revision"):
            _nonnegative(key, getattr(self, key))


@dataclass(frozen=True, slots=True)
class WorkSelectionProposal:
    """Validated L1 output for Self owner to accept, reject, or hold."""

    task_ref: str
    generation: int
    choice_id: str
    candidate: CognitiveWorkCandidate | None
    result_provenance: Provenance

    @property
    def requires_owner_adoption(self) -> bool:
        return self.candidate is not None and self.candidate.origin_kind is None


def _text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise WorkSelectionError(f"{name} must be nonempty text")


def _nonnegative(name: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise WorkSelectionError(f"{name} must be nonnegative integer")


def _origin_is_live(candidate: CognitiveWorkCandidate, present: PresentFrame) -> bool:
    if candidate.origin_kind is None:
        return candidate.origin_ref in {s.envelope.event_id for s in present.signals}
    refs = {
        OriginKind.QUESTION: present.active_question_refs,
        OriginKind.GOAL: present.active_goal_refs,
        OriginKind.INTENT: present.active_intent_refs,
    }[candidate.origin_kind]
    return candidate.origin_ref in refs


def _lens_references(present: PresentFrame) -> dict[str, list[dict[str, str | None]]]:
    result: dict[str, list[dict[str, str | None]]] = {}
    for name, view in (
        ("my_self", present.three_self.my_self),
        ("self_world", present.three_self.self_world),
        ("self_body", present.three_self.self_body),
    ):
        result[name] = [
            {"claim": c.claim_key, "status": c.status.value, "value_ref": c.value_ref}
            for c in sorted(view.claims, key=lambda c: c.claim_key)
        ]
    return result


def propose_work_selection(
    *,
    present: PresentFrame,
    envelope: CommonEnvelope,
    candidates: tuple[CognitiveWorkCandidate, ...],
    owner_revision: int,
    task_ref: str,
    generation: int,
    deadline_ns: int,
    context_provenance: Provenance,
    identity_context: CognitionDatum | None = None,
) -> WorkSelectionRound | None:
    """Prepare one L1 choice without first adopting a Goal.

    Candidates are supplied by the Self's existing semantic owner/known patterns.
    No candidates -> no model request. One candidate -> candidate plus no-work.
    Neither a candidate nor L1's answer creates an actual CognitiveTask owner.
    """
    if not isinstance(present, PresentFrame):
        raise WorkSelectionError("Present must be owner-qualified PresentFrame")
    if not isinstance(envelope, CommonEnvelope) or envelope.kind != "COGNITIVE_TASK":
        raise WorkSelectionError("meta task requires COGNITIVE_TASK envelope")
    if envelope.scope != present.three_self.scope:
        raise WorkSelectionError("foreign Self/world session")
    if envelope.received_at is None or envelope.received_at.domain is not Clock.HOST_MONOTONIC_NS:
        raise WorkSelectionError("meta task requires host reception clock")
    if not isinstance(context_provenance, Provenance):
        raise WorkSelectionError("context requires provenance")
    _text("task_ref", task_ref)
    _nonnegative("owner_revision", owner_revision)
    _nonnegative("generation", generation)
    _nonnegative("deadline_ns", deadline_ns)
    if deadline_ns <= envelope.received_at.value:
        raise WorkSelectionError("deadline must follow reception")
    if not isinstance(candidates, tuple) or any(
        not isinstance(c, CognitiveWorkCandidate) for c in candidates
    ):
        raise WorkSelectionError("candidates must be typed tuple")
    if len({c.candidate_ref for c in candidates}) != len(candidates):
        raise WorkSelectionError("duplicate work candidate")
    for candidate in candidates:
        if not _origin_is_live(candidate, present):
            raise WorkSelectionError("work candidate origin not live in Present")
    if not candidates:
        return None

    ordered = tuple(sorted(candidates, key=lambda c: c.candidate_ref))
    choices = tuple(
        BoundedChoice(c.candidate_ref, c.description) for c in ordered
    ) + (BoundedChoice(NO_NEW_WORK, "Do not start new cognitive work now"),)
    task = CognitiveTask(
        envelope=envelope, task_ref=task_ref,
        requirement=TaskRequirement.SELECT_FINITE,
        source_revision_refs=present.three_self.source_revision_refs,
        deadline_ns=deadline_ns, generation=generation, choices=choices,
    )
    context = (
        CognitionDatum.from_value(
            "present_projection",
            {
                "frame_revision": present.frame_revision,
                "registry_revision": present.registry_revision,
                "epoch_ref": present.three_self.epoch_ref,
                "active_questions": present.active_question_refs,
                "active_goals": present.active_goal_refs,
                "active_intents": present.active_intent_refs,
                "need_refs": present.need_refs,
                "attention_refs": present.attention_refs,
                "lenses": _lens_references(present),
            },
            context_provenance,
        ),
        CognitionDatum.from_value(
            "schema_signals",
            [
                {
                    "event_ref": s.envelope.event_id,
                    "schema_id": s.schema_id,
                    "signal_kind": s.signal_kind,
                    "epistemic_status": s.epistemic_status,
                    "question_target_ref": (
                        s.question_candidate.unknown_target_ref
                        if s.question_candidate is not None else None
                    ),
                }
                for s in sorted(present.signals, key=lambda s: s.envelope.event_id)
            ],
            context_provenance,
        ),
    )
    request = BoundedChoiceRequest(
        request_id=task_ref,
        instruction=(
            "Choose the next cognitive work from the supplied, source-qualified "
            "candidates using Present and Schema signals. You may choose no new "
            "work. Never infer unknown World facts, select physical Actions, "
            "adopt Goals, or invent choices."
        ),
        intent_id=None,
        focus="cognitive_work_selection",
        choices=choices,
        context=context,
        identity_context=identity_context,
        think_allowed=False,
    )
    return WorkSelectionRound(
        task=task, request=request, candidates=ordered,
        present_revision=present.frame_revision,
        registry_revision=present.registry_revision,
        owner_revision=owner_revision,
    )


def accept_selected_work(
    round_: WorkSelectionRound,
    *,
    result: CognitionResultReceipt,
    route: ProfileDecision,
    present: PresentFrame,
    current_source_revision_refs: tuple[str, ...],
    current_present_revision: int,
    current_registry_revision: int,
    current_owner_revision: int,
    current_generation: int,
    now_ns: int,
    compute_admitted: bool,
) -> WorkSelectionProposal:
    """Validate an L1 choice; return a proposal for the original Self owner.

    The existing result_is_current enforces task/profile/choice/deadline and
    compute admission. Caller-owned current revisions fence stale Present.
    UNRESOLVED is not an implicit L2 task or automatic reconsideration.
    """
    if not isinstance(round_, WorkSelectionRound) or not isinstance(
        present, PresentFrame
    ):
        raise WorkSelectionError("invalid selection round or Present")
    for key, value in (
        ("current_present_revision", current_present_revision),
        ("current_registry_revision", current_registry_revision),
        ("current_owner_revision", current_owner_revision),
        ("current_generation", current_generation),
        ("now_ns", now_ns),
    ):
        _nonnegative(key, value)
    if (
        present.three_self.scope != round_.task.envelope.scope
        or present.three_self.source_revision_refs != current_source_revision_refs
        or round_.task.source_revision_refs != current_source_revision_refs
        or present.frame_revision != round_.present_revision
        or current_present_revision != round_.present_revision
        or present.registry_revision != round_.registry_revision
        or current_registry_revision != round_.registry_revision
        or current_owner_revision != round_.owner_revision
        or current_generation != round_.task.generation
        or any(not _origin_is_live(c, present) for c in round_.candidates)
    ):
        raise WorkSelectionError("stale selection owner/frame/schema/origin")
    if route.selected is not Profile.L1 or not result_is_current(
        result, round_.task, route,
        scope=present.three_self.scope,
        current_source_revision_refs=current_source_revision_refs,
        now_ns=now_ns, compute_admitted=compute_admitted,
    ):
        raise WorkSelectionError("selection result not admitted or unresolved")
    candidate = next(
        (c for c in round_.candidates if c.candidate_ref == result.choice_id), None
    )
    if candidate is None and result.choice_id != NO_NEW_WORK:
        raise WorkSelectionError("invented cognitive work choice")
    return WorkSelectionProposal(
        task_ref=round_.task.task_ref,
        generation=round_.task.generation,
        choice_id=result.choice_id,
        candidate=candidate,
        result_provenance=result.provenance,
    )
