"""Q4 I4a read-only source window through ORIGINAL B physical gate.

No Action/WAL writes, Native sends, real World or L1 grants.
"""
from __future__ import annotations

import pytest

from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)


def _gate(*, move=True, place=True, observation_only=False):
    return PhysicalIssueAdmission(
        {"A": "native-a"}, resident_mode=True,
        allow_resident_move=move, allow_resident_place_move=place,
        observation_only=observation_only,
    )


def test_original_i4a_quiescent_window_never_mints_lease_or_action():
    gate = _gate()
    with gate.quiescent_wal_history_window(
        self_id="A", native_session_id="native-a",
    ):
        assert gate.active_action_ids == ()
        assert not gate.closed
        assert gate.resident_states["A"] == "ONLINE"
    assert gate.active_action_ids == ()


@pytest.mark.parametrize("mode", [
    "foreign", "no_move", "observation", "closed", "active", "quarantine",
])
def test_i4a_source_window_denies_broken_original_issuer(mode):
    gate = _gate(
        move=mode != "no_move",
        place=mode not in ("no_move",),
        observation_only=mode == "observation",
    )
    if mode == "closed":
        gate.hold_for_operator()
    if mode == "quarantine":
        gate.quarantine_resident(
            self_id="A", native_session_id="native-a",
        )
    if mode == "active":
        with gate.lease(
            self_id="A", native_session_id="native-a",
            action_id="another", effect_family="NONE",
        ):
            with pytest.raises(PhysicalIssueFenceError):
                with gate.quiescent_wal_history_window(
                    self_id="A", native_session_id="native-a",
                ):
                    pytest.fail("read source during active effect")
        return
    with pytest.raises(PhysicalIssueFenceError):
        with gate.quiescent_wal_history_window(
            self_id="A",
            native_session_id="old-foreign" if mode == "foreign" else "native-a",
        ):
            pytest.fail("source window must not reopen unsafe physical gate")
