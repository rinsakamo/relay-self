from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.provenance import Provenance


class BeliefError(ValueError):
    """Base error for bounded belief assessment."""


class InvalidBeliefData(BeliefError):
    """Raised when proposition, evidence, criterion, or assessment data is malformed."""


class BeliefPropositionMismatch(BeliefError):
    """Raised when evidence for another proposition is mixed into one assessment."""


class EvidenceRelation(str, Enum):
    SUPPORT = "support"
    OPPOSE = "oppose"


class BeliefStatus(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    CONFLICTED = "conflicted"
    UNDETERMINED = "undetermined"


@dataclass(frozen=True, slots=True)
class PropositionKey:
    """Structured proposition identity; no free-text proposition parsing is performed."""

    domain: str
    subject: str
    predicate: str

    def __post_init__(self) -> None:
        _require_key_component("proposition domain", self.domain)
        _require_key_component("proposition subject", self.subject)
        _require_key_component("proposition predicate", self.predicate)

    @property
    def canonical(self) -> str:
        return f"{self.domain}:{self.subject}:{self.predicate}"


@dataclass(frozen=True, slots=True)
class BeliefEvidence:
    """One explicitly qualified evidence item about one structured proposition."""

    evidence_id: str
    proposition: PropositionKey
    relation: EvidenceRelation
    provenance: Provenance

    def __post_init__(self) -> None:
        _require_text("evidence_id", self.evidence_id)
        if not isinstance(self.proposition, PropositionKey):
            raise InvalidBeliefData("evidence proposition must be PropositionKey")
        if not isinstance(self.relation, EvidenceRelation):
            raise InvalidBeliefData("evidence relation must be EvidenceRelation")
        if not isinstance(self.provenance, Provenance):
            raise InvalidBeliefData("evidence provenance must be Provenance")


@dataclass(frozen=True, slots=True)
class BeliefCriterion:
    """Explicit orientation toward one proposition for one bounded assessment."""

    criterion_id: str
    proposition: PropositionKey

    def __post_init__(self) -> None:
        _require_text("criterion_id", self.criterion_id)
        if not isinstance(self.proposition, PropositionKey):
            raise InvalidBeliefData("criterion proposition must be PropositionKey")


@dataclass(frozen=True, slots=True)
class BeliefAssessment:
    """Transient proposition-level assessment with complete admitted evidence lineage."""

    criterion_id: str
    proposition: PropositionKey
    status: BeliefStatus
    evidence: tuple[BeliefEvidence, ...]

    def __post_init__(self) -> None:
        _require_text("criterion_id", self.criterion_id)
        if not isinstance(self.proposition, PropositionKey):
            raise InvalidBeliefData("assessment proposition must be PropositionKey")
        if not isinstance(self.status, BeliefStatus):
            raise InvalidBeliefData("assessment status must be BeliefStatus")
        if not isinstance(self.evidence, tuple) or not all(
            isinstance(value, BeliefEvidence)
            for value in self.evidence
        ):
            raise InvalidBeliefData(
                "assessment evidence must be a tuple of BeliefEvidence values"
            )

        _require_unique_evidence_ids(self.evidence)
        mismatched = tuple(
            item.evidence_id
            for item in self.evidence
            if item.proposition != self.proposition
        )
        if mismatched:
            raise BeliefPropositionMismatch(
                "assessment contains evidence for a different proposition: "
                + ", ".join(mismatched)
            )

        expected = _status_for(self.evidence)
        if self.status is not expected:
            raise InvalidBeliefData(
                "assessment status does not match admitted evidence relations"
            )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(item.evidence_id for item in self.evidence)

    @property
    def support_evidence(self) -> tuple[BeliefEvidence, ...]:
        return tuple(
            item
            for item in self.evidence
            if item.relation is EvidenceRelation.SUPPORT
        )

    @property
    def oppose_evidence(self) -> tuple[BeliefEvidence, ...]:
        return tuple(
            item
            for item in self.evidence
            if item.relation is EvidenceRelation.OPPOSE
        )


def assess_belief(
    evidence: tuple[BeliefEvidence, ...],
    criterion: BeliefCriterion,
) -> BeliefAssessment:
    """Deterministically assess one explicit proposition from qualified evidence.

    Evidence is not treated as World truth. All admitted evidence must already
    target the criterion proposition; mismatches fail closed rather than being
    silently ignored. Evidence order does not resolve conflict.
    """

    if not isinstance(evidence, tuple) or not all(
        isinstance(value, BeliefEvidence)
        for value in evidence
    ):
        raise InvalidBeliefData(
            "evidence must be a tuple of BeliefEvidence values"
        )
    if not isinstance(criterion, BeliefCriterion):
        raise InvalidBeliefData("criterion must be BeliefCriterion")

    _require_unique_evidence_ids(evidence)

    mismatched = tuple(
        item.evidence_id
        for item in evidence
        if item.proposition != criterion.proposition
    )
    if mismatched:
        raise BeliefPropositionMismatch(
            "belief assessment received evidence for a different proposition: "
            + ", ".join(mismatched)
        )

    return BeliefAssessment(
        criterion_id=criterion.criterion_id,
        proposition=criterion.proposition,
        status=_status_for(evidence),
        evidence=evidence,
    )


def _status_for(evidence: tuple[BeliefEvidence, ...]) -> BeliefStatus:
    has_support = any(
        item.relation is EvidenceRelation.SUPPORT
        for item in evidence
    )
    has_oppose = any(
        item.relation is EvidenceRelation.OPPOSE
        for item in evidence
    )

    if has_support and has_oppose:
        return BeliefStatus.CONFLICTED
    if has_support:
        return BeliefStatus.SUPPORTED
    if has_oppose:
        return BeliefStatus.UNSUPPORTED
    return BeliefStatus.UNDETERMINED


def _require_unique_evidence_ids(evidence: tuple[BeliefEvidence, ...]) -> None:
    ids = tuple(item.evidence_id for item in evidence)
    if len(set(ids)) != len(ids):
        raise InvalidBeliefData("evidence_id values must be unique")


def _require_key_component(name: str, value: object) -> None:
    _require_text(name, value)
    assert isinstance(value, str)
    if value != value.strip() or any(character.isspace() for character in value):
        raise InvalidBeliefData(
            f"{name} must be one structured token without whitespace"
        )
    if ":" in value:
        raise InvalidBeliefData(f"{name} must not contain ':'")


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidBeliefData(f"{name} must be a non-empty string")
