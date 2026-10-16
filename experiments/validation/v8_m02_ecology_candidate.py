"""V8 candidate future natural-map metabolism/viability protocol, offline only.

Unlike the frozen V7 within-arm billing study, realized walking distance is
an outcome or mediator, NEVER an across-arm entry condition. No SCIENCE grant,
real-world trial or qualification is made by this candidate protocol.
"""
from __future__ import annotations

import copy
import json
from typing import Any

CLASS = "V8_M02_ECOLOGICAL_VIABILITY_PROTOCOL_CANDIDATE_NOT_ADMITTED"
ARMS = ("BASE_ON", "SHAM_ON", "BASAL_ZERO", "WALK_ZERO", "BOTH_ZERO")
MULTIPLIERS = {
    "BASE_ON": (1, 1), "SHAM_ON": (1, 1),
    "BASAL_ZERO": (0, 1), "WALK_ZERO": (1, 0),
    "BOTH_ZERO": (0, 0),
}
SEEDS = tuple(range(62101,62109))


class NotAdmitted(ValueError):
    pass


def candidate() -> dict[str, Any]:
    """Proposed pre-registration *draft*, not science admission or power."""
    return {
        "schema": "RELAYSELF_V8_M02_NATURAL_MAP_VIABILITY_CANDIDATE_V1",
        "authority_issue": 619,
        "status": "DESIGN_ONLY_UNAPPROVED",
        "predecessor_v7": {
            "science_trials_executed": 0,
            "source_accounting_only": True,
            "retroactive_path_gate_change": False,
            "physical_qualification_of_changed_jar": False,
        },
        "design": {
            "purpose": "METABOLIC_COST_VIABILITY_IN_FINITE_RANDOM_TERRAIN",
            "seeds": list(SEEDS),
            "arms": list(ARMS),
            "trials_per_seed": 5,
            "proposed_physical_science_sessions": len(SEEDS)*len(ARMS),
            "science_power_claim": False,
            "dev_feasibility_before_prereg": True,
            "world": "PAPER_1_21_8_SURVIVAL_HARD_ISOLATED_FINITE_FOOD",
            "max_player_world_ticks_candidate": 24000,
            "hardware_time_is_not_world_ticks": True,
            "pre_action_snapshot":
                "SAME_SEED_AND_IMMUTABLE_CLONED_CHUNK_WORLD_BYTES_ACROSS_5_ARMS",
            "start_pose":
                "SAME_PHYSICAL_XYZ_YAW_PITCH_PER_SEED_CONFIRMED_AFTER_NATIVE_SPAWN",
            "world_state_controls": [
                "NO_MOBS_OR_ENEMIES", "NO_COMPETITORS", "NO_REPRODUCTION",
                "NO_UNRECORDED_FOOD", "NO_OPERATOR_INTERVENTION_AFTER_START",
                "FINITE_DECLARED_FOOD_OPPORTUNITY_PER_SEED",
                "EQUAL_INITIAL_FOOD_SATURATION_HEALTH",
                "EQUAL_SERVER_DIFFICULTY_WEATHER_WORLD_TICK_PHASE",
                "ALL_SESSION_PID_STOP_CLEANUP_AND_WITNESS",
            ],
            "policy": "SAME_CHEAP_NATIVE_L0_SEEK_MOVE_EAT_WITH_L1_L2_OFF",
            "fixed_food_source": "TRANSPARENT_OPERATOR_PLACED_FINITE_DEV_RESOURCE_NOT_NATURAL_PREY",
            "food_position": "SEED_DETERMINISTIC_AND_IDENTICAL_IN_CLONED_WORLD",
            "allowed_cost_interventions": "BASAL_AND_WALK_MULTIPLIERS_ONLY",
            "primary": [
                "SURVIVAL_TIME_IN_TRUE_WORLD_TICKS_INTENTION_TO_TREAT",
                "CUMULATIVE_ACTUAL_EDIBLE_FOOD_GAINED",
                "NATIVE_FOOD_SATURATION_HEALTH_TRAJECTORY",
            ],
            "secondary": [
                "SOURCE_REQUESTED_BASAL_PER_REAL_PLAYER_TICK",
                "SOURCE_WALK_EXHAUSTION_PER_ACTUAL_PACKET_PATH_BLOCK",
                "REAL_WORLD_HORIZONTAL_DISTANCE_AND_DISPLACEMENT",
                "BLOCKED_DETOUR_NO_MOVE_AND_DEATH_OUTCOMES",
                "FOOD_SOURCE_DISTANCE_AND_OBSTACLE_ACCESS",
                "ACTUAL_L0_MOVES_EATS_AND_ACTION_OUTCOMES",
            ],
            "distance_policy":
                "OBSERVE_ALL_ACTUAL_PATHS_NO_MATCHED_DISTANCE_GATE_NO_POSTHOC_REWEIGHTING",
            "stopping": "MAX_WORLD_TICKS_OR_DEATH_OR_TERMINAL_RECORD_ALL_ATTEMPTS",
            "host_abort_handling": "HOST_FAILURE_CENSORED_NOT_SURVIVAL_OR_DEATH",
            "statistics": "SEED_BLOCKED_FACTORIAL_WITH_SHAM_DESCRIPTIVE_NOT_POWERED",
            "causal_comparison_guard":
                "START_SNAPSHOT_AND_POLICY_CONTROL_REQUIRED_NOT_EQUAL_REALIZED_PATHS",
            "scientific_no_go_until": [
                "FRESH_R_QUALIFIED_CHANGED_PAPER_PLUGIN_AND_ALL_PROFILES",
                "PROSPECTIVE_WORLD_CLONE_TERRAIN_POSE_NATIVE_TICK_READBACK",
                "EXPLICIT_NEW_V_SCIENCE_AUTHORIZATION",
                "FEASIBILITY_PILOT_SEPARATELY_RETAINED_AS_DEV",
                "PREREGISTERED_TERMINAL_RULE_AND_ALL_TRIAL_SLOTS_FROZEN",
            ],
        },
        "boundaries": {
            "new_world_starts": 0,
            "science_trials": 0,
            "qualifying_new_run": False,
            "v8_science_go": False,
            "g3_go": False,
            "production_go": False,
            "cognition_benefit_assessed": False,
            "biological_evolution_fitness_assessed": False,
        },
    }


