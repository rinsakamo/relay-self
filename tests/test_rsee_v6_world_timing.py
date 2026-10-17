"""R V6 independent bounded World-start/clock source checks; no physical run."""
from copy import deepcopy

import pytest

from experiments.standard_env.v6_world_timing import (
    ARMS,
    ENERGIES,
    GOLDEN_MANIFEST_SHA256,
    V6_START_SCHEMA,
    V6ClockRejected,
    check_stopped_clones,
    plan,
    review_clock_trace,
    review_paired_start,
)


def _trace(*, phase="LOW", arm="SENSOR_ON", sid="synthetic-session"):
    frames = []
    for i in range(13):
        tick = min(i, 11)
        frames.append({
            "session_id": sid,
            "native_seq": 1 + i * 2,
            "request_id": f"synthetic-v6-{sid}-{i:02d}",
            "host_monotonic_ns": 1_000_000_000 + i * 65_000_000,
            "m0_tick": tick,
            "m0_energy": ENERGIES[phase] - .5 * tick,
            "native_time": {
                "day": 4,
                "time_of_day": 7000 + i * 3,
                "is_day": True,
            },
            "world_age_tick": None,
            "item_visible": i == 12,
            "issued_action": False,
        })
    return {
        "schema": V6_START_SCHEMA,
        "world_start_slot": "WORLD_START_A",
        "arm": arm, "regime": phase,
        "native_session": sid,
        "stopped_world_manifest_sha256": GOLDEN_MANIFEST_SHA256,
        "frames": frames,
    }


def test_v6_r_plan_does_not_read_host_or_assert_time_equivalence():
    data = plan()
    assert data["classification"] == "RSEE_V6_WORLD_TIME_PRE_ADMISSION_PLAN"
    assert data["minecraft_world_age_tick"] == "NOT_IN_FROZEN_MINEFLAYER_SOURCE"
    assert data["world_start_bytes"] == "NOT_READ"
    assert data["cross_arm_native_world_elapsed_parity"] == "NOT_ATTESTED"
    assert data["physical_execution_authorized"] is False


def test_v6_r_keeps_host_elapsed_native_display_and_m0_tick_separate():
    data = review_clock_trace(_trace())
    assert data["classification"] == "RSEE_V6_THREE_CLOCK_STRUCTURAL_REVIEW_ONLY"
    assert data["host_elapsed_ns_start_to_item"] == 12 * 65_000_000
    assert data["native_clock_display_daytime_start_to_item"] == [
        4 * 24000 + 7000, 4 * 24000 + 7036,
    ]
    assert data["m0_wait_charges"] == 11
    assert data["m0_tick_at_item"] == 11
    assert data["m0_energy_at_item"] == 6.5
    assert data["world_age_elapsed_ticks_start_to_item"] is None
    assert data["matched_world_elapsed_tick_attested"] is False
    assert data["world_start_clone_bytes_verified"] is False


def test_v6_r_rejects_wrong_m0_start_host_native_and_issuing_action():
    base = _trace()
    for change in (
        lambda t: t.update(regime="UNREGISTERED"),
        lambda t: t.update(world_start_slot="WORLD_START_Z"),
        lambda t: t.update(stopped_world_manifest_sha256="f" * 64),
        lambda t: t["frames"].pop(2),
        lambda t: t["frames"][3].update(m0_tick=99),
        lambda t: t["frames"][3].update(m0_energy=8),
        lambda t: t["frames"][3].update(native_seq=2),
        lambda t: t["frames"][3].update(request_id=t["frames"][2]["request_id"]),
        lambda t: t["frames"][3].update(session_id="other"),
        lambda t: t["frames"][3].update(host_monotonic_ns=1),
        lambda t: t["frames"][3].update(issued_action=True),
        lambda t: t["frames"][5].update(item_visible=True),
        lambda t: t["frames"][5]["native_time"].update(time_of_day=24000),
        lambda t: t["frames"][5]["native_time"].update(day=-1),
        lambda t: t["frames"][5]["native_time"].update(is_day=1),
        lambda t: t["frames"][5].update(world_age_tick=-1),
        lambda t: t["frames"][5].update(world_age_tick="unknown"),
    ):
        data = deepcopy(base)
        change(data)
        with pytest.raises(V6ClockRejected):
            review_clock_trace(data)


def test_v6_r_clock_display_jump_does_not_count_as_world_age():
    data = _trace()
    data["frames"][-1]["native_time"]["time_of_day"] = 12345
    result = review_clock_trace(data)
    assert result["native_clock_display_daytime_start_to_item"][-1] == 108345
    assert result["world_age_elapsed_ticks_start_to_item"] is None
    assert result["native_time_of_day_is_not_world_age"] is True


def test_v6_r_positive_structural_age_cannot_authenticate_originals():
    data = _trace()
    for i, frame in enumerate(data["frames"]):
        frame["world_age_tick"] = 100 + i * 10
    result = review_clock_trace(data)
    assert result["world_age_elapsed_ticks_start_to_item"] == 120
    assert result["world_age_sample_presence"] == "ALL_UNBOUND"
    assert result["matched_world_elapsed_tick_attested"] is False
    data["frames"][6]["world_age_tick"] = 0
    with pytest.raises(V6ClockRejected):
        review_clock_trace(data)


def test_v6_r_one_complete_paired_start_is_only_candidate_not_admission():
    traces = [
        _trace(phase=regime, arm=arm, sid=f"s-{regime}-{arm}")
        for regime in ENERGIES for arm in ARMS
    ]
    result = review_paired_start(traces)
    assert result["planned_arms"] == 12
    assert result["claimed_world_age_delta_parity_possible"] is False
    assert result["matched_native_world_elapsed_tick_attested"] is False
    assert result["actual_world_starts"] == 0
    assert result["physical_execution_authorized"] is False
    for trace in traces:
        for i, frame in enumerate(trace["frames"]):
            frame["world_age_tick"] = 20 + 8 * i
    result = review_paired_start(traces)
    assert result["claimed_world_age_delta_parity_possible"] is True
    assert result["native_world_age_authenticity_verified"] is False
    assert result["independent_golden_clone_bytes_verified"] is False
    traces[1]["frames"][-1]["world_age_tick"] += 1
    assert review_paired_start(traces)["claimed_world_age_delta_parity_possible"] is False


def test_v6_r_pairs_require_same_start_distinct_sessions_and_all_arms():
    traces = [
        _trace(phase=regime, arm=arm, sid=f"s-{regime}-{arm}")
        for regime in ENERGIES for arm in ARMS
    ]
    for change in (
        lambda x: x.pop(),
        lambda x: x[1].update(world_start_slot="WORLD_START_B"),
        lambda x: x[1].update(native_session=x[0]["native_session"]),
        lambda x: x[1].update(arm=x[0]["arm"], regime=x[0]["regime"]),
    ):
        rows = deepcopy(traces)
        change(rows)
        with pytest.raises(V6ClockRejected):
            review_paired_start(rows)


def test_v6_r_clone_check_requires_real_existing_unique_stopped_worlds(tmp_path):
    with pytest.raises(V6ClockRejected, match="one to 48"):
        check_stopped_clones(
            tmp_path / "jar", tmp_path / "golden", tmp_path / "manifest",
            tmp_path / "original", (),
        )
    with pytest.raises(V6ClockRejected):
        check_stopped_clones(
            tmp_path / "jar", tmp_path / "golden", tmp_path / "manifest",
            tmp_path / "original", (tmp_path / "missing",),
        )
