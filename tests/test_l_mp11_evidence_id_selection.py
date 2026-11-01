"""Source-exact ID selection reduces Gemma numeric copying; NOT real Gemma."""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict

import pytest

from adapters.mineflayer.l_mp11_evidence_id_selection import (
    EvidenceIDRejected,
    evidence_catalog,
    model_evidence_catalog,
    resolve_evidence_ids,
)
from adapters.mineflayer.l_mp11_live_l2_shadow import (
    BoundedLiveL2,
    LiveL2Rejected,
    request_for_live_l2,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionMode, ProviderExpression, RelayEngine
from test_l_mp11_live_previous_action import accept, new_ledger


def ledger1():
    ledger = new_ledger()
    accept(ledger, 1)
    return ledger


def id_reply(req, *, mutate=None):
    n = len(json.loads(req.context[1].value_json))
    evidence = json.loads(req.context[3].value_json)
    ids = {x["evidence_id"] for x in evidence["indexed"]}
    result = {
        "referenced_prior_ordinals": list(range(1, n+1)),
        "reconsideration": "QUESTION_APPLICABILITY",
        "model_family": "PHASE_DEPENDENT",
        "next_test": "CHECK_PAPER_CALLBACK_PHASE",
        "explanation": "After-action movement may involve callback phase.",
        "falsification_test": "Compare fixed-phase Paper motion against next trial.",
        "predicted_wait_total_m": .16,
        "capability_assessment": "CONDITIONAL_HYPOTHESIS",
        "prior_hypothesis_relation": (
            "FIRST_HYPOTHESIS" if n == 1 else "REVISE_PRIOR"
        ),
        "evidence_ids": ["T1_W8"] if n == 1 else ["T2_H1ERR", "T2_W8"],
    }
    assert set(result["evidence_ids"]).issubset(ids)
    if mutate is not None:
        result = mutate(result)
    return result


def fixture(*, mutate=None):
    def provider(req, *, mode):
        assert mode is CognitionMode.OPEN
        return ProviderExpression(
            text=json.dumps(id_reply(req, mutate=mutate),
                            separators=(",", ":")),
            provenance=Provenance("fixture", "not-a-model"),
        )
    return RelayEngine(provider)


def test_catalog_is_only_completed_prior_paper_and_explicit_roles():
    ledger = ledger1()
    catalog = evidence_catalog(ledger)
    assert len(catalog) == 16
    assert catalog[0].evidence_id == "T1_W8"
    assert catalog[0].metric_role == "WAIT8_TOTAL_M"
    assert catalog[0].value_m == pytest.approx(.4)
    assert catalog[1].evidence_id == "T1_CMAE"
    assert catalog[1].pair_index == 0
    assert [x.evidence_id for x in catalog[2:6]] == [
        "T1_P1PRED", "T1_P1ERR", "T1_P2PRED", "T1_P2ERR",
    ]
    assert catalog[2].value_m == pytest.approx(.0325)
    assert catalog[3].value_m == pytest.approx(.0175)
    assert not any("T2" in x.evidence_id for x in catalog)
    request = request_for_live_l2(ledger, evidence_ids=True)
    assert json.loads(request.context[3].value_json) == model_evidence_catalog(ledger)
    assert "evidence_ids" in request.instruction
    assert "numeric_evidence_refs:" not in request.instruction
    assert request.context[0].provenance.source == "l.mp11.live.paper.provisional"


def test_two_valid_id_proposals_receive_authoritative_numbers_and_prior_sha():
    ledger = ledger1()
    gate = BoundedLiveL2(fixture(), require_real_llama=False, evidence_ids=True)
    first = asyncio.run(gate.propose_after(ledger))
    assert first.selected_evidence_ids == ("T1_W8",)
    assert first.numeric_evidence_refs == ({
        "metric_role": "WAIT8_TOTAL_M",
        "trial_ordinal": 1, "pair_index": 0, "value_m": pytest.approx(.4),
    },)
    assert first.provider_source == "fixture"
    assert not first.action_authority and not first.model_structure_admitted
    assert len(first.proposal_sha256) == 64
    accept(ledger, 2)
    second = asyncio.run(gate.propose_after(ledger))
    assert second.selected_evidence_ids == ("T2_H1ERR", "T2_W8")
    assert second.prior_proposal_sha256 == first.proposal_sha256
    assert second.numeric_evidence_refs[0]["metric_role"] == (
        "PRIOR_L2_NEXT_WAIT8_ABS_ERROR_M"
    )
    assert second.numeric_evidence_refs[0]["value_m"] == pytest.approx(.24)
    assert second.numeric_evidence_refs[1]["value_m"] == pytest.approx(.4)
    assert second.model_structure_admitted is False
    assert second.learning_admissions == second.l0_promotions == 0
    assert gate.public_report()["evidence_id_mode"] is True
    assert gate.public_report()["new_action_issuers"] == 0
    with pytest.raises(LiveL2Rejected):
        asyncio.run(gate.propose_after(ledger))


@pytest.mark.parametrize("selected", [
    [], ["T2_W8"], ["T1_W8", "T1_W8"], ["T1_W8", "T1_CMAE"],
    ["T1_W8", "T1_CMAE", "T1_P1PRED"], [1], ["T1_W8", "FOREIGN"],
])
def test_id_fail_closed_on_future_duplicate_unsorted_overbudget_or_foreign(selected):
    ledger = ledger1()
    with pytest.raises(EvidenceIDRejected):
        resolve_evidence_ids(ledger, selected)


@pytest.mark.parametrize("mode", [
    "numeric_copying", "extra_action", "future_reference", "wrong_prior",
    "different_id_order", "not_one_id", "fake_label",
])
def test_model_invalid_or_crosscontract_id_refusal(mode):
    ledger = ledger1()
    def mutate(reply):
        if mode == "numeric_copying":
            reply["numeric_evidence_refs"] = [{
                "metric_role": "WAIT8_TOTAL_M", "trial_ordinal": 1,
                "pair_index": 0, "value_m": .4,
            }]
        elif mode == "extra_action":
            reply["run_command"] = "tp RelaySelf ~ 2 ~"
        elif mode == "future_reference":
            reply["evidence_ids"] = ["T2_W8"]
        elif mode == "wrong_prior":
            reply["prior_hypothesis_relation"] = "REVISE_PRIOR"
        elif mode == "different_id_order":
            reply["evidence_ids"] = ["T1_W8", "T1_CMAE"]
        elif mode == "not_one_id":
            reply["evidence_ids"] = ["T1_W8", "T1_P1ERR"]
        elif mode == "fake_label":
            reply["evidence_ids"] = ["T1_FAKE"]
        return reply
    gate = BoundedLiveL2(
        fixture(mutate=mutate), require_real_llama=False, evidence_ids=True,
    )
    with pytest.raises(LiveL2Rejected):
        asyncio.run(gate.propose_after(ledger))
    assert gate.failed_closed and len(gate.proposals) == 0


def test_id_catalog_cannot_retroactively_qualify_old_model_json():
    ledger = ledger1()
    req = request_for_live_l2(ledger, evidence_ids=False)
    assert "numeric_evidence_refs" in req.instruction
    assert "evidence_ids (ONE" not in req.instruction
    model_id_reply = id_reply(request_for_live_l2(ledger, evidence_ids=True))
    def wrong_mode_provider(req, *, mode):
        assert mode is CognitionMode.OPEN
        return ProviderExpression(
            text=json.dumps(model_id_reply),
            provenance=Provenance("fixture", "wrong-mode-id-output"),
        )
    normal = BoundedLiveL2(
        RelayEngine(wrong_mode_provider), require_real_llama=False,
    )
    assert normal.public_report()["evidence_id_mode"] is False
    with pytest.raises(LiveL2Rejected):
        asyncio.run(normal.propose_after(ledger))
    assert normal.failed_closed


def test_host_does_not_fabricate_missing_second_hypothesis():
    ledger = ledger1()
    with pytest.raises(EvidenceIDRejected):
        evidence_catalog(ledger, previous=object())
    with pytest.raises(EvidenceIDRejected):
        model_evidence_catalog(ledger, previous=object())
    assert "T2_W8" not in [x.evidence_id for x in evidence_catalog(ledger)]


def test_result_is_source_typed_not_model_generated_number():
    ledger = ledger1()
    ids, values = resolve_evidence_ids(ledger, ["T1_P1ERR"])
    assert ids == ("T1_P1ERR",)
    assert asdict(values[0]) == {
        "metric_role": "PAPER_NEXT_TICK_ABS_ERROR_M",
        "trial_ordinal": 1,
        "pair_index": 1,
        "value_m": pytest.approx(.0175),
    }
