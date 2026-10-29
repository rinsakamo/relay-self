"""G4.6 DEV control generation on the *existing* admitted Paper/T1u stream.

The native Node control is sampled on the existing Paper packet callback.
This proves a local generation/mode identity was present when the callback
ran; a Paper frame carries separately sourced server gait facts. Even a
concordant post-command challenge is NOT per-physics-tick causality.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.g45_paper_gait_join_dev import (
    join_g45_native_ack_paper_gait_dev,
)

_KINDS={
    "SPRINT_INPUT":"STABLE_SPRINT_FORWARD_CANDIDATE",
    "JOG":"STABLE_ORDINARY_FORWARD_CANDIDATE",
    "WALK":"STABLE_SNEAK_FORWARD_CANDIDATE",
}


@dataclass(frozen=True, slots=True)
class G46ControlGenerationWindowDev:
    action_id:str
    original_effect_id:str
    requested_input_mode:str
    ack_seq:int
    next_boundary_seq:int
    matched_callback_frames:int
    post_change_challenge_frames:int
    paper_mode_concordant_frames:int
    two_frame_stable_candidate_frames:int
    matching_source_seqs:tuple[int,...]
    post_change_paper_world_ticks:tuple[int,...]
    observed_node_generations:tuple[int,...]
    status:str
    source:str="ORIGINAL_T1F_PAPER_CALLBACK_NODE_GENERATION_AND_G1_T2_DEV"
    node_applied_ack_seen:bool=True
    paper_stable_candidate_not_r_qualified:bool=True
    exact_physics_tick_to_effect_attested:bool=False
    second_t2_owner_created:bool=False


def _concordant(row:dict,mode:str)->bool:
    controls=row["applied_controls"]
    g=row["paper_gait"]
    if (
        type(controls) is not dict or type(g) is not dict
        or any(type(controls.get(k)) is not bool for k in (
            "forward","sprint","sneak",
        ))
        or type(g.get("sprinting")) is not bool
        or type(g.get("sneaking")) is not bool
        or type(g.get("speed_modifiers")) is not int
        or not all(type(g.get(k)) in (int,float) and math.isfinite(g[k])
                   for k in ("speed_base","speed_value"))
    ):
        raise ValueError("G4.6 requires original typed Paper and Node gait")
    if not controls["forward"]:
        return False
    if mode=="SPRINT_INPUT":
        return controls["sprint"] and g["sprinting"] and not controls["sneak"]
    if mode=="JOG":
        return (
            not controls["sprint"] and not controls["sneak"]
            and not g["sprinting"] and not g["sneaking"]
            and g["speed_modifiers"]==0
            and math.isclose(g["speed_value"],g["speed_base"],abs_tol=1e-5)
        )
    return (controls["sneak"] and not controls["sprint"]
            and g["sneaking"] and not g["sprinting"])


def join_g46_control_generation_dev(
    *,session_id:str,original_run_acks:list[dict],
    transition_acks:list[dict],original_clear_acks:list[dict],
    paper_rows:list[dict],t2_rows:list[dict],
)->tuple[G46ControlGenerationWindowDev,...]:
    # G4.5 owns the full source/T2/initial-anchor continuity checks.
    join_g45_native_ack_paper_gait_dev(
        session_id=session_id,transition_acks=transition_acks,
        original_clear_acks=original_clear_acks,paper_rows=paper_rows,
        t2_rows=t2_rows,
    )
    if type(original_run_acks) is not list:
        raise ValueError("G4.6 needs original S49 RUN effect source")
    clears={a["action_id"]:a["clear_seq"] for a in original_clear_acks}
    grouped={}
    for ack in transition_acks:
        grouped.setdefault(ack["action_id"],[]).append(ack)
    source_by_seq={r["source_seq"]:r for r in paper_rows}
    out=[]
    seen=set()
    for run in original_run_acks:
        if (
            type(run) is not dict or set(run)!={
                "action_id","effect_id","ack_seq","source",
                "requested_not_paper_gait",
            }
            or type(run.get("action_id")) is not str
            or run["action_id"] not in clears
            or run["action_id"] in seen
            or run["effect_id"]!=run["action_id"]
            or run["source"]!="ORIGINAL_S49_NATIVE_APPLIED"
            or run["requested_not_paper_gait"] is not True
            or type(run["ack_seq"]) is not int
            or not 0<run["ack_seq"]<clears[run["action_id"]]
        ):
            raise ValueError("G4.6 foreign/duplicated original RUN control")
        seen.add(run["action_id"])
        action=run["action_id"]
        changes=grouped.pop(action,[])
        boundary=[(run["ack_seq"],"SPRINT_INPUT",run["effect_id"])]
        for item in changes:
            if item["ack_seq"]<=boundary[-1][0]:
                raise ValueError("G4.6 non-monotone native gait effect")
            boundary.append((
                item["ack_seq"],item["mode_to"],item["transition_effect_id"],
            ))
        if boundary[-1][0]>=clears[action]:
            raise ValueError("G4.6 native gait beyond original CLEAR")
        for i,(ack_seq,mode,effect_id) in enumerate(boundary):
            next_seq=(boundary[i+1][0] if i+1<len(boundary)
                      else clears[action])
            matched=[]
            after=[]
            concordant=[]
            stable=[]
            generations=set()
            for seq,row in source_by_seq.items():
                if not ack_seq<seq<next_seq:
                    continue
                b=row.get("g46_motor_boundary_dev")
                if b is None:
                    raise ValueError("G4.6 missing original Paper generation")
                if (
                    type(b) is not dict or
                    b.get("action_id")!=action or
                    b.get("effect_id")!=effect_id or
                    b.get("requested_mode")!=mode or
                    b.get("control_phase")!="MOVING"
                ):
                    # Source callback can legitimately report the *next*
                    # control boundary before its emit/ACK; this is UNKNOWN.
                    continue
                gen=b.get("control_generation")
                if type(gen) is not int or gen<=0:
                    raise ValueError("G4.6 invalid motor generation")
                generations.add(gen)
                matched.append(row)
                if row.get("g46_challenge_after_control_dev") is True:
                    after.append(row)
                    if _concordant(row,mode):
                        concordant.append(row)
                        if row["kind"]==_KINDS[mode]:
                            stable.append(row)
            if len(generations)>1:
                raise ValueError("G4.6 duplicated Node generations for one effect")
            status=("PAPER_STABLE_CANDIDATE_NOT_R_QUALIFIED" if stable
                    else "POST_EFFECT_CHALLENGE_MODE_CONCORDANT" if concordant
                    else "POST_EFFECT_CHALLENGE_MODE_UNKNOWN" if after
                    else "NODE_GENERATION_SAMPLED_WITHOUT_POST_EFFECT_CHALLENGE"
                    if matched else "NO_GENERATION_FRAME")
            out.append(G46ControlGenerationWindowDev(
                action_id=action,original_effect_id=effect_id,
                requested_input_mode=mode,ack_seq=ack_seq,
                next_boundary_seq=next_seq,
                matched_callback_frames=len(matched),
                post_change_challenge_frames=len(after),
                paper_mode_concordant_frames=len(concordant),
                two_frame_stable_candidate_frames=len(stable),
                matching_source_seqs=tuple(r["source_seq"] for r in matched),
                post_change_paper_world_ticks=tuple(
                    r["world_tick"] for r in after
                ),
                observed_node_generations=tuple(sorted(generations)),
                status=status,
            ))
    if grouped:
        raise ValueError("G4.6 transition has no original RUN owner")
    return tuple(out)
