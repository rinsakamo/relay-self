"""Audit ONE finished S49/L23 Paper DEV run with S-owned input source.

Reads immutable original console/S7 report produced by the existing L23 runner.
This does not start worlds, issue actions or upgrade clear/Goal/P1 authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.s50_input_witness_source import (
    review_s50_input_samples,
)

BEGIN = "S50_DEV_WAIT_BEGIN "
INPUT = "S50_DEV_INPUT_TICK "


def _fields(line: str, prefix: str) -> dict[str, str]:
    if line.count(prefix) != 1:
        raise ValueError("ambiguous Paper event label")
    out: dict[str, str] = {}
    for token in line.split(prefix, 1)[1].split():
        if token.count("=") != 1:
            raise ValueError("malformed Paper event field")
        k, v = token.split("=", 1)
        if not k or not v or k in out:
            raise ValueError("duplicate/empty Paper event field")
        out[k] = v
    return out


def audit(report: Path, log: Path, capture: Path) -> dict[str, object]:
    data = json.loads(report.read_bytes())
    if (
        data.get("status") != "PASS"
        or data.get("l23_paper", {}).get("status")
        != "PAPER_SOURCE_SHAPE_REVIEWED_ONLY"
        or len(data.get("actual_native_actions", [])) != 1
        or data.get("node_exit") != 0
        or data.get("server_exit") != 0
    ):
        raise ValueError("original S49/L23 World not fully closed DEV PASS")
    raw = log.read_bytes()
    if not 0 < len(raw) <= 2_000_000:
        raise ValueError("Paper original missing/too large")
    lines = raw.decode("utf-8").splitlines()
    begin = [_fields(s, BEGIN) for s in lines if BEGIN in s]
    inputs = [_fields(s, INPUT) for s in lines if INPUT in s]
    if len(begin) != 1 or len(inputs) != 8:
        raise ValueError("Paper WAIT+input source not exactly 1+8 callbacks")
    origin = begin[0]
    if not all(origin.get(k) for k in ("marker_id", "world", "tick")):
        raise ValueError("missing Paper source identity")
    marker = origin["marker_id"]
    l23 = data["l23_paper"]["readback"]
    if (
        l23.get("marker_id") != marker
        or l23.get("paper_world") != origin["world"]
        or l23.get("accepted_goal_status") != "UNDETERMINED"
        or l23.get("paper_sample_count") != 8
        or l23.get("physical_stability_verified") is not False
        or l23.get("p1_wait_ticks_admitted") != 0
        or l23.get("qualified_real_learning_pairs") != 0
    ):
        raise ValueError("L23 source/claim ceiling disagreement")
    subject = inputs[0].get("subject_uuid")
    if not isinstance(subject, str) or not re.fullmatch(
        r"[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}", subject
    ):
        raise ValueError("Paper subject UUID not identifiable")
    start = int(origin["tick"])
    witness = review_s50_input_samples(
        raw, marker_id=marker, world=origin["world"],
        subject_uuid=subject, start_tick=start,
    )
    if (
        witness.first_tick != l23["paper_first_tick"]
        or witness.last_tick != l23["paper_last_tick"]
        or witness.entire_tick_input_idle
        or witness.p1_wait_ticks_admitted != 0
    ):
        raise ValueError("input samples not co-ticked with original L23")
    needed = (
        "native_bridge_received_original.jsonl",
        "native_bridge_sent_original.jsonl",
        "native_bridge_source_receipt.json",
        "l18_s16_terminal_original.jsonl",
        "l16_pre_world_goal_plan.json",
    )
    sha = {}
    for item in (report, log, *(capture / name for name in needed)):
        if not item.is_file():
            raise ValueError(f"missing sealed original: {item}")
        sha[str(item)] = hashlib.sha256(item.read_bytes()).hexdigest()
    return {
        "classification": (
            "DEV_WORLD_OBSERVED_INPUT_LAST_REPORTED_ONLY_"
            "EFFECTIVE_CLEAR_NOT_ATTESTED_GOAL_UNDETERMINED"
        ),
        "s49_original_run": {
            "session_id": data["session_id"],
            "real_action_count": len(data["actual_native_actions"]),
            "l23_paper_sample_state": l23["paper_sample_state"],
        },
        "input_witness": asdict(witness),
        "original_sha256": sha,
        "r_qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--capture-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.report, args.server_log, args.capture_root)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["input_witness"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
