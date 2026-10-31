"""L22 read-only post-S16 settling audit. No World/Action/learning authority.

The existing S16 OUTCOME closes an Action, not the Minecraft physics.
Two spatial probes, even equal ones, cannot establish an idle tick window.
This module preserves post-S16 move events instead of relaxing L16 admission.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from adapters.mineflayer.l16_first_action_goal_originals import L16GoalPlan
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
    MineflayerStreamDecoder,
)
from relay_self.l14_original_bridge_goal_window import (
    MAX_RECEIVED,
    MAX_RECEIVED_LINES,
    MAX_SENT,
    MAX_SENT_LINES,
    _json,
    _lines,
    _strict_receipt,
)

SCHEMA = "L22_POST_S16_SETTLING_DIAGNOSTIC_V1"


class L22SourceRejected(ValueError):
    """Missing, foreign, reordered or malformed physical source."""


@dataclass(frozen=True, slots=True)
class L22SettlingReview:
    schema: str
    session_id: str
    action_id: str
    s16_original_sha256: str
    received_sha256: str
    sent_sha256: str
    after_seq: int
    first_probe_seq: int
    second_probe_seq: int
    move_event_seqs: tuple[int, ...]
    post_s16_displacement_m: float
    two_probe_displacement_m: float
    geometric_goal_candidate: str
    settling_state: str
    reason: str
    accepted_goal_status: str = "UNDETERMINED"
    stable_world_ticks_attested: bool = False
    physically_stopped_proven: bool = False
    independent_goal_owner_authenticated: bool = False
    qualified_real_learning_pairs: int = 0
    s10_updates: int = 0
    s11_grants: int = 0


def inspect_l22_settling(
    *, received_original: bytes, sent_original: bytes, s7_receipt: dict,
    s16_original: bytes, plan: L16GoalPlan, session_id: str, action_id: str,
) -> L22SettlingReview:
    """Audit only sealed first-Action S7 and S16 originals, never issue probes.

    'No move in two probes' is not proof of no movement in intervening
    Minecraft ticks. L22 therefore never emits a qualified Goal label.
    """
    if not isinstance(plan, L16GoalPlan) or not (
        isinstance(session_id, str) and session_id
        and isinstance(action_id, str) and action_id
    ):
        raise L22SourceRejected("explicit typed source identity and plan required")
    if not isinstance(s16_original, bytes) or not (
        0 < len(s16_original) <= 4096 and s16_original.endswith(b"\n")
        and len(s16_original.splitlines()) == 1
    ):
        raise L22SourceRejected("sealed bounded S16 source required")
    try:
        terminal = _json(s16_original)
        rlines = _lines(
            received_original, MAX_RECEIVED, MAX_RECEIVED_LINES, "received",
        )
        slines = _lines(sent_original, MAX_SENT, MAX_SENT_LINES, "sent")
        _strict_receipt(
            s7_receipt, received_original, sent_original, rlines, slines,
        )
        decoder = MineflayerStreamDecoder()
        frames = [decoder.decode(line.decode("utf-8")) for line in rlines]
        sent = [_json(line) for line in slines]
    except (ValueError, TypeError, UnicodeError) as exc:
        raise L22SourceRejected("S7/S16 original or source receipt invalid") from exc
    if (
        not isinstance(terminal, dict)
        or terminal.get("schema") != "L13_S16_TERMINAL_SOURCE_V1"
        or terminal.get("session_id") != session_id
        or terminal.get("action_id") != action_id
        or terminal.get("source_status") != "executed"
        or terminal.get("disposition") != "outcome"
        or terminal.get("reason_code") != "observed_execution"
        or decoder.session_id != session_id
        or not frames
        or any(frame.session_id != session_id for frame in frames)
    ):
        raise L22SourceRejected("S16 OUTCOME and native session not source-bound")
    before_seq = terminal.get("before_seq")
    after_seq = terminal.get("after_seq")
    if (
        type(before_seq) is not int or type(after_seq) is not int
        or not (0 < before_seq < after_seq < len(frames) - 2)
    ):
        raise L22SourceRejected("invalid original S16 Action boundaries")
    after = frames[after_seq]
    if not isinstance(after, MineflayerObservation) or after.kind != "probe":
        raise L22SourceRejected("S16 after snapshot missing")
    cleanup = [
        f for f in frames[before_seq + 1:after_seq]
        if isinstance(f, MineflayerEffectResult)
        and f.action_id == f"{action_id}-s15-clear"
        and f.effect == "clear_controls"
        and f.result == "applied"
        and f.error is None
    ]
    dispatch = [
        f for f in frames[before_seq + 1:after_seq]
        if isinstance(f, MineflayerEffectResult)
        and f.action_id == action_id
        and f.effect == "set_control"
        and f.result == "applied"
        and f.error is None
    ]
    effects = [f for f in frames if isinstance(f, MineflayerEffectResult)]
    if (
        len(cleanup) != 1 or len(dispatch) != 1
        or not dispatch[0].seq < cleanup[0].seq < after_seq
        or len(effects) != 2
    ):
        raise L22SourceRejected("unique motor and S15 clear ACK required")
    ids = (
        f"l16:{session_id}:{action_id}:goal-1",
        f"l16:{session_id}:{action_id}:goal-2",
    )
    probes = [
        f for f in frames[after_seq + 1:]
        if isinstance(f, MineflayerObservation) and f.kind == "probe"
    ]
    if (
        len(probes) != 2 or tuple(f.request_id for f in probes) != ids
        or probes[0].seq >= probes[1].seq
        or frames[-1].seq != probes[-1].seq
    ):
        raise L22SourceRejected("two source-correlated post-S16 probes required")
    outbound_effects = [x for x in sent if x.get("type") == "effect"]
    outbound_probes = [
        x.get("request_id") for x in sent if x.get("type") == "observe"
    ]
    if (
        any(x.get("type") not in ("observe", "effect") for x in sent)
        or len(outbound_effects) != 2
        or outbound_effects[0].get("action_id") != action_id
        or outbound_effects[0].get("effect") != "set_control"
        or outbound_effects[1].get("action_id") != f"{action_id}-s15-clear"
        or outbound_effects[1].get("effect") != "clear_controls"
        or outbound_probes[-2:] != list(ids)
        or outbound_probes.count(ids[0]) != 1
        or outbound_probes.count(ids[1]) != 1
    ):
        raise L22SourceRejected("foreign or duplicated outbound source commands")
    moving = []
    for f in frames[after_seq + 1:probes[-1].seq + 1]:
        if f in probes:
            continue
        if (
            not isinstance(f, MineflayerObservation)
            or f.request_id is not None
            or f.kind not in ("move", "entities")
        ):
            raise L22SourceRejected("unsafe native item inside settling window")
        if f.kind == "move":
            moving.append(f.seq)
    def distance(a: MineflayerObservation, b: MineflayerObservation) -> float:
        return math.hypot(
            a.snapshot.position.x - b.snapshot.position.x,
            a.snapshot.position.z - b.snapshot.position.z,
        )

    d_after = distance(after, probes[-1])
    d_probes = distance(probes[0], probes[1])
    d1 = math.hypot(
        probes[0].snapshot.position.x - plan.target_x,
        probes[0].snapshot.position.z - plan.target_z,
    )
    d2 = math.hypot(
        probes[1].snapshot.position.x - plan.target_x,
        probes[1].snapshot.position.z - plan.target_z,
    )
    if (
        d_probes > plan.stable_probe_delta_max_m
        or (d1 <= plan.tolerance_m) != (d2 <= plan.tolerance_m)
    ):
        candidate = "UNDETERMINED"
    else:
        candidate = "REACHED" if d2 <= plan.tolerance_m else "NOT_REACHED"
    if moving:
        state, reason = "SETTLING_OBSERVED", "POST_S16_MOVE_EVENT"
    elif d_after > plan.stable_probe_delta_max_m:
        state, reason = "SETTLING_OBSERVED", "POST_S16_POSITION_DRIFT"
    else:
        state, reason = "STABILITY_UNPROVEN", "NO_ATTESTED_IDLE_TICK_WINDOW"
    return L22SettlingReview(
        schema=SCHEMA, session_id=session_id, action_id=action_id,
        s16_original_sha256=hashlib.sha256(s16_original).hexdigest(),
        received_sha256=hashlib.sha256(received_original).hexdigest(),
        sent_sha256=hashlib.sha256(sent_original).hexdigest(),
        after_seq=after_seq, first_probe_seq=probes[0].seq,
        second_probe_seq=probes[1].seq, move_event_seqs=tuple(moving),
        post_s16_displacement_m=d_after, two_probe_displacement_m=d_probes,
        geometric_goal_candidate=candidate, settling_state=state,
        reason=reason,
    )
