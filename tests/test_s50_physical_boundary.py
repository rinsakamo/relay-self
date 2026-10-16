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
        "duplicate_new_seq",
        "extra_move",
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
    if fault == "duplicate_new_seq":
        native.append(dict(native[2], seq=len(native)))
    if fault == "extra_move":
        commands.append(dict(type="effect", action_id="other-move", effect="set_control"))
    with pytest.raises(BoundaryRejected):
        verify_native(native, commands, move)


@pytest.mark.parametrize("failure", ["forward_ack", "gate", "settle", "clear_ack", "none"])
def test_executor_release_and_outcome_order(failure):
    from dataclasses import replace
    from types import SimpleNamespace

    import test_feature_s46_eat as s46
    from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import _issue
    from adapters.mineflayer.process_session import MineflayerProcessSession
    from adapters.mineflayer.python_protocol import MineflayerEffectResult, MineflayerPosition
    from adapters.mineflayer.seek_execution import execute_seek_step
    from relay_self.action import ActionState
    from relay_self.action_supervision import ActionSupervisor
    from relay_self.seek_waypoint import SeekCursor, SeekWaypoint

    before = s46.case()
    position = before.snapshot.position
    step = SeekCursor(before.session_id).plan(
        before, SeekWaypoint("goal", MineflayerPosition(position.x + 2, position.y, position.z))
    )
    supervisor = ActionSupervisor()
    issued = _issue(supervisor, "move", "seek", "intent", "DEV synthetic", time_base=10)
    events = []

    class Session(MineflayerProcessSession):
        def __init__(self):
            self.pending = []
            self.next_seq = before.seq + 1

        @property
        def started(self):
            return SimpleNamespace(session_id=before.session_id)

        @property
        def process_returncode(self):
            return None

        async def receive(self):
            row = self.pending.pop(0)
            if isinstance(row, Exception):
                raise row
            return row

        def ack(self, aid, effect, fail=False):
            self.pending.append(
                TimeoutError("lost ACK")
                if fail
                else MineflayerEffectResult(
                    before.session_id, self.next_seq, aid, effect, "applied", None
                )
            )
            self.next_seq += 1

        async def send_look(self, aid, **kwargs):
            self.ack(aid, "look")

        async def send_set_control(self, aid, **kwargs):
            events.append("forward")
            self.ack(aid, "set_control", failure == "forward_ack")

        async def send_clear_controls(self, aid):
            events.append("clear")
            self.ack(aid, "clear_controls", failure == "clear_ack")

        async def send_observe(self, rid):
            events.append("probe")
            self.pending.append(replace(before, seq=self.next_seq, request_id=rid))

    async def phase(name):
        events.append(name)

    async def gate():
        if failure == "gate":
            raise TimeoutError("lost World gate")

    async def settle():
        events.append("settle")
        if failure == "settle":
            raise BoundaryRejected("no physical quiet")

    work = execute_seek_step(
        Session(),
        supervisor,
        issued,
        step,
        phase_hook=phase,
        tick_gate_hook=gate,
        settle_hook=settle,
    )
    if failure == "none":
        asyncio.run(work)
        assert events.index("clear") < events.index("settle") < events.index("probe")
    else:
        with pytest.raises((TimeoutError, BoundaryRejected)):
            asyncio.run(work)
        assert "probe" not in events
    assert events.count("forward") == events.count("clear") == 1
    # Only the caller may close lifecycle, never this motor primitive.
    assert supervisor.get("move").state is ActionState.ISSUED


def test_native_small_tail_is_diagnosed_never_repaired():
    from adapters.mineflayer.m02_paper_dev.s50_boundary import diagnose_motion

    content, move = fixture()
    lines = [
        line.replace(" x=1.2 ", " x=1.2088 ") if "S50_DEV_TICK " in line else line
        for line in content.splitlines()
    ]
    content = "\n".join(lines)
    result = diagnose_motion(content, move["v7_phase_marker_id"])
    assert result["event_metered_horizontal_path_blocks"] == 1.2
    assert result["endpoint_displacement_blocks"] == 1.2088
    assert result["unmetered_travel_lower_bound_blocks"] == pytest.approx(0.0088)
    assert result["body_boundary"] == "BLOCKED"
    with pytest.raises(BoundaryRejected):
        reconcile(content, move, walk_rate=0.01)


