"""Synthetic host report integrity only; NEVER physical original attestation."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

import pytest

from adapters.mineflayer.self_body_s50_l_bcg_handoff import (
    review_l_bcg_after_original_l0,
)
from test_self_body_s50_l1_motion_shadow import real_type_pair
from tools.l_bcg_world_report_preflight import (
    BCGReportRejected,
    review_bcg_host_report,
)


def _report():
    readout, choice = real_type_pair()
    shadow = review_l_bcg_after_original_l0(readout, choice)
    return {
        "status": "PASS", "stage": "CLOSED",
        "session_id": choice.session_id,
        "real_model_calls": 0, "learning_in_world": False,
        "actual_native_actions": [{"terminal": "outcome"}],
        "decisions": [
            {"selected": "WAIT", "issued": False},
            {"selected": "MOVE_AWAY", "issued": True},
            {"selected": "WAIT", "issued": False,
             "probe_seq": choice.probe_seq,
             "entity_id": choice.entity_id,
             "distance_m": choice.distance_m},
        ],
        "live_next_epoch": {
            "current_body": asdict(readout.current_body),
            "current_world": asdict(readout.current_world),
        },
        "l_bcg_shadow": asdict(shadow),
    }


def test_original_s49_host_report_sanity_not_physical_attestation():
    report = _report()
    result = review_bcg_host_report(report)
    assert result["classification"] == "DEV_BCG_HOST_REPORT_SELF_CONSISTENT_ONLY"
    assert result["qualified_training_worlds"] == 0
    assert result["physical_originals_independently_attested"] is False
    assert result["action_issues"] == 0
    assert "goal_remaining_m" in result["required_condition_cues_missing"]
    assert "food" in result["observed_cue_names"]
    assert "m_energy_low" not in result["observed_cue_names"]


@pytest.mark.parametrize("case", [
    "wrong_original_seq", "wrong_world_provenance", "claim_physical",
    "claim_training", "advice_action", "mutable_l0", "bad_threat_distance",
    "invent_energy", "extra_action", "missing_cues", "incomplete_goal",
])
def test_reject_host_report_source_and_authority_escalation(case):
    report = deepcopy(_report())
    shadow = report["l_bcg_shadow"]
    if case == "wrong_original_seq":
        report["live_next_epoch"]["current_body"]["observation"]["native_seq"] += 1
    elif case == "wrong_world_provenance":
        report["live_next_epoch"]["current_world"]["observation"]["provenance"] = {
            "source": "operator", "reference": "invented",
        }
    elif case == "claim_physical":
        shadow["cue_inventory"]["paper_effective_input_clear_attested"] = True
    elif case == "claim_training":
        shadow["used_physical_training_worlds"] = 2
    elif case == "advice_action":
        shadow["advice"] = "RECHECK_BEFORE_NEXT_MOVE"
    elif case == "mutable_l0":
        report["decisions"][-1]["selected"] = "MOVE_AWAY"
    elif case == "bad_threat_distance":
        for row in shadow["cue_inventory"]["observed"]:
            if row["name"] == "s42_threat_distance_m":
                row["value"] += 0.3
    elif case == "invent_energy":
        shadow["cue_inventory"]["observed"].append({
            "name": "m_energy_low", "value": 0,
            "source_ref": shadow["original_native_ref"],
        })
    elif case == "extra_action":
        report["actual_native_actions"].append({"terminal": "outcome"})
    elif case == "missing_cues":
        shadow["cue_inventory"]["missing_required"] = []
    elif case == "incomplete_goal":
        shadow["goal_success_attested"] = True
    with pytest.raises(BCGReportRejected):
        review_bcg_host_report(report)


def test_no_bcg_record_rejected_even_if_s49_parent_is_real():
    report = _report()
    del report["l_bcg_shadow"]
    with pytest.raises(BCGReportRejected):
        review_bcg_host_report(report)
