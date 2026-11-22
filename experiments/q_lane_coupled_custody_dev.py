"""Q1e: read-only, *coupled* S1/S2 WAL and Git custody verification (DEV).

Q1b by itself checks externally pinned WAL/checkpoint history. Q1c/Q1d by
itself checks Git history of arbitrary files. This composition binds the
*same bytes* of the original S1 anchor and later S2 WAL across both checks.

It does not authenticate an external witness, the original Owner, the
actual source time, or the World. It never grants ActionPort/GPU authority.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from experiments.q_lane_evidence_audit_dev import QEvidenceHold
from experiments.q_lane_git_anchor_custody_dev import (
    QGitCustodyHold,
    inspect_git_pre_s2_custody,
)
from experiments.q_lane_s1_boundary_audit_dev import (
    QS1BoundaryHold,
    verify_s1_s2_anchor,
)


class QCoupledCustodyHold(ValueError):
    """Original pre-S2 anchor and S2 WAL are not mutually source-bound."""


_SOURCE_FIELDS = {
    "expected_pre_s2_anchor_sha256", "s1_wal_path",
    "s1_checkpoint_path", "s2_wal_path", "expected_s2_action_id",
    "expected_head", "expected_world_uuid", "expected_owner_id",
    "expected_self_id", "expected_native_session_id",
    "expected_checkpoint_generation",
}
_GIT_FIELDS = {
    "trusted_root_sha", "pre_s2_anchor_commit",
    "post_s2_evidence_commit", "anchor_path", "s2_path",
}


def verify_coupled_s1_s2_custody(
    *, evidence_dir: Path, git_repo_root: Path, anchor_bytes: bytes,
    source_claims: Mapping[str, Any], git_claims: Mapping[str, Any],
) -> dict[str, Any]:
    """Run both original Q readers, not just compare arbitrary receipt dicts.

    The Git evidence file must be byte-identical to the original S2 WAL,
    and the committed pre-S2 anchor must be byte-identical to the separately
    pinned anchor for the S1 WAL/checkpoint proof. All inputs are untrusted
    until verified, and origin/time remain unverified even on a match.
    """
    if (
        type(source_claims) is not dict or set(source_claims) != _SOURCE_FIELDS
        or type(git_claims) is not dict or set(git_claims) != _GIT_FIELDS
        or type(anchor_bytes) is not bytes
    ):
        raise QCoupledCustodyHold("exact source/Git claim fields and anchor bytes required")
    try:
        pre = verify_s1_s2_anchor(
            evidence_dir, anchor_bytes=anchor_bytes, **source_claims,
        )
        git = inspect_git_pre_s2_custody(
            git_repo_root,
            **git_claims,
            expected_anchor_sha256=source_claims["expected_pre_s2_anchor_sha256"],
            expected_s2_sha256=pre["s2_wal_sha256"],
        )
        # Prevent a caller from substituting another Q1b receipt or from
        # changing the raw local WAL between the two domain readers.
        post = verify_s1_s2_anchor(
            evidence_dir, anchor_bytes=anchor_bytes, **source_claims,
        )
        if pre != post:
            raise QCoupledCustodyHold("original S1/S2 evidence drifted between reads")
        if (
            pre["s2_wal_sha256"] != git["s2_sha256"]
            or pre["head"] != source_claims["expected_head"]
            or git["anchor_sha256"] != source_claims["expected_pre_s2_anchor_sha256"]
        ):
            raise QCoupledCustodyHold("S1/S2 WAL and Git custody not source-identical")
    except (QEvidenceHold, QGitCustodyHold, OSError, TypeError, ValueError) as exc:
        raise QCoupledCustodyHold("coupled original source unavailable") from exc
    return {
        "classification": "Q1E_GIT_S1_ANCHOR_S2_WAL_COUPLED_CPU_OFFLINE_DEV",
        "execution_code_head": pre["head"],
        "evidence_git_root_commit": git["trusted_root_sha"],
        "evidence_git_s1_commit": git["pre_s2_anchor_commit"],
        "evidence_git_s2_commit": git["post_s2_evidence_commit"],
        "s1_action_id": pre["s1_action_id"],
        "s2_action_id": pre["s2_action_id"],
        "s1_anchor_sha256": git["anchor_sha256"],
        "s1_wal_sha256": pre["s1_wal_sha256"],
        "s1_checkpoint_sha256": pre["s1_checkpoint_sha256"],
        "s2_wal_sha256": pre["s2_wal_sha256"],
        "history_first_appearance_consistent": True,
        "source_bytes_coupled_at_readback": True,
        "external_git_root_origin_authenticated": False,
        "external_anchor_producer_authenticated": False,
        "actual_pre_s2_runtime_capture_verified": False,
        "original_owner_semantics_verified": False,
        "actual_original_native_paper_verified": False,
        "real_world_attested": False,
        "qual_go": False,
        "science_run": False,
    }
