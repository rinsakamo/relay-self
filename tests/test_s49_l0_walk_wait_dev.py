"""DEV owner-local WAIT admission and physical WALK binding contracts."""
from __future__ import annotations

from pathlib import Path

import pytest

from adapters.mineflayer.normal_action import (
    NormalActionRejected,
    NormalWorldL0,
)
from adapters.mineflayer.s49_l0_walk_wait_two_real_dev import (
    review_native,
)


def owner():
    # Unit-only original instance for admission refusal (no World/source claims).
    host=object.__new__(NormalWorldL0)
    host.session_id="native-session"
    host._used_action_ids={"original-first", "original-second"}
    host.events=3
    host.action_requests=2
    host._s16_stop_source=None
    return host


def test_original_owner_wait_binds_only_after_closed_second(monkeypatch):
    monkeypatch.setenv("S49_L0_GOAL_WAIT_DEV_ONLY","1")
    h=owner()
    h.bind_s16_stop_dev(
        session_id="native-session",second_action_id="original-second",
        residual_m=0.185,tolerance_m=0.20,
    )
    assert h._s16_stop_source==("original-second",0.185)
    with pytest.raises(NormalActionRejected):
        h.bind_s16_stop_dev(
            session_id="native-session",second_action_id="original-second",
            residual_m=0.185,tolerance_m=0.20,
        )


@pytest.mark.parametrize("fault",[
    "no_optin","wrong_session","wrong_action","stale_event",
    "missing_first_grant","outside_deadband","bad_tolerance","nonfinite",
])
def test_original_wait_refuses_unproven_s16(monkeypatch,fault):
    monkeypatch.setenv("S49_L0_GOAL_WAIT_DEV_ONLY","1")
    h=owner()
    kw={
        "session_id":"native-session","second_action_id":"original-second",
        "residual_m":0.185,"tolerance_m":0.20,
    }
    if fault=="no_optin":
        monkeypatch.delenv("S49_L0_GOAL_WAIT_DEV_ONLY")
    elif fault=="wrong_session":kw["session_id"]="other"
    elif fault=="wrong_action":kw["second_action_id"]="foreign"
    elif fault=="stale_event":h.events=2
    elif fault=="missing_first_grant":h._used_action_ids.clear()
    elif fault=="outside_deadband":kw["residual_m"]=0.4
    elif fault=="bad_tolerance":kw["tolerance_m"]=1
    else:kw["residual_m"]=float("nan")
    with pytest.raises(NormalActionRejected):
        h.bind_s16_stop_dev(**kw)


def test_two_world_reviewer_requires_terminal_source_for_both_modes():
    with pytest.raises(ValueError):
        review_native("WALK",{"status":"FAIL"})
    with pytest.raises(ValueError):
        review_native("WAIT",{"status":"PASS","actual_native_actions":[]})


def test_walk_third_uses_forward_not_sprint_and_wait_skips_grant():
    normal=Path("adapters/mineflayer/normal_action.py").read_text()
    runner=Path("adapters/mineflayer/s49_normal_session_real_ci.py").read_text()
    bridge=Path("adapters/mineflayer/bridge.mjs").read_text()
    assert '"MOVE_FORWARD" if self._dev_walk_third and self._count == 2' in normal
    assert '"MOVE_FORWARD" if dev_l0_walk_third_dev and executor._count == 2' in runner
    assert '"third_gait": "WALK" if dev_l0_walk_third_dev' in runner
    assert "host.bind_s16_stop_dev(" in runner
    assert 'criterion_id="s49-closed-s16-relative-step-stop-dev"' in normal
    assert "bot.setControlState(command.control, command.state)" in bridge
    assert "if step.asks_for_action:" in Path(
        "src/relay_self/reactive_l0.py"
    ).read_text()
