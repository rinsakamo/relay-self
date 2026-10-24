"""W4-WIN offline placement-order contract tests; no server/Action launches."""
from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from adapters.mineflayer.self_world_stage_w4_preflight import (
    W4PreworldBlocked,
    plan_native_nh1_placement,
)
from adapters.mineflayer.self_world_stage_w4_window import (
    W4WindowEvent,
    build_w4_window_commands,
    reconcile_w4_window_offline,
)
from test_self_world_stage_w4 import _oriented_closed

TOKEN = "ab12cd34ef56ab12cd34ef56"


def _sample():
    staging, closed = _oriented_closed()
    # Between the far stimulus and fresh near summon the old zombie is gone;
    # no new target can exist before its experimenter command.
    coverage = replace(
        staging.snapshot.nearby_entities_coverage,
        candidate_count=0, truncated=False,
    )
    staging = replace(staging, snapshot=replace(
        staging.snapshot, nearby_entities=(),
        nearby_entities_coverage=coverage,
    ))
    after = closed.original_probe
    planned = plan_native_nh1_placement(
        staging, expected_session=staging.session_id,
        expected_request_id=staging.request_id, before_seq=after.seq, slot=1,
    )
    commands = build_w4_window_commands(
        planned, one_time_token=TOKEN, seen_tokens=frozenset(),
    )
    names = (
        "native_before_probe", "server_summon_write",
        "server_summon_drain", "server_confirm_write",
        "server_confirm_drain", "server_stdout_marker",
        "native_after_probe",
    )
    contents = (
        staging.provenance.reference,
        commands.summon_sha256, commands.summon_sha256,
        commands.confirm_sha256, commands.confirm_sha256,
        f"[19:00:00] [Server thread/INFO]: {commands.expected_log_suffix}",
        after.provenance.reference,
    )
    sources = (
        "sole_native_reader", "existing_world_experimenter",
        "existing_world_experimenter", "existing_world_experimenter",
        "existing_world_experimenter", "existing_server_console_collector",
        "sole_native_reader",
    )
    events = tuple(
        W4WindowEvent(name, i + 10, 1_000 + 10 * i, source, content,
                      server_pid=1234 if 1 <= i <= 5 else None)
        for i, (name, source, content) in enumerate(zip(names, sources, contents))
    )
    kwargs = dict(
        expected_session=staging.session_id,
        before_request_id=staging.request_id,
        after_request_id=after.request_id,
        minimum_seq=staging.seq, slot=1,
        one_time_token=TOKEN, events=events, seen_tokens=frozenset(),
    )
    return staging, after, commands, kwargs, closed


def test_two_command_handshake_only_world_staging_and_readback():
    before, after, commands, kwargs, _closed = _sample()
    assert commands.slot == 1
    assert commands.marker_tag in commands.summon_command
    assert 'Tags:["w4nh1_' in commands.summon_command
    assert 'run say W4NH1_READY_' in commands.confirm_command
    assert "execute if entity" in commands.confirm_command
    assert commands.summon_command.startswith("summon minecraft:zombie ")
    assert "back" not in commands.summon_command
    assert "tp " not in commands.summon_command
    assert commands.summon_sha256 == hashlib.sha256(
        (commands.summon_command + "\n").encode(),
    ).hexdigest()
    assert not commands.physical_run_permitted

    receipt = reconcile_w4_window_offline(before, after, **kwargs)
    assert receipt["placement_window"] == "DEV_PRODUCER_CONTENT_CORRELATED_ONLY"
    assert receipt["observed_zombie_id"] == after.snapshot.nearby_entities[0].entity_id
    assert receipt["before_source"] == before.provenance.reference
    assert receipt["after_source"] == after.provenance.reference
    assert receipt["world_commands"]["marker_tag"] == commands.marker_tag
    assert not receipt["command_dispatch_attested"]
    assert not receipt["server_log_independently_attested"]
    assert not receipt["sole_reader_independently_attested"]
    assert not receipt["physical_run_permitted"]
    assert not receipt["s10_permission"]
    assert not receipt["science_qualified"]


