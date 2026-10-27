"""Causal owner START/END Paper fence, not cross-clock equality or WAIT."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.s49_causal_wait_fence_dev import (
    OriginalOwnerFenceRejected,
    review_original_owner_causal_paper_fence_dev,
)
from adapters.mineflayer.s49_inter_action_stillness_dev import (
    review_original_owner_no_issued_action_gap_dev,
)
from test_s49_inter_action_stillness_dev import fixture
from test_s49_original_owner_gap_dev import make


def source(tmp_path):
    o, still, first, second, sid = make(tmp_path)
    raw, _, timeline, _, _, _, _ = fixture(tmp_path)
    owner = review_original_owner_no_issued_action_gap_dev(
        o, still, first_action_id=first,
        second_action_id=second, session_id=sid,
    )
    original = deepcopy(o)
    original["causal_paper_start_received_after_first_outcome"] = True
    original["causal_paper_end_received_before_original_second_issue"] = True
    lines = []
    for phase, tick, other in (
        ("START", 118, "NONE"),
        ("END", 296, second),
    ):
        params = {
            "action_id": first, "session_id": sid,
            "world": "world-s49", "player_uuid": "player-s49",
            "phase": phase, "second_action_id": other, "tick": tick,
            "original_owner_paper_delivery_only": "true",
            "native_effect_tick_attested": "false", "motor_write": "false",
            "M0_POSTED": "false", "P1_APPLIED": "false",
            "WAIT_ATTESTED": "false",
        }
        lines.append("S49_DASH_DEV_OWNER_FENCE " +
                     " ".join(f"{k}={v}" for k, v in params.items()))
    return {
        "raw": raw + "\n" + "\n".join(lines),
        "owner": owner,
        "original_owner": original,
        "stillness": still,
        "timeline": timeline,
        "first_action_id": first,
        "second_action_id": second,
        "session_id": sid,
    }


def test_original_owner_causally_brackets_static_Paper_tick_ids_without_clock_sync(tmp_path):
    args = source(tmp_path)
    before = deepcopy(args)
    result = review_original_owner_causal_paper_fence_dev(**args)
    assert result["classification"] == "S49_CAUSAL_OWNER_PAPER_STATIC_SUBWINDOW_DEV_ONLY"
    assert result["paper_first_owner_fence_delivery_tick"] == 118
    assert result["paper_second_owner_fence_delivery_tick"] == 296
    assert result["paper_stillness_candidate_interval"] == [122, 289]
    assert result["paper_causal_subwindow_first_tick"] == 122
    assert result["paper_causal_subwindow_last_tick"] == 289
    assert result["paper_causal_subwindow_contiguous_still_ticks"] == 168
    assert result["boundary_guard_ticks_each_side"] == 2
    assert result["owner_original_first_s16_terminal_before_start_delivery"] is True
    assert result["owner_original_second_s15_issue_after_end_delivery"] is True
    assert result["node_original_first_clear_before_start_delivery"] is True
    assert result["node_original_second_set_after_end_delivery"] is True
    assert result["original_issuer_no_second_issue_during_causal_subwindow"] is True
    assert result["same_process_native_paper_clock_epoch_calibrated"] is False
    assert result["node_physics_paper_tick_1_to_1_attested"] is False
    assert result["global_world_quiescence_attested"] is False
    assert result["global_action_absence_attested"] is False
    assert result["physical_WAIT_admitted"] is False
    assert result["P1_recovery_posted"] is False and result["M0_posted"] is False
    assert args == before


@pytest.mark.parametrize("fault", [
    "remove_start", "remove_end", "duplicate_start", "duplicate_end",
    "switch_phase", "foreign_action", "foreign_session", "foreign_world",
    "foreign_player", "foreign_second", "start_wrong_second",
    "native_clock_claim", "owner_delivery_forged", "motor_writes",
    "m0_minted", "p1_minted", "wait_minted", "too_early_start",
    "end_after_second", "same_tick_fences", "short_fence",
    "start_fence_unconfirmed", "end_fence_unconfirmed",
    "owner_second_issued", "owner_fake_duration", "owner_clock_sync",
    "stale_paper_world", "paper_gap", "paper_not_still",
    "paper_wait_minted", "wrong_original_second",
])
def test_no_unsafe_Paper_subwindow_if_fence_or_owner_invalid(tmp_path, fault):
    args = source(tmp_path)
    rows = args["raw"].splitlines()
    mark = "S49_DASH_DEV_OWNER_FENCE "
    indices = [i for i, r in enumerate(rows) if mark in r]
    a, b = indices
    if fault == "remove_start":
        rows.pop(a)
    elif fault == "remove_end":
        rows.pop(b)
    elif fault == "duplicate_start":
        rows.append(rows[a])
    elif fault == "duplicate_end":
        rows.append(rows[b])
    elif fault == "switch_phase":
        rows[a], rows[b] = rows[b], rows[a]
    elif fault == "foreign_action":
        rows[a] = rows[a].replace("action_id=s49-native-move-18", "action_id=alien")
        # Refuse after first fence now missing.
    elif fault == "foreign_session":
        rows[a] = rows[a].replace("session_id=native-session-dev", "session_id=alien")
    elif fault == "foreign_world":
        rows[a] = rows[a].replace("world=world-s49", "world=alien")
    elif fault == "foreign_player":
        rows[a] = rows[a].replace("player_uuid=player-s49", "player_uuid=alien")
    elif fault == "foreign_second":
        rows[b] = rows[b].replace("second_action_id=s49-native-move-55",
                                  "second_action_id=alien")
    elif fault == "start_wrong_second":
        rows[a] = rows[a].replace("second_action_id=NONE", "second_action_id=alien")
    elif fault == "native_clock_claim":
        rows[a] = rows[a].replace(
            "native_effect_tick_attested=false", "native_effect_tick_attested=true"
        )
    elif fault == "owner_delivery_forged":
        rows[a] = rows[a].replace(
            "original_owner_paper_delivery_only=true",
            "original_owner_paper_delivery_only=false",
        )
    elif fault == "motor_writes":
        rows[a] = rows[a].replace("motor_write=false", "motor_write=true")
    elif fault == "m0_minted":
        rows[a] = rows[a].replace("M0_POSTED=false", "M0_POSTED=true")
    elif fault == "p1_minted":
        rows[b] = rows[b].replace("P1_APPLIED=false", "P1_APPLIED=true")
    elif fault == "wait_minted":
        rows[b] = rows[b].replace("WAIT_ATTESTED=false", "WAIT_ATTESTED=true")
    elif fault == "too_early_start":
        rows[a] = rows[a].replace("tick=118", "tick=112")
    elif fault == "end_after_second":
        rows[b] = rows[b].replace("tick=296", "tick=300")
    elif fault == "same_tick_fences":
        rows[b] = rows[b].replace("tick=296", "tick=118")
    elif fault == "short_fence":
        rows[b] = rows[b].replace("tick=296", "tick=124")
    elif fault == "start_fence_unconfirmed":
        args["original_owner"]["causal_paper_start_received_after_first_outcome"] = False
    elif fault == "end_fence_unconfirmed":
        args["original_owner"]["causal_paper_end_received_before_original_second_issue"] = False
    elif fault == "owner_second_issued":
        args["owner"]["at_next_action_request_count"] = 2
    elif fault == "owner_fake_duration":
        args["owner"]["bounded_source_local_duration_consistency"] = False
    elif fault == "owner_clock_sync":
        args["owner"]["host_paper_world_tick_clocks_calibrated"] = True
    elif fault == "stale_paper_world":
        args["timeline"]["world_uuid"] = "alien"
    elif fault == "paper_gap":
        args["timeline"]["tick_gaps_or_replay"] = True
    elif fault == "paper_not_still":
        args["stillness"]["classification"] = "S49_INTER_ACTION_STILLNESS_CANDIDATE_ABSENT_DEV_ONLY"
    elif fault == "paper_wait_minted":
        args["stillness"]["physical_WAIT_admitted"] = True
    else:
        args["second_action_id"] = "alien"
    args["raw"] = "\n".join(rows)
    with pytest.raises(OriginalOwnerFenceRejected):
        review_original_owner_causal_paper_fence_dev(**args)
