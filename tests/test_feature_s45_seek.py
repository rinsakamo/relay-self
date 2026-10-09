"""S45 target-local SEEK step unit tests; no World movement claimed."""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_postmain_s42_world_contrast as s42
from adapters.mineflayer.python_protocol import MineflayerPosition
from relay_self.seek_waypoint import SeekCursor, SeekRejected, SeekStatus, SeekWaypoint


def test_seek_step_is_bounded_and_world_sourced():
    _, near, _, _, _ = s42._pair()
    probe = near.observation
    pos = probe.snapshot.position
    goal = SeekWaypoint("go-east", MineflayerPosition(pos.x + 5, pos.y, pos.z))
    cursor = SeekCursor(probe.session_id)
    step = cursor.plan(probe, goal)
    assert step.status is SeekStatus.STEER
    assert step.step_distance_m == 1.0
    assert step.session_id == probe.session_id and step.yaw is not None
    with pytest.raises(SeekRejected):
        cursor.plan(probe, goal)


def test_seek_arrival_and_height_gap_do_not_move():
    _, near, _, _, _ = s42._pair()
    probe = near.observation
    pos = probe.snapshot.position
    nearby = SeekWaypoint("arrived", MineflayerPosition(pos.x + 0.2, pos.y, pos.z))
    tall = SeekWaypoint("cliff", MineflayerPosition(pos.x + 4, pos.y + 5, pos.z))
    a = SeekCursor(probe.session_id).plan(probe, nearby)
    b = SeekCursor(probe.session_id).plan(probe, tall)
    assert a.status is SeekStatus.ARRIVED and a.step_distance_m == 0
    assert b.status is SeekStatus.NEEDS_ROUTE and b.yaw is None


@pytest.mark.parametrize("bad", ("wrong-session", "not-probe", "missing-request"))
def test_seek_fails_closed(bad):
    _, near, _, _, _ = s42._pair()
    probe = near.observation
    pos = probe.snapshot.position
    goal = SeekWaypoint("g", MineflayerPosition(pos.x + 2, pos.y, pos.z))
    if bad == "wrong-session":
        probe = replace(probe, session_id="other")
    elif bad == "not-probe":
        probe = replace(probe, kind="entities", request_id=None)
    else:
        probe = replace(probe, request_id=None)
    with pytest.raises(SeekRejected):
        SeekCursor(near.observation.session_id).plan(probe, goal)
