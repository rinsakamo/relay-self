"""G4.11 DEV: explain G1 nonstable in-Action frames using existing Paper pairs.

Source-only diagnostics, not an inference that packet cadence caused a
failure. Never change original G49/G410 UNKNOWN or T2/P1/M0 bookkeeping.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass

from adapters.mineflayer.g410_in_action_evidence_quality_dev import (
    join_g410_in_action_evidence_dev,
)


def _digest(row: dict) -> str:
    return hashlib.sha256(json.dumps(
        row, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _controls_equal(left: dict, right: dict) -> bool:
    a, b = left.get("applied_controls"), right.get("applied_controls")
    return type(a) is dict and type(b) is dict and a == b


def _paper_gait_equal(left: dict, right: dict) -> bool:
    a, b = left.get("paper_gait"), right.get("paper_gait")
    if type(a) is not dict or type(b) is not dict:
        return False
    keys = ("sneaking", "sprinting", "speed_modifiers",
            "speed_modifier_details")
    if any(a.get(key) != b.get(key) for key in keys):
        return False
    x, y = a.get("speed_value"), b.get("speed_value")
    return (type(x) in (int, float) and type(y) in (int, float)
            and math.isfinite(x) and math.isfinite(y)
            and math.isclose(x, y, rel_tol=1e-6))


def _node_pair(left: dict, right: dict) -> tuple[bool, bool]:
    a, b = left.get("g46_motor_boundary_dev"), right.get("g46_motor_boundary_dev")
    if type(a) is not dict or type(b) is not dict:
        return False, False
    same_generation = (
        type(a.get("control_generation")) is int
        and type(b.get("control_generation")) is int
        and a["control_generation"] == b["control_generation"]
        and a.get("action_id") == b.get("action_id")
        and a.get("effect_id") == b.get("effect_id")
    )
    same_phase = a.get("control_phase") == b.get("control_phase") == "MOVING"
    return same_generation, same_phase


def _reason(
    kind: str, *, adjacent: bool, has_previous: bool,
    same_generation: bool, same_phase: bool,
    same_controls: bool, same_paper_gait: bool,
) -> str:
    if not has_previous:
        return "NO_PREVIOUS_ORIGINAL_PAPER_FRAME"
    if not adjacent:
        return "NO_ADJACENT_ORIGINAL_PAPER_WORLDTICK"
    if kind == "BLOCKED_OR_STALLED_CONTROL_UNDETERMINED":
        return "G1_NEAR_ZERO_MOTION_WITH_CONTROL_NOT_CAUSAL_BLOCK_PROOF"
    if kind == "MOVING_MODE_UNDETERMINED":
        return "G1_MOVING_MODE_UNDETERMINED"
    if kind == "STABLE_PHYSICAL_IDLE_CANDIDATE":
        return "G1_IDLE_CANDIDATE_INSIDE_ACTION_NOT_WAIT"
    if kind == "TRANSITION_OR_UNDETERMINED":
        if not same_generation or not same_phase:
            return "ADJACENT_NODE_CONTROL_BOUNDARY_DIFFERS"
        if not same_controls:
            return "ADJACENT_NODE_CONTROLS_DIFFER"
        if not same_paper_gait:
            return "ADJACENT_PAPER_GAIT_FACTS_DIFFER"
        return "ADJACENT_PAIR_PRESENT_CAUSE_UNDETERMINED"
    return "OTHER_ORIGINAL_G1_NONSTABLE_KIND"


@dataclass(frozen=True, slots=True)
class G411OriginalG1PairDiagnosticDev:
    session_id: str
    source_seq: int
    world_tick: int
    original_action_id: str
    original_requested_mode: str
    original_g1_kind: str
    original_g410_row_sha256: str
    original_g49_row_sha256: str
    original_t2_row_sha256: str
    previous_paper_seq: int | None
    previous_paper_tick: int | None
    original_paper_seq_gap: int | None
    original_world_tick_gap: int | None
    adjacent_original_paper_worldtick: bool
    same_node_generation: bool
    same_node_phase: bool
    same_node_controls: bool
    same_paper_gait_facts: bool
    original_dxz_m: float | None
    original_motion_blocks_delta: float | None
    original_post_control_challenge: bool
    evidence_class: str
    source: str = "G410_G49_G48_ORIGINAL_G1_ADJACENT_PAPER_PAIR_DIAGNOSTIC_DEV"
    physical_cadence_causality_proven: bool = False
    blocked_collision_proven: bool = False
    packet_to_physics_tick_attested: bool = False
    inferred_wait_or_recovery: bool = False
    unknown_reclassified: bool = False
    p1_or_m0_reposted: bool = False
    second_reader_or_owner_created: bool = False


def join_g411_g1_unstable_pair_census_dev(
    *, session_id: str, g410_rows: list[dict], g49_rows: list[dict],
    g48_rows: list[dict], paper_rows: list[dict], t2_rows: list[dict],
) -> tuple[G411OriginalG1PairDiagnosticDev, ...]:
    # Recompute the exact G410 audit from *unchanged original* receipts.
    expected = [asdict(x) for x in join_g410_in_action_evidence_dev(
        session_id=session_id, g49_rows=g49_rows, g48_rows=g48_rows,
        paper_rows=paper_rows, t2_rows=t2_rows,
    )]
    if (type(g410_rows) is not list or g410_rows != expected
            or not paper_rows):
        raise ValueError("G4.11 original G410/T2/G49 source disagrees")
    ordered = sorted(paper_rows, key=lambda r: r["world_tick"])
    for i, row in enumerate(ordered):
        if (type(row.get("source_seq")) is not int
                or type(row.get("world_tick")) is not int
                or row.get("session_id") != session_id
                or (i and (
                    row["source_seq"] <= ordered[i-1]["source_seq"]
                    or row["world_tick"] <= ordered[i-1]["world_tick"]
                ))):
            raise ValueError("G4.11 original Paper frame order/identity invalid")
    paper_index = {row["source_seq"]: i for i, row in enumerate(ordered)}
    selected = []
    for current in g410_rows:
        if "G1_TWO_SAMPLE_STABLE_KIND" not in current["missing_evidence_axes"]:
            continue
        seq = current["source_seq"]
        if seq not in paper_index:
            raise ValueError("G4.11 selected G410 Paper source missing")
        i = paper_index[seq]
        frame = ordered[i]
        previous = ordered[i-1] if i else None
        seq_gap = (seq-previous["source_seq"] if previous is not None else None)
        tick_gap = (
            frame["world_tick"]-previous["world_tick"]
            if previous is not None else None
        )
        adjacent = tick_gap == 1
        generation, phase = (
            _node_pair(previous, frame)
            if previous is not None and adjacent else (False, False)
        )
        controls = (
            _controls_equal(previous, frame)
            if previous is not None and adjacent else False
        )
        gait = (
            _paper_gait_equal(previous, frame)
            if previous is not None and adjacent else False
        )
        kind = frame["kind"]
        if (kind != current["original_g1_kind"]
                or current["original_active_action"] is None
                or current["g1_two_sample_stable_kind"] != "G1_NOT_STABLE"
                or type(frame.get("g46_challenge_after_control_dev")) is not bool):
            raise ValueError("G4.11 selected UNKNOWN no longer G1 nonstable")
        dxz = frame.get("dxz_m")
        delta = frame.get("paper_motion_blocks_delta")
        if any(x is not None and (
                type(x) not in (int, float) or not math.isfinite(x)
                or x < 0) for x in (dxz, delta)):
            raise ValueError("G4.11 invalid original motion evidence")
        selected.append(G411OriginalG1PairDiagnosticDev(
            session_id=session_id,
            source_seq=seq, world_tick=current["world_tick"],
            original_action_id=current["original_active_action"],
            original_requested_mode=current["original_s49_mode"],
            original_g1_kind=kind,
            original_g410_row_sha256=_digest(current),
            original_g49_row_sha256=current["original_g49_row_sha256"],
            original_t2_row_sha256=current["original_t2_row_sha256"],
            previous_paper_seq=previous["source_seq"] if previous else None,
            previous_paper_tick=previous["world_tick"] if previous else None,
            original_paper_seq_gap=seq_gap, original_world_tick_gap=tick_gap,
            adjacent_original_paper_worldtick=adjacent,
            same_node_generation=generation, same_node_phase=phase,
            same_node_controls=controls, same_paper_gait_facts=gait,
            original_dxz_m=dxz, original_motion_blocks_delta=delta,
            original_post_control_challenge=frame[
                "g46_challenge_after_control_dev"
            ],
            evidence_class=_reason(
                kind, adjacent=adjacent, has_previous=previous is not None,
                same_generation=generation, same_phase=phase,
                same_controls=controls, same_paper_gait=gait,
            ),
        ))
    return tuple(selected)
