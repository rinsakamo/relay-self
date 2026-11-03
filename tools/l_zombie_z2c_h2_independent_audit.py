"""Independent read-only Z2c H2 original postflight and partial-outcome audit.

Replays the preserved Z2b H1/Paper sources BEFORE interpreting the newer H2.
A well-shaped HTTP response is NOT proof of a physically mapped real Gemma.
Most importantly, numeric self-report and coherent qualitative reasoning have
independent classifications, including when strict H2 admission fails.
No network, no Minecraft, no model, no action, no learning admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

from adapters.mineflayer.l_mp11_gemma_wire_contract import enforce_gemma_thinking_off
from adapters.mineflayer.l_zombie_z2b_policy_contract import (
    ZombiePolicyRejected,
    _canonical,
    _unique_pairs,
)
from adapters.mineflayer.l_zombie_z2c_feedback_contract import (
    NUMERIC_TOLERANCE_M,
    TARGET,
    build_request,
    freeze_h2,
    revision_json,
)
from tools.l_zombie_z2c_h2_original_feedback import original_z2b_h2_sources

MAX_RAW = 2_000_000
EXPECTED_H2_FILES = (
    "h2-request-1.raw.json", "h2-response-1.raw.json",
    "h2-status.json", "h2-original-source-readback.json",
    "h2-revision-proposal-v1.json",
)


def _exact_bytes(root: Path, name: str, *, required: bool = True) -> bytes | None:
    if name not in EXPECTED_H2_FILES:
        raise ZombiePolicyRejected("unexpected H2 raw filename")
    target = root / name
    if not target.exists() and not target.is_symlink():
        if required:
            raise ZombiePolicyRejected(f"required original H2 file missing: {name}")
        return None
    if (
        target.is_symlink() or not target.is_file()
        or not target.resolve().is_relative_to(root.resolve())
        or target.stat().st_size > MAX_RAW
    ):
        raise ZombiePolicyRejected("unsafe, oversized or non-regular H2 original")
    return target.read_bytes()


def _strict_json(raw: bytes) -> object:
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _envelope_content(original_response: bytes) -> dict | None:
    """Parse native HTTP only if stop and no thinking leakage; no semantic claim."""
    try:
        outer = _strict_json(original_response)
        if type(outer) is not dict:
            return None
        enforce_gemma_thinking_off(outer)
        choices = outer.get("choices")
        if (
            type(choices) is not list or len(choices) != 1
            or type(choices[0]) is not dict
            or choices[0].get("finish_reason") != "stop"
        ):
            return None
        answer = _strict_json(choices[0]["message"]["content"].encode("utf-8"))
        return answer if type(answer) is dict else None
    except (KeyError, TypeError, ValueError, UnicodeError):
        return None


def audit_saved_h2(original_root: Path, h2_root: Path) -> dict:
    for root in (original_root, h2_root):
        if (
            not isinstance(root, Path) or not root.is_absolute()
            or not root.is_dir() or root.is_symlink()
        ):
            raise ZombiePolicyRejected("absolute non-symlink existing source root required")
    old, world, replay = original_z2b_h2_sources(original_root)
    request_raw = _exact_bytes(h2_root, "h2-request-1.raw.json")
    stored_status = _strict_json(_exact_bytes(h2_root, "h2-status.json"))
    stored_replay = _strict_json(_exact_bytes(h2_root, "h2-original-source-readback.json"))
    if (
        type(stored_status) is not dict
        or stored_replay != replay
        or stored_status.get("source") != "ARCHIVED_Z2B_REAL_H1_AND_EXACT_PAPER_WORLD"
        or stored_status.get("h2_http_requests_max") != 1
        or stored_status.get("retry_count") != 0
        or stored_status.get("h2_worlds") != 0
        or stored_status.get("qualification_go") is not False
        or stored_status.get("science_run") is not False
        or stored_status.get("h1_policy_sha256") != old["policy_sha256"]
        or stored_status.get("h1_world_paper_original_sha256") != world["original_paper_sha256"]
        or stored_status.get("h2_request_sha256") != _sha(request_raw)
    ):
        raise ZombiePolicyRejected("H2 status contradicts saved immutable H1/World source")
    try:
        request = _strict_json(request_raw)
        if type(request) is not dict:
            raise ZombiePolicyRejected("H2 request is not an object")
        expected = build_request(
            model=request["model"],
            old_policy=old, completed_world=world,
            paper_original_sha256=world["original_paper_sha256"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ZombiePolicyRejected("invalid model-facing H2 request") from exc
    if request_raw != _canonical(expected):
        raise ZombiePolicyRejected("H2 request differs from deterministic original-only request")

    response_raw = _exact_bytes(h2_root, "h2-response-1.raw.json", required=False)
    revision_raw = _exact_bytes(h2_root, "h2-revision-proposal-v1.json", required=False)
    if stored_status.get("h2_response_exists") is not (response_raw is not None):
        raise ZombiePolicyRejected("H2 status incorrectly declares response presence")

    report = {
        "schema": "L_ZOMBIE_Z2C_INDEPENDENT_H2_READBACK_V1",
        "original_h1_policy_sha256": old["policy_sha256"],
        "original_paper_sha256": world["original_paper_sha256"],
        "new_h2_request_sha256": _sha(request_raw),
        "new_h2_response_sha256": _sha(response_raw) if response_raw is not None else None,
        "source_files_sha_replayed": replay["archived_files_checked"],
        "worlds_started_by_this_audit": 0,
        "http_requests_started_by_this_audit": 0,
        "reported_worlds_in_h2_attempt": 0,
        "h2_wire_stopped_and_thinking_off": False,
        "numeric_h2_self_report_matches_original_paper": False,
        "numeric_H2_limited_evidence_only": False,
        "full_h2_contract_verified": False,
        "independent_qualitative_semantic_review": "NOT_PERFORMED",
        "B1_Q": "NOT_INDEPENDENTLY_ESTABLISHED",
        "B2": "NOT_ESTABLISHED_NO_HOLDOUT",
        "learning_authorized": False, "action_authorized": False,
        "l0_promotion": False, "qualification_go": False,
        "science_run": False,
    }
    if response_raw is None:
        if revision_raw is not None or stored_status["status"] != "H2_NOT_ESTABLISHED":
            raise ZombiePolicyRejected("unreceived H2 cannot produce an admitted proposal")
        report["classification"] = "H2_NO_SAVED_RESPONSE_NOT_ESTABLISHED"
        return report

    answer = _envelope_content(response_raw)
    report["h2_wire_stopped_and_thinking_off"] = answer is not None
    if answer is not None:
        claimed = answer.get("observed_horizontal_error_m")
        if (
            answer.get("measurement_target") == TARGET
            and answer.get("evaluated_prior_strategy") == old["strategy"]
            and answer.get("error_basis") == "ORIGINAL_PAPER_EXACT_TICK_XZ"
            and type(claimed) in (int, float) and math.isfinite(claimed)
            and claimed >= 0
        ):
            direct = math.dist(world["model_prepared_xz_m"], world["future_actual_xz_m"])
            report["numeric_h2_self_report_matches_original_paper"] = (
                abs(claimed-direct) <= NUMERIC_TOLERANCE_M
            )
            report["numeric_H2_limited_evidence_only"] = (
                report["numeric_h2_self_report_matches_original_paper"]
            )
    try:
        revision = freeze_h2(
            request_raw=request_raw, response_raw=response_raw,
            expected_request=expected, old_policy=old, world=world,
        )
    except ValueError:
        if revision_raw is not None or stored_status["status"] != "H2_NOT_ESTABLISHED":
            raise ZombiePolicyRejected("invalid H2 output cannot have a PASS/proposal receipt") from None
        report["classification"] = (
            "H2_NUMERIC_WIRE_MATCH_QUALITATIVE_OR_SCHEMA_REJECTED"
            if report["numeric_h2_self_report_matches_original_paper"]
            else "H2_WIRE_OR_NUMERIC_UNESTABLISHED"
        )
        return report

    if (
        revision_raw != revision_json(revision)
        or stored_status["status"] != "H2_CONTRACT_DEV_PASS_UNADMITTED"
        or type(stored_status.get("h2_result")) is not dict
        or stored_status["h2_result"].get("revision_sha256") != revision.revision_sha256
        or stored_status["h2_result"].get("observed_error_m") != revision.observed_error_m
        or stored_status["h2_result"].get("learning_admission") is not False
        or stored_status["h2_result"].get("l0_promotion") is not False
        or stored_status.get("real_gguf_process_mapping_verified_here") is not False
    ):
        raise ZombiePolicyRejected("H2 proposal/status mismatch vs rederived raw source")
    report["classification"] = "H2_FULL_CONTRACT_SOURCE_REPLAY_PASS_SEMANTIC_REVIEW_PENDING"
    report["full_h2_contract_verified"] = True
    report["reconsideration"] = revision.reconsideration
    report["proposed_strategy"] = revision.proposed_strategy
    report["proposed_applicability"] = revision.proposed_applicability
    report["proposed_falsification_target"] = revision.next_falsification_target
    report["revision_sha256"] = revision.revision_sha256
    # An enum and a pattern-matching string are not independent semantic proof.
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-root", type=Path, required=True)
    p.add_argument("--h2-root", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    try:
        if (
            not args.report.is_absolute() or args.report.is_symlink()
            or args.report.exists()
            or not args.report.parent.is_dir() or args.report.parent.is_symlink()
            or args.report == args.h2_root or args.report == args.original_root
        ):
            raise ZombiePolicyRejected("new exclusive independent readback report required")
        result = audit_saved_h2(args.original_root, args.h2_root)
        with args.report.open("x", encoding="utf-8") as writer:
            json.dump(result, writer, sort_keys=True, indent=2, allow_nan=False)
            writer.write("\n")
            writer.flush()
            os.fsync(writer.fileno())
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        print(f"Z2C_INDEPENDENT_AUDIT_REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "classification": result["classification"],
        "numeric_h2_self_report_matches_original_paper": (
            result["numeric_h2_self_report_matches_original_paper"]
        ),
        "full_h2_contract_verified": result["full_h2_contract_verified"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
