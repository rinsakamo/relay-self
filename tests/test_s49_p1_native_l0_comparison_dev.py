"""DEV no-authorization source join: true S16 fixture + fake static Paper model."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.s49_p1_native_l0_comparison_dev import (
    P1NextNativeL0Rejected,
    review_next_native_p1_l0_comparison_dev,
)
from test_s49_p1_selfbody_epoch_shadow_dev import inputs
from test_self_action_evidence import _fixture_evidence


def inputs_with_native(tmp_path):
    p = inputs(tmp_path)
    from adapters.mineflayer.s49_p1_selfbody_epoch_shadow_dev import (
        project_p1_static_next_body_epoch_dev,
    )
    body = project_p1_static_next_body_epoch_dev(**p)
    original = _fixture_evidence()
    ids = [p["first_action_id"], p["second_action_id"]]
    sid = p["session_id"]
    for i, (action, action_id) in enumerate(zip(
        original["actual_native_actions"], ids, strict=True,
    )):
        action["action"] = action_id
        action["source"] = sid
        action["event_seq"] = 2 if i == 0 else 12
        action["probe_seq"] = 0 if i == 0 else 8
        e = action["execution_evidence"]
        e["action_id"] = action_id
        e["session_id"] = sid
        e["action_ref"] = "MOVE_FORWARD_SPRINT_DEV"
        e["dispatch_receipt"]["effect"] = "set_forward_sprint_dev"
        e["dispatch_receipt"]["action_id"] = action_id
        e["cleanup_receipt"]["action_id"] = action_id + "-s15-clear"
        for frame in ("before_observation", "dispatch_receipt",
                      "cleanup_receipt", "after_observation"):
            f = e[frame]
            f["session_id"] = sid
            f["provenance"] = {
                "source": "mineflayer", "reference": f"{sid}:{f['seq']}",
            }
    original.update({
        "session_id": sid,
        "dev_sprint_motor": True,
        "dev_m0_action_move_step": True,
        "dev_m0_dash_unboosted_actions": [ids[1]],
        "decisions": [
            {"event_seq": 0, "probe_seq": 0, "selected": "WAIT",
             "issued": False, "distance_m": 10.0},
            {"event_seq": 2, "probe_seq": 0, "selected": "MOVE_AWAY",
             "issued": True, "distance_m": 2.0},
            {"event_seq": 12, "probe_seq": 8, "selected": "MOVE_AWAY",
             "issued": True, "distance_m": 2.0},
        ],
    })
    return dict(
        original=original, body=body, model=p["model"], fence=p["fence"],
        timeline=__import__(
            "test_s49_p1_dev_wait_observed"
        ).example(tmp_path)["timeline"],
    )


def test_next_s49_native_move_real_but_p1_dash_not_measured(tmp_path):
    d = inputs_with_native(tmp_path)
    saved = deepcopy(d)
    result = review_next_native_p1_l0_comparison_dev(**d)
    assert d == saved
    assert result["classification"] == (
        "P1_NEXT_NATIVE_L0_SHADOW_CAPACITY_SOURCE_JOIN_DEV_ONLY"
    )
    assert result["second_original_l0_choice"] == "MOVE_AWAY"
    assert result["second_original_native_outcome"] is True
    assert result["second_native_observed_displacement_m"] == pytest.approx(.627)
    assert result["second_native_before_seq"] < result["second_native_after_seq"]
    assert result["hypothetical_l0_dash_power_options_disagree"] is True
    assert result["native_movement_is_not_p1_fatigue_measurement"] is True
    assert result["native_movement_is_not_dash_power_measurement"] is True
    assert result["l0_shadow_next_dash_constraint"] == (
        "UNDETERMINED_SOURCE_NEEDED_BEFORE_ACTUATION"
    )
    assert result["physical_l0_dash_power_admission"] is None
    assert result["p1_fatigue_independently_observed"] is False
    assert result["original_s49_l0_selection_modified"] is False
    assert result["original_native_reader_added"] is False
    assert result["original_action_issuer_added"] is False
    assert result["live_p1_state_modified"] is False
    assert result["qualification_go"] is False


@pytest.mark.parametrize("fault", [
    "foreign_session", "no_native", "native_wrong_action", "action_bad_source",
    "native_replay", "native_moved_wrong", "native_movement_missing",
    "bad_native_receipt", "wrong_native_effect", "wrong_l0_choice",
    "wrong_l0_probe", "wrong_l0_event", "model_new_issuer",
    "model_real_p1", "model_false_wait", "wrong_digest",
    "model_clocks_sync", "wrong_qual", "missing_native",
    "next_original_delivered_early", "model_l0_grant", "fake_m0",
    "missing_unboosted", "model_new_reader",
])
def test_reject_missing_or_forged_source_or_permissions(tmp_path, fault):
    d = inputs_with_native(tmp_path)
    a = d["original"]["actual_native_actions"][1]
    e = a["execution_evidence"]
    if fault == "foreign_session":
        d["original"]["session_id"] = "foreign"
    elif fault == "no_native":
        del a["execution_evidence"]
    elif fault == "native_wrong_action":
        e["action_id"] = "other"
    elif fault == "action_bad_source":
        a["source"] = "foreign"
    elif fault == "native_replay":
        e["before_observation"]["seq"] = 1
    elif fault == "native_moved_wrong":
        e["after_observation"]["snapshot"]["position"]["x"] += 4
    elif fault == "native_movement_missing":
        a["movement_m"] = 0
    elif fault == "bad_native_receipt":
        e["cleanup_receipt"]["result"] = "rejected"
    elif fault == "wrong_native_effect":
        e["dispatch_receipt"]["effect"] = "set_control"
    elif fault == "wrong_l0_choice":
        d["original"]["decisions"][2]["selected"] = "WAIT"
    elif fault == "wrong_l0_probe":
        d["original"]["decisions"][2]["probe_seq"] = 1
    elif fault == "wrong_l0_event":
        d["original"]["decisions"][2]["event_seq"] = 6
    elif fault == "model_new_issuer":
        d["body"]["new_action_issuers"] = 1
    elif fault == "model_real_p1":
        d["model"]["actual_physical_recovery_attested"] = True
    elif fault == "model_false_wait":
        d["fence"]["physical_WAIT_admitted"] = True
    elif fault == "wrong_digest":
        d["body"]["paper_candidate_source_sha256"] = "0"*64
    elif fault == "model_clocks_sync":
        d["timeline"]["second_window_not_exact_native_effect_timing"] = False
    elif fault == "wrong_qual":
        d["body"]["qualification_go"] = True
    elif fault == "missing_native":
        d["original"]["actual_native_actions"].pop()
    elif fault == "next_original_delivered_early":
        d["fence"]["paper_second_owner_fence_delivery_tick"] = 10000
    elif fault == "model_l0_grant":
        d["body"]["physically_admitted_next_action_power"] = 1.0
    elif fault == "fake_m0":
        d["body"]["m0_posted"] = True
    elif fault == "missing_unboosted":
        d["original"]["dev_m0_dash_unboosted_actions"] = []
    else:
        d["body"]["additional_native_reads"] = 1
    with pytest.raises(P1NextNativeL0Rejected):
        review_next_native_p1_l0_comparison_dev(**d)
