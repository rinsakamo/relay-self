"""Separate-process H8 original audit; never launches a World or issues effects."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from adapters.mineflayer.python_protocol import MineflayerStreamDecoder
from adapters.mineflayer.self_body_s50_l_bcg_handoff import capture_h8_preaction_sources
from tools.l_bcg_world_report_preflight import review_bcg_host_report
from tools.selfbody_l1_shadow_readback import review


def check_original_commands(report: dict, sent_original: bytes) -> None:
    """Exact original route-B requests only; reject extra reads or effects."""
    sid = report["session_id"]
    action = report["actual_native_actions"][0]["action"]
    settling = report["l22_settling"]["runtime"]["request_ids"]
    assert 3 <= len(settling) <= 6
    assert settling == [f"l22:{sid}:{action}:settle-{i + 1}" for i in range(len(settling))]
    expected = [
        {"type": "observe", "request_id": f"s49-actual:{sid}:event-{d['event_seq']}"}
        for d in report["decisions"][:2]
    ] + [
        {"type": "observe", "request_id": f"s15:{sid}:{action}:before"},
        {"type": "effect", "action_id": action, "effect": "set_control", "control": "back", "state": True},
        {"type": "effect", "action_id": action + "-s15-clear", "effect": "clear_controls"},
        {"type": "observe", "request_id": f"s15:{sid}:{action}:after"},
    ] + [{"type": "observe", "request_id": req} for req in settling] + [
        {"type": "observe", "request_id": f"l16:{sid}:{action}:goal-{i}"} for i in (1, 2)
    ] + [{"type": "observe", "request_id": f"s49-actual:{sid}:event-{report['decisions'][2]['event_seq']}"}]
    assert [json.loads(line) for line in sent_original.splitlines()] == expected


def audit(root: Path) -> dict[str, object]:
    original = review(root)
    report = json.loads((root / "s49-report.json").read_bytes())
    host = review_bcg_host_report(report)
    shadow = report["l_bcg_shadow"]
    assert shadow["original_selection"] == "WAIT"
    assert shadow["advice"] == "DEFER_UNKNOWN" and shadow["action_authority"] is False
    assert shadow["used_physical_training_worlds"] == 0
    capture = root / "capture"
    sidecar = json.loads((capture / "h8_preaction_sources.json").read_bytes())
    assert sidecar == report["l_bcg_h8_preaction"]
    native = (capture / "native_bridge_received_original.jsonl").read_bytes()
    prefix = native[:sidecar["native_prefix_bytes"]]
    assert prefix.endswith(b"\n")
    decoder = MineflayerStreamDecoder()
    frames = [decoder.decode(line.decode()) for line in prefix.splitlines()]
    move = report["decisions"][1]
    reading = next(frame for frame in frames if frame.seq == move["probe_seq"])
    expected = capture_h8_preaction_sources(reading, event_seq=move["event_seq"], native_prefix=prefix)
    assert json.loads(json.dumps(expected)) == sidecar
    assert max(frame.seq for frame in frames) < report["actual_native_actions"][0]["execution_evidence"]["before_observation"]["seq"]
    assert sidecar["native_seq"] < report["actual_native_actions"][0]["execution_evidence"]["before_observation"]["seq"]
    assert sidecar["owner_receipts"] == {} and set(sidecar["conditions"].values()) == {"UNKNOWN"}
    # The saved prefix ends before the physical action's native controls and
    # before S15/S16. Separate source order from the later report write time.
    check_original_commands(report, (capture / "native_bridge_sent_original.jsonl").read_bytes())
    sent = [json.loads(line) for line in (capture / "native_bridge_sent_original.jsonl").read_bytes().splitlines()]
    observes = [row["request_id"] for row in sent if row["type"] == "observe"]
    assert len(observes) == len(set(observes))
    assert report["real_model_calls"] == 0 and report["learning_in_world"] is False
    manifest = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(root.rglob("*")) if p.is_file()}
    return {
        "classification": "DEV_H8_ORIGINAL_CHAIN_AND_BCG_DEFER_VERIFIED",
        "original": original, "host_self_consistency": host,
        "preaction": sidecar, "l_bcg_shadow": shadow, "original_sha256": manifest,
        "worlds": 1, "actions": 1, "s16_outcomes": 1, "retries": 0,
        "additional_actions": 0, "additional_native_probes": 0,
        "model_calls": 0, "learning_updates": 0, "qualified_training_worlds": 0,
        "effective_clear": "NOT_ATTESTED", "goal": "UNDETERMINED",
        "qualification": "NO_GO", "science": "NOT_RUN",
        "ceiling": "Saved S7/S16/Paper correlation; no independent wire or physical clear attestation",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root)
    with args.output.open("x") as out:
        out.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(result["classification"])


if __name__ == "__main__":
    main()
