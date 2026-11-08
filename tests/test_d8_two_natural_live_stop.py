"""Two genuinely distinct Paper death/spawn/pickup generations in one live STOP."""
from __future__ import annotations

import asyncio
import json

import pytest

from adapters.mineflayer.d7_live_staged_stop import (
    D7LiveStopRejected,
    read_d7_live_staged_stop,
)

WORLD = "12d3f3ee-5555-4444-bbbb-aabbccddeeff"
PLAYER = "dfa44b66-aaaa-4444-bbbb-112233445566"
ZOMBIES = (
    "aa11bb22-3333-4444-8888-112233445566",
    "aa11bb22-3333-4444-8888-112233445577",
)
ITEMS = (
    "5a79c6f0-abcd-4567-aaaa-111144445555",
    "5a79c6f0-abcd-4567-aaaa-111144445566",
)
SID = "d8-original-s49-native-session"
AID = f"d8-gen2-s49-item-back-1-{SID}"
OFF = {key: False for key in (
    "forward", "back", "left", "right", "jump", "sprint", "sneak",
)}


def pair(zombie: str, item: str, *, tick: int, count: int):
    death = (
        f"RSELF_NATURAL_DROP_DEATH world={WORLD} zombie={zombie}"
        f" tick={tick} rotten_count={count} killer={PLAYER}"
        " source=ACTUAL_PAPER_ENTITY_DEATH_DROPS killer_is_relay_self=true"
    )
    spawn = (
        f"RSELF_NATURAL_DROP_SPAWN world={WORLD} zombie={zombie}"
        f" item={item} tick={tick} rotten_count={count}"
        " source=ACTUAL_PAPER_ITEM_SPAWN_NEAR_DEATH"
    )
    pickup = (
        f"RSELF_NATURAL_DROP_PICKUP world={WORLD} zombie={zombie}"
        f" item={item} player={PLAYER} tick={tick+25}"
        f" rotten_count={count} source=ACTUAL_PAPER_ITEM_PICKUP"
    )
    return death, spawn, pickup


def sample():
    first = pair(ZOMBIES[0], ITEMS[0], tick=32, count=2)
    second = pair(ZOMBIES[1], ITEMS[1], tick=140, count=1)
    lines = [
        "RSELF_D7_PAPER_READY source=PAPER_SERVER_MAIN_THREAD_V1"
        " interval_ticks=1 max_rows=8192 mode=read_only eat_authority=none",
        *first, *second,
    ]
    for i in range(1, 206):
        bits = " ".join(key+"=false" for key in OFF)
        lines.append(
            "RSELF_D7_PAPER_TICK source=PAPER_SERVER_MAIN_THREAD_V1"
            f" ordinal={i} tick={i} world={WORLD} player={PLAYER}"
            " x=8.5 y=-60 z=10 vx=0 vy=0 vz=0 ground=true"
            f" {bits}"
        )
    client = [
        {"kind": "SESSION_START", "client_physics_tick": 0, "native_seq": 0},
        {"kind": "EFFECT_ACK", "client_physics_tick": 2, "native_seq": 132,
         "native_action_id": "d7f-previous-gen-move-s15-clear",
         "controls": dict(OFF)},
        {"kind": "EFFECT_ACK", "client_physics_tick": 31, "native_seq": 232,
         "native_action_id": AID+"-s15-clear", "controls": dict(OFF)},
    ]
    client.extend(
        {"kind": "PHYSICS_TICK", "client_physics_tick": i+32,
         "controls": dict(OFF)}
        for i in range(22)
    )
    return lines, client, first, second


def qualify(lines, client, second):
    return read_d7_live_staged_stop(
        "\n".join(lines),
        "\n".join(json.dumps({
            "source": "S50_DEV_NATIVE_READBACK_V1",
            "ordinal": i, "session_id": SID, **row,
        }) for i, row in enumerate(client, 1)),
        session_id=SID, action_id=AID, clear_seq=232,
        original_stage_line=second[1], original_pickup_line=second[2],
        original_death_line=second[0], source_kind="natural_multi",
    )


def test_two_distinct_paper_generations_last_original_clear_only():
    lines, client, first, second = sample()
    result = qualify(lines, client, second)
    assert result.classification == "D8_DEV_LIVE_SECOND_NATURAL_BODY_STEADY_SOURCE"
    assert result.paper_item_uuid == ITEMS[1]
    assert result.paper_pickup_tick == 165
    assert result.original_clear_seq == 232
    assert result.client_postclear_physics_ticks == 22
    assert result.server_effective_original_clear_tick == "NOT_CAUSALLY_ATTESTED"


