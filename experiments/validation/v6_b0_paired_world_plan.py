"""V #619: one bounded S/R handoff plan; never a World runner or scorer.

The pre-registration is an offline source identity and coverage contract.
It cannot attest randomization, source bytes, native elapsed time, S owner
Action issue, real MOVE/EAT or actual survival.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MANIFEST = Path(__file__).with_name("v6_b0_paired_world_plan.json")
V6_G0_HEAD = "7e11d82b9039c5b752b28e84d10168e586329d1a"
S_SOURCE_HEAD = "28cb0f588192ecfe5d03b12b818508352d1a40a8"
STARTS = ("WORLD_START_A", "WORLD_START_B", "WORLD_START_C", "WORLD_START_D")
REGIMES = (("LOW", 12), ("HIGH", 20))
ARMS = (
    "SENSOR_ON", "SHAM_ON", "SENSOR_MASKED_HIGH",
    "ALWAYS_SEEK", "ALWAYS_WAIT", "EQUAL_INFO_CHEAP_THRESHOLD",
)


class V6PlanRejected(ValueError):
    """Unregistered arm/World or unearned host physical qualification."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise V6PlanRejected(reason)


def load_plan_spec() -> dict[str, Any]:
    d = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return validate_plan_spec(d)


def validate_plan_spec(d: dict[str, Any]) -> dict[str, Any]:
    require(type(d) is dict and set(d) == {
        "schema", "issue", "parent_v6_head", "s_source_head", "scope",
        "intent", "design", "endpoints", "admission",
    }, "unexpected V6 paired plan shape")
    require(
        d["schema"] == "RELAYSELF_V6_B0_PAIRED_WORLD_PRE_ADMISSION_1"
        and d["issue"] == 619
        and d["parent_v6_head"] == V6_G0_HEAD
        and d["s_source_head"] == S_SOURCE_HEAD
        and d["scope"] == "ONE_COHERENT_PROSPECTIVE_S_R_HANDOFF_NO_WORLD_RUN"
        and d["intent"] == "B0_L0_FUNCTIONAL_STATE_DEPENDENCE_NOT_LEARNED_COGNITION",
        "unqualified protocol source/scope",
    )
    # Fail closed on any post-registration mutation, even one that looks
    # favorable; S/R must create an independently reviewed successor.
    registered = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(d == registered, "frozen paired design or admission mutated")
    g = d["design"]
    require(
        g["independent_world_start_slots"] == list(STARTS)
        and g["regimes"] == [
            {"id": "LOW", "initial_m0_energy": 12},
            {"id": "HIGH", "initial_m0_energy": 20},
        ]
        and g["arms"] == list(ARMS)
        and g["total_planned_world_sessions"] == 48
        and (g["first_opportunity_m0_tick"], g["fixed_global_horizon_m0_ticks"],
             g["max_issued_move_per_session"]) == (11, 16, 8)
        and (g["per_tick_basal_cost"], g["per_issued_move_extra"],
             g["verified_eat_credit"]) == (.5, .25, 4)
        and (g["initial_native_food"], g["item_count"], g["item"],
             g["item_initial_distance_m"]) == (13, 1, "rotten_flesh", 2.5)
        and g["pre_item_m0_waits"] == 11,
        "B0 actual G0/source contract changed",
    )
    require(
        g["exogenous_food_schedule"]
        == "SAME_NATIVE_ELAPSED_WORLD_TICK_ACROSS_ARMS_WITHIN_EACH_WORLD_START_OR_INVALID"
        and g["native_world_start"]
        == "IDENTICAL_R_QUALIFIED_GOLDEN_CLONES_PER_START_REQUIRED"
        and g["clock"] == "M0_DECISION_TICKS_NOT_WORLD_TICKS"
        and g["no_retry_or_fallback"] is True
        and g["new_explicit_permission_per_session"] is True,
        "World clock/authorization silently weakened",
    )
    e = d["endpoints"]
    require(
        e["primary"] ==
        "TRUE_M0_FINAL_ENERGY_AT_GLOBAL_TICK16_WITH_VALID_TERMINAL_AND_CENSORING"
        and e["primary_contrasts"] == [
            "ON_MINUS_ALWAYS_SEEK_BY_REGIME",
            "ON_MINUS_ALWAYS_WAIT_BY_REGIME",
        ]
        and e["additional_controls"] == [
            "ON_MINUS_SHAM_BY_REGIME", "ON_MINUS_MASKED_BY_REGIME",
            "ON_MINUS_EQUAL_INFO_CHEAP_BY_REGIME",
        ]
        and e["feasibility_floor_not_power_calculation"] is True
        and e["require_complete_including_failures"] is True
        and e["null"] == "ENERGY_BLIND_POLICY_MAY_OUTPERFORM_ON_OR_TIE",
        "outcome selection/power/cheap control changed",
    )
    a = d["admission"]
    require(
        a == {
            "source_supported_only": True,
            "six_arm_s_real_controller": False,
            "high_energy_s_real_config": False,
            "world_time_exogenous_parity": False,
            "same_world_reset_r_attested": False,
            "physical_action_outcome_r_attested": False,
            "native_nonissued_wait_r_attested": False,
            "golden_reference_frozen": False,
            "prospective_real_trial_authorized": False,
            "actual_world_trials": 0,
            "actual_efficacy_results": 0,
            "b0_science_g3": "NO_GO",
            "production_go": False,
        },
        "counterfeit R/S authority or physical promotion",
    )
    return d


