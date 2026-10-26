"""Original S15 effect ACK -> delayed Paper timestamp DEV join, no second reader."""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

import test_action_feedback_qualification as s17
from adapters.mineflayer.execution import (
    WorldConsequenceStatus,
    build_mineflayer_command,
    execute_mineflayer_command,
)
from adapters.mineflayer.s49_paper_forward_dash_dev import (
    ForwardDashDevRejected,
    review_original_s49_native_effect_edges_dev,
)
from test_s49_m0_dash_extra_owner_dev import source
from test_s49_paper_action_bracket_dev import ACTION, PLAYER, SESSION, WORLD, rows


def original_source():
    receipt, _, native = source()
    native = dict(native)
    native["action_id"] = ACTION
    native["session_id"] = SESSION
    dispatch = dict(native["dispatch_receipt"])
    cleanup = dict(native["cleanup_receipt"])
    dispatch.update(action_id=ACTION, session_id=SESSION, seq=23)
    cleanup.update(action_id=ACTION + "-s15-clear", session_id=SESSION, seq=36)
    native["dispatch_receipt"], native["cleanup_receipt"] = dispatch, cleanup
    bracket = {
        "action_id": ACTION, "session_id": SESSION,
        "world_uuid": WORLD, "player_uuid": PLAYER,
        "arm_tick": 100, "first_tick": 101, "last_tick": 113,
        "release_tick": 114, "original_owner_release": True,
        "independent_source_attested": False,
    }
    return native, bracket


def edge_rows():
    lines = rows()
    lines.insert(3,
        f"S49_DASH_DEV_EDGE action_id={ACTION} session_id={SESSION}"
        f" world={WORLD} player_uuid={PLAYER} phase=APPLIED"
        " native_seq=23 tick=102 marker_after_native_ack=true"
        " synchronized_native_effect_tick=false"
    )
    lines.insert(-2,
        f"S49_DASH_DEV_EDGE action_id={ACTION} session_id={SESSION}"
        f" world={WORLD} player_uuid={PLAYER} phase=CLEARED"
        " native_seq=36 tick=112 marker_after_native_ack=true"
        " synchronized_native_effect_tick=false"
    )
    return lines


def test_native_original_ack_seq_paper_delivery_bracket_no_clock_claim():
    native, bracket = original_source()
    result = review_original_s49_native_effect_edges_dev(
        "\n".join(edge_rows()), action_id=ACTION, session_id=SESSION,
        native_evidence=native, bracket=bracket,
    )
    assert result["native_dispatch_ack_seq"] == 23
    assert result["native_cleanup_ack_seq"] == 36
    assert result["paper_dispatch_ack_marker_tick"] == 102
    assert result["paper_cleanup_ack_marker_tick"] == 112
    assert result["paper_sample_ticks_within_marker_window"] == 11
    assert result["native_single_reader"]
    assert not result["client_effect_world_tick_attested"]
    assert not result["cross_host_clock_synchronized"]


@pytest.mark.parametrize("fault", [
    "missing", "duplicate", "reversed", "different_world",
    "foreign_session", "wrong_dispatch_seq", "wrong_cleanup_seq",
    "before_arm", "after_release", "marker_implies_sync",
    "bad_source_receipt", "wrong_player",
])
def test_native_paper_effect_marker_corruption_denied(fault):
    native, bracket = original_source()
    lines = edge_rows()
    m0 = next(i for i, x in enumerate(lines) if "phase=APPLIED" in x)
    m1 = next(i for i, x in enumerate(lines) if "phase=CLEARED" in x)
    if fault == "missing":
        lines.pop(m0)
    elif fault == "duplicate":
        lines.insert(m0, lines[m0])
    elif fault == "reversed":
        lines[m0], lines[m1] = lines[m1], lines[m0]
    elif fault == "different_world":
        lines[m1] = lines[m1].replace(WORLD, PLAYER)
    elif fault == "foreign_session":
        lines[m0] = lines[m0].replace(SESSION, "foreign")
    elif fault == "wrong_dispatch_seq":
        lines[m0] = lines[m0].replace("native_seq=23", "native_seq=24")
    elif fault == "wrong_cleanup_seq":
        lines[m1] = lines[m1].replace("native_seq=36", "native_seq=35")
    elif fault == "before_arm":
        lines[m0] = lines[m0].replace("tick=102", "tick=99")
    elif fault == "after_release":
        lines[m1] = lines[m1].replace("tick=112", "tick=115")
    elif fault == "marker_implies_sync":
        lines[m0] = lines[m0].replace(
            "synchronized_native_effect_tick=false",
            "synchronized_native_effect_tick=true",
        )
    elif fault == "bad_source_receipt":
        native["cleanup_receipt"] = dict(native["cleanup_receipt"])
        native["cleanup_receipt"]["result"] = "rejected"
    else:
        lines[m0] = lines[m0].replace(PLAYER, WORLD)
    with pytest.raises(ForwardDashDevRejected):
        review_original_s49_native_effect_edges_dev(
            "\n".join(lines), action_id=ACTION, session_id=SESSION,
            native_evidence=native, bracket=bracket,
        )


def test_original_native_session_receives_each_effect_once_then_dev_callback():
    binding, _, _, issued = s17.issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding)
    seen = []

    async def observer(phase, ack):
        assert ack.result == "applied"
        seen.append((phase, ack.action_id, ack.seq))

    consequence = asyncio.run(execute_mineflayer_command(
        s17.successful_session(command), command,
        provenance=s17.provenance("native-edge-ack"),
        on_effect_ack_dev=observer,
    ))
    assert consequence.status is WorldConsequenceStatus.EXECUTED
    assert [(name, aid) for name, aid, _ in seen] == [
        ("APPLIED", command.action_id),
        ("CLEARED", command.cleanup_action_id),
    ]
    assert seen[0][-1] < seen[1][-1]


def test_native_ack_observer_failure_never_claims_successful_action():
    binding, _, _, issued = s17.issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding)

    async def reject(_phase, _ack):
        raise RuntimeError("Paper marker unavailable")

    consequence = asyncio.run(execute_mineflayer_command(
        s17.successful_session(command), command,
        provenance=s17.provenance("native-edge-marker-failed"),
        on_effect_ack_dev=reject,
    ))
    assert consequence.status is WorldConsequenceStatus.FAILED
    assert consequence.cleanup_attempted
    assert "Paper marker unavailable" in consequence.error
