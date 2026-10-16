"""P1-D synthetic negative controls; no real World or V SCIENCE analysis."""
from __future__ import annotations

import copy
import json
from dataclasses import replace

import pytest

from experiments.p1d_evaluation import (
    ARMS,
    CLASS,
    CONTRASTS,
    SEEDS,
    CheapRestState,
    P1DRejected,
    Trial,
    candidate,
    cheap_rest_proposal,
    describe,
    load_plan,
    roster,
    unrun_roster,
    validate_plan,
)


@pytest.fixture
def plan():
    return candidate()


def fixture_trial(seed, arm, *, status="HORIZON", start="a" * 64,
                  source="b" * 64, food=2, rest=0, ticks=2400, **changes):
    default = dict(
        seed=seed, arm=arm, status=status, session_id=f"synthetic:{seed}:{arm}",
        world_start_sha256=start, original_source_sha256=source,
        world_ticks_observed=ticks, edible_food_consumed=food,
        rest_ticks=rest, observed_move_blocks=12.75,
        cpu_ms=101.5, llm_tokens=0,
    )
    default.update(changes)
    return Trial(**default)


def replace_slot(records, seed, arm, **changes):
    return tuple(replace(x, **changes) if (x.seed, x.arm) == (seed, arm) else x
                 for x in records)


def full_synthetic(records=None):
    records = unrun_roster() if records is None else records
    return tuple(fixture_trial(t.seed, t.arm, rest=0 if t.arm == "FATIGUE_OFF_L0" else 5,
                               food=2 if t.arm != "ON_L1" else 3)
                 for t in records)


def test_manifest_candidate_is_explicitly_unapproved(plan, tmp_path):
    p = tmp_path / "p1d.json"
    p.write_text(json.dumps(plan), encoding="utf-8")
    loaded = load_plan(p)
    assert validate_plan(loaded) == validate_plan(plan)
    assert loaded["status"] == "UNAPPROVED_PROSPECTIVE_PROPOSAL_OFFLINE_ONLY"
    assert loaded["golden_freeze"] == "NOT_PRESENT"
    assert loaded["science_grant"] is False
    assert loaded["science_trials"] == 0
    assert loaded["slots_candidate"] == len(SEEDS) * len(ARMS) == 48
    assert len({x[0] for x in CONTRASTS}) > 1


@pytest.mark.parametrize("key,value", [
    ("science_grant", True),
    ("status", "SCIENCE_QUALIFIED"),
    ("golden_freeze", "DONE"),
    ("science_trials", 1),
    ("world_ticks_max_candidate", 999),
    ("slots_candidate", 47),
    ("world_profile_path", "different.json"),
    ("production_go", True),
    ("power_claim", True),
])
def test_cannot_upgrade_or_mutate_candidate(plan, key, value):
    different = copy.deepcopy(plan)
    different[key] = value
    with pytest.raises(P1DRejected):
        validate_plan(different)


def test_future_randomization_requires_new_prospective_version(plan):
    altered = copy.deepcopy(plan)
    altered["independent_seed_ids_candidate"].reverse()
    with pytest.raises(P1DRejected):
        validate_plan(altered)
    altered = copy.deepcopy(plan)
    altered["arms_order"].reverse()
    with pytest.raises(P1DRejected):
        validate_plan(altered)


@pytest.mark.parametrize("payload", [
    '{"schema":"A","schema":"B"}',
    '{"schema":NaN}',
    '{"schema":Infinity}',
    '{"schema":true}',
    '{malformed',
])
def test_strict_json_load_rejects_wrong_input(tmp_path, payload):
    file = tmp_path / "candidate.json"
    file.write_text(payload, encoding="utf-8")
    with pytest.raises(P1DRejected):
        load_plan(file)


def test_missing_plan_fails_closed(tmp_path):
    with pytest.raises(P1DRejected):
        load_plan(tmp_path / "absent.json")


