"""H8 archived H5 owner readback: no false admission of independent Goal/P1/M."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from relay_self.l_bcg_dev_proxy import DevProxyRejected
from relay_self.l_bcg_h8_owner_availability import inspect_h8_owner_sources
from test_l_bcg_h6_dev_proxy import _inputs

ROOT = (
    Path(__file__).resolve().parents[1] / "docs" / "evidence"
    / "l-bcg-h5-20261101"
)


def _originals():
    return {
        **_inputs(),
        "operator_goal_plan_original": (
            ROOT / "run1/capture/l16_pre_world_goal_plan.json"
        ).read_bytes(),
    }


def test_real_h5_has_spatial_plan_but_no_goal_owner():
    o = inspect_h8_owner_sources(**_originals())
    assert o.pre_action_seq == 21
    assert o.operator_plan_tolerance_m == 0.49
    assert math.isclose(o.operator_plan_horizontal_distance_m, math.hypot(9.5, 5.5))
    assert not o.operator_plan_qualifies_goal
    assert not o.pre_action_source_qualified
    assert o.source_qualified_training_worlds == 0
    assert o.learned_l1_attention == "DEFER_UNKNOWN"
    assert o.qualification == "NO_GO"
    assert o.science == "NOT_RUN"
    states = {s.feature: s.status for s in o.features}
    assert len(states) == 8
    assert tuple(states) == o.missing_required
    assert states["goal_remaining_m"] == "OPERATOR_GEOMETRY_ONLY_NOT_GOAL"
    assert states["selected_gait"] == "NO_PRE_ACTION_GAIT_RECEIPT"
    assert states["p1_fatigue_high"] == "NO_CORRELATED_P1_SENSOR_RECEIPT"
    assert states["m_energy_low"] == "NO_CORRELATED_M0_SENSOR_RECEIPT"
    assert states["verified_obstacle"] == "NO_OBSTACLE_GEOMETRY_OWNER"
    assert states["world_revision"] == "NO_CROSS_WORLD_SOURCE_ORDER"
    assert states["verified_post_clear_training"] == "NO_EFFECTIVE_CLEAR_ATTESTATION"
    assert not o.original_l0_choice_modified
    assert o.action_issues == o.learning_commits == 0


def test_numeric_operator_goal_is_not_actual_goal_and_cannot_promote():
    o = inspect_h8_owner_sources(**_originals())
    r = replace(o, operator_plan_tolerance_m=0)
    assert r.operator_plan_qualifies_goal is False
    assert r.pre_action_source_qualified is False


@pytest.mark.parametrize("change", [
    "missing_original", "goal_independent", "authorizes_learning",
    "goal_schema", "nan_goal", "negative_tolerance", "goal_new_target",
    "goal_host_promote", "new_gait_from_direction", "fake_p1",
    "fake_m", "fake_clear",
])
def test_forged_operator_plan_or_h5_owner_claim_rejected(change):
    originals = _originals()
    if change == "missing_original":
        originals["operator_goal_plan_original"] = b""
    elif change in (
        "goal_independent", "authorizes_learning", "goal_schema",
        "nan_goal", "negative_tolerance", "goal_new_target",
    ):
        plan = json.loads(originals["operator_goal_plan_original"])
        if change == "goal_independent":
            plan["independent_external_goal_owner"] = True
        elif change == "authorizes_learning":
            plan["authorizes_learning"] = True
        elif change == "goal_schema":
            plan["schema"] = "QUALIFIED_EXTERNAL_GOAL"
        elif change == "nan_goal":
            plan["target_x"] = float("nan")
        elif change == "negative_tolerance":
            plan["tolerance_m"] = -0.4
        else:
            plan["target_x"] = 1000
        originals["operator_goal_plan_original"] = json.dumps(plan).encode()
    elif change in ("goal_host_promote", "new_gait_from_direction", "fake_p1", "fake_m", "fake_clear"):
        report = json.loads(originals["host_report_original"])
        if change == "goal_host_promote":
            report["l16_capture"]["external_goal_owner_independent"] = True
        elif change == "new_gait_from_direction":
            report["actual_native_actions"][0]["execution_evidence"]["action_ref"] = "RUN"
        elif change == "fake_p1":
            report["l_bcg_shadow"]["cue_inventory"]["missing_required"].remove("p1_fatigue_high")
        elif change == "fake_m":
            report["l_bcg_shadow"]["cue_inventory"]["missing_required"].remove("m_energy_low")
        else:
            report["live_next_epoch"]["window"]["physical_stability_attested"] = True
        originals["host_report_original"] = json.dumps(report).encode()
        audit = json.loads(originals["independent_audit_original"])
        audit["original_sha256"]["s49-report.json"] = hashlib.sha256(
            originals["host_report_original"]
        ).hexdigest()
        originals["independent_audit_original"] = json.dumps(audit).encode()
    with pytest.raises(DevProxyRejected):
        inspect_h8_owner_sources(**originals)


def test_cannot_forge_new_pre_action_record_while_reusing_old_digest():
    originals = _originals()
    bad = originals["s7_received_prefix_original"].replace(
        b'"seq":21', b'"seq":56', 1,
    )
    originals["s7_received_prefix_original"] = bad
    with pytest.raises(DevProxyRejected):
        inspect_h8_owner_sources(**originals)
