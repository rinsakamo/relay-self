"""Bounded L2 OPEN shadow test, no real model or World required."""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import replace

import pytest

from adapters.mineflayer.l_mp11_live_l2_shadow import (
    BoundedLiveL2,
    LiveL2Rejected,
    parse_live_l2,
    request_for_live_l2,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    ProviderExpression,
    RelayEngine,
)
from test_l_mp11_live_previous_action import accept, new_ledger


def output(req, *, change=None):
    prior = json.loads(req.context[1].value_json)
    n = len(prior)
    p = {
        "referenced_prior_ordinals": list(range(1, n + 1)),
        "reconsideration": "QUESTION_APPLICABILITY",
        "model_family": "PHASE_DEPENDENT",
        "next_test": "CHECK_PAPER_CALLBACK_PHASE",
        "explanation": "Observed after-action drift may depend on the input-clear phase.",
        "falsification_test": "Measure actual clear transition ticks before next independently scored trial.",
        "predicted_wait_total_m": 0.16,
        "capability_assessment": "CONDITIONAL_HYPOTHESIS",
        "prior_hypothesis_relation": (
            "FIRST_HYPOTHESIS" if n == 1 else "REVISE_PRIOR"
        ),
        "numeric_evidence_refs": [
            {"metric_role": "WAIT8_TOTAL_M", "trial_ordinal": n,
             "pair_index": 0, "value_m": prior[-1]["paper_wait_total_m"]},
        ] + ([
            {"metric_role": "PRIOR_L2_NEXT_WAIT8_ABS_ERROR_M",
             "trial_ordinal": 2, "pair_index": 0, "value_m": .24},
        ] if n == 2 else []),
    }
    if change:
        p = change(p)
    return p


def fixture_engine(*, source="fake.fixture", changes=None, seen=None):
    def provider(req, *, mode):
        assert mode is CognitionMode.OPEN
        if seen is not None:
            seen.append(req)
        value = output(req, change=changes)
        return ProviderExpression(
            text=json.dumps(value),
            provenance=Provenance(source, "fake-never-model-weights"),
        )
    return RelayEngine(provider)


def one():
    ledger = new_ledger()
    accept(ledger, 1)
    return ledger


def test_model_facing_request_has_only_completed_original_action():
    ledger = one()
    req = request_for_live_l2(ledger)
    history = json.loads(req.context[1].value_json)
    assert len(history) == 1
    assert history[0]["action_id"] == "s49-native-move-11"
    assert "s49-native-move-18" not in req.context[1].value_json
    assert "SINGLE_DECAY" in req.instruction
    assert "UNAPPROVED" in req.instruction
    assert req.context[0].provenance.source == "l.mp11.live.paper.provisional"


def test_two_sequential_open_calls_are_proposals_not_executed_actions():
    seen = []
    ledger = one()
    gate = BoundedLiveL2(
        fixture_engine(source="fake.fixture", seen=seen),
        require_real_llama=False,
    )
    first = asyncio.run(gate.propose_after(ledger))
    assert first.source_prior_count == 1
    assert first.referenced_prior_ordinals == (1,)
    assert first.provider_source == "fake.fixture"
    assert first.next_test == "CHECK_PAPER_CALLBACK_PHASE"
    assert first.capability_assessment == "CONDITIONAL_HYPOTHESIS"
    assert not first.next_test_owner_approved
    assert not first.action_authority and not first.model_structure_admitted
    assert first.learning_admissions == first.l0_promotions == 0
    with pytest.raises(LiveL2Rejected):
        asyncio.run(gate.propose_after(ledger))
    accept(ledger, 2)
    second = asyncio.run(gate.propose_after(ledger))
    assert second.source_prior_count == 2
    assert second.referenced_prior_ordinals == (1, 2)
    assert second.proposal_sha256 != first.proposal_sha256
    assert len(seen) == 2
    assert len(json.loads(seen[0].context[1].value_json)) == 1
    assert len(json.loads(seen[1].context[1].value_json)) == 2
    assert gate.public_report()["experiments_selected_and_executed_by_l2"] == 0
    with pytest.raises(LiveL2Rejected):
        asyncio.run(gate.propose_after(ledger))


def test_fake_provider_source_never_counts_as_real_llama():
    gate = BoundedLiveL2(fixture_engine())
    with pytest.raises(LiveL2Rejected, match="exact scoped"):
        asyncio.run(gate.propose_after(one()))
    assert gate.failed_closed
    assert gate.public_report()["validated_open_calls"] == 0


def test_even_llama_labeled_fixture_has_no_model_identity_attestation():
    gate = BoundedLiveL2(fixture_engine(source="llama.cpp"))
    hypothesis = asyncio.run(gate.propose_after(one()))
    assert hypothesis.provider_source == "llama.cpp"
    assert not hypothesis.action_authority
    assert gate.public_report()["provider_label_is_not_model_weights_attestation"]


