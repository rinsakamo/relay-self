"""Offline negative controls for E Lane SENSE; no native/Paper execution."""
from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerEntityFact,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from adapters.mineflayer.sense_projection import (
    SenseRefusal,
    sense_for_l0_move,
    sense_for_self_world,
    sense_from_native,
)
from relay_self.common_io import ScopeRef
from relay_self.three_self_present import (
    EpistemicStatus,
    Lens,
    LensView,
    PresentContractError,
)


def native(*, kind="move", seq=7, request_id=None, with_entity=True):
    entities = (
        (MineflayerEntityFact(
            19, "zombie", "mob", 2.0, MineflayerPosition(3, 4, 5)
        ),)
        if with_entity else ()
    )
    coverage = MineflayerNearbyEntitiesCoverage(
        MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
        MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
        MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
        len(entities),
        False,
    )
    snapshot = MineflayerSnapshot(
        20, 20, 5, None, MineflayerPosition(1, 4, 5),
        None, (), entities, coverage,
    )
    return MineflayerObservation("native-a", seq, kind, snapshot, request_id)


def project(observation=None, **overrides):
    kwargs = dict(
        scope=ScopeRef("self-a", "world-session-a"),
        expected_native_session="native-a",
        previous_seq=6,
    )
    kwargs.update(overrides)
    return sense_from_native(observation or native(), **kwargs)


def test_one_native_event_feeds_move_and_self_world_without_any_action():
    frame = project()
    move = sense_for_l0_move(frame)
    claims = sense_for_self_world(frame)
    assert move.position == native().snapshot.position
    assert move.source_revision_ref == frame.source_revision_ref
    assert move.route_status == "UNKNOWN"
    assert "collision_shapes" in move.missing
    with pytest.raises(SenseRefusal, match="cannot grant route clearance"):
        replace(move, route_status="CLEAR")
    assert len(move.nearby_entities) == 1

    view = LensView(
        scope=frame.scope, epoch_ref="epoch-1", lens=Lens.SELF_WORLD,
        source_revision_refs=(frame.source_revision_ref,), claims=claims,
    )
    assert view.read("sense.position").status is EpistemicStatus.OBSERVED
    assert view.read("sense.entity.19").status is EpistemicStatus.OBSERVED
    assert view.read("sense.terrain_collision").status is EpistemicStatus.UNKNOWN
    assert view.read("sense.entity.20").status is EpistemicStatus.UNKNOWN
    assert view.read("sense.position").source_refs == (frame.provenance,)


def test_probe_requires_exact_native_request_and_monotonic_sequence():
    frame = project(
        native(kind="probe", request_id="e-sense-7"),
        expected_request_id="e-sense-7",
    )
    assert frame.source_revision_ref == "mineflayer:native-a:7"
    with pytest.raises(SenseRefusal, match="request mismatch"):
        project(native(kind="probe", request_id="e-sense-7"))
    with pytest.raises(SenseRefusal, match="request mismatch"):
        project(native(kind="probe", request_id="e-sense-7"),
                expected_request_id="wrong")


@pytest.mark.parametrize("observation,overrides", [
    (None, {"expected_native_session": "native-b"}),
    (None, {"previous_seq": 7}),
    (None, {"previous_seq": 8}),
    (None, {"previous_seq": True}),
    (None, {"scope": ScopeRef("self-a")}),
    (None, {"scope": ScopeRef("self-b", "world-session-b"),
            "expected_native_session": "native-b"}),
    (native(kind="death"), {}),
    (native(kind="probe", request_id="x"), {"expected_request_id": "y"}),
    (native(kind="move"), {"expected_request_id": "extra"}),
])
def test_invalid_or_unbound_event_refused(observation, overrides):
    with pytest.raises(SenseRefusal):
        project(observation, **overrides)


def test_foreign_native_session_and_stale_lens_rejected():
    obs = replace(native(), session_id="native-b")
    with pytest.raises(SenseRefusal, match="scope"):
        project(obs)
    frame = project()
    with pytest.raises(PresentContractError, match="stale"):
        LensView(
            scope=frame.scope, epoch_ref="epoch-2", lens=Lens.SELF_WORLD,
            source_revision_refs=("mineflayer:native-a:6",),
            claims=sense_for_self_world(frame),
        )


def test_empty_registry_does_not_assert_no_entities_or_safe_terrain():
    frame = project(native(with_entity=False))
    claims = sense_for_self_world(frame)
    assert [c.claim_key for c in claims] == [
        "sense.position", "sense.terrain_collision",
    ]
    assert sense_for_l0_move(frame).route_status == "UNKNOWN"
    assert claims[-1].status is EpistemicStatus.UNKNOWN


def test_no_unqualified_world_claim_or_mutation_from_non_frame():
    with pytest.raises(SenseRefusal):
        sense_for_l0_move(None)
    with pytest.raises(SenseRefusal):
        sense_for_self_world(None)
