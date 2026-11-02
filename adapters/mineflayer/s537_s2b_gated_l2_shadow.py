"""S #537 S2-B: original S2-A read port -> existing S60-A/B1, DEV-only.

This bridge never invents intent/retained revisions. The original S49
runner does NOT yet expose them via its live_probe callback, so the normal
live path is DEFERRED until an exact same-epoch owner witness is supplied.
No new L0/Action/World owner, no model or learner logic is implemented here.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any

from adapters.mineflayer.s537_s2a_l2_read_port import S2AReadOnlyInput
from adapters.mineflayer.s60b1_loopback_adapter import (
    LoopbackDisplacementAdapter,
    LoopbackTransportConfig,
)
from relay_self.best_effort_displacement import BestEffortDisplacement, ModelRequest
from relay_self.interruption_fence import CognitionContext
from relay_self.provenance import Provenance


class S2BSourceRejected(ValueError):
    """Input not bound to a real current owner source or stale S60 lease."""


@dataclass(frozen=True, slots=True)
class S2BOwnerContextRead:
    """Explicit original-owner-provided values, NOT a source attestation.

    Caller must obtain both revisions directly from the original L0/Intent
    owners in the same active S49 epoch, and independently verify provenance.
    A fabricated value is NOT made trustworthy by constructing this type.
    """

    source_input: S2AReadOnlyInput
    context: CognitionContext
    intent_id: str
    owner_scope: str

    def __post_init__(self) -> None:
        entry, ctx = self.source_input, self.context
        if (
            not isinstance(entry, S2AReadOnlyInput)
            or not isinstance(ctx, CognitionContext)
            or ctx.session_id != entry.session_id
            or ctx.world_seq != entry.probe_seq
            or type(ctx.intent_revision) is not int
            or type(ctx.retained_revision) is not int
            or not isinstance(self.intent_id, str)
            or not self.intent_id.strip()
            or self.owner_scope != "ORIGINAL_S49_L0_AND_INTENT_READ_ONLY"
        ):
            raise S2BSourceRejected("exact owner context and source required")


class S2BGatedL2Shadow:
    """At most one S60-B1 attempt; S60-A retains all lease/acceptance power."""

    def __init__(
        self, *, enabled: bool = False, config: LoopbackTransportConfig,
        timeout_s: float = 45.0,
    ) -> None:
        if (
            enabled is not True
            or not isinstance(config, LoopbackTransportConfig)
            or type(timeout_s) not in (float, int)
            or not 0 < timeout_s <= 60
            or config.max_tokens > 256
            or config.slots != 1
        ):
            raise S2BSourceRejected("explicit bounded S2B DEV gate required")
        self.config = config
        self.timeout_s = timeout_s
        self._owner: BestEffortDisplacement | None = None
        self._adapter: LoopbackDisplacementAdapter | None = None
        self._source: S2AReadOnlyInput | None = None
        self._request: ModelRequest | None = None
        self._last_probe_seq: int = -1
        self._session: str | None = None
        self._current: bool = False
        self._closed = False
        self._calls = 0
        self._status = "NOT_SUBMITTED"
        self._accepted: str | None = None

    @property
    def model_attempts(self) -> int:
        return self._calls

    @property
    def status(self) -> str:
        return self._status

    def observe(
        self, source: S2AReadOnlyInput, *,
        owner_read: S2BOwnerContextRead | None = None,
    ) -> None:
        """No awaits. Missing actual owner revisions block, not default to 1."""
        if self._closed:
            raise S2BSourceRejected("closed S2B observer")
        if (
            not isinstance(source, S2AReadOnlyInput)
            or source.model_submitted or source.source_attested
            or source.action_authority or source.learning_authority
            or not source.session_id or not source.request_id
            or not source.world_source_ref or not source.body_source_ref
            or source.world_source_ref != (
                f"present:{source.session_id}:{source.probe_seq}:{source.request_id}"
            )
            or source.body_source_ref != (
                f"native-probe:{source.session_id}:{source.probe_seq}:"
                f"{source.request_id}"
            )
            or source.epoch_id != f"native-{source.probe_seq}"
            or type(source.probe_seq) is not int or source.probe_seq <= self._last_probe_seq
            or self._session not in (None, source.session_id)
            or (
                source.preceding_action_id is not None
                and (
                    type(source.preceding_s16_after_seq) is not int
                    or source.preceding_s16_after_seq >= source.probe_seq
                    or type(source.preceding_action_source_probe_seq) is not int
                    or source.preceding_action_source_probe_seq >= (
                        source.preceding_s16_after_seq
                    )
                )
            )
        ):
            raise S2BSourceRejected("S2A source/session/chronology invalid")
        self._session = source.session_id
        self._last_probe_seq = source.probe_seq
        # The next native probe logically invalidates an earlier S60 result.
        # Missing new original revision does NOT forge a new S60 context.
        if self._source is not None:
            self._current = False
            if self._accepted is not None:
                self._status = "EXPIRED_WORLD_ADVANCED"
        if self._owner is not None and owner_read is not None:
            if (
                owner_read.source_input is not source
                or owner_read.context.session_id != source.session_id
                or owner_read.context.world_seq != source.probe_seq
            ):
                raise S2BSourceRejected("foreign owner revision for native source")
            self._owner.observe(owner_read.context)
        # Exactly one unambiguous S16 result may be bound to next L2 input.
        if self._calls or source.preceding_action_id is None:
            return
        if owner_read is None:
            self._status = "DEFERRED_ORIGINAL_OWNER_REVISION_UNAVAILABLE"
            return
        if owner_read.source_input is not source:
            raise S2BSourceRejected("owner witness does not identify original input")
        # The context object is supplied by the original owner, NOT synthesized.
        context = owner_read.context
        prompt = json.dumps(source.bounded_row(), ensure_ascii=True, sort_keys=True)
        if len(prompt) > 5000:
            raise S2BSourceRejected("bounded L2 input too long")
        model = self.config.model
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": (
                    "You are a read-only Minecraft observation reviewer. "
                    "Explain one uncertainty based on the past Action and "
                    "current observation. Do not authorize commands, "
                    "learning, rewards, or goal success."
                )},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "temperature": 0,
            "max_tokens": self.config.max_tokens,
        }
        adapter = LoopbackDisplacementAdapter(self.config, lambda _request: payload)
        provenance = Provenance(
            "s537-s2b-original-owner-admission",
            f"{source.session_id}:{source.probe_seq}:{source.request_id}",
        )
        owner = BestEffortDisplacement(
            context, provenance.source, adapter.start, adapter.cancel,
            time.monotonic,
        )
        adapter.bind(owner)
        self._owner = owner
        self._adapter = adapter
        self._source = source
        self._current = True
        request = owner.admit(
            context, "L2", priority=1,
            deadline=time.monotonic() + self.timeout_s,
            wait_budget=self.timeout_s, provenance=provenance,
        )
        self._request = request
        self._calls += 1  # attempted S60 submission, NOT backend completion
        self._status = "IN_FLIGHT"
        owner.submit(request)

    def poll(self) -> str | None:
        """S60-A owns acceptance; this only displays a current advisory result."""
        if self._owner is None:
            return None
        result = self._owner.tick()
        if result is None:
            return None
        if (
            not self._current or self._request is None
            or result.request is not self._request
            or not isinstance(result.value, str) or not result.value.strip()
            or self._source is None
            or self._source.probe_seq != self._last_probe_seq
        ):
            self._status = "STALE_OR_UNQUALIFIED_RESULT"
            return None
        self._accepted = result.value[:1000]
        self._status = "ADVISORY_CURRENT_READ_ONLY"
        return self._accepted

    async def close(self) -> dict[str, Any]:
        """Host close is not a provider STOP ACK or GPU/slot release."""
        if self._closed:
            raise S2BSourceRejected("duplicate S2B close")
        self._closed = True
        self._current = False
        if self._adapter is not None:
            await self._adapter.aclose()
        return {
            "schema": "S537_S2B_ORIGINAL_S60_SHADOW_DEV_V1",
            "status": self._status,
            "session_id": self._session,
            "input_source_seq": (
                self._source.probe_seq if self._source is not None else None
            ),
            "latest_probe_seq": self._last_probe_seq,
            "model_attempts": self._calls,
            "accepted_advisory": self._accepted,
            "current": False,
            "owner_events": [
                r.event for r in self._owner.receipts
            ] if self._owner is not None else [],
            "transport_events": [
                e for e, _ in self._adapter.receipts
            ] if self._adapter is not None else [],
            "source_attested": False,
            "action_authority": False,
            "learning_authority": False,
            "backend_stop_ack": False,
            "gpu_release_verified": False,
            "qualification": "NO_GO",
            "science": "NOT_RUN",
        }
