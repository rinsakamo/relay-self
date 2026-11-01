"""S opt-in model request uses real llama.cpp HTTP serialization with fake wire.

Source is genuine pinned S42/B0/L8/M typed original (synthetic native).
HTTP response is fake. This is NOT an actual llama.cpp server or World run.
"""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

import test_metabolism_same_process_slm_product as slm
from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from adapters.mineflayer.s_owner_postepoch_l2_runtime import (
    SPostEpochL2OpenRuntime,
    SPostEpochL2RuntimeResult,
    bounded_s_postepoch_runtime_row,
)
from experiments.metabolism_relay_engine_usage import OwnerEpochEngineBinding
from relay_self.relay_engine import OpenCognitionRequest


class HTTPReply:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.body).encode("utf-8")


def original():
    data = slm.common_epoch()
    tap = slm.host_tap(data)
    assert tap.status == "RECORDED"
    request = OpenCognitionRequest(
        request_id="separate-owner-l2-dev",
        instruction="Analyze uncertainty without authorizing any Action.",
        intent_id="post-owner", focus="POST_S_L2_SHADOW_DEV", context=(),
    )
    binding = OwnerEpochEngineBinding(
        session_id=tap.session_id,
        probe_seq=tap.probe_seq,
        native_request_id=tap.request_id,
        meter_id="one-source-bound-provider-receipt",
        level="L2",
    )
    provider = LlamaCppRelayProvider(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="user-served-model", timeout=5.0,
    )
    args = {
        "original_s_epoch": data[4],
        "original_slm_tap": tap,
        "request": request,
        "binding": binding,
        "provider": provider,
    }
    return data, args


