"""S49 original Action Executor with DEV-only synchronous WAIT issuance fence.

This concrete executor INHERITS the original execute(): it neither replaces
the S14/S15/S16 issuance sequence nor creates another supervisor or writer.
The original execute() dynamically calls require_authorizations *before*
supervisor.issue and any physical IO. Override that exact hook to fail closed.

Not installed in S49 qualify(); no physical run or global injection. Callers
must explicitly construct this DEV subclass in an isolated S49 development
harness. Paper sample references are not an authenticated shared clock.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.s49_wait_owner_fence_dev import S49WaitFenceDev
from relay_self.action import ActionState
from relay_self.intent import IntentCommitment


class S49WaitFencedExecutorDev(NormalSessionActionExecutor):
    """Same original execute path, one ActionSupervisor, one-use WAIT fence."""

    def __init__(
        self, session_id: str, intent: IntentCommitment, *,
        marker_id: str, world: str, dev_only: bool = False,
    ) -> None:
        if dev_only is not True:
            raise BoundaryRejected("S49 WAIT fence explicitly DEV-only")
        super().__init__(session_id, intent)
        self._wait_fence = S49WaitFenceDev(
            owner=self, supervisor=self.supervisor, session_id=session_id,
            marker_id=marker_id, world=world,
        )

    @property
    def wait_phase(self) -> str:
        return self._wait_fence.phase

    @property
    def wait_original_rows(self) -> tuple[dict, ...]:
        return self._wait_fence.original_rows

    def require_authorizations(
        self, step, bound, probe, propose, issue,
    ) -> None:
        """Original execute dispatches here before S15.issue / external IO."""
        if self._wait_fence.phase != "NEW":
            # Guard checks the original step identity before the original
            # authorization path can mutate supervisor or dispatch.
            self._wait_fence.before_issue(
                self, action_id=getattr(step, "action_request_id", None),
                attempted_source_ref=getattr(probe, "request_id", None),
            )
        return super().require_authorizations(step, bound, probe, propose, issue)

    def arm_after_original_outcome(
        self, *, closed_action_id: str, terminal_outcome_ref: str,
        controls_clear_ref: str,
    ) -> None:
        """Confirm existing owner has terminal OUTCOME, never fabricate it."""
        if (
            not isinstance(closed_action_id, str)
            or closed_action_id not in self._dispatched
        ):
            raise BoundaryRejected("WAIT arm requires S49-dispatched prior Action")
        try:
            terminal = self.supervisor.get(closed_action_id)
        except ValueError as exc:
            raise BoundaryRejected("WAIT arm requires owned terminal Action") from exc
        if terminal.state is not ActionState.OUTCOME:
            raise BoundaryRejected("WAIT cannot follow non-OUTCOME Action")
        # The supplied references still require independent R source proof.
        self._wait_fence.arm(
            self, closed_action_id=closed_action_id,
            terminal_outcome_ref=terminal_outcome_ref,
            controls_clear_ref=controls_clear_ref,
        )

    async def screen_wait_samples(
        self, source: AsyncIterator[tuple[int, str]], *,
        seal_source_ref: str,
    ) -> tuple[dict, ...]:
        """Observe a bounded async stream, invalidating on BaseException.

        This wraps only the owner-local read loop. It cannot attest that an
        external Paper tick producer is comprehensive, synchronized or honest.
        """
        if self._wait_fence.phase != "ARMED":
            raise BoundaryRejected("WAIT stream needs prior owner arm")
        try:
            async for tick, source_ref in source:
                self._wait_fence.observe_paper_tick(
                    self, world_tick=tick, source_ref=source_ref,
                )
            return self._wait_fence.seal(self, seal_source_ref=seal_source_ref)
        except BaseException:
            # Must retain original exception/cancellation and invalidate
            # partial evidence even if the stream was abandoned mid-await.
            self._wait_fence.abort(
                self, reason_source_ref="S49_DEV_OWNER_WAIT_STREAM_ABORTED",
            )
            raise

    def abort_wait(self, *, reason_source_ref: str) -> None:
        """Owner cleanup/failure hook, synchronous; never rearm automatically."""
        self._wait_fence.abort(self, reason_source_ref=reason_source_ref)
