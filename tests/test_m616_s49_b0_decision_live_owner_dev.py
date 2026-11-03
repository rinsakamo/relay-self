"""M one-world runner contracts: fake qualify only, never starts World."""
from __future__ import annotations

import asyncio
import json

import pytest
from adapters.mineflayer.s49_b0_owner_decision_witness import bounded_original_b0_decision_row
from adapters.mineflayer.s49_original_planned_postaction import (
    bounded_original_s49_planned_row,
)

import test_m616_s49_b0_original_decision_only as b0fixture
import test_metabolism_s49_owner_admission as original_fixture
from tools.m616_s49_b0_decision_live_owner_dev import (
    M616B0DecisionLiveTap,
    run_original_s49_with_m_b0_readback,
)


@pytest.mark.parametrize("failure", (
    "none", "world_error", "missing_b0", "duplicate_b0",
    "bad_b0_report", "bad_source_report",
))
def test_original_owner_exactly_one_run_and_b0_producer_readback(tmp_path, failure):
    raw = b0fixture._owners()
    original = raw["original_l0"]
    planned = raw["original_planned"]
    b0 = raw["original_b0"]
    report = original_fixture._saved_report(original)
    report["original_planned_observer"] = "CALLBACK_RETURNED"
    report["original_planned_readback"] = bounded_original_s49_planned_row(planned)
    report["original_b0_decision_observer"] = "CALLBACK_RETURNED"
    report["original_b0_decision_readback"] = bounded_original_b0_decision_row(b0)
    if failure == "world_error":
        report["status"] = "FAIL"
    if failure == "bad_b0_report":
        report["original_b0_decision_readback"]["decision_count"] += 1
    if failure == "bad_source_report":
        report["original_completion_readback"]["outcome_count"] = 0

    calls = []
    async def fake_qualify(
        path, log, *,
        completed_l0, completed_l0_dev,
        completed_planned, completed_planned_dev,
        completed_b0_decisions, completed_b0_decisions_dev,
    ):
        calls.append("one_original_qualify")
        assert completed_l0_dev and completed_planned_dev and completed_b0_decisions_dev
        completed_l0(original)
        completed_planned(planned)
        if failure != "missing_b0":
            completed_b0_decisions(b0)
        if failure == "duplicate_b0":
            completed_b0_decisions(b0)
        assert not log.exists()
        path.write_text(json.dumps(report), encoding="utf-8")
        return 1 if failure == "world_error" else 0

    code, result = asyncio.run(run_original_s49_with_m_b0_readback(
        original_qualify=fake_qualify,
        report_path=tmp_path / "s49.json",
        server_log=tmp_path / "server.log",
        tap=M616B0DecisionLiveTap(enabled=True),
    ))
    assert calls == ["one_original_qualify"]
    assert code == (1 if failure == "world_error" else 0)
    if failure == "none":
        assert result["status"] == "RECORDED"
        assert result["m_s14_original_join"]["status"] == "RECORDED"
        assert result["m_original_b0_decision_only"]["status"] == "RECORDED"
        assert result["m_original_b0_decision_only"]["energy_debits"] == 0
    else:
        assert result["status"] == "DEFERRED"
    assert result["new_model_calls"] == result["energy_debits"] == 0
    assert result["source_attested"] is False


def test_disabled_b0_live_owner_tap_is_not_callable(tmp_path):
    async def never_qualify(*_args, **_kwargs):
        raise AssertionError("no World or source call")

    with pytest.raises(ValueError):
        asyncio.run(run_original_s49_with_m_b0_readback(
            original_qualify=never_qualify,
            report_path=tmp_path / "report.json",
            server_log=tmp_path / "server.log",
            tap=M616B0DecisionLiveTap(),
        ))
