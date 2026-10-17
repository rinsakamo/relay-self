"""R Lane independent *read-only* B0 ground2 host-original byte review.

The immutable B0 expectations are copied from the S operator report, not
from a physical inspection by this module. This tool does not run Minecraft,
decode/reconstruct S16 authority, establish collection causation, or grant V GO.
Default invocation is a no-file-I/O plan; --root reads existing originals only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from experiments.standard_env.source_handoff import (
    _physical_file,
    _physical_receipt_root,
    _unique_pairs,
)

B0_HEAD = "2c2659010e79529f897da5c75b1974b3bd3bb57a"
B0_SESSION = "b8b9918e-07dd-43ce-b923-b5fa282ac266"
FILE_SHA = {
    "physical.json": "4c87c8815e170ea827713105c8ad2ea291cde622878e444c89dac6925e9b1d55",
    "physical.native.jsonl": "0c99ae8b7583c7709b751784802186243d383708c9589abf15b892c34a514e81",
    "physical.commands.jsonl": "29a00089a9dcb81cf77c3ab28a2dcfc3f4e5caa4017eaea852510ca00328e6f0",
    "minecraft.log": "b4814335fefa6f90dc4b789a2ff13267cbf87ffd39e6db4a3418b579ce9588d6",
}
MAX_FILE = 16 * 1024 * 1024
MAX_INDEX = 256
INDEX_LINE = re.compile(r"([0-9a-f]{64})  (.+)")


@dataclass(frozen=True)
class ExpectedB0:
    producer_head: str
    session: str
    file_shas: dict[str, str]
    index_sha: str
    index_count: int
    native_count: int
    eat_next_seqs: tuple[int, int]
    ack_seq: int
    end_seq: int


S_REPORTED = ExpectedB0(
    B0_HEAD, B0_SESSION, FILE_SHA,
    "322b693a0beb546270ebb617a1718d619ecbfa42e79a1dad022885f2ed181714",
    50, 172, (103, 169), 170, 171,
)


class B0AuditRejected(ValueError):
    """Unusable existing source bytes or a failed exact expectation."""


def _must(condition: bool, message: str) -> None:
    if not condition:
        raise B0AuditRejected(message)


def _read(root: Path, name: str) -> bytes:
    rel = PurePosixPath(name)
    _must(bool(name) and not rel.is_absolute() and ".." not in rel.parts
          and str(rel) == name and "\\" not in name, "unsafe indexed relative path")
    path = root / name
    _physical_file(path)
    _must(path.is_relative_to(root), "indexed path escapes receipt root")
    _must(path.stat().st_size <= MAX_FILE, "oversize original")
    raw = path.read_bytes()
    _must(len(raw) <= MAX_FILE, "original grew during read")
    return raw


def _json(raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              B0AuditRejected("nonfinite JSON value")))
    except (ValueError, UnicodeError, TypeError) as exc:
        raise B0AuditRejected("invalid/duplicate-key original JSON") from exc


def _lines(raw: bytes, *, max_lines: int) -> list[dict[str, Any]]:
    lines = raw.splitlines(keepends=True)
    _must(0 < len(lines) <= max_lines and all(
        row.endswith(b"\n") and 0 < len(row) <= 1024 * 1024
        for row in lines
    ), "missing/oversized/truncated original JSONL")
    parsed = [_json(row) for row in lines]
    _must(all(type(row) is dict for row in parsed), "nonobject JSONL row")
    return parsed


def _index(root: Path, expected: ExpectedB0) -> dict[str, str]:
    raw = _read(root, "SHA256SUMS")
    _must(hashlib.sha256(raw).hexdigest() == expected.index_sha,
          "S operator-reported index hash mismatch")
    try:
        lines = raw.decode("utf-8").splitlines(keepends=True)
    except UnicodeError as exc:
        raise B0AuditRejected("invalid SHA256 index encoding") from exc
    _must(len(lines) == expected.index_count and len(lines) <= MAX_INDEX,
          "SHA index entry count mismatch")
    found: dict[str, str] = {}
    for line in lines:
        _must(line.endswith("\n"), "truncated SHA index")
        hit = INDEX_LINE.fullmatch(line.rstrip("\n"))
        _must(hit is not None, "invalid SHA256SUMS entry")
        digest, name = hit.groups()
        _must(name not in found and name != "SHA256SUMS", "duplicate/self SHA entry")
        found[name] = digest
    _must(set(expected.file_shas).issubset(found), "mandatory B0 originals not indexed")
    _must(all(found[name] == sha for name, sha in expected.file_shas.items()),
          "reported mandatory SHA disagrees with index")
    for name, digest in found.items():
        _must(hashlib.sha256(_read(root, name)).hexdigest() == digest,
              "indexed original SHA256 mismatch: " + name)
    return found


def _epochs(report: dict[str, Any], expected: ExpectedB0) -> dict[str, Any]:
    _must(report.get("status") == "PASS"
          and report.get("stage") == "CLOSED"
          and report.get("food_source") == "ground2"
          and report.get("food_item") == "rotten_flesh"
          and report.get("session_id") == expected.session
          and report.get("classification")
          == "B0_TWO_OPERATOR_STAGED_GROUND_EPOCHS_ENGINEERING_ONLY",
          "producer report source/status/classification mismatch")
    _must(report.get("m_energy_credited") is True
          and report.get("server_exit") == 0 and report.get("node_exit") == 0
          and report.get("real_model_calls") == 0
          and report.get("zombie_drop_observed") is False,
          "producer report falsely claims receipts, cleanup or zombie drop")
    preflight = report.get("rsee_preflight")
    _must(type(preflight) is dict
          and preflight.get("jar_sha256")
          == "2349d9a8f0d4be2c40e7692890ef46a4b07015e7955b075460d02793be7fbbe7"
          and preflight.get("world_file_count") == 26,
          "producer report lacks qualified RSEE identity claim")
    episodes = report.get("two_ground_epochs")
    _must(type(episodes) is list and len(episodes) == 2,
          "missing two B0 epoch report entries")
    ids: set[str] = set()
    items: set[int] = set()
    movements: set[str] = set()
    ticks: list[int] = []
    for n, ep in enumerate(episodes):
        _must(type(ep) is dict and ep.get("epoch") == n
              and ep.get("stage") == "CLOSED"
              and ep.get("eat_action_terminal") == "outcome",
              "incomplete or duplicated reported epoch")
        aid = ep.get("eat_action_id")
        _must(type(aid) is str and aid == f"b0-multi-e{n}-eat-rotten_flesh"
              and aid not in ids, "missing/duplicate issued EAT ID")
        ids.add(aid)
        pickup = ep.get("ground_pickup")
        _must(type(pickup) is dict
              and pickup.get("epoch") == n
              and pickup.get("pickup_inventory_delta") == 1
              and pickup.get("zombie_drop_observed") is False
              and pickup.get("item_contents_from_entity_metadata") == "UNKNOWN",
              "reported pickup/source mismatch or unsupported causation")
        item = pickup.get("item_entity_id")
        _must(type(item) is int and item not in items, "reused/missing entity ID")
        items.add(item)
        moves = pickup.get("movement_outcomes")
        _must(type(moves) is list and len(moves) == 2,
              "missing two issued move reports")
        for m in moves:
            mid = m.get("action_id")
            _must(type(mid) is str and mid not in movements
                  and type(m.get("before_seq")) is int
                  and type(m.get("after_seq")) is int
                  and 0 <= m["before_seq"] < m["after_seq"] < expected.native_count,
                  "nonunique/invalid issued MOVE trace")
            movements.add(mid)
        eat = ep.get("eat_outcome")
        _must(type(eat) is dict and eat.get("action_id") == aid
              and eat.get("food_after", 0) > eat.get("food_before", 0)
              and eat.get("count_before", -1) - eat.get("count_after", -1) == 1,
              "reported EAT did not have a source-bound consumption delta")
        credit = ep.get("metabolism_after_credit")
        _must(type(credit) is dict
              and credit.get("credited_action_id") == aid
              and credit.get("credit_count") == n + 1
              and credit.get("meals") == n + 1
              and credit.get("intake") == 4
              and credit.get("energy") == 8.5
              and credit.get("terminal") is False
              and type(credit.get("tick")) is int,
              "missing or incorrect independently attributed M0 credit")
        ticks.append(credit["tick"])
        following = ep.get("next_l0")
        _must(type(following) is dict
              and following.get("kind") == "WAIT"
              and following.get("issued_action") is False
              and ep.get("next_native_probe", {}).get("seq")
              == expected.eat_next_seqs[n], "missing fresh post-EAT native source")
    _must(ticks == [14, 21] and len(movements) == 4,
          "reported ledger not continuous/two-epoch")
    terminal = report.get("metabolism_terminal")
    _must(type(terminal) is dict
          and terminal.get("tick") == 21 and terminal.get("meals") == 2
          and terminal.get("energy") == 8.5 and terminal.get("terminal") is False,
          "reported final body differs from epoch 2")
    return {"reported_issued_moves": len(movements),
            "reported_distinct_eats": len(ids), "reported_m0_credits": 2,
            "reported_final_tick": ticks[-1]}


def audit(root: Path, *, expected: ExpectedB0 = S_REPORTED) -> dict[str, Any]:
    """Read existing original bytes once; no write, subprocess or network."""
    _must(type(expected) is ExpectedB0
          and expected.producer_head == B0_HEAD
          and expected.session == B0_SESSION
          and expected.index_count >= len(expected.file_shas),
          "independently pinned producing HEAD/session/expectations required")
    _physical_receipt_root(root)
    index = _index(root, expected)
    native = _lines(_read(root, "physical.native.jsonl"),
                    max_lines=expected.native_count)
    _must(len(native) == expected.native_count, "native stdout frame count mismatch")
    for n, row in enumerate(native):
        _must(row.get("session_id") == expected.session
              and type(row.get("seq")) is int and row["seq"] == n,
              "foreign/replayed/gapped native session sequence")
    _must(native[0].get("type") == "adapter_started"
          and native[expected.ack_seq].get("type") == "shutdown_ack"
          and native[expected.end_seq].get("type") == "connection_end"
          and expected.end_seq == len(native) - 1
          and expected.ack_seq == len(native) - 2,
          "missing distinct native STOP ACK / connection end")
    commands = _lines(_read(root, "physical.commands.jsonl"), max_lines=4096)
    _must(sum(row.get("type") == "shutdown" for row in commands) == 1
          and commands[-1].get("type") == "shutdown",
          "missing/ambiguous outbound shutdown request")
    report = _json(_read(root, "physical.json"))
    _must(type(report) is dict, "B0 report JSON object required")
    result = _epochs(report, expected)
    return {
        "classification": "RSEE_B0_ORIGINAL_BYTES_AND_REPORTED_EPOCHS_REVIEW_ONLY",
        "producer_head_expected": expected.producer_head,
        "producer_session": expected.session,
        "index_sha256_verified": expected.index_sha,
        "indexed_files_sha256_checked": len(index),
        "native_original_rows": len(native),
        "command_original_rows": len(commands),
        "native_shutdown_ack_row": expected.ack_seq,
        "native_connection_end_row": expected.end_seq,
        **result,
        "source_scope": "MINEFLAYER_JSONL_NOT_MINECRAFT_TCP",
        "source_head_attested_from_host_git": False,
        "world_initial_physical_identity_attested": False,
        "native_collect_event_causation_attested": False,
        "typed_s16_independent_semantics_attested": False,
        "live_pid_port_cleanup_independently_attested": False,
        "v_admitted": False,
        "science_qualified": False,
        "physical_execution_authorized": False,
        "side_effects": "READ_ONLY_NO_WRITE_NO_LAUNCH",
    }


def plan() -> dict[str, Any]:
    return {
        "classification": "RSEE_B0_READONLY_AUDIT_PLAN",
        "b0_host_original_bytes": "NOT_READ",
        "v_admitted": False,
        "science_qualified": False,
        "physical_execution_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path)
    args = p.parse_args(argv)
    try:
        result = audit(args.root) if args.root is not None else plan()
    except (ValueError, TypeError, OSError, KeyError, AttributeError) as exc:
        result = {
            "classification": "RSEE_B0_ORIGINAL_READBACK_BLOCKED",
            "error": type(exc).__name__ + ":" + str(exc),
            "physical_execution_authorized": False,
            "science_qualified": False,
            "v_admitted": False,
        }
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0 if result["classification"] in {
        "RSEE_B0_READONLY_AUDIT_PLAN",
        "RSEE_B0_ORIGINAL_BYTES_AND_REPORTED_EPOCHS_REVIEW_ONLY",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
