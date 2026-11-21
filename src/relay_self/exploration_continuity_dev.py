"""Self-owned exploration continuity and strict offline codec."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from relay_self.provenance import Provenance


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