@pytest.mark.parametrize("case", [
    "future", "duplicate", "unsorted", "non_integer",
    "command", "unknown_test", "unknown_family", "promote",
    "impossible", "nan", "negative", "too_long", "empty_refs_revision",
])
def test_fail_closed_on_unbounded_or_unobserved_claims(case):
    changes = {
        "future": lambda p: p | {"referenced_prior_ordinals": [2]},
        "duplicate": lambda p: p | {"referenced_prior_ordinals": [1, 1]},
        "unsorted": lambda p: p | {"referenced_prior_ordinals": [2, 1]},
        "non_integer": lambda p: p | {"referenced_prior_ordinals": [True]},
        "command": lambda p: p | {"run_command": "tp RelaySelf 0 0 0"},
        "unknown_test": lambda p: p | {"next_test": "EXEC_WORLD"},
        "unknown_family": lambda p: p | {"model_family": "MAGIC"},
        "promote": lambda p: p | {"reconsideration": "AUTO_PROMOTE_L0"},
        "impossible": lambda p: p | {"capability_assessment": "PERMANENTLY_IMPOSSIBLE"},
        "nan": lambda p: p | {"predicted_wait_total_m": float("nan")},
        "negative": lambda p: p | {"predicted_wait_total_m": -1},
        "too_long": lambda p: p | {"explanation": "x" * 1000},
        "empty_refs_revision": lambda p: p | {"referenced_prior_ordinals": []},
    }
    gate = BoundedLiveL2(fixture_engine(changes=changes[case]), require_real_llama=False)
    with pytest.raises(LiveL2Rejected):
        asyncio.run(gate.propose_after(one()))
    assert gate.failed_closed and gate.public_report()["validated_open_calls"] == 0


def test_wrong_request_id_or_output_type_never_admitted():
    from relay_self.relay_engine import OpenCognitionResult
    ledger = one()
    req = request_for_live_l2(ledger)
    obj = OpenCognitionResult(
        request_id=req.request_id, text=json.dumps(output(req)),
        provenance=Provenance("llama.cpp", "source-label-not-weight-proof"),
    )
    with pytest.raises(LiveL2Rejected):
        parse_live_l2(ledger, replace(req, instruction="foreign"), obj,
                      require_real_llama=True)
    with pytest.raises(LiveL2Rejected):
        parse_live_l2(ledger, req, replace(obj, request_id="wrong"),
                      require_real_llama=True)
    with pytest.raises(LiveL2Rejected):
        parse_live_l2(ledger, req, object(), require_real_llama=True)


def test_zero_prior_and_unfinished_third_are_not_allowed():
    ledger = new_ledger()
    with pytest.raises(LiveL2Rejected):
        request_for_live_l2(ledger)
    accept(ledger, 1)
    accept(ledger, 2)
    accept(ledger, 3)
    with pytest.raises(LiveL2Rejected):
        request_for_live_l2(ledger)


def test_invalid_call_budget_rejected():
    engine = fixture_engine()
    with pytest.raises(LiveL2Rejected):
        BoundedLiveL2(engine, timeout_s=-1)
    with pytest.raises(LiveL2Rejected):
        BoundedLiveL2(engine, timeout_s=60)
    with pytest.raises(LiveL2Rejected):
        BoundedLiveL2(engine, timeout_s=True)


def test_timeout_preserves_attempt_and_never_releases_next_query():
    def provider(req, *, mode):
        time.sleep(.03)
        return ProviderExpression(text=json.dumps(output(req)),
                                  provenance=Provenance("fake.fixture", "late"))
    gate = BoundedLiveL2(RelayEngine(provider), require_real_llama=False,
                         timeout_s=.001)
    with pytest.raises(TimeoutError):
        asyncio.run(gate.propose_after(one()))
    assert gate.failed_closed and len(gate.attempts) == 1
    assert "TimeoutError" in gate.attempts[0]["error"]
    assert not gate.proposals
    with pytest.raises(LiveL2Rejected):
        asyncio.run(gate.propose_after(one()))


def test_invalid_json_original_remains_in_failed_attempt():
    def provider(req, *, mode):
        return ProviderExpression(text="{invalid-original",
                                  provenance=Provenance("fake.fixture", "original"))
    gate = BoundedLiveL2(RelayEngine(provider), require_real_llama=False)
    with pytest.raises(LiveL2Rejected):
        asyncio.run(gate.propose_after(one()))
    assert gate.public_report()["attempt_originals"][0]["result"]["text"] == "{invalid-original"


def test_live_request_contains_original_prediction_error_not_future():
    ledger = one()
    history = json.loads(request_for_live_l2(ledger).context[1].value_json)
    assert len(history) == 1
    assert history[0]["paper_predicted_next_m"] == [.0325] * 7
    assert history[0]["paper_next_abs_error_m"] == [.0175] * 7
    assert history[0]["paper_cheap_zero_next_mae_m"] == pytest.approx(.05)


