"""S-only prospective Mineflayer held-control readback; not a Paper tick clock.

The DEV wrapper calls bot.getControlState() for all seven controls and writes
its own original evidence file without changing the ordinary bridge protocol.
No server-effective input, all-Action coverage, or physical WAIT is granted.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.process_session import MineflayerProcessStartError
from adapters.mineflayer.python_protocol import MineflayerAdapterStarted
from adapters.mineflayer.s51_eat_real_ci import _recording_session_type

CONTROLS = ("forward", "back", "left", "right", "jump", "sprint", "sneak")
SOURCE = "S50_DEV_NATIVE_READBACK_V1"
MAX_ROWS = 8192


def readback_session_type(native_output, command_output, sidecar: Path):
    """Opt-in isolated process only: no global environment mutation."""
    if (not sidecar.is_absolute() or sidecar.exists()
            or not sidecar.parent.is_dir() or sidecar.is_symlink()
            or sidecar.parent.is_symlink()):
        raise BoundaryRejected("S50 readback requires a fresh absolute sidecar")
    base = _recording_session_type(native_output, command_output)

    class RecordedReadbackSession(base):
        @classmethod
        async def launch(
            cls, config, *, node_executable="node", startup_timeout_s=10.0,
        ):
            if not (0 < startup_timeout_s <= 60):
                raise MineflayerProcessStartError("invalid DEV startup timeout")
            bridge = Path(__file__).with_name("s50_p1_readback_bridge.mjs")
            if not bridge.is_file() or bridge.is_symlink():
                raise MineflayerProcessStartError("missing physical DEV readback bridge")
            env = dict(os.environ)
            if "RELAYSELF_S50_P1_READBACK_FILE" in env:
                raise MineflayerProcessStartError("preexisting readback source env")
            env["RELAYSELF_S50_P1_READBACK_FILE"] = str(sidecar)
            try:
                process = await asyncio.create_subprocess_exec(
                    *config.argv(bridge, node_executable=node_executable),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=None,
                    env=env,
                )
            except OSError as exc:
                raise MineflayerProcessStartError("readback Node launch failed") from exc
            session = cls(process)
            try:
                started = await asyncio.wait_for(
                    session.receive(), timeout=startup_timeout_s,
                )
                if not isinstance(started, MineflayerAdapterStarted):
                    raise MineflayerProcessStartError("missing native adapter startup")
                session._started = started
                return session
            except Exception:
                await session.terminate()
                raise

    return RecordedReadbackSession


def _state(row: dict) -> dict[str, bool]:
    state = row.get("controls")
    if (not isinstance(state, dict) or set(state) != set(CONTROLS)
            or any(type(state[key]) is not bool for key in CONTROLS)):
        raise BoundaryRejected("incomplete/nonboolean Mineflayer native controls")
    return state


def review_native_controls(
    lines: str, native: list[dict], movement: dict,
) -> dict:
    """Match true getControlState snapshots to original native effect/probe ACKs."""
    if not isinstance(native, list) or not isinstance(movement, dict):
        raise BoundaryRejected("missing native provenance")
    session = movement.get("source_session")
    action = movement.get("action_id")
    if not isinstance(session, str) or not session or not isinstance(action, str) or not action:
        raise BoundaryRejected("missing readback session/Action ID")
    try:
        source = [json.loads(line) for line in lines.splitlines()]
    except (ValueError, TypeError) as exc:
        raise BoundaryRejected("bad native control original JSONL") from exc
    if not (5 <= len(source) <= MAX_ROWS):
        raise BoundaryRejected("missing/unbounded direct native source")
    ack_indexes = {
        "forward": movement.get("forward_seq"),
        "clear": movement.get("clear_seq"),
        "after": movement.get("source_after_seq"),
    }
    if any(type(i) is not int or i < 0 or i >= len(native) for i in ack_indexes.values()):
        raise BoundaryRejected("invalid native ACK index")
    forward, clear, after = (native[ack_indexes[key]]
                             for key in ("forward", "clear", "after"))
    if (forward.get("type") != "effect_result"
            or forward.get("action_id") != action
            or forward.get("effect") != "set_control"
            or forward.get("result") != "applied"
            or clear.get("type") != "effect_result"
            or clear.get("action_id") != action + "-clear"
            or clear.get("effect") != "clear_controls"
            or clear.get("result") != "applied"
            or after.get("type") != "observation"
            or after.get("request_id") != action + "-seek-after"):
        raise BoundaryRejected("unbound native readback Action/ACK/probe")
    if not (ack_indexes["forward"] < ack_indexes["clear"] < ack_indexes["after"]):
        raise BoundaryRejected("invalid source seq ordering")
    previous_client_tick = 0
    for i, row in enumerate(source, 1):
        if (not isinstance(row, dict)
                or row.get("source") != SOURCE
                or row.get("session_id") != session
                or type(row.get("ordinal")) is not int
                or row["ordinal"] != i
                or type(row.get("client_physics_tick")) is not int
                or row["client_physics_tick"] < previous_client_tick):
            raise BoundaryRejected("missing/foreign/unordered getControlState original")
        previous_client_tick = row["client_physics_tick"]
        if row.get("kind") not in {
            "SESSION_START", "PHYSICS_TICK", "EFFECT_ACK", "PROBE", "SHUTDOWN_ACK",
        }:
            raise BoundaryRejected("native direct control source incomplete/error")
        if row.get("kind") != "SESSION_START":
            _state(row)

    if source[0].get("kind") != "SESSION_START" or source[0].get("native_seq") != 0:
        raise BoundaryRejected("native readback missing source session begin")
    indexed = {}
    for index, row in enumerate(source):
        if row.get("kind") not in {"EFFECT_ACK", "PROBE", "SHUTDOWN_ACK"}:
            continue
        seq = row.get("native_seq")
        if type(seq) is not int or seq in indexed or not 0 <= seq < len(native):
            raise BoundaryRejected("duplicate/foreign readback source frame")
        frame = native[seq]
        if frame.get("session_id") != session or frame.get("seq") != seq:
            raise BoundaryRejected("readback native session/seq mismatch")
        if row["kind"] == "EFFECT_ACK":
            if (frame.get("type") != "effect_result"
                    or row.get("native_action_id") != frame.get("action_id")):
                raise BoundaryRejected("readback event not tied to native ACK")
        elif row["kind"] == "PROBE":
            if (frame.get("type") != "observation"
                    or frame.get("kind") != "probe"
                    or row.get("native_action_id") != frame.get("request_id")):
                raise BoundaryRejected("readback not tied to native observation")
        elif frame.get("type") != "shutdown_ack":
            raise BoundaryRejected("readback shutdown not tied to STOP")
        indexed[seq] = index
    if (set(indexed) != {
            row["seq"] for row in native
            if row.get("type") in {"effect_result", "shutdown_ack"}
            or (row.get("type") == "observation" and row.get("kind") == "probe")
        }):
        raise BoundaryRejected("missing or extra direct effect/probe/STOP readback")
    for key in ("forward", "clear", "after"):
        if ack_indexes[key] not in indexed:
            raise BoundaryRejected("missing direct Action readback")
    forward_position = indexed[ack_indexes["forward"]]
    clear_position = indexed[ack_indexes["clear"]]
    after_position = indexed[ack_indexes["after"]]
    if not (forward_position < clear_position < after_position):
        raise BoundaryRejected("readback event chronology drift")
    if not _state(source[forward_position])["forward"]:
        raise BoundaryRejected("forward was not actually held after control ACK")
    if any(_state(source[clear_position]).values()):
        raise BoundaryRejected("clear ACK did not clear all seven controls")
    if any(_state(source[after_position]).values()):
        raise BoundaryRejected("after-probe retained native movement control")
    samples = [
        row for row in source[clear_position + 1:]
        if row["kind"] in {"PHYSICS_TICK", "PROBE", "SHUTDOWN_ACK"}
    ]
    if not any(row["kind"] == "PHYSICS_TICK" for row in samples):
        raise BoundaryRejected("missing subsequent client physicsTick samples")
    if any(any(_state(row).values()) for row in samples):
        raise BoundaryRejected("post-clear native controls reactivated")
    if (source[-1]["kind"] != "SHUTDOWN_ACK"
            or native[source[-1]["native_seq"]].get("type") != "shutdown_ack"):
        raise BoundaryRejected("missing terminal direct native STOP readback")

    return {
        "classification": "S50_P1_DIRECT_MINEFLAYER_CONTROL_SAMPLES_DEV_ONLY",
        "source_session": session,
        "action_id": action,
        "controls": list(CONTROLS),
        "source_rows": len(source),
        "post_clear_sample_count": len(samples),
        "clear_readback_all_false": True,
        "after_probe_readback_all_false": True,
        "client_clock": "MINEFLAYER_PHYSICS_TICK_NOT_PAPER_WORLD_TICK",
        "source_scope": "CLIENT_EFFECT_AND_PHYSICS_CALLBACK_SAMPLES_ONLY",
        "paper_effective_input_release_tick": "NOT_ATTESTED",
        "continuous_held_controls_absence": "NOT_ATTESTED",
        "all_S15_S16_issuers_absent": "NOT_ATTESTED",
        "wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "independent_R_qualification": False,
        "science_go": False,
    }
