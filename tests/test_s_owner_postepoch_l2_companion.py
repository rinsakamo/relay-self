"""S #537 genuine original S42 choice + separate completed RelayEngine L2 companion.

The native/B0 and L8 sources are intentionally synthetic fixture sources, and
the provider is an explicit deterministic test double, NOT actual Gemma.
No S49 runtime hook, Action issuance, or scientific result is asserted.
Run ONLY with pinned original S product and L8 original source overlay.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_metabolism_same_process_slm_product as slm
from adapters.mineflayer.s_owner_postepoch_l2_companion import (
    SPostEpochL2CompanionLease,
    bounded_s_l2_companion_cost_row,
)
from experiments.metabolism_cognitive_lifecycle import (
    CognitionCostSample,
    summarize_cognitive_lifecycle,
)
from experiments.metabolism_relay_engine_usage import OwnerEpochEngineBinding
from experiments.metabolism_slm_dev_host_tap import bounded_s_l_m_audit_row
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    OpenCognitionRequest,
    ProviderCallFacts,
    ProviderExpression,
    RelayEngine,
)


def original_and_post_l2(*, missing_tokens=False):
    data = slm.common_epoch()
    tap = slm.host_tap(data)
    assert tap.status == "RECORDED"
    original_s = data[4]
    assert original_s.cognition_requested
    # This S owner decision is still WorldConditionedChoice, not L2.
    assert original_s.cognition_result.selection.value == tap.s_choice
    assert original_s.cognition_result is data[0].s_epoch.cognition_result

    calls = []

    def fake_provider(request, *, mode):
        assert mode is CognitionMode.OPEN
        calls.append(request)
        return ProviderExpression(
            text="private fixture only; no model data should be exported",
            provenance=Provenance("test-provider", "separate-l2-return"),
            call_facts=(
                ProviderCallFacts()
                if missing_tokens
                else ProviderCallFacts(
                    prompt_tokens=37, completion_tokens=23, total_tokens=60,
                )
            ),
        )

    req = OpenCognitionRequest(
        request_id="post-s-l2-model-request-1",
        instruction="Evaluate uncertainty after original S decision",
        intent_id="test-only",
        focus="POST_S_EXPLORATION",
        context=(),
    )
    engine = RelayEngine(fake_provider)
    result = engine.open(req)  # The *test's* explicit cognition owner call.
    binding = OwnerEpochEngineBinding(
        session_id=tap.session_id, probe_seq=tap.probe_seq,
        native_request_id=tap.request_id, meter_id="model-cost-receipt-1",
        level="L2",
    )
    assert len(calls) == 1
    return data, tap, original_s, req, result, binding, calls


def test_owner_preserves_original_s_l8_m_and_separate_l2_accounting():
    data, tap, original_s, req, result, binding, calls = original_and_post_l2()
    ledger = data[1]
    before = (ledger.body, ledger.credit_count, data[5].last_at_ns,
              original_s.cognition_result)
    lease = SPostEpochL2CompanionLease(enabled=True)
    out = lease.observe_after_owner(
        original_s_epoch=original_s, original_slm_tap=tap,
        model_request=req, model_result=result, engine_binding=binding,
    )
    assert out.status == "RECORDED"
    assert out.original_s_epoch is original_s
    assert out.usage.provider_calls == 1
    assert (out.usage.input_tokens, out.usage.output_tokens) == (37, 23)
    assert out.usage.cpu_ns is None and out.usage.gpu_ns is None
    assert out.cost_origin == "POST_S_SEPARATE_L2_COMPANION_NOT_CHEAP_S_COST"
    assert before == (ledger.body, ledger.credit_count, data[5].last_at_ns,
                      original_s.cognition_result)
    assert len(calls) == 1  # M observation never replays model
    row = bounded_s_l2_companion_cost_row(out)
    assert row["provider_calls"] == 1 and row["new_provider_calls"] == 0
    assert row["native_source_attested"] is False
    assert "private fixture only" not in str(row)
    # Old S/L8/M row remains unchanged while companion costs attach as
    # separate later cognition work, NOT original S42 cost.
    m = summarize_cognitive_lifecycle((CognitionCostSample(
        epoch_id="post-s-l2-dev", task_id="unknown-environment",
        condition_id="grass", phase="EXPLORE", outcome="UNKNOWN",
        audit_row=bounded_s_l_m_audit_row(tap), usage=out.usage,
    ),))
    assert m.phases[0].metrics[0].complete_total == 1
    assert m.phases[0].metrics[1].complete_total == 37
    assert m.source_attested is False


def test_missing_provider_tokens_are_unknown_not_zero():
    _, tap, original_s, req, result, binding, _ = original_and_post_l2(
        missing_tokens=True,
    )
    out = SPostEpochL2CompanionLease(enabled=True).observe_after_owner(
        original_s_epoch=original_s, original_slm_tap=tap,
        model_request=req, model_result=result, engine_binding=binding,
    )
    assert out.status == "RECORDED"
    assert out.usage.provider_calls == 1
    assert out.usage.input_tokens is None and out.usage.output_tokens is None
    assert bounded_s_l2_companion_cost_row(out)["input_tokens"] is None


def test_lease_is_single_use_for_original_s_and_model_return():
    _, tap, original_s, req, result, binding, _ = original_and_post_l2()
    lease = SPostEpochL2CompanionLease(enabled=True)
    kwargs = {
        "original_s_epoch": original_s, "original_slm_tap": tap,
        "model_request": req, "model_result": result, "engine_binding": binding,
    }
    first = lease.observe_after_owner(**kwargs)
    assert first.status == "RECORDED"
    assert lease.observe_after_owner(**kwargs).status == "DEFERRED"
    assert lease.observe_after_owner(
        **{**kwargs, "engine_binding": replace(binding, meter_id="new-id")},
    ).status == "DEFERRED"


@pytest.mark.parametrize("attack", (
    "foreign_tap", "bad_status", "foreign_seq", "foreign_request",
    "foreign_session", "wrong_level", "wrong_model_request",
    "wrong_model_result", "inflight_action", "timed_out_actions",
    "forged_s_choice", "no_model", "bad_model_token_total",
    "bad_source_scope", "owner_tap_authority",
))
def test_foreign_source_or_spoofed_meter_is_not_recorded(attack):
    _, tap, original_s, req, result, binding, _ = original_and_post_l2()
    if attack == "foreign_tap":
        tap = replace(tap, original_s_epoch=object())
    elif attack == "bad_status":
        tap = replace(tap, status="DEFERRED")
    elif attack == "foreign_seq":
        binding = replace(binding, probe_seq=binding.probe_seq + 1)
    elif attack == "foreign_request":
        binding = replace(binding, native_request_id="foreign")
    elif attack == "foreign_session":
        binding = replace(binding, session_id="foreign")
    elif attack == "wrong_level":
        binding = replace(binding, level="L0")
    elif attack == "wrong_model_request":
        req = replace(req, request_id="other")
    elif attack == "wrong_model_result":
        result = replace(result, request_id="other")
    elif attack == "inflight_action":
        original_s = replace(original_s, next_action_deadline_ns=123)
        tap = replace(tap, original_s_epoch=original_s)
    elif attack == "timed_out_actions":
        original_s = replace(original_s, timed_out_actions=(object(),))
        tap = replace(tap, original_s_epoch=original_s)
    elif attack == "forged_s_choice":
        tap = replace(tap, s_choice="MOVE_AWAY" if tap.s_choice == "WAIT" else "WAIT")
    elif attack == "no_model":
        result = None
    elif attack == "bad_model_token_total":
        result = replace(result, call_facts=ProviderCallFacts(
            prompt_tokens=37, completion_tokens=23, total_tokens=99,
        ))
    elif attack == "bad_source_scope":
        tap = replace(tap, source_scope="FORGED")
    elif attack == "owner_tap_authority":
        tap = replace(tap, action_authority=True)
    out = SPostEpochL2CompanionLease(enabled=True).observe_after_owner(
        original_s_epoch=original_s, original_slm_tap=tap,
        model_request=req, model_result=result, engine_binding=binding,
    )
    assert out.status == "DEFERRED" and out.usage is None
    assert bounded_s_l2_companion_cost_row(out)["provider_calls"] is None


def test_disabled_does_not_touch_original_source_or_model():
    class NoRead:
        def __getattribute__(self, name):
            raise AssertionError("disabled companion accessed " + name)

    obj = NoRead()
    lease = SPostEpochL2CompanionLease()
    out = lease.observe_after_owner(
        original_s_epoch=obj, original_slm_tap=obj,
        model_request=obj, model_result=obj, engine_binding=obj,
    )
    assert out.status == "DISABLED" and out.original_s_epoch is obj


def test_invalid_or_exceeded_lease_denies_new_companion():
    with pytest.raises(ValueError):
        SPostEpochL2CompanionLease(enabled=1)
    with pytest.raises(ValueError):
        SPostEpochL2CompanionLease(enabled=True, max_epochs=0)
    _, tap, original_s, req, result, binding, _ = original_and_post_l2()
    lease = SPostEpochL2CompanionLease(enabled=True, max_epochs=1)
    assert lease.observe_after_owner(
        original_s_epoch=original_s, original_slm_tap=tap,
        model_request=req, model_result=result, engine_binding=binding,
    ).status == "RECORDED"
    assert lease.observe_after_owner(
        original_s_epoch=replace(original_s),
        original_slm_tap=replace(tap, original_s_epoch=replace(original_s)),
        model_request=req, model_result=result, engine_binding=binding,
    ).status == "DEFERRED"


@pytest.mark.parametrize("attack", (
    {"action_authority": True}, {"source_attested": True},
    {"new_provider_calls": 1}, {"new_native_reads": 1},
    {"energy_debits": 1}, {"action_issues": 1},
    {"habit_grants": 1}, {"learning_updates": 1},
    {"cost_origin": "CHEAP_L0"},
))
def test_export_never_mints_cost_or_action_authority(attack):
    from adapters.mineflayer.s_owner_postepoch_l2_companion import SPostEpochL2Companion

    out = SPostEpochL2Companion(object(), "DISABLED", "not_enabled")
    with pytest.raises(ValueError):
        bounded_s_l2_companion_cost_row(replace(out, **attack))
