"""L-CF3: opt-in budget bridge to the existing S60-B1 transport.

No inference worker, World Action, token extraction from text, or authority to
manufacture a provider-stop receipt. The L side projects a strict HTTP cap;
S/R must independently attest actual usage before terminal accounting.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Any

from adapters.mineflayer.s60b1_loopback_adapter import (
    LoopbackDisplacementAdapter,
    LoopbackTransportConfig,
)
from relay_self.best_effort_displacement import ModelRequest
from relay_self.cognitive_fatigue import (
    CognitiveFatigueRejected,
    FatigueProfile,
    FatigueState,
    L2Start,
    L2Usage,
    account_l2,
    begin_l2,
    budget_for_l2,
)
from relay_self.relay_engine import ProviderCallFacts


class S60FatigueRejected(CognitiveFatigueRejected):
    """Unqualified L2 work, invalid source identity or token budget."""


@dataclass(frozen=True, slots=True)
class S60FatiguePlan:
    session_id: str
    state_sha256: str
    profile_sha256: str
    original: LoopbackTransportConfig
    transport: LoopbackTransportConfig
    max_output_tokens: int
    enabled: bool
    action_authority: bool = False


def plan_s60_l2(
    profile: FatigueProfile, state: FatigueState,
    base: LoopbackTransportConfig,
) -> S60FatiguePlan:
    """Project evaluator-side F_c onto S60-B1's *actual* HTTP output ceiling."""
    if not isinstance(base, LoopbackTransportConfig):
        raise S60FatigueRejected("existing S60-B1 config required")
    budget = budget_for_l2(profile, state, base.max_tokens)
    if not budget.admitted or budget.max_output_tokens is None:
        raise S60FatigueRejected("L2 blocked by fatigue or outstanding work")
    # OFF retains the exact original object and its request semantics.
    transport = base if profile.mode == "OFF" else replace(
        base, max_tokens=budget.max_output_tokens,
    )
    return S60FatiguePlan(
        state.session_id, state.state_sha256, profile.sha256, base,
        transport, budget.max_output_tokens, profile.mode != "OFF",
    )


def bind_s60_payload(
    plan: S60FatiguePlan,
    supplier: Callable[[ModelRequest], Mapping[str, Any]],
) -> Callable[[ModelRequest], Mapping[str, Any]]:
    """Refuse over/under cap before S60 serializes and sends the payload."""
    if not isinstance(plan, S60FatiguePlan) or not callable(supplier):
        raise S60FatigueRejected("typed bound S60 plan and payload required")

    if not plan.enabled:
        # OFF is byte-for-byte legacy supplier contract: S60 alone validates
        # any positive caller ceiling <= its original configured maximum.
        return supplier

    def bounded(request: ModelRequest) -> Mapping[str, Any]:
        if (
            not isinstance(request, ModelRequest)
            or request.level != "L2"
            or request.context.session_id != plan.session_id
        ):
            raise S60FatigueRejected("foreign S60 session or cognition level")
        payload = supplier(request)
        if (
            not isinstance(payload, Mapping)
            or type(payload.get("max_tokens")) is not int
            or payload["max_tokens"] != plan.max_output_tokens
        ):
            raise S60FatigueRejected("S60 request max_tokens must equal fatigue cap")
        return payload

    return bounded


def make_s60_adapter(
    plan: S60FatiguePlan,
    supplier: Callable[[ModelRequest], Mapping[str, Any]],
) -> LoopbackDisplacementAdapter:
    """Reuse the original S60 transport and its S-owned verification."""
    bounded = bind_s60_payload(plan, supplier)
    if plan.enabled:
        from relay_self.cognitive_fatigue_s60_meter import MeteredS60Adapter
        return MeteredS60Adapter(plan.transport, bounded)
    return LoopbackDisplacementAdapter(plan.transport, bounded)


def reserve_s60_l2(
    profile: FatigueProfile, state: FatigueState,
    plan: S60FatiguePlan, request: ModelRequest,
    *, at_ns: int, source_receipt_sha256: str,
) -> FatigueState:
    """Reserve before S60 submit and atomically checkpoint via S owner.

    If the provider fails to start, do NOT treat this reservation as idle.
    Request identity is still an S-owner claim; L cannot authenticate it.
    """
    if profile.mode == "OFF":
        raise S60FatigueRejected("OFF uses existing S60 flow without fatigue reservation")
    if (
        not isinstance(plan, S60FatiguePlan)
        or plan != plan_s60_l2(profile, state, plan.original)
        or not isinstance(request, ModelRequest)
        or request.level != "L2"
        or request.context.session_id != state.session_id
        or type(request.generation) is not int
        or request.generation < 1
        or not request.work_id
    ):
        raise S60FatigueRejected("stale plan or foreign S60 L2 request")
    return begin_l2(
        profile, state,
        L2Start(
            state.session_id, request.work_id, state.seq + 1, at_ns,
            source_receipt_sha256, plan.max_output_tokens,
        ),
        plan.original.max_tokens,
    )


@dataclass(frozen=True, slots=True)
class S60ExternalUsage:
    """Claimed verified S/R source, NOT authenticated by this L-side type."""
    session_id: str
    work_id: str
    source_receipt_sha256: str
    source_status: str  # VERIFIED_NATURAL_COMPLETION / VERIFIED_BACKEND_STOP
    provider_facts: ProviderCallFacts


def settle_s60_l2(
    profile: FatigueProfile, state: FatigueState,
    usage: S60ExternalUsage, *, at_ns: int,
) -> FatigueState:
    """Explicit S/R attested terminal meter only; no inference from text.

    The current S60-B1 adapter returns text, not token usage to L. S must
    first add an independently reviewable source receipt; passing made-up
    S60ExternalUsage here cannot establish engineering/science qualification.
    """
    if (
        not isinstance(usage, S60ExternalUsage)
        or usage.session_id != state.session_id
        or usage.work_id != state.active_work_id
        or usage.source_status not in (
            "VERIFIED_NATURAL_COMPLETION", "VERIFIED_BACKEND_STOP",
        )
        or not isinstance(usage.provider_facts, ProviderCallFacts)
        or usage.provider_facts.prompt_tokens is None
        or usage.provider_facts.completion_tokens is None
        or usage.provider_facts.total_tokens is None
        or usage.provider_facts.total_tokens < 1
        or (usage.source_status == "VERIFIED_NATURAL_COMPLETION"
            and usage.provider_facts.finish_reason not in ("stop", "length"))
        or usage.provider_facts.total_tokens != (
            usage.provider_facts.prompt_tokens
            + usage.provider_facts.completion_tokens
        )
        or usage.provider_facts.requested_max_output_tokens != state.active_max_tokens
        or usage.provider_facts.completion_tokens > state.active_max_tokens
    ):
        raise S60FatigueRejected("source-qualified full cumulative usage required")
    return account_l2(
        profile, state,
        L2Usage(
            state.session_id, usage.work_id, state.seq + 1, at_ns,
            usage.source_receipt_sha256, usage.provider_facts.total_tokens,
            ("COMPLETED" if usage.source_status == "VERIFIED_NATURAL_COMPLETION"
             else "STOP_ACK"),
        ),
    )
