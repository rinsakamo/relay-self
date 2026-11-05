"""Offline negative/positive same-World S49 + reused #734 Paper callback join."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from pathlib import Path

import pytest

from adapters.mineflayer.worldbody_paper_server import (
    WorldBodyStagingRejected,
    stage_fixed_worldbody,
)
from tools.worldbody_p1_same_world_source_post import (
    P1SameWorldSourceRejected,
    inspect_same_world_source,
)

SESSION = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
WORLD = "11111111-2222-3333-4444-555555555555"
PLAYER = "99999999-aaaa-bbbb-cccc-111111111111"
NONCE = SESSION.replace("-", "")[:20]


def report() -> dict:
    return {
        "session_id": SESSION,
        "worldbody_p1_source_nonce": NONCE,
        "status": "PASS",
        "classification": "DEV_ONLY_WORLDBODY_FIXED_PHYSICS_DIRECT_S16_REST",
        "s49_dev_server": "PINNED_PAPER_1_21_8",
        "worldbody_p1_same_world_source_dev": True,
        "worldbody_p1_source_wait_attested": False,
        "worldbody_p1_source_join_state": "PENDING_POST_WORLD_ORIGINAL_SOURCE_JOIN",
        "worldbody_true_fatigue_received_by_self": False,
        "worldbody_physics_write_from_self": False,
        "worldbody_postmove_l0_choice": {"selected": "REST"},
        "worldbody_rest_action_count": 0,
        "actual_native_actions": [
            {"action": "move-20", "event_seq": 20, "source": SESSION,
             "terminal": "outcome", "movement_m": 0.33236130177},
            {"action": "move-48", "event_seq": 48, "source": SESSION,
             "terminal": "outcome", "movement_m": 0.10048599297},
        ],
    }


def same_world_log() -> str:
    out = [
        f"WORLDBODY_ATTACH world={WORLD} player={PLAYER} tick=90 "
        "initial_walk_speed=0.2",
        f"S49P1_START nonce={NONCE} world={WORLD} tick=100 "
        f"player={PLAYER} coverage=SERVER_TICK_CALLBACK_NOT_FULL_TICK",
    ]
    for tick, phase, token in (
        (103, "begin", "s49-native-move-20"),
        (108, "closed", "s49-native-move-20"),
        (112, "begin", "s49-native-move-48"),
        (117, "closed", "s49-native-move-48"),
    ):
        out.append(
            f"S49P1_ACTION nonce={NONCE} world={WORLD} tick={tick} "
            f"index={tick-100} phase={phase} action={token}"
        )
    out.append(
        f"S49P1_CHOICE nonce={NONCE} world={WORLD} tick=125 "
        "index=25 selected=REST"
    )
    for tick in range(101, 146):
        move = int(tick in (105, 114))
        dist = 0.23 if tick == 105 else 0.11 if tick == 114 else 0.0
        out.append(
            f"S49P1_TICK nonce={NONCE} world={WORLD} tick={tick} "
            f"index={tick-100} x=2.5 y=-60.0 z=0.5 "
            f"move_events={move} move_distance={dist} "
            "fight_events=0 swing_events=0 interact_events=0 "
            "velocity_events=0 teleport_events=0 player_damage_events=0 "
            "sprint=false sneak=false swimming=false"
        )
    out.append(
        f"S49P1_STOP nonce={NONCE} world={WORLD} tick=146 "
        "index=45 faults=0 coverage=SERVER_TICK_CALLBACK_NOT_FULL_TICK"
    )
    return "\n".join(out)


def test_original_action_and_paper_census_join_only_as_dev_candidates():
    result = inspect_same_world_source(report(), same_world_log())
    assert result["same_world_native_paper_callback_join"] is True
    assert result["native_action_count"] == 2
    assert result["paper_callback_tick_count"] == 45
    assert result["paper_world_uuid"] == WORLD
    assert result["paper_original_action_windows"][0]["paper_movement_callback_ticks"] == [105]
    assert result["paper_original_action_windows"][1]["paper_movement_callback_ticks"] == [114]
    assert result["paper_quiet_after_choice_candidate_ticks"] == list(range(127, 135))
    assert result["p1_source_bound_tick_admitted_count"] == 0
    assert result["p1_physical_fatigue_recovery_credited"] == 0
    assert result["source_full_tick_wait_independently_attested"] is False
    assert result["p1_physics_wired_into_world"] is False
    assert result["qualification_go"] is False


@pytest.mark.parametrize("variant", (
    "foreign-paper-world", "wrong-player", "cross-session",
    "replayed-start", "missing-tick", "duplicate-marker", "wrong-action",
    "marker-after-rest", "lost-original-terminal", "wrong-paper-id",
    "source-fault", "unclosed-action", "no-physical-move",
    "future-rest-motion", "missing-native-rest", "forged-wait",
    "zero-session", "missing-tail",
))
def test_same_world_join_rejects_mismatched_or_forged_source(variant):
    source = same_world_log()
    original = deepcopy(report())
    if variant == "foreign-paper-world":
        source = source.replace(
            f"S49P1_START nonce={NONCE} world={WORLD}",
            f"S49P1_START nonce={NONCE} world=other-world",
        )
    elif variant == "wrong-player":
        source = source.replace(
            f"WORLDBODY_ATTACH world={WORLD} player={PLAYER}",
            f"WORLDBODY_ATTACH world={WORLD} player={WORLD}",
        )
    elif variant == "cross-session":
        original["session_id"] = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeef"
    elif variant == "replayed-start":
        source += "\n" + source.splitlines()[1]
    elif variant == "missing-tick":
        source = "\n".join(
            line for line in source.splitlines()
            if "S49P1_TICK " not in line or "tick=110 " not in line
        )
    elif variant == "duplicate-marker":
        source += "\n" + next(
            line for line in source.splitlines()
            if "S49P1_ACTION " in line
        )
    elif variant == "wrong-action":
        source = source.replace(
            "action=s49-native-move-48", "action=s49-native-move-99",
        )
    elif variant == "marker-after-rest":
        source = source.replace(
            "tick=117 index=17 phase=closed", "tick=140 index=40 phase=closed",
        )
    elif variant == "lost-original-terminal":
        original["actual_native_actions"][0]["terminal"] = "unknown"
    elif variant == "wrong-paper-id":
        source = source.replace(
            f"S49P1_CHOICE nonce={NONCE} world={WORLD}",
            f"S49P1_CHOICE nonce={NONCE} world=other-world",
        )
    elif variant == "source-fault":
        source += "\nS49P1_SOURCE_FAULT reason=GAPPED_OR_OVERFLOW"
    elif variant == "unclosed-action":
        source = source.replace(
            "phase=closed action=s49-native-move-20",
            "phase=begin action=s49-native-move-20",
        )
    elif variant == "no-physical-move":
        source = source.replace(
            "tick=114 index=14 x=2.5 y=-60.0 z=0.5 "
            "move_events=1 move_distance=0.11",
            "tick=114 index=14 x=2.5 y=-60.0 z=0.5 "
            "move_events=0 move_distance=0.0",
        )
    elif variant == "future-rest-motion":
        source = source.replace(
            "tick=129 index=29 x=2.5 y=-60.0 z=0.5 "
            "move_events=0 move_distance=0.0",
            "tick=129 index=29 x=2.5 y=-60.0 z=0.5 "
            "move_events=1 move_distance=0.02",
        )
    elif variant == "missing-native-rest":
        original["worldbody_postmove_l0_choice"]["selected"] = "WAIT"
    elif variant == "forged-wait":
        original["worldbody_p1_source_wait_attested"] = True
    elif variant == "zero-session":
        original["worldbody_p1_source_nonce"] = ""
    elif variant == "missing-tail":
        source = "\n".join(line for line in source.splitlines()
                           if "S49P1_STOP " not in line)
    with pytest.raises(P1SameWorldSourceRejected):
        inspect_same_world_source(original, source)


def test_pre_world_source_bridge_needs_explicit_separate_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_WORLDBODY_DEV_ONLY", "1")
    monkeypatch.delenv("S49_WB_P1_SOURCE_DEV_ONLY", raising=False)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    with pytest.raises(WorldBodyStagingRejected):
        stage_fixed_worldbody(tmp_path, source_bridge_dev=True)
    assert list(tmp_path.iterdir()) == []


def test_s49_p1_bridge_refuses_missing_gate_before_server(tmp_path, monkeypatch):
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_WORLDBODY_DEV_ONLY", "1")
    monkeypatch.delenv("S49_WB_P1_SOURCE_DEV_ONLY", raising=False)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    out = tmp_path / "report.json"
    result = asyncio.run(s49.qualify(
        out, tmp_path / "paper.log",
        worldbody_dev=True, worldbody_p1_source_dev=True,
    ))
    assert result == 2
    assert __import__("json").loads(out.read_text())["actual_native_actions"] == []
    assert not (tmp_path / "paper.log").exists()


def test_reused_read_only_collector_has_no_new_world_action_or_fatigue_write():
    plugin = Path(
        "adapters/mineflayer/s49_p1_paper_dev/src/main/java/"
        "io/github/rinsakamo/relays49p1/S49P1SourcePlugin.java"
    ).read_text(encoding="utf-8")
    runner = Path(
        "adapters/mineflayer/s49_normal_session_real_ci.py"
    ).read_text(encoding="utf-8")
    assert 'cmd.equals("s49p1action")' in plugin
    assert "source_bridge_dev=worldbody_p1_source_dev" in runner
    assert "p1_source_bound_tick_admitted_count" not in runner
    assert "P1FatigueLaw.advance(" not in plugin
    assert "p.setWalkSpeed(" not in plugin
