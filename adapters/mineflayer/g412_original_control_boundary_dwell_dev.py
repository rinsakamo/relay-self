"""G4.12 DEV: original S49 vs G44 effect-boundary and Paper dwell census.

Only already-admitted original G1/Paper, original native ACK/CLEAR, G49-G411
and T2. An observed generation is neither a physical tick motor input nor
a causal bound on the underlying Node or server change.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from adapters.mineflayer.g49_original_action_gap_census_dev import (
    join_g49_original_action_gap_census_dev,
)
from adapters.mineflayer.g411_g1_unstable_pair_census_dev import (
    join_g411_g1_unstable_pair_census_dev,
)


def _digest(row: dict) -> str:
    return hashlib.sha256(json.dumps(
        row, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _identity(frame: dict) -> tuple | None:
    boundary = frame.get("g46_motor_boundary_dev")
    if type(boundary) is not dict:
        return None
    keys = ("action_id", "effect_id", "requested_mode",
            "control_generation", "control_phase")
    if (any(key not in boundary for key in keys)
            or type(boundary["action_id"]) is not str
            or type(boundary["effect_id"]) is not str
            or boundary["requested_mode"] not in {"SPRINT_INPUT", "JOG", "WALK"}
            or type(boundary["control_generation"]) is not int
            or boundary["control_generation"] < 0
            or boundary["control_phase"] not in {"MOVING", "CLEARED", "INITIAL"}):
        raise ValueError("G4.12 malformed original Node boundary identity")
    return tuple(boundary[key] for key in keys)


@dataclass(frozen=True, slots=True)
class G412OriginalControlBoundaryDwellDev:
    session_id: str
    source_seq: int
    world_tick: int
    original_action_id: str
    original_requested_mode: str
    original_t2_row_sha256: str
    original_g49_row_sha256: str
    original_g411_row_sha256: str
    previous_paper_seq: int | None
    previous_paper_world_tick: int | None
    previous_node_identity: tuple | None
    current_node_identity: tuple | None
    original_action_applied_ack_seq: int
    original_s15_clear_ack_seq: int
    matched_g44_ack_seq: int | None
    original_effect_evidence_class: str
    previous_node_phase: str | None
    original_clear_is_after_selected_frame: bool
    observed_generation_first_tick: int | None
    observed_generation_last_tick: int | None
    observed_generation_worldtick_count: int
    selected_frame_age_within_generation_ticks: int
    observed_following_same_generation_ticks: int
    observed_same_generation_stable_g1_frames: int
    observed_same_generation_post_control_frames: int
    source: str = "G411_G410_G49_ORIGINAL_S49_G44_ACK_PAPER_GENERATION_DWELL_DEV"
    original_unknown_preserved: bool = True
    original_t2_p1_m0_untouched: bool = True
    real_motor_switch_tick_attested: bool = False
    packet_to_physics_tick_attested: bool = False
    physical_input_cadence_causality_proven: bool = False
    inferred_wait_or_recovery: bool = False
    additional_motor_or_reader_created: bool = False


def join_g412_original_control_boundary_dwell_dev(
    *, session_id: str, g411_rows: list[dict], g410_rows: list[dict],
    g49_rows: list[dict], g48_rows: list[dict],
    paper_rows: list[dict], t2_rows: list[dict],
    original_action_acks: list[dict], original_clear_acks: list[dict],
    original_transition_acks: list[dict],
) -> tuple[G412OriginalControlBoundaryDwellDev, ...]:
    # Both immutable upstream audits must be reproducible, byte-for-byte
    # at the serialized row level, from the original G1/Paper and T2.
    checked_g411 = [asdict(item) for item in
        join_g411_g1_unstable_pair_census_dev(
            session_id=session_id, g410_rows=g410_rows, g49_rows=g49_rows,
            g48_rows=g48_rows, paper_rows=paper_rows, t2_rows=t2_rows,
        )]
    if (type(g411_rows) is not list or g411_rows != checked_g411
            or type(original_transition_acks) is not list):
        raise ValueError("G4.12 original G411 input or transition source altered")
    checked_g49 = [asdict(item) for item in
        join_g49_original_action_gap_census_dev(
            session_id=session_id, original_action_acks=original_action_acks,
            original_clear_acks=original_clear_acks, paper_rows=paper_rows,
            t2_rows=t2_rows, g48_rows=g48_rows,
        )]
    if checked_g49 != g49_rows:
        raise ValueError("G4.12 original S49/G49 ACK/CLEAR source mismatch")
    original_acks = {ack["action_id"]: ack for ack in original_action_acks}
    original_clears = {ack["action_id"]: ack for ack in original_clear_acks}
    transitions: dict[str, dict] = {}
    for ack in original_transition_acks:
        if (
            type(ack) is not dict
            or ack.get("effect") != "g44_gait_transition_dev"
            or ack.get("applied") is not True
            or ack.get("world_tick_gait_attested") is not False
            or ack.get("mode_to") not in {"JOG", "WALK"}
            or type(ack.get("action_id")) is not str
            or ack.get("parent_s49_issued_action_id") != ack["action_id"]
            or ack["action_id"] not in original_acks
            or type(ack.get("transition_effect_id")) is not str
            or ack["transition_effect_id"] in transitions
            or type(ack.get("native_probe_seq")) is not int
            or type(ack.get("ack_seq")) is not int
            or not (0 < ack["native_probe_seq"] < ack["ack_seq"]
                    < original_clears[ack["action_id"]]["clear_seq"])
            or not ack["transition_effect_id"].startswith(
                ack["action_id"] + "-g44-"
            )
        ):
            raise ValueError("G4.12 invalid original G44 native ACK")
        transitions[ack["transition_effect_id"]] = ack
    frames = sorted(paper_rows, key=lambda row: row["world_tick"])
    frame_by_seq = {frame["source_seq"]: i for i, frame in enumerate(frames)}
    if len(frame_by_seq) != len(frames):
        raise ValueError("G4.12 duplicate original Paper frame")
    result = []
    for row in g411_rows:
        if row["evidence_class"] != "ADJACENT_NODE_CONTROL_BOUNDARY_DIFFERS":
            continue
        seq = row["source_seq"]
        i = frame_by_seq.get(seq)
        if i is None:
            raise ValueError("G4.12 selected original G411 source missing")
        frame = frames[i]
        prior = frames[i-1] if i else None
        if (prior is None
                or frame["world_tick"] - prior["world_tick"] != 1
                or row["previous_paper_seq"] != prior["source_seq"]
                or row["previous_paper_tick"] != prior["world_tick"]
                or not row["adjacent_original_paper_worldtick"]):
            raise ValueError("G4.12 lost original adjacent G411 boundary")
        action_id = row["original_action_id"]
        native_ack = original_acks.get(action_id)
        clear_ack = original_clears.get(action_id)
        if native_ack is None or clear_ack is None or not (
            native_ack["ack_seq"] < seq < clear_ack["clear_seq"]
        ):
            raise ValueError("G4.12 selected original S49 window not proven")
        curr_id, prev_id = _identity(frame), _identity(prior)
        if curr_id == prev_id and curr_id is not None:
            raise ValueError("G4.12 selected G411 changed boundary is identical")
        matched_ack = None
        classification = "UNKNOWN_UNCORRELATED_NODE_BOUNDARY"
        if curr_id is not None and curr_id[0] == action_id and curr_id[4] == "MOVING":
            if curr_id[1] == action_id and native_ack["ack_seq"] < seq:
                classification = "ORIGINAL_S49_APPLIED_EFFECT_OBSERVED"
            elif curr_id[1] in transitions:
                candidate = transitions[curr_id[1]]
                if (candidate["action_id"] != action_id
                        or candidate["ack_seq"] >= seq
                        or curr_id[2] != candidate["mode_to"]):
                    raise ValueError("G4.12 mixed original G44 effect/ACK generation")
                matched_ack = candidate["ack_seq"]
                classification = "G44_SAME_S49_ACTION_SUBEFFECT_OBSERVED"
        # A selected sample is strictly within the ACK->CLEAR bracket.
        # An original CLEAR cannot be credited at that WorldTick.
        if curr_id is not None:
            # Count the contiguous ORIGINAL captured Paper rows that preserve
            # this exact Node effect+generation+phase inside this one action.
            lo = hi = i
            while lo > 0:
                p = frames[lo-1]
                if (p["world_tick"] != frames[lo]["world_tick"] - 1
                        or p["source_seq"] <= native_ack["ack_seq"]
                        or p["source_seq"] >= clear_ack["clear_seq"]
                        or _identity(p) != curr_id):
                    break
                lo -= 1
            while hi + 1 < len(frames):
                nxt = frames[hi+1]
                if (nxt["world_tick"] != frames[hi]["world_tick"] + 1
                        or nxt["source_seq"] >= clear_ack["clear_seq"]
                        or nxt["source_seq"] <= native_ack["ack_seq"]
                        or _identity(nxt) != curr_id):
                    break
                hi += 1
            cohort = frames[lo:hi+1]
            first = frames[lo]["world_tick"]
            last = frames[hi]["world_tick"]
            stable = sum(f["kind"].startswith("STABLE_")
                         and f["kind"].endswith("_CANDIDATE") for f in cohort)
            challenge = sum(f.get("g46_challenge_after_control_dev") is True
                            for f in cohort)
            age = i - lo + 1
            count = len(cohort)
            follow = hi - i
        else:
            first = last = None
            stable = challenge = age = count = follow = 0
        result.append(G412OriginalControlBoundaryDwellDev(
            session_id=session_id, source_seq=seq, world_tick=row["world_tick"],
            original_action_id=action_id,
            original_requested_mode=row["original_requested_mode"],
            original_t2_row_sha256=row["original_t2_row_sha256"],
            original_g49_row_sha256=row["original_g49_row_sha256"],
            original_g411_row_sha256=_digest(row),
            previous_paper_seq=prior["source_seq"],
            previous_paper_world_tick=prior["world_tick"],
            previous_node_identity=prev_id, current_node_identity=curr_id,
            original_action_applied_ack_seq=native_ack["ack_seq"],
            original_s15_clear_ack_seq=clear_ack["clear_seq"],
            matched_g44_ack_seq=matched_ack,
            original_effect_evidence_class=classification,
            previous_node_phase=prev_id[4] if prev_id is not None else None,
            original_clear_is_after_selected_frame=True,
            observed_generation_first_tick=first,
            observed_generation_last_tick=last,
            observed_generation_worldtick_count=count,
            selected_frame_age_within_generation_ticks=age,
            observed_following_same_generation_ticks=follow,
            observed_same_generation_stable_g1_frames=stable,
            observed_same_generation_post_control_frames=challenge,
        ))
    return tuple(result)
