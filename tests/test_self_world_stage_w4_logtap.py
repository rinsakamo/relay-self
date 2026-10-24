"""W4-WIN tests for tailing the existing server log, never Java stdout."""
from __future__ import annotations

import asyncio
import hashlib
import os
from dataclasses import replace
from pathlib import Path

import pytest

from adapters.mineflayer.self_world_stage_w4_logtap import (
    capture_w4_collector_cursor,
    marker_as_w4_window_event,
    wait_for_w4_collector_marker,
)
from adapters.mineflayer.self_world_stage_w4_preflight import W4PreworldBlocked
from adapters.mineflayer.self_world_stage_w4_window import reconcile_w4_window_offline
from test_self_world_stage_w4_window import _sample


def _line(commands) -> bytes:
    return (
        f"[19:00:00] [Server thread/INFO]: {commands.expected_log_suffix}\n"
    ).encode("utf-8")


def _observe(tmp_path, *, payload: bytes | None = None, old_content: bytes = b"",
             partial: bool = False):
    _before, _after, commands, _kwargs, _closed = _sample()
    path = tmp_path / "existing-single-collector.log"
    path.write_bytes(old_content)
    cursor = capture_w4_collector_cursor(path)
    data = _line(commands) if payload is None else payload

    async def test():
        async def existing_collector_appends():
            await asyncio.sleep(0.005)
            with path.open("ab") as file:
                if partial:
                    file.write(data[:len(data) // 2])
                    file.flush()
                    await asyncio.sleep(0.005)
                    file.write(data[len(data) // 2:])
                else:
                    file.write(data)
                file.flush()

        task = asyncio.create_task(existing_collector_appends())
        try:
            return await wait_for_w4_collector_marker(
                cursor, commands, timeout_s=0.1, poll_s=0.001,
            )
        finally:
            await task

    return asyncio.run(test()), cursor, commands


def test_cursor_is_pre_dispatch_and_ignores_old_complete_marker(tmp_path):
    _, _, commands, _, _ = _sample()
    old = _line(commands)
    marker, cursor, _ = _observe(tmp_path, old_content=old)
    assert cursor.start_byte == len(old)
    assert marker.start_byte == len(old)
    assert marker.end_byte == len(old) * 2
    assert marker.raw_line_sha256 == hashlib.sha256(old).hexdigest()
    assert marker.log_line == old.decode().rstrip("\n")
    assert marker.producer_content_only
    assert not marker.external_source_qualified
    assert not marker.physical_run_permitted


def test_single_complete_marker_after_concurrent_partial_write(tmp_path):
    marker, cursor, commands = _observe(tmp_path, partial=True)
    assert marker.start_byte == cursor.start_byte
    assert marker.log_line.endswith(commands.expected_log_suffix)
    assert marker.end_byte > marker.start_byte


def test_file_log_marker_can_join_original_single_reader_window_offline(tmp_path):
    before, after, _commands, kwargs, _closed = _sample()
    marker, _, commands = _observe(tmp_path)
    events = list(kwargs["events"])
    base = marker.read_monotonic_ns
    for i, original in enumerate(events):
        ns = base + (i - 5) * 1000
        events[i] = replace(original, monotonic_ns=ns)
    events[5] = marker_as_w4_window_event(
        marker, order=events[5].order, server_pid=1234,
    )
    receipt = reconcile_w4_window_offline(
        before, after, **{**kwargs, "events": tuple(events)}
    )
    assert receipt["world_commands"]["confirmation_marker"] == commands.confirmation_marker
    assert receipt["events"][5]["content"] == marker.log_line
    assert receipt["placement_window"] == "DEV_PRODUCER_CONTENT_CORRELATED_ONLY"
    assert not receipt["server_log_independently_attested"]
    assert not receipt["physical_run_permitted"]
    assert not receipt["s10_permission"]


@pytest.mark.parametrize("attack", (
    "wrong_marker", "no_newline", "duplicate_marker", "newline_injection",
    "input_echo", "invalid_utf8", "old_only", "oversized",
))
def test_unqualified_collector_content_rejected(tmp_path, attack):
    _, _, commands, _, _ = _sample()
    line = _line(commands)
    payload = line
    old = b""
    if attack == "wrong_marker":
        payload = line.replace(b"_S1", b"_S2")
    elif attack == "no_newline":
        payload = line[:-1]
    elif attack == "duplicate_marker":
        payload = line + line
    elif attack == "newline_injection":
        payload = line.replace(b"INFO]:", b"INFO]:\r")
    elif attack == "input_echo":
        payload = (commands.confirm_command + "\n").encode()
    elif attack == "invalid_utf8":
        payload = b"\xff\n" + line
    elif attack == "old_only":
        old, payload = line, b""
    elif attack == "oversized":
        payload = b"x" * 65_537 + line
    with pytest.raises(W4PreworldBlocked):
        _observe(tmp_path, payload=payload, old_content=old)


def test_collector_log_replacement_after_cursor_fails_closed(tmp_path):
    _, _, commands, _, _ = _sample()
    path = tmp_path / "collector.log"
    path.write_bytes(b"old\n")
    cursor = capture_w4_collector_cursor(path)
    path.rename(tmp_path / "old-collector.log")
    path.write_bytes(_line(commands))
    with pytest.raises(W4PreworldBlocked, match="replaced"):
        asyncio.run(wait_for_w4_collector_marker(
            cursor, commands, timeout_s=0.02, poll_s=0.001,
        ))


def test_collector_truncation_after_cursor_fails_closed(tmp_path):
    _, _, commands, _, _ = _sample()
    path = tmp_path / "collector.log"
    path.write_bytes(b"old-byte-content-longer-than-marker\n")
    cursor = capture_w4_collector_cursor(path)
    path.write_bytes(b"")
    with pytest.raises(W4PreworldBlocked, match="truncated"):
        asyncio.run(wait_for_w4_collector_marker(
            cursor, commands, timeout_s=0.02, poll_s=0.001,
        ))


@pytest.mark.parametrize("attack", ("symlink", "hardlink", "relative"))
def test_unsafe_collector_log_path_rejected(tmp_path, attack):
    path = tmp_path / "collector.log"
    path.write_bytes(b"line\n")
    if attack == "symlink":
        alias = tmp_path / "log-link"
        alias.symlink_to(path)
    elif attack == "hardlink":
        alias = tmp_path / "log-hardlink"
        os.link(path, alias)
    else:
        alias = Path("relative-collector.log")
    with pytest.raises(W4PreworldBlocked):
        capture_w4_collector_cursor(alias)


def test_unsafe_marker_conversion_rejected(tmp_path):
    marker, _, _ = _observe(tmp_path)
    with pytest.raises(W4PreworldBlocked):
        marker_as_w4_window_event(marker, order=True, server_pid=1234)
    with pytest.raises(W4PreworldBlocked):
        marker_as_w4_window_event(marker, order=6, server_pid=0)


def test_old_unterminated_log_line_cannot_prefix_future_marker(tmp_path):
    _, _, commands, _, _ = _sample()
    path = tmp_path / "existing-collector.log"
    path.write_bytes(b"[19:00:00] [Server thread/INFO]: attacker prefix")
    with pytest.raises(W4PreworldBlocked, match="unfinished line"):
        capture_w4_collector_cursor(path)
    # Complete previous unrelated logs are admissible, but never old markers.
    path.write_bytes(b"[19:00:00] [Server thread/INFO]: old unrelated\\n".replace(
        b"\\n", b"\n",
    ))
    cursor = capture_w4_collector_cursor(path)
    assert cursor.start_byte == path.stat().st_size
