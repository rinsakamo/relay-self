"""D Lane D3: bounded owner-retained Question and L2 attempt continuity.

Stored solely inside the ORIGINAL PersistentCognition file. The owner must
serialize/persist a RESERVED attempt BEFORE any GPU dispatch; the CPU adapter
cannot send to a model, authorize physical actions, or attest a World fork.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from relay_self.cognitive_minimal_dev import WorldPercept
from relay_self.common_io import ScopeRef
from relay_self.exploration_goal_dev import (
    ExplorationL2Task,
    ExplorationRound,
    L2TargetReview,
    prepare_exploration_l2,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import OpenCognitionRequest

if TYPE_CHECKING:
    from relay_self.cognitive_minimal_dev import Selection
    from relay_self.persistent_cognition import PersistentCognition


class ExplorationContinuityError(ValueError):
    """Refuse inconsistent, stale or potentially replayed owner cognition."""


class AttemptPhase(str, Enum):
    RESERVED = "RESERVED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"
    UNRESOLVED = "UNRESOLVED"
    REFERENCED_OBSERVED_TARGET = "REFERENCED_OBSERVED_TARGET"


@dataclass(frozen=True, slots=True)
class QuestionRecord:
    """A Question belongs to the Self, not to a WorldBody or L2 worker."""

    question_ref: str
    origin: Provenance
    open: bool = True

    def __post_init__(self) -> None:
        _text("question ref", self.question_ref)
        if not isinstance(self.origin, Provenance) or type(self.open) is not bool:
            raise ExplorationContinuityError("typed Question origin/open required")


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    """A pre-dispatch reservation survives crash, timeout or new native JOIN."""

    attempt_ref: str
    question_ref: str
    evidence_digest: str
    phase: AttemptPhase
    owner_provenance: Provenance

    def __post_init__(self) -> None:
        _text("attempt ref", self.attempt_ref)
        _text("attempt question ref", self.question_ref)
        if (type(self.evidence_digest) is not str
                or len(self.evidence_digest) != 64
                or any(c not in "0123456789abcdef" for c in self.evidence_digest)):
            raise ExplorationContinuityError("attempt evidence digest must be SHA256")
        if not isinstance(self.phase, AttemptPhase) or not isinstance(
            self.owner_provenance, Provenance
        ):
            raise ExplorationContinuityError("typed attempt phase/owner required")


@dataclass(frozen=True, slots=True)
class ExplorationContinuity:
    """Original owner-controlled immutable cognition extension, no new DB."""

    self_id: str
    revision: int
    questions: tuple[QuestionRecord, ...] = ()
    attempts: tuple[AttemptRecord, ...] = ()

    def __post_init__(self) -> None:
        _text("Self ID", self.self_id)
        _nat("continuity revision", self.revision)
        if (type(self.questions) is not tuple or len(self.questions) > 64
                or any(not isinstance(q, QuestionRecord) for q in self.questions)):
            raise ExplorationContinuityError("invalid/beyond-limit Question history")
        if (type(self.attempts) is not tuple or len(self.attempts) > 256
                or any(not isinstance(a, AttemptRecord) for a in self.attempts)):
            raise ExplorationContinuityError("invalid/beyond-limit attempt history")
        refs = [q.question_ref for q in self.questions]
        if len(refs) != len(set(refs)):
            raise ExplorationContinuityError("duplicate Question ref")
        attempts = [a.attempt_ref for a in self.attempts]
        if len(attempts) != len(set(attempts)):
            raise ExplorationContinuityError("duplicate attempt ref")
        pairs = [(a.question_ref, a.evidence_digest) for a in self.attempts]
        if len(pairs) != len(set(pairs)) or any(
            a.question_ref not in refs for a in self.attempts
        ):
            raise ExplorationContinuityError("duplicate or orphan Question attempt")
        for a in self.attempts:
            if a.attempt_ref != _attempt_ref(self.self_id, a.question_ref,
                                             a.evidence_digest):
                raise ExplorationContinuityError("attempt ID digest mismatch")


def _text(name: str, value: object) -> str:
    if type(value) is not str or not value.strip() or len(value) > 256:
        raise ExplorationContinuityError(f"{name} must be bounded text")
    return value


def _nat(name: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ExplorationContinuityError(f"{name} must be nonnegative int")
    return value


def _exact(obj: object, fields: set[str], label: str) -> dict[str, Any]:
    if type(obj) is not dict or set(obj) != fields:
        raise ExplorationContinuityError(f"{label}: exact fields required")
    return obj


def _sha(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _attempt_ref(self_id: str, question_ref: str, evidence_digest: str) -> str:
    return "l2-attempt:v1:" + _sha([self_id, question_ref, evidence_digest])


def _current(cognition: PersistentCognition) -> ExplorationContinuity:
    from relay_self.persistent_cognition import PersistentCognition

    if not isinstance(cognition, PersistentCognition):
        raise ExplorationContinuityError("original PersistentCognition required")
    state = cognition.exploration_continuity
    if state is None:
        return ExplorationContinuity(cognition.identity.self_id, 0)
    if state.self_id != cognition.identity.self_id:
        raise ExplorationContinuityError("foreign Self continuity")
    return state


def retain_open_question(
    cognition: PersistentCognition,
    *,
    question_ref: str,
    origin: Provenance,
    expected_revision: int,
    current_present_question_refs: tuple[str, ...],
) -> PersistentCognition:
    """The original Self owner decides to retain an already active Question.

    No Question is synthesized from L2, raw WorldBody or unknown observations.
    """
    state = _current(cognition)
    _nat("expected revision", expected_revision)
    _text("Question", question_ref)
    if (expected_revision != state.revision
            or not isinstance(origin, Provenance)
            or question_ref not in current_present_question_refs):
        raise ExplorationContinuityError("stale/unprojected Question")
    if any(q.question_ref == question_ref for q in state.questions):
        raise ExplorationContinuityError("Question already registered")
    next_state = replace(
        state, revision=state.revision + 1,
        questions=(*state.questions, QuestionRecord(question_ref, origin)),
    )
    return cognition.retain_exploration_continuity(
        next_state, expected_revision=state.revision,
    )


def open_question_refs(
    cognition: PersistentCognition,
    *, expected_self_id: str,
) -> tuple[str, ...]:
    """Inert refs after a verified owner-generation restore.

    They must be projected by the original Present owner; this does NOT
    requalify their evidence as current World observations.
    """
    state = _current(cognition)
    if state.self_id != expected_self_id:
        raise ExplorationContinuityError("foreign restored Self cognition")
    return tuple(q.question_ref for q in state.questions if q.open)


def _evidence_digest(round_: ExplorationRound, question_ref: str) -> str:
    """Semantic evidence key; native session/source/owner epoch are excluded.

    Merely rejoining/revising the owner cannot relaunch the same Question.
    A genuinely changed referenced epistemic basis can admit a fresh attempt.
    """
    if question_ref not in round_.present.active_question_refs:
        raise ExplorationContinuityError("Question is not current in Present")
    basis = sorted({
        (e.kind.value, e.present_ref, e.status.value)
        for e in round_.need.basis
    })
    if not basis:
        raise ExplorationContinuityError("empty evidence cannot authorize retry")
    return _sha([question_ref, basis])


@dataclass(frozen=True, slots=True)
class L2Reservation:
    """One source/native-session bound *candidate*, not a dispatch grant."""

    task: ExplorationL2Task
    attempt_ref: str
    owner_state_revision: int
    intent_owner_revision: int
    native_session_ref: str


def reserve_exploration_l2(
    cognition: PersistentCognition,
    *,
    round_: ExplorationRound,
    selection: Selection,
    expected_revision: int,
    current_intent_owner_revision: int,
    native_session_ref: str,
    owner_provenance: Provenance,
) -> tuple[PersistentCognition, L2Reservation | None]:
    """Stage a crash-safe RESERVED record before model dispatch.

    If identical semantic evidence has *ever* been reserved (including
    CANCELLED/TIMEOUT/UNRESOLVED), no automatic retry can be prepared.
    """
    state = _current(cognition)
    _nat("expected continuity revision", expected_revision)
    _text("native session ref", native_session_ref)
    if not isinstance(owner_provenance, Provenance):
        raise ExplorationContinuityError("original Self owner provenance required")
    if (state.revision != expected_revision
            or state.self_id != round_.present.three_self.scope.self_id
            or round_.owner_revision != current_intent_owner_revision):
        raise ExplorationContinuityError("foreign/stale owner revision")
    task = prepare_exploration_l2(
        round_, selection=selection,
        current_owner_revision=current_intent_owner_revision,
        attempted_keys=frozenset(),
    )
    if task is None:
        return cognition, None
    question = next((q for q in state.questions
                     if q.question_ref == task.question_ref), None)
    if question is None or not question.open:
        raise ExplorationContinuityError("unretained or closed L2 Question")
    digest = _evidence_digest(round_, task.question_ref)
    if any(a.question_ref == task.question_ref
           and a.evidence_digest == digest for a in state.attempts):
        return cognition, None
    attempt = AttemptRecord(
        _attempt_ref(state.self_id, task.question_ref, digest),
        task.question_ref, digest, AttemptPhase.RESERVED,
        owner_provenance,
    )
    next_state = replace(
        state, revision=state.revision + 1,
        attempts=(*state.attempts, attempt),
    )
    updated = cognition.retain_exploration_continuity(
        next_state, expected_revision=state.revision,
    )
    return updated, L2Reservation(
        task=task, attempt_ref=attempt.attempt_ref,
        owner_state_revision=next_state.revision,
        intent_owner_revision=current_intent_owner_revision,
        native_session_ref=native_session_ref,
    )


def validate_persisted_l2_reservation(
    original_owner_cognition_path: str | Path,
    *,
    reservation: L2Reservation,
    current_scope: ScopeRef,
    current_native_session_ref: str,
    current_intent_owner_revision: int,
    current_source_revision_refs: tuple[str, ...],
) -> OpenCognitionRequest:
    """Read back the **original owner's** durable file before external L2.

    The caller must separately own and attest its current GPU work lease.
    D never invokes a model. After a rejoin, a past reservation is inert.
    """
    from relay_self.persistent_cognition import load_persistent_cognition

    if not isinstance(reservation, L2Reservation) or not isinstance(
        current_scope, ScopeRef
    ):
        raise ExplorationContinuityError("typed owner reservation required")
    _text("current native session", current_native_session_ref)
    _nat("current owner revision", current_intent_owner_revision)
    task = reservation.task
    if (
        current_scope != task.scope
        or current_native_session_ref != reservation.native_session_ref
        or current_intent_owner_revision != reservation.intent_owner_revision
        or current_source_revision_refs != task.source_revision_refs
    ):
        raise ExplorationContinuityError("stale L2 session/world/owner")
    saved = _current(load_persistent_cognition(original_owner_cognition_path))
    if (
        saved.self_id != task.scope.self_id
        or saved.revision != reservation.owner_state_revision
        or not any(q.open and q.question_ref == task.question_ref
                   for q in saved.questions)
        or not any(a.attempt_ref == reservation.attempt_ref
                   and a.question_ref == task.question_ref
                   and a.phase is AttemptPhase.RESERVED
                   for a in saved.attempts)
    ):
        raise ExplorationContinuityError("L2 reservation not durably committed")
    return task.request


def record_l2_attempt_result(
    cognition: PersistentCognition,
    *,
    reservation: L2Reservation,
    phase: AttemptPhase,
    expected_revision: int,
    reviewed_target: L2TargetReview | None = None,
    current_percept: WorldPercept | None = None,
    current_source_revision_refs: tuple[str, ...] = (),
) -> PersistentCognition:
    """Owner-mediated terminal audit, without closing the Question.

    Result status is not a new Target, a World fact or an Action outcome.
    """
    state = _current(cognition)
    if (not isinstance(reservation, L2Reservation)
            or phase is AttemptPhase.RESERVED
            or not isinstance(phase, AttemptPhase)
            or state.revision != expected_revision
            or state.self_id != reservation.task.scope.self_id
            or state.revision < reservation.owner_state_revision):
        raise ExplorationContinuityError("stale/invalid terminal L2 record")
    if phase is AttemptPhase.REFERENCED_OBSERVED_TARGET:
        if (not isinstance(reviewed_target, L2TargetReview)
                or reviewed_target.status != "REFERENCED_OBSERVED_TARGET"
                or reviewed_target.target is None
                or reviewed_target.question_ref != reservation.task.question_ref
                or not isinstance(current_percept, WorldPercept)
                or current_percept.scope != reservation.task.scope
                or current_source_revision_refs != reservation.task.source_revision_refs
                or not any(
                    t == reviewed_target.target and t.live
                    and t.observed_sequence <= current_percept.sequence
                    for t in current_percept.targets
                )):
            raise ExplorationContinuityError(
                "resolved reference requires prior typed current World review"
            )
    elif (reviewed_target is not None or current_percept is not None
          or current_source_revision_refs):
        raise ExplorationContinuityError("unresolved result cannot cite a target")
    index = next((i for i, a in enumerate(state.attempts)
                  if a.attempt_ref == reservation.attempt_ref), None)
    if index is None or state.attempts[index].phase is not AttemptPhase.RESERVED:
        raise ExplorationContinuityError("attempt not pending; duplicate result")
    updated = list(state.attempts)
    updated[index] = replace(updated[index], phase=phase)
    next_state = replace(
        state, revision=state.revision + 1, attempts=tuple(updated),
    )
    return cognition.retain_exploration_continuity(
        next_state, expected_revision=state.revision,
    )


def encode_exploration_continuity(state: ExplorationContinuity) -> dict[str, Any]:
    if not isinstance(state, ExplorationContinuity):
        raise ExplorationContinuityError("typed continuity required")
    return {
        "schema_version": 1, "self_id": state.self_id, "revision": state.revision,
        "questions": [
            {"question_ref": q.question_ref, "open": q.open,
             "origin": {"source": q.origin.source, "reference": q.origin.reference}}
            for q in state.questions
        ],
        "attempts": [
            {"attempt_ref": a.attempt_ref, "question_ref": a.question_ref,
             "evidence_digest": a.evidence_digest, "phase": a.phase.value,
             "owner_provenance": {
                 "source": a.owner_provenance.source,
                 "reference": a.owner_provenance.reference,
             }}
            for a in state.attempts
        ],
    }


def decode_exploration_continuity(
    payload: object, *, expected_self_id: str,
) -> ExplorationContinuity:
    root = _exact(
        payload, {"schema_version", "self_id", "revision", "questions", "attempts"},
        "continuity",
    )
    if root["schema_version"] != 1 or type(root["schema_version"]) is not int:
        raise ExplorationContinuityError("unsupported continuity version")
    if root["self_id"] != expected_self_id:
        raise ExplorationContinuityError("foreign Self continuity")
    def prov(value: object) -> Provenance:
        p = _exact(value, {"source", "reference"}, "provenance")
        return Provenance(_text("source", p["source"]),
                          _text("reference", p["reference"]))

    if type(root["questions"]) is not list or type(root["attempts"]) is not list:
        raise ExplorationContinuityError("Question/attempt arrays required")
    try:
        questions = tuple(QuestionRecord(
            _text("question_ref", (qv := _exact(
                q, {"question_ref", "open", "origin"}, "question"
            ))["question_ref"]),
            prov(qv["origin"]),
            qv["open"],
        ) for q in root["questions"])
        attempts = tuple(AttemptRecord(
            _text("attempt_ref", (av := _exact(
                a, {"attempt_ref", "question_ref", "evidence_digest",
                    "phase", "owner_provenance"}, "attempt"
            ))["attempt_ref"]),
            _text("question_ref", av["question_ref"]),
            av["evidence_digest"], AttemptPhase(av["phase"]),
            prov(av["owner_provenance"]),
        ) for a in root["attempts"])
        return ExplorationContinuity(
            self_id=expected_self_id, revision=_nat(
                "continuity revision", root["revision"],
            ), questions=questions, attempts=attempts,
        )
    except (TypeError, ValueError) as exc:
        raise ExplorationContinuityError("invalid continuity record") from exc
