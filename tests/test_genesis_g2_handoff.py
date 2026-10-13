from __future__ import annotations

from dataclasses import fields

import pytest

from experiments.genesis_g2_handoff import (
    BirthOpportunity,
    FundedBirthReceipt,
    FundedGenesisRegistry,
    PhysicalBirthDebit,
)
from experiments.genesis_heredity import GenesisConfig, MOutcome, MOutcomeBatch


def ready(*, seed: int = 5, count: int = 2, cost: float = 8.0) -> FundedGenesisRegistry:
    ledger = FundedGenesisRegistry(seed=seed, config=GenesisConfig(birth_cost=cost))
    ledger.spawn_founders(count)
    ledger.record_m_outcomes(
        MOutcomeBatch(
            "M-episode:1", 1,
            tuple(MOutcome(i, 1, "ALIVE", i + 1.0) for i in range(count)),
        )
    )
    return ledger


def opportunity(*ids: int, batch: str = "M-episode:1", tick: int = 1) -> BirthOpportunity:
    return BirthOpportunity(batch, tick, ids)


def paid(plan, *, receipt_id: str = "proof-1", cost: float = 8.0) -> FundedBirthReceipt:
    # Each same-parent transaction is chained; never reuses an energy snapshot.
    by_parent: dict[int, float] = {}
    debits = []
    for index, parent_id in enumerate(plan.parent_ids):
        before = by_parent.get(parent_id, 40.0)
        after = before - cost
        debits.append(PhysicalBirthDebit(f"debit-{index}", parent_id, before, after, cost))
        by_parent[parent_id] = after
    return FundedBirthReceipt(receipt_id, plan.plan_id, plan.batch_id, plan.tick, tuple(debits))


def test_g2_preselects_then_accepts_only_matching_debit_parent() -> None:
    ledger = ready(count=2)
    plan = ledger.prepare_births("plan-1", opportunity(1), count=2)
    assert plan.parent_ids == (1, 1)
    assert ledger.births == 0
    assert ledger.active_ids == (0, 1)
    children = ledger.commit_funded_births(paid(plan), mutate=False)
    assert [child.parent_id for child in children] == [1, 1]
    assert [child.generation for child in children] == [1, 1]
    assert all(child.genome == ledger.lineage[1].genome for child in children)
    assert ledger.active_ids == (0, 1, 2, 3)
    assert ledger.births == 2
    assert ledger.pending_plan is None
    assert all(not hasattr(child, "energy") for child in children)
    assert {field.name for field in fields(children[0])}.isdisjoint({"memory", "habit", "q_values"})


def test_g2_reproduces_identical_seed_and_lineage() -> None:
    a, b = ready(seed=16), ready(seed=16)
    for ledger in (a, b):
        plan = ledger.prepare_births("p1", opportunity(0, 1), count=3)
        ledger.commit_funded_births(paid(plan))
    assert a.lineage == b.lineage
    assert a.active_ids == b.active_ids


def test_g2_conserved_debit_cannot_be_redirected_to_other_parent() -> None:
    ledger = ready()
    plan = ledger.prepare_births("p1", opportunity(1), count=1)
    wrong = FundedBirthReceipt(
        "receipt", plan.plan_id, plan.batch_id, plan.tick,
        (PhysicalBirthDebit("wrong-debit", 0, 40, 32, 8),),
    )
    with pytest.raises(ValueError, match="differs from genetic parent"):
        ledger.commit_funded_births(wrong)
    assert ledger.births == 0
    assert ledger.pending_plan == plan
    assert ledger.commit_funded_births(paid(plan), mutate=False)


def test_duplicate_or_nonconsecutive_transfer_fails_atomically() -> None:
    ledger = ready(count=1)
    plan = ledger.prepare_births("p", opportunity(0), count=2)
    stale_double_debit = FundedBirthReceipt(
        "bad", plan.plan_id, plan.batch_id, plan.tick, (
            PhysicalBirthDebit("a", 0, 40, 32, 8),
            PhysicalBirthDebit("b", 0, 40, 32, 8),
        ),
    )
    with pytest.raises(ValueError, match="nonconsecutive"):
        ledger.commit_funded_births(stale_double_debit)
    assert ledger.births == 0
    duplicate_ids = FundedBirthReceipt(
        "bad", plan.plan_id, plan.batch_id, plan.tick, (
            PhysicalBirthDebit("same", 0, 40, 32, 8),
            PhysicalBirthDebit("same", 0, 32, 24, 8),
        ),
    )
    with pytest.raises(ValueError, match="duplicate physical"):
        ledger.commit_funded_births(duplicate_ids)
    assert ledger.births == 0


@pytest.mark.parametrize(
    "delta",
    [
        lambda r: FundedBirthReceipt(r.receipt_id, "wrong", r.batch_id, r.tick, r.debits),
        lambda r: FundedBirthReceipt(r.receipt_id, r.plan_id, "wrong", r.tick, r.debits),
        lambda r: FundedBirthReceipt(r.receipt_id, r.plan_id, r.batch_id, r.tick + 1, r.debits),
        lambda r: FundedBirthReceipt(r.receipt_id, r.plan_id, r.batch_id, r.tick, ()),
    ],
)
def test_g2_rejects_unmatched_receipts(delta) -> None:
    ledger = ready()
    plan = ledger.prepare_births("p", opportunity(0), count=1)
    with pytest.raises(ValueError):
        ledger.commit_funded_births(delta(paid(plan)))
    assert ledger.births == 0
    assert ledger.pending_plan == plan