def test_real_provider_journals_http_response_and_explicit_budget(tmp_path, monkeypatch):
    from adapters.mineflayer.l_mp11_live_l2_shadow import JournaledLiveLlamaProvider
    response = {"id": "fake-http-id", "model": "fake-model", "choices": []}
    import io
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda *a, **k: io.BytesIO(json.dumps(response).encode()))
    provider = JournaledLiveLlamaProvider(
        journal_root=tmp_path, endpoint="http://127.0.0.1:8080/v1/chat/completions",
        model="fake-model",
    )
    body = {"max_tokens": 256}
    assert provider._call(body) == response
    saved = json.loads((tmp_path / "llama-http-1.json").read_text())
    assert saved["request"]["max_tokens"] == body["max_tokens"] == 512
    assert saved["response"] == response
    assert saved["finished_monotonic_ns"] >= saved["started_monotonic_ns"]


def test_second_open_has_previous_proposal_sha_and_scored_next_wait8_target():
    ledger = new_ledger()
    accept(ledger, 1)
    gate = BoundedLiveL2(fixture_engine(), require_real_llama=False)
    prior = asyncio.run(gate.propose_after(ledger))
    accept(ledger, 2)
    with pytest.raises(LiveL2Rejected):
        request_for_live_l2(ledger)  # second call MUST be tied to prior L2
    req = request_for_live_l2(ledger, previous_proposal=prior)
    history = json.loads(req.context[1].value_json)
    previous = json.loads(req.context[2].value_json)
    assert len(history) == 2
    assert previous["previous_proposal_sha256"] == prior.proposal_sha256
    assert previous["previous_model_family"] == prior.model_family
    assert previous["target_kind"] == "NEXT_TRIAL_WAIT8_TOTAL_DISPLACEMENT_M"
    assert previous["previous_prediction_m"] == pytest.approx(.16)
    assert previous["target_observed_m"] == pytest.approx(.4)
    assert previous["prior_prediction_abs_error_m"] == pytest.approx(.24)
    assert previous["model_revised_and_admitted"] is False
    result = asyncio.run(gate.propose_after(ledger))
    assert result.prior_hypothesis_relation == "REVISE_PRIOR"
    assert result.prior_proposal_sha256 == prior.proposal_sha256
    assert result.numeric_evidence_refs[0]["metric_role"] == "WAIT8_TOTAL_M"
    assert result.numeric_evidence_refs[0]["trial_ordinal"] == 2
    assert not result.model_structure_admitted
    assert result.learning_admissions == result.l0_promotions == 0


@pytest.mark.parametrize("case", [
    "mae-as-total", "prediction-as-error", "foreign-prior", "wrong-relation",
    "unobserved-future", "no-new-measurement", "unbounded-claim",
])
def test_second_open_wrong_metric_roles_or_false_structural_revision_rejected(case):
    ledger = new_ledger()
    accept(ledger, 1)
    def corrupt(p):
        if p["prior_hypothesis_relation"] == "FIRST_HYPOTHESIS":
            return p
        if case == "mae-as-total":
            p["numeric_evidence_refs"][0]["value_m"] = .05
        elif case == "prediction-as-error":
            p["numeric_evidence_refs"][1]["value_m"] = .16
        elif case == "foreign-prior":
            p["numeric_evidence_refs"][1]["metric_role"] = "NEXT_TICK_THRESHOLD"
        elif case == "wrong-relation":
            p["prior_hypothesis_relation"] = "FIRST_HYPOTHESIS"
        elif case == "unobserved-future":
            p["numeric_evidence_refs"][0]["trial_ordinal"] = 3
        elif case == "no-new-measurement":
            p["numeric_evidence_refs"] = [
                {"metric_role": "WAIT8_TOTAL_M", "trial_ordinal": 1,
                 "pair_index": 0, "value_m": .4},
            ]
        elif case == "unbounded-claim":
            p["self_authorized_action"] = True
        return p
    gate = BoundedLiveL2(
        fixture_engine(changes=corrupt), require_real_llama=False,
    )
    asyncio.run(gate.propose_after(ledger))
    accept(ledger, 2)
    with pytest.raises(LiveL2Rejected):
        asyncio.run(gate.propose_after(ledger))
    assert len(gate.proposals) == 1
    assert gate.failed_closed


def test_original_failed_run_cannot_be_requalified_by_later_eof_envelope():
    from adapters.mineflayer.l_mp11_paper_eof_envelope import seal_after_shutdown
    from test_self_body_s50_l2_mp11_paper_audit import original
    from tools.mp11_g3_paper_one_world_audit import review

    # This is synthetic: the historical FAIL report status remains immutable.
    raw = original() + b"> "
    report = {
        "status": "FAIL",
        "classification": "MP11_G3_ORIGINAL_PAPER_NOT_QUALIFIED",
        "node_exit": 0, "server_exit": 0, "real_model_calls": 2,
        "mp11_paper_eof_predeclared": True,
        "mp11_paper_eof": __import__("dataclasses").asdict(
            seal_after_shutdown(raw, predeclared=True),
        ),
    }
    with pytest.raises(Exception, match="original single-World complete runtime"):
        review(report, raw, expected_l2_calls=2)
