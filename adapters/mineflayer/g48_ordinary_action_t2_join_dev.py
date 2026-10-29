"""G4.8 DEV: original ordinary JOG/WALK S49 effects on the single T2 ledger.

Extends the G4.7 read-only per-WorldTick audit without replaying energy/P1.
Exact original applied effect ACK through original CLEAR brackets each Action.
Node control generation is sampled in the existing admitted T1u callback.
Even a two-frame G1 candidate is NOT per-physics-tick input causality.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.g47_original_t2_gait_join_dev import (
    join_g47_original_t2_worldticks_dev,
)

_KINDS = {
    "JOG": "STABLE_ORDINARY_FORWARD_CANDIDATE",
    "WALK": "STABLE_SNEAK_FORWARD_CANDIDATE",
}


@dataclass(frozen=True, slots=True)
class G48OriginalOrdinaryTickDev:
    session_id: str
    source_seq: int
    world_tick: int
    original_t2_row_sha256: str
    g47_status: str
    final_status: str
    original_t2_applied_gait: str | None
    ordinary_action_id: str | None
    ordinary_native_ack_seq: int | None
    original_effect_id: str | None
    requested_mode: str | None
    observed_node_generation: int | None
    postchange_challenge_observed: bool
    source: str = "ORIGINAL_S49_ORDINARY_APPLIED_ACK_NODE_T1U_G1_T2_DEV"
    new_p1_or_m0_posting: bool = False
    second_t2_owner_created: bool = False
    exact_packet_to_physics_tick_attested: bool = False
    qualified: bool = False


def join_g48_ordinary_action_t2_worldticks_dev(
    *, session_id: str, original_run_acks: list[dict],
    original_ordinary_acks: list[dict], transition_acks: list[dict],
    original_clear_acks: list[dict], paper_rows: list[dict],
    t2_rows: list[dict],
) -> tuple[G48OriginalOrdinaryTickDev, ...]:
    original = join_g47_original_t2_worldticks_dev(
        session_id=session_id, original_run_acks=original_run_acks,
        transition_acks=transition_acks,
        original_clear_acks=original_clear_acks,
        paper_rows=paper_rows, t2_rows=t2_rows,
    )
    if type(original_ordinary_acks) is not list:
        raise ValueError("G4.8 original ordinary ACK list invalid")
    clear_seq = {c["action_id"]: c["clear_seq"] for c in original_clear_acks}
    run_actions = {r["action_id"] for r in original_run_acks}
    ordinary = {}
    for a in original_ordinary_acks:
        if (
            type(a) is not dict
            or set(a) != {
                "action_id", "effect_id", "mode", "ack_seq",
                "effect", "source",
            }
            or type(a.get("action_id")) is not str
            or not a["action_id"].startswith("goal-")
            or a["action_id"] in ordinary
            or a["action_id"] in run_actions
            or a["action_id"] not in clear_seq
            or a["effect_id"] != a["action_id"]
            or a["mode"] not in _KINDS
            or a["effect"] != (
                "set_control" if a["mode"] == "JOG"
                else "set_forward_sneak_dev"
            )
            or a["source"] != "ORIGINAL_S49_NATIVE_APPLIED"
            or type(a["ack_seq"]) is not int
            or not 0 < a["ack_seq"] < clear_seq[a["action_id"]]
        ):
            raise ValueError("G4.8 refuses foreign/duplicated ordinary Action ACK")
        ordinary[a["action_id"]] = a
    by_paper = {p["source_seq"]: p for p in paper_rows}
    out = []
    for row in original:
        if row.status == "SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV":
            out.append(G48OriginalOrdinaryTickDev(
                session_id=session_id, source_seq=row.source_seq,
                world_tick=row.world_tick,
                original_t2_row_sha256=row.original_t2_row_sha256,
                g47_status=row.status,
                final_status="SOURCE_BOUND_STAGED_GAIT_CANDIDATE_DEV",
                original_t2_applied_gait=row.original_t2_applied_gait,
                ordinary_action_id=None, ordinary_native_ack_seq=None,
                original_effect_id=None, requested_mode=None,
                observed_node_generation=None,
                postchange_challenge_observed=False,
            ))
            continue
        ack = ordinary.get(row.original_active_action)
        if ack is None or not (
            ack["ack_seq"] < row.source_seq <
            clear_seq[ack["action_id"]]
        ):
            out.append(G48OriginalOrdinaryTickDev(
                session_id=session_id, source_seq=row.source_seq,
                world_tick=row.world_tick,
                original_t2_row_sha256=row.original_t2_row_sha256,
                g47_status=row.status,
                final_status="UNKNOWN_NO_ORDINARY_EPOCH",
                original_t2_applied_gait=row.original_t2_applied_gait,
                ordinary_action_id=None, ordinary_native_ack_seq=None,
                original_effect_id=None, requested_mode=None,
                observed_node_generation=None,
                postchange_challenge_observed=False,
            ))
            continue
        p = by_paper[row.source_seq]
        b = p.get("g46_motor_boundary_dev")
        gen = None
        post = False
        status = "UNKNOWN_ORDINARY_NODE_BOUNDARY"
        if (
            type(b) is dict
            and b.get("g48_ordinary_action_dev") is True
            and b.get("action_id") == ack["action_id"]
            and b.get("effect_id") == ack["effect_id"]
            and b.get("requested_mode") == ack["mode"]
            and b.get("transition_index") == 0
            and b.get("control_phase") == "MOVING"
            and type(b.get("control_generation")) is int
            and b["control_generation"] > 0
        ):
            gen = b["control_generation"]
            post = p.get("g46_challenge_after_control_dev") is True
            if not post:
                status = "UNKNOWN_ORDINARY_PRECHANGE_CHALLENGE"
            elif p["kind"] != _KINDS[ack["mode"]]:
                status = "UNKNOWN_ORDINARY_UNSTABLE_PAPER_GAIT"
            elif (
                row.original_t2_applied_gait != ack["mode"]
                or row.original_g3_unknown_fallback
            ):
                status = "UNKNOWN_ORDINARY_T2_GAIT_FALLBACK"
            elif row.original_g3_extra_m0_paid != 0:
                raise ValueError("G4.8 original ordinary gait must not add M0 debit")
            else:
                status = "SOURCE_BOUND_ORDINARY_GAIT_CANDIDATE_DEV"
        out.append(G48OriginalOrdinaryTickDev(
            session_id=session_id, source_seq=row.source_seq,
            world_tick=row.world_tick,
            original_t2_row_sha256=row.original_t2_row_sha256,
            g47_status=row.status, final_status=status,
            original_t2_applied_gait=row.original_t2_applied_gait,
            ordinary_action_id=ack["action_id"],
            ordinary_native_ack_seq=ack["ack_seq"],
            original_effect_id=ack["effect_id"],
            requested_mode=ack["mode"],
            observed_node_generation=gen,
            postchange_challenge_observed=post,
        ))
    return tuple(out)
