"""Offline RelayUI replay boundary tests: no Minecraft, Node or model execution."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from adapters.mineflayer import self_demo, self_replay_ui as viewer
from relay_self.persistent_cognition import save_persistent_cognition
from test_self_demo import _native_report


@pytest.fixture
def evidence(tmp_path: Path) -> Path:
    root = tmp_path / "frozen-golden"
    root.mkdir()
    report = _native_report()
    trace = self_demo.project_native_report(report)
    memory = self_demo.retain_native_observations(trace)
    (root / "native_report.json").write_text(
        json.dumps(report), encoding="utf-8",
    )
    l2 = {
        "kind": "l2_live_observer",
        "source_type": "SELF_DEMO_S60B1_LIVE_L2",
        "session": report["session_id"],
        "status": "EXPIRED_WORLD_ADVANCED",
        "source_world_seq": 6,
        "latest_world_seq": 22,
        "model_attempts": 1,
        "text_current": False,
        "text_observation_only": "read only",
        "native_l0_action_owner": "S49_NATIVE_EXISTING",
        "l0_blocked_on_l2": False,
        "l2_used_as_action": False,
        "authorized_actions": 0,
        "learning_updates": 0,
        "habit_grants": 0,
    }
    lines = [
        *trace,
        l2,
        {
            "kind": "observed_memory",
            "source_type": self_demo.SOURCE_NATIVE,
            "retained_episodes": len(memory.memories),
            "learning_preference_changed": False,
            "habit_auto_granted": False,
            "durable_file": "observed_memory.json",
        },
    ]
    (root / "self_trace.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in lines),
        encoding="utf-8",
    )
    (root / "live_l2.jsonl").write_text(
        json.dumps(l2) + "\n", encoding="utf-8",
    )
    save_persistent_cognition(root / "observed_memory.json", memory)
    return root


def test_replay_preserves_real_boundary_without_new_claims(evidence: Path) -> None:
    result = viewer.load_replay(evidence)
    assert result["qualification"] == "NATIVE_REPLAY_VALIDATED_NOT_CONTINUOUS_LIVE"
    assert [row["kind"] for row in result["events"]].count("native_observation") == 3
    assert [row["kind"] for row in result["events"]].count("decision") == 3
    assert [row["kind"] for row in result["events"]].count("native_action_outcome") == 2
    assert len(result["events"]) == 8
    assert [x["selected"] for x in result["events"] if x["kind"] == "decision"] == [
        "WAIT", "MOVE_AWAY", "MOVE_AWAY",
    ]
    assert len(result["sources"]) == 4
    assert result["l2"]["status"] == "EXPIRED_WORLD_ADVANCED"
    assert result["l2"]["text_current"] is False
    assert result["retained_observed_episodes"] == 2
    assert result["learning_updates"] == 0
    assert result["habit_grants"] == 0
    assert result["goal_success_attested"] is False


def test_cli_dry_run_never_writes_or_launches(evidence: Path, capsys) -> None:
    original = {p.name: p.read_bytes() for p in evidence.iterdir()}
    assert viewer.main(["--evidence-dir", str(evidence), "--dry-run"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["events"] == 8
    assert status["model_launched"] is False
    assert status["world_launched"] is False
    assert status["action_issued"] is False
    assert original == {p.name: p.read_bytes() for p in evidence.iterdir()}


def test_generated_replay_single_file_is_static_and_exclusive(
    evidence: Path, tmp_path: Path, capsys,
) -> None:
    output = tmp_path / "Self-1-replay.html"
    assert viewer.main([
        "--evidence-dir", str(evidence), "--output-file", str(output),
    ]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["classification"] == "NATIVE_REPLAY_VALIDATED_NOT_CONTINUOUS_LIVE"
    html = output.read_text()
    assert '<script type="application/json" id="relay-data">' in html
    assert "RELAYUI_SELF1_OFFLINE_REPLAY_V1" in html
    assert 'textContent' in html
    assert "World Replay" in html
    assert "Minecraft" in html
    assert evidence / "native_report.json" != output
    with pytest.raises(viewer.ReplayRejected, match="already exist"):
        viewer.write_replay(viewer.load_replay(evidence), evidence, output)


def test_no_output_inside_immutable_evidence(evidence: Path) -> None:
    replay = viewer.load_replay(evidence)
    with pytest.raises(viewer.ReplayRejected, match="inside source evidence"):
        viewer.write_replay(replay, evidence, evidence / "replay.html")
    assert not (evidence / "replay.html").exists()


@pytest.mark.parametrize("mutation", [
    "trace_choice",
    "trace_session",
    "trace_l2",
    "stale_marked_current",
    "l2_granted_action",
    "memory_corrupted",
    "missing_native",
    "source_symlink",
    "extra_trace",
    "duplicate_json",
])
def test_broken_or_forged_source_does_not_produce_ui(
    evidence: Path, tmp_path: Path, capsys, mutation: str,
) -> None:
    source = evidence / "self_trace.jsonl"
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    if mutation == "trace_choice":
        rows[2]["selected"] = "MOVE_AWAY"
    elif mutation == "trace_session":
        rows[0]["session"] = "foreign"
    elif mutation == "trace_l2":
        rows[-2]["status"] = "ACCEPTED_READ_ONLY_SAME_PRESENT"
    elif mutation == "stale_marked_current":
        rows[-2]["text_current"] = True
        (evidence / "live_l2.jsonl").write_text(json.dumps(rows[-2]) + "\n")
    elif mutation == "l2_granted_action":
        rows[-2]["authorized_actions"] = 1
        (evidence / "live_l2.jsonl").write_text(json.dumps(rows[-2]) + "\n")
    elif mutation == "memory_corrupted":
        (evidence / "observed_memory.json").write_text('{"memories":[]}')
    elif mutation == "missing_native":
        (evidence / "native_report.json").unlink()
    elif mutation == "source_symlink":
        source.unlink()
        source.symlink_to(tmp_path / "nowhere")
    elif mutation == "extra_trace":
        rows.append({"kind": "fabricated-success"})
    elif mutation == "duplicate_json":
        (evidence / "native_report.json").write_text('{"milestone":"S49","milestone":"FAKE"}')
    if mutation in {
        "trace_choice", "trace_session", "trace_l2",
        "stale_marked_current", "l2_granted_action", "extra_trace",
    }:
        source.write_text("".join(json.dumps(row) + "\n" for row in rows))
    output = tmp_path / "should-not-exist.html"
    assert viewer.main([
        "--evidence-dir", str(evidence), "--output-file", str(output),
    ]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["classification"] == "RELAYUI_REPLAY_SOURCE_BLOCKED"
    assert not output.exists()
    assert result["world_launched"] is False


def test_script_injection_remains_encoded_as_source_data(evidence: Path) -> None:
    x = "<img src=x onerror=alert(1)>"
    rows = [json.loads(line) for line in (
        evidence / "self_trace.jsonl"
    ).read_text().splitlines()]
    rows[-2]["text_observation_only"] = x
    (evidence / "live_l2.jsonl").write_text(json.dumps(rows[-2]) + "\n")
    (evidence / "self_trace.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows),
    )
    result = viewer.load_replay(evidence)
    html = viewer.render_replay(result)
    assert x not in html
    assert "\\u003cimg" in html
    assert "</script><script>" not in html


def test_source_file_size_and_missing_output_denied(evidence: Path, tmp_path: Path) -> None:
    report = evidence / "native_report.json"
    report.write_bytes(b" " * (viewer.MAX_SOURCE_BYTES + 1))
    with pytest.raises(viewer.ReplayRejected, match="size limit"):
        viewer.load_replay(evidence)
    with pytest.raises(viewer.ReplayRejected, match="already exist"):
        viewer.write_replay({"events": []}, evidence, report)
