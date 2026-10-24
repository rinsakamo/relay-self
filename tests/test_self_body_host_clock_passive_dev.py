"""#632 offline-only producer-local callback timing contract negatives."""
import asyncio
from dataclasses import FrozenInstanceError, replace

import pytest

from experiments.self_body_host_clock_passive_dev import (
    HostClockOrigin,
    PassiveHostCallbackTimer,
    PassiveHostClockRejected,
)
from relay_self.provenance import Provenance
from relay_self.self_body import (
    BodyField,
    BodyObservation,
    SelfBodyView,
    compose_self_body_view,
)


def body(seq=1, *, self_id="s1", session="S", observed=True):
    if not observed:
        obs = None
    else:
        obs = BodyObservation(
            session_id=session, native_seq=seq, request_id=f"probe-{seq}",
            fields=(
                BodyField("position_x", 1.0),
                BodyField("position_y", 64.0),
                BodyField("position_z", 1.0),
            ),
            source_provenance=Provenance("mineflayer", f"{session}:{seq}"),
        )
    return compose_self_body_view(
        self_id=self_id, session_id=session,
        epoch_id=f"epoch-{seq}", observation=obs,
    )


def ticks(*timestamps):
    values = iter(timestamps)
    return lambda: next(values)


def test_synthetic_callback_duration_is_not_physical_dodge_latency():
    meter = PassiveHostCallbackTimer(self_id="s1", clock=ticks(1_000, 501_000))
    ticket = meter.enter(body())
    result = meter.exit(ticket)
    assert result.callback_elapsed_ns == 500_000
    assert result.callback_elapsed_ms == pytest.approx(0.5)
    assert result.origin is HostClockOrigin.SYNTHETIC_DEV_CLOCK
    assert result.sample_kind == "PASSIVE_CALLBACK_PROCESSING_ONLY"
    assert result.action_start_ns is None
    assert result.world_cue_onset_ns is None
    assert result.movement_speed_mps is None
    assert result.real_action_outcome_attested is False
    assert result.allowed_to_act is False
    assert meter.rows() == (result,)


def test_injected_clock_is_never_mislabeled_native_monotonic():
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(10, 10))
    assert m.origin is HostClockOrigin.SYNTHETIC_DEV_CLOCK
    assert m.exit(m.enter(body())).callback_elapsed_ns == 0


def test_default_clock_label_is_python_process_monotonic():
    m = PassiveHostCallbackTimer(self_id="s1")
    assert m.origin is HostClockOrigin.PYTHON_PROCESS_MONOTONIC
    assert m.exit(m.enter(body())).callback_elapsed_ns >= 0


def test_backward_monotonic_time_fails_closed_without_retaining_sample():
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(900, 800))
    with pytest.raises(PassiveHostClockRejected, match="reversed"):
        m.exit(m.enter(body()))
    assert m.rows() == ()


@pytest.mark.parametrize("bad", (-1, True, float("nan"), "123", 2**65))
def test_malformed_clock_sample_is_rejected(bad):
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(bad))
    with pytest.raises(PassiveHostClockRejected, match="clock"):
        m.enter(body())
    assert m.rows() == ()


@pytest.mark.parametrize("bad", (0, -1, 129, True, 1.5))
def test_invalid_capacity_is_rejected(bad):
    with pytest.raises(PassiveHostClockRejected, match="capacity"):
        PassiveHostCallbackTimer(self_id="s1", capacity=bad)


def test_overlapping_and_replayed_ticket_refused():
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(1, 2))
    ticket = m.enter(body())
    with pytest.raises(PassiveHostClockRejected, match="overlapping"):
        m.enter(body(seq=2))
    m.exit(ticket)
    with pytest.raises(PassiveHostClockRejected, match="duplicate"):
        m.exit(ticket)


def test_source_seq_not_a_clock_or_new_duration():
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(5, 9, 10, 13))
    first = m.exit(m.enter(body(seq=1)))
    next_ = m.exit(m.enter(body(seq=9000)))
    assert first.callback_elapsed_ns == 4
    assert next_.callback_elapsed_ns == 3
    assert not hasattr(next_, "world_elapsed_ns")


def test_replayed_source_seq_rejected():
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(0, 1))
    m.exit(m.enter(body(seq=2)))
    with pytest.raises(PassiveHostClockRejected, match="replay"):
        m.enter(body(seq=1))


def test_foreign_session_and_identity_rejected():
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(1, 2))
    m.exit(m.enter(body()))
    with pytest.raises(PassiveHostClockRejected, match="invalid native"):
        m.enter(body(seq=2, session="T"))
    with pytest.raises(PassiveHostClockRejected, match="foreign"):
        m.enter(body(seq=2, self_id="someone-else"))


def test_blank_body_is_unknown_not_timed_from_fabricated_present():
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(1))
    with pytest.raises(PassiveHostClockRejected, match="invalid native"):
        m.enter(body(observed=False))


