"""V8 admission bridge: deterministic OFFLINE candidate roster and R-scoped handoff.

This module NEVER authenticates original World bytes, powers a study, or issues
a SCIENCE grant. It cannot turn R engineering qualifications into V7/V8 trials.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from experiments.validation import v8_m02_ecology_candidate as v8

CLASS = "V8_CANDIDATE_ROSTER_ONLY_SCIENCE_NOT_ADMITTED"
V7_PATH_TOLERANCE_BLOCKS = 0.005
R_SOURCE = (
    "https://github.com/rinsakamo/relay-self/blob/"
    "infra/rsee-r6-s9-native-original-readback-20261012/"
    "docs/rsee-m02-v7-four-arm-physical-qualification-20261017.md"
)

# Four new physical qualifications reported by independent R, 2026-10-17.
# These are provenance POINTERS, not independently authenticated R original bytes.
R_FOUR_ARM_HANDOFF = {
    "SHAM_ON": {
        "source_artifact_id": 12055677136,
        "grant": "USER_M02_V7_SHAM_ON_20261017_ONCE",
        "config_sha256": "939c2da60ed4ce2f5afb5609c1f784886e3b021104c28a83658c17b744159b16",
        "tick_chord_lower_bound_blocks": 1.9389928412050272,
        "basal_requested_first_200": 0.2,
        "walk_setter_input": 0.019389928412050277,
    },
    "BASAL_ZERO": {
        "source_artifact_id": 12056065364,
        "grant": "USER_M02_V7_BASAL_ZERO_20261017_ONCE",
        "config_sha256": "471c93d5625c48946babd10faa30ff7d9b6d118f8a85583f3a604a8dcaffebd7",
        "tick_chord_lower_bound_blocks": 1.7231471919306607,
        "basal_requested_first_200": 0.0,
        "walk_setter_input": 0.01723147191930661,
    },
    "WALK_ZERO": {
        "source_artifact_id": 12055886025,
        "grant": "USER_M02_V7_WALK_ZERO_20261017_ONCE",
        "config_sha256": "74f098cf2e03a98bb7fafaff7e9a3e32b0a02724f3acb4bb198d7e0d666e7749",
        "tick_chord_lower_bound_blocks": 1.9389928412050272,
        "basal_requested_first_200": 0.2,
        "walk_setter_input": 0.0,
    },
    "BOTH_ZERO": {
        "source_artifact_id": 12055002431,
        "grant": "USER_M02_V7_BOTH_ZERO_20261017_ONCE",
        "config_sha256": "b09887414109abf3bdf115257a8f42a35730d7cc6d1520203221c9115d87b73c",
        "tick_chord_lower_bound_blocks": 1.9389928412050272,
        "basal_requested_first_200": 0.0,
        "walk_setter_input": 0.0,
    },
}
R_PLUGIN_SHA256 = "a43afa4d0a1fdaf01c633efd2543ed24b6b53b12ee38ed62a33594057e701e8f"


class NotAdmitted(ValueError):
    """Structural mismatch, not evidence of an authentic physical experiment."""


def draft_roster() -> dict[str, Any]:
    """40 hypothetical slots, deterministic draft order, no World allocation."""
    slots = []
    for seed in v8.SEEDS:
        # Draft order is seed-blocked and deterministic; it is NOT an
        # approved or blinded randomized assignment for a powered study.
        order = sorted(
            v8.ARMS,
            key=lambda arm: hashlib.sha256(
                f"V8_CANDIDATE_ONLY:{seed}:{arm}".encode("ascii")
            ).hexdigest(),
        )
        for position, arm in enumerate(order):
            slots.append({
                "slot_id": f"V8-CAND-{seed}-{arm}",
                "seed": seed,
                "arm": arm,
                "draft_order": position,
                "state": "NOT_RUN",
                "source_world_uuid": None,
                "initial_terrain_snapshot_digest": None,
                "native_start_pose_and_tick": None,
                "host_and_stop_originals": None,
                "science_grant": None,
                "science_evidence": None,
            })
    return {
        "schema": "RELAYSELF_V8_CANDIDATE_ROSTER_V1",
        "authority": "V_619_DRAFT_625",
        "basis": "V8_DESIGN_ONLY_UNAPPROVED_NOT_POWERED",
        "v6_science_executed": 0,
        "v7_science_executed": 0,
        "v8_science_executed": 0,
        "r_scoped_engineering_profiles": list(v8.ARMS),
        "r_not_v_science": True,
        "all_slots": slots,
        "science_admission": False,
        "grant_issued": False,
    }


def review_roster(roster: Any) -> dict[str, Any]:
    """No caller-provided flags or SHA-shaped claims can elevate this draft."""
    if type(roster) is not dict or roster != draft_roster():
        raise NotAdmitted("V8 draft altered, executed, missing, or promoted")
    v8.review_plan(v8.candidate())
    slots = roster["all_slots"]
    if len(slots) != 40 or len({s["slot_id"] for s in slots}) != 40:
        raise NotAdmitted("missing or duplicate hypothetical slot")
    for seed in v8.SEEDS:
        subset = [s for s in slots if s["seed"] == seed]
        if {s["arm"] for s in subset} != set(v8.ARMS):
            raise NotAdmitted("incomplete seed block")
        if {s["draft_order"] for s in subset} != set(range(5)):
            raise NotAdmitted("invalid candidate order")
    return {
        "classification": CLASS,
        "proposed_slots": len(slots),
        "executed_trials": 0,
        "randomization_status": "DRAFT_ORDER_NOT_APPROVED",
        "science_go": False,
        "production_go": False,
    }


def review_r_handoff(handoff: Any) -> dict[str, Any]:
    """Record R's claimed engineering scope without pretending to re-audit it."""
    if type(handoff) is not dict or handoff != R_FOUR_ARM_HANDOFF:
        raise NotAdmitted("R handoff evidence claims not equal to fixed report")
    x = list(handoff.values())
    if len({a["source_artifact_id"] for a in x}) != 4:
        raise NotAdmitted("aliased physical archives")
    if len({a["grant"] for a in x}) != 4:
        raise NotAdmitted("reused one-shot qualification grant")
    spread = max(a["tick_chord_lower_bound_blocks"] for a in x) - min(
        a["tick_chord_lower_bound_blocks"] for a in x
    )
    if spread <= V7_PATH_TOLERANCE_BLOCKS:
        raise NotAdmitted("R handoff contradicts frozen V7 path failure")
    return {
        "classification": "R_FOUR_ARM_SOURCE_REPORT_RECORDED_NOT_REAUDITED",
        "qualified_by_r_engineering_only": 4,
        "previous_base_on_qualified_separately": True,
        "mechanism_engineering_profiles_total": 5,
        "r_original_source": R_SOURCE,
        "source_jar_sha256": R_PLUGIN_SHA256,
        "four_arm_tick_chord_spread_blocks": spread,
        "continuous_subtick_path_attested": False,
        "net_hunger_effect_attested": False,
        "v7_frozen_matched_path_gate": "FAIL",
        "v7_science_executed": 0,
        "v8_science_go": False,
    }


def main() -> None:
    print(json.dumps({
        "roster": review_roster(draft_roster()),
        "r_handoff": review_r_handoff(copy.deepcopy(R_FOUR_ARM_HANDOFF)),
        "next_gates": [
            "S_DEV_IMMUTABLE_CHUNK_CLONE_NATIVE_POSE_AND_START_TICK",
            "S_DEV_FINITE_FOOD_DIFFICULTY_AND_TRUE_L0_OUTCOME",
            "R_INDEPENDENT_FRESH_V8_SOURCE_AND_WORLD_QUALIFICATION",
            "V_FEASIBILITY_POWER_ENDPOINT_CENSOR_AND_STOP_RULE_FREEZE",
            "V_SEPARATE_SCIENCE_APPROVAL_AND_NEW_UNCONSUMED_GRANTS",
        ],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
