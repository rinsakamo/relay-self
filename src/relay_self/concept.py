from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.belief import BeliefAssessment
from relay_self.provenance import Provenance


class ConceptError(ValueError):
    """Base error for bounded structured concept classification."""


class InvalidConceptData(ConceptError):
    """Raised when concept keys, features, candidates, or criteria are malformed."""


class ConceptSourceUnavailable(ConceptError):
    """Raised when an explicitly source-dependent CNC route has no source result."""


class ConceptStatus(str, Enum):
    MATCHED = "matched"
    NOT_MATCHED = "not_matched"
    UNDETERMINED = "undetermined"


FeatureValue = bool | int | str


@dataclass(frozen=True, slots=True)
class ConceptKey:
    """Structured concept identity; no free-text concept parsing is performed."""

    domain: str
    name: str

    def __post_init__(self) -> None:
        _require_token("concept domain", self.domain)
        _require_token("concept name", self.name)

    @property
    def canonical(self) -> str:
        return f"{self.domain}:{self.name}"


@dataclass(frozen=True, slots=True)
class ConceptFeature:
    """One immutable caller-supplied structured feature."""

    key: str
    value: FeatureValue

    def __post_init__(self) -> None:
        _require_token("feature key", self.key)
        _require_feature_value(self.value)


@dataclass(frozen=True, slots=True)
class ConceptCandidate:
    """Immutable reference to caller-owned structured source material."""

    candidate_id: str
    payload_ref: str
    features: tuple[ConceptFeature, ...]
    provenance: Provenance
    source_refs: tuple[str, ...] = ()
    source_provenance: tuple[Provenance, ...] = ()

    def __post_init__(self) -> None:
        _require_text("candidate_id", self.candidate_id)
        _require_text("payload_ref", self.payload_ref)
        _validate_features("candidate features", self.features, allow_empty=True)
        if not isinstance(self.provenance, Provenance):
            raise InvalidConceptData("candidate provenance must be Provenance")
        _validate_text_tuple("source_refs", self.source_refs)
        if not isinstance(self.source_provenance, tuple) or not all(
            isinstance(value, Provenance)
            for value in self.source_provenance
        ):
            raise InvalidConceptData(
                "source_provenance must be a tuple of Provenance values"
            )


@dataclass(frozen=True, slots=True)
class ConceptCriterion:
    """Explicit membership rule for one structured concept."""

    criterion_id: str
    concept: ConceptKey
    required_features: tuple[ConceptFeature, ...]

    def __post_init__(self) -> None:
        _require_text("criterion_id", self.criterion_id)
        if not isinstance(self.concept, ConceptKey):
            raise InvalidConceptData("criterion concept must be ConceptKey")
        _validate_features(
            "required_features",
            self.required_features,
            allow_empty=False,
        )


@dataclass(frozen=True, slots=True)
class ConceptRepresentation:
    """Transient immutable classification result retaining source and rule identity."""

    source: ConceptCandidate
    criterion: ConceptCriterion
    status: ConceptStatus
    supporting_features: tuple[ConceptFeature, ...]
    missing_feature_keys: tuple[str, ...]
    mismatched_feature_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source, ConceptCandidate):
            raise InvalidConceptData("representation source must be ConceptCandidate")
        if not isinstance(self.criterion, ConceptCriterion):
            raise InvalidConceptData(
                "representation criterion must be ConceptCriterion"
            )
        if not isinstance(self.status, ConceptStatus):
            raise InvalidConceptData("representation status must be ConceptStatus")
        _validate_features(
            "supporting_features",
            self.supporting_features,
            allow_empty=True,
        )
        _validate_text_tuple("missing_feature_keys", self.missing_feature_keys)
        _validate_text_tuple(
            "mismatched_feature_keys",
            self.mismatched_feature_keys,
        )

    @property
    def concept(self) -> ConceptKey:
        return self.criterion.concept

    @property
    def candidate_id(self) -> str:
        return self.source.candidate_id


