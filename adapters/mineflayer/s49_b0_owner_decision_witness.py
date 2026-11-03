"""S-owned B0 *decision-only* witness inside one original S49 session.

B0EnergyLedger.decide() is the original B0 owner's decision, called once
on each existing correlated native S49 probe. Do NOT call ledger.step():
S49 does not supply one consecutive, qualified M0 energy tick, food action
or a physics-side energy transition. This witness is NOT a real energy debit,
and it grants neither B0 control of S49's escape L0 nor M true-E authority.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.b0_energy_bridge import B0Decision, B0EnergyLedger
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s49_completed_decision_bridge import S49OriginalCompletedBatch
from adapters.mineflayer.self_body_m0_projection import (
    B0CognitionViews,
    compose_b0_cognition_views,
)
from experiments.metabolism_viability import initial_body, observe_energy


class S49B0WitnessRejected(ValueError):
    """Absent or mismatched original B0 source, or fake energy accounting."""


@dataclass(frozen=True, slots=True)
class S49OriginalB0Decision:
    original_probe: MineflayerObservation
    original_decision: B0Decision
    original_view: B0CognitionViews


@dataclass(frozen=True, slots=True)
class S49OriginalB0DecisionBatch:
    session_id: str
    original_l0: S49OriginalCompletedBatch
    owner_ledger: B0EnergyLedger
    original_decisions: tuple[S49OriginalB0Decision, ...]
    source_scope: str = "S49_ORIGINAL_B0_DECISION_ONLY_MODEL_ENERGY_UNADVANCED"
    source_attested: bool = False
    action_authority: bool = False
    energy_transitions: int = 0
    energy_debits: int = 0
    food_credits: int = 0
    new_native_reads: int = 0
    model_calls: int = 0


class S49B0DecisionWitness:
    """One original B0 ledger, no energy transition and no new native read."""

    def __init__(self, session_id: str) -> None:
        self.ledger = B0EnergyLedger(session_id, forage_policy="no_ground_seek")
        self._rows: list[S49OriginalB0Decision] = []
        self._failed = False

    def observe(self, original_probe: MineflayerObservation) -> None:
        if self._failed:
            return
        try:
            if not isinstance(original_probe, MineflayerObservation):
                raise S49B0WitnessRejected("original typed native probe required")
            # The exact existing B0 owner makes this decision and maintains
            # its own native source freshness. This is NOT a B0.tick().
            decision = self.ledger.decide(original_probe)
            # Original S projection must occur now, while B0's mutable
            # native-seq cursor still equals THIS decision's probe.
            views = compose_b0_cognition_views(
                original_probe, self.ledger, decision,
                self_id="self-s49-b0-dev",
                epoch_id=f"b0-owner-native-{original_probe.seq}",
            )
            self._rows.append(S49OriginalB0Decision(
                original_probe, decision, views,
            ))
        except Exception:
            self._failed = True
            self._rows.clear()

    def complete(self, original_l0: S49OriginalCompletedBatch) -> S49OriginalB0DecisionBatch:
        if self._failed:
            raise S49B0WitnessRejected("B0 original owner observer failed")
        batch = S49OriginalB0DecisionBatch(
            self.ledger.session_id, original_l0, self.ledger, tuple(self._rows),
        )
        validate_original_b0_decisions(batch)
        return batch


def validate_original_b0_decisions(batch: S49OriginalB0DecisionBatch) -> None:
    """Fail closed: exact original probe identities and no shadow ledger debit."""
    if not isinstance(batch, S49OriginalB0DecisionBatch):
        raise S49B0WitnessRejected("typed B0 owner batch required")
    if (
        batch.source_scope != "S49_ORIGINAL_B0_DECISION_ONLY_MODEL_ENERGY_UNADVANCED"
        or batch.source_attested is not False
        or batch.action_authority is not False
        or batch.energy_transitions != 0 or batch.energy_debits != 0
        or batch.food_credits != 0 or batch.new_native_reads != 0
        or batch.model_calls != 0
        or not isinstance(batch.original_l0, S49OriginalCompletedBatch)
        or not isinstance(batch.owner_ledger, B0EnergyLedger)
        or batch.original_l0.session_id != batch.session_id
        or batch.owner_ledger.session_id != batch.session_id
        or type(batch.original_decisions) is not tuple
        or not 1 <= len(batch.original_decisions) <= 8
        or len(batch.original_decisions) != len(batch.original_l0.steps)
    ):
        raise S49B0WitnessRejected("foreign B0 ledger/session or fabricated authority")
    ledger = batch.owner_ledger
    if (
        ledger.body != initial_body(ledger.config)
        or ledger.credit_count != 0
        or ledger._last_eat_seq != -1
        or ledger._last_decision_seq != batch.original_decisions[-1].original_probe.seq
    ):
        raise S49B0WitnessRejected("B0 energy owner was advanced or credited")
    last_seq = -1
    for original, record in zip(batch.original_l0.steps, batch.original_decisions):
        if (
            not isinstance(record, S49OriginalB0Decision)
            or record.original_probe is not original.probe
            or not isinstance(record.original_decision, B0Decision)
            or record.original_probe.session_id != batch.session_id
            or record.original_decision.probe_seq != original.probe.seq
            or record.original_probe.seq <= last_seq
            or record.original_decision.body_tick != ledger.body.tick
            or record.original_decision.sensor_reading
            != observe_energy(ledger.body, ledger.sensor).reading
            or not isinstance(record.original_view, B0CognitionViews)
            or record.original_view.world.self_body is not record.original_view.body
            or record.original_view.body.observation is None
            or record.original_view.body.observation.native_seq != original.probe.seq
            or record.original_view.body.observation.session_id != batch.session_id
            or record.original_view.l0_kind != record.original_decision.kind
            or record.original_view.sensor_tick != ledger.body.tick
        ):
            raise S49B0WitnessRejected("B0 decision/probe/ledger source mismatch")
        last_seq = original.probe.seq


def bounded_original_b0_decision_row(batch: S49OriginalB0DecisionBatch) -> dict[str, object]:
    validate_original_b0_decisions(batch)
    return {
        "schema": "S49_ORIGINAL_B0_DECISION_ONLY_DEV_V1",
        "status": "RECORDED",
        "session_id": batch.session_id,
        "decision_count": len(batch.original_decisions),
        "decision_probe_seqs": [
            row.original_decision.probe_seq for row in batch.original_decisions
        ],
        "decision_kinds": [
            row.original_decision.kind for row in batch.original_decisions
        ],
        "owner_model_tick": batch.owner_ledger.body.tick,
        "energy_transitions": 0,
        "energy_debits": 0,
        "food_credits": 0,
        "true_world_energy": "UNKNOWN_NO_PHYSICAL_ENERGY_TICK",
        "b0_owner_model_energy": "UNADVANCED_INITIAL_STATE_NOT_PHYSICAL_COST",
        "s42_owner_receipt": "NOT_SUPPLIED_BY_B0_DECISION_ONLY",
        "l8_owner_receipt": "NOT_SUPPLIED_BY_B0_DECISION_ONLY",
        "source_attested": False,
        "action_authority": False,
        "new_native_reads": 0,
        "new_model_calls": 0,
        "new_action_issues": 0,
    }
