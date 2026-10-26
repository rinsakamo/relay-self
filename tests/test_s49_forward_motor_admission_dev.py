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

def test_forward_s16_evidence_requires_separate_dev_flag():
    from dataclasses import replace

    import test_action_feedback_qualification as s17
    from adapters.mineflayer.self_action_evidence import (
        NativeEvidenceRejected,
        capture_native_action_evidence,
        verify_native_action_evidence,
    )

    *_, original, _, _ = s17.executed_closed_chain()
    forward = replace(original, action_ref="MOVE_FORWARD")
    with pytest.raises(NativeEvidenceRejected):
        capture_native_action_evidence(forward)
    evidence = capture_native_action_evidence(forward, allow_dev_forward=True)
    assert evidence["action_ref"] == "MOVE_FORWARD"
    assert evidence["goal_success_attested"] is False
    with pytest.raises(NativeEvidenceRejected):
        verify_native_action_evidence(
            evidence, action_id=forward.action_id,
            session_id=forward.session_id, movement_m=forward.movement_distance,
        )
    verify_native_action_evidence(
        evidence, action_id=forward.action_id,
        session_id=forward.session_id, movement_m=forward.movement_distance,
        allow_dev_forward=True,
    )
    with pytest.raises(NativeEvidenceRejected):
        capture_native_action_evidence(forward, allow_dev_forward=1)

def test_sprint_one_effect_schema_and_bound_direction():
    import json

    from adapters.mineflayer.execution import MOVE_FORWARD_SPRINT_DEV_REF
    from adapters.mineflayer.python_protocol import encode_forward_sprint_dev

    payload = json.loads(encode_forward_sprint_dev("s49-native-move-19"))
    assert payload == {
        "type": "effect", "action_id": "s49-native-move-19",
        "effect": "set_forward_sprint_dev", "forward": True, "sprint": True,
    }
    obj = MineflayerCommand(
        action_id="s49-native-move-19", binding_id="s49-binding-19",
        action_ref=MOVE_FORWARD_SPRINT_DEV_REF,
        effect="set_forward_sprint_dev", control="forward", state=True,
        duration_s=0.2, cleanup_action_id="s49-native-move-19-s15-clear",
    )
    assert obj.control == "forward"
    for eff, direction in [
        ("set_control", "forward"), ("set_forward_sprint_dev", "back"),
        ("set_forward_sprint_dev", "sprint"),
    ]:
        with pytest.raises(InvalidMineflayerExecutionData):
            MineflayerCommand(
                action_id=obj.action_id, binding_id=obj.binding_id,
                action_ref=obj.action_ref, effect=eff, control=direction,
                state=True, duration_s=0.2, cleanup_action_id=obj.cleanup_action_id,
            )


def test_sprint_dev_gate_blocks_before_minecraft(monkeypatch, tmp_path):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_FORWARD_MOTOR_DEV_ONLY", "1")
    monkeypatch.delenv("S49_SPRINT_MOTOR_DEV_ONLY", raising=False)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(
        original, "_fetch_official_server",
        lambda *a, **kw: pytest.fail("unauthorized sprint World"),
    )
    p = tmp_path / "gated.json"
    rc = asyncio.run(original.qualify(
        p, tmp_path / "paper.log", dev_forward_motor=True,
        dev_sprint_motor=True,
    ))
    assert rc == 2
    assert json.loads(p.read_text())["actual_native_actions"] == []


def test_forward_sprint_s16_receipt_is_dev_gated():
    from dataclasses import replace

    import test_action_feedback_qualification as s17
    from adapters.mineflayer.self_action_evidence import (
        NativeEvidenceRejected,
        capture_native_action_evidence,
        verify_native_action_evidence,
    )

    *_, before, _, _ = s17.executed_closed_chain()
    sprint = replace(
        before, action_ref="MOVE_FORWARD_SPRINT_DEV",
        dispatch_receipt=replace(
            before.dispatch_receipt, effect="set_forward_sprint_dev",
        ),
    )
    with pytest.raises(NativeEvidenceRejected):
        capture_native_action_evidence(sprint, allow_dev_forward=True)
    evidence = capture_native_action_evidence(
        sprint, allow_dev_forward=True, allow_dev_sprint=True,
    )
    with pytest.raises(NativeEvidenceRejected):
        verify_native_action_evidence(
            evidence, action_id=sprint.action_id,
            session_id=sprint.session_id, movement_m=sprint.movement_distance,
            allow_dev_forward=True,
        )
    verify_native_action_evidence(
        evidence, action_id=sprint.action_id, session_id=sprint.session_id,
        movement_m=sprint.movement_distance,
        allow_dev_forward=True, allow_dev_sprint=True,
    )


def test_sprint_longer_bounded_duration_does_not_change_backward_default():
    from adapters.mineflayer.execution import (
        MOVE_BACKWARD_DURATION_S,
        MOVE_FORWARD_SPRINT_DEV_REF,
    )

    assert MOVE_BACKWARD_DURATION_S == 0.20
    original_backward = _command("MOVE_BACKWARD", "back")
    assert original_backward.duration_s == MOVE_BACKWARD_DURATION_S
    assert MOVE_FORWARD_SPRINT_DEV_REF == "MOVE_FORWARD_SPRINT_DEV"
