"""G4.7 exact original G1/T2 tick, P1/M0 immutable receipt, UNKNOWN tests."""
from copy import deepcopy

import pytest

from adapters.mineflayer.g47_original_t2_gait_join_dev import (
    join_g47_original_t2_worldticks_dev,
)


def _paper(seq, tick, *, mode, kind, effect, generation, after):
    controls = dict.fromkeys((
        "forward", "back", "left", "right", "jump", "sneak", "sprint",
    ), False)
    controls["forward"] = True
    controls["sprint"] = mode == "SPRINT_INPUT"
    controls["sneak"] = mode == "WALK"
    return {
        "session_id": "session-g47", "source_seq": seq,
        "world_tick": tick, "kind": kind,
        "t2_activity": "MOVE_OR_UNDETERMINED",
        "applied_controls": controls,
        "paper_gait": {
            "speed_base": 0.1, "speed_value": (
                0.13 if mode == "SPRINT_INPUT" else 0.1
            ),
            "sneaking": mode == "WALK",
            "sprinting": mode == "SPRINT_INPUT",
            "speed_modifiers": 1 if mode == "SPRINT_INPUT" else 0,
        },
        "g46_motor_boundary_dev": {
            "action_id": "goal-g47-step-2",
            "effect_id": effect,
            "requested_mode": mode,
            "control_generation": generation,
            "control_phase": "MOVING",
            "transition_index": {
                "SPRINT_INPUT": 0, "JOG": 1, "WALK": 2,
            }[mode],
        },
        "g46_challenge_after_control_dev": after,
    }


def _args():
    action = "goal-g47-step-2"
    row_spec = [
        (8, 200, "SPRINT_INPUT", "STABLE_SPRINT_FORWARD_CANDIDATE", action, 3, True, "RUN"),
        (12, 201, "JOG", "TRANSITION_OR_UNDETERMINED", action + "-g44-1-jog", 4, False, None),
        (15, 202, "JOG", "STABLE_ORDINARY_FORWARD_CANDIDATE", action + "-g44-1-jog", 4, True, "JOG"),
        (20, 203, "WALK", "TRANSITION_OR_UNDETERMINED", action + "-g44-2-walk", 5, False, None),
        (22, 204, "WALK", "STABLE_SNEAK_FORWARD_CANDIDATE", action + "-g44-2-walk", 5, True, "WALK"),
    ]
    paper = [
        _paper(seq, tick, mode=mode, kind=kind,
               effect=effect, generation=gen, after=after)
        for seq, tick, mode, kind, effect, gen, after, _ in row_spec
    ]
    t2 = []
    for seq, tick, _, _, _, _, _, gait in row_spec:
        t2.append({
            "session_id": "session-g47", "source_seq": seq,
            "world_tick": tick, "active_action": action,
            "motor_mode": gait if gait else "UNDETERMINED",
            "applied_gait": gait,
            "activity": "MOVE_OR_UNDETERMINED",
            "g3_single_p1_owner_dev": True,
            "g3_unknown_fallback_dev": gait is None,
            "g3_extra_m0_paid_dev": 0.0,
            "full_tick_R_attested": False,
            "qualification": False,
            "p1": {"before": {"fatigue": tick}, "after": {"fatigue": tick + 1}},
            "m0": {"before": {"energy": 10.0}, "after": {"energy": 9.9}},
        })
    return {
        "session_id": "session-g47",
        "original_run_acks": [{
            "action_id": action, "effect_id": action, "ack_seq": 6,
            "source": "ORIGINAL_S49_NATIVE_APPLIED",
            "requested_not_paper_gait": True,
        }],
        "transition_acks": [
            {
                "action_id": action,
                "parent_s49_issued_action_id": action,
                "effect": "g44_gait_transition_dev",
                "applied": True, "world_tick_gait_attested": False,
                "mode_to": "JOG", "native_probe_seq": 9,
                "ack_seq": 10, "transition_effect_id": action + "-g44-1-jog",
            },
            {
                "action_id": action,
                "parent_s49_issued_action_id": action,
                "effect": "g44_gait_transition_dev",
                "applied": True, "world_tick_gait_attested": False,
                "mode_to": "WALK", "native_probe_seq": 16,
                "ack_seq": 18, "transition_effect_id": action + "-g44-2-walk",
            },
        ],
        "original_clear_acks": [{
            "action_id": action, "clear_seq": 24,
            "s16_seq": 25, "s16_terminal": "outcome",
        }],
        "paper_rows": paper,
        "t2_rows": t2,
    }


