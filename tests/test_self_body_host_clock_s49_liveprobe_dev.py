"""Offline S49 live_probe handoff: *no* real World, Java, Node, or Action."""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from adapters.mineflayer import s49_normal_session_real_ci
from adapters.mineflayer.self_product_passive_views import (
    DEV_SELF_ID,
    MAX_PROBES,
    PassiveSelfViews,
)
from experiments.self_body_host_clock_passive_dev import (
    HostClockOrigin,
    PassiveHostCallbackTimer,
    PassiveHostClockRejected,
)
from experiments.self_body_host_clock_s49_liveprobe_dev import (
    S49PassiveClockJoinRejected,
    S49PassiveHostClockDEV,
)
from test_self_product_passive_views import probe


def ticks(*values):
    it = iter(values)
    return lambda: next(it)


def observer(*, clock=None, capacity=MAX_PROBES, work=None):
    return S49PassiveHostClockDEV(
        timer=PassiveHostCallbackTimer(
            self_id=DEV_SELF_ID, capacity=capacity, clock=clock,
        ),
        observer=work,
    )


def test_exact_original_s49_live_probe_shape_with_three_probes(monkeypatch, tmp_path):
    received = []
    actions_from_original = []

    async def fake_original_qualify(report, server_log, *, live_probe=None):
        assert live_probe is not None
        for seq in (8, 19, 47):
            received.append(seq)
            await live_probe(probe(seq))
            actions_from_original.append(f"original-action-{seq}")
        return 0

    monkeypatch.setattr(s49_normal_session_real_ci, "qualify", fake_original_qualify)
    relay = observer(clock=ticks(10, 20, 30, 45, 70, 90))

    async def run():
        return await s49_normal_session_real_ci.qualify(
            tmp_path / "report.json", tmp_path / "server.log",
            live_probe=relay.observe,
        )

    assert asyncio.run(run()) == 0
    assert received == [8, 19, 47]
    assert len(actions_from_original) == 3  # Fake original owner only.
    assert [x.native_seq for x in relay.timer.rows()] == [8, 19, 47]
    assert [x.callback_elapsed_ns for x in relay.timer.rows()] == [10, 15, 20]
    assert len(relay.views.rows()) == 3
    assert relay.failures() == ()
    assert relay.summary()["additional_native_receives"] == 0
    assert relay.summary()["s10_updates"] == 0
    assert relay.timer.rows()[0].origin is HostClockOrigin.SYNTHETIC_DEV_CLOCK
    assert not (tmp_path / "report.json").exists()


def test_same_source_join_and_no_fabricated_world_time():
    relay = observer(clock=ticks(10, 25))
    asyncio.run(relay.observe(probe(8)))
    row = relay.views.rows()[0]
    interval = relay.timer.rows()[0]
    assert interval.source_ref == row["body_source_ref"]
    assert interval.session_id == row["session_id"]
    assert interval.native_seq == row["native_seq"]
    assert interval.sample_kind == "PASSIVE_CALLBACK_PROCESSING_ONLY"
    assert interval.action_start_ns is None
    assert interval.world_cue_onset_ns is None
    assert interval.movement_speed_mps is None
    assert not interval.allowed_to_act
    assert not interval.real_action_outcome_attested


def test_ordinary_async_observer_failure_nonveto_and_no_success_sample():
    visited = []
    async def work(view):
        visited.append(view.observation.native_seq)
        if len(visited) == 1:
            raise RuntimeError("optional observer failed")

    relay = observer(clock=ticks(1, 2, 3), work=work)
    async def fake_owner():
        issued = []
        for seq in (8, 19):
            await relay.observe(probe(seq))
            issued.append(seq)
        return issued

    assert asyncio.run(fake_owner()) == [8, 19]
    assert visited == [8, 19]
    assert len(relay.timer.aborted_tickets()) == 1
    assert len(relay.timer.rows()) == 1
    assert len(relay.views.rows()) == 2
    assert relay.views.summary()["observer_errors"] == ["RuntimeError"]
    assert relay.failures()[0].stage == "callback"
    assert relay.summary()["physical_timing_attested"] is False


@pytest.mark.parametrize("failure", [
    asyncio.CancelledError, KeyboardInterrupt, SystemExit, BaseException,
])
def test_cancellation_and_system_interrupt_abort_then_propagate(failure):
    async def broken(_view):
        raise failure("interrupted")

    relay = observer(clock=ticks(1), work=broken)
    async def call_once():
        await relay.observe(probe(8))

    with pytest.raises(failure):
        asyncio.run(call_once())
    assert relay.timer.rows() == ()
    assert len(relay.timer.aborted_tickets()) == 1
    assert relay.failures()[0].cancelled_or_interrupted is True


def test_stale_duplicate_and_foreign_session_nonveto_without_new_sample():
    relay = observer(clock=ticks(1, 2, 3, 4))
    async def run():
        for x in (probe(8), probe(8), probe(7), probe(19, sid="other"),
                  probe(19)):
            await relay.observe(x)
    asyncio.run(run())
    assert [r.native_seq for r in relay.timer.rows()] == [8, 19]
    assert [r["native_seq"] for r in relay.views.rows()] == [8, 19]
    assert len(relay.failures()) == 3
    assert len(relay.views.summary()["observer_errors"]) == 3


