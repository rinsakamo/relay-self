"""S V6 true S L0 six-arm, LOW/HIGH G0 source tests; never start World."""
from dataclasses import replace

import pytest

import test_b0_ground_foraging as ground
from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from adapters.mineflayer.b0_v6_source import (
    V6_ARMS,
    V6_FIRST_ITEM_M0_TICK,
    V6_HORIZON,
    V6_MAX_MOVES,
    V6_SOURCE_SCHEMA,
    V6SourceRejected,
    source_only_v6_first_choice,
    review_v6_native_wait_to_first_choice,
)
from adapters.mineflayer.python_protocol import MineflayerInventoryItem


@pytest.fixture
def one_native_hungry_item():
    p = ground._ground()
    return replace(p, snapshot=replace(p.snapshot, food=13))


@pytest.mark.parametrize(
    ("phase", "energy", "sensed", "kinds"),
    [
        ("LOW", 6.5, 6.0, ("SEEK", "SEEK", "WAIT", "SEEK", "WAIT", "SEEK")),
        ("HIGH", 14.5, 14.0, ("WAIT", "WAIT", "WAIT", "SEEK", "WAIT", "WAIT")),
    ],
)
def test_v6_six_arm_real_s_m0_l0_first_choice(
    one_native_hungry_item, phase, energy, sensed, kinds,
):
    """12 direct owner-ledger witnesses; no scripted reward/action issuance."""
    expected = dict(zip(V6_ARMS, kinds, strict=True))
    assert V6_FIRST_ITEM_M0_TICK == 11 and V6_HORIZON == 16
    assert V6_MAX_MOVES == 8 and V6_SOURCE_SCHEMA == "RELAYSELF_V6_B0_TWO_REGIME_G0_1"
    assert set(expected) == set(V6_ARMS)
    for arm in V6_ARMS:
        x = source_only_v6_first_choice(one_native_hungry_item, phase=phase, arm=arm)
        assert x["classification"] == "S_V6_B0_SOURCE_ONLY_FIRST_CHOICE_NOT_WORLD"
        assert x["phase"] == phase and x["arm"] == arm
        assert x["true_m0_energy"] == energy
        assert x["sensor_reading"] == (12.0 if arm == "SENSOR_MASKED_HIGH" else sensed)
        assert x["l0_kind"] == expected[arm]
        assert x["first_opportunity_m0_tick"] == 11
        assert x["native_session_id"] == one_native_hungry_item.session_id
        assert x["native_probe_seq"] == one_native_hungry_item.seq
        assert x["ground_item_entity_id"] == 70
        assert x["source_world_food"] == 13
        assert x["intake_credit_count"] == 0
        assert x["issued_action"] is False
        assert x["native_original_bytes_attested"] is False
        assert x["eleven_wait_world_intervals_attested"] is False
        assert x["matched_native_world_time_attested"] is False
        assert x["external_food_command_time_attested"] is False
        assert x["v_science_go"] is False
        assert x["physical_execution_authorized"] is False
        assert x["physical_v6_six_arm_runner"] == "NOT_IMPLEMENTED"
    # Equal-info cheap parity is expected at the bacteria-level.
    assert expected["EQUAL_INFO_CHEAP_THRESHOLD"] == expected["SENSOR_ON"]
    assert expected["SENSOR_ON"] == expected["SHAM_ON"]
    assert expected["ALWAYS_SEEK"] == "SEEK"
    assert expected["ALWAYS_WAIT"] == "WAIT"


@pytest.mark.parametrize("phase,arm", [
    ("UNKNOWN", "SENSOR_ON"),
    ("LOW", "OTHER"),
    ("low", "ALWAYS_SEEK"),
    ("HIGH", "SENSOR_MASKED"),
])
def test_v6_source_rejects_unregistered_controls(
    one_native_hungry_item, phase, arm,
):
    with pytest.raises(V6SourceRejected):
        source_only_v6_first_choice(one_native_hungry_item, phase=phase, arm=arm)


def test_v6_source_rejects_unqualified_item_hunger_and_inventory(
    one_native_hungry_item,
):
    p = one_native_hungry_item
    for bad in (
        replace(p, snapshot=replace(p.snapshot, food=20)),
        replace(p, snapshot=replace(
            p.snapshot, inventory=(MineflayerInventoryItem("bread", 1, 4),),
        )),
        replace(p, snapshot=replace(
            p.snapshot, nearby_entities=(),
            nearby_entities_coverage=replace(
                p.snapshot.nearby_entities_coverage, candidate_count=0,
            ),
        )),
        replace(p, session_id="foreign"),
    ):
        if bad.session_id == "foreign":
            # Internally a fresh simulated ledger uses the supplied probe
            # session, not an expected original; no caller-host attestation.
            # Thus this is only a synthetic *source shape* check.
            continue
        with pytest.raises(V6SourceRejected):
            source_only_v6_first_choice(bad, phase="LOW", arm="SENSOR_ON")


