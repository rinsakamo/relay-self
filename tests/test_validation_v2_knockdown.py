"""#619 V-owned preregistration negatives; synthetic contrasts are never science."""
from __future__ import annotations

import copy
import hashlib

import pytest

from experiments.validation import v2_knockdown as v2


def fixture_records():
    rows = []
    for seed in range(4):
        start = hashlib.sha256(f"world-start-{seed}".encode()).hexdigest()
        for arm in v2.ARMS:
            ticks = 16 if arm != "SENSOR_MASKED" else 8
            rows.append({
                "seed": seed, "arm": arm, "session_id": f"synthetic-{seed}-{arm}",
                "world_start_sha256": start,
                "synthetic_trace_sha256": hashlib.sha256(
                    f"synthetic-stream-{seed}-{arm}".encode()
                ).hexdigest(),
                "source_head": v2.S_HEAD, "origin": "SYNTHETIC",
                "runner_mode": "NON_FORCING_SOURCE_SHAPED",
                "wait_nonissued": True, "m0_terminal_free_ticks": ticks,
                "termination": "HORIZON_CENSORED" if ticks == 16 else "M0_STARVATION",
                "synthetic_eat_count": int(arm != "SENSOR_MASKED"),
                "synthetic_moves": 2 if arm != "SENSOR_MASKED" else 0,
                "final_m0_energy": 8 if ticks == 16 else 0,
                "simulated_work_units": 3 if arm == "CHEAP_NATIVE" else 4,
            })
    return rows


def test_preregistered_bounded_design_is_not_an_experiment():
    d = v2.load_protocol()
    assert list(d["arms"]) == list(v2.ARMS)
    assert v2.main() == 0
    assert not d["boundaries"]["science_go"]
    assert not d["boundaries"]["real_world_runs_authorized"]


@pytest.mark.parametrize(("section", "key", "value"), [
    ("sources", "s_sensor_head", "0" * 40),
    ("sources", "v1_head", "0" * 40),
    ("boundaries", "science_go", True),
    ("boundaries", "original_byte_audit_not_run", False),
    ("boundaries", "real_world_runs_authorized", True),
    ("boundaries", "physical_runs", 1),
    ("design", "no_forced_seeking", False),
    ("design", "minimum_independent_world_starts", 1),
    ("design", "horizon_m0_ticks", 999),
    ("design", "wait_semantics", "FAKE_S16_WAIT_OUTCOME"),
    ("design", "intended_reference", "GOLDEN_SCIENCE_PASS"),
])
def test_design_cannot_be_modified_to_promote_science(section, key, value):
    d = copy.deepcopy(v2.load_protocol())
    d[section][key] = value
    with pytest.raises(v2.V2Rejected):
        v2.validate_protocol(d)


def test_masked_is_explicit_bias12_not_unbiased_sensor_removal():
    d = copy.deepcopy(v2.load_protocol())
    d["arms"]["SENSOR_MASKED"]["bias"] = 0
    with pytest.raises(v2.V2Rejected):
        v2.validate_protocol(d)
    d = copy.deepcopy(v2.load_protocol())
    d["arms"]["SHAM_ON"]["forage_policy"] = "native_only"
    with pytest.raises(v2.V2Rejected):
        v2.validate_protocol(d)


def test_v2_primary_terminal_endpoint_is_unreachable_under_fixed_m0_budget():
    result = v2.check_preregistered_primary_reachability()
    assert result["classification"] == "V2_PRIMARY_ENDPOINT_STRUCTURALLY_NONDISCRIMINATING"
    assert result["initial_energy"] == 12
    assert result["horizon_m0_ticks"] == 16
    assert result["max_total_moves"] == 8
    assert result["max_spend_without_food"] == 10
    assert result["min_end_energy_without_food"] == 2
    assert result["terminal_reachable_by_registered_actions"] is False
    assert result["terminal_free_ticks_for_all_complete_valid_arms"] == 16
    assert result["requires_prospective_redesign_for_terminal_discrimination"]
    assert not result["science_go"] and result["real_world_trials"] == 0


def test_v2_ceiling_does_not_silently_rewrite_frozen_manifest():
    d = v2.load_protocol()
    before = copy.deepcopy(d)
    v2.check_preregistered_primary_reachability(d)
    assert d == before
    d["design"]["horizon_m0_ticks"] = 24
    with pytest.raises(v2.V2Rejected):
        v2.check_preregistered_primary_reachability(d)


def test_synthetic_positive_difference_never_means_scientific_gain():
    out = v2.review_synthetic_records(fixture_records())
    assert out["paired_starts"] == 4
    assert all(x["sensor_minus_masked_ticks"] == 8 for x in out["pairwise_ticks"])
    assert all(x["sensor_minus_cheap_ticks"] == 0 for x in out["pairwise_ticks"])
    assert out["science_go"] is False
    assert out["sensor_causal_outcome"] == "NOT_DEMONSTRATED"
    assert out["physically_independent_original_bytes"] == "NOT_RUN"


@pytest.mark.parametrize(("index", "field", "value"), [
    (0, "origin", "GITHUB_REPORTED_PHYSICAL"),
    (0, "source_head", "0" * 40),
    (0, "runner_mode", "FORCED_SEEK_OR_REJECT_WAIT"),
    (0, "wait_nonissued", False),
    (0, "termination", "M0_STARVATION"),
    (0, "m0_terminal_free_ticks", 999),
    (0, "final_m0_energy", 0),
    (0, "synthetic_moves", 9),
    (0, "synthetic_eat_count", -1),
    (0, "session_id", "synthetic-0-SHAM_ON"),
    (0, "world_start_sha256", "0" * 64),
    (0, "synthetic_trace_sha256", "0"),
])
def test_bad_evidence_or_forced_world_rejected(index, field, value):
    rows = fixture_records()
    rows[index][field] = value
    with pytest.raises(v2.V2Rejected):
        v2.review_synthetic_records(rows)


def test_no_missing_arms_or_world_seed_aliases():
    rows = fixture_records()[:-1]
    with pytest.raises(v2.V2Rejected):
        v2.review_synthetic_records(rows)
    rows = fixture_records()
    rows[4]["world_start_sha256"] = rows[0]["world_start_sha256"]
    with pytest.raises(v2.V2Rejected):
        v2.review_synthetic_records(rows)
    rows = fixture_records()
    rows[4]["synthetic_trace_sha256"] = rows[0]["synthetic_trace_sha256"]
    with pytest.raises(v2.V2Rejected):
        v2.review_synthetic_records(rows)


def test_live_original_claims_cannot_be_smuggled_into_fixture():
    rows = fixture_records()
    rows[0]["physical_original_verified"] = True
    with pytest.raises(v2.V2Rejected):
        v2.review_synthetic_records(rows)
    rows = fixture_records()
    rows[0]["origin"] = "PHYSICAL"
    with pytest.raises(v2.V2Rejected):
        v2.review_synthetic_records(rows)


def test_study_cannot_drop_cheapest_equal_info_control():
    rows = [r for r in fixture_records() if r["arm"] != "CHEAP_NATIVE"]
    with pytest.raises(v2.V2Rejected):
        v2.review_synthetic_records(rows)
