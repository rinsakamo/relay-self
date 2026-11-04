"""S49 Paper P1 callback-tick DEV source and original owner anti-confusion."""
from __future__ import annotations

import asyncio
import json

import pytest

from adapters.mineflayer.s49_p1_paper_dev import (
    S49P1SourceRejected,
    inspect_paper_tick_source,
)

SESSION = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
WORLD = "11111111-2222-3333-4444-555555555555"
PLAYER = "99999999-aaaa-bbbb-cccc-111111111111"
TARGET = "88888888-aaaa-bbbb-cccc-222222222222"
NONCE = SESSION.replace("-", "")[:20]


def native():
    return {
        "status": "PASS",
        "session_id": SESSION,
        "rest_intent_selected": True,
        "rest_action_issued": False,
        "attack_server_health_drop_observed": True,
        "actual_native_actions": [{
            "kind": "ATTACK", "action_id": "one-action", "terminal": "outcome",
        }],
    }


def sample_log():
    lines = [
        f"S49P1_START nonce={NONCE} world={WORLD} tick=100 "
        f"player={PLAYER} coverage=SERVER_TICK_CALLBACK_NOT_FULL_TICK",
        f"S49P1_FIGHT nonce={NONCE} world={WORLD} tick=103 "
        f"attacker={PLAYER} target={TARGET} damage=0.94",
        f"S49P1_REST nonce={NONCE} world={WORLD} tick=115 index=15",
    ]
    for index, tick in enumerate(range(101, 131), 1):
        fight = int(tick == 104)
        line = (
            f"S49P1_TICK nonce={NONCE} world={WORLD} tick={tick} index={index} "
            "x=2.5 y=-60.0 z=0.5 move_events=0 move_distance=0.0 "
            f"fight_events={fight} swing_events={fight} interact_events=0 "
            "velocity_events=0 teleport_events=0 player_damage_events=0 "
            "sprint=false sneak=false swimming=false"
        )
        lines.append(line)
    lines.append(
        f"S49P1_STOP nonce={NONCE} world={WORLD} tick=131 "
        "index=30 faults=0 coverage=SERVER_TICK_CALLBACK_NOT_FULL_TICK"
    )
    return "\n".join(lines)


def test_one_source_paper_fight_then_rest_contiguous_tick_callbacks():
    result = inspect_paper_tick_source(
        sample_log(), nonce=NONCE, native_report=native(),
    )
    assert result["native_session_id"] == SESSION
    assert result["world_tick_start"] == 100
    assert result["paper_fight_event_tick"] == 103
    assert result["paper_fight_callback_tick"] == 104
    assert result["paper_rest_marker_tick"] == 115
    assert result["total_consecutive_source_callback_rows"] == 30
    assert result["rest_candidate_quiet_source_ticks"] == list(range(117, 125))
    assert result["source_full_tick_activity_independently_attested"] is False
    assert result["p1_fatigue_physically_attested"] is False


@pytest.mark.parametrize("change", (
    "gap", "duplicate-fight", "missing-fight", "wrong-nonce", "wrong-world",
    "wrong-player", "moving-rest", "swing-rest", "rest-before-fight",
    "bad-body", "missing-stop", "replay-start", "source-fault",
    "missing-source", "foreign-native", "no-health-drop",
))
def test_paper_source_fails_closed_on_missing_or_ambiguous_tick(change):
    source = sample_log()
    scope = native()
    if change == "gap":
        source = "\n".join(line for line in source.splitlines()
                           if "S49P1_TICK " not in line or "tick=120 " not in line)
    elif change == "duplicate-fight":
        source += (
            f"\nS49P1_FIGHT nonce={NONCE} world={WORLD} tick=103 "
            f"attacker={PLAYER} target={TARGET} damage=0.94"
        )
    elif change == "missing-fight":
        source = "\n".join(line for line in source.splitlines()
                           if "S49P1_FIGHT " not in line)
    elif change == "wrong-nonce":
        source = source.replace("S49P1_REST nonce=" + NONCE,
                                "S49P1_REST nonce=wrongnonce12345")
    elif change == "wrong-world":
        source = source.replace(f"world={WORLD} tick=120", "world=otherworld tick=120")
    elif change == "wrong-player":
        source = source.replace(f"attacker={PLAYER}", f"attacker={TARGET}")
    elif change == "moving-rest":
        source = source.replace("tick=122 index=22 x=2.5",
                                "tick=122 index=22 x=2.6")
    elif change == "swing-rest":
        source = source.replace("tick=122 index=22 x=2.5", 
                                "tick=122 index=22 x=2.5")
        source = source.replace("tick=122 index=22 x=2.5 y=-60.0 z=0.5 move_events=0 move_distance=0.0 fight_events=0 swing_events=0",
                                "tick=122 index=22 x=2.5 y=-60.0 z=0.5 move_events=0 move_distance=0.0 fight_events=0 swing_events=1")
    elif change == "rest-before-fight":
        source = source.replace("S49P1_REST nonce=" + NONCE
                                + f" world={WORLD} tick=115",
                                "S49P1_REST nonce=" + NONCE
                                + f" world={WORLD} tick=102")
    elif change == "bad-body":
        source = source.replace("tick=125 index=25 x=2.5",
                                "tick=125 index=25 x=NaN")
    elif change == "missing-stop":
        source = "\n".join(line for line in source.splitlines()
                           if "S49P1_STOP " not in line)
    elif change == "replay-start":
        source += "\n" + source.splitlines()[0]
    elif change == "source-fault":
        source += "\nS49P1_SOURCE_FAULT reason=NO_PLAYER_OR_WORLD"
    elif change == "missing-source":
        source = ""
    elif change == "foreign-native":
        scope["actual_native_actions"][0]["terminal"] = "unknown"
    elif change == "no-health-drop":
        scope["attack_server_health_drop_observed"] = False
    with pytest.raises(S49P1SourceRejected):
        inspect_paper_tick_source(source, nonce=NONCE, native_report=scope)


@pytest.mark.parametrize("variant", (
    "missing-gate", "attack-conflict", "rest-conflict", "unified-conflict",
    "invalid-type", "paper-byte-missing",
))
def test_paper_dev_requires_exact_owner_before_java(tmp_path, monkeypatch, variant):
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_BUG0_P1_PAPER_DEV_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(
        s49, "_fetch_official_server",
        lambda *_: (_ for _ in ()).throw(AssertionError("Mojang startup attempted")),
    )
    flags = {"bug0_p1_paper_dev": True}
    if variant == "missing-gate":
        monkeypatch.delenv("S49_BUG0_P1_PAPER_DEV_ONLY")
    elif variant == "attack-conflict":
        flags["bug0_attack_dev"] = True
    elif variant == "rest-conflict":
        flags["bug0_rest_dev"] = True
    elif variant == "unified-conflict":
        flags["bug0_unified_survival_dev"] = True
    elif variant == "invalid-type":
        flags["bug0_p1_paper_dev"] = "true"
    else:
        monkeypatch.delenv("S49_P1_PAPER_JAR", raising=False)
    out = tmp_path / "report.json"
    code = asyncio.run(s49.qualify(
        out, tmp_path / "paper.log", **flags,
    ))
    report = json.loads(out.read_text())
    assert code == 2 and report["status"] == "BLOCKED"
    assert report["actual_native_actions"] == []
    assert not (tmp_path / "paper.log").exists()
