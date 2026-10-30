"""Read-only M1 bridge against pinned *actual* S #634 SelfBody types.

This test is run with the product SelfBody source in a separate checkout.
There is no product code modification or claim of native source attestation.
"""
from dataclasses import replace

import pytest

from experiments.fatigue_p1 import FatigueProfile
from experiments.fatigue_p1 import initial_state as begin_fatigue
from experiments.metabolism_m01_minecraft import (
    M01Profile,
    WorldTickSample,
    begin,
)
from experiments.metabolism_route_bounds import (
    RouteBounds,
    quote_route_range,
)
from experiments.metabolism_selfbody_cognition import (
    export_m01_owner_sensor,
    from_selfbody_to_cognition,
)
from experiments.metabolism_viability import Interoception
from relay_self.provenance import Provenance
from relay_self.self_body import (
    BodyField,
    BodyInteroception,
    BodyObservation,
    compose_self_body_view,
)


def setup_scenario(*, energy=8, sid="session-m", tick=100):
    profile = M01Profile(
        "m01-product-contract", capacity=20, initial_energy=8,
        basal_per_world_tick=0.1, movement_per_block=0.3,
        food_energy=(("cooked_beef", 5.0),),
    )
    state = replace(
        begin(profile, WorldTickSample(sid, tick, (0.0, 64.0, 0.0))),
        energy=energy,
    )
    fatigue = FatigueProfile(enabled=False)
    p1 = begin_fatigue(fatigue, sid, world_tick=tick)

    def route(label, destination, length):
        return RouteBounds(
            label, destination, length, length, .5, .5, 0, 0, 0, 0
        )

    ranges = tuple(
        quote_route_range(
            profile, state, option,
            fatigue_profile=fatigue, fatigue_state=p1,
        )
        for option in (
            route("food", "FOOD_OPPORTUNITY", 5),
            route("goal", "GOAL", 10),
        )
    )
    sensor = Interoception(quantum=0.1)
    handoff = export_m01_owner_sensor(
        profile, state, sensor, native_seq=8, request_id="probe-8"
    )
    native_provenance = Provenance("mineflayer", f"{sid}:8")
    observation = BodyObservation(
        session_id=sid,
        native_seq=8,
        request_id="probe-8",
        fields=(BodyField("food", 13), BodyField("health", 20)),
        source_provenance=native_provenance,
    )

    def product_body(sensor_key="m01_energy_sensor",
                     owner_name="m01-owner-local-sensor",
                     reading=None,
                     owner_tick=None,
                     owner_ref=None):
        source = BodyInteroception(
            field=BodyField(
                sensor_key, handoff.reading if reading is None else reading
            ),
            session_id=sid,
            native_seq=8,
            request_id="probe-8",
            native_provenance=native_provenance,
            owner_tick=handoff.world_tick if owner_tick is None else owner_tick,
            owner_provenance=Provenance(
                owner_name,
                handoff.owner_source_ref if owner_ref is None else owner_ref,
            ),
        )
        return compose_self_body_view(
            self_id="self-m", session_id=sid, epoch_id="epoch-8",
            observation=observation, interoceptions=(source,),
        )

    return profile, sensor, ranges, handoff, product_body


def test_product_selfbody_exact_join_produces_only_conditional_model_hints():
    profile, sensor, ranges, handoff, make_body = setup_scenario()
    result = from_selfbody_to_cognition(
        make_body(), profile=profile, sensor=sensor, route_ranges=ranges,
        handoff=handoff, noise_bound=0,
    )
    assert result.sensor_model == "M01_OWNER_LOCAL"
    assert result.session_id == "session-m"
    assert result.epoch_id == "epoch-8"
    assert result.native_seq == 8
    assert result.owner_world_tick == 100
    assert [r.affordability for r in result.results] == [
        "MODEL_AFFORDABLE_ALL_BOUNDS", "MODEL_AFFORDABLE_ALL_BOUNDS"
    ]
    assert result.action_authority is False
    assert result.learning_updates == result.habit_grants == 0
    assert not hasattr(result, "selected_action")
    assert not hasattr(result, "true_energy")
    assert not hasattr(result, "reward")
    assert "NOT_WORLD" in result.reason


def test_same_source_lower_sensed_energy_changes_readonly_resource_context():
    profile, sensor, ranges, handoff, make_body = setup_scenario(energy=3)
    result = from_selfbody_to_cognition(
        make_body(), profile=profile, sensor=sensor, route_ranges=ranges,
        handoff=handoff, noise_bound=0,
    )
    assert [r.affordability for r in result.results] == [
        "MODEL_AFFORDABLE_ALL_BOUNDS", "MODEL_INSUFFICIENT_ALL_BOUNDS"
    ]


