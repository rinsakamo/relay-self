"""Pinned original S / L8 plus M post-epoch Engine handoff contract.

This runs in the CI same-process overlay: original S/B0 and L8 imports are
pinned. Native inputs are synthetic; model provider is a fake. One positive
shape uses an explicitly SYNTHETIC tap re-bound to a separate original S
coordinator result. This does not prove deployed S42 -> model linkage.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_metabolism_same_process_slm_product as slm
from experiments.metabolism_relay_engine_usage import (
    OwnerEngineCall,
    OwnerEpochEngineBinding,
)
from experiments.metabolism_s_owner_engine_handoff import (
    bounded_s_owner_engine_cost_row,
    observe_s_owner_engine_usage,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    OpenCognitionRequest,
    ProviderCallFacts,
    ProviderExpression,
    RelayEngine,
)
from relay_self.runtime_coordination import coordinate_decision_epoch


def fake_model_epoch():
    requests = []

    def provider(request, *, mode):
        assert mode is CognitionMode.OPEN
        requests.append(request)
        return ProviderExpression(
            text="private fake expression",
            provenance=Provenance("fake-provider", "not-native"),
            call_facts=ProviderCallFacts(
                prompt_tokens=27, completion_tokens=13, total_tokens=40,
            ),
        )

    req = OpenCognitionRequest(
        request_id="original-s-open-1", instruction="Analyze new surface",
        intent_id="test", focus="SURFACE", context=(),
    )
    engine = RelayEngine(provider)
    result = coordinate_decision_epoch(
        ActionSupervisor(), at_ns=10,
        provenance=Provenance("test", "original-coordinator"),
        decision_step=lambda: req,
        relay_engine=engine.open,
    )
    assert requests == [req]
    assert result.cognition_result.request_id == req.request_id
    return req, result


def test_existing_s42_deterministic_choice_is_not_mistaken_for_llm_cost():
    data = slm.common_epoch()
    tap = slm.host_tap(data)
    assert tap.status == "RECORDED" and data[4].cognition_requested
    value = observe_s_owner_engine_usage(
        enabled=True, original_s_epoch=data[4], original_slm_tap=tap,
    )
    assert value.status == "UNMEASURED" and value.usage is None
    row = bounded_s_owner_engine_cost_row(value)
    assert row["provider_calls"] is None
    assert row["input_tokens"] is None
    assert row["new_model_calls"] == 0
    assert row["source_attested"] is False


def test_real_s_coordinator_with_fake_model_result_receipt_only_on_identity():
    data = slm.common_epoch()
    real_tap = slm.host_tap(data)
    req, engine_epoch = fake_model_epoch()
    # Synthetic source envelope, explicitly NOT emitted by the real S/L8/M
    # pipeline, which presently observes a WorldConditionedChoice epoch.
    synthetic_tap = replace(real_tap, original_s_epoch=engine_epoch)
    binding = OwnerEpochEngineBinding(
        session_id=synthetic_tap.session_id,
        probe_seq=synthetic_tap.probe_seq,
        native_request_id=synthetic_tap.request_id,
        meter_id="meter-own-engine-1", level="L2",
    )
    original_return = engine_epoch.cognition_result
    observed = observe_s_owner_engine_usage(
        enabled=True, original_s_epoch=engine_epoch,
        original_slm_tap=synthetic_tap,
        engine_call=OwnerEngineCall(req, original_return),
        binding=binding,
    )
    assert observed.status == "RECORDED"
    assert observed.original_s_epoch is engine_epoch
    assert observed.usage.provider_calls == 1
    assert observed.usage.input_tokens == 27
    assert observed.usage.output_tokens == 13
    assert observed.usage.cpu_ns is None and observed.usage.gpu_ns is None
    assert "private fake expression" not in repr(bounded_s_owner_engine_cost_row(observed))


def test_wrong_s_tap_and_replayed_engine_result_are_rejected():
    data = slm.common_epoch()
    actual_tap = slm.host_tap(data)
    req, result = fake_model_epoch()
    binding = OwnerEpochEngineBinding(
        session_id=actual_tap.session_id, probe_seq=actual_tap.probe_seq,
        native_request_id=actual_tap.request_id,
        meter_id="m-1", level="L2",
    )
    for tap, call, target in (
        (actual_tap, OwnerEngineCall(req, result.cognition_result), result),
        (replace(actual_tap, original_s_epoch=result),
         OwnerEngineCall(req, replace(result.cognition_result)), result),
        (actual_tap, OwnerEngineCall(req, result.cognition_result), data[4]),
    ):
        observed = observe_s_owner_engine_usage(
            enabled=True, original_s_epoch=target,
            original_slm_tap=tap, engine_call=call, binding=binding,
        )
        assert observed.status == "DEFERRED"
        assert observed.usage is None
        assert bounded_s_owner_engine_cost_row(observed)["provider_calls"] is None


def test_cheap_s_epoch_rejects_unrelated_engine_meter_injection():
    data = slm.common_epoch()
    tap = slm.host_tap(data)
    req, fake = fake_model_epoch()
    binding = OwnerEpochEngineBinding(
        session_id=tap.session_id, probe_seq=tap.probe_seq,
        native_request_id=tap.request_id, meter_id="forged-meter", level="L2",
    )
    observed = observe_s_owner_engine_usage(
        enabled=True, original_s_epoch=data[4], original_slm_tap=tap,
        engine_call=OwnerEngineCall(req, fake.cognition_result),
        binding=binding,
    )
    assert observed.status == "DEFERRED" and observed.usage is None


def test_disabled_never_reads_source_or_engine():
    class Unreadable:
        def __getattribute__(self, _name):
            raise AssertionError("disabled observer read a source")
    original = object()
    observed = observe_s_owner_engine_usage(
        original_s_epoch=original, original_slm_tap=Unreadable(),
        engine_call=Unreadable(), binding=Unreadable(),
    )
    assert observed.status == "DISABLED" and observed.original_s_epoch is original


@pytest.mark.parametrize("patch", [
    {"action_authority": True},
    {"native_reads": 1},
    {"energy_debits": 1},
    {"learning_updates": 1},
    {"model_invocations": 1},
    {"reason": "made_up"},
])
def test_bounded_engine_audit_rejects_forged_authority(patch):
    data = slm.common_epoch()
    observed = observe_s_owner_engine_usage(
        enabled=True, original_s_epoch=data[4],
        original_slm_tap=slm.host_tap(data),
    )
    with pytest.raises(ValueError):
        bounded_s_owner_engine_cost_row(replace(observed, **patch))


def test_unadmitted_tap_never_produces_usage():
    data = slm.common_epoch()
    original = slm.host_tap(data)
    for bad in (
        replace(original, status="DEFERRED"),
        replace(original, source_scope="not_owner"),
        replace(original, action_authority=True),
    ):
        observed = observe_s_owner_engine_usage(
            enabled=True, original_s_epoch=data[4], original_slm_tap=bad,
        )
        assert observed.status == "DEFERRED"
        assert observed.usage is None
