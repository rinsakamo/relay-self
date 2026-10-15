"""Negative controls for the V7 prospective pre-science roster.

Synthetic metadata ONLY: these tests cannot qualify a real Paper World.
"""
from __future__ import annotations

import copy
import json

import pytest

from experiments.validation import v7_m02_trial_roster as roster
from experiments.validation.v7_m02_physics import V7Rejected


def _attempt(aid: str = "dev-original-001") -> dict:
    return {
        "attempt_id": aid,
        "mode": "DEV",
        "outcome": "UNDETERMINED",
        "original_bundle_sha256": "a" * 64,
        "r_review": "NOT_RUN",
        "science_trial": False,
        "grant_reused": False,
    }


def test_exact_twenty_slots_no_physical_science():
    doc = roster.new_roster()
    result = roster.review_roster(doc)
    assert len({(x["seed"], x["arm"]) for x in doc["slots"]}) == 20
    assert doc["slots"][0]["seed"] == 61021
    assert result["prospective_science_slots"] == 20
    assert result["actual_v7_science_trials"] == 0
    assert result["v7_science_go"] is False
    assert result["r_physical_authentication_by_this_review"] is False


def test_dev_and_r_prescience_metadata_stay_not_run():
    doc = roster.new_roster()
    doc["slots"][0]["prescience_attempts"].append(_attempt())
    another = _attempt("r-review-only-002")
    another["mode"] = "QUALIFICATION"
    another["outcome"] = "PASS_CLAIMED"
    another["r_review"] = "PASS_CLAIMED"
    doc["slots"][1]["prescience_attempts"].append(another)
    result = roster.review_roster(doc)
    assert result["prescience_attempts_preserved"] == {
        "DEV": 1, "QUALIFICATION": 1,
    }
    assert result["qualified_physics_effect_by_this_review"] is False
    assert result["actual_v7_science_trials"] == 0


@pytest.mark.parametrize("mutation", [
    lambda x: x["slots"].pop(),
    lambda x: x["slots"][1].update(copy.deepcopy(x["slots"][0])),
    lambda x: x["slots"][0].update({"arm": "OTHER"}),
    lambda x: x["slots"][0].update({"config_sha256": "b" * 64}),
    lambda x: x["slots"][0].update({"science_status": "PASS"}),
    lambda x: x.update({"science_trials_executed": 1}),
    lambda x: x.update({"science_execution_authorized": True}),
    lambda x: x.update({"historical_qualification_grant_reused": True}),
    lambda x: x.update({"v7_manifest_sha256": "0" * 64}),
])
def test_reject_slot_drift_or_science_promotion(mutation):
    doc = roster.new_roster()
    mutation(doc)
    with pytest.raises(V7Rejected):
        roster.review_roster(doc)


@pytest.mark.parametrize("key,value", [
    ("mode", "SCIENCE"),
    ("outcome", "SCIENCE_PASS"),
    ("science_trial", True),
    ("grant_reused", True),
    ("r_review", "QUALIFIED"),
    ("original_bundle_sha256", "a" * 63),
    ("original_bundle_sha256", 42),
    ("attempt_id", "../unsafe"),
])
def test_reject_fake_attempt_claims(key, value):
    doc = roster.new_roster()
    bad = _attempt()
    bad[key] = value
    doc["slots"][0]["prescience_attempts"].append(bad)
    with pytest.raises(V7Rejected):
        roster.review_roster(doc)


def test_duplicate_id_across_arms_is_not_a_new_trial():
    doc = roster.new_roster()
    doc["slots"][0]["prescience_attempts"].append(_attempt())
    doc["slots"][1]["prescience_attempts"].append(_attempt())
    with pytest.raises(V7Rejected, match="duplicate"):
        roster.review_roster(doc)


def test_invalid_attempt_keeps_no_original_hash_and_no_go():
    doc = roster.new_roster()
    a = _attempt()
    a["outcome"] = "FAILED"
    a["original_bundle_sha256"] = None
    doc["slots"][0]["prescience_attempts"].append(a)
    result = roster.review_roster(doc)
    assert result["prescience_attempts_preserved"]["DEV"] == 1
    assert result["v7_science_go"] is False


def test_json_duplicate_and_nonfinite_rejected(tmp_path):
    doc = roster.new_roster()
    path = tmp_path / "roster.json"
    raw = json.dumps(doc)
    path.write_text(raw.replace('"schema":', '"schema": "extra", "schema":', 1))
    with pytest.raises(V7Rejected, match="duplicate"):
        roster.read_roster(path)
    path.write_text(raw.replace('"science_trials_executed": 0',
                                '"science_trials_executed": NaN', 1))
    with pytest.raises(V7Rejected, match="nonfinite"):
        roster.read_roster(path)
