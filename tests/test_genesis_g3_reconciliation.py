from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.genesis_g2_handoff import (
    BirthOpportunity,
    FundedBirthReceipt,
    FundedGenesisRegistry,
    PhysicalBirthDebit,
)
from experiments.genesis_g3_reconciliation import (
    MFundedEvent,
    MFundedLineageBridge,
    MReadback,
    MSourceIdentity,
    ParentBalance,
    SourceBoundGenesisRegistry,
    event_fingerprint,
)
from experiments.genesis_heredity import GenesisConfig, MOutcome, MOutcomeBatch

SOURCE = MSourceIdentity("offline-session", "frozen-world-snapshot", "M-ledger-rev")


def ready(*, parents: int = 2, seed: int = 9, cost: float = 2.0):
    registry = SourceBoundGenesisRegistry(seed=seed, config=GenesisConfig(birth_cost=cost))
    registry.spawn_founders(parents)
    registry.record_m_outcomes(
        MOutcomeBatch(
            "batch:1",
            1,
            tuple(MOutcome(i, 1, "ALIVE", 6.0) for i in range(parents)),
        )
    )
    bridge = MFundedLineageBridge(registry, expected_source=SOURCE, ledger_revision=10)
    return registry, bridge


def make_event(
    plan,
    *,
    event_id: str = "event:1",
    source: MSourceIdentity = SOURCE,
    revision_before: int = 10,
    cost: float = 2.0,
    first_energy: float = 20.0,
):
    balances = {parent: first_energy for parent in sorted(set(plan.parent_ids))}
    initial = tuple(ParentBalance(i, energy) for i, energy in balances.items())
    debits = []
    for index, parent_id in enumerate(plan.parent_ids):
        before = balances[parent_id]
        after = before - cost
        debits.append(PhysicalBirthDebit(f"debit:{event_id}:{index}", parent_id, before, after, cost))
        balances[parent_id] = after
    end = tuple(ParentBalance(i, energy) for i, energy in balances.items())
    receipt = FundedBirthReceipt(
        f"receipt:{event_id}", plan.plan_id, plan.batch_id, plan.tick, tuple(debits)
    )
    event = MFundedEvent(
        event_id, source, receipt, revision_before, revision_before + 1, initial, end
    )
    readback = MReadback(source, event.ledger_after_revision, event_fingerprint(event), end)
    return event, readback


def test_g3_full_parent_funding_consistent_and_replayable() -> None:
    a, bridge_a = ready(seed=9)
    b, bridge_b = ready(seed=9)
    for registry, bridge in ((a, bridge_a), (b, bridge_b)):
        plan = registry.prepare_births("plan:1", BirthOpportunity("batch:1", 1, (1,)), count=3)
        event, readback = make_event(plan)
        children = bridge.reconcile_and_commit(plan, event, readback)
        assert tuple(child.parent_id for child in children) == (1, 1, 1)
        assert all(child.generation == 1 for child in children)
        assert registry.active_ids == (0, 1, 2, 3, 4)
        assert bridge.ledger_revision == 11
        assert len(bridge.commits) == 1
        assert bridge.commits[0].child_ids == (2, 3, 4)
        assert bridge.commits[0].evidence_status == "OFFLINE_READBACK_CONSISTENT"
    assert a.lineage == b.lineage
    assert bridge_a.commits == bridge_b.commits


def test_g3_rejects_direct_unqualified_g2_commit() -> None:
    registry, _ = ready()
    plan = registry.prepare_births("p", BirthOpportunity("batch:1", 1, (0,)), count=1)
    event, _ = make_event(plan)
    with pytest.raises(ValueError, match="requires M readback"):
        registry.commit_funded_births(event.receipt)
    assert registry.pending_plan == plan
    assert registry.births == 0


