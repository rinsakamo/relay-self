"""M B0 decision-only S49/S14/S16 source joins (synthetic native).

The original B0 owner and S14 coordinator implementations are real code,
but their probes/Action receipts are TEST FIXTURES, not Minecraft evidence.
"""
from __future__ import annotations

from dataclasses import replace

import pytest
import test_m616_s49_s14_planned_owner_join as m_s14_test

from adapters.mineflayer.s49_b0_owner_decision_witness import (
    S49B0DecisionWitness,
)
from adapters.mineflayer.s49_completed_decision_bridge import (
    read_original_s49_completions,
)
from experiments.metabolism_s49_b0_original_decision_only import (
    M616B0DecisionLease,
    bounded_m_b0_original_decision_row,
    observe_m_s49_b0_owner_decisions,
)
from experiments.metabolism_s49_s14_planned_owner_join import (
    bounded_m_s14_planned_row,
    observe_s49_s14_planned,
)


def _owners():
    original, planned, m_admission, m_s16 = m_s14_test._sources()
    third = read_original_s49_completions(
        tuple(item.step for item in original.steps),
        {item.probe.seq: item.probe for item in original.steps},
        {
            item.step.action_request_id: item.action_receipt
            for item in original.steps if item.action_receipt is not None
        },
    )
    assert third is not original and third is not planned.original_l0
    witness = S49B0DecisionWitness(original.session_id)
    for item in original.steps:
        witness.observe(item.probe)
    b0 = witness.complete(third)
    planned_obs = observe_s49_s14_planned(
        enabled=True, original_l0=original, original_planned=planned,
        m_admission_row=m_admission, m_s16_row=m_s16,
    )
    assert planned_obs.status == "RECORDED"
    m_planned = bounded_m_s14_planned_row(planned_obs)
    return dict(
        original_l0=original, original_planned=planned,
        original_b0=b0, m_admission_row=m_admission,
        m_s16_row=m_s16, m_planned_row=m_planned,
    )


def test_real_b0_owner_decisions_match_original_s49_probe_source_without_debit():
    kwargs = _owners()
    result = observe_m_s49_b0_owner_decisions(enabled=True, **kwargs)
    assert result.status == "RECORDED"
    assert result.session_id == kwargs["original_l0"].session_id
    assert result.original_b0 is kwargs["original_b0"]
    assert len(result.resources) == len(kwargs["original_l0"].steps)
    row = bounded_m_b0_original_decision_row(result)
    assert row["status"] == "RECORDED"
    assert row["decision_count"] == len(kwargs["original_l0"].steps)
    assert all(d["b0_kind"] == "WAIT" for d in row["decisions"])
    assert all(d["affordability_wait"] == "UNKNOWN" for d in row["decisions"])
    assert all(d["affordability_move"] == "UNKNOWN" for d in row["decisions"])
    assert all(d["model_cost_wait"] == 0.5 for d in row["decisions"])
    assert all(d["model_cost_move"] == 0.75 for d in row["decisions"])
    assert row["energy_transition_count"] == row["energy_debits"] == 0
    assert row["true_world_energy"] == "UNKNOWN_NO_PHYSICAL_ENERGY_TICK"
    assert row["provider_calls"] is None and row["cpu_ns"] is None
    assert not row["source_attested"] and not row["action_authority"]
    assert "snapshot" not in repr(row) and "true_energy" not in repr(row)


@pytest.mark.parametrize("fault", (
    "missing_b0", "foreign_b0", "same_l0_wrapper", "same_s14_wrapper",
    "copy_step", "copy_probe", "copy_s16", "wrong_s16_readout",
    "wrong_m_planned", "wrong_b0_session", "fake_b0_energy_debit",
    "advanced_b0_tick", "tamper_sensor", "partial_b0",
))
def test_bad_b0_original_decision_is_atomic_deferred(fault):
    kw = _owners()
    b0 = kw["original_b0"]
    if fault == "missing_b0":
        kw["original_b0"] = None
    elif fault == "foreign_b0":
        kw["original_b0"] = replace(b0, session_id="foreign")
    elif fault == "same_l0_wrapper":
        kw["original_b0"] = replace(b0, original_l0=kw["original_l0"])
    elif fault == "same_s14_wrapper":
        kw["original_b0"] = replace(
            b0, original_l0=kw["original_planned"].original_l0,
        )
    elif fault in ("copy_step", "copy_probe", "copy_s16"):
        first = b0.original_l0.steps[0]
        if fault == "copy_step":
            first = replace(first, step=replace(first.step))
        elif fault == "copy_probe":
            first = replace(first, probe=replace(first.probe))
        else:
            first = replace(first, action_receipt=replace(first.action_receipt))
        kw["original_b0"] = replace(
            b0, original_l0=replace(
                b0.original_l0, steps=(first, *b0.original_l0.steps[1:]),
            ),
        )
    elif fault == "wrong_s16_readout":
        kw["m_s16_row"] = dict(kw["m_s16_row"], status="DEFERRED")
    elif fault == "wrong_m_planned":
        kw["m_planned_row"] = dict(kw["m_planned_row"], status="DEFERRED")
    elif fault == "wrong_b0_session":
        b0.owner_ledger.session_id = "foreign"
    elif fault == "fake_b0_energy_debit":
        kw["original_b0"] = replace(b0, energy_debits=1)
    elif fault == "advanced_b0_tick":
        b0.owner_ledger.step("WAIT")
    elif fault == "tamper_sensor":
        first = b0.original_decisions[0]
        kw["original_b0"] = replace(
            b0, original_decisions=(
                replace(first, original_decision=replace(
                    first.original_decision,
                    sensor_reading=first.original_decision.sensor_reading + 5,
                )),
                *b0.original_decisions[1:],
            ),
        )
    elif fault == "partial_b0":
        kw["original_b0"] = replace(
            b0, original_decisions=b0.original_decisions[:-1],
        )
    result = observe_m_s49_b0_owner_decisions(enabled=True, **kw)
    assert result.status == "DEFERRED"
    assert result.original_b0 is None and result.resources == ()
    row = bounded_m_b0_original_decision_row(result)
    assert row["decisions"] == [] and row["energy_debits"] == 0


def test_default_off_no_source_access_and_replay_denied():
    class NoAccess:
        def __getattribute__(self, name):
            raise AssertionError(name)

    x = NoAccess()
    r = observe_m_s49_b0_owner_decisions(
        original_l0=x, original_planned=x, original_b0=x,
        m_admission_row=x, m_s16_row=x, m_planned_row=x,
    )
    assert r.status == "DISABLED"
    kw = _owners()
    lease = M616B0DecisionLease(enabled=True)
    assert lease.admit(**kw).status == "RECORDED"
    assert lease.admit(**kw).status == "DEFERRED"
