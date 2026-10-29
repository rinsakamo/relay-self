"""G4.7 DEV read-only join: each ORIGINAL T2 P1/M0 WorldTick to G46 mode.

No Action, native reader, new T2 owner, energy credit, or gait proposal.
UNKNOWN is preserved even when control was requested but Paper evidence is
insufficient. One original G1 frame and its original T2 receipt are joined
by the exact same session/source sequence/WorldTick.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from adapters.mineflayer.g46_paper_control_generation_dev import (
    join_g46_control_generation_dev,
)

_MODE_KIND = {
    "SPRINT_INPUT": ("STABLE_SPRINT_FORWARD_CANDIDATE", "RUN"),
    "JOG": ("STABLE_ORDINARY_FORWARD_CANDIDATE", "JOG"),
    "WALK": ("STABLE_SNEAK_FORWARD_CANDIDATE", "WALK"),
}


@dataclass(frozen=True, slots=True)
class G47OriginalT2WorldTickJoinDev:
    session_id: str
    source_seq: int
    world_tick: int
    original_t2_row_sha256: str
    original_active_action: str | None
    original_t2_motor_mode: str
    original_t2_applied_gait: str | None
    original_t2_activity: str
    original_g3_unknown_fallback: bool
    original_g3_extra_m0_paid: float
    original_p1: dict
    original_m0: dict
    original_g1_kind: str
    native_effect_id: str | None
    node_control_generation: int | None
    requested_input_mode: str | None
    postchange_challenge_observed: bool
    status: str
    source: str = "ORIGINAL_S49_NODE_G46_G1_PAPER_T2_P1_M0_DEV"
    qualified: bool = False
    packet_to_physics_tick_attested: bool = False
    second_t2_owner_created: bool = False
    new_p1_or_m0_posting: bool = False


def join_g47_original_t2_worldticks_dev(
    *, session_id: str, original_run_acks: list[dict],
    transition_acks: list[dict], original_clear_acks: list[dict],
    paper_rows: list[dict], t2_rows: list[dict],
) -> tuple[G47OriginalT2WorldTickJoinDev, ...]:
    # G4.5/G4.6 retain original Paper → T2 source and Action phase checks.
    windows = join_g46_control_generation_dev(
        session_id=session_id, original_run_acks=original_run_acks,
        transition_acks=transition_acks,
        original_clear_acks=original_clear_acks,
        paper_rows=paper_rows, t2_rows=t2_rows,
    )
    if not t2_rows:
        raise ValueError("G4.7 requires original T2 accounting rows")
    paper = {r["source_seq"]: r for r in paper_rows}
    out = []
    last_seq = -1
    last_tick = -1
    for original in t2_rows:
        if (
            type(original) is not dict
            or original.get("session_id") != session_id
            or type(original.get("source_seq")) is not int
            or type(original.get("world_tick")) is not int
            or original["source_seq"] <= last_seq
            or original["world_tick"] != last_tick + 1
            and last_tick >= 0
            or original["source_seq"] not in paper
            or paper[original["source_seq"]].get("world_tick")
            != original["world_tick"]
            or paper[original["source_seq"]].get("session_id") != session_id
            or paper[original["source_seq"]].get("t2_activity")
            != original.get("activity")
            or type(original.get("m0")) is not dict
            or type(original.get("p1")) is not dict
            or original.get("g3_single_p1_owner_dev") is not True
            or original.get("qualification") is not False
            or original.get("full_tick_R_attested") is not False
            or type(original.get("g3_unknown_fallback_dev")) is not bool
            or type(original.get("g3_extra_m0_paid_dev")) not in (int, float)
        ):
            raise ValueError("G4.7 refuses foreign/nonconsecutive original T2 receipt")
        seq = original["source_seq"]
        last_seq, last_tick = seq, original["world_tick"]
        g1 = paper[seq]
        in_windows = [
            w for w in windows if w.ack_seq < seq < w.next_boundary_seq
        ]
        if len(in_windows) > 1:
            raise ValueError("G4.7 overlapping original S49 effect windows")
        w = in_windows[0] if in_windows else None
        mode = w.requested_input_mode if w is not None else None
        boundary = g1.get("g46_motor_boundary_dev")
        effect = w.original_effect_id if w is not None else None
        generation = None
        postchange = False
        status = "UNKNOWN_NO_ORIGINAL_G46_EFFECT_WINDOW"
        if w is not None:
            if original.get("active_action") != w.action_id:
                status = "UNKNOWN_NO_ACTIVE_ORIGINAL_T2_ACTION"
            elif type(boundary) is not dict:
                status = "UNKNOWN_MISSING_NODE_GENERATION"
            elif (
                boundary.get("effect_id") != effect
                or boundary.get("action_id") != w.action_id
                or boundary.get("requested_mode") != mode
                or boundary.get("control_phase") != "MOVING"
                or type(boundary.get("control_generation")) is not int
                or boundary["control_generation"] <= 0
            ):
                status = "UNKNOWN_NODE_EFFECT_BOUNDARY"
            else:
                generation = boundary["control_generation"]
                postchange = g1.get("g46_challenge_after_control_dev") is True
                if not postchange:
                    status = "UNKNOWN_PRECHANGE_CHALLENGE"
                elif g1["kind"] != _MODE_KIND[mode][0]:
                    status = "UNKNOWN_UNSTABLE_PAPER_GAIT"
                elif (
                    original.get("applied_gait") != _MODE_KIND[mode][1]
                    or original.get("g3_unknown_fallback_dev") is True
                ):
                    status = "UNKNOWN_ORIGINAL_T2_GAIT_FALLBACK"
                elif original["g3_extra_m0_paid_dev"] != 0:
                    # The G4.7 source only describes RUN/JOG/WALK, not DASH;
                    # a disputed extra charge must never be silently endorsed.
                    raise ValueError("G4.7 unexpected extra M0 debit")
                else:
                    status = "SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV"
        # Hash and copy only the originals: never recalculate state, never post.
        digest = hashlib.sha256(json.dumps(
            original, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        out.append(G47OriginalT2WorldTickJoinDev(
            session_id=session_id, source_seq=seq,
            world_tick=original["world_tick"],
            original_t2_row_sha256=digest,
            original_active_action=original.get("active_action"),
            original_t2_motor_mode=original.get("motor_mode", "UNDETERMINED"),
            original_t2_applied_gait=original.get("applied_gait"),
            original_t2_activity=original["activity"],
            original_g3_unknown_fallback=original["g3_unknown_fallback_dev"],
            original_g3_extra_m0_paid=original["g3_extra_m0_paid_dev"],
            original_p1=original["p1"].copy(), original_m0=original["m0"].copy(),
            original_g1_kind=g1["kind"], native_effect_id=effect,
            node_control_generation=generation,
            requested_input_mode=mode,
            postchange_challenge_observed=postchange, status=status,
        ))
    return tuple(out)
