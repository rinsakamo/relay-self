"""#632 offline-only producer-local callback timing contract negatives."""
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
