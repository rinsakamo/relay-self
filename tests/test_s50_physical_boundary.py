"""Synthetic negative controls, never original World attestation."""

import asyncio
import copy

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import (
    BoundaryRejected,
    await_quiet,
    reconcile,
    verify_native,
)


def fixture(distance=1.2):
    marker = "action-session"

    def line(prefix, **fields):
        return prefix + " ".join(f"{k}={v}" for k, v in fields.items())

    out = []
    for phase, tick, x, packets in [
        ("PRE_FORWARD", 10, 0, 0),
        ("POST_FORWARD", 11, 0, 0),
        ("PRE_CLEAR", 17, distance / 2, 1),
        ("POST_CLEAR", 18, distance / 2, 1),
    ]:
        out.append(
            line(
                "M02_DEV_S50_PHASE ",
                marker_id=marker,
                phase=phase,
                world_full_time=tick,
                player_tick=tick,
                world="world",
                packets=packets if distance else 0,
                blocks=x,
                billed=x * 0.01,
                x=x,
                y=0,
                z=0,
            )
        )
    for i in range(1, 3) if distance else []:
        out.append(
            line(
                "M02_DEV_MOTION ",
                id=i,
                reason="WALK",
                blocks=distance / 2,
                billed=distance * 0.005,
                cumulative_blocks=distance * i / 2,
                cumulative_billed=distance * i * 0.005,
                from_x=distance * (i - 1) / 2,
                from_y=0,
                from_z=0,
                to_x=distance * i / 2,
                to_y=0,
                to_z=0,
                world_full_time=16 if i == 1 else 19,
                world="world",
                marker_id=marker,
            )
        )
    for t in range(11, 28):
        d = 0 if t <= 16 else distance / 2 if t <= 19 else distance
        packets = 0 if not distance or t <= 16 else 1 if t <= 19 else 2
        out.append(
            line(
                "S50_DEV_TICK ",
                marker_id=marker,
                world="world",
                tick=t,
                packets=packets,
                blocks=d,
                billed=d * 0.01,
                x=d,
                y=0,
                z=0,
            )
        )
    movement = dict(
        action_id="action",
        source_session="session",
        v7_phase_marker_id=marker,
        native_start_position=dict(x=0, y=0, z=0),
        native_target_position=dict(x=2, y=0, z=0),
        observed_progress_blocks=2 - abs(2 - distance),
    )
    return "\n".join(out), movement


@pytest.mark.parametrize("distance", [0, 0.4, 1, 1.2])
def test_realized_path_not_nominal_and_zero_move_not_wait(distance):
    content, move = fixture(distance)
    result = reconcile(content, move, walk_rate=0.01)
    assert result["native_horizontal_path_blocks"] == pytest.approx(distance)
    assert result["native_walk_exhaustion"] == pytest.approx(distance * 0.01)
    assert result["distance_after_post_clear_world_bracket_blocks"] == distance / 2
    assert result["wait_recovery_eligible_ticks"] == 0
    assert result["hard_one_block_cap"] == "NOT_GUARANTEED"


@pytest.mark.parametrize(
    "old,new",
    [
        ("tick=23 ", "tick=22 "),
        ("tick=23 ", "tick=24 "),
        ("world=world", "world=foreign"),
        ("marker_id=action-session", "marker_id=alien"),
        ("blocks=0.6 ", "blocks=0.7 "),
        ("billed=0.006 ", "billed=0.007 "),
        ("from_x=0.6 ", "from_x=0.5 "),
        ("id=2 ", "id=1 "),
        ("x=1.2 ", "x=1.3 "),
    ],
)
def test_corrupt_originals_fail_closed(old, new):
    content, move = fixture()
    assert old in content
    with pytest.raises(BoundaryRejected):
        reconcile(content.replace(old, new, 1), move, walk_rate=0.01)


def test_missing_tick_and_duplicate_event():
    content, move = fixture()
    for bad in [
        "\n".join(x for x in content.splitlines() if "tick=23 " not in x),
        content + "\n" + next(x for x in content.splitlines() if "M02_DEV_MOTION " in x),
    ]:
        with pytest.raises(BoundaryRejected):
            reconcile(bad, move, walk_rate=0.01)


def test_outcome_progress_and_action_mismatch():
    content, move = fixture()
    for key, value in [("observed_progress_blocks", 1), ("source_session", "alien")]:
        wrong = dict(move, **{key: value})
        with pytest.raises(BoundaryRejected):
            reconcile(content, wrong, walk_rate=0.01)


def test_unsettled_or_ended_world_blocks(tmp_path, monkeypatch):
    path = tmp_path / "world.log"
    content, move = fixture()
    path.write_text("\n".join(x for x in content.splitlines() if "S50_DEV_TICK " not in x))

    async def no_sleep(_):
        pass

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    with pytest.raises(BoundaryRejected):
        asyncio.run(await_quiet(path, move["v7_phase_marker_id"]))
    path.unlink()
    with pytest.raises(BoundaryRejected):
        asyncio.run(await_quiet(path, move["v7_phase_marker_id"]))


def native_fixture():
    move = dict(
        action_id="action",
        source_session="session",
        source_before_seq=0,
        look_seq=1,
        forward_seq=2,
        clear_seq=3,
        source_after_seq=4,
    )
    native = [dict(type="observation", request_id="before")]
    commands = []
    for aid, effect in [
        ("action-look", "look"),
        ("action", "set_control"),
        ("action-clear", "clear_controls"),
    ]:
        native.append(dict(type="effect_result", action_id=aid, effect=effect, result="applied"))
        commands.append(dict(type="effect", action_id=aid, effect=effect))
    commands[1].update(control="forward", state=True)
    native += [dict(type="observation", request_id="action-seek-after"), dict(type="shutdown_ack")]
    for i, r in enumerate(native):
        r.update(seq=i, session_id="session")
    return native, commands, move


def test_native_ack_chain():
    verify_native(*native_fixture())


@pytest.mark.parametrize(
    "fault",
    [
        "missing_ack",
        "wrong_action",
        "wrong_session",
        "clear_failed",
        "duplicate",
        "no_stop",
        "disconnect",
        "wrong_control",
    ],
)
def test_native_failures(fault):
    native, commands, move = copy.deepcopy(native_fixture())
    if fault == "missing_ack":
        native[2]["type"] = "observation"
    if fault == "wrong_action":
        native[2]["action_id"] = "alien"
    if fault == "wrong_session":
        native[3]["session_id"] = "alien"
    if fault == "clear_failed":
        native[3]["result"] = "rejected"
    if fault == "duplicate":
        native.append(native[2])
    if fault == "no_stop":
        native.pop()
    if fault == "disconnect":
        native[3]["type"] = "connection_end"
    if fault == "wrong_control":
        commands[1]["state"] = False
    with pytest.raises(BoundaryRejected):
        verify_native(native, commands, move)
