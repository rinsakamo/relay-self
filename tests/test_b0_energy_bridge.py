"""B0 S51->M0 typed synthetic bridge tests; no live World."""
from dataclasses import replace

import pytest

import test_feature_s46_eat as s46
from adapters.mineflayer.b0_energy_bridge import (
    B0_SENSOR_SEEK_THRESHOLD,
    B0EnergyLedger,
    B0EnergyRejected,
    nofood_native_wait,
    verify_starvation_reentry_denied,
)
from adapters.mineflayer.eat_execution import EatingActionReceipt
from adapters.mineflayer.python_protocol import MineflayerInventoryItem
from experiments.metabolism_viability import Interoception, MetabolismConfig
from relay_self.action import ActionLifecycle
from relay_self.action_supervision import ActionSupervisor
from relay_self.eat_hunger import EatingOutcome
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


def _before():
    p = s46.case()
    return replace(p, snapshot=replace(
        p.snapshot,
        inventory=(MineflayerInventoryItem("rotten_flesh", 2, 4),),
    ))


def _receipt(before, *, unknown=False):
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
    terminal = (supervisor.mark_unknown("b0-eat", at_ns=6, provenance=src) if unknown
                else supervisor.record_outcome("b0-eat", at_ns=6, provenance=src))
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
    {"action_id": "forged-other-action"},
    {"provenance": Provenance("operator", "forged-outcome")},
])
def test_invalid_eat_never_credit(changes):
    p = _before()
    ledger = B0EnergyLedger(p.session_id)
    valid = _receipt(p)
    bad = replace(valid, outcome=replace(valid.outcome, **changes))
    with pytest.raises(B0EnergyRejected):
        ledger.step("WAIT", eating=bad)
    assert ledger.body.tick == ledger.credit_count == ledger.body.meals == 0


def test_unknown_eat_never_credits_even_with_claimed_food_delta():
    before = _before()
    ledger = B0EnergyLedger(before.session_id)
    with pytest.raises(B0EnergyRejected):
        ledger.step("WAIT", eating=_receipt(before, unknown=True))
    assert ledger.credit_count == ledger.body.meals == ledger.body.tick == 0


def test_foreign_and_stale_decision_probes_do_not_advance_l0_or_m0():
    before = _before()
    ledger = B0EnergyLedger(before.session_id)
    with pytest.raises(B0EnergyRejected):
        ledger.decide(replace(before, session_id="foreign"))
    assert ledger.decide(before).kind == "EAT"
    with pytest.raises(B0EnergyRejected):
        ledger.decide(before)
    assert ledger.body.tick == ledger.credit_count == 0


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


def _empty_food_world():
    origin = _before()
    return replace(
        origin,
        snapshot=replace(origin.snapshot, food=20, inventory=()),
    )


def test_nofood_native_stream_starves_exactly_once_and_rejects_new_l0():
    origin = _empty_food_world()
    ledger = B0EnergyLedger(origin.session_id)
    observed = []
    for epoch in range(64):
        probe = replace(
            origin, seq=origin.seq + epoch,
            request_id=f"synthetic-nofood-{epoch:02d}",
        )
        decision, transition = nofood_native_wait(ledger, probe)
        assert decision.kind == "WAIT" and decision.body_tick == epoch
        assert transition.intake == 0
        assert transition.expenditure == 0.5
        assert ledger.credit_count == ledger.body.meals == 0
        observed.append(transition.terminal_now)
        if transition.terminal_now:
            break
    assert epoch == 23
    assert observed == [False] * 23 + [True]
    assert ledger.body.energy == 0
    assert ledger.body.tick == 24
    assert ledger.body.terminal
    post = replace(
        origin, seq=probe.seq + 1, request_id="synthetic-nofood-postterminal",
    )
    snapshot = ledger.body
    verify_starvation_reentry_denied(ledger, post)
    assert ledger.body == snapshot
    assert ledger.credit_count == 0


def test_nofood_controls_reject_inventory_before_any_metabolic_charge():
    origin = _empty_food_world()
    ledger = B0EnergyLedger(origin.session_id)
    observed_food = replace(
        origin,
        snapshot=replace(origin.snapshot, inventory=(
            MineflayerInventoryItem("rotten_flesh", 1, 4),
        )),
    )
    with pytest.raises(B0EnergyRejected, match="no-food source"):
        nofood_native_wait(ledger, observed_food)
    assert ledger.body.tick == 0 and ledger.body.energy == 12
    assert ledger.credit_count == 0