def test_timer_capacity_error_does_not_veto_existing_passive_views():
    relay = observer(clock=ticks(1, 2), capacity=1)
    async def fake_owner():
        issued = []
        for seq in (8, 19):
            await relay.observe(probe(seq))
            issued.append(seq)
        return issued
    assert asyncio.run(fake_owner()) == [8, 19]
    assert len(relay.views.rows()) == 2
    assert len(relay.timer.rows()) == 1
    assert relay.failures()[0].stage == "clock-enter"
    assert relay.views.summary()["observer_errors"] == ["PassiveHostClockRejected"]


def test_clock_exit_failure_aborts_and_stays_terminal_while_l0_continues():
    relay = observer(clock=ticks(10, 9, 11))
    async def run():
        for seq in (8, 19):
            await relay.observe(probe(seq))
    asyncio.run(run())
    assert len(relay.views.rows()) == 2
    assert relay.timer.rows() == ()
    assert len(relay.timer.aborted_tickets()) == 1
    assert [r.stage for r in relay.failures()] == ["clock-exit", "clock-enter"]
    assert relay.failures()[0].error_type == "PassiveHostClockRejected"


def test_clock_enter_failure_does_not_suppress_original_passive_projection():
    def broken():
        raise RuntimeError("clock source unavailable")
    relay = observer(clock=broken)
    asyncio.run(relay.observe(probe(8)))
    assert len(relay.views.rows()) == 1
    assert relay.timer.rows() == ()
    assert relay.failures()[0].stage == "clock-enter"
    assert relay.views.summary()["observer_errors"] == ["PassiveHostClockRejected"]


def test_legacy_max_three_probes_fourth_not_a_new_clock_sample():
    relay = observer(clock=ticks(1, 2, 3, 4, 5, 6))
    async def run():
        for seq in (8, 19, 47, 58):
            await relay.observe(probe(seq))
    asyncio.run(run())
    assert relay.summary()["native_probes_joined"] == MAX_PROBES
    assert relay.summary()["clock_samples"] == MAX_PROBES
    assert len(relay.failures()) == 1
    assert relay.failures()[0].stage == "legacy-admission"


def test_invalid_native_subclass_no_new_clock_row_but_nonveto():
    from adapters.mineflayer.python_protocol import MineflayerObservation

    class FakeNative(MineflayerObservation):
        pass

    native = probe(8)
    forged = FakeNative(**{
        key: getattr(native, key) for key in native.__dataclass_fields__
    })
    relay = observer(clock=ticks(1, 2))
    asyncio.run(relay.observe(forged))
    assert len(relay.views.rows()) in (0, 1)
    assert relay.timer.rows() == ()
    assert len(relay.failures()) >= 1


def test_join_rejects_injected_mismatching_source_without_timing():
    relay = observer(clock=ticks(1, 2))
    original = probe(8)
    bad = replace(original, request_id="bad-unrelated-source")
    asyncio.run(relay.observe(bad))
    assert relay.timer.rows() == ()
    assert len(relay.failures()) == 1
    assert relay.failures()[0].stage == "legacy-admission"


def test_async_await_duration_is_not_cpu_time_or_cognition():
    async def wait(_view):
        await asyncio.sleep(0)

    relay = observer(clock=ticks(100, 200), work=wait)
    asyncio.run(relay.observe(probe(8)))
    assert relay.timer.rows()[0].callback_elapsed_ns == 100
    assert relay.summary()["cognition_time_attested"] is False


def test_no_reader_issuer_or_admission_capability_on_s49_wrapper():
    relay = observer(clock=ticks(1, 2))
    for forbidden in (
        "receive", "send_set_control", "send_observe", "issue_action",
        "grant_action", "commit_learning", "execute", "authorize",
    ):
        assert not hasattr(relay, forbidden)


def test_wrong_timer_self_and_foreign_view_owner_rejected():
    with pytest.raises(S49PassiveClockJoinRejected, match="different Self"):
        S49PassiveHostClockDEV(timer=PassiveHostCallbackTimer(self_id="other"))
    class FakeViews(PassiveSelfViews):
        pass
    with pytest.raises(S49PassiveClockJoinRejected, match="original passive"):
        S49PassiveHostClockDEV(views=FakeViews())


def test_aborted_callback_never_promotes_a_success_receipt():
    async def fail(_view):
        raise RuntimeError("failed passive view")
    relay = observer(clock=ticks(1), work=fail)
    asyncio.run(relay.observe(probe(8)))
    assert relay.summary()["clock_samples"] == 0
    assert relay.summary()["aborted_callbacks"] == 1
    assert relay.summary()["physical_timing_attested"] is False
    assert relay.summary()["s10_updates"] == 0


def test_invalid_sync_observer_return_does_not_block_original_owner():
    relay = observer(clock=ticks(1), work=lambda view: None)
    asyncio.run(relay.observe(probe(8)))
    assert len(relay.views.rows()) == 1
    assert relay.timer.rows() == ()
    assert relay.failures()[0].error_type == "TypeError"
    assert relay.timer.aborted_tickets()


def test_advisory_failure_ledger_is_bounded():
    relay = observer(clock=ticks(1, 2))
    async def run():
        for _ in range(30):
            await relay.observe(probe(8))
    asyncio.run(run())
    assert len(relay.failures()) == MAX_PROBES + 1
    assert relay.summary()["failure_overflow"] == 26
    assert len(relay.timer.rows()) == 1
