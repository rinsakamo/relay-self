"""S59-B purely deterministic stop-ACK contract tests, not real backend stops."""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.s59b_stop_ack_contract import (
    NativeStopAck,
    NativeStopLedger,
    NativeStopRejected,
    NativeStopStage,
    NativeStopSubject,
)


def subject() -> NativeStopSubject:
    return NativeStopSubject(
        owner_session="self-native-one",
        work_id="l2-fully-bound-work",
        completion_id="chatcmpl-active-A",
        work_generation=3,
        backend_pid=67890,
        slot_id=0,
        slot_generation=2,
        world_seq=19,
    )


def prepare() -> tuple[NativeStopLedger, NativeStopSubject]:
    key = subject()
    ledger = NativeStopLedger(key)
    ledger.started(time_ns=100)
    ledger.progress(time_ns=150, generated_tokens=13)
    ledger.request_stop(key, time_ns=180, authorized_by="independent-operator")
    return ledger, key


def ack(key: NativeStopSubject) -> NativeStopAck:
    return NativeStopAck(
        subject=key,
        timestamp_ns=200,
        native_worker_id="llama-worker-1",
        native_task_id=2000,
        acknowledged_request_id=key.completion_id,
        processed=True,
        slot_released=True,
        source="native-backend-worker",
    )


def test_positive_fixture_qualifies_contract_only_not_physical_stop():
    ledger, key = prepare()
    ledger.accept_native_ack(ack(key))
    ledger.observe_slot_idle(
        key, time_ns=240, backend_pid_alive=key.backend_pid,
        source="independent-backend-slot-observer", generated_tokens_after_ack=15,
    )
    ledger.admit_reused_slot(
        time_ns=300, same_live_pid=key.backend_pid,
        slot_id=key.slot_id, new_slot_generation=3,
        new_completion_id="chatcmpl-new-B", completed_generated_tokens=8,
        source="independent-backend-slot-observer",
    )
    receipt = ledger.snapshot()
    assert ledger.stage is NativeStopStage.SLOT_REUSED
    assert receipt["same_process_slot_reuse_contract_met"] is True
    assert receipt["native_worker_ack_recorded"] is True
    assert receipt["physical_qualification"] is False
    assert receipt["runtime_stop_command_sent"] is False
    assert receipt["in_flight_backend_preemption_qualified"] is False
    assert receipt["gpu_compute_quiescence_observed"] is False
    assert receipt["dynamic_vram_release_observed"] is False


@pytest.mark.parametrize("wrong", [
    {"owner_session": "other-session"},
    {"completion_id": "chatcmpl-other"},
    {"work_id": "foreign"},
    {"work_generation": 4},
    {"backend_pid": 123},
    {"slot_id": 1},
    {"slot_generation": 5},
    {"world_seq": 20},
])
def test_wrong_exact_authority_coordinate_denied(wrong):
    ledger, key = prepare()
    with pytest.raises(NativeStopRejected):
        ledger.accept_native_ack(ack(replace(key, **wrong)))


def test_host_cancel_or_http_close_is_not_native_ack():
    ledger, key = prepare()
    with pytest.raises(NativeStopRejected):
        ledger.accept_native_ack(
            replace(ack(key), source="python-task-cancel"),
        )
    with pytest.raises(NativeStopRejected):
        ledger.accept_native_ack(
            replace(ack(key), source="http-socket-closed"),
        )
    assert ledger.snapshot()["native_worker_ack_recorded"] is False


def test_enqueue_ack_does_not_equal_processed_slot_release():
    ledger, key = prepare()
    with pytest.raises(NativeStopRejected):
        ledger.accept_native_ack(replace(ack(key), processed=False))
    with pytest.raises(NativeStopRejected):
        ledger.accept_native_ack(replace(ack(key), slot_released=False))


def test_natural_completion_before_interrupt_cannot_stop():
    ledger = NativeStopLedger(subject())
    ledger.started(time_ns=100)
    ledger.progress(time_ns=120, generated_tokens=3)
    ledger.natural_completion()
    with pytest.raises(NativeStopRejected):
        ledger.request_stop(subject(), time_ns=130, authorized_by="independent-operator")


