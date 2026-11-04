"""S49 original owner -> bounded Paper callback-tick source (DEV ONLY).

The native Paper plugin never writes P1 state or grants actions. This module
records the Paper's successive callback snapshots and one tagged combat event;
they are candidate physical body ticks, NOT independently certified complete
full World-tick activity or formal R evidence.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.s31a_real_server_ci import _command
from adapters.mineflayer.s49_attack_then_rest_dev import run_s49_attack_then_rest_dev


class S49P1SourceRejected(ValueError):
    """Native Paper callback source absent, foreign, ambiguous or incomplete."""


def _rows(log: str, key: str) -> list[dict[str, str]]:
    marker = "S49P1_" + key + " "
    matches = []
    for line in log.splitlines():
        if marker not in line:
            continue
        bits = line.split(marker, 1)[1].split()
        if not bits or any(bit.count("=") != 1 for bit in bits):
            raise S49P1SourceRejected("malformed " + key + " row")
        pairs = [bit.split("=", 1) for bit in bits]
        fields = dict(pairs)
        if len(fields) != len(pairs):
            raise S49P1SourceRejected("duplicate " + key + " source fields")
        matches.append(fields)
    return matches


def _int(row: dict[str, str], key: str) -> int:
    try:
        raw = row[key]
        if not re.fullmatch(r"0|[1-9][0-9]*", raw):
            raise ValueError("bad integer")
        value = int(raw)
        if value > 1_000_000_000_000:
            raise ValueError("overflow")
        return value
    except (KeyError, ValueError) as exc:
        raise S49P1SourceRejected("invalid " + key) from exc


def _float(row: dict[str, str], key: str) -> float:
    import math

    try:
        value = float(row[key])
        if not math.isfinite(value):
            raise ValueError("nonfinite")
        return value
    except (KeyError, ValueError) as exc:
        raise S49P1SourceRejected("invalid " + key) from exc


def inspect_paper_tick_source(
    log: str, *, nonce: str, native_report: dict[str, Any],
) -> dict[str, Any]:
    """Pure source-shape check, no independent source authenticity promotion."""
    if not re.fullmatch(r"[a-z0-9]{12,32}", nonce):
        raise S49P1SourceRejected("invalid nonce")
    if (
        native_report.get("status") != "PENDING_NATIVE_JOIN"
        and native_report.get("status") != "PASS"
    ):
        raise S49P1SourceRejected("original S49 join not complete")
    actions = native_report.get("actual_native_actions")
    if (
        not isinstance(actions, list) or len(actions) != 1
        or actions[0].get("kind") != "ATTACK"
        or actions[0].get("terminal") != "outcome"
        or native_report.get("rest_intent_selected") is not True
        or native_report.get("rest_action_issued") is not False
        or native_report.get("attack_server_health_drop_observed") is not True
    ):
        raise S49P1SourceRejected("not original one ATTACK then REST")
    if _rows(log, "SOURCE_FAULT"):
        raise S49P1SourceRejected("server source overflow or missing World/player")
    starts, rests, stops, fights, ticks = (
        _rows(log, key)
        for key in ("START", "REST", "STOP", "FIGHT", "TICK")
    )
    if (
        any(len(v) != 1 for v in (starts, rests, stops, fights))
        or not 20 <= len(ticks) <= 480
    ):
        raise S49P1SourceRejected("incomplete or duplicate source brackets")
    start, rest, stop, fight = starts[0], rests[0], stops[0], fights[0]
    world = start.get("world")
    player_uuid = start.get("player")
    if (
        not world or not re.fullmatch(r"[0-9a-f-]{36}", world)
        or not player_uuid or not re.fullmatch(r"[0-9a-f-]{36}", player_uuid)
        or not re.fullmatch(r"[0-9a-f-]{36}", fight.get("attacker", ""))
        or not re.fullmatch(r"[0-9a-f-]{36}", fight.get("target", ""))
        or fight["attacker"] != player_uuid
        or _float(fight, "damage") <= 0
        or any(r.get("nonce") != nonce or r.get("world") != world
               for r in (start, rest, stop, fight, *ticks))
        or stop.get("coverage") != "SERVER_TICK_CALLBACK_NOT_FULL_TICK"
        or start.get("coverage") != "SERVER_TICK_CALLBACK_NOT_FULL_TICK"
        or _int(stop, "faults") != 0
    ):
        raise S49P1SourceRejected("foreign or unbounded Paper source")
    began = _int(start, "tick")
    ended = _int(stop, "tick")
    rest_tick = _int(rest, "tick")
    fight_tick = _int(fight, "tick")
    if not began <= fight_tick < rest_tick <= ended:
        raise S49P1SourceRejected("FIGHT/REST source order missing")
    if _int(stop, "index") != len(ticks):
        raise S49P1SourceRejected("incomplete tick publisher")
    rows = []
    last = began
    for index, row in enumerate(ticks, 1):
        tick = _int(row, "tick")
        if tick != last + 1 or _int(row, "index") != index:
            raise S49P1SourceRejected("gapped or reordered native World tick")
        last = tick
        counts = {key: _int(row, key) for key in (
            "move_events", "fight_events", "swing_events",
            "interact_events", "velocity_events", "teleport_events",
            "player_damage_events",
        )}
        distance = _float(row, "move_distance")
        coords = tuple(_float(row, axis) for axis in ("x", "y", "z"))
        if (
            any(v > 10000 for v in counts.values())
            or not 0 <= distance <= 10000
            or any(row.get(k) not in ("true", "false")
                   for k in ("sprint", "sneak", "swimming"))
        ):
            raise S49P1SourceRejected("invalid callback body flags/counters")
        rows.append({"world_tick": tick, "index": index,
                     "coordinates": coords, "event_counters": counts,
                     "observed_move_blocks": distance,
                     "sprint": row["sprint"] == "true",
                     "sneak": row["sneak"] == "true",
                     "swimming": row["swimming"] == "true"})
    if not ended >= last:
        raise S49P1SourceRejected("STOP predates tick row")
    combat_callbacks = [x for x in rows if x["event_counters"]["fight_events"]]
    if (
        len(combat_callbacks) != 1
        or combat_callbacks[0]["event_counters"]["fight_events"] != 1
        or not fight_tick <= combat_callbacks[0]["world_tick"] <= fight_tick + 1
    ):
        raise S49P1SourceRejected("not one Paper fight source tick")
    post_rest = [x for x in rows if x["world_tick"] >= rest_tick + 2]
    if len(post_rest) < 8:
        raise S49P1SourceRejected("no bounded post-REST tick coverage")
    # Keep both all-frame originals and a separately scoped post-REST interval.
    def quiet(x: dict[str, Any]) -> bool:
        return (not any(x["event_counters"].values())
                and x["observed_move_blocks"] == 0
                and not x["sprint"] and not x["sneak"] and not x["swimming"])
    if not all(quiet(x) for x in post_rest[:8]):
        raise S49P1SourceRejected("post-REST native callback movement/activity")
    if len({x["coordinates"] for x in post_rest[:8]}) != 1:
        raise S49P1SourceRejected("position changed in post-REST tick sample")
    return {
        "classification": "S49_P1_PAPER_CALLBACK_TICK_SOURCE_DEV_ONLY",
        "nonce": nonce, "paper_world": world, "paper_player_uuid": player_uuid,
        "native_session_id": native_report["session_id"],
        "native_attack_action_id": actions[0]["action_id"],
        "paper_fight_event_tick": fight_tick,
        "paper_fight_callback_tick": combat_callbacks[0]["world_tick"],
        "paper_rest_marker_tick": rest_tick,
        "world_tick_start": began, "world_tick_last_callback": last,
        "world_tick_stop": ended,
        "total_consecutive_source_callback_rows": len(rows),
        "rest_candidate_quiet_source_ticks": [
            x["world_tick"] for x in post_rest[:8]
        ],
        "paper_fight_final_damage": _float(fight, "damage"),
        "source_tick_rows": rows,
        "source_complete_callback_series": True,
        "source_full_tick_activity_independently_attested": False,
        "r_source_original_independently_attested": False,
        "p1_fatigue_physically_attested": False,
        "m_basal_cost_waived": False,
        "qualification_go": False,
    }


async def _send_and_wait(
    server: object, log_path: Path, *, command: str, key: str, nonce: str,
) -> None:
    if getattr(server, "stdin", None) is None or not log_path.is_file():
        raise S49P1SourceRejected("no original server collector")
    _command(server, command)
    await server.stdin.drain()
    for _ in range(90):
        log = log_path.read_text(encoding="utf-8")
        matches = [r for r in _rows(log, key) if r.get("nonce") == nonce]
        if len(matches) == 1:
            return
        if len(matches) > 1 or _rows(log, "SOURCE_FAULT"):
            raise S49P1SourceRejected("duplicate/failed Paper source marker")
        await asyncio.sleep(0.1)
    raise S49P1SourceRejected("missing " + key + " server marker")


async def run_s49_p1_paper_dev(
    session: MineflayerProcessSession, server: object,
    owner: NormalSessionActionExecutor,
    report: dict[str, Any], log_path: Path,
) -> None:
    """One S49 original ATTACK->REST, with server-only source hooks."""
    if not isinstance(session, MineflayerProcessSession):
        raise S49P1SourceRejected("original process required")
    nonce = session.started.session_id.replace("-", "")[:20]
    report["p1_paper_source_scope"] = "DEV_CALLBACK_BOUNDED_NO_R_ATTESTATION"
    source_started = False
    report["stage"] = "S49_P1_PAPER_SOURCE_WAIT_FOR_NATIVE_ADMISSION"
    async def mark_attack_source() -> None:
        nonlocal source_started
        await _send_and_wait(
            server, log_path, command=f"s49p1start {nonce}",
            key="START", nonce=nonce,
        )
        source_started = True

    try:
        async def mark_rest() -> None:
            await _send_and_wait(
                server, log_path, command=f"s49p1rest {nonce}",
                key="REST", nonce=nonce,
            )

        await run_s49_attack_then_rest_dev(
            session, server, owner, report,
            health_log=log_path, rest_intent_hook=mark_rest,
            attack_pre_issue_hook=mark_attack_source,
        )
    finally:
        # Never mask a pre-issue refusal or reissue an ATTACK.
        if source_started:
            await _send_and_wait(
                server, log_path, command=f"s49p1stop {nonce}",
                key="STOP", nonce=nonce,
            )
    report["status"] = "PENDING_NATIVE_JOIN"
    checked = inspect_paper_tick_source(
        log_path.read_text(encoding="utf-8"),
        nonce=nonce, native_report=report,
    )
    # Full raw row sequence remains in original server log; expose bounded summary.
    report["p1_paper_tick_source"] = {
        k: v for k, v in checked.items() if k != "source_tick_rows"
    }
    report["p1_paper_tick_series_evidence"] = {
        "source_log": log_path.name,
        "original_row_count": len(checked["source_tick_rows"]),
        "source_kind": "S49_PAPER_PLUGIN_SERVER_CALLBACK",
    }
    report["stage"] = "S49_P1_SOURCE_BOUNDED_JOIN_CLOSED"
