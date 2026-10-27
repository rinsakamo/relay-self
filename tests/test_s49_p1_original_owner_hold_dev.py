"""Original S49 S15 producer-local Paper World tick hold (DEV only)."""
from __future__ import annotations

import asyncio

import pytest

from adapters.mineflayer.s49_p1_original_owner_hold_dev import (
    OriginalOwnerTickHoldRejected,
    await_original_paper_hold_dev,
    inspect_original_paper_hold_dev,
)


def sample_rows(n=15, *, first=250, positive_start=2, positive_end=8):
    lines = []
    for index in range(1, n + 1):
        on = positive_start <= index <= positive_end
        lines.append(
            f"[INFO] S49_DASH_DEV_TICK action_id=move-101"
            f" session_id=sid-one index={index} tick={first+index-1}"
            f" p1_world_ticks={index} p1_motor_dev=true"
            f" world=world-one player_uuid=player-one"
            f" modifier_applied={'true' if on else 'false'}"
            f" p1_current_applied_power={.75 if on else 0}"
        )
    return "\n".join(lines) + "\n"


def test_paper_tick_hold_waits_for_15th_and_leaves_S15_cleanup_owner():
    assert inspect_original_paper_hold_dev(
        sample_rows(14), action_id="move-101", session_id="sid-one",
    ) is None
    record = inspect_original_paper_hold_dev(
        sample_rows(), action_id="move-101", session_id="sid-one",
    )
    assert record["classification"] == "ORIGINAL_S49_S15_PAPER_PRODUCER_TICK_HOLD_DEV_ONLY"
    assert record["paper_hold_target_sample_index"] == 15
    assert record["paper_hold_target_world_tick"] == 264
    assert record["paper_positive_boost_ticks_before_release"] == 7
    assert record["same_original_s15_clear_owner"] is True
    assert record["native_action_duration_world_ticks_exact"] is False
    assert record["node_paper_host_clocks_synchronized"] is False
    assert record["qualification_go"] is False


@pytest.mark.parametrize("fault", [
    "gap", "index_replay", "index_missing", "p1_index", "positive_eight",
    "positive_six", "positive_late", "world_changed", "player_changed",
    "sid_changed", "wrong_power", "foreign_clock", "nan_power",
])
def test_reject_source_violations(fault):
    s = sample_rows()
    if fault == "gap":
        s = s.replace("tick=257", "tick=268")
    elif fault == "index_replay":
        s = s.replace("index=8", "index=7")
    elif fault == "index_missing":
        s = s.replace("index=8", "index=9")
    elif fault == "p1_index":
        s = s.replace("p1_world_ticks=8", "p1_world_ticks=0")
    elif fault == "positive_eight":
        s = s.replace("index=9 tick=258 p1_world_ticks=9 p1_motor_dev=true world=world-one player_uuid=player-one modifier_applied=false p1_current_applied_power=0",
                      "index=9 tick=258 p1_world_ticks=9 p1_motor_dev=true world=world-one player_uuid=player-one modifier_applied=true p1_current_applied_power=0.75")
    elif fault == "positive_six":
        s = s.replace("index=8 tick=257 p1_world_ticks=8 p1_motor_dev=true world=world-one player_uuid=player-one modifier_applied=true p1_current_applied_power=0.75",
                      "index=8 tick=257 p1_world_ticks=8 p1_motor_dev=true world=world-one player_uuid=player-one modifier_applied=false p1_current_applied_power=0")
    elif fault == "positive_late":
        s = s.replace("index=15 tick=264 p1_world_ticks=15 p1_motor_dev=true world=world-one player_uuid=player-one modifier_applied=false p1_current_applied_power=0",
                      "index=15 tick=264 p1_world_ticks=15 p1_motor_dev=true world=world-one player_uuid=player-one modifier_applied=true p1_current_applied_power=0.75")
    elif fault == "world_changed":
        s = s.replace("world=world-one", "world=world-two", 1)
    elif fault == "player_changed":
        s = s.replace("player_uuid=player-one", "player_uuid=player-two", 1)
    elif fault == "sid_changed":
        s = s.replace("session_id=sid-one", "session_id=foreign", 1)
    elif fault == "wrong_power":
        s = s.replace("index=8 tick=257 p1_world_ticks=8 p1_motor_dev=true world=world-one player_uuid=player-one modifier_applied=true p1_current_applied_power=0.75",
                      "index=8 tick=257 p1_world_ticks=8 p1_motor_dev=true world=world-one player_uuid=player-one modifier_applied=true p1_current_applied_power=0")
    elif fault == "foreign_clock":
        s = s.replace("tick=255", "tick=-1")
    else:
        s = s.replace("p1_current_applied_power=0.75", "p1_current_applied_power=nan", 1)
    with pytest.raises(OriginalOwnerTickHoldRejected):
        inspect_original_paper_hold_dev(s, action_id="move-101", session_id="sid-one")


def test_real_awaiter_only_reads_file_and_returns_owner_receipt(tmp_path):
    target = tmp_path / "paper_server.log"
    target.write_text(sample_rows())
    got = asyncio.run(await_original_paper_hold_dev(
        target, action_id="move-101", session_id="sid-one",
    ))
    assert got["paper_hold_target_sample_index"] == 15
    assert got["same_original_s15_clear_owner"] is True
    assert got["physical_p1_recovery_attested"] is False


def test_producer_local_hold_requires_source_identity():
    with pytest.raises(OriginalOwnerTickHoldRejected):
        inspect_original_paper_hold_dev(
            sample_rows(), action_id="move-101", session_id="foreign",
        )
