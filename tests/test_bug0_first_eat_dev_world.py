"""Bug-0 one physical first-EAT DEV entry: synthetic runner exercises real S49/S51.

No Minecraft/Java/Node in pytest; the dedicated GH action is the one real World.
"""
import asyncio
import json
from types import SimpleNamespace

import pytest

import test_bug0_first_eat_shadow as b0
import test_bug0_s49_s51_eat_handoff as earlier_owner
import adapters.mineflayer.s51_eat_real_ci as s51


def test_physical_dev_requires_distinct_gate_before_java(tmp_path, monkeypatch):
    monkeypatch.setenv("S51_REAL_SERVER_CI", "1")
    monkeypatch.delenv("S51_BUG0_FIRST_EAT_DEV_ONLY", raising=False)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    path = tmp_path / "blocked.json"
    rc = asyncio.run(s51.qualify(
        path, tmp_path / "paper.log", bug0_first_eat_dev=True,
    ))
    report = json.loads(path.read_text())
    assert rc == 2
    assert report["status"] == "BLOCKED"
    assert report["physical_java_started"] is False
    assert report["actual_native_actions"] == []
    assert report["food_commands_issued"] == 0
    assert "explicit DEV one-action gate" in report["error"]


@pytest.mark.parametrize("food,source,shadow", (
    ("rotten_flesh", "inventory", False),
    ("bread", "ground", False),
    ("bread", "inventory", True),
))
def test_non_initial_or_mixed_dev_modes_rejected(tmp_path, food, source, shadow):
    with pytest.raises(ValueError):
        asyncio.run(s51.qualify(
            tmp_path / "invalid.json", tmp_path / "paper.log",
            bug0_first_eat_dev=True, bug0_first_eat_shadow=shadow,
            food_item=food, food_source=source,
        ))
    assert not (tmp_path / "invalid.json").exists()


def test_opt_in_one_action_runner_delegates_original_s49_s51(tmp_path, monkeypatch):
    """Scripted native receipts; proves wiring, NOT physical World evidence."""
    owner, earlier, fresh = b0.pair()
    del owner
    calls = []
    sessions = []
    monkeypatch.setenv("S51_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S51_BUG0_FIRST_EAT_DEV_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)

    class FakeStdin:
        async def drain(self):
            return None

    class FakeServer:
        stdin = FakeStdin()
        pid = 127
        returncode = 0

    class Session(earlier_owner.ScriptedNativeSession):
        def __init__(self):
            super().__init__(fresh, f"bug0-first-eat-{fresh.session_id}")
            self._process.pid = 128
            sessions.append(self)

        async def shutdown(self, *, timeout_s=10):
            calls.append("shutdown")
            return 0

    class SessionType:
        @staticmethod
        async def launch(*args, **kwargs):
            calls.append("launch")
            return Session()

    class Ledger:
        body = SimpleNamespace(tick=0, energy=9)
        config = SimpleNamespace(basal_cost=0.1, food_energy=4)

        def __init__(self, *args, **kwargs):
            pass

        def decide(self, observation):
            assert observation is earlier
            return SimpleNamespace(kind="EAT", eat_choice=SimpleNamespace(item_name="bread"))

    def stage_official(path):
        path.write_bytes(b"never-run-fixture")
        return {"fixture_only": True}

    def config(root):
        (root / "server.properties").write_text("fixture=true\n")

    async def ready(*args, **kwargs):
        return FakeServer(), None, None

    async def noop(*args, **kwargs):
        return None

    async def probe(_session, request_id):
        return earlier if request_id.startswith("s51-hunger-native:") else fresh

    monkeypatch.setattr(s51, "_fetch_official_server", stage_official)
    monkeypatch.setattr(s51, "_write_config", config)
    monkeypatch.setattr(s51, "_ready_server", ready)
    monkeypatch.setattr(s51, "_recording_session_type", lambda *_: SessionType)
    monkeypatch.setattr(s51, "_await_spawn", noop)
    monkeypatch.setattr(s51, "_shutdown_server", noop)
    monkeypatch.setattr(s51, "_correlated_observe", probe)
    monkeypatch.setattr(s51, "_command", lambda *args: None)
    monkeypatch.setattr(s51, "B0EnergyLedger", Ledger)

    report_path = tmp_path / "one-eat.json"
    rc = asyncio.run(s51.qualify(
        report_path, tmp_path / "paper.log",
        bug0_first_eat_dev=True,
    ))
    report = json.loads(report_path.read_text())
    assert rc == 0
    assert report["status"] == "PASS"
    assert report["classification"] == "DEV_ONLY_BUG0_FIRST_EAT_S49_S51_PHYSICAL_OUTCOME"
    assert report["dev_authorization_scope"] == (
        "ONE_DISPOSABLE_WORLD_ONE_FIRST_EAT_LOCAL_OPERATOR_DEV"
    )
    assert report["independent_eat_grant_attested"] is False
    assert report["physical_eat_authorized"] is False  # external qualification
    assert report["actual_native_actions"][0]["same_supervisor"] is True
    assert report["before"]["food"] == 7
    assert report["after"]["food"] == 12
    assert report["after"]["item_count_delta"] == 1
    assert report["food_commands_issued"] == 2
    assert report["m_energy_credited"] is False
    assert report["learning_in_world"] is False
    assert calls.count("shutdown") == 1
    assert sessions[0].commands == [
        ("equip", report["issued_action_id"] + "-equip", "bread"),
        ("consume", report["issued_action_id"] + "-consume"),
        ("observe", report["issued_action_id"] + "-after-eating-00"),
    ]
    assert (tmp_path / "one-eat.native.jsonl").exists()
    assert (tmp_path / "one-eat.commands.jsonl").exists()
