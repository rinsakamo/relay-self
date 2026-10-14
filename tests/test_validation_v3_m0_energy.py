"""V3 prospective mechanistic end-energy primary; no World/GPU/model."""
from __future__ import annotations

import copy
import hashlib

import pytest

from experiments.validation import v3_m0_energy as v3


def source_cases():
    result = []
    for seed in range(4):
        world = hashlib.sha256(f"synthetic-world-start-{seed}".encode()).hexdigest()
        for arm in v3.ARMS:
            meals = int(arm != "SENSOR_MASKED")
            moves = 0 if arm == "SENSOR_MASKED" else 2
            result.append({
                "world_seed": seed, "world_start_sha256": world, "arm": arm,
                "session": f"shaped-{seed}-{arm}",
                "synthetic_trace_sha256": hashlib.sha256(
                    f"synthetic-trace-{seed}-{arm}".encode()
                ).hexdigest(),
                "source_head": v3.S_HEAD, "origin": "SYNTHETIC_SOURCE_SHAPED",
                "m0_ticks": 16, "issued_moves": moves, "qualified_meals": meals,
                "end_m0_energy": 4 - moves * .25 + 4 * meals,
                "native_time_evidence": "NOT_ATTESTED",
                "issued_s16_wait_outcomes": 0, "actual_world_action_count": 0,
            })
    return result


def test_new_primary_is_versioned_and_does_not_change_frozen_v2():
    m = v3.load_manifest()
    assert m["predecessor_v2_head"] == v3.PARENT_V2
    assert m["design"]["global_m0_ticks"] == 16
    assert m["design"]["primary"] == "M0_END_ENERGY_AT_GLOBAL_TICK_16"
    assert not m["boundaries"]["real_execution_authorized"]
    assert not m["boundaries"]["original_world_clock_pairing_qualified"]
    assert v3.main() == 0


def test_synthetic_on_masked_delta_but_cheap_null_no_science():
    r = v3.review_source_shaped(source_cases())
    assert r["paired_world_starts_source_shaped"] == 4
    assert r["sensor_on_beats_masked_every_pair"]
    assert r["mechanistic_lesion_effect_only"]
    assert r["cheap_equal_or_better_on_every_pair"]
    assert all(x["on_minus_masked"] == 3.5 for x in r["pairwise_energy_differences"])
    assert all(x["on_minus_sham"] == x["on_minus_cheap"] == 0
               for x in r["pairwise_energy_differences"])
    assert r["incremental_sensor_benefit_over_strongest_cheap"] == "NOT_DEMONSTRATED"
    assert r["science_go"] is False and r["real_world_trials"] == 0


@pytest.mark.parametrize(("group", "key", "value"), [
    ("top", "status", "SUCCESS"),
    ("top", "s_groundv2_source_head", "0" * 40),
    ("top", "predecessor_v2_head", "0" * 40),
    ("boundaries", "real_execution_authorized", True),
    ("boundaries", "original_world_clock_pairing_qualified", True),
    ("boundaries", "scientific_g3", "GO"),
    ("design", "primary", "M0_TERMINAL_FREE_TICKS_WITH_CENSORING"),
    ("design", "global_m0_ticks", 24),
    ("design", "total_issued_move_budget", 16),
    ("design", "externally_staged_item_count", 4),
    ("design", "minimum_independent_matched_world_starts", 1),
    ("design", "arms", ["SENSOR_ON", "SENSOR_MASKED"]),
])
def test_unregistered_admission_or_posthoc_primary_rejected(group, key, value):
    d = copy.deepcopy(v3.load_manifest())
    (d if group == "top" else d[group])[key] = value
    with pytest.raises(v3.V3Rejected):
        v3.validate_manifest(d)


@pytest.mark.parametrize(("index", "key", "value"), [
    (0, "source_head", "0" * 40),
    (0, "origin", "REAL_WORLD"),
    (0, "native_time_evidence", "ORIGINAL_VERIFIED"),
    (0, "m0_ticks", 15),
    (0, "issued_moves", 9),
    (0, "issued_moves", -1),
    (0, "qualified_meals", 2),
    (0, "qualified_meals", -1),
    (0, "end_m0_energy", 0),
    (0, "end_m0_energy", 7.75),
    (0, "issued_s16_wait_outcomes", 1),
    (0, "actual_world_action_count", 1),
    (0, "session", "shaped-0-SHAM_ON"),
    (0, "synthetic_trace_sha256", "0" * 64),
    (0, "world_start_sha256", "bad-digest"),
])
def test_source_shaped_evidence_injection_or_inconsistent_energy_rejected(index,key,value):
    rows = source_cases()
    rows[index][key] = value
    with pytest.raises(v3.V3Rejected):
        v3.review_source_shaped(rows)


def test_unmatched_missing_or_replayed_world_rejected():
    rows = source_cases()[:-1]
    with pytest.raises(v3.V3Rejected):
        v3.review_source_shaped(rows)
    rows = source_cases()
    rows[4]["world_start_sha256"] = rows[0]["world_start_sha256"]
    with pytest.raises(v3.V3Rejected):
        v3.review_source_shaped(rows)
    rows = source_cases()
    rows[1]["world_start_sha256"] = rows[4]["world_start_sha256"]
    with pytest.raises(v3.V3Rejected):
        v3.review_source_shaped(rows)
    rows = source_cases()
    rows.append(copy.deepcopy(rows[0]))
    rows[-1]["synthetic_trace_sha256"] = hashlib.sha256(b"distinct").hexdigest()
    rows[-1]["session"] = "distinct-but-duplicate-arm"
    with pytest.raises(v3.V3Rejected):
        v3.review_source_shaped(rows)


def test_cheap_better_than_sensor_no_positive_science_claim():
    rows = source_cases()
    for row in rows:
        if row["arm"] == "SENSOR_ON":
            row["issued_moves"] = 4
            row["end_m0_energy"] = 4 - 1 + 4
    r = v3.review_source_shaped(rows)
    assert r["cheap_equal_or_better_on_every_pair"]
    assert all(x["on_minus_cheap"] == -.5 for x in r["pairwise_energy_differences"])
    assert not r["science_go"]
