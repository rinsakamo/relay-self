"""Target-specific, read-only MinecraftPresent -> SelfWorld observation adapter.

A native entity registry is bounded visibility, NOT a World census.
This adapter does not peek at other Self memory, intentions or prediction.
"""
from __future__ import annotations

from adapters.mineflayer.present_projection import MinecraftPresent
from relay_self.self_world import (
    InvalidSelfWorldData,
    WorldEntityObservation,
    WorldObservation,
)


def project_self_world_present(
    present: MinecraftPresent,
    *,
    observer_id: str,
    observed_at_ns: int | None = None,
) -> WorldObservation:
    """Only explicitly observed exterior facts are exposed to one Self.

    Observed time, if supplied, must be independently source-qualified by the
    caller; this projection cannot attest the physical clock or event origin.
    """
    if not isinstance(present, MinecraftPresent):
        raise InvalidSelfWorldData("requires existing MinecraftPresent")
    if (present.provenance.source != "mineflayer"
            or present.provenance.reference != f"{present.session_id}:{present.seq}"):
        raise InvalidSelfWorldData("foreign or mismatched Mineflayer source provenance")
    if present.coverage_candidates < len(present.observed_entities):
        raise InvalidSelfWorldData("incomplete entity coverage")
    entities = tuple(
        WorldEntityObservation(
            entity_ref=f"entity-{entity.entity_id}",
            label=entity.name,
            position=entity.position,
            distance_m=entity.distance_m,
        )
        for entity in present.observed_entities
    )
    return WorldObservation(
        observer_id=observer_id,
        session_id=present.session_id,
        native_seq=present.seq,
        request_id=present.request_id,
        entities=entities,
        coverage_scope=present.coverage_scope,
        coverage_radius_m=present.coverage_radius_m,
        coverage_cap=present.coverage_cap,
        coverage_candidates=present.coverage_candidates,
        coverage_truncated=present.coverage_truncated,
        provenance=present.provenance,
        observed_at_ns=observed_at_ns,
    )
