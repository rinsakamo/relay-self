"""FLAT-only direct client LOOK yaw readback: NEVER Paper-effective or P1 WAIT."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.m02_paper_dev.s50_p1_native_pose import (
    read_client_look_pose,
)

SESSION = "be9aa263-afac-4b17-945b-09eef6c47126"
ACTION = "m02-paper-walk-1"
SOURCE = "S50_DEV_NATIVE_READBACK_V1"


def rows():
    base = {"source": SOURCE, "session_id": SESSION}
    def row(kind, ordinal, tick, *, seq=None, action=None, yaw=None, pitch=0):
        item = dict(base, kind=kind, ordinal=ordinal, client_physics_tick=tick)
        if seq is not None:
            item["native_seq"] = seq
        if action is not None:
            item["native_action_id"] = action
        if yaw is not None:
            item["client_yaw_radians"] = yaw
            item["client_pitch_radians"] = pitch
        return item
    return [
        row("SESSION_START", 1, 0, seq=0),
        row("PHYSICS_TICK", 2, 1, yaw=0),
        row("EFFECT_ACK", 3, 1, seq=7, action=ACTION + "-look",
            yaw=-math.pi / 2),
        row("PHYSICS_TICK", 4, 2, yaw=-math.pi / 2),
    ]


def write(path, records):
    path.write_text("\n".join(json.dumps(x, allow_nan=True) for x in records)+"\n")


def review(path: Path):
    return read_client_look_pose(
        path, session_id=SESSION, action_id=ACTION,
        requested_yaw_rad=-math.pi / 2,
    )


def test_native_look_ack_yaw_is_not_paper_yaw(tmp_path):
    source = tmp_path / "s50_p1_native_controls_original.jsonl"
    write(source, rows())
    result = review(source)
    assert result["look_ack_native_seq"] == 7
    assert result["look_ack_client_physics_tick"] == 1
    assert result["native_client_yaw_radians"] == pytest.approx(-math.pi / 2)
    assert result["yaw_gap_radians"] == pytest.approx(0)
    assert result["source_rows_at_review"] == 4
    assert result["paper_effective_yaw"] == "SEPARATE_PAPER_SOURCE_REQUIRED"
    assert result["server_effective_input_tick"] == "NOT_ATTESTED"
    assert result["P1_SourceBoundTick_WAIT_issued"] == 0
    assert result["P1_fatigue_recovered"] == 0.0
    assert not result["science_go"]
    # Later owner ACK/STOP rows do not rewrite the stable early LOOK witness.
    later = rows() + [{
        "source": SOURCE, "session_id": SESSION, "kind": "EFFECT_ACK",
        "ordinal": 5, "client_physics_tick": 2, "native_seq": 8,
        "native_action_id": ACTION, "client_yaw_radians": -math.pi / 2,
        "client_pitch_radians": 0,
    }]
    write(source, later)
    again = review(source)
    assert again["native_client_yaw_radians"] == result["native_client_yaw_radians"]
    assert again["look_ack_native_seq"] == result["look_ack_native_seq"]
    assert again["source_rows_at_review"] == 5


@pytest.mark.parametrize("change", [
    "yaw_zero", "yaw_reverse", "pitch_wrong", "yaw_nan", "yaw_bool",
    "missing_yaw", "missing_pitch", "wrong_session", "missing_look",
    "duplicate_look", "wrong_action", "wrong_ack_kind",
    "look_not_first_effect", "bad_seq", "bad_ordinal", "bad_source",
    "regressed_tick", "missing_session_start", "duplicate_json_key",
])
def test_malformed_or_fake_client_look_is_never_forward_admitted(tmp_path, change):
    original = rows()
    data = copy.deepcopy(original)
    look = data[2]
    if change == "yaw_zero":
        look["client_yaw_radians"] = 0
    elif change == "yaw_reverse":
        look["client_yaw_radians"] = math.pi / 2
    elif change == "pitch_wrong":
        look["client_pitch_radians"] = .2
    elif change == "yaw_nan":
        look["client_yaw_radians"] = math.nan
    elif change == "yaw_bool":
        look["client_yaw_radians"] = True
    elif change == "missing_yaw":
        del look["client_yaw_radians"]
    elif change == "missing_pitch":
        del look["client_pitch_radians"]
    elif change == "wrong_session":
        look["session_id"] = "foreign"
    elif change == "missing_look":
        data.pop(2)
        data[2]["ordinal"] = 3
    elif change == "duplicate_look":
        data.append(dict(look, ordinal=5, client_physics_tick=2))
    elif change == "wrong_action":
        look["native_action_id"] = "other-look"
    elif change == "wrong_ack_kind":
        look["kind"] = "PROBE"
    elif change == "look_not_first_effect":
        data.insert(2, dict(look, ordinal=3, native_action_id="foreign"))
        for i, row in enumerate(data, 1):
            row["ordinal"] = i
    elif change == "bad_seq":
        look["native_seq"] = 0
    elif change == "bad_ordinal":
        look["ordinal"] = 13
    elif change == "bad_source":
        look["source"] = "fake"
    elif change == "regressed_tick":
        look["client_physics_tick"] = 0
    elif change == "missing_session_start":
        data.pop(0)
        for i, row in enumerate(data, 1):
            row["ordinal"] = i
    path = tmp_path / "original_native_pose.jsonl"
    write(path, data)
    if change == "duplicate_json_key":
        raw = path.read_text()
        raw = raw.replace('"native_seq": 7', '"native_seq": 7, "native_seq": 7')
        path.write_text(raw)
    with pytest.raises(BoundaryRejected):
        review(path)


def test_untrusted_nonfile_and_symlink_refused(tmp_path):
    path = tmp_path / "native.jsonl"
    with pytest.raises(BoundaryRejected):
        review(path)
    other = tmp_path / "other.jsonl"
    write(other, rows())
    path.symlink_to(other)
    with pytest.raises(BoundaryRejected):
        review(path)


def test_paper_and_native_pose_gates_are_sequential(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source = (root / "adapters" / "mineflayer" / "m02_paper_dev" /
              "s51_paper_physics_dev.py").read_text()
    phase = source.split("async def phase_hook(phase: str)", 1)[1]
    assert phase.index("read_client_look_pose(") < phase.index(
        "await_paper_look_before_forward(")
    assert phase.index("await_paper_look_before_forward(") < phase.index(
        "_v7_source_phase_command(")
    assert "p1_flat_client_look_before_forward" in source
    wrapper = (root / "adapters" / "mineflayer" / "m02_paper_dev" /
               "s50_p1_readback_bridge.mjs").read_text()
    assert "RELAY_S50_P1_FLAT_FORCE_SERVER_LOOK_DEV" in wrapper
    assert "bot.entity.yaw" in wrapper and "bot.entity.pitch" in wrapper
