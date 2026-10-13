from __future__ import annotations

from dataclasses import fields

import pytest

from experiments.genesis_g4_variation import (
    Variant,
    VariationBudget,
    diagnose,
    marginal_bin_coverage,
    mutate_candidates,
    normalized_distance,
    paired_variation,
)
from experiments.genesis_heredity import Genome


def test_g4_seeded_equal_budget_against_random_pool_baseline() -> None:
    budget = VariationBudget(evaluated_slots=8, proposal_slots=64)
    a, b = paired_variation(17, budget), paired_variation(17, budget)
    assert a == b
    assert set(a) == {"uniform_pool", "maximin_pool"}
    baseline, diverse = a["uniform_pool"], a["maximin_pool"]
    for arm in (baseline, diverse):
        assert len(arm.candidates) == 8
        assert arm.proposals_drawn == 64
        assert len({row.proposal_index for row in arm.candidates}) == 8
        assert all(row.source_candidate_id is None for row in arm.candidates)
    assert baseline.distance_comparisons == 0
    assert diverse.distance_comparisons > 0
    assert diagnose(diverse).minimum_spacing > diagnose(baseline).minimum_spacing


def test_g4_spacing_not_confused_with_any_scientific_outcome() -> None:
    arms = paired_variation(211, VariationBudget(8, 64))
    spaced = diagnose(arms["maximin_pool"])
    random = diagnose(arms["uniform_pool"])
    assert spaced.minimum_spacing > random.minimum_spacing
    # Maximin spacing need NOT dominate marginal 1D coverage; report both.
    assert spaced.marginal_bin_coverage < random.marginal_bin_coverage
    assert all(not hasattr(v, "energy") and not hasattr(v, "reward")
               for arm in arms.values() for v in arm.candidates)
    assert {"birth_receipt", "memory", "habit", "q_values", "fitness"} \
        .isdisjoint({f.name for f in fields(Variant)})


def test_g4_all_variants_are_valid_initial_genomes_without_biological_birth() -> None:
    arms = paired_variation(43, VariationBudget(12, 96))
    for arm in arms.values():
        assert len({v.genome for v in arm.candidates}) == 12
        assert all(isinstance(v.genome, Genome) for v in arm.candidates)
        assert all(v.candidate_id == i for i, v in enumerate(arm.candidates))
        assert all(v.generator in ("uniform_pool", "maximin_pool") for v in arm.candidates)
        assert diagnose(arm).selected == 12


def test_g4_mutation_is_only_candidate_derivation() -> None:
    source = paired_variation(1, VariationBudget(4, 16))["uniform_pool"].candidates
    budget = VariationBudget(6, 12)
    a = mutate_candidates(991, source, budget)
    b = mutate_candidates(991, source, budget)
    assert a == b
    assert len(a.candidates) == 6
    assert a.proposals_drawn == 12
    assert a.distance_comparisons == 0
    source_by_id = {v.candidate_id: v.genome for v in source}
    assert all(v.source_candidate_id in source_by_id for v in a.candidates)
    assert any(v.genome != source_by_id[v.source_candidate_id] for v in a.candidates)
    assert len({v.candidate_id for v in a.candidates}) == 6


def test_g4_mutation_off_is_identity_not_world_spawn() -> None:
    source = paired_variation(5, VariationBudget(3, 12))["maximin_pool"].candidates
    out = mutate_candidates(11, source, VariationBudget(6, 6), sigma_multiplier=0)
    assert all(v.genome == source[v.source_candidate_id].genome for v in out.candidates)
    assert all(not hasattr(v, "physical_birth") for v in out.candidates)


def test_g4_accepts_one_slot_and_avoids_false_diversity_guarantees() -> None:
    arms = paired_variation(1, VariationBudget(1, 1))
    assert all(diagnose(v).minimum_spacing == 0.0 for v in arms.values())
    assert all(diagnose(v).selected == 1 for v in arms.values())


@pytest.mark.parametrize(
    "slots,proposals",
    [(0, 5), (3, 2), (2, 4097), (257, 4096), (True, 2), (1, 0)],
)
def test_g4_strict_evaluation_and_proposal_budget(slots, proposals) -> None:
    with pytest.raises(ValueError, match="budget"):
        VariationBudget(slots, proposals)


def test_g4_bad_generator_seed_sources_and_sigma_fail_closed() -> None:
    with pytest.raises(ValueError, match="seed"):
        paired_variation(True, VariationBudget(2, 3))
    with pytest.raises(ValueError, match="source"):
        mutate_candidates(1, (), VariationBudget(2, 3))
    with pytest.raises(ValueError, match="multiplier"):
        mutate_candidates(
            1, paired_variation(1, VariationBudget(2, 3))["uniform_pool"].candidates,
            VariationBudget(2, 3), sigma_multiplier=float("nan")
        )
    with pytest.raises(ValueError, match="ambiguous"):
        one = paired_variation(1, VariationBudget(2, 3))["uniform_pool"].candidates[0]
        mutate_candidates(1, (one, one), VariationBudget(2, 3))


def test_g4_metrics_normalized_finite_and_bounds_checked() -> None:
    first = Genome(0, 0, 0.01)
    last = Genome(2, 1, 1)
    assert normalized_distance(first, last) == pytest.approx(3 ** 0.5)
    assert marginal_bin_coverage((first, last), bins=2) == 1.0
    with pytest.raises(ValueError, match="bin"):
        marginal_bin_coverage((first,), bins=0)


def test_g4_proposals_can_be_more_expensive_than_diverse_evaluation_gain() -> None:
    arms = paired_variation(211, VariationBudget(8, 64))
    dense, spaced = diagnose(arms["uniform_pool"]), diagnose(arms["maximin_pool"])
    assert spaced.proposals == dense.proposals
    assert spaced.selected == dense.selected
    assert spaced.distance_comparisons > dense.distance_comparisons
    # For this seed, 1-D coverage is actually WORSE despite better 3-D spacing.
    assert spaced.marginal_bin_coverage < dense.marginal_bin_coverage
    assert spaced.minimum_spacing > dense.minimum_spacing