def test_existing_b0_product_energy_sensor_cannot_be_reused_as_m01():
    profile, sensor, ranges, _, make_body = setup_scenario()
    b0 = make_body(
        sensor_key="m0_energy_sensor",
        owner_name="b0-m0-owner-local-sensor",
    )
    assert b0.sensed("m0_energy_sensor").origin.value == "interoception"
    assert b0.sensed("m01_energy_sensor").origin.value == "unknown"
    result = from_selfbody_to_cognition(
        b0, profile=profile, sensor=sensor, route_ranges=ranges,
    )
    assert result.sensor_model == "UNBOUND"
    assert all(r.affordability == "UNKNOWN" for r in result.results)
    assert all(r.min_energy_cost is None for r in result.results)
    assert "B0_IS_DIFFERENT_MODEL" in result.reason
    assert result.action_authority is False
    # No M0.1 forecast is promoted just because B0 was present.


def test_missing_m01_owner_handoff_does_not_assume_a_matched_sensor():
    profile, sensor, ranges, _, make_body = setup_scenario()
    result = from_selfbody_to_cognition(
        make_body(), profile=profile, sensor=sensor, route_ranges=ranges,
    )
    assert all(r.affordability == "UNKNOWN" for r in result.results)


@pytest.mark.parametrize("tamper", [
    "reading", "owner_tick", "owner_source", "owner_reference", "profile",
    "native_seq", "request_id", "session", "source_scope",
])
def test_product_join_tampering_fails_closed(tamper):
    profile, sensor, ranges, handoff, make_body = setup_scenario()
    body = make_body()
    if tamper == "reading":
        body = make_body(reading=handoff.reading + 1)
    elif tamper == "owner_tick":
        body = make_body(owner_tick=99)
    elif tamper == "owner_source":
        body = make_body(owner_name="b0-m0-owner-local-sensor")
    elif tamper == "owner_reference":
        body = make_body(owner_ref="forged-owner-tick")
    elif tamper == "profile":
        handoff = replace(handoff, profile_sha256="0" * 64)
    elif tamper == "native_seq":
        handoff = replace(handoff, native_seq=9)
    elif tamper == "request_id":
        handoff = replace(handoff, request_id="foreign")
    elif tamper == "session":
        handoff = replace(handoff, session_id="foreign")
    else:
        handoff = replace(handoff, source_scope="WORLD_SOURCE_ATTESTED")
    with pytest.raises(ValueError):
        from_selfbody_to_cognition(
            body, profile=profile, sensor=sensor, route_ranges=ranges,
            handoff=handoff, noise_bound=0,
        )


def test_stale_cost_tick_cannot_enter_next_product_epoch():
    profile, sensor, ranges, handoff, make_body = setup_scenario()
    wrong_range = replace(ranges[0], owner_world_tick=handoff.world_tick + 1)
    with pytest.raises(ValueError):
        from_selfbody_to_cognition(
            make_body(), profile=profile, sensor=sensor,
            route_ranges=(wrong_range,), handoff=handoff, noise_bound=0,
        )


def test_unbounded_noise_retains_unknown_even_with_joined_product_sensor():
    profile, sensor, ranges, handoff, make_body = setup_scenario()
    result = from_selfbody_to_cognition(
        make_body(), profile=profile, sensor=sensor, route_ranges=ranges,
        handoff=handoff,
    )
    assert result.sensor_model == "M01_OWNER_LOCAL"
    assert [r.affordability for r in result.results] == ["UNKNOWN", "UNKNOWN"]


def test_repeated_read_does_not_change_product_selfbody_or_original_ranges():
    profile, sensor, ranges, handoff, make_body = setup_scenario()
    body = make_body()
    inputs = (body, ranges, handoff)
    one = from_selfbody_to_cognition(
        body, profile=profile, sensor=sensor, route_ranges=ranges,
        handoff=handoff, noise_bound=0,
    )
    two = from_selfbody_to_cognition(
        body, profile=profile, sensor=sensor, route_ranges=ranges,
        handoff=handoff, noise_bound=0,
    )
    assert one == two
    assert inputs == (body, ranges, handoff)
    assert body.observed("energy").value is None
    assert body.observed("food").value == 13
