"""Original S49 forward motor DEV admission and negative boundary (offline)."""
from __future__ import annotations

import asyncio
import json

import pytest

from adapters.mineflayer import s49_normal_session_real_ci as original
from adapters.mineflayer.execution import (
    InvalidMineflayerExecutionData,
    MineflayerCommand,
)
from adapters.mineflayer.normal_action import NormalActionRejected, NormalSessionActionExecutor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance


def _command(ref: str, control: str) -> MineflayerCommand:
    return MineflayerCommand(
        action_id="s49-native-move-1", binding_id="s49-binding-1",
        action_ref=ref, effect="set_control", control=control,
        state=True, duration_s=0.2,
        cleanup_action_id="s49-native-move-1-s15-clear",
    )


def test_forward_and_backward_binding_never_silently_swap():
    assert _command("MOVE_BACKWARD", "back").control == "back"
    assert _command("MOVE_FORWARD", "forward").control == "forward"
    for ref, control in (
        ("MOVE_BACKWARD", "forward"),
        ("MOVE_FORWARD", "back"),
        ("MOVE_FORWARD", "sprint"),
        ("MOVE_SIDE", "forward"),
    ):
        with pytest.raises(InvalidMineflayerExecutionData):
            _command(ref, control)


def test_original_executor_is_backward_unless_explicit_dev_enabled():
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="escape near zombie", at_ns=1,
        provenance=Provenance("dev-test", "intent"),
    )
    default = NormalSessionActionExecutor("session-dev", intent)
    forward = NormalSessionActionExecutor("session-dev", intent, dev_forward_motor=True)
    assert default._dev_forward_motor is False
    assert forward._dev_forward_motor is True
    with pytest.raises(NormalActionRejected):
        NormalSessionActionExecutor("session-dev", intent, dev_forward_motor=1)


@pytest.mark.parametrize("bad_gate", [None, "0", "yes"])
def test_original_qualify_rejects_forward_before_world(
    monkeypatch, tmp_path, bad_gate,
):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    if bad_gate is None:
        monkeypatch.delenv("S49_FORWARD_MOTOR_DEV_ONLY", raising=False)
    else:
        monkeypatch.setenv("S49_FORWARD_MOTOR_DEV_ONLY", bad_gate)

    def forbid_server(*args, **kwargs):
        raise AssertionError("unadmitted DEV launched real server")

    monkeypatch.setattr(original, "_fetch_official_server", forbid_server)
    report_file = tmp_path / "forward-blocked.json"
    rc = asyncio.run(original.qualify(
        report_file, tmp_path / "server.log", dev_forward_motor=True,
    ))
    report = json.loads(report_file.read_text(encoding="utf-8"))
    assert rc == 2
    assert report["status"] == "BLOCKED"
    assert report["actual_native_actions"] == []
    assert report["dev_forward_motor"] is True


def test_forward_cannot_combine_with_original_next_epoch(monkeypatch, tmp_path):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_FORWARD_MOTOR_DEV_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(
        original, "_fetch_official_server",
        lambda *args, **kwargs: pytest.fail("unauthorized World startup"),
    )
    rc = asyncio.run(original.qualify(
        tmp_path / "report.json", tmp_path / "server.log",
        dev_forward_motor=True, dev_next_epoch="MOVE_AWAY",
    ))
    assert rc == 2