def offline_session_slots() -> list[dict[str, Any]]:
    """48 *slots*; never real session/world IDs or permits.

    Interleave paired conditions with a fixed cyclic offset across starts.
    The labels are placeholders; an R-qualified real start fingerprint must
    replace them in a separate authorized original-byte trial, not here.
    """
    _ = load_plan_spec()
    grid = [(regime, arm) for regime, _ in REGIMES for arm in ARMS]
    rows = []
    for i, start in enumerate(STARTS):
        rotated = grid[i * 3:] + grid[:i * 3]
        for j, (regime, arm) in enumerate(rotated):
            rows.append({
                "world_start_slot": start,
                "planned_order": j,
                "regime": regime,
                "arm": arm,
                "initial_m0_energy": dict(REGIMES)[regime],
                "world_start_digest": None,
                "native_opportunity_time_attested": False,
                "s_physical_arm_implemented": False,
                "user_live_grant": False,
                "world_run_status": "NOT_RUN",
            })
    return validate_offline_slots(rows)


def validate_offline_slots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    d = load_plan_spec()
    require(type(rows) is list and len(rows) == d["design"]["total_planned_world_sessions"],
            "incomplete planned cohort")
    expected = [(regime, arm) for regime, _ in REGIMES for arm in ARMS]
    allowed = {
        "world_start_slot", "planned_order", "regime", "arm",
        "initial_m0_energy", "world_start_digest",
        "native_opportunity_time_attested", "s_physical_arm_implemented",
        "user_live_grant", "world_run_status",
    }
    for i, start in enumerate(STARTS):
        block = rows[i * 12:(i + 1) * 12]
        rotated = expected[i * 3:] + expected[:i * 3]
        for j, row in enumerate(block):
            regime, arm = rotated[j]
            require(type(row) is dict and set(row) == allowed
                    and row["world_start_slot"] == start
                    and type(row["planned_order"]) is int
                    and row["planned_order"] == j
                    and row["regime"] == regime
                    and row["arm"] == arm
                    and type(row["initial_m0_energy"]) is int
                    and row["initial_m0_energy"] == dict(REGIMES)[regime],
                    "altered regime/arm pairing or run order")
            require(
                row["world_start_digest"] is None
                and row["native_opportunity_time_attested"] is False
                and row["s_physical_arm_implemented"] is False
                and row["user_live_grant"] is False
                and row["world_run_status"] == "NOT_RUN",
                "fabricated World start, grant or trial evidence",
            )
    return rows


def main() -> int:
    rows = offline_session_slots()
    print(json.dumps({
        "classification": "V6_PAIRED_WORLD_PRE_ADMISSION_PROTOCOL_ONLY",
        "total_unexecuted_session_slots": len(rows),
        "number_of_real_world_trials": 0,
        "s_full_six_arm_mode_qualified": False,
        "r_native_elapsed_world_clock_matched": False,
        "science_g3": "NO_GO",
        "production_go": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
