"""Self + C15 read-only timeline, source and privilege boundary tests.

No Node, Java, Minecraft, GPU, LLM POST or Action issuer is executed.
"""
from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from adapters.mineflayer import self_demo, self_lane_c_timeline as joined
from adapters.mineflayer.self_lane_c_witness import (
    SCHEMA,
    SelfSpatialObservation,
)
from adapters.mineflayer.self_timeline import SCHEMA as TIMELINE_SCHEMA
from relay_self.persistent_cognition import save_persistent_cognition
from test_self_action_evidence import _fixture_evidence
from test_self_demo import _native_report
from test_self_timeline import _l2


def _questions(report):
    sid = report["session_id"]
    return {
        "schema": joined.SPATIAL_QUESTIONS_SCHEMA,
        "session_id": sid,
        "questions": [
            {
                "action_id": action["action"],
                "goal": {"low": [50, 62, 20], "high": [52, 66, 22]},
                "alternative": {
                    "low": [-52, 62, 20], "high": [-50, 66, 22],
                },
            }
            for action in report["actual_native_actions"]
        ],
    }


def test_product_timeline_retains_all_l0_l2_memory_and_c15_unknown():
    report = _fixture_evidence()
    memory = self_demo.retain_native_observations(
        self_demo.project_native_report(report)
    )
    sidecar = _l2()
    sidecar["session"] = report["session_id"]
    rows = joined.timeline_with_spatial(
        report, questions=_questions(report),
        memory=memory, live_l2=sidecar,
    )
    assert len([r for r in rows if r["kind"] == "selection"]) == 3
    assert len([r for r in rows if r["kind"] == "action_outcome"]) == 2
    assert len([r for r in rows if r["kind"] == "lane_c_spatial_observation"]) == 2
    assert len([r for r in rows if r["kind"] == "memory"]) == 1
    assert len([r for r in rows if r["kind"] == "l2_observer"]) == 1
    assert rows[-1]["kind"] == "summary"
    assert rows[-1]["lane_c_regions_observed"] == ["UNDETERMINED"] * 2
    assert rows[-1]["lane_c_spatial_events"] == 2
    assert rows[-1]["observed_memory_episodes"] == 2
    assert rows[-1]["actual_new_minecraft_actions"] == 0
    assert rows[-1]["actual_new_model_requests"] == 0
    assert not rows[-1]["lane_c_physical_goal_attested"]
    assert not rows[-1]["lane_c_s17_feedback_issued"]
    for row in rows:
        if row["kind"] == "action_outcome":
            assert row["spatial_goal_success"] == "UNKNOWN"
        if row["kind"] == "lane_c_spatial_observation":
            assert row["schema"] == TIMELINE_SCHEMA
            assert row["region_reason"] == "NO_COMPLETE_ORIGINAL_BRIDGE_JSONL"
            assert not row["physical_source_attested"]
            assert not row["goal_success_attested"]
            assert row["signed_action_label"] == "BLOCKED_UNDERDETERMINED"
            assert row["s10_updates"] == row["s11_habit_promotions"] == 0
            assert not row["s17_feedback_issued"]


def test_retrospective_observed_region_still_does_not_promote_goal(monkeypatch):
    report = _fixture_evidence()

    def fake_witness(_report, *, action_id, spec, source_lines):
        assert spec.start_action_id == action_id
        return SelfSpatialObservation(
            schema=SCHEMA, status="GOAL_REGION_OBSERVED",
            reason="SPATIAL_ENDPOINT_ONLY", session_id=report["session_id"],
            action_id=action_id, source_references=("fixture:1",),
            source_sha256="0" * 64, source_matches_s16=True,
        )

    monkeypatch.setattr(joined, "qualify_self_action_spatial", fake_witness)
    rows = joined.timeline_with_spatial(
        report, questions=_questions(report),
    )
    assert all(
        r["spatial_goal_success"] == "UNKNOWN"
        for r in rows if r["kind"] == "action_outcome"
    )
    values = [r for r in rows if r["kind"] == "lane_c_spatial_observation"]
    assert len(values) == 2
    assert all(r["region_status"] == "GOAL_REGION_OBSERVED" for r in values)
    assert all(
        r["question_origin"] == "CALLER_SUPPLIED_RETROSPECTIVE_NOT_PRECOMMITTED_GOAL"
        and not r["goal_success_attested"]
        and not r["s17_feedback_issued"]
        for r in values
    )
    assert rows[-1]["lane_c_regions_observed"] == ["GOAL_REGION_OBSERVED"] * 2
    assert rows[-1]["world_goal_success_attested"] is False


@pytest.mark.parametrize("failure", [
    "wrong_session", "wrong_schema", "one_action", "duplicate_action",
    "foreign_action", "missing_action", "extra_field", "overlap_regions",
    "bad_geometry", "bool_coordinate", "no_questions",
])
def test_foreign_retrospective_spatial_questions_fail_closed(failure):
    report = _fixture_evidence()
    questions = _questions(report)
    entries = questions["questions"]
    if failure == "wrong_session":
        questions["session_id"] = "another-session"
    elif failure == "wrong_schema":
        questions["schema"] = "UNTRUSTED"
    elif failure == "one_action":
        entries.pop()
    elif failure == "duplicate_action":
        entries[1]["action_id"] = entries[0]["action_id"]
    elif failure == "foreign_action":
        entries[0]["action_id"] = "other-action"
    elif failure == "missing_action":
        entries[0].pop("action_id")
    elif failure == "extra_field":
        entries[0]["automatic_habit"] = True
    elif failure == "overlap_regions":
        entries[0]["alternative"] = copy.deepcopy(entries[0]["goal"])
    elif failure == "bad_geometry":
        entries[0]["goal"]["low"] = [1, 2]
    elif failure == "bool_coordinate":
        entries[0]["goal"]["low"][0] = True
    elif failure == "no_questions":
        questions["questions"] = []
    with pytest.raises(ValueError):
        joined.timeline_with_spatial(report, questions=questions)


