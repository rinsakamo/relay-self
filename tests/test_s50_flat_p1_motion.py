"""S FLAT→P1 motion original candidate, including false-recovery negative controls."""
from __future__ import annotations

import copy
import hashlib
import json
import math

import pytest

from adapters.mineflayer.m02_paper_dev import s50_flat_p1_motion as bridge
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.m02_paper_dev.v7_paired_config import (
    ARMS, TEMPLATE, render_arm,
)


def source(arm="SHAM_ON"):
    factor = ARMS[arm][1]
    world = "bba420a8-7943-465f-997e-e857e7587b93"
    original = []
    cumulative = 0.0
    billed_cumulative = 0.0
    for event_id, (tick, x1, x2) in enumerate(
        ((20, 0.5, 0.7), (21, 0.7, 1.2)), 1
    ):
        blocks = x2 - x1
        billed = blocks * .01 * factor
        cumulative += blocks
        billed_cumulative += billed
        original.append(
            "[Server thread/INFO]: M02_DEV_MOTION "
            f"id={event_id} reason=WALK blocks={blocks} billed={billed} "
            f"cumulative_blocks={cumulative} cumulative_billed={billed_cumulative} "
            f"from_x={x1} from_y=-60.0 from_z=0.5 "
            f"to_x={x2} to_y=-60.0 to_z=0.5 "
            f"world_full_time={tick} world={world} marker_id=dev"
        )
    report = {
        "arm": arm, "mode": "FLAT_DEV_ONLY", "status": "PASS",
        "cleanup_complete": True, "original_unchanged": True,
        "science_trials": 0, "engineering_qualified": False,
        "config_sha256": hashlib.sha256(
            render_arm(TEMPLATE.read_bytes(), arm)
        ).hexdigest(),
        "basal_multiplier": ARMS[arm][0],
        "walk_multiplier": ARMS[arm][1],
        "initial_server_marker": {
            "seed": "63101", "world": world,
            "x": "0.5", "y": "-60.0", "z": "0.5",
            "full_time": "16", "motion_blocks": "0.0",
        },
        "terminal_server_marker": {
            "seed": "63101", "world": world,
            "full_time": "100", "motion_blocks": str(cumulative),
            "motion_billed": str(billed_cumulative),
        },
        "foraging": {"status": "PICKUP_SOURCE_CONSISTENT",
                     "movement_outcomes": [
                         {"kind": "PROGRESSED", "terminal": "outcome"},
                         {"kind": "ARRIVED", "terminal": "outcome"},
                     ]},
        "eating": {"state": "outcome"},
        "metabolism_source": {
            "motion_log_cap": 300, "motion_logged_rows": 2,
            "motion_blocks": cumulative, "motion_billed": billed_cumulative,
        },
    }
    return "\n".join(original) + "\n", report


@pytest.mark.parametrize("arm", list(ARMS))
def test_positive_motion_is_only_an_unadmitted_p1_candidate(arm):
    original, report = source(arm)
    got = bridge.screen_motion(original, report, arm=arm)
    assert got["native_motion_events"] == 2
    assert got["native_moving_tick_count"] == 2
    assert got["tick_event_groups"][0]["world_full_time"] == 20
    assert math.isclose(got["native_observed_horizontal_blocks"], .7)
    assert math.isclose(got["native_billed_walk_exhaustion"],
                        .007 * ARMS[arm][1])
    assert math.isclose(got["hypothetical_P1_motion_gain_unadmitted"], .028)
    assert got["p1_fatigue_recovered"] == 0.0
    assert not got["P1_state_advanced"]
    assert not got["wait_SourceBoundTick_issued"]
    assert not got["move_SourceBoundTick_issued"]
    assert got["unobserved_ticks"] == "UNKNOWN_NOT_WAIT"


@pytest.mark.parametrize("edit", [
    lambda c, r: (c.replace("id=2 ", "id=1 "), r),
    lambda c, r: (c.replace("world_full_time=21", "world_full_time=19"), r),
    lambda c, r: (c.replace("cumulative_blocks=0.7", "cumulative_blocks=0.9"), r),
    lambda c, r: (c.replace(" billed=", " billed=0.2", 1), r),
    lambda c, r: (c.replace("to_x=1.2", "to_x=1.9"), r),
    lambda c, r: (c.replace("reason=WALK", "reason=SPRINT"), r),
    lambda c, r: (c.replace("world_full_time=20", "world_full_time=200"), r),
    lambda c, r: (c.replace("marker_id=dev", "marker_id=dev marker_id=forged"), r),
    lambda c, r: ("", r),
])
def test_tampered_original_fails_closed(edit):
    original, report = source()
    original, report = edit(original, copy.deepcopy(report))
    with pytest.raises(BoundaryRejected):
        bridge.screen_motion(original, report, arm="SHAM_ON")


@pytest.mark.parametrize("field,value", [
    ("mode", "SCIENCE"), ("arm", "BOTH_ZERO"), ("status", "FAIL"),
    ("cleanup_complete", False), ("original_unchanged", False),
    ("science_trials", 1), ("engineering_qualified", True),
    ("walk_multiplier", 0), ("config_sha256", "0" * 64),
])
def test_foreign_report_rejected(field, value):
    original, report = source()
    report[field] = value
    with pytest.raises(BoundaryRejected):
        bridge.screen_motion(original, report, arm="SHAM_ON")


def test_wrong_paper_seed_rejected_and_silence_never_wait():
    original, report = source()
    report["terminal_server_marker"]["seed"] = "62101"
    with pytest.raises(BoundaryRejected, match="seed"):
        bridge.screen_motion(original, report, arm="SHAM_ON")
    original, report = source()
    good = bridge.screen_motion(original, report, arm="SHAM_ON")
    assert good["terminal_full_time"] - good["start_full_time"] > 2
    assert good["p1_wait_ticks_admitted"] == 0


def test_original_hash_guard_and_corrupt_original(tmp_path):
    root = tmp_path / "SHAM_ON"
    root.mkdir()
    original, report = source()
    (root / "report.json").write_text(json.dumps(report))
    (root / "paper_server.log").write_text(original)
    manifest = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ("report.json", "paper_server.log")
    }
    (root / "sha256.json").write_text(json.dumps(manifest))
    assert bridge.read_archived_original(root, arm="SHAM_ON")[
        "native_motion_events"
    ] == 2
    (root / "paper_server.log").write_text(original + "tamper\n")
    with pytest.raises(BoundaryRejected, match="SHA"):
        bridge.read_archived_original(root, arm="SHAM_ON")
