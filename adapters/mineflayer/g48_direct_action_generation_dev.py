"""G4.8 read-only original direct JOG/WALK Action generation × G47 T2.

The only P1/M0 postings have *already happened* in original T2. We must not
infer physical per-physics-tick acceptance from an applied effect ACK,
host-local control generation, or a Paper stable-gait candidate.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

_MODES = {
    "JOG": ("set_control", "STABLE_ORDINARY_FORWARD_CANDIDATE", "JOG"),
    "WALK": ("set_forward_sneak_dev", "STABLE_SNEAK_FORWARD_CANDIDATE", "WALK"),
}


@dataclass(frozen=True, slots=True)
class G48DirectActionWorldTickDev:
    session_id: str
    source_seq: int
    world_tick: int
    original_t2_row_sha256: str
    original_g47_row_sha256: str
    g47_status: str
    original_t2_applied_gait: str | None
    original_action_id: str | None
    original_effect_id: str | None
    original_applied_ack_seq: int | None
    node_control_generation: int | None
    direct_requested_mode: str | None
    original_g1_kind: str
    post_control_challenge: bool
    status: str
    source: str = "S49_ORIGINAL_DIRECT_EFFECT_G46_CONTROL_G1_PAPER_T2_DEV"
    complete_tick_motor_acceptance_attested: bool = False
    additional_reader_or_t2_owner: bool = False
    p1_or_m0_posted: bool = False


def join_g48_direct_action_worldticks_dev(
    *, session_id: str, g47_rows: list[dict],
    direct_acks: list[dict], original_clear_acks: list[dict],
    paper_rows: list[dict], t2_rows: list[dict],
) -> tuple[G48DirectActionWorldTickDev, ...]:
    if (not isinstance(session_id, str) or not session_id
            or type(g47_rows) is not list or not g47_rows
            or type(direct_acks) is not list
            or type(original_clear_acks) is not list
            or type(paper_rows) is not list
            or type(t2_rows) is not list
            or len(g47_rows) != len(t2_rows)):
        raise ValueError("G4.8 original source or T2 ledger missing")
    clears = {}
    for clear in original_clear_acks:
        if (type(clear) is not dict
                or type(clear.get("action_id")) is not str
                or type(clear.get("clear_seq")) is not int
                or type(clear.get("s16_seq")) is not int
                or clear["action_id"] in clears
                or not 0 < clear["clear_seq"] < clear["s16_seq"]):
            raise ValueError("G4.8 invalid original S15 CLEAR")
        clears[clear["action_id"]] = clear["clear_seq"]
    actions = {}
    for ack in direct_acks:
        if (
            type(ack) is not dict
            or set(ack) != {
                "action_id", "effect_id", "effect", "ack_seq",
                "requested_input_mode", "source", "requested_not_paper_gait",
            }
            or type(ack["action_id"]) is not str
            or not ack["action_id"].startswith("goal-")
            or ack["action_id"] in actions
            or ack["action_id"] not in clears
            or ack["effect_id"] != ack["action_id"]
            or ack["source"] != "ORIGINAL_S49_NATIVE_APPLIED"
            or ack["requested_not_paper_gait"] is not True
            or ack["requested_input_mode"] not in _MODES
            or ack["effect"] != _MODES[ack["requested_input_mode"]][0]
            or type(ack["ack_seq"]) is not int
            or not 0 < ack["ack_seq"] < clears[ack["action_id"]]
        ):
            raise ValueError("G4.8 foreign, duplicated or forged original direct Action ACK")
        actions[ack["action_id"]] = ack
    paper = {row["source_seq"]: row for row in paper_rows}
    if len(paper) != len(paper_rows):
        raise ValueError("G4.8 duplicated Paper source sequence")
    out = []
    for old, original in zip(g47_rows, t2_rows):
        if (
            type(old) is not dict or type(original) is not dict
            or old.get("session_id") != session_id
            or original.get("session_id") != session_id
            or old.get("source_seq") != original.get("source_seq")
            or old.get("world_tick") != original.get("world_tick")
            or old.get("original_active_action") != original.get("active_action")
            or old.get("original_t2_applied_gait") != original.get("applied_gait")
            or old.get("original_t2_activity") != original.get("activity")
            or old.get("original_p1") != original.get("p1")
            or old.get("original_m0") != original.get("m0")
            or old.get("original_g3_unknown_fallback")
            != original.get("g3_unknown_fallback_dev")
            or type(old.get("source_seq")) is not int
            or old["source_seq"] not in paper
            or paper[old["source_seq"]].get("world_tick") != old["world_tick"]
            or paper[old["source_seq"]].get("session_id") != session_id
            or paper[old["source_seq"]].get("kind") != old.get("original_g1_kind")
            or old.get("original_t2_row_sha256") != hashlib.sha256(
                json.dumps(original,sort_keys=True,separators=(",",":")).encode()
            ).hexdigest()
        ):
            raise ValueError("G4.8 refuses altered G47 original T2 or Paper receipt")
        g1 = paper[old["source_seq"]]
        if old.get("status") == "SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV":
            status = "G47_STABLE_CANDIDATE_UNCHANGED"
        else:
            status = "UNKNOWN_NO_DIRECT_ACTION_ACK_WINDOW"
        action = None
        effect = None
        ack_seq = None
        generation = None
        mode = None
        postchange = False
        matched = [
            ack for ack in actions.values()
            if ack["ack_seq"] < old["source_seq"] < clears[ack["action_id"]]
        ]
        if len(matched) > 1:
            raise ValueError("G4.8 overlapping original direct Action ACK windows")
        if matched:
            ack = matched[0]
            action = ack["action_id"]
            effect = ack["effect_id"]
            ack_seq = ack["ack_seq"]
            mode = ack["requested_input_mode"]
            b = g1.get("g46_motor_boundary_dev")
            if old["status"] != "UNKNOWN_NO_ORIGINAL_G46_EFFECT_WINDOW":
                raise ValueError("G4.8 direct Action overlaps earlier G47 RUN binding")
            if old["original_active_action"] != action:
                status = "UNKNOWN_DIRECT_ACTION_NOT_T2_ACTIVE"
            elif (type(b) is not dict
                  or b.get("action_id") != action
                  or b.get("effect_id") != effect
                  or b.get("requested_mode") != mode
                  or b.get("transition_index") != 0
                  or b.get("control_phase") != "MOVING"
                  or type(b.get("control_generation")) is not int
                  or b["control_generation"] <= 0):
                status = "UNKNOWN_DIRECT_NODE_CONTROL_GENERATION"
            else:
                generation = b["control_generation"]
                postchange = g1.get("g46_challenge_after_control_dev") is True
                if not postchange:
                    status = "UNKNOWN_DIRECT_PRECHANGE_CHALLENGE"
                elif g1["kind"] != _MODES[mode][1]:
                    status = "UNKNOWN_DIRECT_UNSTABLE_PAPER_GAIT"
                elif (old["original_t2_applied_gait"] != _MODES[mode][2]
                      or old.get("original_g3_unknown_fallback") is True
                      or original.get("g3_extra_m0_paid_dev") != 0):
                    status = "UNKNOWN_DIRECT_ORIGINAL_T2_FALLBACK"
                else:
                    status = "DIRECT_SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV"
        old_sha = hashlib.sha256(
            json.dumps(old,sort_keys=True,separators=(",",":")).encode(),
        ).hexdigest()
        out.append(G48DirectActionWorldTickDev(
            session_id=session_id, source_seq=old["source_seq"],
            world_tick=old["world_tick"],
            original_t2_row_sha256=old["original_t2_row_sha256"],
            original_g47_row_sha256=old_sha,
            g47_status=old["status"],
            original_t2_applied_gait=old["original_t2_applied_gait"],
            original_action_id=action, original_effect_id=effect,
            original_applied_ack_seq=ack_seq,
            node_control_generation=generation, direct_requested_mode=mode,
            original_g1_kind=g1["kind"],
            post_control_challenge=postchange, status=status,
        ))
    return tuple(out)