def test_non_native_provenance_rejected():
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(1))
    view = body()
    obs = replace(
        view.observation,
        source_provenance=Provenance("synthetic-dev", "S:1"),
    )
    with pytest.raises(PassiveHostClockRejected, match="invalid native"):
        m.enter(replace(view, observation=obs))


def test_subclass_cannot_override_observed_body_fields():
    class Substitute(SelfBodyView):
        def observed(self, key):
            return replace(super().observed(key), value=999)

    good = body()
    forged = Substitute(**{
        k: getattr(good, k) for k in good.__dataclass_fields__
    })
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(1))
    with pytest.raises(PassiveHostClockRejected, match="overridden"):
        m.enter(forged)


def test_output_cannot_grant_issued_action_or_native_world_events():
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(10, 20))
    row = m.exit(m.enter(body()))
    for value in (
        {"allowed_to_act": True},
        {"real_action_outcome_attested": True},
        {"action_start_ns": 10},
        {"world_cue_onset_ns": 10},
        {"movement_speed_mps": 5},
        {"sample_kind": "NATIVE_ATTACK_START"},
    ):
        with pytest.raises(PassiveHostClockRejected, match="cannot attest"):
            replace(row, **value)
    with pytest.raises(FrozenInstanceError):
        row.callback_elapsed_ns = 0


def test_bounded_samples_and_immutable_result():
    m = PassiveHostCallbackTimer(
        self_id="s1", capacity=1, clock=ticks(10, 20),
    )
    row = m.exit(m.enter(body()))
    assert m.rows() == (row,)
    with pytest.raises(PassiveHostClockRejected, match="budget"):
        m.enter(body(seq=2))


def test_foreign_or_fabricated_callback_ticket_rejected():
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(10, 20))
    ticket = m.enter(body())
    fake = replace(ticket, entered_ns=11)
    with pytest.raises(PassiveHostClockRejected, match="foreign"):
        m.exit(fake)
    assert m.exit(ticket).callback_elapsed_ns == 10


def test_no_motor_or_native_reader_interface():
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(1, 2))
    for forbidden in (
        "receive", "send_set_control", "issue_action", "grant_action",
        "commit_learning", "update_world", "native_timestamp",
    ):
        assert not hasattr(m, forbidden)


def test_duplicate_probe_request_id_with_advancing_seq_is_rejected():
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(10, 11))
    m.exit(m.enter(body(seq=1)))
    later = body(seq=2)
    stale = replace(
        later.observation, request_id="probe-1",
    )
    with pytest.raises(PassiveHostClockRejected, match="replay"):
        m.enter(replace(later, observation=stale))


def test_failed_callback_aborts_without_emitting_false_success():
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(1, 3, 5))
    ticket = m.enter(body(seq=1))
    m.abort(ticket)
    assert m.rows() == ()
    with pytest.raises(PassiveHostClockRejected, match="duplicate"):
        m.exit(ticket)
    fresh = m.enter(body(seq=2))
    assert m.exit(fresh).callback_elapsed_ns == 2


def test_clock_error_is_terminal_even_if_later_time_would_recover():
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(100, 99, 101))
    ticket = m.enter(body(seq=1))
    with pytest.raises(PassiveHostClockRejected, match="reversed"):
        m.exit(ticket)
    with pytest.raises(PassiveHostClockRejected, match="terminal"):
        m.exit(ticket)
    assert m.rows() == ()


def test_clock_callback_raises_and_never_emits_an_interval():
    def broken_clock():
        raise RuntimeError("no clock")

    m = PassiveHostCallbackTimer(self_id="s1", clock=broken_clock)
    with pytest.raises(PassiveHostClockRejected, match="sampling failed"):
        m.enter(body(seq=1))
    assert m.rows() == ()


def test_cross_process_clock_domain_refused_without_fabricated_time(monkeypatch):
    from experiments.self_body_host_clock_passive_dev import os

    origin_pid = os.getpid()
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(100, 200))
    ticket = m.enter(body(seq=1))
    monkeypatch.setattr(os, "getpid", lambda: origin_pid + 1)
    with pytest.raises(PassiveHostClockRejected, match="cross-process"):
        m.exit(ticket)
    with pytest.raises(PassiveHostClockRejected, match="terminal"):
        m.exit(ticket)
    assert m.rows() == ()


def test_forged_abort_ticket_cannot_erase_actual_callback():
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(100, 200))
    ticket = m.enter(body(seq=1))
    with pytest.raises(PassiveHostClockRejected, match="foreign"):
        m.abort(replace(ticket, native_seq=77))
    assert m.exit(ticket).callback_elapsed_ns == 100


def test_injected_clock_origin_cannot_be_reassigned_by_public_setter():
    m = PassiveHostCallbackTimer(self_id="s1", clock=ticks(10, 20))
    with pytest.raises(AttributeError):
        m.origin = HostClockOrigin.PYTHON_PROCESS_MONOTONIC
    row = m.exit(m.enter(body()))
    assert row.origin is HostClockOrigin.SYNTHETIC_DEV_CLOCK


