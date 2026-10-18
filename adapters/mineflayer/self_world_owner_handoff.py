"""Stage O DEV-only exact S49 retained owner identity readback.

This is a witness of the *original live L0 owner snapshot* being reused as
a read-only cognition input in subsequent source epochs. It is deliberately
not a LearningUpdateAuthority, a copy, a new persistent store, a new L0
policy, or proof of physical adaptation. The S49 original remains owner.
"""
from __future__ import annotations

from typing import Any

from adapters.mineflayer.normal_action import NormalRetainedOwnerReadback
from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.epoch_continuation import read_retained_preference
from relay_self.learning import LearningPreferenceState
from relay_self.provenance import Provenance


class StageOOwnerReadback:
    def __init__(self) -> None:
        self._original: LearningPreferenceState | None = None
        self._session: str | None = None
        self._intent: str | None = None
        self._source_rows: list[dict[str, Any]] = []
        self._last_seq: int = -1
        self._errors: list[str] = []

    def receive_original_owner(self, row: NormalRetainedOwnerReadback) -> None:
        """Called only from the *original* NormalWorldL0 constructor."""
        if not isinstance(row, NormalRetainedOwnerReadback):
            raise TypeError("original L0 retained owner readback required")
        if self._original is not None:
            raise ValueError("no duplicate L0 retained owner handoff")
        if (not row.session_id or row.intent_id != "escape-threat"
                or not isinstance(row.owner_snapshot, LearningPreferenceState)
                or row.owner_snapshot.target_id != "risk_weight"):
            raise ValueError("foreign or non-S49 S10 retained owner")
        read = read_retained_preference(
            row.owner_snapshot, row.owner_snapshot,
            required_target_id="risk_weight",
            expected_revision=row.owner_snapshot.revision,
            provenance=Provenance(
                "selfworld-stage-o-owner-read", f"{row.session_id}:initial",
            ),
        )
        if read.snapshot is not row.owner_snapshot:
            raise ValueError("S49 owner identity changed during handoff")
        self._session = row.session_id
        self._intent = row.intent_id
        self._original = row.owner_snapshot

    def observe_existing_probe(self, reading: MineflayerObservation) -> None:
        """No new probe: reads the same owner for each S49 source epoch."""
        owner, sid = self._original, self._session
        if owner is None or sid is None:
            raise ValueError("original S49 owner not captured")
        if not isinstance(reading, MineflayerObservation):
            raise TypeError("original native probe required")
        prefix = f"s49-actual:{sid}:event-"
        if (
            reading.session_id != sid
            or reading.kind != "probe"
            or reading.provenance.source != "mineflayer"
            or not isinstance(reading.request_id, str)
            or not reading.request_id.startswith(prefix)
            or not reading.request_id[len(prefix):].isdecimal()
            or reading.seq <= self._last_seq
        ):
            raise ValueError("foreign, stale or uncorrelated existing S49 source")
        read = read_retained_preference(
            owner, owner, required_target_id=owner.target_id,
            expected_revision=owner.revision,
            provenance=Provenance(
                "selfworld-stage-o-owner-read", f"{sid}:{reading.seq}",
            ),
        )
        if read.snapshot is not owner:
            raise ValueError("owner identity replaced")
        self._last_seq = reading.seq
        self._source_rows.append({
            "source_probe_seq": reading.seq,
            "source_request_id": reading.request_id,
            "source_session": sid,
            "retained_target": owner.target_id,
            "retained_revision": read.revision,
            "retained_value": owner.value,
            "exact_original_owner_identity": True,
            "read_only": True,
        })

    def record_error(self, phase: str, error: Exception) -> None:
        self._errors.append(f"{phase}:{type(error).__name__}")

    def summary(self) -> dict[str, Any]:
        owner = self._original
        return {
            "kind": "stage_o_original_owner_readback",
            "classification": "DEV_ONLY_ORIGINAL_OWNER_READ_ONLY",
            "session_id": self._session,
            "intent_id": self._intent,
            "captured_original_l0_retained_identity": owner is not None,
            "source_read_count": len(self._source_rows),
            "original_owner_target": owner.target_id if owner else None,
            "original_owner_revision": owner.revision if owner else None,
            "original_owner_value": owner.value if owner else None,
            "same_owner_source_reads": list(self._source_rows),
            "observer_errors": list(self._errors),
            "s10_update_authority": False,
            "s10_commits": 0,
            "s49_l0_retained_mutated": False,
            "next_epoch_learned_action": False,
            "additional_native_actions": 0,
        }
