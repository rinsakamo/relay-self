"""DEV-only same-World S49 MOVE + reused #734 Paper callback source join.

Post-World auditor ONLY. Does not authorize Action, mint a P1-B SourceBoundTick,
credit physical WAIT, supply WorldBody hidden truth to Self or apply FatigueLaw.
The source plugin is an original read-only callback collector, NOT a complete
full-tick S/R input/control or independent physical state attestation.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

from adapters.mineflayer.s49_p1_paper_dev import _float, _int, _rows
from tools.worldbody_fixed_physical_post import _rows as _wb_rows


class P1SameWorldSourceRejected(ValueError):
    """Original S49 / Paper source pair absent, foreign or ambiguous."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise P1SameWorldSourceRejected(message)


def inspect_same_world_source(report: dict[str, Any], paper_log: str) -> dict[str, Any]:
    """Join two genuine S49 closures to the ONE Paper 1.21.8 callback census.

    This is bounded DEV source-correlation, never independent R authentication.
    The returned candidate tick classifications are not FatigueFrame instances.
    """
    _require(isinstance(report, dict) and isinstance(paper_log, str),
             "report and Paper log required")
    sid = report.get("session_id")
    nonce = report.get("worldbody_p1_source_nonce")
    actions = report.get("actual_native_actions")
    _require(
        isinstance(sid, str) and bool(re.fullmatch(r"[0-9a-f-]{36}", sid))
        and isinstance(nonce, str) and nonce == sid.replace("-", "")[:20]
        and report.get("status") == "PASS"
        and report.get("classification")
            == "DEV_ONLY_WORLDBODY_FIXED_PHYSICS_DIRECT_S16_REST"
        and report.get("s49_dev_server") == "PINNED_PAPER_1_21_8"
        and report.get("worldbody_p1_same_world_source_dev") is True
        and report.get("worldbody_p1_source_wait_attested") is False
        and report.get("worldbody_p1_source_join_state")
            == "PENDING_POST_WORLD_ORIGINAL_SOURCE_JOIN"
        and report.get("worldbody_true_fatigue_received_by_self") is False
        and report.get("worldbody_physics_write_from_self") is False
        and report.get("worldbody_postmove_l0_choice", {}).get("selected") == "REST"
        and report.get("worldbody_rest_action_count") == 0
        and isinstance(actions, list) and len(actions) == 2
        and not _rows(paper_log, "SOURCE_FAULT")
        and not _rows(paper_log, "FIGHT")
        and not _rows(paper_log, "REST"),
        "wrong original same-session S49 WorldBody evidence",
    )
    _require(
        all(
            isinstance(a, dict) and a.get("terminal") == "outcome"
            and a.get("source") == sid
            and type(a.get("event_seq")) is int and a["event_seq"] >= 0
            and isinstance(a.get("action"), str) and bool(a["action"])
            and type(a.get("movement_m")) in (int, float)
            and math.isfinite(a["movement_m"]) and a["movement_m"] > 0
            for a in actions
        ) and actions[0]["event_seq"] < actions[1]["event_seq"],
        "not two original ordered closed S16 MOVE outcomes",
    )

    starts = _rows(paper_log, "START")
    stops = _rows(paper_log, "STOP")
    choices = _rows(paper_log, "CHOICE")
    marks = _rows(paper_log, "ACTION")
    ticks = _rows(paper_log, "TICK")
    attach = _wb_rows(paper_log, "ATTACH")
    _require(
        len(starts) == len(stops) == len(choices) == len(attach) == 1
        and len(marks) == 4 and 12 <= len(ticks) <= 2400,
        "missing, duplicate or oversized same-World source",
    )
    start, stop, choice, anchor = starts[0], stops[0], choices[0], attach[0]
    world = start.get("world")
    player = start.get("player")
    _require(
        isinstance(world, str) and bool(re.fullmatch(r"[0-9a-f-]{36}", world))
        and isinstance(player, str) and bool(re.fullmatch(r"[0-9a-f-]{36}", player))
        and anchor.get("world") == world and anchor.get("player") == player
        and start.get("coverage") == "SERVER_TICK_CALLBACK_NOT_FULL_TICK"
        and stop.get("coverage") == "SERVER_TICK_CALLBACK_NOT_FULL_TICK"
        and choice.get("selected") == "REST"
        and all(x.get("nonce") == nonce and x.get("world") == world
                for x in (start, stop, choice, *marks, *ticks))
        and _int(stop, "faults") == 0
        and _int(start, "tick") >= _int(anchor, "tick"),
        "foreign World/session, impossible coverage or modified server truth",
    )

    began, ended = _int(start, "tick"), _int(stop, "tick")
    last = began
    parsed = []
    for i, row in enumerate(ticks, start=1):
        tick = _int(row, "tick")
        counters = {key: _int(row, key) for key in (
            "move_events", "fight_events", "swing_events", "interact_events",
            "velocity_events", "teleport_events", "player_damage_events",
        )}
        distance = _float(row, "move_distance")
        coords = tuple(_float(row, k) for k in ("x", "y", "z"))
        flags = tuple(row.get(k) for k in ("sprint", "sneak", "swimming"))
        _require(
            tick == last + 1 and _int(row, "index") == i
            and all(n <= 10000 for n in counters.values())
            and distance >= 0 and all(k in ("true", "false") for k in flags),
            "gapped/invalid Paper callback tick",
        )
        last = tick
        quiet = not any(counters.values()) and distance == 0 and all(
            k == "false" for k in flags
        )
        parsed.append({
            "tick": tick, "move_events": counters["move_events"],
            "fight_events": counters["fight_events"],
            "move_distance": distance, "quiet": quiet,
            "position": coords,
        })
    _require(last <= ended and _int(stop, "index") == len(parsed)
             and not any(t["fight_events"] for t in parsed),
             "source incomplete or unexpected combat")

    windows = []
    previous_close = began
    for index, original in enumerate(actions):
        first, second = marks[index * 2:index * 2 + 2]
        expected_token = f"s49-native-move-{original['event_seq']}"
        opened, closed = _int(first, "tick"), _int(second, "tick")
        _require(
            first.get("phase") == "begin" and second.get("phase") == "closed"
            and first.get("action") == second.get("action") == expected_token
            and previous_close <= opened <= closed <= ended
            and _int(first, "index") <= _int(second, "index")
            and began <= opened
            and _int(first, "index") <= len(parsed)
            and _int(second, "index") <= len(parsed),
            "source marker is not an original one-action-at-a-time S49 closure",
        )
        # Native effects and Paper callbacks may straddle 1 server tick.
        # That boundary uncertainty is visible; it never becomes a P1-B frame.
        between = [x for x in parsed if opened <= x["tick"] <= closed + 1]
        observed = [x for x in between if x["move_events"] > 0]
        _require(
            observed and all(x["move_distance"] > 0 for x in observed),
            "no corresponding Paper move callback within original action window",
        )
        windows.append({
            "original_s49_action_id": original["action"],
            "original_s49_event_seq": original["event_seq"],
            "original_s16_move_m": original["movement_m"],
            "paper_start_tick": opened, "paper_close_tick": closed,
            "paper_movement_callback_ticks": [x["tick"] for x in observed],
            "paper_callback_path_m": sum(x["move_distance"] for x in observed),
            "paper_window_is_true_action_effect_attestation": False,
        })
        previous_close = closed

    choice_tick = _int(choice, "tick")
    _require(previous_close <= choice_tick <= ended
             and _int(choice, "index") <= len(parsed),
             "REST selection before original closed moves or after source end")
    idle = [x for x in parsed if x["tick"] >= choice_tick + 2]
    _require(
        len(idle) >= 8 and all(x["quiet"] for x in idle[:8])
        and len({x["position"] for x in idle[:8]}) == 1,
        "post-choice quiet Paper candidates absent",
    )

    return {
        "classification": "DEV_S49_TWO_MOVES_SAME_WORLD_PAPER_CALLBACK_JOIN_ONLY",
        "native_session_id": sid,
        "native_action_count": len(actions),
        "native_terminal_sequence": ["outcome", "outcome"],
        "paper_world_uuid": world, "paper_player_uuid": player,
        "paper_tick_start": began, "paper_tick_stop": ended,
        "paper_callback_tick_count": len(parsed),
        "paper_original_action_windows": windows,
        "paper_l0_rest_choice_tick": choice_tick,
        "paper_quiet_after_choice_candidate_ticks": [
            x["tick"] for x in idle[:8]
        ],
        "same_world_native_paper_callback_join": True,
        "source_coverage": "SERVER_TICK_CALLBACK_NOT_FULL_TICK",
        "source_full_tick_wait_independently_attested": False,
        "p1_source_bound_tick_admitted_count": 0,
        "p1_physical_fatigue_recovery_credited": 0,
        "p1_physics_wired_into_world": False,
        "self_received_private_worldbody_fatigue": False,
        "world_rules_mutable_by_self": False,
        "qualification_go": False,
        "science_run": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--paper-log", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = inspect_same_world_source(
        json.loads(args.report.read_text(encoding="utf-8")),
        args.paper_log.read_text(encoding="utf-8"),
    )
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print("DEV_SAME_WORLD_ACTION_PAPER_JOIN_ONLY_NO_TRUE_P1_WAIT")


if __name__ == "__main__":
    main()
