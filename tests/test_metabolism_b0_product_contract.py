"""M B0 one-tick cognition with *actual* S #634 ledger, L0 and SelfBody.

Import this test only with the exact product checkout in the M CI.
These are synthetic native probes; NOT original certified Minecraft Worlds.
"""
from dataclasses import replace

import pytest

from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from adapters.mineflayer.self_body_m0_projection import compose_b0_cognition_views
from experiments.metabolism_b0_cognition import read_b0_resource_context
from experiments.metabolism_viability import Interoception, MetabolismConfig
from test_self_live_think import native_probe


def make_views(energy=12.0, *, sid="b0-cognition", sensor=None, config=None):
    config = config or MetabolismConfig()
    sensor = sensor or Interoception(quantum=0.1)
    ledger = B0EnergyLedger(sid, config=config, sensor=sensor)
    ledger.body = replace(ledger.body, energy=energy)
    probe = native_probe(8, 3.0, sid=sid)
    decision = ledger.decide(probe)
    views = compose_b0_cognition_views(
        probe, ledger, decision, self_id="B0-self", epoch_id="epoch-8"
    )
    return views, ledger, decision


def test_product_b0_real_owner_wait_move_costs_are_model_specific():
    views, ledger, decision = make_views()
    result = read_b0_resource_context(
        views, config=ledger.config, sensor=ledger.sensor, noise_bound=0,
    )
    assert result.session_id == ledger.session_id
    assert result.self_id == "B0-self"
    assert result.epoch_id == "epoch-8"
    assert result.native_seq == decision.probe_seq == 8
    assert result.owner_tick == decision.body_tick == ledger.body.tick
    assert result.original_l0_kind == decision.kind == views.l0_kind
    assert [f.activity for f in result.facts] == ["WAIT", "MOVE"]
    assert [f.modeled_energy_cost for f in result.facts] == pytest.approx(
        [ledger.config.basal_cost,
         ledger.config.basal_cost + ledger.config.move_cost]
    )
    assert [f.affordability for f in result.facts] == [
        "MODEL_AFFORDABLE", "MODEL_AFFORDABLE"
    ]
    assert result.action_authority is False
    assert result.action_issues == result.learning_updates == result.habit_grants == 0
    assert not hasattr(result, "selected_action")
    assert not hasattr(result, "true_energy")
    assert not hasattr(result, "physical_exhaustion")
    assert views.body.observed("energy").value is None
    assert ledger.body.energy == 12


def test_low_b0_sensed_energy_separates_wait_move_without_changing_l0():
    high, high_ledger, high_decision = make_views(12.0)
    low, low_ledger, low_decision = make_views(0.6)
    high_r = read_b0_resource_context(
        high, config=high_ledger.config, sensor=high_ledger.sensor,
        noise_bound=0,
    )
    low_r = read_b0_resource_context(
        low, config=low_ledger.config, sensor=low_ledger.sensor,
        noise_bound=0,
    )
    assert [f.affordability for f in low_r.facts] == [
        "MODEL_AFFORDABLE", "MODEL_INSUFFICIENT"
    ]
    assert [f.affordability for f in high_r.facts] == [
        "MODEL_AFFORDABLE", "MODEL_AFFORDABLE"
    ]
    assert low_decision.kind == high_decision.kind
    assert low_r.original_l0_kind == low_decision.kind
    assert low_ledger.body.energy == 0.6  # no write or food credit


def test_blind_b0_sensor_cheap_null_does_not_mint_resource_confidence():
    blind = Interoception(gain=0, bias=3.0)
    low, low_ledger, _ = make_views(0.6, sensor=blind)
    high, high_ledger, _ = make_views(12.0, sensor=blind)
    assert low.body.sensed("m0_energy_sensor").value == 3
    assert high.body.sensed("m0_energy_sensor").value == 3
    low_r = read_b0_resource_context(
        low, config=low_ledger.config, sensor=blind, noise_bound=0,
    )
    high_r = read_b0_resource_context(
        high, config=high_ledger.config, sensor=blind, noise_bound=0,
    )
    assert low_r == high_r
    assert [f.affordability for f in low_r.facts] == ["UNKNOWN", "UNKNOWN"]
    assert low_r.energy_lower is None


