"""Read-only Self event stream: one coherent World/L0/L2/Memory session.

These tests never start Minecraft, Node, GPU, llama.cpp or issue a Game Action.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from adapters.mineflayer import self_demo, self_timeline
from relay_self.persistent_cognition import save_persistent_cognition
from test_self_demo import _native_report


def _memory():
    report = _native_report()
    trace = self_demo.project_native_report(report)
    return self_demo.retain_native_observations(trace)


def _l2():
    return {
        "kind": "l2_live_observer",
        "source_type": "SELF_DEMO_S60B1_LIVE_L2",
        "session": "real-native-session-test-record",
        "native_l0_action_owner": "S49_NATIVE_EXISTING",
        "model_attempts": 1,
        "source_world_seq": 6,
        "latest_world_seq": 22,
        "text_source_seq": 6,
        "text_observation_only": "Maybe observe whether the hazard moves.",
        "text_current": False,
        "status": "EXPIRED_WORLD_ADVANCED",
        "authorized_actions": 0,
        "l2_used_as_action": False,
        "learning_updates": 0,
        "habit_grants": 0,
        "backend_stop_ack": False,
        "gpu_release_verified": False,
        "model_binary_identity_verified": False,
    }


def test_three_epochs_and_two_original_native_actions_as_readonly_timeline():
    entries = self_timeline.timeline(_native_report())
    assert [x["kind"] for x in entries] == [
        "session", "present", "selection",
        "present", "selection", "action_outcome",
        "present", "selection", "action_outcome", "summary",
    ]
    assert [x["candidate"] for x in entries if x["kind"] == "selection"] == [
        "WAIT", "MOVE_AWAY", "MOVE_AWAY",
    ]
    assert [x["probe_seq"] for x in entries if x["kind"] == "present"] == [
        6, 14, 22,
    ]
    assert all(
        x["spatial_goal_success"] == "UNKNOWN"
        and x["signed_negative_feedback"] is False
        for x in entries if x["kind"] == "action_outcome"
    )
    assert entries[0]["authority"] == "REPORTED_NOT_INDEPENDENTLY_ATTESTED"
    assert entries[0]["source_frame_status"] == "LEGACY_ACTION_FRAMES_NOT_RETAINED"
    assert entries[-1]["actual_new_minecraft_actions"] == 0
    assert entries[-1]["actual_new_model_requests"] == 0
    assert entries[-1]["observed_memory_episodes"] is None


def test_existing_owner_memory_and_live_l2_join_one_session_without_promotion():
    entries = self_timeline.timeline(
        _native_report(), live_l2=_l2(), memory=_memory(),
    )
    assert [x["kind"] for x in entries][-3:] == [
        "l2_observer", "memory", "summary",
    ]
    l2, mem, summary = entries[-3:]
    assert l2["source_world_seq"] == 6
    assert l2["latest_world_seq"] == 22
    assert not l2["text_current"]
    assert not l2["temporal_L0_L2_overlap_independently_verified"]
    assert l2["model_actions_authorized"] == 0
    assert mem["observed_action_episodes"] == 2
    assert not mem["habit_acquisition_verified"]
    assert not mem["learning_preferences_changed"]
    assert summary["l2_sidecar_present"]
    assert summary["observed_memory_episodes"] == 2
    assert not summary["production_habit_promoted"]


@pytest.mark.parametrize("field,value", [
    ("session", "foreign-world"),
    ("model_attempts", 2),
    ("source_world_seq", 55),
    ("latest_world_seq", 99),
    ("native_l0_action_owner", "L2_ISSUER"),
    ("authorized_actions", 1),
    ("learning_updates", 1),
    ("habit_grants", 1),
    ("l2_used_as_action", True),
    ("backend_stop_ack", True),
    ("gpu_release_verified", True),
    ("text_current", True),
    ("text_source_seq", 14),
    ("text_observation_only", "m" * 1001),
])
def test_advisory_witness_cannot_forge_action_learning_or_source(field, value):
    l2 = _l2()
    l2[field] = value
    with pytest.raises(self_timeline.TimelineRejected):
        self_timeline.timeline(_native_report(), live_l2=l2)


def test_foreign_or_forged_retained_memory_denied():
    original = _memory()
    from dataclasses import replace

    forged = replace(
        original.memories[0],
        content=original.memories[0].content.replace(
            '"goal_success_attested": false', '"goal_success_attested": true',
        ),
    )
    assert forged.content != original.memories[0].content
    with pytest.raises(self_timeline.TimelineRejected):
        self_timeline.timeline(
            _native_report(),
            memory=replace(original, memories=(forged, original.memories[1])),
        )
    with pytest.raises(self_timeline.TimelineRejected):
        self_timeline.timeline(
            _native_report(),
            memory=replace(
                original, identity=replace(original.identity, self_id="wrong-session"),
            ),
        )


def test_bad_original_report_never_becomes_a_timeline():
    raw = _native_report()
    raw["status"] = "FAIL"
    with pytest.raises(ValueError):
        self_timeline.timeline(raw)
    raw = _native_report()
    raw["actual_native_actions"][0]["terminal"] = "issued"
    with pytest.raises(ValueError):
        self_timeline.timeline(raw)


def test_cli_reads_existing_original_files_and_prints_jsonl_only(
    capsys, tmp_path: Path,
):
    source = tmp_path / "native_report.json"
    l2_file = tmp_path / "live_l2.jsonl"
    stored = tmp_path / "observed_memory.json"
    source.write_text(json.dumps(_native_report()), encoding="utf-8")
    l2_file.write_text(json.dumps(_l2()) + "\n", encoding="utf-8")
    save_persistent_cognition(stored, _memory())
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert self_timeline.main([
        "--native-report", str(source),
        "--live-l2", str(l2_file), "--memory", str(stored),
        "--format", "jsonl",
    ]) == 0
    data = [json.loads(x) for x in capsys.readouterr().out.splitlines()]
    assert len(data) == 12
    assert data[-1]["kind"] == "summary"
    assert all(x["schema"] == self_timeline.SCHEMA for x in data)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_cli_human_timeline_is_readable_and_missing_sources_fail_closed(
    capsys, tmp_path: Path,
):
    source = tmp_path / "native_report.json"
    source.write_text(json.dumps(_native_report()), encoding="utf-8")
    assert self_timeline.main(["--native-report", str(source)]) == 0
    content = capsys.readouterr().out
    assert "Epoch 1" in content
    assert "L0 → WAIT" in content
    assert "goal UNKNOWN" in content
    assert "no physical attestation" in content
    assert self_timeline.main([
        "--native-report", str(tmp_path / "absent"),
    ]) == 2
    denied = json.loads(capsys.readouterr().out)
    assert denied["reason"] == "SOURCE_REJECTED"
    assert denied["world_actions_issued"] == 0
