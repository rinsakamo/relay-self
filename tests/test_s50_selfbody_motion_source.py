"""S50 Paper/Node source -> SelfBody-candidate handoff; never physical truth."""
from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError

import pytest

from adapters.mineflayer.m02_paper_dev.s50_selfbody_motion_source import (
    S50BodyMotionSourceRejected,
    project_s50_body_motion_source,
)

SID = "3148d4a1-1a2a-4475-9f70-f3363a356be4"
ACTION = "s49-native-move-23"
MARKER = ACTION + "-" + SID
WORLD = "6cfb0817-fbe2-49f2-9b5e-bbf59f3a2e62"
UUID = "dcae346d-e66f-331a-b459-a5a5370e9738"
CONTROLS = ("forward", "back", "left", "right", "jump", "sneak", "sprint")


def paper(*, input_active: int = -1, broken_pose: int = -1) -> bytes:
    rows = []
    old_z = 1.7070768816725144
    deltas = [0.05903579322217567, 0.005210808286785218] + [0.0] * 6
    for index, delta in enumerate(deltas, 1):
        tick = 250 + index
        from_z = old_z + (0.01 if index == broken_pose else 0.0)
        new_z = old_z - delta
        rows.append(
            f"[INFO] S50_DEV_WAIT_TICK marker_id={MARKER} "
            f"world={WORLD} tick={tick} index={index} "
            f"from_x=-0.5 from_y=-60 from_z={from_z} "
            f"x=-0.5 y=-60 z={new_z} motion_packets=0"
        )
        flags = {
            "forward": "true" if tick == input_active else "false",
            "backward": "false", "left": "false", "right": "false",
            "jump": "false", "sneak": "false", "sprint": "false",
        }
        rows.append(
            f"[INFO] S50_DEV_INPUT_TICK marker_id={MARKER} world={WORLD} "
            f"subject_uuid={UUID} tick={tick} index={index} "
            "input_events=0 last_input_event_tick=-1 event_overflow=false "
            + " ".join(f"{k}={v}" for k, v in flags.items()) + " "
            "coverage=LAST_REPORTED_INPUT_CALLBACK_SAMPLE_ONLY "
            "effective_s15_clear_tick=NOT_ATTESTED"
        )
        old_z = new_z
    return ("\n".join(rows) + "\n").encode()


def client(*, missing_clear: bool = False, false_clear: bool = False) -> bytes:
    active = {k: (k == "back") for k in CONTROLS}
    inactive = {k: False for k in CONTROLS}
    rows = [
        {
            "revision": 1, "session_id": SID, "index": 1, "node_ns": "1000",
            "clock_scope": "NODE_ONLY", "server_world_tick": "NOT_OBSERVED",
            "source": "CLIENT_WRITE_RETURNED_NOT_NETWORK_DELIVERY",
            "kind": "PACKET_WRITE_RETURNED", "packet_index": 1,
            "packet_name": "position", "network_delivered": False,
            "paper_received": False,
        },
        {
            "revision": 1, "session_id": SID, "index": 2, "node_ns": "2000",
            "clock_scope": "NODE_ONLY", "server_world_tick": "NOT_OBSERVED",
            "source": "CLIENT_WRITE_RETURNED_NOT_NETWORK_DELIVERY",
            "kind": "NATIVE_CONTROL_EFFECT_RETURNED", "effect": "set_control",
            "controls_after_sample": active,
        },
        {
            "revision": 1, "session_id": SID, "index": 3, "node_ns": "3000",
            "clock_scope": "NODE_ONLY", "server_world_tick": "NOT_OBSERVED",
            "source": "CLIENT_WRITE_RETURNED_NOT_NETWORK_DELIVERY",
            "kind": "NATIVE_CONTROL_EFFECT_RETURNED",
            "effect": "set_control" if missing_clear else "clear_controls",
            "controls_after_sample": active if false_clear else inactive,
        },
    ]
    rows.append({
        "revision": 1, "kind": "TRACE_END",
        "complete": True, "lost": False, "recorded_rows": 3,
        "input_write_authority": False, "server_packet_received": False,
        "effective_s15_clear_tick": "NOT_ATTESTED",
    })
    return ("\n".join(json.dumps(row) for row in rows) + "\n").encode()


def l23(paper_bytes: bytes):
    return {
        "session_id": SID, "action_id": ACTION, "marker_id": MARKER,
        "paper_world": WORLD,
        "paper_original_sha256": hashlib.sha256(paper_bytes).hexdigest(),
        "paper_first_tick": 251, "paper_last_tick": 258,
        "paper_sample_count": 8, "paper_activity_ticks": [251, 252],
        "accepted_goal_status": "UNDETERMINED",
        "physical_stability_verified": False,
        "p1_wait_ticks_admitted": 0, "qualified_real_learning_pairs": 0,
    }