def test_cannot_stop_without_observed_native_generation_progress():
    ledger = NativeStopLedger(subject())
    ledger.started(time_ns=100)
    with pytest.raises(NativeStopRejected):
        ledger.request_stop(subject(), time_ns=150, authorized_by="independent-operator")


def test_stop_request_must_be_independently_authorized():
    ledger = NativeStopLedger(subject())
    ledger.started(time_ns=100)
    ledger.progress(time_ns=130, generated_tokens=5)
    with pytest.raises(NativeStopRejected):
        ledger.request_stop(
            subject(), time_ns=150, authorized_by="model-output",
        )


def test_no_duplicate_ack_stop_or_stale_completion():
    ledger, key = prepare()
    with pytest.raises(NativeStopRejected):
        ledger.request_stop(key, time_ns=181, authorized_by="independent-operator")
    ledger.accept_native_ack(ack(key))
    with pytest.raises(NativeStopRejected):
        ledger.accept_native_ack(ack(key))
    with pytest.raises(NativeStopRejected):
        ledger.progress(time_ns=220, generated_tokens=99)


def test_no_early_ack_or_reversed_monotonic_clock():
    ledger, key = prepare()
    with pytest.raises(NativeStopRejected):
        ledger.accept_native_ack(replace(ack(key), timestamp_ns=175))
    assert ledger.stage is NativeStopStage.STOP_REQUESTED


def test_idle_observation_cannot_substitute_missing_native_ack():
    ledger, key = prepare()
    with pytest.raises(NativeStopRejected):
        ledger.observe_slot_idle(
            key, time_ns=250, backend_pid_alive=key.backend_pid,
            source="independent-backend-slot-observer",
            generated_tokens_after_ack=15,
        )


def test_backend_pid_replacement_cannot_claim_same_server_slot_reuse():
    ledger, key = prepare()
    ledger.accept_native_ack(ack(key))
    with pytest.raises(NativeStopRejected):
        ledger.observe_slot_idle(
            key, time_ns=230, backend_pid_alive=12345,
            source="independent-backend-slot-observer",
            generated_tokens_after_ack=15,
        )


@pytest.mark.parametrize("bad", [
    {"slot_id": 1},
    {"same_live_pid": 123456},
    {"new_slot_generation": 2},
    {"new_completion_id": "chatcmpl-active-A"},
    {"completed_generated_tokens": 0},
    {"source": "http-observer"},
])
def test_reuse_fails_for_wrong_slot_pid_generation_or_observer(bad):
    ledger, key = prepare()
    ledger.accept_native_ack(ack(key))
    ledger.observe_slot_idle(
        key, time_ns=240, backend_pid_alive=key.backend_pid,
        source="independent-backend-slot-observer",
        generated_tokens_after_ack=15,
    )
    props = {
        "time_ns": 300, "same_live_pid": key.backend_pid, "slot_id": 0,
        "new_slot_generation": 3, "new_completion_id": "chatcmpl-new-B",
        "completed_generated_tokens": 8,
        "source": "independent-backend-slot-observer",
    }
    props.update(bad)
    with pytest.raises(NativeStopRejected):
        ledger.admit_reused_slot(**props)


def test_invalid_subject_cannot_enter_contract():
    with pytest.raises(NativeStopRejected):
        replace(subject(), backend_pid=0)
    with pytest.raises(NativeStopRejected):
        replace(subject(), work_generation=True)
    with pytest.raises(NativeStopRejected):
        replace(subject(), completion_id="")


def test_invalid_stop_ack_evidence_rejected_before_state_mutation():
    ledger, key = prepare()
    with pytest.raises(NativeStopRejected):
        ledger.accept_native_ack(
            replace(ack(key), acknowledged_request_id="unrelated-completion"),
        )
    assert ledger.native_ack is None
    assert ledger.stage is NativeStopStage.STOP_REQUESTED
