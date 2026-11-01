"""M-only readout of real typed RelayEngine results; provider is a DEV fixture."""
from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.metabolism_cognitive_lifecycle import (
    CognitionCostSample,
    CognitiveLifecycleRejected,
    summarize_cognitive_lifecycle,
)
from experiments.metabolism_relay_engine_usage import (
    OwnerEngineCall,
    OwnerEpochEngineBinding,
    cognitive_receipt_from_engine_results,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionMode,
    DecisionStatus,
    OpenCognitionRequest,
    ProviderCallFacts,
    ProviderDecision,
    ProviderExpression,
    RelayEngine,
    RelayEngineAttempt,
    RelayEngineResult,
)


def audit(seq=9):
    # Standalone M-layer allowlisted row fixture. The source-producing S
    # serializer is independently exercised by the pinned S cross-contract CI.
    return {
        "schema": "SLM_PASSIVE_DEV_AUDIT_V1",
        "status": "RECORDED", "reason": "complete",
        "session_id": "native-session", "probe_seq": seq,
        "request_id": f"native-request-{seq}",
        "s_choice": "WAIT", "l1_candidate": None, "l1_status": None,
        "m_model_tension": "NO_MODEL_TENSION", "l1_model_status": None,
        "source_scope": "DEV_OPTIONAL_S_L_M_AUDIT_NOT_ACTION_INPUT",
        "native_source_attested": False, "action_authority": False,
        "new_native_reads": 0, "new_cognition_calls": 0, "action_issues": 0,
        "learning_updates": 0, "habit_grants": 0, "food_credits": 0,
    }


def binding(seq=9):
    return OwnerEpochEngineBinding(
        session_id="native-session", probe_seq=seq,
        native_request_id=f"native-request-{seq}",
        meter_id=f"meter-{seq}", level="L2",
    )


def open_req(id="l2-exp"):
    return OpenCognitionRequest(
        request_id=id, instruction="Test a possible model",
        intent_id="dev", focus="MOTION", context=(),
    )


def bounded_req(id="l2-bound", think=True):
    return BoundedChoiceRequest(
        request_id=id, instruction="Choose possible experiment",
        intent_id="dev", focus="MOTION", choices=(
            BoundedChoice("grass", "Known grass"),
            BoundedChoice("ice", "Unknown ice"),
        ), context=(), think_allowed=think,
    )


def test_actual_engine_bounded_think_and_open_outputs_flow_into_m_lifecycle():
    actual_calls = []

    def provider(req, *, mode):
        actual_calls.append(mode)
        if mode is CognitionMode.OPEN:
            return ProviderExpression(
                text="private experiment text never persisted to M",
                provenance=Provenance("fixture", "provider-result"),
                call_facts=ProviderCallFacts(prompt_tokens=41, completion_tokens=19,
                                              total_tokens=60),
            )
        if mode is CognitionMode.BOUNDED:
            return ProviderDecision.unresolved(
                reason="needs thought",
                call_facts=ProviderCallFacts(prompt_tokens=10, completion_tokens=4),
            )
        return ProviderDecision.resolved(
            "ice", reason="new idea",
            call_facts=ProviderCallFacts(prompt_tokens=20, completion_tokens=5),
        )

    engine = RelayEngine(provider)
    breq, oreq = bounded_req(), open_req()
    bres, ores = engine(breq), engine.open(oreq)
    assert actual_calls == [
        CognitionMode.BOUNDED, CognitionMode.THINK, CognitionMode.OPEN,
    ]
    receipt = cognitive_receipt_from_engine_results(
        audit_row=audit(), binding=binding(),
        completed_calls=(OwnerEngineCall(breq, bres), OwnerEngineCall(oreq, ores)),
    )
    assert receipt.provider_calls == 3
    assert (receipt.input_tokens, receipt.output_tokens) == (71, 28)
    assert receipt.wall_ns == bres.elapsed_ns + ores.elapsed_ns
    assert receipt.cpu_ns is None and receipt.gpu_ns is None
    assert receipt.request_id == "native-request-9"
    assert "private experiment" not in repr(receipt)
    summary = summarize_cognitive_lifecycle((CognitionCostSample(
        epoch_id="epoch-9", task_id="ice-test", condition_id="ice",
        phase="EXPLORE", outcome="UNKNOWN", audit_row=audit(), usage=receipt,
    ),))
    phase = summary.phases[0]
    assert phase.usage_receipts == 1
    assert next(m for m in phase.metrics if m.name == "provider_calls").complete_total == 3
    assert next(m for m in phase.metrics if m.name == "cpu_ns").complete_total is None
    assert not summary.source_attested


