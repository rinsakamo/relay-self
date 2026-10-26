"""Offline parser negatives for one issued S49 forward+sprint Paper window."""
from __future__ import annotations

import pytest

from adapters.mineflayer.s49_paper_forward_dash_dev import (
    ForwardDashDevRejected,
    review_forward_dash_rows,
)

ACTION = "s49-native-move-19"
SESSION = "session-1"


def _rows(positive: bool = True) -> str:
    truth = "true" if positive else "false"
    on = 1 if positive else 0
    other = 0 if positive else 1
    return (
        "S49_DASH_DEV_TICK action_id=" + ACTION + " session_id=" + SESSION
        + " tick=104 index=1 input_forward_only=" + truth
        + " modifier_applied=" + truth
        + " dash_stance_active=true input_edge_attested=false\n"
        + "S49_DASH_DEV_COMPLETE action_id=" + ACTION
        + " session_id=" + SESSION + " reason=OWNER_RELEASE"
        + f" forward_boost_ticks={on} other_direction_or_ambiguous_ticks={other}"
        + " modifier_applied=false authority=NONE P1_APPLIED=false M0_POSTED=false\n"
    )


def test_positive_and_negative_report_are_distinguished():
    good = review_forward_dash_rows(_rows(), action_id=ACTION, session_id=SESSION)
    assert good["paper_forward_boost_ticks"] == 1
    assert good["paper_modifier_removed"] is True
    assert good["m0_posted"] is False and good["p1_native_updated"] is False
    uncertain = review_forward_dash_rows(
        _rows(False), action_id=ACTION, session_id=SESSION,
    )
    assert uncertain["paper_gait_ticks_observed"] == 1
    assert uncertain["paper_forward_boost_ticks"] == 0


@pytest.mark.parametrize("change", [
    "foreign_session", "duplicate", "unknown_modifier", "contradictory",
    "missing_complete", "mismatch_count", "bad_tick",
])
def test_forged_or_broken_paper_window_rejected(change):
    raw = _rows()
    if change == "foreign_session":
        raw = raw.replace("session_id=" + SESSION, "session_id=other")
    elif change == "duplicate":
        raw = raw + raw
    elif change == "unknown_modifier":
        raw = raw.replace("modifier_applied=true", "modifier_applied=unknown")
    elif change == "contradictory":
        raw = raw.replace("input_forward_only=true", "input_forward_only=false")
    elif change == "missing_complete":
        raw = raw.splitlines()[0]
    elif change == "mismatch_count":
        raw = raw.replace("forward_boost_ticks=1", "forward_boost_ticks=0")
    else:
        raw = raw.replace("tick=104", "tick=0")
    with pytest.raises(ForwardDashDevRejected):
        review_forward_dash_rows(raw, action_id=ACTION, session_id=SESSION)