@pytest.mark.parametrize('failure', [BaseException, KeyboardInterrupt, SystemExit])
def test_base_exception_clock_failure_remains_terminal(failure):
    calls = 0

    def clock():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise failure('clock interrupted')
        return 100

    m = PassiveHostCallbackTimer(self_id='s1', clock=clock)
    with pytest.raises(failure):
        m.enter(body())
    with pytest.raises(PassiveHostClockRejected, match='terminal'):
        m.enter(body())
    assert calls == 1 and m.rows() == ()


def test_aborted_attempt_consumes_budget_and_retains_failure_history():
    m = PassiveHostCallbackTimer(self_id='s1', capacity=1, clock=ticks(1, 2))
    ticket = m.enter(body())
    m.abort(ticket)
    assert m.aborted_tickets() == (ticket,)
    with pytest.raises(PassiveHostClockRejected, match='budget'):
        m.enter(body(seq=2))
    assert m.rows() == ()


def test_later_success_does_not_hide_aborted_source_or_allow_reuse():
    m = PassiveHostCallbackTimer(self_id='s1', clock=ticks(1, 2, 3))
    ticket = m.enter(body())
    m.abort(ticket)
    with pytest.raises(PassiveHostClockRejected, match='replay'):
        m.enter(body())
    m.exit(m.enter(body(seq=2)))
    assert m.aborted_tickets() == (ticket,)
    assert len(m.rows()) == 1


def test_abort_cannot_reset_terminal_clock_fault():
    m = PassiveHostCallbackTimer(self_id='s1', clock=ticks(10, 9, 11))
    ticket = m.enter(body())
    with pytest.raises(PassiveHostClockRejected, match='reversed'):
        m.exit(ticket)
    m.abort(ticket)
    with pytest.raises(PassiveHostClockRejected, match='terminal'):
        m.enter(body(seq=2))
    assert m.rows() == ()


@pytest.mark.parametrize('bad', [-1, True, 1.5, float('nan'), 2**63])
def test_invalid_exit_timestamp_is_terminal_after_abort(bad):
    m = PassiveHostCallbackTimer(self_id='s1', clock=ticks(10, bad, 11))
    ticket = m.enter(body())
    with pytest.raises(PassiveHostClockRejected, match='clock'):
        m.exit(ticket)
    m.abort(ticket)
    with pytest.raises(PassiveHostClockRejected, match='terminal'):
        m.enter(body(seq=2))
    assert m.rows() == ()


def test_observation_subclass_cannot_override_source_reference():
    class Substitute(BodyObservation):
        @property
        def source_ref(self):
            return 'forged-source'

    view = body()
    obs = view.observation
    forged = Substitute(**{k: getattr(obs, k) for k in obs.__dataclass_fields__})
    m = PassiveHostCallbackTimer(self_id='s1', clock=ticks(1, 2))
    with pytest.raises(PassiveHostClockRejected, match='native source'):
        m.enter(replace(view, observation=forged))


@pytest.mark.parametrize('failure', [RuntimeError, BaseException])
def test_failed_exit_clock_cannot_recover(failure):
    calls = 0

    def clock():
        nonlocal calls
        calls += 1
        if calls == 2:
            raise failure('exit failure')
        return calls

    m = PassiveHostCallbackTimer(self_id='s1', clock=clock)
    ticket = m.enter(body())
    expected = PassiveHostClockRejected if failure is RuntimeError else failure
    with pytest.raises(expected):
        m.exit(ticket)
    m.abort(ticket)
    with pytest.raises(PassiveHostClockRejected, match='terminal'):
        m.enter(body(seq=2))
    assert m.rows() == ()


@pytest.mark.parametrize('failure', [RuntimeError, asyncio.CancelledError,
                                     KeyboardInterrupt, SystemExit])
def test_future_async_owner_aborts_all_callback_base_exceptions(failure):
    m = PassiveHostCallbackTimer(self_id='s1', clock=ticks(1))

    async def owner():
        ticket = m.enter(body())
        try:
            raise failure('callback stopped')
        except BaseException:
            m.abort(ticket)
            raise
        else:
            m.exit(ticket)

    with pytest.raises(failure):
        asyncio.run(owner())
    assert m.rows() == ()
    assert len(m.aborted_tickets()) == 1


def test_wrong_source_reference_and_session_pair_rejected():
    view = body()
    m = PassiveHostCallbackTimer(self_id='s1', clock=ticks(1))
    for obs in (
        replace(view.observation, source_provenance=Provenance('mineflayer', 'T:1')),
        replace(view.observation, session_id='T'),
    ):
        with pytest.raises(PassiveHostClockRejected, match='native source'):
            m.enter(replace(view, observation=obs))
