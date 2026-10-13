"""B0 S51->M0 typed synthetic bridge tests; no live World."""
from dataclasses import replace

import pytest

import test_feature_s46_eat as s46
from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger, B0EnergyRejected
from adapters.mineflayer.eat_execution import EatingActionReceipt
from adapters.mineflayer.python_protocol import MineflayerInventoryItem
from experiments.metabolism_viability import Interoception, MetabolismConfig
from relay_self.action import ActionLifecycle
from relay_self.action_supervision import ActionSupervisor
from relay_self.eat_hunger import EatingOutcome
from relay_self.intent import IntentCommitment
from relay_self.skill import SkillExecution


def _before():
    p = s46.case()
    return replace(p, snapshot=replace(
        p.snapshot,
        inventory=(MineflayerInventoryItem("rotten_flesh", 2, 4),),
    ))


def _receipt(before):
    src = before.provenance
    intent = IntentCommitment()
    intent.commit("test-eat", objective="eat", at_ns=1, provenance=src)
    skill = SkillExecution.start(
        "test-skill", skill_id="eat", intent_commitment=intent,
        at_ns=2, provenance=src,
    )
    proposed = ActionLifecycle.propose(
        "b0-eat", skill_execution=skill, intent_commitment=intent,
        at_ns=3, provenance=src,
    )
    authorized = proposed.authorize(
        at_ns=4, authority="synthetic-test-only", provenance=src,
    )
    supervisor = ActionSupervisor()
    issued = supervisor.issue(
        authorized, at_ns=5, deadline_ns=200, provenance=src,
    )
    assert issued.action_id == "b0-eat"
    terminal = supervisor.record_outcome("b0-eat", at_ns=6, provenance=src)
    outcome = EatingOutcome(
        before.session_id, "b0-eat", before.snapshot.food, 12.0,
        "rotten_flesh", 2, 1, before.seq + 4, src,
    )
    return EatingActionReceipt(terminal, outcome)


def test_real_contract_shaped_eat_credit_then_fresh_next_l0():
    before = _before()
    ledger = B0EnergyLedger(before.session_id)
    decision = ledger.decide(before)
    assert decision.kind == "EAT" and decision.sensor_reading == 12
    receipt = _receipt(before)
    transition = ledger.step("WAIT", eating=receipt)
    assert transition.intake == 4
    assert ledger.body.energy == 15.5
    assert ledger.body.meals == ledger.credit_count == 1
    after = replace(
        before, seq=receipt.outcome.after_probe_seq + 1,
        request_id="b0-next-epoch",
        snapshot=replace(before.snapshot, food=18.0, inventory=(
            MineflayerInventoryItem("rotten_flesh", 1, 4),
        )),
    )
    next_l0 = ledger.decide(after)
    assert next_l0.kind == "WAIT" and next_l0.body_tick == 1
    assert next_l0.sensor_reading == 16
    with pytest.raises(B0EnergyRejected):
        ledger.step("WAIT", eating=receipt)
    with pytest.raises(B0EnergyRejected):
        ledger.decide(after)
    assert ledger.credit_count == 1 and ledger.body.tick == 1


@pytest.mark.parametrize("changes", [
    {"count_after": 2},
    {"food_after": 7},
    {"session_id": "foreign"},
    {"after_probe_seq": -1},
    {"consumed_item": "stone"},
])
def test_invalid_eat_never_credit(changes):
    p = _before()
    ledger = B0EnergyLedger(p.session_id)
    valid = _receipt(p)
    bad = replace(valid, outcome=replace(valid.outcome, **changes))
    with pytest.raises(B0EnergyRejected):
        ledger.step("WAIT", eating=bad)
    assert ledger.body.tick == ledger.credit_count == ledger.body.meals == 0


def test_pickup_and_movement_do_not_count_as_eating():
    p = _before()
    ledger = B0EnergyLedger(p.session_id)
    assert ledger.step("MOVE").expenditure == 0.75
    assert ledger.body.energy == 11.25 and ledger.credit_count == 0
    ledger.step("WAIT")
    assert ledger.body.energy == 10.75 and ledger.credit_count == 0


def test_wait_exhaustion_is_irreversible_even_with_later_food():
    p = _before()
    ledger = B0EnergyLedger(
        p.session_id, config=MetabolismConfig(initial_energy=1, basal_cost=0.5),
    )
    assert not ledger.step("WAIT").terminal_now
    assert ledger.step("WAIT").terminal_now
    assert ledger.body.terminal and ledger.body.energy == 0
    with pytest.raises(B0EnergyRejected):
        ledger.step("WAIT", eating=_receipt(p))
    with pytest.raises(B0EnergyRejected):
        ledger.decide(p)


def test_interoception_zero_gain_hides_true_energy():
    p = _before()
    ledger = B0EnergyLedger(p.session_id, sensor=Interoception(gain=0, bias=3))
    a = ledger.decide(p)
    ledger.step("MOVE")
    b = ledger.decide(replace(p, seq=p.seq + 1, request_id="next"))
    assert a.sensor_reading == b.sensor_reading == 3
    assert a.body_tick == 0 and b.body_tick == 1


def test_eat_receipt_cannot_be_used_as_move_credit():
    p = _before()
    ledger = B0EnergyLedger(p.session_id)
    with pytest.raises(B0EnergyRejected):
        ledger.step("MOVE", eating=_receipt(p))
    assert ledger.credit_count == 0