def test_actual_provider_serializer_one_post_s_call_and_m_readback(monkeypatch):
    from adapters.llama_cpp import relay_engine as http_module

    wire_calls = []

    def fake_urlopen(request, *, timeout):
        wire = json.loads(request.data.decode("utf-8"))
        wire_calls.append((request.full_url, timeout, wire))
        return HTTPReply({
            "choices": [{
                "message": {"content": "private fake response never exported"},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 32,
                "completion_tokens": 12,
                "total_tokens": 44,
            },
        })

    monkeypatch.setattr(http_module.urllib.request, "urlopen", fake_urlopen)
    data, kwargs = original()
    ledger, supervisor = data[1], data[5]
    before = ledger.body, ledger.credit_count, supervisor.last_at_ns
    original_choice = data[4].cognition_result
    runtime = SPostEpochL2OpenRuntime(enabled=True, max_calls=1)
    result = runtime.execute(**kwargs)

    assert result.status == "RECORDED"
    assert runtime.calls_reserved == 1
    assert result.provider_calls_observed == 1
    assert result.companion.usage.provider_calls == 1
    assert result.companion.usage.input_tokens == 32
    assert result.companion.usage.output_tokens == 12
    assert result.companion.usage.cpu_ns is None
    assert not result.source_attested and not result.action_authority
    assert len(wire_calls) == 1
    url, timeout, payload = wire_calls[0]
    assert url == "http://127.0.0.1:1234/v1/chat/completions"
    assert timeout == 5.0
    assert payload["model"] == "user-served-model"
    assert payload["max_tokens"] == 256
    assert payload["reasoning_effort"] == "none"
    assert payload["cache_prompt"] is False
    assert payload["messages"][1]["content"].find("separate-owner-l2-dev") >= 0
    assert ledger.body is before[0]
    assert ledger.credit_count == before[1]
    assert supervisor.last_at_ns == before[2]
    assert data[4].cognition_result is original_choice
    assert supervisor.open_actions == ()
    row = bounded_s_postepoch_runtime_row(result)
    assert row["observed_provider_calls"] == 1
    assert row["input_tokens"] == 32
    assert row["output_tokens"] == 12
    assert "private fake response" not in repr(row)

    again = runtime.execute(**kwargs)
    assert again.status == "DEFERRED"
    assert again.reason == "duplicate_or_budget_exhausted"
    assert len(wire_calls) == 1


def test_missing_usage_is_unknown_not_free(monkeypatch):
    from adapters.llama_cpp import relay_engine as http_module

    def fake_urlopen(_request, *, timeout):
        return HTTPReply({
            "choices": [{"message": {"content": "fixture"}, "finish_reason": "stop"}],
        })

    monkeypatch.setattr(http_module.urllib.request, "urlopen", fake_urlopen)
    _, kwargs = original()
    out = SPostEpochL2OpenRuntime(enabled=True).execute(**kwargs)
    assert out.status == "RECORDED"
    assert out.provider_calls_observed == 1
    assert out.companion.usage.input_tokens is None
    assert out.companion.usage.output_tokens is None
    assert bounded_s_postepoch_runtime_row(out)["input_tokens"] is None


@pytest.mark.parametrize("attack", [
    "source_not_recorded", "foreign_tap", "forged_tap", "foreign_probe",
    "foreign_session", "wrong_level", "wrong_focus", "inflight_action",
    "timed_out_action", "foreign_world_choice", "remote_endpoint",
    "https_endpoint", "untrusted_provider",
])
def test_rejects_before_network_request(monkeypatch, attack):
    from adapters.llama_cpp import relay_engine as http_module

    count = 0

    def forbidden(*_args, **_kwargs):
        nonlocal count
        count += 1
        raise AssertionError("invalid source must not call HTTP")

    monkeypatch.setattr(http_module.urllib.request, "urlopen", forbidden)
    _, kwargs = original()
    args = kwargs.copy()
    tap = args["original_slm_tap"]
    epoch = args["original_s_epoch"]
    bind = args["binding"]
    if attack == "source_not_recorded":
        args["original_slm_tap"] = replace(tap, status="DEFERRED")
    elif attack == "foreign_tap":
        args["original_slm_tap"] = replace(tap, original_s_epoch=object())
    elif attack == "forged_tap":
        args["original_slm_tap"] = replace(tap, action_authority=True)
    elif attack == "foreign_probe":
        args["binding"] = replace(bind, probe_seq=bind.probe_seq + 1)
    elif attack == "foreign_session":
        args["binding"] = replace(bind, session_id="other-session")
    elif attack == "wrong_level":
        args["binding"] = replace(bind, level="L1")
    elif attack == "wrong_focus":
        args["request"] = replace(args["request"], focus="EXECUTE_ACTION")
    elif attack == "inflight_action":
        e = replace(epoch, next_action_deadline_ns=900)
        args["original_s_epoch"] = e
        args["original_slm_tap"] = replace(tap, original_s_epoch=e)
    elif attack == "timed_out_action":
        e = replace(epoch, timed_out_actions=(object(),))
        args["original_s_epoch"] = e
        args["original_slm_tap"] = replace(tap, original_s_epoch=e)
    elif attack == "foreign_world_choice":
        e = replace(epoch, cognition_result=object())
        args["original_s_epoch"] = e
        args["original_slm_tap"] = replace(tap, original_s_epoch=e)
    elif attack in ("remote_endpoint", "https_endpoint"):
        url = {
            "remote_endpoint": "http://example.org:8000/v1/chat/completions",
            "https_endpoint": "https://127.0.0.1:443/v1/chat/completions",
        }[attack]
        args["provider"] = LlamaCppRelayProvider(
            endpoint=url, model="test-model",
        )
    elif attack == "untrusted_provider":
        args["provider"] = lambda *args, **kwargs: None
    result = SPostEpochL2OpenRuntime(enabled=True).execute(**args)
    assert result.status == "DEFERRED"
    assert result.requests_submitted == 0
    assert count == 0


def test_failed_or_ambiguous_http_burns_budget_without_claiming_zero(monkeypatch):
    from adapters.llama_cpp import relay_engine as http_module

    attempts = 0

    def fails(_request, *, timeout):
        nonlocal attempts
        attempts += 1
        raise TimeoutError("backend outcome not known")

    monkeypatch.setattr(http_module.urllib.request, "urlopen", fails)
    _, kwargs = original()
    runtime = SPostEpochL2OpenRuntime(enabled=True)
    out = runtime.execute(**kwargs)
    assert out.status == "CALL_UNCERTAIN"
    assert out.external_call_outcome_unknown
    assert out.requests_submitted == runtime.calls_reserved == 1
    assert out.provider_calls_observed is None
    assert out.companion is None
    row = bounded_s_postepoch_runtime_row(out)
    assert row["backend_call_outcome_unknown"]
    assert row["observed_provider_calls"] is None
    assert row["input_tokens"] is None
    assert runtime.execute(**kwargs).status == "DEFERRED"
    assert attempts == 1


def test_invalid_response_after_http_is_unknown_without_retry(monkeypatch):
    from adapters.llama_cpp import relay_engine as http_module

    attempted = []

    def bad(_request, *, timeout):
        attempted.append(1)
        return HTTPReply({"choices": []})

    monkeypatch.setattr(http_module.urllib.request, "urlopen", bad)
    _, kwargs = original()
    out = SPostEpochL2OpenRuntime(enabled=True).execute(**kwargs)
    assert out.status == "CALL_UNCERTAIN"
    assert out.provider_calls_observed is None
    assert len(attempted) == 1


def test_disabled_does_not_read_source_or_network():
    class NoAccess:
        def __getattribute__(self, name):
            raise AssertionError("OFF touched " + name)

    o = NoAccess()
    runtime = SPostEpochL2OpenRuntime()
    out = runtime.execute(
        original_s_epoch=o, original_slm_tap=o,
        provider=o, request=o, binding=o,
    )
    assert out.status == "DISABLED"
    assert runtime.calls_reserved == 0
    assert bounded_s_postepoch_runtime_row(out)["attempted_http_requests"] == 0


@pytest.mark.parametrize("attack", [
    {"action_authority": True}, {"source_attested": True},
    {"energy_debits": 1}, {"action_issues": 1},
    {"learning_updates": 1}, {"habit_grants": 1},
    {"requests_submitted": 1}, {"provider_calls_observed": 0},
    {"external_call_outcome_unknown": True},
])
def test_bounded_runtime_export_rejects_forged_readout(attack):
    off = SPostEpochL2RuntimeResult("DISABLED", "not_enabled", None)
    with pytest.raises(ValueError):
        bounded_s_postepoch_runtime_row(replace(off, **attack))


def test_invalid_budget_or_optin_fails_closed():
    with pytest.raises(ValueError):
        SPostEpochL2OpenRuntime(enabled=1)
    with pytest.raises(ValueError):
        SPostEpochL2OpenRuntime(enabled=True, max_calls=4)
    with pytest.raises(ValueError):
        SPostEpochL2OpenRuntime(enabled=True, max_calls=True)


def test_canonical_provider_rejects_query_before_runtime_exists():
    # Existing owner/provider constructor already fails closed at this layer.
    with pytest.raises(ValueError):
        LlamaCppRelayProvider(
            endpoint="http://127.0.0.1:1234/v1/chat/completions?override=true",
            model="test-model",
        )