def test_g2_rejects_cost_mismatch_even_with_energy_conservation() -> None:
    ledger = ready(cost=8)
    plan = ledger.prepare_births("p", opportunity(0), count=1)
    with pytest.raises(ValueError, match="unauthorized child energy"):
        ledger.commit_funded_births(paid(plan, cost=6))
    assert ledger.births == 0


def test_g2_stale_invalid_and_reused_plans_fail() -> None:
    ledger = ready()
    plan = ledger.prepare_births("p", opportunity(0, 1), count=1)
    with pytest.raises(ValueError, match="pending"):
        ledger.prepare_births("other", opportunity(0), count=1)
    with pytest.raises(ValueError, match="unresolved"):
        ledger.record_m_outcomes(
            MOutcomeBatch("M-episode:2", 2, (MOutcome(0, 2, "ALIVE"), MOutcome(1, 2, "ALIVE")))
        )
    ledger.abort_birth_plan(plan.plan_id)
    assert ledger.aborted_plans == ("p",)
    with pytest.raises(ValueError, match="already planned"):
        ledger.prepare_births("again", opportunity(0), count=1)
    with pytest.raises(ValueError, match="duplicate plan"):
        ledger.prepare_births("p", opportunity(0), count=1)
    ledger.record_m_outcomes(
        MOutcomeBatch("M-episode:2", 2, (MOutcome(0, 2, "ALIVE"), MOutcome(1, 2, "ALIVE")))
    )
    new = ledger.prepare_births(
        "p2", opportunity(0, batch="M-episode:2", tick=2), count=1
    )
    assert ledger.commit_funded_births(paid(new))


def test_g2_cannot_replay_receipt_or_birth_plan() -> None:
    ledger = ready()
    plan = ledger.prepare_births("p", opportunity(0), count=1)
    receipt = paid(plan)
    ledger.commit_funded_births(receipt)
    with pytest.raises(ValueError, match="no pending"):
        ledger.commit_funded_births(receipt)
    with pytest.raises(ValueError, match="already planned"):
        ledger.prepare_births("p2", opportunity(0), count=1)


def test_g2_filters_starved_and_m_only_eligibility_controls_funding() -> None:
    ledger = FundedGenesisRegistry(seed=2)
    ledger.spawn_founders(2)
    ledger.record_m_outcomes(
        MOutcomeBatch("m1", 1, (MOutcome(0, 1, "STARVED"), MOutcome(1, 1, "ALIVE", 2)))
    )
    with pytest.raises(ValueError, match="non-survivor"):
        ledger.prepare_births("invalid", opportunity(0, 1, batch="m1"), count=1)
    good = ledger.prepare_births("p", opportunity(1, batch="m1"), count=1)
    assert good.parent_ids == (1,)
    assert ledger.commit_funded_births(paid(good, cost=2))
    assert ledger.deaths[0].individual_id == 0
    assert ledger.active_ids == (1, 2)


def test_g2_surplus_weighting_requires_external_m_eligibility() -> None:
    ledger = ready()
    plan = ledger.prepare_births("weighted", opportunity(1), count=2, selection="surplus_weighted")
    assert plan.selection == "surplus_weighted"
    assert plan.parent_ids == (1, 1)
    assert ledger.commit_funded_births(paid(plan))


def test_g2_no_birth_with_legacy_one_step_api() -> None:
    ledger = ready()
    with pytest.raises(ValueError, match="requires preselected"):
        ledger.spawn_children(None)


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(batch_id="bad", tick=1, eligible_ids=(0,)),
        dict(batch_id="M-episode:1", tick=2, eligible_ids=(0,)),
        dict(batch_id="M-episode:1", tick=1, eligible_ids=(0, 0)),
        dict(batch_id="M-episode:1", tick=1, eligible_ids=(1, 0)),
    ],
)
def test_g2_opportunity_rejects_invalid_roster_or_stale_cohort(kwargs) -> None:
    ledger = ready()
    if kwargs["eligible_ids"] in ((0, 0), (1, 0)):
        with pytest.raises(ValueError, match="eligible roster"):
            BirthOpportunity(**kwargs)
    else:
        with pytest.raises(ValueError):
            ledger.prepare_births("p", BirthOpportunity(**kwargs), count=1)


def test_g2_no_plan_when_birth_cap_exceeded() -> None:
    ledger = FundedGenesisRegistry(seed=1, config=GenesisConfig(max_active=2))
    ledger.spawn_founders(2)
    ledger.record_m_outcomes(
        MOutcomeBatch("m1", 1, (MOutcome(0, 1, "ALIVE"), MOutcome(1, 1, "ALIVE")))
    )
    with pytest.raises(ValueError, match="capacity"):
        ledger.prepare_births("p", opportunity(0, batch="m1"), count=1)


def test_invalid_physical_transfer_is_not_energy_proof() -> None:
    with pytest.raises(ValueError, match="conserved"):
        PhysicalBirthDebit("d1", 0, 10, 9, 8)
    with pytest.raises(ValueError, match="viability"):
        PhysicalBirthDebit("d1", 0, 8, 0, 8)
    with pytest.raises(ValueError, match="energy"):
        PhysicalBirthDebit("d1", 0, 10, float("nan"), 8)


def test_opportunity_and_debit_are_offline_assertions_not_proof_of_m_origin() -> None:
    # Nothing in this fixture signs a source or imports/launches Minecraft.
    assert "world_source" not in {f.name for f in fields(BirthOpportunity)}
    assert "world_source" not in {f.name for f in fields(PhysicalBirthDebit)}
