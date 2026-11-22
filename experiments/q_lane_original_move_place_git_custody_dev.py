"""Q1h read-only cross-binding of canonical MOVE_PLACE WAL and Git S1 custody.

Q1b/Q1e accept a synthetic flat WAL. Q1g separately validates an actual
PhysicalActionJournal v2 envelope in a narrow S1->one-S2 MOVE_PLACE slice.
Q1h binds Q1g's RAW WAL sha to the actual pre-S2 anchor, its checkpoint
bytes and Git-held pre/post immutable blobs. NO original-source authority.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from experiments.q_lane_evidence_audit_dev import QEvidenceHold, _raw_file
from experiments.q_lane_git_anchor_custody_dev import (
    QGitCustodyHold, inspect_git_pre_s2_custody,
)
from experiments.q_lane_original_move_place_wal_dev import (
    QMovePlaceWalHold, audit_q1g_original_move_place_wal,
)
from experiments.q_lane_s1_boundary_audit_dev import _FIELDS, _json


class QOriginalMovePlaceGitHold(ValueError):
    """Canonical S1/S2 WAL, independent anchor or Git source does not join."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def audit_q1h_original_move_place_git_custody(
    *, evidence_dir: Path, git_repo_root: Path, external_anchor_bytes: bytes,
    externally_pinned_anchor_sha256: str,
    expected_code_head: str, expected_world_uuid: str, expected_owner_id: str,
    expected_self_id: str, expected_native_session_id: str,
    expected_checkpoint_generation: int, s1_wal_file: str,
    s1_checkpoint_file: str, s2_wal_file: str, expected_s2_action_id: str,
    git_claims: dict[str, str],
) -> dict[str, Any]:
    """Require one frozen S1 anchor, checkpoint and canonical S2 move WAL.

    The two independent provenance checkers are called twice. Even passing
    results say NOTHING about the external source of trust or physical time.
    """
    if (
        type(external_anchor_bytes) is not bytes or not external_anchor_bytes
        or type(externally_pinned_anchor_sha256) is not str
        or len(externally_pinned_anchor_sha256) != 64
        or any(c not in "0123456789abcdef" for c in externally_pinned_anchor_sha256)
        or _sha(external_anchor_bytes) != externally_pinned_anchor_sha256
        or type(git_claims) is not dict
        or set(git_claims) != {
            "trusted_root_sha", "pre_s2_anchor_commit",
            "post_s2_evidence_commit", "anchor_path", "s2_path",
        }
        or type(expected_checkpoint_generation) is not int
        or expected_checkpoint_generation < 0
        or len({s1_wal_file, s1_checkpoint_file, s2_wal_file}) != 3
    ):
        raise QOriginalMovePlaceGitHold("external original source pins/fields incomplete")
    try:
        anchor = _json(external_anchor_bytes)
        identities: dict[str, object] = {
            "head": expected_code_head, "world_uuid": expected_world_uuid,
            "owner_id": expected_owner_id, "self_id": expected_self_id,
            "native_session_id": expected_native_session_id,
            "checkpoint_generation": expected_checkpoint_generation,
        }
        if (
            set(anchor) != _FIELDS
            or anchor["schema"] != 1
            or anchor["phase"] != "S1_TERMINAL_PRE_S2"
            or any(anchor[key] != expected or type(anchor[key]) is not type(expected)
                   for key, expected in identities.items())
            or anchor["s1_status"] != "NATIVE_PLACE_MOVE_SETTLED"
            or type(anchor["s1_action_count"]) is not int
            or not 1 <= anchor["s1_action_count"] < 64
        ):
            raise QOriginalMovePlaceGitHold("S1 anchor original scope/phase not verified")
        local_scope: dict[str, object] = {
            "evidence_dir": evidence_dir, "s1_wal_file": s1_wal_file,
            "s2_wal_file": s2_wal_file,
            "expected_s1_wal_sha256": anchor["s1_wal_sha256"],
            "expected_self_id": expected_self_id,
            "expected_native_session_id": expected_native_session_id,
            "expected_s1_action_count": anchor["s1_action_count"],
            "expected_last_s1_action_id": anchor["s1_action_id"],
            "expected_s2_action_id": expected_s2_action_id,
        }
        before = audit_q1g_original_move_place_wal(**local_scope)
        checkpoint_raw = _raw_file(evidence_dir, s1_checkpoint_file)
        if _sha(checkpoint_raw) != anchor["s1_checkpoint_sha256"]:
            raise QOriginalMovePlaceGitHold("original S1 checkpoint bytes differ from anchor")
        git_scope = {
            **git_claims,
            "repo_root": git_repo_root,
            "expected_anchor_sha256": externally_pinned_anchor_sha256,
            "expected_s2_sha256": before["s2_wal_raw_sha256"],
        }
        first_git = inspect_git_pre_s2_custody(**git_scope)
        after = audit_q1g_original_move_place_wal(**local_scope)
        if before != after:
            raise QOriginalMovePlaceGitHold("canonical WAL readbacks changed between audit domains")
        if _raw_file(evidence_dir, s1_checkpoint_file) != checkpoint_raw:
            raise QOriginalMovePlaceGitHold("original checkpoint changed between reads")
        last_git = inspect_git_pre_s2_custody(**git_scope)
        if first_git != last_git:
            raise QOriginalMovePlaceGitHold("Git anchor/WAL custody changed between reads")
    except (QEvidenceHold, QGitCustodyHold, QMovePlaceWalHold, OSError, ValueError, TypeError) as exc:
        raise QOriginalMovePlaceGitHold("original S1/S2 physical and Git source not joined") from exc
    return {
        "classification": "Q1H_ORIGINAL_MOVE_PLACE_GIT_WAL_COUPLED_CPU_OFFLINE_DEV",
        "execution_code_head": expected_code_head,
        "self_id": expected_self_id,
        "native_session_id": expected_native_session_id,
        "world_uuid_claim": expected_world_uuid,
        "owner_claim": expected_owner_id,
        "checkpoint_generation_claim": expected_checkpoint_generation,
        "s1_original_anchor_sha256": externally_pinned_anchor_sha256,
        "s1_original_wal_sha256": before["s1_wal_raw_sha256"],
        "s1_checkpoint_sha256": _sha(checkpoint_raw),
        "s2_original_wal_sha256": before["s2_wal_raw_sha256"],
        "s1_last_action_id": before["s1_last_action_id"],
        "s2_action_id": before["s2_action_id"],
        "s2_terminal_status_label": before["s2_terminal_status_label"],
        "committed_blob_chain_consistent": True,
        "canonical_move_place_wal_structurally_consistent": True,
        "source_readback_stable_at_inspection": True,
        "external_witness_origin_authenticated": False,
        "actual_pre_s2_runtime_capture_verified": False,
        "original_owner_authentication_verified": False,
        "original_stage28_checkpoint_semantics_verified": False,
        "native_ack_paper_source_independently_verified": False,
        "s2_skill_success_attested": False,
        "real_world_attested": False,
        "qual_go": False,
        "science_run": False,
    }
