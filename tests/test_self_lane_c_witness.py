"""Self × Lane C: only source-linked spatial evidence, never signed feedback.

Deterministic records are constructed with the real Mineflayer decoder and
actual frozen C15 transcript format; NO real Minecraft/LLM/GPU executed.
"""
from __future__ import annotations

import copy
import json
from dataclasses import asdict

import pytest

import test_ac_c_c15_goal_witness as c15
import test_self_demo as product
from adapters.mineflayer.goal_witness import EndpointReducer, SpatialContract
from adapters.mineflayer.python_protocol import parse_mineflayer_line
from adapters.mineflayer.self_lane_c_witness import (
    SCHEMA,
    observation_json,
    qualify_self_action_spatial,
)

ACTION = "c15-control-on"
STOP = ACTION + "-s15-clear"


def fixture(*, end=c15.GOAL):
    rows = c15.transcript(end)
    rows[3]["action_id"] = STOP
    spec = SpatialContract(
        c15.SESSION, ACTION, STOP,
        c15.spatial_contract().goal,
        c15.spatial_contract().alternative,
    )
    frames = []
    for row in rows[1:5]:
        msg = parse_mineflayer_line(json.dumps(row))
        frame = asdict(msg)
        frame["provenance"] = {
            "source": "mineflayer",
            "reference": f"{row['session_id']}:{row['seq']}",
        }
        frames.append(frame)
    evidence = {
        "schema": "SELF_NATIVE_ACTION_DECODED_FRAMES_V1",
        "action_id": ACTION,
        "binding_id": "synthetic-source-bound-binding",
        "action_ref": "MOVE_BACKWARD",
        "session_id": c15.SESSION,
        "status": "executed",
        "before_observation": frames[0],
        "dispatch_receipt": frames[1],
        "cleanup_receipt": frames[2],
        "after_observation": frames[3],
        "movement_m": abs(end[0] - c15.BASELINE[0]),
        "cleanup_attempted": True,
        "goal_success_attested": False,
        "learning_feedback_qualified": False,
    }
    report = {
        "status": "PASS",
        "session_id": c15.SESSION,
        "actual_native_actions": [
            {
                "action": ACTION, "terminal": "outcome",
                "source": c15.SESSION, "movement_m": evidence["movement_m"],
                "execution_evidence": evidence,
            },
        ],
    }
    return report, spec, [json.dumps(x) + "\n" for x in rows]


@pytest.mark.parametrize(("end", "expected"), [
    (c15.GOAL, "GOAL_REGION_OBSERVED"),
    (c15.ALTERNATIVE, "ALTERNATIVE_REGION_OBSERVED"),
])
def test_spatial_endpoint_when_actual_source_frames_and_two_poststop_probes_match(
    end, expected,
):
    report, spec, lines = fixture(end=end)
    result = qualify_self_action_spatial(
        report, action_id=ACTION, spec=spec, source_lines=lines,
    )
    assert result.status == expected
    assert result.reason == "SPATIAL_ENDPOINT_ONLY"
    assert result.schema == SCHEMA
    assert result.source_matches_s16
    assert result.source_sha256 is not None
    assert result.source_references == tuple(f"{c15.SESSION}:{i}" for i in range(6))
    assert result.physical_source_attested is False
    assert result.goal_success_attested is False
    assert result.signed_action_label == "BLOCKED_UNDERDETERMINED"
    assert result.s17_feedback_issued is False
    assert result.s10_updates == result.s11_habit_promotions == 0
    reread = json.loads(observation_json(result))
    assert reread["status"] == expected
    assert reread["goal_success_attested"] is False


def test_existing_self_s16_four_decoded_frames_insufficient_for_c15():
    report, spec, lines = fixture()
    # Self S49 preserves one *after* observation only, not an independent
    # second post-stop probe. This must NOT be copied or interpolated.
    outcome = qualify_self_action_spatial(
        report, action_id=ACTION, spec=spec, source_lines=lines[:-1],
    )
    assert outcome.source_matches_s16
    assert outcome.status == "UNDETERMINED"
    assert outcome.reason == "INCOMPLETE_TRANSACTION"
    assert outcome.goal_success_attested is False
    assert outcome.source_references == tuple(f"{c15.SESSION}:{i}" for i in range(5))


