"""Factorial invariants and adversarial envelopes; no model/strategy execution."""
import json
from copy import deepcopy
from dataclasses import asdict, replace

import pytest

from experiments import self_world_cognitive_evidence_use as gate
from experiments import self_world_goal_cost_orthogonality as audit
from experiments import self_world_host_two_axis as host
from experiments.self_world_metadata_ablation import digest
from test_self_world_host_two_axis import sources as verified_sources


@pytest.fixture
def sources(tmp_path, monkeypatch):
    return verified_sources.__wrapped__(tmp_path, monkeypatch)


@pytest.fixture
def matrix(sources, monkeypatch):
    monkeypatch.setattr(host.probe, "load_sources", lambda _: sources)
    pins = {case.case_id: digest(asdict(replay)) for case, replay in sources}
    return audit.collect_factorial(None, pins)


def test_all_forty_cells_and_pair_counts(matrix):
    result = audit.audit_factorial(matrix)
    assert result == {"conditions": 40, "READY": 30, "DEFER": 10,
                      "goal_pairs": 20, "cost_pairs": 20,
                      "model_necessity": "MODEL_NECESSITY_UNDETERMINED",
                      "scope": gate.SCOPE, "strategy_selections": 0}


@pytest.mark.parametrize("epoch_index", range(10))
def test_each_fixed_source_has_goal_invariance_and_only_cost_delta(matrix, epoch_index):
    rows = matrix[epoch_index * 4:epoch_index * 4 + 4]
    assert rows[0].host_record == rows[1].host_record == rows[2].host_record == rows[3].host_record
    for a, b in ((rows[0], rows[2]), (rows[1], rows[3])):
        assert a.candidates.custody_manifest == b.candidates.custody_manifest
        assert a.candidates.status == b.candidates.status
    for a, b in ((rows[0], rows[1]), (rows[2], rows[3])):
        assert set(b.candidates.available) - set(a.candidates.available) == {audit.MORE}
        assert audit.MORE not in a.candidates.available


def test_match_and_mismatch_keep_separate_evidence(matrix):
    match = matrix[3 * 4]
    mismatch = matrix[5 * 4]
    p = json.loads(match.candidates.request.context[1].value_json)
    assert p["matched_scope"] == {"property": "entity_label", "supported_value": "zombie",
                                  "scope": "observed_target_only"}
    p = json.loads(mismatch.candidates.request.context[1].value_json)
    assert p["current_positive"][0]["label"] == "skeleton"
    assert p["matched_scope"] is None and p["review_status"] == "MISMATCH"
    assert mismatch.host_record["prediction"]["predicted_value"] == "zombie"
    assert mismatch.host_record["prediction"]["observed_value"] == "skeleton"
    assert "USE_MATCHED_FORECAST_SCOPE" not in mismatch.candidates.admissible


