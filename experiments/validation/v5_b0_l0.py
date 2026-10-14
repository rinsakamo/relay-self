"""B0/L0 bacteria-like scope: prospective source-only validation, not World trials."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MANIFEST = Path(__file__).with_name("v5_b0_l0_manifest.json")
SCHEMA = "RELAYSELF_V5_B0_L0_PROSPECTIVE_1"
V4_HEAD = "4c5de5fd111fd35c29bf5431eb681e87220035f7"
S_HEAD = "28cb0f588192ecfe5d03b12b818508352d1a40a8"
REGIMES = ("LOW_ENERGY", "HIGH_ENERGY")
ARMS = (
    "SENSOR_ON", "SHAM_ON", "MASKED_HIGH",
    "ALWAYS_SEEK", "ALWAYS_WAIT", "EQUAL_INFORMATION_THRESHOLD",
)


class V5Rejected(ValueError):
    """Invalid source, scope, physical promotion or reinterpreted control."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise V5Rejected(reason)


def load_manifest() -> dict[str, Any]:
    return validate_manifest(json.loads(MANIFEST.read_text(encoding="utf-8")))


def validate_manifest(d: dict[str, Any]) -> dict[str, Any]:
    need(type(d) is dict and set(d) == {
        "schema", "issue", "parent_v4_head", "s_source_head", "status",
        "required_mechanisms", "not_required_at_b0",
        "scientific_targets", "prospective", "admission", "frozen",
    }, "V5 shape changed")
    need(
        d["schema"] == SCHEMA and d["issue"] == 619
        and d["parent_v4_head"] == V4_HEAD and d["s_source_head"] == S_HEAD
        and d["status"] == "B0_CONCEPTUAL_SCOPE_OFFLINE_ONLY",
        "origin or status changed",
    )
    need(d["required_mechanisms"] == [
        "L0_NATIVE_OBSERVE_DECIDE", "M0_ENERGY_AND_SENSOR",
        "WORLD_ACTION_OUTCOME", "SAME_BODY_MULTIEPOCH_CONTINUITY",
    ] and d["not_required_at_b0"] == [
        "L1", "L2", "LEARNING", "MEMORY_HABIT", "REPRODUCTION", "EVOLUTION",
    ], "B0 capability level changed")
    need(d["scientific_targets"] == {
        "t1": "STATE_CONDITIONAL_SEEK_WAIT_FROM_INTEROCEPTION",
        "t2": "WORLD_VERIFIED_NET_VIABILITY_VERSUS_ENERGY_BLIND_CONTROLS",
        "t3": "EXTRA_COMPLEX_COGNITION_VERSUS_EQUAL_INFORMATION_CHEAP_NOT_REQUIRED",
        "higher_cognition_equal_information_cheap_null_preserved": True,
    }, "B0 target/advanced claim changed")
    need(d["prospective"] == {
        "regimes": list(REGIMES), "controls": list(ARMS),
        "primary_candidate": "REAL_WORLD_NET_M0_ENERGY_WITH_TERMINAL_AND_CENSORING",
        "fixed_threshold": 8, "fixed_quantum": 1,
        "masked_gain": 0, "masked_bias": 12,
        "initial_energy_for_existing_b0": 12, "capacity": 20,
        "basal": .5, "move_extra": .25, "verified_eat_credit": 4,
        "external_food_and_hazard_schedule": "REQUIRED_BEFORE_OUTCOMES",
        "source_matched_native_world_time": "REQUIRED_BY_R",
        "no_posthoc_optimization": True,
        "cheap_information_equivalence_allowed_for_b0": True,
        "learn_train_holdout_required_for_b0": False,
        "train_holdout_required_for_future_learning_claim": True,
    }, "future preregistration changed")
    need(d["admission"] == {
        "physical_multiregime_s_implemented": False,
        "real_world_source_clock_qualified": False,
        "original_b0_r_readback": "REVIEW_ONLY_58_FILES_50_OF_50",
        "new_world_trials": 0, "new_user_grants": False,
        "ecological_effect": "UNTESTED",
        "science_go": False, "production_go": False,
    } and d["frozen"] == ["V2", "V3", "V4"], "unearned qualification")
    return d