def test_previous_physical_report_without_frames_not_backfilled():
    r, spec, lines = fixture()
    r["actual_native_actions"][0].pop("execution_evidence")
    outcome = qualify_self_action_spatial(
        r, action_id=ACTION, spec=spec, source_lines=lines,
    )
    assert outcome.status == "UNDETERMINED"
    assert outcome.reason == "INVALID_OR_MISSING_S16_SOURCE_FRAMES"
    assert not outcome.source_matches_s16


@pytest.mark.parametrize("failure", [
    "no_source", "source_tampered", "session_conflict", "seq_gap",
    "start_ack_changed", "missing_start_ack", "s16_bad_position",
    "s16_fake_goal_success", "s16_wrong_cleanup",
    "wrong_spec_action", "wrong_spec_session", "wrong_entry_terminal",
    "missing_action", "duplicate_action", "report_failed",
    "wrong_report_session", "wrong_movement", "swapped_source_frames",
    "unsorted_source_seq", "empty_lines", "invalid_wire", "strange_source",
])
def test_no_action_goal_feedback_or_habit_from_invalid_or_unbound_source(failure):
    report, spec, lines = fixture()
    lines = list(lines)
    a = report["actual_native_actions"][0]
    e = a["execution_evidence"]
    if failure == "no_source":
        lines = None
    elif failure == "source_tampered":
        x = json.loads(lines[4])
        x["snapshot"]["position"]["x"] = 5.1
        lines[4] = json.dumps(x) + "\n"
    elif failure == "session_conflict":
        x = json.loads(lines[4])
        x["session_id"] = "another-session"
        lines[4] = json.dumps(x) + "\n"
    elif failure == "seq_gap":
        x = json.loads(lines[4])
        x["seq"] = 99
        lines[4] = json.dumps(x) + "\n"
    elif failure == "start_ack_changed":
        x = json.loads(lines[2])
        x["action_id"] = "foreign-action"
        lines[2] = json.dumps(x) + "\n"
    elif failure == "missing_start_ack":
        lines.pop(2)
    elif failure == "s16_bad_position":
        e["after_observation"]["snapshot"]["position"]["x"] = 6
    elif failure == "s16_fake_goal_success":
        e["goal_success_attested"] = True
    elif failure == "s16_wrong_cleanup":
        e["cleanup_receipt"]["action_id"] = "foreign-stop"
    elif failure == "wrong_spec_action":
        spec = SpatialContract(c15.SESSION, "foreign-action", STOP, spec.goal, spec.alternative)
    elif failure == "wrong_spec_session":
        spec = SpatialContract("other-session", ACTION, STOP, spec.goal, spec.alternative)
    elif failure == "wrong_entry_terminal":
        a["terminal"] = "unknown"
    elif failure == "missing_action":
        report["actual_native_actions"] = []
    elif failure == "duplicate_action":
        report["actual_native_actions"].append(copy.deepcopy(a))
    elif failure == "report_failed":
        report["status"] = "FAIL"
    elif failure == "wrong_report_session":
        report["session_id"] = "foreign-session"
    elif failure == "wrong_movement":
        a["movement_m"] = 2.0
    elif failure == "swapped_source_frames":
        lines[3], lines[4] = lines[4], lines[3]
    elif failure == "unsorted_source_seq":
        lines[5] = lines[4]
    elif failure == "empty_lines":
        lines = []
    elif failure == "invalid_wire":
        lines[3] = "{not-json"
    elif failure == "strange_source":
        lines = ["not even source"]
    result = qualify_self_action_spatial(
        report, action_id=ACTION, spec=spec, source_lines=lines,
    )
    assert result.status == "UNDETERMINED", failure
    assert result.goal_success_attested is False
    assert result.signed_action_label == "BLOCKED_UNDERDETERMINED"
    assert result.s17_feedback_issued is False
    assert result.s10_updates == result.s11_habit_promotions == 0


def test_no_live_world_l2_or_native_action_runner_imported():
    import inspect

    import adapters.mineflayer.self_lane_c_witness as link

    text = inspect.getsource(link)
    assert "from adapters.mineflayer.s49_normal_session_real_ci import" not in text
    assert "from adapters.mineflayer.self_demo import" not in text
    assert "from relay_self.learning import" not in text
    assert "subprocess" not in text
    assert "WorldConsequence" not in text
    assert product._native_report()["actual_native_actions"][0]["terminal"] == "outcome"
    assert hasattr(EndpointReducer, "qualify")