@pytest.mark.parametrize("attack", [
    "goal_swap", "cost_swap", "request_id", "request_digest", "custody",
    "foreign_identity", "source_digest", "extra_source_key", "false_absence",
    "memory_authority", "cost_candidate", "source_truth", "match_scope", "positive",
    "defer_bypass", "missing_cell", "duplicate_cell",
])
def test_mutated_factorial_fails_closed(matrix, attack):
    rows = list(deepcopy(matrix))
    # MATCH following, zero cost, EXPLAIN: READY, C/M/W.
    index = 12
    row = rows[index]
    r = row.candidates
    if attack == "goal_swap":
        row = replace(row, goal=gate.GoalSpec("ASSESS_FORECAST", 2, 0.0))
    elif attack == "cost_swap":
        row = replace(row, goal=gate.GoalSpec("EXPLAIN_OBSERVED", 2, 0.5))
    elif attack in ("request_id", "request_digest", "match_scope", "positive"):
        request = r.request
        if attack == "request_id":
            request = replace(request, request_id="foreign-request")
        elif attack in ("match_scope", "positive"):
            value = json.loads(request.context[1].value_json)
            if attack == "match_scope":
                value["matched_scope"]["property"] = "world_safety"
            else:
                value["current_positive"][0]["label"] = "invented"
            datum = replace(request.context[1], value_json=json.dumps(value))
            request = replace(request, context=(request.context[0], datum))
        r = replace(r, request=request,
                    request_sha256="0" * 64 if attack == "request_digest" else digest(asdict(request)))
    elif attack == "custody":
        r.custody_manifest["binding"]["self_id"] = "foreign"
    elif attack in ("foreign_identity", "source_digest", "extra_source_key", "false_absence",
                    "source_truth"):
        rec = row.host_record
        if attack == "foreign_identity":
            rec["binding"]["self_id"] = "foreign"
        elif attack == "source_digest":
            rec["observation"]["source_bound_digest"] = "0" * 64
        elif attack == "extra_source_key":
            rec["injected"] = True
        elif attack == "false_absence":
            rec["observation"]["world_absence_established"] = True
        else:
            rec["observation"]["selected_positive_observations"][0]["label"] = "invented"
    elif attack == "memory_authority":
        r = replace(r, memory_writes=1)
    elif attack == "cost_candidate":
        r = replace(r, available=(*r.available, audit.MORE))
    elif attack == "defer_bypass":
        index, row = 0, rows[0]
        r = replace(row.candidates, status="READY", request=r.request,
                    request_sha256=r.request_sha256)
    elif attack == "missing_cell":
        rows.pop()
    elif attack == "duplicate_cell":
        rows[-1] = rows[0]
    if attack not in ("missing_cell", "duplicate_cell"):
        rows[index] = replace(row, candidates=r)
    with pytest.raises(gate.EvidenceUseBlocked):
        audit.audit_factorial(rows)


@pytest.mark.parametrize("leak", ["self_id", "session_id", "epoch_id", "source_receipt_sha256",
                                  "source_request_id", "observation_digest", "provenance"])
def test_host_custody_leak_even_with_recomputed_request_digest(matrix, leak):
    rows = list(deepcopy(matrix))
    row = rows[12]
    record, request = row.host_record, row.candidates.request
    value = (record["binding"][leak] if leak in record["binding"] else {
        "source_request_id": record["observation"]["observation_source"]["request_id"],
        "observation_digest": record["observation"]["source_bound_digest"],
        "provenance": record["observation"]["observation_provenance"]["source"],
    }[leak])
    request = replace(request, instruction=request.instruction + " " + value)
    rows[12] = replace(row, candidates=replace(row.candidates, request=request,
                                              request_sha256=digest(asdict(request))))
    with pytest.raises(gate.EvidenceUseBlocked):
        audit.audit_factorial(rows)


@pytest.mark.parametrize("cost", [-0.1, float("nan"), float("inf"), True])
def test_invalid_cost_rejected_before_request(cost):
    with pytest.raises(gate.EvidenceUseBlocked):
        gate.GoalSpec("EXPLAIN_OBSERVED", 2, cost)


def test_missing_or_foreign_source_pin(sources, monkeypatch):
    monkeypatch.setattr(host.probe, "load_sources", lambda _: sources)
    with pytest.raises(gate.EvidenceUseBlocked):
        audit.collect_factorial(None, {})
    pins = {case.case_id: digest(asdict(replay)) for case, replay in sources}
    pins[sources[0][0].case_id] = "0" * 64
    with pytest.raises(ValueError):
        audit.collect_factorial(None, pins)


@pytest.mark.parametrize("swap", ["goal", "cost", "source"])
def test_selection_acceptance_reloads_and_rejects_swapped_binding(matrix, swap):
    # Acceptance validation is a protocol negative control, not cognitive judgment.
    row = matrix[12]
    kwargs = dict(source_root=None, case_id=row.case_id, epoch=row.epoch,
                  expected_source_digest=row.candidates.custody_manifest["source_digest"],
                  goal=row.goal, choice_id="USE_CURRENT_POSITIVE",
                  request_sha256=row.candidates.request_sha256)
    if swap == "goal":
        kwargs["goal"] = gate.GoalSpec("ASSESS_FORECAST", 2, 0.0)
    elif swap == "cost":
        kwargs["goal"] = gate.GoalSpec("EXPLAIN_OBSERVED", 2, 0.5)
    else:
        kwargs["expected_source_digest"] = "0" * 64
    with pytest.raises(ValueError):
        gate.validate_selected_strategy(row.candidates, **kwargs)
