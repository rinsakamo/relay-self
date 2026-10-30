"""G4.13 read-only G1 witness placement within original G412 Paper dwell.

Never change G1 gait status, infer packet-to-physics acceptance, lengthen
controls, or award WAIT/P1/M0 credit. Reproduce G412 from original receipts.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from adapters.mineflayer.g412_original_control_boundary_dwell_dev import (
    _identity,
    join_g412_original_control_boundary_dwell_dev,
)


def _digest(row: dict) -> str:
    return hashlib.sha256(json.dumps(
        row, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


_STABLE = {
    "STABLE_DASH_MODIFIER_FORWARD_CANDIDATE",
    "STABLE_SPRINT_FORWARD_CANDIDATE",
    "STABLE_ORDINARY_FORWARD_CANDIDATE",
    "STABLE_SNEAK_FORWARD_CANDIDATE",
}


@dataclass(frozen=True, slots=True)
class G413OriginalG1GenerationWitnessDev:
    session_id: str
    source_seq: int
    world_tick: int
    original_action_id: str
    original_effect_evidence_class: str
    original_g412_row_sha256: str
    original_g411_row_sha256: str
    original_g49_row_sha256: str
    original_t2_row_sha256: str
    original_generation_first_tick: int | None
    original_generation_last_tick: int | None
    original_generation_paper_worldticks: int
    original_generation_paper_frame_sha256: tuple[str, ...]
    original_generation_g1_kinds: tuple[str, ...]
    original_generation_post_control_challenges: tuple[bool, ...]
    original_generation_stable_source_seqs: tuple[int, ...]
    original_generation_post_control_source_seqs: tuple[int, ...]
    selected_frame_original_g1_kind: str
    selected_frame_post_control_challenge: bool
    stable_candidate_worldticks: int
    post_control_challenge_worldticks: int
    stable_with_post_control_challenge_worldticks: int
    first_stable_kind_worldtick_offset: int | None
    first_post_control_challenge_worldtick_offset: int | None
    first_stable_with_post_control_worldtick_offset: int | None
    evidence_class: str
    source: str = "G412_ORIGINAL_G1_STABLE_CHALLENGE_GENERATION_WITNESS_DEV"
    original_unknown_unchanged: bool = True
    original_g1_classification_unchanged: bool = True
    original_t2_p1_m0_untouched: bool = True
    physics_tick_packet_acceptance_attested: bool = False
    real_motor_latency_inferred: bool = False
    physical_wait_inferred: bool = False
    extra_motor_or_reader: bool = False


def _classify(*, count: int, stable: int, after: int, both: int) -> str:
    if count < 1:
        return "NO_BOUNDED_ORIGINAL_PAPER_GENERATION"
    if both:
        return "ORIGINAL_G1_STABLE_KIND_AND_POST_CONTROL_PRESENT_NOT_CAUSAL_GAIT"
    if stable and not after:
        return "ORIGINAL_G1_STABLE_KIND_BUT_NO_POST_CONTROL_CHALLENGE"
    if stable and after:
        return "ORIGINAL_G1_STABLE_AND_CHALLENGE_ON_SEPARATE_FRAMES"
    if stable:
        return "ORIGINAL_G1_STABLE_KIND_WITHOUT_CHALLENGE"
    if count == 1:
        return "ONLY_ONE_ORIGINAL_PAPER_GENERATION_FRAME"
    if after:
        return "MULTIPLE_FRAMES_WITH_CHALLENGE_G1_REMAINS_NONSTABLE"
    return "MULTIPLE_FRAMES_NO_STABLE_G1_OR_POST_CONTROL_CHALLENGE"


def join_g413_original_g1_generation_witness_dev(
    *, session_id: str, g412_rows: list[dict], g411_rows: list[dict],
    g410_rows: list[dict], g49_rows: list[dict], g48_rows: list[dict],
    paper_rows: list[dict], t2_rows: list[dict],
    original_action_acks: list[dict], original_clear_acks: list[dict],
    original_transition_acks: list[dict],
) -> tuple[G413OriginalG1GenerationWitnessDev, ...]:
    verified = [asdict(row) for row in
                join_g412_original_control_boundary_dwell_dev(
                    session_id=session_id, g411_rows=g411_rows,
                    g410_rows=g410_rows, g49_rows=g49_rows,
                    g48_rows=g48_rows, paper_rows=paper_rows,
                    t2_rows=t2_rows, original_action_acks=original_action_acks,
                    original_clear_acks=original_clear_acks,
                    original_transition_acks=original_transition_acks,
                )]
    if type(g412_rows) is not list or g412_rows != verified:
        raise ValueError("G4.13 source G412 audit differs from originals")
    frames = sorted(paper_rows, key=lambda f: f["world_tick"])
    by_tick = {f["world_tick"]: f for f in frames}
    if len(by_tick) != len(frames):
        raise ValueError("G4.13 duplicated original Paper WorldTick")
    out = []
    for row in g412_rows:
        first, last = (
            row["observed_generation_first_tick"],
            row["observed_generation_last_tick"],
        )
        if first is None or last is None:
            cohort = []
        else:
            if (type(first) is not int or type(last) is not int
                    or first > last):
                raise ValueError("G4.13 nonmonotone source generation")
            cohort = [by_tick.get(tick) for tick in range(first, last + 1)]
            if any(frame is None for frame in cohort):
                raise ValueError("G4.13 missing original Paper generation tick")
        if (
            len(cohort) != row["observed_generation_worldtick_count"]
            or len(cohort) != (last - first + 1 if first is not None else 0)
            or any(frame["session_id"] != session_id
                   or _identity(frame) != row["current_node_identity"]
                   for frame in cohort)
            or (cohort and row["source_seq"] not in
                [frame["source_seq"] for frame in cohort])
        ):
            raise ValueError("G4.13 original G412 generation was rewritten")
        kinds = tuple(frame["kind"] for frame in cohort)
        challenges = tuple(
            frame.get("g46_challenge_after_control_dev") for frame in cohort
        )
        if (any(type(kind) is not str for kind in kinds)
                or any(type(x) is not bool for x in challenges)):
            raise ValueError("G4.13 invalid original G1/challenge source")
        stable_positions = [i for i, kind in enumerate(kinds) if kind in _STABLE]
        after_positions = [i for i, flag in enumerate(challenges) if flag]
        combined_positions = sorted(set(stable_positions) & set(after_positions))
        if (
            len(stable_positions) != row["observed_same_generation_stable_g1_frames"]
            or len(after_positions) != row["observed_same_generation_post_control_frames"]
        ):
            raise ValueError("G4.13 original G412 witness aggregate mismatch")
        selected_frame = next(
            (frame for frame in cohort if frame["source_seq"] == row["source_seq"]),
            None,
        )
        if selected_frame is None and cohort:
            raise ValueError("G4.13 selected source frame absent")
        out.append(G413OriginalG1GenerationWitnessDev(
            session_id=session_id, source_seq=row["source_seq"],
            world_tick=row["world_tick"],
            original_action_id=row["original_action_id"],
            original_effect_evidence_class=row["original_effect_evidence_class"],
            original_g412_row_sha256=_digest(row),
            original_g411_row_sha256=row["original_g411_row_sha256"],
            original_g49_row_sha256=row["original_g49_row_sha256"],
            original_t2_row_sha256=row["original_t2_row_sha256"],
            original_generation_first_tick=first,
            original_generation_last_tick=last,
            original_generation_paper_worldticks=len(cohort),
            original_generation_paper_frame_sha256=tuple(
                _digest(frame) for frame in cohort
            ),
            original_generation_g1_kinds=kinds,
            original_generation_post_control_challenges=challenges,
            original_generation_stable_source_seqs=tuple(
                cohort[i]["source_seq"] for i in stable_positions
            ),
            original_generation_post_control_source_seqs=tuple(
                cohort[i]["source_seq"] for i in after_positions
            ),
            selected_frame_original_g1_kind=(
                selected_frame["kind"] if selected_frame else "UNAVAILABLE"
            ),
            selected_frame_post_control_challenge=(
                selected_frame["g46_challenge_after_control_dev"]
                if selected_frame else False
            ),
            stable_candidate_worldticks=len(stable_positions),
            post_control_challenge_worldticks=len(after_positions),
            stable_with_post_control_challenge_worldticks=len(combined_positions),
            first_stable_kind_worldtick_offset=(
                stable_positions[0] if stable_positions else None
            ),
            first_post_control_challenge_worldtick_offset=(
                after_positions[0] if after_positions else None
            ),
            first_stable_with_post_control_worldtick_offset=(
                combined_positions[0] if combined_positions else None
            ),
            evidence_class=_classify(
                count=len(cohort), stable=len(stable_positions),
                after=len(after_positions), both=len(combined_positions),
            ),
        ))
    return tuple(out)
