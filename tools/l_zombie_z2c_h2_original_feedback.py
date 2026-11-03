"""Post-outcome Z2c: replay real Z2b originals, make one H2 model call.

Z2b H1 and all Paper originals remain byte-for-byte immutable. This tool
never runs Paper, summons a mob, executes actions, or changes memory.
The actual GGUF file and process mapping need independent operator checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from adapters.mineflayer.l_zombie_z2b_policy_contract import (
    ZombiePolicyRejected,
    _canonical,
)
from adapters.mineflayer.l_zombie_z2c_feedback_contract import (
    build_request,
    freeze_h2,
    revision_json,
)
from tools.l_zombie_z2b_paper_policy_audit import audit_prepared_l2_world
from tools.l_zombie_z2b_prepare_gemma import _loopback, verify_prepared_archive
from tools.l_zombie_z2b_saved_original_readback import readback

MAX_HTTP = 2_000_000


def original_z2b_h2_sources(root: Path) -> tuple[dict, dict, dict]:
    """Verify ALL archived files + rederive the old H1/world from originals."""
    if (
        not isinstance(root, Path) or not root.is_absolute()
        or not root.is_dir() or root.is_symlink()
    ):
        raise ZombiePolicyRejected("absolute immutable archived Z2b original root required")
    receipt = readback(root)
    if (
        receipt["classification"] != "SAVED_Z2B_ORIGINAL_REPLAY_PASS_NOT_LIVE_ATTESTATION"
        or receipt["new_model_calls"] != 0 or receipt["new_worlds"] != 0
    ):
        raise ZombiePolicyRejected("saved original replay failed")
    try:
        z1b, = (root / "priors/z1b").rglob("paper-console-original.raw")
        z2a, = (root / "priors/z2a").rglob("paper-console-original.raw")
        target, = (root / "world-evidence").rglob("paper-console-original.raw")
        policy = verify_prepared_archive(
            prepared_root=root / "gemma-preparation",
            z1b_original=z1b, z2a_original=z2a,
        )
        old = json.loads((root / "gemma-preparation/prepared-zombie-l2-policy-v1.json").read_text())
        if old["policy_sha256"] != policy.policy_sha256:
            raise ZombiePolicyRejected("historical H1 typed-policy mismatch")
        original = target.read_bytes()
        paper_sha = hashlib.sha256(original).hexdigest()
        world = audit_prepared_l2_world(
            original, sha256=paper_sha, marker="z1-source-1",
            session="z1-client-1", prepared=policy,
        )
        saved = json.loads((root / "independent-prepared-world-audit.json").read_text())
        world["model_original_wire_cryptographically_joined_by_this_parser"] = True
        if world != saved:
            raise ZombiePolicyRejected("original Paper model policy audit differs")
        if (
            old["strategy"] != "STATIONARY"
            or world["prepared_policy_error_m"] is None
            or abs(world["prepared_policy_error_m"] - 1.4837801948120548) > 1e-10
            or world["issued_tick"] != 37 or world["target_tick"] != 57
        ):
            raise ZombiePolicyRejected("not exact Z2b completed historical H1")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ZombiePolicyRejected("Z2b frozen H1 + outcome original revalidation failed") from exc
    return old, world, receipt


def _safe_new_root(root: Path) -> None:
    if (
        not isinstance(root, Path) or not root.is_absolute()
        or root.exists() or root.is_symlink()
        or not root.parent.is_dir() or root.parent.is_symlink()
    ):
        raise ZombiePolicyRejected("unique new absolute H2 evidence root required")


def _atomic_new(path: Path, data: bytes) -> None:
    with path.open("xb") as writer:
        writer.write(data)
        writer.flush()
        os.fsync(writer.fileno())


def real_h2_once(
    *, original_root: Path, output_root: Path, endpoint: str, model: str,
) -> dict:
    """Exactly one HTTP POST, after independently re-reading completed H1."""
    _loopback(endpoint)
    if os.environ.get("L_ZOMBIE_Z2C_REAL_H2_DEV") != "1":
        raise ZombiePolicyRejected("Z2c real-H2 grant missing")
    _safe_new_root(output_root)
    prior, world, replay = original_z2b_h2_sources(original_root)
    body = build_request(
        model=model, old_policy=prior, completed_world=world,
        paper_original_sha256=world["original_paper_sha256"],
    )
    outbound = _canonical(body)
    output_root.mkdir(mode=0o700, exist_ok=False)
    _atomic_new(output_root / "h2-request-1.raw.json", outbound)
    _atomic_new(output_root / "h2-original-source-readback.json",
                _canonical(replay) + b"\n")
    status = "H2_NOT_ESTABLISHED"
    answer_status = None
    try:
        request = urllib.request.Request(
            endpoint, data=outbound, method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=75) as http:
                raw = http.read(MAX_HTTP + 1)
        except urllib.error.HTTPError as exc:
            raw = exc.read(MAX_HTTP + 1)
            _atomic_new(output_root / "h2-response-1.raw.json", raw)
            raise ZombiePolicyRejected(f"one H2 real HTTP failed status={exc.code}") from exc
        _atomic_new(output_root / "h2-response-1.raw.json", raw)
        if not 0 < len(raw) <= MAX_HTTP:
            raise ZombiePolicyRejected("H2 response empty or oversized")
        revision = freeze_h2(
            request_raw=outbound, response_raw=raw,
            expected_request=body, old_policy=prior, world=world,
        )
        _atomic_new(output_root / "h2-revision-proposal-v1.json",
                    revision_json(revision))
        status = "H2_CONTRACT_DEV_PASS_UNADMITTED"
        answer_status = {
            "reconsideration": revision.reconsideration,
            "proposed_strategy": revision.proposed_strategy,
            "observed_error_m": revision.observed_error_m,
            "revision_sha256": revision.revision_sha256,
            "new_worlds": 0, "h2_http_requests": 1, "retries": 0,
            "B1_N": "NUMERIC_RECOGNITION_LIMITED_DEV",
            "B1_Q": "SEMANTIC_REVIEW_REQUIRED",
            "B2": "NOT_ESTABLISHED",
            "learning_admission": False, "l0_promotion": False,
            "real_model_gguf_process_mapping_attested_here": False,
        }
        return {"status": status, **answer_status}
    finally:
        receipt = {
            "status": status,
            "source": "ARCHIVED_Z2B_REAL_H1_AND_EXACT_PAPER_WORLD",
            "h2_http_requests_max": 1,
            "h2_worlds": 0,
            "retry_count": 0,
            "h1_policy_sha256": prior["policy_sha256"],
            "h1_world_paper_original_sha256": world["original_paper_sha256"],
            "h2_request_sha256": hashlib.sha256(outbound).hexdigest(),
            "h2_response_exists": (output_root / "h2-response-1.raw.json").exists(),
            "real_gguf_process_mapping_verified_here": False,
            "h2_result": answer_status,
            "qualification_go": False, "science_run": False,
        }
        _atomic_new(output_root / "h2-status.json", _canonical(receipt) + b"\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-root", required=True, type=Path)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    try:
        report = real_h2_once(
            original_root=args.original_root,
            output_root=args.evidence_root,
            endpoint=args.endpoint,
            model=args.model,
        )
    except (OSError, ValueError, urllib.error.URLError) as exc:
        print(f"Z2C_H2_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
