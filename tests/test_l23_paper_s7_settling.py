"""L23 Paper-vs-S7 candidate only. Synthetic Paper callbacks, real sealed L22 S7.

No tests here grant physical idle, Goal, P1 WAIT or experience learning.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from adapters.mineflayer.l16_first_action_goal_originals import L16GoalPlan
from adapters.mineflayer.l23_paper_s7_settling import (
    L23SourceRejected,
    inspect_l23_paper_s7,
)

CAPTURE = (
    Path(__file__).resolve().parents[1]
    / "docs/evidence/l22-real-20261031/run1/capture"
)
WORLD = "test-paper-world-uuid"


def original_args():
    terminal = (CAPTURE / "l18_s16_terminal_original.jsonl").read_bytes()
    info = json.loads(terminal)
    return dict(
        received_original=(
            CAPTURE / "native_bridge_received_original.jsonl"
        ).read_bytes(),
        sent_original=(CAPTURE / "native_bridge_sent_original.jsonl").read_bytes(),
        s7_receipt=json.loads((
            CAPTURE / "native_bridge_source_receipt.json"
        ).read_bytes()),
        s16_original=terminal,
        plan=L16GoalPlan(0.0, 0.0, 0.49, 0.05),
        session_id=info["session_id"],
        action_id=info["action_id"],
        expected_world=WORLD,
    )


def paper_fixture(args, *, motion_tick=0):
    """Build fake S-owned callback rows; NEVER claim it is a real Paper file."""
    goal = json.loads(args["received_original"].splitlines()[-1])
    pos = goal["snapshot"]["position"]
    x, y, z = (pos[n] for n in ("x", "y", "z"))
    marker = f"{args['action_id']}-{args['session_id']}"
    fields = dict(
        marker_id=marker, world=WORLD, tick=300,
        x=x, y=y, z=z, packets=4, blocks=1.0,
        tick_meter_blocks=1.0, combat_events=0, swing_events=0,
        basal_ticks=0,
    )
    rows = [
        "[INFO] M02_DEV_S50_PHASE " + " ".join(
            f"{k}={v}" for k, v in dict(
                marker_id=marker, phase=phase, world_full_time=tick,
                world=WORLD, player_tick=tick,
                packets=4, blocks=1.0, billed=0.0,
                x=x, y=y, z=z,
            ).items()
        )
        for phase, tick in (("PRE_FORWARD", 290), ("POST_CLEAR", 300))
    ]
    rows.append("[INFO] S50_DEV_WAIT_BEGIN " + " ".join(
        f"{k}={v}" for k, v in fields.items()
    ))
    for i in range(1, 9):
        start = (x, y, z)
        if i == motion_tick:
            z += 0.125
        data = dict(
            marker_id=marker, world=WORLD, tick=300 + i,
            index=i, from_x=start[0], from_y=start[1], from_z=start[2],
            x=x, y=y, z=z,
            motion_packets=4 + (i >= motion_tick > 0),
            motion_blocks=1.0 + 0.125 * (i >= motion_tick > 0),
            tick_meter_blocks=1.0 + 0.125 * (i >= motion_tick > 0),
            combat_events=0, swing_events=0, basal_ticks=i,
            sprint="false", sneak="false", swimming="false",
        )
        rows.append("[INFO] S50_DEV_WAIT_TICK " + " ".join(
            f"{k}={v}" for k, v in data.items()
        ))
    return ("\n".join(rows) + "\n").encode()


def test_real_l22_s7_plus_synthetic_paper_remains_unqualified():
    args = original_args()
    result = inspect_l23_paper_s7(
        **args, paper_original=paper_fixture(args),
    )
    assert result.paper_sample_count == 8
    assert (result.paper_first_tick, result.paper_last_tick) == (301, 308)
    assert result.paper_activity_ticks == ()
    assert result.paper_s7_geometry_compatible
    assert result.paper_sample_state == "PAPER_8_QUIET_SAMPLES_ONLY"
    assert result.clock_alignment == "NOT_ATTESTED"
    assert result.paper_effective_input_clear_tick == "NOT_ATTESTED"
    assert not result.paper_full_tick_input_idle
    assert not result.physical_stability_verified
    assert result.accepted_goal_status == "UNDETERMINED"
    assert result.qualified_real_learning_pairs == 0
    assert result.p1_wait_ticks_admitted == 0
    assert result.s10_updates == result.s11_grants == 0


def test_motion_with_valid_paper_counter_is_activity_not_idle():
    args = original_args()
    result = inspect_l23_paper_s7(
        **args, paper_original=paper_fixture(args, motion_tick=3),
    )
    assert result.paper_sample_state == "PAPER_SAMPLED_ACTIVITY"
    assert result.paper_activity_ticks == (303,)
    assert not result.paper_s7_geometry_compatible
    assert not result.physical_stability_verified


@pytest.mark.parametrize("fault", [
    "lost_tick", "duplicate_tick", "gapped_tick", "foreign_world",
    "foreign_marker", "negative_counter", "broken_from_pose", "nonfinite",
    "duplicate_field", "truncated_original", "s7_sha",
    "missing_phase", "wrong_phase", "post_clear_after_wait",
])
def test_corrupted_or_foreign_originals_fail_closed(fault):
    args = original_args()
    original = paper_fixture(args)
    if fault == "lost_tick":
        rows = original.splitlines(keepends=True)
        original = b"".join(rows[:-1])
    elif fault == "duplicate_tick":
        rows = original.splitlines(keepends=True)
        original = b"".join([*rows, rows[-1]])
    elif fault == "gapped_tick":
        original = original.replace(b"tick=304 index=4", b"tick=305 index=4")
    elif fault == "foreign_world":
        original = original.replace(b"test-paper-world-uuid", b"other-world", 1)
    elif fault == "foreign_marker":
        original = original.replace(
            f"{args['action_id']}-{args['session_id']}".encode(),
            b"foreign-action",
            1,
        )
    elif fault == "negative_counter":
        original = original.replace(b"motion_packets=4", b"motion_packets=-4", 1)
    elif fault == "broken_from_pose":
        original = original.replace(b"from_x=10.5", b"from_x=11.5", 1)
    elif fault == "nonfinite":
        original = original.replace(b"from_x=10.5", b"from_x=nan", 1)
    elif fault == "duplicate_field":
        original = original.replace(
            b"index=1 ", b"index=1 index=1 ", 1,
        )
    elif fault == "missing_phase":
        original = b"".join(original.splitlines(keepends=True)[1:])
    elif fault == "wrong_phase":
        original = original.replace(b"phase=PRE_FORWARD", b"phase=POST_CLEAR", 1)
    elif fault == "post_clear_after_wait":
        original = original.replace(
            b"phase=POST_CLEAR world_full_time=300",
            b"phase=POST_CLEAR world_full_time=320", 1,
        )
    elif fault == "truncated_original":
        original = b""
    elif fault == "s7_sha":
        args["s7_receipt"]["received_sha256"] = "0" * 64
    with pytest.raises((L23SourceRejected, ValueError, TypeError)):
        inspect_l23_paper_s7(**args, paper_original=original)


def test_paper_tick_zero_is_not_s16_server_tick():
    args = original_args()
    original = paper_fixture(args)
    result = inspect_l23_paper_s7(**args, paper_original=original)
    # The made-up Paper beginning at 300 is independent from L22's S7
    # time_of_day=259; neither number proves a shared physical timestamp.
    assert result.paper_first_tick == 301
    assert result.clock_alignment == "NOT_ATTESTED"
    assert not result.world_session_independently_bound


@pytest.mark.parametrize(("before", "after"), [(1, 2), (2, 3)])
def test_paper_console_log_order_is_required_even_when_ticks_look_valid(
    before, after,
):
    """Source timestamps and row-local counters cannot repair reversed logs."""
    args = original_args()
    rows = paper_fixture(args).splitlines(keepends=True)
    rows[before], rows[after] = rows[after], rows[before]
    with pytest.raises(L23SourceRejected, match="original log order invalid"):
        inspect_l23_paper_s7(**args, paper_original=b"".join(rows))


def test_paper_log_line_cannot_mix_two_source_event_kinds():
    args = original_args()
    original = paper_fixture(args).replace(
        b"S50_DEV_WAIT_BEGIN ",
        b"S50_DEV_WAIT_BEGIN S50_DEV_WAIT_TICK ",
        1,
    )
    with pytest.raises(L23SourceRejected, match="mixed Paper event labels"):
        inspect_l23_paper_s7(**args, paper_original=original)