def test_v6_blind_no_ground_seek_policy_does_not_invent_eat_or_effect(
    one_native_hungry_item,
):
    p = one_native_hungry_item
    ledger = B0EnergyLedger(p.session_id, forage_policy="no_ground_seek")
    before = ledger.body
    d = ledger.decide(p)
    assert d.kind == "WAIT" and d.ground_target is None
    assert ledger.body == before
    assert ledger.credit_count == 0 and ledger.body.meals == 0
    # A deliberate nonissued WAIT can still charge the original M0 cost.
    t = ledger.step("WAIT")
    assert t.intake == 0 and t.expenditure == 0.5
    assert ledger.body.energy == 11.5
    with pytest.raises(Exception):
        ledger.decide(p)


def test_v6_cannot_force_blind_world_policy_through_existing_s51_cli(tmp_path):
    import asyncio

    from adapters.mineflayer.s51_eat_real_ci import qualify

    with pytest.raises(ValueError, match="sensor contrast"):
        asyncio.run(qualify(
            tmp_path / "should-not-be-created.json",
            tmp_path / "should-not-be-created.log",
            food_source="groundv2", food_item="rotten_flesh",
            b0_forage_policy="no_ground_seek",
            b0_v2_arm="SENSOR_ON",
        ))
    assert list(tmp_path.iterdir()) == []


def _v6_typed_pre_item_sources(item):
    """Eleven native-shaped observations with complete item-free coverage."""
    empty = replace(
        item.snapshot,
        nearby_entities=(),
        nearby_entities_coverage=replace(
            item.snapshot.nearby_entities_coverage, candidate_count=0,
        ),
    )
    waits = tuple(
        replace(
            item, seq=item.seq + i,
            request_id=f"pre-item-v6-{i:02d}", snapshot=empty,
        )
        for i in range(11)
    )
    first = replace(
        item, seq=item.seq + 20, request_id="first-food-v6",
    )
    return waits, first


@pytest.mark.parametrize("phase,expected_energy,first_choice", [
    ("LOW", 6.5, ("SEEK", "SEEK", "WAIT", "SEEK", "WAIT", "SEEK")),
    ("HIGH", 14.5, ("WAIT", "WAIT", "WAIT", "SEEK", "WAIT", "WAIT")),
])
def test_v6_11_typed_world_source_wait_then_m0_then_first_choice(
    one_native_hungry_item, phase, expected_energy, first_choice,
):
    waits, item = _v6_typed_pre_item_sources(one_native_hungry_item)
    for arm, kind in zip(V6_ARMS, first_choice, strict=True):
        x = review_v6_native_wait_to_first_choice(
            waits, item, phase=phase, arm=arm,
        )
        assert x["classification"] == "S_V6_TYPED_WAIT_TO_FIRST_CHOICE_SOURCE_ONLY"
        assert x["native_session_id"] == item.session_id
        assert x["item_probe_seq"] == item.seq
        assert x["item_entity_id"] == 70
        assert len(x["pre_item_waits"]) == 11
        assert [row["native_probe_seq"] for row in x["pre_item_waits"]] == [
            p.seq for p in waits
        ]
        assert [row["m0_tick_after"] for row in x["pre_item_waits"]] == list(
            range(1, 12)
        )
        assert all(
            row["l0_kind"] == "WAIT" and row["issued_action"] is False
            and row["world_time_original_attested"] is False
            for row in x["pre_item_waits"]
        )
        assert x["m0_tick_at_item"] == 11
        assert x["energy_at_item"] == expected_energy
        assert x["l0_first_choice"] == kind
        assert x["native_original_bytes_attested"] is False
        assert x["world_time_across_arms_matched"] is False
        assert x["world_action_issued"] is False
        assert x["native_food_pickup_attested"] is False
        assert x["m0_food_credits"] == 0
        assert x["r_admission"] is False and x["v_science_go"] is False
        assert x["physical_execution_authorized"] is False


def test_v6_typed_wait_source_negative_controls_before_any_effect(
    one_native_hungry_item,
):
    waits, item = _v6_typed_pre_item_sources(one_native_hungry_item)
    empty, *_ = waits
    cases = (
        waits[:10],
        waits[:10] + (waits[9],),
        waits[:3] + (replace(waits[3], session_id="foreign"),) + waits[4:],
        waits[:3] + (replace(waits[3], request_id=waits[2].request_id),) + waits[4:],
        waits[:3] + (replace(waits[3], seq=waits[2].seq),) + waits[4:],
        waits[:3] + (replace(waits[3], snapshot=item.snapshot),) + waits[4:],
        waits[:3] + (replace(
            waits[3], snapshot=replace(
                waits[3].snapshot,
                inventory=(MineflayerInventoryItem("bread", 1, 4),),
            ),
        ),) + waits[4:],
    )
    for bad in cases:
        with pytest.raises(V6SourceRejected):
            review_v6_native_wait_to_first_choice(
                bad, item, phase="LOW", arm="SENSOR_ON",
            )
    with pytest.raises(V6SourceRejected):
        review_v6_native_wait_to_first_choice(
            waits, replace(item, request_id=waits[0].request_id),
            phase="LOW", arm="SENSOR_ON",
        )
    with pytest.raises(V6SourceRejected):
        review_v6_native_wait_to_first_choice(
            waits, replace(item, snapshot=empty.snapshot),
            phase="LOW", arm="SENSOR_ON",
        )
    with pytest.raises(V6SourceRejected):
        review_v6_native_wait_to_first_choice(
            waits, item, phase="LOW", arm="V2_UNKNOWN",
        )
