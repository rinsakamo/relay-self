"""DEV-only fixed-pose Paper yaw readback: negative FORWARD admission tests."""
from __future__ import annotations

import asyncio
import math
from types import SimpleNamespace

import pytest

from adapters.mineflayer.m02_paper_dev import s50_p1_flat_look as subject
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected

MARKER = "m02-paper-walk-1-session-P1LOOK-01"
WORLD = "bba420a8-7943-465f-997e-e857e7587b93"


def original(*, yaw="-90.0", pitch="0.0", marker=MARKER,
             seed="63101", x="0.5", y="-60.0", z="0.5",
             full_time="23", world=WORLD):
    return (
        "[Server thread/INFO]: S_V8_DEV_SNAPSHOT "
        f"marker_id={marker} world={world} seed={seed} "
        f"full_time={full_time} player_tick=8 "
        f"x={x} y={y} z={z} yaw={yaw} pitch={pitch} "
        "food=20 saturation=5 health=20 exhaustion=0 "
        "basal_requested=0.008 motion_blocks=0 motion_billed=0"
    )


def check(**changes):
    return subject.check_snapshot(
        original(**changes), marker_id=MARKER,
        expected_yaw_rad=-math.pi/2, world=WORLD, previous_tick=22,
    )


def test_real_paper_degrees_match_existing_native_look_radians():
    result = check()
    assert result["orientation_matches"] is True
    assert result["yaw_gap_degrees"] == pytest.approx(0.0)
    assert result["paper_full_time"] == 23
    assert result["look_requested_yaw_degrees"] == pytest.approx(-90)
    assert result["P1_fatigue_recovered"] == 0
    assert result["real_move_authorized_by_this_snapshot"] is False
    assert result["later_forward_server_effective_tick"] == "NOT_ATTESTED"


@pytest.mark.parametrize("yaw", [
    "0", "-83", "45", "180", "NaN", "inf", "-inf",
])
def test_previous_blocked_yaw_and_fake_numbers_not_eligible(yaw):
    if yaw in ("NaN", "inf", "-inf"):
        with pytest.raises(BoundaryRejected):
            check(yaw=yaw)
    else:
        assert check(yaw=yaw)["orientation_matches"] is False


@pytest.mark.parametrize("change", [
    {"seed": "62101"}, {"marker": "foreign"}, {"world": "other"},
    {"x": "0.65"}, {"z": "1.707742656099451"}, {"y": "-59.8"},
    {"pitch": "14.5"}, {"full_time": "21.0"},
    {"full_time": "-1"}, {"full_time": "nan"}, {"x": "nan"},
])
def test_spoofed_or_moved_paper_pose_never_proves_look(change):
    if set(change) == {"pitch"}:
        assert check(**change)["orientation_matches"] is False
    else:
        with pytest.raises(BoundaryRejected):
            check(**change)


def test_regressed_clock_and_duplicate_original_fields_rejected():
    with pytest.raises(BoundaryRejected):
        subject.check_snapshot(
            original(full_time="22"), marker_id=MARKER,
            expected_yaw_rad=-math.pi/2, world=WORLD, previous_tick=23,
        )
    with pytest.raises(BoundaryRejected, match="duplicate"):
        subject.check_snapshot(
            original() + " yaw=-90.0", marker_id=MARKER,
            expected_yaw_rad=-math.pi/2, world=WORLD, previous_tick=22,
        )


def test_bounded_existing_paper_command_only_never_generates_forward(
    tmp_path, monkeypatch,
):
    log = tmp_path / "paper_server.log"
    log.write_text("")
    commands = []

    def emit(_server, command):
        commands.append(command)
        marker = command.split(" ", 1)[1]
        with log.open("a") as out:
            out.write(original(marker=marker, yaw="0" if len(commands) == 1
                               else "-90") + "\n")

    async def drain():
        return None

    monkeypatch.setattr(subject, "_command", emit)
    server = SimpleNamespace(returncode=None, stdin=SimpleNamespace(drain=drain))
    witness = asyncio.run(subject.await_paper_look_before_forward(
        server, log, marker="m02-paper-walk-1-session",
        expected_yaw_rad=-math.pi/2,
    ))
    assert witness["orientation_matches"] is True
    assert witness["source_snapshots_checked"] == 2
    assert len(commands) == 2
    assert all(cmd.startswith("relaydevsnapshot ") for cmd in commands)


def test_no_paper_yaw_never_proceeds_to_motor_control(tmp_path, monkeypatch):
    log = tmp_path / "paper_server.log"
    log.write_text("")
    commands = []

    def emit(_server, command):
        commands.append(command)
        marker = command.split(" ", 1)[1]
        with log.open("a") as out:
            out.write(original(marker=marker, yaw="0") + "\n")

    async def drain():
        return None

    monkeypatch.setattr(subject, "_command", emit)
    server = SimpleNamespace(returncode=None, stdin=SimpleNamespace(drain=drain))
    with pytest.raises(BoundaryRejected, match="LOOK_ACK_WITHOUT_PAPER_EFFECTIVE_YAW"):
        asyncio.run(subject.await_paper_look_before_forward(
            server, log, marker="m02-paper-walk-1-session",
            expected_yaw_rad=-math.pi/2,
        ))
    assert len(commands) == subject.MAX_SNAPSHOTS
    assert all(cmd.startswith("relaydevsnapshot ") for cmd in commands)

def test_flat_p1_look_is_child_only_and_cleaned_up(monkeypatch):
    monkeypatch.delenv(subject.FLAT_LOOK_ENV, raising=False)
    with subject.single_flat_p1_child_look_launch(eligible=True):
        assert subject.FLAT_LOOK_ENV in __import__("os").environ
        assert __import__("os").environ[subject.FLAT_LOOK_ENV] == "1"
        with pytest.raises(BoundaryRejected):
            with subject.single_flat_p1_child_look_launch(eligible=True):
                pass
    assert subject.FLAT_LOOK_ENV not in __import__("os").environ
    with pytest.raises(BoundaryRejected):
        with subject.single_flat_p1_child_look_launch(eligible=False):
            pass
    monkeypatch.setenv(subject.FLAT_LOOK_ENV, "FOREIGN")
    with pytest.raises(BoundaryRejected):
        with subject.single_flat_p1_child_look_launch(eligible=True):
            pass
    assert __import__("os").environ[subject.FLAT_LOOK_ENV] == "FOREIGN"


def test_failed_child_launch_always_unsets_force_flag(monkeypatch):
    monkeypatch.delenv(subject.FLAT_LOOK_ENV, raising=False)
    with pytest.raises(RuntimeError, match="spawn failed"):
        with subject.single_flat_p1_child_look_launch(eligible=True):
            raise RuntimeError("spawn failed")
    assert subject.FLAT_LOOK_ENV not in __import__("os").environ
