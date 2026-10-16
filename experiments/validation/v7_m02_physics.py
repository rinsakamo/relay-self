"""V7: prospective M0.2 two-factor physical cost discrimination; SYNTHETIC ONLY.

The qualified M0.2 Paper reference is a single engineering capability witness.
This module does not retrieve or relabel that physical run and NEVER starts a
World or authorizes SCIENCE. It computes reference arithmetic against a frozen
new five-arm 2x2+sham design. Native food-meter deltas are NOT a substitute for
World tick or packet-based billed exhaustion.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

MANIFEST = Path(__file__).with_name("v7_m02_physics_manifest.json")
SCHEMA = "RELAYSELF_V7_M02_PHYSICS_IDENTIFIABILITY_PREREG_V1"
CLASSIFICATION = "V7_M02_SYNTHETIC_INSTRUMENT_ARITHMETIC_ONLY"
ARMS = ("BASE_ON", "SHAM_ON", "BASAL_ZERO", "WALK_ZERO", "BOTH_ZERO")
MULTIPLIERS = {"BASE_ON": (1, 1), "SHAM_ON": (1, 1),
               "BASAL_ZERO": (0, 1), "WALK_ZERO": (1, 0),
               "BOTH_ZERO": (0, 0)}
SEEDS = (61021, 61022, 61023, 61024)
TICKS = 200
BASAL_RATE = 0.001
WALK_RATE = 0.01
TOLERANCE = 0.005
SHA256 = re.compile("[0-9a-f]{64}\\Z")
TRIAL_KEYS = {
    "origin", "seed", "arm", "nonce", "synthetic_setup_sha256",
    "synthetic_trace_sha256", "world_ticks", "motion_packets",
    "observed_path_blocks", "billed_basal", "billed_walk",
    "walk_native_event_replacement", "other_charges",
    "native_food_end", "native_saturation_end",
    "virtual_m0_ledger_used", "science_attested",
}


class V7Rejected(ValueError):
    """Do not admit altered preregistration or forged/promoted records."""


def require(value: bool, message: str) -> None:
    if not value:
        raise V7Rejected(message)


def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for k, v in pairs:
        require(k not in obj, "duplicate manifest key")
        obj[k] = v
    return obj


def finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink()
            and path.stat().st_size <= 32768, "invalid manifest path/size")
    raw = path.read_bytes()
    try:
        o = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(
                           V7Rejected("nonfinite manifest value")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise V7Rejected("unreadable manifest") from exc
    return validate_manifest(o)


def validate_manifest(o: Any) -> dict[str, Any]:
    require(type(o) is dict and set(o) == {
        "schema", "authority_issue", "status", "question",
        "source_qualification", "design", "rate_arms", "invariants", "boundaries",
    }, "manifest shape changed")
    require(o["schema"] == SCHEMA and o["authority_issue"] == 619
            and o["status"] == "PROSPECTIVE_OFFLINE_ONLY", "V authority/status")
    require(o["question"] ==
            "CAN_PAPER_BASAL_AND_WALK_CHARGES_BE_SEPARATELY_IDENTIFIED_UNDER_MATCHED_WORLD_TICKS_AND_OBSERVED_MOTION",
            "question replaced")
    src = o["source_qualification"]
    require(src == {
        "classification": "M02_RSEE_PAPER_CANDIDATE_ENGINEERING_QUALIFIED",
        "original_physical_run": 38730925452,
        "original_artifact_id": 11970775361,
        "s_producer_head": "50d3dfe96a37d18cc8fec68334cfc2e0204a996b",
        "r_independent_head": "0d2c57a4112389e9612fefa306d9abbc131b5d25",
        "m_engine_head": "4c2f549c6b9ed3fbe2ee04230526ac5577da8feb",
        "qualification_scope": "BASAL_WALK_S50_MOVE_S51_EAT_ONLY_NOT_ECOLOGY_OR_SCIENCE",
    }, "physical reference is immutable and scope bounded")
    d = o["design"]
    require(type(d) is dict and set(d) == {
        "cohort", "independent_seeds", "arms_order",
        "trials_per_seed", "total_planned_trials", "world_minecraft_version",
        "server", "java_major", "duration_world_ticks",
        "walk_nominal_step_blocks", "max_observed_path_blocks",
        "matched_path_tolerance_blocks", "initial_food", "initial_saturation",
        "no_food_introduction", "no_hunger_effect", "no_damage",
        "player", "primary", "secondary", "contrasts", "cost_rule",
        "statistical_claim", "decision_rule", "stop_rule", "source_rule",
        "clock_rule", "cheap_null_rule", "unit",
    }, "design changed")
    require(d["cohort"] == "FOUR_INDEPENDENT_WORLD_SEEDS_FIVE_PAIRED_ARMS"
            and d["independent_seeds"] == list(SEEDS)
            and d["arms_order"] == list(ARMS)
            and type(d["trials_per_seed"]) is int
            and d["trials_per_seed"] == 5
            and type(d["total_planned_trials"]) is int
            and d["total_planned_trials"] == 20,
            "paired factorial/feasibility count")
    require(d["world_minecraft_version"] == "1.21.8"
            and d["server"] == "Paper_build_60"
            and type(d["java_major"]) is int and d["java_major"] == 21
            and type(d["duration_world_ticks"]) is int
            and d["duration_world_ticks"] == TICKS
            and d["walk_nominal_step_blocks"] == 1
            and d["max_observed_path_blocks"] == 2
            and d["matched_path_tolerance_blocks"] == TOLERANCE
            and d["initial_food"] == 20
            and d["initial_saturation"] == 5
            and d["player"] == "RelaySelf"
            and all(d[k] is True for k in (
                "no_food_introduction", "no_hunger_effect", "no_damage")),
            "World clock/environment changed")
    require(d["primary"] ==
            "ORIGINAL_SOURCE_BILLED_EXHAUSTION_SEPARATED_BY_BASAL_WORLD_TICK_AND_WALK_PLAYER_MOVE_PACKET"
            and d["secondary"] == [
                "NATIVE_FOOD_SATURATION_HEALTH", "WALK_EVENT_REPLACEMENT_ZERO",
                "BODY_TICK_MONOTONICITY", "HOST_CPU_WALL_VRAM_SEPARATE",
            ]
            and d["contrasts"] == [
                "BASE_ON_MINUS_SHAM_ON", "BASE_ON_MINUS_BASAL_ZERO",
                "BASE_ON_MINUS_WALK_ZERO", "ADD_INTERACTION_FOUR_CELL",
            ]
            and d["cost_rule"] == "q_times_standard_multiplier_plus_additional"
            and d["unit"] == "Minecraft_exhaustion", "endpoints changed")
    require(d["statistical_claim"] ==
            "DESCRIPTIVE_PAIRED_MECHANISM_FEASIBILITY_NOT_POWERED_OR_ECOLOGICAL_CALIBRATION"
            and d["decision_rule"] ==
            "PREDECLARED_PER_SEED_NO_DROPPED_TRIALS_REPORT_INVALID_SEPARATELY_NO_POSTHOC_TUNING"
            and d["stop_rule"] ==
            "EACH_SLOT_STOP_AFTER_200_REAL_WORLD_TICKS_OR_TERMINAL_PRESERVE_ALL_ATTEMPTS"
            and d["source_rule"] ==
            "NEW_S_OWNED_EPISODE_AND_INDEPENDENT_R_V_ORIGINAL_BILLING_WORLD_TICK_PATH_AND_PROCESS_WITNESS"
            and d["clock_rule"] ==
            "WORLD_SERVER_TICKS_NOT_M0_LEDGER_NOT_HOST_ELAPSED_SECONDS"
            and d["cheap_null_rule"] ==
            "ON_VERSUS_SHAM_MUST_BE_NULL_TO_WITHIN_SOURCE_NUMERIC_TOLERANCE",
            "science admission weakened")
    require(type(o["rate_arms"]) is dict and set(o["rate_arms"]) == set(ARMS),
            "arm changed")
    for arm, (basal, walk) in MULTIPLIERS.items():
        require(o["rate_arms"][arm] == {
            "basal_multiplier": basal, "walk_multiplier": walk},
            "factor values or sham modified")
    require(o["invariants"] == {
        "basal_standard": BASAL_RATE, "walk_standard": WALK_RATE,
        "additional": 0, "all_16_action_entries_preserved": True,
        "non_cognition_enabled_bools_unchanged": True,
        "cognition_still_off": True,
        "m0_virtual_energy_ledger_forbidden": True,
        "only_basal_and_walk_multiplier_change": True,
        "paper_source_qualification_NOT_reused_for_changed_configs": True,
        "separate_S_DEV_exploration_allowed": True,
        "qualification_originals_never_changed": True,
        "v2_v6_frozen_studies_not_reinterpreted": True,
    }, "profile or historical boundary changed")
    require(o["boundaries"] == {
        "r_physical_arm_admission": "NOT_RUN",
        "s_paired_arm_runner": "NOT_IMPLEMENTED",
        "actual_20_science_world_trials": 0,
        "third_qualification_grant_consumed": True,
        "science_execution_authorized": False,
        "world_launches_by_v7": 0,
        "v_science_go": False,
        "ecological_calibration_qualified": False,
        "cognition_benefit_qualified": False,
        "production_go": False,
    }, "science promotion or consumed grant reused")
    return o


def review_synthetic(rows: list[dict[str, Any]],
                     plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """Review ALL 20 artificial rows; no source hashes prove real World events."""
    validate_manifest(load_manifest() if plan is None else plan)
    require(type(rows) is list and len(rows) == 20,
            "all twenty original planned slots required even for synthetic")
    seen_nonces: set[str] = set()
    seen_trace: set[str] = set()
    by_seed: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    summary: list[dict[str, Any]] = []
    for row in rows:
        require(type(row) is dict and set(row) == TRIAL_KEYS, "synthetic-only row shape")
        seed, arm = row["seed"], row["arm"]
        require(type(seed) is int and seed in SEEDS and arm in ARMS,
                "foreign seed/arm")
        require(arm not in by_seed[seed], "duplicate seed-arm slot")
        require(row["origin"] == "SYNTHETIC_ONLY"
                and row["science_attested"] is False
                and row["virtual_m0_ledger_used"] is False,
                "attempted real evidence promotion or M0 ledger reuse")
        nonce, setup, trace = (
            row["nonce"], row["synthetic_setup_sha256"],
            row["synthetic_trace_sha256"],
        )
        require(type(nonce) is str and bool(re.fullmatch("[0-9a-f]{32}", nonce))
                and nonce not in seen_nonces
                and type(setup) is str and bool(SHA256.fullmatch(setup))
                and type(trace) is str and bool(SHA256.fullmatch(trace))
                and trace not in seen_trace, "reused or invalid synthetic identity")
        seen_nonces.add(nonce)
        seen_trace.add(trace)
        require(type(row["world_ticks"]) is int and row["world_ticks"] == TICKS
                and type(row["motion_packets"]) is int
                and 1 <= row["motion_packets"] <= 100,
                "native World tick or motion packet count mismatch")
        for name in ("observed_path_blocks", "billed_basal", "billed_walk",
                     "walk_native_event_replacement", "other_charges",
                     "native_saturation_end"):
            require(finite(row[name]), "invalid numeric source")
        x = row["observed_path_blocks"]
        require(0.5 < x <= 2, "physical path must be bounded in blocks")
        require(row["walk_native_event_replacement"] == 0
                and row["other_charges"] == 0
                and type(row["native_food_end"]) is int
                and 0 <= row["native_food_end"] <= 20
                and 0 <= row["native_saturation_end"] <= 20,
                "source nonmovement double charge or invalid native readout")
        basal, walk = MULTIPLIERS[arm]
        expected_basal = TICKS * BASAL_RATE * basal
        expected_walk = x * WALK_RATE * walk
        require(abs(row["billed_basal"] - expected_basal) <= 1e-8
                and abs(row["billed_walk"] - expected_walk) <= 1e-8,
                "source charges incompatible with preregistered physics rule")
        by_seed[seed][arm] = row
    require(set(by_seed) == set(SEEDS), "missing seed")
    for seed in SEEDS:
        arms = by_seed[seed]
        require(set(arms) == set(ARMS), "incomplete paired arms")
        require(len({v["synthetic_setup_sha256"] for v in arms.values()}) == 1,
                "paired seed setup mismatch")
        paths = [v["observed_path_blocks"] for v in arms.values()]
        require(max(paths) - min(paths) <= TOLERANCE, "unmatched actual paths")
        def bill(arm: str) -> float:
            v = arms[arm]
            return v["billed_basal"] + v["billed_walk"]
        contrast_sham = bill("BASE_ON") - bill("SHAM_ON")
        contrast_basal = bill("BASE_ON") - bill("BASAL_ZERO")
        contrast_walk = bill("BASE_ON") - bill("WALK_ZERO")
        interaction = (bill("BASE_ON") - bill("BASAL_ZERO")
                       - bill("WALK_ZERO") + bill("BOTH_ZERO"))
        require(abs(contrast_sham) <= 1e-7
                and abs(contrast_basal - TICKS * BASAL_RATE) <= 1e-7
                and abs(contrast_walk - WALK_RATE * paths[0]) <= 1e-4
                and abs(interaction) <= 1e-4,
                "per-seed factorial arithmetic/parity violation")
        summary.append({
            "seed": seed, "on_minus_sham": contrast_sham,
            "basal_effect": contrast_basal,
            "walk_effect": contrast_walk,
            "interaction": interaction,
            "walk_to_basal_ratio": contrast_walk / contrast_basal,
        })
    return {
        "classification": CLASSIFICATION,
        "mode": "SYNTHETIC_ONLY", "synthetic_rows": len(rows),
        "per_seed_descriptive_contrasts": summary,
        "actual_world_starts": 0, "v_science_go": False,
        "ecological_calibration_qualified": False,
        "cognition_benefit_qualified": False, "production_go": False,
        "required_next": [
            "S_PAIRED_PAPER_RUNNER_IN_DISPOSABLE_DEV",
            "R_NEW_FOUR_PROFILE_BINARY_CONFIG_WORLD_IDENTITY_ADMISSION",
            "V_PREREG_ORIGINAL_WORLD_TICK_AND_PACKET_BILLING_ATTESTATION",
            "FRESH_EXPLICIT_SCIENCE_EXECUTION_AUTHORIZATION",
        ],
    }


def synthetic_fixture() -> list[dict[str, Any]]:
    """Deterministic test data, not actual Paper source and never inference."""
    rows = []
    for i, seed in enumerate(SEEDS):
        path = 1.1 + i * 0.05
        setup = hashlib.sha256(f"synthetic-setup-{seed}".encode()).hexdigest()
        for j, arm in enumerate(ARMS):
            basal, walk = MULTIPLIERS[arm]
            rows.append({
                "origin": "SYNTHETIC_ONLY", "seed": seed, "arm": arm,
                "nonce": f"{seed:08x}{j:024x}",
                "synthetic_setup_sha256": setup,
                "synthetic_trace_sha256": hashlib.sha256(
                    f"synthetic-trace-{seed}-{arm}".encode()).hexdigest(),
                "world_ticks": TICKS, "motion_packets": 9,
                "observed_path_blocks": path,
                "billed_basal": TICKS * BASAL_RATE * basal,
                "billed_walk": path * WALK_RATE * walk,
                "walk_native_event_replacement": 0.0,
                "other_charges": 0.0,
                "native_food_end": 20, "native_saturation_end": 5.0,
                "virtual_m0_ledger_used": False,
                "science_attested": False,
            })
    return rows


def main() -> None:
    report = review_synthetic(synthetic_fixture())
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
