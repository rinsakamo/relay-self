"""Independent read-only Route B original correlation; DEV only, no typed replay."""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.l16_first_action_goal_originals import L16GoalPlan
from adapters.mineflayer.l22_post_s16_settling import inspect_l22_settling
from adapters.mineflayer.l23_paper_s7_settling import _paper_rows, inspect_l23_paper_s7
from adapters.mineflayer.m02_paper_dev.s50_live_paper_window import (
    capture_s50_live_paper_window,
    verify_s50_live_window_against_final_paper,
)
from adapters.mineflayer.normal_action import NormalWorldL0
from adapters.mineflayer.python_protocol import MineflayerObservation, MineflayerStreamDecoder
from test_postmain_two_epoch_continuation import _epoch_one
from tools.s50_l23_packet_world_readback import audit as packet_audit
from tools.s50_selfbody_motion_readback import review_originals


def review(root: Path) -> dict[str, object]:
    report = json.loads((root / "s49-report.json").read_bytes())
    capture = root / "capture"
    prefix = capture / "pre-next-l0-prefix"
    terminal_raw = (capture / "l18_s16_terminal_original.jsonl").read_bytes()
    terminal = json.loads(terminal_raw)
    sid, action = terminal["session_id"], terminal["action_id"]
    plan_source = json.loads((capture / "l16_pre_world_goal_plan.json").read_bytes())
    plan = L16GoalPlan(*(plan_source[k] for k in (
        "target_x", "target_z", "tolerance_m", "stable_probe_delta_max_m",
    )))
    paper = (root / "server.log").read_bytes()
    starts = _paper_rows(paper, "S50_DEV_WAIT_BEGIN ")
    inputs = _paper_rows(paper, "S50_DEV_INPUT_TICK ")
    args = dict(
        received_original=(prefix / "native_bridge_received_original.jsonl").read_bytes(),
        sent_original=(prefix / "native_bridge_sent_original.jsonl").read_bytes(),
        s7_receipt=json.loads((prefix / "native_bridge_source_receipt.json").read_bytes()),
        s16_original=terminal_raw, plan=plan, action_id=action, session_id=sid,
    )
    l22 = asdict(inspect_l22_settling(**args))
    l23 = asdict(inspect_l23_paper_s7(**args, paper_original=paper, expected_world=starts[0]["world"]))
    assert json.loads(json.dumps(l22)) == report["l22_settling"]["audit"]
    assert json.loads(json.dumps(l23)) == report["l23_paper"]["readback"]
    full_receipt = json.loads((capture / "native_bridge_source_receipt.json").read_bytes())
    received = (capture / "native_bridge_received_original.jsonl").read_bytes()
    sent = (capture / "native_bridge_sent_original.jsonl").read_bytes()
    for kind, raw in (("received", received), ("sent", sent)):
        assert full_receipt[kind + "_sha256"] == hashlib.sha256(raw).hexdigest()
        assert full_receipt[kind + "_bytes"] == len(raw)
        assert full_receipt[kind + "_lines"] == len(raw.splitlines())
        assert raw.startswith(args[kind + "_original"])
    decoder = MineflayerStreamDecoder()
    frames = [decoder.decode(row.decode()) for row in received.splitlines()]
    commands = [json.loads(row) for row in sent.splitlines()]
    _, committed, *_ = _epoch_one()
    policy = NormalWorldL0(sid, "escape-threat", committed.new_state, max_events=3, max_action_requests=1)
    decisions = report["decisions"]
    assert [x["selected"] for x in decisions] == ["WAIT", "MOVE_AWAY", "WAIT"]
    assert len(report["actual_native_actions"]) == 1
    native_pairs = []
    for d in decisions:
        event, probe = frames[d["event_seq"]], frames[d["probe_seq"]]
        assert isinstance(event, MineflayerObservation) and event.kind == "entities"
        assert event.request_id is None
        assert event.seq < probe.seq
        assert probe.request_id == f"s49-actual:{sid}:event-{event.seq}"
        assert commands.count({"type": "observe", "request_id": probe.request_id}) == 1
        # Original policy evaluation only; never grant or execute an Action.
        choice = policy._check(event, probe)
        assert choice.selection.value == d["selected"]
        assert choice.entity_id == d["entity_id"] and choice.probe_seq == probe.seq
        assert choice.distance_m == d["distance_m"]
        native_pairs.append({"event_seq": event.seq, "probe_seq": probe.seq,
                             "entity_id": choice.entity_id, "selected": choice.selection.value})
    assert len({d["entity_id"] for d in decisions}) == 3
    b = report["live_next_epoch"]
    assert b["post_window_world_stimulus_sent"] and b["prior_typed_identity"]
    third = frames[decisions[2]["probe_seq"]]
    assert decisions[2]["event_seq"] > b["last_prior_probe_seq"] > terminal["after_seq"]
    assert b["current_body"]["observation"]["native_seq"] == third.seq
    assert b["current_body"]["observation"]["request_id"] == third.request_id
    assert b["current_body"]["outcome"] is None
    assert b["current_world"]["observation"]["native_seq"] == third.seq
    assert b["lease"]["next_l0_provisional_paper_reads"] == 1
    assert b["lease"]["status"] == "LIVE_NEXT_EPOCH_READOUT_CONSUMED"
    window = capture_s50_live_paper_window(
        (root / "live-paper-prefix.log").read_bytes(), session_id=sid, action_id=action,
        world=starts[0]["world"], subject_uuid=inputs[0]["subject_uuid"],
    )
    assert json.loads(json.dumps(asdict(window))) == b["window"]
    assert verify_s50_live_window_against_final_paper(window, paper)
    assert b["readback"]["previous_paper_sha256"] == window.paper_prefix_sha256
    assert b["readback"]["source_status_at_decision"] == "PROVISIONAL_PAPER_ONLY"
    assert b["readback"]["full_node_trace_complete"] is False
    for k in ("extra_actions", "extra_model_calls", "learning_updates", "p1_wait_admitted",
              "l10_pairs", "s10_updates", "s11_grants"):
        assert b["readback"][k] == 0
    producer = review_originals(
        report_original=(root / "s49-report.json").read_bytes(), paper_original=paper,
        client_original=(root / "client-packet-original.jsonl").read_bytes(),
        subject_uuid=inputs[0]["subject_uuid"],
    )
    assert json.loads(json.dumps(producer)) == report["selfbody_s50_join"]["source"]
    packet = packet_audit(root / "s49-report.json", root / "server.log",
                          root / "client-packet-original.jsonl", prefix)
    footer = json.loads((root / "client-packet-original.jsonl").read_bytes().splitlines()[-1])
    assert footer["kind"] == "TRACE_END" and footer["complete"] and not footer["lost"]
    cleanup = json.loads((root / "cleanup.json").read_bytes())
    assert cleanup["runner_exit"] == 0 and cleanup["port_rebind"]
    assert cleanup["world_roots"] and all(x["removed"] for x in cleanup["world_roots"])
    assert all(x["pid_gone"] for x in cleanup["owned_processes"])
    assert report["node_exit"] == report["server_exit"] == 0
    assert report["status"] == "PASS" and b["full_node_s50_owner_pass"]
    return {"classification": "DEV_LIVE_NEXT_L0_NATIVE_EPOCH_REFERENCED_PASS",
            "l22": l22, "l23": l23, "packet": packet, "native_pairs": native_pairs,
            "full_session_s7": full_receipt, "live_window": asdict(window),
            "trace_footer": footer, "cleanup": cleanup,
            "typed_identity_scope": "Live host identity assertions; JSON is not typed authority",
            "decision_time_source": "PROVISIONAL_PAPER_ONLY", "goal": "UNDETERMINED",
            "qualification": "NO_GO", "science": "NOT_RUN"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = review(args.root)
    with args.output.open("x") as out:
        out.write(json.dumps(result, indent=2) + "\n")
    print(result["classification"])


if __name__ == "__main__":
    main()