def project(paper_original=None, client_original=None, l23_source_readback=None):
    po = paper() if paper_original is None else paper_original
    co = client() if client_original is None else client_original
    return project_s50_body_motion_source(
        paper_original=po, client_original=co,
        l23_source_readback=l23(po) if l23_source_readback is None
        else l23_source_readback, session_id=SID, action_id=ACTION,
        world=WORLD, subject_uuid=UUID, first_tick=251,
    )


def test_paper_motion_after_local_clear_is_a_fallible_physical_diagnostic():
    view = project()
    assert view.schema == "S50_SELFBODY_MOTION_DIAGNOSTIC_V0"
    assert len(view.paper_samples) == 8
    assert view.observed_motion_while_reported_input_off_ticks == (251, 252)
    assert view.paper_samples[0].displacement_m > 0.05
    assert view.paper_samples[1].displacement_m > 0
    assert all(p.displacement_m == 0.0 for p in view.paper_samples[2:])
    assert [e.effect for e in view.client_effects] == [
        "set_control", "clear_controls",
    ]
    assert [e.local_controls_active for e in view.client_effects] == [True, False]
    assert view.client_player_input_write_returns == 0
    assert view.client_position_write_returns == 1
    assert view.paper_player_input_callbacks == 0
    assert view.client_packet_diagnostic == (
        "NO_PLAYER_INPUT_WRITE_ON_OBSERVED_CLIENT_PATH"
    )
    assert view.cross_clock_alignment == "NOT_ATTESTED"
    assert view.provenance_ceiling == "DIAGNOSTIC_ONLY_NOT_NATIVE_PRESENT"
    assert view.effective_s15_clear_world_tick == "NOT_ATTESTED"
    assert not view.physically_stopped_attested
    assert not view.full_tick_input_coverage
    assert not view.goal_admitted
    assert view.p1_wait_ticks_admitted == view.l10_pairs_admitted == 0
    assert view.s10_updates_admitted == view.s11_grants_admitted == 0
    with pytest.raises(FrozenInstanceError):
        view.physically_stopped_attested = True


def test_input_active_is_not_mistaken_for_physical_stillness():
    raw = paper(input_active=251)
    view = project(paper_original=raw, l23_source_readback=l23(raw))
    assert view.paper_samples[0].last_reported_input_active is True
    assert view.observed_motion_while_reported_input_off_ticks == (252,)
    assert not view.physically_stopped_attested


@pytest.mark.parametrize("fault", [
    "truncated_paper", "foreign_world", "wrong_uuid",
    "missing_input", "input_overflow", "discontinuous_pose",
    "nonfinite_pose", "nonconsecutive_tick", "wrong_l23_hash",
    "wrong_l23_goal", "false_l23_stability", "missing_clear",
    "false_clear", "truncated_client", "foreign_client",
    "mismatched_activity",
])
def test_reject_unreviewed_or_false_physical_source(fault):
    po, co = paper(), client()
    readback = l23(po)
    if fault == "truncated_paper":
        po = b"\n".join(po.splitlines()[:-2]) + b"\n"
    elif fault == "foreign_world":
        po = po.replace(WORLD.encode(), b"wrong-world", 1)
    elif fault == "wrong_uuid":
        po = po.replace(UUID.encode(), b"foreign-player", 1)
    elif fault == "missing_input":
        po = b"\n".join(row for row in po.splitlines()
            if b"S50_DEV_INPUT_TICK" not in row or b"index=5" not in row) + b"\n"
    elif fault == "input_overflow":
        po = po.replace(b"event_overflow=false", b"event_overflow=true", 1)
    elif fault == "discontinuous_pose":
        po = paper(broken_pose=3)
    elif fault == "nonfinite_pose":
        po = po.replace(b"x=-0.5", b"x=NaN", 1)
    elif fault == "nonconsecutive_tick":
        po = po.replace(b"tick=254 index=4", b"tick=260 index=4", 1)
    elif fault == "wrong_l23_hash":
        readback["paper_original_sha256"] = "0" * 64
    elif fault == "wrong_l23_goal":
        readback["accepted_goal_status"] = "REACHED"
    elif fault == "false_l23_stability":
        readback["physical_stability_verified"] = True
    elif fault == "missing_clear":
        co = client(missing_clear=True)
    elif fault == "false_clear":
        co = client(false_clear=True)
    elif fault == "truncated_client":
        co = b"\n".join(co.splitlines()[:-1]) + b"\n"
    elif fault == "foreign_client":
        co = co.replace(SID.encode(), b"foreign-session", 1)
    elif fault == "mismatched_activity":
        readback["paper_activity_ticks"] = []
    if fault in {
        "truncated_paper", "foreign_world", "wrong_uuid", "missing_input",
        "input_overflow", "discontinuous_pose", "nonfinite_pose",
        "nonconsecutive_tick",
    }:
        readback = l23(po)
    with pytest.raises((S50BodyMotionSourceRejected, ValueError)):
        project(paper_original=po, client_original=co, l23_source_readback=readback)
