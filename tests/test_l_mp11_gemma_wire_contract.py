"""Strict Gemma-4 llama.cpp native JSON Schema + no-thinking wire controls.

Synthetic HTTP fixtures only; no real GGUF or Minecraft World in this CI.
"""
from __future__ import annotations

import io
import json

import pytest

from adapters.mineflayer.l_mp11_gemma_wire_contract import (
    GEMMA_MAX_COMPLETION,
    GEMMA_SCHEMA_NAME,
    GemmaWireRejected,
    enforce_gemma_thinking_off,
    pin_gemma_wire,
    strict_gemma_evidence_schema,
)
from tools.l_mp11_gemma_structured_preflight import (
    GemmaPreflightRejected,
    run,
    synthetic_test_body,
    verify_preflight_report,
)


def result(*, finish_reason="stop", reasoning=None, tokens=180):
    return {
        "id": "synthetic-http-completion",
        "model": "local-gemma-preflight-fixture",
        "choices": [{
            "index": 0,
            "finish_reason": finish_reason,
            "message": {
                "role": "assistant",
                "reasoning_content": reasoning,
                "content": json.dumps({
                    "referenced_prior_ordinals": [1],
                    "reconsideration": "QUESTION_APPLICABILITY",
                    "model_family": "PHASE_DEPENDENT",
                    "next_test": "CHECK_PAPER_CALLBACK_PHASE",
                    "explanation": "The example movement may have phase dependence.",
                    "falsification_test": "Compare fixed-phase and varied-phase simulated examples.",
                    "predicted_wait_total_m": .16,
                    "capability_assessment": "CONDITIONAL_HYPOTHESIS",
                    "prior_hypothesis_relation": "FIRST_HYPOTHESIS",
                    "evidence_ids": ["T1_W8"],
                }, separators=(",", ":")),
            },
        }],
        "usage": {
            "prompt_tokens": 240,
            "completion_tokens": tokens,
            "total_tokens": 240 + tokens,
            "completion_tokens_details": {"reasoning_tokens": 0},
        },
    }


def test_actual_source_catalog_becomes_native_strict_bounded_schema():
    body = synthetic_test_body("local-gemma")
    pinned = pin_gemma_wire(body, evidence_ids=True)
    assert pinned is body
    assert body["max_tokens"] == GEMMA_MAX_COMPLETION == 512
    assert body["reasoning_effort"] == "none"
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    assert body["temperature"] == 0 and body["seed"] == 1
    assert body["cache_prompt"] is False and body["stream"] is False
    fmt = body["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["name"] == GEMMA_SCHEMA_NAME
    assert fmt["json_schema"]["strict"] is True
    schema = fmt["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["properties"]["evidence_ids"]["items"]["enum"] == sorted([
        "T1_W8", "T1_CMAE",
        *[f"T1_P{i}{kind}" for i in range(1, 8) for kind in ("PRED", "ERR")],
    ])
    assert schema["properties"]["prior_hypothesis_relation"]["enum"] == [
        "FIRST_HYPOTHESIS"
    ]
    assert schema["properties"]["evidence_ids"]["maxItems"] == 1
    assert strict_gemma_evidence_schema(body) == fmt


def test_legacy_mode_is_not_silently_requalified_as_strict():
    original = pin_gemma_wire(synthetic_test_body("model"), evidence_ids=False)
    assert original["response_format"] == {"type": "json_object"}
    assert original["reasoning_effort"] == "none"
    assert original["chat_template_kwargs"] == {"enable_thinking": False}


@pytest.mark.parametrize("thought", [
    "unclosed reasoning", "$thought", "<think>some analysis</think>",
])
def test_explicit_thinking_off_must_be_observed_not_just_requested(thought):
    with pytest.raises(GemmaWireRejected, match="reasoning channel"):
        enforce_gemma_thinking_off(result(reasoning=thought))


def test_reasoning_in_content_or_token_usage_fails_closed():
    response = result()
    enforce_gemma_thinking_off(response)
    response["choices"][0]["message"]["content"] += "<think>"
    with pytest.raises(GemmaWireRejected):
        enforce_gemma_thinking_off(response)
    response = result()
    response["usage"]["completion_tokens_details"]["reasoning_tokens"] = 7
    with pytest.raises(GemmaWireRejected):
        enforce_gemma_thinking_off(response)


def test_missing_or_foreign_source_cannot_construct_schema():
    body = synthetic_test_body("model")
    raw = json.loads(body["messages"][1]["content"])
    raw["context"][0]["provenance"]["source"] = "fake.unowned.data"
    body["messages"][1]["content"] = json.dumps(raw)
    with pytest.raises(GemmaWireRejected):
        pin_gemma_wire(body, evidence_ids=True)


