"""Q4 CPU/DEV structural corroboration of one settled original PLACE.

This validates a caller-supplied Native/Paper receipt *shape* and the original
canonical WAL row. It cannot authenticate raw external producers or prove
physical motor stoppage. It never issues an Action or modifies a journal.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
)
from relay_self.owned_paper_world_dev import PaperTickReceipt


class Q4PlaceRepeatHold(RuntimeError):
    """Previous original PLACE has no corroborated bounded terminal readback."""


@dataclass(frozen=True, slots=True)
class Q4PlaceTerminalReadback:
    look: MineflayerEffectResult
    start: MineflayerEffectResult
    stop: MineflayerEffectResult
    initial_stop: MineflayerObservation
    first_stable: MineflayerObservation
    settled: MineflayerObservation
    paper_stop: PaperTickReceipt
    paper_first: PaperTickReceipt
    paper_settled: PaperTickReceipt
    forward_ms: float
    host_ms: float


def verify_q4_previous_place_terminal_cpu(
    *, row: dict[str, Any], action_id: str,
    native_session_id: str, paper_session_id: str,
    evidence: Q4PlaceTerminalReadback,
) -> None:
    """Fail closed before *any* second original physical PLACE lease.

    Matching typed fields are not authenticated original Native/Paper IO. An
    independent Q review must compare the exact raw streams before real DEV
    qualification; caller-created evidence must not be reported as World PASS.
    """
    if (
        type(action_id) is not str or not action_id
        or type(native_session_id) is not str or not native_session_id
        or type(paper_session_id) is not str or not paper_session_id
        or type(row) is not dict
        or not isinstance(evidence, Q4PlaceTerminalReadback)
    ):
        raise Q4PlaceRepeatHold("typed original Q4 source required")
    try:
        acks = (evidence.look, evidence.start, evidence.stop)
        probes = (
            evidence.initial_stop, evidence.first_stable, evidence.settled,
        )
        paper = (
            evidence.paper_stop, evidence.paper_first, evidence.paper_settled,
        )
        if (
            any(not isinstance(x, MineflayerEffectResult) for x in acks)
            or any(not isinstance(x, MineflayerObservation) for x in probes)
            or any(not isinstance(x, PaperTickReceipt) for x in paper)
            or row["capability"] != "MOVE_PLACE"
            or row["status"] != "NATIVE_PLACE_MOVE_SETTLED"
            or row["action_id"] != action_id
            or row["session_id"] != native_session_id
            or row.get("control") != "forward"
            or row.get("gait_mode") == "SNEAK"
            or any(x.session_id != native_session_id for x in acks + probes)
            or (evidence.look.action_id, evidence.start.action_id,
                evidence.stop.action_id) != (
                    action_id + "-look", action_id + "-start",
                    action_id + "-stop",
                )
            or tuple(x.effect for x in acks)
            != ("look", "set_control", "clear_controls")
            or any(x.result != "applied" or x.error is not None for x in acks)
            or not (row["probe_seq"] < evidence.look.seq
                    < evidence.start.seq < evidence.stop.seq
                    < probes[0].seq < probes[1].seq < probes[2].seq)
            or row["effect_seqs"] != [x.seq for x in acks]
            or any(x.kind != "probe" or not x.request_id
                   or x.snapshot.time is None or x.snapshot.health <= 0
                   for x in probes)
            or len({x.request_id for x in probes}) != 3
            or any(x.provenance.source != "mineflayer"
                   or x.provenance.reference != f"{native_session_id}:{x.seq}"
                   for x in probes)
            or row["initial_stop_seq"] != probes[0].seq
            or row["first_stable_seq"] != probes[1].seq
            or row["after_seq"] != probes[2].seq
            or any(p.server_session_id != paper_session_id or not p.source_ref
                   or type(p.tick) is not int or p.tick < 0 for p in paper)
            or len({p.source_ref for p in paper}) != 3
            or any(type(x) not in (int, float) or not math.isfinite(x)
                   for x in (evidence.forward_ms, evidence.host_ms))
            or not 0 <= evidence.forward_ms <= 800
            or not evidence.forward_ms <= evidence.host_ms <= 2000
        ):
            raise Q4PlaceRepeatHold("Q4 native action or Paper source mismatch")
        ticks = tuple(
            x.snapshot.time.day * 24000 + x.snapshot.time.time_of_day
            for x in probes
        )
        if (
            (row["initial_stop_tick"], row["first_stable_tick"],
             row["settled_tick"]) != ticks
            or not 8 <= ticks[1] - ticks[0] <= 200
            or not 8 <= ticks[2] - ticks[1] <= 200
            or not 8 <= paper[1].tick - paper[0].tick <= 200
            or not 8 <= paper[2].tick - paper[1].tick <= 200
        ):
            raise Q4PlaceRepeatHold("Q4 independent 8+8 tick windows absent")
        before = row["started_position"]
        after = row["settled_position"]
        actual = probes[-1].snapshot.position
        first = probes[1].snapshot.position
        if (
            after is None
            or (actual.x, actual.y, actual.z)
            != (after["x"], after["y"], after["z"])
            or math.dist(
                (first.x, first.y, first.z),
                (actual.x, actual.y, actual.z),
            ) > 0.06
        ):
            raise Q4PlaceRepeatHold("Q4 STOP position not settled")
        displacement = math.dist(
            (before["x"], before["y"], before["z"]),
            (after["x"], after["y"], after["z"]),
        )
        if (
            not math.isfinite(displacement)
            or not 0.1 <= displacement <= 1.0
            or abs(row["displacement_m"] - displacement) > 1e-6
        ):
            raise Q4PlaceRepeatHold("Q4 original MOVE overshoot or no progress")
    except Q4PlaceRepeatHold:
        raise
    except (AttributeError, KeyError, IndexError, TypeError, ValueError,
            ArithmeticError) as exc:
        raise Q4PlaceRepeatHold("Q4 readback cannot be verified") from exc