def source_only_l0_matrix() -> dict[str, Any]:
    """Conditional S policy at synthetic native-hungry one-item source."""
    d = load_manifest()
    x = d["prospective"]
    cases = {"LOW_ENERGY": 3.5, "HIGH_ENERGY": 19.5}
    rows = {}
    for regime, energy in cases.items():
        seen = round(energy / x["fixed_quantum"]) * x["fixed_quantum"]
        on = "SEEK" if seen <= x["fixed_threshold"] else "WAIT"
        rows[regime] = {
            "true_energy": energy, "observed_energy": float(seen),
            "SENSOR_ON": on, "SHAM_ON": on, "MASKED_HIGH": "WAIT",
            "ALWAYS_SEEK": "SEEK", "ALWAYS_WAIT": "WAIT",
            "EQUAL_INFORMATION_THRESHOLD": on,
        }
    need(
        rows["LOW_ENERGY"]["SENSOR_ON"] == "SEEK"
        and rows["HIGH_ENERGY"]["SENSOR_ON"] == "WAIT"
        and all(rows[r]["SENSOR_ON"] == rows[r]["EQUAL_INFORMATION_THRESHOLD"]
                for r in REGIMES), "source-shaped policy parity drift",
    )
    return {
        "classification": "V5_B0_L0_SOURCE_SHAPED_INFORMATION_GATE_ONLY",
        "choices": rows,
        "l0_information_dependence": "DESIGNED_POLICY_ONLY",
        "same_information_cheap_equivalent": True,
        "b0_invalidated_by_equivalent_cheap": False,
        "higher_cognition_achieved": False,
        "ecological_benefit": "UNTESTED",
        "world_trials": 0, "science_go": False,
    }


def synthetic_energy(actions: list[str], *, energy: float = 19.5) -> float:
    """Illustrative four-tick cost calculation; EAT is NOT a real receipt."""
    p = load_manifest()["prospective"]
    need(
        type(actions) is list and len(actions) == 4
        and all(type(a) is str and a in ("WAIT", "MOVE", "EAT") for a in actions)
        and actions.count("EAT") <= 1
        and type(energy) in (float, int) and 0 < energy <= p["capacity"],
        "unsupported synthetic witness",
    )
    e = float(energy)
    for act in actions:
        if act == "EAT":
            e = min(p["capacity"], e + p["verified_eat_credit"])
        e -= p["basal"]
        if act == "MOVE":
            e -= p["move_extra"]
        need(e > 0, "example does not model terminal episode")
    return e


def no_presumed_ecological_advantage() -> dict[str, Any]:
    """Same high-energy starting state admits opposite rankings."""
    on = synthetic_energy(["WAIT"] * 4)
    blind_success = synthetic_energy(["MOVE", "MOVE", "EAT", "WAIT"])
    blind_failure = synthetic_energy(["MOVE"] * 4)
    need(blind_success > on > blind_failure, "payoff reversal lost")
    return {
        "classification": "V5_ECOLOGICAL_EFFECT_SIGN_UNDERDETERMINED",
        "on_wait": on, "blind_food_obtained": blind_success,
        "blind_food_not_obtained": blind_failure,
        "source": "UNAUTHENTICATED_ILLUSTRATIVE_ONLY",
        "new_world_trials": 0, "science_go": False,
    }


def main() -> int:
    d = load_manifest()
    print(json.dumps({
        "classification": "V5_B0_L0_ONLY_PROSPECTIVE_NOT_RUN",
        "level": "B0_L0_ONLY",
        "equal_information_cheap_beating_required": False,
        "ecological_outcome": d["admission"]["ecological_effect"],
        "world_trials": 0, "science_go": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