def test_g3_does_not_accept_plain_g2_registry() -> None:
    old = FundedGenesisRegistry(seed=1)
    with pytest.raises(ValueError, match="source-bound"):
        MFundedLineageBridge(old, expected_source=SOURCE, ledger_revision=0)


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda event, readback: (replace(event, source=MSourceIdentity(
            "other", SOURCE.world_snapshot, SOURCE.metabolism_ledger
        )), readback), "source identity"),
        (lambda event, readback: (event, replace(readback, source=MSourceIdentity(
            SOURCE.source_session, "replaced-world", SOURCE.metabolism_ledger
        ))), "source identity"),
        (lambda event, readback: (
            replace(event, ledger_before_revision=9), readback
        ), "ledger revision"),
        (lambda event, readback: (
            event, replace(readback, ledger_revision=12)
        ), "ledger revision"),
        (lambda event, readback: (
            event, replace(readback, event_sha256="0" * 64)
        ), "readback"),
        (lambda event, readback: (
            event, replace(readback, balances_after=(ParentBalance(0, 12),))
        ), "readback"),
        (lambda event, readback: (
            replace(event, receipt=replace(event.receipt, plan_id="unexpected")), readback
        ), "G plan"),
        (lambda event, readback: (
            replace(event, receipt=replace(event.receipt, tick=2)), readback
        ), "tick"),
    ],
)
def test_g3_invalid_event_is_atomic(change, match: str) -> None:
    registry, bridge = ready(parents=1)
    plan = registry.prepare_births("p", BirthOpportunity("batch:1", 1, (0,)), count=1)
    event, readback = make_event(plan)
    bad_event, bad_readback = change(event, readback)
    with pytest.raises(ValueError, match=match):
        bridge.reconcile_and_commit(plan, bad_event, bad_readback)
    assert bridge.ledger_revision == 10
    assert bridge.commits == ()
    assert registry.births == 0
    assert registry.pending_plan == plan
    assert bridge.reconcile_and_commit(plan, event, readback)


@pytest.mark.parametrize("failure", ["before", "after", "missing", "extra"])
def test_g3_ledger_energy_snapshot_guards(failure: str) -> None:
    registry, bridge = ready(parents=1)
    plan = registry.prepare_births("p", BirthOpportunity("batch:1", 1, (0,)), count=2)
    event, _ = make_event(plan)
    if failure == "before":
        bad = replace(event, balances_before=(ParentBalance(0, 15),))
    elif failure == "after":
        bad = replace(event, balances_after=(ParentBalance(0, 17),))
    elif failure == "missing":
        bad = replace(
            event, balances_before=(ParentBalance(1, 20),),
            balances_after=(ParentBalance(1, 16),)
        )
    else:
        bad = replace(event, balances_before=(ParentBalance(0, 20), ParentBalance(1, 20)),
                      balances_after=(ParentBalance(0, 16), ParentBalance(1, 20)))
    # Self-consistent *readback* cannot waive physical parent-vs-ledger checks.
    bad_readback = MReadback(
        SOURCE, bad.ledger_after_revision, event_fingerprint(bad), bad.balances_after
    )
    with pytest.raises(ValueError, match="snapshot|debit|balance|mismatch"):
        bridge.reconcile_and_commit(plan, bad, bad_readback)
    assert registry.births == 0
    assert bridge.commits == ()


