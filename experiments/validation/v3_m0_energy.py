"""V3 / #619: new prospective end-energy contrast with strict cheap null.

V2 frozen terminal-time primary was algebraically constant. V3 is an
explicitly versioned design, source-shaped only and never a real-world result.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

MANIFEST = Path(__file__).with_name("v3_m0_energy_manifest.json")
SCHEMA = "RELAYSELF_V3_M0_NET_ENERGY_PROSPECTIVE_1"
PARENT_V2 = "920d5742692d920987d1c321138893cb63c3de8d"
S_HEAD = "28cb0f588192ecfe5d03b12b818508352d1a40a8"
ARMS = ("SENSOR_ON", "SHAM_ON", "SENSOR_MASKED", "CHEAP_NATIVE")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class V3Rejected(ValueError):
    """Changed preregistration, fabricated admission or mismatched comparison."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise V3Rejected(message)


def validate_manifest(d: dict[str, Any]) -> dict[str, Any]:
    require(type(d) is dict and set(d) == {
        "schema", "issue", "predecessor_v2_head",
        "s_groundv2_source_head", "status", "design", "boundaries",
    }, "V3 shape")
    require(d["schema"] == SCHEMA and d["issue"] == 619
            and d["predecessor_v2_head"] == PARENT_V2
            and d["s_groundv2_source_head"] == S_HEAD
            and d["status"] == "PROSPECTIVE_EXPLORATORY_UNRUN", "V3 origin")
    m = d["design"]
    require(type(m) is dict and set(m) == {
        "target", "primary", "explanation", "initial_m0_energy",
        "basal_cost_per_m0_tick", "move_extra_cost",
        "food_energy_per_qualified_eat", "capacity", "global_m0_ticks",
        "total_issued_move_budget", "externally_staged_item_count",
        "s_item_opportunity_m0_tick", "minimum_independent_matched_world_starts",
        "arms", "baseline", "predeclared_pairwise_contrasts",
        "source_budget", "preliminary_interpretation", "cheap_equivalent_if",
        "no_positive_science_from_mechanistic_lesion", "pair_floor_is_power_claim",
    }, "V3 design changed")
    require(m == {
        "target": "HAND_CODED_SENSOR_GATED_FORAGING_EXPRESSION_NOT_LEARNING",
        "primary": "M0_END_ENERGY_AT_GLOBAL_TICK_16",
        "explanation": "E16=12-16*0.5-0.25*issued_moves+4*qualified_meals",
        "initial_m0_energy": 12, "basal_cost_per_m0_tick": 0.5,
        "move_extra_cost": 0.25, "food_energy_per_qualified_eat": 4,
        "capacity": 20, "global_m0_ticks": 16,
        "total_issued_move_budget": 8, "externally_staged_item_count": 1,
        "s_item_opportunity_m0_tick": 11,
        "minimum_independent_matched_world_starts": 4,
        "arms": list(ARMS),
        "baseline": "STRENGTH_MATCHED_NATIVE_ONLY_FOOD_SELECTOR",
        "predeclared_pairwise_contrasts": [
            "ON_MINUS_SHAM", "ON_MINUS_MASKED", "ON_MINUS_CHEAP",
        ],
        "source_budget": "FIXED_WORLD_START_AND_EXOGENOUS_NATIVE_CLOCK_REQUIRED",
        "preliminary_interpretation": "MECHANISTIC_SENSOR_POLICY_CONTRAST_ONLY",
        "cheap_equivalent_if": "CHEAP_EQUAL_OR_BETTER_THAN_ON_AT_MATCHED_BUDGET",
        "no_positive_science_from_mechanistic_lesion": True,
        "pair_floor_is_power_claim": False,
    }, "V3 predeclared primary/physics/comparators changed")
    require(d["boundaries"] == {
        "operator_staged_food_only": True,
        "original_world_clock_pairing_qualified": False,
        "actual_host_original_bytes_verified": False,
        "actual_world_trials": 0,
        "scientific_g3": "NO_GO",
        "real_execution_authorized": False,
        "sensor_learned": False,
        "no_s_file_changes": True,
        "nonissued_wait_not_s16": True,
        "no_s11_habit_grant": True,
    }, "V3 unearned admission")
    return d