def test_roster_complete_ordered_deterministic_distinct_and_no_run(plan):
    r1, r2 = roster(), roster()
    assert r1 == r2 and len(r1) == 48 and len(set(r1)) == 48
    assert all(sum(seed == s for seed, _ in r1) == len(ARMS) for s in SEEDS)
    assert all(set(arm for s, arm in r1 if s == seed) == set(ARMS) for seed in SEEDS)
    assert tuple((t.seed, t.arm) for t in unrun_roster()) == r1
    result = describe(unrun_roster(), plan=plan)
    assert result["classification"] == CLASS
    assert result["statuses"] == {"NOT_RUN": 48}
    assert result["expected_slots"] == 48
    assert result["science_go"] is False and result["scientific_effect_claim"] is False
    for pair in result["contrasts"].values():
        assert pair["n_paired_arithmetic_only"] == 0
        assert pair["mean_food_delta_if_observable"] is None
        assert pair["mean_survival_fraction_delta_if_observable"] is None
        assert pair["unpaired_reasons"] == {"UNPAIRED_MISSING_CENSORED_OR_INVALID": 8}


def test_fixed_l0_is_world_tick_not_action_count():
    rests = [t for t in range(100) if cheap_rest_proposal("ON_FIXED_L0_REST", t)[0]]
    assert rests == [19, 39, 59, 79, 99]
    assert not any(cheap_rest_proposal("FATIGUE_OFF_L0", t)[0] for t in range(100))
    assert cheap_rest_proposal("ON_FIXED_L0_REST", 19)[1] == CheapRestState()


def test_fsm_hysteresis_only_quantized_sensor_not_evaluator_truth():
    sensor = [0.0, .6, .7, .9, .5, .3, .8, .1]
    state = CheapRestState()
    proposals = []
    for tick, reading in enumerate(sensor):
        proposal, state = cheap_rest_proposal("ON_FSM_SENSOR", tick,
                                             sensor_reading=reading, state=state)
        proposals.append(proposal)
    assert proposals == [False, False, True, True, True, False, True, False]
    assert not hasattr(state, "fatigue")


@pytest.mark.parametrize("arm,clock,sensor", [
    ("ON_L1", 10, .9),
    ("ON_L2", 10, .9),
    ("ON_L1_SHAM", 10, .9),
    ("ON_FSM_SENSOR", 10, None),
    ("ON_FSM_SENSOR", 10, float("nan")),
    ("ON_FSM_SENSOR", 10, float("inf")),
    ("ON_FIXED_L0_REST", -1, None),
    ("ON_FIXED_L0_REST", True, None),
])
def test_no_advanced_policy_or_invalid_world_clock(arm, clock, sensor):
    with pytest.raises(P1DRejected):
        cheap_rest_proposal(arm, clock, sensor_reading=sensor)


def test_synthetic_complete_arithmetic_is_never_scientific_result(plan):
    r = full_synthetic()
    out = describe(r, plan=plan)
    contrast = out["contrasts"]["ON_L1_MINUS_ON_FIXED_L0_REST"]
    assert contrast["n_paired_arithmetic_only"] == 8
    assert contrast["mean_food_delta_if_observable"] == 1
    assert contrast["mean_survival_fraction_delta_if_observable"] == 0
    assert len(contrast["paired_seed_descriptors"]) == 8
    assert out["science_go"] is False
    assert out["no_source_originals_authenticated_by_this_code"] is True
    assert out["no_v_preregistration_or_power"] is True


def test_valid_death_retained_as_paired_physical_failure(plan):
    r = full_synthetic()
    seed = SEEDS[0]
    r = replace_slot(r, seed, "ON_L1", status="DEATH", world_ticks_observed=400,
                     edible_food_consumed=0)
    out = describe(r, plan=plan)
    pair = out["contrasts"]["ON_L1_MINUS_ON_FIXED_L0_REST"]
    assert pair["n_paired_arithmetic_only"] == 8
    assert pair["paired_seed_descriptors"][0]["survival_fraction_difference"] == pytest.approx(
        (400 - 2400) / 2400
    )
    assert out["statuses"] == {"DEATH": 1, "HORIZON": 47}


def test_different_world_start_not_a_paired_result(plan):
    r = full_synthetic()
    r = replace_slot(r, SEEDS[0], "ON_L1", world_start_sha256="c" * 64)
    out = describe(r, plan=plan)
    contrast = out["contrasts"]["ON_L1_MINUS_ON_FIXED_L0_REST"]
    assert contrast["n_paired_arithmetic_only"] == 7
    assert contrast["unpaired_reasons"] == {"UNPAIRED_DIFFERENT_NATIVE_WORLD_START": 1}


