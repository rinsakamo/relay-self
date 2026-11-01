"""S49 original L0 decision/physical closure readback, never an S42 epoch.

S49's real owner calls this ONLY after its original run_session has returned
and its original S16 actions have closed. No model, native read, L8/B0
synthesis, new coordinator, Action, memory or learning is performed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.normal_action import NormalActionReceipt
from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.action import ActionState
from relay_self.reactive_l0 import L0Step
from relay_self.world_conditioned_choice import WorldChoiceKind


class S49CompletionRejected(ValueError):
    """Original run_session steps and terminal S16 evidence do not correspond."""


@dataclass(frozen=True, slots=True)
class S49OriginalCompletedStep:
    """Exact objects returned by S49 L0, correlated probe and S16 owner."""

    step: L0Step
    probe: MineflayerObservation
    action_receipt: NormalActionReceipt | None
    source_scope: str = "S49_ORIGINAL_L0_STEP_WITH_OPTIONAL_S16_NOT_S42_EPOCH"
    source_attested: bool = False
    action_authority: bool = False


@dataclass(frozen=True, slots=True)
class S49OriginalCompletedBatch:
    session_id: str
    steps: tuple[S49OriginalCompletedStep, ...]
    real_s42_epoch_supplied: bool = False
    real_b0_decision_supplied: bool = False
    real_l8_epoch_supplied: bool = False
    new_native_reads: int = 0
    new_model_calls: int = 0
    new_action_issues: int = 0
    learning_updates: int = 0
    energy_debits: int = 0
    source_attested: bool = False
    action_authority: bool = False


def read_original_s49_completions(
    steps: tuple[L0Step, ...],
    probes: Mapping[int, MineflayerObservation],
    action_receipts: Mapping[str, NormalActionReceipt],
    *,
    max_steps: int = 8,
) -> S49OriginalCompletedBatch:
    """Join the owner-returned sequence with exact previously received objects.

    Never construct a DecisionEpochResult: a live S49 L0Step is *not* an S42
    coordinator result, and native probes do not manufacture B0/L8 originals.
    This is owner-declared source identity, not independent W3/Paper attestation.
    """
    if (
        type(steps) is not tuple or not 1 <= len(steps) <= max_steps
        or type(max_steps) is not int or not 1 <= max_steps <= 8
        or not isinstance(probes, Mapping)
        or not isinstance(action_receipts, Mapping)
    ):
        raise S49CompletionRejected("bounded returned owner steps required")
    result: list[S49OriginalCompletedStep] = []
    used_probe_ids: set[int] = set()
    used_action_ids: set[str] = set()
    last_event_seq = -1
    last_probe_seq = -1
    session_id: str | None = None
    for step in steps:
        if not isinstance(step, L0Step):
            raise S49CompletionRejected("original typed L0Step missing")
        choice = step.choice
        probe = probes.get(choice.probe_seq)
        if (
            not isinstance(probe, MineflayerObservation)
            or probe.kind != "probe"
            or probe.provenance.source != "mineflayer"
            or probe.request_id != choice.request_id
            or probe.session_id != choice.session_id
            or probe.seq != choice.probe_seq
            or probe.seq <= step.event_seq
            or step.event_seq <= last_event_seq
            or probe.seq <= last_probe_seq
            or choice.probe_seq in used_probe_ids
            or (session_id is not None and choice.session_id != session_id)
            or not any(
                e.name == "zombie" and e.entity_id == choice.entity_id
                for e in probe.snapshot.nearby_entities
            )
        ):
            raise S49CompletionRejected("original native probe/decision mismatch")
        session_id = choice.session_id
        last_event_seq = step.event_seq
        last_probe_seq = probe.seq
        used_probe_ids.add(probe.seq)
        receipt = None
        if choice.selection is WorldChoiceKind.WAIT:
            if step.asks_for_action or step.grant is not None:
                raise S49CompletionRejected("WAIT cannot carry Action authority")
        elif choice.selection is WorldChoiceKind.MOVE_AWAY:
            action_id = step.action_request_id
            receipt = action_receipts.get(action_id)
            if (
                not step.asks_for_action
                or not isinstance(action_id, str) or not action_id
                or action_id in used_action_ids
                or not isinstance(receipt, NormalActionReceipt)
                or receipt.terminal.state is not ActionState.OUTCOME
                or receipt.terminal.action_id != action_id
                or receipt.consequence.action_id != action_id
                or receipt.consequence.session_id != session_id
                or receipt.consequence.status is not WorldConsequenceStatus.EXECUTED
                or receipt.consequence.movement_distance is None
                or receipt.consequence.movement_distance < 0.05
                or receipt.source != probe.provenance
            ):
                raise S49CompletionRejected("MOVE lacks original S16 terminal")
            used_action_ids.add(action_id)
        else:
            raise S49CompletionRejected("unsupported original L0 choice")
        result.append(S49OriginalCompletedStep(step, probe, receipt))
    if set(action_receipts) != used_action_ids or set(probes) != used_probe_ids:
        raise S49CompletionRejected("unmatched action or probe from owner session")
    assert session_id is not None
    return S49OriginalCompletedBatch(session_id, tuple(result))


def bounded_original_s49_completion_row(
    batch: S49OriginalCompletedBatch,
) -> dict[str, object]:
    """Privacy-minimal diagnostics: never serialize original World objects."""
    if not isinstance(batch, S49OriginalCompletedBatch) or (
        batch.real_s42_epoch_supplied or batch.real_b0_decision_supplied
        or batch.real_l8_epoch_supplied or batch.source_attested
        or batch.action_authority
        or any(type(getattr(batch, name)) is not int or getattr(batch, name) != 0
               for name in (
                   "new_native_reads", "new_model_calls", "new_action_issues",
                   "learning_updates", "energy_debits",
               ))
    ):
        raise S49CompletionRejected("observer cannot mint source or authority")
    if (
        type(batch.steps) is not tuple or not 1 <= len(batch.steps) <= 8
        or not all(isinstance(s, S49OriginalCompletedStep) for s in batch.steps)
        or any(s.source_attested or s.action_authority for s in batch.steps)
    ):
        raise S49CompletionRejected("invalid original completion window")
    return {
        "schema": "S49_ORIGINAL_COMPLETION_DEV_V1",
        "session_id": batch.session_id,
        "step_count": len(batch.steps),
        "wait_count": sum(s.step.choice.selection is WorldChoiceKind.WAIT
                          for s in batch.steps),
        "outcome_count": sum(s.action_receipt is not None for s in batch.steps),
        "decisions": [
            {
                "event_seq": s.step.event_seq,
                "probe_seq": s.probe.seq,
                "request_id": s.probe.request_id,
                "choice": s.step.choice.selection.value,
                "action_id": s.step.action_request_id,
                "s16_terminal": (
                    s.action_receipt.terminal.state.value
                    if s.action_receipt is not None else None
                ),
            }
            for s in batch.steps
        ],
        "real_s42_epoch_supplied": False,
        "real_b0_decision_supplied": False,
        "real_l8_epoch_supplied": False,
        "source_attested": False,
        "action_authority": False,
        "new_native_reads": 0,
        "new_model_calls": 0,
        "new_action_issues": 0,
        "learning_updates": 0,
        "energy_debits": 0,
    }
