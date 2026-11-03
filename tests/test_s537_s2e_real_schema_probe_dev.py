"""S #537 S2-E one-shot schema probe: fake HTTP only, no model or World."""
from __future__ import annotations

import json

import pytest

from tools import s537_s2e_real_schema_probe_dev as probe


def _completion(
    content: str, *,
    finish_reason: str = "stop",
    reasoning_content: str | None = None,
) -> bytes:
    message = {"role": "assistant", "content": content}
    if reasoning_content is not None:
        message["reasoning_content"] = reasoning_content
    return json.dumps({
        "model": "fake-s2e",
        "choices": [{
            "index": 0, "message": message,
            "finish_reason": finish_reason,
        }],
        "usage": {
            "prompt_tokens": 15, "completion_tokens": 20, "total_tokens": 35,
        },
    }).encode()


def test_shape_exact_build10874_and_strict_three_field_schema():
    payload = probe.probe_payload("fake-s2e", 64)
    probe.assert_build10874_shape(payload)
    wrapper = payload["response_format"]
    assert set(wrapper) == {"type", "json_schema"}
    assert set(wrapper["json_schema"]) == {"schema"}
    schema = wrapper["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "status", "observation", "uncertainty",
    }
    assert set(payload) == {
        "model", "messages", "stream", "temperature",
        "max_tokens", "response_format",
    }
    assert payload["model"] == "fake-s2e"
    assert payload["max_tokens"] == 64


@pytest.mark.parametrize("bad_format", [
    {"type": "json_schema", "schema": {"type": "object"}},
    {"type": "json_schema", "json_schema": {"schema": {}}},
    {"type": "json_schema", "json_schema": {"properties": {}}},
    {"type": "json_object", "schema": {}},
])
def test_pre_http_rejects_incorrect_or_empty_schema(bad_format):
    payload = probe.probe_payload("fake-s2e", 64)
    payload["response_format"] = bad_format
    with pytest.raises(ValueError):
        probe.assert_build10874_shape(payload)


def test_one_local_post_only_and_original_validator(monkeypatch):
    calls = []

    class Reply:
        status = 200

        def read(self, bound):
            assert bound == probe.RESPONSE_LIMIT + 1
            return _completion(json.dumps({
                "status": "DEFER", "observation": "prior action recorded",
                "uncertainty": "next motion is unknown",
            }))

    class FakeConnection:
        def __init__(self, host, port, *, timeout):
            calls.append(("connect", host, port, timeout))

        def request(self, method, path, *, body, headers):
            calls.append(("request", method, path))
            assert headers["Content-Type"] == "application/json"
            payload = json.loads(body)
            probe.assert_build10874_shape(payload)

        def getresponse(self):
            return Reply()

        def close(self):
            calls.append(("close",))

    monkeypatch.setattr(probe.http.client, "HTTPConnection", FakeConnection)
    status, sent, received = probe.probe_once(
        model="fake-s2e", port=19837, max_tokens=64, timeout_s=3.0,
    )
    assert status == 200
    assert sent and received
    assert len([x for x in calls if x[0] == "request"]) == 1
    assert len([x for x in calls if x[0] == "close"]) == 1
    review = probe.validate_completion("fake-s2e", 19837, 64, received)
    assert review["status"] == "DEFER"


@pytest.mark.parametrize("bad_response", [
    _completion('{"status":"DEFER","observation":"ok","uncertainty":"?"}', finish_reason="length"),
    _completion('{"status":"DEFER","observation":"ok","uncertainty":"?"}', reasoning_content="thinking"),
    _completion('{"status":"DEFER","observation":"ok","uncertainty":"?","command":"attack"}'),
])
def test_original_transport_rejects_invalid_real_probe_envelopes(bad_response):
    from adapters.mineflayer.s60b1_loopback_adapter import TransportUnconfirmed

    with pytest.raises(TransportUnconfirmed):
        probe.validate_completion("fake-s2e", 19837, 64, bad_response)
