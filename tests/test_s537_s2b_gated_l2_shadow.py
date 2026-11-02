"""S2-B offline source gate uses a local FAKE HTTP peer, never real Gemma.

This tests the existing S60-A and S60-B1 implementation, not World success,
model identity, reasoning quality, real S49 revision access or GPU release.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.s60b1_loopback_adapter import LoopbackTransportConfig
from adapters.mineflayer.s537_s2a_l2_read_port import S2AReadOnlyInput
from adapters.mineflayer.s537_s2b_gated_l2_shadow import (
    S2BGatedL2Shadow,
    S2BOwnerContextRead,
    S2BSourceRejected,
)
from relay_self.interruption_fence import CognitionContext


def _input(seq=51, prev=True):
    sid = "synthetic-S2B-session"
    rid = f"s49-actual:{sid}:event-{seq-1}"
    return S2AReadOnlyInput(
        self_id="self-s537-s1-native", session_id=sid, epoch_id=f"native-{seq}",
        probe_seq=seq, request_id=rid,
        world_source_ref=f"present:{sid}:{seq}:{rid}",
        body_source_ref=f"native-probe:{sid}:{seq}:{rid}",
        observed_world=(("entity-5", "zombie", 2.5),),
        observed_body=(("health", 20), ("food", 18)),
        preceding_action_id="s49-native-move-20" if prev else None,
        preceding_s16_after_seq=29 if prev else None,
        preceding_action_source_probe_seq=21 if prev else None,
    )


def _read(source):
    # EXPLICITLY SYNTHETIC. Not proof of a real S49 owner context.
    return S2BOwnerContextRead(
        source_input=source,
        context=CognitionContext(source.session_id, source.probe_seq, 1, 1),
        intent_id="escape-threat",
        owner_scope="ORIGINAL_S49_L0_AND_INTENT_READ_ONLY",
    )


def _shadow(port):
    return S2BGatedL2Shadow(
        enabled=True, config=LoopbackTransportConfig(
            "fixture-model", port, slots=1, max_tokens=64,
            connect_s=0.3, read_s=1, whole_s=1,
        ), timeout_s=1,
    )


def test_missing_original_revision_must_defer_without_model():
    async def go():
        shadow = _shadow(19092)
        src = _input()
        shadow.observe(src)
        assert shadow.model_attempts == 0
        assert shadow.status == "DEFERRED_ORIGINAL_OWNER_REVISION_UNAVAILABLE"
        assert (await shadow.close())["backend_stop_ack"] is False
    asyncio.run(go())


@pytest.mark.parametrize("kind", [
    "foreign", "future_s16", "replay", "bad_world_ref",
    "wrong_ctx", "missing_owner", "bad_owner_scope",
])
def test_wrong_source_or_missing_owner_never_starts_transport(kind):
    async def go():
        shadow = _shadow(19092)
        src = _input()
        if kind == "foreign":
            src = replace(src, session_id="foreign")
        if kind == "future_s16":
            src = replace(src, preceding_s16_after_seq=src.probe_seq + 1)
        if kind == "bad_world_ref":
            src = replace(src, world_source_ref="unknown")
        if kind == "wrong_ctx":
            with pytest.raises(S2BSourceRejected):
                S2BOwnerContextRead(
                    src,
                    CognitionContext(src.session_id, src.probe_seq - 1, 1, 1),
                    "escape-threat", "ORIGINAL_S49_L0_AND_INTENT_READ_ONLY",
                )
        if kind == "bad_owner_scope":
            with pytest.raises(S2BSourceRejected):
                S2BOwnerContextRead(
                    src,
                    CognitionContext(src.session_id, src.probe_seq, 1, 1),
                    "escape-threat", "synthetic",
                )
        if kind in ("foreign", "future_s16", "bad_world_ref"):
            with pytest.raises(S2BSourceRejected):
                shadow.observe(src)
        else:
            shadow.observe(src)
            if kind == "replay":
                with pytest.raises(S2BSourceRejected):
                    shadow.observe(src)
        assert shadow.model_attempts == 0
        await shadow.close()
    asyncio.run(go())


def test_bounded_config_requires_opt_in_and_no_large_output():
    cfg = LoopbackTransportConfig("fixture-model", 19092)
    with pytest.raises(S2BSourceRejected):
        S2BGatedL2Shadow(config=cfg)
    with pytest.raises(S2BSourceRejected):
        S2BGatedL2Shadow(enabled=True, config=cfg)


def test_s60_owned_loopback_single_model_advisory_only():
    async def peer(reader, writer):
        try:
            raw = await reader.readuntil(b"\r\n\r\n")
            length = next(
                int(line.split(b":", 1)[1])
                for line in raw.split(b"\r\n")
                if line.lower().startswith(b"content-length:")
            )
            payload = json.loads((await reader.readexactly(length)).decode())
            assert payload["messages"][1]["role"] == "user"
            assert "preceding_action_id" in payload["messages"][1]["content"]
            assert payload["max_tokens"] == 64
            answer = json.dumps({
                "model": "fixture-model",
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": "Uncertain displacement."},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13},
            }).encode()
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                + f"Content-Length: {len(answer)}\r\nConnection: close\r\n\r\n".encode()
                + answer
            )
            await writer.drain()
        finally:
            writer.close()

    async def go():
        server = await asyncio.start_server(peer, "127.0.0.1", 0)
        async with server:
            port = server.sockets[0].getsockname()[1]
            shadow = _shadow(port)
            src = _input()
            shadow.observe(src, owner_read=_read(src))
            assert shadow.model_attempts == 1
            assert shadow.poll() is None
            for _ in range(100):
                await asyncio.sleep(.01)
                text = shadow.poll()
                if text is not None:
                    break
            else:
                raise AssertionError("fixture S60 backend not observed")
            assert text == "Uncertain displacement."
            assert shadow.status == "ADVISORY_CURRENT_READ_ONLY"
            next_src = _input(60)
            shadow.observe(next_src, owner_read=_read(next_src))
            assert shadow.status == "EXPIRED_WORLD_ADVANCED"
            assert shadow.model_attempts == 1
            report = await shadow.close()
            assert "BACKEND_COMPLETION_OBSERVED" in report["owner_events"]
            assert "HTTP_COMPLETION_OBSERVED" in report["transport_events"]
            assert not report["source_attested"]
            assert not report["backend_stop_ack"]
            assert not report["gpu_release_verified"]
            assert not report["action_authority"]
            assert report["qualification"] == "NO_GO"
    asyncio.run(go())