def test_nofood_terminal_denial_requires_fresh_matching_world_source():
    origin = _empty_food_world()
    ledger = B0EnergyLedger(
        origin.session_id,
        config=MetabolismConfig(initial_energy=0.5),
    )
    _, terminal = nofood_native_wait(ledger, origin)
    assert terminal.terminal_now
    with pytest.raises(B0EnergyRejected, match="post-terminal"):
        verify_starvation_reentry_denied(ledger, origin)
    with pytest.raises(B0EnergyRejected, match="post-terminal"):
        verify_starvation_reentry_denied(ledger, replace(
            origin, seq=origin.seq + 1, session_id="foreign",
            request_id="foreign-next",
        ))
    assert ledger.body.tick == 1 and ledger.body.terminal


def _forage_probe():
    import test_b0_ground_foraging as ground

    original = ground._ground()
    return replace(
        original, snapshot=replace(original.snapshot, food=13.0),
    )


def _ledger_after_identical_waits(source, *, policy, sensor, waits):
    ledger = B0EnergyLedger(
        source.session_id, forage_policy=policy, sensor=sensor,
    )
    for _ in range(waits):
        transition = ledger.step("WAIT")
        assert not transition.terminal_now
    return ledger


def test_opt_in_interoception_changes_l0_seek_on_matched_world_and_body():
    source = _forage_probe()
    assert B0_SENSOR_SEEK_THRESHOLD == 8.0
    # Same native-shaped source, exact M0 state/cost/decision-tick budget.
    on = _ledger_after_identical_waits(
        source, policy="sensor_gate", sensor=Interoception(), waits=10,
    )
    sham = _ledger_after_identical_waits(
        source, policy="sensor_gate", sensor=Interoception(gain=1), waits=10,
    )
    masked = _ledger_after_identical_waits(
        source, policy="sensor_gate",
        sensor=Interoception(gain=0, bias=12), waits=10,
    )
    cheap = _ledger_after_identical_waits(
        source, policy="native_only", sensor=Interoception(), waits=10,
    )
    assert {x.body.energy for x in (on, sham, masked, cheap)} == {7.0}
    assert {x.body.tick for x in (on, sham, masked, cheap)} == {10}
    assert [x.decide(source).kind for x in (on, sham, masked, cheap)] == [
        "SEEK", "SEEK", "WAIT", "SEEK",
    ]
    assert on.credit_count == sham.credit_count == masked.credit_count == cheap.credit_count == 0
    assert on.body == sham.body == masked.body == cheap.body


def test_opt_in_sensor_gate_waits_when_true_body_high_without_truth_leak():
    source = _forage_probe()
    on = B0EnergyLedger(source.session_id, forage_policy="sensor_gate")
    masked = B0EnergyLedger(
        source.session_id, forage_policy="sensor_gate",
        sensor=Interoception(gain=0, bias=12),
    )
    cheap = B0EnergyLedger(source.session_id)
    assert on.decide(source).kind == "WAIT"
    assert masked.decide(source).kind == "WAIT"
    assert cheap.decide(source).kind == "SEEK"
    assert on.body == masked.body == cheap.body


def test_sensor_gate_does_not_disable_eat_or_terminal_safety():
    source = _forage_probe()
    eaten = replace(
        source,
        snapshot=replace(source.snapshot, inventory=(
            MineflayerInventoryItem("rotten_flesh", 1, 4),
        )),
    )
    ledger = B0EnergyLedger(
        source.session_id, forage_policy="sensor_gate",
        config=MetabolismConfig(initial_energy=0.5),
        sensor=Interoception(gain=0, bias=12),
    )
    assert ledger.decide(eaten).kind == "EAT"
    assert ledger.step("WAIT").terminal_now
    with pytest.raises(B0EnergyRejected):
        ledger.decide(replace(eaten, seq=eaten.seq + 1, request_id="dead-probe"))
    with pytest.raises(B0EnergyRejected):
        ledger.step("WAIT")
    assert ledger.body.terminal and ledger.body.energy == 0


def test_sensor_gate_rejects_bad_configuration():
    source = _forage_probe()
    with pytest.raises(B0EnergyRejected, match="policy"):
        B0EnergyLedger(source.session_id, forage_policy="best")
    with pytest.raises(B0EnergyRejected, match="interoception"):
        B0EnergyLedger(source.session_id, sensor="fake")