def test_unknown_provider_token_usage_never_becomes_zero():
    def provider(req, *, mode):
        return ProviderExpression(
            text="no usage info", provenance=Provenance("fixture", "missing-usage"),
            call_facts=ProviderCallFacts(),
        )
    engine = RelayEngine(provider)
    request = open_req()
    result = engine.open(request)
    receipt = cognitive_receipt_from_engine_results(
        audit_row=audit(), binding=binding(),
        completed_calls=(OwnerEngineCall(request, result),),
    )
    assert receipt.provider_calls == 1 and receipt.input_tokens is None
    assert receipt.output_tokens is None and receipt.wall_ns >= 0


def test_partial_usage_in_multi_call_is_unknown_not_partial_total():
    def provider(req, *, mode):
        facts = (ProviderCallFacts(prompt_tokens=3, completion_tokens=2)
                 if req.request_id == "a" else ProviderCallFacts())
        return ProviderExpression(
            text="fixture", provenance=Provenance("fixture", "mixed"),
            call_facts=facts,
        )
    engine = RelayEngine(provider)
    a, b = open_req("a"), open_req("b")
    r = cognitive_receipt_from_engine_results(
        audit_row=audit(), binding=binding(), completed_calls=(
            OwnerEngineCall(a, engine.open(a)), OwnerEngineCall(b, engine.open(b)),
        ),
    )
    assert r.provider_calls == 2 and r.input_tokens is None
    assert r.output_tokens is None


@pytest.mark.parametrize("attack", [
    "foreign_session", "foreign_probe", "foreign_native_request",
    "non_recorded", "fake_authority", "duplicate_engine_request",
    "wrong_open_request", "wrong_engine_type", "empty_calls",
    "bad_level", "bad_meter_id", "incorrect_token_total",
])
def test_fake_source_or_incoherent_typed_engine_fails_closed(attack):
    req = open_req()

    def provider(r, *, mode):
        return ProviderExpression(
            text="dev", provenance=Provenance("fixture", "fixed"),
            call_facts=ProviderCallFacts(prompt_tokens=2, completion_tokens=1),
        )
    result = RelayEngine(provider).open(req)
    row = audit()
    owner = binding()
    calls = (OwnerEngineCall(req, result),)
    if attack == "foreign_session":
        owner = replace(owner, session_id="foreign")
    elif attack == "foreign_probe":
        owner = replace(owner, probe_seq=10)
    elif attack == "foreign_native_request":
        owner = replace(owner, native_request_id="foreign")
    elif attack == "non_recorded":
        row["status"] = "DEFERRED"
    elif attack == "fake_authority":
        row["action_authority"] = True
    elif attack == "duplicate_engine_request":
        calls = (OwnerEngineCall(req, result), OwnerEngineCall(req, result))
    elif attack == "wrong_open_request":
        calls = (OwnerEngineCall(open_req("foreign"), result),)
    elif attack == "wrong_engine_type":
        calls = (OwnerEngineCall(bounded_req(), result),)
    elif attack == "empty_calls":
        calls = ()
    elif attack == "bad_level":
        owner = replace(owner, level="L3")
    elif attack == "bad_meter_id":
        owner = replace(owner, meter_id="")
    elif attack == "incorrect_token_total":
        result = replace(result, call_facts=ProviderCallFacts(
            prompt_tokens=2, completion_tokens=1, total_tokens=999,
        ))
        calls = (OwnerEngineCall(req, result),)
    with pytest.raises(CognitiveLifecycleRejected):
        cognitive_receipt_from_engine_results(
            audit_row=row, binding=owner, completed_calls=calls,
        )


def test_bounded_rules_reject_synthetic_impossible_escalation():
    request = bounded_req(think=False)
    attempt = RelayEngineAttempt(
        mode=CognitionMode.BOUNDED, status=DecisionStatus.UNRESOLVED,
        choice_id=None, reason="unknown", elapsed_ns=1,
    )
    fake = RelayEngineResult(
        status=DecisionStatus.UNRESOLVED, choice_id=None,
        attempts=(attempt,), think_allowed=True,
    )
    with pytest.raises(CognitiveLifecycleRejected):
        cognitive_receipt_from_engine_results(
            audit_row=audit(), binding=binding(),
            completed_calls=(OwnerEngineCall(request, fake),),
        )


def test_observer_never_executes_provider_again():
    count = 0

    def provider(req, *, mode):
        nonlocal count
        count += 1
        return ProviderExpression(
            text="already-finished", provenance=Provenance("fixture", "only-once"),
        )

    req = open_req()
    result = RelayEngine(provider).open(req)
    for _ in range(2):
        cognitive_receipt_from_engine_results(
            audit_row=audit(), binding=binding(),
            completed_calls=(OwnerEngineCall(req, result),),
        )
    assert count == 1
