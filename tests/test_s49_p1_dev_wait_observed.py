"""Paper tick-local negative controls for source-reviewed P1 DEV recovery."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.s49_causal_wait_fence_dev import (
    review_original_owner_causal_paper_fence_dev,
)
from adapters.mineflayer.s49_p1_dev_wait_observed import (
    P1ObservedWaitDevRejected,
    replay_p1_observed_static_wait_dev,
)
from adapters.mineflayer.s49_p1_fenced_recovery_shadow_dev import (
    project_p1_fenced_wait_shadow_dev,
)
from experiments.fatigue_p1 import FatigueProfile
from test_s49_causal_wait_fence_dev import source


def example(tmp_path):
    args = source(tmp_path)
    fence = review_original_owner_causal_paper_fence_dev(**args)
    profile = FatigueProfile(enabled=True, initial=0.6)
    sid = args["session_id"]
    first, second = args["first_action_id"], args["second_action_id"]
    shadow = project_p1_fenced_wait_shadow_dev(
        fence=fence,
        p1_replay={
            "single_p1_model_replayed": True, "source_qualified": False,
            "p1_ledger_posted": False, "m0_ledger_posted": False,
            "fatigue_initial": 0.6, "fatigue_final": 0.6155207399,
            "world_ticks_replayed": 13,
        },
        action_bracket={
            "original_owner_release": True,
            "independent_source_attested": False,
            "last_tick": 113,
            "elapsed_callbacks": 13,
        },
        profile=profile, session_id=sid,
        first_action_id=first, second_action_id=second,
        original_m0_energy_remaining=10.413667611509306,
    )
    return dict(
        raw=args["raw"], fence=fence, shadow=shadow,
        stillness=args["stillness"], timeline=args["timeline"],
        profile=profile, first_action_id=first,
        second_action_id=second, session_id=sid,
    )


def test_observed_each_tick_is_dev_model_not_authorized_p1(tmp_path):
    d = example(tmp_path)
    copy = deepcopy(d)
    result = replay_p1_observed_static_wait_dev(**d)
    assert d == copy
    assert result["evidence_grade"] == "DEV_WORLD_OBSERVED"
    assert result["first_tick"] == 122 and result["last_tick"] == 289
    assert result["dev_wait_model_ticks_replayed"] == 168
    assert result["paper_max_horizontal_delta_m"] == 0
    assert result["p1_dev_model_after"] == pytest.approx(
        d["shadow"]["counterfactual_end_fatigue"], abs=1e-11,
    )
    assert result["p1_dev_model_recovered"] == pytest.approx(
        d["shadow"]["counterfactual_p1_recovered_if_all_wait"], abs=1e-11,
    )
    assert len(result["paper_candidate_source_sha256"]) == 64
    assert result["p1_dev_state_is_counterfactual_copy"] is True
    assert result["r_qualified_wait_ticks"] == 0
    assert result["r_qualified_p1_recovery"] == 0
    assert result["live_p1_owner_state_modified"] is False
    assert result["m0_posted"] is False
    assert result["source_bound_tick_created"] is False


@pytest.mark.parametrize("fault", [
    "missing", "duplicate", "reorder", "changed_tick", "foreign_session",
    "foreign_action", "foreign_player", "foreign_world", "duplicate_field",
    "nan_pos", "large_motion", "motor_write", "wait_attested", "p1_applied",
    "m0_posted", "first_modifier", "second_applied", "second_cleared",
    "lost_node_off", "wrong_owner", "changed_fence", "shadow_wait_qualified",
    "shadow_modified", "wrong_profile", "forged_m0", "fake_qualification",
    "wrong_source_timeline",
])
def test_no_dev_tick_recovery_on_corrupt_paper_or_authority(tmp_path, fault):
    d = example(tmp_path)
    rows = d["raw"].splitlines()
    # Every source tick has index = tick - 100, candidate tick 155 is row 54.
    i = 54
    assert "tick=155" in rows[i]
    if fault == "missing":
        rows.pop(i)
    elif fault == "duplicate":
        rows.insert(i, rows[i])
    elif fault == "reorder":
        rows[i], rows[i+1] = rows[i+1], rows[i]
    elif fault == "changed_tick":
        rows[i] = rows[i].replace("tick=155", "tick=156")
    elif fault == "foreign_session":
        rows[i] = rows[i].replace("session_id=native-session-dev", "session_id=alien")
    elif fault == "foreign_action":
        rows[i] = rows[i].replace(d["first_action_id"], "alien")
    elif fault == "foreign_player":
        rows[i] = rows[i].replace("player_uuid=player-s49", "player_uuid=alien")
    elif fault == "foreign_world":
        rows[i] = rows[i].replace("world=world-s49", "world=alien")
    elif fault == "duplicate_field":
        rows[i] += " tick=155"
    elif fault == "nan_pos":
        rows[i] = rows[i].replace("z=0.0", "z=nan")
    elif fault == "large_motion":
        rows[i] = rows[i].replace("z=0.0", "z=0.2")
    elif fault == "motor_write":
        rows[i] = rows[i].replace("motor_write=false", "motor_write=true")
    elif fault == "wait_attested":
        rows[i] = rows[i].replace("WAIT_ATTESTED=false", "WAIT_ATTESTED=true")
    elif fault == "p1_applied":
        rows[i] = rows[i].replace("P1_APPLIED=false", "P1_APPLIED=true")
    elif fault == "m0_posted":
        rows[i] = rows[i].replace("M0_POSTED=false", "M0_POSTED=true")
    elif fault == "first_modifier":
        rows[i] = rows[i].replace("first_dash_modifier_present=false",
                                  "first_dash_modifier_present=true")
    elif fault == "second_applied":
        rows[i] = rows[i].replace("second_applied_marker_seen=false",
                                  "second_applied_marker_seen=true")
    elif fault == "second_cleared":
        rows[i] = rows[i].replace("second_cleared_marker_seen=false",
                                  "second_cleared_marker_seen=true")
    elif fault == "lost_node_off":
        d["stillness"]["node_all_controls_off_until_second_set"] = False
    elif fault == "wrong_owner":
        d["fence"]["original_issuer_no_second_issue_during_causal_subwindow"] = False
    elif fault == "changed_fence":
        d["fence"]["paper_causal_subwindow_last_tick"] += 1
    elif fault == "shadow_wait_qualified":
        d["shadow"]["physical_wait_admitted"] = True
    elif fault == "shadow_modified":
        d["shadow"]["counterfactual_end_fatigue"] += 0.1
    elif fault == "wrong_profile":
        d["profile"] = FatigueProfile(enabled=True, initial=0.5)
    elif fault == "forged_m0":
        d["timeline"]["world_tick_m0_debits_posted"] = True
    elif fault == "fake_qualification":
        d["fence"]["qualification_go"] = True
    else:
        d["timeline"]["observed_contiguous_paper_ticks"] = 216
    d["raw"] = "\n".join(rows)
    with pytest.raises(P1ObservedWaitDevRejected):
        replay_p1_observed_static_wait_dev(**d)
