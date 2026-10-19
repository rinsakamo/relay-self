"""W4-HANDOFF async simulation; never starts Java or Node."""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from adapters.mineflayer.self_world_stage_w4_handoff import simulate_w4_handoff
from adapters.mineflayer.self_world_stage_w4_preflight import W4PreworldBlocked
from test_self_world_stage_w4_window import TOKEN, _sample


def _run(*, marker_mode="normal", seen_tokens=frozenset(), closed=True, **overrides):
    before, after, _commands, kwargs, original_closed = _sample()
    options = dict(
        expected_session=kwargs["expected_session"],
        before_request_id=kwargs["before_request_id"],
        after_request_id=kwargs["after_request_id"],
        minimum_seq=kwargs["minimum_seq"],
        slot=1, one_time_token=TOKEN,
        seen_tokens=seen_tokens,
        marker_mode=marker_mode,
        closed=original_closed if closed else None,
    )
    options.update(overrides)
    return asyncio.run(simulate_w4_handoff(before, after, **options))


def test_fake_single_reader_write_marker_after_probe_s16_join():
    result = _run()
    assert result["schema"] == "W4_WIN_HANDOFF_SYNTHETIC_DEV_V0"
    assert result["native_probe_deliveries"] == 2
    assert result["native_reader_owners"] == 1
    assert result["java_stdout_consumers"] == 0
    assert result["physical_server_commands_sent"] == 0
    assert result["synthetic_server_write_records"] == 2
    assert [r["name"] for r in result["world_window"]["events"]] == [
        "native_before_probe", "server_summon_write",
        "server_summon_drain", "server_confirm_write",
        "server_confirm_drain", "server_stdout_marker",
        "native_after_probe",
    ]
    assert result["original_s16_stage_s_join"]["original_s16_stage_s"][
        "stage_s_direction"
    ] == "hold"
    assert result["placement_window"] == "UNATTESTED_PREWORLD_BLOCKED"
    assert result["evidence_scope"] == "SYNTHETIC_OFFLINE_ONLY"
    assert not result["real_world_attested"]
    assert not result["physical_run_permitted"]
    assert not result["s10_permission"]
    assert not result["science_qualified"]


@pytest.mark.parametrize("fault", ("missing", "duplicate", "wrong", "partial"))
def test_absent_duplicate_wrong_partial_marker_prevents_delivery(fault):
    with pytest.raises(W4PreworldBlocked):
        _run(marker_mode=fault)


def test_reused_token_rejected_at_preflight():
    with pytest.raises(W4PreworldBlocked):
        _run(seen_tokens=frozenset({TOKEN}))


@pytest.mark.parametrize("corruption", (
    "foreign_session", "bad_before_probe", "post_replay",
    "same_request", "negative_cursor", "foreign_closure", "wrong_slot",
))
def test_invalid_source_or_original_action_cannot_cross_barrier(corruption):
    before, after, _, kwargs, closed = _sample()
    opts = dict(
        expected_session=kwargs["expected_session"],
        before_request_id=kwargs["before_request_id"],
        after_request_id=kwargs["after_request_id"],
        minimum_seq=kwargs["minimum_seq"],
        slot=1, one_time_token=TOKEN, seen_tokens=frozenset(),
        closed=closed,
    )
    if corruption == "foreign_session":
        opts["expected_session"] = "wrong-session"
    elif corruption == "bad_before_probe":
        opts["before_request_id"] = "wrong-request"
    elif corruption == "post_replay":
        after = replace(after, seq=before.seq)
    elif corruption == "same_request":
        opts["after_request_id"] = opts["before_request_id"]
    elif corruption == "negative_cursor":
        opts["minimum_seq"] = -1
    elif corruption == "foreign_closure":
        opts["closed"] = replace(
            closed, original_probe=replace(closed.original_probe, session_id="foreign")
        )
    elif corruption == "wrong_slot":
        opts["slot"] = 0
    with pytest.raises(W4PreworldBlocked):
        asyncio.run(simulate_w4_handoff(before, after, **opts))


def test_readonly_preclosure_candidate_keeps_authority_disabled():
    receipt = _run(closed=False)
    assert receipt["original_s16_stage_s_join"] is None
    assert receipt["world_window"]["placement_window"] == (
        "DEV_PRODUCER_CONTENT_CORRELATED_ONLY"
    )
    assert receipt["physical_server_commands_sent"] == 0
    assert not receipt["s10_permission"]
