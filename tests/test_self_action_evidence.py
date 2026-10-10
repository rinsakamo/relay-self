"""Product evidence retention: original decoded S15/S16 fields, not raw wire.

All physical-like fixtures here are deterministic old S17 fake sessions.
No Minecraft launch or external command occurs in these tests.
"""
from __future__ import annotations

import copy
import json
from dataclasses import replace

import pytest

import test_action_feedback_qualification as s17
import test_self_demo as demo_test
from adapters.mineflayer import self_demo
from adapters.mineflayer.self_action_evidence import (
    EVIDENCE_SCHEMA,
    NativeEvidenceRejected,
    capture_native_action_evidence,
    verify_native_action_evidence,
)


def _source():
    # Existing S17 fake issued Action and original typed S16 consequence.
    *_, consequence, _, _ = s17.executed_closed_chain()
    return consequence


def _fixture_evidence():
    original = capture_native_action_evidence(_source())
    # Explicit synthetic projection for the self-demo report fixture. NEVER a
    # replacement for a missing actual source observation in a prior run.
    report = demo_test._native_report()
    for index, action in enumerate(report["actual_native_actions"]):
        evidence = copy.deepcopy(original)
        evidence["session_id"] = report["session_id"]
        evidence["action_id"] = action["action"]
        evidence["movement_m"] = action["movement_m"]
        for name in (
            "before_observation", "dispatch_receipt",
            "cleanup_receipt", "after_observation",
        ):
            frame = evidence[name]
            frame["session_id"] = report["session_id"]
            frame["seq"] += index * 10
            frame["provenance"] = {
                "source": "mineflayer",
                "reference": f"{report['session_id']}:{frame['seq']}",
            }
        evidence["dispatch_receipt"]["action_id"] = action["action"]
        evidence["cleanup_receipt"]["action_id"] = f"{action['action']}-s15-clear"
        before = evidence["before_observation"]["snapshot"]["position"]
        after = evidence["after_observation"]["snapshot"]["position"]
        after["x"] = before["x"] + action["movement_m"]
        after["z"] = before["z"]
        verify_native_action_evidence(
            evidence, action_id=action["action"],
            session_id=report["session_id"], movement_m=action["movement_m"],
        )
        action["execution_evidence"] = evidence
    return report


def test_capture_existing_s16_typed_decoded_frames_and_recompute_movement():
    source = _source()
    evidence = capture_native_action_evidence(source)
    assert evidence["schema"] == EVIDENCE_SCHEMA
    assert evidence["session_id"] == source.session_id
    assert evidence["action_id"] == source.action_id
    assert evidence["before_observation"]["snapshot"]["position"]
    assert evidence["after_observation"]["snapshot"]["position"]
    assert evidence["dispatch_receipt"]["effect"] == "set_control"
    assert evidence["cleanup_receipt"]["effect"] == "clear_controls"
    assert [evidence[k]["seq"] for k in (
        "before_observation", "dispatch_receipt",
        "cleanup_receipt", "after_observation",
    )] == sorted(evidence[k]["seq"] for k in (
        "before_observation", "dispatch_receipt",
        "cleanup_receipt", "after_observation",
    ))
    reread = json.loads(json.dumps(evidence))
    assert reread == evidence
    verify_native_action_evidence(
        reread, action_id=source.action_id, session_id=source.session_id,
        movement_m=source.movement_distance,
    )
    assert evidence["goal_success_attested"] is False
    assert evidence["learning_feedback_qualified"] is False


def test_new_report_preserves_complete_decoded_observations_in_trace_and_memory():
    report = _fixture_evidence()
    rows = self_demo.project_native_report(report)
    assert rows[0]["action_frames_complete"] is True
    assert rows[-1]["action_frames_complete"] is True
    actions = [row for row in rows if row["kind"] == "native_action_outcome"]
    assert len(actions) == 2
    assert all(row["decoded_execution_evidence"] is not None for row in actions)
    assert all(len(row["execution_evidence_sha256"]) == 64 for row in actions)
    memory = self_demo.retain_native_observations(rows)
    for mem, action in zip(memory.memories, actions, strict=True):
        payload = json.loads(mem.content)
        assert payload["execution_evidence_sha256"] == action["execution_evidence_sha256"]
        assert payload["action_frames_complete"] is True
        assert payload["goal_success_attested"] is False


def test_old_real_report_remains_honestly_evidence_partial_without_fake_backfill():
    report = demo_test._native_report()
    rows = self_demo.project_native_report(report)
    assert rows[0]["action_frames_complete"] is False
    assert rows[-1]["action_frames_complete"] is False
    assert all(
        row["decoded_execution_evidence"] is None
        and row["execution_evidence_sha256"] is None
        for row in rows if row["kind"] == "native_action_outcome"
    )


@pytest.mark.parametrize("kind", [
    "missing", "bad_source", "bad_action", "bad_movement",
    "bad_before_x", "wrong_seq", "wrong_dispatch",
    "missing_snapshot", "wrong_cleanup", "claimed_goal",
    "claimed_feedback", "extra_field", "bad_provenance",
])
def test_unreproducible_or_forged_new_report_rejected(kind):
    report = _fixture_evidence()
    e = report["actual_native_actions"][0]["execution_evidence"]
    if kind == "missing":
        del report["actual_native_actions"][1]["execution_evidence"]
    elif kind == "bad_source":
        e["session_id"] = "other-world"
    elif kind == "bad_action":
        e["action_id"] = "other-action"
    elif kind == "bad_movement":
        e["movement_m"] += 0.1
    elif kind == "bad_before_x":
        e["before_observation"]["snapshot"]["position"]["x"] += 0.1
    elif kind == "wrong_seq":
        e["after_observation"]["seq"] = e["before_observation"]["seq"]
    elif kind == "wrong_dispatch":
        e["dispatch_receipt"]["result"] = "rejected"
    elif kind == "missing_snapshot":
        del e["after_observation"]["snapshot"]["position"]
    elif kind == "wrong_cleanup":
        e["cleanup_receipt"]["action_id"] = "other-cleanup"
    elif kind == "claimed_goal":
        e["goal_success_attested"] = True
    elif kind == "claimed_feedback":
        e["learning_feedback_qualified"] = True
    elif kind == "extra_field":
        e["source_physically_authenticated"] = True
    else:
        e["before_observation"]["provenance"]["reference"] = "forged:10"
    with pytest.raises((self_demo.DemoRejected, NativeEvidenceRejected)):
        self_demo.project_native_report(report)


def test_capture_rejects_unexecuted_s16_and_does_not_start_world():
    original = _source()
    with pytest.raises(NativeEvidenceRejected):
        capture_native_action_evidence(
            replace(original, status=type(original.status).UNDETERMINED,
                    movement_distance=None)
        )


def test_s49_only_uses_existing_closed_consequence_no_new_probe_or_action():
    from pathlib import Path
    import adapters.mineflayer.s49_normal_session_real_ci as s49

    text = Path(s49.__file__).read_text(encoding="utf-8")
    assert "capture_native_action_evidence(" in text
    assert '"execution_evidence": capture_native_action_evidence(' in text
