"""S49 REST source checks. No real World/Action is started here."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

import test_bug0_s49_attack_owner as original
import test_bug0_s49_food_refusal_priority as fixtures
from adapters.mineflayer import s49_rest_dev
from adapters.mineflayer import s49_normal_session_real_ci as s49
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0
from adapters.mineflayer.s49_rest_dev import (
    S49RestRejected,
    bounded_rest_interval,
    safe_rest_decision,
)
from adapters.mineflayer.s49_rest_paper_time import (
    RestTimeRejected,
    ServerGameTime,
    parse_game_time,
    read_game_time,
)


NONCE = "abcde123456789abcd00"


def paper(phase: str, value: str = "The time is 1234") -> str:
    return (
        f"[12:00 INFO]: [Server] RSELF_REST_{NONCE}_{phase}_START\n"
        f"[12:00 INFO]: {value}\n"
        f"[12:00 INFO]: [Server] RSELF_REST_{NONCE}_{phase}_END\n"
    )


def test_paper_native_gametime_exact_markers():
    r = parse_game_time(paper("before"), phase="before", nonce=NONCE)
    assert r is not None
    assert r.tick == 1234 and r.log_line_number == 2
    assert r.source == "ORIGINAL_PAPER_SERVER_CONSOLE"
    assert r.independent_world_tick_attestation is False
    assert bounded_rest_interval(1234, 1242) == 8


@pytest.mark.parametrize("text", (
    lambda: paper("before").replace("The time is 1234", "Time not found"),
    lambda: paper("before").replace("The time is 1234", "The time is 12\nThe time is 13"),
    lambda: paper("before").replace("The time is 1234", "The time is -5"),
    lambda: paper("before") + paper("before"),
    lambda: paper("before").replace("_before_START", "_before_END"),
))
def test_paper_gametime_ambiguous_or_invalid_rejected(text):
    with pytest.raises(RestTimeRejected):
        parse_game_time(text(), phase="before", nonce=NONCE)


@pytest.mark.parametrize("before,after", (
    (0, 0), (5, 12), (100, 201), (100, 99), (-1, 30), (100.0, 109),
))
def test_incomplete_or_excessive_rest_time_is_never_admitted(before, after):
    with pytest.raises(S49RestRejected):
        bounded_rest_interval(before, after)


def test_paper_game_time_read_only_console(tmp_path, monkeypatch):
    log = tmp_path / "paper.log"
    log.write_text("ready\n")
    commands = []

    class FakeStdin:
        async def drain(self):
            pass

    def fake_command(_server, command):
        commands.append(command)
        if command.startswith("say "):
            log.write_text(log.read_text() + f"[Server] {command[4:]}\n")
        elif command == "time query gametime":
            log.write_text(log.read_text() + "The time is 500\n")

    from adapters.mineflayer import s49_rest_paper_time
    monkeypatch.setattr(s49_rest_paper_time, "_command", fake_command)
    result = asyncio.run(read_game_time(
        SimpleNamespace(stdin=FakeStdin(), returncode=None),
        log, phase="before", nonce=NONCE,
    ))
    assert result.tick == 500
    assert commands == [
        f"say RSELF_REST_{NONCE}_before_START",
        "time query gametime",
        f"say RSELF_REST_{NONCE}_before_END",
    ]


@pytest.mark.parametrize("kind", ("zombie", "hungry", "stale-owner", "truncated"))
def test_rest_candidate_rejects_danger_or_other_authority(kind):
    sample = fixtures.sample(food=20, seq=100)
    owner = original._owner(sample)
    policy = S49BasicPriorityL0(sample.session_id)
    if kind == "zombie":
        sample = fixtures.sample(food=20, seq=100, zombie=True)
    elif kind == "hungry":
        sample = fixtures.sample(food=13, seq=100)
    elif kind == "stale-owner":
        owner._count = 1
    elif kind == "truncated":
        # The wire-format permits truncated coverage only when the first
        # 16 native registry facts are actually present.
        with_mob = fixtures.sample(food=20, seq=100, zombie=True)
        mob = with_mob.snapshot.nearby_entities[0]
        sample = replace(with_mob, snapshot=replace(
            with_mob.snapshot,
            nearby_entities_coverage=replace(
                with_mob.snapshot.nearby_entities_coverage,
                candidate_count=17, truncated=True,
            ),
            nearby_entities=tuple(
                replace(mob, entity_id=1000 + i) for i in range(16)
            ),
        ))
    with pytest.raises((S49RestRejected, ValueError)):
        safe_rest_decision(owner, policy, sample)
    assert owner.supervisor.open_actions == ()


def test_original_s49_rest_hold_with_time_and_native_endpoints_no_actions(monkeypatch, tmp_path):
    initial = fixtures.sample(food=20, seq=110)
    before = fixtures.sample(food=20, seq=111)
    after = fixtures.sample(food=20, seq=112)
    owner = original._owner(initial)
    source = iter((initial, before, after))
    reported_time = []
    cmds = []
    log = tmp_path / "paper.log"
    log.write_text("original native Paper\n")

    class FakeStdin:
        async def drain(self):
            pass

    class FakeSession:
        started = SimpleNamespace(session_id=initial.session_id)
        process_returncode = None

    async def observe(_session, _id):
        return next(source)

    async def sample(_server, _log, *, phase, nonce):
        assert _log == log
        reported_time.append(phase)
        return ServerGameTime(
            phase=phase, tick=1000 if phase=="before" else 1012,
            source="ORIGINAL_PAPER_SERVER_CONSOLE",
            native_line="The time is x", log_line_number=2,
            start_marker=phase, end_marker=phase,
        )

    async def no_delay(_):
        pass

    monkeypatch.setattr(s49_rest_dev, "MineflayerProcessSession", FakeSession)
    monkeypatch.setattr(s49_rest_dev, "_correlated_observe", observe)
    monkeypatch.setattr(s49_rest_dev, "read_game_time", sample)
    monkeypatch.setattr(s49_rest_dev, "_command", lambda _, c: cmds.append(c))
    monkeypatch.setattr(s49_rest_dev.asyncio, "sleep", no_delay)
    report = {}
    asyncio.run(s49_rest_dev.run_s49_rest_dev(
        FakeSession(), SimpleNamespace(stdin=FakeStdin()), owner,
        report, server_log=log,
    ))
    assert report["rest_paper_elapsed_ticks"] == 12
    assert report["rest_endpoint_stationary_observed"] is True
    assert report["rest_endpoint_position_delta_m"] == 0
    assert report["rest_action_issued"] is False
    assert report["actual_native_actions"] == []
    assert report["rest_p1_model_integrated"] is False
    assert report["rest_p1_fatigue_before"] is None
    assert report["rest_p1_fatigue_after"] is None
    assert report["rest_p1_fatigue_recovered"] == 0
    assert report["rest_full_tick_inactivity_attested"] is False
    assert report["rest_energy_debit"] == 0
    assert owner._count == 0 and not owner._dispatched
    assert owner.supervisor.open_actions == ()
    assert reported_time == ["before", "after"]
    assert "kill @e[type=!minecraft:player]" in cmds
    assert not any("attack" in c or "move" in c for c in cmds)


@pytest.mark.parametrize("variant", (
    "missing-gate", "attack-conflict", "food-conflict",
    "wrong-type", "unified-conflict",
))
def test_rest_real_world_optin_refused_before_server(variant, tmp_path, monkeypatch):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_BUG0_REST_DEV_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(
        s49, "_fetch_official_server",
        lambda *_: (_ for _ in ()).throw(AssertionError("Java started")),
    )
    opts = {"bug0_rest_dev": True}
    if variant == "missing-gate":
        monkeypatch.delenv("S49_BUG0_REST_DEV_ONLY")
    elif variant == "attack-conflict":
        opts["bug0_attack_health_dev"] = True
    elif variant == "food-conflict":
        opts["bug0_food_loop_dev"] = True
    elif variant == "unified-conflict":
        opts["bug0_unified_survival_dev"] = True
    else:
        opts["bug0_rest_dev"] = "true"
    out = tmp_path / "rest-blocked.json"
    rc = asyncio.run(s49.qualify(
        out, tmp_path / "paper.log", **opts,
    ))
    report = json.loads(out.read_text())
    assert rc == 2 and report["status"] == "BLOCKED"
    assert report["actual_native_actions"] == []
    assert not (tmp_path / "paper.log").exists()
