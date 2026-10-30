"""G4.10 DEV-only read-only evidence quality of G4.9 in-Action UNKNOWN.

Never reinterpret original G48/G49 classification, perform motor I/O, infer
physical WAIT, or post to the original T2/P1/M0 ledgers. Each selected row
is a diagnostic of existing original S49/T1u/G1/T2 evidence, not physics
tick attestation.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

_IN_ACTION = {
    "DASH": "UNKNOWN_INSIDE_APPLIED_DASH_ACTION",
    "RUN": "UNKNOWN_INSIDE_APPLIED_RUN_ACTION",
    "JOG": "UNKNOWN_INSIDE_APPLIED_JOG_ACTION",
    "WALK": "UNKNOWN_INSIDE_APPLIED_WALK_ACTION",
}
_G1_STABLE = {
    "STABLE_DASH_MODIFIER_FORWARD_CANDIDATE",
    "STABLE_SPRINT_FORWARD_CANDIDATE",
    "STABLE_ORDINARY_FORWARD_CANDIDATE",
    "STABLE_SNEAK_FORWARD_CANDIDATE",
}
_DASH_KEYS = {
    "minecraft:sprinting": 0.3,
    "relays49dashdev:forward_dash_only": 0.5,
}


def _digest(row: dict) -> str:
    return hashlib.sha256(json.dumps(
        row, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _dash_modifier_identity(gait: object) -> str:
    if type(gait) is not dict:
        return "DASH_PAPER_DETAILS_UNAVAILABLE"
    mods = gait.get("speed_modifier_details")
    if type(mods) is not list or len(mods) != 2:
        return "DASH_PAPER_DETAILS_UNAVAILABLE"
    try:
        by_key = {m["key"]: m for m in mods if type(m) is dict}
        if len(by_key) != 2 or set(by_key) != set(_DASH_KEYS):
            return "DASH_PAPER_EXACT_ID_MISMATCH"
        if (gait.get("speed_modifiers") != 2
                or not math.isclose(gait["speed_base"], 0.1, abs_tol=1e-6)
                or not math.isclose(gait["speed_value"], 0.195, abs_tol=1e-5)):
            return "DASH_PAPER_EXACT_ID_MISMATCH"
        for key, amount in _DASH_KEYS.items():
            mod = by_key[key]
            if (mod.get("operation") != "MULTIPLY_SCALAR_1"
                    or type(mod.get("amount")) not in (int, float)
                    or not math.isfinite(mod["amount"])
                    or not math.isclose(mod["amount"], amount, abs_tol=1e-6)):
                return "DASH_PAPER_EXACT_ID_MISMATCH"
        return "DASH_PAPER_EXACT_ID_PRESENT_SINGLE_FRAME"
    except (KeyError, TypeError, ValueError, OverflowError):
        return "DASH_PAPER_EXACT_ID_MISMATCH"


@dataclass(frozen=True, slots=True)
class G410InActionEvidenceQualityDev:
    session_id: str
    source_seq: int
    world_tick: int
    original_active_action: str
    original_s49_mode: str
    original_t2_row_sha256: str
    original_g48_row_sha256: str
    original_g49_row_sha256: str
    original_g48_status: str
    original_g1_kind: str
    node_mode: str | None
    node_effect_generation: str
    post_control_challenge: str
    g1_two_sample_stable_kind: str
    paper_modifier_identity: str
    original_t2_applied_gait: str | None
    g3_dash_debit_evidence: str
    missing_evidence_axes: tuple[str, ...]
    source: str = "G49_ORIGINAL_IN_ACTION_UNKNOWN_G48_G1_PAPER_T2_G410_READ_ONLY"
    remains_unknown: bool = True
    full_physics_tick_gait_attested: bool = False
    physical_wait_or_idle_inferred: bool = False
    new_p1_or_m0_posting: bool = False
    additional_native_readers_or_t2_owners: int = 0


def join_g410_in_action_evidence_dev(
    *, session_id: str, g49_rows: list[dict], g48_rows: list[dict],
    paper_rows: list[dict], t2_rows: list[dict],
) -> tuple[G410InActionEvidenceQualityDev, ...]:
    if (type(session_id) is not str or not session_id
            or any(type(rows) is not list for rows in (
                g49_rows, g48_rows, paper_rows, t2_rows,
            ))
            or not t2_rows
            or len(g49_rows) != len(g48_rows) != len(t2_rows)):
        raise ValueError("G4.10 missing original aligned source rows")
    if len(g49_rows) != len(g48_rows) or len(g49_rows) != len(t2_rows):
        raise ValueError("G4.10 incomplete original per-tick census")
    paper = {}
    for frame in paper_rows:
        if (type(frame) is not dict
                or frame.get("session_id") != session_id
                or type(frame.get("source_seq")) is not int
                or frame["source_seq"] in paper):
            raise ValueError("G4.10 foreign/duplicate original Paper source")
        paper[frame["source_seq"]] = frame
    result = []
    previous_seq = -1
    previous_tick = -1
    for g49, g48, t2 in zip(g49_rows, g48_rows, t2_rows):
        if any(type(row) is not dict for row in (g49, g48, t2)):
            raise ValueError("G4.10 malformed source")
        seq = t2.get("source_seq")
        tick = t2.get("world_tick")
        if (any(row.get("session_id") != session_id for row in (g49, g48, t2))
                or type(seq) is not int or type(tick) is not int
                or seq <= previous_seq
                or (previous_tick >= 0 and tick != previous_tick + 1)
                or any(row.get("source_seq") != seq or row.get("world_tick") != tick
                       for row in (g49, g48))
                or g49.get("original_t2_row_sha256") != _digest(t2)
                or g48.get("original_t2_row_sha256") != _digest(t2)
                or g49.get("original_g48_row_sha256") != _digest(g48)
                or g49.get("original_g48_status") != g48.get("status")
                or g49.get("original_active_action") != t2.get("active_action")
                or g48.get("original_t2_applied_gait") != t2.get("applied_gait")
                or seq not in paper or paper[seq].get("world_tick") != tick
                or g49.get("original_paper_g1_kind") != paper[seq].get("kind")
                or g48.get("original_g1_kind") != paper[seq].get("kind")
                or g49.get("still_unknown") is not (
                    g48.get("status") not in {
                        "G47_STABLE_CANDIDATE_UNCHANGED",
                        "DIRECT_SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV",
                    }
                )):
            raise ValueError("G4.10 mismatched original G49/G48/T2/G1 SHA or identity")
        previous_seq, previous_tick = seq, tick
        gap = g49.get("source_gap_class")
        if gap not in _IN_ACTION.values():
            continue
        mode = g49.get("original_s49_requested_mode")
        action = t2.get("active_action")
        ack = g49.get("original_s49_applied_ack_seq")
        clear = g49.get("original_s15_clear_ack_seq")
        if (mode not in _IN_ACTION or gap != _IN_ACTION[mode]
                or type(action) is not str or not action.startswith("goal-")
                or type(ack) is not int or type(clear) is not int
                or not 0 < ack < seq < clear
                or g49.get("still_unknown") is not True):
            raise ValueError("G4.10 forged original in-Action unknown bracket")
        frame = paper[seq]
        boundary = frame.get("g46_motor_boundary_dev")
        node_ok = (
            type(boundary) is dict
            and boundary.get("action_id") == action
            and type(boundary.get("effect_id")) is str
            and boundary.get("control_phase") == "MOVING"
            and type(boundary.get("control_generation")) is int
            and boundary["control_generation"] > 0
            and boundary.get("requested_mode") in {"SPRINT_INPUT", "JOG", "WALK"}
        )
        # A RUN parent Action can have G44 JOG/WALK subeffects. Do not
        # demand the parent Action's gait from the Paper callback.
        node_mode = boundary.get("requested_mode") if node_ok else None
        challenge = frame.get("g46_challenge_after_control_dev") is True
        stable_kind = frame["kind"] in _G1_STABLE
        modifier = (_dash_modifier_identity(frame.get("paper_gait"))
                    if mode == "DASH" else "NOT_APPLICABLE_TO_PARENT_MODE")
        original_gait = t2.get("applied_gait")
        debit = t2.get("g3_extra_m0_paid_dev")
        if (type(debit) not in (int, float) or not math.isfinite(debit)
                or debit < 0 or (debit > 0 and original_gait != "DASH")):
            raise ValueError("G4.10 foreign or contradictory original G3 debit")
        dash_debit = (
            "NOT_APPLICABLE_TO_PARENT_MODE" if mode != "DASH"
            else "ORIGINAL_G3_DASH_DEBIT_PRESENT" if debit > 0
            else "ORIGINAL_G3_NO_DASH_DEBIT"
        )
        missing = []
        if not node_ok:
            missing.append("NODE_EFFECT_GENERATION")
        if not challenge:
            missing.append("POST_CONTROL_CHALLENGE")
        if not stable_kind:
            missing.append("G1_TWO_SAMPLE_STABLE_KIND")
        if mode == "DASH" and modifier != "DASH_PAPER_EXACT_ID_PRESENT_SINGLE_FRAME":
            missing.append("DASH_PAPER_EXACT_MODIFIER_IDENTITY")
        if original_gait is None or t2.get("g3_unknown_fallback_dev") is True:
            missing.append("ORIGINAL_T2_APPLIED_GAIT")
        if mode == "DASH" and debit == 0:
            missing.append("ORIGINAL_G3_DASH_DEBIT_PROOF")
        result.append(G410InActionEvidenceQualityDev(
            session_id=session_id, source_seq=seq, world_tick=tick,
            original_active_action=action, original_s49_mode=mode,
            original_t2_row_sha256=g49["original_t2_row_sha256"],
            original_g48_row_sha256=g49["original_g48_row_sha256"],
            original_g49_row_sha256=_digest(g49),
            original_g48_status=g48["status"], original_g1_kind=frame["kind"],
            node_mode=node_mode,
            node_effect_generation="MATCHED_NODE_GENERATION" if node_ok
            else "NO_MATCHED_NODE_GENERATION",
            post_control_challenge="AFTER_CONTROL" if challenge
            else "NO_POST_CONTROL_CHALLENGE",
            g1_two_sample_stable_kind="G1_RECORDED_STABLE_KIND" if stable_kind
            else "G1_NOT_STABLE",
            paper_modifier_identity=modifier,
            original_t2_applied_gait=original_gait,
            g3_dash_debit_evidence=dash_debit,
            missing_evidence_axes=tuple(missing),
        ))
    return tuple(result)
