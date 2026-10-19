"""W4 original-owner interface tests. No client or server handles."""
from __future__ import annotations

import asyncio
import hashlib
from dataclasses import asdict

import pytest

from adapters.mineflayer.self_world_stage_w4_logtap import (
    W4CollectorCursor,
    W4CollectorMarker,
)
from adapters.mineflayer.self_world_stage_w4_owner_contract import (
    W4OwnerHandoffGate,
)
from adapters.mineflayer.self_world_stage_w4_preflight import W4PreworldBlocked
from test_self_world_stage_w4_window import TOKEN, _sample


def _values():
    pre, post, _, _, _ = _sample()
    owner = object()
    gate = W4OwnerHandoffGate(session_id=pre.session_id, native_owner=owner)
    return pre, post, gate, owner


def _before(gate, owner, pre, *, token=TOKEN, origin="s49_original_owner_pre_world"):
    return gate.before_world(
        pre, owner=owner, request_id=pre.request_id, slot=1,
        token=token, origin=origin,
    )


def _mark(gate, owner, commands):
    from pathlib import Path

    cursor = W4CollectorCursor(Path("/synthetic/log"), 1, 2, 100)
    line = f"[19:00] [Server thread/INFO]: {commands.expected_log_suffix}"
    raw = (line + "\n").encode("utf-8")
    marker = W4CollectorMarker(
        cursor, line,
        100, 100 + len(raw), hashlib.sha256(raw).hexdigest(), 200,
    )
    gate.observe_existing_collector_marker(marker, owner=owner)
    return marker


def test_owner_sequence_preserves_readonly_and_exact_two_probes():
    pre, post, gate, owner = _values()
    commands = _before(gate, owner, pre)
    assert gate.phase == "AWAIT_MARKER"
    _mark(gate, owner, commands)
    assert gate.phase == "AWAIT_POST_PROBE"
    receipt = gate.after_world(post, owner=owner, request_id=post.request_id)
    assert gate.phase == "IDLE"
    assert receipt.pre_source == pre.provenance.reference
    assert receipt.post_source == post.provenance.reference
    assert receipt.slot == 1
    assert not receipt.owner_attested
    assert not receipt.physical_run_permitted
    assert not receipt.s10_permission
    assert asdict(receipt)["placement_window"] == "UNATTESTED_PREWORLD_BLOCKED"


@pytest.mark.parametrize("bad", (
    "post_as_pre", "foreign_owner", "wrong_origin", "double_pre",
    "marker_first", "post_before_marker", "foreign_marker_owner",
    "missing_marker", "post_replay", "foreign_after_owner",
    "same_request", "stale_pre", "invalid_token",
))
def test_owner_boundary_fail_closed(bad):
    pre, post, gate, owner = _values()
    foreign = object()
    if bad == "marker_first":
        with pytest.raises(W4PreworldBlocked):
            _mark(gate, owner, _sample()[2])
    elif bad == "post_as_pre":
        with pytest.raises(W4PreworldBlocked):
            _before(gate, owner, pre, origin="s49_post_entity_reprobe")
    elif bad == "foreign_owner":
        with pytest.raises(W4PreworldBlocked):
            _before(gate, foreign, pre)
    elif bad == "wrong_origin":
        with pytest.raises(W4PreworldBlocked):
            _before(gate, owner, pre, origin="caller_pre_world")
    elif bad == "stale_pre":
        commands = _before(gate, owner, pre)
        _mark(gate, owner, commands)
        gate.after_world(post, owner=owner, request_id=post.request_id)
        with pytest.raises(W4PreworldBlocked):
            _before(gate, owner, pre)
    elif bad == "invalid_token":
        with pytest.raises(W4PreworldBlocked):
            _before(gate, owner, pre, token="garbage")
    else:
        commands = _before(gate, owner, pre)
        if bad == "double_pre":
            with pytest.raises(W4PreworldBlocked):
                _before(gate, owner, pre)
        elif bad == "foreign_marker_owner":
            with pytest.raises(W4PreworldBlocked):
                _mark(gate, foreign, commands)
        elif bad == "post_before_marker":
            with pytest.raises(W4PreworldBlocked):
                gate.after_world(post, owner=owner, request_id=post.request_id)
        elif bad == "missing_marker":
            gate.abort(owner=owner)
        else:
            _mark(gate, owner, commands)
            if bad == "post_replay":
                with pytest.raises(W4PreworldBlocked):
                    gate.after_world(pre, owner=owner, request_id=pre.request_id)
            elif bad == "foreign_after_owner":
                with pytest.raises(W4PreworldBlocked):
                    gate.after_world(post, owner=foreign, request_id=post.request_id)
            elif bad == "same_request":
                with pytest.raises(W4PreworldBlocked):
                    gate.after_world(post, owner=owner, request_id=pre.request_id)
    assert gate.phase == "BLOCKED"
    with pytest.raises(W4PreworldBlocked):
        _before(gate, owner, pre)


def test_after_owner_token_reuse_rejected_across_slots():
    pre, post, gate, owner = _values()
    commands = _before(gate, owner, pre)
    _mark(gate, owner, commands)
    gate.after_world(post, owner=owner, request_id=post.request_id)
    with pytest.raises(W4PreworldBlocked):
        _before(gate, owner, pre)
    assert gate.phase == "BLOCKED"


def test_no_port_handles_or_background_tasks_created():
    pre, post, gate, owner = _values()
    assert not hasattr(gate, "session") and not hasattr(gate, "server")
    before_count = len(asyncio.all_tasks()) if _in_loop() else 0
    commands = _before(gate, owner, pre)
    _mark(gate, owner, commands)
    gate.after_world(post, owner=owner, request_id=post.request_id)
    assert before_count == 0


def _in_loop():
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


@pytest.mark.parametrize("tamper", ("sha", "span", "line", "duplicate_marker"))
def test_reject_mutated_existing_collector_marker(tamper):
    from dataclasses import replace

    pre, _post, gate, owner = _values()
    commands = _before(gate, owner, pre)
    cursor = W4CollectorCursor(__import__("pathlib").Path("/synthetic/log"), 1, 2, 100)
    line = f"[19:00] [Server thread/INFO]: {commands.expected_log_suffix}"
    raw = (line + "\n").encode("utf-8")
    marker = W4CollectorMarker(
        cursor, line, 100, 100 + len(raw),
        hashlib.sha256(raw).hexdigest(), 200,
    )
    if tamper == "sha":
        marker = replace(marker, raw_line_sha256="0" * 64)
    elif tamper == "span":
        marker = replace(marker, end_byte=marker.end_byte + 1)
    elif tamper == "line":
        marker = replace(marker, log_line=marker.log_line + "unexpected")
    else:
        marker = replace(marker, log_line=marker.log_line.replace(
            commands.confirmation_marker,
            commands.confirmation_marker + commands.confirmation_marker,
        ))
    with pytest.raises(W4PreworldBlocked):
        gate.observe_existing_collector_marker(marker, owner=owner)
    assert gate.phase == "BLOCKED"
