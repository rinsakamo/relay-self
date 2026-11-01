"""#653 L1-MP1: archived independent World replay and fail-closed controls.

These original-audit JSON files have been preserved from two *different*
Minecraft DEV Worlds. Their summaries are not an alternative authentication
of the original Paper logs. CI does not run a fresh Minecraft World.
"""
from __future__ import annotations

import copy
import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from adapters.mineflayer.m02_paper_dev.s50_live_paper_window import (
    S50LivePaperTick,
    S50LivePaperWindow,
)
from adapters.mineflayer.self_body_s50_l1_motion_prediction import (
    MotionPredictionRejected,
    evaluate_heldout,
    freeze_forecast,
    from_archival_readback,
    from_live_window,
)

ROOT = Path(__file__).resolve().parents[1]
ROUTE_B = ROOT / (
    "docs/evidence/issue651-route-b-20261031/run1/independent-original-readback.json"
)
L1_SHADOW = ROOT / (
    "docs/evidence/issue653-l1-motion-shadow-20261031/run1/"
    "independent-l1-original-readback.json"
)


def audited_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def pair():
    return (
        from_archival_readback(audited_json(ROUTE_B)),
        from_archival_readback(audited_json(L1_SHADOW)),
    )


def test_archived_two_original_worlds_train_prior_and_score_heldout():
    train, heldout = pair()
    report = evaluate_heldout(train, heldout)
    assert train.session_id == "15f04c47-1a80-4705-99e1-ebedb963e3a3"
    assert heldout.session_id == "3da31d96-95bf-49db-ac5e-5fabe8f35b38"
    assert train.paper_world_uuid != heldout.paper_world_uuid
    assert report.sample_pairs == 7
    assert math.isclose(report.slope, 0.20331885786720635, abs_tol=1e-12)
    assert math.isclose(report.l1_linear.mae_m, 0.000723384425636194, abs_tol=1e-12)
    assert math.isclose(report.l1_linear.rmse_m, 0.0013722649368450835, abs_tol=1e-12)
    assert report.l1_linear.mae_m < report.no_memory_zero.mae_m
    assert report.l1_linear.mae_m < report.last_value.mae_m
    assert report.l1_linear.mae_m < report.training_mean.mae_m
    assert report.l1_linear == report.cheap_same_linear
    assert report.exact_cheap_equivalence
    assert report.classification == "CHEAP_LINEAR_EQUIVALENT"
    assert report.provenance_ceiling == "ARCHIVAL_READBACK_REPLAY_NOT_REAUTHENTICATED"
    assert report.goal == "UNDETERMINED"
    assert not any((
        report.learning_updates, report.s10_updates, report.s11_grants,
        report.p1_wait_admitted, report.extra_actions, report.native_probes,
    ))


def test_reverse_is_sensitivity_not_the_preregistered_primary_split():
    a, b = pair()
    reverse = evaluate_heldout(b, a)
    assert reverse.sample_pairs == 7
    assert math.isclose(reverse.l1_linear.mae_m, 0.0006927084716710948, abs_tol=1e-12)
    assert reverse.l1_linear == reverse.cheap_same_linear
    assert reverse.goal == "UNDETERMINED"


def test_bounded_frozen_forecast_depends_on_training_not_future_labels():
    a, b = pair()
    original = freeze_forecast(a)
    different_heldout = replace(b, steps=tuple(
        replace(s, displacement_m=float(i) / 100)
        for i, s in enumerate(b.steps)
    ))
    assert freeze_forecast(a) == original  # evaluation never retrains
    assert evaluate_heldout(a, b).slope == evaluate_heldout(a, different_heldout).slope
    assert original.slope > 0
    assert not original.learned_l1_policy
    assert original.s10_updates == original.s11_grants == original.action_issues == 0


def test_exact_no_memory_control_and_one_bit_have_no_new_intelligence_claim():
    a, b = pair()
    evaluated = evaluate_heldout(a, b)
    # The learner itself IS a simple single-feature linear rule. Same info,
    # identical outputs and errors, irrespective of any numerical advantage
    # over the weaker ZERO / LAST / MEAN controls.
    assert evaluated.l1_linear == evaluated.cheap_same_linear
    assert evaluated.no_memory_zero.mae_m > 0
    assert evaluated.classification == "CHEAP_LINEAR_EQUIVALENT"


