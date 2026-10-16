"""L-CF3 deterministic S60-B1 budget/receipt tests; no backend or World."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.s60b1_loopback_adapter import (
    LoopbackTransportConfig,
    TransportUnconfirmed,
)
from relay_self.best_effort_displacement import BestEffortDisplacement, ModelRequest
from relay_self.cognitive_fatigue import (
    CognitiveFatigueRejected,
    FatigueProfile,
    FatigueState,
    NonL2Interval,
    budget_for_l2,
    recover_idle,
)
from relay_self.cognitive_fatigue_s60 import (
    S60ExternalUsage,
    S60FatigueRejected,
    bind_s60_payload,
    make_s60_adapter,
    plan_s60_l2,
    reserve_s60_l2,
    settle_s60_l2,
)
from relay_self.interruption_fence import CognitionContext
from relay_self.provenance import Provenance
from relay_self.relay_engine import ProviderCallFacts

BASE = LoopbackTransportConfig("gemma-test", 15671, max_tokens=96)
SHA = "a" * 64


def request(session="session-a", work="s60-1", level="L2", generation=1):
    return ModelRequest(
        work, generation, CognitionContext(session, 1, 1, 1),
        level, 1, 100.0, 10.0, Provenance("l-cf3-test", "probe-1"),
    )


def payload(req, cap):
    return {
        "model": BASE.model,
        "messages": [{"role": "user", "content": "bounded thought"}],
        "temperature": 0,
        "max_tokens": cap,
        "stream": False,
    }


def fixture(mode="NONLINEAR", initial=0.7):
    profile = FatigueProfile(mode=mode, initial_fatigue=initial)
    state = FatigueState.genesis(profile, "session-a", 0)
    return profile, state


def test_off_keeps_exact_s60_transport_and_original_request_cap():
    p, s = fixture("OFF", 0.8)
    plan = plan_s60_l2(p, s, BASE)
    assert plan.transport is BASE
    assert plan.max_output_tokens == 96
    assert plan.action_authority is False


def test_linear_nonlinear_and_fixed_apply_real_s60_config_bounds():
    p, s = fixture("NONLINEAR")
    cap = plan_s60_l2(p, s, BASE).transport.max_tokens
    lin = replace(p, mode="LINEAR")
    fixed = replace(p, mode="FIXED", fixed_max_tokens=27)
    assert 1 <= cap < plan_s60_l2(lin, FatigueState.genesis(lin, "session-a", 0), BASE).max_output_tokens
    assert plan_s60_l2(fixed, FatigueState.genesis(fixed, "session-a", 0), BASE).max_output_tokens == 27
    assert cap == budget_for_l2(p, s, BASE.max_tokens).max_output_tokens
    assert BASE.max_tokens == 96


def test_adapter_uses_actual_bounded_s60_payload_no_other_provider():
    p, s = fixture()
    plan = plan_s60_l2(p, s, BASE)
    async def trial():
        adapter = make_s60_adapter(
            plan, lambda req: payload(req, plan.max_output_tokens),
        )
        raw = adapter._payload(request())
        assert raw and str(plan.max_output_tokens).encode() in raw
        assert adapter.config.max_tokens == plan.max_output_tokens
        assert adapter.transport_tasks == 0
    asyncio.run(trial())


def test_payload_over_under_foreign_level_and_session_fail_before_http():
    p, s = fixture()
    plan = plan_s60_l2(p, s, BASE)
    async def corrected():
        adapter = make_s60_adapter(plan, lambda req: payload(req, plan.max_output_tokens + 1))
        with pytest.raises(TransportUnconfirmed):
            adapter._payload(request())
        bounded = bind_s60_payload(plan, lambda req: payload(req, plan.max_output_tokens))
        with pytest.raises(S60FatigueRejected):
            bounded(request(session="foreign"))
        with pytest.raises(S60FatigueRejected):
            bounded(request(level="L1"))
        assert bounded(request())["max_tokens"] == plan.max_output_tokens
    asyncio.run(corrected())


def test_reserve_requires_matching_issued_S60_identity_and_replay_refused():
    p, s = fixture()
    plan = plan_s60_l2(p, s, BASE)
    started = reserve_s60_l2(
        p, s, plan, request(), at_ns=10, source_receipt_sha256=SHA,
    )
    assert started.active_work_id == "s60-1"
    assert started.active_max_tokens == plan.max_output_tokens
    with pytest.raises(S60FatigueRejected):
        plan_s60_l2(p, started, BASE)
    with pytest.raises(S60FatigueRejected):
        reserve_s60_l2(p, started, plan, request(), at_ns=11, source_receipt_sha256=SHA)
    with pytest.raises(S60FatigueRejected):
        reserve_s60_l2(p, s, plan, request("other"), at_ns=10, source_receipt_sha256=SHA)


def test_cancellation_or_timeout_does_not_generate_free_terminal_or_idle():
    p, s = fixture()
    plan = plan_s60_l2(p, s, BASE)
    active = reserve_s60_l2(p, s, plan, request(), at_ns=10, source_receipt_sha256=SHA)
    with pytest.raises(S60FatigueRejected):
        settle_s60_l2(p, active, None, at_ns=100)
    with pytest.raises(CognitiveFatigueRejected):
        recover_idle(
            p, active,
            NonL2Interval("session-a", active.seq + 1, 10, 1000000000, SHA),
        )
    with pytest.raises(S60FatigueRejected):
        plan_s60_l2(p, active, BASE)


def test_synthetic_terminal_facts_are_source_shaped_not_authentication():
    p, s = fixture()
    plan = plan_s60_l2(p, s, BASE)
    active = reserve_s60_l2(p, s, plan, request(), at_ns=10, source_receipt_sha256=SHA)
    facts = ProviderCallFacts(
        plan.max_output_tokens, 120, 10, 130, "stop",
    )
    claim = S60ExternalUsage("session-a", "s60-1", "b"*64,
                              "VERIFIED_NATURAL_COMPLETION", facts)
    done = settle_s60_l2(p, active, claim, at_ns=1000)
    assert done.total_metered_tokens == 130
    assert done.active_work_id is None and done.fatigue > active.fatigue
    with pytest.raises(CognitiveFatigueRejected):
        settle_s60_l2(p, done, claim, at_ns=2000)


@pytest.mark.parametrize("broken", [
    {"total_tokens": 2}, {"completion_tokens": None},
    {"requested_max_output_tokens": 97},
    {"completion_tokens": 97, "total_tokens": 217},
])
def test_missing_or_mismatched_terminal_meter_rejected(broken):
    p, s = fixture()
    plan = plan_s60_l2(p, s, BASE)
    active = reserve_s60_l2(p, s, plan, request(), at_ns=10, source_receipt_sha256=SHA)
    facts = dict(requested_max_output_tokens=plan.max_output_tokens,
                 prompt_tokens=120, completion_tokens=10, total_tokens=130,
                 finish_reason="stop")
    facts.update(broken)
    claim = S60ExternalUsage("session-a", "s60-1", "b"*64,
                              "VERIFIED_NATURAL_COMPLETION", ProviderCallFacts(**facts))
    with pytest.raises(S60FatigueRejected):
        settle_s60_l2(p, active, claim, at_ns=1000)


def test_l0_owner_remains_completely_outside_l2_gate():
    p, s = fixture(initial=0.99)
    with pytest.raises(S60FatigueRejected):
        plan_s60_l2(p, s, BASE)
    assert s.blocked
    # L2 gating never returns a grant and does not even receive an L0 request.
    assert plan_s60_l2(FatigueProfile(mode="OFF"),
                       FatigueState.genesis(FatigueProfile(mode="OFF"), "session-a", 0),
                       BASE).action_authority is False

def test_off_legacy_supplier_can_use_smaller_output_than_ceiling():
    p, s = fixture("OFF")
    plan = plan_s60_l2(p, s, BASE)
    async def run():
        adapter = make_s60_adapter(plan, lambda req: payload(req, 32))
        assert b'"max_tokens": 32' in adapter._payload(request())
        assert adapter.config is BASE
    asyncio.run(run())

def test_off_requires_no_extra_fatigue_reservation_or_effect():
    p, s = fixture("OFF")
    plan = plan_s60_l2(p, s, BASE)
    with pytest.raises(S60FatigueRejected):
        reserve_s60_l2(p, s, plan, request(), at_ns=10, source_receipt_sha256=SHA)


def test_natural_completion_without_finish_reason_cannot_settle():
    p, s = fixture()
    plan = plan_s60_l2(p, s, BASE)
    active = reserve_s60_l2(p, s, plan, request(), at_ns=10, source_receipt_sha256=SHA)
    facts = ProviderCallFacts(plan.max_output_tokens, 20, 5, 25, None)
    claim = S60ExternalUsage("session-a", "s60-1", "c" * 64,
                             "VERIFIED_NATURAL_COMPLETION", facts)
    with pytest.raises(S60FatigueRejected):
        settle_s60_l2(p, active, claim, at_ns=1000)


def test_actual_existing_s60_loopback_http_request_uses_l_cf_cap():
    """Offline fake provider: exercise S60 owner submit -> original HTTP POST."""
    async def trial():
        seen = []

        async def fake_provider(reader, writer):
            try:
                header = await reader.readuntil(b"\r\n\r\n")
                length = next(
                    int(line.partition(b":")[2])
                    for line in header.split(b"\r\n")
                    if line.startswith(b"Content-Length:")
                )
                request_body = json.loads(await reader.readexactly(length))
                seen.append(request_body)
                body = json.dumps({
                    "model": BASE.model,
                    "choices": [{
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "non-authorizing"},
                    }],
                    "usage": {
                        "prompt_tokens": 14,
                        "completion_tokens": 3,
                        "total_tokens": 17,
                    },
                }).encode()
                writer.write(
                    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                    + f"Content-Length: {len(body)}\r\n".encode()
                    + b"Connection: close\r\n\r\n" + body
                )
                await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()

        server = await asyncio.start_server(fake_provider, "127.0.0.1", 0)
        async with server:
            port = server.sockets[0].getsockname()[1]
            base = replace(BASE, port=port)
            p, state = fixture()
            plan = plan_s60_l2(p, state, base)
            adapter = make_s60_adapter(
                plan, lambda req: payload(req, plan.max_output_tokens),
            )
            context = CognitionContext("session-a", 1, 1, 1)
            owner = BestEffortDisplacement(
                context, "l-cf3-test", adapter.start, adapter.cancel, lambda: 1.0,
            )
            adapter.bind(owner)
            task = owner.admit(
                context, "L2", 1, 20.0, 5.0,
                Provenance("l-cf3-test", "probe-1"),
            )
            reserved = reserve_s60_l2(
                p, state, plan, task, at_ns=1_000_000_000,
                source_receipt_sha256=SHA,
            )
            owner.submit(task)
            await asyncio.wait_for(adapter._attempt.task, 2)
            result = owner.tick()
            assert result is not None
            assert result.request is task
            assert result.value == "non-authorizing"
            assert len(seen) == 1
            assert seen[0]["max_tokens"] == plan.max_output_tokens
            assert 1 <= seen[0]["max_tokens"] < base.max_tokens
            # Original S60 exposes text, not attested usage; never infer free
            # completion or cognitive idle from response alone.
            assert reserved.active_work_id == task.work_id
            with pytest.raises(CognitiveFatigueRejected):
                recover_idle(
                    p, reserved,
                    NonL2Interval("session-a", reserved.seq + 1,
                                  reserved.last_ns, 3_000_000_000, SHA),
                )
            await adapter.aclose()
    asyncio.run(trial())