def classify_concept(
    candidate: ConceptCandidate,
    criterion: ConceptCriterion,
) -> ConceptRepresentation:
    """Classify one structured candidate under one explicit concept criterion.

    A present-but-different required value is an explicit NOT_MATCHED witness.
    If no required value contradicts the rule but at least one required key is
    absent, classification is UNDETERMINED. All required values matching yields
    MATCHED. No truth, belief, attention, or free-text inference is performed.
    """

    if not isinstance(candidate, ConceptCandidate):
        raise InvalidConceptData("candidate must be ConceptCandidate")
    if not isinstance(criterion, ConceptCriterion):
        raise InvalidConceptData("criterion must be ConceptCriterion")

    by_key = {feature.key: feature for feature in candidate.features}
    supporting: list[ConceptFeature] = []
    missing: list[str] = []
    mismatched: list[str] = []

    for requirement in criterion.required_features:
        observed = by_key.get(requirement.key)
        if observed is None:
            missing.append(requirement.key)
            continue
        if observed.value != requirement.value:
            mismatched.append(requirement.key)
            continue
        supporting.append(observed)

    if mismatched:
        status = ConceptStatus.NOT_MATCHED
    elif missing:
        status = ConceptStatus.UNDETERMINED
    else:
        status = ConceptStatus.MATCHED

    return ConceptRepresentation(
        source=candidate,
        criterion=criterion,
        status=status,
        supporting_features=tuple(supporting),
        missing_feature_keys=tuple(missing),
        mismatched_feature_keys=tuple(mismatched),
    )


def concept_candidate_from_belief(
    value: object,
    *,
    candidate_id: str,
    payload_ref: str,
    provenance: Provenance,
) -> ConceptCandidate:
    """Explicitly project an existing BLF result into structured CNC input.

    This bridge does not reassess evidence or alter belief status. The caller
    supplies the projection provenance and explicitly chooses to invoke it.
    """

    if not isinstance(value, BeliefAssessment):
        raise ConceptSourceUnavailable(
            "BLF-dependent CNC work requires an explicit BeliefAssessment"
        )
    if not isinstance(provenance, Provenance):
        raise InvalidConceptData("projection provenance must be Provenance")

    return ConceptCandidate(
        candidate_id=candidate_id,
        payload_ref=payload_ref,
        features=(
            ConceptFeature("source_kind", "belief_assessment"),
            ConceptFeature("belief_status", value.status.value),
            ConceptFeature("proposition", value.proposition.canonical),
        ),
        provenance=provenance,
        source_refs=(
            f"belief:{value.criterion_id}",
            f"proposition:{value.proposition.canonical}",
            *(f"evidence:{item.evidence_id}" for item in value.evidence),
        ),
        source_provenance=tuple(
            item.provenance
            for item in value.evidence
        ),
    )


def _validate_features(
    name: str,
    values: object,
    *,
    allow_empty: bool,
) -> None:
    if not isinstance(values, tuple) or not all(
        isinstance(value, ConceptFeature)
        for value in values
    ):
        raise InvalidConceptData(f"{name} must be a tuple of ConceptFeature values")
    if not allow_empty and not values:
        raise InvalidConceptData(f"{name} must not be empty")

    keys = tuple(value.key for value in values)
    if len(set(keys)) != len(keys):
        raise InvalidConceptData(f"{name} feature keys must be unique")


def _validate_text_tuple(name: str, values: object) -> None:
    if not isinstance(values, tuple):
        raise InvalidConceptData(f"{name} must be a tuple")
    seen: set[str] = set()
    for index, value in enumerate(values):
        _require_text(f"{name}[{index}]", value)
        if value in seen:
            raise InvalidConceptData(f"{name} must not contain duplicates: {value}")
        seen.add(value)


def _require_feature_value(value: object) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, int):
        return
    if isinstance(value, str):
        if not value or value != value.strip() or any(
            character.isspace()
            for character in value
        ):
            raise InvalidConceptData(
                "string feature values must be one non-empty structured token"
            )
        return
    raise InvalidConceptData(
        "feature value must be bool, int, or one structured string token"
    )


def _require_token(name: str, value: object) -> None:
    _require_text(name, value)
    assert isinstance(value, str)
    if value != value.strip() or any(character.isspace() for character in value):
        raise InvalidConceptData(
            f"{name} must be one structured token without whitespace"
        )
    if ":" in value:
        raise InvalidConceptData(f"{name} must not contain ':'")


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidConceptData(f"{name} must be a non-empty string")
