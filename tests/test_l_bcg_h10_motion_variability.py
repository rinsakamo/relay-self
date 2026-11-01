"""H10 archived eight real H9b source-only diagnostics and adversarial controls."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from relay_self.l_bcg_h10_motion_variability import (
    SLOTS,
    H10Rejected,
    inspect_h10_world,
    summarize_h10,
)
from tools.l_bcg_h10_motion_readback import audit_archived_eight_worlds

ROOT = (
    Path(__file__).resolve().parents[1] / "docs/evidence"
    / "l-bcg-h9b-20261101"
)


def _archived_one(slot="A-F1"):
    base = ROOT / "worlds" / slot
    original = (base / "run1/s49-report.json").read_bytes()
    return (
        json.loads(original),
        original,
        json.loads((base / "independent-audit.json").read_bytes()),
        json.loads((base / "original-sha256.json").read_bytes()),
    )


def test_real_h9b_archived_eight_originals_reconstruct_four_sample_patterns():
    x = audit_archived_eight_worlds(ROOT)
    assert x["classification"] == "H10_8_WORLD_ARCHIVED_MOTION_WINDOW_FORENSIC_DEV_ONLY"
    assert x["modal_baseline_worlds"] == 5
    assert x["modal_baseline_world_ids"] == [
        "B-F1", "B-F2", "A-F2", "A-E1", "A-E2",
    ]
    assert x["unique_proxy_patterns"] == 4
    assert x["max_proxy_total_slot"] == "A-F1"
    assert x["min_proxy_total_slot"] == "B-E1"
    assert x["action_move_distinct_counts"] == 3
    assert x["cause_of_variability"] == "UNDETERMINED"
    assert x["paper_native_clock_alignment"] == "NOT_ATTESTED"
    assert x["eval_paper_proxy_matches_frozen_score_source"]
    assert x["original_h9b_eval_unchanged"]
    assert x["qualified_training_worlds"] == 0
    assert x["new_worlds"] == x["original_actions_added"] == 0
    assert x["model_calls"] == x["learning_updates"] == 0
    assert x["l1_advice"] == "DEFER_UNKNOWN"
    assert x["qualification"] == "NO_GO"
    assert x["science"] == "NOT_RUN"
    assert [w["slot"] for w in x["worlds"]] == list(SLOTS)
    assert all(
        not w["source_is_pre_action_condition"]
        and not w["temporal_causation_claim"]
        and w["paper_reported_input_off_all"]
        and w["clock_alignment"] == "NOT_ATTESTED"
        and w["physically_effective_clear"] == "NOT_ATTESTED"
        and w["native_after_seq_before_settling"]
        and w["paper_sample_count"] == 8
        and w["paper_last_tick"] - w["paper_first_tick"] == 7
        for w in x["worlds"]
    )


def test_same_proxy_can_have_different_native_original_action_distance():
    x = audit_archived_eight_worlds(ROOT)
    by = {w["slot"]: w for w in x["worlds"]}
    a = by["A-F2"]
    b = by["B-F1"]
    assert abs(a["paper_proxy_total_m"] - b["paper_proxy_total_m"]) < 1e-10
    assert abs(a["original_action_move_m"] - b["original_action_move_m"]) > 0.1
    assert b["original_s42_distance_m"] == 3.5
    assert a["original_s42_distance_m"] == 2.0
    assert abs(by["A-F1"]["paper_proxy_total_m"] - 0.128320140730378) < 1e-10
    assert abs(by["B-E1"]["paper_proxy_total_m"] - 0.01475441320763693) < 1e-10
    assert by["A-F1"]["paper_positive_sample_count"] == 4
    assert by["B-E1"]["paper_positive_sample_count"] == 1
    assert by["A-F2"]["paper_positive_sample_count"] == 3
    assert by["B-E1"]["first_sample_share_of_proxy"] == 1.0
    assert 0 < by["A-F1"]["first_sample_share_of_proxy"] < 1


@pytest.mark.parametrize("change", [
    "unmatched_digest", "audit_sha", "audit_acceptance", "fake_training",
    "invented_clear", "h8_future_probe", "fake_native_order",
    "fake_action_result", "paper_input_active", "extra_tick",
    "missing_tick", "negative_motion", "wrong_paper_uuid",
    "clock_promotion", "unqualified_goal", "s16_after_l22",
])
def test_h10_forged_original_and_temporal_claims_rejected(change):
    report, original, audit, manifest = _archived_one()
    report, audit, manifest = copy.deepcopy((report, audit, manifest))
    if change == "unmatched_digest":
        original += b"forged"
    elif change == "audit_sha":
        audit["original_sha256"]["s49-report.json"] = "f" * 64
    elif change == "audit_acceptance":
        audit["classification"] = "QUALIFIED_WORLD"
    elif change == "fake_training":
        audit["qualified_training_worlds"] = 1
    elif change == "invented_clear":
        report["live_next_epoch"]["window"]["effective_clear_tick"] = 257
    elif change == "h8_future_probe":
        report["l_bcg_h8_preaction"]["native_seq"] = 100
    elif change == "fake_native_order":
        report["actual_native_actions"][0]["execution_evidence"]["cleanup_receipt"]["seq"] = 20
    elif change == "fake_action_result":
        report["actual_native_actions"][0]["execution_evidence"]["dispatch_receipt"]["result"] = "rejected"
    elif change == "paper_input_active":
        report["live_next_epoch"]["window"]["ticks"][0]["last_reported_input_active"] = True
    elif change == "extra_tick":
        report["live_next_epoch"]["window"]["ticks"].append({"world_tick": 300, "last_reported_input_active": False, "displacement_m": 0})
    elif change == "missing_tick":
        report["live_next_epoch"]["window"]["ticks"].pop()
    elif change == "negative_motion":
        report["live_next_epoch"]["window"]["ticks"][0]["displacement_m"] = -2
    elif change == "wrong_paper_uuid":
        report["live_next_epoch"]["window"]["paper_world_uuid"] = ""
    elif change == "clock_promotion":
        report["l23_paper"]["readback"]["clock_alignment"] = "ATTESTED"
    elif change == "unqualified_goal":
        audit["goal"] = "REACHED"
    else:
        report["l22_settling"]["runtime"]["observed_probe_seqs"] = [1, 2, 3]
    if change not in ("unmatched_digest", "audit_sha", "audit_acceptance", "fake_training", "unqualified_goal"):
        original = json.dumps(report, sort_keys=True).encode()
        digest = hashlib.sha256(original).hexdigest()
        manifest["s49-report.json"] = digest
        audit["original_sha256"]["s49-report.json"] = digest
        if change != "h8_future_probe":
            audit["preaction"] = report["l_bcg_h8_preaction"]
    with pytest.raises((H10Rejected, TypeError, ValueError, AssertionError)):
        inspect_h10_world(
            slot="A-F1", report=report, report_original=original,
            audit=audit, original_manifest=manifest,
        )


def test_h10_refuses_reusing_world_as_distinct_slot():
    r, raw, audit, manifest = _archived_one("A-F1")
    one = inspect_h10_world(
        slot="A-F1", report=r, report_original=raw,
        audit=audit, original_manifest=manifest,
    )
    with pytest.raises(H10Rejected, match="eight archived"):
        summarize_h10((one,))
    # There is no reliance on mutable outcome to admit formal training;
    # even if someone duplicated the row, cross-World IDs fail.
    from dataclasses import replace
    fake = tuple(
        replace(one, slot=slot) for slot in SLOTS
    )
    with pytest.raises(H10Rejected, match="cross-World"):
        summarize_h10(fake)
