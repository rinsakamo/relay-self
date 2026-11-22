"""E Lane SENSE v0.1: Mineflayer-local read-only perception fanout.

Reuses the existing Mineflayer observation stream. It is not a sensor owner,
World authority, memory writer, Action issuer or real-World route qualifier.
The existing owner must separately authenticate native/World association.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from adapters.mineflayer.python_protocol import (
    MineflayerEntityFact,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
)
from relay_self.common_io import ScopeRef
from relay_self.provenance import Provenance
from relay_self.three_self_present import EpistemicStatus, Lens, LensClaim


class SenseRefusal(ValueError):
    """Missing or stale observation; do not publish as current perception."""


_SENSE_KINDS = frozenset(
    {"spawn", "respawn", "probe", "move", "forcedMove", "entities"}
)


@dataclass(frozen=True, slots=True)
class SenseFrame:
    """A single native observation, never a persistent or authoritative World map."""

    scope: ScopeRef
    observation: MineflayerObservation
    source_revision_ref: str

    @property
    def provenance(self) -> Provenance:
        return self.observation.provenance

    @property
    def position(self) -> MineflayerPosition:
        return self.observation.snapshot.position

    @property
    def nearby_entities(self) -> tuple[MineflayerEntityFact, ...]:
        return self.observation.snapshot.nearby_entities

    @property
    def nearby_coverage(self) -> MineflayerNearbyEntitiesCoverage:
        return self.observation.snapshot.nearby_entities_coverage


def sense_from_native(
    observation: MineflayerObservation,
    *,
    scope: ScopeRef,
    expected_native_session: str,
    previous_seq: int,
    expected_request_id: str | None = None,
) -> SenseFrame:
    """Accept one owner-supplied native event, not an independently verified World fact.

    The caller must own the receive stream and independently bind ScopeRef to
    the original Self/World owner. This function cannot attest Paper UUID,
    generation, collision geometry, simultaneous pose, or event timing.
    """
    if not isinstance(observation, MineflayerObservation):
        raise SenseRefusal("native observation unavailable")
    if (
        not isinstance(scope, ScopeRef)
        or scope.world_session_id is None
        or type(expected_native_session) is not str
        or not expected_native_session
        or observation.session_id != expected_native_session
    ):
        raise SenseRefusal("missing or mismatched native/World scope")
    if type(previous_seq) is not int or previous_seq < 0 or observation.seq <= previous_seq:
        raise SenseRefusal("stale, duplicate or invalid native sequence")
    if observation.kind not in _SENSE_KINDS:
        raise SenseRefusal("observation is not a SENSE event")
    if observation.kind == "probe":
        if (
            type(expected_request_id) is not str
            or not expected_request_id
            or observation.request_id != expected_request_id
        ):
            raise SenseRefusal("probe request mismatch")
    elif expected_request_id is not None or observation.request_id is not None:
        raise SenseRefusal("unexpected request ID on passive event")
    return SenseFrame(
        scope=scope,
        observation=observation,
        source_revision_ref=f"mineflayer:{observation.session_id}:{observation.seq}",
    )


@dataclass(frozen=True, slots=True)
class SenseMoveInput:
    """Source-referenced L0 MOVE input; UNKNOWN is NOT a permission to move."""

    scope: ScopeRef
    source_revision_ref: str
    position: MineflayerPosition
    nearby_entities: tuple[MineflayerEntityFact, ...]
    nearby_coverage: MineflayerNearbyEntitiesCoverage
    route_status: str = "UNKNOWN"
    missing: tuple[str, ...] = (
        "world_uuid", "body_aabb", "collision_shapes",
        "loaded_chunk_coverage", "observation_atomicity",
    )

    def __post_init__(self) -> None:
        if self.route_status != "UNKNOWN":
            raise SenseRefusal("SENSE cannot grant route clearance")


def sense_for_l0_move(frame: SenseFrame) -> SenseMoveInput:
    """No MOVE selection, motor call, STOP, or synthetic traversability grant."""
    if not isinstance(frame, SenseFrame):
        raise SenseRefusal("SENSE frame required")
    return SenseMoveInput(
        scope=frame.scope,
        source_revision_ref=frame.source_revision_ref,
        position=frame.position,
        nearby_entities=frame.nearby_entities,
        nearby_coverage=frame.nearby_coverage,
    )


def sense_for_self_world(frame: SenseFrame) -> tuple[LensClaim, ...]:
    """Create references for the existing SelfWorld lens, not a new Memory store.

    The owner must project these with the exact source_revision_refs tuple.
    Native registry truncation/absence never proves that entities are absent.
    """
    if not isinstance(frame, SenseFrame):
        raise SenseRefusal("SENSE frame required")
    common = dict(
        scope=frame.scope,
        lens=Lens.SELF_WORLD,
    )
    observed = dict(
        status=EpistemicStatus.OBSERVED,
        source_refs=(frame.provenance,),
        source_revision_refs=(frame.source_revision_ref,),
    )
    claims = [
        LensClaim(
            **common, **observed, claim_key="sense.position",
            value_ref=f"{frame.source_revision_ref}:position",
        ),
    ]
    for entity in frame.nearby_entities:
        claims.append(
            LensClaim(
                **common, **observed,
                claim_key=f"sense.entity.{entity.entity_id}",
                value_ref=f"{frame.source_revision_ref}:entity:{entity.entity_id}",
                coverage_ref=f"{frame.source_revision_ref}:entities-coverage",
            )
        )
    # This native protocol does not include local BlockState or collision boxes.
    claims.append(
        LensClaim(
            **common,
            claim_key="sense.terrain_collision",
            status=EpistemicStatus.UNKNOWN,
        )
    )
    return tuple(claims)


def sense_for_composite_source(
    frame: SenseFrame, *, owner_source_refs: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[LensClaim, ...]]:
    """Bind native claims to a caller-qualified composite projection revision.

    The caller must independently qualify the owner sources and current frame
    under the same owner lock. This function is not source qualification.
    The native claim provenance and value refs remain native, not Paper facts.
    """
    if (not isinstance(frame, SenseFrame) or type(owner_source_refs) is not tuple
            or not owner_source_refs or any(type(ref) is not str or not ref for ref in owner_source_refs)
            or len(set(owner_source_refs)) != len(owner_source_refs)
            or frame.source_revision_ref in owner_source_refs):
        raise SenseRefusal("distinct qualified owner and native revisions required")
    refs = (*owner_source_refs, frame.source_revision_ref)
    claims = tuple(
        replace(claim, source_revision_refs=refs)
        if claim.status is EpistemicStatus.OBSERVED else claim
        for claim in sense_for_self_world(frame)
    )
    coverage = frame.nearby_coverage
    coverage_value = (
        f"{frame.source_revision_ref}:entities-coverage:scope:{coverage.source_scope}:"
        f"max-distance:{coverage.max_distance}:max-entities:{coverage.max_entities}:"
        f"candidates:{coverage.candidate_count}:truncated:{coverage.truncated}"
    )
    return refs, (*claims, LensClaim(
        frame.scope, Lens.SELF_WORLD, "sense.nearby_entities_coverage",
        EpistemicStatus.OBSERVED, (frame.provenance,), refs, coverage_value,
        coverage_value,
    ))


