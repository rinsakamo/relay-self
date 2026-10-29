"""G4.9 normal original ACK/CLEAR boundary / original Paper/T2 gap inventory."""
from copy import deepcopy
from dataclasses import asdict

import pytest

from adapters.mineflayer.g48_direct_action_generation_dev import (
    join_g48_direct_action_worldticks_dev,
)
from adapters.mineflayer.g49_original_action_gap_census_dev import (
    join_g49_original_action_gap_census_dev,
)
from test_s49_g48_direct_action_generation_dev import _joined


def _args():
    a = _joined()
    g48 = [asdict(r) for r in join_g48_direct_action_worldticks_dev(**a)]
    direct = a["direct_acks"]
    all_acks = [{
        "action_id": "goal-g47-step-2",
        "effect_id": "goal-g47-step-2",
        "effect": "set_forward_sprint_dev",
        "ack_seq": 6, "requested_mode": "RUN",
        "source": "ORIGINAL_S49_NATIVE_APPLIED",
        "requested_not_paper_gait": True,
    }] + [{
        **{k: v for k, v in row.items() if k != "requested_input_mode"},
        "requested_mode": row["requested_input_mode"],
    } for row in direct]
    return {
        "session_id": a["session_id"],
        "original_action_acks": all_acks,
        "original_clear_acks": a["original_clear_acks"],
        "paper_rows": a["paper_rows"], "t2_rows": a["t2_rows"],
        "g48_rows": g48,
    }


def test_g49_every_original_t2_tick_receipt_preserved_and_gap_censused():
    args = _args()
    unchanged = deepcopy(args)
    out = join_g49_original_action_gap_census_dev(**args)
    assert unchanged == args
    assert len(out) == 10
    assert sum(not row.still_unknown for row in out) == 6
    assert sum(row.still_unknown for row in out) == 4
    assert [x.source_gap_class for x in out] == [
        "EXISTING_SOURCE_BOUND_STABLE_CANDIDATE",
        "UNKNOWN_INSIDE_APPLIED_RUN_ACTION",
        "EXISTING_SOURCE_BOUND_STABLE_CANDIDATE",
        "UNKNOWN_INSIDE_APPLIED_RUN_ACTION",
        "EXISTING_SOURCE_BOUND_STABLE_CANDIDATE",
        "UNKNOWN_INSIDE_APPLIED_JOG_ACTION",
        "EXISTING_SOURCE_BOUND_STABLE_CANDIDATE",
        "EXISTING_SOURCE_BOUND_STABLE_CANDIDATE",
        "UNKNOWN_INSIDE_APPLIED_WALK_ACTION",
        "EXISTING_SOURCE_BOUND_STABLE_CANDIDATE",
    ]
    assert out[-1].original_s49_effect == "set_forward_sneak_dev"
    assert out[0].original_s49_requested_mode == "RUN"
    assert all(len(x.original_t2_row_sha256) == 64
                   and len(x.original_g48_row_sha256) == 64
                   and not x.original_t2_p1_m0_reposted
                   and x.additional_readers_or_t2_owners == 0
                   and not x.physics_tick_motor_attested for x in out)


def test_g49_unknown_without_current_t2_action_is_not_physical_idle_proof():
    a = _args()
    a["t2_rows"][1]["active_action"] = None
    import hashlib
    import json
    a["g48_rows"][1]["original_t2_row_sha256"] = hashlib.sha256(json.dumps(
        a["t2_rows"][1],sort_keys=True,separators=(",",":"),
    ).encode()).hexdigest()
    rows = join_g49_original_action_gap_census_dev(**a)
    assert rows[1].source_gap_class == "UNKNOWN_T2_UNBOUND_INSIDE_NATIVE_ACTION"
    assert rows[1].still_unknown


@pytest.mark.parametrize("modify", [
    "duplicate_ack", "foreign_effect", "missing_ack",
    "wrong_action_mode", "ack_after_clear", "modified_t2_p1",
    "g48_tick_relabel", "duplicate_clear", "forged_stable_after_clear",
])
def test_g49_fail_closed_original_source_negative_controls(modify):
    a = _args()
    if modify == "duplicate_ack":
        a["original_action_acks"].append(dict(a["original_action_acks"][-1]))
    elif modify == "foreign_effect":
        a["original_action_acks"][1]["effect"] = "set_forward_sprint_dev"
    elif modify == "missing_ack":
        a["original_action_acks"].pop()
    elif modify == "wrong_action_mode":
        a["original_action_acks"][1]["requested_mode"] = "DASH"
    elif modify == "ack_after_clear":
        a["original_action_acks"][0]["ack_seq"] = 99
    elif modify == "modified_t2_p1":
        a["t2_rows"][0]["p1"] = {"forged": True}
    elif modify == "g48_tick_relabel":
        a["g48_rows"][0]["world_tick"] += 1
    elif modify == "duplicate_clear":
        a["original_clear_acks"].append(dict(a["original_clear_acks"][-1]))
    elif modify == "forged_stable_after_clear":
        a["original_action_acks"][0]["ack_seq"] = 23
    with pytest.raises(ValueError, match="G4.9"):
        join_g49_original_action_gap_census_dev(**a)


def test_g49_retains_unknown_gait_even_with_original_effect_ack():
    a = _args()
    # The applied Action ACK and Paper mode alone do not justify gait:
    # original G48 pre-change challenge remains unknown.
    out = join_g49_original_action_gap_census_dev(**a)
    assert out[5].original_s49_requested_mode == "JOG"
    assert out[5].original_g48_status == "UNKNOWN_DIRECT_PRECHANGE_CHALLENGE"
    assert out[5].still_unknown
