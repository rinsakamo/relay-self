from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.python_protocol import (
    MineflayerEntityFact,
    MineflayerObservation,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance

SEEK_FOCUS = "SEEK"


class SeekExperimentError(ValueError):
    """Raised when the bounded SEEK experiment input is invalid."""


class SeekStatus(str, Enum):
    FOUND = "found"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class SeekBinding:
    """Explicit target binding for the experiment-local SEEK operation."""

    target_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.target_name, str) or not self.target_name.strip():
            raise SeekExperimentError(
                "SEEK target_name must be non-empty text"
            )


@dataclass(frozen=True, slots=True)
class SeekSurface:
    """One transient SEEK-local problem under an existing parent intent."""

    parent_intent_id: str
    parent_objective: str
    focus: str
    binding: SeekBinding
    observation: MineflayerObservation

    def __post_init__(self) -> None:
        if not self.parent_intent_id.strip():
            raise SeekExperimentError(
                "SEEK surface requires a parent intent id"
            )
        if not self.parent_objective.strip():
            raise SeekExperimentError(
                "SEEK surface requires a parent objective"
            )
        if self.focus != SEEK_FOCUS:
            raise SeekExperimentError(
                "SEEK surface focus must remain SEEK"
            )
        if not isinstance(self.binding, SeekBinding):
            raise SeekExperimentError(
                "SEEK surface requires a SeekBinding"
            )
        if not isinstance(self.observation, MineflayerObservation):
            raise SeekExperimentError(
                "SEEK surface requires MineflayerObservation"
            )


@dataclass(frozen=True, slots=True)
class SeekResult:
    """Transient result over one bounded observation surface."""

    status: SeekStatus
    surface: SeekSurface
    matches: tuple[MineflayerEntityFact, ...]
    observation_provenance: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.status, SeekStatus):
            raise SeekExperimentError(
                "SEEK result status must be SeekStatus"
            )
        if not isinstance(self.surface, SeekSurface):
            raise SeekExperimentError(
                "SEEK result requires a SeekSurface"
            )
        if not isinstance(self.matches, tuple) or not all(
            isinstance(entity, MineflayerEntityFact)
            for entity in self.matches
        ):
            raise SeekExperimentError(
                "SEEK matches must be MineflayerEntityFact values"
            )
        if not isinstance(self.observation_provenance, Provenance):
            raise SeekExperimentError(
                "SEEK result requires observation Provenance"
            )
        if self.status is SeekStatus.FOUND and not self.matches:
            raise SeekExperimentError(
                "FOUND SEEK result requires at least one match"
            )
        if self.status is SeekStatus.UNRESOLVED and self.matches:
            raise SeekExperimentError(
                "UNRESOLVED SEEK result cannot carry matches"
            )


def project_seek_surface(
    observation: MineflayerObservation,
    *,
    intent_commitment: IntentCommitment,
    binding: SeekBinding,
) -> SeekSurface:
    """Project one child-local SEEK problem without starting a Skill lifecycle."""

    if not isinstance(observation, MineflayerObservation):
        raise SeekExperimentError(
            "SEEK projection requires MineflayerObservation"
        )
    if not isinstance(intent_commitment, IntentCommitment):
        raise SeekExperimentError(
            "SEEK projection requires IntentCommitment"
        )
    if not isinstance(binding, SeekBinding):
        raise SeekExperimentError(
            "SEEK projection requires SeekBinding"
        )

    current = intent_commitment.current_intent
    if current is None:
        raise SeekExperimentError(
            "SEEK projection requires a Current Intent"
        )

    return SeekSurface(
        parent_intent_id=current.intent_id,
        parent_objective=current.objective,
        focus=SEEK_FOCUS,
        binding=binding,
        observation=observation,
    )


def resolve_seek(surface: SeekSurface) -> SeekResult:
    """Resolve only what the current bounded entity observation establishes."""

    if not isinstance(surface, SeekSurface):
        raise SeekExperimentError(
            "SEEK resolution requires a SeekSurface"
        )

    matches = tuple(
        entity
        for entity in surface.observation.snapshot.nearby_entities
        if entity.name == surface.binding.target_name
    )
    status = (
        SeekStatus.FOUND
        if matches
        else SeekStatus.UNRESOLVED
    )
    return SeekResult(
        status=status,
        surface=surface,
        matches=matches,
        observation_provenance=surface.observation.provenance,
    )


def run_seek(
    observation: MineflayerObservation,
    *,
    intent_commitment: IntentCommitment,
    target_name: str,
) -> SeekResult:
    """Use the same transient SEEK operation for any parent Current Intent."""

    surface = project_seek_surface(
        observation,
        intent_commitment=intent_commitment,
        binding=SeekBinding(target_name=target_name),
    )
    return resolve_seek(surface)
