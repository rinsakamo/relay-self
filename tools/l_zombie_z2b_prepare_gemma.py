"""Z2b local-only ONE actual Gemma-4 policy preparation (never start a World).

Original previous World logs must be supplied locally, and every original
byte is SHA pinned. Native strict Schema and reasoning-OFF are required.
A successful transport request is NOT GGUF physical-mapping attestation.
Use one request, zero retries and preserve failed raw replies too.
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
from urllib.parse import urlsplit

from adapters.mineflayer.l_zombie_z2b_policy_contract import (
    EXPECTED_PRIOR_SHA,
    ZombiePolicyRejected,
    _canonical,
    freeze_from_http,
    policy_json,
    request,
)
from tools.l_zombie_paper_original_audit import audit_paper_zombie_window
from tools.l_zombie_z2a_prospective_audit import audit_z2a_prospective

MAX_RAW = 16_000_000
MAX_HTTP = 2_000_000
MODEL_GGUF_SHA = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"


def source_summaries(*, z1b_raw: bytes, z2a_raw: bytes) -> tuple[dict, dict]:
    raws = (z1b_raw, z2a_raw)
    if any(type(x) is not bytes or not 0 < len(x) <= MAX_RAW for x in raws):
        raise ZombiePolicyRejected("two bounded old physical Paper originals required")
    actual = tuple(hashlib.sha256(x).hexdigest() for x in raws)
    if actual != EXPECTED_PRIOR_SHA:
        raise ZombiePolicyRejected("old real World Paper raw SHA mismatch")
    results = []
    for raw, sha, evidence in zip(
        raws, actual, ("Z1B_T40_T60", "Z2A_T46_T66"), strict=True,
    ):
        try:
            paper = audit_paper_zombie_window(
                raw, original_sha256=sha,
                expected_marker="z1-source-1", expected_session="z1-client-1",
            )
        except (ValueError, UnicodeError) as exc:
            raise ZombiePolicyRejected("invalid original prior Paper 31 tick witness") from exc
        results.append({
            "evidence_id": evidence,
            "source_scope": "COMPLETED_PREVIOUS_WORLD",
            "raw_original_sha256": sha,
            "world_uuid": paper.world_uuid,
            "zombie_uuid": paper.entity_uuid,
            "reference_tick": paper.forecast_freeze_tick,
            "target_tick": paper.target_tick,
            "start_xz_m": list(paper.forecast_freeze_xz_m),
            "end_xz_m": list(paper.target_xz_m),
            "position_source": "EXACT_PAPER_TICK_NOT_NATIVE_CLIENT_TICK",
            "chase_causality": "NOT_ATTESTED",
        })
    try:
        z2a_check = audit_z2a_prospective(
            z2a_raw, sha256=EXPECTED_PRIOR_SHA[1],
            marker="z1-source-1", session="z1-client-1",
        )
    except (ValueError, UnicodeError) as exc:
        raise ZombiePolicyRejected("Z2a must have genuine prior frozen CHEAP source") from exc
    results[1]["past_stationary_error_m"] = z2a_check["stationary_error_m"]
    results[1]["past_velocity_error_m"] = z2a_check["constant_velocity_error_m"]
    return (results[0], results[1])


def _loopback(url: str) -> str:
    try:
        u = urlsplit(url)
        if (
            u.scheme != "http" or u.hostname not in ("127.0.0.1", "localhost")
            or not 1 <= u.port <= 65535
            or u.path != "/v1/chat/completions"
            or u.username or u.password or u.query or u.fragment
        ):
            raise ZombiePolicyRejected("only exact loopback llama.cpp HTTP endpoint")
    except (ValueError, AttributeError) as exc:
        raise ZombiePolicyRejected("malformed local llama.cpp endpoint") from exc
    return url


def prepare_one_http(
    *, endpoint: str, model: str, z1b_original: Path, z2a_original: Path,
    evidence_root: Path,
) -> dict:
    """Exactly one POST; no retry, never changes Paper or any action authority."""
    _loopback(endpoint)
    if (
        os.environ.get("L_ZOMBIE_Z2B_REAL_GEMMA_DEV") != "1"
        or not isinstance(evidence_root, Path) or not evidence_root.is_absolute()
        or evidence_root.is_symlink() or evidence_root.exists()
        or evidence_root.parent.is_symlink()
    ):
        raise ZombiePolicyRejected("explicit new real model evidence-root/DEV grant required")
    for original in (z1b_original, z2a_original):
        if (not isinstance(original, Path) or not original.is_absolute()
                or not original.is_file() or original.is_symlink()):
            raise ZombiePolicyRejected("exact prior original absolute physical file required")
    past = source_summaries(
        z1b_raw=z1b_original.read_bytes(), z2a_raw=z2a_original.read_bytes(),
    )
    body = request(model, original_prior=past)
    outbound = _canonical(body)
    evidence_root.mkdir(mode=0o700, parents=False, exist_ok=False)
    with (evidence_root / "llama-request-1.raw.json").open("xb") as dest:
        dest.write(outbound)
        dest.flush()
        os.fsync(dest.fileno())
    status = "FAIL_MODEL_NOT_QUALIFIED"
    try:
        r = urllib.request.Request(
            endpoint, data=outbound, method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(r, timeout=75) as source:
                reply = source.read(MAX_HTTP+1)
        except urllib.error.HTTPError as exc:
            reply = exc.read(MAX_HTTP+1)
            (evidence_root / "llama-response-1.raw.json").write_bytes(reply)
            raise ZombiePolicyRejected(f"real model HTTP failure: {exc.code}") from exc
        with (evidence_root / "llama-response-1.raw.json").open("xb") as dest:
            dest.write(reply)
            dest.flush()
            os.fsync(dest.fileno())
        if not 0 < len(reply) <= MAX_HTTP:
            raise ZombiePolicyRejected("empty/oversized real model response")
        policy = freeze_from_http(
            original_request=outbound, original_response=reply,
            expected_request=body,
        )
        with (evidence_root / "prepared-zombie-l2-policy-v1.json").open("xb") as dest:
            dest.write(policy_json(policy))
            dest.flush()
            os.fsync(dest.fileno())
        status = "PREPARED_POLICY_CONTRACT_PASS_NOT_PHYSICALLY_QUALIFIED"
        return {
            "status": status,
            "policy_sha256": policy.policy_sha256,
            "selected_strategy": policy.strategy,
            "speed_m_per_tick": policy.speed_m_per_tick,
            "original_requests": 1,
            "actual_gguf_sha_and_process_mapping_attested_here": False,
            "gemma_transport_qualified": True,
            "future_world_visited": False,
            "learning_admitted": False,
            "l0_promoted": False,
        }
    finally:
        # On HTTP/network error there may be no response bytes; preserve request.
        # External owner must preserve failure and NOT restart this attempt.
        report = {
            "status": status, "requests_max": 1, "retries": 0,
            "old_source_sha256": EXPECTED_PRIOR_SHA,
            "request_sha256": hashlib.sha256(outbound).hexdigest(),
            "model_weights_attested_by_this_tool": False,
            "future_world_visited": False,
        }
        with (evidence_root / "request-status.json").open("x", encoding="utf-8") as dest:
            json.dump(report, dest, sort_keys=True, indent=2)
            dest.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--z1b-paper-original", type=Path, required=True)
    parser.add_argument("--z2a-paper-original", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        outcome = prepare_one_http(
            endpoint=args.endpoint, model=args.model,
            z1b_original=args.z1b_paper_original,
            z2a_original=args.z2a_paper_original,
            evidence_root=args.evidence_root,
        )
    except (OSError, ValueError, urllib.error.URLError) as exc:
        print(f"Z2B_POLICY_PREPARE_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(outcome, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
