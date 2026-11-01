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


def test_world_classification_is_explicit_and_cannot_bypass_ceiling():
    originals = _originals()
    audit = json.loads(originals["independent_audit_original"])
    audit["classification"] = "DEV_H8_ORIGINAL_CHAIN_AND_BCG_DEFER_VERIFIED"
    originals["independent_audit_original"] = json.dumps(audit).encode()
    with pytest.raises(DevProxyRejected):
        inspect_h8_owner_sources(**originals)
    result = inspect_h8_owner_sources(
        **originals, audit_classification=audit["classification"],
    )
    assert result.learned_l1_attention == "DEFER_UNKNOWN"
    audit["qualified_training_worlds"] = 1
    originals["independent_audit_original"] = json.dumps(audit).encode()
    with pytest.raises(DevProxyRejected):
        inspect_h8_owner_sources(**originals, audit_classification=audit["classification"])


def test_live_preaction_diagnostic_uses_only_existing_native_source():
    from adapters.mineflayer.python_protocol import MineflayerStreamDecoder
    from adapters.mineflayer.self_body_s50_l_bcg_handoff import capture_h8_preaction_sources

    raw = _originals()["s7_received_prefix_original"]
    decoder = MineflayerStreamDecoder()
    frames = [decoder.decode(line.decode()) for line in raw.splitlines()]
    reading = next(frame for frame in frames if frame.seq == 21)
    prefix = b"\n".join(raw.splitlines()[:22]) + b"\n"
    result = capture_h8_preaction_sources(reading, event_seq=20, native_prefix=prefix)
    assert result["native_seq"] == result["body"]["native_seq"] == result["world"]["native_seq"]
    assert result["native_prefix_sha256"] == hashlib.sha256(prefix).hexdigest()
    assert set(result["conditions"].values()) == {"UNKNOWN"}
    assert result["owner_receipts"] == {}
    assert result["advice"] == "DEFER_UNKNOWN" and not result["action_authority"]
    with pytest.raises(ValueError):
        capture_h8_preaction_sources(reading, event_seq=55, native_prefix=prefix)
    with pytest.raises(ValueError):
        capture_h8_preaction_sources(reading, event_seq=20, native_prefix=prefix[:-len(prefix.splitlines()[-1])-1])


def test_independent_command_audit_rejects_an_extra_probe_or_effect():
    from tools.l_bcg_h8_world_readback import check_original_commands

    report = json.loads((ROOT / "run1/s49-report.json").read_bytes())
    sent = (ROOT / "run1/capture/native_bridge_sent_original.jsonl").read_bytes()
    check_original_commands(report, sent)
    for extra in (b'{"type":"observe","request_id":"extra"}\n',
                  b'{"type":"effect","action_id":"extra","effect":"clear_controls"}\n'):
        with pytest.raises(AssertionError):
            check_original_commands(report, sent + extra)


def test_real_h8_world_is_not_h5_and_never_uses_next_epoch_for_preaction():
    from relay_self.l_bcg_h7_preaction import audit_h7_pre_action

    root = ROOT.parent / "l-bcg-h8-20261101"
    files = {
        "host_report_original": "run1/s49-report.json",
        "independent_audit_original": "independent-audit.json",
        "s16_original": "run1/capture/l18_s16_terminal_original.jsonl",
        "s7_received_prefix_original":
            "run1/capture/pre-next-l0-prefix/native_bridge_received_original.jsonl",
        "paper_server_original": "run1/server.log",
        "operator_goal_plan_original": "run1/capture/l16_pre_world_goal_plan.json",
    }
    originals = {key: (root / path).read_bytes() for key, path in files.items()}
    result = inspect_h8_owner_sources(
        **originals, audit_classification="DEV_H8_ORIGINAL_CHAIN_AND_BCG_DEFER_VERIFIED",
    )
    old = inspect_h8_owner_sources(**_originals())
    assert result.session_id != old.session_id and result.paper_world_id != old.paper_world_id
    assert result.operator_plan_horizontal_distance_m != old.operator_plan_horizontal_distance_m
    h7 = audit_h7_pre_action(
        **{key: value for key, value in originals.items() if key != "operator_goal_plan_original"},
        audit_classification="DEV_H8_ORIGINAL_CHAIN_AND_BCG_DEFER_VERIFIED",
    )
    report = json.loads(originals["host_report_original"])
    assert h7.original_choice_probe_seq == report["decisions"][1]["probe_seq"]
    assert h7.original_next_epoch_probe_seq == report["decisions"][2]["probe_seq"]
    assert h7.original_next_epoch_probe_seq != audit_h7_pre_action(**_inputs()).original_next_epoch_probe_seq
    assert all(cue.native_seq < h7.episode.action_after_native_seq for cue in h7.pre_action_observed)
    assert result.learned_l1_attention == "DEFER_UNKNOWN"
    assert result.missing_required == old.missing_required
    assert result.source_qualified_training_worlds == 0
