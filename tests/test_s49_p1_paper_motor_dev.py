"""Isolated P1 Paper native tick audit and deliberate proof-negative cases."""
from __future__ import annotations

import pytest

from adapters.mineflayer.s49_paper_forward_dash_dev import (
    ForwardDashDevRejected,
    audit_native_paper_p1_dev,
)
from experiments.fatigue_p1 import FatigueProfile, initial_state
from experiments.p1_gait_dev import (
    GaitTickDev,
    advance_gait_dev,
    p1_motor_power_limit_dev,
)

ACTION = "s49-native-move-20"
SESSION = "p1-native-dev"


def valid_paper_p1_rows():
    cfg = FatigueProfile(enabled=True, initial=0.6)
    state = initial_state(cfg, SESSION)
    prev = 0.0
    rows = []
    for i in range(1, 14):
        transition = advance_gait_dev(
            cfg, state, GaitTickDev(
                SESSION, i, "DASH" if prev > 0 else "RUN",
                "forward", prev, 1.0 if prev > 0 else None,
            ),
        )
        next_power = (
            p1_motor_power_limit_dev(cfg, transition.after, 1.0, 1.0)
            if i >= 3 else 0.0
        )
        rows.append(
            "S49_DASH_DEV_TICK action_id=" + ACTION
            + " session_id=" + SESSION
            + f" tick={243+i} p1_world_ticks={i} p1_motor_dev=true"
            + f" p1_before={state.fatigue} p1_after={transition.after.fatigue}"
            + f" p1_prev_applied_power={prev}"
            + f" p1_current_applied_power={next_power}"
            + f" modifier_applied={'true' if next_power else 'false'}"
        )
        prev = next_power
        state = transition.after
    return "\n".join(rows)


def test_paper_p1_fatigue_power_fades_and_m0_is_only_proposed():
    evidence = audit_native_paper_p1_dev(
        valid_paper_p1_rows(), action_id=ACTION, session_id=SESSION,
    )
    assert evidence["world_ticks_replayed"] == 13
    assert evidence["single_p1_model_replayed"]
    assert evidence["actual_power_fade"] > 0.01
    assert evidence["initial_boost_power"] < 1.0
    assert evidence["last_boost_power"] < evidence["initial_boost_power"]
    assert evidence["m0_charge_proposal_not_posted"] > 0
    assert evidence["source_qualified"] is False
    assert evidence["p1_ledger_posted"] is False
    assert evidence["m0_ledger_posted"] is False


@pytest.mark.parametrize("corruption", [
    "foreign_session", "missing_tick", "replay", "wrong_fatigue",
    "forged_power", "disable_p1", "nonconsecutive", "invalid_number",
])
def test_paper_p1_rejects_untrusted_world_sequence(corruption):
    lines = valid_paper_p1_rows().splitlines()
    if corruption == "foreign_session":
        lines[3] = lines[3].replace("session_id=" + SESSION, "session_id=foreign")
    elif corruption == "missing_tick":
        lines.pop(4)
    elif corruption == "replay":
        lines.insert(4, lines[3])
    elif corruption == "wrong_fatigue":
        lines[3] = lines[3].replace("p1_after=", "p1_after=0.01", 1)
    elif corruption == "forged_power":
        lines[5] = lines[5].replace("p1_current_applied_power=", "p1_current_applied_power=0.05", 1)
    elif corruption == "disable_p1":
        lines[2] = lines[2].replace("p1_motor_dev=true", "p1_motor_dev=false")
    elif corruption == "nonconsecutive":
        lines[5] = lines[5].replace("tick=249", "tick=260")
    else:
        lines[0] = lines[0].replace("p1_before=0.6", "p1_before=nan")
    with pytest.raises(ForwardDashDevRejected):
        audit_native_paper_p1_dev(
            "\n".join(lines), action_id=ACTION, session_id=SESSION,
        )