@pytest.mark.parametrize("mutation", [
    "same_session", "same_world", "same_digest", "foreign_subject",
    "different_source_type", "short_window", "long_window", "bad_tick",
    "negative_displacement", "nan_displacement", "bool_displacement",
    "inf_displacement", "missing_digest", "invalid_digest", "fake_source",
])
def test_source_identity_length_finite_and_provenance_fences(mutation):
    a, b = pair()
    steps = list(b.steps)
    if mutation == "same_session":
        b = replace(b, session_id=a.session_id)
    elif mutation == "same_world":
        b = replace(b, paper_world_uuid=a.paper_world_uuid)
    elif mutation == "same_digest":
        b = replace(b, paper_prefix_sha256=a.paper_prefix_sha256)
    elif mutation == "foreign_subject":
        b = replace(b, subject_uuid="foreign-subject")
    elif mutation == "different_source_type":
        b = replace(b, source_ceiling="LIVE_PROVISIONAL_PAPER_ONLY")
    elif mutation == "short_window":
        b = replace(b, steps=b.steps[:-1])
    elif mutation == "long_window":
        b = replace(b, steps=(*b.steps, b.steps[-1]))
    elif mutation == "bad_tick":
        steps[2] = replace(steps[2], world_tick=10000)
    elif mutation == "negative_displacement":
        steps[1] = replace(steps[1], displacement_m=-0.1)
    elif mutation == "nan_displacement":
        steps[1] = replace(steps[1], displacement_m=float("nan"))
    elif mutation == "bool_displacement":
        steps[1] = replace(steps[1], displacement_m=True)
    elif mutation == "inf_displacement":
        steps[1] = replace(steps[1], displacement_m=float("inf"))
    elif mutation == "missing_digest":
        b = replace(b, paper_prefix_sha256="")
    elif mutation == "invalid_digest":
        b = replace(b, paper_prefix_sha256="x" * 64)
    elif mutation == "fake_source":
        b = replace(b, source_ceiling="SOURCE_VERIFIED")
    if mutation in (
        "bad_tick", "negative_displacement", "nan_displacement",
        "bool_displacement", "inf_displacement",
    ):
        b = replace(b, steps=tuple(steps))
    with pytest.raises(MotionPredictionRejected):
        evaluate_heldout(a, b)


@pytest.mark.parametrize("mutation", [
    "goal", "qualification", "science", "classification", "sample",
    "input_flag", "scope", "rest", "clear", "complete", "missing",
    "alias", "bool_tick", "fake_goal_admitted", "p1", "sha",
])
def test_archival_readback_cannot_claim_owner_authority(mutation):
    source = copy.deepcopy(audited_json(L1_SHADOW))
    window = source["route_b"]["live_window"]
    if mutation == "goal":
        source["goal"] = "REACHED"
    elif mutation == "qualification":
        source["qualification"] = "PASS"
    elif mutation == "science":
        source["science"] = "PASS"
    elif mutation == "classification":
        source["classification"] = "DEV_WORLD_FABRICATED"
    elif mutation == "sample":
        window["ticks"].pop()
    elif mutation == "input_flag":
        window["ticks"][0]["last_reported_input_active"] = 1
    elif mutation == "scope":
        window["scope"] = "SOURCE_COMPLETE"
    elif mutation == "rest":
        window["physical_stability_attested"] = True
    elif mutation == "clear":
        window["effective_clear_tick"] = "251"
    elif mutation == "complete":
        window["node_trace_complete"] = True
    elif mutation == "missing":
        del window["ticks"][0]["displacement_m"]
    elif mutation == "alias":
        window["marker_id"] = "fake"
    elif mutation == "bool_tick":
        window["ticks"][0]["world_tick"] = True
    elif mutation == "fake_goal_admitted":
        window["goal_admitted"] = True
    elif mutation == "p1":
        window["p1_wait_granted"] = 8
    else:
        window["paper_prefix_sha256"] = "tampered"
    with pytest.raises(MotionPredictionRejected):
        from_archival_readback(source)


def test_existing_in_process_typed_window_can_supply_same_readonly_features():
    archive = audited_json(ROUTE_B)["live_window"]
    window = S50LivePaperWindow(
        session_id=archive["session_id"], action_id=archive["action_id"],
        marker_id=archive["marker_id"],
        paper_world_uuid=archive["paper_world_uuid"],
        subject_uuid=archive["subject_uuid"],
        paper_prefix_sha256=archive["paper_prefix_sha256"],
        paper_prefix_bytes=archive["paper_prefix_bytes"],
        ticks=tuple(S50LivePaperTick(
            x["world_tick"], x["displacement_m"],
            x["last_reported_input_active"],
        ) for x in archive["ticks"]),
        input_event_count_at_window_end=0,
    )
    out = from_live_window(window)
    assert out.source_ceiling == "LIVE_PROVISIONAL_PAPER_ONLY"
    assert out.steps == pair()[0].steps
    with pytest.raises(MotionPredictionRejected):
        from_live_window(replace(window, goal_admitted=True))
    with pytest.raises(MotionPredictionRejected):
        from_live_window({"paper": "fake"})


def test_empty_real_training_is_zero_but_never_qualified_l1_learning():
    train, heldout = pair()
    quiet = replace(train, steps=tuple(
        replace(step, displacement_m=0.0) for step in train.steps
    ))
    report = evaluate_heldout(quiet, heldout)
    assert report.slope == 0
    assert report.l1_linear == report.no_memory_zero
    assert report.l1_linear == report.cheap_same_linear
    assert report.s10_updates == report.s11_grants == 0
