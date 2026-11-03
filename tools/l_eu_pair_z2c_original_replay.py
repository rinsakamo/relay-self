"""Replay archived Z2b/Z2c physical originals into a NON-admitted EU pair graph.

No new Gemma HTTP and no World. Refuses malformed raw H1/H2 and fails before
ledger export on original SHA/readback mismatches. Host semantic review stays
explicitly marked HOST_NOT_INDEPENDENT; wrong H2 claims remain unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from relay_self.experience_understanding import (
    EULedger,
    EUPairRejected,
    Experience,
    PairLink,
    Understanding,
    encode_ledger,
)
from tools.l_zombie_z2c_h2_independent_audit import audit_saved_h2
from tools.l_zombie_z2c_h2_original_feedback import original_z2b_h2_sources

WORLD_SOURCE = "docs/evidence/l-z2b-real-20261102"
H2_SOURCE = "docs/evidence/l-z2c-real-h2-20261103"
H2_REPLY = H2_SOURCE + "/h2-original/h2-response-1.raw.json"
H2_INDEPENDENT = H2_SOURCE + "/h2-original/h2-independent-original-audit.json"
H2_SEMANTIC = H2_SOURCE + "/semantic-review.json"
H1_POLICY = WORLD_SOURCE + "/gemma-preparation/prepared-zombie-l2-policy-v1.json"
WORLD_AUDIT = WORLD_SOURCE + "/independent-prepared-world-audit.json"
ORIGINAL_PAPER_SHA = "1c20c9e7aa456cdf163edf56a3caab3eead2431febb3f40743896054730e4815"
H1_POLICY_SHA = "5ab25d00180e72b739474f4aaca93317421b2f275975cb737775b7061dbde4ed"
H2_HTTP_SHA = "66e47bcf99f72fea9e32ca49ad3dc806cd5794f56d6fbdb050a6c97b7ee51a78"
MAX_SOURCE = 2_000_000


def read(repo: Path, relative: str) -> tuple[dict, str]:
    path = repo / relative
    if (
        path.is_symlink() or not path.is_file()
        or not path.resolve().is_relative_to(repo.resolve())
        or path.stat().st_size > MAX_SOURCE
    ):
        raise EUPairRejected("unsafe original source path or oversized original")
    raw = path.read_bytes()
    try:
        return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()
    except (UnicodeError, ValueError) as exc:
        raise EUPairRejected("old original source JSON malformed") from exc


def build_z2c_eu_ledger(repo: Path) -> EULedger:
    """Pure archived original replay; no provider, user Memory or Action owner."""
    if not isinstance(repo, Path) or not repo.is_absolute() or not repo.is_dir() or repo.is_symlink():
        raise EUPairRejected("absolute existing repo root required")
    old, paper, replay = original_z2b_h2_sources(repo / WORLD_SOURCE)
    h2 = audit_saved_h2(repo / WORLD_SOURCE, repo / H2_SOURCE / "h2-original")
    if (
        replay["archived_files_checked"] != 68
        or old["policy_sha256"] != H1_POLICY_SHA
        or paper["original_paper_sha256"] != ORIGINAL_PAPER_SHA
        or paper["strategy"] != "STATIONARY"
        or paper["issued_tick"] != 37
        or paper["target_tick"] != 57
        or h2["classification"] != "H2_NUMERIC_WIRE_MATCH_QUALITATIVE_OR_SCHEMA_REJECTED"
        or h2["numeric_h2_self_report_matches_original_paper"] is not True
        or h2["full_h2_contract_verified"] is not False
        or h2["source_files_sha_replayed"] != 68
    ):
        raise EUPairRejected("historical Z2b physical or Z2c cognitive original differs")
    h1_policy, policy_file_sha = read(repo, H1_POLICY)
    world_review, world_review_sha = read(repo, WORLD_AUDIT)
    independent, indep_sha = read(repo, H2_INDEPENDENT)
    semantic, semantic_sha = read(repo, H2_SEMANTIC)
    raw_reply, h2_sha = read(repo, H2_REPLY)
    if (
        h1_policy.get("policy_sha256") != H1_POLICY_SHA
        or h1_policy["strategy"] != "STATIONARY"
        or policy_file_sha == H1_POLICY_SHA  # policy digest is NOT file digest
        or world_review["original_paper_sha256"] != ORIGINAL_PAPER_SHA
        or independent != h2
        or semantic["B1_Q"] != "FAIL"
        or semantic["Z2c_R"] != "RAW_CANDIDATE_SAVED_PROPOSED_NOT_ADMITTED_TYPED_REVISION_REJECTED"
        or h2_sha != H2_HTTP_SHA
    ):
        raise EUPairRejected("H1/H2 original and audit/semantic exact binding failed")
    try:
        model_h2 = json.loads(raw_reply["choices"][0]["message"]["content"])
    except (KeyError, TypeError, ValueError) as exc:
        raise EUPairRejected("missing original Gemma H2 message.content") from exc
    if (
        model_h2.get("evaluated_prior_strategy") != "STATIONARY"
        or model_h2.get("old_falsification_named_strategy") != "STATIONARY"
        or model_h2.get("reconsideration") != "ABSTAIN_PENDING_MORE_EVIDENCE"
        or model_h2.get("proposed_strategy") != "TARGET_APPROACH"
        or model_h2.get("proposed_speed_m_per_tick") is not None
        or h1_policy["falsification_test"].find("CONSTANT_VELOCITY") < 0
    ):
        raise EUPairRejected("historical contradictory understanding was corrected or forged")
    relative_paper = next(
        (p.relative_to(repo).as_posix()
         for p in (repo / WORLD_SOURCE / "world-evidence").rglob("paper-console-original.raw")
         if hashlib.sha256(p.read_bytes()).hexdigest() == ORIGINAL_PAPER_SHA),
        None,
    )
    if relative_paper is None:
        raise EUPairRejected("no physical original Paper source with exact SHA")
    result = EULedger("relay-self-l-eu-z2b-z2c")
    result = result.add_experience(Experience(
        experience_id="E_Z2B_PAPER_T37_T57",
        source_sha256=ORIGINAL_PAPER_SHA,
        source_path=relative_paper,
        source_kind="WORLD_OUTCOME",
        source_status="ARCHIVED_REPLAY_VERIFIED",
        world_uuid=paper["world_uuid"],
        fact_summary=(
            "Paper+20 tick original outcome differs from the frozen STATIONARY "
            "prediction by 1.4837801948120548m (CHEAP baselines tied)."
        ),
        source_event="PAPER_T37_FROZEN_TO_T57_OBSERVED",
    ))
    result = result.add_experience(Experience(
        experience_id="E_Z2C_REAL_H2_RESPONSE",
        source_sha256=h2_sha,
        source_path=H2_REPLY,
        source_kind="MODEL_SELF_REVIEW",
        source_status="ARCHIVED_REPLAY_VERIFIED",
        world_uuid=paper["world_uuid"],
        fact_summary=(
            "H2 original reply gave a limited numerical match but misnamed H1 "
            "falsification, and proposed TARGET_APPROACH with ABSTAIN and null speed."
        ),
        source_event="POST_Z2B_H2_SINGLE_REAL_HTTP_REPLY",
    ))
    result = result.add_understanding(Understanding(
        understanding_id="U_H1_GEMMA_STATIONARY",
        stage="ORIGINAL_HYPOTHESIS",
        original_response_sha256=old["model_response_sha256"],
        source_kind="REAL_GEMMA_H1_PREPARED_POLICY",
        source_strategy=h1_policy["strategy"],
        applicability=h1_policy["applicability"],
        reason_original=h1_policy["reason"],
        falsification_original=h1_policy["falsification_test"],
        parent_ids=(),
        evidence_ids=("E_Z2B_PAPER_T37_T57",),
    ))
    result = result.add_understanding(Understanding(
        understanding_id="U_H2_GEMMA_RAW_REINTERPRETATION",
        stage="POST_OUTCOME_REINTERPRETATION",
        original_response_sha256=h2_sha,
        source_kind="REAL_GEMMA_H2_FAILED_CONTRACT",
        source_strategy=model_h2["proposed_strategy"],
        applicability=model_h2["proposed_applicability"],
        reason_original=model_h2["rationale"],
        falsification_original=model_h2["next_falsification_test"],
        parent_ids=("U_H1_GEMMA_STATIONARY",),
        evidence_ids=("E_Z2B_PAPER_T37_T57", "E_Z2C_REAL_H2_RESPONSE"),
    ))
    result = result.link(PairLink(
        experience_id="E_Z2B_PAPER_T37_T57",
        understanding_id="U_H1_GEMMA_STATIONARY",
        relation="TESTED_BY",
        review="ORIGINAL_PREDICTION_MISMATCH",
        review_source_sha256=world_review_sha,
        review_provenance="ORIGINAL_PAPER_INDEPENDENT_SOURCE_AUDIT",
        reason="Exact Paper tick+20 outcome mismatches H1; source alone cannot prove cause.",
    ))
    result = result.link(PairLink(
        experience_id="E_Z2B_PAPER_T37_T57",
        understanding_id="U_H2_GEMMA_RAW_REINTERPRETATION",
        relation="REVISES_ABOUT",
        review="PROPOSAL_NOT_ADMITTED",
        review_source_sha256=indep_sha,
        review_provenance="Z2C_H2_INDEPENDENT_CONTRACT_READBACK",
        reason="One real H2 followed the World; semantic contract rejected it, no revision admitted.",
    ))
    result = result.link(PairLink(
        experience_id="E_Z2C_REAL_H2_RESPONSE",
        understanding_id="U_H2_GEMMA_RAW_REINTERPRETATION",
        relation="CONTRADICTED_BY",
        review="NUMERIC_LIMITED_SEMANTIC_FAIL",
        review_source_sha256=semantic_sha,
        review_provenance="HOST_SEMANTIC_REVIEW_NOT_INDEPENDENT",
        reason=(
            "H2 missed old CONSTANT_VELOCITY falsification and suggested TARGET_APPROACH "
            "while choosing ABSTAIN with null speed; no typed revision created."
        ),
    ))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if (
            not args.output.is_absolute() or args.output.is_symlink()
            or args.output.exists() or not args.output.parent.is_dir()
            or args.output.parent.is_symlink()
        ):
            raise EUPairRejected("write only to a new exclusive absolute output file")
        ledger = build_z2c_eu_ledger(args.repo)
        blob = encode_ledger(ledger)
        with args.output.open("xb") as writer:
            writer.write(blob)
            writer.flush()
            os.fsync(writer.fileno())
    except (OSError, ValueError, TypeError, StopIteration) as exc:
        print(f"L_EU_Z2C_REPLAY_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": "EU_SHADOW_ORIGINAL_REPLAY_PASS_NO_ADMISSION",
        "ledger_sha256": hashlib.sha256(blob).hexdigest(),
        "experiences": len(ledger.experiences),
        "understandings": len(ledger.understandings),
        "links": len(ledger.links),
        "worlds_started": 0,
        "model_http_calls": 0,
        "learning_updates": 0,
        "authority": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
