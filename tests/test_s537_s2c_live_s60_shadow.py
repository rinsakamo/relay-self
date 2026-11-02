"""S2-C offline tests. The HTTP peer, owner source and S49 are SYNTHETIC.

Tests actual existing S60-A/S60-B1 without Minecraft or real Gemma.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.normal_action import _READ_ONLY_CLOSURE, NormalWorldL0
from adapters.mineflayer.s49_completed_decision_bridge import (
    bounded_original_s49_completion_row,
)
from adapters.mineflayer.s60b1_loopback_adapter import LoopbackTransportConfig
from adapters.mineflayer.s537_s2b_gated_l2_shadow import (
    S2BGatedL2Shadow,
    S2BSourceRejected,
)
from relay_self.intent import IntentCommitment
from relay_self.interruption_fence import CognitionContext
from relay_self.provenance import Provenance
from test_s49_owner_cognition_crosslane import _load_pinned
from test_s537_s2a_source_bound_read_port import (
    _closure,
    _realistic_synthetic_batch,
)
from test_s537_s2b_gated_l2_shadow import _input, _read
from tools.s537_s2c_live_s60_shadow_dev import (
    S2CAsyncObserver,
    main,
    run_s2c_live_shadow_dev,
)


@pytest.fixture
def pinned_owners(monkeypatch):
    m = _load_pinned(
        monkeypatch, "experiments.metabolism_s49_owner_admission",
        "S0_PINNED_M_SOURCE",
    )
    wb = _load_pinned(
        monkeypatch, "relay_self.self_cognition_slice",
        "S1_PINNED_WB_SOURCE",
    )
    return m, wb


def _original_owners(batch):
    from test_postmain_s42_world_contrast import _pair

    retained, *_ = _pair()
    host = NormalWorldL0(
        batch.session_id, "escape-threat", retained,
        max_events=3, max_action_requests=2,
    )
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="escape near zombie", at_ns=1,
        provenance=Provenance("synthetic", "fixture-original-owner"),
    )
    return host, intent


def _config(port):
    return LoopbackTransportConfig(
        "fixture-model", port, slots=1, max_tokens=64,
        connect_s=.5, read_s=1, whole_s=1,
    )


def test_model_call_uses_original_prior_s16_but_original_s49_never_awaits(
    pinned_owners, tmp_path,
):
    batch = _realistic_synthetic_batch()
    host, intent = _original_owners(batch)
    exchanges = []
    gate = asyncio.Event()

    async def peer(reader, writer):
        try:
            raw = await reader.readuntil(b"\r\n\r\n")
            length = next(
                int(line.split(b":", 1)[1])
                for line in raw.split(b"\r\n")
                if line.lower().startswith(b"content-length:")
            )
            payload = json.loads((await reader.readexactly(length)).decode())
            source = json.loads(payload["messages"][1]["content"])
            exchanges.append(source)
            assert source["original_owner"]["intent_id"] == "escape-threat"
            assert source["original_owner"]["intent_event_generation"] == 1
            assert source["original_owner"]["retained_revision"] == 1
            assert source["current_wb_l1_and_previous_s16"]["preceding_action_id"]
            await gate.wait()
        finally:
            writer.close()

    async def fake_qualify(
        path, log, *, live_probe, completed_l0, completed_l0_dev,
        owner_epoch_readonly,
    ):
        assert completed_l0_dev is True
        first, second = (entry.probe for entry in batch.steps)
        owner_epoch_readonly(first, host, intent)
        await live_probe(first)
        callback = _READ_ONLY_CLOSURE.get()
        assert callback is not None
        callback(_closure(batch))
        owner_epoch_readonly(second, host, intent)
        await live_probe(second)
        # Continue original World independently of a stalled provider.
        await asyncio.sleep(.08)
        assert not gate.is_set()
        completed_l0(batch)
        row = bounded_original_s49_completion_row(batch)
        path.write_text(json.dumps({
            "status": "PASS", "session_id": batch.session_id,
            "original_completion_observer": "CALLBACK_RETURNED",
            "original_completion_readback": row,
            "source_pair_trace": [{
                "event_seq": d["event_seq"], "probe_seq": d["probe_seq"],
            } for d in row["decisions"]],
        }))
        return 0

    async def go():
        server = await asyncio.start_server(peer, "127.0.0.1", 0)
        async with server:
            port = server.sockets[0].getsockname()[1]
            observer = S2CAsyncObserver(_config(port), timeout_s=.6)
            code, result = await run_s2c_live_shadow_dev(
                original_qualify=fake_qualify,
                report_path=tmp_path / "s49.json",
                server_log=tmp_path / "server.log",
                observer=observer,
            )
            gate.set()
            assert code == 0
            assert result["source_join_status"] == "RECORDED"
            assert result["status"] == "DEFERRED"  # no later S16 in 2-step fixture
            assert result["s60_submissions"] == 1
            assert result["s60"]["l0_awaited_provider"] is False
            assert result["s60"]["original_s16_invalidations"] == 0
            assert result["s60"]["backend_stop_ack"] is False
            assert result["s60"]["gpu_release_verified"] is False
            assert result["s2a"]["with_previous_s16"] == 1
            assert len(exchanges) == 1
    asyncio.run(go())


def test_original_s16_after_current_epoch_invalidates_s60_owner():
    async def go():
        shadow = S2BGatedL2Shadow(
            enabled=True, config=_config(19093), timeout_s=.6,
        )
        src = _input()
        shadow.observe(src, owner_read=_read(src))
        assert shadow.model_attempts == 1
        batch = _realistic_synthetic_batch()
        closed = _closure(batch)
        new_probe = replace(
            closed.original_probe,
            session_id=src.session_id, seq=src.probe_seq,
            request_id=src.request_id,
        )
        new_con = replace(
            closed.consequence,
            after_observation=replace(
                closed.consequence.after_observation,
                session_id=src.session_id, seq=60,
            ),
        )
        closed = replace(closed, original_probe=new_probe, consequence=new_con)
        with pytest.raises(S2BSourceRejected):
            shadow.invalidate_on_original_s16(
                closed, new_context=CognitionContext(src.session_id, 59, 1, 1),
            )
        shadow.invalidate_on_original_s16(
            closed, new_context=CognitionContext(src.session_id, 60, 1, 1),
        )
        assert shadow.status == "EXPIRED_ORIGINAL_S16_WORLD_ADVANCED"
        assert shadow._current is False
        assert "DISPLACED" in [event.event for event in shadow._owner.receipts]
        out = await shadow.close()
        assert out["accepted_advisory_current"] is False
        assert out["backend_stop_ack"] is False
        assert out["model_attempts"] == 1
    asyncio.run(go())


def test_runner_default_off_blocks_before_any_world(monkeypatch, capsys):
    import sys

    monkeypatch.delenv("S537_S2C_LIVE_L2_DEV_ONLY", raising=False)
    monkeypatch.setattr(sys, "argv", [
        "s2c",
        "--m-owner-dir", "/missing/m", "--wb-owner-dir", "/missing/wb",
        "--report", "/tmp/s2c-out.json", "--server-log", "/tmp/s2c-server.log",
        "--s2c-report", "/tmp/s2c-report.json",
        "--model-alias", "fixture", "--model-port", "19431",
    ])
    assert main() == 2
    assert '"BLOCKED"' in capsys.readouterr().out
