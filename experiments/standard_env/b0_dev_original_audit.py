"""R-only read-only review of S #545's 2026-10-15 B0 DEV original bytes.

This is NOT Golden World qualification, source-authenticated TCP capture,
independent ActionSupervisor reconstruction, STOP qualification, or V admission.
Default invocation performs no filesystem access. No file is ever written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.standard_env.source_handoff import (
    _physical_file, _physical_receipt_root, _unique_pairs,
)

S_HEAD = "291417539497f42269af9a15512cea320f375310"
S_COMPLETION_HEAD = "ec02b414d09fb0885eb481b1488f1a861ed73edb"
R_START_HEAD = "49592916c141bdcc58b373efeb7f3130351ed641"
GOLDEN_HEAD = "34820f6bf391c77f325d7c29d3b779a33e3ca835"
RUN_ID = "ed76bb71518a4bebbe5639e768c74a79"
SESSION = "0e177abe-88e3-498e-afc5-d850e789dc60"
FILE_SHA = {
    "native_report.native.jsonl": "0d6e5422de4e1c2b21c025f5dd7f6ca5e5f6f62034c315f1a1fec7ff077736bc",
    "native_report.commands.jsonl": "c3c49eca903e648749842290f9af33895cb6976d1b218477488e5807b6bf2ebb",
    "minecraft_server.log": "1c1acb7ae16e861e5b44b0e800ef7b65971c1d9f76a1e3a78c4323240f4207f2",
    "native_report.json": "fde569accd2e6e6d6f3ed308960ef08a59c159164b765b8c7aad0d459b7a0fec",
    "dev_receipt.json": "8da5883e71876b03dcaa45e39c11ea57156b65d7cdeb7354e8a28ff0d48f3350",
}
INDEX_SHA = "d5446025952d9f4b34619a11a43c2d34cfb1cf5ce87b5e5ae40b262df88b30df"
READBACK_SHA = "fd53e8fbe0bd372be9bec68269fd20d23b92f94fecb32c4e82632f0d81c9843e"
LINE = re.compile(r"([0-9a-f]{64})  ([A-Za-z0-9._-]+)")
MAX_FILE = 16 * 1024 * 1024


class Rejected(ValueError):
    """Source record not admissible to even the bounded DEV byte review."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise Rejected(reason)


@dataclass(frozen=True)
class Expectations:
    session: str = SESSION
    run_id: str = RUN_ID
    index_sha: str = INDEX_SHA
    readback_sha: str = READBACK_SHA
    shas: dict[str, str] | None = None
    indexed_count: int = 7
    native_count: int = 148


def read(path: Path) -> bytes:
    _physical_file(path)
    before = path.stat()
    require(before.st_size <= MAX_FILE, "oversize original")
    value = path.read_bytes()
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            and len(value) == before.st_size, "original changed during read")
    return value


def decode(raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              Rejected("nonfinite JSON")))
    except (ValueError, UnicodeError, TypeError) as exc:
        raise Rejected("invalid or duplicate-key JSON") from exc


def jsonl(raw: bytes, limit: int) -> list[dict[str, Any]]:
    lines = raw.splitlines(keepends=True)
    require(0 < len(lines) <= limit and all(
        item.endswith(b"\n") and len(item) < 1_000_000 for item in lines
    ), "missing, truncated or oversized JSONL")
    rows = [decode(item) for item in lines]
    require(all(type(item) is dict for item in rows), "nonobject JSONL")
    return rows


def inventory(frame: dict[str, Any]) -> int:
    snap = frame.get("snapshot")
    require(type(snap) is dict and type(snap.get("inventory")) is list,
            "native inventory absent")
    values = snap["inventory"]
    require(all(type(v) is dict for v in values), "malformed native inventory")
    return sum(v.get("count", 0) for v in values if v.get("name") == "rotten_flesh")


def probe(rows: list[dict[str, Any]], seq: int) -> dict[str, Any]:
    require(type(seq) is int and 0 <= seq < len(rows), "foreign native probe sequence")
    row = rows[seq]
    require(row.get("type") == "observation" and row.get("kind") == "probe",
            "reference is not an inbound native probe")
    return row


