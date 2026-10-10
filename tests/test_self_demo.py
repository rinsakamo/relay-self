"""Product Self demo smoke + S49 real owner report boundary.

No Java/Node/Minecraft/GGUF action is executed during these tests.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from adapters.mineflayer import self_demo as demo


def _native_report() -> dict:
    sid = "real-native-session-test-record"
    d = [
        {"event_seq": 4, "entity_id": 12, "probe_seq": 6,
         "distance_m": 10.0, "selected": "WAIT", "issued": False},
        {"event_seq": 12, "entity_id": 13, "probe_seq": 14,
         "distance_m": 2.0, "selected": "MOVE_AWAY", "issued": True},
        {"event_seq": 20, "entity_id": 14, "probe_seq": 22,
         "distance_m": 2.0, "selected": "MOVE_AWAY", "issued": True},
    ]
    return {
        "milestone": "S49", "status": "PASS",
        "classification": "REAL_ONE_SESSION_L0_WAIT_TWO_AUTHORIZED_MOVES_QUALIFIED",
        "session_id": sid, "minecraft_version": "1.21.8",
        "mineflayer_version": "4.39.0",
        "retained_origin": "S19_FROZEN_SYNTHETIC_GOVERNED_REV1",
        "decisions": d,
        "source_pair_trace": [
            {"event_seq": t["event_seq"], "probe_seq": t["probe_seq"],
             "probe_entities": [{"name": "zombie", "id": t["entity_id"],
                                 "d": t["distance_m"]}]}
            for t in d
        ],
        "actual_native_actions": [
            {"event_seq": t["event_seq"], "probe_seq": t["probe_seq"],
             "terminal": "outcome", "source": sid,
             "movement_m": 0.627, "action": f"action-{i}"}
            for i, t in enumerate(d[1:], start=1)
        ],
        "real_model_calls": 0, "learning_in_world": False, "server_exit": 0,
    }


def test_synthetic_smoke_uses_actual_s10_authority_and_s11_selection():
    trace = demo.smoke_trace()
    assert len([x for x in trace if x["kind"] == "epoch"]) == 3
    assert [x["choice"] for x in trace if x["kind"] == "epoch"] == [
        "WAIT", "FLEE", "WAIT"
    ]
    assert [x["retained_revision"] for x in trace if x["kind"] == "epoch"] == [
        0, 0, 1
    ]
    assert [x["kind"] for x in trace].count("synthetic_feedback") == 1
    assert trace[-1]["actual_world_actions"] == 0
    assert trace[-1]["synthetic_learning_updates"] == 1
    assert all(x["source_type"] == demo.SOURCE_SMOKE for x in trace)
    assert trace[-1]["production_habit_granted"] is False


def test_native_projector_converts_three_existing_decisions_and_two_outcomes():
    trace = demo.project_native_report(_native_report())
    assert len(trace) == 10
    assert [x["kind"] for x in trace].count("native_observation") == 3
    assert [x["kind"] for x in trace].count("decision") == 3
    assert [x["kind"] for x in trace].count("native_action_outcome") == 2
    assert [x["selected"] for x in trace if x["kind"] == "decision"] == [
        "WAIT", "MOVE_AWAY", "MOVE_AWAY"
    ]
    assert trace[-1]["native_terminal_actions"] == 2
    assert trace[-1]["in_world_learning_updates"] == 0
    assert all(x["source_type"] == demo.SOURCE_NATIVE for x in trace)
    for item in trace:
        if item["kind"] == "native_action_outcome":
            assert not item["goal_success_attested"]
            assert not item["signed_negative_z"]
            assert not item["retained_update"]


@pytest.mark.parametrize("change", [
    {"status": "FAIL"}, {"status": "BLOCKED"},
    {"classification": "pretend-action-success"},
    {"real_model_calls": 1}, {"learning_in_world": True},
    {"session_id": ""}, {"decisions": []},
    {"actual_native_actions": []},
])
def test_owner_report_shortcut_and_fake_qualification_denied(change: dict):
    r = _native_report()
    r.update(change)
    with pytest.raises(demo.DemoRejected):
        demo.project_native_report(r)


def test_wrong_action_outcome_or_forged_source_is_denied():
    for attribute, value in (
        ("terminal", "unknown"),
        ("source", "foreign-session"),
        ("movement_m", 0.01),
        ("action", ""),
        ("event_seq", 4),
    ):
        r = _native_report()
        r["actual_native_actions"][0][attribute] = value
        with pytest.raises(demo.DemoRejected):
            demo.project_native_report(r)


def test_native_event_mismatch_and_probe_swap_fails_closed():
    for kind in ("wrong_seq", "wrong_probe", "duplicate_entity",
                 "wrong_decision", "ignored_action"):
        r = _native_report()
        if kind == "wrong_seq":
            r["decisions"][1]["event_seq"] = 4
        elif kind == "wrong_probe":
            r["source_pair_trace"][1]["probe_seq"] = 30
        elif kind == "duplicate_entity":
            r["decisions"][2]["event_seq"] = 12
        elif kind == "wrong_decision":
            r["decisions"][0]["selected"] = "MOVE_AWAY"
        else:
            r["decisions"][2]["issued"] = False
        with pytest.raises(demo.DemoRejected):
            demo.project_native_report(r)



def test_existing_persistent_cognition_retains_only_native_observations(tmp_path):
    from relay_self.persistent_cognition import (
        load_persistent_cognition,
        save_persistent_cognition,
    )

    trace = demo.project_native_report(_native_report())
    snapshot = demo.retain_native_observations(trace)
    assert len(snapshot.memories) == 2
    assert len(set(m.memory_id for m in snapshot.memories)) == 2
    assert snapshot.identity.directives
    assert snapshot.appraisal_dispositions == ()
    for item in snapshot.memories:
        obj = json.loads(item.content)
        assert obj["terminal"] == "outcome"
        assert obj["movement_m"] == 0.627
        assert obj["goal_success_attested"] is False
        assert obj["learning_feedback_qualified"] is False
        assert item.source_provenance.source == "self-demo-projected-S49-report"
    file = tmp_path / "observed_memory.json"
    save_persistent_cognition(file, snapshot)
    restored = load_persistent_cognition(file)
    assert restored == snapshot


def test_native_memory_cannot_come_from_synthetic_or_unverified_goal():
    with pytest.raises(demo.DemoRejected):
        demo.retain_native_observations(demo.smoke_trace())
    rows = list(demo.project_native_report(_native_report()))
    rows[3] = {**rows[3], "goal_success_attested": True}
    with pytest.raises(demo.DemoRejected):
        demo.retain_native_observations(tuple(rows))


def test_default_dry_run_never_issues_actions(capsys):
    assert demo.main([]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["kind"] == "ready"
    assert out["source_type"] == "NO_WORLD_USED"
    assert out["actions_issued"] == 0
    assert out["mode"] == "DRY_RUN"


def test_smoke_command_prints_jsonl_without_live_process(capsys):
    assert demo.main(["--smoke"]) == 0
    data = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(data) == len(demo.smoke_trace())
    assert data[-1]["actual_world_actions"] == 0


def test_live_without_consent_is_blocked_before_any_resources(capsys, tmp_path):
    assert demo.main(["--run-disposable", "--output-dir", str(tmp_path)]) == 2
    out = json.loads(capsys.readouterr().out)
    assert out["kind"] == "blocked"
    assert out["reason"] == "OPERATOR_CONSENT_REQUIRED"


def test_live_without_directory_is_blocked_before_node_or_java(capsys):
    assert demo.main([
        "--run-disposable", "--confirm", demo.CONFIRM
    ]) == 2
    out = json.loads(capsys.readouterr().out)
    assert out["reason"] == "OUTPUT_DIRECTORY_NOT_PREPARED"


def test_live_collision_denied_even_with_consent_and_toolchain(
    monkeypatch, tmp_path, capsys,
):
    monkeypatch.setattr(demo.shutil, "which", lambda _: "/fake/tool")
    (tmp_path / "native_report.json").write_text("do not overwrite")
    assert demo.main([
        "--run-disposable", "--confirm", demo.CONFIRM,
        "--output-dir", str(tmp_path)
    ]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "EVIDENCE_ALREADY_EXISTS"


def test_output_trace_is_new_file_only(tmp_path: Path):
    dest = tmp_path / "trace.jsonl"
    rows = demo.smoke_trace()
    demo._write_trace(dest, rows)
    written = [json.loads(s) for s in dest.read_text().splitlines()]
    assert len(written) == len(rows)
    with pytest.raises(FileExistsError):
        demo._write_trace(dest, rows)


def test_product_module_does_not_own_real_action_or_habit_authority():
    source = Path(demo.__file__).read_text(encoding="utf-8")
    for banned in (
        "MineflayerProcessSession.launch(",
        "execute_seek_step(",
        "commit_test_quorum_habit(",
        "send_set_control(",
        "model_response_to_action(",
    ):
        assert banned not in source
