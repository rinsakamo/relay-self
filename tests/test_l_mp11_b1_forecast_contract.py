"""B1 V2: honest forecast abstention and source-bound self-evaluation (FAKE LLM)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from adapters.mineflayer.l_mp11_b1_forecast_contract import (
    TARGET,
    historical_v1_b1_readback,
    schema_v2_additions,
    validate_b1_v2,
)
from adapters.mineflayer.l_mp11_gemma_wire_contract import (
    GemmaWireRejected,
    pin_gemma_wire,
)
from adapters.mineflayer.l_mp11_live_l2_shadow import (
    BoundedLiveL2,
    LiveL2ProposalV2,
    LiveL2Rejected,
    request_for_live_l2,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionMode, ProviderExpression, RelayEngine
from test_l_mp11_evidence_id_selection import id_reply
from test_l_mp11_live_previous_action import accept, new_ledger
from tools.l_mp11_gemma_structured_preflight import synthetic_test_body


def v2_reply(req, *, abstain=False, bad=None):
    n = len(json.loads(req.context[1].value_json))
    answer = id_reply(req) if n == 1 else {
        "referenced_prior_ordinals": [1, 2],
        "reconsideration": "QUESTION_APPLICABILITY",
        "model_family": "PHASE_DEPENDENT",
        "next_test": "CHECK_PAPER_CALLBACK_PHASE",
        "explanation": "Original total displacement in meters was observed.",
        "falsification_test": "Compare a later independent physical movement.",
        "predicted_wait_total_m": None,
        "capability_assessment": "CONDITIONAL_HYPOTHESIS",
        "prior_hypothesis_relation": "ABSTAIN_ON_PRIOR",
        "evidence_ids": ["T1_W8", "T2_W8"],
    }
    answer.update({
        "measurement_target": TARGET,
        "forecast_status": (
            "ABSTAIN_INSUFFICIENT_EVIDENCE" if abstain else "NUMERIC_ESTIMATE"
        ),
        "prior_evaluation_basis": (
            "FIRST_UNTESTED" if n == 1
            else "NO_SCORABLE_FORECAST" if abstain else "SCORED_ERROR"
        ),
        "prior_evaluation_reason": (
            "First trial: forecast has not been checked against another trial."
            if n == 1 else
            "No numeric H1 forecast to score; the new displacement is observed only."
            if abstain else
            "The absolute difference is read from H1 error and Action2 displacement."
        ),
        "explanation": "Observed WAIT8 total displacement is expressed in meters.",
        "falsification_test": "Compare the following physical trial under same conditions.",
        "prior_hypothesis_relation": (
            "FIRST_HYPOTHESIS" if n == 1 else
            "ABSTAIN_ON_PRIOR" if abstain else "REVISE_PRIOR"
        ),
        "predicted_wait_total_m": None if abstain else 0.16,
        "evidence_ids": (
            ["T1_W8"] if n == 1 else
            ["T1_W8", "T2_W8"] if abstain
            else ["T2_H1ERR", "T2_W8"]
        ),
    })
    if bad is not None:
        answer = bad(answer, n)
    return answer


def v2_engine(*, abstain=False, bad=None):
    def provider(req, *, mode):
        assert mode is CognitionMode.OPEN
        return ProviderExpression(
            text=json.dumps(v2_reply(req, abstain=abstain, bad=bad)),
            provenance=Provenance("fixture", "synthetic-offline-not-actual-Gemma"),
        )
    return RelayEngine(provider)


def first():
    ledger = new_ledger()
    accept(ledger, 1)
    return ledger


def test_native_v2_schema_exact_14_keys_and_legacy_still_ten():
    body = synthetic_test_body("gemma", b1_contract_v2=True)
    wire = pin_gemma_wire(body, evidence_ids=True, b1_contract_v2=True)
    schema = wire["response_format"]["json_schema"]
    assert schema["name"] == "relay_l2_b1_explicit_forecast_v2"
    assert schema["strict"] is True
    assert len(schema["schema"]["required"]) == 14
    assert schema["schema"]["additionalProperties"] is False
    assert schema["schema"]["properties"]["measurement_target"]["enum"] == [TARGET]
    assert schema["schema"]["properties"]["forecast_status"]["enum"] == [
        "NUMERIC_ESTIMATE", "ABSTAIN_INSUFFICIENT_EVIDENCE",
        "ABSTAIN_OUTSIDE_APPLICABILITY", "ABSTAIN_MODEL_UNRESOLVED",
    ]
    assert set(schema_v2_additions()).issubset(schema["schema"]["properties"])
    legacy = pin_gemma_wire(
        synthetic_test_body("gemma"), evidence_ids=True,
    )
    assert len(legacy["response_format"]["json_schema"]["schema"]["required"]) == 10
    with pytest.raises(GemmaWireRejected):
        pin_gemma_wire(synthetic_test_body("gemma"),
                       evidence_ids=False, b1_contract_v2=True)


def test_v2_numeric_realistic_two_opens_freeze_h1_before_h2():
    ledger = first()
    gate = BoundedLiveL2(
        v2_engine(), require_real_llama=False,
        evidence_ids=True, b1_contract_v2=True,
    )
    first_result = asyncio.run(gate.propose_after(ledger))
    assert isinstance(first_result, LiveL2ProposalV2)
    assert first_result.forecast_status == "NUMERIC_ESTIMATE"
    assert first_result.measurement_target == TARGET
    assert not first_result.numeric_prior_forecast_scored
    accept(ledger, 2)
    second = asyncio.run(gate.propose_after(ledger))
    assert second.prior_proposal_sha256 == first_result.proposal_sha256
    assert second.numeric_prior_forecast_scored
    assert not second.cannot_score_forecast
    assert second.prior_evaluation_basis == "SCORED_ERROR"
    assert second.selected_evidence_ids == ("T2_H1ERR", "T2_W8")
    assert second.prior_hypothesis_relation == "REVISE_PRIOR"
    assert second.learning_admissions == second.l0_promotions == 0
    assert gate.public_report()["b1_contract_v2_mode"] is True
    assert gate.public_report()["new_action_issuers"] == 0


def test_v2_valid_h1_abstention_never_fabricates_error():
    ledger = first()
    gate = BoundedLiveL2(
        v2_engine(abstain=True), require_real_llama=False,
        evidence_ids=True, b1_contract_v2=True,
    )
    h1 = asyncio.run(gate.propose_after(ledger))
    assert h1.predicted_wait_total_m is None
    assert h1.forecast_status == "ABSTAIN_INSUFFICIENT_EVIDENCE"
    accept(ledger, 2)
    h2 = asyncio.run(gate.propose_after(ledger))
    assert h2.prior_hypothesis_relation == "ABSTAIN_ON_PRIOR"
    assert h2.prior_evaluation_basis == "NO_SCORABLE_FORECAST"
    assert h2.cannot_score_forecast
    assert not h2.numeric_prior_forecast_scored
    assert h2.selected_evidence_ids == ("T1_W8", "T2_W8")


@pytest.mark.parametrize("reason", [
    "wait times", "elapsed time", "time elapsed",
])
def test_displacement_unit_is_not_a_duration(reason):
    ledger = first()
    def wrong(p, n):
        p["explanation"] = f"Measured {reason} differs in the grass environment."
        return p
    gate = BoundedLiveL2(
        v2_engine(bad=wrong), require_real_llama=False,
        evidence_ids=True, b1_contract_v2=True,
    )
    with pytest.raises(LiveL2Rejected, match="typed"):
        asyncio.run(gate.propose_after(ledger))
    assert gate.failed_closed


@pytest.mark.parametrize("bad", [
    lambda p, n: p.update(forecast_status="NUMERIC_ESTIMATE", predicted_wait_total_m=None),
    lambda p, n: p.update(forecast_status="ABSTAIN_MODEL_UNRESOLVED", predicted_wait_total_m=0.2),
    lambda p, n: p.update(measurement_target="WAIT8_TOTAL_SECONDS"),
    lambda p, n: p.update(prior_evaluation_basis="SCORED_ERROR"),
    lambda p, n: p.update(prior_evaluation_reason="Short"),
    lambda p, n: p.update(command="tp player 0 0 0"),
])
def test_b1_v2_first_response_rejects_inconsistent_forecast_abstention(bad):
    ledger = first()
    def wrong(p, n):
        bad(p, n)
        return p
    gate = BoundedLiveL2(
        v2_engine(bad=wrong), require_real_llama=False,
        evidence_ids=True, b1_contract_v2=True,
    )
    with pytest.raises(LiveL2Rejected):
        asyncio.run(gate.propose_after(ledger))
    assert gate.failed_closed


@pytest.mark.parametrize("case", [
    "fake_score", "unscored_keep", "fake_prediction_error",
    "missing_qualitative_sources", "fake_h1_error_source",
])
def test_prior_null_cannot_be_stated_as_scored_h1_error(case):
    ledger = first()
    gate = BoundedLiveL2(
        v2_engine(abstain=True), require_real_llama=False,
        evidence_ids=True, b1_contract_v2=True,
    )
    asyncio.run(gate.propose_after(ledger))
    accept(ledger, 2)
    def wrong(p, n):
        if n != 2:
            return p
        if case == "fake_score":
            p["prior_evaluation_basis"] = "SCORED_ERROR"
        elif case == "unscored_keep":
            p["prior_hypothesis_relation"] = "KEEP_PRIOR"
        elif case == "fake_prediction_error":
            p["explanation"] = "Predicted and actual displacement differ in this trial."
        elif case == "missing_qualitative_sources":
            p["prior_evaluation_basis"] = "QUALITATIVE_ONLY"
            p["evidence_ids"] = ["T2_W8"]
        elif case == "fake_h1_error_source":
            p["evidence_ids"] = ["T1_W8", "T2_H1ERR"]
        return p
    # No second H2 can be newly requested if it wasn't in original source:
    gate.engine = v2_engine(abstain=True, bad=wrong)
    with pytest.raises(LiveL2Rejected):
        asyncio.run(gate.propose_after(ledger))


def test_explicit_qualitative_keep_without_forecast_is_not_scored_B1():
    result = {
        "measurement_target": TARGET,
        "forecast_status": "ABSTAIN_MODEL_UNRESOLVED",
        "prior_evaluation_basis": "QUALITATIVE_ONLY",
        "prior_evaluation_reason": (
            "Both completed trials show nearly the same total movement in meters; "
            "there was no prior numeric prediction."
        ),
        "prior_hypothesis_relation": "KEEP_PRIOR",
        "predicted_wait_total_m": None,
        "explanation": "Two observed WAIT8 displacements are approximately equal.",
    }
    tagged = validate_b1_v2(
        result, trial_count=2, previous_prediction_m=None,
        selected_ids=("T1_W8", "T2_W8"),
    )
    assert tagged.qualitative_only
    assert tagged.cannot_score_forecast
    assert not tagged.numeric_prior_forecast_scored


def test_v2_does_not_reinterpret_original_686_hypotheses_or_world(tmp_path):
    root = Path("docs/evidence/l-cognitive-loop-20261102/world")
    h1 = json.loads((root / "l2-frozen-1.json").read_text())
    h2 = json.loads((root / "l2-frozen-2.json").read_text())
    old = historical_v1_b1_readback(h1["proposal"], h2["proposal"])
    assert old["classification"] == "HISTORICAL_V1_UNSCORABLE_NOT_B1"
    assert old["h1_numeric_prediction"] is None
    assert old["numeric_forecast_error"] is None
    assert old["h2_relation_v1"] == "KEEP_PRIOR"
    assert old["h2_selected_ids_v1"] == ("T1_W8", "T2_W8")
    assert old["h1_to_h2_sha_verified"]
    assert not old["world_result_changed"]
    assert not old["can_establish_B1_numeric_self_evaluation"]
    assert "measurement_target" not in h1["proposal"]
    assert "forecast_status" not in h2["attempt"]["result"]["text"]
    # Presence of real source artifacts here never becomes new model inference.
    assert not list(tmp_path.iterdir())


def test_legacy_and_v2_requests_cannot_cross_versions():
    ledger = first()
    req_v2 = request_for_live_l2(
        ledger, evidence_ids=True, b1_contract_v2=True,
    )
    req_v1 = request_for_live_l2(ledger, evidence_ids=True)
    assert req_v2 != req_v1
    assert "WAIT8_TOTAL_M" in req_v2.instruction
    assert "wait duration" in req_v2.instruction
    assert "B1 read-only prediction contract V2" not in req_v1.instruction
    with pytest.raises(LiveL2Rejected):
        request_for_live_l2(ledger, evidence_ids=False, b1_contract_v2=True)



def test_v2_strict_synthetic_preflight_only_accepts_matching_v2_raw(tmp_path, monkeypatch):
    """A previously successful v1 probe cannot unlock the new v2 World."""
    import io
    import urllib.request

    from test_l_mp11_gemma_wire_contract import result
    from tools.l_mp11_gemma_structured_preflight import (
        GemmaPreflightRejected,
        run,
        verify_preflight_report,
    )

    body = result()
    message = body["choices"][0]["message"]
    response = json.loads(message["content"])
    response.update({
        "measurement_target": TARGET,
        "forecast_status": "NUMERIC_ESTIMATE",
        "prior_evaluation_basis": "FIRST_UNTESTED",
        "prior_evaluation_reason": (
            "Synthetic first trial cannot yet score a forecast against another trial."
        ),
    })
    message["content"] = json.dumps(response, separators=(",", ":"))
    monkeypatch.setattr(
        urllib.request, "urlopen",
        lambda *a, **kwargs: io.BytesIO(json.dumps(body).encode("utf-8")),
    )
    endpoint = "http://127.0.0.1:8080/v1/chat/completions"
    root = tmp_path / "probe"
    receipt = run(endpoint, "fixture-alias", root, b1_contract_v2=True)
    assert receipt["b1_contract_v2"] is True
    report_path = root / "gemma-structured-preflight.json"
    verified = verify_preflight_report(
        report_path, endpoint=endpoint, model="fixture-alias",
        b1_contract_v2=True,
    )
    assert verified == receipt
    with pytest.raises(GemmaPreflightRejected):
        verify_preflight_report(report_path, endpoint=endpoint, model="fixture-alias")
    raw = json.loads((root / "llama-request-1.raw.json").read_text())
    assert len(raw["response_format"]["json_schema"]["schema"]["required"]) == 14
    assert raw["chat_template_kwargs"] == {"enable_thinking": False}


def test_independent_feedback_reconstructs_v2_two_proposals_from_original():
    from test_l_mp11_live_previous_action import ACTIONS, MARKERS, snapshot
    from tools.l_mp11_feedback_original_audit import audit_feedback_originals

    ledger = new_ledger()
    gate = BoundedLiveL2(
        v2_engine(), require_real_llama=False,
        evidence_ids=True, b1_contract_v2=True,
    )
    # The independent auditor requires real provider labeling for a
    # parser-path fixture, but that label is NOT proof of genuine model weights.
    def labeled_provider(req, *, mode):
        assert mode is CognitionMode.OPEN
        return ProviderExpression(
            text=json.dumps(v2_reply(req)),
            provenance=Provenance("llama.cpp", "synthetic-not-actual-weights"),
        )
    gate.engine = RelayEngine(labeled_provider)
    windows = []
    for i in (1, 2):
        receipt = accept(ledger, i)
        asyncio.run(gate.propose_after(ledger))
        windows.append({"paper_prefix_length": receipt.paper_prefix_length})
    report = {
        "session_id": ledger.session_id,
        "mp11_g3": {
            "paper_world_uuid": ledger.world_uuid,
            "subject_uuid": ledger.subject_uuid,
            "paper_markers": MARKERS,
        },
        "mp11_g2": {"typed_s16_actions": [
            {"action_id": action, "native_seq": i * 25}
            for i, action in enumerate(ACTIONS, 1)
        ]},
        "l_mp11_live_prefix": {"observations": windows},
        "l_mp11_live_l2": gate.public_report(),
    }
    raw = snapshot(3)
    audited = audit_feedback_originals(report, raw)
    assert audited["b1_v2_typed_evaluation_reconstructed"] is True
    assert audited["h1_to_feedback_to_h2_sha_verified"] is True
    assert audited["causal_interpretation_attested"] is False
    report["l_mp11_live_l2"]["proposals"][1]["prior_evaluation_basis"] = (
        "QUALITATIVE_ONLY"
    )
    with pytest.raises(ValueError):
        audit_feedback_originals(report, raw)
