"""M #616: source-bound original S49 S14 planned coordinator intake (DEV).

A separate S owner supplies its already-executed post-Action epoch. M does
not re-run _native_epoch_two, create a S42 owner, mint model usage or debit
metabolic energy. All old M #683 readouts remain separate, unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from experiments.metabolism_s49_original_owner_receipts import (
    bounded_original_s49_owner_receipt_row,
    observe_original_s49_s16_receipts,
)
from experiments.metabolism_s49_owner_admission import (
    S49MAdmissionReadout,
    admit_original_s49_batch,
    bounded_s49_m_admission_row,
)

JoinStatus = Literal["DISABLED", "RECORDED", "DEFERRED"]


@dataclass(frozen=True, slots=True)
class S49MS14PlannedObservation:
    status: JoinStatus
    reason: str
    original_planned: object | None = None
    session_id: str | None = None
    action_rows: tuple[tuple[str, int, int, int], ...] = ()
    source_attested: bool = False
    action_authority: bool = False


def observe_s49_s14_planned(
    *,
    enabled: bool = False,
    original_l0: object,
    original_planned: object,
    m_admission_row: object,
    m_s16_row: object,
) -> S49MS14PlannedObservation:
    """Validate the two *different wrapper batches* but identical owner refs.

    S49 independently constructs the completed_l0 and completed_planned batch
    wrappers. Object identity holds for every inner step/probe/S16 original,
    not for those two freshly constructed wrapper objects. Any mismatch is
    atomic DEFERRED with no partial Action or epoch exposure.
    """
    if type(enabled) is not bool or not enabled:
        return S49MS14PlannedObservation("DISABLED", "not_enabled")
    try:
        from adapters.mineflayer.s49_completed_decision_bridge import (
            S49OriginalCompletedBatch,
        )
        from adapters.mineflayer.s49_original_planned_postaction import (
            S49OriginalPlannedBatch,
            bind_original_s49_planned,
            bounded_original_s49_planned_row,
        )

        if (
            not isinstance(original_l0, S49OriginalCompletedBatch)
            or not isinstance(original_planned, S49OriginalPlannedBatch)
            or not isinstance(m_admission_row, dict)
            or not isinstance(m_s16_row, dict)
            or original_planned.original_l0 is original_l0
            # The S owner produces distinct wrappers for its independent
            # callbacks; accept same-inner-original identity, never copies.
            or len(original_l0.steps) != len(original_planned.original_l0.steps)
            or original_l0.session_id != original_planned.session_id
            or original_l0.session_id != original_planned.original_l0.session_id
            or any(
                a.step is not b.step
                or a.probe is not b.probe
                or a.action_receipt is not b.action_receipt
                for a, b in zip(
                    original_l0.steps, original_planned.original_l0.steps
                )
            )
        ):
            raise ValueError("foreign, copied, or replayed S49 owner source")

        source = bind_original_s49_planned(
            original_planned.original_l0, original_planned.moves,
        )
        source_row = bounded_original_s49_planned_row(original_planned)
        if (
            source.session_id != original_planned.session_id
            or source_row.get("status") != "RECORDED"
            or source_row.get("wait_epoch_count") != 0
            or source_row.get("move_epoch_count") != len(source.moves)
            or source_row.get("s42_owner_receipt")
            != "NOT_SUPPLIED_BY_S49_S14_PLANNED_CALLBACK"
            or source_row.get("b0_owner_receipt")
            != "NOT_SUPPLIED_BY_S49_S14_PLANNED_CALLBACK"
            or source_row.get("l8_owner_receipt")
            != "NOT_SUPPLIED_BY_S49_S14_PLANNED_CALLBACK"
        ):
            raise ValueError("S49 original planned owner unavailable")

        # Re-evaluate both original M #683 validators, not just caller JSON
        # status flags. The prior owner readouts must agree with these exactly.
        typed_admission = S49MAdmissionReadout(
            "RECORDED", "s49_original_completed_only",
            admit_original_s49_batch(original_l0),
        )
        fresh_m_admission = bounded_s49_m_admission_row(typed_admission)
        s16 = observe_original_s49_s16_receipts(
            enabled=True, batch=original_l0,
            original_admission=typed_admission,
        )
        fresh_s16 = bounded_original_s49_owner_receipt_row(s16)
        if (
            s16.status != "RECORDED"
            or m_admission_row != fresh_m_admission
            or m_s16_row != fresh_s16
            or fresh_m_admission.get("kind") != "ORIGINAL_PYTHON_BATCH"
            or fresh_m_admission.get("status") != "RECORDED"
            or len(s16.original_actions) != len(source.moves)
            or len(source_row["actions"]) != len(source.moves)
        ):
            raise ValueError("original M S49/S16 admission missing or mismatched")

        actions: list[tuple[str, int, int, int]] = []
        for source_move, source_action, old in zip(
            source.moves, source_row["actions"], s16.original_actions
        ):
            # No reconstruction of S14 epochs from JSON. This is the same
            # source-owning original Python S49 L0/S16 set.
            if (
                source_move.step is not old.original_step
                or source_move.probe is not old.original_probe
                or source_move.receipt is not old.original_s16
                or source_action["action_id"] != old.action_id
                or source_action["event_seq"] != old.event_seq
                or source_action["probe_seq"] != old.probe_seq
                or source_action["s16_after_seq"] != old.after_seq
                or source_action["planned_cognition_requested"] is not False
                or source_action["original_admission"] != "admitted"
            ):
                raise ValueError("planned epoch and original physical closure mismatch")
            actions.append((
                old.action_id, old.event_seq, old.probe_seq, old.after_seq,
            ))
        return S49MS14PlannedObservation(
            "RECORDED", "same_original_s49_s14_s16_source",
            original_planned=original_planned,
            session_id=source.session_id,
            action_rows=tuple(actions),
        )
    except Exception:
        # Passive M diagnostic must never change an S49 Action or owner report.
        return S49MS14PlannedObservation(
            "DEFERRED", "original_s49_planned_owner_rejected",
        )


class M616S14PlannedLease:
    """Once-only DEV intake. Replays and a second callback never become valid."""

    def __init__(self, *, enabled: bool = False) -> None:
        if type(enabled) is not bool:
            raise ValueError("DEV planned lease flag must be boolean")
        self.enabled = enabled
        self._used = False

    def admit(
        self, *, original_l0: object, original_planned: object,
        m_admission_row: object, m_s16_row: object,
    ) -> S49MS14PlannedObservation:
        if not self.enabled:
            return S49MS14PlannedObservation("DISABLED", "not_enabled")
        if self._used:
            return S49MS14PlannedObservation(
                "DEFERRED", "original_s49_planned_owner_rejected",
            )
        self._used = True
        return observe_s49_s14_planned(
            enabled=True,
            original_l0=original_l0,
            original_planned=original_planned,
            m_admission_row=m_admission_row,
            m_s16_row=m_s16_row,
        )


def bounded_m_s14_planned_row(value: S49MS14PlannedObservation) -> dict[str, object]:
    if (
        not isinstance(value, S49MS14PlannedObservation)
        or value.source_attested or value.action_authority
        or value.reason not in {
            "DISABLED": ("not_enabled",),
            "RECORDED": ("same_original_s49_s14_s16_source",),
            "DEFERRED": ("original_s49_planned_owner_rejected",),
        }.get(value.status, ())
        or (
            (value.status == "RECORDED")
            != (value.original_planned is not None)
        )
        or (
            value.status != "RECORDED"
            and (value.session_id is not None or value.action_rows)
        )
    ):
        raise ValueError("forged M planned source/authority")
    accepted = value.status == "RECORDED"
    if accepted and (
        type(value.session_id) is not str or not value.session_id
        or not 1 <= len(value.action_rows) <= 8
        or any(
            type(row) is not tuple or len(row) != 4
            or type(row[0]) is not str or not row[0]
            or any(type(x) is not int or x < 0 for x in row[1:])
            for row in value.action_rows
        )
    ):
        raise ValueError("invalid accepted planned owner Action rows")
    return {
        "schema": "M_S49_S14_PLANNED_SOURCE_JOIN_DEV_V1",
        "status": value.status,
        "reason": value.reason,
        "session_id": value.session_id if accepted else None,
        "move_epoch_count": len(value.action_rows) if accepted else None,
        "wait_epoch_count": 0 if accepted else None,
        "actions": [
            {
                "action_id": action,
                "event_seq": event,
                "probe_seq": probe,
                "s16_after_seq": after,
                "original_planned": "S14_COORDINATOR_RETURNED",
                "planned_cognition_requested": False,
            }
            for action, event, probe, after in value.action_rows
        ] if accepted else [],
        "s42_owner_receipt": "NOT_SUPPLIED_BY_S49_S14_PLANNED_CALLBACK",
        "b0_owner_receipt": "NOT_SUPPLIED_BY_S49_S14_PLANNED_CALLBACK",
        "l8_owner_receipt": "NOT_SUPPLIED_BY_S49_S14_PLANNED_CALLBACK",
        "model_usage": "UNKNOWN_NO_MODEL_METER",
        "metabolic_energy": "UNKNOWN_NO_B0_OWNER",
        "l8_learning": "UNKNOWN_NO_L8_OWNER",
        "provider_calls": None, "input_tokens": None,
        "output_tokens": None, "wall_ns": None, "cpu_ns": None, "gpu_ns": None,
        "source_attested": False, "action_authority": False,
        "new_native_reads": 0, "new_model_calls": 0,
        "new_action_issues": 0, "learning_updates": 0,
        "energy_debits": 0,
    }
