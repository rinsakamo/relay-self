"""Self product + frozen C15: real typed source contract, no World/model calls.

Synthetic sources verify conditional *spatial-only* positives. The historical
Minecraft output never contained a second poststop probe; it stays UNKNOWN.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from adapters.mineflayer.goal_witness import Region
from adapters.mineflayer.self_spatial_review import (
    _load_regions,
    main,
    review_s49_spatial,
)
from test_self_action_evidence import _fixture_evidence
from test_self_demo import _native_report


def _case():
    report = _fixture_evidence()
    action = report["actual_native_actions"][0]
    e = action["execution_evidence"]
    sid = report["session_id"]
    before = e["before_observation"]["snapshot"]["position"]
    after = e["after_observation"]["snapshot"]["position"]
    # A fixture-specific PREDECLARED region in this test is NOT a production
    # goal certificate; the program never constructs boxes from final World.
    goal = Region(
        (after["x"] - .2, after["y"] - .5, after["z"] - .2),
        (after["x"] + .2, after["y"] + .5, after["z"] + .2),
    )
    alternative = Region(
        (after["x"] + 2.0, after["y"] - .5, after["z"] - .2),
        (after["x"] + 2.4, after["y"] + .5, after["z"] + .2),
    )
    assert before["x"] < goal.low[0]
    frames = [
        {
            "type": "adapter_started",
            "session_id": sid,
            "seq": 0,
            "mineflayer_version": "4.39.0",
            "config": {
                "host": "127.0.0.1", "port": 25565,
                "username": "RelaySelf", "version": None,
            },
        },
    ]
    for key, type_name in (
        ("before_observation", "observation"),
        ("dispatch_receipt", "effect_result"),
        ("cleanup_receipt", "effect_result"),
        ("after_observation", "observation"),
    ):
        frame = copy.deepcopy(e[key])
        frame.pop("provenance", None)
        frame["type"] = type_name
        frames.append(frame)
    post = copy.deepcopy(frames[-1])
    post["seq"] += 1
    post["request_id"] = "fixture-extra-independent-poststop-probe"
    frames.append(post)
    return report, frames, goal, alternative


def _review(report, frames, goal, alternative):
    return review_s49_spatial(
        report, (json.dumps(x) for x in frames),
        goal=goal, alternative=alternative, action_index=0,
    )


def test_c15_is_integrated_for_fully_matched_two_poststop_source():
    report, frames, goal, alternative = _case()
    verdict = _review(report, frames, goal, alternative)
    assert verdict.classification == "GOAL_REGION_OBSERVED"
    assert verdict.reason == "SPATIAL_ENDPOINT_ONLY"
    assert len(verdict.source_references) == 6
    assert verdict.world_session == report["session_id"]
    assert verdict.action_id == report["actual_native_actions"][0]["action"]
    assert verdict.physical_source_attested is False
    assert verdict.action_caused_goal is False
    assert verdict.goal_success_signed is False
    assert verdict.negative_reward_signed is False
    assert verdict.learning_feedback_created is False
    assert verdict.production_habit_granted is False
    assert verdict.world_actions_issued == 0
    assert verdict.l2_calls == 0


def test_existing_S49_real_report_without_action_frames_is_never_promoted():
    source = _native_report()
    _, frames, goal, alt = _case()
    verdict = _review(source, frames, goal, alt)
    assert verdict.classification == "UNDETERMINED"
    assert verdict.reason == "LEGACY_S49_ACTION_FRAMES_ABSENT"


@pytest.mark.parametrize("tamper", [
    "one_poststop", "stop_changed", "wrong_session",
    "foreign_after_snapshot", "wrong_actual_action", "stale_source_seq",
    "second_as_move", "poststop_moved", "other_action_receipt",
])
def test_partial_foreign_or_corrupted_native_evidence_denied(tamper):
    report, frames, goal, alternative = _case()
    if tamper == "one_poststop":
        frames.pop()
    elif tamper == "stop_changed":
        frames[3]["action_id"] = "wrong-stop"
    elif tamper == "wrong_session":
        frames[-1]["session_id"] = "different-session"
    elif tamper == "foreign_after_snapshot":
        frames[-2]["snapshot"]["position"]["x"] += .11
    elif tamper == "wrong_actual_action":
        frames[2]["action_id"] = "other-action"
    elif tamper == "stale_source_seq":
        frames[-1]["seq"] = frames[-2]["seq"]
    elif tamper == "second_as_move":
        frames[-1]["kind"] = "move"
    elif tamper == "poststop_moved":
        frames[-1]["snapshot"]["position"]["x"] += 0.9
    else:
        report["actual_native_actions"][0]["action"] = "other-action"
    result = _review(report, frames, goal, alternative)
    assert result.classification == "UNDETERMINED"
    assert result.goal_success_signed is False
    assert result.learning_feedback_created is False


def test_no_spatial_goal_is_inferred_from_movement_alone():
    report, frames, goal, alternative = _case()
    frames = frames[:5]
    # Exactly one S16 after observation is NOT C15's two independent probes.
    result = _review(report, frames, goal, alternative)
    assert result.classification == "UNDETERMINED"
    assert result.goal_success_signed is False


def test_explicit_offline_cli_stores_readonly_review_only(tmp_path: Path, capsys):
    report, frames, goal, alternative = _case()
    root = tmp_path / "input"
    root.mkdir()
    a, b, c = root / "report.json", root / "source.jsonl", root / "regions.json"
    a.write_text(json.dumps(report), encoding="utf-8")
    b.write_text("".join(json.dumps(x)+"\n" for x in frames), encoding="utf-8")
    c.write_text(json.dumps({
        "goal": {"low": goal.low, "high": goal.high},
        "alternative": {"low": alternative.low, "high": alternative.high},
    }), encoding="utf-8")
    assert _load_regions(c) == (goal, alternative)
    dest = tmp_path / "review"
    dest.mkdir()
    opts = [
        "--native-report", str(a), "--source-transcript", str(b),
        "--regions", str(c), "--action-index", "0", "--output-dir", str(dest),
    ]
    assert main(opts) == 0
    v = json.loads((dest / "spatial_review.json").read_text())
    assert v["classification"] == "GOAL_REGION_OBSERVED"
    assert v["production_habit_granted"] is False
    assert "GOAL_REGION_OBSERVED" in capsys.readouterr().out
    assert main(opts) == 2  # no overwrite/replay
    assert (dest / "spatial_review.json").is_file()


def test_bad_regions_and_missing_native_report_never_trigger_world(tmp_path):
    _, frames, goal, alternative = _case()
    origin = tmp_path / "transcript.jsonl"
    origin.write_text("\n".join(json.dumps(x) for x in frames), encoding="utf-8")
    spec = tmp_path / "regions.json"
    spec.write_text(json.dumps({
        "goal": {"low": goal.low, "high": goal.high},
        "alternative": {"low": goal.low, "high": goal.high},
    }), encoding="utf-8")
    out = tmp_path / "output"
    out.mkdir()
    assert main([
        "--native-report", str(tmp_path/"missing.json"),
        "--source-transcript", str(origin), "--regions", str(spec),
        "--action-index", "0", "--output-dir", str(out),
    ]) == 2
    assert not (out/"spatial_review.json").exists()


def test_no_game_action_or_learner_in_review_module():
    import adapters.mineflayer.self_spatial_review as integration

    text = Path(integration.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "execute_mineflayer_command(", "session.send_observe(",
        "ActionSupervisor(", "commit_learning_update(", "HabitRepertoire(",
        "subprocess.run(", "asyncio.run(", "MinecraftProcessSession(",
    ):
        assert forbidden not in text
