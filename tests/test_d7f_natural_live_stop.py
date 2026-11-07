"""D7-F natural Paper zombie death/ItemSpawn/Pickup source, never fabricated."""
from __future__ import annotations

import json

import pytest

from adapters.mineflayer.d7_live_staged_stop import (
    D7LiveStopRejected,
    read_d7_live_staged_stop,
)

WORLD = "12d3f3ee-5555-4444-bbbb-aabbccddeeff"
PLAYER = "dfa44b66-aaaa-4444-bbbb-112233445566"
ZOMBIE = "aa11bb22-3333-4444-8888-112233445566"
ITEM = "5a79c6f0-abcd-4567-aaaa-111144445555"
SID = "s49-original-one-bot"
AID = "d6-s49-item-back-1-"+SID
OFF = {k: False for k in ("forward", "back", "left", "right",
                        "jump", "sprint", "sneak")}


def natural():
    death = (
        f"RSELF_NATURAL_DROP_DEATH world={WORLD} zombie={ZOMBIE}"
        f" tick=31 rotten_count=1 killer={PLAYER}"
        " source=ACTUAL_PAPER_ENTITY_DEATH_DROPS killer_is_relay_self=true"
    )
    spawned = (
        f"RSELF_NATURAL_DROP_SPAWN world={WORLD} zombie={ZOMBIE}"
        f" item={ITEM} tick=32 rotten_count=1"
        " source=ACTUAL_PAPER_ITEM_SPAWN_NEAR_DEATH"
    )
    pickup = (
        f"RSELF_NATURAL_DROP_PICKUP world={WORLD} zombie={ZOMBIE}"
        f" item={ITEM} player={PLAYER} tick=66 rotten_count=1"
        " source=ACTUAL_PAPER_ITEM_PICKUP"
    )
    lines = [
        "RSELF_D7_PAPER_READY source=PAPER_SERVER_MAIN_THREAD_V1"
        " interval_ticks=1 max_rows=8192 mode=read_only eat_authority=none",
        death, spawned, pickup,
    ]
    for i in range(40):
        tick = i+55
        bits = " ".join(k+"=false" for k in OFF)
        lines.append(
            "RSELF_D7_PAPER_TICK source=PAPER_SERVER_MAIN_THREAD_V1"
            f" ordinal={i+1} tick={tick} player={PLAYER} world={WORLD}"
            " x=8.5 y=-60.0 z=10.5 vx=0.0 vy=0.0 vz=0.0"
            f" ground=true {bits}"
        )
    client = [
        {"kind": "SESSION_START", "client_physics_tick": 0, "native_seq": 0},
        {"kind": "EFFECT_ACK", "client_physics_tick": 2, "native_seq": 35,
         "native_action_id": AID+"-s15-clear", "controls": dict(OFF)},
    ]
    client.extend({"kind": "PHYSICS_TICK", "client_physics_tick": i+3,
                   "controls": dict(OFF)} for i in range(20))
    return lines, client, death, spawned, pickup


def evaluate(lines, client, death, spawned, pickup):
    wire = "\n".join(json.dumps({
        "source": "S50_DEV_NATIVE_READBACK_V1",
        "ordinal": i, "session_id": SID, **row,
    }) for i, row in enumerate(client, 1))
    return read_d7_live_staged_stop(
        "\n".join(lines), wire,
        session_id=SID, action_id=AID, clear_seq=35,
        original_stage_line=spawned,
        original_pickup_line=pickup,
        source_kind="natural", original_death_line=death,
    )


def test_true_natural_killer_to_item_pickup_and_live_stop():
    lines, client, death, spawn, pickup = natural()
    result = evaluate(lines, client, death, spawn, pickup)
    assert result.classification == "D7_F_DEV_LIVE_NATURAL_BODY_STEADY_SOURCE"
    assert result.paper_item_uuid == ITEM
    assert result.paper_player_uuid == PLAYER
    assert result.paper_pickup_tick == 66
    assert result.paper_quiet_tail_ticks >= 8
    assert result.server_effective_original_clear_tick == "NOT_CAUSALLY_ATTESTED"


