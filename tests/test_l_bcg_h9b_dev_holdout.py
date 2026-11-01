"""H9b synthetic protocol/model guards; no H9b real World has run.

Uses typed synthetic 8 independent DEV Worlds; preserved H9a A/B only to
test source-exclusion and timestamp parser, NEVER as H9b experience.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from relay_self.l_bcg_h9a_pair import H9aArmResult
from relay_self.l_bcg_h9b_dev_holdout import (
    SLOTS,
    H9bRecord,
    H9bRejected,
    build_h9b_plan,
    compare_h9b_dev_holdout,
    source_digest,
)
from relay_self.l_bcg_h9b_freeze import (
    freeze_h9b_dev_proxy,
    serialize_frozen,
    validate_frozen_original,
)
from tools.l_bcg_h9b_dev_holdout import _prospective_config_audit

HEAD = "a" * 40
ARCHIVE = (
    Path(__file__).resolve().parents[1] / "docs/evidence"
    / "l-bcg-h9a-20261101"
)


def _example():
    plan = build_h9b_plan(executor_head=HEAD)
    plan_original = (json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n").encode()
    plan_sha = source_digest(plan_original)
    records = []
    for i, (slot, arm, role) in enumerate(SLOTS):
        y = 0.06 + (0.003 if arm == "A" else 0.0) + (i % 2) * 0.001
        source = H9aArmResult(
            arm_id=arm,
            requested_distance_m=2.0 if arm == "A" else 3.5,
            observed_s42_distance_m=2.0 if arm == "A" else 3.5,
            original_preaction_native_seq=21 + i,
            original_session_id=f"synthetic-h9b-session-{i}",
            original_paper_world_id=f"synthetic-h9b-paper-{i}",
            executor_head=HEAD,
            original_report_sha256=f"{i + 1:064x}",
            cheap_near_under_3m=arm == "A",
            sampled_reported_input_off_motion_m=y,
        )
        records.append(H9bRecord(
            slot_id=slot, arm=source,
            frozen_plan_sha256=plan_sha,
            prereg_sha256=f"{i + 30:064x}",
        ))
    first = tuple(records[:4])
    frozen = freeze_h9b_dev_proxy(
        plan=plan, plan_original=plan_original, fit_records=first,
    )
    frozen_bytes = serialize_frozen(frozen)
    digest = source_digest(frozen_bytes)
    records = tuple(
        replace(row, frozen_model_sha256=digest)
        if role == "dev_eval" else row
        for row, (_, _, role) in zip(records, SLOTS)
    )
    return plan, plan_original, records, frozen_bytes


def test_fixed_preregistered_8_worlds_frozen_before_eval():
    plan, raw, records, frozen_bytes = _example()
    model, frozen_sha = validate_frozen_original(
        plan=plan, plan_original=raw,
        fit_records=records[:4], frozen_original=frozen_bytes,
    )
    assert model.plan_sha256 == source_digest(raw)
    assert model.executor_head == HEAD
    assert frozen_sha == records[4].frozen_model_sha256
    assert model.cheap_threshold_m == 3.0
    assert model.classifier == "H9B_FROZEN_4_WORLD_DEV_PROXY_NOT_FORMAL_L1"
    assert not model.goal_attested and not model.effective_clear_attested
    result = compare_h9b_dev_holdout(
        plan=plan, plan_original=raw,
        records=records, frozen_model_original=frozen_bytes,
    )
    assert result.classification == "H9B_8_WORLD_DEV_PROXY_FIT_EVAL_ONLY"
    assert (result.fit_world_count, result.eval_world_count) == (4, 4)
    assert result.model_frozen_before_eval
    assert result.candidate_condition_responsive
    assert result.candidate_vs_cheap_threshold == "EQUIVALENT_WITHIN_1E-9_M"
    assert len(result.scores) == 4
    assert result.cheap_global_mae_m >= 0
    assert abs(result.cheap_threshold_bin_mae_m - result.candidate_linear_mae_m) <= 1e-9
    assert not result.causal_learning_improvement_attested
    assert not result.cross_world_generalization_attested
    assert result.physical_training_worlds == result.formal_heldout_worlds == 0
    assert result.learned_l1_attention == "DEFER_UNKNOWN"
    assert result.qualification == "NO_GO" and result.science == "NOT_RUN"


def test_missing_heldout_fails_bounded_eight_world_rule():
    plan, raw, records, model = _example()
    with pytest.raises(H9bRejected):
        compare_h9b_dev_holdout(
            plan=plan, plan_original=raw,
            records=records[:7], frozen_model_original=model,
        )


@pytest.mark.parametrize("change", [
    "duplicate_world", "duplicate_session", "duplicate_report",
    "duplicate_prereg", "wrong_order", "wrong_arm",
    "wrong_head", "old_h9a_session", "old_h9a_world",
    "future_marker_missing", "future_model_wrong", "fit_model_claim",
    "goal_attested", "qualified_training", "action_authority",
    "changed_prereg_plan", "no_native_arm_match", "wrong_native_distance",
])
def test_world_reuse_or_qualification_fails_closed(change):
    plan, raw, records, model = _example()
    rows = list(records)
    if change in ("duplicate_world", "duplicate_session", "duplicate_report",
                  "duplicate_prereg"):
        key = {
            "duplicate_world": "original_paper_world_id",
            "duplicate_session": "original_session_id",
            "duplicate_report": "original_report_sha256",
        }.get(change)
        if key:
            rows[5] = replace(rows[5], arm=replace(
                rows[5].arm, **{key: getattr(rows[4].arm, key)}
            ))
        else:
            rows[5] = replace(rows[5], prereg_sha256=rows[4].prereg_sha256)
    elif change == "wrong_order":
        rows[5], rows[4] = rows[4], rows[5]
    elif change == "wrong_arm":
        rows[5] = replace(rows[5], arm=replace(rows[5].arm, arm_id="B"))
    elif change == "wrong_head":
        rows[5] = replace(rows[5], arm=replace(rows[5].arm, executor_head="b" * 40))
    elif change == "old_h9a_session":
        rows[5] = replace(rows[5], arm=replace(
            rows[5].arm, original_session_id="1ba73115-4038-40ef-8435-90ad7c7e8f92",
        ))
    elif change == "old_h9a_world":
        rows[5] = replace(rows[5], arm=replace(
            rows[5].arm,
            original_paper_world_id="48e59ab1-dba7-440c-8a6e-e63b064a9f27",
        ))
    elif change == "future_marker_missing":
        rows[5] = replace(rows[5], frozen_model_sha256=None)
    elif change == "future_model_wrong":
        rows[5] = replace(rows[5], frozen_model_sha256="b" * 64)
    elif change == "fit_model_claim":
        rows[0] = replace(rows[0], frozen_model_sha256="b" * 64)
    elif change == "goal_attested":
        rows[5] = replace(rows[5], arm=replace(
            rows[5].arm, physical_effective_clear_attested=True,
        ))
    elif change == "qualified_training":
        rows[5] = replace(rows[5], arm=replace(
            rows[5].arm, qualified_training_worlds=1,
        ))
    elif change == "action_authority":
        rows[5] = replace(rows[5], arm=replace(rows[5].arm, new_actions=1))
    elif change == "changed_prereg_plan":
        rows[5] = replace(rows[5], frozen_plan_sha256="a" * 64)
    elif change == "no_native_arm_match":
        rows[5] = replace(rows[5], arm=replace(
            rows[5].arm, observed_arm_matched=False,
        ))
    elif change == "wrong_native_distance":
        rows[5] = replace(rows[5], arm=replace(
            rows[5].arm, observed_s42_distance_m=9.0,
        ))
    with pytest.raises(H9bRejected):
        compare_h9b_dev_holdout(
            plan=plan, plan_original=raw,
            records=tuple(rows), frozen_model_original=model,
        )


@pytest.mark.parametrize("change", [
    "threshold", "slots", "future_before_fit", "bad_head",
    "relaxed_config", "qualification", "missing_role",
])
def test_protocol_drift_is_rejected_even_when_model_can_be_refitted(change):
    plan, raw, records, model = _example()
    plan = json.loads(json.dumps(plan))
    if change == "threshold":
        plan["cheap_threshold_m"] = 2.5
    elif change == "slots":
        plan["slots"][0]["slot_id"] = "B-F1"
    elif change == "future_before_fit":
        plan["fit_before_eval"] = False
    elif change == "bad_head":
        plan["executor_head"] = "not-a-sha"
    elif change == "relaxed_config":
        plan["config_rule"] = "IGNORE_ALL_COMMENTS"
    elif change == "qualification":
        plan["qualified_training_worlds"] = 1
    else:
        plan["slots"][1].pop("role")
    mutated = json.dumps(plan).encode()
    with pytest.raises(H9bRejected):
        compare_h9b_dev_holdout(
            plan=plan, plan_original=mutated,
            records=records, frozen_model_original=model,
        )


def test_frozen_fit_only_bytes_change_rejected():
    plan, raw, records, frozen = _example()
    altered = frozen.replace(b'"cheap_threshold_m":3.0', b'"cheap_threshold_m":2.0')
    assert altered != frozen
    with pytest.raises(H9bRejected):
        compare_h9b_dev_holdout(
            plan=plan, plan_original=raw,
            records=records, frozen_model_original=altered,
        )


def test_existing_h9a_originals_parse_as_timestamp_example_but_cannot_be_h9b_data():
    # Old posthoc H9a config equivalence is now prospective H9b protocol
    # only on NEW Worlds. This is a byte parser test; old pair stays rejected.
    shas = _prospective_config_audit((ARCHIVE / "a", ARCHIVE / "b"))
    assert len(shas) == 2 and shas[0] != shas[1]
    old = json.loads((ARCHIVE / "pair/result-rejected.json").read_bytes())
    assert old["exploratory_pair_pass"] is False


def test_eval_outcome_cannot_change_frozen_fit_predictions():
    plan, raw, records, frozen = _example()
    first = compare_h9b_dev_holdout(
        plan=plan, plan_original=raw,
        records=records, frozen_model_original=frozen,
    )
    rows = list(records)
    rows[6] = replace(rows[6], arm=replace(
        rows[6].arm,
        sampled_reported_input_off_motion_m=0.2,
    ))
    after = compare_h9b_dev_holdout(
        plan=plan, plan_original=raw,
        records=tuple(rows), frozen_model_original=frozen,
    )
    assert [x.candidate_linear_pred_m for x in first.scores] == [
        x.candidate_linear_pred_m for x in after.scores
    ]
    assert [x.cheap_threshold_bin_pred_m for x in first.scores] == [
        x.cheap_threshold_bin_pred_m for x in after.scores
    ]
    assert first.candidate_linear_mae_m != after.candidate_linear_mae_m
    assert first.cheap_threshold_bin_mae_m != after.cheap_threshold_bin_mae_m


def test_fit_outcome_rewrite_after_freeze_refused_even_with_same_world_ids():
    plan, raw, records, frozen = _example()
    rows = list(records)
    rows[1] = replace(rows[1], arm=replace(
        rows[1].arm,
        sampled_reported_input_off_motion_m=0.12,
    ))
    with pytest.raises(H9bRejected, match="frozen DEV model bytes differ"):
        compare_h9b_dev_holdout(
            plan=plan, plan_original=raw,
            records=tuple(rows), frozen_model_original=frozen,
        )


def test_saved_coefficients_are_deserialized_after_integrity_audit(monkeypatch):
    plan, raw, records, original = _example()
    import relay_self.l_bcg_h9b_freeze as module

    def forbidden_fit(**kwargs):
        raise AssertionError("evaluation must not call fit API")

    monkeypatch.setattr(module, "freeze_h9b_dev_proxy", forbidden_fit)
    loaded, digest = validate_frozen_original(
        plan=plan, plan_original=raw, fit_records=records[:4],
        frozen_original=original,
    )
    assert serialize_frozen(loaded) == original
    assert loaded.candidate_slope == json.loads(original)["candidate_slope"]
    assert digest == source_digest(original)


def test_actual_executor_and_runtime_assets_checked_against_prereg(tmp_path):
    import shutil
    from datetime import datetime

    from tools.l_bcg_h9b_dev_holdout import _runtime_source_audit

    root = tmp_path / "world"
    shutil.copytree(ARCHIVE / "a", root)
    prereg = json.loads((root / "predeclared.json").read_bytes())
    prereg["declared_utc"] = "2026-11-01T07:00:00+00:00"
    attempt = datetime.fromisoformat("2026-11-01T07:10:00+00:00")
    _runtime_source_audit(root, prereg, attempt)
    prereg["executor_head"] = "b" * 40
    with pytest.raises(ValueError, match="actual executor HEAD"):
        _runtime_source_audit(root, prereg, attempt)
    prereg["executor_head"] = json.loads((root / "predeclared.json").read_bytes())["executor_head"]
    prereg["runtime_assets"]["plugin"]["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="actual runtime asset"):
        _runtime_source_audit(root, prereg, attempt)


def test_original_mutation_and_delayed_declaration_rejected(tmp_path):
    import shutil
    from datetime import datetime

    from tools.l_bcg_h9b_dev_holdout import _runtime_source_audit

    root = tmp_path / "world"
    shutil.copytree(ARCHIVE / "a", root)
    prereg = json.loads((root / "predeclared.json").read_bytes())
    prereg["declared_utc"] = "2026-11-01T08:00:00+00:00"
    attempt = datetime.fromisoformat("2026-11-01T07:10:00+00:00")
    with pytest.raises(ValueError, match="chronology"):
        _runtime_source_audit(root, prereg, attempt)
    prereg["declared_utc"] = "2026-11-01T07:00:00+00:00"
    with (root / "run1/server.log").open("ab") as out:
        out.write(b"mutated")
    with pytest.raises(ValueError, match="original bytes changed"):
        _runtime_source_audit(root, prereg, attempt)


def test_freeze_boundary_rejects_early_eval_or_late_fit_audit(tmp_path):
    from tools.l_bcg_h9b_dev_holdout import _check_freeze_boundary

    model = tmp_path / "frozen-model.json"
    model.write_bytes(b"frozen original")
    boundary = {
        "frozen_original_sha256": source_digest(model.read_bytes()),
        "plan_sha256": "a" * 64,
        "frozen_utc": "2026-11-01T07:05:00+00:00",
    }
    model.with_suffix(".boundary.json").write_text(json.dumps(boundary))
    for slot, _, role in SLOTS:
        root = tmp_path / slot
        (root / "run1").mkdir(parents=True)
        marker = {"launcher_entered_utc": "2026-11-01T07:00:00+00:00" if role == "dev_fit"
                  else "2026-11-01T07:06:00+00:00"}
        (root / "run1/WORLD_ATTEMPT_STARTED.json").write_text(json.dumps(marker))
        (root / "audited-complete.json").write_text(json.dumps({
            "completed_utc": "2026-11-01T07:04:00+00:00",
        }))
    _check_freeze_boundary(tmp_path, model, "a" * 64)
    path = tmp_path / "B-E1/run1/WORLD_ATTEMPT_STARTED.json"
    path.write_text(json.dumps({"launcher_entered_utc": "2026-11-01T07:03:00+00:00"}))
    with pytest.raises(ValueError, match="EVAL World"):
        _check_freeze_boundary(tmp_path, model, "a" * 64)
