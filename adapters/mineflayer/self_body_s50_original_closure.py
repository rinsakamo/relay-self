"""Opt-in DEV 1-slot bridge from *original S49 closed typed Action* to SelfBody.

Only called by original normal_action.observe_closed_native_actions, *after*
S16 ActionSupervisor terminal closure. No probe, packet, control, Action
authority, ledger write, model, or owner-state reconstruction from JSON.
A later, independently reviewed S50 motion diagnostic can be attached once.
"""
from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator
from typing import Mapping

from adapters.mineflayer.normal_action import (
    NormalActionClosedReadback,
    observe_closed_native_actions,
)
from adapters.mineflayer.self_body_projection import project_body_action_readback
from adapters.mineflayer.self_body_s50_motion_companion import (
    SelfBodyS50MotionCompanion,
    compose_self_body_s50_motion_companion,
)
from relay_self.action import ActionState
from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.self_body import SelfBodyView, compose_self_body_view


class SelfBodyS50ClosedOwnerRejected(ValueError):
    """The original typed S49/S15/S16 action closure was not admitted."""


class SelfBodyS50ClosedOwnerLease:
    """At most ONE original closed Action from a single original S49 invocation.

    The lease is a short-lived typed pointer, not durable state/memory.
    Caller must close/expire at end of one DEV run or cognition epoch.
    """

    def __init__(self, *, self_id: str, expected_action_id: str | None = None):
        if (
            not isinstance(self_id, str) or not self_id or self_id.strip() != self_id
            or (expected_action_id is not None and
                (not isinstance(expected_action_id, str)
                 or not expected_action_id or expected_action_id.strip() != expected_action_id))
        ):
            raise SelfBodyS50ClosedOwnerRejected("bounded SelfBody identity required")
        self._self_id = self_id
        self._expected_action_id = expected_action_id
        self._body: SelfBodyView | None = None
        self._status = "WAITING_FOR_ORIGINAL_S16"
        self._closed = False
        self._seen_closures = 0
        self._errors: list[str] = []

    def observe_original_closed(self, original: NormalActionClosedReadback) -> None:
        """Original S49 calls synchronously after terminal; NEVER veto source owner.

        Deliberately swallow errors at this local callback boundary and revoke
        this lease on any duplicate/foreign/unknown closure. The original S49
        listener independently swallows observer errors; we record a reason.
        """
        self._seen_closures += 1
        try:
            if self._closed or self._body is not None or self._seen_closures != 1:
                raise SelfBodyS50ClosedOwnerRejected("stale/duplicate S49 closure")
            if not isinstance(original, NormalActionClosedReadback):
                raise SelfBodyS50ClosedOwnerRejected("original typed S49 closure required")
            c, o, terminal, probe = (
                original.consequence, original.interpretation,
                original.terminal, original.original_probe,
            )
            if (
                terminal.state is not ActionState.OUTCOME
                or o.disposition is not ActionOutcomeDisposition.OUTCOME
                or o.reason_code != "observed_execution"
                or o.source_status != "executed"
                or terminal.action_id != o.action_id
                or c.action_id != o.action_id
                or c.session_id != o.session_id
                or probe.session_id != o.session_id
                or probe.kind != "probe"
                or probe.request_id is None
                or c.before_observation is None
                or c.before_observation.seq <= probe.seq
                or c.after_observation is None
                or c.after_observation.seq <= c.before_observation.seq
                or (
                    self._expected_action_id is not None
                    and o.action_id != self._expected_action_id
                )
            ):
                raise SelfBodyS50ClosedOwnerRejected(
                    "S16/Action/native before-after source mismatch"
                )
            # Crucial: the existing owner adapter checks ORIGINAL typed
            # before/after native probes and exact S15/S16 consequence lineage.
            body_observation = project_body_action_readback(c, o)
            body = compose_self_body_view(
                session_id=o.session_id,
                epoch_id=f"s49-original-after-{body_observation.native_seq}",
                self_id=self._self_id,
                observation=body_observation,
                outcome=o,
                minimum_native_seq=c.before_observation.seq + 1,
            )
            if (
                body.observation is not body_observation
                or body.outcome is not o
                or body.observation.action_id != o.action_id
                or body.observation.consequence_provenance != o.world_provenance
            ):
                raise SelfBodyS50ClosedOwnerRejected("SelfBody owner source changed")
            self._body = body
            self._status = "ONE_ORIGINAL_TYPED_S16_ACTION_READY"
        except Exception as exc:
            self._body = None
            self._closed = True
            self._status = "REVOKED_ON_BAD_OR_MULTIPLE_ORIGINAL_CLOSURE"
            self._errors.append(type(exc).__name__)

    def consume_s50_once(
        self, source: Mapping[str, object],
    ) -> SelfBodyS50MotionCompanion:
        """Combine only after S50 original-source review, once, after S49 closure.

        Does not authenticate source bytes; upstream S50 source owner must do
        this. Failed joins revoke the lease to prevent replay/guessing.
        """
        if (
            self._closed or self._body is None
            or self._status != "ONE_ORIGINAL_TYPED_S16_ACTION_READY"
        ):
            raise SelfBodyS50ClosedOwnerRejected(
                "no live original typed S16/native Present lease"
            )
        original = self._body
        self._closed = True
        self._body = None
        try:
            joined = compose_self_body_s50_motion_companion(original, source)
            self._status = "ONE_S50_DIAGNOSTIC_JOIN_CONSUMED"
            return joined
        except Exception:
            self._status = "REVOKED_ON_INVALID_S50_SOURCE"
            raise

    def close(self) -> None:
        self._closed = True
        self._body = None
        if self._status == "ONE_ORIGINAL_TYPED_S16_ACTION_READY":
            self._status = "EXPIRED_WITHOUT_S50_SOURCE"
        elif self._status == "WAITING_FOR_ORIGINAL_S16":
            self._status = "EXPIRED_WITHOUT_ORIGINAL_CLOSURE"

    def status(self) -> dict[str, object]:
        return {
            "status": self._status,
            "original_closures_seen": self._seen_closures,
            "errors": tuple(self._errors),
            "typed_original_ready": self._body is not None and not self._closed,
            "new_native_probes": 0,
            "new_action_issuers": 0,
            "new_s16_outcome_owners": 0,
            "new_packet_writes": 0,
            "model_calls": 0,
            "memory_writes": 0,
            "world_tick_alignment": "NOT_ATTESTED",
            "p1_wait_admitted": 0,
            "l10_pairs_admitted": 0,
        }


@contextmanager
def observe_original_s49_selfbody_closure(
    lease: SelfBodyS50ClosedOwnerLease,
) -> Iterator[SelfBodyS50ClosedOwnerLease]:
    """Connect original existing normal_action callback; never patch issuer.

    Do NOT overlap with S49's separate Stage-R closure observer, which also
    owns the single context-local callback slot. Only one owner is installed.
    """
    if not isinstance(lease, SelfBodyS50ClosedOwnerLease):
        raise SelfBodyS50ClosedOwnerRejected("typed existing lease required")
    with observe_closed_native_actions(lease.observe_original_closed):
        try:
            yield lease
        finally:
            # Intentionally DON'T automatically clear a live lease: caller may
            # need to collect S50 post-S16 World ticks immediately afterward.
            # Caller MUST explicitly close at end of one DEV epoch/session.
            pass
