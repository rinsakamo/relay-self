"""G4.5 source-order-only native gait ACK → original Paper/G1/T2 segments.

The single original reader owns both Node and Paper messages. A stable
candidate between typed ACK and CLEAR is not packet-to-tick causality or
full per-WorldTick physical gait attestation.
"""
from __future__ import annotations

from dataclasses import dataclass

_EXPECTED = {
    "JOG": "STABLE_ORDINARY_FORWARD_CANDIDATE",
    "WALK": "STABLE_SNEAK_FORWARD_CANDIDATE",
}


@dataclass(frozen=True, slots=True)
class G45PaperGaitSegmentDev:
    action_id: str
    transition_ack_seq: int
    next_boundary_seq: int
    mode_to: str
    original_paper_frames: int
    initial_or_transition_unknown_frames: int
    stable_matching_candidate_frames: int
    stable_other_candidate_frames: int
    stable_matching_world_ticks: tuple[int, ...]
    stable_matching_source_seqs: tuple[int, ...]
    source: str = "ORIGINAL_NATIVE_S15_ACK_AND_ORIGINAL_T1U_G1_T2_DEV"
    status: str = "NO_STABLE_FRAME"
    applied_node_control_attested: bool = True
    paper_stable_candidate_seen: bool = False
    packet_to_paper_tick_causality_attested: bool = False
    full_tick_gait_attested: bool = False
    second_t2_owner_created: bool = False


def join_g45_native_ack_paper_gait_dev(
    *,session_id:str,transition_acks:list[dict],
    original_clear_acks:list[dict],
    paper_rows:list[dict],t2_rows:list[dict],
) -> tuple[G45PaperGaitSegmentDev, ...]:
    if (
        type(session_id) is not str or not session_id
        or any(type(x) is not list for x in (
            transition_acks,original_clear_acks,paper_rows,t2_rows,
        ))
    ):
        raise ValueError("G4.5 refuses invalid joined sources")
    clears={}
    for a in original_clear_acks:
        if (
            not isinstance(a,dict) or a.get("action_id") in clears
            or type(a.get("action_id")) is not str
            or not a["action_id"].startswith("goal-")
            or type(a.get("clear_seq")) is not int
            or type(a.get("s16_seq")) is not int
            or not 0<a["clear_seq"]<a["s16_seq"]
            or a.get("s16_terminal") not in ("outcome","unknown")
        ):
            raise ValueError("G4.5 invalid original CLEAR or S16 provenance")
        clears[a["action_id"]]=a["clear_seq"]
    t2_by_seq={}
    for row in t2_rows:
        if (
            not isinstance(row,dict)
            or type(row.get("source_seq")) is not int
            or type(row.get("world_tick")) is not int
            or row["source_seq"] in t2_by_seq
        ):
            raise ValueError("G4.5 invalid unique original T2 tick source")
        t2_by_seq[row["source_seq"]]=row
    paper_by_seq={}
    for row in paper_rows:
        if (
            not isinstance(row,dict)
            or row.get("session_id")!=session_id
            or type(row.get("source_seq")) is not int
            or type(row.get("world_tick")) is not int
            or row["source_seq"] in paper_by_seq
            or row["source_seq"] not in t2_by_seq
            or t2_by_seq[row["source_seq"]]["world_tick"]!=row["world_tick"]
        ):
            raise ValueError("G4.5 Paper interval lacks same original T2 owner")
        paper_by_seq[row["source_seq"]]=row
    grouped={}
    for ack in transition_acks:
        if (
            not isinstance(ack,dict)
            or ack.get("action_id") not in clears
            or ack.get("parent_s49_issued_action_id")!=ack["action_id"]
            or ack.get("effect")!="g44_gait_transition_dev"
            or ack.get("applied") is not True
            or ack.get("world_tick_gait_attested") is not False
            or ack.get("mode_to") not in _EXPECTED
            or type(ack.get("native_probe_seq")) is not int
            or type(ack.get("ack_seq")) is not int
            or not 0<ack["native_probe_seq"]<ack["ack_seq"]<clears[ack["action_id"]]
        ):
            raise ValueError("G4.5 refuses foreign or unclosed native gait ACK")
        grouped.setdefault(ack["action_id"],[]).append(ack)
    out=[]
    for action,acks in grouped.items():
        if len(acks)>2 or [a["mode_to"] for a in acks] not in (
            ["JOG"],["JOG","WALK"],
        ):
            raise ValueError("G4.5 invalid staged original gait modes")
        for i,ack in enumerate(acks):
            next_seq=(acks[i+1]["ack_seq"] if i+1<len(acks)
                      else clears[action])
            if next_seq<=ack["ack_seq"]:
                raise ValueError("G4.5 native sub-effects out of order")
            matched=[]
            unknown=other=frames=0
            for seq,row in paper_by_seq.items():
                if ack["ack_seq"]<seq<next_seq:
                    frames+=1
                    kind=row["kind"]
                    if kind==_EXPECTED[ack["mode_to"]]:
                        matched.append(row)
                    elif kind.startswith("STABLE_"):
                        other+=1
                    else:
                        unknown+=1
            out.append(G45PaperGaitSegmentDev(
                action_id=action,transition_ack_seq=ack["ack_seq"],
                next_boundary_seq=next_seq,mode_to=ack["mode_to"],
                original_paper_frames=frames,
                initial_or_transition_unknown_frames=unknown,
                stable_matching_candidate_frames=len(matched),
                stable_other_candidate_frames=other,
                stable_matching_world_ticks=tuple(x["world_tick"] for x in matched),
                stable_matching_source_seqs=tuple(x["source_seq"] for x in matched),
                status=("PAPER_STABLE_CANDIDATE_OBSERVED" if matched
                        else "NO_STABLE_FRAME"),
                paper_stable_candidate_seen=bool(matched),
            ))
    return tuple(out)
