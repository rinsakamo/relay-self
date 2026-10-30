"""L9: exact S native Present <-> SelfWorld/SelfBody <-> L8 epoch observer.

A source-level, post-S read-only join. No runtime scheduling, new World read,
current-epoch training, Body resource accounting or motor/L1 adoption.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.s34_native_world_cognition_ci import NativeThreat
from relay_self.l1_epoch_observer import (
    SEpochL1Observation,
    SEpochObservationRejected,
    observe_s_epoch_l1,
)
from relay_self.learning import LearningPreferenceState
from relay_self.learning_epoch import LearningEpochResult
from relay_self.self_body import BodyOrigin, SelfBodyView
from relay_self.self_world import SelfWorldView, WorldOrigin


class WorldBodyEpochRejected(ValueError):
    """S, L, SelfWorld and SelfBody disagree about the same current source."""


@dataclass(frozen=True, slots=True)
class WorldBodyEpochShadow:
    """Only an observational attachment to the original S/L8 decision."""

    world: SelfWorldView
    body: SelfBodyView
    original_s_l8: SEpochL1Observation
    world_source_ref: str
    body_source_ref: str
    observed_entity_ref: str
    observed_distance_m: float
    observed_food: float
    observed_health: float
    action_issues: int = 0
    new_source_reads: int = 0
    memory_writes: int = 0
    learning_updates: int = 0
    habit_grants: int = 0
    action_authority: bool = False
    physical_learning_attested: bool = False


def observe_s_world_body_epoch_l1(
    s_epoch: object,
    *,
    native: NativeThreat,
    world: SelfWorldView,
    body: SelfBodyView,
    retained: LearningPreferenceState,
    learning: LearningEpochResult,
    retention_enabled: bool,
) -> WorldBodyEpochShadow:
    """Check original positive Present facts before invoking L8 read-only compare.

    Source SHA and current revision must already be S/R/V admitted. The
    SelfWorld/SelfBody views are fallible projections, not independent
    authentication. A missing target is UNKNOWN, never absence/safety.
    """
    if (
        not isinstance(native, NativeThreat)
        or not isinstance(world, SelfWorldView)
        or not isinstance(body, SelfBodyView)
        or not isinstance(learning, LearningEpochResult)
        or not isinstance(retained, LearningPreferenceState)
        or type(retention_enabled) is not bool
    ):
        raise WorldBodyEpochRejected("existing typed native/world/body/S/L owners required")
    source = native.observation
    exterior = world.observation
    internal = body.observation
    if (
        exterior is None or internal is None
        or world.self_body is not body
        or world.self_id != learning.cognition.identity.self_id
        or body.self_id != world.self_id
        or world.session_id != body.session_id
        or world.session_id != source.session_id
        or world.epoch_id != body.epoch_id
        or learning.current.session_id != source.session_id
        or learning.current.source_provenance != source.provenance
        or source.kind != "probe"
        or native.request_id != source.request_id
        or not source.request_id
        or source.provenance.source != "mineflayer"
        or exterior.observer_id != world.self_id
        or exterior.session_id != source.session_id
        or internal.session_id != source.session_id
        or exterior.native_seq != internal.native_seq
        or exterior.native_seq != source.seq
        or exterior.request_id != internal.request_id
        or exterior.request_id != source.request_id
        or exterior.provenance != internal.source_provenance
        or exterior.provenance != source.provenance
        or internal.action_id is not None
        or internal.consequence_provenance is not None
        or body.outcome is not None
        or learning.current.original_probe_sha256
        not in learning.admitted_current_probe_sha256
    ):
        raise WorldBodyEpochRejected("foreign, unadmitted, future-outcome or mixed current Present")
    if any(
        next((m for m in learning.cognition.memories if m.memory_id == memory.memory_id), None)
        != memory for memory in world.memories
    ):
        raise WorldBodyEpochRejected("foreign SelfWorld remembered source")

    snapshot = source.snapshot
    coverage = snapshot.nearby_entities_coverage
    expected = {
        f"entity-{item.entity_id}": item for item in snapshot.nearby_entities
    }
    if (
        exterior.coverage_scope != coverage.source_scope
        or exterior.coverage_radius_m != coverage.max_distance
        or exterior.coverage_cap != coverage.max_entities
        or exterior.coverage_candidates != coverage.candidate_count
        or exterior.coverage_truncated != coverage.truncated
        or len(exterior.entities) != len(snapshot.nearby_entities)
        or len(expected) != len(snapshot.nearby_entities)
    ):
        raise WorldBodyEpochRejected("original bounded native entity registry differs")
    for item in exterior.entities:
        original = expected.get(item.entity_ref)
        if (
            original is None
            or item.label != original.name
            or item.position != (
                original.position.x, original.position.y, original.position.z
            )
            or item.distance_m != original.distance
            or item.visible_action is not None
        ):
            raise WorldBodyEpochRejected("SelfWorld invented or altered a positively observed entity")
    selected = world.observed_entity(f"entity-{native.entity_id}")
    if (
        selected.origin is not WorldOrigin.OBSERVED
        or selected.value is None
        or selected.value.label != "zombie"
        or not math.isclose(
            selected.value.distance_m, native.distance_m,
            rel_tol=0.0, abs_tol=1e-6,
        )
    ):
        raise WorldBodyEpochRejected("original target entity not present with exact geometry")

    expected_fields = {
        "position_x": snapshot.position.x,
        "position_y": snapshot.position.y,
        "position_z": snapshot.position.z,
        "health": snapshot.health,
        "food": snapshot.food,
        "food_saturation": snapshot.food_saturation,
    }
    if (
        len(internal.fields) != len(expected_fields)
        or {field.key: field.value for field in internal.fields} != expected_fields
        or len({field.key for field in internal.fields}) != len(expected_fields)
    ):
        raise WorldBodyEpochRejected("SelfBody Present not identical to original native body facts")
    food = body.observed("food")
    health = body.observed("health")
    if (
        food.origin is not BodyOrigin.OBSERVATION
        or health.origin is not BodyOrigin.OBSERVATION
        or food.value != snapshot.food
        or health.value != snapshot.health
    ):
        raise WorldBodyEpochRejected("SelfBody hypothesis/belief cannot become observed food or health")
    try:
        contrasted = observe_s_epoch_l1(
            s_epoch, native=native, retained=retained,
            learning=learning, retention_enabled=retention_enabled,
        )
    except SEpochObservationRejected as exc:
        raise WorldBodyEpochRejected("original S/L8 epoch refused or did not close") from exc
    return WorldBodyEpochShadow(
        world=world, body=body, original_s_l8=contrasted,
        world_source_ref=exterior.source_ref,
        body_source_ref=internal.source_ref,
        observed_entity_ref=f"entity-{native.entity_id}",
        observed_distance_m=native.distance_m,
        observed_food=food.value,
        observed_health=health.value,
    )
