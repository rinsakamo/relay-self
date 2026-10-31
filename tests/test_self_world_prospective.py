"""Stage L source-sealed pre-Action PRD tests; NO real Minecraft/Java/Node.

Fixtures are original S49/S15 shaped native data, NOT proof of physical
prospective performance. Positive physical proof requires a separate DEV run.
"""
from __future__ import annotations

import copy
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.self_action_evidence import verify_native_action_evidence
from adapters.mineflayer.self_world_prospective import (
    ProspectiveSourceRejected,
    ProspectiveWitnessWriter,
    verify_prospective_native_reviews,
)
from test_self_action_evidence import _fixture_evidence
from test_self_live_think import native_probe


def _sealed_fixture(tmp_path):
    report = _fixture_evidence()
    sid = report["session_id"]
    path = tmp_path / "pre-action.jsonl"
    writer = ProspectiveWitnessWriter(path)
    for decision in report["decisions"]:
        probe = native_probe(decision["probe_seq"], decision["distance_m"], sid=sid)
        fact = replace(
            probe.snapshot.nearby_entities[0], entity_id=decision["entity_id"],
        )
        probe = replace(
            probe,
            request_id=f"s49-actual:{sid}:event-{decision['event_seq']}",
            snapshot=replace(probe.snapshot, nearby_entities=(fact,)),
        )
        # This is the exact code path invoked BEFORE original S49 Action.
        writer.record(probe)
    writer.close()
    for action in report["actual_native_actions"]:
        decision = next(d for d in report["decisions"]
                        if d["event_seq"] == action["event_seq"])
        evidence = action["execution_evidence"]
        for key in ("before_observation", "dispatch_receipt",
                    "cleanup_receipt", "after_observation"):
            frame = evidence[key]
            frame["seq"] += decision["probe_seq"]
            frame["provenance"]["reference"] = f"{sid}:{frame['seq']}"
        for key in ("before_observation", "after_observation"):
            snapshot = evidence[key]["snapshot"]
            snapshot["nearby_entities"] = [{
                "entity_id": decision["entity_id"], "name": "zombie",
                "entity_type": "mob", "distance": 2.0,
                "position": {"x": 2.0, "y": 64.0, "z": 0.0},
            }]
            snapshot["nearby_entities_coverage"]["candidate_count"] = 1
        verify_native_action_evidence(
            evidence, action_id=action["action"], session_id=sid,
            movement_m=action["movement_m"],
        )
    return report, path.read_bytes()


def test_stage_l_two_immutable_probes_forecast_before_real_action_fixture(tmp_path):
    report, sealed = _sealed_fixture(tmp_path)
    original = sealed.decode().splitlines()
    assert len(original) == 3
    a, b, c = [json.loads(x) for x in original]
    assert (a["native_seq"], b["native_seq"], c["native_seq"]) == (6, 14, 22)
    assert b["target_ref"] == "entity-13"
    assert b["predicted_value"] == "zombie"
    assert b["source_ref"].startswith("present:")
    assert b["sha256"] == c["prev_sha256"]
    results = verify_prospective_native_reviews(report, sealed)
    assert len(results) == 2
    assert all(x["status"] == "match" for x in results)
    assert all(x["reason"] == "observed_prediction_match" for x in results)
    assert all(x["forecast_was_sealed_in_s49_probe_callback"] for x in results)
    assert all(x["action_authorizations_from_forecast"] == 0 for x in results)
    assert all(x["s10_learning_committed"] is False for x in results)


@pytest.mark.parametrize("bad", (
    "missing_record", "forged_digest", "foreign_probe", "post_action_seq",
    "forged_s16_before", "wrong_entity", "reordered_rows", "duplicate",
))
def test_stage_l_no_hindsight_or_forged_native_lineage(tmp_path, bad):
    report, sealed = _sealed_fixture(tmp_path)
    report = copy.deepcopy(report)
    rows = [json.loads(x) for x in sealed.splitlines()]
    if bad == "missing_record":
        rows.pop(1)
    elif bad == "forged_digest":
        rows[1]["predicted_value"] = "skeleton"
    elif bad == "foreign_probe":
        report["source_pair_trace"][1]["probe_seq"] += 1
    elif bad == "post_action_seq":
        report["actual_native_actions"][0]["execution_evidence"][
            "before_observation"]["seq"] = rows[1]["native_seq"]
    elif bad == "forged_s16_before":
        report["actual_native_actions"][0]["execution_evidence"][
            "before_observation"]["snapshot"]["nearby_entities"][0][
                "entity_id"
            ] += 10
    elif bad == "wrong_entity":
        report["decisions"][1]["entity_id"] = 999
    elif bad == "reordered_rows":
        rows[1], rows[2] = rows[2], rows[1]
    else:
        rows.append(copy.deepcopy(rows[2]))
    tampered = b"".join(json.dumps(row).encode() + b"\n" for row in rows)
    with pytest.raises(ProspectiveSourceRejected):
        verify_prospective_native_reviews(report, tampered)


def test_stage_l_unseen_successor_is_unknown_not_failure(tmp_path):
    report, sealed = _sealed_fixture(tmp_path)
    action = report["actual_native_actions"][0]
    after = action["execution_evidence"]["after_observation"]["snapshot"]
    after["nearby_entities"] = []
    after["nearby_entities_coverage"]["candidate_count"] = 0
    results = verify_prospective_native_reviews(report, sealed)
    assert results[0]["status"] == "undetermined"
    assert results[0]["reason"] == "target_or_property_unobserved"
    assert results[0]["observed_value"] is None
    assert results[1]["status"] == "match"


def test_stage_l_positive_disagreement_is_not_reward(tmp_path):
    report, sealed = _sealed_fixture(tmp_path)
    action = report["actual_native_actions"][0]
    after = action["execution_evidence"]["after_observation"]["snapshot"]
    after["nearby_entities"][0]["name"] = "skeleton"
    results = verify_prospective_native_reviews(report, sealed)
    assert results[0]["status"] == "mismatch"
    assert results[0]["observed_value"] == "skeleton"
    assert results[0]["s17_feedback_created"] is False
    assert results[0]["s10_learning_committed"] is False
    assert results[0]["action_authorizations_from_forecast"] == 0


def test_stage_l_new_file_exclusive_and_unrelated_existing_file_preserved(tmp_path):
    path = tmp_path / "pre-action.jsonl"
    first = ProspectiveWitnessWriter(path)
    first.close()
    with pytest.raises(FileExistsError):
        ProspectiveWitnessWriter(path)
    assert path.read_bytes() == b""