@pytest.mark.parametrize("case", [
    "same_zombie", "same_item", "first_wrong_killer", "first_foreign_world",
    "missing_first_pickup", "duplicate_first_spawn", "wrong_second_count",
    "first_after_second", "reused_first_source", "wrong_last_clear",
    "last_paper_motor_active", "extra_third_death",
])
def test_second_gen_never_qualifies_with_replayed_or_foreign_source(case):
    lines, client, first, second = sample()
    if case == "same_zombie":
        lines[4] = lines[4].replace(ZOMBIES[1], ZOMBIES[0])
        second = (lines[4], second[1], second[2])
    elif case == "same_item":
        lines[5] = lines[5].replace(ITEMS[1], ITEMS[0])
        second = (second[0], lines[5], second[2])
    elif case == "first_wrong_killer":
        lines[1] = lines[1].replace(PLAYER, ZOMBIES[0])
    elif case == "first_foreign_world":
        lines[1] = lines[1].replace(WORLD, ZOMBIES[0])
    elif case == "missing_first_pickup":
        lines.pop(3)
    elif case == "duplicate_first_spawn":
        lines.insert(2, first[1])
    elif case == "wrong_second_count":
        lines[6] = lines[6].replace("rotten_count=1", "rotten_count=2")
        second = (second[0], second[1], lines[6])
    elif case == "first_after_second":
        lines[3] = lines[3].replace("tick=57", "tick=170")
    elif case == "reused_first_source":
        second = first
    elif case == "wrong_last_clear":
        client[2]["native_action_id"] = AID+"-clear"
    elif case == "last_paper_motor_active":
        lines[-1] = lines[-1].replace("back=false", "back=true")
    elif case == "extra_third_death":
        lines.insert(7, second[0])
    with pytest.raises(D7LiveStopRejected):
        qualify(lines, client, second)


def qualify_passive(lines, client, second):
    """No S15 clear exists for gen2; use genuine current S49 ATTACK ACK."""
    attack_id = f"d8-gen2-s49-attack-1-{SID}"
    client[2]["native_action_id"] = attack_id
    return read_d7_live_staged_stop(
        "\n".join(lines),
        "\n".join(json.dumps({
            "source": "S50_DEV_NATIVE_READBACK_V1",
            "ordinal": i, "session_id": SID, **row,
        }) for i, row in enumerate(client, 1)),
        session_id=SID, action_id=attack_id, clear_seq=232,
        original_stage_line=second[1], original_pickup_line=second[2],
        original_death_line=second[0], source_kind="natural_multi_passive",
    )


def test_gen2_genuine_paper_passive_no_move_qualifies_only_after_attack():
    lines, client, _, second = sample()
    source = qualify_passive(lines, client, second)
    assert source.classification == (
        "D8_DEV_LIVE_SECOND_NATURAL_PASSIVE_PICKUP_STEADY_SOURCE"
    )
    assert source.original_clear_seq == -1
    assert source.original_attack_effect_seq == 232
    assert source.server_effective_original_clear_tick == "NOT_APPLICABLE_NO_MOVE"
    assert source.paper_item_uuid == ITEMS[1]
    assert source.client_postclear_physics_ticks == 22


@pytest.mark.parametrize("case", [
    "missing_attack_ack", "foreign_attack_ack", "active_client",
    "reused_zombie", "reused_item", "missing_pickup", "wrong_killer",
])
def test_passive_no_move_cannot_reuse_stale_or_fake_source(case):
    lines, client, _, second = sample()
    if case == "missing_attack_ack":
        client.pop(2)
    elif case == "foreign_attack_ack":
        client[2]["native_seq"] = 999
    elif case == "active_client":
        client[-1]["controls"]["back"] = True
    elif case == "reused_zombie":
        lines[4] = lines[4].replace(ZOMBIES[1], ZOMBIES[0])
        second = (lines[4], second[1], second[2])
    elif case == "reused_item":
        lines[5] = lines[5].replace(ITEMS[1], ITEMS[0])
        second = (second[0], lines[5], second[2])
    elif case == "missing_pickup":
        lines.pop(6)
    elif case == "wrong_killer":
        lines[4] = lines[4].replace(PLAYER, ZOMBIES[1])
        second = (lines[4], second[1], second[2])
    with pytest.raises(D7LiveStopRejected):
        qualify_passive(lines, client, second)


def test_two_generations_probe_prefixes_are_disjoint():
    """The D6 and D8 observation/action namespaces cannot alias."""
    first = {
        f"d6-item-{i}-{tag}"
        for i in range(1, 5)
        for tag in ("before", "current", "pickup-recheck")
    }
    second = {
        f"d8-gen2-item-{i}-{tag}"
        for i in range(1, 5)
        for tag in ("before", "current", "pickup-recheck")
    }
    second.update({
        "d8-gen2-paper-precollected-native-check",
        "d8-gen2-native-after-real-pickup",
        "d8-gen2-fresh-rearm-source",
    })
    assert first.isdisjoint(second)
    assert len(first | second) == len(first) + len(second)


def test_d8_actual_process_session_rejects_reused_probe_before_dispatch(
    monkeypatch,
):
    """R4 safeguard is applied by the real process-session send path."""
    from adapters.mineflayer.process_session import (
        MineflayerProcessIOError,
        MineflayerProcessSession,
    )

    monkeypatch.setenv("D8_TWO_NATURAL_FOOD_CYCLES_WORLD_ONLY", "1")
    session = MineflayerProcessSession.__new__(MineflayerProcessSession)
    session._d8_sent_probe_request_ids = set()
    transmitted = []

    async def capture(line):
        transmitted.append(line)

    monkeypatch.setattr(session, "_send", capture)
    before = "d6-item-1-before"
    after = "d8-gen2-item-1-before"
    asyncio.run(session.send_observe(before))
    asyncio.run(session.send_observe(after))
    assert len(transmitted) == 2
    assert before != after
    with pytest.raises(MineflayerProcessIOError, match="duplicate probe send"):
        asyncio.run(session.send_observe(after))
    assert len(transmitted) == 2
    assert session._d8_sent_probe_request_ids == {before, after}
