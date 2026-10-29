"""G4.8 DEV: ordinary original S49 JOG/WALK epochs, same G1/T2 receipts.

The original S49/T1u Node control-state callback supplies an additional
source-bound epoch for an otherwise UNKNOWN G4.7 WorldTick. Source proof is
strict, but a callback cannot prove command-to-server physics tick causality.
No new P1/M0 posting or replacement of an original G47 classification.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

_MODES = {
    "JOG": ("JOG_ACTION","STABLE_ORDINARY_FORWARD_CANDIDATE","set_control"),
    "WALK": ("WALK_ACTION","STABLE_SNEAK_FORWARD_CANDIDATE","set_forward_sneak_dev"),
}


@dataclass(frozen=True,slots=True)
class G48OrdinaryT2TickDev:
    session_id: str
    source_seq: int
    world_tick: int
    original_t2_row_sha256: str
    original_g47_status: str
    g48_status: str
    original_active_action: str | None
    original_t2_applied_gait: str | None
    original_p1: dict
    original_m0: dict
    ordinary_effect_id: str | None
    ordinary_requested_mode: str | None
    ordinary_control_generation: int | None
    ordinary_epoch_sampled: bool
    ordinary_postchange_challenge: bool
    newly_bound_ordinary_candidate: bool
    source: str = "ORIGINAL_S49_ORDINARY_JOG_WALK_G46_G1_T2_DEV"
    p1_m0_reposted: bool = False
    exact_physics_tick_motor_attested: bool = False
    new_t2_owner: bool = False


def join_g48_ordinary_original_t2_dev(
    *,session_id:str,original_g47_rows:list[dict],
    ordinary_acks:list[dict],original_clear_acks:list[dict],
    paper_rows:list[dict],t2_rows:list[dict],
) -> tuple[G48OrdinaryT2TickDev,...]:
    if (
        type(session_id) is not str or not session_id
        or any(type(x) is not list for x in (
            original_g47_rows,ordinary_acks,original_clear_acks,
            paper_rows,t2_rows,
        ))
        or not t2_rows or len(original_g47_rows)!=len(t2_rows)
    ):
        raise ValueError("G4.8 needs complete original G47/T2 provenance")
    clears={}
    for v in original_clear_acks:
        if (
            type(v) is not dict or type(v.get("action_id")) is not str
            or v["action_id"] in clears
            or type(v.get("clear_seq")) is not int
            or type(v.get("s16_seq")) is not int
            or not 0<v["clear_seq"]<v["s16_seq"]
            or v.get("s16_terminal") not in ("outcome","unknown")
        ):
            raise ValueError("G4.8 invalid original applied CLEAR scope")
        clears[v["action_id"]]=v["clear_seq"]
    ordinary={}
    for v in ordinary_acks:
        if (
            type(v) is not dict
            or set(v)!={"action_id","effect_id","ack_seq",
                         "requested_mode","effect","source"}
            or v.get("action_id") in ordinary
            or v.get("action_id") not in clears
            or v.get("requested_mode") not in _MODES
            or v.get("effect")!=_MODES[v["requested_mode"]][2]
            or v.get("effect_id")!=v["action_id"]
            or v.get("source")!="ORIGINAL_S49_NATIVE_APPLIED"
            or type(v.get("ack_seq")) is not int
            or not 0<v["ack_seq"]<clears[v["action_id"]]
        ):
            raise ValueError("G4.8 forged or unbound ordinary S49 effect ACK")
        ordinary[v["action_id"]]=v
    paper_by_seq={}
    for row in paper_rows:
        if (
            type(row) is not dict
            or type(row.get("source_seq")) is not int
            or row["source_seq"] in paper_by_seq
            or row.get("session_id")!=session_id
        ):
            raise ValueError("G4.8 duplicate/foreign original G1 source")
        paper_by_seq[row["source_seq"]]=row
    out=[]
    for g47,original in zip(original_g47_rows,t2_rows):
        if (
            type(g47) is not dict or type(original) is not dict
            or g47.get("session_id")!=session_id
            or original.get("session_id")!=session_id
            or g47.get("source_seq")!=original.get("source_seq")
            or g47.get("world_tick")!=original.get("world_tick")
            or original.get("source_seq") not in paper_by_seq
            or paper_by_seq[original["source_seq"]].get("world_tick")
            !=original["world_tick"]
            or g47.get("original_active_action")!=original.get("active_action")
            or g47.get("original_t2_applied_gait")!=original.get("applied_gait")
            or g47.get("original_p1")!=original.get("p1")
            or g47.get("original_m0")!=original.get("m0")
            or type(original.get("p1")) is not dict
            or type(original.get("m0")) is not dict
            or original.get("g3_single_p1_owner_dev") is not True
            or original.get("qualification") is not False
            or original.get("full_tick_R_attested") is not False
            or type(g47.get("status")) is not str
        ):
            raise ValueError("G4.8 original T2 P1/M0 or G47 receipt changed")
        digest=hashlib.sha256(json.dumps(
            original,sort_keys=True,separators=(",",":"),
        ).encode("utf-8")).hexdigest()
        if g47.get("original_t2_row_sha256")!=digest:
            raise ValueError("G4.8 original T2 SHA receipt changed")
        action=original.get("active_action")
        ack=ordinary.get(action)
        src=paper_by_seq[original["source_seq"]]
        eligible=(
            ack is not None
            and ack["ack_seq"]<original["source_seq"]<clears[action]
        )
        mode=ack["requested_mode"] if eligible else None
        effect=ack["effect_id"] if eligible else None
        bound=src.get("g46_motor_boundary_dev")
        sampled=False
        after=False
        gen=None
        extra=False
        status=g47["status"]
        if eligible and g47["status"]=="UNKNOWN_NO_ORIGINAL_G46_EFFECT_WINDOW":
            status="UNKNOWN_ORDINARY_NODE_EPOCH_NOT_SAMPLED"
            if (
                type(bound) is dict and bound.get("action_id")==action
                and bound.get("effect_id")==effect
                and bound.get("requested_mode")==_MODES[mode][0]
                and bound.get("control_phase")=="MOVING"
                and bound.get("transition_index")==0
                and type(bound.get("control_generation")) is int
                and bound["control_generation"]>0
            ):
                sampled=True
                gen=bound["control_generation"]
                after=src.get("g46_challenge_after_control_dev") is True
                if not after:
                    status="UNKNOWN_ORDINARY_PRECHANGE_CHALLENGE"
                elif src.get("kind")!=_MODES[mode][1]:
                    status="UNKNOWN_ORDINARY_UNSTABLE_PAPER_GAIT"
                elif (
                    original.get("applied_gait")!=mode
                    or original.get("g3_unknown_fallback_dev") is not False
                ):
                    status="UNKNOWN_ORDINARY_ORIGINAL_T2_FALLBACK"
                elif original.get("g3_extra_m0_paid_dev")!=0:
                    raise ValueError("G4.8 ordinary gait forbids extra M0 debit")
                else:
                    status="SOURCE_BOUND_ORDINARY_GAIT_CANDIDATE_DEV"
                    extra=True
        elif eligible and g47["status"]=="SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV":
            raise ValueError("G4.8 cannot double-certify G47 gait candidate")
        out.append(G48OrdinaryT2TickDev(
            session_id=session_id,source_seq=original["source_seq"],
            world_tick=original["world_tick"],
            original_t2_row_sha256=digest,
            original_g47_status=g47["status"],g48_status=status,
            original_active_action=action,
            original_t2_applied_gait=original.get("applied_gait"),
            original_p1=json.loads(json.dumps(original["p1"])),
            original_m0=json.loads(json.dumps(original["m0"])),
            ordinary_effect_id=effect,
            ordinary_requested_mode=mode,
            ordinary_control_generation=gen,
            ordinary_epoch_sampled=sampled,
            ordinary_postchange_challenge=after,
            newly_bound_ordinary_candidate=extra,
        ))
    return tuple(out)
