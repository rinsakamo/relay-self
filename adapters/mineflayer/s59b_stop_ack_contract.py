"""S59-B synthetic contract for request-scoped native backend stop evidence.

This is *not* a connector, interrupt sender, llama.cpp protocol endpoint,
GPU monitor or runtime-identity attestation. Untrusted clients could invent
these records. Physical qualification requires separately observed backend
worker events bound to the actual server/model binary and process.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NativeStopRejected(ValueError):
    """Missing, late, foreign or stage-inconsistent native stop evidence."""


@dataclass(frozen=True, slots=True)
class NativeStopSubject:
    owner_session: str
    work_id: str
    completion_id: str
    work_generation: int
    backend_pid: int
    native_task_id: int
    slot_id: int
    slot_generation: int
    world_seq: int

    def __post_init__(self) -> None:
        if (
            not all(
                isinstance(v, str) and 0 < len(v) <= 256
                for v in (self.owner_session, self.work_id, self.completion_id)
            )
            or any(
                type(v) is not int or v < 0 for v in (
                    self.work_generation, self.slot_id,
                    self.slot_generation, self.world_seq,
                )
            )
            or self.work_generation == 0
            or self.slot_generation == 0
            or type(self.backend_pid) is not int
            or self.backend_pid <= 0
            or type(self.native_task_id) is not int
            or self.native_task_id <= 0
        ):
            raise NativeStopRejected("complete exact request/session/PID/slot binding required")


class NativeStopStage(str, Enum):
    ADMITTED = "ADMITTED"
    GENERATING = "GENERATING"
    STOP_REQUESTED = "STOP_REQUESTED"
    NATIVE_ACK = "NATIVE_ACK"
    SLOT_IDLE = "SLOT_IDLE"
    SLOT_REUSED = "SLOT_REUSED"


@dataclass(frozen=True, slots=True)
class NativeStopAck:
    subject: NativeStopSubject
    timestamp_ns: int
    native_worker_id: str
    native_task_id: int
    acknowledged_request_id: str
    processed: bool
    slot_released: bool
    source: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.subject, NativeStopSubject)
            or type(self.timestamp_ns) is not int or self.timestamp_ns <= 0
            or not isinstance(self.native_worker_id, str)
            or not self.native_worker_id
            or type(self.native_task_id) is not int or self.native_task_id <= 0
            or not isinstance(self.acknowledged_request_id, str)
            or not self.acknowledged_request_id
            or type(self.processed) is not bool
            or type(self.slot_released) is not bool
            or self.source != "native-backend-worker"
        ):
            raise NativeStopRejected("worker-authored exact ACK, not transport closure, required")


class NativeStopLedger:
    """Enforces order/identity; cannot independently attest evidence provenance."""

    def __init__(self, subject: NativeStopSubject) -> None:
        if not isinstance(subject, NativeStopSubject):
            raise NativeStopRejected("typed native stop subject required")
        self.subject = subject
        self.stage = NativeStopStage.ADMITTED
        self.start_ns: int | None = None
        self.progress_ns: int | None = None
        self.generated_before_stop = 0
        self.stop_request_ns: int | None = None
        self.native_ack: NativeStopAck | None = None
        self.idle_ns: int | None = None
        self.reuse_ns: int | None = None
        self.natural_completion_observed = False
        self.gpu_compute_quiescence_observed = False
        self.dynamic_vram_release_observed = False

    @staticmethod
    def _time(value: int, after: int | None) -> None:
        if (
            type(value) is not int or value <= 0
            or (after is not None and value <= after)
        ):
            raise NativeStopRejected("strictly advancing one-host monotonic timestamps required")

    def started(self, *, time_ns: int) -> None:
        if self.stage is not NativeStopStage.ADMITTED:
            raise NativeStopRejected("generation may start once")
        self._time(time_ns, None)
        self.start_ns = time_ns
        self.stage = NativeStopStage.GENERATING

    def progress(self, *, time_ns: int, generated_tokens: int) -> None:
        if (
            self.stage is not NativeStopStage.GENERATING
            or self.natural_completion_observed
            or type(generated_tokens) is not int
            or generated_tokens <= self.generated_before_stop
        ):
            raise NativeStopRejected("fresh native token progress during active generation required")
        self._time(time_ns, self.progress_ns or self.start_ns)
        self.progress_ns = time_ns
        self.generated_before_stop = generated_tokens

    def natural_completion(self) -> None:
        if self.stage not in (
            NativeStopStage.ADMITTED, NativeStopStage.GENERATING,
        ):
            raise NativeStopRejected("cannot forge a natural completion after STOP")
        self.natural_completion_observed = True

    def request_stop(
        self, subject: NativeStopSubject, *,
        time_ns: int, authorized_by: str,
    ) -> None:
        if (
            subject != self.subject
            or self.stage is not NativeStopStage.GENERATING
            or self.progress_ns is None
            or self.natural_completion_observed
            or authorized_by != "independent-operator"
        ):
            raise NativeStopRejected("only live exact authorized request may stop")
        self._time(time_ns, self.progress_ns)
        self.stop_request_ns = time_ns
        self.stage = NativeStopStage.STOP_REQUESTED

    def accept_native_ack(self, ack: NativeStopAck) -> None:
        if (
            self.stage is not NativeStopStage.STOP_REQUESTED
            or not isinstance(ack, NativeStopAck)
            or ack.subject != self.subject
            or ack.acknowledged_request_id != self.subject.completion_id
            or ack.native_task_id != self.subject.native_task_id
            or not ack.processed
            or not ack.slot_released
        ):
            raise NativeStopRejected("native worker release ACK for exact request absent")
        self._time(ack.timestamp_ns, self.stop_request_ns)
        self.native_ack = ack
        self.stage = NativeStopStage.NATIVE_ACK

    def observe_slot_idle(
        self, subject: NativeStopSubject, *,
        time_ns: int,
        backend_pid_alive: int,
        source: str,
        generated_tokens_after_ack: int,
    ) -> None:
        if (
            self.stage is not NativeStopStage.NATIVE_ACK
            or subject != self.subject
            or type(backend_pid_alive) is not int
            or backend_pid_alive != self.subject.backend_pid
            or source != "independent-backend-slot-observer"
            or type(generated_tokens_after_ack) is not int
            or generated_tokens_after_ack < 0
            or generated_tokens_after_ack < self.generated_before_stop
        ):
            raise NativeStopRejected("native slot idle with same live backend PID required")
        self._time(time_ns, self.native_ack.timestamp_ns if self.native_ack else None)
        # Sampling later may include tokens generated between the last pre-stop
        # observation and ACK. This is NOT proof of post-ACK inference.
        self.idle_ns = time_ns
        self.stage = NativeStopStage.SLOT_IDLE

    def admit_reused_slot(
        self, *,
        time_ns: int,
        same_live_pid: int,
        slot_id: int,
        new_slot_generation: int,
        new_completion_id: str,
        completed_generated_tokens: int,
        source: str,
    ) -> None:
        if (
            self.stage is not NativeStopStage.SLOT_IDLE
            or type(same_live_pid) is not int
            or same_live_pid != self.subject.backend_pid
            or type(slot_id) is not int
            or slot_id != self.subject.slot_id
            or type(new_slot_generation) is not int
            or new_slot_generation <= self.subject.slot_generation
            or not isinstance(new_completion_id, str)
            or not new_completion_id
            or new_completion_id == self.subject.completion_id
            or type(completed_generated_tokens) is not int
            or completed_generated_tokens <= 0
            or source != "independent-backend-slot-observer"
        ):
            raise NativeStopRejected("different completion using same live PID/slot required")
        self._time(time_ns, self.idle_ns)
        self.reuse_ns = time_ns
        self.stage = NativeStopStage.SLOT_REUSED

    def snapshot(self) -> dict[str, object]:
        """A synthetic evidence-contract witness, not a physical qualification."""
        return {
            "milestone": "S59-B",
            "classification": "SYNTHETIC_BACKEND_STOP_ACK_CONTRACT_ONLY",
            "stage": self.stage.value,
            "completion_id": self.subject.completion_id,
            "work_generation": self.subject.work_generation,
            "slot_generation": self.subject.slot_generation,
            "backend_pid": self.subject.backend_pid,
            "native_task_id": self.subject.native_task_id,
            "generated_tokens_observed_before_stop": self.generated_before_stop,
            "stop_request_recorded": self.stop_request_ns is not None,
            "native_worker_ack_recorded": self.native_ack is not None,
            "same_process_slot_reuse_contract_met": (
                self.stage is NativeStopStage.SLOT_REUSED
            ),
            "gpu_compute_quiescence_observed": self.gpu_compute_quiescence_observed,
            "dynamic_vram_release_observed": self.dynamic_vram_release_observed,
            "runtime_stop_command_sent": False,
            "physical_qualification": False,
            "in_flight_backend_preemption_qualified": False,
        }