def test_saved_original_hash_mutation_is_rejected(tmp_path):
    import hashlib
    import json

    from adapters.mineflayer.m02_paper_dev.s50_boundary import diagnose_bundle

    content, _ = fixture()
    native, commands, _ = native_fixture()
    native[0]["request_id"] = "m02-before-walk"
    native[0]["snapshot"] = dict(position=dict(x=0, y=0, z=0))
    native[4]["snapshot"] = dict(position=dict(x=1.2, y=0, z=0))
    events = [dict(state=s) for s in ["proposed", "authorized", "issued"]]
    journal = [
        dict(action_id="action", session_id="session", state="issued", events=events),
        dict(
            action_id="action",
            session_id="session",
            state="unknown",
            events=events + [dict(state="unknown")],
        ),
    ]

    def jsonl(items):
        return "".join(json.dumps(r) + "\n" for r in items)

    sources = {
        "paper_server.log": content,
        "s50_action_original.jsonl": jsonl(journal),
        "original_native.jsonl": jsonl(native),
        "owner_commands.jsonl": jsonl(commands),
    }
    hashes = {}
    for name, text in sources.items():
        (tmp_path / name).write_text(text)
        hashes[name] = hashlib.sha256(text.encode()).hexdigest()
    from adapters.mineflayer.m02_paper_dev.v7_paired_config import TEMPLATE, render_arm

    config_sha = hashlib.sha256(render_arm(TEMPLATE.read_bytes(), "BASE_ON")).hexdigest()
    (tmp_path / "m02_report.json").write_text(
        json.dumps(
            dict(
                source_session_id="session",
                v7_arm="BASE_ON",
                evidence_hashes=hashes,
                plugin_config_sha256=config_sha,
            )
        )
    )
    assert diagnose_bundle(tmp_path)["original_terminal"] == "unknown"
    with (tmp_path / "paper_server.log").open("a") as stream:
        stream.write("changed")
    with pytest.raises(BoundaryRejected, match="hash mismatch"):
        diagnose_bundle(tmp_path)


def _tick_meter_fixture():
    """Synthetic straight +X; event meter misses 0.0088 native displacement."""
    old, movement = fixture(1.2)
    marker = "action-session"
    path = 1.2088
    lines = []
    for row in old.splitlines():
        if "M02_DEV_MOTION " in row:
            row = row.replace("billed=0.006", "billed=0.0")
            row = row.replace("cumulative_billed=0.006", "cumulative_billed=0.0")
            row = row.replace("cumulative_billed=0.012", "cumulative_billed=0.0")
        if "S50_DEV_TICK " in row:
            tick = int(row.split("tick=")[1].split()[0])
            original_x = 0 if tick <= 16 else 0.6 if tick <= 19 else 1.2
            value = 0 if tick <= 16 else 0.6 if tick <= 19 else path
            row = row.replace(f" x={original_x} ", f" x={value} ")
            row = row.replace(f"billed={original_x * .01}", "billed=0.0")
            row = row.replace("billed=0.006", "billed=0.0")
            row = row.replace("billed=0.012", "billed=0.0")
            row += (f" tick_meter_blocks={value}"
                    f" tick_meter_billed={value * .01}")
        if "M02_DEV_S50_PHASE " in row:
            row = row.replace("billed=0.006", "billed=0.0")
            row = row.replace("billed=0.012", "billed=0.0")
        lines.append(row)
    lines.append(
        "S50_DEV_TICK_METER_ARM marker_id=action-session world=world "
        "world_full_time=10 x=0 y=0 z=0"
    )
    last = 0.0
    for i, tick in enumerate(range(11, 28), 1):
        current = 0.0 if tick <= 16 else 0.6 if tick <= 19 else path
        blocks = current - last
        charge = blocks * .01
        lines.append(
            f"S50_DEV_TICK_MOTION id={i} marker_id={marker} world=world "
            f"world_full_time={tick} from_x={last} from_y=0 from_z=0 "
            f"to_x={current} to_y=0 to_z=0 blocks={blocks} billed={charge} "
            f"cumulative_blocks={current} cumulative_billed={current * .01} "
            f"write_before=0.1 write_target={0.1 + charge} "
            f"write_after={0.1 + charge}"
        )
        last = current
    movement["observed_progress_blocks"] = path
    return "\n".join(lines), movement


def test_dev_tick_meter_covers_previous_event_tail_without_double_billing():
    from adapters.mineflayer.m02_paper_dev.s50_boundary import reconcile_tick_meter

    source, movement = _tick_meter_fixture()
    result = reconcile_tick_meter(source, movement, walk_rate=.01)
    assert result["native_horizontal_path_blocks"] == pytest.approx(1.2088)
    assert result["native_walk_exhaustion"] == pytest.approx(.012088)
    assert result["native_event_observed_blocks_not_billed"] == pytest.approx(1.2)
    assert result["observed_tick_motion_source"]["native_event_double_billing_prevented"]
    assert result["sub_tick_path"] == "NOT_ATTESTED"
    assert result["wait_recovery_eligible_ticks"] == 0


