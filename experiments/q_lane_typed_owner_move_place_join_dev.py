"""Q1j read-only joint original typed OwnerCut + canonical S1/S2/Git receipt.

A typed owner cut with a matching SHA and internally consistent
Intent/Skill lineage is not an authenticated original runtime snapshot.
Q1j only joins its *raw* source with Q1h's raw canonical MOVE_PLACE WAL,
checkpoint and committed blob history for a strict one-S2 same-session slice.
"""
from __future__ import annotations

from typing import Any

from experiments.q_lane_original_move_place_git_custody_dev import (
    QOriginalMovePlaceGitHold,
    audit_q1h_original_move_place_git_custody,
)
from experiments.q_lane_typed_owner_cut_audit_dev import (
    QTypedOwnerCutHold,
    audit_q1i_typed_owner_cut,
)


class QTypedOriginalSourceJoinHold(ValueError):
    """Q1j cannot join original canonical S1/S2 with typed OwnerCut."""


_Q1H_FIELDS = {
    "evidence_dir", "git_repo_root", "external_anchor_bytes",
    "externally_pinned_anchor_sha256", "expected_code_head",
    "expected_world_uuid", "expected_owner_id", "expected_self_id",
    "expected_native_session_id", "expected_checkpoint_generation",
    "s1_wal_file", "s1_checkpoint_file", "s2_wal_file",
    "expected_s2_action_id", "git_claims",
}


def audit_q1j_typed_owner_move_place_git_join(
    *, q1h_source_claims: dict[str, Any],
    expected_checkpoint_world_id: str,
    expected_checkpoint_branch_id: str,
) -> dict[str, Any]:
    """Require matching same-generation *saved* Self lineage and S1 WAL.

    A positive receipt says CHECKPOINT_SHAPE_AND_LINEAGE_CPU_OFFLINE_DEV,
    NOT an actual Stage28 generation proof or Original Owner attestation.
    """
    if type(q1h_source_claims) is not dict or set(q1h_source_claims) != _Q1H_FIELDS:
        raise QTypedOriginalSourceJoinHold("exact trusted-scope claim field set required")
    if any(
        type(value) is not str or not value.strip()
        for value in (expected_checkpoint_world_id, expected_checkpoint_branch_id)
    ):
        raise QTypedOriginalSourceJoinHold("checkpoint World/branch identity required")
    source = dict(q1h_source_claims)
    try:
        wal = audit_q1h_original_move_place_git_custody(**source)
        generation = source["expected_checkpoint_generation"]
        if type(generation) is not int or generation < 0 or generation > 999_999_999_999:
            raise QTypedOriginalSourceJoinHold("numeric checkpoint generation unqualified")
        cut_args = {
            "evidence_dir": source["evidence_dir"],
            "checkpoint_file": source["s1_checkpoint_file"],
            "expected_checkpoint_sha256": wal["s1_checkpoint_sha256"],
            "expected_generation_id": f"g-{generation:012d}",
            "expected_self_id": source["expected_self_id"],
            "expected_world_id": expected_checkpoint_world_id,
            "expected_branch_id": expected_checkpoint_branch_id,
            "expected_former_native_session_id": source["expected_native_session_id"],
        }
        cut = audit_q1i_typed_owner_cut(**cut_args)
        skill = cut["skills"].get(wal["s1_skill_execution_id"])
        intent = cut["intents"].get(wal["s1_intent_id"])
        if (
            skill is None or intent is None
            or skill["intent_id"] != wal["s1_intent_id"]
            or skill["last_state"] not in ("failed", "cancelled")
            or intent["final_kind"] != "completed"
        ):
            raise QTypedOriginalSourceJoinHold(
                "original S1 Skill and Intent were not reviewed and released in saved cut"
            )
        # Source may change between the first read of the typed cut and
        # Q1h's original S1/S2/Git readback; run both checks again.
        wal_again = audit_q1h_original_move_place_git_custody(**source)
        cut_again = audit_q1i_typed_owner_cut(**cut_args)
        if wal_again != wal or cut_again != cut:
            raise QTypedOriginalSourceJoinHold("S1/S2 WAL or typed Owner source drifted")
    except (QTypedOwnerCutHold, QOriginalMovePlaceGitHold, TypeError, KeyError, ValueError) as exc:
        raise QTypedOriginalSourceJoinHold(
            "original typed Owner/physical checkpoint source not admitted"
        ) from exc
    return {
        "classification": "Q1J_TYPED_OWNER_CANONICAL_S1_S2_GIT_JOIN_CPU_OFFLINE_DEV",
        "execution_code_head_claim": wal["execution_code_head"],
        "original_generation_id": cut["generation_id"],
        "self_id": cut["self_id"],
        "checkpoint_world_id": cut["world_id"],
        "checkpoint_branch_id": cut["branch_id"],
        "former_native_session_id": cut["former_native_session_id"],
        "s1_intent_id": wal["s1_intent_id"],
        "s1_skill_execution_id": wal["s1_skill_execution_id"],
        "s1_skill_last_state": skill["last_state"],
        "s1_intent_last_state": intent["final_kind"],
        "s1_checkpoint_sha256": cut["raw_checkpoint_sha256"],
        "s1_wal_raw_sha256": wal["s1_original_wal_sha256"],
        "s2_wal_raw_sha256": wal["s2_original_wal_sha256"],
        "s1_anchor_sha256": wal["s1_original_anchor_sha256"],
        "matched_original_source_bytes_and_lineage": True,
        "actual_original_owner_identity_authenticated": False,
        "typed_product_full_restore_attested": False,
        "pattern_registry_semantics_attested": False,
        "independent_prior_witness_authenticated": False,
        "actual_s1_s2_runtime_order_attested": False,
        "native_paper_source_attested": False,
        "physical_issue_authorized": False,
        "real_world_attested": False,
        "qual_go": False,
        "science_run": False,
    }
