"""S50 #627: passive packet witness cannot secretly grant motor or WAIT."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.m02_paper_dev.s50_p1_packet_trace import review_s50_packet_trace

SESSION = "s50-native-session-001"
PACKET_SOURCE = "S50_DEV_PASSIVE_PACKET_V1"


def rows():
    packet = {
        "shape_valid": True, "x": 0.5, "y": -60, "z": 0.5,
        "yaw": 0, "pitch": 0, "teleportId": 9, "flags": {"yaw": False},
    }
    source = [
        {"kind": "SESSION_START", "native_seq": 0},
        {"kind": "PACKET_IN_BEFORE", "packet_name": "position",
         "packet_fields": packet, "client_yaw_radians": 0.0,
         "client_pitch_radians": 0.0},
        {"kind": "PACKET_OUT", "packet_name": "teleport_confirm",
         "packet_fields": {"shape_valid": True, "teleportId": 9},
         "client_yaw_radians": 3.14159, "client_pitch_radians": 0.0},
        {"kind": "PACKET_IN_AFTER", "packet_name": "position",
         "packet_fields": packet, "client_yaw_radians": 3.14159,
         "client_pitch_radians": 0.0},
        {"kind": "CLIENT_PHYSICS_TICK", "client_yaw_radians": 3.14159,
         "client_pitch_radians": 0.0, "client_physics_tick": 1},
        {"kind": "NATIVE_EFFECT_ACK", "native_seq": 5,
         "native_action_id": "move-1-look", "effect": "look", "result": "applied",
         "client_yaw_radians": -1.570796, "client_pitch_radians": 0.0},
        {"kind": "PACKET_OUT", "packet_name": "look",
         "packet_fields": {"shape_valid": True, "yaw": 270, "pitch": 0},
         "client_yaw_radians": -1.570796, "client_pitch_radians": 0.0},
        {"kind": "SHUTDOWN_ACK", "native_seq": 7,
         "client_yaw_radians": -1.570796, "client_pitch_radians": 0.0},
    ]
    for i, row in enumerate(source, 1):
        row.update({
            "source": PACKET_SOURCE, "ordinal": i,
            "session_id": SESSION,
        })
        row.setdefault("client_physics_tick", 1 if i >= 5 else 0)
    return source


def audit(source):
    return review_s50_packet_trace(
        "\n".join(json.dumps(row) for row in source)
    )


def test_source_order_and_client_correction_without_paper_qualification():
    result = audit(rows())
    assert result["packet_inbound_callbacks"] == 1
    assert result["packet_outbound_writes_observed"] == 2
    assert result["client_physics_callbacks"] == 1
    assert result["correction_callbacks"][0]["teleport_id"] == 9
    assert result["correction_callbacks"][0]["before_client_pose"][0] == 0
    assert result["correction_callbacks"][0]["after_client_pose"][0] == 3.14159
    assert result["native_effect_acks"][0]["effect"] == "look"
    assert result["shutdown_ack_seen"] is True
    assert result["source_bytes_authenticated"] is False
    assert result["setup_teleport_settled"] is False
    assert result["runtime_owner_handoff_admitted"] is False
    assert result["source_packet_delivery_to_server"] == "NOT_ATTESTED"
    assert result["P1_SourceBoundTick_WAIT"] == 0
    assert result["self_feedback_delivered"] is False


@pytest.mark.parametrize(("index", "field", "value"), [
    (0, "session_id", "alien"),
    (0, "native_seq", 1),
    (2, "source", "fake"),
    (2, "ordinal", 5),
    (1, "packet_name", "set_control"),
    (1, "kind", "PACKET_IN_AFTER"),
    (3, "packet_name", "player_rotation"),
    (3, "client_physics_tick", 22),
    (5, "client_physics_tick", 0),
    (5, "native_seq", 0),
    (5, "result", "impossible"),
    (6, "packet_name", "attack_entity"),
    (7, "kind", "PACKET_OUT"),
])
def test_forged_packet_sequence_rejected(index, field, value):
    source = copy.deepcopy(rows())
    source[index][field] = value
    with pytest.raises(BoundaryRejected):
        audit(source)


def test_missing_rotation_correction_or_duplicate_keys_fail_closed():
    source = rows()
    source.pop(3)
    for i, row in enumerate(source, 1):
        row["ordinal"] = i
    with pytest.raises(BoundaryRejected):
        audit(source)
    source = rows()
    source[1]["packet_fields"] = {"shape_valid": False}
    with pytest.raises(BoundaryRejected):
        audit(source)
    original = "\n".join(json.dumps(row) for row in rows())
    with pytest.raises(BoundaryRejected):
        review_s50_packet_trace(original.replace(
            '"ordinal": 1', '"ordinal": 1, "ordinal": 1', 1
        ))


def test_packet_duplicate_client_tick_and_unexpected_mutation_fail_closed():
    source = rows()
    source[4]["client_physics_tick"] = 3
    with pytest.raises(BoundaryRejected):
        audit(source)
    source = rows()
    source[3]["packet_fields"] = {
        **source[3]["packet_fields"], "yaw": 45,
    }
    with pytest.raises(BoundaryRejected):
        audit(source)
    source = rows()
    source[6]["packet_fields"]["yaw"] = float("nan")
    with pytest.raises(BoundaryRejected):
        audit(source)


def test_direct_node_packet_forwarding_negative_controls():
    executable = shutil.which("node")
    if executable is None:
        pytest.skip("Node not on this offline test host")
    test_file = (
        Path(__file__).resolve().parents[1] / "adapters" / "mineflayer"
        / "m02_paper_dev" / "s50_p1_packet_trace.test.mjs"
    )
    run = subprocess.run(
        [executable, "--test", str(test_file)], capture_output=True,
        text=True, timeout=30, check=False,
    )
    assert run.returncode == 0, run.stdout + run.stderr