@pytest.mark.parametrize("bad", [
    "missing-arm", "missing-tick", "duplicate-tick", "bad-id",
    "foreign-session", "foreign-world", "overbilling", "wrong-pose",
    "wrong-accumulation", "wrong-writer", "event-double-bill",
    "truncated-source", "wrong-Action-progress",
])
def test_dev_tick_meter_negative_controls(bad):
    from adapters.mineflayer.m02_paper_dev.s50_boundary import reconcile_tick_meter

    source, movement = _tick_meter_fixture()
    lines = source.splitlines()
    if bad == "missing-arm":
        lines = [x for x in lines if not x.startswith("S50_DEV_TICK_METER_ARM ")]
    if bad == "missing-tick":
        lines = [x for x in lines if not ("S50_DEV_TICK_MOTION " in x and "world_full_time=15 " in x)]
    if bad == "duplicate-tick":
        lines += [next(x for x in lines if x.startswith("S50_DEV_TICK_MOTION "))]
    if bad == "bad-id":
        lines = [x.replace("id=2 ", "id=3 ", 1) if x.startswith("S50_DEV_TICK_MOTION id=2 ") else x for x in lines]
    if bad == "foreign-session":
        lines = [x.replace("marker_id=action-session", "marker_id=foreign", 1)
                 if x.startswith("S50_DEV_TICK_MOTION ") else x for x in lines]
    if bad == "foreign-world":
        lines = [x.replace("world=world", "world=foreign", 1)
                 if x.startswith("S50_DEV_TICK_MOTION ") else x for x in lines]
    if bad == "overbilling":
        lines = [x.replace("billed=0.006 ", "billed=0.007 ", 1)
                 if x.startswith("S50_DEV_TICK_MOTION ") else x for x in lines]
    if bad == "wrong-pose":
        lines = [x.replace("to_x=0.6", "to_x=0.7", 1)
                 if "S50_DEV_TICK_MOTION " in x else x for x in lines]
    if bad == "wrong-accumulation":
        lines = [x.replace("cumulative_blocks=0.6", "cumulative_blocks=0.7", 1)
                 if "S50_DEV_TICK_MOTION " in x else x for x in lines]
    if bad == "wrong-writer":
        lines = [x.replace("write_target=0.106", "write_target=0.107", 1)
                 if "S50_DEV_TICK_MOTION " in x else x for x in lines]
    if bad == "event-double-bill":
        lines = [x.replace("billed=0.0 ", "billed=0.006 ", 1)
                 if x.startswith("M02_DEV_MOTION ") else x for x in lines]
    if bad == "truncated-source":
        lines = [x for x in lines if not ("S50_DEV_TICK_MOTION " in x and "world_full_time=27 " in x)]
    if bad == "wrong-Action-progress":
        movement["observed_progress_blocks"] = 1.2
    with pytest.raises(BoundaryRejected):
        reconcile_tick_meter("\n".join(lines), movement, walk_rate=.01)


def test_native_tick_writer_can_sample_in_pre_forward_world_tick():
    """Paper may process PRE_FORWARD command before its own scheduler in same tick."""
    from adapters.mineflayer.m02_paper_dev.s50_boundary import reconcile_tick_meter

    source, movement = _tick_meter_fixture()
    converted = []
    for row in source.splitlines():
        if row.startswith("S50_DEV_TICK_MOTION "):
            first = row.split(" ", 2)[1]
            index = int(first.split("=")[1])
            row = row.replace("S50_DEV_TICK_MOTION id=" + str(index) + " ",
                              "S50_DEV_TICK_MOTION id=" + str(index + 1) + " ", 1)
        converted.append(row)
    converted.insert(
        next(i for i, row in enumerate(converted)
             if row.startswith("S50_DEV_TICK_MOTION ")),
        "S50_DEV_TICK_MOTION id=1 marker_id=action-session world=world "
        "world_full_time=10 from_x=0 from_y=0 from_z=0 to_x=0 to_y=0 to_z=0 "
        "blocks=0 billed=0 cumulative_blocks=0 cumulative_billed=0 "
        "write_before=0.1 write_target=0.1 write_after=0.1"
    )
    result = reconcile_tick_meter("\n".join(converted), movement, walk_rate=0.01)
    assert result["native_horizontal_path_blocks"] == pytest.approx(1.2088)
    assert result["observed_tick_motion_source"]["source_rows"] == 18
