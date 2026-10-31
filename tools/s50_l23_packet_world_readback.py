"""Independent DEV audit of S49/L23 Paper original + new S50 Node sidecar.

Does not execute Minecraft or assert wire delivery, server input acceptance,
World-clock alignment, Goal success, P1 recovery or L10 learning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.s50_client_packet_source import (
    inspect_s50_client_packets,
)

ORIGINALS = (
    "native_bridge_received_original.jsonl",
    "native_bridge_sent_original.jsonl",
    "native_bridge_source_receipt.json",
    "l18_s16_terminal_original.jsonl",
    "l16_pre_world_goal_plan.json",
)


def audit(
    report: Path, server_log: Path, sidecar: Path, capture_root: Path,
) -> dict[str, object]:
    saved = json.loads(report.read_bytes())
    l23 = saved.get("l23_paper", {})
    reviewed = l23.get("readback", {})
    actions = saved.get("action", [])
    if (
        saved.get("status") != "PASS"
        or saved.get("node_exit") != 0
        or saved.get("server_exit") != 0
        or l23.get("status") != "PAPER_SOURCE_SHAPE_REVIEWED_ONLY"
        or not isinstance(actions, list) or len(actions) != 1
        or not isinstance(reviewed, dict)
        or reviewed.get("accepted_goal_status") != "UNDETERMINED"
        or reviewed.get("paper_sample_count") != 8
        or reviewed.get("qualified_real_learning_pairs") != 0
        or reviewed.get("p1_wait_ticks_admitted") != 0
        or reviewed.get("physical_stability_verified") is not False
    ):
        raise ValueError("not a sealed passing S49/L23 one-Action DEV original")
    session = saved.get("session_id")
    marker = reviewed.get("marker_id")
    world = reviewed.get("paper_world")
    if (
        not all(isinstance(s, str) and s for s in (session, marker, world))
        or reviewed.get("session_id") != session
        or not marker.endswith("-" + session)
        or l23.get("marker_id") != marker
        or reviewed.get("paper_first_tick") is None
        or reviewed.get("paper_last_tick") != reviewed["paper_first_tick"] + 7
        or actions[0].get("terminal") != "outcome"
    ):
        raise ValueError("native session/marker/World source mismatch")
    original_paths = [report, server_log, sidecar]
    for name in ORIGINALS:
        source = capture_root / name
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"missing sealed S7/S16 original: {name}")
        original_paths.append(source)
    paper_original = server_log.read_bytes()
    if hashlib.sha256(paper_original).hexdigest() != reviewed.get(
        "paper_original_sha256"
    ):
        raise ValueError("Paper log does not equal L23-reviewed original hash")
    packet = inspect_s50_client_packets(
        sidecar.read_bytes(), paper_original,
        session_id=session, marker_id=marker, world=world,
    )
    return {
        "classification": (
            "DEV_PACKET_SOURCE_ONLY_NO_CLOCK_OR_WIRE_ACCEPTANCE_ATTESTATION"
        ),
        "world_session_id": session,
        "paper_world": world,
        "action_count": 1,
        "l23_paper_activity_ticks": reviewed.get("paper_activity_ticks"),
        "packet_diagnostic": packet,
        "original_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in original_paths
        },
        "effective_client_clear_tick": "NOT_ATTESTED",
        "full_tick_input_coverage": False,
        "goal_accepted": False,
        "p1_wait_ticks_admitted": 0,
        "l10_pairs_admitted": 0,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--paper-original", type=Path, required=True)
    parser.add_argument("--client-sidecar", type=Path, required=True)
    parser.add_argument("--capture-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = audit(
        args.report, args.paper_original, args.client_sidecar, args.capture_root
    )
    args.output.write_text(
        json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(data["packet_diagnostic"]["readback"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
