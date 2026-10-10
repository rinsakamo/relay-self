"""R3-A offline measurement observer. R3_LIVE_AUTH_PENDING; no live entrypoint."""
from __future__ import annotations

import asyncio
import math
from collections import deque

from adapters.mineflayer.s60b2_offline_diagnostic import STAGES, OfflineDiagnosticTransport
from adapters.mineflayer.s60b2_owned_backend_probe import ProbeRejected, durable_write


class R3DiagnosticTransport(OfflineDiagnosticTransport):
    """Reuse R2 classification, with fail-closed buffering and durable draining.

    Only synthetic localhost measurement is qualified. No physical-run grant
    flows through this class. Future/lease acceptance remains inherited B1/B2.
    """

    def __init__(self, config, payload, journal):
        super().__init__(config, payload, journal)
        # R2's rolling buffer must not silently discard early failure evidence.
        self._diagnostics = deque()
        self._diagnostic_overflow = False
        self._diagnostic_generation = None
        self._diagnostic_count = 0

    def _observe(self, stage, attempt, *, task_required=True):
        previous = len(self._diagnostics)
        super()._observe(stage, attempt, task_required=task_required)
        if len(self._diagnostics) == previous:
            return
        generation = self._diagnostics[-1].generation
        if generation != self._diagnostic_generation:
            self._diagnostic_generation = generation
            self._diagnostic_count = 0
        self._diagnostic_count += 1
        if len(self._diagnostics) > 64 or self._diagnostic_count > 64:
            self._diagnostics.pop()
            self._diagnostic_overflow = True

    async def drain(self):
        await super().drain()
        if self._diagnostic_overflow:
            raise ProbeRejected("diagnostic observation buffer exhausted")
        while self._diagnostics:
            receipt = self._diagnostics[0]
            if (receipt.stage not in STAGES or type(receipt.generation) is not int
                or receipt.generation < 1 or type(receipt.elapsed_ms) is not int
                or not 0 <= receipt.elapsed_ms <= 86_400_000):
                raise ProbeRejected("diagnostic receipt unconfirmed")
            observed = self._diagnostic_start + receipt.elapsed_ms / 1000 - self.journal.start
            if not math.isfinite(observed) or not 0 <= observed <= 86_400:
                raise ProbeRejected("diagnostic journal time unconfirmed")
            pending = asyncio.create_task(durable_write(
                self.journal, "DIAG_" + receipt.stage,
                generation=receipt.generation, observed_elapsed_s=observed))
            try:
                await asyncio.shield(pending)
            except asyncio.CancelledError:
                await pending
                self._diagnostics.popleft()  # committed receipt cannot be replayed
                raise
            self._diagnostics.popleft()
