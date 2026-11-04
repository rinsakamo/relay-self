"""Paper server health evidence sidecar: offline anti-confusion fixtures only."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

import test_bug0_s49_attack_owner as existing
from adapters.mineflayer import (
    attack_execution,
    normal_action,
    s49_attack_dev,
    s49_attack_server_health,
)
from adapters.mineflayer import (
    s49_normal_session_real_ci as s49,
)
from adapters.mineflayer.s49_attack_server_health import (
    ServerHealthReadbackRejected,
    ServerHealthSample,
    parse_health_log,
    sample_tagged_zombie_health,
)
from relay_self.action import ActionState

NONCE = "abcdef01234567890123"


def _response(stage, content="Zombie has the following entity data: 20.0f"):
    return (
        f"[10:01:01 INFO]: [Server] RSELF_HEALTH_{NONCE}_{stage}_START\n"
        f"[10:01:01 INFO]: {content}\n"
        f"[10:01:01 INFO]: [Server] RSELF_HEALTH_{NONCE}_{stage}_END\n"
    )


def test_parse_exact_paper_zombie_health_and_source():
    before = parse_health_log(_response("before"), stage="before", nonce=NONCE)
    after = parse_health_log(
        _response("after", "Zombie has the following entity data: 19.0f"),
        stage="after", nonce=NONCE,
    )
    assert before is not None and after is not None
    assert (before.health, after.health) == (20.0, 19.0)
    assert before.log_line_number == 2
    assert before.source == "ORIGINAL_PAPER_SERVER_CONSOLE"
    assert before.source_independently_attested is False
    assert before.marker_start.endswith("_before_START")


@pytest.mark.parametrize("broken", (
    "duplicate-health", "no-health", "two-starts", "two-ends",
    "reversed", "negative", "impossible", "unknown-format",
))
def test_paper_log_invalid_health_fails_closed(broken):
    valid = _response("before")
    if broken == "duplicate-health":
        valid = valid.replace(
            "[10:01:01 INFO]: [Server] RSELF_HEALTH_"
            + NONCE + "_before_END",
            "Zombie has the following entity data: 18.0f\n"
            + "[10:01:01 INFO]: [Server] RSELF_HEALTH_"
            + NONCE + "_before_END",
        )
    elif broken == "no-health":
        valid = _response("before", "Cannot find Health on target")
    elif broken == "two-starts":
        valid = (
            f"[10:00 INFO]: [Server] RSELF_HEALTH_{NONCE}_before_START\n"
            + valid
        )
    elif broken == "two-ends":
        valid += f"[10:01:02 INFO]: [Server] RSELF_HEALTH_{NONCE}_before_END\n"
    elif broken == "reversed":
        valid = (
            f"[10:00 INFO]: [Server] RSELF_HEALTH_{NONCE}_before_END\n"
            f"[10:01 INFO]: [Server] RSELF_HEALTH_{NONCE}_before_START\n"
        )
    elif broken == "negative":
        valid = _response("before", "Zombie has the following entity data: -1.0f")
    elif broken == "impossible":
        valid = _response("before", "Zombie has the following entity data: 40.0f")
    else:
        valid = _response("before", "Zombie has the following entity data: null")
    with pytest.raises(ServerHealthReadbackRejected):
        parse_health_log(valid, stage="before", nonce=NONCE)


def test_pending_log_is_not_falsely_zero_health():
    assert parse_health_log("", stage="before", nonce=NONCE) is None
    pending = f"[10:01 INFO]: [Server] RSELF_HEALTH_{NONCE}_before_START\n"
    assert parse_health_log(pending, stage="before", nonce=NONCE) is None
    with pytest.raises(ServerHealthReadbackRejected):
        parse_health_log(
            _response("before"), stage="before", nonce="invalid!*",
        )


def test_exact_paper_command_origin_without_action(tmp_path, monkeypatch):
    paper = tmp_path / "paper.log"
    paper.write_text("server ready\n")
    commands = []

    class FakeStdin:
        async def drain(self):
            pass

    def collect(_server, command):
        commands.append(command)
        if command.startswith("say "):
            paper.write_text(
                paper.read_text() + f"[Server] {command[4:]}\n"
            )
        elif command.startswith("data get entity "):
            paper.write_text(
                paper.read_text()
                + "Zombie has the following entity data: 20.0f\n"
            )

    monkeypatch.setattr(s49_attack_server_health, "_command", collect)
    fake_server = SimpleNamespace(stdin=FakeStdin(), returncode=None)
    result = asyncio.run(sample_tagged_zombie_health(
        fake_server, paper, stage="before", nonce=NONCE,
    ))
    assert result.health == 20.0
    assert len(commands) == 3
    assert commands[0] == f"say RSELF_HEALTH_{NONCE}_before_START"
    assert commands[1] == (
        "data get entity @e[type=minecraft:zombie,"
        "tag=RelaySelfAttackTarget,limit=1] Health"
    )
    assert commands[2] == f"say RSELF_HEALTH_{NONCE}_before_END"


def test_original_s49_runner_with_paper_before_after_never_mints_owner(
    monkeypatch, tmp_path,
):
    first, second = existing._pair()
    owner = existing._owner(first)
    eid = second.snapshot.nearby_entities[0].entity_id
    session = existing.FakeNativeSession(second)
    paper = tmp_path / "paper.log"
    paper.write_text("Paper TEST only\n")
    paper_samples = []
    calls = []

    class FakeStdin:
        async def drain(self):
            pass

    async def read(_session, _req):
        return next(calls_iter)

    calls_iter = iter((first, second))

    async def no_sleep(_):
        pass

    async def sampled(_server, _path, *, stage, nonce):
        assert _path == paper
        paper_samples.append(stage)
        assert nonce == first.session_id.replace("-", "")[:20]
        return ServerHealthSample(
            stage=stage, target_tag="RelaySelfAttackTarget",
            source="ORIGINAL_PAPER_SERVER_CONSOLE",
            health=20.0 if stage == "before" else 19.0,
            marker_start="before" if stage == "before" else "after",
            marker_end="end", native_line="fake paper health",
            log_line_number=2 if stage == "before" else 5,
        )

    monkeypatch.setattr(s49_attack_dev, "MineflayerProcessSession",
                        existing.FakeNativeSession)
    monkeypatch.setattr(normal_action, "MineflayerProcessSession",
                        existing.FakeNativeSession)
    monkeypatch.setattr(attack_execution, "MineflayerProcessSession",
                        existing.FakeNativeSession)
    monkeypatch.setattr(s49_attack_dev, "_correlated_observe", read)
    monkeypatch.setattr(s49_attack_dev, "_command", lambda _, c: calls.append(c))
    monkeypatch.setattr(s49_attack_dev.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(s49_attack_dev, "sample_tagged_zombie_health", sampled)
    report = {}
    result = asyncio.run(s49_attack_dev.run_s49_attack_dev(
        session, SimpleNamespace(stdin=FakeStdin()), owner, report,
        health_log=paper,
    ))
    assert result.terminal.state is ActionState.OUTCOME
    assert owner._count == 1 and not owner.supervisor.open_actions
    assert report["attack_server_health_drop_observed"] is True
    assert report["attack_server_health_delta"] == 1.0
    assert report["attack_evidence"]["damage_attested"] is False
    assert report["attack_evidence"]["outcome_scope"] == (
        "ATTACK_COMMAND_ACK_PLUS_PAPER_HEALTH_READBACK"
    )
    assert paper_samples == ["before", "after"]
    assert sum(cmd.startswith("execute at RelaySelf run summon") for cmd in calls) == 1
    assert "RelaySelfAttackTarget" in next(
        cmd for cmd in calls if "summon minecraft:zombie" in cmd
    )
    assert session.sent[0][0] == "attack"
    assert len([x for x in session.sent if x[0] == "attack"]) == 1
    assert report["attack_target_entity_id"] == eid


@pytest.mark.parametrize("variant", [
    "missing-gate", "attack-conflict", "food-conflict",
    "wrong-type", "unified-conflict",
])
def test_health_mode_fails_before_java_without_exclusive_gate(
    tmp_path, monkeypatch, variant,
):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_BUG0_ATTACK_HEALTH_DEV_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(
        s49, "_fetch_official_server",
        lambda *_: (_ for _ in ()).throw(AssertionError("Java launched")),
    )
    opts = {"bug0_attack_health_dev": True}
    if variant == "missing-gate":
        monkeypatch.delenv("S49_BUG0_ATTACK_HEALTH_DEV_ONLY")
    elif variant == "attack-conflict":
        opts["bug0_attack_dev"] = True
    elif variant == "food-conflict":
        opts["bug0_food_loop_dev"] = True
    elif variant == "unified-conflict":
        opts["bug0_unified_survival_dev"] = True
    else:
        opts["bug0_attack_health_dev"] = "true"
    path = tmp_path / "no_world.json"
    rc = asyncio.run(s49.qualify(path, tmp_path / "paper.log", **opts))
    state = json.loads(path.read_text())
    assert rc == 2 and state["status"] == "BLOCKED"
    assert state["actual_native_actions"] == []
    assert not (tmp_path / "paper.log").exists()
