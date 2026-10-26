"""Two original S49 Actions: one continuous Paper World clock, zero new M0 writes."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.s49_two_action_world_timeline_dev import (
    TwoActionWorldTimelineRejected,
    review_two_action_world_timeline_dev,
)


def source():
    sid, first, second = "native-session-dev", "s49-native-move-18", "s49-native-move-55"
    arm, end1, release, apply2, clear2, finish = 100, 113, 114, 130, 142, 147
    def row(kind, **kwargs):
        return "S49_DASH_DEV_TRAIL_" + kind + " " + " ".join(
            f"{k}={v}" for k, v in kwargs.items()
        )
    log = []
    x, z = 0., 0.
    for tick in range(arm + 1, finish + 1):
        dx = .15 if tick <= end1 else .01 if tick <= apply2 else (
            .12 if tick <= clear2 else .025
        )
        x += dx
        log.append(row(
            "TICK", action_id=first, session_id=sid,
            world="world-s49", player_uuid="player-s49",
            tick=tick, index=tick-arm,
            second_applied_marker_seen=str(tick > apply2).lower(),
            second_cleared_marker_seen=str(tick > clear2).lower(),
            first_dash_modifier_present=str(tick < release).lower(),
            x=round(x, 8), z=z,
            motor_write="false", M0_POSTED="false",
            P1_APPLIED="false", WAIT_ATTESTED="false",
        ))
    for tick, phase, seq in ((apply2, "APPLIED", 60), (clear2, "CLEARED", 72)):
        log.append(row(
            "EDGE", action_id=second, session_id=sid,
            world="world-s49", player_uuid="player-s49",
            tick=tick, phase=phase, native_seq=seq,
            delivered_after_original_native_ack="true",
            exact_client_effect_tick_attested="false",
        ))
    log.append(row(
        "COMPLETE", action_id=first, second_action_id=second,
        session_id=sid, world="world-s49", player_uuid="player-s49",
        tick=finish, samples=finish-arm,
        reason="SECOND_NATIVE_ACK_MARKER_PLUS_FIVE",
        motor_write="false", M0_POSTED="false",
        P1_APPLIED="false", WAIT_ATTESTED="false",
    ))
    original_actions = [
        {"action": first, "terminal": "outcome"},
        {"action": second, "terminal": "outcome", "execution_evidence": {
            "session_id": sid,
            "dispatch_receipt": {
                "session_id": sid, "action_id": second,
                "effect": "set_forward_sprint_dev", "result": "applied",
                "seq": 60,
            },
            "cleanup_receipt": {
                "session_id": sid, "action_id": second + "-s15-clear",
                "effect": "clear_controls", "result": "applied",
                "seq": 72,
            },
        }},
    ]
    return {
        "raw": "\n".join(log),
        "action_id": first, "session_id": sid,
        "bracket": {
            "classification": "PAPER_LOCAL_ARM_TICK_RELEASE_BRACKET_DEV_ONLY",
            "action_id": first, "session_id": sid, "world_uuid": "world-s49",
            "player_uuid": "player-s49", "arm_tick": arm, "first_tick": 101,
            "last_tick": end1, "release_tick": release, "elapsed_callbacks": 13,
            "original_owner_release": True, "independent_source_attested": False,
            "mineflayer_paper_tick_synchronized": False,
        },
        "passive": {
            "classification": "PAPER_PASSIVE_POST_RELEASE_TRANSLATION_DEV_ONLY",
            "action_id": first, "session_id": sid,
            "first_sample_tick": 115, "last_sample_tick": 119,
            "paper_callbacks": 5, "WAIT_sourcebound_admitted": False,
            "M0_posted": False,
        },
        "first_native_ack": {
            "classification": "S49_NATIVE_ACK_TO_PAPER_MARKER_DELIVERY_DEV_ONLY",
            "action_id": first, "session_id": sid,
            "native_cleanup_ack_seq": 35, "native_single_reader": True,
            "paper_release_tick": release, "independent_source_attested": False,
        },
        "original_actions": original_actions,
        "original_m0_postings": [
            {"action_id": first, "session_id": sid,
             "m0_tick_after": 1, "basal_debit": .5, "move_debit": .25},
            {"action_id": second, "session_id": sid,
             "m0_tick_after": 2, "basal_debit": .5, "move_debit": .25,
             "energy_after": 10.413667611509306},
        ],
        "final_original_energy": 10.413667611509306,
    }


def test_two_action_paper_full_time_single_contiguous_readonly_shadow():
    k = source()
    before = deepcopy(k)
    r = review_two_action_world_timeline_dev(**k)
    assert r["classification"] == "M0_TWO_NATIVE_ACTIONS_CONTIGUOUS_WORLD_TIMELINE_SHADOW_DEV_ONLY"
    assert r["first_sample_tick"] == 101
    assert r["last_sample_tick"] == 147
    assert r["observed_contiguous_paper_ticks"] == 47
    assert [r[x] for x in (
        "first_action_paper_tick_count",
        "first_release_to_second_ack_delivery_bridge_ticks",
        "second_ack_delivery_window_ticks", "second_clear_to_tail_ticks",
    )] == [13, 17, 12, 5]
    assert r["observed_normalized_world_seconds"] == 47 / 20
    assert r["basal_shadow_all_observed_ticks_not_posted"] == pytest.approx(47 * .025)
    assert r["move_shadow_first_action_window_not_posted"] == pytest.approx(13 * .0125)
    assert r["move_shadow_second_ack_window_geometric_proxy_not_posted"] == pytest.approx(12 * .0125)
    assert r["second_window_translation_proxy_ticks"] == 12
    assert r["tick_gaps_or_replay"] is False
    assert r["double_counted_world_ticks"] is False
    assert r["second_window_not_exact_native_effect_timing"] is True
    assert r["bridge_motion_classification"] == "UNKNOWN_NOT_CERTIFIED_WAIT_OR_MOVE"
    assert r["original_owner_energy_unchanged"] == 10.413667611509306
    assert not any(r[f] for f in ("world_tick_m0_debits_posted", "legacy_action_m0_replaced",
                                  "WAIT_sourcebound_admitted", "P1_recovery_posted",
                                  "independent_source_attested", "science_go", "qualification_go"))
    assert k == before


def test_same_world_tick_marker_callback_order_is_ambiguous():
    k = source()
    k["raw"] = k["raw"].replace(
        "tick=130 index=30 second_applied_marker_seen=false",
        "tick=130 index=30 second_applied_marker_seen=true",
    ).replace(
        "tick=142 index=42 second_applied_marker_seen=true second_cleared_marker_seen=false",
        "tick=142 index=42 second_applied_marker_seen=true second_cleared_marker_seen=true",
    )
    assert review_two_action_world_timeline_dev(**k)["observed_contiguous_paper_ticks"] == 47


@pytest.mark.parametrize("fault", [
    "missing", "duplicate", "foreign_actor", "foreign_session", "wrong_world",
    "replayed_seq", "backward_tick", "wrong_count", "fake_control",
    "fake_M0", "fake_P1", "fake_WAIT", "retained_modifier", "nan_pos",
    "teleport", "missing_apply", "missing_clear", "replayed_clear",
    "foreign_native_ack", "wrong_native_ack_seq", "fake_native_ack_source",
    "fake_client_effect_tick", "applied_after_clear", "terminal_missing",
    "terminal_wrong_action", "terminal_fake_success", "negative_count",
    "not_enough_second_movement", "missing_basal_owner", "fake_ledger",
    "invalid_per_second_rate", "fake_wait_bridge", "fake_source_trust",
    "native_second_foreign_session", "no_native_outcome",
])
def test_replayed_foreign_or_fabricated_two_action_world_time_denied(fault):
    k = source()
    if fault in ("missing", "duplicate", "foreign_actor", "foreign_session", "wrong_world",
                 "replayed_seq", "backward_tick", "wrong_count", "fake_control",
                 "fake_M0", "fake_P1", "fake_WAIT", "retained_modifier",
                 "nan_pos", "teleport", "not_enough_second_movement"):
        lines = k["raw"].splitlines()
        if fault == "missing":
            lines.pop(21)
        elif fault == "duplicate":
            lines.insert(20, lines[20])
        elif fault == "foreign_actor":
            lines[20] = lines[20].replace("player_uuid=player-s49", "player_uuid=other")
        elif fault == "foreign_session":
            lines[20] = lines[20].replace("session_id=native-session-dev", "session_id=wrong")
        elif fault == "wrong_world":
            lines[20] = lines[20].replace("world=world-s49", "world=foreign")
        elif fault == "replayed_seq":
            lines[20] = lines[20].replace("index=21", "index=20")
        elif fault == "backward_tick":
            lines[20] = lines[20].replace("tick=121", "tick=120")
        elif fault == "wrong_count":
            lines[-1] = lines[-1].replace("samples=47", "samples=48")
        elif fault == "fake_control":
            lines[20] = lines[20].replace("second_applied_marker_seen=false", "second_applied_marker_seen=true")
        elif fault == "fake_M0":
            lines[20] = lines[20].replace("M0_POSTED=false", "M0_POSTED=true")
        elif fault == "fake_P1":
            lines[20] = lines[20].replace("P1_APPLIED=false", "P1_APPLIED=true")
        elif fault == "fake_WAIT":
            lines[20] = lines[20].replace("WAIT_ATTESTED=false", "WAIT_ATTESTED=true")
        elif fault == "retained_modifier":
            lines[20] = lines[20].replace("first_dash_modifier_present=false",
                                          "first_dash_modifier_present=true")
        elif fault == "nan_pos":
            lines[20] = " ".join(
                "x=nan" if field.startswith("x=") else field
                for field in lines[20].split()
            )
        elif fault == "teleport":
            lines[20] = lines[20].replace("x=", "x=90", 1)
        else:
            # Deliberately freeze the second claimed movement window.
            # Keep ticks/markers intact; geometrically no real MOVE signal.
            x_prev = next(part for part in lines[29].split()
                          if part.startswith("x="))
            for i in range(30, 42):
                lines[i] = " ".join(
                    x_prev if field.startswith("x=") else field
                    for field in lines[i].split()
                )
        k["raw"] = "\n".join(lines)
    elif fault.startswith("missing_") and fault != "missing_basal_owner":
        tag = "S49_DASH_DEV_TRAIL_EDGE "
        lines = k["raw"].splitlines()
        i = next(i for i, v in enumerate(lines) if tag in v and
                 (("APPLIED" in v) if fault == "missing_apply" else ("CLEARED" in v)))
        lines.pop(i)
        k["raw"] = "\n".join(lines)
    elif fault == "replayed_clear":
        lines = k["raw"].splitlines()
        lines.insert(-1, lines[-2])
        k["raw"] = "\n".join(lines)
    elif fault == "foreign_native_ack":
        k["raw"] = k["raw"].replace("native_seq=60", "native_seq=600")
    elif fault == "wrong_native_ack_seq":
        k["original_actions"][1]["execution_evidence"]["cleanup_receipt"]["seq"] = 75
    elif fault == "fake_native_ack_source":
        k["raw"] = k["raw"].replace("delivered_after_original_native_ack=true",
                                     "delivered_after_original_native_ack=false")
    elif fault == "fake_client_effect_tick":
        k["raw"] = k["raw"].replace("exact_client_effect_tick_attested=false",
                                     "exact_client_effect_tick_attested=true")
    elif fault == "applied_after_clear":
        k["raw"] = k["raw"].replace("tick=130 phase=APPLIED", "tick=146 phase=APPLIED")
    elif fault == "terminal_missing":
        k["raw"] = "\n".join(k["raw"].splitlines()[:-1])
    elif fault == "terminal_wrong_action":
        k["raw"] = k["raw"].replace("second_action_id=s49-native-move-55",
                                     "second_action_id=foreign")
    elif fault == "terminal_fake_success":
        k["raw"] = k["raw"].replace("reason=SECOND_NATIVE_ACK_MARKER_PLUS_FIVE",
                                     "reason=PLUGIN_DISABLED")
    elif fault == "negative_count":
        k["raw"] = k["raw"].replace("samples=47", "samples=-5")
    elif fault == "missing_basal_owner":
        k["original_m0_postings"].pop()
    elif fault == "fake_ledger":
        k["final_original_energy"] = 11
    elif fault == "invalid_per_second_rate":
        k["basal_per_world_second"] = float("nan")
    elif fault == "fake_wait_bridge":
        k["passive"]["WAIT_sourcebound_admitted"] = True
    elif fault == "fake_source_trust":
        k["bracket"]["independent_source_attested"] = True
    elif fault == "native_second_foreign_session":
        k["original_actions"][1]["execution_evidence"]["session_id"] = "alien"
    else:
        k["original_actions"][1]["terminal"] = "unknown"
    with pytest.raises(TwoActionWorldTimelineRejected):
        review_two_action_world_timeline_dev(**k)