def audit(root: Path, readback: Path, expected: Expectations = Expectations()) -> dict[str, Any]:
    """Read existing frozen DEV evidence; never create an evidence/World root."""
    require(type(expected) is Expectations and expected.session == SESSION
            and expected.run_id == RUN_ID, "foreign producer identity")
    _physical_receipt_root(root)
    _physical_file(readback)
    require(not readback.is_relative_to(root) and readback != root,
            "external readback must be outside frozen original root")
    shas = expected.shas if expected.shas is not None else FILE_SHA
    raw_index = read(root / "SHA256SUMS")
    require(hashlib.sha256(raw_index).hexdigest() == expected.index_sha,
            "index SHA256 mismatch")
    lines = raw_index.decode("ascii").splitlines(keepends=True)
    require(len(lines) == expected.indexed_count
            and all(s.endswith("\n") for s in lines), "index count/truncation")
    index: dict[str, str] = {}
    for line in lines:
        m = LINE.fullmatch(line.rstrip("\n"))
        require(m is not None and m.group(2) not in index
                and m.group(2) != "SHA256SUMS", "unsafe or duplicate SHA index")
        index[m.group(2)] = m.group(1)
    require(set(shas).issubset(index) and
            all(index[name] == sha for name, sha in shas.items()),
            "indexed mandatory original SHA mismatch")
    originals = {name: read(root / name) for name in index}
    require(all(hashlib.sha256(raw).hexdigest() == index[name]
                for name, raw in originals.items()), "original SHA256 mismatch")
    raw_readback = read(readback)
    require(hashlib.sha256(raw_readback).hexdigest() == expected.readback_sha,
            "external readback SHA256 mismatch")
    require(type(decode(raw_readback)) is dict, "readback is not a JSON object")

    native = jsonl(originals["native_report.native.jsonl"], expected.native_count)
    require(len(native) == expected.native_count, "native seq count mismatch")
    for seq, row in enumerate(native):
        require(row.get("session_id") == expected.session
                and type(row.get("seq")) is int and row["seq"] == seq,
                "foreign, missing, duplicate or reordered native seq")
    require(native[0].get("type") == "adapter_started"
            and native[-2].get("type") == "shutdown_ack"
            and native[-1].get("type") == "connection_end",
            "native STOP ACK / connection end missing or misplaced")
    commands = jsonl(originals["native_report.commands.jsonl"], 4096)
    require(commands[-1].get("type") == "shutdown"
            and sum(c.get("type") == "shutdown" for c in commands) == 1,
            "outbound STOP request missing or repeated")
    effects = [c for c in commands if c.get("type") == "effect"]
    ids = [c.get("action_id") for c in effects]
    require(all(type(a) is str and a for a in ids) and len(ids) == len(set(ids)),
            "duplicate/invalid child native Action ID")
    child = [c for c in effects if c.get("effect") in ("equip_item", "consume_held")]
    require(sorted(c.get("effect") for c in child) == ["consume_held", "equip_item"]
            and child[0]["action_id"] != child[1]["action_id"],
            "missing, repeated or aliased EAT child effects")
    for c in child:
        matches = [x for x in native if x.get("type") == "effect_result"
                   and x.get("action_id") == c["action_id"]
                   and x.get("effect") == c["effect"]]
        require(len(matches) == 1 and matches[0].get("result") == "applied",
                "EAT child effect not independently observed APPLIED")

    report = decode(originals["native_report.json"])
    receipt = decode(originals["dev_receipt.json"])
    require(type(report) is dict and type(receipt) is dict, "missing report/DEV receipt")
    require(receipt.get("classification") == "DEV_ONLY"
            and receipt.get("mode") == "DEV"
            and receipt.get("scenario") == "b0-ground"
            and receipt.get("run_id") == expected.run_id
            and receipt.get("session_id") == expected.session
            and receipt.get("engineering_qualified") is False
            and receipt.get("science_success") is False
            and receipt.get("m_energy_credited") is False
            and receipt.get("g3_go") is False
            and receipt.get("stop_ack") == "UNATTESTED"
            and receipt.get("git_head") == S_HEAD
            and receipt.get("world_source") == "NEW_S51_DEV_WORLD_NOT_GOLDEN",
            "DEV scope/provenance/qualification boundary mismatch")
    require(report.get("mode") == "DEV"
            and report.get("classification") == "DEV_ONLY"
            and report.get("owner_status") == "PASS"
            and report.get("status") == "PASS"
            and report.get("stage") == "CLOSED"
            and report.get("session_id") == expected.session
            and report.get("food_source") == "ground"
            and report.get("food_item") == "rotten_flesh"
            and report.get("world_source") == "NEW_DEV_MOJANG_WORLD_NOT_RSEE_GOLDEN"
            and report.get("engineering_qualified") is False
            and report.get("grant_consumed") is False
            and report.get("server_exit") == 0 and report.get("node_exit") == 0
            and report.get("real_model_calls") == 0,
            "producer DEV / physical exit claim inconsistent")
    pickup = report.get("ground_pickup")
    require(type(pickup) is dict and pickup.get("status") == "PICKUP_SOURCE_CONSISTENT"
            and pickup.get("pickup_evidence") == "ITEM_DISAPPEARED_AND_INVENTORY_ROSE_ONLY"
            and pickup.get("pickup_inventory_delta") == 1
            and pickup.get("zombie_drop_observed") is False
            and pickup.get("item_contents_from_entity_metadata") == "UNKNOWN"
            and pickup.get("m_energy_credited") is False,
            "source-limited ground pickup inconsistent")
    moves = pickup.get("movement_outcomes")
    require(type(moves) is list and len(moves) == 2
            and len({m.get("action_id") for m in moves}) == 2,
            "not two distinct reported MOVE outcomes")
    for move in moves:
        a, b = move.get("before_seq"), move.get("after_seq")
        require(type(a) is int and type(b) is int and a < b
                and move.get("kind") == "MOVE"
                and b < len(native), "invalid reported MOVE outcome")
        probe(native, a)
        probe(native, b)
    source_seq = pickup.get("source_probe_seq")
    pickup_seq = pickup.get("pickup_probe_seq")
    before_pickup, after_pickup = probe(native, source_seq), probe(native, pickup_seq)
    require(source_seq < pickup_seq
            and inventory(before_pickup) == 0
            and inventory(after_pickup) == 1,
            "forged pickup inventory delta")

    before = report.get("before")
    after = report.get("after")
    outcome = report.get("eat_outcome")
    credit = report.get("metabolism_after_eat")
    old = report.get("metabolism_before_eat")
    require(all(type(x) is dict for x in (before, after, outcome, credit, old)),
            "missing consumption or M0 parent records")
    parent = report.get("issued_action_id")
    require(type(parent) is str and parent == "s51-eat-rotten_flesh"
            and report.get("action_terminal") == "outcome"
            and outcome.get("action_id") == parent
            and after.get("action_id") == parent
            and after.get("terminal") == "outcome",
            "UNKNOWN or foreign parent EAT Action")
    pre, post = probe(native, before.get("probe_seq")), probe(native, after.get("after_seq"))
    require(pre["seq"] < post["seq"] and pre["seq"] > pickup_seq
            and pre["snapshot"].get("food") == 13
            and post["snapshot"].get("food") == 17
            and inventory(pre) == 1 and inventory(post) == 0
            and outcome.get("food_before") == 13
            and outcome.get("food_after") == 17
            and outcome.get("count_before") == 1
            and outcome.get("count_after") == 0,
            "forged Minecraft food/rotten_flesh delta")
    require(credit.get("credited_action_id") == parent
            and credit.get("credit_count") == 1
            and credit.get("meals") == 1
            and credit.get("intake") == 4
            and credit.get("expenditure") == 0.5
            and old.get("energy") == 5.0
            and credit.get("energy") == 8.5
            and credit.get("terminal") is False,
            "missing/duplicate/foreign M0 credited EAT")
    nxt = report.get("next_native_probe")
    decision = report.get("next_l0")
    require(type(nxt) is dict and type(decision) is dict
            and nxt.get("seq") == 145
            and decision.get("probe_seq") == 145
            and decision.get("kind") == "WAIT"
            and decision.get("issued_action") is False
            and probe(native, 145).get("request_id") == "b0-next-l0-native",
            "missing next fresh native WAIT")
    require(receipt.get("dev_b0_m0_credit_count") in (None, 1)
            and receipt.get("dev_b0_next_l0_kind") in (None, "WAIT"),
            "outer DEV projection disagrees with source")
    # Never repair historical S49 zeros in the original DEV receipt.
    require(hashlib.sha256(read(root / "SHA256SUMS")).hexdigest()
            == expected.index_sha and
            hashlib.sha256(read(readback)).hexdigest() == expected.readback_sha
            and all(hashlib.sha256(read(root / name)).hexdigest() == value
                    for name, value in index.items()),
            "evidence changed between pre/post readbacks")
    return {
        "classification": "RSEE_B0_DEV_ORIGINAL_BYTES_AND_SOURCE_SHAPED_EFFECTS_REVIEW_ONLY",
        "run_id": expected.run_id, "session": expected.session,
        "reported_s_producer_head": S_HEAD, "s_completion_head": S_COMPLETION_HEAD,
        "golden_head": GOLDEN_HEAD,
        "indexed_files_checked": len(index), "native_rows": len(native),
        "native_stop_ack_seq": 146, "native_connection_end_seq": 147,
        "issued_move_reports": len(moves), "eat_parent_outcomes": 1,
        "m0_credits_reported": 1, "minecraft_food_delta": 4,
        "stop_ack_original_frame_present": True,
        "independent_normal_shutdown_qualified": False,
        "host_process_pid_port_attested": False,
        "host_git_head_independently_attested": False,
        "golden_qualified": False, "engineering_qualified": False,
        "science_go": False, "v6_science_trials": 0, "production_go": False,
        "physical_world_launches_by_reviewer": 0,
        "side_effects": "READ_ONLY_NO_WRITE_NO_PROCESS",
    }


def plan() -> dict[str, Any]:
    return {
        "classification": "PREWORLD_READY_NOT_AUTHORIZED_PENDING_OFFLINE_REVIEW",
        "dev_host_originals": "NOT_READ",
        "golden_qualified": False, "engineering_qualified": False,
        "science_go": False, "physical_execution_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--readback", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.root is None and args.readback is None:
            result = plan()
        else:
            require(args.root is not None and args.readback is not None,
                    "both original root and external readback required")
            result = audit(args.root, args.readback)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        result = {
            "classification": "RSEE_B0_DEV_READBACK_BLOCKED",
            "reason": f"{type(exc).__name__}: {exc}",
            "golden_qualified": False, "engineering_qualified": False,
            "science_go": False, "physical_execution_authorized": False,
        }
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 2 if result["classification"] == "RSEE_B0_DEV_READBACK_BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
