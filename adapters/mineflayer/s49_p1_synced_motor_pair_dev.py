"""Two new Paper Worlds, two model F scenarios, one enabled client speed mapping.

The existing original S49 owns both native Action issuances and S16 readbacks.
This independent DEV review joins first-action Node-local attribute visibility
to the already source-replayed Paper motor and original native geometry.
It never measures real same-Self WAIT recovery nor grants L0 motor capacity.
"""
from __future__ import annotations

import json
from pathlib import Path

from adapters.mineflayer.s49_p1_dash_pair_review_dev import (
    review_p1_world_pair_dev,
)
from adapters.mineflayer.s49_paper_forward_dash_dev import (
    PAIR_FATIGUE,
    PAIR_SOURCE_DIGEST,
)
from adapters.mineflayer.s49_speed_attr_boundary_dev import (
    review_speed_attr_boundary_dev,
)


class P1SyncedMotorPairRejected(ValueError):
    """The physical motor pair is not genuinely source-joined with Node."""


def validate_synced_pair_dev(pair: dict, witnesses: dict[str, dict]) -> dict:
    if (
        type(pair) is not dict
        or type(witnesses) is not dict
        or set(witnesses) != set(PAIR_FATIGUE)
        or pair.get("classification")
           != "P1_TWO_FRESH_WORLD_PRELOADED_MODEL_MOTOR_SENSITIVITY_DEV_ONLY"
        or pair.get("prior_p1_model_source_sha256") != PAIR_SOURCE_DIGEST
        or pair.get("model_initial_value_was_preloaded_not_lived") is not True
        or pair.get("same_self_longitudinal_wait_recovery") is not False
        or pair.get("actual_p1_fatigue_observed") is not False
        or pair.get("distance_causally_attributed_to_wait_recovery") is not False
        or pair.get("world_ticks_phase_matched") is not False
        or pair.get("physically_qualified_l0_power_admission") is not None
        or pair.get("new_action_issuers") != 0
        or pair.get("r_qualified_wait_ticks") != 0
        or pair.get("qualification_go") is not False
        or pair.get("science_go") is not False
    ):
        raise P1SyncedMotorPairRejected("model/source safety contract changed")
    joined = {}
    for case, report_key in (
        ("CARRY", "carry_world"),
        ("WAIT_ASSUMED", "wait_assumed_world"),
    ):
        arm = pair.get(report_key)
        native = witnesses.get(case)
        if (
            type(arm) is not dict or type(native) is not dict
            or arm.get("case") != case
            or arm.get("preloaded_hypothetical_fatigue") != PAIR_FATIGUE[case]
            or arm.get("actual_source_frames_verified") is not True
            or arm.get("model_replay_verified") is not True
            or native.get("classification")
               != "S49_NODE_PAPER_ATTRIBUTE_TO_PHYSICS_KEY_DIAGNOSTIC_DEV_ONLY"
            or native.get("session_id") != arm.get("session_id")
            or native.get("action_id") != arm.get("first_action_id")
            or native.get("native_sync_enabled") is not True
            or native.get("node_packet_paper_dash_seen_count", 0) < 1
            or native.get("node_decoded_generic_dash_seen_count", 0) < 1
            or native.get("node_projected_physics_dash_seen_count", 0) < 1
            or native.get("node_active_physics_key_dash_seen_count", 0) < 1
            or native.get("node_physics_ticks_sampled", 0) < 3
            or native.get("no_additional_packet_reader") is not True
            or native.get("paper_native_clock_same_epoch") is not False
            or native.get("physics_speed_attribute_consumed_proven") is not False
            or native.get("physical_fatigue_attested") is not False
            or native.get("actual_p1_state_updated") is not False
            or native.get("native_action_changed") is not False
            or native.get("qualification_go") is not False
            or native.get("science_go") is not False
        ):
            raise P1SyncedMotorPairRejected(
                f"{case} original Node motor witness missing or modified"
            )
        joined[case] = {
            "session_id": arm["session_id"],
            "first_action_id": arm["first_action_id"],
            "paper_world_uuid": arm["paper_world_uuid"],
            "preloaded_p1_model_f": PAIR_FATIGUE[case],
            "paper_first_applied_power": arm["paper_first_applied_power"],
            "paper_mean_applied_power": arm["paper_mean_applied_power"],
            "paper_mean_boost_sampled_speed_mps":
                arm["paper_mean_boost_sampled_speed_mps"],
            "paper_peak_sampled_speed_mps": arm["paper_peak_sampled_speed_mps"],
            "first_s16_displacement_m": arm["first_native_distance_m"],
            "second_unboosted_s16_displacement_m":
                arm["second_unboosted_distance_m"],
            "node_paper_packet_boost_samples":
                native["node_packet_paper_dash_seen_count"],
            "node_client_physics_boost_ticks":
                native["node_active_physics_key_dash_seen_count"],
            "node_local_physics_displacement_m":
                native["node_local_active_displacement_m"],
            "original_action_issuer_retained": True,
        }
    base, rested = joined["CARRY"], joined["WAIT_ASSUMED"]
    if (
        base["session_id"] == rested["session_id"]
        or base["paper_world_uuid"] == rested["paper_world_uuid"]
        or pair.get("paper_applied_power_gain", 0) <= 0.1
    ):
        raise P1SyncedMotorPairRejected("new independent model-F Worlds not separated")
    physical_delta = (
        rested["first_s16_displacement_m"] - base["first_s16_displacement_m"]
    )
    speed_delta = (
        rested["paper_mean_boost_sampled_speed_mps"]
        - base["paper_mean_boost_sampled_speed_mps"]
    )
    if (
        abs(physical_delta - pair["measured_first_native_distance_delta_m"]) > 1e-9
        or abs(speed_delta - pair["measured_paper_boost_speed_delta_mps"]) > 1e-9
        or pair.get("physical_output_difference_observed")
           != (physical_delta > 0.15 and speed_delta > 0.2)
    ):
        raise P1SyncedMotorPairRejected("Paper/S16 joint motor delta was rewritten")
    return {
        "classification": "P1_SYNCED_TWO_MODEL_WORLD_PHYSICAL_DASH_SENSITIVITY_DEV_ONLY",
        "frozen_prior_candidate_source_sha256": PAIR_SOURCE_DIGEST,
        "arms": joined,
        "paper_model_power_gain": pair["paper_applied_power_gain"],
        "actual_first_s16_displacement_gain_m": physical_delta,
        "actual_paper_mean_boost_speed_gain_mps": speed_delta,
        "physical_movement_separation_observed": (
            pair["physical_output_difference_observed"]
        ),
        "physical_motor_gain_if_not_separated": "NOT_ESTABLISHED",
        "both_client_physicsticks_contain_paper_dash_bonus": True,
        "new_independent_worlds": True,
        "model_f_preloaded_not_lived": True,
        "same_self_longitudinal_wait_recovery_observed": False,
        "actual_p1_fatigue_sensor_read": False,
        "paper_node_clocks_synchronized": False,
        "physics_attribute_consumed_in_all_ticks_proven": False,
        "fatigue_recovery_causally_identified": False,
        "l0_physical_dash_power_admission": None,
        "new_native_action_issuers": 0,
        "new_native_packet_readers": 0,
        "extra_p1_or_m0_postings": 0,
        "r_qualified_wait_ticks": 0,
        "qualification_go": False,
        "science_go": False,
    }


def review_p1_synced_world_pair_dev(root: Path) -> dict:
    if not isinstance(root, Path) or root.is_symlink() or not root.is_dir():
        raise P1SyncedMotorPairRejected("untrusted paired DEV source directory")
    pair = review_p1_world_pair_dev(root)
    witnesses = {}
    for case, key in (
        ("CARRY", "carry_world"),
        ("WAIT_ASSUMED", "wait_assumed_world"),
    ):
        arm = pair[key]
        witnesses[case] = review_speed_attr_boundary_dev(
            root / case / "node_speed_attr_boundary_dev.json",
            session_id=arm["session_id"],
            action_id=arm["first_action_id"],
            sync_expected=True,
        )
    result = validate_synced_pair_dev(pair, witnesses)
    (root / "p1_synced_motor_pair_dev.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(review_p1_synced_world_pair_dev(args.root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
