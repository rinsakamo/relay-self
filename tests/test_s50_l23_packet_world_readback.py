"""Independent original-source review: no false effective clear or learning."""
from __future__ import annotations

import hashlib
import json

import pytest

from tools.s50_l23_packet_world_readback import audit

SID = "6b29d6fe-ea4d-41cb-8645-dd00f9c8f062"
MARKER = "s49-native-move-18-" + SID
WORLD = "6dc19601-85ef-4a4c-b900-a9dcb1162438"


def fixtures(root):
    capture = root / "capture"
    capture.mkdir()
    for name in (
        "native_bridge_received_original.jsonl",
        "native_bridge_sent_original.jsonl",
        "native_bridge_source_receipt.json",
        "l18_s16_terminal_original.jsonl",
        "l16_pre_world_goal_plan.json",
    ):
        (capture / name).write_text(name + "\n")
    paper = root / "paper.log"
    paper.write_text("".join(
        f"[INFO] S50_DEV_INPUT_TICK marker_id={MARKER} world={WORLD} "
        f"subject_uuid=same tick={250 + i} index={i + 1}\n"
        for i in range(8)
    ))
    sidecar = root / "client.jsonl"
    source = [
        {
            "revision": 1, "session_id": SID, "index": 1,
            "node_ns": "123456", "clock_scope": "NODE_ONLY",
            "server_world_tick": "NOT_OBSERVED",
            "source": "CLIENT_WRITE_RETURNED_NOT_NETWORK_DELIVERY",
            "kind": "PACKET_WRITE_RETURNED", "packet_index": 1,
            "packet_name": "position", "network_delivered": False,
            "paper_received": False,
        },
        {
            "revision": 1, "kind": "TRACE_END",
            "complete": True, "lost": False, "recorded_rows": 1,
            "input_write_authority": False, "server_packet_received": False,
            "effective_s15_clear_tick": "NOT_ATTESTED",
        },
    ]
    sidecar.write_text("".join(json.dumps(x) + "\n" for x in source))
    report = root / "report.json"
    report.write_text(json.dumps({
        "status": "PASS", "node_exit": 0, "server_exit": 0,
        "session_id": SID, "actual_native_actions": [{"terminal": "outcome"}],
        "l23_paper": {
            "status": "PAPER_SOURCE_SHAPE_REVIEWED_ONLY",
            "marker_id": MARKER,
            "readback": {
                "session_id": SID, "marker_id": MARKER,
                "paper_world": WORLD, "paper_first_tick": 250,
                "paper_last_tick": 257, "paper_sample_count": 8,
                "paper_activity_ticks": [250, 251, 252],
                "paper_original_sha256": hashlib.sha256(
                    paper.read_bytes()
                ).hexdigest(),
                "physical_stability_verified": False,
                "accepted_goal_status": "UNDETERMINED",
                "p1_wait_ticks_admitted": 0,
                "qualified_real_learning_pairs": 0,
            },
        },
    }))
    return report, paper, sidecar, capture


def test_pinned_s49_l23_and_client_source_only(tmp_path):
    report, paper, sidecar, capture = fixtures(tmp_path)
    result = audit(report, paper, sidecar, capture)
    assert result["action_count"] == 1
    assert result["l23_paper_activity_ticks"] == [250, 251, 252]
    assert result["packet_diagnostic"]["readback"]["diagnostic"] == (
        "NO_PLAYER_INPUT_WRITE_ON_OBSERVED_CLIENT_PATH"
    )
    assert result["effective_client_clear_tick"] == "NOT_ATTESTED"
    assert not result["full_tick_input_coverage"]
    assert not result["goal_accepted"]
    assert result["p1_wait_ticks_admitted"] == result["l10_pairs_admitted"] == 0
    assert len(result["original_sha256"]) == 8


@pytest.mark.parametrize("fault", [
    "status_fail", "extra_action", "no_node_clean", "false_goal",
    "different_session", "wrong_l23_hash", "sidecar_lost", "no_s16",
    "wrong_action_field",
])
def test_reject_wrong_cross_source_origin(tmp_path, fault):
    report, paper, sidecar, capture = fixtures(tmp_path)
    if fault == "wrong_l23_hash":
        paper.write_bytes(paper.read_bytes() + b"outside-original\n")
    elif fault == "sidecar_lost":
        sidecar.write_text(sidecar.read_text().replace(
            '"complete": true', '"complete": false'
        ))
    elif fault == "no_s16":
        (capture / "l18_s16_terminal_original.jsonl").unlink()
    else:
        row = json.loads(report.read_text())
        if fault == "status_fail":
            row["status"] = "FAIL"
        elif fault == "extra_action":
            row["actual_native_actions"].append({"terminal": "outcome"})
        elif fault == "no_node_clean":
            row["node_exit"] = 1
        elif fault == "false_goal":
            row["l23_paper"]["readback"]["accepted_goal_status"] = "REACHED"
        elif fault == "different_session":
            row["session_id"] = "different"
        elif fault == "wrong_action_field":
            row["action"] = row.pop("actual_native_actions")
        report.write_text(json.dumps(row))
    with pytest.raises(ValueError):
        audit(report, paper, sidecar, capture)
