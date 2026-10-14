"""R V6 read-only candidate native clock producer+original-byte admission gate.

Separate source *identity* from actual full-session native stdout *bytes*.
Neither can timestamp Minecraft /summon effect or verify matched World starts.
Never starts Java, Node, Mineflayer, Minecraft or a trial.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess
from pathlib import Path
from typing import Any

S_CANDIDATE_HEAD = "67c03400a16d0170264e16884b8d82439e3a3194"
S_BLOBS = {
    "adapters/mineflayer/bridge.mjs": "f0b73706da1f735b74fa75d3210b4757ed08f62a",
    "adapters/mineflayer/v6_native_clock.mjs": "ceb40b5fc116fe47a7d70c76ac60c58271750c64",
    "adapters/mineflayer/python_protocol.py": "8f05628b4386059e5d219f8ad0bf6a14711f18b8",
    "adapters/mineflayer/package.json": "bcaea4ca15e4e2ec70b84b7d6f7a9ee70ad9da9",
}
PACKET_SOURCE = "minecraft_1_21_8_clientbound_update_time"
PACKET_PRECISION = "SERVER_UPDATE_TIME_PACKET_SAMPLE_ONLY"
MAX_NATIVE_BYTES = 16 * 1024 * 1024
MAX_LINES = 200_000
SHA = re.compile(r"[a-f0-9]{64}\Z")
DIGIT = re.compile(r"(0|[1-9][0-9]*)\Z")
SIGNED = re.compile(r"(0|-?[1-9][0-9]*)\Z")


class V6PacketRejected(ValueError):
    """A source is missing, altered, duplicated, forged or unsupported."""


def _need(ok: bool, problem: str) -> None:
    if not ok:
        raise V6PacketRejected(problem)


def _safe(path: Path, *, directory: bool) -> Path:
    _need(isinstance(path, Path) and path.is_absolute()
          and not path.is_symlink(), "absolute original non-symlink path required")
    try:
        _need(path.resolve(strict=True) == path, "noncanonical source path")
        _need(not any(p.is_symlink() for p in path.parents),
              "symlinked source ancestry")
        if directory:
            _need(path.is_dir(), "directory source required")
        else:
            _need(path.is_file() and stat.S_ISREG(path.lstat().st_mode),
                  "regular original file required")
    except OSError as exc:
        raise V6PacketRejected("source path inaccessible") from exc
    return path


def review_s_clock_source(checkout: Path) -> dict[str, Any]:
    """Independent pinned producer review, NOT a fresh Golden RSEE producer."""
    root = _safe(checkout, directory=True)
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, timeout=8,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True, text=True, check=True, timeout=8,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise V6PacketRejected("cannot establish exact clean S source") from exc
    _need(head == S_CANDIDATE_HEAD and not dirty,
          "S experimental clock checkout changed or dirty")
    for relative, expected in S_BLOBS.items():
        f = _safe(root / relative, directory=False)
        raw = f.read_bytes()
        _need(len(raw) <= 200_000, "S producer source unusually large")
        blob = hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
        ).hexdigest()
        _need(blob == expected, "S experimental native clock source differs")
    return {
        "classification": "RSEE_V6_EXPERIMENTAL_CLOCK_SOURCE_PINNED_REVIEW_ONLY",
        "s_source_head": head, "verified_blobs": len(S_BLOBS),
        "golden_rsee_source_unmodified": True,
        "original_native_bytes_verified": False,
        "native_server_packet_age_attested": False,
        "exact_console_command_effect_tick_attested": False,
        "physical_execution_authorized": False, "science_g3": "NO_GO",
    }


def _unique_pairs(rows: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in rows:
        _need(key not in out, "duplicate original JSON field")
        out[key] = value
    return out


def _unsigned(value: Any, *, allow_zero: bool = True, max_value: int = 2**63) -> int:
    _need(type(value) is str and DIGIT.fullmatch(value) is not None,
          "not an original canonical unsigned decimal")
    number = int(value)
    _need(number < max_value and (allow_zero or number > 0),
          "original unsigned decimal out of bounds")
    return number


def _signed(value: Any) -> int:
    _need(type(value) is str and SIGNED.fullmatch(value) is not None,
          "not an original canonical signed decimal")
    number = int(value)
    _need(-(2**63) <= number < 2**63, "signed native time out of bounds")
    return number


def review_native_original(
    path: Path, *, expected_sha256: str, expected_session: str,
) -> dict[str, Any]:
    """Independent byte readback with S-reported SHA as external comparison.

    Original stream identity is compared to a distinct expected SHA; this is
    not cryptographic proof of server packet origin or runtime control.
    """
    _need(type(expected_sha256) is str
          and SHA.fullmatch(expected_sha256) is not None,
          "independent SHA256 comparand required")
    _need(type(expected_session) is str and bool(expected_session.strip()),
          "independent expected session required")
    file = _safe(path, directory=False)
    _need(file.stat().st_size <= MAX_NATIVE_BYTES, "oversize native original")
    with file.open("rb") as f:
        raw = f.read(MAX_NATIVE_BYTES + 1)
    _need(len(raw) <= MAX_NATIVE_BYTES, "oversize native original")
    digest = hashlib.sha256(raw).hexdigest()
    _need(digest == expected_sha256, "native original SHA256 mismatch")
    rows = raw.splitlines()
    _need(3 <= len(rows) <= MAX_LINES, "empty/incomplete native original")
    packet_count = 0
    first_age = last_age = None
    first_host = last_host = None
    previous_age = previous_host = -1
    ack_seen = False
    ended = False
    for seq, line in enumerate(rows):
        _need(bool(line) and len(line) <= 32768, "malformed native JSONL line")
        try:
            row = json.loads(line, object_pairs_hook=_unique_pairs)
        except (ValueError, UnicodeError) as exc:
            raise V6PacketRejected("invalid original native JSON") from exc
        _need(type(row) is dict and row.get("session_id") == expected_session
              and type(row.get("seq")) is int and row["seq"] == seq,
              "native session/sequence gap, replay or foreign packet")
        kind = row.get("type")
        _need(type(kind) is str and bool(kind), "unknown native message type")
        if seq == 0:
            _need(kind == "adapter_started"
                  and row.get("mineflayer_version") == "4.39.0"
                  and type(row.get("config")) is dict
                  and row["config"].get("version") == "1.21.8",
                  "not the intended Minecraft 1.21.8 original session")
        if kind == "native_clock_packet":
            _need(set(row) == {
                "type", "session_id", "seq", "source", "observation_precision",
                "world_age_ticks", "world_day_time_raw_ticks", "tick_day_time",
                "host_monotonic_ns", "command_effect_tick_attested",
            }, "native packet has extra/missing fields")
            _need(row["source"] == PACKET_SOURCE
                  and row["observation_precision"] == PACKET_PRECISION
                  and type(row["tick_day_time"]) is bool
                  and row["command_effect_tick_attested"] is False,
                  "unqualified packet source or forged command-effect authority")
            age = _unsigned(row["world_age_ticks"])
            _signed(row["world_day_time_raw_ticks"])
            host = _unsigned(row["host_monotonic_ns"], allow_zero=False,
                             max_value=2**128)
            _need(age >= previous_age and host >= previous_host,
                  "native packet age/host monotonic clock regressed")
            previous_age, previous_host = age, host
            first_age = age if first_age is None else first_age
            first_host = host if first_host is None else first_host
            last_age, last_host = age, host
            packet_count += 1
        if kind == "shutdown_ack":
            _need(not ack_seen and not ended, "duplicate/later shutdown ACK")
            ack_seen = True
        if kind == "connection_end":
            _need(ack_seen and seq == len(rows) - 1,
                  "missing shutdown ACK or nonterminal connection_end")
            ended = True
    _need(ended and packet_count >= 2,
          "incomplete native stream or no two independent age samples")
    return {
        "classification": "RSEE_V6_PACKET_BYTES_MATCH_REVIEW_ONLY",
        "native_original_sha256": digest,
        "expected_s_session": expected_session, "native_rows": len(rows),
        "native_packet_age_samples": packet_count,
        "first_age_sample_ticks": first_age, "last_age_sample_ticks": last_age,
        "sampled_world_age_delta": last_age - first_age,
        "first_packet_host_ns": first_host, "last_packet_host_ns": last_host,
        "native_original_bytes_sha256_match": True,
        "server_packet_payload_provenance_independently_attested": False,
        "world_start_identity_at_launch_attested": False,
        "exact_console_summon_effect_age_attested": False,
        "matched_world_time_across_arms": False,
        "physical_execution_authorized": False, "science_g3": "NO_GO",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s-checkout", type=Path)
    parser.add_argument("--native-original", type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--expected-session")
    args = parser.parse_args(argv)
    try:
        if not any((args.s_checkout, args.native_original,
                    args.expected_sha256, args.expected_session)):
            result = {
                "classification": "RSEE_V6_NATIVE_PACKET_READONLY_PLAN",
                "pin_candidate_s_head": S_CANDIDATE_HEAD,
                "original_bytes": "NOT_READ",
                "world_effect_tick": "NOT_ATTESTED",
                "physical_execution_authorized": False,
                "science_g3": "NO_GO",
            }
        else:
            _need(args.s_checkout is not None, "S checkout is mandatory")
            pinned = review_s_clock_source(args.s_checkout)
            if args.native_original is None:
                _need(args.expected_sha256 is None and args.expected_session is None,
                      "original comparands without source")
                result = pinned
            else:
                _need(args.expected_sha256 is not None
                      and args.expected_session is not None,
                      "original session and SHA comparand required")
                result = {
                    **review_native_original(
                        args.native_original,
                        expected_sha256=args.expected_sha256,
                        expected_session=args.expected_session,
                    ),
                    "s_clock_candidate_head": pinned["s_source_head"],
                    "s_clock_source_blobs_verified": pinned["verified_blobs"],
                }
    except (OSError, TypeError, ValueError, UnicodeError) as exc:
        print(json.dumps({
            "classification": "RSEE_V6_PACKET_REVIEW_BLOCKED",
            "reason": type(exc).__name__ + ": " + str(exc),
            "original_bytes_attested": False,
            "command_effect_tick_attested": False,
            "physical_execution_authorized": False,
            "science_g3": "NO_GO",
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
