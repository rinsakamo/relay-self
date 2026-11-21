from dataclasses import dataclass
from enum import Enum

from relay_self.provenance import Provenance


class AppraisalError(ValueError):
    """Base error for the minimum executable appraisal representation."""


class InvalidAppraisalData(AppraisalError):
    """Raised when appraisal state or projection input is malformed."""


class AppraisalTargetKind(str, Enum):
    """Scope of one persistent appraisal tendency."""

    ENTITY_CLASS = "ENTITY_CLASS"
    ENTITY_INSTANCE = "ENTITY_INSTANCE"


class AppraisalAspect(str, Enum):
    """Independent directional appraisal dimensions implemented by Self 1.0."""

    HARM_LIKELIHOOD = "HARM_LIKELIHOOD"
    AFFILIATION_LIKELIHOOD = "AFFILIATION_LIKELIHOOD"


class AppraisalBias(str, Enum):
    """Directional prior only; this is not an emotion or action score."""

    DOWN = "DOWN"
    NEUTRAL = "NEUTRAL"
    UP = "UP"


@dataclass(frozen=True, slots=True)
class AppraisalDisposition:
    """Persistent Self-owned tendency for one target scope and appraisal aspect."""

    target_kind: AppraisalTargetKind
    target_key: str
    aspect: AppraisalAspect
    bias: AppraisalBias
    source_provenance: Provenance
    integration_provenance: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.target_kind, AppraisalTargetKind):
            raise InvalidAppraisalData(
                "target_kind must be AppraisalTargetKind"
            )
        _require_text("target_key", self.target_key)
        if not isinstance(self.aspect, AppraisalAspect):
            raise InvalidAppraisalData("aspect must be AppraisalAspect")
        if not isinstance(self.bias, AppraisalBias):
            raise InvalidAppraisalData("bias must be AppraisalBias")
        _require_provenance("source_provenance", self.source_provenance)
        _require_provenance(
            "integration_provenance",
            self.integration_provenance,
        )

    @property
    def key(self) -> tuple[AppraisalTargetKind, str, AppraisalAspect]:
        return (self.target_kind, self.target_key, self.aspect)


@dataclass(frozen=True, slots=True)
class CurrentAppraisal:
    """Transient Self-relative projection for one currently observed entity."""

    entity_class: str
    entity_instance: str | None
    observation_provenance: Provenance
    active_dispositions: tuple[AppraisalDisposition, ...]

    def __post_init__(self) -> None:
        _require_text("entity_class", self.entity_class)
        if self.entity_instance is not None:
            _require_text("entity_instance", self.entity_instance)
        _require_provenance(
            "observation_provenance",
            self.observation_provenance,
        )
        if not isinstance(self.active_dispositions, tuple) or not all(
            isinstance(disposition, AppraisalDisposition)
            for disposition in self.active_dispositions
        ):
            raise InvalidAppraisalData(
                "active_dispositions must be AppraisalDisposition tuple"
            )

    def bias_for(self, aspect: AppraisalAspect) -> AppraisalBias:
        if not isinstance(aspect, AppraisalAspect):
            raise InvalidAppraisalData("aspect must be AppraisalAspect")
        for disposition in self.active_dispositions:
            if disposition.aspect is aspect:
                return disposition.bias
        return AppraisalBias.NEUTRAL


def project_entity_appraisal(
    *,
    entity_class: str,
    entity_instance: str | None,
    observation_provenance: Provenance,
    dispositions: tuple[AppraisalDisposition, ...],
) -> CurrentAppraisal:
    """Project class priors plus exact-instance experience into the Present.

    Instance-scoped evidence overrides a class-scoped tendency only for the
    same appraisal aspect. Nothing here establishes enemy/ally truth or
    authorizes an Action.
    """

    _require_text("entity_class", entity_class)
    if entity_instance is not None:
        _require_text("entity_instance", entity_instance)
    _require_provenance("observation_provenance", observation_provenance)
    if not isinstance(dispositions, tuple) or not all(
        isinstance(disposition, AppraisalDisposition)
        for disposition in dispositions
    ):
        raise InvalidAppraisalData(
            "dispositions must be AppraisalDisposition tuple"
        )

    seen: set[
        tuple[AppraisalTargetKind, str, AppraisalAspect]
    ] = set()
    for disposition in dispositions:
        if disposition.key in seen:
            raise InvalidAppraisalData(
                "duplicate appraisal disposition key in projection"
            )
        seen.add(disposition.key)

    selected: dict[AppraisalAspect, AppraisalDisposition] = {}

    for disposition in dispositions:
        if (
            disposition.target_kind is AppraisalTargetKind.ENTITY_CLASS
            and disposition.target_key == entity_class
        ):
            selected[disposition.aspect] = disposition

    if entity_instance is not None:
        for disposition in dispositions:
            if (
                disposition.target_kind is AppraisalTargetKind.ENTITY_INSTANCE
                and disposition.target_key == entity_instance
            ):
                selected[disposition.aspect] = disposition

    return CurrentAppraisal(
        entity_class=entity_class,
        entity_instance=entity_instance,
        observation_provenance=observation_provenance,
        active_dispositions=tuple(
            selected[aspect]
            for aspect in AppraisalAspect
            if aspect in selected
        ),
    )


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidAppraisalData(f"{name} must be a non-empty string")


def _require_provenance(name: str, value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidAppraisalData(f"{name} must be Provenance")