@pytest.mark.parametrize("attack", (
    "missing_log", "wrong_log", "echoed_command", "two_lines",
    "event_reordered", "event_omitted", "equal_time", "time_reversed",
    "bad_seq", "same_reader_forged", "foreign_pid", "foreign_server_source",
    "summon_hash", "confirm_hash", "different_native_after",
    "different_post_request", "same_post_request", "foreign_session",
    "post_before_pre", "stale_cursor", "missing_target", "multiple_targets",
    "reused_entity", "wrong_coordinates", "truncated_registry",
    "legacy_orientation", "missing_token", "invalid_token",
    "wrong_slot", "fake_event", "non_tuple_events", "missing_clock",
))
def test_offline_window_content_negative_controls(attack):
    before, after, _commands, kwargs, _closed = _sample()
    events = list(kwargs["events"])
    if attack == "missing_log":
        events[5] = replace(events[5], content="")
    elif attack == "wrong_log":
        events[5] = replace(events[5], content=events[5].content + "-WRONG")
    elif attack == "echoed_command":
        events[5] = replace(events[5], content=kwargs["events"][3].content)
    elif attack == "two_lines":
        events[5] = replace(events[5], content=events[5].content + "\nspoof")
    elif attack == "event_reordered":
        events[3], events[4] = events[4], events[3]
    elif attack == "event_omitted":
        events.pop(3)
    elif attack == "equal_time":
        events[3] = replace(events[3], monotonic_ns=events[2].monotonic_ns)
    elif attack == "time_reversed":
        events[3] = replace(events[3], order=events[2].order)
    elif attack == "bad_seq":
        events[-1] = replace(events[-1], content="session-1:999")
    elif attack == "same_reader_forged":
        events[0] = replace(events[0], source="second_reader")
    elif attack == "foreign_pid":
        events[3] = replace(events[3], server_pid=999)
    elif attack == "foreign_server_source":
        events[5] = replace(events[5], source="invented_collector")
    elif attack == "summon_hash":
        events[1] = replace(events[1], content="0"*64)
    elif attack == "confirm_hash":
        events[4] = replace(events[4], content="0"*64)
    elif attack == "different_native_after":
        events[-1] = replace(events[-1], content=before.provenance.reference)
    elif attack == "different_post_request":
        kwargs["after_request_id"] = "not-the-probe"
    elif attack == "same_post_request":
        kwargs["after_request_id"] = kwargs["before_request_id"]
    elif attack == "foreign_session":
        kwargs["expected_session"] = "other"
    elif attack == "post_before_pre":
        after = replace(after, seq=before.seq)
    elif attack == "stale_cursor":
        kwargs["minimum_seq"] = before.seq + 1
    elif attack == "missing_target":
        coverage = replace(after.snapshot.nearby_entities_coverage,
                           candidate_count=0, truncated=False)
        after = replace(after, snapshot=replace(
            after.snapshot, nearby_entities=(), nearby_entities_coverage=coverage,
        ))
    elif attack == "multiple_targets":
        one = after.snapshot.nearby_entities[0]
        after = replace(after, snapshot=replace(
            after.snapshot,
            nearby_entities=(one, replace(one, entity_id=one.entity_id + 100)),
            nearby_entities_coverage=replace(
                after.snapshot.nearby_entities_coverage, candidate_count=2,
            ),
        ))
    elif attack == "reused_entity":
        before = replace(before, snapshot=replace(
            before.snapshot,
            nearby_entities=after.snapshot.nearby_entities,
            nearby_entities_coverage=after.snapshot.nearby_entities_coverage,
        ))
    elif attack == "wrong_coordinates":
        one = after.snapshot.nearby_entities[0]
        shifted = replace(one.position, x=one.position.x + 1)
        after = replace(after, snapshot=replace(
            after.snapshot,
            nearby_entities=(replace(one, position=shifted),),
        ))
    elif attack == "truncated_registry":
        cov = after.snapshot.nearby_entities_coverage
        target = after.snapshot.nearby_entities[0]
        others = tuple(
            replace(target, entity_id=target.entity_id + i, name="item",
                    entity_type="other")
            for i in range(1, cov.max_entities)
        )
        after = replace(after, snapshot=replace(
            after.snapshot,
            nearby_entities=(target,) + others,
            nearby_entities_coverage=replace(
                cov, candidate_count=cov.max_entities + 1,
                truncated=True,
            ),
        ))
    elif attack == "legacy_orientation":
        from dataclasses import fields

        from adapters.mineflayer.python_protocol import MineflayerSnapshot

        after = replace(after, snapshot=MineflayerSnapshot(
            **{f.name: getattr(after.snapshot, f.name)
               for f in fields(MineflayerSnapshot)}
        ))
    elif attack == "missing_token":
        kwargs["one_time_token"] = ""
    elif attack == "invalid_token":
        kwargs["one_time_token"] = "bad token\n"
    elif attack == "wrong_slot":
        kwargs["slot"] = 0
    elif attack == "fake_event":
        events[3] = None
    elif attack == "non_tuple_events":
        kwargs["events"] = events
    elif attack == "missing_clock":
        events[3] = replace(events[3], monotonic_ns=None)
    if attack != "non_tuple_events":
        kwargs["events"] = tuple(events)
    with pytest.raises(W4PreworldBlocked):
        reconcile_w4_window_offline(before, after, **kwargs)


