"""G4.9 DEV read-only census of why original T2 WorldTicks remain UNKNOWN.

One Original S49 Action dispatch ACK / S15 CLEAR bracket, original G1 Paper
sample, and existing immutable G47/G48 audits. No physical gait inference,
Action issuance, extra reader, synthetic P1/M0 debit, or change to T2.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

_EXPECTED_EFFECT = {
    "DASH": "set_forward_sprint_dev",
    "RUN": "set_forward_sprint_dev",
    "JOG": "set_control",
    "WALK": "set_forward_sneak_dev",
}
_STABLE = frozenset({
    "G47_STABLE_CANDIDATE_UNCHANGED",
    "DIRECT_SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV",
})


@dataclass(frozen=True, slots=True)
class G49OriginalActionTickGapDev:
    session_id: str
    source_seq: int
    world_tick: int
    original_t2_row_sha256: str
    original_g48_row_sha256: str
    original_active_action: str | None
    original_paper_g1_kind: str
    original_node_control_phase: str
    original_g48_status: str
    original_s49_requested_mode: str | None
    original_s49_applied_ack_seq: int | None
    original_s15_clear_ack_seq: int | None
    original_s49_effect: str | None
    source_gap_class: str
    still_unknown: bool
    source: str = "ORIGINAL_S49_APPLIED_ACK_S15_CLEAR_G1_G48_T2_G49_DEV"
    physics_tick_motor_attested: bool = False
    original_t2_p1_m0_reposted: bool = False
    additional_readers_or_t2_owners: int = 0


def join_g49_original_action_gap_census_dev(
    *, session_id: str, original_action_acks: list[dict],
    original_clear_acks: list[dict], paper_rows: list[dict],
    t2_rows: list[dict], g48_rows: list[dict],
) -> tuple[G49OriginalActionTickGapDev, ...]:
    if (
        type(session_id) is not str or not session_id
        or any(type(x) is not list for x in (
            original_action_acks, original_clear_acks, paper_rows,
            t2_rows, g48_rows,
        ))
        or not t2_rows or len(t2_rows) != len(g48_rows)
    ):
        raise ValueError("G4.9 absent original session or aligned original T2")
    clears = {}
    for item in original_clear_acks:
        if (
            type(item) is not dict
            or type(item.get("action_id")) is not str
            or item["action_id"] in clears
            or type(item.get("clear_seq")) is not int
            or type(item.get("s16_seq")) is not int
            or not 0 < item["clear_seq"] < item["s16_seq"]
            or item.get("s16_terminal") not in {"outcome", "unknown"}
        ):
            raise ValueError("G4.9 invalid original S15 clear")
        clears[item["action_id"]] = item
    acks = {}
    for item in original_action_acks:
        if (
            type(item) is not dict
            or set(item) != {
                "action_id", "effect_id", "effect", "ack_seq",
                "requested_mode", "source", "requested_not_paper_gait",
            }
            or type(item.get("action_id")) is not str
            or not item["action_id"].startswith("goal-")
            or item["action_id"] in acks
            or item["action_id"] not in clears
            or item.get("effect_id") != item["action_id"]
            or item.get("requested_mode") not in _EXPECTED_EFFECT
            or item.get("effect") != _EXPECTED_EFFECT[item["requested_mode"]]
            or item.get("source") != "ORIGINAL_S49_NATIVE_APPLIED"
            or item.get("requested_not_paper_gait") is not True
            or type(item.get("ack_seq")) is not int
            or not 0 < item["ack_seq"] < clears[item["action_id"]]["clear_seq"]
        ):
            raise ValueError("G4.9 foreign original Action effect ACK")
        acks[item["action_id"]] = item
    if len(acks) != len(original_clear_acks):
        # Terminal UNKNOWN may occur *after* motor APPLIED, but cannot invent
        # a dispatch without proof. If unacknowledged, refuse this census.
        raise ValueError("G4.9 original S49 dispatch/clear owner mismatch")
    paper = {}
    for item in paper_rows:
        if (
            type(item) is not dict
            or item.get("session_id") != session_id
            or type(item.get("source_seq")) is not int
            or item["source_seq"] in paper
        ):
            raise ValueError("G4.9 duplicated or foreign original Paper frame")
        paper[item["source_seq"]] = item
    out = []
    previous_seq = -1
    previous_tick = -1
    for original, old in zip(t2_rows, g48_rows):
        seq = original.get("source_seq")
        tick = original.get("world_tick")
        if (
            type(original) is not dict or type(old) is not dict
            or original.get("session_id") != session_id
            or old.get("session_id") != session_id
            or type(seq) is not int or type(tick) is not int
            or seq <= previous_seq
            or (previous_tick >= 0 and tick != previous_tick + 1)
            or old.get("source_seq") != seq or old.get("world_tick") != tick
            or old.get("original_t2_row_sha256") != hashlib.sha256(
                json.dumps(original, sort_keys=True, separators=(",",":")).encode(),
            ).hexdigest()
            or old.get("original_t2_applied_gait") != original.get("applied_gait")
            or seq not in paper or paper[seq].get("world_tick") != tick
            or paper[seq].get("kind") != old.get("original_g1_kind")
        ):
            raise ValueError("G4.9 altered original T2/G48/Paper source")
        previous_seq, previous_tick = seq, tick
        g1 = paper[seq]
        node = g1.get("g46_motor_boundary_dev")
        if (
            type(node) is not dict
            or node.get("control_phase") not in {"INITIAL", "MOVING", "CLEARED"}
            or type(node.get("control_generation")) is not int
        ):
            raise ValueError("G4.9 missing original Node control phase")
        action = original.get("active_action")
        if action is not None and (type(action) is not str
                                   or not action.startswith("goal-")):
            raise ValueError("G4.9 unrecognized original T2 Action scope")
        matching_windows = [
            a for a in acks.values()
            if a["ack_seq"] < seq < clears[a["action_id"]]["clear_seq"]
        ]
        if len(matching_windows) > 1:
            raise ValueError("G4.9 overlapping original Action ACK/CLEAR windows")
        active_ack = acks.get(action)
        native_window = matching_windows[0] if matching_windows else None
        stable = old.get("status") in _STABLE
        if stable:
            if (active_ack is None or native_window != active_ack
                    or old.get("original_action_id") not in (None, action)):
                raise ValueError("G4.9 stable candidate outside original applied Action")
            gap = "EXISTING_SOURCE_BOUND_STABLE_CANDIDATE"
        elif native_window is not None and action is None:
            gap = "UNKNOWN_T2_UNBOUND_INSIDE_NATIVE_ACTION"
        elif action is None:
            gap = "UNKNOWN_NO_T2_ACTIVE_ACTION"
        elif active_ack is None:
            gap = "UNKNOWN_ACTIVE_ACTION_LACKS_TYPED_ACK"
        elif seq <= active_ack["ack_seq"]:
            gap = "UNKNOWN_PRE_ACTION_APPLIED_ACK"
        elif seq >= clears[action]["clear_seq"]:
            gap = "UNKNOWN_AFTER_ORIGINAL_CLEAR"
        elif native_window != active_ack:
            gap = "UNKNOWN_S49_EFFECT_SOURCE_MISMATCH"
        else:
            gap = "UNKNOWN_INSIDE_APPLIED_" + active_ack["requested_mode"] + "_ACTION"
        if (old.get("status") == "G47_STABLE_CANDIDATE_UNCHANGED"
                and old.get("original_action_id") is not None):
            raise ValueError("G4.9 modified historical G47 identity")
        out.append(G49OriginalActionTickGapDev(
            session_id=session_id, source_seq=seq, world_tick=tick,
            original_t2_row_sha256=old["original_t2_row_sha256"],
            original_g48_row_sha256=hashlib.sha256(
                json.dumps(old, sort_keys=True, separators=(",",":")).encode(),
            ).hexdigest(),
            original_active_action=action,
            original_paper_g1_kind=g1["kind"],
            original_node_control_phase=node["control_phase"],
            original_g48_status=old["status"],
            original_s49_requested_mode=active_ack["requested_mode"] if active_ack else None,
            original_s49_applied_ack_seq=active_ack["ack_seq"] if active_ack else None,
            original_s15_clear_ack_seq=(
                clears[action]["clear_seq"] if action in clears else None
            ),
            original_s49_effect=active_ack["effect"] if active_ack else None,
            source_gap_class=gap,
            still_unknown=not stable,
        ))
    return tuple(out)
