"""S49-owned post-Action readback of *already run* S14 planned epochs.

This does not execute an epoch or issue a native Action. The local S49 on_action
closure supplies its original objects after S16 OUTCOME, and the completed
original L0 batch is joined only after the whole original run_session returns.
An S14 planned epoch is NOT a separate S42 owner receipt or a model meter.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.s49_completed_decision_bridge import S49OriginalCompletedBatch
from adapters.mineflayer.self_action_evidence import capture_native_action_evidence
from relay_self.action import ActionState
from relay_self.epoch_plan import PlannedDecisionEpochResult
from relay_self.world_conditioned_choice import WorldChoiceKind


class S49PlannedReadbackRejected(ValueError):
    """Original S49 planned epoch, L0 decision, or S16 source did not join."""


@dataclass(frozen=True, slots=True)
class S49OriginalPlannedMove:
    """Exact S-owned Python objects; never expose these in a saved JSON row."""

    step: object
    probe: object
    receipt: object
    epoch: PlannedDecisionEpochResult
    plan: object
    admission: object


@dataclass(frozen=True, slots=True)
class S49OriginalPlannedBatch:
    session_id: str
    original_l0: S49OriginalCompletedBatch
    moves: tuple[S49OriginalPlannedMove, ...]
    source_attested: bool = False
    action_authority: bool = False
    real_s42_owner_supplied: bool = False
    real_b0_owner_supplied: bool = False
    real_l8_owner_supplied: bool = False


_EXPECTED_WORK = (
    "s19-att", "s19-blf", "s19-cnc", "s19-prd-wait",
    "s19-prd-move", "s19-plan", "s19-route", "s19-admit",
)


def bind_original_s49_planned(
    original_l0: S49OriginalCompletedBatch,
    moves: tuple[S49OriginalPlannedMove, ...],
) -> S49OriginalPlannedBatch:
    """Require source/object identity from exactly the original MOVE Actions.

    Never fill a WAIT with a fabricated planned epoch. This read-only join
    rejects the entire batch, not a selected subset, on any missing/extra row.
    """
    if (
        not isinstance(original_l0, S49OriginalCompletedBatch)
        or type(moves) is not tuple
        or not 1 <= len(original_l0.steps) <= 8
        or original_l0.source_attested
        or original_l0.action_authority
        or original_l0.real_s42_epoch_supplied
        or original_l0.real_b0_decision_supplied
        or original_l0.real_l8_epoch_supplied
        or not original_l0.session_id
    ):
        raise S49PlannedReadbackRejected("untrusted S49 original L0 owner batch")
    expected = tuple(s for s in original_l0.steps if s.action_receipt is not None)
    if not 1 <= len(expected) <= 8 or len(expected) != len(moves):
        raise S49PlannedReadbackRejected("missing or extra original planned Action")
    used: set[str] = set()
    previous_after = -1
    for original, row in zip(expected, moves):
        step = original.step
        probe = original.probe
        receipt = original.action_receipt
        if (
            not isinstance(row, S49OriginalPlannedMove)
            or row.step is not step
            or row.probe is not probe
            or row.receipt is not receipt
            or step.choice.selection is not WorldChoiceKind.MOVE_AWAY
            or not step.asks_for_action
            or step.action_request_id in used
            or receipt is None
            or receipt.terminal.action_id != step.action_request_id
            or receipt.terminal.state is not ActionState.OUTCOME
            or receipt.consequence.status is not WorldConsequenceStatus.EXECUTED
            or receipt.consequence.session_id != original_l0.session_id
            or probe.session_id != original_l0.session_id
            or probe.seq != step.choice.probe_seq
            or probe.request_id != step.choice.request_id
            or not isinstance(row.epoch, PlannedDecisionEpochResult)
            or row.epoch.executed_work_ids != _EXPECTED_WORK
            or row.epoch.suppressed_work_ids
            or row.epoch.decision.cognition_requested is not False
            or row.epoch.decision.cognition_result is not None
            or row.epoch.decision.next_action_deadline_ns is not None
            or getattr(getattr(row.plan, "selected", None), "candidate_id", None)
            != "MOVE_AWAY"
            or getattr(getattr(row.admission, "status", None), "value", None)
            != "admitted"
        ):
            raise S49PlannedReadbackRejected("original planned/Action identity invalid")
        native = capture_native_action_evidence(receipt.consequence)
        b = native["before_observation"]["seq"]
        a = native["after_observation"]["seq"]
        if not (previous_after < step.event_seq < probe.seq < b < a):
            raise S49PlannedReadbackRejected("replayed or nonmonotonic source")
        previous_after = a
        used.add(step.action_request_id)
    for original in original_l0.steps:
        if original.step.choice.selection is WorldChoiceKind.WAIT and (
            original.action_receipt is not None or original.step.asks_for_action
        ):
            raise S49PlannedReadbackRejected("WAIT cannot acquire an Action epoch")
    return S49OriginalPlannedBatch(original_l0.session_id, original_l0, moves)


def bounded_original_s49_planned_row(batch: S49OriginalPlannedBatch) -> dict[str, object]:
    """Privacy-minimal summary, not an independent physics/source attestation."""
    if (
        not isinstance(batch, S49OriginalPlannedBatch)
        or batch.source_attested or batch.action_authority
        or batch.real_s42_owner_supplied or batch.real_b0_owner_supplied
        or batch.real_l8_owner_supplied
    ):
        raise S49PlannedReadbackRejected("fabricated original owner authority")
    checked = bind_original_s49_planned(batch.original_l0, batch.moves)
    if checked.session_id != batch.session_id:
        raise S49PlannedReadbackRejected("foreign owner session")
    return {
        "schema": "S49_ORIGINAL_S14_PLANNED_POSTACTION_DEV_V1",
        "status": "RECORDED",
        "session_id": batch.session_id,
        "move_epoch_count": len(batch.moves),
        "wait_epoch_count": 0,
        "actions": [
            {
                "action_id": row.step.action_request_id,
                "event_seq": row.step.event_seq,
                "probe_seq": row.probe.seq,
                "s16_after_seq": row.receipt.consequence.after_observation.seq,
                "executed_work_ids": list(row.epoch.executed_work_ids),
                "planned_cognition_requested": False,
                "original_plan": "MOVE_AWAY",
                "original_admission": "admitted",
            }
            for row in batch.moves
        ],
        "s42_owner_receipt": "NOT_SUPPLIED_BY_S49_S14_PLANNED_CALLBACK",
        "b0_owner_receipt": "NOT_SUPPLIED_BY_S49_S14_PLANNED_CALLBACK",
        "l8_owner_receipt": "NOT_SUPPLIED_BY_S49_S14_PLANNED_CALLBACK",
        "provider_calls": None,
        "input_tokens": None,
        "output_tokens": None,
        "wall_ns": None,
        "cpu_ns": None,
        "gpu_ns": None,
        "source_attested": False,
        "action_authority": False,
        "new_model_calls": 0,
        "new_native_reads": 0,
        "new_action_issues": 0,
        "learning_updates": 0,
        "energy_debits": 0,
    }
