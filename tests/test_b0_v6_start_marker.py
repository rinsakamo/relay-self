"""Source-only start World gametime and L0 association; no Minecraft."""
import hashlib
from dataclasses import replace

import pytest

import test_b0_ground_foraging as ground
from adapters.mineflayer.v6_atomic_fixture import (
    proposed_datapack_files,
    review_reported_scores,
)
from adapters.mineflayer.v6_start_marker import (
    GUARD,
    INSTALL_LINES,
    MAX_SCORE,
    PACK_FOLDER,
    READBACK_LINES,
    START_FUNCTION_PATH,
    STARTS,
    V6StartRejected,
    proposed_start_pack,
    review_claimed_elapsed,
    review_claimed_start,
    source_plan,
    start_function_lines,
)

NONCE = "a1b2c3d4e5f60718293a4b5c6d7e8f90"


def _first_l0():
    x = ground._ground()
    return replace(x, snapshot=replace(
        x.snapshot,
        nearby_entities=(),
        nearby_entities_coverage=replace(
            x.snapshot.nearby_entities_coverage, candidate_count=0,
        ),
        inventory=(),
        food=13,
    ))


def _claims():
    probe = _first_l0()
    pack = proposed_start_pack(STARTS[0], NONCE)
    sha = hashlib.sha256(pack[START_FUNCTION_PATH]).hexdigest()
    start = review_claimed_start(
        slot=STARTS[0], nonce=NONCE, first_l0=probe,
        expected_session_id=probe.session_id, expected_first_probe_seq=probe.seq,
        attempt_count=1, reported_gametime=100,
        source_function_sha256=sha,
    )
    food_bytes = proposed_datapack_files()[
        "data/relayself_v6/function/atomic_food.mcfunction"
    ]
    food_sha = hashlib.sha256(food_bytes).hexdigest()
    food = review_reported_scores(
        before=180, after=180, summon_succeeded=1,
        attempt_count=1,
        source_function_sha256=food_sha, expected_function_sha256=food_sha,
    )
    return start, food, probe


@pytest.mark.parametrize("slot", STARTS)
def test_new_separate_start_pack_has_replay_lock_no_golden_mutation(slot):
    files = proposed_start_pack(slot, NONCE)
    assert set(files) == {
        "pack.mcmeta",
        "data/relayself_v6_start/function/install.mcfunction",
        START_FUNCTION_PATH,
    }
    assert all(f.endswith(b"\n") for f in files.values())
    assert "add #start_attempt rs_v6_tick 0" in INSTALL_LINES[0]
    assert not any("players set #start_attempt" in s for s in INSTALL_LINES)
    lines = start_function_lines(slot, NONCE)
    assert lines[0] == "scoreboard players add #start_attempt rs_v6_tick 1"
    assert all(line.startswith(GUARD) for line in lines[1:4])
    assert "time query gametime" in lines[2]
    assert NONCE in lines[3] and slot in lines[3]
    assert "matches 2.." in lines[-1]
    assert not any("summon " in line or "time set" in line for line in lines)
    assert READBACK_LINES[0].endswith("#start_attempt rs_v6_tick")
    assert PACK_FOLDER == "relayself_v6_start_v1"
    plan = source_plan(slot, NONCE)
    assert plan["required_prior_setup"] == "FOOD_V2_OBJECTIVE_INSTALL_FIRST"
    assert plan["physical_execution_authorized"] is False
    assert plan["instrumented_live_start_attested"] is False
    assert plan["science_g3"] == "NO_GO"


@pytest.mark.parametrize("slot,nonce", [
    ("UNKNOWN", NONCE), ("world_start_a", NONCE),
    ("WORLD_START_A", "not_hex"), ("WORLD_START_B", NONCE.upper()),
    ("WORLD_START_A", NONCE + "a"), ("WORLD_START_A", True),
])
def test_bad_staged_identity_refused(slot, nonce):
    with pytest.raises(V6StartRejected):
        proposed_start_pack(slot, nonce)


@pytest.mark.parametrize("attempt,tick", [
    (0, 100), (2, 100), (True, 100),
    (1.0, 100), (1, -1), (1, MAX_SCORE + 1),
    (1, True), (1, 100.0),
])
def test_no_bad_source_start_scores(attempt, tick):
    p = _first_l0()
    sha = source_plan("WORLD_START_A", NONCE)["sha256"][START_FUNCTION_PATH]
    with pytest.raises(V6StartRejected):
        review_claimed_start(
            slot="WORLD_START_A", nonce=NONCE, first_l0=p,
            expected_session_id=p.session_id, expected_first_probe_seq=p.seq,
            attempt_count=attempt, reported_gametime=tick,
            source_function_sha256=sha,
        )


def test_good_claim_still_is_not_first_probe_time_authenticity():
    start, food, p = _claims()
    assert start["native_session_id"] == p.session_id
    assert start["first_l0_probe_seq"] == p.seq
    assert start["first_l0_to_server_effect_same_tick_attested"] is False
    assert start["server_original_console_bytes_attested"] is False
    pair = review_claimed_elapsed(
        start, food,
        expected_slot="WORLD_START_A", expected_session_id=p.session_id,
    )
    assert pair["claimed_elapsed_world_ticks"] == 80
    assert pair["r_independent_originals_attested"] is False
    assert pair["paired_12_arm_world_time_matched"] is False
    assert pair["m0_decision_tick_equated_to_world_time"] is False
    assert pair["physical_execution_authorized"] is False


def test_reject_foreign_probe_source_and_wrong_source_bytes():
    probe = _first_l0()
    sha = source_plan(STARTS[0], NONCE)["sha256"][START_FUNCTION_PATH]
    common = dict(
        slot=STARTS[0], nonce=NONCE, first_l0=probe,
        expected_session_id=probe.session_id, expected_first_probe_seq=probe.seq,
        attempt_count=1, reported_gametime=100,
        source_function_sha256=sha,
    )
    for overrides in (
        {"expected_session_id": "foreign"},
        {"expected_first_probe_seq": probe.seq + 1},
        {"source_function_sha256": "0" * 64},
        {"first_l0": replace(probe, session_id="foreign")},
        {"first_l0": replace(probe, kind="death")},
        {"first_l0": replace(probe, snapshot=replace(
            probe.snapshot, inventory=(ground.MineflayerInventoryItem(
                "rotten_flesh", 1, 2,
            ),),
        ))},
    ):
        with pytest.raises(V6StartRejected):
            review_claimed_start(**(common | overrides))


def test_pair_rejects_wrong_slot_identity_or_inverted_timeline():
    start, food, probe = _claims()
    for s, f, expected_slot, expected_session in (
        (start, food, "WORLD_START_B", probe.session_id),
        (start, food, "WORLD_START_A", "foreign"),
        (start, food | {"claimed_server_gametime": 99},
         "WORLD_START_A", probe.session_id),
        (start, food | {"claimed_server_gametime": True},
         "WORLD_START_A", probe.session_id),
        (start, food | {"claimed_atomic_function_attempt_count": 2},
         "WORLD_START_A", probe.session_id),
    ):
        with pytest.raises(V6StartRejected):
            review_claimed_elapsed(
                s, f, expected_slot=expected_slot,
                expected_session_id=expected_session,
            )


def test_start_pack_distinct_from_frozen_food_producer():
    start_paths = set(proposed_start_pack(STARTS[0], NONCE))
    food_paths = set(proposed_datapack_files())
    assert start_paths & food_paths == {"pack.mcmeta"}
    assert source_plan(STARTS[0], NONCE)["sha256"][START_FUNCTION_PATH]
