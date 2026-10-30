"""G4.12 original native ACK vs observed Paper generation boundary census."""
from copy import deepcopy
from dataclasses import asdict

import pytest

from adapters.mineflayer.g410_in_action_evidence_quality_dev import (
    join_g410_in_action_evidence_dev,
)
from adapters.mineflayer.g411_g1_unstable_pair_census_dev import (
    join_g411_g1_unstable_pair_census_dev,
)
from adapters.mineflayer.g412_original_control_boundary_dwell_dev import (
    join_g412_original_control_boundary_dwell_dev,
)
from test_s49_g49_original_action_gap_census_dev import _args as g49_args


def _args():
    raw = g49_args()
    g49_rows = [asdict(row) for row in
                __import__(
                    "adapters.mineflayer.g49_original_action_gap_census_dev",
                    fromlist=["join_g49_original_action_gap_census_dev"],
                ).join_g49_original_action_gap_census_dev(**raw)]
    base = {
        "session_id": raw["session_id"],
        "g49_rows": g49_rows,
        "g48_rows": raw["g48_rows"],
        "paper_rows": raw["paper_rows"],
        "t2_rows": raw["t2_rows"],
    }
    g410_rows = [asdict(row) for row in
                 join_g410_in_action_evidence_dev(**base)]
    g411_rows = [asdict(row) for row in
                 join_g411_g1_unstable_pair_census_dev(
                     **base, g410_rows=g410_rows,
                 )]
    original = "goal-g47-step-2"
    transitions = [
        {
            "action_id": original,
            "parent_s49_issued_action_id": original,
            "native_probe_seq": 9, "ack_seq": 10,
            "transition_effect_id": original + "-g44-1-jog",
            "mode_to": "JOG", "effect": "g44_gait_transition_dev",
            "applied": True, "world_tick_gait_attested": False,
        },
        {
            "action_id": original,
            "parent_s49_issued_action_id": original,
            "native_probe_seq": 16, "ack_seq": 18,
            "transition_effect_id": original + "-g44-2-walk",
            "mode_to": "WALK", "effect": "g44_gait_transition_dev",
            "applied": True, "world_tick_gait_attested": False,
        },
    ]
    return {
        **base, "g410_rows": g410_rows, "g411_rows": g411_rows,
        "original_action_acks": raw["original_action_acks"],
        "original_clear_acks": raw["original_clear_acks"],
        "original_transition_acks": transitions,
    }


def test_g412_native_subeffect_acks_and_contiguous_original_paper_dwell():
    args = _args()
    before = deepcopy(args)
    out = join_g412_original_control_boundary_dwell_dev(**args)
    assert args == before
    assert [r.source_seq for r in out] == [12, 20]
    assert [r.original_effect_evidence_class for r in out] == [
        "G44_SAME_S49_ACTION_SUBEFFECT_OBSERVED",
        "G44_SAME_S49_ACTION_SUBEFFECT_OBSERVED",
    ]
    assert [r.matched_g44_ack_seq for r in out] == [10, 18]
    assert [r.observed_generation_worldtick_count for r in out] == [2, 2]
    assert [r.observed_following_same_generation_ticks for r in out] == [1, 1]
    assert [r.observed_same_generation_stable_g1_frames for r in out] == [1, 1]
    assert all(r.selected_frame_age_within_generation_ticks == 1
               and r.original_clear_is_after_selected_frame
               and not r.real_motor_switch_tick_attested
               and not r.packet_to_physics_tick_attested
               and not r.physical_input_cadence_causality_proven
               and not r.inferred_wait_or_recovery
               and not r.additional_motor_or_reader_created
               and r.original_t2_p1_m0_untouched
               and r.original_unknown_preserved
               and len(r.original_g411_row_sha256) == 64
               for r in out)


def test_g412_missing_g44_ack_must_not_be_invented():
    a = _args()
    a["original_transition_acks"] = []
    out = join_g412_original_control_boundary_dwell_dev(**a)
    assert all(r.original_effect_evidence_class
               == "UNKNOWN_UNCORRELATED_NODE_BOUNDARY" for r in out)
    assert all(r.matched_g44_ack_seq is None for r in out)


@pytest.mark.parametrize("mutation", [
    "g411_rewrite", "alter_p1", "alter_original_ack",
    "duplicate_transition", "wrong_transition_action", "wrong_transition_mode",
    "transition_ack_after_frame", "duplicate_paper", "foreign_transition",
    "wrong_s15_clear", "g44_fake_physics", "foreign_g49_receipt",
])
def test_g412_fail_closed_original_source_and_transition_receipt(mutation):
    a = _args()
    if mutation == "g411_rewrite":
        a["g411_rows"][0]["evidence_class"] = "FORGED"
    elif mutation == "alter_p1":
        a["t2_rows"][0]["p1"] = {"forged": True}
    elif mutation == "alter_original_ack":
        a["original_action_acks"][0]["ack_seq"] = 99
    elif mutation == "duplicate_transition":
        a["original_transition_acks"].append(dict(a["original_transition_acks"][0]))
    elif mutation == "wrong_transition_action":
        a["original_transition_acks"][0]["action_id"] = "goal-foreign"
    elif mutation == "wrong_transition_mode":
        a["original_transition_acks"][0]["mode_to"] = "RUN"
    elif mutation == "transition_ack_after_frame":
        a["original_transition_acks"][0]["ack_seq"] = 15
    elif mutation == "duplicate_paper":
        a["paper_rows"].append(dict(a["paper_rows"][-1]))
    elif mutation == "foreign_transition":
        a["original_transition_acks"][0]["transition_effect_id"] = "other"
    elif mutation == "wrong_s15_clear":
        a["original_clear_acks"][0]["clear_seq"] = 4
    elif mutation == "g44_fake_physics":
        a["original_transition_acks"][0]["world_tick_gait_attested"] = True
    else:
        a["g49_rows"][0]["original_t2_row_sha256"] = "0" * 64
    with pytest.raises(ValueError, match=r"G4\.(9|10|11|12)"):
        join_g412_original_control_boundary_dwell_dev(**a)


def test_g412_remains_unknown_if_no_matching_effect_even_when_node_changed():
    a = _args()
    # No native accepted G44 sub-effect, so Paper alone cannot be promoted.
    a["original_transition_acks"] = []
    rows = join_g412_original_control_boundary_dwell_dev(**a)
    assert all(r.original_unknown_preserved for r in rows)
    assert all(r.observed_generation_worldtick_count >= 1 for r in rows)
