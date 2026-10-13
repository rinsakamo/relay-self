"""G1 experiment-local genome, birth and lineage mechanics (Issue #622).

The M-owned outcome/birth-receipt objects below are OFFLINE CONTRACT ENVELOPES.
They do not authenticate a Minecraft outcome or prove actual energy debiting.
No Self/Action/Memory/Habit object is constructed or inherited here.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Literal

# Field: hard min, hard max, founder uniform min/max, mutation Gaussian sigma.
# sensor_gain maps to M0 Interoception.gain; epsilon and learning rate map to
# existing experiments/evolved_values.py. No production Self wiring is implied.
_TRAITS = {
    "sensor_gain": (0.0, 2.0, 0.0, 2.0, 0.15),
    "exploration_rate": (0.0, 1.0, 0.0, 1.0, 0.08),
    "learning_rate": (0.01, 1.0, 0.05, 0.50, 0.05),
}


def _finite_number(value: float) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _positive_int(value: int) -> bool:
    return type(value) is int and value > 0


@dataclass(frozen=True)
class Genome:
    sensor_gain: float
    exploration_rate: float
    learning_rate: float

    def __post_init__(self) -> None:
        for key, (low, high, _, _, _) in _TRAITS.items():
            value = getattr(self, key)
            if not _finite_number(value) or not low <= value <= high:
                raise ValueError(f"invalid gene: {key}")


@dataclass(frozen=True)
class GenesisConfig:
    max_active: int = 24
    max_total_births: int = 200
    birth_cost: float = 2.0
    mutation_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if not _positive_int(self.max_active) or not _positive_int(self.max_total_births):
            raise ValueError("invalid population limit")
        if not _finite_number(self.birth_cost) or self.birth_cost <= 0:
            raise ValueError("invalid birth cost")
        if not _finite_number(self.mutation_multiplier) or self.mutation_multiplier < 0:
            raise ValueError("invalid mutation multiplier")


@dataclass(frozen=True)
class Individual:
    individual_id: int
    parent_id: int | None
    generation: int
    birth_tick: int
    genome: Genome
    birth_receipt: str | None = None

    # Deliberately no acquired Memory, Habit, Q-state or current energy fields.


@dataclass(frozen=True)
class MOutcome:
    individual_id: int
    tick: int
    state: Literal["ALIVE", "STARVED"]
    surplus: float = 0.0

    def __post_init__(self) -> None:
        if type(self.individual_id) is not int or self.individual_id < 0:
            raise ValueError("invalid individual id")
        if not _positive_int(self.tick):
            raise ValueError("invalid M tick")
        if self.state not in ("ALIVE", "STARVED"):
            raise ValueError("invalid M state")
        if not _finite_number(self.surplus) or self.surplus < 0:
            raise ValueError("invalid surplus")
        if self.state == "STARVED" and self.surplus != 0:
            raise ValueError("terminal individual has surplus")


@dataclass(frozen=True)
class MOutcomeBatch:
    batch_id: str
    tick: int
    outcomes: tuple[MOutcome, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.batch_id, str) or not self.batch_id.strip():
            raise ValueError("missing M batch id")
        if not _positive_int(self.tick):
            raise ValueError("invalid M batch tick")
        if not isinstance(self.outcomes, tuple):
            raise ValueError("M outcomes must be a tuple")


@dataclass(frozen=True)
class BirthAuthorization:
    """External M/R assertion of *already paid* birth costs, not proof of payment."""

    receipt_id: str
    batch_id: str
    tick: int
    count: int
    debited_total: float

    def __post_init__(self) -> None:
        if not isinstance(self.receipt_id, str) or not self.receipt_id.strip():
            raise ValueError("missing birth receipt")
        if not isinstance(self.batch_id, str) or not self.batch_id.strip():
            raise ValueError("missing source batch")
        if not _positive_int(self.tick) or not _positive_int(self.count):
            raise ValueError("invalid birth authorization")
        if not _finite_number(self.debited_total) or self.debited_total <= 0:
            raise ValueError("invalid debited cost")


@dataclass(frozen=True)
class TerminalRecord:
    individual_id: int
    tick: int
    reason: Literal["STARVED"] = "STARVED"


class GenesisRegistry:
    """Seeded mechanical ledger. No endogenous birth opportunity or fitness."""

    def __init__(self, *, seed: int, config: GenesisConfig | None = None) -> None:
        if type(seed) is not int:
            raise ValueError("seed must be int")
        self.config = config or GenesisConfig()
        self._rng = random.Random(seed)
        self._next_id = 0
        self._individuals: dict[int, Individual] = {}
        self._active: set[int] = set()
        self._terminals: list[TerminalRecord] = []
        self._surplus: dict[int, float] = {}
        self._last_tick = 0
        self._last_batch: str | None = None
        self._used_batches: set[str] = set()
        self._used_receipts: set[str] = set()
        self._births = 0

    def _founder_genome(self) -> Genome:
        values = {
            key: self._rng.uniform(founder_low, founder_high)
            for key, (_, _, founder_low, founder_high, _) in _TRAITS.items()
        }
        return Genome(**values)

    def _mutated_genome(self, genome: Genome) -> Genome:
        values = {}
        for key, (low, high, _, _, sigma) in _TRAITS.items():
            proposal = getattr(genome, key) + self._rng.gauss(
                0.0, sigma * self.config.mutation_multiplier
            )
            values[key] = min(high, max(low, proposal))
        return Genome(**values)

    def spawn_founders(self, count: int) -> tuple[Individual, ...]:
        if self._individuals or self._last_tick != 0:
            raise ValueError("founders can only be spawned once at initial tick")
        if not _positive_int(count) or count > self.config.max_active:
            raise ValueError("founder count exceeds limit")
        new = []
        for _ in range(count):
            individual = Individual(self._next_id, None, 0, 0, self._founder_genome())
            self._individuals[individual.individual_id] = individual
            self._active.add(individual.individual_id)
            self._next_id += 1
            new.append(individual)
        return tuple(new)

    def record_m_outcomes(self, batch: MOutcomeBatch) -> tuple[TerminalRecord, ...]:
        """Accept exactly one complete status snapshot for the active cohort."""
        if not self._individuals or not self._active:
            raise ValueError("no active individuals")
        if batch.batch_id in self._used_batches or batch.tick <= self._last_tick:
            raise ValueError("stale/duplicate M batch")
        ids = [outcome.individual_id for outcome in batch.outcomes]
        if len(ids) != len(set(ids)) or set(ids) != self._active:
            raise ValueError("incomplete or duplicate M cohort")
        if any(outcome.tick != batch.tick for outcome in batch.outcomes):
            raise ValueError("mismatched M tick")
        terminated = tuple(
            TerminalRecord(outcome.individual_id, batch.tick)
            for outcome in sorted(batch.outcomes, key=lambda item: item.individual_id)
            if outcome.state == "STARVED"
        )
        for record in terminated:
            self._active.remove(record.individual_id)
        self._terminals.extend(terminated)
        self._surplus = {
            outcome.individual_id: outcome.surplus
            for outcome in batch.outcomes
            if outcome.state == "ALIVE"
        }
        self._last_tick = batch.tick
        self._last_batch = batch.batch_id
        self._used_batches.add(batch.batch_id)
        return terminated

    def spawn_children(
        self,
        authorization: BirthAuthorization,
        *,
        selection: Literal["uniform", "surplus_weighted"] = "uniform",
        inherit: bool = True,
        mutate: bool = True,
    ) -> tuple[Individual, ...]:
        if type(inherit) is not bool or type(mutate) is not bool:
            raise ValueError("invalid control flag")
        if authorization.receipt_id in self._used_receipts:
            raise ValueError("reused birth receipt")
        if authorization.tick != self._last_tick or authorization.batch_id != self._last_batch:
            raise ValueError("birth authorization not bound to current M batch")
        cost = authorization.count * self.config.birth_cost
        if not math.isclose(authorization.debited_total, cost, rel_tol=1e-12, abs_tol=0):
            raise ValueError("birth cost not accounted for")
        if len(self._active) + authorization.count > self.config.max_active:
            raise ValueError("active population capacity exceeded")
        if self._births + authorization.count > self.config.max_total_births:
            raise ValueError("total birth limit exceeded")
        parents = sorted(self._surplus)
        if not parents or set(parents) != self._active:
            raise ValueError("no fresh viable parents")
        if selection not in ("uniform", "surplus_weighted"):
            raise ValueError("unsupported selection mode")
        weights = [self._surplus[parent_id] for parent_id in parents]
        if selection == "surplus_weighted" and not any(weight > 0 for weight in weights):
            raise ValueError("zero surplus for weighted control")

        new = []
        for _ in range(authorization.count):
            if selection == "uniform":
                parent_id = self._rng.choice(parents)
            else:
                parent_id = self._rng.choices(parents, weights=weights, k=1)[0]
            parent = self._individuals[parent_id]
            if not inherit:
                genome = self._founder_genome()  # independent-genome negative control
            elif mutate:
                genome = self._mutated_genome(parent.genome)
            else:
                genome = parent.genome
            child = Individual(
                self._next_id,
                parent_id,
                parent.generation + 1,
                authorization.tick,
                genome,
                authorization.receipt_id,
            )
            self._individuals[child.individual_id] = child
            self._active.add(child.individual_id)
            self._next_id += 1
            new.append(child)
        self._births += len(new)
        self._used_receipts.add(authorization.receipt_id)
        return tuple(new)

    @property
    def active_ids(self) -> tuple[int, ...]:
        return tuple(sorted(self._active))

    @property
    def lineage(self) -> tuple[Individual, ...]:
        return tuple(self._individuals[key] for key in sorted(self._individuals))

    @property
    def deaths(self) -> tuple[TerminalRecord, ...]:
        return tuple(self._terminals)

    @property
    def births(self) -> int:
        return self._births
