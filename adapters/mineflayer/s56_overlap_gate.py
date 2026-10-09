"""S56 observed L2-inflight / physical L0 closure overlap witness.

No test-server delays. Thread-safe host timings and bounded negative gates.
The caller owns native verified Action OUTCOME, native World identity, separate
Action admission and actual backend model attestation. This witness grants none.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum


class OverlapDenied(ValueError):
    """Missing or false physical L0 / active model chronology."""


class OverlapStage(str, Enum):
    NEW = "NEW"
    MODEL_ENTERED = "MODEL_ENTERED"
    L0_ENTERED = "L0_ENTERED"
    L0_CLOSED = "L0_CLOSED"


@dataclass(frozen=True, slots=True)
class OverlapReceipt:
    l2_start_ns: int
    l0_enter_ns: int
    l0_closed_ns: int
    l2_end_ns: int | None
    l0_action_id: str
    physical_movement_m: float

    @property
    def proven_overlap(self) -> bool:
        return (
            self.l2_start_ns < self.l0_enter_ns < self.l0_closed_ns
            and (self.l2_end_ns is None or self.l0_closed_ns < self.l2_end_ns)
            and self.physical_movement_m >= 0.05
        )


class L0ModelOverlap:
    """One model-call attempt, one matching native-World Action receipt."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.started = threading.Event()
        self.finished = threading.Event()
        self.stage = OverlapStage.NEW
        self.l2_start_ns: int | None = None
        self.l2_end_ns: int | None = None
        self.l0_enter_ns: int | None = None
        self.l0_closed_ns: int | None = None
        self.action_id: str | None = None
        self.physical_movement_m: float | None = None
        self.provider_attempt_count = 0

    def model_enter(self) -> None:
        with self.lock:
            if self.stage is not OverlapStage.NEW:
                raise OverlapDenied("only one model attempt in the session")
            self.l2_start_ns = time.monotonic_ns()
            self.provider_attempt_count += 1
            self.stage = OverlapStage.MODEL_ENTERED
            self.started.set()

    def model_exit(self) -> None:
        with self.lock:
            if self.l2_start_ns is None or self.l2_end_ns is not None:
                raise OverlapDenied("missing or repeated model-exit witness")
            self.l2_end_ns = time.monotonic_ns()
            self.finished.set()

    def l0_enter(self, *, action_id: str) -> None:
        with self.lock:
            if (
                self.stage is not OverlapStage.MODEL_ENTERED
                or self.l2_start_ns is None
                or self.l2_end_ns is not None
                or not isinstance(action_id, str)
                or not action_id
            ):
                raise OverlapDenied("L0 must start during ongoing model call")
            self.l0_enter_ns = time.monotonic_ns()
            self.action_id = action_id
            self.stage = OverlapStage.L0_ENTERED

    def l0_closed(self, *, action_id: str, movement_m: float) -> OverlapReceipt:
        with self.lock:
            if (
                self.stage is not OverlapStage.L0_ENTERED
                or self.l0_enter_ns is None
                or self.l2_start_ns is None
                or self.l2_end_ns is not None
                or action_id != self.action_id
                or type(movement_m) not in (int, float)
                or not 0.05 <= movement_m <= 20
            ):
                raise OverlapDenied("not a terminal physically measured live-L0 Action")
            self.l0_closed_ns = time.monotonic_ns()
            self.physical_movement_m = movement_m
            self.stage = OverlapStage.L0_CLOSED
            receipt = self._receipt_unlocked()
            if not receipt.proven_overlap:
                raise OverlapDenied("model provider finished before L0 outcome")
            return receipt

    def _receipt_unlocked(self) -> OverlapReceipt:
        if (
            self.l2_start_ns is None or self.l0_enter_ns is None
            or self.l0_closed_ns is None or self.action_id is None
            or self.physical_movement_m is None
        ):
            raise OverlapDenied("incomplete overlap evidence")
        return OverlapReceipt(
            self.l2_start_ns, self.l0_enter_ns, self.l0_closed_ns,
            self.l2_end_ns, self.action_id, self.physical_movement_m,
        )

    def receipt(self) -> OverlapReceipt:
        with self.lock:
            if self.stage is not OverlapStage.L0_CLOSED:
                raise OverlapDenied("physical Action closure absent")
            return self._receipt_unlocked()
