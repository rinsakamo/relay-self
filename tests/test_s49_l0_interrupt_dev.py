"""Offline guard tests; no Mineflayer, Paper, action execution, or GPU."""
import pytest

from adapters.mineflayer.s49_l0_interrupt_dev import (
    L0Interruption,
    S49L0InterruptRejected,
    classify_s49_l0_interrupt,
)


def check(assessment, **changes):
    values = {
        "l0_shadow_evaluated": True,
        "l0_fresh_world_tick_attested": False,
        "authorized_action_issued": False,
        "tps_admission_granted": False,
    }
    values.update(changes)
    return classify_s49_l0_interrupt(assessment, **values)


@pytest.mark.parametrize("signal,expect", [
    ("UNKNOWN", L0Interruption.INTERRUPT_UNKNOWN),
    ("LOW_HEALTH", L0Interruption.INTERRUPT_LOW_HEALTH),
    ("LOW_FOOD", L0Interruption.INTERRUPT_LOW_FOOD),
    ("KNOWN_NEAR_HOSTILE", L0Interruption.INTERRUPT_KNOWN_HOSTILE),
    ("NO_KNOWN_URGENT_SIGNAL", L0Interruption.CONTINUE_UNVERIFIED),
])
def test_exact_known_l0_signals_never_issue_an_action(signal, expect):
    result = check(signal)
    assert result is expect
    assert "AUTHORIZED" not in result.value
    assert "TPS" not in result.value


@pytest.mark.parametrize("invalid", [
    None, "", [], True, "SAFE", "STOP_AUTHORIZED", "KNOWN_NEAR_HOSTILE ",
])
def test_bad_assessment_rejects(invalid):
    with pytest.raises(S49L0InterruptRejected):
        check(invalid)


@pytest.mark.parametrize("forgery", [
    {"l0_shadow_evaluated": False},
    {"l0_fresh_world_tick_attested": True},
    {"authorized_action_issued": True},
    {"tps_admission_granted": True},
    {"l0_shadow_evaluated": 1},
    {"authorized_action_issued": 0},
])
def test_spoofed_shadow_authority_or_nonbool_flags_rejects(forgery):
    with pytest.raises(S49L0InterruptRejected):
        check("NO_KNOWN_URGENT_SIGNAL", **forgery)