@pytest.mark.parametrize("corruption", [
    "no_death", "wrong_death_killer", "forged_death_parameter",
    "non_self_killer", "duplicate_natural_spawn", "foreign_item",
    "foreign_player", "foreign_world", "wrong_zombie",
    "wrong_count_two", "no_pickup", "passive_staged_item",
    "paper_tick_missing", "latest_paper_input_active", "client_clear_wrong",
])
def test_natural_item_provenance_fails_closed(corruption):
    lines, client, death, spawn, pickup = natural()
    if corruption == "no_death":
        lines.pop(1)
    elif corruption == "wrong_death_killer":
        lines[1] = lines[1].replace(PLAYER, "11111111-2222-4444-8888-999999999999")
    elif corruption == "forged_death_parameter":
        death = death.replace(PLAYER, "11111111-2222-4444-8888-999999999999")
    elif corruption == "non_self_killer":
        lines[1] = lines[1].replace("killer_is_relay_self=true", "killer_is_relay_self=false")
        death = lines[1]
    elif corruption == "duplicate_natural_spawn":
        lines.insert(3, lines[2])
    elif corruption == "foreign_item":
        lines[3] = lines[3].replace(ITEM, "11111111-2222-4444-8888-999999999999")
    elif corruption == "foreign_player":
        lines[3] = lines[3].replace(PLAYER, "11111111-2222-4444-8888-999999999999")
    elif corruption == "foreign_world":
        lines[-1] = lines[-1].replace(WORLD, "11111111-2222-4444-8888-999999999999")
    elif corruption == "wrong_zombie":
        lines[2] = lines[2].replace(ZOMBIE, "11111111-2222-4444-8888-999999999999")
    elif corruption == "wrong_count_two":
        lines[2] = lines[2].replace("rotten_count=1", "rotten_count=2")
    elif corruption == "no_pickup":
        lines.pop(3)
    elif corruption == "passive_staged_item":
        lines.insert(1, "RSELF_LOOT_STAGED fabricated=true")
    elif corruption == "paper_tick_missing":
        lines[-2] = lines[-2].replace("tick=93", "tick=94")
    elif corruption == "latest_paper_input_active":
        lines[-1] = lines[-1].replace("back=false", "back=true")
    elif corruption == "client_clear_wrong":
        client[1]["native_action_id"] = AID+"-clear"
    with pytest.raises(D7LiveStopRejected):
        evaluate(lines, client, death, spawn, pickup)


def test_staged_source_cannot_claim_natural_death():
    lines, client, death, spawn, pickup = natural()
    with pytest.raises(D7LiveStopRejected):
        read_d7_live_staged_stop(
            "\n".join(lines), "\n".join(
                json.dumps({"source": "S50_DEV_NATIVE_READBACK_V1",
                            "ordinal": i, "session_id": SID, **row})
                for i, row in enumerate(client, 1)),
            session_id=SID, action_id=AID, clear_seq=35,
            original_stage_line=spawn, original_pickup_line=pickup,
        )


def test_latest_of_two_original_move_clears_is_verified_before_natural_eat():
    lines, client, death, spawn, pickup = natural()
    old = {
        "kind": "EFFECT_ACK",
        "client_physics_tick": 1,
        "native_seq": 25,
        "native_action_id": "d6-s49-item-back-1-prior-same-session-s15-clear",
        "controls": dict(OFF),
    }
    client.insert(1, old)
    out = evaluate(lines, client, death, spawn, pickup)
    assert out.original_clear_seq == 35
    assert out.client_postclear_physics_ticks == 20
    assert out.classification == "D7_F_DEV_LIVE_NATURAL_BODY_STEADY_SOURCE"


def test_true_vanilla_two_item_stack_has_same_killer_item_and_one_future_eat():
    lines, client, death, spawn, pickup = natural()
    death = death.replace("rotten_count=1", "rotten_count=2")
    spawn = spawn.replace("rotten_count=1", "rotten_count=2")
    pickup = pickup.replace("rotten_count=1", "rotten_count=2")
    lines[1], lines[2], lines[3] = death, spawn, pickup
    result = evaluate(lines, client, death, spawn, pickup)
    assert result.classification == "D7_F_DEV_LIVE_NATURAL_BODY_STEADY_SOURCE"
    assert result.paper_item_uuid == ITEM
    assert result.paper_quiet_tail_ticks >= 8


def test_mixed_one_vs_two_natural_counts_never_qualify():
    lines, client, death, spawn, pickup = natural()
    altered = spawn.replace("rotten_count=1", "rotten_count=2")
    lines[2] = altered
    with pytest.raises(D7LiveStopRejected):
        evaluate(lines, client, death, altered, pickup)
