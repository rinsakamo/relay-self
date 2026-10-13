from __future__ import annotations

import pytest

from experiments.metabolism_viability import (
    Interoception,
    MetabolismConfig,
    combat_respawn,
    initial_body,
    metabolism_step,
    observe_energy,
)


def test_wait_always_spends_basal_energy_and_eventually_starves() -> None:
    config = MetabolismConfig(initial_energy=1.0, basal_cost=0.25)
    state = initial_body(config)
    for _ in range(3):
        outcome = metabolism_step(state, action="WAIT", consumed_food_units=0, config=config)
        assert not outcome.terminal_now
        state = outcome.after
    outcome = metabolism_step(state, action="WAIT", consumed_food_units=0, config=config)
    assert outcome.after.energy == 0.0
    assert outcome.terminal_now
    with pytest.raises(ValueError, match="terminal"):
        metabolism_step(outcome.after, action="WAIT", consumed_food_units=1, config=config)


def test_movement_fighting_cost_more_than_waiting() -> None:
    config = MetabolismConfig()
    state = initial_body(config)
    wait = metabolism_step(state, action="WAIT", consumed_food_units=0, config=config)
    move = metabolism_step(state, action="MOVE", consumed_food_units=0, config=config)
    fight = metabolism_step(state, action="FIGHT", consumed_food_units=0, config=config)
    assert wait.after.energy > move.after.energy > fight.after.energy


def test_verified_food_adds_energy_but_cannot_overfill_capacity() -> None:
    config = MetabolismConfig(initial_energy=19.0, capacity=20.0)
    outcome = metabolism_step(initial_body(config), action="WAIT", consumed_food_units=2, config=config)
    assert outcome.intake == 8.0
    assert outcome.overflow == 7.0
    assert outcome.after.energy == 19.5
    assert outcome.after.meals == 2


def test_hp_knockout_respawn_does_not_refill_or_reset_body() -> None:
    config = MetabolismConfig(initial_energy=6.0)
    before = metabolism_step(initial_body(config), action="FIGHT", consumed_food_units=0, config=config).after
    after = combat_respawn(before)
    assert after.energy == before.energy
    assert after.tick == before.tick
    assert after.meals == before.meals
    assert after.knockouts == 1
    assert not after.terminal


def test_interoception_zero_gain_cannot_track_energy() -> None:
    config = MetabolismConfig()
    full = initial_body(config)
    depleted = metabolism_step(full, action="FIGHT", consumed_food_units=0, config=config).after
    blind = Interoception(gain=0.0, bias=3.0)
    assert observe_energy(full, blind).reading == observe_energy(depleted, blind).reading
    sensing = Interoception(gain=1.0, quantum=0.01)
    assert observe_energy(full, sensing).reading != observe_energy(depleted, sensing).reading


def test_physically_starved_body_cannot_respawn() -> None:
    config = MetabolismConfig(initial_energy=0.5, basal_cost=0.5)
    starved = metabolism_step(initial_body(config), action="WAIT", consumed_food_units=0, config=config).after
    with pytest.raises(ValueError, match="starved"):
        combat_respawn(starved)


@pytest.mark.parametrize("action,food", [("JUMP", 0), ("WAIT", -1), ("WAIT", 1.0), ("WAIT", True)])
def test_invalid_inputs_fail_closed(action: str, food: int) -> None:
    config = MetabolismConfig()
    with pytest.raises(ValueError):
        metabolism_step(initial_body(config), action=action, consumed_food_units=food, config=config)


def test_invalid_configuration_and_sensor_fail_closed() -> None:
    with pytest.raises(ValueError):
        MetabolismConfig(basal_cost=0)
    with pytest.raises(ValueError):
        MetabolismConfig(initial_energy=21)
    with pytest.raises(ValueError):
        MetabolismConfig(food_energy=float("nan"))
    with pytest.raises(ValueError):
        Interoception(gain=-1)
    with pytest.raises(ValueError):
        Interoception(quantum=0)
