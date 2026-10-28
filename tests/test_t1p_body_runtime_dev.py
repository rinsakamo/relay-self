"""T1p unforced L0/Body policy: pure fail-closed offline characterization."""
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from adapters.mineflayer.t1p_body_runtime_dev import T1pRejected, decide_l0


def sample():
    frame = SimpleNamespace(
        session_id="owned-session", seq=17,
        data={"status": "ADMITTED", "assessment": "NO_KNOWN_URGENT_SIGNAL",
              "snapshot": {"input": 0, "world_tick": 120},
              "control": {"phase": "INITIAL"}})
    owner = SimpleNamespace(
        session_id="owned-session", previous=frame, failed=False,
        active_action=None, pending_meal=None, clear_seq=None,
        fatigue=SimpleNamespace(fatigue=0.0),
        profile=SimpleNamespace(capacity=1.0),
        energy=SimpleNamespace(body=SimpleNamespace(energy=12.0)))
    return frame, owner


def test_first_epoch_uses_admitted_paper_not_scripted_hazard():
    frame, owner = sample()
    assert decide_l0(frame, owner, completed=0, limit=2) == "MOVE"


def test_second_epoch_requires_original_control_clear():
    frame, owner = sample()
    assert decide_l0(frame, owner, completed=1, limit=2) == "HALT"
    owner.clear_seq = 19
    frame.data["control"]["phase"] = "CLEARED"
    assert decide_l0(frame, owner, completed=1, limit=2) == "MOVE"
    assert decide_l0(frame, owner, completed=2, limit=2) == "COMPLETE"


@pytest.mark.parametrize("assessment", [
    "LOW_HEALTH", "LOW_FOOD", "KNOWN_NEAR_HOSTILE", "UNKNOWN",
])
def test_unforced_hazard_does_not_generate_an_action(assessment):
    frame, owner = sample()
    frame.data["assessment"] = assessment
    assert decide_l0(frame, owner, completed=0, limit=2) == "HALT"


@pytest.mark.parametrize("phase,bits", [
    ("MOVING", 0), ("CLEARED", 1), ("INITIAL", 2),
])
def test_nonidle_native_motor_state_cannot_issue(phase, bits):
    frame, owner = sample()
    frame.data["control"]["phase"] = phase
    frame.data["snapshot"]["input"] = bits
    assert decide_l0(frame, owner, completed=0, limit=2) == "HALT"


def test_host_body_guard_holds_without_granting_extra_action():
    frame, owner = sample()
    owner.fatigue.fatigue = 0.9
    assert decide_l0(frame, owner, completed=0, limit=2) == "HOLD_BODY"
    owner.fatigue.fatigue = 0.0
    owner.energy.body.energy = 0.5
    assert decide_l0(frame, owner, completed=0, limit=2) == "HALT"


@pytest.mark.parametrize("change", [
    lambda frame, owner: setattr(owner, "failed", True),
    lambda frame, owner: setattr(owner, "active_action", "old-action"),
    lambda frame, owner: setattr(owner, "pending_meal", "unconfirmed-eat"),
    lambda frame, owner: setattr(owner, "previous", None),
    lambda frame, owner: setattr(owner, "fatigue", None),
    lambda frame, owner: setattr(frame, "session_id", "foreign"),
    lambda frame, owner: setattr(frame, "seq", 18),
    lambda frame, owner: frame.data.update(status="STALE"),
])
def test_lost_or_foreign_source_never_issues(change):
    frame, owner = sample()
    change(frame, owner)
    with pytest.raises(T1pRejected):
        decide_l0(frame, owner, completed=0, limit=2)


@pytest.mark.parametrize("completed,limit", [
    (-1, 2), (3, 2), (0, 33), (True, 2), (0, 2.0),
])
def test_invalid_bounded_budget_rejected(completed, limit):
    frame, owner = sample()
    with pytest.raises(T1pRejected):
        decide_l0(frame, owner, completed=completed, limit=limit)


def test_source_is_not_relabelled_success_or_rewritten():
    frame, owner = sample()
    before = deepcopy(frame.data)
    assert decide_l0(frame, owner, completed=0, limit=2) == "MOVE"
    assert frame.data == before
    assert owner.active_action is None
    assert owner.energy.body.energy == 12.0
