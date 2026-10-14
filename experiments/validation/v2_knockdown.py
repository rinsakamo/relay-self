"""V2 / #619: strict preregistration and nonpromoting synthetic lesion review.

No World, model, host originals, Action owner, scientific evidence or toggles.
The S-owned source is reviewed only by exact-HEAD, isolated CI checkout.
"""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

SCHEMA = "RELAYSELF_V2_KNOCKDOWN_PREREG_1"
PROTOCOL = Path(__file__).with_name("v2_knockdown_manifest.json")
V_HEAD = "53d50029da64a95c56bb56c6d48b5d14ce94e84a"
S_HEAD = "34cf226e55645f85172317172c37ae6cbd481ae4"
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
ARMS = ("SENSOR_ON", "SHAM_ON", "SENSOR_MASKED", "CHEAP_NATIVE")
SENSORS = {
    "SENSOR_ON": ("sensor_gate", 1, 0, 1),
    "SHAM_ON": ("sensor_gate", 1, 0, 1),
    "SENSOR_MASKED": ("sensor_gate", 0, 12, 1),
    "CHEAP_NATIVE": ("native_only", 1, 0, 1),
}


class V2Rejected(ValueError):
    """Unregistered design, fabricated admission, or incomparable evidence."""


def require(condition: bool, why: str) -> None:
    if not condition:
        raise V2Rejected(why)


def _sha(x: Any) -> bool:
    return isinstance(x, str) and SHA256.fullmatch(x) is not None


def validate_protocol(d: dict[str, Any]) -> dict[str, Any]:
    require(type(d) is dict and set(d) == {
        "schema", "issue", "status", "sources", "arms", "design", "boundaries",
    }, "manifest top-level")
    require(d["schema"] == SCHEMA and d["issue"] == 619, "authority identity")
    require(d["status"] == "PROSPECTIVE_OFFLINE_ONLY", "status promotion")
    require(d["sources"] == {
        "v1_head": V_HEAD, "s_sensor_head": S_HEAD, "s_product_pr": 545,
        "v1_pr": 595, "m0_issue": 616, "product_issue": 537, "rsee_issue": 575,
    }, "pinned source / ownership changed")
    require(type(d["arms"]) is dict and set(d["arms"]) == set(ARMS), "missing arm")
    for name, expected in SENSORS.items():
        a = d["arms"][name]
        require(type(a) is dict and set(a) == {
            "forage_policy", "gain", "bias", "quantum", "toggle_path",
        }, "arm shape")
        require((a["forage_policy"], a["gain"], a["bias"], a["quantum"])
                == expected and a["toggle_path"] == "sensor_setting",
                "arm sensor/policy/sham mismatch")
    z = d["design"]
    require(type(z) is dict and set(z) == {
        "study", "intended_reference", "minimum_independent_world_starts",
        "horizon_m0_ticks", "max_issued_moves", "exogenous_food_schedule",
        "no_forced_seeking", "wait_semantics", "stop_rule", "primary",
        "secondary", "baseline_rule", "source_rule", "analysis_rule",
    }, "design shape")
    require(z["study"] == "ACQUIRED_STATE_EXPRESSION_ONLY_NOT_DEVELOPMENT"
            and z["intended_reference"] == "FROZEN_REAL_PRODUCT_NOT_YET_ELIGIBLE",
            "unqualified reference Self")
    require(type(z["minimum_independent_world_starts"]) is int
            and z["minimum_independent_world_starts"] == 4, "paired-seed count")
    require(type(z["horizon_m0_ticks"]) is int and z["horizon_m0_ticks"] == 16
            and type(z["max_issued_moves"]) is int
            and z["max_issued_moves"] == 8, "precommitted horizon/budget")
    require(z["no_forced_seeking"] is True
            and z["wait_semantics"] == "NONISSUED_BOUNDED_OBSERVATION"
            and z["stop_rule"] == "RUN_TO_M0_TERMINAL_OR_16_TICKS_REPORT_CENSORING",
            "WAIT handling / biased stopping")
    require(z["exogenous_food_schedule"]
            == "PRECOMMITTED_IDENTICAL_PER_PAIRED_WORLD_START", "food allocation")
    require(z["primary"] == "M0_TERMINAL_FREE_TICKS_WITH_CENSORING",
            "primary endpoint changed")
    require(z["secondary"] == [
        "NATIVE_S51_EAT_OUTCOME_COUNT", "M0_FINAL_ENERGY",
        "M0_NET_ENERGY", "NATIVE_MOVE_COUNT", "RESOURCE_COSTS",
        "FOOD_SOURCE_PROVENANCE",
    ], "secondary outcomes changed")
    require(z["baseline_rule"]
            == "SENSOR_ON_MUST_BE_COMPARED_WITH_SHAM_AND_STRONGEST_CHEAP_NATIVE",
            "cheap baseline missing")
    require(z["source_rule"]
            == "INDEPENDENT_ORIGINAL_BYTES_WORLD_RESET_GOAL_AND_ACTION_CHAIN_REQUIRED_FOR_LIVE",
            "live evidence weakened")
    require(z["analysis_rule"]
            == "MATCHED_WORLD_SEED_ARM_LEVEL_CONTRAST_PREDECLARED_NO_POSTHOC_TUNING",
            "non-preregistered analysis")
    require(d["boundaries"] == {
        "m0_physics_always_on": True, "safety_l0_always_on": True,
        "action_authority_unchanged": True,
        "goal_attestation_not_implemented": True,
        "non_forcing_world_runner_not_implemented": True,
        "original_byte_audit_not_run": True,
        "consumed_grants_not_reusable": True,
        "real_world_runs_authorized": False,
        "physical_runs": 0, "model_calls": 0,
        "science_go": False, "production_go": False,
    }, "evidence admission or authority forged")
    return d