def test_legacy_report_is_visible_but_has_no_c15_promotion():
    report = _native_report()
    rows = joined.timeline_with_spatial(report, questions=_questions(report))
    assert len([r for r in rows if r["kind"] == "lane_c_spatial_observation"]) == 2
    assert all(
        r["region_reason"] == "INVALID_OR_MISSING_S16_SOURCE_FRAMES"
        for r in rows if r["kind"] == "lane_c_spatial_observation"
    )


def test_cli_uses_only_saved_files_without_mutating_evidence(
    capsys, tmp_path: Path,
):
    report = _fixture_evidence()
    report_path = tmp_path / "native_report.json"
    questions_path = tmp_path / "questions.json"
    memory_path = tmp_path / "memory.json"
    l2_path = tmp_path / "l2.jsonl"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    questions_path.write_text(json.dumps(_questions(report)), encoding="utf-8")
    memory = self_demo.retain_native_observations(self_demo.project_native_report(report))
    save_persistent_cognition(memory_path, memory)
    sidecar = _l2()
    sidecar["session"] = report["session_id"]
    l2_path.write_text(json.dumps(sidecar) + "\n", encoding="utf-8")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    argv = [
        "--native-report", str(report_path),
        "--spatial-questions", str(questions_path),
        "--live-l2", str(l2_path),
        "--memory", str(memory_path), "--format", "jsonl",
    ]
    assert joined.main(argv) == 0
    lines = capsys.readouterr().out.splitlines()
    rows = [json.loads(x) for x in lines]
    assert rows[-1]["lane_c_spatial_events"] == 2
    assert rows[-1]["l2_sidecar_present"]
    assert len([r for r in rows if r["kind"] == "lane_c_spatial_observation"]) == 2
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
    assert joined.main(argv[:-2] + ["--format", "text"]) == 0
    out = capsys.readouterr().out
    assert "UNDETERMINED" in out and "no S17/S10/S11 authority" in out


@pytest.mark.parametrize("problem", [
    "source_symlink", "source_oversized", "source_invalid_json",
    "wrong_questions", "no_native_report", "bad_bridge",
])
def test_cli_blocks_unbounded_foreign_or_forged_sources(
    capsys, tmp_path: Path, problem,
):
    report = _fixture_evidence()
    report_path = tmp_path / "native.json"
    question_path = tmp_path / "questions.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    question_path.write_text(json.dumps(_questions(report)), encoding="utf-8")
    argv = [
        "--native-report", str(report_path),
        "--spatial-questions", str(question_path),
        "--format", "jsonl",
    ]
    if problem == "source_symlink":
        original = tmp_path / "source-original.json"
        original.write_text(json.dumps(_questions(report)))
        sym = tmp_path / "source-symlink.json"
        sym.symlink_to(original)
        argv[argv.index("--spatial-questions") + 1] = str(sym)
    elif problem == "source_oversized":
        question_path.write_bytes(b"x" * (joined.MAX_SOURCE_BYTES + 1))
    elif problem == "source_invalid_json":
        question_path.write_text("{not json", encoding="utf-8")
    elif problem == "wrong_questions":
        question_path.write_text('{"schema": "WRONG"}', encoding="utf-8")
    elif problem == "no_native_report":
        argv[argv.index("--native-report") + 1] = str(tmp_path / "missing")
    elif problem == "bad_bridge":
        original = tmp_path / "bridge.jsonl"
        original.write_text("{not a bridge frame\n", encoding="utf-8")
        argv += ["--bridge-jsonl", str(original)]
        # Malformed supplied bridge is unknown per-action, not a new success.
        assert joined.main(argv) == 0
        rows = [json.loads(x) for x in capsys.readouterr().out.splitlines()]
        assert all(
            r["region_status"] == "UNDETERMINED"
            for r in rows if r["kind"] == "lane_c_spatial_observation"
        )
        return
    assert joined.main(argv) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "UNDETERMINED"
    assert result["world_actions_issued"] == result["model_requests_issued"] == 0
    assert not result["s17_feedback_issued"]
    assert result["s10_updates"] == result["s11_promotions"] == 0


def test_module_has_no_world_or_learning_owner_imports():
    import inspect

    import adapters.mineflayer.self_lane_c_timeline as subject

    src = inspect.getsource(subject)
    assert "from adapters.mineflayer.s49_normal_session_real_ci import" not in src
    assert "from relay_self.learning import" not in src
    assert "subprocess" not in src
    assert "createBot" not in src
    assert not replace(
        SelfSpatialObservation(
            schema=SCHEMA, status="UNDETERMINED", reason="SOURCE_UNAVAILABLE",
            session_id=None, action_id=None, source_references=(),
            source_sha256=None, source_matches_s16=False,
        ),
        goal_success_attested=False,
    ).goal_success_attested
