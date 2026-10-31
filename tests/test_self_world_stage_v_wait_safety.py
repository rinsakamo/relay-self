"""Stage V candidate near-WAIT safety observation: synthetic World only.

Even healthy stationary no-harm exposure is NOT an admission right.
"""
from __future__ import annotations

import math
from dataclasses import replace

import pytest

import test_self_world_stage_s_feedback as s_fixture
from adapters.mineflayer.python_protocol import (
    MineflayerEntityHurt,
    MineflayerNativeClockPacket,
)
from adapters.mineflayer.self_world_stage_v_wait_safety import (
    StageVWaitRejected,
    StageVWaitResult,
    StageVWaitRule,
    screen_near_wait_observation,
)


def _clock(sid, seq, ticks):
    return MineflayerNativeClockPacket(
        session_id=sid,
        seq=seq,
        source="minecraft_1_21_8_clientbound_update_time",
        observation_precision="SERVER_UPDATE_TIME_PACKET_SAMPLE_ONLY",
        world_age_ticks=str(ticks),
        world_day_time_raw_ticks=str(ticks),
        tick_day_time=True,
        host_monotonic_ns=str(10000000 + 10000 * seq),
        command_effect_tick_attested=False,
    )


def _inputs():
    original = s_fixture._synthetic_targeted_witness()
    before = replace(original.original_probe, seq=3)
    after = replace(before, seq=13, request_id=(
        f"s49-actual:{before.session_id}:event-12"
    ))
    return {
        "before": before,
        "after": after,
        "start_clock": _clock(before.session_id, 2, 100),
        "end_clock": _clock(before.session_id, 14, 125),
        "hurt_events": (),
        "death_events": (),
        "bot_entity_id": 99,
        "rule": StageVWaitRule(),
    }


def test_v_healthy_stationary_candidate_never_unlocks_near_wait():
    evidence = _inputs()
    result = screen_near_wait_observation(**evidence)
    assert result.status is StageVWaitResult.NO_HARM_WINDOW_CANDIDATE
    assert result.world_age_tick_delta == 25
    assert result.near_zombie_id is not None
    assert result.health_before == result.health_after
    assert result.hurt_events == 0
    assert not result.safe_to_wait_near_zombie
    assert not result.physical_wait_permitted
    assert not result.stream_continuity_independently_attested
    assert not result.signed_world_source_attested
    assert not result.survival_gain_proven
    assert not result.science_qualified


@pytest.mark.parametrize("bad", (
    "damage", "actor_hurt", "death", "zero_health",
))
def test_v_observed_harm_takes_precedence_over_no_harm_candidate(bad):
    items = _inputs()
    after = items["after"]
    if bad == "damage":
        items["after"] = replace(
            after, snapshot=replace(after.snapshot, health=after.snapshot.health-1),
        )
    elif bad == "actor_hurt":
        items["hurt_events"] = (
            MineflayerEntityHurt(
                session_id=after.session_id, seq=10, entity_id=99,
                source_entity_id=3, actor_entity_id=99,
            ),
        )
    elif bad == "death":
        items["death_events"] = (
            replace(after, seq=10, kind="death", request_id=None),
        )
    else:
        items["after"] = replace(
            after, snapshot=replace(after.snapshot, health=0),
        )
    result = screen_near_wait_observation(**items)
    assert result.status is StageVWaitResult.HARM_OBSERVED
    assert not result.physical_wait_permitted
    assert not result.safe_to_wait_near_zombie


@pytest.mark.parametrize("bad", (
    "short_ticks", "healed_health", "target_missing",
    "target_changed", "different_entity_distance", "bot_moved",
))
def test_v_incomplete_or_confounded_no_harm_is_undetermined_or_rejected(bad):
    items = _inputs()
    after = items["after"]
    if bad == "short_ticks":
        items["end_clock"] = _clock(after.session_id, 14, 109)
    elif bad == "healed_health":
        items["after"] = replace(
            after, snapshot=replace(after.snapshot, health=after.snapshot.health+1),
        )
    elif bad == "target_missing":
        items["after"] = replace(
            after, snapshot=replace(
                after.snapshot, nearby_entities=(),
                nearby_entities_coverage=replace(
                    after.snapshot.nearby_entities_coverage, candidate_count=0,
                ),
            ),
        )
    elif bad == "target_changed":
        e = after.snapshot.nearby_entities[0]
        items["after"] = replace(
            after, snapshot=replace(
                after.snapshot, nearby_entities=(replace(e, entity_id=e.entity_id+99),),
            ),
        )
    elif bad == "different_entity_distance":
        e = after.snapshot.nearby_entities[0]
        items["after"] = replace(
            after, snapshot=replace(
                after.snapshot, nearby_entities=(replace(e, distance=e.distance+1),),
            ),
        )
    else:
        p = after.snapshot.position
        moved = replace(p, z=p.z + 0.1)
        e = after.snapshot.nearby_entities[0]
        actual = math.dist(
            (moved.x, moved.y, moved.z),
            (e.position.x, e.position.y, e.position.z),
        )
        items["after"] = replace(
            after, snapshot=replace(
                after.snapshot, position=moved,
                nearby_entities=(replace(e, distance=actual),),
            ),
        )
    if bad == "different_entity_distance":
        with pytest.raises(StageVWaitRejected):
            screen_near_wait_observation(**items)
    else:
        result = screen_near_wait_observation(**items)
        assert result.status is StageVWaitResult.UNDETERMINED
        assert not result.physical_wait_permitted


@pytest.mark.parametrize("bad", (
    "foreign_after", "nonmonotone_seq", "foreign_clock",
    "counter_decreased", "foreign_hurt", "foreign_death",
    "reused_event_clock", "wrong_start_clock",
))
def test_v_foreign_clock_or_world_event_evidence_fail_closed(bad):
    items = _inputs()
    before, after = items["before"], items["after"]
    if bad == "foreign_after":
        items["after"] = replace(after, session_id="other-session")
    elif bad == "nonmonotone_seq":
        items["after"] = replace(after, seq=before.seq)
    elif bad == "foreign_clock":
        items["end_clock"] = replace(items["end_clock"], session_id="other-session")
    elif bad == "counter_decreased":
        items["end_clock"] = _clock(before.session_id, 14, 99)
    elif bad == "foreign_hurt":
        items["hurt_events"] = (
            MineflayerEntityHurt(
                session_id="foreign", seq=10, entity_id=99,
                source_entity_id=None, actor_entity_id=99,
            ),
        )
    elif bad == "foreign_death":
        items["death_events"] = (
            replace(after, seq=10, kind="death", request_id=None, session_id="foreign"),
        )
    elif bad == "reused_event_clock":
        items["end_clock"] = _clock(before.session_id, 12, 125)
    else:
        items["start_clock"] = _clock(before.session_id, 4, 100)
    with pytest.raises(StageVWaitRejected):
        screen_near_wait_observation(**items)


def test_v_rule_frozen_and_health_only_not_equivalent_to_qualified_safety():
    with pytest.raises(StageVWaitRejected):
        StageVWaitRule(exposure_ticks=0)
    with pytest.raises(StageVWaitRejected):
        StageVWaitRule(near_radius_m=200.0)
    result = screen_near_wait_observation(**_inputs())
    assert result.status is StageVWaitResult.NO_HARM_WINDOW_CANDIDATE
    assert not result.stream_continuity_independently_attested
    assert not result.physical_wait_permitted
