"""D7-E current-World source without shutdown: stop evidence != EAT grant."""
from __future__ import annotations

import json

import pytest

from adapters.mineflayer.d7_live_staged_stop import (
    D7LiveStopRejected, read_d7_live_staged_stop,
)

SID = "1a23b456-6e89-4bcb-9af0-112233445566"
ACTION = "d6-s49-item-back-1-"+SID
WORLD = "12d3f3ee-5555-4444-bbbb-aabbccddeeff"
PLAYER = "dfa44b66-aaaa-4444-bbbb-112233445566"
ITEM = "5a79c6f0-abcd-4567-aaaa-111144445555"
OFF = {k: False for k in ("forward", "back", "left", "right",
                        "jump", "sprint", "sneak")}


def sample():
    stage = (f"RSELF_LOOT_STAGED world={WORLD} owner={PLAYER} entity={ITEM} "
             "item=rotten_flesh count=1 tick=31 "
             "source=OPERATOR_FIXTURE_NOT_ZOMBIE_DROP mode=BACK_2_2M")
    picked = (f"RSELF_LOOT_PICKED world={WORLD} owner={PLAYER} entity={ITEM} "
              "item=rotten_flesh count=1 tick=66 "
              "source=ACTUAL_PAPER_PICKUP_EVENT")
    paper = [
        "RSELF_D7_PAPER_READY source=PAPER_SERVER_MAIN_THREAD_V1"
        " interval_ticks=1 max_rows=8192 mode=read_only eat_authority=none",
        stage, picked,
    ]
    for i in range(40):
        tick = 55+i
        bits = " ".join(k+"=false" for k in OFF)
        paper.append(
            "RSELF_D7_PAPER_TICK source=PAPER_SERVER_MAIN_THREAD_V1"
            f" ordinal={i+1} tick={tick} player={PLAYER} world={WORLD}"
            " x=8.5 y=-60.0 z=10.5 vx=0.0 vy=0.0 vz=0.0"
            f" ground=true {bits}"
        )
    wire = [
        {"kind": "SESSION_START", "client_physics_tick": 0, "native_seq": 0},
        {"kind": "EFFECT_ACK", "client_physics_tick": 2, "native_seq": 15,
         "native_action_id": ACTION+"-s15-clear", "controls": dict(OFF)},
    ]
    wire.extend({"kind": "PHYSICS_TICK", "client_physics_tick": i+3,
                 "controls": dict(OFF)} for i in range(20))
    return "\n".join(paper), wire, stage, picked


def invoke(paper, rows, stage, picked):
    return read_d7_live_staged_stop(
        paper, "\n".join(json.dumps({
            "source": "S50_DEV_NATIVE_READBACK_V1", "ordinal": i,
            "session_id": SID, **row,
        }) for i, row in enumerate(rows, 1)),
        session_id=SID, action_id=ACTION, clear_seq=15,
        original_stage_line=stage, original_pickup_line=picked,
    )


def test_original_source_idle_after_real_pickup_observable_before_shutdown():
    paper, rows, st, pk = sample()
    out = invoke(paper, rows, st, pk)
    assert out.classification == "D7_E_DEV_LIVE_STAGED_BODY_STEADY_SOURCE"
    assert out.paper_item_uuid == ITEM
    assert out.paper_quiet_tail_ticks >= 8
    assert out.client_postclear_physics_ticks == 20
    assert out.server_effective_original_clear_tick == "NOT_CAUSALLY_ATTESTED"


@pytest.mark.parametrize("case", [
    "wrong_pickup", "foreign_paper_world", "missing_pickup",
    "paper_gap", "paper_reactivation", "paper_nonfinite",
    "paper_early_stop", "paper_no_idle", "wrong_clear_id",
    "client_restart", "client_reactivation", "client_truncated",
    "client_short", "s50_shutdown", "lost_ack",
])
def test_foreign_or_stale_live_source_rejected(case):
    paper, rows, st, pk = sample()
    lines = paper.splitlines()
    if case == "wrong_pickup":
        pk = pk.replace(ITEM, "00000000-1111-4444-8888-555555555555")
    elif case == "foreign_paper_world":
        lines[-1] = lines[-1].replace(WORLD, "foreign-world")
    elif case == "missing_pickup":
        lines.pop(2)
    elif case == "paper_gap":
        lines[-5] = lines[-5].replace("tick=90", "tick=95")
    elif case == "paper_reactivation":
        lines[-1] = lines[-1].replace("back=false", "back=true")
    elif case == "paper_nonfinite":
        lines[-1] = lines[-1].replace("vx=0.0", "vx=NaN")
    elif case == "paper_early_stop":
        lines.append("RSELF_D7_PAPER_STOP total_ticks=40")
    elif case == "paper_no_idle":
        lines[-1] = lines[-1].replace("vx=0.0", "vx=0.3")
    elif case == "wrong_clear_id":
        rows[1]["native_action_id"] = ACTION+"-clear"
    elif case == "client_restart":
        rows[4]["client_physics_tick"] = 0
    elif case == "client_reactivation":
        rows[-1]["controls"]["back"] = True
    elif case == "client_truncated":
        rows.append({"kind": "PHYSICS_TICK", "client_physics_tick": 23})
    elif case == "client_short":
        rows = rows[:9]
    elif case == "s50_shutdown":
        rows[-1]["kind"] = "SHUTDOWN_ACK"
    elif case == "lost_ack":
        rows.pop(1)
    with pytest.raises(D7LiveStopRejected):
        invoke("\n".join(lines), rows, st, pk)


def test_old_quiet_does_not_qualify_latest_paper_body():
    paper, rows, st, pk = sample()
    ls = paper.splitlines()
    ls[-1] = ls[-1].replace("back=false", "back=true")
    with pytest.raises(D7LiveStopRejected):
        invoke("\n".join(ls), rows, st, pk)
