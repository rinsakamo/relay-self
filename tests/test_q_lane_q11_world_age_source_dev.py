"""Q11 independent clock-basis verification; all sources are synthetic CPU data."""
from __future__ import annotations

import pytest

from experiments.q_lane_q4_raw_native_wal_audit_dev import Q4EvidenceHold, _time
from experiments.q_lane_q9_u24_s1_stop_diagnostic_dev import (
    Q9U24Hold,
    audit_u24_failed_s1,
)
from test_q_lane_q9_u24_s1_stop_diagnostic_dev import _make_source, _modify


def test_world_age_clock_not_daylight_for_stop_tick():
    first = {"time": {"day": 0, "time_of_day": 6000, "is_day": True,
                      "world_age_ticks": 120}}
    later = {"time": {"day": 0, "time_of_day": 6000, "is_day": True,
                      "world_age_ticks": 140}}
    assert _time(first) == 120
    assert _time(later) - _time(first) == 20
    assert _time({"time": {
        "day": 0, "time_of_day": 6000, "is_day": True,
    }}) == 6000


@pytest.mark.parametrize("age", [-1, True, None, 1.5, "140", 2**53])
def test_reject_invalid_source_world_age(age):
    with pytest.raises(Q4EvidenceHold):
        _time({"time": {"day": 0, "time_of_day": 6000, "is_day": True,
                        "world_age_ticks": age}})


def test_q9_nominal_refuses_mixed_daylight_and_server_age(tmp_path):
    manifest = _make_source(tmp_path, "two_moves")

    def add_age(messages):
        for row in messages:
            if str(row.get("request_id", "")).startswith("p0d-move-stop-"):
                row["snapshot"]["time"]["world_age_ticks"] = 101
        messages[-1]["snapshot"]["time"].pop("world_age_ticks")

    manifest = _modify(tmp_path, "native_stdout", add_age, "two_moves")
    with pytest.raises(Q9U24Hold, match="clock source changed"):
        audit_u24_failed_s1(root=tmp_path, manifest_path=manifest,
                            trial="two_moves")


def test_q9_reports_legacy_clock_basis_for_u24_original_style(tmp_path):
    manifest = _make_source(tmp_path, "two_moves")
    result = audit_u24_failed_s1(root=tmp_path, manifest_path=manifest,
                                  trial="two_moves")
    assert result["native_clock_basis"] == "LEGACY_DAYLIGHT_TIME"