def load_protocol() -> dict[str, Any]:
    return validate_protocol(json.loads(PROTOCOL.read_text(encoding="utf-8")))


def review_synthetic_records(
    records: list[dict[str, Any]], protocol: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe bounded *synthetic* paired contrasts, never qualify real science.

    Source hashes in fixture records are mere strings, not verified originals.
    No 'physical', 'authenticated', or arbitrary promotion fields are accepted.
    """
    d = validate_protocol(protocol if protocol is not None else load_protocol())
    require(type(records) is list and bool(records), "no synthetic records")
    expected_keys = {
        "seed", "arm", "session_id", "world_start_sha256",
        "synthetic_trace_sha256", "source_head", "origin", "runner_mode",
        "wait_nonissued", "m0_terminal_free_ticks", "termination",
        "synthetic_eat_count", "synthetic_moves", "final_m0_energy",
        "simulated_work_units",
    }
    groups: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    sessions: set[str] = set()
    traces: set[str] = set()
    for r in records:
        require(type(r) is dict and set(r) == expected_keys, "trial shape or promotion")
        require(type(r["seed"]) is int and r["seed"] >= 0, "seed")
        require(r["arm"] in ARMS and r["arm"] not in groups[r["seed"]],
                "missing/duplicated policy")
        require(r["source_head"] == S_HEAD and r["origin"] == "SYNTHETIC",
                "reported/real-source masquerading as synthetic")
        require(r["runner_mode"] == "NON_FORCING_SOURCE_SHAPED"
                and r["wait_nonissued"] is True, "forced SEEK/WAIT fake S16")
        require(isinstance(r["session_id"], str) and bool(r["session_id"])
                and r["session_id"] not in sessions, "session alias/reuse")
        require(_sha(r["world_start_sha256"])
                and _sha(r["synthetic_trace_sha256"])
                and r["synthetic_trace_sha256"] not in traces,
                "invalid/reused digest")
        require(type(r["m0_terminal_free_ticks"]) is int
                and 0 <= r["m0_terminal_free_ticks"]
                <= d["design"]["horizon_m0_ticks"], "invalid horizon")
        require(r["termination"] in ("HORIZON_CENSORED", "M0_STARVATION"),
                "invalid termination")
        require((r["termination"] == "HORIZON_CENSORED")
                == (r["m0_terminal_free_ticks"]
                    == d["design"]["horizon_m0_ticks"]),
                "censor vs terminal inconsistent")
        for k in ("synthetic_eat_count", "synthetic_moves", "simulated_work_units"):
            require(type(r[k]) is int and r[k] >= 0, "invalid synthetic count")
        require(r["synthetic_moves"] <= d["design"]["max_issued_moves"],
                "move budget exceeded")
        e = r["final_m0_energy"]
        require(type(e) in (float, int) and math.isfinite(e)
                and 0 <= e <= 20, "energy range")
        require((e == 0) == (r["termination"] == "M0_STARVATION"),
                "M0 terminal energy inconsistent")
        sessions.add(r["session_id"])
        traces.add(r["synthetic_trace_sha256"])
        groups[r["seed"]][r["arm"]] = r
    require(len(groups) >= d["design"]["minimum_independent_world_starts"],
            "insufficient distinct synthetic starts")
    results: list[dict[str, Any]] = []
    starts: set[str] = set()
    for seed, arm_rows in sorted(groups.items()):
        require(set(arm_rows) == set(ARMS), "unpaired four-arm source")
        ids = {r["world_start_sha256"] for r in arm_rows.values()}
        require(len(ids) == 1, "arms lack common reset reference")
        start = ids.pop()
        require(start not in starts, "World-start alias across seeds")
        starts.add(start)
        results.append({
            "seed": seed,
            "sensor_minus_sham_ticks": (
                arm_rows["SENSOR_ON"]["m0_terminal_free_ticks"]
                - arm_rows["SHAM_ON"]["m0_terminal_free_ticks"]
            ),
            "sensor_minus_masked_ticks": (
                arm_rows["SENSOR_ON"]["m0_terminal_free_ticks"]
                - arm_rows["SENSOR_MASKED"]["m0_terminal_free_ticks"]
            ),
            "sensor_minus_cheap_ticks": (
                arm_rows["SENSOR_ON"]["m0_terminal_free_ticks"]
                - arm_rows["CHEAP_NATIVE"]["m0_terminal_free_ticks"]
            ),
        })
    return {
        "classification": "V2_SYNTHETIC_PAIRED_CONTRAST_ONLY",
        "paired_starts": len(results),
        "pairwise_ticks": results,
        "physically_independent_original_bytes": "NOT_RUN",
        "behavioral_survival": "NOT_ATTESTED",
        "sensor_causal_outcome": "NOT_DEMONSTRATED",
        "cheap_baseline_dominance": "NOT_DEMONSTRATED",
        "scientific_g3": "NO_GO",
        "science_go": False, "product_go": False,
        "new_world_runs": 0, "model_calls": 0,
    }


def check_preregistered_primary_reachability(
    protocol: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Conditional algebraic ceiling; never infer actual physical outcomes.

    M0 source values originate in the frozen S-owned B0 reference and
    must be rechecked independently in a pinned source checkout.
    Counts include all non-eating WAIT/MOVE ticks. EAT only adds energy;
    FIGHT is outside this prospective S ground-foraging runner.
    """
    d = validate_protocol(protocol if protocol is not None else load_protocol())
    # S's frozen MetabolismConfig: initial=12, basal=0.5, MOVE extra=0.25.
    # These are conditional source assertions, not an R-host attestation.
    initial_energy = 12.0
    basal_cost = 0.5
    move_extra_cost = 0.25
    horizon = d["design"]["horizon_m0_ticks"]
    max_moves = d["design"]["max_issued_moves"]
    worst_case_consumption = (
        horizon * basal_cost + min(horizon, max_moves) * move_extra_cost
    )
    min_final_energy = initial_energy - worst_case_consumption
    require(min_final_energy > 0, "primary survival bound changed; reassess")
    return {
        "classification": "V2_PRIMARY_ENDPOINT_STRUCTURALLY_NONDISCRIMINATING",
        "source": "S_M0_CONFIG_OFFLINE_CONDITIONAL_NOT_PHYSICAL_ATTESTATION",
        "initial_energy": initial_energy,
        "horizon_m0_ticks": horizon,
        "max_total_moves": max_moves,
        "basal_cost_per_tick": basal_cost,
        "extra_cost_per_move": move_extra_cost,
        "max_spend_without_food": worst_case_consumption,
        "min_end_energy_without_food": min_final_energy,
        "terminal_reachable_by_registered_actions": False,
        "terminal_free_ticks_for_all_complete_valid_arms": horizon,
        "scope": "WAIT_OR_MOVE_ONLY_NONNEGATIVE_INTAKE_SINGLE_ITEM",
        "real_world_trials": 0,
        "requires_prospective_redesign_for_terminal_discrimination": True,
        "science_go": False,
    }


def main() -> int:
    d = load_protocol()
    print(json.dumps({
        "classification": "V2_PREREGISTRATION_ONLY",
        "schema": d["schema"], "issue": d["issue"],
        "arms": list(d["arms"]),
        "minimum_world_starts_future": d["design"]["minimum_independent_world_starts"],
        "non_forcing_runner": "NOT_IMPLEMENTED",
        "actual_world_trial": "NOT_RUN",
        "science_go": False, "new_world_runs": 0, "model_calls": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
