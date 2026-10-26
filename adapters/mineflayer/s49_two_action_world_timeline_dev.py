"""Producer-local, bounded Paper World timeline across TWO original S49 Actions.

This only replays trusted-shape local logs and explicitly chosen DEV rates.
Second Action ACK-to-Paper markers are *delivery* boundaries, NOT native
effect World ticks. No WAIT certification, source attestation or M0 posting.
"""
from __future__ import annotations

import math


class TwoActionWorldTimelineRejected(ValueError):
    pass


def _fields(line: str, marker: str) -> dict:
    return dict(part.split("=", 1) for part in line.split(marker, 1)[1].split()
                if part.count("=") == 1)


def review_two_action_world_timeline_dev(
    raw: str, *, action_id: str, session_id: str,
    bracket: dict, passive: dict, first_native_ack: dict,
    original_actions: list, original_m0_postings: list,
    final_original_energy: float,
    basal_per_world_second: float = 0.5,
    move_per_world_second: float = 0.25,
) -> dict:
    """Continuously sampled Paper tick intervals, no interpolated missing ticks.

    2nd observed window is AFTER Paper receives original S15 APPLIED ACK
    until Paper receives CLEARED ACK, not a certified motor-onset interval.
    """
    if (type(raw) is not str or len(raw) > 10_000_000
            or any(type(v) is not dict for v in
                   (bracket, passive, first_native_ack))
            or type(original_actions) is not list or len(original_actions) != 2
            or type(original_m0_postings) is not list
            or len(original_m0_postings) != 2
            or not isinstance(action_id, str) or not action_id
            or not isinstance(session_id, str) or not session_id
            or any(type(rate) not in (float, int) or not math.isfinite(rate)
                   or rate <= 0 or rate > 4 for rate in
                   (basal_per_world_second, move_per_world_second))
            or type(final_original_energy) not in (float, int)
            or not math.isfinite(final_original_energy)):
        raise TwoActionWorldTimelineRejected("invalid explicit DEV rate/inputs")
    first, second = original_actions
    if (any(x.get("session_id") != session_id
            or x.get("action_id") != action_id for x in
            (bracket, passive, first_native_ack))
            or first.get("action") != action_id
            or second.get("action") == action_id
            or first.get("terminal") != "outcome"
            or second.get("terminal") != "outcome"
            or bracket.get("classification")
               != "PAPER_LOCAL_ARM_TICK_RELEASE_BRACKET_DEV_ONLY"
            or bracket.get("original_owner_release") is not True
            or bracket.get("independent_source_attested") is not False
            or bracket.get("mineflayer_paper_tick_synchronized") is not False
            or passive.get("classification")
               != "PAPER_PASSIVE_POST_RELEASE_TRANSLATION_DEV_ONLY"
            or passive.get("WAIT_sourcebound_admitted") is not False
            or passive.get("M0_posted") is not False
            or first_native_ack.get("classification")
               != "S49_NATIVE_ACK_TO_PAPER_MARKER_DELIVERY_DEV_ONLY"
            or first_native_ack.get("native_single_reader") is not True
            or first_native_ack.get("paper_release_tick")
               != bracket.get("release_tick")
            or first_native_ack.get("independent_source_attested") is not False):
        raise TwoActionWorldTimelineRejected("foreign original Action/World custody")
    try:
        dispatch2 = second["execution_evidence"]["dispatch_receipt"]
        clear2 = second["execution_evidence"]["cleanup_receipt"]
        sid2 = second["execution_evidence"]["session_id"]
    except (KeyError, TypeError) as exc:
        raise TwoActionWorldTimelineRejected("second typed native receipts absent") from exc
    if (sid2 != session_id
            or dispatch2.get("session_id") != session_id
            or clear2.get("session_id") != session_id
            or dispatch2.get("action_id") != second["action"]
            or clear2.get("action_id") != second["action"] + "-s15-clear"
            or dispatch2.get("effect") != "set_forward_sprint_dev"
            or clear2.get("effect") != "clear_controls"
            or dispatch2.get("result") != "applied"
            or clear2.get("result") != "applied"):
        raise TwoActionWorldTimelineRejected("second original native S15 ACK mismatch")
    groups = {"TICK": [], "EDGE": [], "COMPLETE": []}
    for line in raw.splitlines():
        for name in groups:
            marker = "S49_DASH_DEV_TRAIL_" + name + " "
            if marker in line:
                data = _fields(line, marker)
                # Reject a foreign duplicate/overlap carrying the same first
                # action even when its session differs.
                if data.get("action_id") == action_id:
                    groups[name].append(data)
                break
    ticks, edges, completes = (groups["TICK"], groups["EDGE"], groups["COMPLETE"])
    if not 15 <= len(ticks) <= 1200 or len(edges) != 2 or len(completes) != 1:
        raise TwoActionWorldTimelineRejected("missing/bounded tick or edge custody")
    world, player = bracket.get("world_uuid"), bracket.get("player_uuid")
    if not isinstance(world, str) or not isinstance(player, str):
        raise TwoActionWorldTimelineRejected("missing Paper actor identity")
    arm, first_end, release = (
        bracket.get("arm_tick"), bracket.get("last_tick"),
        bracket.get("release_tick"),
    )
    if any(type(x) is not int or x < 0 for x in (arm, first_end, release)):
        raise TwoActionWorldTimelineRejected("missing original Paper tick times")
    if (passive.get("first_sample_tick") != release + 1
            or passive.get("last_sample_tick") != release + 5
            or passive.get("paper_callbacks") != 5
            or release < first_end):
        raise TwoActionWorldTimelineRejected("Paper first-release passive sample gap")
    edge_ticks = []
    ack_sequences = [dispatch2.get("seq"), clear2.get("seq")]
    for i, (row, phase) in enumerate(zip(edges, ("APPLIED", "CLEARED"))):
        try:
            tick, seq = int(row["tick"]), int(row["native_seq"])
        except (ValueError, KeyError) as exc:
            raise TwoActionWorldTimelineRejected("malformed original second ACK marker") from exc
        if (row.get("session_id") != session_id
                or row.get("world") != world
                or row.get("player_uuid") != player
                or row.get("action_id") != second["action"]
                or row.get("phase") != phase
                or row.get("delivered_after_original_native_ack") != "true"
                or row.get("exact_client_effect_tick_attested") != "false"
                or type(ack_sequences[i]) is not int
                or seq != ack_sequences[i]):
            raise TwoActionWorldTimelineRejected("forged/replayed second native ACK")
        edge_ticks.append(tick)
    applied, cleared = edge_ticks
    if (not release + 5 < applied < cleared
            or cleared - applied < 3
            or clear2["seq"] <= dispatch2["seq"]
            or dispatch2["seq"] <= first_native_ack["native_cleanup_ack_seq"]):
        raise TwoActionWorldTimelineRejected("second action ACK/release order absent")
    complete = completes[0]
    try:
        finish, samples = int(complete["tick"]), int(complete["samples"])
    except (KeyError, ValueError) as exc:
        raise TwoActionWorldTimelineRejected("malformed trail terminal") from exc
    if (complete.get("session_id") != session_id
            or complete.get("world") != world
            or complete.get("player_uuid") != player
            or complete.get("second_action_id") != second["action"]
            or complete.get("reason") != "SECOND_NATIVE_ACK_MARKER_PLUS_FIVE"
            or any(complete.get(name) != "false" for name in
                   ("motor_write", "M0_POSTED", "P1_APPLIED", "WAIT_ATTESTED"))
            or finish != cleared + 5
            or samples != finish - arm
            or len(ticks) != samples):
        raise TwoActionWorldTimelineRejected("second Paper timeline not naturally closed")
    coords = []
    for i, row in enumerate(ticks, 1):
        try:
            index, tick = int(row["index"]), int(row["tick"])
            x, z = float(row["x"]), float(row["z"])
        except (KeyError, ValueError) as exc:
            raise TwoActionWorldTimelineRejected("malformed Paper timeline tick") from exc
        if (index != i or tick != arm + i or tick > finish
                or not math.isfinite(x) or not math.isfinite(z)
                or row.get("session_id") != session_id
                or row.get("world") != world
                or row.get("player_uuid") != player
                or row.get("second_applied_marker_seen")
                   != ("true" if tick > applied else "false")
                or row.get("second_cleared_marker_seen")
                   != ("true" if tick > cleared else "false")
                or (tick > release and
                    row.get("first_dash_modifier_present") != "false")
                or any(row.get(name) != "false" for name in
                       ("motor_write", "M0_POSTED", "P1_APPLIED", "WAIT_ATTESTED"))):
            raise TwoActionWorldTimelineRejected("gapped/replayed or foreign Paper World tick")
        if coords and math.hypot(x - coords[-1][0], z - coords[-1][1]) > 2:
            raise TwoActionWorldTimelineRejected("unbounded sampled translation")
        coords.append((x, z))
    if (ticks[0]["tick"] != str(arm + 1)
            or ticks[-1]["tick"] != str(finish)
            or first_end >= applied
            or applied >= finish):
        raise TwoActionWorldTimelineRejected("original/second intervals overlap")
    # Each observed tick has exactly one label. A bridge tick is
    # NOT proof that client motion was inactive; second APPLIED marker
    # always arrived after real effect ACK, not physical onset.
    first_n = first_end - arm
    bridge_n = applied - first_end
    second_n = cleared - applied
    tail_n = finish - cleared
    if (first_n != bracket.get("elapsed_callbacks")
            or first_n + bridge_n + second_n + tail_n != samples
            or bridge_n < 5 or tail_n != 5):
        raise TwoActionWorldTimelineRejected("distinct tick category coverage missing")
    # Motion is only a geometric proxy, never control/authoritative MOVE.
    second_translation_proxy = sum(
        math.hypot(coords[tick - arm - 1][0] - coords[tick - arm - 2][0],
                   coords[tick - arm - 1][1] - coords[tick - arm - 2][1]) > 0.02
        for tick in range(applied + 1, cleared + 1)
    )
    if second_translation_proxy < 3:
        raise TwoActionWorldTimelineRejected("no second Action Paper moving geometry")
    m1, m2 = original_m0_postings
    if (m1.get("action_id") != action_id
            or m2.get("action_id") != second["action"]
            or m1.get("session_id") != session_id
            or m2.get("session_id") != session_id
            or m1.get("m0_tick_after") != 1 or m2.get("m0_tick_after") != 2
            or m1.get("basal_debit") != .5 or m2.get("basal_debit") != .5
            or m1.get("move_debit") != .25 or m2.get("move_debit") != .25
            or not math.isclose(
                m2.get("energy_after", float("nan")),
                final_original_energy, abs_tol=1e-10,
            )):
        raise TwoActionWorldTimelineRejected("original M0 owner modified/unbound")
    per_basal = basal_per_world_second / 20
    per_move = move_per_world_second / 20
    return {
        "classification": "M0_TWO_NATIVE_ACTIONS_CONTIGUOUS_WORLD_TIMELINE_SHADOW_DEV_ONLY",
        "session_id": session_id,
        "action_ids": [action_id, second["action"]],
        "world_uuid": world, "player_uuid": player,
        "first_sample_tick": arm + 1, "last_sample_tick": finish,
        "observed_contiguous_paper_ticks": samples,
        "explicit_world_ticks_per_normalized_second": 20,
        "explicit_basal_rate_per_normalized_world_second": basal_per_world_second,
        "explicit_move_rate_per_normalized_world_second": move_per_world_second,
        "first_action_paper_tick_count": first_n,
        "first_release_to_second_ack_delivery_bridge_ticks": bridge_n,
        "second_ack_delivery_window_ticks": second_n,
        "second_clear_to_tail_ticks": tail_n,
        "second_ack_delivery_applied_tick": applied,
        "second_ack_delivery_cleared_tick": cleared,
        "second_window_translation_proxy_ticks": second_translation_proxy,
        "observed_normalized_world_seconds": samples / 20,
        "basal_shadow_all_observed_ticks_not_posted": per_basal * samples,
        "move_shadow_first_action_window_not_posted": per_move * first_n,
        "move_shadow_second_ack_window_geometric_proxy_not_posted":
            per_move * second_translation_proxy,
        "bridge_motion_classification": "UNKNOWN_NOT_CERTIFIED_WAIT_OR_MOVE",
        "second_window_not_exact_native_effect_timing": True,
        "tick_gaps_or_replay": False, "double_counted_world_ticks": False,
        "original_owner_energy_unchanged": final_original_energy,
        "legacy_action_m0_replaced": False,
        "world_tick_m0_debits_posted": False,
        "P1_recovery_posted": False, "WAIT_sourcebound_admitted": False,
        "independent_source_attested": False,
        "qualification_go": False, "science_go": False,
    }