def review_plan(x: Any) -> dict[str, Any]:
    expected=candidate()
    if type(x) is not dict or x != expected:
        raise NotAdmitted("prospective V8 design candidate modified or incomplete")
    d=x["design"]
    if (len(set(d["seeds"])) != len(SEEDS)
            or len(d["arms"]) != len(ARMS)
            or d["distance_policy"] !=
            "OBSERVE_ALL_ACTUAL_PATHS_NO_MATCHED_DISTANCE_GATE_NO_POSTHOC_REWEIGHTING"):
        raise NotAdmitted("candidate identity/distance rule rejected")
    return {
        "classification": CLASS,
        "draft_seed_count": len(SEEDS),
        "draft_arm_count": len(ARMS),
        "draft_future_science_slots": d["proposed_physical_science_sessions"],
        "all_new_science_trials_unexecuted": True,
        "minimum_control_required": {
            "world_clone_bytes": True,
            "native_pose": True,
            "full_world_tick_window": True,
            "obstacles_not_excluded_after_outcome": True,
            "actual_walk_path_can_differ": True,
        },
        "next_step": "PILOT_DEV_ONLY_THEN_SEPARATE_R_QUALIFICATION_AND_V_PREREG_GRANT",
        "science_go": False,
        "production_go": False,
    }


def main() -> None:
    print(json.dumps(review_plan(copy.deepcopy(candidate())), sort_keys=True))


if __name__ == "__main__":
    main()
