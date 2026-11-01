"""H6: real stored H5 original-byte fixture, not new World or training evidence."""
from __future__ import annotations

import dataclasses
import math
from pathlib import Path

import pytest

from relay_self.l_bcg_dev_proxy import (
    DevProxyRejected,
    read_h6_provisional_world,
    summarize_h6_provisional_worlds,
)
from relay_self.l1_bcg_motion_shadow import (
    BCGRejected,
    MotionContext,
    MotorSourceAdmission,
    compare_conditional_motion_shadow,
)

ROOT = (
    Path(__file__).resolve().parents[1] / "docs" / "evidence"
    / "l-bcg-h5-20261101"
)


def _inputs():
    return dict(
        host_report_original=(ROOT / "run1/s49-report.json").read_bytes(),
        independent_audit_original=(ROOT / "independent-audit.json").read_bytes(),
        s16_original=(
            ROOT / "run1/capture/l18_s16_terminal_original.jsonl"
        ).read_bytes(),
        s7_received_prefix_original=(
            ROOT / "run1/capture/pre-next-l0-prefix/native_bridge_received_original.jsonl"
        ).read_bytes(),
        paper_server_original=(ROOT / "run1/server.log").read_bytes(),
    )


def test_h5_exact_real_originals_read_as_dev_proxy_not_training():
    e = read_h6_provisional_world(**_inputs())
    assert e.action_id == "s49-native-move-20"
    assert e.action_before_native_seq == 23
    assert e.action_after_native_seq == 30
    assert e.next_native_seq == 56
    assert e.before_minecraft_food == 20.0
    assert e.before_s42_threat_distance_m == 2.0
    assert e.sampled_input_off_ticks == tuple(range(252, 260))
    assert math.isclose(e.sampled_input_off_motion_m, 0.06424660150896066, abs_tol=1e-10)
    assert e.sampled_any_motion
    assert e.classification == "DEV_SAMPLED_LAST_REPORTED_INPUT_OFF_PROXY_ONLY"
    assert not e.physical_effective_clear_attested
    assert not e.goal_attested
    assert not e.physical_training_eligible
    assert e.learning_commits == e.extra_actions == 0
    result = summarize_h6_provisional_worlds((e,))
    assert result.distinct_provisional_worlds == 1
    assert result.cheap_last_world_motion == "SAMPLED_MOTION"
    assert result.cheap_any_world_motion == "SAMPLED_MOTION"
    assert result.learned_l1_attention == "DEFER_UNKNOWN"
    assert not result.learned_policy_qualified
    assert result.admitted_training_worlds == 0


@pytest.mark.parametrize("name", [
    "host_report_original", "independent_audit_original",
    "s16_original", "s7_received_prefix_original", "paper_server_original",
])
def test_changed_original_or_audit_rejected(name):
    originals = _inputs()
    originals[name] = originals[name] + b"forged append\n"
    with pytest.raises(DevProxyRejected):
        read_h6_provisional_world(**originals)


@pytest.mark.parametrize("change", [
    "promote_qualified", "claim_stable", "claim_goal", "future_clear",
    "rewrite_action", "rewrite_food", "rewrite_threat", "fake_paper_ticks",
    "repeat_action", "new_goal_success",
])
def test_changed_claims_fail_closed_under_byte_attestation(change):
    import hashlib
    import json

    inputs = _inputs()
    report = json.loads(inputs["host_report_original"])
    audit = json.loads(inputs["independent_audit_original"])
    if change == "promote_qualified":
        audit["qualified_training_worlds"] = 1
    elif change == "claim_stable":
        report["live_next_epoch"]["window"]["physical_stability_attested"] = True
    elif change == "claim_goal":
        report["l_bcg_shadow"]["goal_success_attested"] = True
    elif change == "future_clear":
        report["live_next_epoch"]["window"]["effective_clear_tick"] = "252"
    elif change == "rewrite_action":
        report["actual_native_actions"][0]["action"] = "fake-action"
    elif change == "rewrite_food":
        report["actual_native_actions"][0]["execution_evidence"]["before_observation"]["snapshot"]["food"] = 3
    elif change == "rewrite_threat":
        report["decisions"][1]["distance_m"] = 20.0
    elif change == "fake_paper_ticks":
        report["live_next_epoch"]["window"]["ticks"][0]["displacement_m"] = 55.0
    elif change == "repeat_action":
        report["actual_native_actions"].append(report["actual_native_actions"][0])
    elif change == "new_goal_success":
        report["l_bcg_shadow"]["conditional"] = {"fake": True}
    # This is a LOCAL consistency check, not a defense against a fully
    # colluding owner rewriting both originals and a signed external witness.
    inputs["host_report_original"] = json.dumps(report).encode()
    inputs["independent_audit_original"] = json.dumps(audit).encode()
    # Even if the local digest manifest is adjusted, the independent
    # source/claim cross-check must refuse the edit.
    audit["original_sha256"]["s49-report.json"] = hashlib.sha256(
        inputs["host_report_original"]
    ).hexdigest()
    inputs["independent_audit_original"] = json.dumps(audit).encode()
    with pytest.raises(DevProxyRejected):
        read_h6_provisional_world(**inputs)


def test_provisional_episodes_never_cross_formal_motor_outcome_gate():
    e = read_h6_provisional_world(**_inputs())
    c = MotionContext(
        self_id="self", session_id="future", world_id="future-world",
        world_revision=100, body_source_ref="body:future",
        world_source_ref="world:future", source_kind="OBSERVED",
        remaining_m=1.0, tolerance_m=0.5, gait="WALK",
        fatigue_high=False, energy_low=False, obstacle=False,
        freshness_ok=True, regime="flat",
    )
    with pytest.raises(BCGRejected, match="typed completed motor outcome"):
        compare_conditional_motion_shadow(
            current=c, training=(e,),
            admission=MotorSourceAdmission(frozenset(), frozenset()),
            memory_enabled=True,
        )


def test_duplicate_world_and_false_physical_promotion_rejected():
    e = read_h6_provisional_world(**_inputs())
    with pytest.raises(DevProxyRejected, match="duplicate"):
        summarize_h6_provisional_worlds((e, e))
    with pytest.raises(DevProxyRejected, match="over-qualified"):
        summarize_h6_provisional_worlds((dataclasses.replace(e, physical_training_eligible=True),))


def test_same_action_id_is_legal_in_different_worlds_but_not_same_session():
    e = read_h6_provisional_world(**_inputs())
    other = dataclasses.replace(e, paper_world_id="another-world", session_id="another-session")
    comparison = summarize_h6_provisional_worlds((e, other))
    assert comparison.distinct_provisional_worlds == 2
    assert comparison.admitted_training_worlds == 0
    with pytest.raises(DevProxyRejected):
        summarize_h6_provisional_worlds((e, dataclasses.replace(e, paper_world_id="other-world")))