def test_no_noise_bound_and_coarse_quantization_fail_to_confidently_choose():
    views, ledger, _ = make_views(0.6)
    unknown = read_b0_resource_context(
        views, config=ledger.config, sensor=ledger.sensor,
    )
    assert [f.affordability for f in unknown.facts] == ["UNKNOWN", "UNKNOWN"]
    coarse = Interoception(quantum=1.0)
    new_views, new_ledger, _ = make_views(0.6, sensor=coarse)
    coarse_r = read_b0_resource_context(
        new_views, config=new_ledger.config, sensor=coarse, noise_bound=0,
    )
    assert coarse_r.facts[1].affordability == "MODEL_AMBIGUOUS"


def test_original_native_food_and_s51_eat_are_not_minted_by_b0_hint():
    views, ledger, _ = make_views()
    before = ledger.body
    before_credit = ledger.credit_count
    first = read_b0_resource_context(
        views, config=ledger.config, sensor=ledger.sensor, noise_bound=0,
    )
    second = read_b0_resource_context(
        views, config=ledger.config, sensor=ledger.sensor, noise_bound=0,
    )
    assert first == second
    assert ledger.body == before
    assert ledger.credit_count == before_credit == 0
    assert len(first.facts) == 2
    assert not any(f.activity == "EAT" for f in first.facts)
    assert first.source_scope.endswith("NOT_S49_OR_WORLD_ATTESTED")


@pytest.mark.parametrize("attack", [
    "scope", "tick", "native", "selfbody", "owner_source", "owner_reference",
    "reading", "native_provenance", "session",
])
def test_owner_origin_and_epoch_tampering_rejected(attack):
    views, ledger, _ = make_views()
    item = views.body.interoceptions[0]
    if attack == "scope":
        views = replace(views, source_scope="NATIVE_ATTESTED")
    elif attack == "tick":
        views = replace(views, sensor_tick=views.sensor_tick + 1)
    elif attack == "native":
        views = replace(
            views, body=replace(
                views.body, observation=replace(views.body.observation, native_seq=9),
            ),
        )
    elif attack == "selfbody":
        views = replace(views, body=replace(views.body, self_id="foreign"))
    elif attack == "owner_source":
        item = replace(item, owner_provenance=replace(
            item.owner_provenance, source="fake",
        ))
    elif attack == "owner_reference":
        item = replace(item, owner_provenance=replace(
            item.owner_provenance, reference="forged",
        ))
    elif attack == "reading":
        item = replace(item, field=replace(item.field, value=item.field.value + 5))
    elif attack == "native_provenance":
        item = replace(item, native_provenance=replace(
            item.native_provenance, reference="forged",
        ))
    elif attack == "session":
        views = replace(views, body=replace(views.body, session_id="foreign"))
    if attack in (
        "owner_source", "owner_reference", "reading", "native_provenance",
    ):
        body = replace(views.body, interoceptions=(item,))
        views = replace(views, body=body, world=replace(views.world, self_body=body))
    with pytest.raises((ValueError, AttributeError)):
        read_b0_resource_context(
            views, config=ledger.config, sensor=ledger.sensor, noise_bound=0,
        )


def test_b0_profile_assumption_remains_conditional_not_native_attestation():
    views, ledger, _ = make_views(0.6)
    correct = read_b0_resource_context(
        views, config=ledger.config, sensor=ledger.sensor, noise_bound=0,
    )
    wrong_cost = replace(ledger.config, move_cost=0.01)
    hypothetical = read_b0_resource_context(
        views, config=wrong_cost, sensor=ledger.sensor, noise_bound=0,
    )
    assert correct.facts[1].affordability == "MODEL_INSUFFICIENT"
    assert hypothetical.facts[1].affordability == "MODEL_AFFORDABLE"
    # Contract limitation: only the S/B0 owner can authenticate config
    # identity; a caller-provided cost cannot be certified here.


@pytest.mark.parametrize("invalid", [-1, True, float("nan"), float("inf")])
def test_invalid_noise_rejected(invalid):
    views, ledger, _ = make_views()
    with pytest.raises(ValueError):
        read_b0_resource_context(
            views, config=ledger.config, sensor=ledger.sensor,
            noise_bound=invalid,
        )
