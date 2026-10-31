"""L16 synthetic process-bound S7 capture and first S49 Action Goal window."""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace

import pytest

import test_l15_s49_original_goal_preflight as l15
from adapters.mineflayer.l16_first_action_goal_originals import (
    L16GoalPlan,
    L16SourceRejected,
    inspect_l16_first_action_prefix,
)
from adapters.mineflayer.process_session import (
    MineflayerProcessIOError,
    MineflayerProcessSession,
)
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from adapters.mineflayer.self_s7_native_receipt import NativeStreamReceipt
from test_mineflayer_process_session import FakeProcess


def fixture():
    args = l15.s49_original_source()
    criterion = json.loads(args["external_criterion_original"])
    plan = L16GoalPlan(
        criterion["target_x"], criterion["target_z"],
        criterion["tolerance_m"], criterion["stable_probe_delta_max_m"],
    )
    item = args["item"]
    params = dict(
        received_original=args["received_original"],
        sent_original=args["sent_original"],
        s7_receipt=args["s7_source_receipt"],
        plan=plan,
        plan_original=plan.original_bytes(),
        action_id=item.action.action_id,
        session_id=item.native.observation.session_id,
        before_seq=1, dispatch_seq=2, cleanup_seq=3, after_seq=4,
        first_probe_seq=5, second_probe_seq=6,
        first_probe_request_id="goal-probe-5",
        second_probe_request_id="goal-probe-6",
    )
    return params


@pytest.mark.parametrize(("offset", "expected"), [
    (0, "REACHED"), (50, "NOT_REACHED"),
])
def test_source_shaped_goal_only_not_physical_reward(offset, expected):
    args = fixture()
    if offset:
        args["plan"] = replace(args["plan"], target_x=args["plan"].target_x+offset)
        args["plan_original"] = args["plan"].original_bytes()
    result = inspect_l16_first_action_prefix(**args)
    assert result.observed_goal_status == expected
    assert result.complete_single_action_captured_prefix
    assert result.received_sha256 == hashlib.sha256(
        args["received_original"],
    ).hexdigest()
    assert not result.independent_external_goal_authenticated
    assert not result.physical_no_intervention_proven
    assert result.qualified_real_l10_pairs == result.l10_adoptions == 0
    assert result.action_issues == result.s10_updates == result.s11_habit_grants == 0


def test_unstable_goal_probes_remain_undetermined():
    args = fixture()
    rows = args["received_original"].splitlines(keepends=True)
    data = json.loads(rows[-1])
    data["snapshot"]["position"]["x"] += 0.3
    rows[-1] = (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()
    args["received_original"] = b"".join(rows)
    args["s7_receipt"] = l15.l14._index(
        args["received_original"], args["sent_original"],
    )
    assert inspect_l16_first_action_prefix(**args).observed_goal_status == "UNDETERMINED"


@pytest.mark.parametrize("fault", [
    "lost_line", "wrong_receipt_sha", "wrong_plan_bytes",
    "wrong_goal_probe_id", "wrong_action", "wrong_session",
    "post_shutdown", "extra_motor", "wrong_clear_effect",
    "wrong_outbound_order", "false_previous_action_seq",
])
def test_source_fail_closed_without_learning(fault):
    args = fixture()
    if fault == "wrong_receipt_sha":
        args["s7_receipt"] = {**args["s7_receipt"], "received_sha256": "0"*64}
    elif fault == "wrong_plan_bytes":
        args["plan_original"] += b"\n"
    elif fault == "wrong_goal_probe_id":
        args["first_probe_request_id"] = "foreign"
    elif fault == "wrong_action":
        args["action_id"] = "other"
    elif fault == "wrong_session":
        args["session_id"] = "other-session"
    elif fault == "false_previous_action_seq":
        args["before_seq"] = 0
    else:
        if fault in ("lost_line", "wrong_clear_effect"):
            rows = args["received_original"].splitlines(keepends=True)
            if fault == "lost_line":
                rows.pop(2)
            else:
                data = json.loads(rows[3])
                data["effect"] = "set_control"
                rows[3] = (
                    json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n"
                ).encode()
            args["received_original"] = b"".join(rows)
        elif fault == "post_shutdown":
            args["sent_original"] += b'{"type":"shutdown"}\n'
        elif fault == "extra_motor":
            args["sent_original"] += args["sent_original"].splitlines(
                keepends=True,
            )[1]
        elif fault == "wrong_outbound_order":
            rows = args["sent_original"].splitlines(keepends=True)
            rows[1], rows[2] = rows[2], rows[1]
            args["sent_original"] = b"".join(rows)
        args["s7_receipt"] = l15.l14._index(
            args["received_original"], args["sent_original"],
        )
    with pytest.raises((L16SourceRejected, ValueError)):
        inspect_l16_first_action_prefix(**args)


def test_s7_single_existing_process_records_first_action_then_detaches(
    monkeypatch, tmp_path,
):
    args = fixture()
    raw = args["received_original"]
    process = FakeProcess(raw.splitlines(keepends=True))
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("fixture")
    recorder = NativeStreamReceipt(
        tmp_path / "native_bridge_received_original.jsonl",
        tmp_path / "native_bridge_sent_original.jsonl",
    )

    async def fake_subprocess(*_args, **_kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)

    async def run_single_session():
        s = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
            native_receipt=recorder,
        )
        await s.send_observe()
        await s.receive()  # S49 before Action
        await s.send_set_control(args["action_id"], control="back", state=True)
        await s.receive()  # genuine-shaped dispatch ACK
        await s.send_clear_controls(f'{args["action_id"]}-s15-clear')
        await s.receive()  # cleanup ACK
        await s.send_observe()
        await s.receive()  # existing S16 after-Action
        await s.send_observe("goal-probe-5")
        await s.receive()
        await s.send_observe("goal-probe-6")
        await s.receive()
        index = s.finish_native_receipt()
        with pytest.raises(MineflayerProcessIOError):
            s.finish_native_receipt()
        # S49 process is still alive; later actions can use it, but are
        # OUTSIDE the first-Action captured prefix and do not alter it.
        await s.send_observe("later-second-action-session")
        assert process.returncode is None
        return index

    index = asyncio.run(run_single_session())
    assert recorder.received.read_bytes() == raw
    assert recorder.sent.read_bytes() == args["sent_original"]
    assert index["received_sha256"] == hashlib.sha256(raw).hexdigest()
    assert index["sent_sha256"] == hashlib.sha256(
        args["sent_original"],
    ).hexdigest()
    args["s7_receipt"] = index
    assert inspect_l16_first_action_prefix(**args).observed_goal_status == "REACHED"


@pytest.mark.parametrize(("coordinates", "invalid"), [
    ((float("nan"), 0), True),
    ((float("inf"), 1), True),
    ((0, 1), False),
])
def test_goal_plan_is_explicit_and_finite(coordinates, invalid):
    if invalid:
        with pytest.raises(L16SourceRejected):
            L16GoalPlan(*coordinates)
    else:
        plan = L16GoalPlan(*coordinates)
        assert b'"authorizes_learning":false' in plan.original_bytes()


def test_s49_cli_requires_explicit_l16_confirmation_before_real_world(monkeypatch):
    import sys

    from adapters.mineflayer.s49_normal_session_real_ci import main

    monkeypatch.setattr(sys, "argv", [
        "s49", "--report", "/tmp/unused-report",
        "--server-log", "/tmp/unused-server",
        "--l16-capture-root", "/tmp/nonexistent-l16",
        "--l16-goal-target-x", "1", "--l16-goal-target-z", "2",
    ])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
