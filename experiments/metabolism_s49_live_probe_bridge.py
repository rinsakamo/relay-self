"""Explicitly optional S49 live_probe -> original S/L8/M post-epoch source seam.

S49 has a pre-choice async live_probe callback. It is NOT its S42
DecisionEpochResult nor its S49 native Action outcome. This M-only adapter
captures the *same already-observed* native probe by reference for one
strictly later, source-joined passive diagnosis. It does not replay native
I/O, grant an Action, change S49 L0, synthesize B0 or advance learning.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from experiments.metabolism_slm_dev_host_tap import (
    SLMDevTapResult,
    observe_optional_s_l_m_dev,
)

SourceStatus = Literal[
    "DISABLED", "EMPTY", "CAPTURED", "REJECTED", "CONSUMED",
]


@dataclass(frozen=True, slots=True)
class S49PassiveSourceSummary:
    """References only; no source payload or Minecraft authority."""

    status: SourceStatus
    accepted_probes: int
    rejected_probes: int
    session_id: str | None
    current_seq: int | None
    action_authority: bool = False
    source_attested: bool = False
    new_native_reads: int = 0
    new_cognition_calls: int = 0
    action_issues: int = 0
    learning_updates: int = 0
    food_credits: int = 0
    source_scope: str = "S49_PASSIVE_PRECHOICE_SOURCE_LEASE_DEV_ONLY"


class S49PassiveSourceLease:
    """One-slot S49 live_probe callback, consumed once after S completion.

    A callback method is intentionally async for compatibility with S49
    qualify(live_probe=...), but contains NO await: no asyncio task, sleep,
    provider, filesystem or TCP. S49's original caller must still own
    timeout and Action issuer. This class cannot authenticate source bytes.
    """

    def __init__(self, *, enabled: bool = False, max_probes: int = 4) -> None:
        if type(enabled) is not bool or (
            type(max_probes) is not int or not 1 <= max_probes <= 8
        ):
            raise ValueError("explicit bool and bounded DEV source budget required")
        self.enabled = enabled
        self.max_probes = max_probes
        self._session_id: str | None = None
        self._last_seq: int | None = None
        self._last_probe: object | None = None
        self._status: SourceStatus = "EMPTY" if enabled else "DISABLED"
        self._accepted = 0
        self._rejected = 0

    async def observe(self, probe: object) -> None:
        """S49 invokes this on the *existing* probe, before its own L0 choice.

        A bad passive source NEVER throws into S49. Clear the lease rather
        than allowing any stale previously captured probe to be reused.
        """
        if not self.enabled:
            return
        try:
            from adapters.mineflayer.python_protocol import MineflayerObservation

            if (
                not isinstance(probe, MineflayerObservation)
                or probe.kind != "probe"
                or type(probe.session_id) is not str or not probe.session_id
                or type(probe.seq) is not int or probe.seq < 0
                or type(probe.request_id) is not str or not probe.request_id
                or probe.provenance.source != "mineflayer"
                or (
                    self._session_id is not None
                    and self._session_id != probe.session_id
                )
                or (
                    self._last_seq is not None
                    and probe.seq <= self._last_seq
                )
                or self._accepted >= self.max_probes
            ):
                raise ValueError("not one fresh, bounded original native probe")
            self._session_id = probe.session_id
            self._last_seq = probe.seq
            self._last_probe = probe
            self._accepted += 1
            self._status = "CAPTURED"
        except Exception:
            self._last_probe = None
            self._rejected += 1
            self._status = "REJECTED"

    def observe_after_original_s_epoch(
        self,
        *,
        original_s_epoch: object,
        native: object,
        ledger: object,
        original_b0_decision: object,
        retained: object,
        self_id: str,
        epoch_id: str,
        learning: object | None = None,
        retention_enabled: bool | None = None,
        noise_bound: float | None = None,
    ) -> SLMDevTapResult:
        """No new S decision: require original captured native object identity.

        A source may be joined only once. Missing B0/S42/L8 originals, or
        a later S49 probe, yields DEFERRED without changing S49 control.
        """
        if not self.enabled:
            return SLMDevTapResult(
                original_s_epoch, "DISABLED", "not_enabled",
            )
        probe = self._last_probe
        self._last_probe = None
        if probe is None or self._status != "CAPTURED":
            return SLMDevTapResult(
                original_s_epoch, "DEFERRED", "owner_source_or_scope_rejected",
            )
        self._status = "CONSUMED"
        try:
            if getattr(native, "observation", None) is not probe:
                return SLMDevTapResult(
                    original_s_epoch, "DEFERRED",
                    "owner_source_or_scope_rejected",
                )
        except Exception:
            return SLMDevTapResult(
                original_s_epoch, "DEFERRED", "owner_source_or_scope_rejected",
            )
        try:
            return observe_optional_s_l_m_dev(
                enabled=True,
                original_s_epoch=original_s_epoch,
                probe=probe, native=native,
                ledger=ledger, original_b0_decision=original_b0_decision,
                retained=retained, self_id=self_id, epoch_id=epoch_id,
                learning=learning, retention_enabled=retention_enabled,
                noise_bound=noise_bound,
            )
        except Exception:
            return SLMDevTapResult(
                original_s_epoch, "OBSERVER_ERROR", "observer_internal_error",
            )

    def summary(self) -> S49PassiveSourceSummary:
        return S49PassiveSourceSummary(
            status=self._status,
            accepted_probes=self._accepted,
            rejected_probes=self._rejected,
            session_id=self._session_id,
            current_seq=self._last_seq,
        )
