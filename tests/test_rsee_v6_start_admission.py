"""R V6 separate single-use start marker and two-pack source-only negatives."""
import hashlib
import json
from copy import deepcopy

import pytest

from experiments.standard_env.v6_atomic_admission import (
    S_ATOMIC_SOURCE_HEAD,
    expected_pack_bytes,
)
from experiments.standard_env.v6_start_admission import (
    S_START_SOURCE_BLOB,
    S_START_SOURCE_HEAD,
    START_PACK_DIR,
    StartReviewRejected,
    expected_combined_pack_bytes,
    expected_start_pack_bytes,
    main,
    plan,
    review_elapsed_claim,
    review_s_start_source,
    review_staged_clone,
    review_staged_index,
)

SLOT = "WORLD_START_A"
NONCE = "0123456789abcdef0123456789abcdef"


def _index():
    original = (
        ("level.dat", 6, hashlib.sha256(b"golden").hexdigest()),
        ("region/r.0.0.mca", 8, hashlib.sha256(b"not-real").hexdigest()),
    )
    added = tuple(
        (path, len(raw), hashlib.sha256(raw).hexdigest())
        for path, raw in sorted(expected_combined_pack_bytes(SLOT, NONCE).items())
    )
    return original, original + added


def _claims():
    return {
        "slot": SLOT, "nonce": NONCE, "session_id": "synthetic-not-attested",
        "first_probe_seq": 12, "first_probe_request_id": "p0",
        "reported_start_attempt": 1, "reported_start_gametime": 3000,
        "reported_food_attempt": 1, "reported_food_before": 3120,
        "reported_food_after": 3120, "reported_summon_success": 1,
        "m0_tick_at_food": 11,
    }