def test_single_local_http_probe_and_readback_no_world(tmp_path, monkeypatch):
    import urllib.request

    response = result()
    calls = []
    def fake_http(request, *, timeout):
        calls.append((request, timeout))
        return io.BytesIO(json.dumps(response).encode("utf-8"))
    monkeypatch.setattr(urllib.request, "urlopen", fake_http)
    endpoint = "http://127.0.0.1:8080/v1/chat/completions"
    report = run(endpoint, "local-gemma", tmp_path / "probe")
    assert report["actual_requests"] == 1
    assert report["strict_json_schema"] is True
    assert report["thinking_off_checked"] is True
    assert report["model_weights_attested"] is False
    assert report["world_qualified"] is False
    assert report["physical_paper_observation"] is False
    assert len(calls) == 1
    req = json.loads((tmp_path / "probe" / "llama-request-1.raw.json").read_text())
    assert req["response_format"]["type"] == "json_schema"
    assert req["chat_template_kwargs"] == {"enable_thinking": False}
    assert verify_preflight_report(
        tmp_path / "probe" / "gemma-structured-preflight.json",
        endpoint=endpoint, model="local-gemma",
    ) == report
    with pytest.raises(FileExistsError):
        run(endpoint, "local-gemma", tmp_path / "probe")


def test_length_cutoff_or_thought_is_not_bypassed_before_world(tmp_path, monkeypatch):
    import urllib.request

    for name, response in (
        ("length", result(finish_reason="length", tokens=512)),
        ("thinking", result(reasoning="hidden tokens")),
    ):
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda *a, response=response, **k: io.BytesIO(
                                json.dumps(response).encode(),
                            ))
        with pytest.raises((GemmaPreflightRejected, GemmaWireRejected, ValueError)):
            run("http://127.0.0.1:8080/v1/chat/completions",
                "model", tmp_path / name)
        assert (tmp_path / name / "llama-response-1.raw.json").exists()
        assert not (tmp_path / name / "gemma-structured-preflight.json").exists()


@pytest.mark.parametrize("tamper", [
    "reasoning", "schema", "response", "source", "model", "missing",
])
def test_tampered_preflight_does_not_unlock_world(
    tmp_path, monkeypatch, tamper,
):
    import urllib.request

    monkeypatch.setattr(
        urllib.request, "urlopen",
        lambda *a, **k: io.BytesIO(json.dumps(result()).encode()),
    )
    endpoint = "http://127.0.0.1:8080/v1/chat/completions"
    root = tmp_path / "probe"
    run(endpoint, "model", root)
    report_path = root / "gemma-structured-preflight.json"
    if tamper in {"reasoning", "schema"}:
        path = root / "llama-request-1.raw.json"
        request = json.loads(path.read_text())
        if tamper == "reasoning":
            request["chat_template_kwargs"]["enable_thinking"] = True
        else:
            request["response_format"]["json_schema"]["strict"] = False
        path.write_text(json.dumps(request))
    elif tamper == "response":
        (root / "llama-response-1.raw.json").write_text('{"not":"original"}')
    elif tamper == "missing":
        (root / "llama-response-1.raw.json").unlink()
    else:
        report = json.loads(report_path.read_text())
        report["model" if tamper == "model" else "request_sha256"] = "tampered"
        report_path.write_text(json.dumps(report))
    with pytest.raises(GemmaPreflightRejected):
        verify_preflight_report(report_path, endpoint=endpoint, model="model")


def test_preflight_only_accepts_loopback_not_remote(tmp_path):
    for endpoint in [
        "https://public.example/v1/chat/completions",
        "http://1.2.3.4:8080/v1/chat/completions",
        "http://127.0.0.1:8080/something",
        "http://127.0.0.1:8080/v1/chat/completions?bad=yes",
    ]:
        with pytest.raises(GemmaPreflightRejected):
            run(endpoint, "model", tmp_path / "unused")


@pytest.mark.parametrize("key,value", [
    ("model_family", "UNSUPPORTED"),
    ("reconsideration", 1),
    ("next_test", "ISSUE_ACTION"),
    ("capability_assessment", "LEARNED"),
    ("explanation", "too short"),
    ("falsification_test", "x" * 121),
    ("predicted_wait_total_m", 4),
    ("predicted_wait_total_m", True),
    ("predicted_wait_total_m", float("nan")),
    ("referenced_prior_ordinals", [True]),
    ("referenced_prior_ordinals", [1, 1]),
    ("evidence_ids", ["T1_W8", "T1_W8"]),
])
def test_schema_noncompliance_never_opens_world_gate(
    tmp_path, monkeypatch, key, value,
):
    import urllib.request

    response = result()
    output = json.loads(response["choices"][0]["message"]["content"])
    output[key] = value
    response["choices"][0]["message"]["content"] = json.dumps(output)
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: io.BytesIO(
        json.dumps(response).encode(),
    ))
    root = tmp_path / "rejected"
    with pytest.raises(GemmaPreflightRejected):
        run("http://127.0.0.1:8080/v1/chat/completions", "model", root)
    assert (root / "llama-response-1.raw.json").exists()
    assert not (root / "gemma-structured-preflight.json").exists()


def test_duplicate_output_keys_rejected_before_world(tmp_path, monkeypatch):
    import urllib.request

    response = result()
    message = response["choices"][0]["message"]
    message["content"] = message["content"][:-1] + ',"model_family":"PHASE_DEPENDENT"}'
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: io.BytesIO(
        json.dumps(response).encode(),
    ))
    with pytest.raises(GemmaPreflightRejected):
        run("http://127.0.0.1:8080/v1/chat/completions", "model", tmp_path / "probe")
