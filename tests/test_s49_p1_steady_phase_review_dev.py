"""Original S49 two preloaded P1 model motor cases: steady phase sources."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.s49_p1_matched_boost_review_dev import (
    compare_matched_boost_pairs_dev,
)
from adapters.mineflayer.s49_p1_steady_phase_review_dev import (
    SteadyPhaseRejected,
    compare_steady_phase_dev,
    node_positive_transitions_dev,
)
from test_s49_p1_matched_boost_review_dev import (
    synced_example,
    synthetic_source,
)
from test_s49_speed_attr_boundary_dev import trace


def example():
    previous = synced_example()
    source = {case: synthetic_source(case, previous)
              for case in ("CARRY", "WAIT_ASSUMED")}
    paired = compare_matched_boost_pairs_dev(previous, source)
    raw = {}
    for case in ("CARRY", "WAIT_ASSUMED"):
        a = paired["arms"][case]
        t = trace()
        t["session_id"] = a["session_id"]
        t["action_id"] = a["action_id"]
        # S49 original callback source is still the only physical native owner.
        if case == "WAIT_ASSUMED":
            for row in t["rows"]:
                if row["kind"] == "ACTIVE_PHYSICS":
                    row["z"] *= 1.2
        raw[case] = t
    return paired, raw


def test_paper_bonus_ordinal_2_to_7_and_local_node_positive_transitions():
    paired, raw = example()
    saved = deepcopy((paired, raw))
    result = compare_steady_phase_dev(paired, raw)
    assert (paired, raw) == saved
    assert result["paper_first_bonus_sample_excluded"] is True
    assert result["node_first_positive_bonus_sample_excluded"] is True
    assert result["paper_bonus_count_per_world"] == 7
    assert result["node_common_stable_intervals"] == 2
    assert result["node_common_stable_mean_speed_proxy_gain_mps"] > 0
    assert len(result["paper_stable_speed_delta_by_ordinal_mps"]) == 6
    assert result["node_physics_20hz_nominal_not_attested"] is True
    assert result["world_tick_phase_synchronized"] is False
    assert result["causal_fatigue_effect_size_identified"] is False
    assert result["physical_l0_dash_capability_admitted"] is None
    assert result["new_native_action_issuers"] == 0
    assert result["qualification_go"] is False


def test_real_negative_speed_result_keeps_hypothetical_limit_unqualified():
    paired, raw = example()
    # Genuine identical within-clock velocities are not a failed source proof.
    raw["WAIT_ASSUMED"] = deepcopy(raw["CARRY"])
    raw["WAIT_ASSUMED"]["session_id"] = paired["arms"]["WAIT_ASSUMED"]["session_id"]
    raw["WAIT_ASSUMED"]["action_id"] = paired["arms"]["WAIT_ASSUMED"]["action_id"]
    result = compare_steady_phase_dev(paired, raw)
    assert result["node_common_stable_mean_speed_proxy_gain_mps"] == pytest.approx(0)
    assert result["node_common_speed_gain_positive"] is False
    assert result["physical_l0_dash_capability_admitted"] is None


@pytest.mark.parametrize("fault", [
    "foreign_session", "other_action", "sync_disabled", "unverified_paper",
    "native_clock_claim", "added_issuer", "extra_reader", "bad_p1_claim",
    "missing_node", "bad_model", "bonus_count", "world_clock_conflated",
    "l0_granted", "qualified", "missing_end", "duplicate_physics",
    "nonfinite_position", "unbounded_physics", "missing_source",
])
def test_any_tampered_world_local_motor_phase_rejected(fault):
    paired, raw = example()
    carry, rested = raw["CARRY"], raw["WAIT_ASSUMED"]
    if fault == "foreign_session":
        carry["session_id"] = "other"
    elif fault == "other_action":
        rested["action_id"] = "not-s49"
    elif fault == "sync_disabled":
        rested["sync_enabled"] = False
    elif fault == "unverified_paper":
        paired["classification"] = "NATIVE_P1_QUALIFIED"
    elif fault == "native_clock_claim":
        rested["paper_clock_synchronized"] = True
    elif fault == "added_issuer":
        rested["added_issuers"] = 1
    elif fault == "extra_reader":
        rested["added_readers"] = 1
    elif fault == "bad_p1_claim":
        rested["source_attested"] = True
    elif fault == "missing_node":
        raw.pop("CARRY")
    elif fault == "bad_model":
        paired["model_preload_not_actual_longitudinal_p1_recovery"] = False
    elif fault == "bonus_count":
        paired["arms"]["CARRY"]["exact_paper_positive_bonus_ticks"] = 6
    elif fault == "world_clock_conflated":
        paired["world_clock_phase_matched"] = True
    elif fault == "l0_granted":
        paired["physical_l0_dash_power_admission"] = 1.
    elif fault == "qualified":
        paired["qualification_go"] = True
    elif fault == "missing_end":
        rested["complete"] = False
    elif fault == "duplicate_physics":
        rested["rows"][5]["physics_ordinal"] = 2
    elif fault == "nonfinite_position":
        rested["rows"][5]["z"] = float("nan")
    elif fault == "unbounded_physics":
        rested["rows"][4]["physics_movement_speed"]["modifiers"][0]["amount"] = 3
    else:
        paired["arms"]["WAIT_ASSUMED"]["session_id"] = "different"
    with pytest.raises(SteadyPhaseRejected):
        compare_steady_phase_dev(paired, raw)


def test_first_unboosted_node_sample_allowed_but_steady_core_stays_bounded():
    paired, raw = example()
    t = raw["CARRY"]
    t["rows"][3]["physics_movement_speed"] = None
    with pytest.raises(SteadyPhaseRejected):
        node_positive_transitions_dev(
            t, sid=paired["arms"]["CARRY"]["session_id"],
            aid=paired["arms"]["CARRY"]["action_id"],
        )
