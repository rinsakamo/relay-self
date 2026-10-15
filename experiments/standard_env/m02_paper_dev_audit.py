"""R-owned read-only inspection of S's M0.2 Paper physical DEV originals.

No Paper launch, profile calibration, qualification, source-origin attestation,
scientific inference, or promotion of B0/M0.1 to Paper metabolism.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import stat
from pathlib import Path
from typing import Any

S_SOURCE_HEAD = "52d9bbf1b4ee2e8ff810d213e36d0caf347652ee"
M_SOURCE_HEAD = "4c2f549c6b9ed3fbe2ee04230526ac5577da8feb"
ORIGINAL_SHA256 = {
    "paper_server.log": "61b5d9ff7505b93cbaf6944365d7959d60f8697b795786141cccdfd5cb3692a6",
    "original_native.jsonl": "e95c8fadf641d37099601e12e9d546d7e581b78601a3ff5c1a90c1984614a7f3",
    "owner_commands.jsonl": "d81b0242a8ab7a68faf1ba8d6b845c3f27e19598a96716c247d456d2fb0",
}
MOVEMENT = re.compile(
    r"\bM02_DEV_MOTION id=(\d+) reason=(\w+) blocks=([0-9.eE+-]+) "
    r"billed=([0-9.eE+-]+) cumulative_blocks=([0-9.eE+-]+) "
    r"cumulative_billed=([0-9.eE+-]+)"
)
EVENT = re.compile(
    r"\bM02_DEV_EVENT id=(\d+) reason=(\w+) "
    r"original=([0-9.eE+-]+) replaced=([0-9.eE+-]+)"
)
BODY = re.compile(r"\bM02_DEV_BODY sampled_tick=(\d+) .*exhaustion=([0-9.eE+-]+)")
MAX_FILE = 32 * 1024 * 1024


class Rejected(ValueError):
    """Original bytes or source-shaped physical observation not admissible."""


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise Rejected(msg)


def finite(x: object) -> float:
    require(type(x) in (float, int) and math.isfinite(x) and x >= 0,
            "nonfinite/negative physical scalar")
    return float(x)


def number(s: str) -> float:
    try:
        return finite(float(s))
    except ValueError as exc:
        raise Rejected("invalid finite physical scalar") from exc


def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, value in pairs:
        require(k not in out, "duplicate JSON key")
        out[k] = value
    return out


def decode(raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              Rejected("nonfinite JSON")))
    except (UnicodeError, ValueError, TypeError) as exc:
        raise Rejected("invalid JSON original") from exc


def read_original(path: Path) -> bytes:
    require(path.is_file() and not path.is_symlink()
            and stat.S_ISREG(path.lstat().st_mode), "nonregular original")
    a = path.stat()
    require(a.st_size <= MAX_FILE, "oversized original")
    raw = path.read_bytes()
    b = path.stat()
    require(len(raw) == a.st_size
            and (a.st_dev, a.st_ino, a.st_size, a.st_mtime_ns)
            == (b.st_dev, b.st_ino, b.st_size, b.st_mtime_ns),
            "original changed during read")
    return raw


def rows(raw: bytes) -> list[dict[str, Any]]:
    lines = raw.splitlines(keepends=True)
    require(0 < len(lines) <= 10000 and all(x.endswith(b"\n")
            and len(x) < 1_000_000 for x in lines), "truncated JSONL")
    result = [decode(x) for x in lines]
    require(all(type(x) is dict for x in result), "invalid JSONL frame")
    return result


def probe(native: list[dict[str, Any]], seq: int) -> dict[str, Any]:
    require(type(seq) is int and 0 <= seq < len(native), "foreign probe seq")
    frame = native[seq]
    require(frame.get("type") == "observation" and frame.get("kind") == "probe",
            "not an original native probe")
    require(type(frame.get("snapshot")) is dict, "missing probe snapshot")
    return frame


def stock(frame: dict[str, Any], item: str) -> int:
    items = frame["snapshot"].get("inventory")
    require(type(items) is list and all(type(i) is dict for i in items),
            "native inventory malformed")
    total = 0
    for row in items:
        if row.get("name") == item:
            n = row.get("count")
            require(type(n) is int and n >= 0, "native stock invalid")
            total += n
    return total


def inspect(log: bytes, native_raw: bytes, command_raw: bytes,
            report: dict[str, Any]) -> dict[str, Any]:
    """Independently recompute source-shaped facts; do not trust report PASS."""
    require(type(report) is dict
            and report.get("milestone") == "M0.2_PAPER_DEV"
            and report.get("classification") == "M02_PAPER_DEV_ONLY_PHYSICS_OBSERVED"
            and report.get("status") == "PASS"
            and report.get("owner_status") == "PASS"
            and report.get("physical_world") == "STARTED_NEW_DEV_PAPER"
            and report.get("minecraft_version") == "1.21.8"
            and report.get("steak") == "cooked_beef"
            and report.get("m0_virtual_ledger_used") is False
            and report.get("qualified") is False
            and report.get("science_go") is False
            and report.get("production_go") is False
            and report.get("node_exit") == 0
            and report.get("java_exit") == 0
            and report.get("port_released_after_shutdown") is True,
            "not a closed unqualified DEV physical producer report")

    original_log = log.decode("utf-8")
    require(original_log.count("M02_DEV_ONLY: candidate physics") == 1,
            "plugin source startup count not one")
    walk_events: list[tuple[int, float, float]] = []
    motion: list[tuple[int, float, float]] = []
    bodies: list[tuple[int, float]] = []
    for line in original_log.splitlines():
        e = EVENT.search(line)
        if e and e.group(2) == "WALK":
            walk_events.append((int(e.group(1)), number(e.group(3)),
                                number(e.group(4))))
        m = MOVEMENT.search(line)
        if m and m.group(2) == "WALK":
            motion.append((int(m.group(1)), number(m.group(3)),
                           number(m.group(4))))
            # Reject forged independently inconsistent cumulative telemetry.
            billed_blocks = sum(x[1] for x in motion)
            billed_amount = sum(x[2] for x in motion)
            require(math.isclose(billed_blocks, number(m.group(5)),
                                 abs_tol=1e-7, rel_tol=1e-7)
                    and math.isclose(billed_amount, number(m.group(6)),
                                     abs_tol=1e-7, rel_tol=1e-7),
                    "packet cumulative movement disagrees")
        b = BODY.search(line)
        if b:
            bodies.append((int(b.group(1)), number(b.group(2))))
    require(walk_events and motion and bodies, "missing native Paper evidence")
    require(all(original == 0 and applied == 0 for _, original, applied in walk_events),
            "native WALK event not replacement-zero")
    require([x[0] for x in motion] == list(range(1, len(motion) + 1)),
            "missing/duplicate motion packet ID")
    require(len({x[0] for x in walk_events}) == len(walk_events),
            "repeated native event ID")
    require(all(0 < x[1] <= 1 for x in motion), "unbounded packet displacement")
    total_blocks = sum(x[1] for x in motion)
    total_cost = sum(x[2] for x in motion)
    require(0.5 < total_blocks < 2
            and math.isclose(total_cost, total_blocks * 0.01,
                             abs_tol=1e-7, rel_tol=1e-7),
            "observed distance/exhaustion mismatch")
    require(any(tick == 20 for tick, _ in bodies)
            and all(bodies[i][0] < bodies[i + 1][0]
                    for i in range(len(bodies) - 1)),
            "missing or reordered World tick sample")
    native = rows(native_raw)
    session = report.get("source_session_id")
    require(type(session) is str and session
            and all(x.get("session_id") == session
                    and type(x.get("seq")) is int and x["seq"] == i
                    for i, x in enumerate(native)), "foreign/missing native seq")
    require(native[0].get("type") == "adapter_started"
            and native[-2].get("type") == "shutdown_ack"
            and native[-1].get("type") == "connection_end",
            "missing raw native STOP")
    commands = rows(command_raw)
    require(commands[-1].get("type") == "shutdown"
            and sum(c.get("type") == "shutdown" for c in commands) == 1,
            "not a single outbound STOP")
    effects = [c for c in commands if c.get("type") == "effect"]
    ids = [c.get("action_id") for c in effects]
    require(all(type(x) is str and x for x in ids)
            and len(ids) == len(set(ids)), "duplicate issued native effects")
    move = report.get("movement")
    eat = report.get("eating")
    require(type(move) is dict and type(eat) is dict
            and move.get("source_session") == session
            and eat.get("source_session") == session
            and move.get("action_id") == "m02-paper-walk-1"
            and move.get("action_state") == "outcome"
            and move.get("requested_max_step_blocks") == 1.0
            and finite(move.get("observed_progress_blocks")) > 0.05
            and eat.get("action_id") == "m02-paper-eat-steak-1"
            and eat.get("action_state") == "outcome"
            and eat.get("virtual_energy_credit") == 0,
            "S50/S51 qualified authority not reported")
    first = probe(native, move.get("source_before_seq"))
    last = probe(native, move.get("source_after_seq"))
    require(first["seq"] < last["seq"], "MOVE probe order")
    outcome = eat.get("native_outcome")
    require(type(outcome) is dict
            and outcome.get("action_id") == eat["action_id"]
            and outcome.get("session_id") == session
            and outcome.get("consumed_item") == "cooked_beef"
            and outcome.get("count_before") == 3
            and outcome.get("count_after") == 2
            and outcome.get("food_before") == 13
            and outcome.get("food_after") == 20,
            "native EAT report did not show steak/food")
    equip_id = eat["action_id"] + "-equip"
    consume_id = eat["action_id"] + "-consume"
    for effect, action_id in [("equip_item", equip_id),
                              ("consume_held", consume_id)]:
        require(sum(c.get("effect") == effect and c.get("action_id") == action_id
                    for c in effects) == 1
                and sum(n.get("type") == "effect_result"
                        and n.get("effect") == effect
                        and n.get("action_id") == action_id
                        and n.get("result") == "applied" for n in native) == 1,
                "missing source-correlated EAT child effect")
    after = probe(native, outcome.get("after_probe_seq"))
    require(after["snapshot"].get("food") == 20
            and stock(after, "cooked_beef") == 2
            and after["seq"] > last["seq"], "EAT not supported by fresh native")
    require(finite(eat.get("saturation_after")) >=
            finite(eat.get("saturation_before")), "no saturation recovery")
    return {
        "classification": "RSEE_M02_PAPER_DEV_ORIGINAL_SOURCE_REVIEW_ONLY",
        "s_source_head": S_SOURCE_HEAD,
        "m_reference_head": M_SOURCE_HEAD,
        "native_rows": len(native),
        "session_id": session,
        "paper_walk_events": len(walk_events),
        "observed_motion_packets": len(motion),
        "observed_motion_blocks": total_blocks,
        "recomputed_walk_exhaustion": total_cost,
        "native_stop_ack_seq": native[-2]["seq"],
        "native_connection_end_seq": native[-1]["seq"],
        "observed_native_steak_eat": True,
        "strict_pickup_causality": "NOT_TESTED",
        "host_cleanup_independently_attested": False,
        "paper_source_independently_qualified": False,
        "engineering_qualified": False,
        "science_go": False,
        "production_go": False,
        "physical_world_launches_by_reviewer": 0,
    }


def audit(root: Path) -> dict[str, Any]:
    """Read pinned DEV original bytes without modifying them."""
    require(root.is_dir() and not root.is_symlink()
            and all(not p.is_symlink() for p in root.parents),
            "unsafe/foreign root")
    originals = {name: read_original(root / name) for name in ORIGINAL_SHA256}
    require(all(hashlib.sha256(originals[name]).hexdigest() == digest
                for name, digest in ORIGINAL_SHA256.items()),
            "pinned original SHA256 mismatch")
    report_raw = read_original(root / "m02_report.json")
    report = decode(report_raw)
    require(type(report) is dict, "invalid report")
    hashes = report.get("evidence_hashes")
    require(type(hashes) is dict and all(hashes.get(name) == digest
            for name, digest in ORIGINAL_SHA256.items()), "owner hashes disagree")
    checked = inspect(originals["paper_server.log"],
                      originals["original_native.jsonl"],
                      originals["owner_commands.jsonl"], report)
    require(all(hashlib.sha256(read_original(root / name)).hexdigest() == digest
                for name, digest in ORIGINAL_SHA256.items())
            and hashlib.sha256(read_original(root / "m02_report.json")).digest()
            == hashlib.sha256(report_raw).digest(), "original changed after audit")
    checked["original_sha256"] = dict(ORIGINAL_SHA256)
    return checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-root", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.original_root is None:
            result = {"classification": "M02_READBACK_NOT_RUN_NO_ORIGINAL_ROOT",
                      "engineering_qualified": False, "science_go": False,
                      "physical_world_launches_by_reviewer": 0}
        else:
            result = audit(args.original_root)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result = {"classification": "M02_DEV_ORIGINAL_READBACK_BLOCKED",
                  "reason": f"{type(exc).__name__}: {exc}",
                  "engineering_qualified": False, "science_go": False,
                  "physical_world_launches_by_reviewer": 0}
    print(json.dumps(result, sort_keys=True))
    return 2 if result["classification"] == "M02_DEV_ORIGINAL_READBACK_BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
