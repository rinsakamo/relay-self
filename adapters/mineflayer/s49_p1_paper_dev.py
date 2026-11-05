"""S49 original owner -> bounded Paper callback-tick source (DEV ONLY).

The native Paper plugin never writes P1 state or grants actions. This module
records the Paper's successive callback snapshots and one tagged combat event;
they are candidate physical body ticks, NOT independently certified complete
full World-tick activity or formal R evidence.
"""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
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
    expected_choice: str = "REST",
    marker_style: str = "legacy",
) -> dict[str, Any]:
    """Pure source-shape check, no independent source authenticity promotion."""
    if not re.fullmatch(r"[a-z0-9]{12,32}", nonce):
        raise S49P1SourceRejected("invalid nonce")
    if (expected_choice not in ("REST", "WAIT")
            or marker_style not in ("legacy", "choice")
            or (marker_style == "legacy" and expected_choice == "WAIT")):
        raise S49P1SourceRejected("unsupported source decision marker")
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
        or native_report.get("rest_intent_selected") is not (expected_choice == "REST")
        or (expected_choice == "WAIT" and
            native_report.get("rest_choice", {}).get("selected") != "WAIT")
        or native_report.get("rest_action_issued") is not False
        or native_report.get("attack_server_health_drop_observed") is not True
    ):
        raise S49P1SourceRejected("not original one ATTACK then REST")
    if _rows(log, "SOURCE_FAULT"):
        raise S49P1SourceRejected("server source overflow or missing World/player")
    starts, rests, stops, fights, ticks, choices = (
        _rows(log, key)
        for key in ("START", "REST", "STOP", "FIGHT", "TICK", "CHOICE")
    )
    markers = rests if marker_style == "legacy" else choices
    if (
        any(len(v) != 1 for v in (starts, stops, fights, markers))
        or (marker_style == "choice" and rests)
        or (marker_style == "legacy" and choices)
        or not 20 <= len(ticks) <= 480
    ):
        raise S49P1SourceRejected("incomplete or contradictory source brackets")
    start, marker, stop, fight = starts[0], markers[0], stops[0], fights[0]
    if marker_style == "choice" and marker.get("selected") != expected_choice:
        raise S49P1SourceRejected("wrong native L0 choice marker")
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
               for r in (start, marker, stop, fight, *ticks))
        or stop.get("coverage") != "SERVER_TICK_CALLBACK_NOT_FULL_TICK"
        or start.get("coverage") != "SERVER_TICK_CALLBACK_NOT_FULL_TICK"
        or _int(stop, "faults") != 0
    ):
        raise S49P1SourceRejected("foreign or unbounded Paper source")
    began = _int(start, "tick")
    ended = _int(stop, "tick")
    choice_tick = _int(marker, "tick")
    fight_tick = _int(fight, "tick")
    if not began <= fight_tick < choice_tick <= ended:
        raise S49P1SourceRejected("FIGHT/choice source order missing")
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
    post_rest = [x for x in rows if x["world_tick"] >= choice_tick + 2]
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
        "paper_rest_marker_tick": choice_tick if expected_choice == "REST" else None,
        "paper_choice_marker_tick": choice_tick,
        "paper_selected_intent": expected_choice,
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
    report: dict[str, Any], log_path: Path, *,
    prospective_rest_dev: bool = False,
    p1_checkout: Path | None = None,
    margin_choice_dev: bool = False,
    high_fatigue_dev: bool = False,
) -> None:
    """One S49 original ATTACK->REST, with server-only source hooks."""
    if not isinstance(session, MineflayerProcessSession):
        raise S49P1SourceRejected("original process required")
    if (
        type(prospective_rest_dev) is not bool
        or type(margin_choice_dev) is not bool
        or type(high_fatigue_dev) is not bool
        or (margin_choice_dev and not prospective_rest_dev)
        or (high_fatigue_dev and not margin_choice_dev)
        or (prospective_rest_dev and (
            not isinstance(p1_checkout, Path)
            or not p1_checkout.is_absolute()
            or not p1_checkout.is_dir()
        ))
    ):
        raise S49P1SourceRejected("pinned original P1 checkout required for DEV sensor")
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

        async def mark_choice(selected: str) -> None:
            if selected not in ("REST", "WAIT"):
                raise S49P1SourceRejected("unsafe S49 native choice marker")
            await _send_and_wait(
                server, log_path,
                command=f"s49p1choice {nonce} {selected}",
                key="CHOICE", nonce=nonce,
            )

        async def pre_decision_sensor(probe: object) -> dict[str, Any]:
            # Separate pinned P1 evaluator reads the already published
            # Paper prefix. It has no server command, Body mutation or
            # Self Action authority. Never infer from post-REST samples.
            assert p1_checkout is not None
            args = [
                sys.executable, "-B",
                "tools/bug0_s49_p1_prospective_sensor.py",
                "--paper-log", str(log_path),
                "--p1-checkout", str(p1_checkout),
                "--session-id", session.started.session_id,
                "--probe-seq", str(probe.seq),
            ]
            if margin_choice_dev:
                args.extend(["--sensor-policy", "margin"])
            if high_fatigue_dev:
                args.extend(["--experimental-wait-rate", "0.001"])
            result = await asyncio.to_thread(
                subprocess.run, args, capture_output=True, text=True,
                timeout=12, check=True,
            )
            raw = json.loads(result.stdout)
            if margin_choice_dev:
                if (
                    raw.get("sensor_decision_policy") != "margin"
                    or raw.get("experimental_wait_recovery_per_tick") != (
                        0.001 if high_fatigue_dev else 0.002
                    )
                ):
                    raise S49P1SourceRejected(
                        "wrong frozen DEV P1 profile before original L0"
                    )
                if high_fatigue_dev and raw.get("request_rest") is not True:
                    raise S49P1SourceRejected(
                        "high-fatigue model cannot justify REST: no Action replay"
                    )
            elif raw.get("request_rest") is not True:
                raise S49P1SourceRejected(
                    "prospective experimental P1 sensor did not request REST"
                )
            return raw

        args: dict[str, Any] = {
            "health_log": log_path,
            "rest_intent_hook": mark_rest,
            "attack_pre_issue_hook": mark_attack_source,
            "paper_health_sequential": True,
        }
        if prospective_rest_dev:
            args["prospective_rest_request"] = pre_decision_sensor
        if margin_choice_dev:
            args.pop("rest_intent_hook")
            args["choice_marker_hook"] = mark_choice
        await run_s49_attack_then_rest_dev(
            session, server, owner, report, **args,
        )
    finally:
        # Never mask a pre-issue refusal or reissue an ATTACK.
        if source_started:
            await _send_and_wait(
                server, log_path, command=f"s49p1stop {nonce}",
                key="STOP", nonce=nonce,
            )
    report["status"] = "PENDING_NATIVE_JOIN"
    selected = report.get("rest_choice", {}).get("selected")
    checked = inspect_paper_tick_source(
        log_path.read_text(encoding="utf-8"),
        nonce=nonce, native_report=report,
        expected_choice=selected if margin_choice_dev else "REST",
        marker_style="choice" if margin_choice_dev else "legacy",
    )
    if prospective_rest_dev:
        sensor = report.get("prospective_p1_sensor")
        if (
            not isinstance(sensor, dict)
            or sensor.get("source_kind")
                != "PAPER_PRE_DECISION_CALLBACK_P1_VIRTUAL_SENSOR_DEV"
            or (not margin_choice_dev and sensor.get("request_rest") is not True)
            or (margin_choice_dev and
                sensor.get("request_rest") is not (selected == "REST"))
            or (high_fatigue_dev and sensor.get("request_rest") is not True)
            or sensor.get("experimental_wait_recovery_per_tick") != (
                0.001 if high_fatigue_dev else 0.002
            )
            or sensor.get("model_default_fatigue_pre_decision") != 0
            or not 0 < sensor.get("model_experimental_fatigue_pre_decision", -1) <= 1
            or sensor.get("paper_source_uuid") != checked["paper_world"]
            or not (
                checked["paper_fight_callback_tick"]
                <= sensor["source_as_of_tick"]
                < checked["paper_choice_marker_tick"]
                <= checked["world_tick_last_callback"]
            )
        ):
            raise S49P1SourceRejected(
                "late/foreign retrospective REST model sensor cannot be admitted"
            )
        report["prospective_p1_s49_join"] = {
            "status": (
                "DEV_THRESHOLD_MARGIN_MODEL_SENSOR_NATIVE_CHOICE"
                if margin_choice_dev
                else "DEV_NONDEFAULT_PROFILE_MODEL_SENSOR_REST_CHOSEN"
            ),
            "source_as_of_server_tick": sensor["source_as_of_tick"],
            "rest_marker_server_tick": checked["paper_rest_marker_tick"],
            "choice_marker_server_tick": checked["paper_choice_marker_tick"],
            "actual_original_l0_choice": selected,
            "model_fatigue_pre_decision": (
                sensor["model_experimental_fatigue_pre_decision"]
            ),
            "original_default_model_fatigue_pre_decision": 0,
            "source_future_read_for_decision": False,
            "independent_physical_fatigue_recovery": False,
        }
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
