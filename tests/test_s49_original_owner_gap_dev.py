"""Original executor no-issued-Action bookends, not global/World WAIT proof."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.s49_inter_action_stillness_dev import (
    InterActionStillnessRejected,
    review_inter_action_stillness_dev,
    review_original_owner_no_issued_action_gap_dev,
)
from test_s49_inter_action_stillness_dev import fixture


def make(tmp_path):
    raw, path, timeline, _, first, second, sid = fixture(tmp_path)
    still = review_inter_action_stillness_dev(
        raw, path, timeline=timeline,
        first_action_id=first, second_action_id=second, session_id=sid,
    )
    owner = {
        "classification": "S49_ORIGINAL_EXECUTOR_NO_ISSUE_GAP_DEV_ONLY",
        "session_id": sid,
        "first_terminal_action_id": first,
        "host_first_outcome_monotonic_ns": 200_000_000_000,
        "first_terminal_outcome": True,
        "native_action_count_at_first_terminal": 1,
        "native_open_actions_at_first_terminal": 0,
        "second_requested_action_id": second,
        "host_next_action_request_monotonic_ns": 208_300_000_000,
        "elapsed_owner_local_monotonic_ns": 8_300_000_000,
        "same_original_S49_executor": True,
        "native_action_count_at_next_request": 1,
        "native_dispatched_action_ids": [first],
        "native_open_actions_at_next_request": 0,
        "native_action_count_after_second_terminal": 2,
        "native_open_actions_after_second_terminal": 0,
        "all_actions_globally_absent_attested": False,
        "paper_world_tick_bound_attested": False,
        "node_control_epoch_aligned_attested": False,
        "WAIT_admitted": False,
        "P1_recovery_posted": False,
        "M0_posted": False,
    }
    return owner, still, first, second, sid


def audit(o, s, first, second, sid):
    return review_original_owner_no_issued_action_gap_dev(
        o, s, first_action_id=first,
        second_action_id=second, session_id=sid,
    )


def test_same_original_action_owner_no_intervening_issues_not_physical_wait(tmp_path):
    owner, still, first, second, sid = make(tmp_path)
    untouched = deepcopy(owner)
    result = audit(owner, still, first, second, sid)
    assert result["classification"].startswith("S49_ORIGINAL_OWNER_NO_ACTION_ISSUE")
    assert result["original_owner_no_new_issue_between_bookends"] is True
    assert result["open_actions_at_bookends"] == [0, 0, 0]
    assert result["original_owner_gap_monotonic_ms"] == 8300
    assert result["paper_candidate_consecutive_still_ticks"] >= 8
    assert result["node_input_off_physics_callbacks"] == 154
    assert result["host_node_monotonic_clocks_calibrated"] is False
    assert result["host_paper_world_tick_clocks_calibrated"] is False
    assert result["physical_overlap_time_attested"] is False
    assert result["global_issuer_absence_attested"] is False
    assert result["physical_WAIT_admitted"] is False
    assert result["P1_recovery_posted"] is False
    assert result["M0_posted"] is False
    assert owner == untouched


@pytest.mark.parametrize("fault", [
    "other_first", "other_second", "other_session", "other_stillness_session",
    "other_owner_type", "fake_first_terminal", "fake_executor", "count_first_2",
    "count_next_2", "count_final_1", "open_first", "open_next", "open_final",
    "foreign_dispatched", "extra_dispatched", "zero_duration", "backward_clock",
    "invalid_clock", "forged_time", "no_stillness", "controls_on",
    "clock_sync_minted", "global_action_attested", "paper_bound_attested",
    "wait_minted", "p1_minted", "m0_minted", "paper_wait_minted",
])
def test_foreign_clock_action_or_fake_wait_refused(tmp_path, fault):
    o, st, first, second, sid = make(tmp_path)
    if fault == "other_first":
        o["first_terminal_action_id"] = "foreign"
    elif fault == "other_second":
        o["second_requested_action_id"] = "foreign"
    elif fault == "other_session":
        o["session_id"] = "foreign"
    elif fault == "other_stillness_session":
        st["session_id"] = "foreign"
    elif fault == "other_owner_type":
        o["classification"] = "CERTIFIED_WAIT"
    elif fault == "fake_first_terminal":
        o["first_terminal_outcome"] = False
    elif fault == "fake_executor":
        o["same_original_S49_executor"] = False
    elif fault == "count_first_2":
        o["native_action_count_at_first_terminal"] = 2
    elif fault == "count_next_2":
        o["native_action_count_at_next_request"] = 2
    elif fault == "count_final_1":
        o["native_action_count_after_second_terminal"] = 1
    elif fault == "open_first":
        o["native_open_actions_at_first_terminal"] = 1
    elif fault == "open_next":
        o["native_open_actions_at_next_request"] = 1
    elif fault == "open_final":
        o["native_open_actions_after_second_terminal"] = 1
    elif fault == "foreign_dispatched":
        o["native_dispatched_action_ids"] = ["alien"]
    elif fault == "extra_dispatched":
        o["native_dispatched_action_ids"] = [first, "alien"]
    elif fault == "zero_duration":
        o["elapsed_owner_local_monotonic_ns"] = 0
        o["host_next_action_request_monotonic_ns"] = o["host_first_outcome_monotonic_ns"]
    elif fault == "backward_clock":
        o["host_next_action_request_monotonic_ns"] = 0
    elif fault == "invalid_clock":
        o["host_next_action_request_monotonic_ns"] = 12.5
    elif fault == "forged_time":
        o["elapsed_owner_local_monotonic_ns"] += 1
    elif fault == "no_stillness":
        st["classification"] = "S49_INTER_ACTION_STILLNESS_CANDIDATE_ABSENT_DEV_ONLY"
    elif fault == "controls_on":
        st["node_all_controls_off_until_second_set"] = False
    elif fault == "clock_sync_minted":
        o["node_control_epoch_aligned_attested"] = True
    elif fault == "global_action_attested":
        o["all_actions_globally_absent_attested"] = True
    elif fault == "paper_bound_attested":
        o["paper_world_tick_bound_attested"] = True
    elif fault == "wait_minted":
        o["WAIT_admitted"] = True
    elif fault == "p1_minted":
        o["P1_recovery_posted"] = True
    elif fault == "m0_minted":
        o["M0_posted"] = True
    else:
        st["physical_WAIT_admitted"] = True
    with pytest.raises(InterActionStillnessRejected):
        audit(o, st, first, second, sid)
