"""H9a synthetic negative control + prior H8 archival control: NO H9a World run."""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from relay_self.l_bcg_h9a_pair import (
    EXPECTED_PREREG_CEILING,
    compare_h9a_pair,
    review_h9a_arm,
)
from relay_self.l_bcg_h9a_stimulus import (
    H9aRejected,
    select_h9a_stimulus,
    verify_h9a_observed_distance,
)
from tools.l_bcg_h9a_pair_readback import _critical_runtime_assets

ROOT = (
    Path(__file__).resolve().parents[1] / "docs" / "evidence"
    / "l-bcg-h8-20261101"
)
HEAD = "a244f5b2ae92878b337297398f5ff3cb48afbdb5"


def _fake_h9a_h8_fixture():
    """H8 real original reshaped in test memory only; NOT a real H9a observation."""
    report = json.loads((ROOT / "run1/s49-report.json").read_bytes())
    audit = json.loads((ROOT / "independent-audit.json").read_bytes())
    report["l_bcg_h9a_stimulus"] = asdict(select_h9a_stimulus(
        2.0, l_bcg_shadow_dev=True,
        live_next_epoch_dev=True, l22_settling_probes=5,
    ))
    raw = json.dumps(report, sort_keys=True).encode()
    audit["original_sha256"]["s49-report.json"] = hashlib.sha256(raw).hexdigest()
    prereg = {
        "schema": "L_BCG_H9A_ARM_PREREG_V1",
        "source_ceiling": EXPECTED_PREREG_CEILING,
        "arm_id": "A",
        "worlds": 1,
        "max_original_actions": 1,
        "retries": 0,
        "additional_l_bcg_actions": 0,
        "additional_native_probes": 0,
        "model_calls": 0,
        "learning_updates": 0,
        "qualified_training_worlds": 0,
        "cheap_threshold_m": 3.0,
        "requested_distance_m": 2.0,
        "executor_head": HEAD,
    }
    return report, audit, prereg, raw


def test_default_s49_staging_untouched_and_only_explicit_bounded_optin():
    assert select_h9a_stimulus(
        None, l_bcg_shadow_dev=False,
        live_next_epoch_dev=False, l22_settling_probes=None,
    ) is None
    a = select_h9a_stimulus(
        2.0, l_bcg_shadow_dev=True,
        live_next_epoch_dev=True, l22_settling_probes=5,
    )
    b = select_h9a_stimulus(
        3.5, l_bcg_shadow_dev=True,
        live_next_epoch_dev=True, l22_settling_probes=5,
    )
    assert a is not None and b is not None
    assert a.requested_near_m == 2.0 and b.requested_near_m == 3.5
    assert a.cheap_threshold_m == b.cheap_threshold_m == 3.0
    assert not a.action_authority and not b.action_authority
    assert a.formal_training_worlds == b.formal_training_worlds == 0


@pytest.mark.parametrize("bad", [
    -1.0, 0.0, 2.1, 3.0, 3.6, 4.0, 10.0, True, float("nan"), float("inf"),
    "3.5",
])
def test_unsafe_arm_distance_fails_closed(bad):
    with pytest.raises(H9aRejected):
        select_h9a_stimulus(
            bad, l_bcg_shadow_dev=True,
            live_next_epoch_dev=True, l22_settling_probes=5,
        )


@pytest.mark.parametrize("flags", [
    (False, True, 5), (True, False, 5),
    (True, True, None), (True, True, 2), (True, True, True),
])
def test_arm_disallowed_without_original_single_action_bcg_route(flags):
    with pytest.raises(H9aRejected):
        select_h9a_stimulus(
            3.5, l_bcg_shadow_dev=flags[0],
            live_next_epoch_dev=flags[1], l22_settling_probes=flags[2],
        )


def test_observed_native_distance_not_requested_operator_distance():
    a = select_h9a_stimulus(
        2.0, l_bcg_shadow_dev=True,
        live_next_epoch_dev=True, l22_settling_probes=5,
    )
    b = select_h9a_stimulus(
        3.5, l_bcg_shadow_dev=True,
        live_next_epoch_dev=True, l22_settling_probes=5,
    )
    assert verify_h9a_observed_distance(
        a, original_s42_distance_m=2.04, original_l0_choice="MOVE_AWAY",
    )
    assert verify_h9a_observed_distance(
        b, original_s42_distance_m=3.48, original_l0_choice="MOVE_AWAY",
    )
    assert not verify_h9a_observed_distance(
        b, original_s42_distance_m=2.0, original_l0_choice="MOVE_AWAY",
    )
    assert not verify_h9a_observed_distance(
        a, original_s42_distance_m=2.0, original_l0_choice="WAIT",
    )


def test_h8_real_original_only_synthetic_h9a_fixture_produces_provisional_arm():
    report, audit, prereg, raw = _fake_h9a_h8_fixture()
    x = review_h9a_arm(
        report=report, independent_h8_audit=audit,
        prereg=prereg, original_report_bytes=raw,
    )
    assert x.arm_id == "A"
    assert x.observed_s42_distance_m == x.requested_distance_m == 2.0
    assert x.original_preaction_native_seq == 21
    assert x.cheap_near_under_3m
    assert x.sampled_reported_input_off_motion_m > 0
    assert x.qualified_training_worlds == 0
    assert x.l_bcg_advice == "DEFER_UNKNOWN"


