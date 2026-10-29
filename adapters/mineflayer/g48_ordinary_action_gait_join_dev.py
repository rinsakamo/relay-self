"""G4.8 DEV: source-correlate original ordinary JOG/WALK S49 Actions.

Pure read-only overlay on G4.7 already-accounted original T2/P1/M0 ticks.
The original G4.7 staged RUN->JOG->WALK results are preserved without change.
Outside those staged windows, one original ordinary S49 APPLIED ACK binds a
single original Node control generation and independently sourced G1/T2 Paper
WorldTick. Missing/late/contradictory evidence remains UNKNOWN.
"""
from __future__ import annotations

from dataclasses import replace

from adapters.mineflayer.g47_original_t2_gait_join_dev import (
    G47OriginalT2WorldTickJoinDev,
    join_g47_original_t2_worldticks_dev,
)

_ORDINARY = {
    "JOG": ("JOG_ACTION", "set_control",
            "STABLE_ORDINARY_FORWARD_CANDIDATE"),
    "WALK": ("WALK_ACTION", "set_forward_sneak_dev",
             "STABLE_SNEAK_FORWARD_CANDIDATE"),
}


def join_g48_ordinary_action_gait_dev(
    *, session_id: str, original_run_acks: list[dict],
    original_ordinary_acks: list[dict],
    transition_acks: list[dict], original_clear_acks: list[dict],
    paper_rows: list[dict], t2_rows: list[dict],
) -> tuple[G47OriginalT2WorldTickJoinDev, ...]:
    base = join_g47_original_t2_worldticks_dev(
        session_id=session_id, original_run_acks=original_run_acks,
        transition_acks=transition_acks,
        original_clear_acks=original_clear_acks,
        paper_rows=paper_rows, t2_rows=t2_rows,
    )
    if type(original_ordinary_acks) is not list:
        raise ValueError("G4.8 invalid original ordinary ACK collection")
    clears = {}
    for c in original_clear_acks:
        if c["action_id"] in clears:
            raise ValueError("G4.8 duplicate original CLEAR")
        clears[c["action_id"]] = c["clear_seq"]
    windows = []
    seen = set()
    for ack in original_ordinary_acks:
        if type(ack) is not dict or set(ack) != {
            "action_id", "effect_id", "ack_seq", "effect",
            "requested_mode", "requested_not_paper_gait", "source",
        }:
            raise ValueError("G4.8 malformed original ordinary ACK")
        action = ack["action_id"]
        mode = ack["requested_mode"]
        if (
            type(action) is not str or not action.startswith("goal-")
            or action in seen or action not in clears or mode not in _ORDINARY
            or ack["effect_id"] != action
            or ack["effect"] != _ORDINARY[mode][1]
            or type(ack["ack_seq"]) is not int
            or not 0 < ack["ack_seq"] < clears[action]
            or ack["requested_not_paper_gait"] is not True
            or ack["source"] != "ORIGINAL_S49_NATIVE_APPLIED"
            or any(a["action_id"] == action for a in original_run_acks)
            or any(a["action_id"] == action for a in transition_acks)
        ):
            raise ValueError("G4.8 foreign/duplicated/mismatched ordinary Action")
        seen.add(action)
        windows.append((ack["ack_seq"], clears[action], action, mode))
    g1 = {p["source_seq"]: p for p in paper_rows}
    result = []
    for r in base:
        matches = [
            (action, mode) for lo, hi, action, mode in windows
            if lo < r.source_seq < hi
        ]
        if len(matches) > 1:
            raise ValueError("G4.8 overlapping original Action intervals")
        if not matches:
            result.append(r)
            continue
        action, mode = matches[0]
        if r.status != "UNKNOWN_NO_ORIGINAL_G46_EFFECT_WINDOW":
            raise ValueError("G4.8 cannot overwrite original staged G4.7 gait")
        p = g1[r.source_seq]
        b = p.get("g46_motor_boundary_dev")
        status = "UNKNOWN_ORDINARY_ACTION_NOT_ORIGINAL_T2_ACTIVE"
        generation = None
        after = False
        if r.original_active_action == action:
            if not isinstance(b, dict):
                status = "UNKNOWN_ORDINARY_CONTROL_GENERATION_MISSING"
            elif (
                b.get("action_id") != action
                or b.get("effect_id") != action
                or b.get("requested_mode") != _ORDINARY[mode][0]
                or b.get("control_phase") != "MOVING"
                or b.get("transition_index") != 0
                or type(b.get("control_generation")) is not int
                or b["control_generation"] <= 0
            ):
                status = "UNKNOWN_ORDINARY_CONTROL_BOUNDARY"
            else:
                generation = b["control_generation"]
                after = p.get("g46_challenge_after_control_dev") is True
                if not after:
                    status = "UNKNOWN_PRECHANGE_CHALLENGE"
                elif p["kind"] != _ORDINARY[mode][2]:
                    status = "UNKNOWN_UNSTABLE_PAPER_GAIT"
                elif r.original_t2_applied_gait != mode or r.original_g3_unknown_fallback:
                    status = "UNKNOWN_ORIGINAL_T2_GAIT_FALLBACK"
                elif r.original_g3_extra_m0_paid != 0:
                    raise ValueError("G4.8 ordinary Action has extra M0 charge")
                else:
                    status = "SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV"
        result.append(replace(
            r, native_effect_id=action,
            requested_input_mode=_ORDINARY[mode][0],
            node_control_generation=generation,
            postchange_challenge_observed=after,
            status=status,
            source="ORIGINAL_S49_ORDINARY_ACTION_G46_G1_PAPER_T2_P1_M0_DEV",
        ))
    if len(result) != len(t2_rows):
        raise ValueError("G4.8 one original T2 row per output required")
    return tuple(result)
