"""WB lane: bounded, read-only cognition slices from already composed Self views.

This is a projection of existing source-qualified view objects, NOT a new
World/Body truth, native reader, memory store, model, or Action owner.
The caller must still qualify the original Present and source clocks.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.self_body import BodyOrigin, BodyReading, SelfBodyView
from relay_self.self_world import (
    InvalidSelfWorldData,
    SelfWorldView,
    WorldEntityObservation,
)


class CognitionTier(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"


# Never use a request-supplied budget to bypass bounded per-tier limits.
_BODY_KEYS = (
    "health", "food", "position_x", "position_y",
    "position_z", "food_saturation",
)
_LIMITS = {
    CognitionTier.L0: (2, 1, 0, 0),
    CognitionTier.L1: (4, 3, 0, 0),
    CognitionTier.L2: (6, 8, 4, 4),
}


@dataclass(frozen=True, slots=True)
class VisibleWorldCue:
    """Observed exterior detail; never a statement that other entities are absent."""

    entity: WorldEntityObservation
    source_ref: str
    source_provenance: object


@dataclass(frozen=True, slots=True)
class CognitionSlice:
    """One immutable presentation, not a transferable source attestation."""

    self_id: str
    session_id: str
    epoch_id: str
    tier: CognitionTier
    world_status: str   # UNKNOWN / BOUNDED / TRUNCATED
    body_status: str    # UNKNOWN / OBSERVED
    world_source_ref: str | None
    body_source_ref: str | None
    body_cues: tuple[BodyReading, ...]
    visible_world: tuple[VisibleWorldCue, ...]
    remembered_ids: tuple[str, ...]
    scenario_ids: tuple[str, ...]
    world_omitted: int
    body_omitted: int
    remembered_omitted: int
    detail_available: bool

    @property
    def source_attested(self) -> bool:
        """Source qualification remains the upstream native/independent owner's job."""
        return False


def project_cognition_slice(
    view: SelfWorldView,
    *,
    tier: CognitionTier,
) -> CognitionSlice:
    """Pure, deterministic tier-limited read of one already qualified epoch.

    L0 never waits for beliefs, memory or a model. L1 sees bounded observations.
    L2 may *reference* own retained IDs and counterfactual IDs, but they never
    enter observed body/world cues. No provider, observation, mutation or Action.
    """
    if not isinstance(view, SelfWorldView) or not isinstance(tier, CognitionTier):
        raise InvalidSelfWorldData("typed SelfWorld and cognition tier required")
    body_limit, world_limit, memory_limit, scenario_limit = _LIMITS[tier]
    body = view.self_body
    observation = view.observation
    if body is not None:
        if not isinstance(body, SelfBodyView) or (
            body.self_id != view.self_id
            or body.session_id != view.session_id
            or body.epoch_id != view.epoch_id
        ):
            raise InvalidSelfWorldData("body owner/session/epoch mismatch")
    if observation is not None:
        if (observation.observer_id != view.self_id
                or observation.session_id != view.session_id):
            raise InvalidSelfWorldData("world owner/session mismatch")
    if body is not None and body.observation is not None and observation is not None:
        bo = body.observation
        if (
            bo.native_seq != observation.native_seq
            or bo.request_id != observation.request_id
            or bo.source_provenance != observation.provenance
        ):
            raise InvalidSelfWorldData("body/world original Present mismatch")

    # Only physical OBSERVATION; interoception, hypothetical, predicted and
    # remembered values are not promoted to native body or World state.
    observed_body = () if body is None else tuple(
        reading
        for key in _BODY_KEYS
        if (reading := body.observed(key)).origin is BodyOrigin.OBSERVATION
    )
    body_cues = observed_body[:body_limit]
    visible = () if observation is None else tuple(observation.entities)
    # Proximity is a deterministic display order, not an invented threat score.
    ranked = sorted(
        visible, key=lambda e: (
            e.distance_m is None,
            e.distance_m if e.distance_m is not None else 0,
            e.entity_ref,
        ),
    )
    world_cues = tuple(
        VisibleWorldCue(item, observation.source_ref, observation.provenance)
        for item in ranked[:world_limit]
    ) if observation is not None else ()
    memories = tuple(memory.memory_id for memory in view.memories)
    scenarios = tuple(s.scenario_id for s in view.scenarios)
    if observation is None:
        world_status = "UNKNOWN"
    elif observation.coverage_truncated:
        world_status = "TRUNCATED"
    else:
        world_status = "BOUNDED"
    body_status = "OBSERVED" if body_cues else "UNKNOWN"
    return CognitionSlice(
        self_id=view.self_id,
        session_id=view.session_id,
        epoch_id=view.epoch_id,
        tier=tier,
        world_status=world_status,
        body_status=body_status,
        world_source_ref=observation.source_ref if observation is not None else None,
        body_source_ref=(
            body.observation.source_ref
            if body is not None and body.observation is not None else None
        ),
        body_cues=body_cues,
        visible_world=world_cues,
        remembered_ids=memories[:memory_limit],
        scenario_ids=scenarios[:scenario_limit],
        world_omitted=len(visible) - len(world_cues),
        body_omitted=len(observed_body) - len(body_cues),
        remembered_omitted=len(memories) - min(len(memories), memory_limit),
        detail_available=(
            len(visible) > len(world_cues)
            or len(observed_body) > len(body_cues)
            or len(memories) > min(len(memories), memory_limit)
            or len(scenarios) > min(len(scenarios), scenario_limit)
            or bool(view.forecasts or view.beliefs)
        ),
    )
