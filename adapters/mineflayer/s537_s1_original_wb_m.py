"""S #537 S1: source-joined WB L1 + M originals beside unchanged live S49.

Every World probe originates at the existing S49 live_probe callback.
The original S49 completed_l0 callback occurs after original S16 closure.
This reader neither requests observations nor issues or vetoes Actions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s49_completed_decision_bridge import S49OriginalCompletedBatch
from adapters.mineflayer.s49_owner_cognition_join import (
    bounded_s49_cognition_join_row,
    join_completed_s49_cognition,
)
from adapters.mineflayer.self_body_projection import project_body_present
from adapters.mineflayer.self_world_projection import project_self_world_present
from relay_self.self_body import compose_self_body_view
from relay_self.self_world import compose_self_world_view

_SELF = "self-s537-s1-native"
_LIMIT = 8


@dataclass(frozen=True, slots=True)
class S1SourceObservation:
    """Exact original source object, plus original WB owner projection."""

    native_probe: MineflayerObservation
    wb_slice: object


class S1WBMMatchedObserver:
    """Single-use source observer, never a replacement S49 Action owner."""

    def __init__(self, *, enabled: bool = False) -> None:
        if enabled is not True:
            raise ValueError("S1 explicitly enabled DEV-only observer required")
        from experiments.metabolism_s49_owner_admission import S49MAdmissionLease

        self._m_lease = S49MAdmissionLease(enabled=True, max_batches=1)
        self._session: str | None = None
        self._observed: list[S1SourceObservation] = []
        self.errors: list[str] = []
        self.completed_callbacks = 0
        self.readout: dict[str, Any] | None = None

    def record_error(self, exc: Exception) -> None:
        """Optional observer errors must never interrupt original L0."""
        self.errors.append(type(exc).__name__)

    def observe(self, reading: MineflayerObservation) -> None:
        """Called after S49 correlated native probe, before L0 decision."""
        from relay_self.self_cognition_slice import (
            CognitionTier,
            project_cognition_slice,
        )

        if (
            not isinstance(reading, MineflayerObservation)
            or reading.kind != "probe"
            or len(self._observed) >= _LIMIT
            or not isinstance(reading.session_id, str)
            or not reading.session_id
            or self._session not in (None, reading.session_id)
            or not isinstance(reading.request_id, str)
            or not reading.request_id.startswith(
                f"s49-actual:{reading.session_id}:event-"
            )
            or (
                self._observed
                and reading.seq <= self._observed[-1].native_probe.seq
            )
        ):
            raise ValueError("foreign, replayed or excess original probe")
        present = project_mineflayer_present(reading)
        epoch = f"native-{reading.seq}"
        body = compose_self_body_view(
            self_id=_SELF, session_id=reading.session_id, epoch_id=epoch,
            observation=project_body_present(present),
        )
        world = compose_self_world_view(
            self_id=_SELF, session_id=reading.session_id, epoch_id=epoch,
            observation=project_self_world_present(present, observer_id=_SELF),
            self_body=body,
        )
        slice_ = project_cognition_slice(world, tier=CognitionTier.L1)
        expected_world = (
            f"present:{reading.session_id}:{reading.seq}:{reading.request_id}"
        )
        expected_body = (
            f"native-probe:{reading.session_id}:{reading.seq}:{reading.request_id}"
        )
        if (
            world.self_body is not body
            or slice_.world_source_ref != expected_world
            or slice_.body_source_ref != expected_body
            or slice_.source_attested
            or slice_.tier is not CognitionTier.L1
            or slice_.session_id != reading.session_id
            or slice_.self_id != _SELF
            or slice_.epoch_id != epoch
        ):
            raise ValueError("WB L1 original native source mismatch")
        self._session = reading.session_id
        self._observed.append(S1SourceObservation(reading, slice_))

    def completed(self, batch: S49OriginalCompletedBatch) -> None:
        """After S49 original S16; capture only bounded DEV source evidence."""
        self.completed_callbacks += 1
        if self.completed_callbacks != 1:
            self.readout = {"status": "DEFERRED", "reason": "duplicate_callback"}
            return
        try:
            from relay_self.self_cognition_slice import CognitionSlice, CognitionTier

            if (
                self.errors
                or not isinstance(batch, S49OriginalCompletedBatch)
                or batch.session_id != self._session
                or len(batch.steps) != len(self._observed)
                or not 1 <= len(batch.steps) <= _LIMIT
            ):
                raise ValueError("original batch and observed WB source mismatch")
            rows: list[dict[str, object]] = []
            for source, captured in zip(batch.steps, self._observed, strict=True):
                probe, view = captured.native_probe, captured.wb_slice
                expected_world = (
                    f"present:{probe.session_id}:{probe.seq}:{probe.request_id}"
                )
                expected_body = (
                    f"native-probe:{probe.session_id}:{probe.seq}:{probe.request_id}"
                )
                if (
                    source.probe is not probe
                    or not isinstance(view, CognitionSlice)
                    or view.tier is not CognitionTier.L1
                    or view.self_id != _SELF
                    or view.session_id != batch.session_id
                    or view.epoch_id != f"native-{probe.seq}"
                    or view.world_source_ref != expected_world
                    or view.body_source_ref != expected_body
                    or view.source_attested
                ):
                    raise ValueError("WB probe identity or native source mismatch")
                rows.append({
                    "probe_seq": probe.seq,
                    "request_id": probe.request_id,
                    "world_source_ref": view.world_source_ref,
                    "body_source_ref": view.body_source_ref,
                    "world_status": view.world_status,
                    "body_status": view.body_status,
                    "tier": view.tier.value,
                    "world_cues": len(view.visible_world),
                    "body_cues": len(view.body_cues),
                })
            # At least one genuine next original cognition epoch after S16
            # closure: the second original MOVE has a later third decision.
            next_after = []
            for previous, following in zip(batch.steps, batch.steps[1:]):
                receipt = previous.action_receipt
                if receipt is None:
                    continue
                after = receipt.consequence.after_observation
                if (
                    not isinstance(after, MineflayerObservation)
                    or after.session_id != batch.session_id
                    or after.seq >= following.probe.seq
                ):
                    raise ValueError("next native probe is not after original S16")
                next_after.append({
                    "action_id": receipt.terminal.action_id,
                    "s16_after_seq": after.seq,
                    "next_probe_seq": following.probe.seq,
                })
            if not next_after:
                raise ValueError("no original S16 to subsequent epoch evidence")
            m = self._m_lease.admit_batch(batch)
            joined = join_completed_s49_cognition(
                enabled=True, batch=batch, m_admission=m,
            )
            if (
                m.status != "RECORDED"
                or joined.status != "RECORDED"
                or joined.m_status != "ORIGINAL_PYTHON_BATCH_RECORDED"
                or len(joined.decisions) != len(rows)
            ):
                raise ValueError("original M admission or S postowner join missing")
            self.readout = {
                "schema": "S537_S1_WB_M_ORIGINAL_SOURCE_DEV_V1",
                "status": "RECORDED",
                "reason": "same_original_S49_postowner_and_WB_predecision_sources",
                "session_id": batch.session_id,
                "s49": bounded_s49_cognition_join_row(joined),
                "wb_status": "L1_SOURCE_BOUND_PRESENT_READ_ONLY",
                "wb_rows": rows,
                "m_status": m.status,
                "s16_to_next_epoch": next_after,
                "source_attested": False,
                "action_authority": False,
                "model_usage": "UNKNOWN_NO_METER",
                "new_native_reads": 0,
                "new_model_calls": 0,
                "new_action_issues": 0,
                "learning_updates": 0,
                "energy_debits": 0,
            }
        except (ValueError, AttributeError, TypeError, ImportError, KeyError):
            self.readout = {
                "status": "DEFERRED",
                "reason": "cross_owner_original_source_not_admitted",
            }
