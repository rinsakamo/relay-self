"""Offline Future fixtures, no provider, GPU or World execution."""
import asyncio
from dataclasses import replace

import pytest

from relay_self.best_effort_displacement import BestEffortDisplacement, DisplacementRejected
from relay_self.interruption_fence import CognitionContext, InterruptRejected
from relay_self.provenance import Provenance

CONTEXT = CognitionContext("world", 3, 1, 2)
SOURCE = Provenance("admission", "offline-current")


class Rig:
    def __init__(self):
        self.now = 0.0
        self.futures = []
        self.starts = []
        self.cancels = []
        self.cancel_effect = lambda: None
        self.start_effect = None
        self.owner = BestEffortDisplacement(
            CONTEXT, "admission", self.start, self.cancel, lambda: self.now,
        )

    def start(self, request):
        self.starts.append(request)
        if self.start_effect:
            return self.start_effect()
        future = asyncio.get_running_loop().create_future()
        self.futures.append(future)
        return future

    def cancel(self, request):
        self.cancels.append(request)
        # Negative control: old result already fenced before client callback.
        lease = self.owner._active
        with pytest.raises(InterruptRejected):
            lease.fence.accept_l2_result(lease.ticket, self.owner.context)
        self.cancel_effect()

    def request(self, priority=1, level="L1", deadline=20.0, budget=5.0):
        return self.owner.admit(
            self.owner.context, level, priority, deadline, budget, SOURCE,
        )

    def submit(self, **kwargs):
        request = self.request(**kwargs)
        self.owner.submit(request)
        return request

    def events(self):
        return [receipt.event for receipt in self.owner.receipts]


def test_blocked_l2_l1_l0_then_natural_completion_stale_and_new_attempt():
    async def scenario():
        rig = Rig()
        old = rig.submit(level="L2")
        urgent = rig.submit(priority=2)
        ran = []

        async def l0():
            ran.append("L0")

        receipt = await rig.owner.urgent_l0(CONTEXT, l0)
        assert ran == ["L0"] and receipt.l0_completed
        assert not receipt.backend_stopped and not receipt.gpu_released
        assert rig.owner.active is old and rig.owner.pending is urgent
        assert rig.starts == [old] and rig.cancels == [old]
        rig.futures[0].set_result("old Action/Learning text")
        assert rig.owner.tick() is None
        assert rig.starts == [old, urgent]
        rig.futures[1].set_result("fresh transient")
        result = rig.owner.tick()
        assert result.request is urgent and result.value == "fresh transient"
        assert rig.owner.tick() is None
        assert rig.events().count("STALE_REJECTED") == 1
        assert not any("ACK" in e or "GPU" in e or "IDLE" in e for e in rig.events())
    asyncio.run(scenario())


@pytest.mark.parametrize("expiry", ["budget", "deadline"])
def test_ignored_cancel_forever_bounds_pending_and_l0(expiry):
    async def scenario():
        rig = Rig()
        old = rig.submit(level="L2")
        rig.submit(priority=2, deadline=2 if expiry == "deadline" else 20, budget=5)
        rig.now = 2 if expiry == "deadline" else 5
        assert rig.owner.tick() is None
        assert rig.owner.active is old and rig.owner.pending is None
        assert len(rig.starts) == 1
        assert "CANCEL_UNCONFIRMED_BACKEND_BUSY" in rig.events()

        async def l0():
            return "UNKNOWN"

        assert await rig.owner.run_l0(l0) == "UNKNOWN"
        for _ in range(1000):
            rig.submit(priority=2, deadline=10000, budget=1)
        assert len(rig.owner.receipts) == 64
        assert len(rig.starts) == len(rig.futures) == len(rig.cancels) == 1
        assert rig.owner.pending is not None
    asyncio.run(scenario())


