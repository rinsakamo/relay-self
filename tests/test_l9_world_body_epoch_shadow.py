"""L9: L8 observes only the same S-owned Present through typed World/Body."""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_l1_epoch_observer as l8
import test_l1_s_choice_shadow as l7
from relay_self.l1_s_choice_shadow import SChoiceContrastStatus
from relay_self.l9_world_body_epoch_shadow import (
    WorldBodyEpochRejected,
    observe_s_world_body_epoch_l1,
)
from relay_self.self_body import (
    BodyField,
    BodyObservation,
    InvalidSelfBodyData,
    compose_self_body_view,
)
from relay_self.self_world import (
    InvalidSelfWorldData,
    WorldEntityObservation,
    WorldObservation,
    compose_self_world_view,
)


def _source(*, near=True, enabled=True):
    before, retained, native, s_choice, learned = l7.scenario(
        near=near, enabled=enabled,
        tags=("alpha", "beta", "novel_cue") if near else ("alpha", "novel_cue"),
    )
    supervisor, s_epoch = l8.run_s_epoch(native, retained)
    reading = native.observation
    snap = reading.snapshot
    sid = reading.session_id
    observer = before.identity.self_id
    epoch = f"l9-s-epoch-{reading.seq}"
    body_obs = BodyObservation(
        session_id=sid, native_seq=reading.seq, request_id=reading.request_id,
        fields=(
            BodyField("position_x", snap.position.x),
            BodyField("position_y", snap.position.y),
            BodyField("position_z", snap.position.z),
            BodyField("health", snap.health),
            BodyField("food", snap.food),
            BodyField("food_saturation", snap.food_saturation),
        ),
        source_provenance=reading.provenance,
    )
    body = compose_self_body_view(
        self_id=observer, session_id=sid, epoch_id=epoch, observation=body_obs,
    )
    coverage = snap.nearby_entities_coverage
    world_obs = WorldObservation(
        observer_id=observer, session_id=sid, native_seq=reading.seq,
        request_id=reading.request_id,
        entities=tuple(
            WorldEntityObservation(
                f"entity-{item.entity_id}", item.name,
                (item.position.x, item.position.y, item.position.z),
                item.distance,
            )
            for item in snap.nearby_entities
        ),
        coverage_scope=coverage.source_scope,
        coverage_radius_m=coverage.max_distance,
        coverage_cap=coverage.max_entities,
        coverage_candidates=coverage.candidate_count,
        coverage_truncated=coverage.truncated,
        provenance=reading.provenance,
    )
    world = compose_self_world_view(
        self_id=observer, session_id=sid, epoch_id=epoch,
        observation=world_obs, self_body=body,
        retained=learned.cognition,
    )
    return {
        "s_epoch": s_epoch, "native": native, "world": world,
        "body": body, "retained": retained, "learning": learned,
        "retention_enabled": enabled,
    }, supervisor


def test_l9_same_original_s_epoch_with_world_and_body_l1_shadow_but_no_action():
    args, supervisor = _source()
    original = args["s_epoch"]
    memory = args["learning"].cognition
    previous_ns = supervisor.last_at_ns
    result = observe_s_world_body_epoch_l1(**args)
    assert result.original_s_l8.s_epoch is original
    assert result.original_s_l8.comparison.status is SChoiceContrastStatus.L1_DIFFERS
    assert result.original_s_l8.comparison.l1_shadow_ref == "WAIT"
    assert result.original_s_l8.comparison.s_choice.value == "MOVE_AWAY"
    assert result.original_s_l8.comparison.s_choice_kept
    assert result.observed_entity_ref == f"entity-{args['native'].entity_id}"
    assert result.observed_distance_m == args["native"].distance_m
    assert result.observed_food == args["native"].observation.snapshot.food
    assert result.observed_health == args["native"].observation.snapshot.health
    assert result.world is args["world"] and result.body is args["body"]
    assert result.action_issues == result.new_source_reads == 0
    assert result.memory_writes == result.learning_updates == result.habit_grants == 0
    assert not result.action_authority and not result.physical_learning_attested
    assert supervisor.last_at_ns == previous_ns
    assert supervisor.open_actions == ()
    assert args["learning"].cognition is memory


def test_l9_retention_off_and_far_world_still_use_original_s_choice():
    for near, enabled in [(True, False), (False, True)]:
        args, _ = _source(near=near, enabled=enabled)
        result = observe_s_world_body_epoch_l1(**args)
        assert result.original_s_l8.comparison.s_choice_kept
        if enabled:
            assert result.original_s_l8.comparison.s_choice.value == "WAIT"
            assert result.original_s_l8.comparison.l1_shadow_ref == "MOVE_AWAY"
        else:
            assert result.original_s_l8.comparison.status is SChoiceContrastStatus.WITHHELD
            assert result.original_s_l8.comparison.l1_shadow_ref is None


