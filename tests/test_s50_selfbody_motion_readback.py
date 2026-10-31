"""Post-exit S50 -> SelfBody candidate projection is source-only."""
from __future__ import annotations

import json

import pytest

from test_s50_selfbody_motion_source import ACTION, SID, UUID, client, l23, paper
from tools.s50_selfbody_motion_readback import review_originals


def report_bytes(paper_raw: bytes, *, status: str = "PASS",
                 goal: str = "UNDETERMINED") -> bytes:
    source = l23(paper_raw)
    source["accepted_goal_status"] = goal
    return json.dumps({
        "status": status,
        "session_id": SID,
        "node_exit": 0, "server_exit": 0,
        "actual_native_actions": [{"action": ACTION, "terminal": "outcome"}],
        "l23_paper": {
            "status": "PAPER_SOURCE_SHAPE_REVIEWED_ONLY",
            "readback": source,
        },
    }).encode()


def review(*, report=None, paper_raw=None, node_raw=None, uuid=UUID):
    po = paper() if paper_raw is None else paper_raw
    return review_originals(
        report_original=report_bytes(po) if report is None else report,
        paper_original=po, client_original=client() if node_raw is None else node_raw,
        subject_uuid=uuid,
    )


def test_one_dev_original_yields_candidate_not_selfbody_world_truth():
    record = review()
    assert record["source_classification"] == "S50_TO_SELFBODY_CANDIDATE_READ_ONLY"
    body = record["physical_body_diagnostic"]
    assert body["paper_world_uuid"] != body["session_id"]
    assert body["observed_motion_while_reported_input_off_ticks"] == [251, 252]
    assert body["cross_clock_alignment"] == "NOT_ATTESTED"
    assert body["effective_s15_clear_world_tick"] == "NOT_ATTESTED"
    assert record["selfbody_native_present_admitted"] is False
    assert record["physical_wait_admitted"] is False
    assert record["goal_admitted"] is False
    assert record["learning_updates"] == 0


@pytest.mark.parametrize("fault", [
    "missing_action", "second_action", "wrong_session", "node_failed",
    "wrong_report_status", "false_goal", "changed_paper", "wrong_subject",
])
def test_invalid_owner_result_fails_without_minting_body_observation(fault):
    po = paper()
    original = json.loads(report_bytes(po))
    if fault == "missing_action":
        original["actual_native_actions"] = []
    elif fault == "second_action":
        original["actual_native_actions"].append({"action": "x", "terminal": "outcome"})
    elif fault == "wrong_session":
        original["session_id"] = "foreign"
    elif fault == "node_failed":
        original["node_exit"] = 3
    elif fault == "wrong_report_status":
        original["status"] = "FAIL"
    elif fault == "false_goal":
        original["l23_paper"]["readback"]["accepted_goal_status"] = "REACHED"
    elif fault == "changed_paper":
        po += b"\nchanged original\n"
    elif fault == "wrong_subject":
        pass
    with pytest.raises(ValueError):
        review(
            report=json.dumps(original).encode(), paper_raw=po,
            uuid="wrong-subject" if fault == "wrong_subject" else UUID,
        )