def test_three_competing_priorities_deadlines_and_newest_wins():
    async def scenario():
        rig = Rig()
        rig.submit(level="L2")
        a = rig.submit(priority=4)
        rig.submit(priority=3, level="L2")
        assert rig.owner.pending is a
        b = rig.submit(priority=4, deadline=3)
        assert rig.owner.pending is b
        c = rig.submit(priority=5, level="L2", deadline=10)
        assert rig.owner.pending is c
        rig.now = 3
        rig.futures[0].set_result("stale")
        assert rig.owner.tick() is None
        assert rig.starts[-1] is c and len(rig.starts) == 2
        assert rig.events().count("PENDING_REPLACED") == 2
    asyncio.run(scenario())


@pytest.mark.parametrize("cancel_kind", ["raise", "task_cancel", "completion", "cancelled_error"])
def test_cancel_failure_local_cancel_and_completion_race(cancel_kind):
    async def scenario():
        rig = Rig()
        rig.submit(level="L2")

        def effect():
            if cancel_kind == "raise":
                raise RuntimeError("private prompt/path must not appear")
            if cancel_kind == "cancelled_error":
                raise asyncio.CancelledError()
            if cancel_kind == "task_cancel":
                rig.futures[0].cancel()
            if cancel_kind == "completion":
                rig.futures[0].set_result("stale")
        rig.cancel_effect = effect
        rig.submit(priority=2)
        latest = rig.submit(priority=3)
        assert rig.owner.tick() is None
        if cancel_kind == "completion":
            assert rig.owner.active is latest and len(rig.starts) == 2
        else:
            assert len(rig.starts) == 1
            rig.now = 5
            rig.owner.tick()
            assert rig.owner.pending is None
        assert len(rig.cancels) == 1
        assert "private" not in repr(rig.owner.receipts)
    asyncio.run(scenario())


@pytest.mark.parametrize("field", ["world_seq", "intent_revision", "retained_revision", "session_id"])
def test_context_changes_revoke_active_pending_and_issued(field):
    async def scenario():
        rig = Rig()
        old = rig.submit(level="L2")
        rig.submit(priority=2)
        unused = rig.request(priority=3)
        current = replace(CONTEXT, **{field: "new-world" if field == "session_id"
                                      else getattr(CONTEXT, field) + 1})
        rig.owner.observe(current)
        assert rig.owner.pending is None
        with pytest.raises(DisplacementRejected):
            rig.owner.submit(unused)
        rig.futures[0].set_result("stale")
        assert rig.owner.tick() is None
        assert rig.starts == [old]
        with pytest.raises(DisplacementRejected):
            rig.owner.admit(CONTEXT, "L1", 3, 20, 5, SOURCE)
    asyncio.run(scenario())


def test_forgery_replay_superseded_admission_and_foreign_owner():
    async def scenario():
        rig, other = Rig(), Rig()
        first = rig.request()
        latest = rig.request()
        assert first.work_id != latest.work_id != other.request().work_id
        for fake in (first, replace(latest), other.request()):
            with pytest.raises(DisplacementRejected):
                rig.owner.submit(fake)
        rig.owner.submit(latest)
        with pytest.raises(DisplacementRejected):
            rig.owner.submit(latest)
        assert len(rig.starts) == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("changes", [
    {"context": CognitionContext("foreign", 3, 1, 2)},
    {"provenance": Provenance("model", "forged")},
    {"priority": True}, {"priority": -1}, {"deadline": float("nan")},
    {"deadline": float("inf")}, {"deadline": 0}, {"wait_budget": 0},
    {"wait_budget": float("inf")}, {"level": "L0"},
])
def test_invalid_source_budget_and_level(changes):
    async def scenario():
        rig = Rig()
        arguments = dict(context=CONTEXT, level="L1", priority=2,
                         deadline=10, wait_budget=2, provenance=SOURCE)
        arguments.update(changes)
        with pytest.raises(DisplacementRejected):
            rig.owner.admit(**arguments)
        assert not rig.starts
    asyncio.run(scenario())


