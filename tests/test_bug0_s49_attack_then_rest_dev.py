"""Bug-0 ATTACK->REST joint original owner gates (offline)."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

import test_bug0_s49_food_refusal_priority as sample_sources
from adapters.mineflayer import s49_attack_then_rest_dev as bridge
from relay_self.action import ActionState


@dataclass
class MockOwner:
    session_id: str
    _count: int = 0
    _dispatched: set[str] = field(default_factory=set)
    supervisor: object = field(default_factory=lambda: SimpleNamespace(open_actions=()))
    _post_move_settling_unqualified: bool = False
    intent: object = field(default_factory=lambda: SimpleNamespace(
        current_intent=SimpleNamespace(intent_id="escape-threat"),
    ))


class MockSession:
    def __init__(self, sid):
        self.started = SimpleNamespace(session_id=sid)
        self.process_returncode = None


class MockStdin:
    def __init__(self):
        self.drains = 0

    async def drain(self):
        self.drains += 1


def _source_probes():
    return tuple(sample_sources.sample(food=20, seq=500 + i) for i in range(9))


def test_one_original_attack_then_rest_observation_no_duplicate_action(monkeypatch, tmp_path):
    probes = iter(_source_probes())
    sid = sample_sources.sample(food=20).session_id
    owner = MockOwner(sid)
    server = SimpleNamespace(stdin=MockStdin())
    session = MockSession(sid)
    commands = []

    async def attack(session, server, owner, report, *, health_log):
        assert health_log == tmp_path / "paper.log"
        assert not owner._dispatched
        owner._count = 1
        owner._dispatched.add("attack-1")
        report["actual_native_actions"] = [{
            "action_id": "attack-1", "kind": "ATTACK", "terminal": "outcome",
        }]
        report["attack_server_health_drop_observed"] = True
        return SimpleNamespace(
            terminal=SimpleNamespace(state=ActionState.OUTCOME, action_id="attack-1"),
            effect=SimpleNamespace(seq=42),
            after_probe=SimpleNamespace(seq=43),
        )

    async def probe(_session, _request_id):
        return next(probes)

    async def nop(_duration):
        return None

    monkeypatch.setattr(bridge, "MineflayerProcessSession", MockSession)
    monkeypatch.setattr(bridge, "NormalSessionActionExecutor", MockOwner)
    monkeypatch.setattr(bridge, "run_s49_attack_dev", attack)
    monkeypatch.setattr(bridge, "_correlated_observe", probe)
    monkeypatch.setattr(bridge, "_command", lambda _server, command: commands.append(command))
    monkeypatch.setattr(bridge.asyncio, "sleep", nop)

    report = {}
    asyncio.run(bridge.run_s49_attack_then_rest_dev(
        session, server, owner, report, health_log=tmp_path / "paper.log",
    ))
    assert owner._count == 1 and owner._dispatched == {"attack-1"}
    assert [x["kind"] for x in report["actual_native_actions"]] == ["ATTACK"]
    assert len(commands) == 1 and "RelaySelfAttackTarget" in commands[0]
    assert report["rest_intent_selected"] is True
    assert report["rest_action_issued"] is False
    assert report["rest_observation"]["sample_count"] == 9
    assert report["rest_observation"]["physical_wait_full_tick_attested"] is False
    assert report["p1_scope"]["physical_p1_wait_ticks_attested"] == 0
    assert report["p1_scope"]["p1_fatigue_recovery_attested"] is False
    assert report["p1_scope"]["p1_fatigue_before"] is None
    assert report["p1_scope"]["p1_fatigue_after"] is None
    assert report["attack_rest_link"]["rest_baseline_probe_seq"] > 43
    assert report["p1_scope"]["m_basal_cost_waived"] is False
    assert report["stage"] == "BUG0_ATTACK_THEN_REST_NATIVE_SAMPLES_CLOSED"


@pytest.mark.parametrize("variant", [
    "missing-gate", "rest-conflict", "attack-conflict", "attack-health-conflict",
    "food-conflict", "unified-conflict", "bad-typed-flag",
])
def test_joint_mode_no_java_without_exclusive_gate(tmp_path, monkeypatch, variant):
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_BUG0_ATTACK_REST_DEV_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(
        s49, "_fetch_official_server",
        lambda *_: (_ for _ in ()).throw(AssertionError("Java started")),
    )
    flags = {"bug0_attack_rest_dev": True}
    if variant == "missing-gate":
        monkeypatch.delenv("S49_BUG0_ATTACK_REST_DEV_ONLY")
    elif variant == "rest-conflict":
        flags["bug0_rest_dev"] = True
    elif variant == "attack-conflict":
        flags["bug0_attack_dev"] = True
    elif variant == "attack-health-conflict":
        flags["bug0_attack_health_dev"] = True
    elif variant == "food-conflict":
        flags["bug0_food_loop_dev"] = True
    elif variant == "unified-conflict":
        flags["bug0_unified_survival_dev"] = True
    else:
        flags["bug0_attack_rest_dev"] = "true"
    path = tmp_path / "blocked.json"
    rc = asyncio.run(s49.qualify(path, tmp_path / "paper.log", **flags))
    data = json.loads(path.read_text())
    assert rc == 2 and data["status"] == "BLOCKED"
    assert data["actual_native_actions"] == []
    assert not (tmp_path / "paper.log").exists()


def test_attacked_body_not_reclassified_wait_if_action_open(monkeypatch, tmp_path):
    sid = sample_sources.sample().session_id
    owner = MockOwner(sid)
    owner.supervisor = SimpleNamespace(open_actions=("attack-1",))
    server = SimpleNamespace(stdin=MockStdin())
    session = MockSession(sid)
    monkeypatch.setattr(bridge, "MineflayerProcessSession", MockSession)
    monkeypatch.setattr(bridge, "NormalSessionActionExecutor", MockOwner)
    with pytest.raises(bridge.S49AttackRestDevRejected, match="fresh original"):
        asyncio.run(bridge.run_s49_attack_then_rest_dev(
            session, server, owner, {}, health_log=tmp_path / "paper.log",
        ))
