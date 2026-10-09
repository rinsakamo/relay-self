"""Target-specific, lossless-enough Mineflayer -> Present evidence projection.

No new cross-World API, danger label, truth owner, or persistent state.
The projection is an immutable native-source read (not a World census).
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.provenance import Provenance


class InvalidMineflayerPresent(ValueError):
    """Incomplete or non-correlated target source."""


@dataclass(frozen=True, slots=True)
class MinecraftEntityPresent:
    entity_id: int
    name: str | None
    distance_m: float
    position: tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class MinecraftPresent:
    session_id: str
    seq: int
    request_id: str
    body_position: tuple[float, float, float]
    health: float
    food: float
    food_saturation: float
    inventory: tuple[tuple[str, int, int], ...]
    observed_entities: tuple[MinecraftEntityPresent, ...]
    coverage_scope: str
    coverage_radius_m: float
    coverage_cap: int
    coverage_candidates: int
    coverage_truncated: bool
    provenance: Provenance


def project_mineflayer_present(reading: MineflayerObservation) -> MinecraftPresent:
    if (
        not isinstance(reading, MineflayerObservation)
        or reading.kind != "probe"
        or not reading.request_id
        or reading.provenance.source != "mineflayer"
    ):
        raise InvalidMineflayerPresent("requires correlated native Mineflayer probe")
    snapshot = reading.snapshot
    coverage = snapshot.nearby_entities_coverage
    if coverage.candidate_count < len(snapshot.nearby_entities):
        raise InvalidMineflayerPresent("impossible native candidate coverage")
    pos = snapshot.position
    return MinecraftPresent(
        session_id=reading.session_id,
        seq=reading.seq,
        request_id=reading.request_id,
        body_position=(pos.x, pos.y, pos.z),
        health=snapshot.health,
        food=snapshot.food,
        food_saturation=snapshot.food_saturation,
        inventory=tuple((i.name, i.count, i.slot) for i in snapshot.inventory),
        observed_entities=tuple(
            MinecraftEntityPresent(
                entity_id=e.entity_id, name=e.name, distance_m=e.distance,
                position=(e.position.x, e.position.y, e.position.z),
            )
            for e in snapshot.nearby_entities
        ),
        coverage_scope=coverage.source_scope,
        coverage_radius_m=coverage.max_distance,
        coverage_cap=coverage.max_entities,
        coverage_candidates=coverage.candidate_count,
        coverage_truncated=coverage.truncated,
        provenance=reading.provenance,
    )
