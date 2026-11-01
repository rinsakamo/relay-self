"""H7: archived H5 actual native S42 pre-Action cues, not new physical World."""
from __future__ import annotations

import dataclasses
import hashlib
import json

import pytest

from relay_self.l_bcg_dev_proxy import DevProxyRejected
from relay_self.l_bcg_h7_preaction import (
    audit_h7_pre_action,
    compare_h7_cheap_pre_action,
)
from test_l_bcg_h6_dev_proxy import _inputs


def test_h5_original_action_preceded_by_native_S42_not_next_epoch():
    audit = audit_h7_pre_action(**_inputs())
    assert audit.original_choice_event_seq == 20
    assert audit.original_choice_probe_seq == 21
    assert audit.original_action_before_probe_seq == 23
    assert audit.original_next_epoch_probe_seq == 56
    assert audit.cheap_native_threat_near
    assert not audit.cheap_native_food_low
    assert audit.missing_bcg_conditions == (
        "goal_remaining_m", "goal_tolerance_m", "selected_gait",
        "p1_fatigue_high", "m_energy_low", "verified_obstacle",
        "world_revision", "verified_post_clear_training",
    )
    cues = {x.name: x for x in audit.pre_action_observed}
    assert len(cues) == 8
    assert cues["s42_hostile_distance_m"].value == 2.0
    assert cues["s42_hostile_distance_m"].native_seq == 21
    assert cues["minecraft_food"].value == 20
    assert cues["s15_before_minecraft_food"].native_seq == 23
    assert cues["position_z"].value == -5.5
    assert all(x.phase == "ORIGINAL_S49_PRE_ACTION" for x in cues.values())
    assert all(x.native_seq < audit.episode.action_after_native_seq for x in cues.values())
    assert all("event-55" not in x.native_source_ref for x in cues.values())
    assert not audit.qualifies_goal
    assert not audit.qualifies_p1_m
    assert not audit.qualifies_post_clear
    assert not audit.physical_training_worlds


def test_cheap_baselines_are_observed_flags_not_l1_action():
    audit = audit_h7_pre_action(**_inputs())
    result = compare_h7_cheap_pre_action((audit,))
    assert result == {
        "observed_worlds": 1, "cheap_food_low_worlds": 0,
        "cheap_threat_near_worlds": 1, "cheap_sampled_motion_worlds": 1,
        "source_ceiling": "DEV_ARCHIVED_H5_PRE_ACTION_NATIVE_NOT_GOAL_OR_P1_M",
        "learned_l1_attention": "DEFER_UNKNOWN",
        "physical_training_worlds": 0, "action_issues": 0,
        "learning_updates": 0,
    }


def test_empty_history_does_not_conjure_training():
    result = compare_h7_cheap_pre_action(())
    assert result["observed_worlds"] == 0
    assert result["physical_training_worlds"] == 0
    assert result["learned_l1_attention"] == "DEFER_UNKNOWN"


@pytest.mark.parametrize("case", [
    "future_target_distance", "claimed_m_energy", "postworld_goal",
    "wrong_s42_seq", "wrong_action_id", "wrong_s15_before",
    "wrong_next_epoch_native", "claimed_clear", "duplicate_action",
])
def test_archived_original_source_or_qualification_change_rejected(case):
    src = _inputs()
    report = json.loads(src["host_report_original"])
    audit = json.loads(src["independent_audit_original"])
    if case == "future_target_distance":
        report["decisions"][1]["distance_m"] = 10
    elif case == "claimed_m_energy":
        report["l_bcg_shadow"]["cue_inventory"]["missing_required"].remove("m_energy_low")
    elif case == "postworld_goal":
        report["l_bcg_shadow"]["goal_success_attested"] = True
    elif case == "wrong_s42_seq":
        report["decisions"][1]["probe_seq"] = 56
    elif case == "wrong_action_id":
        report["actual_native_actions"][0]["action"] = "bad"
    elif case == "wrong_s15_before":
        report["actual_native_actions"][0]["execution_evidence"]["before_observation"]["seq"] = 55
    elif case == "wrong_next_epoch_native":
        report["live_next_epoch"]["current_body"]["observation"]["native_seq"] = 21
    elif case == "claimed_clear":
        report["live_next_epoch"]["window"]["effective_clear_tick"] = 252
    elif case == "duplicate_action":
        report["actual_native_actions"].append(report["actual_native_actions"][0])
    src["host_report_original"] = json.dumps(report, ensure_ascii=False).encode()
    audit["original_sha256"]["s49-report.json"] = hashlib.sha256(
        src["host_report_original"]
    ).hexdigest()
    src["independent_audit_original"] = json.dumps(audit).encode()
    with pytest.raises(DevProxyRejected):
        audit_h7_pre_action(**src)


def test_only_real_original_episode_counted_even_if_naive_fixture_duplicates():
    episode = audit_h7_pre_action(**_inputs())
    with pytest.raises(DevProxyRejected, match="duplicate"):
        compare_h7_cheap_pre_action((episode, episode))
    with pytest.raises(DevProxyRejected, match="provisional"):
        compare_h7_cheap_pre_action((
            dataclasses.replace(episode, physical_training_worlds=1),
        ))


@pytest.mark.parametrize("corrupted", [
    "s7_received_prefix_original", "s16_original", "paper_server_original",
    "host_report_original",
])
def test_original_digest_tamper_rejected(corrupted):
    src = _inputs()
    src[corrupted] += b"forged source"
    with pytest.raises(DevProxyRejected):
        audit_h7_pre_action(**src)