@pytest.mark.parametrize("status", ["INFRA_ABORT", "SOLO_INVALID", "SOURCE_UNQUALIFIED"])
def test_censored_status_kept_and_never_faked_as_food_zero(plan, status):
    r = full_synthetic()
    seed = SEEDS[0]
    invalid = Trial(seed, "ON_L1", status, session_id="incomplete-recorded",
                    world_ticks_observed=21)
    r = tuple(invalid if (x.seed, x.arm) == (seed, "ON_L1") else x for x in r)
    report = describe(r, plan=plan)
    assert report["statuses"][status] == 1
    contrast = report["contrasts"]["ON_L1_MINUS_ON_FIXED_L0_REST"]
    assert contrast["n_paired_arithmetic_only"] == 7
    assert contrast["unpaired_reasons"] == {"UNPAIRED_MISSING_CENSORED_OR_INVALID": 1}


@pytest.mark.parametrize("bad", [
    {"world_ticks_observed": None},
    {"world_ticks_observed": 0},
    {"world_ticks_observed": 2401},
    {"world_ticks_observed": 2399},
    {"world_ticks_observed": True},
    {"edible_food_consumed": -1},
    {"edible_food_consumed": 1.5},
    {"rest_ticks": 2401},
    {"rest_ticks": True},
    {"observed_move_blocks": -1},
    {"observed_move_blocks": float("nan")},
    {"cpu_ms": float("inf")},
    {"llm_tokens": -1},
    {"llm_tokens": True},
    {"original_source_sha256": "fake"},
    {"world_start_sha256": "different"},
    {"session_id": ""},
])
def test_physical_receipts_strict_on_all_arms(plan, bad):
    r = full_synthetic()
    r = replace_slot(r, SEEDS[0], "ON_L1", **bad)
    with pytest.raises(P1DRejected):
        describe(r, plan=plan)


def test_off_l0_cannot_claim_rest(plan):
    r = replace_slot(full_synthetic(), SEEDS[0], "FATIGUE_OFF_L0", rest_ticks=1)
    with pytest.raises(P1DRejected, match="REST"):
        describe(r, plan=plan)


@pytest.mark.parametrize("status", ["INFRA_ABORT", "SOLO_INVALID", "SOURCE_UNQUALIFIED"])
def test_invalid_never_has_primary_endpoint(plan, status):
    r = full_synthetic()
    replacement = fixture_trial(SEEDS[0], "ON_L1", status=status)
    r = tuple(replacement if (x.seed, x.arm) == (SEEDS[0], "ON_L1") else x for x in r)
    with pytest.raises(P1DRejected):
        describe(r, plan=plan)


def test_not_run_cannot_carry_a_made_up_receipt(plan):
    r = replace_slot(unrun_roster(), SEEDS[0], "ON_L1", session_id="pretend")
    with pytest.raises(P1DRejected):
        describe(r, plan=plan)


def test_duplicate_session_across_arms_fails(plan):
    r = replace_slot(full_synthetic(), SEEDS[0], "ON_L1",
                     session_id=f"synthetic:{SEEDS[0]}:ON_L2")
    with pytest.raises(P1DRejected, match="reused"):
        describe(r, plan=plan)


def test_cannot_cherry_pick_or_shuffle_slots(plan):
    r = full_synthetic()
    for broken in (r[:-1], tuple(reversed(r)), r[:-1] + (r[0],), r + (r[0],)):
        with pytest.raises(P1DRejected):
            describe(broken, plan=plan)


def test_no_match_on_realized_distance_or_cpu_budget(plan):
    r = replace_slot(full_synthetic(), SEEDS[0], "ON_L1",
                     observed_move_blocks=0, cpu_ms=9000, llm_tokens=550)
    report = describe(r, plan=plan)
    assert report["contrasts"]["ON_L1_MINUS_ON_FIXED_L0_REST"]["n_paired_arithmetic_only"] == 8
    assert report["science_go"] is False


def test_all_infra_blocked_does_not_become_strong_null(plan):
    r = tuple(Trial(x.seed, x.arm, "INFRA_ABORT",
                    session_id=f"synthetic-block:{x.seed}:{x.arm}") for x in unrun_roster())
    result = describe(r, plan=plan)
    assert result["statuses"] == {"INFRA_ABORT": 48}
    assert all(x["mean_food_delta_if_observable"] is None
               for x in result["contrasts"].values())
    assert result["scientific_effect_claim"] is False