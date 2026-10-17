"""Strict recorded-action/command provenance, never native held-input attestation."""
from __future__ import annotations

import copy

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.m02_paper_dev.s50_p1_control_action import (
    review_control_action,
)


ACTION = "m02-paper-walk-1"
SESSION = "11111111-2222-4333-8444-555555555555"
MARKER = ACTION + "-" + SESSION
WORLD = "00000000-0000-0000-0000-000000000001"


def fixture():
    movement = {
        "action_id": ACTION, "source_session": SESSION,
        "v7_phase_marker_id": MARKER, "source_before_seq": 1,
        "look_seq": 2, "forward_seq": 3, "clear_seq": 4,
        "source_after_seq": 5,
    }
    native = [
        {"type": "adapter_started", "session_id": SESSION, "seq": 0},
        {"type": "observation", "session_id": SESSION, "seq": 1},
        {"type": "effect_result", "session_id": SESSION, "seq": 2,
         "action_id": ACTION + "-look", "effect": "look", "result": "applied"},
        {"type": "effect_result", "session_id": SESSION, "seq": 3,
         "action_id": ACTION, "effect": "set_control", "result": "applied"},
        {"type": "effect_result", "session_id": SESSION, "seq": 4,
         "action_id": ACTION + "-clear", "effect": "clear_controls",
         "result": "applied"},
        {"type": "observation", "session_id": SESSION, "seq": 5,
         "request_id": ACTION + "-seek-after"},
        {"type": "shutdown_ack", "session_id": SESSION, "seq": 6},
    ]
    commands = [
        {"type": "effect", "action_id": ACTION + "-look", "effect": "look"},
        {"type": "effect", "action_id": ACTION, "effect": "set_control",
         "control": "forward", "state": True},
        {"type": "effect", "action_id": ACTION + "-clear",
         "effect": "clear_controls"},
    ]
    proposed = [{"state": v} for v in ("proposed", "authorized", "issued")]
    journal = [
        {"action_id": ACTION, "session_id": SESSION,
         "clock": "SYNTHETIC_DEV_LOGICAL_ORDER_NOT_WORLD_TIME",
         "state": "issued", "events": proposed},
        {"action_id": ACTION, "session_id": SESSION,
         "clock": "SYNTHETIC_DEV_LOGICAL_ORDER_NOT_WORLD_TIME",
         "state": "outcome", "events": proposed + [{"state": "outcome"}]},
    ]
    paper = [
        f"M02_DEV_S50_PHASE marker_id={MARKER} world={WORLD} "
        f"phase={phase} world_full_time={tick}"
        for phase, tick in (
            ("PRE_FORWARD", 50), ("POST_FORWARD", 51),
            ("PRE_CLEAR", 57), ("POST_CLEAR", 58))
    ]
    paper.append(f"S50_DEV_WAIT_BEGIN marker_id={MARKER} world={WORLD} tick=60")
    for i in range(1, 9):
        paper.append(
            f"S50_DEV_WAIT_TICK marker_id={MARKER} world={WORLD} "
            f"tick={60+i} index={i}"
        )
    return ("\n".join(paper), native, commands, journal, movement)


def review(f):
    return review_control_action(*f)


def test_clean_correlation_is_commanded_clear_not_true_held_readback():
    out = review(fixture())
    assert out["issued_terminal_sequence"] == ["issued", "outcome"]
    assert out["paper_post_clear_tick"] == 58
    assert out["paper_wait_begin_tick"] == 60
    assert out["native_commanded_control_after_clear"] == "CLEARED_BY_APPLIED_COMMAND_ACK"
    assert out["native_held_controls_readback"] == "NOT_ATTESTED"
    assert out["client_server_effective_tick_mapping"] == "NOT_ATTESTED"
    assert out["all_other_action_issuers_absent"] == "NOT_ATTESTED"
    assert out["wait_ticks_admitted"] == 0
    assert out["p1_fatigue_recovered"] == 0
    assert out["science_go"] is False


@pytest.mark.parametrize("change", [
    "foreign_action", "wrong_session", "open_action", "wrong_clock",
    "extra_action", "bad_events", "missing_ack", "rejected_clear",
    "duplicated_ack", "foreign_native", "motor_still_forward",
    "wrong_control", "additional_effect", "missing_stop",
    "phase_wrong_marker", "phase_wrong_world", "begin_before_clear",
    "missing_wait_tick", "regressed_native_seq", "wrong_probe",
])
def test_action_control_or_paper_tamper_fails_closed(change):
    original = list(fixture())
    f = copy.deepcopy(original)
    paper, native, commands, journal, movement = f
    if change == "foreign_action":
        journal[1]["action_id"] = "foreign"
    elif change == "wrong_session":
        journal[0]["session_id"] = "foreign"
    elif change == "open_action":
        journal[1]["state"] = "issued"
    elif change == "wrong_clock":
        journal[0]["clock"] = "PAPER_WORLD_TICK"
    elif change == "extra_action":
        journal.append(copy.deepcopy(journal[1]))
    elif change == "bad_events":
        journal[1]["events"][-1]["state"] = "unknown"
    elif change == "missing_ack":
        native.pop(4)
    elif change == "rejected_clear":
        native[4]["result"] = "rejected"
    elif change == "duplicated_ack":
        native.append(copy.deepcopy(native[4]))
    elif change == "foreign_native":
        native[3]["session_id"] = "other"
    elif change == "motor_still_forward":
        commands.pop(2)
    elif change == "wrong_control":
        commands[1]["control"] = "jump"
    elif change == "additional_effect":
        commands.append({"type": "effect", "action_id": "other", "effect": "look"})
    elif change == "missing_stop":
        native.pop()
    elif change == "phase_wrong_marker":
        paper = paper.replace("marker_id=" + MARKER, "marker_id=other", 1)
    elif change == "phase_wrong_world":
        paper = paper.replace("world=" + WORLD, "world=other", 1)
    elif change == "begin_before_clear":
        paper = paper.replace("world=" + WORLD + " tick=60",
                              "world=" + WORLD + " tick=57")
    elif change == "missing_wait_tick":
        paper = "\n".join(line for line in paper.splitlines() if "index=7" not in line)
    elif change == "regressed_native_seq":
        native[4]["seq"] = 3
    elif change == "wrong_probe":
        native[5]["request_id"] = "someone-else"
    with pytest.raises(BoundaryRejected):
        review((paper, native, commands, journal, movement))
