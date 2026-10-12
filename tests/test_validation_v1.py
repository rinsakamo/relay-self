"""V1 negative controls: no offline synthetic success promoted to physical/science."""
from __future__ import annotations

import json

import pytest

from experiments.validation import v1


def case(**changes):
    a = {
        "source_sha256": "a" * 64, "cheap_source_sha256": "a" * 64,
        "source_session": "s", "cheap_source_session": "s",
        "candidate_actions": ["WAIT", "MOVE"], "cheap_actions": ["MOVE", "WAIT"],
        "oracle_leakage": False, "stale_l2_as_action": False,
        "unknown_as_success": False, "heldout_lineage_disjoint": True,
        "cheap_baseline_run": True, "goal_receipts_verified": True,
        "world_outcome_delta": 1.0, "resource_adjusted_delta": 0.5,
        "costs_measured": True, "independent_reuse": True,
    }
    a.update(changes)
    return a


def test_ledger_cannot_promote_report_to_verified():
    ledger = v1.inventory()
    assert len(ledger["claims"]) >= 10
    assert all(row["evidence_origin"] != "LOCAL_SOURCE_VERIFIED"
               for row in ledger["claims"])
    assert all(row["status"] != "SCIENTIFIC_ADVANTAGE" for row in ledger["claims"])
    assert ledger["golden"]["raw_original_verification"] == "NOT_RUN"


@pytest.mark.parametrize("mutation", [
    {"status": "LOCAL_SOURCE_VERIFIED"},
    {"evidence_origin": "LOCAL_SOURCE_VERIFIED"},
    {"source_head": "invalid"},
    {"receipt_sha256": "0" * 32},
    {"status": "PHYSICAL_REPORTED", "evidence_origin": "GITHUB_CI_REPORT"},
])
def test_forged_inventory_provenance_fails(tmp_path, mutation):
    obj = v1.inventory()
    obj["claims"][0].update(mutation)
    candidate = tmp_path / "bad.json"
    candidate.write_text(json.dumps(obj), encoding="utf-8")
    with pytest.raises(v1.V1Rejected):
        v1.inventory(candidate)


def test_reused_claim_identity_fails(tmp_path):
    obj = v1.inventory()
    obj["claims"][1]["id"] = obj["claims"][0]["id"]
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(obj))
    with pytest.raises(v1.V1Rejected, match="duplicate"):
        v1.inventory(path)


def test_remote_golden_is_only_report_and_no_new_actions():
    info = v1.golden_audit()
    assert info["report_class"] == "GITHUB_REPORTED_ONLY"
    assert info["original_bytes"] == "NOT_RUN"
    assert info["native_projection"] == "NOT_RUN"
    assert info["goal_success"] == "UNDETERMINED"
    assert info["stop_ack"] == "UNDETERMINED"
    assert info["new_model_calls"] == info["new_physical_actions"] == 0


def test_missing_or_tampered_originals_fail_before_source_projection(tmp_path, monkeypatch):
    source = tmp_path / "golden"
    source.mkdir()
    called = []
    monkeypatch.setattr(v1.r1, "plan", lambda *_args: called.append("plan"))
    with pytest.raises(v1.r1.SharedRuntimeRejected):
        v1.golden_audit(source)
    assert not called
    for name in v1.GOLDEN_SHA:
        (source / name).write_bytes(b"forged-but-plausible")
    with pytest.raises(v1.V1Rejected, match="SHA256 mismatch"):
        v1.golden_audit(source)
    assert not called


def test_symlinked_receipt_never_trusted(tmp_path):
    source = tmp_path / "golden"
    source.mkdir()
    real = tmp_path / "outside"
    real.write_bytes(b"immutable?")
    (source / "native_report.json").symlink_to(real)
    with pytest.raises(v1.r1.SharedRuntimeRejected):
        v1.golden_audit(source)


@pytest.mark.parametrize("poison", [
    {"source_sha256": "b" * 64},
    {"cheap_source_session": "foreign"},
    {"candidate_actions": ["WAIT"]},
    {"oracle_leakage": True},
    {"stale_l2_as_action": True},
    {"unknown_as_success": True},
])
def test_provenance_leakage_stale_authority_fail_closed(poison):
    result = v1.admission(case(**poison))
    assert result["gates"]["G0"] == "NO_GO_SOURCE_OR_AUTHORITY"
    assert result["classification"] == "NO_GO"
    assert result["science_qualified"] is False
    assert result["physical_execution_authorized"] is False


def test_unknown_goal_and_absent_cheap_control_never_positive():
    result = v1.admission(case(goal_receipts_verified=False, cheap_baseline_run=False))
    assert result["gates"]["G3"] == "UNDETERMINED"
    assert result["gates"]["G4"] == "UNDETERMINED"
    assert result["classification"].startswith("UNDETERMINED")


@pytest.mark.parametrize("delta", [0, -1])
def test_matched_cheap_control_equal_or_better_denies_advantage(delta):
    r = v1.admission(case(world_outcome_delta=delta))
    assert r["gates"]["G3"] == "NO_GO_NO_INCREMENTAL_GOAL_GAIN"
    assert r["classification"] == "NO_GO"


def test_resource_cost_can_reverse_world_gain():
    r = v1.admission(case(world_outcome_delta=2, resource_adjusted_delta=-0.1))
    assert r["gates"]["G3"] == "REVIEW_WITNESSES_REQUIRED"
    assert r["gates"]["G4"] == "NO_GO_NO_RESOURCE_GAIN"
    assert r["classification"] == "NO_GO"


def test_positive_declared_fields_never_self_qualify_science():
    r = v1.admission(case())
    assert r["gates"]["G5"] == "REVIEW_INDEPENDENT_LINEAGES_REQUIRED"
    assert r["science_qualified"] is False
    assert r["classification"] == "UNDETERMINED_INDEPENDENT_REVIEW_REQUIRED"


def test_malformed_oracle_and_nan_deltas_rejected():
    for candidate in (
        case(oracle_leakage="false"), case(world_outcome_delta=float("nan")),
        case(resource_adjusted_delta=float("inf")), case(candidate_actions=["WAIT", "WAIT"]),
        {**case(), "secret_evaluator_truth": "winning_action"},
    ):
        with pytest.raises(v1.V1Rejected):
            v1.admission(candidate)


def test_cli_default_non_generating(capsys):
    assert v1.main([]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["science_g3"] == "NO_GO"
    assert result["self1_product"] == "UNDETERMINED"
    assert result["golden_audit"]["original_bytes"] == "NOT_RUN"
    assert result["new_model_calls"] == result["new_physical_actions"] == 0


def test_cli_forged_case_rejected(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"oracle_truth": 1}))
    assert v1.main(["--comparison-json", str(path)]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["classification"] == "V1_EVIDENCE_BLOCKED"
    assert result["physical_execution_authorized"] is False