@pytest.mark.parametrize("mutation", [
    "wrong_report_sha", "fake_distance", "fake_source", "fake_training",
    "future_gait", "fake_goal", "wrong_requested", "wrong_cheap",
    "fake_clear", "extra_probe", "extra_action", "wrong_prereg_action",
    "no_preaction", "negative_paper",
])
def test_forged_source_or_condition_rejected(mutation):
    report, audit, prereg, raw = _fake_h9a_h8_fixture()
    report, audit, prereg = copy.deepcopy((report, audit, prereg))
    if mutation == "wrong_report_sha":
        raw += b"forged"
    elif mutation == "fake_distance":
        report["decisions"][1]["distance_m"] = 3.5
    elif mutation == "fake_source":
        report["l_bcg_h8_preaction"]["native_seq"] = 57
    elif mutation == "fake_training":
        audit["qualified_training_worlds"] = 1
    elif mutation == "future_gait":
        report["l_bcg_h8_preaction"]["conditions"]["selected_gait"] = "DASH"
    elif mutation == "fake_goal":
        audit["goal"] = "REACHED"
    elif mutation == "wrong_requested":
        prereg["requested_distance_m"] = 3.5
    elif mutation == "wrong_cheap":
        prereg["cheap_threshold_m"] = 2.0
    elif mutation == "fake_clear":
        report["live_next_epoch"]["window"]["effective_clear_tick"] = 257
    elif mutation == "extra_probe":
        audit["additional_native_probes"] = 1
    elif mutation == "extra_action":
        audit["additional_actions"] = 1
    elif mutation == "wrong_prereg_action":
        prereg["max_original_actions"] = 2
    elif mutation == "no_preaction":
        report["l_bcg_h8_preaction"] = None
    elif mutation == "negative_paper":
        report["live_next_epoch"]["window"]["ticks"][0]["displacement_m"] = -1
    if mutation not in ("wrong_report_sha", "wrong_requested", "wrong_cheap", "wrong_prereg_action"):
        raw = json.dumps(report, sort_keys=True).encode()
        audit["original_sha256"]["s49-report.json"] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(H9aRejected):
        review_h9a_arm(
            report=report, independent_h8_audit=audit,
            prereg=prereg, original_report_bytes=raw,
        )


def test_synthetic_two_world_comparator_is_not_learning_or_causality():
    report, audit, prereg, raw = _fake_h9a_h8_fixture()
    a = review_h9a_arm(
        report=report, independent_h8_audit=audit,
        prereg=prereg, original_report_bytes=raw,
    )
    # Synthetic World B is a typed dummy for pair guards, not original evidence.
    b = replace(
        a, arm_id="B", requested_distance_m=3.5,
        observed_s42_distance_m=3.5, original_session_id="synthetic-b",
        original_paper_world_id="synthetic-world-b",
        original_report_sha256="f" * 64,
        cheap_near_under_3m=False,
    )
    pair = compare_h9a_pair(a, b)
    assert pair.cheap_comparator_differs
    assert pair.distance_delta_m == 1.5
    assert pair.formal_train_worlds == pair.formal_heldout_worlds == 0
    assert not pair.real_causal_improvement_attested
    assert pair.learned_l1_attention == "DEFER_UNKNOWN"
    assert not pair.l0_policy_modified


@pytest.mark.parametrize("change", [
    "same_session", "same_world", "same_report", "different_code",
    "wrong_low_cheap", "wrong_high_cheap", "fake_qualified",
    "action_authority", "wrong_order",
])
def test_wrong_pair_rejected(change):
    report, audit, prereg, raw = _fake_h9a_h8_fixture()
    a = review_h9a_arm(
        report=report, independent_h8_audit=audit,
        prereg=prereg, original_report_bytes=raw,
    )
    b = replace(
        a, arm_id="B", requested_distance_m=3.5,
        observed_s42_distance_m=3.5, original_session_id="synthetic-b",
        original_paper_world_id="synthetic-world-b",
        original_report_sha256="f" * 64,
        cheap_near_under_3m=False,
    )
    if change == "same_session":
        b = replace(b, original_session_id=a.original_session_id)
    elif change == "same_world":
        b = replace(b, original_paper_world_id=a.original_paper_world_id)
    elif change == "same_report":
        b = replace(b, original_report_sha256=a.original_report_sha256)
    elif change == "different_code":
        b = replace(b, executor_head="a" * 40)
    elif change == "wrong_low_cheap":
        a = replace(a, cheap_near_under_3m=False)
    elif change == "wrong_high_cheap":
        b = replace(b, cheap_near_under_3m=True)
    elif change == "fake_qualified":
        b = replace(b, qualified_training_worlds=1)
    elif change == "action_authority":
        b = replace(b, new_actions=1)
    elif change == "wrong_order":
        a, b = b, a
    with pytest.raises(H9aRejected):
        compare_h9a_pair(a, b)


def test_h8_archived_original_proves_critical_asset_manifest_shape(tmp_path):
    """Same SHA comparison is required for H9a two NEW World roots."""
    archived = (ROOT / "run1/runtime-assets-sha256.json").read_bytes()
    original = _critical_runtime_assets(ROOT / "run1")
    assert len(original) == 4
    (tmp_path / "runtime-assets-sha256.json").write_bytes(archived)
    assert _critical_runtime_assets(tmp_path) == original

    changed = json.loads(archived)
    plugin = next(k for k in changed if k.endswith("/plugins/relay-metabolism-paper-dev.jar"))
    changed[plugin]["sha256"] = "0" * 64
    (tmp_path / "runtime-assets-sha256.json").write_text(json.dumps(changed))
    assert _critical_runtime_assets(tmp_path) != original
    (tmp_path / "runtime-assets-sha256.json").unlink()
    with pytest.raises(ValueError, match="missing/unsafe"):
        _critical_runtime_assets(tmp_path)