def test_g47_exact_worldtick_join_and_immutability():
    a = _args()
    original = deepcopy(a)
    joined = join_g47_original_t2_worldticks_dev(**a)
    assert a == original
    assert [x.world_tick for x in joined] == list(range(200, 205))
    assert [x.status for x in joined] == [
        "SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV",
        "UNKNOWN_PRECHANGE_CHALLENGE",
        "SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV",
        "UNKNOWN_PRECHANGE_CHALLENGE",
        "SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV",
    ]
    assert [x.original_t2_applied_gait for x in joined] == [
        "RUN", None, "JOG", None, "WALK",
    ]
    assert [x.node_control_generation for x in joined] == [3, 4, 4, 5, 5]
    assert all(len(x.original_t2_row_sha256) == 64
               and not x.qualified
               and not x.packet_to_physics_tick_attested
               and not x.second_t2_owner_created
               and not x.new_p1_or_m0_posting for x in joined)
    assert joined[2].original_p1 == a["t2_rows"][2]["p1"]
    assert joined[2].original_m0 == a["t2_rows"][2]["m0"]
    # Read-only review may not expose nested mutable original T2 state.
    joined[2].original_p1["after"]["fatigue"] = -1
    assert a == original


def test_g47_original_gait_fallback_remains_unknown():
    a = _args()
    a["t2_rows"][2]["applied_gait"] = None
    a["t2_rows"][2]["g3_unknown_fallback_dev"] = True
    assert join_g47_original_t2_worldticks_dev(
        **a,
    )[2].status == "UNKNOWN_ORIGINAL_T2_GAIT_FALLBACK"


def test_g47_unknown_outside_original_s49_gait_effect_window():
    a = _args()
    tick = 205
    a["paper_rows"].append({
        "session_id": a["session_id"], "source_seq": 26,
        "world_tick": tick, "kind": "TRANSITION_OR_UNDETERMINED",
        "t2_activity": "MOVE_OR_UNDETERMINED",
    })
    a["t2_rows"].append({
        **a["t2_rows"][-1],
        "source_seq": 26, "world_tick": tick,
        "active_action": None,
    })
    out = join_g47_original_t2_worldticks_dev(**a)
    assert out[-1].status == "UNKNOWN_NO_ORIGINAL_G46_EFFECT_WINDOW"


@pytest.mark.parametrize("change", [
    "foreign_session", "lost_t2", "reversed_tick", "foreign_p1_owner",
    "modified_worldtick", "g1_activity_mismatch", "positive_gait_extra",
    "qualification_claim", "wrong_p1_receipt",
])
def test_g47_strict_accounting_provenance(change):
    a = _args()
    if change == "foreign_session":
        a["t2_rows"][2]["session_id"] = "foreign"
    elif change == "lost_t2":
        a["t2_rows"].pop(2)
    elif change == "reversed_tick":
        a["t2_rows"][3]["world_tick"] = 201
    elif change == "foreign_p1_owner":
        a["t2_rows"][2]["g3_single_p1_owner_dev"] = False
    elif change == "modified_worldtick":
        a["paper_rows"][2]["world_tick"] = 999
    elif change == "g1_activity_mismatch":
        a["paper_rows"][2]["t2_activity"] = "WAIT_DEV"
    elif change == "positive_gait_extra":
        a["t2_rows"][2]["g3_extra_m0_paid_dev"] = 0.1
    elif change == "qualification_claim":
        a["t2_rows"][2]["full_tick_R_attested"] = True
    else:
        a["t2_rows"][2]["p1"] = None
    with pytest.raises(ValueError, match="G4.[567]"):
        join_g47_original_t2_worldticks_dev(**a)
