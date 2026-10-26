"""Explicit World-second units, no fabricated M0 basal debit or WAIT."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.s49_m0_world_time_shadow_dev import (
    M0WorldRateDev,
    WorldTimeM0ShadowRejected,
    project_s49_world_time_m0_shadow_dev,
)

A = "s49-native-move-19"
S = "offline-native-session"


def source():
    bracket = {
        "classification": "PAPER_LOCAL_ARM_TICK_RELEASE_BRACKET_DEV_ONLY",
        "action_id": A, "session_id": S,
        "world_uuid": "11111111-2222-4333-8444-555555555555",
        "arm_tick": 244, "first_tick": 245, "last_tick": 257,
        "release_tick": 258, "elapsed_callbacks": 13,
        "original_owner_release": True, "independent_source_attested": False,
        "mineflayer_paper_tick_synchronized": False,
    }
    passive = {
        "classification": "PAPER_PASSIVE_POST_RELEASE_TRANSLATION_DEV_ONLY",
        "action_id": A, "session_id": S,
        "first_sample_tick": 259, "last_sample_tick": 263,
        "paper_callbacks": 5, "WAIT_sourcebound_admitted": False,
        "action_authority": False, "speed_modifier_present": False,
        "P1_posted": False, "M0_posted": False,
    }
    edges = {
        "classification": "S49_NATIVE_ACK_TO_PAPER_MARKER_DELIVERY_DEV_ONLY",
        "action_id": A, "session_id": S,
        "paper_release_tick": 258,
        "marker_after_native_ack": True, "native_single_reader": True,
        "client_effect_world_tick_attested": False,
    }
    fingerprint = {
        "classification": "S49_NODE_PAPER_CONSECUTIVE_TRANSLATION_FOOTPRINT_DEV_ONLY",
        "action_id": A, "session_id": S,
        "two_producer_local_motion_views_consistent": True,
        "native_Paper_tick_correspondence_attested": False,
        "physical_WAIT_qualified": False,
        "P1_posted": False, "M0_posted": False,
    }
    original = [
        {
            "action_id": A, "session_id": S, "m0_tick_before": 0,
            "m0_tick_after": 1, "basal_debit": .5, "move_debit": .25,
            "dash_extra_debit": .08633238849069515,
            "energy_before": 12, "energy_after": 11.163667611509306,
            "source_scope": "S49_NATIVE_ACTION_M0_STEP_DEV_NOT_WORLD_TICK",
        },
        {
            "action_id": A + "-second", "session_id": S, "m0_tick_before": 1,
            "m0_tick_after": 2, "basal_debit": .5, "move_debit": .25,
            "dash_extra_debit": 0, "energy_before": 11.163667611509306,
            "energy_after": 10.413667611509306,
            "source_scope": "S49_NATIVE_ACTION_M0_STEP_DEV_NOT_WORLD_TICK",
        },
    ]
    return {
        "action_id": A, "session_id": S,
        "paper_action_bracket": bracket,
        "passive_post_release": passive,
        "native_edges": edges,
        "node_paper_moving_footprint": fingerprint,
        "original_m0_postings": original,
        "original_energy_remaining": 10.413667611509306,
        "rate": M0WorldRateDev(basal_energy_per_world_second=.5),
    }


def test_explicit_world_seconds_preserve_disjoint_observation_and_original_energy():
    inp = source()
    before = deepcopy(inp["original_m0_postings"])
    r = project_s49_world_time_m0_shadow_dev(**inp)
    assert r["classification"] == "M0_PAPER_WORLD_TICK_BASAL_SHADOW_NOT_POSTED_DEV_ONLY"
    assert r["world_ticks_per_world_second"] == 20
    assert r["explicit_basal_energy_per_world_second"] == .5
    assert r["basal_energy_per_observed_world_tick"] == .025
    assert r["original_action_observed_interval"] == [245, 257]
    assert r["original_action_observed_ticks"] == 13
    assert r["passive_post_release_observed_interval"] == [259, 263]
    assert r["passive_post_release_observed_ticks"] == 5
    assert r["unsampled_between_intervals_ticks"] == 1
    assert r["unsampled_between_intervals_billed"] is False
    assert r["observed_distinct_world_ticks"] == 18
    assert r["observed_normalized_world_seconds"] == pytest.approx(.9)
    assert r["active_window_basal_projection"] == pytest.approx(.325)
    assert r["passive_window_basal_projection"] == pytest.approx(.125)
    assert r["combined_basal_projection_not_posted"] == pytest.approx(.450)
    assert r["original_action_basal_posted"] == 1.0
    assert r["original_energy_remaining_unchanged"] == pytest.approx(10.413667611509306)
    assert r["legacy_action_m0_replaced"] is False
    assert not r["double_charged"] and not r["world_tick_basal_posted"]
    assert not r["source_world_clock_authoritative_across_processes"]
    assert not r["wall_clock_seconds_attested"]
    assert not r["WAIT_admitted"] and not r["P1_recovery_posted"]
    assert not r["M0_posted"] and not r["qualification_go"] and not r["science_go"]
    assert inp["original_m0_postings"] == before


def test_rate_is_explicit_and_can_change_without_modifying_actual_body():
    inp = source()
    inp["rate"] = M0WorldRateDev(basal_energy_per_world_second=1.0)
    a = project_s49_world_time_m0_shadow_dev(**inp)
    assert a["combined_basal_projection_not_posted"] == pytest.approx(.9)
    assert a["original_energy_remaining_unchanged"] == 10.413667611509306


@pytest.mark.parametrize("cfg", [
    {"basal_energy_per_world_second": 0},
    {"basal_energy_per_world_second": -1},
    {"basal_energy_per_world_second": 5},
    {"basal_energy_per_world_second": float("nan")},
    {"basal_energy_per_world_second": float("inf")},
    {"basal_energy_per_world_second": True},
    {"basal_energy_per_world_second": "0.5"},
    {"basal_energy_per_world_second": .5, "world_ticks_per_world_second": 0},
    {"basal_energy_per_world_second": .5, "world_ticks_per_world_second": 200},
    {"basal_energy_per_world_second": .5, "world_ticks_per_world_second": True},
    {"basal_energy_per_world_second": .5, "calibration": "PRODUCTION_APPROVED"},
])
def test_missing_implicit_or_high_risk_rate_rejected(cfg):
    with pytest.raises(WorldTimeM0ShadowRejected):
        M0WorldRateDev(**cfg)


@pytest.mark.parametrize("corrupt", [
    "foreign_action", "foreign_paper", "foreign_edge", "foreign_fp",
    "bad_session", "fake_bracket", "fake_paper", "fake_edge", "fake_fp",
    "false_release", "independent_authority", "marker_absent", "new_reader",
    "client_tick_claim", "no_paper_owner", "minted_wait", "minted_m0",
    "minted_p1", "stale_fingerprint", "fake_tickjoin",
    "count_missing", "count_duplicate", "tick_gap", "tick_overlap",
    "release_gap", "post_early", "post_late", "wrong_count",
    "first_underrun", "false_clock_sync", "replayed_m0_action",
    "old_owner_scope", "foreign_second", "wrong_m0_tick", "wrong_m0_rate",
    "unbacked_balance", "not_owner_balance", "insufficient_energy",
])
def test_missing_replayed_or_forged_world_intervals_rejected(corrupt):
    kwargs = source()
    b = kwargs["paper_action_bracket"]
    p = kwargs["passive_post_release"]
    e = kwargs["native_edges"]
    f = kwargs["node_paper_moving_footprint"]
    m = kwargs["original_m0_postings"]
    if corrupt == "foreign_action":
        kwargs["action_id"] = "alien"
    elif corrupt == "foreign_paper":
        p["action_id"] = "alien"
    elif corrupt == "foreign_edge":
        e["action_id"] = "alien"
    elif corrupt == "foreign_fp":
        f["action_id"] = "alien"
    elif corrupt == "bad_session":
        b["session_id"] = "alien"
    elif corrupt == "fake_bracket":
        b["classification"] = "R_QUALIFIED"
    elif corrupt == "fake_paper":
        p["classification"] = "R_QUALIFIED"
    elif corrupt == "fake_edge":
        e["classification"] = "R_QUALIFIED"
    elif corrupt == "fake_fp":
        f["classification"] = "R_QUALIFIED"
    elif corrupt == "false_release":
        b["original_owner_release"] = False
    elif corrupt == "independent_authority":
        b["independent_source_attested"] = True
    elif corrupt == "marker_absent":
        e["marker_after_native_ack"] = False
    elif corrupt == "new_reader":
        e["native_single_reader"] = False
    elif corrupt == "client_tick_claim":
        e["client_effect_world_tick_attested"] = True
    elif corrupt == "no_paper_owner":
        e["paper_release_tick"] = 300
    elif corrupt == "minted_wait":
        p["WAIT_sourcebound_admitted"] = True
    elif corrupt == "minted_m0":
        p["M0_posted"] = True
    elif corrupt == "minted_p1":
        f["P1_posted"] = True
    elif corrupt == "stale_fingerprint":
        f["two_producer_local_motion_views_consistent"] = False
    elif corrupt == "fake_tickjoin":
        f["native_Paper_tick_correspondence_attested"] = True
    elif corrupt == "count_missing":
        b["elapsed_callbacks"] = 12
    elif corrupt == "count_duplicate":
        b["elapsed_callbacks"] = 14
    elif corrupt == "tick_gap":
        b["last_tick"] = 259
    elif corrupt == "tick_overlap":
        p["first_sample_tick"] = 257
    elif corrupt == "release_gap":
        b["release_tick"] = 400
        e["paper_release_tick"] = 400
        p["first_sample_tick"] = 401
        p["last_sample_tick"] = 405
    elif corrupt == "post_early":
        p["first_sample_tick"] = 258
    elif corrupt == "post_late":
        p["last_sample_tick"] = 265
    elif corrupt == "wrong_count":
        p["paper_callbacks"] = 4
    elif corrupt == "first_underrun":
        b["first_tick"] = 200
    elif corrupt == "false_clock_sync":
        b["mineflayer_paper_tick_synchronized"] = True
    elif corrupt == "replayed_m0_action":
        m[1]["action_id"] = A
    elif corrupt == "old_owner_scope":
        m[0]["source_scope"] = "PAPER_TICK_OWNER_FAKE"
    elif corrupt == "foreign_second":
        m[1]["session_id"] = "alien"
    elif corrupt == "wrong_m0_tick":
        m[1]["m0_tick_after"] = 3
    elif corrupt == "wrong_m0_rate":
        m[0]["basal_debit"] = 13 * .5
    elif corrupt == "unbacked_balance":
        m[1]["energy_before"] = 42
    elif corrupt == "not_owner_balance":
        kwargs["original_energy_remaining"] = 9
    else:
        kwargs["original_energy_remaining"] = 0
    with pytest.raises(WorldTimeM0ShadowRejected):
        project_s49_world_time_m0_shadow_dev(**kwargs)


def test_rate_immutable_and_no_mutable_ledger():
    rate = M0WorldRateDev(basal_energy_per_world_second=.5)
    with pytest.raises((AttributeError, TypeError)):
        rate.basal_energy_per_world_second = 17
    assert not hasattr(rate, "body") and not hasattr(rate, "step")
