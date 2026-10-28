"""Fail-closed contracts for three-mode Node source isolation."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from adapters.mineflayer.s49_p1_attr_trace_isolation_review_dev import (
    P1TraceIsolationRejected,
    summarize_isolation,
)


def fixture():
    arms = {}
    for mode in ("OFF", "MEM", "FILE"):
        for case in ("CARRY", "WAIT_ASSUMED"):
            name = f"{mode}_{case}"
            arms[name] = {
                "name": name, "mode": mode, "case": case,
                "session_id": "session-" + name,
                "world_uuid": "world-" + name,
                "first_action_id": "action-" + name,
                "native_actions": 2,
                "speed_projection_on": True,
                "observer_enabled": mode != "OFF",
                "trace_file_exists": mode == "FILE",
                "paper_positive_ticks": 7,
                "paper_gait_ticks": 13,
                "mean_paper_positive_speed_mps": 6.5,
                "first_s16_distance_m": 3.7,
                "node_observed_physics_ticks": 12 if mode == "FILE" else None,
                "node_observed_positive_attribute_ticks": (
                    6 if mode == "FILE" else None
                ),
                "genuine_s49_outcomes": True,
                "paper_original_owner_release": True,
                "qualification_go": False,
                "science_go": False,
            }
    return arms


def test_six_arms_are_separate_and_no_fabricated_tick_measurements():
    f = fixture()
    previous = deepcopy(f)
    r = summarize_isolation(f)
    assert f == previous
    assert r["source_verified_all_six_worlds"] is True
    assert r["file_write_causally_changes_movement_proven"] is False
    assert r["MEM_sync_trace_write_on_CLEAR"] is False
    assert r["MEM_internal_tick_count_attested"] is False
    assert r["native_action_tick_controlled"] is False
    assert r["qualification_go"] is False
    assert r["science_go"] is False


def test_negative_delta_is_not_censored():
    f = fixture()
    f["FILE_CARRY"]["first_s16_distance_m"] = 3.1
    f["MEM_CARRY"]["first_s16_distance_m"] = 3.9
    r = summarize_isolation(f)
    assert r["per_model_differences"]["CARRY"]["file_minus_mem_s16_m"] < 0


@pytest.mark.parametrize("fault", [
    "missing", "extra", "duplicate_session", "duplicate_world",
    "wrong_case", "wrong_mode", "wrong_name", "foreign_first_action",
    "observer_on_for_off", "observer_off_for_mem", "wrong_file_presence",
    "paper_not_seven", "paper_not_release", "missing_owner",
    "bad_distance", "missing_file_ticks", "invented_mem_ticks",
    "invented_off_ticks", "fake_qual", "fake_science",
])
def test_isolation_refusal(fault):
    f = fixture()
    x = f["MEM_CARRY"]
    if fault == "missing":
        f.pop("MEM_CARRY")
    elif fault == "extra":
        f["EXTRA"] = deepcopy(x)
    elif fault == "duplicate_session":
        x["session_id"] = f["OFF_CARRY"]["session_id"]
    elif fault == "duplicate_world":
        x["world_uuid"] = f["OFF_CARRY"]["world_uuid"]
    elif fault == "wrong_case":
        x["case"] = "WAIT_ASSUMED"
    elif fault == "wrong_mode":
        x["mode"] = "FILE"
    elif fault == "wrong_name":
        x["name"] = "OFF_CARRY"
    elif fault == "foreign_first_action":
        x["first_action_id"] = ""
    elif fault == "observer_on_for_off":
        f["OFF_CARRY"]["observer_enabled"] = True
    elif fault == "observer_off_for_mem":
        x["observer_enabled"] = False
    elif fault == "wrong_file_presence":
        x["trace_file_exists"] = True
    elif fault == "paper_not_seven":
        x["paper_positive_ticks"] = 6
    elif fault == "paper_not_release":
        x["paper_original_owner_release"] = False
    elif fault == "missing_owner":
        x["native_actions"] = 1
    elif fault == "bad_distance":
        x["first_s16_distance_m"] = float("nan")
    elif fault == "missing_file_ticks":
        f["FILE_CARRY"]["node_observed_physics_ticks"] = None
    elif fault == "invented_mem_ticks":
        x["node_observed_physics_ticks"] = 12
    elif fault == "invented_off_ticks":
        f["OFF_CARRY"]["node_observed_positive_attribute_ticks"] = 6
    elif fault == "fake_qual":
        x["qualification_go"] = True
    else:
        x["science_go"] = True
    with pytest.raises(P1TraceIsolationRejected):
        summarize_isolation(f)


def test_bridge_memory_mode_has_no_serialization_or_file_write_at_clear():
    source = Path("adapters/mineflayer/bridge.mjs").read_text()
    memory = source.index("if (attrBoundaryMemoryOnly) return")
    sync = source.index("writeFileSync(attrBoundaryPath", memory)
    assert memory < sync
    assert "S49_SPEED_ATTR_BOUNDARY_MEMORY_DEV_ONLY" in source
    assert "if (!attrBoundary || attrBoundarySealed" in source
    # Same sampler and listeners in MEM and FILE; only CLEAR I/O differs.
    assert source.count("if (attrBoundaryEnabled) {") == 1
    assert source.count("attrBoundarySample('ACTIVE_PHYSICS'") == 1


def test_python_run_requires_exact_off_mem_file_gate():
    source = Path("adapters/mineflayer/s49_paper_forward_dash_dev.py").read_text()
    assert 'None, "OFF", "MEM", "FILE"' in source
    assert "'1' if trace_memory_only else '0'" in source
    assert "if speed_attr_boundary_dev and not trace_ab_off and not trace_memory_only" in source
