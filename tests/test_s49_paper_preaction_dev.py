"""Negative controls for pre-armed server-side BACK transition (offline only)."""
from __future__ import annotations

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_paper_preaction_dev import (
    review_s49_preaction_paper_dev,
)
from test_s49_paper_transcript_dev import (
    FOREIGN,
    RUN_ID,
    transcript,
    typed_owner,
)


def pre_transcript(capture):
    base = transcript(capture)
    subject, remainder = base.split("\n", 1)
    ex = capture._executor
    action = capture.projection.action_id
    session = capture.projection.session_id
    common = (
        f"marker_id={action}-{session} action_id={action}"
        f" session_id={session} world={ex._wait_fence._world}"
        f" run_id={RUN_ID}"
    )
    pre = (
        f"S49_OBSERVER_PRE_ARM {common} tick=68 input_idle=true\n"
        f"S49_OBSERVER_BACK_TRUE {common} tick=69 back=true\n"
        f"S49_OBSERVER_BACK_FALSE {common} tick=70 back=false\n"
    )
    return subject + "\n" + pre + remainder


def review(capture, raw):
    return review_s49_preaction_paper_dev(
        capture, raw,
        expected_player_uuid="32345678-1234-4234-8234-123456789abc",
    )


def test_back_on_off_precedes_paper_idle_without_any_p1_credit(monkeypatch):
    capture = typed_owner(monkeypatch)
    candidate = review(capture, pre_transcript(capture))
    assert candidate["status"] == "BACK_TRUE_TO_FALSE_PAPER_SHAPE_ONLY"
    assert (candidate["pre_arm_tick"], candidate["back_true_tick"],
            candidate["back_false_tick"]) == (68, 69, 70)
    assert candidate["observer_run_id"] == RUN_ID
    assert candidate["s49_native_clear_caused_edge"] == "NOT_ATTESTED"
    assert candidate["server_effective_control_release"] == "NOT_ATTESTED"
    assert candidate["whole_tick_self_inactivity"] == "NOT_ATTESTED"
    assert candidate["source_bound_tick"] is None
    assert candidate["wait_interval_ref"] is None
    assert candidate["wait_ticks_admitted"] == 0
    assert candidate["p1_fatigue_recovered"] == 0.0
    assert candidate["qualification_go"] is False
    assert capture._executor.wait_phase == "NEW"


@pytest.mark.parametrize("mutation", [
    "missing_arm", "missing_true", "missing_false", "duplicate_true",
    "duplicate_false", "reordered_edges", "same_tick", "reverse_clock",
    "late_release", "prearm_active", "wrong_true", "wrong_false",
    "foreign_action", "foreign_session", "foreign_world",
    "foreign_run", "prearm_late", "timeout", "restart",
    "input_reactivation", "movement", "different_paper_run",
    "no_s49_close", "foreign_s50",
])
def test_transition_untrusted_or_partial_fails_closed(monkeypatch, mutation):
    capture = typed_owner(monkeypatch)
    original = pre_transcript(capture)
    rows = original.splitlines(keepends=True)
    if mutation == "missing_arm":
        original = "".join(rows[:1] + rows[2:])
    elif mutation == "missing_true":
        original = "".join(rows[:2] + rows[3:])
    elif mutation == "missing_false":
        original = "".join(rows[:3] + rows[4:])
    elif mutation == "duplicate_true":
        original = "".join(rows[:3] + [rows[2]] + rows[3:])
    elif mutation == "duplicate_false":
        original = "".join(rows[:4] + [rows[3]] + rows[4:])
    elif mutation == "reordered_edges":
        original = "".join(rows[:2] + [rows[3], rows[2]] + rows[4:])
    elif mutation == "same_tick":
        original = original.replace("tick=69 back=true", "tick=70 back=true")
    elif mutation == "reverse_clock":
        original = original.replace("tick=69 back=true", "tick=71 back=true")
    elif mutation == "late_release":
        original = original.replace("tick=70 back=false", "tick=71 back=false")
    elif mutation == "prearm_active":
        original = original.replace("tick=68 input_idle=true", "tick=68 input_idle=false")
    elif mutation == "wrong_true":
        original = original.replace("tick=69 back=true", "tick=69 back=false")
    elif mutation == "wrong_false":
        original = original.replace("tick=70 back=false", "tick=70 back=true")
    elif mutation == "foreign_action":
        original = "".join(rows[:2] + [rows[2].replace(
            "action_id=" + capture.projection.action_id, "action_id=foreign", 1,
        )] + rows[3:])
    elif mutation == "foreign_session":
        original = "".join(rows[:3] + [rows[3].replace(
            "session_id=" + capture.projection.session_id, "session_id=foreign", 1,
        )] + rows[4:])
    elif mutation == "foreign_world":
        original = "".join(rows[:2] + [rows[2].replace(
            "world=paper-dev-world-s49", "world=foreign", 1,
        )] + rows[3:])
    elif mutation == "foreign_run":
        original = "".join(rows[:2] + [rows[2].replace(
            "run_id=" + RUN_ID, "run_id=" + FOREIGN, 1,
        )] + rows[3:])
    elif mutation == "prearm_late":
        original = original.replace("tick=68 input_idle=true", "tick=70 input_idle=true")
    elif mutation == "timeout":
        original = original.replace("tick=68 input_idle=true", "tick=1 input_idle=true")
    elif mutation == "restart":
        original += pre_transcript(capture)
    elif mutation == "input_reactivation":
        original += "S49_DEV_BACK_WAIT_ABORT reason=SERVER_INPUT_ACTIVE_DURING_OBSERVATION\n"
    elif mutation == "movement":
        original += "S49_DEV_BACK_WAIT_ABORT reason=SELF_MOVEMENT_EVENT_DURING_OBSERVATION\n"
    elif mutation == "different_paper_run":
        original = "".join(rows[:5] + [rows[5].replace(
            "run_id=" + RUN_ID, "run_id=" + FOREIGN, 1,
        )] + rows[6:])
    elif mutation == "no_s49_close":
        capture._state = "FAILED"
    else:
        original = original.replace(
            "S49_OBSERVER_BACK_TRUE", "S50_OBSERVER_BACK_TRUE",
        )
    with pytest.raises(BoundaryRejected):
        review(capture, original)


def test_prearm_requires_its_own_records_not_post_only(monkeypatch):
    capture = typed_owner(monkeypatch)
    with pytest.raises(BoundaryRejected):
        review(capture, transcript(capture))


def test_paper_logger_prefix_only_changes_text_digest(monkeypatch):
    capture = typed_owner(monkeypatch)
    paper = "".join(
        "[Server INFO] " + row
        for row in pre_transcript(capture).splitlines(keepends=True)
    )
    assert review(capture, paper)["wait_ticks_admitted"] == 0
