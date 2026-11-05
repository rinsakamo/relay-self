"""Original #734 callback source reuse, not physical P1-B admission."""
from dataclasses import replace

import pytest

from adapters.mineflayer.s49_p1_paper_dev import S49P1SourceRejected
from adapters.mineflayer.worldbody_p1_source_candidates import (
    assess_existing_paper_p1_source,
    p1_physical_tick_from_callback,
)
from test_bug0_s49_p1_paper_dev import NONCE, SESSION, native, sample_log


def test_existing_paper_tick_emitter_reused_with_wait_still_unqualified():
    result = assess_existing_paper_p1_source(
        sample_log(), nonce=NONCE, native_report=native(),
    )
    assert result.session_id == SESSION
    assert result.callback_count == 30
    assert result.p1_admitted_tick_count == 0
    assert result.original_source_qualification == "DEV_CALLBACK_BOUNDED_ONLY"
    assert len(result.outstanding_owner_evidence) == 3
    assert [x.world_tick for x in result.candidates] == list(range(101, 131))
    assert [x.world_tick for x in result.candidates
            if x.activity == "FIGHT_CALLBACK_CANDIDATE"] == [104]
    quiet = [x for x in result.candidates
             if x.activity == "QUIET_CALLBACK_WAIT_CANDIDATE"]
    assert {x.world_tick for x in quiet} >= set(range(117, 125))
    assert all(not x.admissible_as_source_bound_tick for x in result.candidates)
    assert all(not x.genuine_full_tick_wait_attested for x in result.candidates)
    for row in result.candidates:
        with pytest.raises(ValueError, match="S/R tick owner not connected"):
            p1_physical_tick_from_callback(row)


def test_original_callback_with_move_is_not_autocredited_as_p1_move_or_wait():
    log = sample_log().replace(
        "tick=108 index=8 x=2.5 y=-60.0 z=0.5 move_events=0 move_distance=0.0",
        "tick=108 index=8 x=2.5 y=-60.0 z=0.5 move_events=1 move_distance=0.12",
    )
    result = assess_existing_paper_p1_source(
        log, nonce=NONCE, native_report=native(),
    )
    candidate = next(x for x in result.candidates if x.world_tick == 108)
    assert candidate.activity == "MOVE_CALLBACK_CANDIDATE"
    assert candidate.observed_move_blocks == 0.12
    assert candidate.admissible_as_source_bound_tick is False
    # #734's sole original S49 Action is ATTACK, not an authorized MOVE.
    assert result.original_attack_action_id == "one-action"


def test_eventless_callback_must_not_turn_blocked_move_into_wait():
    result = assess_existing_paper_p1_source(
        sample_log(), nonce=NONCE, native_report=native(),
    )
    apparent_quiet = next(
        x for x in result.candidates if x.world_tick == 118
    )
    assert apparent_quiet.activity == "QUIET_CALLBACK_WAIT_CANDIDATE"
    # Even if another S49 Action blocked with zero distance, this callback
    # has no S Action/control lifecycle and cannot qualify its activity.
    assert apparent_quiet.admissible_as_source_bound_tick is False
    with pytest.raises(ValueError):
        p1_physical_tick_from_callback(apparent_quiet)
    forged = replace(
        apparent_quiet, admissible_as_source_bound_tick=True,
        genuine_full_tick_wait_attested=True,
    )
    with pytest.raises(ValueError):
        p1_physical_tick_from_callback(forged)


@pytest.mark.parametrize("variant", (
    "gapped-tick", "foreign-world", "extra-swing-in-rest",
    "missing-fight", "foreign-original-action", "unbounded-tick",
))
def test_existing_inspector_rejects_bad_source_before_any_p1_frame(variant):
    log = sample_log()
    scope = native()
    if variant == "gapped-tick":
        log = "\n".join(
            line for line in log.splitlines() if "S49P1_TICK " not in line
            or "tick=120 " not in line
        )
    elif variant == "foreign-world":
        log = log.replace("world=11111111-2222-3333-4444-555555555555 tick=120",
                          "world=otherworld tick=120")
    elif variant == "extra-swing-in-rest":
        log = log.replace(
            "tick=122 index=22 x=2.5 y=-60.0 z=0.5 move_events=0 move_distance=0.0 fight_events=0 swing_events=0",
            "tick=122 index=22 x=2.5 y=-60.0 z=0.5 move_events=0 move_distance=0.0 fight_events=0 swing_events=1",
        )
    elif variant == "missing-fight":
        log = "\n".join(line for line in log.splitlines()
                        if "S49P1_FIGHT " not in line)
    elif variant == "foreign-original-action":
        scope["actual_native_actions"][0]["terminal"] = "unknown"
    else:
        log = log.replace("S49P1_STOP nonce=", "S49P1_SOURCE_FAULT nonce=")
    with pytest.raises(S49P1SourceRejected):
        assess_existing_paper_p1_source(log, nonce=NONCE, native_report=scope)


def test_no_worldbody_or_p1_physics_write_implicit_in_source_adapter():
    import inspect

    import adapters.mineflayer.worldbody_p1_source_candidates as module

    code = inspect.getsource(module)
    assert "inspect_paper_tick_source(" in code
    assert "p1_physical_tick_from_callback(" in code
    assert "advance(" not in code
    assert "FatigueFrame(" not in code
    assert "setWalkSpeed(" not in code