def load_manifest() -> dict[str, Any]:
    return validate_manifest(json.loads(MANIFEST.read_text(encoding="utf-8")))


def _sha(x: Any) -> bool:
    return isinstance(x, str) and HEX64.fullmatch(x) is not None


def review_source_shaped(rows: list[dict[str, Any]], *,
                         manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Check numerical identifiability, not physical or scientific evidence."""
    d = validate_manifest(manifest if manifest is not None else load_manifest())
    m = d["design"]
    require(type(rows) is list and bool(rows), "missing source-shaped pairs")
    groups: dict[int, dict[str, dict[str, Any]]] = {}
    sessions: set[str] = set()
    traces: set[str] = set()
    keys = {
        "world_seed", "world_start_sha256", "arm", "session",
        "synthetic_trace_sha256", "source_head", "origin",
        "m0_ticks", "issued_moves", "qualified_meals",
        "end_m0_energy", "native_time_evidence",
        "issued_s16_wait_outcomes", "actual_world_action_count",
    }
    for row in rows:
        require(type(row) is dict and set(row) == keys,
                "unexpected trial shape or real-evidence promotion")
        seed = row["world_seed"]
        require(type(seed) is int and seed >= 0, "invalid seed")
        require(row["arm"] in ARMS, "foreign comparison arm")
        require(row["origin"] == "SYNTHETIC_SOURCE_SHAPED"
                and row["source_head"] == S_HEAD
                and row["native_time_evidence"] == "NOT_ATTESTED",
                "synthetic/physical provenance confusion")
        require(_sha(row["world_start_sha256"])
                and _sha(row["synthetic_trace_sha256"])
                and row["synthetic_trace_sha256"] not in traces,
                "forged/reused digest")
        session = row["session"]
        require(isinstance(session, str) and bool(session)
                and session not in sessions, "session reused/foreign")
        require(row["issued_s16_wait_outcomes"] == 0
                and type(row["issued_s16_wait_outcomes"]) is int
                and row["actual_world_action_count"] == 0
                and type(row["actual_world_action_count"]) is int,
                "fabricated issued WAIT or world run")
        require(type(row["m0_ticks"]) is int
                and row["m0_ticks"] == m["global_m0_ticks"],
                "unmatched full-horizon tick")
        n_move = row["issued_moves"]
        n_eat = row["qualified_meals"]
        require(type(n_move) is int and 0 <= n_move <= m["total_issued_move_budget"]
                and type(n_eat) is int
                and 0 <= n_eat <= m["externally_staged_item_count"],
                "unsupported action or intake budget")
        end = row["end_m0_energy"]
        expected = (
            m["initial_m0_energy"]
            - m["global_m0_ticks"] * m["basal_cost_per_m0_tick"]
            - n_move * m["move_extra_cost"]
            + n_eat * m["food_energy_per_qualified_eat"]
        )
        require(type(end) in (int, float) and math.isfinite(end)
                and 0 < end <= m["capacity"] and end == expected,
                "M0 energy attribution mismatch")
        arm_rows = groups.setdefault(seed, {})
        require(row["arm"] not in arm_rows, "duplicate arm/seed")
        arm_rows[row["arm"]] = row
        sessions.add(session)
        traces.add(row["synthetic_trace_sha256"])
    require(len(groups) >= m["minimum_independent_matched_world_starts"],
            "source starts below feasibility floor")
    unique_starts: set[str] = set()
    details: list[dict[str, Any]] = []
    for seed, peers in sorted(groups.items()):
        require(set(peers) == set(ARMS), "incomplete four-arm matched set")
        starts = {r["world_start_sha256"] for r in peers.values()}
        require(len(starts) == 1, "different source World reset")
        world = starts.pop()
        require(world not in unique_starts, "World reset reused across seeds")
        unique_starts.add(world)
        energies = {arm: r["end_m0_energy"] for arm, r in peers.items()}
        details.append({
            "seed": seed,
            "on_minus_sham": energies["SENSOR_ON"] - energies["SHAM_ON"],
            "on_minus_masked": energies["SENSOR_ON"] - energies["SENSOR_MASKED"],
            "on_minus_cheap": energies["SENSOR_ON"] - energies["CHEAP_NATIVE"],
        })
    cheap_equal_or_better_all = all(
        x["on_minus_cheap"] <= 0 for x in details
    )
    lesion_difference_all = all(
        x["on_minus_masked"] > 0 for x in details
    )
    result = {
        "classification": "V3_SYNTHETIC_ENERGY_CONTRAST_ONLY",
        "primary": m["primary"],
        "paired_world_starts_source_shaped": len(details),
        "pairwise_energy_differences": details,
        "cheap_equal_or_better_on_every_pair": cheap_equal_or_better_all,
        "sensor_on_beats_masked_every_pair": lesion_difference_all,
        "mechanistic_lesion_effect_only": lesion_difference_all,
        "incremental_sensor_benefit_over_strongest_cheap": "NOT_DEMONSTRATED",
        "native_world_food_and_clock": "NOT_ATTESTED",
        "r_original_byte_audit": "NOT_RUN",
        "genuine_s51_eat_provenance": "NOT_ATTESTED",
        "real_world_trials": 0,
        "scientific_g3": "NO_GO",
        "science_go": False,
    }
    return result



def review_fixed_fixture_first_choice(
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Source-conditional policy identifiability at *the* fixed item opportunity.

    The matched first item appears only after 11 M0 basal WAIT charges.
    ON/SHAM and native_only CHEAP all choose SEEK on the same hungry,
    single-item native observation; MASKED reads high and chooses WAIT.
    This is a deterministic G0 mechanism witness, not a World outcome.
    """
    m = validate_manifest(manifest if manifest is not None else load_manifest())["design"]
    e = m["initial_m0_energy"] - (
        m["s_item_opportunity_m0_tick"] * m["basal_cost_per_m0_tick"]
    )
    require(e > 0 and m["s_item_opportunity_m0_tick"] < m["global_m0_ticks"],
            "invalid before-fixture energy or opportunity")
    # Exact pinned S Interoception uses round(x / quantum) * quantum,
    # with the default quantum=1; policy threshold 8 is checked in CI.
    reading = float(round(e))
    fixed_mask_reading = 12.0
    seek_threshold = 8.0
    decisions = {
        "SENSOR_ON": "SEEK" if reading <= seek_threshold else "WAIT",
        "SHAM_ON": "SEEK" if reading <= seek_threshold else "WAIT",
        "SENSOR_MASKED": (
            "SEEK" if fixed_mask_reading <= seek_threshold else "WAIT"
        ),
        "CHEAP_NATIVE": "SEEK",
    }
    require(decisions == {
        "SENSOR_ON": "SEEK", "SHAM_ON": "SEEK",
        "SENSOR_MASKED": "WAIT", "CHEAP_NATIVE": "SEEK",
    }, "first-opportunity choices no longer match source-conditional design")
    return {
        "classification": "V3_FIRST_OPPORTUNITY_ON_CHEAP_POLICY_EQUIVALENCE",
        "fixture_at_m0_tick": m["s_item_opportunity_m0_tick"],
        "pre_fixture_wait_charges": m["s_item_opportunity_m0_tick"],
        "energy_at_first_fixture": e,
        "on_sensor_reading": reading,
        "fixed_mask_sensor_reading": fixed_mask_reading,
        "single_item_qualifier": "NATIVE_HUNGRY_FOOD_LT_14_ONE_ITEM_COMPLETE",
        "decisions": decisions,
        "on_sham_first_choice_equivalent": True,
        "on_cheap_first_choice_equivalent": True,
        "full_world_trajectory_equivalent": "NOT_ATTESTED",
        "incremental_on_benefit_over_cheap_identifiable_from_first_choice": False,
        "world_time_equal_across_arms": "NOT_ATTESTED",
        "source_assumptions": "S_PINNED_M0_AND_B0_L0_CI_ONLY",
        "real_world_trials": 0,
        "science_go": False,
    }


def main() -> int:
    d = load_manifest()
    print(json.dumps({
        "classification": "V3_NEW_PROSPECTIVE_PRIMARY_NOT_RUN",
        "primary": d["design"]["primary"],
        "predecessor_primary": "V2_TERMINAL_TIME_ALGEBRAICALLY_CONSTANT",
        "matched_world_starts": 0,
        "scientific_g3": "NO_GO",
        "real_world_trials": 0,
        "science_go": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
