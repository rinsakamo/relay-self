"""B0 two-epoch control and source gates; no Java/Node/World startup."""
import asyncio
from dataclasses import replace

import pytest

import test_feature_s46_eat as s46
from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from adapters.mineflayer.b0_two_epoch import (
    B0TwoEpochRejected,
    _admit_hunger_wait,
    run_two_ground_epochs,
)
from adapters.mineflayer.python_protocol import MineflayerInventoryItem
from experiments.metabolism_viability import MetabolismConfig


def test_two_epoch_hunger_wait_requires_real_item_free_source():
    probe = s46.case()
    no_item = replace(probe, snapshot=replace(
        probe.snapshot, inventory=(),
    ))
    ledger = B0EnergyLedger(no_item.session_id)
    trace = _admit_hunger_wait(ledger, no_item)
    assert trace["l0_kind"] == "WAIT"
    assert trace["issued_action"] is False
    assert trace["probe_seq"] == no_item.seq
    assert ledger.body.tick == 0
    with pytest.raises(B0TwoEpochRejected, match="no item fixture"):
        _admit_hunger_wait(ledger, replace(
            no_item, seq=no_item.seq + 1,
            snapshot=replace(no_item.snapshot, inventory=(
                MineflayerInventoryItem("rotten_flesh", 1, 5),
            )),
        ))


def test_two_epoch_runner_refuses_stale_or_used_body_before_world():
    probe = s46.case()
    ledger = B0EnergyLedger(probe.session_id)
    with pytest.raises(B0TwoEpochRejected, match="fresh live"):
        asyncio.run(run_two_ground_epochs(None, None, ledger, [{"already": "used"}]))
    terminal = B0EnergyLedger(
        probe.session_id,
        config=MetabolismConfig(initial_energy=0.5),
    )
    terminal.step("WAIT")
    assert terminal.body.terminal
    with pytest.raises(B0TwoEpochRejected, match="fresh live"):
        asyncio.run(run_two_ground_epochs(None, None, terminal, []))


def test_nonforcing_two_epoch_prelaunch_rejects_used_trace():
    probe = s46.case()
    ledger = B0EnergyLedger(probe.session_id, forage_policy="sensor_gate")
    with pytest.raises(B0TwoEpochRejected, match="fresh live"):
        asyncio.run(run_two_ground_epochs(
            None, None, ledger, [{"used": True}], nonforcing=True,
        ))


def test_nonforcing_terminal_is_measured_outcome_not_forced_seek(monkeypatch):
    import adapters.mineflayer.b0_two_epoch as two

    probe = s46.case()
    ledger = B0EnergyLedger(
        probe.session_id, forage_policy="sensor_gate",
        config=MetabolismConfig(initial_energy=1),
    )

    async def fake_stage(*args):
        return None

    async def fake_opportunity(*args, **kwargs):
        assert kwargs["nonforcing"] is True
        assert kwargs["epoch"] == 0
        ledger.step("WAIT")
        ledger.step("WAIT")
        return {
            "status": "M0_TERMINAL_NO_PICKUP",
            "pickup_inventory_delta": 0,
            "epoch": 0,
        }

    monkeypatch.setattr(two, "_stage_hunger", fake_stage)
    monkeypatch.setattr(two, "acquire_staged_ground_flesh", fake_opportunity)
    traces = []
    result = asyncio.run(run_two_ground_epochs(
        None, None, ledger, traces, nonforcing=True,
    ))
    assert result["outcome"] == "M0_TERMINAL_NO_PICKUP"
    assert result["m0_terminal"] is True
    assert result["credits"] == result["meals"] == 0
    assert result["epochs_started"] == 1
    assert len(traces) == 1 and traces[0]["stage"] == "OBSERVED_NONFORCING_NO_PICKUP"


def test_v2_arm_identity_and_global_horizon_admission():
    from adapters.mineflayer.b0_two_epoch import (
        V2_ARMS,
        V2_FIRST_ITEM_TICK,
        V2_HORIZON_M0_TICKS,
        V2_MAX_ISSUED_MOVES,
        validate_v2_arm,
    )
    from experiments.metabolism_viability import Interoception

    probe = s46.case()
    assert (V2_HORIZON_M0_TICKS, V2_MAX_ISSUED_MOVES, V2_FIRST_ITEM_TICK) == (16, 8, 11)
    assert tuple(V2_ARMS) == (
        "SENSOR_ON", "SHAM_ON", "SENSOR_MASKED", "CHEAP_NATIVE",
    )
    for arm, (policy, gain, bias) in V2_ARMS.items():
        ledger = B0EnergyLedger(
            probe.session_id, forage_policy=policy,
            sensor=Interoception(gain=gain, bias=bias),
        )
        validate_v2_arm(ledger, arm)
        ledger.step("WAIT")
        with pytest.raises(B0TwoEpochRejected, match="fresh"):
            validate_v2_arm(ledger, arm)
    bad = B0EnergyLedger(probe.session_id, forage_policy="native_only")
    with pytest.raises(B0TwoEpochRejected, match="mismatch"):
        validate_v2_arm(bad, "SENSOR_MASKED")


def test_v2_study_does_not_claim_science_or_allow_m0_horizon_overrun(monkeypatch):
    import adapters.mineflayer.b0_two_epoch as study
    from experiments.metabolism_viability import Interoception

    probe = s46.case()
    ledger = B0EnergyLedger(
        probe.session_id, forage_policy="sensor_gate",
        sensor=Interoception(),
    )
    async def stage(*args):
        for _ in range(11):
            ledger.step("WAIT")

    async def ground(*args, **kwargs):
        assert kwargs["nonforcing"] is True
        assert kwargs["global_m0_horizon"] == 16
        assert kwargs["global_move_limit"] == 8
        assert kwargs["source_time_bracket"] == {}
        kwargs["source_time_bracket"].update({
            "before_fixture_native_world_time": {
                "time_of_day": 10, "day": 0, "is_day": True,
            },
            "after_visible_native_world_time": {
                "time_of_day": 13, "day": 0, "is_day": True,
            },
        })
        assert ledger.body.tick == 11
        for _ in range(5):
            ledger.step("WAIT")
        return {
            "status": "HORIZON_CENSORED_NO_PICKUP",
            "movement_outcomes": [],
        }
    monkeypatch.setattr(study, "_stage_hunger", stage)
    monkeypatch.setattr(study, "acquire_staged_ground_flesh", ground)
    report = {}
    result = asyncio.run(study.run_v2_fixed_study(
        None, None, ledger, "SENSOR_ON", report,
    ))
    assert result["outcome"] == "HORIZON_CENSORED"
    assert result["source_outcome"] == "HORIZON_CENSORED_NO_PICKUP"
    assert result["m0_terminal_free_ticks"] == 16
    assert result["eats"] == result["issued_moves"] == 0
    assert result["final_m0_energy"] == 4
    assert result["v_scientific_admission"] == "NO_GO"
    assert report["predeclared_item_spawn_m0_tick"] == 11
    assert report["source_time_bracket"]["before_fixture_native_world_time"]["time_of_day"] == 10
    assert report["source_time_bracket"]["after_visible_native_world_time"]["time_of_day"] == 13
