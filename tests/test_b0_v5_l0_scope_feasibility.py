"""S-side V5 *source-only* feasibility of bacteria-level L0+M0.

Uses the REAL S B0EnergyLedger / interoception / native-shaped ground source.
There is no V5 live study profile, World clock qualification, action issue,
food intake, native cheap-baseline implementation, or scientific admission.
"""
import pytest


V5_CONCEPTUAL_ARMS = (
    "SENSOR_ON", "SHAM_ON", "MASKED_HIGH",
    "ALWAYS_SEEK", "ALWAYS_WAIT", "EQUAL_INFORMATION_THRESHOLD",
)
V5_REGIMES = ("LOW_ENERGY", "HIGH_ENERGY")


def _same_hungry_one_item():
    import test_b0_ground_foraging as ground

    original = ground._ground()
    from dataclasses import replace

    source = replace(original, snapshot=replace(original.snapshot, food=13.0))
    from adapters.mineflayer.b0_ground_foraging import select_ground_target
    target = select_ground_target(source)
    assert source.snapshot.inventory == ()
    assert not source.snapshot.nearby_entities_coverage.truncated
    assert target.entity_id == 70
    return source


def _fresh_after_one_basal_wait(source, initial, arm):
    from experiments.metabolism_viability import Interoception, MetabolismConfig

    config = MetabolismConfig(initial_energy=initial)
    kwargs = {
        "SENSOR_ON": ("sensor_gate", Interoception()),
        "SHAM_ON": ("sensor_gate", Interoception(gain=1.0, bias=0.0)),
        "MASKED_HIGH": ("sensor_gate", Interoception(gain=0.0, bias=12.0)),
        "CHEAP_NATIVE": ("native_only", Interoception()),
    }
    policy, sensor = kwargs[arm]
    from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger

    ledger = B0EnergyLedger(
        source.session_id, config=config, sensor=sensor, forage_policy=policy,
    )
    transition = ledger.step("WAIT")
    assert transition.intake == 0
    assert transition.expenditure == config.basal_cost == 0.5
    assert transition.after.tick == 1 and not transition.terminal_now
    assert ledger.credit_count == ledger.body.meals == 0
    return ledger


@pytest.mark.parametrize(
    ("regime", "initial", "energy", "sensed", "on_action"),
    [
        ("LOW_ENERGY", 4.0, 3.5, 4.0, "SEEK"),
        ("HIGH_ENERGY", 20.0, 19.5, 20.0, "WAIT"),
    ],
)
def test_v5_same_native_source_different_m0_cheap_l0_choices(
    regime, initial, energy, sensed, on_action,
):
    """Different independently initialized bodies; NOT a live World comparison."""
    from adapters.mineflayer.b0_energy_bridge import B0_SENSOR_SEEK_THRESHOLD

    assert regime in V5_REGIMES and B0_SENSOR_SEEK_THRESHOLD == 8.0
    p = _same_hungry_one_item()
    ledgers = {
        arm: _fresh_after_one_basal_wait(p, initial, arm)
        for arm in ("SENSOR_ON", "SHAM_ON", "MASKED_HIGH", "CHEAP_NATIVE")
    }
    decisions = {arm: ledger.decide(p) for arm, ledger in ledgers.items()}
    assert {ledger.body.energy for ledger in ledgers.values()} == {energy}
    assert {ledger.body.tick for ledger in ledgers.values()} == {1}
    assert {ledger.body.meals for ledger in ledgers.values()} == {0}
    assert {ledger.credit_count for ledger in ledgers.values()} == {0}
    assert {decision.probe_seq for decision in decisions.values()} == {p.seq}
    assert decisions["SENSOR_ON"].sensor_reading == sensed
    assert decisions["SHAM_ON"].sensor_reading == sensed
    assert decisions["MASKED_HIGH"].sensor_reading == 12.0
    assert decisions["SENSOR_ON"].kind == on_action
    assert decisions["SHAM_ON"].kind == on_action
    assert decisions["MASKED_HIGH"].kind == "WAIT"
    assert decisions["CHEAP_NATIVE"].kind == "SEEK"
    assert decisions["SENSOR_ON"].kind == (
        "SEEK" if sensed <= B0_SENSOR_SEEK_THRESHOLD else "WAIT"
    )
    # EQUAL_INFORMATION_THRESHOLD is a *counterfactual one-line comparator*;
    # an equal-info cheap rule duplicates the implemented ON choice.
    # ALWAYS_SEEK and ALWAYS_WAIT are ALSO prospective counterfactual controls,
    # not implemented S50/S51 World issuers.
    blind_reference_choices = {
        "ALWAYS_SEEK": "SEEK",
        "ALWAYS_WAIT": "WAIT",
        "EQUAL_INFORMATION_THRESHOLD": on_action,
    }
    assert tuple(blind_reference_choices) == V5_CONCEPTUAL_ARMS[3:]
    assert blind_reference_choices["EQUAL_INFORMATION_THRESHOLD"] == (
        decisions["SENSOR_ON"].kind
    )
    # Pure choice must not invent S16 issuance/OUTCOME or M0 food credit.
    from adapters.mineflayer.b0_energy_bridge import B0EnergyRejected

    for ledger in ledgers.values():
        assert ledger.body.energy == energy
        assert ledger.body.tick == 1
        with pytest.raises(B0EnergyRejected, match="fresh World probe"):
            ledger.decide(p)


def test_v5_g0_rejects_foreign_source_and_incomplete_ground_coverage():
    from adapters.mineflayer.b0_energy_bridge import B0EnergyRejected

    p = _same_hungry_one_item()
    from dataclasses import replace

    ledger = _fresh_after_one_basal_wait(p, 4.0, "SENSOR_ON")
    foreign = replace(p, session_id="other-native-session")
    with pytest.raises(B0EnergyRejected, match="fresh World probe"):
        ledger.decide(foreign)
    incomplete = replace(
        p, snapshot=replace(
            p.snapshot,
            nearby_entities_coverage=replace(
                p.snapshot.nearby_entities_coverage, truncated=True,
            ),
        ),
    )
    from adapters.mineflayer.b0_ground_foraging import GroundRejected, select_ground_target

    with pytest.raises(GroundRejected):
        select_ground_target(incomplete)
    assert ledger.body.energy == 3.5 and ledger.body.tick == 1
    assert ledger.credit_count == 0


def test_v5_is_not_implemented_as_existing_v2_or_live_permission():
    from adapters.mineflayer.b0_two_epoch import V2_ARMS, V2_FIRST_ITEM_TICK

    # V5's six arms and independently assigned LOW/HIGH energy are neither
    # a hidden alias nor a retroactive change to the frozen V2 study path.
    assert V2_FIRST_ITEM_TICK == 11
    assert set(V2_ARMS) == {
        "SENSOR_ON", "SHAM_ON", "SENSOR_MASKED", "CHEAP_NATIVE",
    }
    assert set(V5_CONCEPTUAL_ARMS) != set(V2_ARMS)
    assert V5_REGIMES == ("LOW_ENERGY", "HIGH_ENERGY")
    # There is no test-side external food schedule, physical World result,
    # reference Golden admission, or fresh operator authorization.
