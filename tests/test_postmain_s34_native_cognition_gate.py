"""S34 qualification of true native Minecraft threat input and Skill2 goal source."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_source_native_world as s27
from adapters.mineflayer.s34_native_world_cognition_ci import (
    MAX_GOAL_DISTANCE_M,
    S34EvidenceFailure,
    _native_threat,
    _real_epoch_one,
    _native_epoch_two,
    _real_skill2_evidence,
)

ROOT = Path(__file__).resolve().parents[1]


def _probe(*, distance=2.0, request_id="s34-unit:001"):
    _, _, _, kwargs = s27._fixture(distance_m=distance)
    observation = replace(kwargs["observation"], request_id=request_id)
    return observation


def test_s34_actual_native_source_alias_is_exact_typed_protocol():
    obs = _probe(distance=2.0)
    native = _native_threat(obs, "s34-unit:001")
    assert native.distance_m == 2.0
    assert native.entity_id > 0
    assert native.request_id == obs.request_id
    assert native.observation.provenance == obs.provenance
    assert MAX_GOAL_DISTANCE_M == 4.0


@pytest.mark.parametrize("variant", [
    "missing_id", "wrong_id", "wrong_name", "absent", "incomplete",
    "wrong_entity", "nonprobe",
])
def test_threat_gate_fails_closed_for_unsupported_sensor_sources(variant):
    obs = _probe()
    expected_id = obs.snapshot.nearby_entities[0].entity_id
    req = obs.request_id
    if variant == "missing_id":
        obs = replace(obs, request_id=None)
    elif variant == "wrong_id":
        req = "s34-another:request"
    elif variant == "wrong_name":
        entity = replace(obs.snapshot.nearby_entities[0], name="skeleton")
        obs = replace(obs, snapshot=replace(obs.snapshot, nearby_entities=(entity,)))
    elif variant == "absent":
        coverage = replace(obs.snapshot.nearby_entities_coverage, candidate_count=0)
        obs = replace(obs, snapshot=replace(obs.snapshot,
            nearby_entities=(), nearby_entities_coverage=coverage))
    elif variant == "incomplete":
        coverage = replace(obs.snapshot.nearby_entities_coverage, truncated=True)
        obs = replace(obs, snapshot=replace(obs.snapshot, nearby_entities_coverage=coverage))
    elif variant == "wrong_entity":
        expected_id += 100
    else:
        obs = replace(obs, request_id=None, kind="entities")
    with pytest.raises((S34EvidenceFailure, ValueError)):
        _native_threat(obs, req, expected_entity_id=expected_id)


def test_goal_threshold_does_not_claim_false_failure():
    assert 3.99 < MAX_GOAL_DISTANCE_M
    assert 4.0 >= MAX_GOAL_DISTANCE_M
    close = _native_threat(_probe(distance=2.0), "s34-unit:001")
    far = _native_threat(_probe(distance=5.0), "s34-unit:001")
    assert close.distance_m < MAX_GOAL_DISTANCE_M
    assert far.distance_m >= MAX_GOAL_DISTANCE_M


def test_exact_native_evidence_is_threaded_into_s19_cognition_not_just_preflight():
    source = (ROOT / "adapters/mineflayer/s34_native_world_cognition_ci.py").read_text()
    assert callable(_real_epoch_one) and callable(_native_epoch_two)
    assert "native.observation.provenance" in source
    assert 'values["external"][1].provenance == native.observation.provenance' in source
    assert "s20.s19._epoch_two(" not in source
    assert 'status = (' in source and "goal.distance_m < MAX_GOAL_DISTANCE_M" in source
    assert "s21.SkillGoalEvidence(" in source
    assert "provenance=goal.observation.provenance" in source
    assert "project_source_native_threat(" in source
    assert "run_explicit_postfailure_epoch(" in source
    assert callable(_real_skill2_evidence)


def test_static_plan_is_not_fake_dynamic_result():
    plan = json.loads((ROOT / "docs/postmain-s34-plan-receipt.json").read_text())
    assert plan["base_head"] == "9de005def9cb8727cd388e382da3b95d4fc8bbdf"
    assert plan["status"] == "PENDING_CI"
    assert plan["qualification_requires"] == "S34_REPORT.status == PASS"
    assert plan["skill2_goal_criterion"].startswith("escape from nearest exact zombie")
