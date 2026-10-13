"""G4: budget-matched, offline initial-genome variation; NOT reproduction.

No energy, World Action, intrinsic fitness, behavior result, memory, or
physical birth. Source candidates are sampling provenance, not living parents.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Literal, Sequence

from experiments.genesis_heredity import _TRAITS, Genome, _finite_number, _positive_int

Strategy = Literal["uniform_pool", "maximin_pool", "mutation"]

_FIELDS = tuple(_TRAITS)


@dataclass(frozen=True)
class Variant:
    candidate_id: int
    genome: Genome
    generator: Strategy
    proposal_index: int | None = None
    source_candidate_id: int | None = None

    def __post_init__(self) -> None:
        if type(self.candidate_id) is not int or self.candidate_id < 0:
            raise ValueError("invalid candidate identity")
        if not isinstance(self.genome, Genome):
            raise ValueError("invalid immutable genome")
        if self.generator not in ("uniform_pool", "maximin_pool", "mutation"):
            raise ValueError("invalid variation operator")
        if self.proposal_index is not None and (
            type(self.proposal_index) is not int or self.proposal_index < 0
        ):
            raise ValueError("invalid source proposal")
        if self.source_candidate_id is not None and (
            type(self.source_candidate_id) is not int or self.source_candidate_id < 0
        ):
            raise ValueError("invalid candidate ancestry")


@dataclass(frozen=True)
class VariationBatch:
    seed: int
    strategy: Strategy
    candidates: tuple[Variant, ...]
    proposals_drawn: int
    distance_comparisons: int

    def __post_init__(self) -> None:
        if type(self.seed) is not int:
            raise ValueError("invalid seed")
        if self.strategy not in ("uniform_pool", "maximin_pool", "mutation"):
            raise ValueError("invalid strategy")
        if not isinstance(self.candidates, tuple) or not self.candidates:
            raise ValueError("empty candidate batch")
        if (
            type(self.proposals_drawn) is not int
            or self.proposals_drawn < len(self.candidates)
            or type(self.distance_comparisons) is not int
            or self.distance_comparisons < 0
        ):
            raise ValueError("invalid budget accounting")
        if any(x.candidate_id != idx or x.generator != self.strategy
               for idx, x in enumerate(self.candidates)):
            raise ValueError("inconsistent candidate batch IDs")


@dataclass(frozen=True)
class VariationBudget:
    evaluated_slots: int
    proposal_slots: int

    def __post_init__(self) -> None:
        if (
            not _positive_int(self.evaluated_slots)
            or not _positive_int(self.proposal_slots)
            or self.proposal_slots < self.evaluated_slots
            or self.proposal_slots > 4096
            or self.evaluated_slots > 256
        ):
            raise ValueError("invalid variation budget")


def _draw_founder(rng: random.Random) -> Genome:
    return Genome(**{
        key: rng.uniform(_TRAITS[key][2], _TRAITS[key][3])
        for key in _FIELDS
    })


def _normalized(genome: Genome) -> tuple[float, ...]:
    return tuple(
        (getattr(genome, key) - _TRAITS[key][0]) /
        (_TRAITS[key][1] - _TRAITS[key][0])
        for key in _FIELDS
    )


def normalized_distance(a: Genome, b: Genome) -> float:
    return math.dist(_normalized(a), _normalized(b))


def minimum_pairwise_distance(genomes: Sequence[Genome]) -> float:
    if len(genomes) < 2:
        return 0.0
    return min(
        normalized_distance(genomes[i], genomes[j])
        for i in range(len(genomes))
        for j in range(i + 1, len(genomes))
    )


def marginal_bin_coverage(genomes: Sequence[Genome], *, bins: int = 8) -> float:
    """Coverage of marginal trait bins, NOT quality, fitness or volume."""
    if not _positive_int(bins) or bins > 256:
        raise ValueError("invalid bin count")
    if not genomes:
        return 0.0
    seen: set[tuple[int, int]] = set()
    for item in genomes:
        for axis, coordinate in enumerate(_normalized(item)):
            seen.add((axis, min(bins - 1, int(coordinate * bins))))
    return len(seen) / (len(_FIELDS) * bins)


def paired_variation(seed: int, budget: VariationBudget) -> dict[str, VariationBatch]:
    """Both arms inspect the SAME seeded random pool and evaluate equal N.

    Maximin deliberately spends more pairwise-comparison CPU cycles to improve
    initial-trait spacing. It never sees World outcomes, health, food, reward
    or behavior. Uniform uses a seeded random subset from exactly that pool.
    """
    if type(seed) is not int:
        raise ValueError("seed must be integer")
    rng = random.Random(seed)
    proposals = tuple(_draw_founder(rng) for _ in range(budget.proposal_slots))

    uniform_rng = random.Random(seed ^ 0x47345641)
    random_indices = uniform_rng.sample(range(len(proposals)), budget.evaluated_slots)

    diverse_indices: list[int] = []
    unselected = set(range(len(proposals)))
    normalized = [_normalized(genome) for genome in proposals]
    checks = 0
    # First point is a reproducible far-from-center seed, not a viability score.
    while len(diverse_indices) < budget.evaluated_slots:
        best_idx = -1
        best_score = -1.0
        for idx in sorted(unselected):
            if diverse_indices:
                score = min(math.dist(normalized[idx], normalized[j]) for j in diverse_indices)
                checks += len(diverse_indices)
            else:
                score = math.dist(normalized[idx], (0.5,) * len(_FIELDS))
                checks += 1
            if score > best_score:
                best_score, best_idx = score, idx
        diverse_indices.append(best_idx)
        unselected.remove(best_idx)

    def package(indices: Sequence[int], strategy: Strategy, comparisons: int) -> VariationBatch:
        return VariationBatch(
            seed=seed,
            strategy=strategy,
            candidates=tuple(
                Variant(candidate_id=i, genome=proposals[idx],
                        generator=strategy, proposal_index=idx)
                for i, idx in enumerate(indices)
            ),
            proposals_drawn=budget.proposal_slots,
            distance_comparisons=comparisons,
        )

    return {
        "uniform_pool": package(random_indices, "uniform_pool", 0),
        "maximin_pool": package(diverse_indices, "maximin_pool", checks),
    }


def mutate_candidates(
    seed: int,
    sources: Sequence[Variant],
    budget: VariationBudget,
    *,
    sigma_multiplier: float = 1.0,
) -> VariationBatch:
    """Choose prior source IDs uniformly; external M/V owns any source filter.

    Candidate provenance is not an in-World parentage link or M birth payment.
    """
    if type(seed) is not int:
        raise ValueError("seed must be integer")
    if not _finite_number(sigma_multiplier) or sigma_multiplier < 0:
        raise ValueError("invalid mutation multiplier")
    if not sources or any(not isinstance(item, Variant) for item in sources):
        raise ValueError("invalid source candidates")
    ids = [item.candidate_id for item in sources]
    if len(ids) != len(set(ids)):
        raise ValueError("ambiguous source candidate identities")

    rng = random.Random(seed)
    # Identical independent proposal budget for all arms; only the first
    # evaluated_slots sampled proposals are admitted. No reroll on similarity.
    proposals: list[tuple[int, Genome]] = []
    for _ in range(budget.proposal_slots):
        source = rng.choice(sources)
        values = {}
        for key in _FIELDS:
            low, high, _, _, sigma = _TRAITS[key]
            shifted = getattr(source.genome, key) + rng.gauss(
                0.0, sigma * sigma_multiplier
            )
            values[key] = min(high, max(low, shifted))
        proposals.append((source.candidate_id, Genome(**values)))

    return VariationBatch(
        seed=seed,
        strategy="mutation",
        candidates=tuple(
            Variant(candidate_id=i, genome=genome, generator="mutation",
                    proposal_index=i, source_candidate_id=source_id)
            for i, (source_id, genome) in enumerate(proposals[:budget.evaluated_slots])
        ),
        proposals_drawn=budget.proposal_slots,
        distance_comparisons=0,
    )


@dataclass(frozen=True)
class VariationDiagnostic:
    selected: int
    proposals: int
    distance_comparisons: int
    unique_genomes: int
    marginal_bin_coverage: float
    minimum_spacing: float


def diagnose(batch: VariationBatch, *, bins: int = 8) -> VariationDiagnostic:
    genomes = tuple(item.genome for item in batch.candidates)
    return VariationDiagnostic(
        selected=len(genomes),
        proposals=batch.proposals_drawn,
        distance_comparisons=batch.distance_comparisons,
        unique_genomes=len(set(genomes)),
        marginal_bin_coverage=marginal_bin_coverage(genomes, bins=bins),
        minimum_spacing=minimum_pairwise_distance(genomes),
    )
