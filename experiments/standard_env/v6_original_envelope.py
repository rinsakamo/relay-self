"""R #575 V6 read-only prospective original capture envelope, NOT source authority.

The S producer does not yet emit this three-original protocol. This gate can
check canonical complete *candidate* streams against externally supplied hashes
when they exist; even matching bytes cannot authenticate Minecraft server
origin, rule out unlogged privileged commands, or grant V science/World use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from experiments.standard_env.v6_packet_provenance import (
    MAX_NATIVE_BYTES,
    _safe,
    _unique_pairs,
    review_native_original,
)
from experiments.standard_env.v6_start_admission import (
    S_START_SOURCE_HEAD,
    _identity,
)
from experiments.standard_env.v6_atomic_admission import S_ATOMIC_SOURCE_HEAD

SCHEMA = "RSEE_V6_PROSPECTIVE_ORIGINAL_BUNDLE_V1"
ORIGINAL_NAMES = ("server_stdout_original.log", "issuer_commands_original.jsonl",
                  "native_bridge_original.jsonl")
SHA = re.compile(r"[a-f0-9]{64}\Z")
MAX_SERVER_BYTES = 4 * 1024 * 1024
MAX_JOURNAL_BYTES = 256 * 1024
ISSUER_PHASES = (
    ("food_install", "function relayself_v6:install"),
    ("start_install", "function relayself_v6_start:install"),
    ("first_native_probe", "PROBE_NONISSUED"),
    ("start_function", "function relayself_v6_start:start_trial"),
    ("read_start_attempt", "scoreboard players get #start_attempt rs_v6_tick"),
    ("read_start_gametime", "scoreboard players get #start_gametime rs_v6_tick"),
    ("food_function", "execute at RelaySelf run function relayself_v6:atomic_food"),
    ("read_food_attempt", "scoreboard players get #attempt rs_v6_tick"),
    ("read_food_before", "scoreboard players get #before rs_v6_tick"),
    ("read_food_after", "scoreboard players get #after rs_v6_tick"),
    ("read_food_success", "scoreboard players get #ok rs_v6_tick"),
    ("shutdown_request", "stop"),
)
# Journal is an issuer claim, not server acknowledgement or a full command log.


class OriginalBundleRejected(ValueError):
    """Prospective recorded-stream integrity or source correlation failed."""


def _need(ok: bool, why: str) -> None:
    if not ok:
        raise OriginalBundleRejected(why)


def _read_original(root: Path, name: str, digest: str, limit: int) -> bytes:
    _need(type(digest) is str and SHA.fullmatch(digest) is not None,
          "external original SHA256 comparand must be canonical")
    f = _safe(root / name, directory=False)
    _need(f.stat().st_size <= limit, "original stream size bound exceeded")
    with f.open("rb") as handle:
        raw = handle.read(limit + 1)
    _need(len(raw) <= limit and hashlib.sha256(raw).hexdigest() == digest,
          "original bytes differ from externally provided digest")
    _need(raw.endswith(b"\n") and not raw.startswith(b"\xef\xbb\xbf")
          and b"\r" not in raw and b"\x00" not in raw,
          "original must be nonempty LF-terminated without BOM/CR/NUL")
    return raw


def _lines(raw: bytes, *, max_count: int) -> list[dict[str, Any]]:
    lines = raw.split(b"\n")[:-1]
    _need(1 <= len(lines) <= max_count
          and all(0 < len(row) <= 16384 for row in lines),
          "truncated/blank/oversized original JSONL")
    records = []
    for line in lines:
        try:
            parsed = json.loads(line.decode("utf-8"),
                                object_pairs_hook=_unique_pairs,
                                parse_constant=lambda _: (_ for _ in ()).throw(
                                    OriginalBundleRejected("nonfinite JSON value")))
        except (ValueError, UnicodeError) as exc:
            raise OriginalBundleRejected("not canonical JSONL object") from exc
        _need(type(parsed) is dict, "JSONL record is not an object")
        records.append(parsed)
    return records


def _review_issuer(raw: bytes, *, session: str,
                   first_probe_seq: int, first_probe_request: str) -> dict[str, Any]:
    rows = _lines(raw, max_count=256)
    _need(len(rows) == len(ISSUER_PHASES), "missing/repeated/unexpected command phase")
    previous_host = -1
    for i, (record, (phase, command)) in enumerate(zip(rows, ISSUER_PHASES)):
        _need(set(record) == {
            "session_id", "seq", "phase", "issuer_command", "host_monotonic_ns",
            "first_probe_native_seq", "first_probe_request_id",
        }, "issuer record fields mismatch")
        _need(record["session_id"] == session
              and type(record["seq"]) is int and record["seq"] == i
              and record["phase"] == phase
              and record["issuer_command"] == command
              and type(record["host_monotonic_ns"]) is int
              and record["host_monotonic_ns"] > previous_host,
              "issuer phases/order/clock/source mismatch")
        prev_seq = record["first_probe_native_seq"]
        prev_request = record["first_probe_request_id"]
        _need(type(prev_seq) is int and prev_seq == first_probe_seq
              and type(prev_request) is str and prev_request == first_probe_request,
              "issuer lost native L0 correlation")
        previous_host = record["host_monotonic_ns"]
    return {"candidate_issuer_rows": len(rows), "first_l0_seq": first_probe_seq}


def review_original_bundle(
    root: Path, *, expected_shas: dict[str, str],
    session: str, slot: str, nonce: str,
    first_probe_seq: int, first_probe_request: str,
) -> dict[str, Any]:
    """Byte-match and continuity review, never server-origin attestation."""
    _identity(slot, nonce)
    _need(type(expected_shas) is dict
          and set(expected_shas) == set(ORIGINAL_NAMES),
          "all three independent original hash comparands required")
    _need(type(session) is str and bool(session.strip())
          and type(first_probe_seq) is int and first_probe_seq > 0
          and type(first_probe_request) is str and bool(first_probe_request),
          "unbound original session/first native observation")
    root = _safe(root, directory=True)
    _need(all((root / p).is_file() for p in ORIGINAL_NAMES),
          "required original is missing")
    _need(len({(root / p).resolve(strict=True) for p in ORIGINAL_NAMES}) == 3,
          "original file aliasing")
    server = _read_original(root, ORIGINAL_NAMES[0],
                            expected_shas[ORIGINAL_NAMES[0]], MAX_SERVER_BYTES)
    journal = _read_original(root, ORIGINAL_NAMES[1],
                             expected_shas[ORIGINAL_NAMES[1]], MAX_JOURNAL_BYTES)
    native = _read_original(root, ORIGINAL_NAMES[2],
                            expected_shas[ORIGINAL_NAMES[2]], MAX_NATIVE_BYTES)
    # Packet reviewer independently checks full native seq0..STOP and clock
    # samples. It *also* refuses a post-STOP packet or duplicate start.
    packet = review_native_original(
        root / ORIGINAL_NAMES[2],
        expected_sha256=expected_shas[ORIGINAL_NAMES[2]],
        expected_session=session,
    )
    rows = _lines(native, max_count=200_000)
    observations = [r for r in rows if r.get("type") == "observation"]
    _need(bool(observations)
          and observations[0].get("seq") == first_probe_seq
          and observations[0].get("request_id") == first_probe_request,
          "first native observation missing/foreign to issuer")
    issued = _review_issuer(
        journal, session=session, first_probe_seq=first_probe_seq,
        first_probe_request=first_probe_request,
    )
    try:
        stdout = server.decode("utf-8")
    except UnicodeError as exc:
        raise OriginalBundleRejected("server console original not UTF-8") from exc
    start_marker = f"RELAYSELF_V6_TRIAL_START_{slot}_{nonce}_NOT_ADMITTED"
    food_marker = "RELAYSELF_V6_FIRST_INVOCATION_SOURCE_NOT_ADMITTED"
    _need(stdout.count(start_marker) == 1
          and stdout.count(food_marker) == 1
          and stdout.index(start_marker) < stdout.index(food_marker),
          "source-shaped server stdout markers missing/repeated/reordered")
    # A matched capture can still be fabricated by a claimant, server output
    # can omit privileged commands, and normal server logs are not a full
    # authenticated command/score ledger. Never derive true gametime.
    return {
        "classification": "RSEE_V6_THREE_ORIGINAL_BYTES_AND_ORDER_REVIEW_ONLY",
        "source_contract_schema": SCHEMA,
        "expected_s_start_head": S_START_SOURCE_HEAD,
        "expected_s_food_head": S_ATOMIC_SOURCE_HEAD,
        "world_start_slot": slot, "session_correlation_nonce": nonce,
        "expected_session": session,
        "original_sha256_matches": {
            name: hashlib.sha256(raw).hexdigest()
            for name, raw in zip(ORIGINAL_NAMES, (server, journal, native))
        },
        "native_rows": packet["native_rows"],
        "native_packet_age_samples": packet["native_packet_age_samples"],
        **issued,
        "server_stdout_marker_order_consistent": True,
        "issuer_journal_original_matches_external_sha": True,
        "first_native_observation_correlated_in_captured_bytes": True,
        "server_output_origin_authenticated": False,
        "issuer_exclusivity_and_no_privileged_reset_attested": False,
        "server_function_parser_or_load_attested": False,
        "original_server_score_readback_attested": False,
        "true_start_or_summon_effect_tick_attested": False,
        "matched_12_arm_elapsed_world_tick_attested": False,
        "physical_execution_authorized": False, "science_g3": "NO_GO",
    }


def plan() -> dict[str, Any]:
    return {
        "classification": "RSEE_V6_PROSPECTIVE_ORIGINAL_BUNDLE_PLAN_ONLY",
        "schema": SCHEMA, "expected_originals": list(ORIGINAL_NAMES),
        "s_producer_for_this_bundle": "NOT_IMPLEMENTED",
        "any_server_originals_read": False,
        "minecraft_server_authenticity": "NOT_ATTESTED",
        "actual_world_time": "NOT_ATTESTED",
        "physical_execution_authorized": False, "science_g3": "NO_GO",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--expected-shas-json", type=Path)
    parser.add_argument("--session")
    parser.add_argument("--slot")
    parser.add_argument("--nonce")
    parser.add_argument("--first-probe-seq", type=int)
    parser.add_argument("--first-probe-request")
    args = parser.parse_args(argv)
    try:
        inputs = (args.root, args.expected_shas_json, args.session, args.slot,
                  args.nonce, args.first_probe_seq, args.first_probe_request)
        if any(x is not None for x in inputs):
            _need(all(x is not None for x in inputs),
                  "every precommitted original identity input required")
            file = _safe(args.expected_shas_json, directory=False)
            _need(file.stat().st_size <= 2048, "oversize SHA comparison manifest")
            expected = json.loads(file.read_text("utf-8"), object_pairs_hook=_unique_pairs)
            result = review_original_bundle(
                args.root, expected_shas=expected, session=args.session,
                slot=args.slot, nonce=args.nonce,
                first_probe_seq=args.first_probe_seq,
                first_probe_request=args.first_probe_request,
            )
        else:
            result = plan()
    except (OSError, UnicodeError, TypeError, ValueError) as exc:
        print(json.dumps({
            "classification": "RSEE_V6_ORIGINAL_BUNDLE_BLOCKED",
            "reason": type(exc).__name__ + ": " + str(exc),
            "physical_execution_authorized": False, "science_g3": "NO_GO",
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
