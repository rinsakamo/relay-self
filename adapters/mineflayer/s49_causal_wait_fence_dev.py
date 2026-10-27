"""Read-only causal Paper World-tick fence from the SOLE original S49 issuer.

Paper START delivery occurs after first original S16 terminal and native
clear; Paper END delivery is awaited BEFORE original second Action ISSUE.
This brackets a conservative Paper interval without equating clocks.
Not qualification for physical WAIT/P1 or M0 posting.
"""
from __future__ import annotations

from adapters.mineflayer.s49_two_action_world_timeline_dev import _fields


class OriginalOwnerFenceRejected(ValueError):
    pass


def review_original_owner_causal_paper_fence_dev(
    raw: str, *, owner: dict, original_owner: dict,
    stillness: dict, timeline: dict,
    first_action_id: str, second_action_id: str, session_id: str,
) -> dict:
    if (
        type(raw) is not str or len(raw) > 10_000_000
        or any(type(x) is not dict for x in (
            owner, original_owner, stillness, timeline
        ))
        or owner.get("classification") != (
            "S49_ORIGINAL_OWNER_NO_ACTION_ISSUE_PLUS_NODE_PAPER_STATIC_CANDIDATE_DEV_ONLY"
        )
        or owner.get("action_ids") != [first_action_id, second_action_id]
        or owner.get("session_id") != session_id
        or owner.get("original_owner_no_new_issue_between_bookends") is not True
        or owner.get("open_actions_at_bookends") != [0, 0, 0]
        or owner.get("first_terminal_count") != 1
        or owner.get("at_next_action_request_count") != 1
        or owner.get("after_second_terminal_count") != 2
        or owner.get("physical_WAIT_admitted") is not False
        or owner.get("node_all_inputs_off_at_local_callbacks") is not True
        or owner.get("bounded_source_local_duration_consistency") is not True
        or owner.get("host_paper_world_tick_clocks_calibrated") is not False
        or original_owner.get("session_id") != session_id
        or original_owner.get("first_terminal_action_id") != first_action_id
        or original_owner.get("second_requested_action_id") != second_action_id
        or original_owner.get("causal_paper_start_received_after_first_outcome")
           is not True
        or original_owner.get("causal_paper_end_received_before_original_second_issue")
           is not True
        or original_owner.get("native_action_count_at_first_terminal") != 1
        or original_owner.get("native_action_count_at_next_request") != 1
        or stillness.get("classification") != (
            "S49_INTER_ACTION_STILLNESS_CANDIDATE_DEV_ONLY"
        )
        or stillness.get("action_ids") != [first_action_id, second_action_id]
        or stillness.get("session_id") != session_id
        or stillness.get("node_all_controls_off_until_second_set") is not True
        or stillness.get("physical_WAIT_admitted") is not False
        or timeline.get("classification") != (
            "M0_TWO_NATIVE_ACTIONS_CONTIGUOUS_WORLD_TIMELINE_SHADOW_DEV_ONLY"
        )
        or timeline.get("action_ids") != [first_action_id, second_action_id]
        or timeline.get("session_id") != session_id
        or timeline.get("tick_gaps_or_replay") is not False
        or timeline.get("world_tick_m0_debits_posted") is not False
    ):
        raise OriginalOwnerFenceRejected("unqualified or foreign S49 producer boundaries")
    matching = []
    marker = "S49_DASH_DEV_OWNER_FENCE "
    for line in raw.splitlines():
        if marker in line:
            row = _fields(line, marker)
            if row.get("action_id") == first_action_id:
                matching.append(row)
    if len(matching) != 2:
        raise OriginalOwnerFenceRejected("missing, duplicated or replayed Paper fence")
    w, p = timeline.get("world_uuid"), timeline.get("player_uuid")
    ticks = []
    for row, phase, other in zip(
        matching, ("START", "END"), ("NONE", second_action_id)
    ):
        try:
            tick = int(row["tick"])
        except (KeyError, ValueError) as exc:
            raise OriginalOwnerFenceRejected("invalid Paper fence tick") from exc
        if (
            row.get("session_id") != session_id
            or row.get("world") != w or row.get("player_uuid") != p
            or row.get("phase") != phase
            or row.get("second_action_id") != other
            or row.get("original_owner_paper_delivery_only") != "true"
            or row.get("native_effect_tick_attested") != "false"
            or any(row.get(field) != "false" for field in (
                "motor_write", "M0_POSTED", "P1_APPLIED", "WAIT_ATTESTED"
            ))
        ):
            raise OriginalOwnerFenceRejected("foreign or privileged Paper fence")
        ticks.append(tick)
    start, end = ticks
    paper_first = timeline["first_sample_tick"]
    paper_last = timeline["last_sample_tick"]
    first_end = paper_first - 1 + timeline["first_action_paper_tick_count"]
    second_delivered = timeline["second_ack_delivery_applied_tick"]
    if (
        not all(type(n) is int for n in (paper_first, paper_last, first_end,
                                         second_delivered))
        or not paper_first < first_end < start < end < second_delivered < paper_last
        or end - start < 10
        or timeline["observed_contiguous_paper_ticks"] != paper_last - paper_first + 1
    ):
        raise OriginalOwnerFenceRejected("Paper fence chronology/gap not proven")
    c0, c1 = (
        stillness.get("paper_first_candidate_tick"),
        stillness.get("paper_last_candidate_tick"),
    )
    if not all(type(n) is int for n in (c0, c1)) or c0 > c1:
        raise OriginalOwnerFenceRejected("missing measured body-stillness run")
    # Discard both fence delivery ticks and their adjacent callbacks:
    # Paper scheduler order in the same fullTime tick is ambiguous.
    low, high = max(c0, start + 2), min(c1, end - 2)
    if high - low + 1 < 8:
        raise OriginalOwnerFenceRejected("no eight static Paper ticks inside owner fence")
    if (
        owner.get("P1_recovery_posted") is not False
        or owner.get("M0_posted") is not False
        or stillness.get("P1_recovery_posted") is not False
        or stillness.get("M0_posted") is not False
        or owner.get("physical_overlap_time_attested") is not False
    ):
        raise OriginalOwnerFenceRejected("false WAIT or source clock authority")
    return {
        "classification": "S49_CAUSAL_OWNER_PAPER_STATIC_SUBWINDOW_DEV_ONLY",
        "session_id": session_id,
        "action_ids": [first_action_id, second_action_id],
        "world_uuid": w, "player_uuid": p,
        "paper_first_owner_fence_delivery_tick": start,
        "paper_second_owner_fence_delivery_tick": end,
        "paper_stillness_candidate_interval": [c0, c1],
        "paper_causal_subwindow_first_tick": low,
        "paper_causal_subwindow_last_tick": high,
        "paper_causal_subwindow_contiguous_still_ticks": high - low + 1,
        "boundary_guard_ticks_each_side": 2,
        "owner_original_first_s16_terminal_before_start_delivery": True,
        "owner_original_second_s15_issue_after_end_delivery": True,
        "node_original_first_clear_before_start_delivery": True,
        "node_original_second_set_after_end_delivery": True,
        "original_issuer_no_second_issue_during_causal_subwindow": True,
        "node_local_controls_off_sampled_between_first_clear_second_set": True,
        "paper_body_static_measured_inside_causal_subwindow": True,
        "same_process_native_paper_clock_epoch_calibrated": False,
        "node_physics_paper_tick_1_to_1_attested": False,
        "global_world_quiescence_attested": False,
        "global_action_absence_attested": False,
        "physical_WAIT_admitted": False,
        "P1_recovery_posted": False,
        "M0_posted": False,
        "qualification_go": False,
        "science_go": False,
    }
