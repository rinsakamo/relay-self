"""WorldBody third-MOVE after REST: direct observations and no physics-oracle paths."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

import test_postmain_s42_world_contrast as s42
from adapters.mineflayer.normal_action import (
    NormalActionRejected, NormalWorldL0,
)
from adapters.mineflayer.worldbody_direct_selfbody import (
    DirectMoveExperience,
    DirectWorldBodyObservationRejected,
    check_post_rest_motor_output,
)
from tools.worldbody_post_rest_motor_retest_post import audit_post_rest_retest


def move(which: int, seq: int, distance: float) -> DirectMoveExperience:
    return DirectMoveExperience(
        session_id="one-owner-one-session",
        action_id=f"original-move-{which}",
        native_seq=seq,
        action_distance_m=distance,
        source_ref=f"native-probe:one-owner-one-session:{seq}:request-{seq}",
        observed_fields=("position_x", "position_y", "position_z", "health", "food"),
    )


def test_three_native_moves_with_intervening_rest_regain_output():
    result = check_post_rest_motor_output(
        move(1, 31, 0.332),
        move(2, 62, 0.100),
        move(3, 88, 0.320),
        final_rest_probe_seq=79,
    )
    assert result.regained_motor_output is True
    assert result.recovery_over_exhausted_ratio == pytest.approx(3.2)
    assert result.recovery_over_first_ratio == pytest.approx(0.320 / 0.332)
    assert result.worldbody_truth_accessed is False
    assert len(result.source_refs) == 3


def test_post_rest_direct_output_may_fail_without_lying_about_physics():
    result = check_post_rest_motor_output(
        move(1, 31, 0.332),
        move(2, 62, 0.100),
        move(3, 88, 0.110),
        final_rest_probe_seq=79,
    )
    assert result.regained_motor_output is False


@pytest.mark.parametrize("variant", (
    "missing-rest-sample", "future-rest-sample", "old-third",
    "same-action", "foreign-session", "foreign-source",
    "hidden-fatigue", "hidden-rate", "second-not-degraded",
    "zero-third", "nonfinite-third", "noninteger-clock",
))
def test_invalid_third_native_source_rejected(variant):
    a, b, c = move(1, 31, 0.332), move(2, 62, 0.100), move(3, 88, 0.320)
    rest_seq = 79
    if variant == "missing-rest-sample":
        rest_seq = 62
    elif variant == "future-rest-sample":
        rest_seq = 95
    elif variant == "old-third":
        c = replace(c, native_seq=61)
    elif variant == "same-action":
        c = replace(c, action_id=b.action_id)
    elif variant == "foreign-session":
        c = replace(c, session_id="other-session")
    elif variant == "foreign-source":
        c = replace(c, source_ref="hypothesis:fake")
    elif variant == "hidden-fatigue":
        c = replace(c, hidden_worldbody_fatigue_accessed=True)
    elif variant == "hidden-rate":
        c = replace(c, worldbody_rate_accessed=True)
    elif variant == "second-not-degraded":
        b = replace(b, action_distance_m=0.30)
    elif variant == "zero-third":
        c = replace(c, action_distance_m=0)
    elif variant == "nonfinite-third":
        c = replace(c, action_distance_m=float("nan"))
    elif variant == "noninteger-clock":
        rest_seq = 79.0
    with pytest.raises(DirectWorldBodyObservationRejected):
        check_post_rest_motor_output(a, b, c, final_rest_probe_seq=rest_seq)


def test_same_original_l0_extends_only_after_two_completed_events():
    retained = s42._pair()[0]
    host = NormalWorldL0(
        "one-owner-one-session", "escape-threat", retained,
        max_events=3, max_action_requests=2,
    )
    with pytest.raises(NormalActionRejected):
        host.extend_after_worldbody_rest_dev(token=object())
    host.events = 3
    host.action_requests = 2
    host._seen_entities.update((1, 2, 3))
    host._used_action_ids.update(("move-1", "move-2"))
    host.extend_after_worldbody_rest_dev(token=object())
    assert host.events == 3 and host.action_requests == 2
    assert host.max_events == 4 and host.max_action_requests == 3
    with pytest.raises(NormalActionRejected):
        host.extend_after_worldbody_rest_dev(token=object())


@pytest.mark.parametrize("variant", (
    "no-retest-grant", "no-paper-grant", "old-mode-conflict",
    "p1-conflict", "rest-conflict", "wrong-flag-type",
))
def test_exclusive_post_rest_mode_blocks_before_world(tmp_path, monkeypatch, variant):
    from adapters.mineflayer import s49_normal_session_real_ci as runner

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_WORLDBODY_DEV_ONLY", "1")
    monkeypatch.setenv("S49_WORLDBODY_RETEST_DEV_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    kw = {"worldbody_retest_dev": True}
    if variant == "no-retest-grant":
        monkeypatch.delenv("S49_WORLDBODY_RETEST_DEV_ONLY")
    elif variant == "no-paper-grant":
        monkeypatch.delenv("S49_WORLDBODY_DEV_ONLY")
    elif variant == "old-mode-conflict":
        kw["worldbody_dev"] = True
    elif variant == "p1-conflict":
        kw["bug0_p1_paper_dev"] = True
    elif variant == "rest-conflict":
        kw["bug0_rest_dev"] = True
    elif variant == "wrong-flag-type":
        kw["worldbody_retest_dev"] = "true"
    report = tmp_path / "blocked.json"
    server_log = tmp_path / "not-started.log"
    assert asyncio.run(runner.qualify(report, server_log, **kw)) == 2
    row = json.loads(report.read_text(encoding="utf8"))
    assert row["status"] == "BLOCKED"
    assert row["actual_native_actions"] == []
    assert not server_log.exists()


def test_posthoc_cannot_certify_third_motor_without_original_3_actions():
    with pytest.raises(ValueError):
        audit_post_rest_retest(
            {"status": "PASS", "classification":
             "DEV_ONLY_WORLDBODY_ORIGINAL_S49_POST_REST_THIRD_MOTOR_OUTCOME",
             "actual_native_actions": [{"terminal": "outcome"}] * 2},
            "WORLDBODY_INTERNAL truth_fatigue=0.0000001",
        )