@pytest.mark.parametrize("fault", [
    "body_missing", "world_missing", "foreign_body", "foreign_world_self",
    "body_wrong_epoch", "body_wrong_seq", "body_wrong_request",
    "body_wrong_food", "body_wrong_health", "body_wrong_saturation",
    "body_wrong_position", "body_hypothesis_instead_observation",
    "body_action_readback_without_original", "world_entity_missing",
    "world_entity_distance", "world_entity_position", "world_entity_name",
    "world_entity_extra", "world_entity_visible_action",
    "world_registry_truncated", "world_coverage_forged",
    "world_wrong_seq", "world_wrong_request", "world_wrong_provenance",
    "foreign_memory", "foreign_learning_self", "unadmitted_current",
    "s_epoch_not_completed", "retention_mismatch", "foreign_session",
])
def test_l9_strict_original_self_world_body_binding(fault):
    a, _ = _source()
    with pytest.raises((WorldBodyEpochRejected, InvalidSelfBodyData, InvalidSelfWorldData)):
        body = a["body"]
        world = a["world"]
        observation = world.observation
        source_body = body.observation
        if fault == "body_missing":
            a["body"] = replace(body, observation=None)
        elif fault == "world_missing":
            a["world"] = replace(world, observation=None)
        elif fault == "foreign_body":
            a["body"] = replace(body, session_id="foreign")
        elif fault == "foreign_world_self":
            a["world"] = replace(world, self_id="foreign")
        elif fault == "body_wrong_epoch":
            a["body"] = replace(body, epoch_id="old")
        elif fault == "body_wrong_seq":
            a["body"] = replace(body, observation=replace(
                source_body, native_seq=source_body.native_seq - 1,
            ))
        elif fault == "body_wrong_request":
            a["body"] = replace(body, observation=replace(
                source_body, request_id="other",
            ))
        elif fault in ("body_wrong_food", "body_wrong_health",
                       "body_wrong_saturation", "body_wrong_position"):
            key = {
                "body_wrong_food": "food",
                "body_wrong_health": "health",
                "body_wrong_saturation": "food_saturation",
                "body_wrong_position": "position_x",
            }[fault]
            fields = tuple(
                replace(field, value=field.value + 1) if field.key == key else field
                for field in source_body.fields
            )
            new_body = replace(body, observation=replace(source_body, fields=fields))
            a["body"] = new_body
            a["world"] = replace(world, self_body=new_body)
        elif fault == "body_hypothesis_instead_observation":
            new_body = replace(body, observation=None)
            a["body"] = new_body
            a["world"] = replace(world, self_body=new_body)
        elif fault == "body_action_readback_without_original":
            new_body = replace(body, observation=replace(
                source_body, action_id="goal-forged",
            ))
            a["body"] = new_body
            a["world"] = replace(world, self_body=new_body)
        elif fault.startswith("world_entity_"):
            target = observation.entities[0]
            if fault == "world_entity_missing":
                entities = ()
            elif fault == "world_entity_distance":
                entities = (replace(target, distance_m=target.distance_m + 1),)
            elif fault == "world_entity_position":
                entities = (replace(target, position=(1.0, 1.0, 1.0)),)
            elif fault == "world_entity_name":
                entities = (replace(target, label="skeleton"),)
            elif fault == "world_entity_extra":
                entities = (target, replace(target, entity_ref="entity-999"))
            else:
                entities = (replace(target, visible_action="attack"),)
            a["world"] = replace(
                world, observation=replace(observation, entities=entities),
            )
        elif fault == "world_registry_truncated":
            a["world"] = replace(world, observation=replace(
                observation, coverage_truncated=True,
            ))
        elif fault == "world_coverage_forged":
            a["world"] = replace(world, observation=replace(
                observation, coverage_cap=observation.coverage_cap + 1,
            ))
        elif fault == "world_wrong_seq":
            a["world"] = replace(world, observation=replace(
                observation, native_seq=observation.native_seq - 1,
            ))
        elif fault == "world_wrong_request":
            a["world"] = replace(world, observation=replace(
                observation, request_id="other",
            ))
        elif fault == "world_wrong_provenance":
            from relay_self.provenance import Provenance
            a["world"] = replace(world, observation=replace(
                observation, provenance=Provenance("synthetic", "forged"),
            ))
        elif fault == "foreign_memory":
            from relay_self.persistent_cognition import Memory
            from relay_self.provenance import Provenance
            a["world"] = replace(world, memories=(
                Memory("foreign", "fake", Provenance("test", "one"),
                       Provenance("test", "two")),
            ))
        elif fault == "foreign_learning_self":
            a["world"] = replace(world, self_id="foreign")
        elif fault == "unadmitted_current":
            a["learning"] = replace(
                a["learning"], admitted_current_probe_sha256=frozenset(),
            )
        elif fault == "s_epoch_not_completed":
            a["s_epoch"] = replace(a["s_epoch"], cognition_result=None)
        elif fault == "retention_mismatch":
            a["retention_enabled"] = False
        else:
            a["world"] = replace(world, session_id="foreign")
        observe_s_world_body_epoch_l1(**a)


def test_l9_cannot_use_l8_contrast_to_commit_or_change_original_s_epoch():
    a, _ = _source()
    left = observe_s_world_body_epoch_l1(**a)
    right = observe_s_world_body_epoch_l1(**a)
    assert left == right
    assert left.original_s_l8.s_epoch is a["s_epoch"]
    assert left.original_s_l8.comparison.action_authority is False
    assert left.action_authority is False
    assert left.original_s_l8.comparison.learning_updates == 0
    assert a["s_epoch"].cognition_result.selection.value == "MOVE_AWAY"
