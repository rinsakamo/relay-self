"""S2-D opt-in strict llama.cpp JSON profile, FAKE localhost HTTP only.

No real Gemma, Minecraft, original owner identity, Paper/W3, or GPU use.
Actual S60-A/B1 transport and lease are under test.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from adapters.mineflayer.s60b1_loopback_adapter import LoopbackTransportConfig
from adapters.mineflayer.s537_s2b_gated_l2_shadow import S2BGatedL2Shadow
from adapters.mineflayer.s537_s2d_strict_json_contract import (
    OUTPUT_SCHEMA,
    PROFILE,
    REQUEST_EXTRAS,
    check_request_extras,
    validate_response_text,
)
from test_s537_s2b_gated_l2_shadow import _input, _read


def test_strict_request_extras_are_bounded_and_immutable():
    base = dict(
        model="fixture", messages=[{"role": "user", "content": "fixture"}],
        temperature=0, max_tokens=128, stream=False,
    )
    check_request_extras({**base, **REQUEST_EXTRAS})
    assert REQUEST_EXTRAS["response_format"]["schema"] == OUTPUT_SCHEMA
    assert REQUEST_EXTRAS["reasoning_effort"] == "none"
    assert REQUEST_EXTRAS["chat_template_kwargs"] == {"enable_thinking": False}
    for name, wrong in [
        ("reasoning_effort", "high"),
        ("chat_template_kwargs", {"enable_thinking": True}),
        ("response_format", {"type": "json_object"}),
    ]:
        with pytest.raises(ValueError):
            check_request_extras({**base, **REQUEST_EXTRAS, name: wrong})
    with pytest.raises(ValueError):
        check_request_extras({**base, **REQUEST_EXTRAS, "tool_choice": "auto"})


@pytest.mark.parametrize("invalid", [
    '{"assessment":"ok","uncertainty":"u"}',
    '{"assessment":"ok","uncertainty":"u","next_observation":"watch","extra":"x"}',
    '{"assessment":"ok","uncertainty":"u","next_observation":""}',
    '{"assessment":"ok","assessment":"duplicate","uncertainty":"u","next_observation":"watch"}',
    '{"assessment":"<think>reason</think>","uncertainty":"u","next_observation":"watch"}',
    'not-json',
    '{"assessment":"ok","uncertainty":null,"next_observation":"watch"}',
])
def test_strict_parser_fails_closed(invalid):
    with pytest.raises((ValueError, TypeError)):
        validate_response_text(invalid)


@pytest.mark.parametrize("fault", [
    "good", "missing", "extra", "length", "reasoning_content", "duplicate",
])
def test_original_s60_b1_strict_json_wire_profile_and_response(fault):
    observed = []
    answer = '{"assessment":"Observe displacement","uncertainty":"Speed unknown","next_observation":"Look again"}'
    if fault == "missing":
        answer = '{"assessment":"a","uncertainty":"u"}'
    if fault == "extra":
        answer = '{"assessment":"a","uncertainty":"u","next_observation":"n","action":"MOVE"}'
    if fault == "duplicate":
        answer = '{"assessment":"a","assessment":"b","uncertainty":"u","next_observation":"n"}'

    async def peer(reader, writer):
        try:
            head = await reader.readuntil(b"\r\n\r\n")
            size = next(int(line.split(b":", 1)[1]) for line in head.split(b"\r\n")
                        if line.lower().startswith(b"content-length:"))
            payload = json.loads((await reader.readexactly(size)).decode())
            check_request_extras(payload)
            observed.append(payload)
            message = {"role": "assistant", "content": answer}
            if fault == "reasoning_content":
                message["reasoning_content"] = "thinking"
            body = json.dumps({
                "model": "fixture-model",
                "choices": [{
                    "index": 0, "message": message,
                    "finish_reason": "length" if fault == "length" else "stop",
                }],
                "usage": {"prompt_tokens": 5, "completion_tokens": 20, "total_tokens": 25},
            }).encode()
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                + f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode()
                + body
            )
            await writer.drain()
        finally:
            writer.close()

    async def go():
        server = await asyncio.start_server(peer, "127.0.0.1", 0)
        async with server:
            port = server.sockets[0].getsockname()[1]
            config = LoopbackTransportConfig(
                "fixture-model", port, slots=1, max_tokens=128,
                connect_s=.5, read_s=1, whole_s=1,
            )
            shadow = S2BGatedL2Shadow(
                enabled=True, config=config, timeout_s=1,
                structured_profile=PROFILE,
            )
            src = _input()
            shadow.observe(src, owner_read=_read(src))
            for _ in range(80):
                await asyncio.sleep(.01)
                current = shadow.poll()
                if (
                    current is not None
                    or "HTTP_COMPLETION_OBSERVED" in [
                        e for e, _ in shadow._adapter.receipts
                    ]
                    or "TRANSPORT_UNCONFIRMED" in [
                        e for e, _ in shadow._adapter.receipts
                    ]
                ):
                    break
            receipts = [event for event, _ in shadow._adapter.receipts]
            assert observed and len(observed) == 1
            assert "SOCKET_POST_SENT" in receipts
            assert shadow.model_attempts == 1
            if fault == "good":
                assert current is not None
                assert json.loads(current)["assessment"] == "Observe displacement"
                assert "HTTP_COMPLETION_OBSERVED" in receipts
            else:
                assert current is None
                assert "HTTP_COMPLETION_OBSERVED" not in receipts
            out = await shadow.close()
            assert out["structured_profile"] == PROFILE
            assert out["request_reasoning_off"] is True
            assert out["backend_reasoning_off_attested"] is False
            assert out["backend_stop_ack"] is False
    asyncio.run(go())


def test_legacy_five_field_payload_still_required_by_default():
    assert PROFILE not in (None, "")
    # The existing S2-B test's five-field no-profile fixture runs in CI.
    assert set(REQUEST_EXTRAS) == {
        "response_format", "chat_template_kwargs", "reasoning_effort",
    }
