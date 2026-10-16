"""L-CF4: original S60 transport bytes -> opt-in metered evidence candidate.

All HTTP peers are ephemeral local Python fixtures. No Minecraft, GPU, LLM,
World Action, R qualification, or real provider-cost experiment.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from hashlib import sha256

import pytest

from adapters.mineflayer.s60b1_loopback_adapter import (
    LoopbackDisplacementAdapter,
    LoopbackTransportConfig,
    TransportUnconfirmed,
)
from relay_self.best_effort_displacement import BestEffortDisplacement
from relay_self.cognitive_fatigue import (
    CognitiveFatigueRejected,
    FatigueProfile,
    FatigueState,
    NonL2Interval,
    recover_idle,
)
from relay_self.cognitive_fatigue_s60 import (
    S60FatigueRejected,
    make_s60_adapter,
    plan_s60_l2,
    reserve_s60_l2,
)
from relay_self.cognitive_fatigue_s60_meter import MeteredS60Adapter
from relay_self.interruption_fence import CognitionContext
from relay_self.provenance import Provenance
from test_feature_s60b1_adapter import FakeHTTP, envelope, response


SOURCE = Provenance("admission", "source-cf4")
CONTEXT = CognitionContext("cf4-session", 3, 1, 1)
SOURCE_HASH = "a" * 64


def make_profile(mode="NONLINEAR", initial=0.7):
    profile = FatigueProfile(mode=mode, initial_fatigue=initial)
    return profile, FatigueState.genesis(profile, CONTEXT.session_id, 0)


def make_rig(server, p, state):
    base = LoopbackTransportConfig("offline-model", server.port, max_tokens=96)
    plan = plan_s60_l2(p, state, base)
    def payload(request):
        return {
            "model": plan.transport.model,
            "messages": [{"role": "user", "content": "private prompt content"}],
            "temperature": 0, "max_tokens": plan.max_output_tokens,
            "stream": False,
        }
    adapter = make_s60_adapter(plan, payload)
    owner = BestEffortDisplacement(
        CONTEXT, "admission", adapter.start, adapter.cancel, lambda: 1.0,
    )
    adapter.bind(owner)
    return plan, owner, adapter


def issue(p, state, plan, owner):
    req = owner.admit(CONTEXT, "L2", 1, 20, 10, SOURCE)
    reserved = reserve_s60_l2(
        p, state, plan, req, at_ns=1_000_000_000,
        source_receipt_sha256=SOURCE_HASH,
    )
    owner.submit(req)
    return req, reserved


def test_off_preserves_original_unmetered_transport_and_no_extra_requirement():
    async def scenario():
        async with FakeHTTP() as server:
            p, state = make_profile(mode="OFF")
            plan, owner, adapter = make_rig(server, p, state)
            assert not plan.enabled
            assert type(adapter) is LoopbackDisplacementAdapter
            assert not isinstance(adapter, MeteredS60Adapter)
            assert plan.transport is plan.original
            assert not hasattr(adapter, "metered_completion")
            await adapter.aclose()
    asyncio.run(scenario())


def test_on_real_s60_post_has_exact_budget_and_captures_original_digests():
    async def scenario():
        async with FakeHTTP() as server:
            raw = response()
            server.responses = [raw]
            p, state = make_profile()
            plan, owner, adapter = make_rig(server, p, state)
            assert type(adapter) is MeteredS60Adapter
            assert not plan.action_authority
            assert adapter.metered_completion is None
            req, reserved = issue(p, state, plan, owner)
            assert await server.next_post() == 0
            assert adapter.metered_completion is None
            sent = server.posts[0][1]
            assert sent["max_tokens"] == plan.max_output_tokens
            assert 1 <= sent["max_tokens"] < 96
            server.release[0].set()
            await asyncio.wait_for(adapter._attempt.task, 2)
            result = owner.tick()
            assert result is not None
            assert result.request is req and result.value == "transient-output"
            meter = adapter.metered_completion
            assert meter is not None and meter is adapter.metered_completion
            assert meter.work_id == req.work_id
            assert meter.generation == req.generation
            assert meter.session_id == CONTEXT.session_id
            assert meter.world_seq == CONTEXT.world_seq
            assert meter.max_output_tokens == plan.max_output_tokens
            assert (meter.prompt_tokens, meter.completion_tokens, meter.total_tokens) == (10, 3, 13)
            # Only the raw HTTP JSON *body*, not HTTP headers, is hashed.
            raw_body = json.dumps(envelope()).encode()
            assert meter.response_sha256 == sha256(raw_body).hexdigest()
            assert meter.request_sha256 == sha256(
                json.dumps(sent, ensure_ascii=False, allow_nan=False).encode()
            ).hexdigest()
            assert not meter.externally_qualified
            assert not meter.backend_stop_ack
            assert not meter.action_authority
            assert "private prompt content" not in repr(meter)
            assert "transient-output" not in repr(meter)
            # A transport candidate does NOT itself settle evaluator F_c.
            assert reserved.active_work_id == req.work_id
            with pytest.raises(CognitiveFatigueRejected):
                recover_idle(p, reserved, NonL2Interval(
                    CONTEXT.session_id, reserved.seq + 1,
                    reserved.last_ns, 2_000_000_000, SOURCE_HASH,
                ))
            await adapter.aclose()
    asyncio.run(scenario())


@pytest.mark.parametrize("problem", [
    "missing_usage", "missing_total", "wrong_sum", "bool_token",
    "completion_exceeds_budget", "missing_finish", "bad_usage_type",
])
def test_unmetered_or_invalid_http_completion_never_yields_a_candidate(problem):
    async def scenario():
        async with FakeHTTP() as server:
            raw = envelope()
            if problem == "missing_usage":
                raw.pop("usage")
            elif problem == "missing_total":
                raw["usage"].pop("total_tokens")
            elif problem == "wrong_sum":
                raw["usage"]["total_tokens"] += 4
            elif problem == "bool_token":
                raw["usage"]["completion_tokens"] = True
            elif problem == "completion_exceeds_budget":
                raw["usage"]["completion_tokens"] = 1000
            elif problem == "missing_finish":
                raw["choices"][0].pop("finish_reason")
            elif problem == "bad_usage_type":
                raw["usage"] = None
            server.responses = [response(json.dumps(raw).encode())]
            p, state = make_profile()
            plan, owner, adapter = make_rig(server, p, state)
            req, reserved = issue(p, state, plan, owner)
            await server.next_post()
            server.release[0].set()
            await asyncio.wait_for(adapter._attempt.task, 2)
            assert adapter.metered_completion is None
            assert owner.tick() is None
            assert reserved.active_work_id == req.work_id
            with pytest.raises(S60FatigueRejected):
                plan_s60_l2(p, reserved, plan.original)
            await adapter.aclose()
    asyncio.run(scenario())


def test_host_cancel_then_backend_may_continue_but_cost_does_not_disappear():
    async def scenario():
        async with FakeHTTP() as server:
            server.responses = [response()]
            p, state = make_profile()
            plan, owner, adapter = make_rig(server, p, state)
            req, reserved = issue(p, state, plan, owner)
            assert await server.next_post() == 0
            owner.observe(replace(CONTEXT, world_seq=CONTEXT.world_seq + 1))
            assert "DISPLACED" in [e.event for e in owner.receipts]
            assert adapter.metered_completion is None
            server.release[0].set()
            await asyncio.wait_for(adapter._attempt.task, 2)
            assert adapter.metered_completion is None
            assert reserved.active_work_id == req.work_id
            assert owner.tick() is None
            with pytest.raises(CognitiveFatigueRejected):
                recover_idle(p, reserved, NonL2Interval(
                    CONTEXT.session_id, reserved.seq + 1,
                    reserved.last_ns, 4_000_000_000, SOURCE_HASH,
                ))
            await adapter.aclose()
    asyncio.run(scenario())


def test_repeated_candidate_read_cannot_be_used_as_a_terminal_receipt():
    async def scenario():
        async with FakeHTTP() as server:
            server.responses = [response()]
            p, state = make_profile()
            plan, owner, adapter = make_rig(server, p, state)
            req, reserved = issue(p, state, plan, owner)
            await server.next_post()
            server.release[0].set()
            await asyncio.wait_for(adapter._attempt.task, 2)
            first = adapter.metered_completion
            assert first is not None
            assert adapter.metered_completion == first
            assert first.status == "HTTP_COMPLETION_METER_CANDIDATE"
            assert not first.externally_qualified
            assert reserved.active_work_id == req.work_id
            with pytest.raises(S60FatigueRejected):
                plan_s60_l2(p, reserved, plan.original)
            await adapter.aclose()
    asyncio.run(scenario())