@pytest.mark.parametrize("failure", ["start_raise", "bad_future", "provider_error", "local_cancel"])
def test_ambiguous_backend_failure_never_releases_slot(failure):
    async def scenario():
        rig = Rig()
        if failure == "start_raise":
            def fail():
                raise RuntimeError("secret")
            rig.start_effect = fail
        if failure == "bad_future":
            rig.start_effect = lambda: "fake terminal"
        old = rig.submit(level="L2")
        if failure == "provider_error":
            rig.futures[0].set_exception(RuntimeError("secret"))
        if failure == "local_cancel":
            rig.futures[0].cancel()
        rig.submit(priority=2)
        for _ in range(3):
            assert rig.owner.tick() is None
        assert rig.owner.active is old and len(rig.starts) == 1
        rig.now = 5
        rig.owner.tick()
        assert rig.owner.pending is None
        assert "secret" not in repr(rig.owner.receipts)
        # Claimed/unknown idle is not an accepted API or an admission contract.
        assert not hasattr(rig.owner, "acknowledge_idle")
        assert not hasattr(rig.owner, "acknowledge_backend_stop")
    asyncio.run(scenario())


def test_l0_failure_and_unknown_no_reissue_with_no_model():
    async def scenario():
        rig = Rig()
        calls = []

        async def fail():
            calls.append(1)
            raise RuntimeError("Action UNKNOWN")

        with pytest.raises(RuntimeError):
            await rig.owner.run_l0(fail)
        assert calls == [1] and "L0_COMPLETED" not in rig.events()

        async def unknown():
            return "UNKNOWN"

        assert await rig.owner.run_l0(unknown) == "UNKNOWN"
        assert not rig.starts
    asyncio.run(scenario())


def test_natural_completion_before_cancel_still_revoked_and_not_double_admitted():
    async def scenario():
        rig = Rig()
        rig.submit(level="L2")
        rig.futures[0].set_result("old")
        newest = rig.submit(priority=2)
        assert rig.owner.tick() is None
        assert rig.starts[-1] is newest and len(rig.starts) == 2
        assert rig.owner.tick() is None
        assert len(rig.starts) == 2
    asyncio.run(scenario())


def test_expired_pending_not_started_on_simultaneous_provider_completion():
    async def scenario():
        rig = Rig()
        rig.submit(level="L2")
        rig.submit(priority=2, deadline=2)
        rig.now = 2
        rig.futures[0].set_result("old")
        assert rig.owner.tick() is None
        assert len(rig.starts) == 1 and rig.owner.active is None
    asyncio.run(scenario())


def test_lower_priority_cannot_revoke_active_and_current_result_is_transient():
    async def scenario():
        rig = Rig()
        old = rig.submit(priority=4)
        rig.submit(priority=3)
        assert not rig.cancels and rig.owner.pending is None
        rig.futures[0].set_result("current")
        assert rig.owner.tick().request is old
    asyncio.run(scenario())


def test_regressed_context_clock_and_reused_future_fail_closed():
    async def scenario():
        rig = Rig()
        with pytest.raises(DisplacementRejected):
            rig.owner.observe(replace(CONTEXT, retained_revision=1))
        rig.submit()
        rig.futures[0].set_result("fresh")
        assert rig.owner.tick() is not None
        rig.start_effect = lambda: rig.futures[0]
        request = rig.submit()
        assert rig.owner.active is request
        assert rig.owner.tick() is None
        rig.now = -1
        with pytest.raises(DisplacementRejected):
            rig.owner.tick()
    asyncio.run(scenario())


def test_cancel_callback_reentry_cannot_corrupt_pending():
    async def scenario():
        rig = Rig()
        rig.submit(level="L2")
        rig.cancel_effect = lambda: rig.owner.tick()
        request = rig.submit(priority=2)
        assert rig.owner.pending is request and len(rig.starts) == 1
        assert "HOST_CANCEL_FAILED" in rig.events()
    asyncio.run(scenario())
