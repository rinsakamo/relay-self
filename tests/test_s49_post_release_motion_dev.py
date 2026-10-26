"""Passive physical Paper motion after original S49 owner released DASH.

Samples are a *translation* witness, not Minecraft control flags or a
qualified SourceBoundTick / P1 WAIT recovery / M0 accounting event.
"""
from __future__ import annotations

import pytest

from adapters.mineflayer.s49_paper_forward_dash_dev import (
    ForwardDashDevRejected,
    review_post_release_motion_dev,
)
from test_s49_native_ack_paper_edges_dev import original_source
from test_s49_paper_action_bracket_dev import ACTION, SESSION, WORLD, PLAYER


def witness():
    _native, bracket = original_source()
    edges = {
        "action_id": ACTION, "session_id": SESSION,
        "paper_release_tick": 114, "native_single_reader": True,
        "independent_source_attested": False,
    }
    rows = []
    for i, delta in enumerate([0.10, 0.06, 0.03, 0.009, 0.001], 1):
        rows.append(
            f"S49_DASH_DEV_POST_RELEASE action_id={ACTION} session_id={SESSION}"
            f" tick={114+i} index={i} world={WORLD} player_uuid={PLAYER}"
            f" horizontal_delta_m={delta}"
            f" boundary={'MIXED' if i == 1 else 'POST_RELEASE'}"
            " modifier_present=false motor_write=false"
            " P1_APPLIED=false M0_POSTED=false WAIT_ATTESTED=false"
        )
    return rows, bracket, edges


def test_passive_paper_motion_never_mints_wait_or_m0_p1():
    rows, bracket, edges = witness()
    result = review_post_release_motion_dev(
        "\n".join(rows), action_id=ACTION, session_id=SESSION,
        bracket=bracket, edges=edges,
    )
    assert result["paper_callbacks"] == 5
    assert result["first_sample_tick"] == 115
    assert result["last_sample_tick"] == 119
    assert result["post_release_positive_translation_ticks"] == 3
    assert result["post_release_low_delta_ticks"] == 1
    assert result["first_delta_m_mixed_boundary"] == .10
    assert not result["WAIT_sourcebound_admitted"]
    assert not result["native_control_effect_tick_attested"]
    assert not result["M0_posted"] and not result["P1_posted"]


@pytest.mark.parametrize("corruption", [
    "missing", "duplicate", "wrong_world", "wrong_player", "foreign_session",
    "gap", "noncanonical_index", "negative", "nan", "infinite", "teleport",
    "mixed_marker_on_second", "second_marked_mixed", "modifier",
    "motor_write", "P1_claim", "M0_claim", "WAIT_claim", "wrong_action",
    "bad_ack", "foreign_bracket",
])
def test_forged_or_incomplete_post_release_motion_denied(corruption):
    rows, bracket, edges = witness()
    if corruption == "missing":
        rows.pop(2)
    elif corruption == "duplicate":
        rows.insert(1, rows[0])
    elif corruption == "wrong_world":
        rows[2] = rows[2].replace(WORLD, PLAYER)
    elif corruption == "wrong_player":
        rows[2] = rows[2].replace(PLAYER, WORLD)
    elif corruption == "foreign_session":
        rows[2] = rows[2].replace("session_id=" + SESSION, "session_id=alien")
    elif corruption == "gap":
        rows[2] = rows[2].replace("tick=117", "tick=119")
    elif corruption == "noncanonical_index":
        rows[2] = rows[2].replace("index=3", "index=4")
    elif corruption == "negative":
        rows[2] = rows[2].replace("horizontal_delta_m=0.03", "horizontal_delta_m=-.5")
    elif corruption == "nan":
        rows[2] = rows[2].replace("horizontal_delta_m=0.03", "horizontal_delta_m=nan")
    elif corruption == "infinite":
        rows[2] = rows[2].replace("horizontal_delta_m=0.03", "horizontal_delta_m=inf")
    elif corruption == "teleport":
        rows[2] = rows[2].replace("horizontal_delta_m=0.03", "horizontal_delta_m=20")
    elif corruption in ("mixed_marker_on_second", "second_marked_mixed"):
        rows[1] = rows[1].replace("boundary=POST_RELEASE", "boundary=MIXED")
    elif corruption == "modifier":
        rows[2] = rows[2].replace("modifier_present=false", "modifier_present=true")
    elif corruption == "motor_write":
        rows[2] = rows[2].replace("motor_write=false", "motor_write=true")
    elif corruption == "P1_claim":
        rows[2] = rows[2].replace("P1_APPLIED=false", "P1_APPLIED=true")
    elif corruption == "M0_claim":
        rows[2] = rows[2].replace("M0_POSTED=false", "M0_POSTED=true")
    elif corruption == "WAIT_claim":
        rows[2] = rows[2].replace("WAIT_ATTESTED=false", "WAIT_ATTESTED=true")
    elif corruption == "wrong_action":
        rows[2] = rows[2].replace("action_id=" + ACTION, "action_id=alien")
    elif corruption == "bad_ack":
        edges["paper_release_tick"] = 116
    else:
        bracket["world_uuid"] = PLAYER
    with pytest.raises(ForwardDashDevRejected):
        review_post_release_motion_dev(
            "\n".join(rows), action_id=ACTION, session_id=SESSION,
            bracket=bracket, edges=edges,
        )
