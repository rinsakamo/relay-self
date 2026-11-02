"""S #537 S2-A: passive WB L1 + already-closed S16 -> bounded L2 read port.

Only the ORIGINAL S49 live_probe and NormalSessionActionExecutor closure
callbacks supply data. No model, World reader, S60 acceptance, Action
authority, Memory/Learning/Habit, energy accounting or native writes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.normal_action import NormalActionClosedReadback
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s537_s1_original_wb_m import S1WBMMatchedObserver
from relay_self.action import ActionState
from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.self_cognition_slice import CognitionSlice, CognitionTier

MAX_EPOCHS = 8
MAX_CLOSURES = 3


@dataclass(frozen=True, slots=True)
class S2AReadOnlyInput:
    """Current L1 source at an actual S49 probe, never an L2 recommendation."""

    self_id: str
    session_id: str
    epoch_id: str
    probe_seq: int
    request_id: str
    world_source_ref: str
    body_source_ref: str
    observed_world: tuple[tuple[str, str | None, float | None], ...]
    observed_body: tuple[tuple[str, object], ...]
    preceding_action_id: str | None
    preceding_s16_after_seq: int | None
    preceding_action_source_probe_seq: int | None
    source_attested: bool = False
    action_authority: bool = False
    learning_authority: bool = False
    model_submitted: bool = False

    def bounded_row(self) -> dict[str, object]:
        """Small untrusted input projection; no raw native or owner objects."""
        return {
            "self_id": self.self_id, "session_id": self.session_id,
            "epoch_id": self.epoch_id, "probe_seq": self.probe_seq,
            "request_id": self.request_id,
            "world_source_ref": self.world_source_ref,
            "body_source_ref": self.body_source_ref,
            "observed_world": [
                {"entity_ref": r, "label": label, "distance_m": distance}
                for r, label, distance in self.observed_world
            ],
            "observed_body": [
                {"key": key, "observed_value": value}
                for key, value in self.observed_body
            ],
            "preceding_action_id": self.preceding_action_id,
            "preceding_s16_after_seq": self.preceding_s16_after_seq,
            "preceding_action_source_probe_seq":
                self.preceding_action_source_probe_seq,
            "source_attested": False, "action_authority": False,
            "learning_authority": False, "model_submitted": False,
        }


class S2ASourceBoundObserver(S1WBMMatchedObserver):
    """S1 child with a bounded, host-ordered, model-free S2 input readout."""

    def __init__(self, *, enabled: bool = False) -> None:
        super().__init__(enabled=enabled)
        self._closed: list[NormalActionClosedReadback] = []
        self._inputs: list[S2AReadOnlyInput] = []
        self._closed_action_ids: set[str] = set()
        self._s2_errors: list[str] = []

    def record_error(self, exc: Exception) -> None:
        super().record_error(exc)
        self._s2_errors.append(type(exc).__name__)

    def observe_closed(self, closed: NormalActionClosedReadback) -> None:
        """Called inside original executor AFTER its typed S16 terminal."""
        try:
            self._require_closed(closed)
            self._closed.append(closed)
            self._closed_action_ids.add(closed.terminal.action_id)
        except (ValueError, AttributeError, TypeError) as exc:
            # Original Executor must not be vetoed even by a forged observer.
            self.record_error(exc)

    def _require_closed(self, closed: NormalActionClosedReadback) -> None:
        if not isinstance(closed, NormalActionClosedReadback):
            raise ValueError("real typed S16 closure required")
        owner = closed.terminal
        con = closed.consequence
        interpretation = closed.interpretation
        probe = closed.original_probe
        after = con.after_observation
        before = con.before_observation
        if (
            len(self._closed) >= MAX_CLOSURES
            or not self._observed
            or probe is not self._observed[-1].native_probe
            or not isinstance(after, MineflayerObservation)
            or not isinstance(before, MineflayerObservation)
            or owner.state is not ActionState.OUTCOME
            or interpretation.disposition is not ActionOutcomeDisposition.OUTCOME
            or interpretation.reason_code != "observed_execution"
            or con.status is not WorldConsequenceStatus.EXECUTED
            or interpretation.source_status != con.status.value
            or interpretation.action_id != owner.action_id
            or interpretation.action_id != con.action_id
            or interpretation.session_id != probe.session_id
            or interpretation.world_provenance != con.provenance
            or interpretation.binding_id != con.binding_id
            or interpretation.action_ref != con.action_ref
            or owner.intent_id != interpretation.intent_id
            or owner.skill_execution_id != interpretation.skill_execution_id
            or con.session_id != probe.session_id
            or before.session_id != probe.session_id
            or after.session_id != probe.session_id
            or before.seq != probe.seq
            or after.seq <= before.seq
            or owner.action_id in self._closed_action_ids
            or (
                self._closed and before.seq <=
                self._closed[-1].consequence.after_observation.seq
            )
            or not isinstance(probe.request_id, str)
            or not probe.request_id.startswith(
                f"s49-actual:{probe.session_id}:event-"
            )
            or owner.action_id != (
                "s49-native-move-" + probe.request_id.rsplit("event-", 1)[-1]
            )
        ):
            raise ValueError("S16 closure not ordered against original S49 source")

    def observe(self, reading: MineflayerObservation) -> None:
        """Build the L2 candidate before S49 decides; never query a model."""
        super().observe(reading)
        source = self._observed[-1]
        view = source.wb_slice
        if (
            not isinstance(view, CognitionSlice)
            or view.tier is not CognitionTier.L1
            or len(self._inputs) >= MAX_EPOCHS
            or view.source_attested
            or not view.world_source_ref
            or not view.body_source_ref
            or reading is not source.native_probe
        ):
            raise ValueError("S2-A requires genuine bounded S1 WB L1 input")
        last = self._closed[-1] if self._closed else None
        if last is not None:
            after = last.consequence.after_observation
            if (
                after is None or after.seq >= reading.seq
                or last.original_probe.seq >= reading.seq
            ):
                raise ValueError("S2-A cannot read a future or unfinished S16")
        visible = tuple(
            (v.entity.entity_ref, v.entity.label, v.entity.distance_m)
            for v in view.visible_world
        )
        body = tuple((b.key, b.value) for b in view.body_cues)
        if len(visible) > 3 or len(body) > 4:
            raise ValueError("WB L1 tier budget exceeded")
        self._inputs.append(S2AReadOnlyInput(
            self_id=view.self_id,
            session_id=reading.session_id,
            epoch_id=view.epoch_id,
            probe_seq=reading.seq,
            request_id=reading.request_id,
            world_source_ref=view.world_source_ref,
            body_source_ref=view.body_source_ref,
            observed_world=visible,
            observed_body=body,
            preceding_action_id=(last.terminal.action_id if last else None),
            preceding_s16_after_seq=(
                last.consequence.after_observation.seq if last else None
            ),
            preceding_action_source_probe_seq=(
                last.original_probe.seq if last else None
            ),
        ))

    def s2a_readout(self) -> dict[str, Any]:
        """Post-run audit; never pretend an offline or deferred result is L2."""
        s1 = self.readout
        if (
            self.errors or self._s2_errors
            or not isinstance(s1, dict) or s1.get("status") != "RECORDED"
            or len(self._inputs) != len(self._observed)
            or len(self._inputs) < 2
            or s1.get("session_id") != self._inputs[0].session_id
            or len(self._closed) != sum(
                item["action_id"] is not None
                for item in s1["s49"]["decision_source_ids"]
            )
            or any(
                a.probe_seq != b["probe_seq"]
                or a.request_id != b["request_id"]
                or a.world_source_ref != b["world_source_ref"]
                or a.body_source_ref != b["body_source_ref"]
                for a, b in zip(self._inputs, s1["wb_rows"], strict=True)
            )
        ):
            return {"status": "DEFERRED", "reason": "S2_A_SOURCE_OR_S1_NOT_ADMITTED"}
        for closed in self._closed:
            if not any(
                item.step.action_request_id == closed.terminal.action_id
                and item.action_receipt is not None
                and item.action_receipt.terminal is closed.terminal
                and item.action_receipt.consequence is closed.consequence
                for item in self._completed_source_steps
            ):
                return {
                    "status": "DEFERRED",
                    "reason": "S2_A_ORIGINAL_S16_IDENTITY_NOT_ESTABLISHED",
                }
        ready = sum(item.preceding_action_id is not None for item in self._inputs)
        if ready == 0:
            return {"status": "DEFERRED", "reason": "NO_S16_TO_NEXT_EPOCH"}
        return {
            "schema": "S537_S2A_BOUND_L1_AND_PREVIOUS_S16_DEV_V1",
            "status": "RECORDED",
            "reason": "HOST_ORDERED_READ_ONLY_NO_MODEL",
            "session_id": self._inputs[0].session_id,
            "input_count": len(self._inputs),
            "closed_s16_count": len(self._closed),
            "with_previous_s16": ready,
            "inputs": [entry.bounded_row() for entry in self._inputs],
            "source_attested": False,
            "action_authority": False,
            "learning_authority": False,
            "new_native_reads": 0,
            "new_model_calls": 0,
            "new_action_issues": 0,
            "learning_updates": 0,
            "energy_debits": 0,
            "s60_submissions": 0,
        }

    def completed(self, batch: object) -> None:
        """Retain original typed batch exclusively for end-of-run S16 identity."""
        self._completed_source_steps = (
            batch.steps if hasattr(batch, "steps") else ()
        )
        super().completed(batch)
