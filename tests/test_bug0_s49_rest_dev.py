"""Bug-0 S49 REST intent/physical WAIT ambiguity gates, all offline."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

import test_bug0_s49_food_refusal_priority as samples
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0
from adapters.mineflayer.s49_rest_dev import (
    S49RestDevRejected,
    inspect_rest_native_samples,
)


def _probes():
    return tuple(samples.sample(food=20, seq=200 + i) for i in range(9))


def test_rest_intent_selection_not_an_action_or_p1_recovery():
    p = _probes()[0]
    choice = S49BasicPriorityL0(p.session_id).decide(p, rest_requested=True)
    assert (choice.selected, choice.preferred) == ("REST", "REST")
    assert choice.reason == "REST_INTENT_ONLY_P1_WAIT_UNATTESTED"
    assert not choice.action_issued and not choice.permission_granted
    result = inspect_rest_native_samples(_probes(), session_id=p.session_id)
    assert result["native_stationary_sample_candidate"] is True
    assert result["sample_count"] == 9
    assert result["physical_wait_full_tick_attested"] is False
    assert result["physical_inactivity_between_samples_attested"] is False
    assert result["p1_owner_integrated"] is False
    assert result["p1_fatigue_before"] is None
    assert result["p1_fatigue_after"] is None
    assert result["p1_fatigue_recovery_attested"] is False
    assert result["m_basal_cost_waived"] is False
    assert len(result["samples"]) == 9


@pytest.mark.parametrize("change", (
    "missing", "repeated", "foreign", "duplicate-seq",
    "duplicate-request", "unprobed", "moving", "cumulative-drift",
    "threat", "truncated", "dead", "no-oxygen",
))
def test_rest_native_probes_fail_closed(change):
    original = list(_probes())
    p = original[4]
    if change == "missing":
        original.pop()
    elif change == "repeated":
        original[4] = original[3]
    elif change == "foreign":
        original[4] = replace(p, session_id="foreign-session")
    elif change == "duplicate-seq":
        original[4] = replace(p, seq=original[3].seq)
    elif change == "duplicate-request":
        original[4] = replace(p, request_id=original[3].request_id)
    elif change == "unprobed":
        original[4] = replace(p, kind="entities", request_id=None)
    elif change == "moving":
        pos = p.snapshot.position
        original[4] = replace(p, snapshot=replace(
            p.snapshot, position=replace(pos, x=pos.x + 0.2),
        ))
    elif change == "cumulative-drift":
        for i in range(1, 9):
            q = original[i]
            pos = q.snapshot.position
            original[i] = replace(q, snapshot=replace(
                q.snapshot, position=replace(pos, x=pos.x + 0.01 * i),
            ))
    elif change == "threat":
        original[4] = samples.sample(food=20, seq=p.seq, zombie=True)
    elif change == "truncated":
        original[4] = samples.sample(food=20, seq=p.seq, truncated=True)
    elif change == "dead":
        original[4] = replace(p, snapshot=replace(p.snapshot, health=0.0))
    elif change == "no-oxygen":
        original[4] = replace(p, snapshot=replace(p.snapshot, oxygen_level=0.0))
    with pytest.raises(S49RestDevRejected):
        inspect_rest_native_samples(tuple(original), session_id=original[0].session_id)


def test_rest_priorities_do_not_override_eat_or_threat():
    p = samples.sample(food=13, seq=300)
    l0 = S49BasicPriorityL0(p.session_id)
    eat = l0.decide(p, rest_requested=True)
    danger = l0.decide(samples.sample(
        food=20, seq=301, zombie=True,
    ), rest_requested=True)
    assert eat.selected == "EAT"
    assert (danger.selected, danger.preferred, danger.fallback) == (
        "DEFER", "MOVE_AWAY", "ATTACK",
    )
    assert not eat.action_issued and not danger.action_issued


@pytest.mark.parametrize("case", (
    "missing-gate", "attack-conflict", "health-conflict",
    "food-conflict", "unified-conflict", "observer-conflict", "invalid-switch",
))
def test_rest_mode_blocks_before_java_without_exclusive_gate(
    tmp_path, monkeypatch, case,
):
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_BUG0_REST_DEV_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(
        s49, "_fetch_official_server",
        lambda *_: (_ for _ in ()).throw(AssertionError("Java started")),
    )
    flags = {"bug0_rest_dev": True}
    if case == "missing-gate":
        monkeypatch.delenv("S49_BUG0_REST_DEV_ONLY")
    elif case == "attack-conflict":
        flags["bug0_attack_dev"] = True
    elif case == "health-conflict":
        flags["bug0_attack_health_dev"] = True
    elif case == "food-conflict":
        flags["bug0_food_loop_dev"] = True
    elif case == "unified-conflict":
        flags["bug0_unified_survival_dev"] = True
    elif case == "observer-conflict":
        flags["completed_l0_dev"] = True
    else:
        flags["bug0_rest_dev"] = "true"
    report = tmp_path / "rest-blocked.json"
    result = asyncio.run(s49.qualify(
        report, tmp_path / "paper.log", **flags,
    ))
    value = json.loads(report.read_text())
    assert result == 2 and value["status"] == "BLOCKED"
    assert value["actual_native_actions"] == []
    assert not (tmp_path / "paper.log").exists()