def test_window_token_is_per_slot_and_no_cross_slot_reuse():
    before, after, _, _kwargs, _closed = _sample()
    slot1 = plan_native_nh1_placement(
        before, expected_session=before.session_id,
        expected_request_id=before.request_id, before_seq=after.seq, slot=1,
    )
    slot2 = plan_native_nh1_placement(
        before, expected_session=before.session_id,
        expected_request_id=before.request_id, before_seq=after.seq, slot=2,
    )
    a = build_w4_window_commands(slot1, one_time_token=TOKEN,
                                 seen_tokens=frozenset())
    spent = frozenset({TOKEN})
    with pytest.raises(W4PreworldBlocked):
        build_w4_window_commands(slot2, one_time_token=TOKEN, seen_tokens=spent)
    second_token = "ff12cd34ef56ab12cd34ef56"
    b = build_w4_window_commands(slot2, one_time_token=second_token,
                                 seen_tokens=spent)
    assert a.marker_tag != b.marker_tag
    assert a.confirmation_marker != b.confirmation_marker
    assert a.summon_command != b.summon_command
    assert not a.physical_run_permitted and not b.physical_run_permitted


def test_offline_window_joins_original_s16_and_frozen_stage_s_without_grant():
    from adapters.mineflayer.self_world_stage_w4_window import (
        join_w4_window_and_s16_offline,
    )

    before, after, _, kwargs, closed = _sample()
    assert closed.original_probe == after
    result = join_w4_window_and_s16_offline(
        before, closed, expected_session=kwargs["expected_session"],
        before_request_id=kwargs["before_request_id"],
        minimum_seq=kwargs["minimum_seq"], slot=kwargs["slot"],
        one_time_token=kwargs["one_time_token"], events=kwargs["events"],
        seen_tokens=kwargs["seen_tokens"],
    )
    assert result["original_s16_stage_s"]["stage_s_direction"] == "hold"
    assert result["window"]["after_source"] == after.provenance.reference
    assert result["placement_window"] == "UNATTESTED_PREWORLD_BLOCKED"
    assert not result["s10_permission"]
    assert not result["physical_run_permitted"]


def test_offline_window_rejects_swapped_original_s16_probe():
    from adapters.mineflayer.self_world_stage_w4_window import (
        join_w4_window_and_s16_offline,
    )

    before, _, _, kwargs, closed = _sample()
    corrupt = replace(closed, original_probe=replace(
        closed.original_probe, seq=closed.original_probe.seq + 9,
    ))
    with pytest.raises(W4PreworldBlocked):
        join_w4_window_and_s16_offline(
            before, corrupt, expected_session=kwargs["expected_session"],
            before_request_id=kwargs["before_request_id"],
            minimum_seq=kwargs["minimum_seq"], slot=kwargs["slot"],
            one_time_token=kwargs["one_time_token"], events=kwargs["events"],
            seen_tokens=kwargs["seen_tokens"],
        )


@pytest.mark.parametrize("component", ("window", "join"))
def test_repeated_window_token_rejected(component):
    before, after, _, kwargs, closed = _sample()
    kwargs["seen_tokens"] = frozenset({TOKEN})
    with pytest.raises(W4PreworldBlocked):
        if component == "window":
            reconcile_w4_window_offline(before, after, **kwargs)
        else:
            from adapters.mineflayer.self_world_stage_w4_window import (
                join_w4_window_and_s16_offline,
            )

            join_w4_window_and_s16_offline(
                before, closed, expected_session=kwargs["expected_session"],
                before_request_id=kwargs["before_request_id"],
                minimum_seq=kwargs["minimum_seq"], slot=kwargs["slot"],
                one_time_token=kwargs["one_time_token"], events=kwargs["events"],
                seen_tokens=kwargs["seen_tokens"],
            )


def test_missing_token_ledger_is_a_hard_block():
    before, after, _, kwargs, closed = _sample()
    del kwargs["seen_tokens"]
    with pytest.raises(W4PreworldBlocked):
        reconcile_w4_window_offline(before, after, **kwargs)
    from adapters.mineflayer.self_world_stage_w4_window import (
        join_w4_window_and_s16_offline,
    )

    with pytest.raises(W4PreworldBlocked):
        join_w4_window_and_s16_offline(
            before, closed, expected_session=kwargs["expected_session"],
            before_request_id=kwargs["before_request_id"],
            minimum_seq=kwargs["minimum_seq"], slot=kwargs["slot"],
            one_time_token=kwargs["one_time_token"], events=kwargs["events"],
        )
