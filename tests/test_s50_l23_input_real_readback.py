"""Offline S50/L23 original-readback test; never starts Minecraft."""
from __future__ import annotations

import json

import pytest

from tools.s50_l23_input_real_readback import audit

MARKER = "s49-native-move-18-6b29d6fe-ea4d-41cb-8645-dd00f9c8f062"
WORLD = "6dc19601-85ef-4a4c-b900-a9dcb1162438"
SUBJECT = "01020304-0506-0708-090a-0b0c0d0e0f10"


def make_originals(tmp_path):
    capture = tmp_path / "capture"
    capture.mkdir()
    for name in (
        "native_bridge_received_original.jsonl",
        "native_bridge_sent_original.jsonl",
        "native_bridge_source_receipt.json",
        "l18_s16_terminal_original.jsonl",
        "l16_pre_world_goal_plan.json",
    ):
        (capture / name).write_text(name + "\n")
    report = tmp_path / "report.json"
    report.write_text(json.dumps({
        "status": "PASS",
        "session_id": "6b29d6fe-ea4d-41cb-8645-dd00f9c8f062",
        "actual_native_actions": [{"action": "s49-native-move-18"}],
        "node_exit": 0, "server_exit": 0,
        "l23_paper": {
            "status": "PAPER_SOURCE_SHAPE_REVIEWED_ONLY",
            "readback": {
                "marker_id": MARKER, "paper_world": WORLD,
                "accepted_goal_status": "UNDETERMINED",
                "paper_sample_count": 8,
                "paper_first_tick": 250, "paper_last_tick": 257,
                "paper_sample_state": "PAPER_SAMPLED_ACTIVITY",
                "physical_stability_verified": False,
                "p1_wait_ticks_admitted": 0,
                "qualified_real_learning_pairs": 0,
            },
        },
    }))
    log = tmp_path / "server.log"
    rows = [
        f"[INFO] S50_DEV_WAIT_BEGIN marker_id={MARKER} world={WORLD} tick=249",
    ]
    for i in range(1, 9):
        fields = {
            "marker_id": MARKER, "world": WORLD, "subject_uuid": SUBJECT,
            "tick": 249 + i, "index": i, "input_events": 0,
            "last_input_event_tick": -1, "event_overflow": "false",
            "forward": "false", "backward": "false",
            "left": "false", "right": "false", "jump": "false",
            "sneak": "false", "sprint": "false",
            "coverage": "LAST_REPORTED_INPUT_CALLBACK_SAMPLE_ONLY",
            "effective_s15_clear_tick": "NOT_ATTESTED",
        }
        rows.append("[INFO] S50_DEV_INPUT_TICK " + " ".join(
            f"{k}={v}" for k, v in fields.items()
        ))
    log.write_text("\n".join(rows) + "\n")
    return report, log, capture


def test_real_run_shape_without_promoting_input_idle(tmp_path):
    args = make_originals(tmp_path)
    result = audit(*args)
    assert result["s49_original_run"]["real_action_count"] == 1
    assert result["input_witness"]["first_tick"] == 250
    assert result["input_witness"]["last_tick"] == 257
    assert result["input_witness"]["sampled_input_active_ticks"] == ()
    assert result["input_witness"]["effective_client_clear_tick"] == "NOT_ATTESTED"
    assert not result["input_witness"]["entire_tick_input_idle"]
    assert len(result["original_sha256"]) == 7


@pytest.mark.parametrize("fault", [
    "incomplete_tick", "foreign_world", "wrong_subject", "non_pass",
    "node_not_closed", "bad_l23_claim", "missing_s16_original",
])
def test_incomplete_or_unauthorized_real_originals_rejected(tmp_path, fault):
    report, log, capture = make_originals(tmp_path)
    if fault == "incomplete_tick":
        log.write_text("\n".join(log.read_text().splitlines()[:-1]) + "\n")
    elif fault == "foreign_world":
        log.write_text(log.read_text().replace(
            "world=" + WORLD, "world=foreign", 1,
        ))
    elif fault == "wrong_subject":
        log.write_text(log.read_text().replace(
            "subject_uuid=" + SUBJECT, "subject_uuid=foreign", 1,
        ))
    elif fault == "missing_s16_original":
        (capture / "l18_s16_terminal_original.jsonl").unlink()
    else:
        data = json.loads(report.read_text())
        if fault == "non_pass":
            data["status"] = "FAIL"
        elif fault == "node_not_closed":
            data["node_exit"] = 1
        elif fault == "bad_l23_claim":
            data["l23_paper"]["readback"]["physical_stability_verified"] = True
        report.write_text(json.dumps(data))
    with pytest.raises((ValueError, OSError)):
        audit(report, log, capture)
