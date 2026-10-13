"""G2: two-phase parent commitment and physical-debit *attestation* boundary.

OFFLINE ONLY. A PhysicalBirthDebit is caller-provided and unauthenticated;
this module never modifies M energy or verifies a real World source.
M2 #621 currently lacks a tick-bound cross-lane receipt; do NOT coerce its
BirthRecord into an authenticated G2 transaction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from experiments.genesis_heredity import (
    GenesisRegistry,
    Individual,
    MOutcomeBatch,
    _finite_number,
    _positive_int,
)

Selection = Literal["uniform", "surplus_weighted"]


@dataclass(frozen=True)
class BirthOpportunity:
    """M-side selection-eligible IDs for exactly one G cohort snapshot."""

    batch_id: str
    tick: int
    eligible_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.batch_id, str) or not self.batch_id.strip():
            raise ValueError("invalid opportunity batch")
        if not _positive_int(self.tick):
            raise ValueError("invalid opportunity tick")
        if (
            not isinstance(self.eligible_ids, tuple)
            or not self.eligible_ids
            or any(type(value) is not int or value < 0 for value in self.eligible_ids)
            or len(self.eligible_ids) != len(set(self.eligible_ids))
            or self.eligible_ids != tuple(sorted(self.eligible_ids))
        ):
            raise ValueError("invalid eligible roster")


@dataclass(frozen=True)
class BirthPlan:
    plan_id: str
    batch_id: str
    tick: int
    parent_ids: tuple[int, ...]
    selection: Selection

    def __post_init__(self) -> None:
        if not isinstance(self.plan_id, str) or not self.plan_id.strip():
            raise ValueError("invalid plan id")
        if not isinstance(self.batch_id, str) or not self.batch_id.strip():
            raise ValueError("invalid plan batch")
        if not _positive_int(self.tick) or not self.parent_ids:
            raise ValueError("invalid plan")
        if any(type(value) is not int or value < 0 for value in self.parent_ids):
            raise ValueError("invalid parent ids")
        if self.selection not in ("uniform", "surplus_weighted"):
            raise ValueError("invalid selection")


@dataclass(frozen=True)
class PhysicalBirthDebit:
    debit_id: str
    parent_id: int
    before: float
    after: float
    child_energy: float

    def __post_init__(self) -> None:
        if not isinstance(self.debit_id, str) or not self.debit_id.strip():
            raise ValueError("invalid debit id")
        if type(self.parent_id) is not int or self.parent_id < 0:
            raise ValueError("invalid debit parent")
        if not all(_finite_number(x) for x in (self.before, self.after, self.child_energy)):
            raise ValueError("invalid debit energy")
        if min(self.before, self.after, self.child_energy) <= 0:
            raise ValueError("invalid debit viability")
        if not math.isclose(
            self.before - self.after, self.child_energy, rel_tol=1e-12, abs_tol=1e-12
        ):
            raise ValueError("parent/child energy not conserved")


@dataclass(frozen=True)
class FundedBirthReceipt:
    receipt_id: str
    plan_id: str
    batch_id: str
    tick: int
    debits: tuple[PhysicalBirthDebit, ...]

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, str) or not value.strip()
            for value in (self.receipt_id, self.plan_id, self.batch_id)
        ):
            raise ValueError("invalid funded receipt identity")
        if not _positive_int(self.tick):
            raise ValueError("invalid funded receipt tick")
        if not isinstance(self.debits, tuple) or not self.debits:
            raise ValueError("invalid funded debit list")


class FundedGenesisRegistry(GenesisRegistry):
    """G1 lineage with a strict preselect -> M debit -> lineage commit path.

    There may be only ONE plan per M outcome tick. A failed debit can be
    aborted, but cannot trigger opportunistic rerolls within the same cohort.
    """

    def __init__(self, *, seed: int, config=None) -> None:
        super().__init__(seed=seed, config=config)
        self._pending_plan: BirthPlan | None = None
        self._planned_batches: set[str] = set()
        self._used_plan_ids: set[str] = set()
        self._used_debit_ids: set[str] = set()
        self._aborted_plans: set[str] = set()

    def record_m_outcomes(self, batch: MOutcomeBatch):
        if self._pending_plan is not None:
            raise ValueError("unresolved birth plan before next M batch")
        return super().record_m_outcomes(batch)

    def spawn_children(self, *args, **kwargs):
        # The legacy single-step contract allows parent assignment *after*
        # generic paid-cost assertion. That is not sufficient for G2.
        raise ValueError("G2 requires preselected funded parent receipts")

    def prepare_births(
        self,
        plan_id: str,
        opportunity: BirthOpportunity,
        *,
        count: int,
        selection: Selection = "uniform",
    ) -> BirthPlan:
        if not isinstance(plan_id, str) or not plan_id.strip():
            raise ValueError("invalid plan identity")
        if plan_id in self._used_plan_ids:
            raise ValueError("duplicate plan identity")
        if self._pending_plan is not None:
            raise ValueError("another birth plan is pending")
        if not self._active or self._last_batch != opportunity.batch_id:
            raise ValueError("opportunity lacks current M cohort")
        if opportunity.tick != self._last_tick or opportunity.batch_id in self._planned_batches:
            raise ValueError("stale or already planned M cohort")
        if not set(opportunity.eligible_ids) <= self._active:
            raise ValueError("birth opportunity includes non-survivor")
        if not set(opportunity.eligible_ids) <= set(self._surplus):
            raise ValueError("birth opportunity includes unverified survivor")
        if not _positive_int(count):
            raise ValueError("invalid birth count")
        if len(self._active) + count > self.config.max_active:
            raise ValueError("active population capacity exceeded")
        if self._births + count > self.config.max_total_births:
            raise ValueError("total birth limit exceeded")
        if selection not in ("uniform", "surplus_weighted"):
            raise ValueError("unsupported selection mode")
        candidates = opportunity.eligible_ids
        weights = [self._surplus[id_] for id_ in candidates]
        if selection == "surplus_weighted" and not any(weight > 0 for weight in weights):
            raise ValueError("zero surplus for weighted selection")

        parents = tuple(
            self._rng.choice(candidates)
            if selection == "uniform"
            else self._rng.choices(candidates, weights=weights, k=1)[0]
            for _ in range(count)
        )
        plan = BirthPlan(plan_id, opportunity.batch_id, opportunity.tick, parents, selection)
        self._pending_plan = plan
        self._planned_batches.add(opportunity.batch_id)
        self._used_plan_ids.add(plan_id)
        return plan

    @property
    def pending_plan(self) -> BirthPlan | None:
        return self._pending_plan

    @property
    def aborted_plans(self) -> tuple[str, ...]:
        return tuple(sorted(self._aborted_plans))

    def abort_birth_plan(self, plan_id: str) -> None:
        if self._pending_plan is None or self._pending_plan.plan_id != plan_id:
            raise ValueError("no matching pending birth plan")
        self._pending_plan = None
        self._aborted_plans.add(plan_id)

    def commit_funded_births(
        self,
        receipt: FundedBirthReceipt,
        *,
        inherit: bool = True,
        mutate: bool = True,
    ) -> tuple[Individual, ...]:
        if type(inherit) is not bool or type(mutate) is not bool:
            raise ValueError("invalid inheritance control")
        plan = self._pending_plan
        if plan is None:
            raise ValueError("no pending birth plan")
        if (
            receipt.plan_id != plan.plan_id
            or receipt.batch_id != plan.batch_id
            or receipt.tick != plan.tick
        ):
            raise ValueError("receipt does not match birth plan")
        if receipt.receipt_id in self._used_receipts:
            raise ValueError("reused birth receipt")
        if len(receipt.debits) != len(plan.parent_ids):
            raise ValueError("wrong number of physical births")
        debit_ids = [entry.debit_id for entry in receipt.debits]
        if len(debit_ids) != len(set(debit_ids)):
            raise ValueError("duplicate physical debit IDs")
        if set(debit_ids) & self._used_debit_ids:
            raise ValueError("reused physical debit ID")
        last_after: dict[int, float] = {}
        for parent_id, debit in zip(plan.parent_ids, receipt.debits):
            if parent_id != debit.parent_id or parent_id not in self._active:
                raise ValueError("funded parent differs from genetic parent")
            if parent_id in last_after and not math.isclose(
                last_after[parent_id], debit.before, rel_tol=1e-12, abs_tol=1e-12
            ):
                raise ValueError("nonconsecutive debits from same parent")
            last_after[parent_id] = debit.after
            if not math.isclose(
                debit.child_energy, self.config.birth_cost, rel_tol=1e-12, abs_tol=1e-12
            ):
                raise ValueError("unauthorized child energy transfer")

        # No state or RNG mutation happens until every debit is validated.
        children = []
        for parent_id in plan.parent_ids:
            parent = self._individuals[parent_id]
            if not inherit:
                child_genome = self._founder_genome()
            elif mutate:
                child_genome = self._mutated_genome(parent.genome)
            else:
                child_genome = parent.genome
            child = Individual(
                self._next_id,
                parent_id,
                parent.generation + 1,
                plan.tick,
                child_genome,
                receipt.receipt_id,
            )
            self._individuals[child.individual_id] = child
            self._active.add(child.individual_id)
            self._next_id += 1
            children.append(child)
        self._births += len(children)
        self._used_receipts.add(receipt.receipt_id)
        self._used_debit_ids.update(debit_ids)
        self._pending_plan = None
        return tuple(children)