def test_g3_event_id_replay_and_old_ledger_revision_on_next_epoch() -> None:
    registry, bridge = ready(parents=1)
    plan = registry.prepare_births("p1", BirthOpportunity("batch:1", 1, (0,)), count=1)
    event, readback = make_event(plan)
    bridge.reconcile_and_commit(plan, event, readback)
    # The newborn is included in the next complete M cohort.
    registry.record_m_outcomes(
        MOutcomeBatch(
            "batch:2", 2, (MOutcome(0, 2, "ALIVE", 4), MOutcome(1, 2, "ALIVE", 4))
        )
    )
    plan2 = registry.prepare_births(
        "p2", BirthOpportunity("batch:2", 2, (0,)), count=1
    )
    old_event, old_readback = make_event(plan2, event_id="event:1", revision_before=11)
    with pytest.raises(ValueError, match="replayed M event"):
        bridge.reconcile_and_commit(plan2, old_event, old_readback)
    stale_event, stale_readback = make_event(plan2, event_id="event:2", revision_before=10)
    with pytest.raises(ValueError, match="ledger revision"):
        bridge.reconcile_and_commit(plan2, stale_event, stale_readback)
    new_event, new_readback = make_event(plan2, event_id="event:2", revision_before=11)
    assert bridge.reconcile_and_commit(plan2, new_event, new_readback)
    assert bridge.ledger_revision == 12
    assert len(bridge.commits) == 2


def test_g3_starved_parent_and_abort_do_not_forge_birth() -> None:
    registry = SourceBoundGenesisRegistry(seed=1)
    registry.spawn_founders(2)
    registry.record_m_outcomes(
        MOutcomeBatch("m1", 1, (MOutcome(0, 1, "STARVED"), MOutcome(1, 1, "ALIVE", 8)))
    )
    bridge = MFundedLineageBridge(registry, expected_source=SOURCE, ledger_revision=0)
    with pytest.raises(ValueError, match="non-survivor"):
        registry.prepare_births("bad", BirthOpportunity("m1", 1, (0,)), count=1)
    plan = registry.prepare_births("p", BirthOpportunity("m1", 1, (1,)), count=1)
    registry.abort_birth_plan(plan.plan_id)
    assert registry.births == 0
    assert bridge.commits == ()
    assert tuple(row.individual_id for row in registry.deaths) == (0,)


def test_g3_mutation_off_and_randomized_genome_controls_remain_distinct() -> None:
    inherited, bridge_a = ready(parents=1, seed=44)
    independent, bridge_b = ready(parents=1, seed=44)
    for registry, bridge, inherit in (
        (inherited, bridge_a, True), (independent, bridge_b, False)
    ):
        plan = registry.prepare_births("p", BirthOpportunity("batch:1", 1, (0,)), count=1)
        event, readback = make_event(plan)
        bridge.reconcile_and_commit(plan, event, readback, inherit=inherit, mutate=False)
    assert inherited.lineage[1].genome == inherited.lineage[0].genome
    assert independent.lineage[1].genome != independent.lineage[0].genome


def test_g3_bad_evidence_shapes_fail_before_any_born() -> None:
    with pytest.raises(ValueError, match="source identity"):
        MSourceIdentity("", "world", "M")
    with pytest.raises(ValueError, match="balance ID"):
        ParentBalance(True, 2)
    with pytest.raises(ValueError, match="energy balance"):
        ParentBalance(0, float("nan"))
    with pytest.raises(ValueError, match="readback digest"):
        MReadback(SOURCE, 1, "not-a-hash", (ParentBalance(0, 1),))
    registry, bridge = ready(parents=1)
    plan = registry.prepare_births("p", BirthOpportunity("batch:1", 1, (0,)), count=1)
    with pytest.raises(ValueError, match="revision transition"):
        event, _ = make_event(plan)
        replace(event, ledger_after_revision=event.ledger_before_revision)
    assert bridge.commits == ()


def test_g3_hash_not_an_authentication_signature() -> None:
    registry, _ = ready(parents=1)
    plan = registry.prepare_births("p", BirthOpportunity("batch:1", 1, (0,)), count=1)
    event, _ = make_event(plan)
    # A caller who forges BOTH event and readback can still compute this hash.
    # M/R original-source authentication remains an external mandatory gate.
    forged = replace(event, balances_before=(ParentBalance(0, 100),),
                     balances_after=(ParentBalance(0, 98),))
    assert event_fingerprint(forged) != event_fingerprint(event)
    assert len(event_fingerprint(forged)) == 64
