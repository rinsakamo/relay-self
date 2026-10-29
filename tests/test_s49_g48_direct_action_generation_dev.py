"""G4.8 exact original direct JOG/WALK Action vs G47 source/tick receipts."""
from copy import deepcopy
from dataclasses import asdict

import pytest

from adapters.mineflayer.g47_original_t2_gait_join_dev import (
    join_g47_original_t2_worldticks_dev,
)
from adapters.mineflayer.g48_direct_action_generation_dev import (
    join_g48_direct_action_worldticks_dev,
)
from test_s49_g47_original_t2_gait_join_dev import _args, _paper


def _joined():
    a = _args()
    old = a["t2_rows"][-1]
    for action_idx, mode, ack, clear, start_tick, start_seq, count in [
        (3, "JOG", 25, 30, 205, 26, 3),
        (4, "WALK", 31, 35, 208, 32, 2),
    ]:
        action = f"goal-g47-step-{action_idx}"
        a["original_clear_acks"].append({
            "action_id": action, "clear_seq": clear,
            "s16_seq": clear + 1, "s16_terminal": "outcome",
        })
        a.setdefault("direct_acks", []).append({
            "action_id": action, "effect_id": action,
            "effect": "set_control" if mode == "JOG" else "set_forward_sneak_dev",
            "ack_seq": ack, "requested_input_mode": mode,
            "source": "ORIGINAL_S49_NATIVE_APPLIED",
            "requested_not_paper_gait": True,
        })
        for i in range(count):
            seq, tick = start_seq + i, start_tick + i
            kind = (
                "STABLE_ORDINARY_FORWARD_CANDIDATE" if mode == "JOG"
                else "STABLE_SNEAK_FORWARD_CANDIDATE"
            )
            row = _paper(seq, tick, mode=mode, kind=kind, effect=action,
                         generation=6 + action_idx, after=i > 0)
            row["g46_motor_boundary_dev"]["transition_index"] = 0
            a["paper_rows"].append(row)
            a["t2_rows"].append({
                **deepcopy(old),
                "source_seq": seq, "world_tick": tick,
                "active_action": action,
                "applied_gait": mode,
                "motor_mode": mode,
                "g3_unknown_fallback_dev": False,
                "p1": {"before": {"fatigue": tick}, "after": {"fatigue": tick + 1}},
            })
    r = [asdict(x) for x in join_g47_original_t2_worldticks_dev(**{
        k: v for k, v in a.items() if k != "direct_acks"
    })]
    return {
        "session_id": a["session_id"],
        "g47_rows": r, "direct_acks": a["direct_acks"],
        "original_clear_acks": a["original_clear_acks"],
        "paper_rows": a["paper_rows"], "t2_rows": a["t2_rows"],
    }


def test_g48_original_direct_jog_walk_and_exact_unknown_source():
    args = _joined()
    original = deepcopy(args)
    out = join_g48_direct_action_worldticks_dev(**args)
    assert args == original
    assert len(out) == len(args["t2_rows"]) == 10
    assert [r.status for r in out[-5:]] == [
        "UNKNOWN_DIRECT_PRECHANGE_CHALLENGE",
        "DIRECT_SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV",
        "DIRECT_SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV",
        "UNKNOWN_DIRECT_PRECHANGE_CHALLENGE",
        "DIRECT_SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV",
    ]
    assert out[-1].direct_requested_mode == "WALK"
    assert out[-1].original_effect_id == "goal-g47-step-4"
    assert out[-1].node_control_generation == 10
    assert out[-4].node_control_generation == 9
    assert all(not r.complete_tick_motor_acceptance_attested
                   and not r.additional_reader_or_t2_owner and not r.p1_or_m0_posted
               for r in out)


@pytest.mark.parametrize("mutate", [
    "foreign_t2_p1", "g47_digest", "wrong_ack", "duplicate_ack",
    "mismatched_paper_tick", "overlap_ack", "fake_qual",
])
def test_g48_refuses_foreign_or_duplicate_original_sources(mutate):
    a = _joined()
    if mutate == "foreign_t2_p1":
        a["t2_rows"][-1]["p1"]["after"]["fatigue"] = 999
    elif mutate == "g47_digest":
        a["g47_rows"][-1]["original_t2_row_sha256"] = "0" * 64
    elif mutate == "wrong_ack":
        a["direct_acks"][-1]["effect"] = "set_control"
    elif mutate == "duplicate_ack":
        a["direct_acks"].append(dict(a["direct_acks"][-1]))
    elif mutate == "mismatched_paper_tick":
        a["paper_rows"][-1]["world_tick"] += 10
    elif mutate == "overlap_ack":
        a["direct_acks"][-1]["ack_seq"] = 26
    else:
        a["g47_rows"][-1]["original_t2_applied_gait"] = "DASH"
    with pytest.raises(ValueError, match="G4.8"):
        join_g48_direct_action_worldticks_dev(**a)


def test_g48_mismatched_generation_or_gait_is_unknown_no_gait_claim():
    a = _joined()
    a["paper_rows"][-1]["g46_motor_boundary_dev"]["effect_id"] = "foreign"
    out = join_g48_direct_action_worldticks_dev(**a)
    assert out[-1].status == "UNKNOWN_DIRECT_NODE_CONTROL_GENERATION"
    assert out[-1].node_control_generation is None
    a = _joined()
    a["paper_rows"][-1]["kind"] = "MOVING_MODE_UNDETERMINED"
    a["g47_rows"][-1]["original_g1_kind"] = "MOVING_MODE_UNDETERMINED"
    out = join_g48_direct_action_worldticks_dev(**a)
    assert out[-1].status == "UNKNOWN_DIRECT_UNSTABLE_PAPER_GAIT"


def test_g48_original_t2_gait_fallback_stays_unknown():
    a = _joined()
    a["t2_rows"][-1]["applied_gait"] = None
    a["t2_rows"][-1]["g3_unknown_fallback_dev"] = True
    a["g47_rows"][-1]["original_t2_applied_gait"] = None
    a["g47_rows"][-1]["original_g3_unknown_fallback"] = True
    import hashlib
    import json
    a["g47_rows"][-1]["original_t2_row_sha256"] = hashlib.sha256(json.dumps(
        a["t2_rows"][-1], sort_keys=True, separators=(",",":"),
    ).encode()).hexdigest()
    out = join_g48_direct_action_worldticks_dev(**a)
    assert out[-1].status == "UNKNOWN_DIRECT_ORIGINAL_T2_FALLBACK"
