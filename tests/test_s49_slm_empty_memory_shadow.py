"""L8 empty-memory shadow can be enabled without inventing prior World goals.

Synthetic original S49 owner source; this is NOT a physical World,
learned policy, qualified episode or S49 Action execution test.
"""
from __future__ import annotations

import asyncio

import pytest

from adapters.mineflayer import slm_passive_dev_run
from adapters.mineflayer.slm_passive_dev import S49SLMDevOwner
from relay_self.contextual_shadow import ContextualStatus

from test_s49_slm_passive_dev import decide, setup


def test_l8_retention_on_without_admitted_goals_abstains_and_keeps_s49():
    owner, host, supervisor, native, event = setup()
    owner.retention_enabled = True  # Same existing S49 host and owner, opt-in only.
    step = decide(owner, host, native, event)
    assert len(owner.pending) == 1
    assert owner.pending[0][3].cognition_result is step.choice
    assert step.choice.selection.value == "MOVE_AWAY"
    assert host.action_requests == 1
    assert supervisor.open_actions == ()

    result = owner.finish([])
    assert result["observer_errors"] == 0
    assert result["l8_retention_enabled"] is True
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["status"] == "RECORDED"
    assert row["s_choice"] == "MOVE_AWAY"
    assert row["l1_status"] == "no_admissible_l1_proposal"
    assert row["l1_candidate"] is None
    assert row["l1_model_status"] == "NO_ADMISSIBLE_L1_CANDIDATE"
    assert row["action_issues"] == 0
    assert row["learning_updates"] == row["habit_grants"] == 0
    assert row["food_credits"] == 0
    assert row["native_source_attested"] is False
    assert owner.ledger.credit_count == 0


def test_l8_empty_memory_enabled_and_disabled_keep_original_choice_equal():
    def run(enabled):
        owner, host, _, native, event = setup()
        owner.retention_enabled = enabled
        step = decide(owner, host, native, event)
        result = owner.finish([])
        return step.choice.selection.value, result

    off_choice, off = run(False)
    on_choice, on = run(True)
    assert off_choice == on_choice == "MOVE_AWAY"
    assert off["rows"][0]["l1_status"] == "retention_off"
    assert on["rows"][0]["l1_status"] == "no_admissible_l1_proposal"
    assert all(row["action_authority"] is False for row in (
        off["rows"][0], on["rows"][0],
    ))


def test_constructor_only_accepts_boolean_opt_in():
    assert S49SLMDevOwner().retention_enabled is False
    assert S49SLMDevOwner(retention_enabled=True).retention_enabled is True
    for value in ("yes", 1, None, [], object()):
        with pytest.raises(ValueError):
            S49SLMDevOwner(retention_enabled=value)


def test_runner_flag_is_exclusive_opt_in_without_world(monkeypatch, tmp_path):
    import sys

    calls = []

    async def no_world(report, server_log, *, raw_capture_root, slm_dev_owner):
        assert raw_capture_root.is_dir()
        calls.append(slm_dev_owner.retention_enabled)
        return 0

    monkeypatch.setattr(slm_passive_dev_run, "qualify", no_world)
    for index, flag in enumerate((False, True)):
        args = [
            "slm-dev", "--output-dir", str(tmp_path / f"fresh-{index}"),
            "--confirm", "S49-SLM-ONE-DISPOSABLE-DEV-WORLD",
        ]
        if flag:
            args.append("--l8-empty-memory-shadow")
        monkeypatch.setattr(sys, "argv", args)
        assert slm_passive_dev_run.main() == 0
    assert calls == [False, True]