def test_default_plan_does_not_read_world_or_claim_attestation(capsys):
    assert main([]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data == plan()
    assert data["expected_added_pack_files"] == 6
    assert data["s_start_source_head"] == S_START_SOURCE_HEAD
    assert data["s_food_source_head"] == S_ATOMIC_SOURCE_HEAD
    assert data["physical_execution_authorized"] is False
    assert data["science_g3"] == "NO_GO"
    assert len(S_START_SOURCE_BLOB) == 40


def test_start_function_independent_exact_bytes_and_separate_food_v2():
    start = expected_start_pack_bytes(SLOT, NONCE)
    food = expected_pack_bytes()
    both = expected_combined_pack_bytes(SLOT, NONCE)
    assert len(start) == 3 and len(food) == 3 and len(both) == 6
    assert not set(start).intersection(food)
    assert {k: both[k] for k in food} == food
    assert all(path.startswith(START_PACK_DIR + "/") for path in start)
    meta = json.loads(start[f"{START_PACK_DIR}/pack.mcmeta"])
    assert meta["pack"]["pack_format"] == 81
    installer = start[
        f"{START_PACK_DIR}/data/relayself_v6_start/function/install.mcfunction"
    ].decode().splitlines()
    assert len(installer) == 2
    assert all(" players add " in line and line.endswith(" rs_v6_tick 0")
               for line in installer)
    assert not any("players set" in line for line in installer)
    f = start[
        f"{START_PACK_DIR}/data/relayself_v6_start/function/start_trial.mcfunction"
    ].decode().splitlines()
    assert f[0] == "scoreboard players add #start_attempt rs_v6_tick 1"
    assert len(f) == 5
    assert all("matches 1 run" in line for line in f[1:4])
    assert "time query gametime" in f[2]
    assert f"RELAYSELF_V6_TRIAL_START_{SLOT}_{NONCE}_NOT_ADMITTED" in f[3]
    assert "matches 2.. run say" in f[4]
    assert not any("summon" in line for line in f)
    assert not any("set #start_attempt" in line for line in f)


@pytest.mark.parametrize(("slot", "nonce"), [
    ("WORLD_START_Z", NONCE),
    (True, NONCE),
    (SLOT, "A" * 32),
    (SLOT, "g" * 32),
    (SLOT, "a" * 31),
    (SLOT, ""),
    (SLOT, None),
])
def test_reject_unregistered_or_uncanonical_cohort_identity(slot, nonce):
    with pytest.raises(StartReviewRejected):
        expected_start_pack_bytes(slot, nonce)


def test_exact_six_file_delta_synthetic_only():
    original, staged = _index()
    reviewed = review_staged_index(original, staged, slot=SLOT, nonce=NONCE)
    assert reviewed["classification"] == "RSEE_V6_TWO_PACK_STAGED_DELTA_REVIEW_ONLY"
    assert reviewed["original_file_count"] == 2
    assert reviewed["added_pack_file_count"] == 6
    assert reviewed["original_world_bytes_independently_read"] is False
    assert reviewed["server_function_loaded"] is False
    assert reviewed["native_elapsed_world_ticks_attested"] is False
    assert reviewed["physical_execution_authorized"] is False


def test_mutated_or_missing_clone_and_alternate_nonce_fail_closed():
    original, staged = _index()
    variants = (
        staged[:-1], staged + (("unknown", 1, "f" * 64),),
        staged + (staged[-1],),
        tuple(x for x in staged if x[0] != "level.dat"),
        tuple((p, n, "f" * 64) if p == "level.dat" else (p, n, h)
              for p, n, h in staged),
        tuple((p, n + 1, h) if p.endswith("start_trial.mcfunction")
              else (p, n, h) for p, n, h in staged),
    )
    for variant in variants:
        with pytest.raises(StartReviewRejected):
            review_staged_index(original, variant, slot=SLOT, nonce=NONCE)
    with pytest.raises(StartReviewRejected):
        review_staged_index(original, staged, slot=SLOT, nonce="f" * 32)


def test_index_row_type_duplicates_and_bogus_golden_are_rejected():
    original, staged = _index()
    for bad in (
        (("level.dat", True, "f" * 64),),
        (("level.dat", 1, "INVALID"),),
        ("bad",),
        original + (original[0],),
    ):
        with pytest.raises(StartReviewRejected):
            review_staged_index(bad, staged, slot=SLOT, nonce=NONCE)


def test_reported_elapsed_is_never_authenticated_world_time():
    data = review_elapsed_claim(**_claims())
    assert data["claimed_elapsed_world_ticks"] == 120
    assert data["first_l0_and_server_start_same_tick"] == "NOT_ATTESTED"
    assert data["source_originals_independently_verified"] is False
    assert data["matched_12_arm_world_time_attested"] is False
    assert data["m0_tick_not_minecraft_tick"] is True
    assert data["science_g3"] == "NO_GO"


@pytest.mark.parametrize(("field", "invalid"), [
    ("slot", "WORLD_START_X"),
    ("nonce", "not-a-nonce"),
    ("session_id", ""),
    ("first_probe_seq", True),
    ("first_probe_seq", -1),
    ("first_probe_request_id", ""),
    ("reported_start_attempt", 2),
    ("reported_start_attempt", True),
    ("reported_start_gametime", -1),
    ("reported_start_gametime", True),
    ("reported_start_gametime", 3200),
    ("reported_food_attempt", 0),
    ("reported_food_before", 3121),
    ("reported_food_after", 3121),
    ("reported_food_after", 2**31),
    ("reported_summon_success", 0),
    ("m0_tick_at_food", 12),
    ("m0_tick_at_food", "11"),
])
def test_elapsed_claim_invalid_and_replay_rejection(field, invalid):
    claims = deepcopy(_claims())
    claims[field] = invalid
    with pytest.raises(StartReviewRejected):
        review_elapsed_claim(**claims)


def test_no_host_or_source_auto_provision(tmp_path, capsys):
    with pytest.raises((StartReviewRejected, ValueError, OSError)):
        review_s_start_source(tmp_path, slot=SLOT, nonce=NONCE)
    with pytest.raises((StartReviewRejected, ValueError, OSError)):
        review_staged_clone(
            jar=tmp_path / "missing.jar", golden=tmp_path / "gold",
            manifest=tmp_path / "manifest",
            initial_evidence=tmp_path / "initial",
            staged_clone=tmp_path / "clone",
            s_start_checkout=tmp_path, s_food_checkout=tmp_path,
            slot=SLOT, nonce=NONCE,
        )
    assert main(["--slot", SLOT, "--nonce", NONCE]) == 2
    assert json.loads(capsys.readouterr().out)[
        "classification"
    ] == "RSEE_V6_TWO_PACK_START_SOURCE_BLOCKED"
