"""W4-HANDOFF: fully simulated single-owner causal barrier (DEV only).

All ports below are internal synthetic fixtures: no Minecraft, Java process,
Mineflayer receiver, Action, or S10 issuer is opened or passed in. The returned
receipt is local producer content, never external source/custody qualification.
"""
from __future__ import annotations

import asyncio
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_world_stage_w4_logtap import (
    capture_w4_collector_cursor,
    marker_as_w4_window_event,
    wait_for_w4_collector_marker,
)
from adapters.mineflayer.self_world_stage_w4_preflight import (
    W4PreworldBlocked,
    plan_native_nh1_placement,
)
from adapters.mineflayer.self_world_stage_w4_window import (
    W4WindowEvent,
    build_w4_window_commands,
    join_w4_window_and_s16_offline,
    reconcile_w4_window_offline,
)

_OFFLINE_MODES = frozenset({"normal", "missing", "duplicate", "wrong", "partial"})


async def simulate_w4_handoff(
    before: MineflayerObservation,
    after: MineflayerObservation,
    *,
    expected_session: str,
    before_request_id: str,
    after_request_id: str,
    minimum_seq: int,
    slot: int,
    one_time_token: str,
    seen_tokens: frozenset[str],
    closed=None,
    marker_mode: str = "normal",
) -> dict:
    """Run an ordered offline barrier with entirely fake, non-injectable ports.

    `before` and `after` are supplied fixture objects, not acquired here.
    The only command destination is a newly created temporary fake log file.
    The only "world" effect is appending synthetic bytes there.
    """
    if (
        marker_mode not in _OFFLINE_MODES
        or type(seen_tokens) is not frozenset
        or not before_request_id or not after_request_id
        or before_request_id == after_request_id
    ):
        raise W4PreworldBlocked("offline handoff parameters rejected")
    placement = plan_native_nh1_placement(
        before, expected_session=expected_session,
        expected_request_id=before_request_id, before_seq=after.seq,
        slot=slot,
    )
    commands = build_w4_window_commands(
        placement, one_time_token=one_time_token, seen_tokens=seen_tokens,
    )
    # Fix one simulated native owner: exactly two probe deliveries in order.
    # Do not mutate/repair after, or infer the after event before the barrier.
    next_order = 0
    last_clock = 0
    events: list[W4WindowEvent] = []
    fake_server_pid = 4242

    def receipt(name: str, source: str, content: str, server: bool) -> None:
        nonlocal next_order, last_clock
        next_order += 1
        last_clock = max(time.monotonic_ns(), last_clock + 1)
        events.append(W4WindowEvent(
            name=name, order=next_order, monotonic_ns=last_clock,
            source=source, content=content,
            server_pid=fake_server_pid if server else None,
        ))

    receipt("native_before_probe", "sole_native_reader",
            before.provenance.reference, False)
    with tempfile.TemporaryDirectory(prefix="w4-nh1-synthetic-only-") as root:
        # Never accept a caller-supplied path or a real server/reader handle.
        path = Path(root) / "existing-collector-fake.log"
        path.write_bytes(b"[00:00:00] [Server thread/INFO]: old unrelated line\n")
        if marker_mode == "partial":
            # Only a fully newline-terminated record is acceptable.
            to_append = (
                f"[19:00:00] [Server thread/INFO]: {commands.expected_log_suffix}"
            ).encode()
        elif marker_mode == "wrong":
            to_append = b"[19:00:00] [Server thread/INFO]: [Server] WRONG\n"
        else:
            to_append = (
                f"[19:00:00] [Server thread/INFO]: {commands.expected_log_suffix}\n"
            ).encode()
        if marker_mode == "duplicate":
            to_append += to_append
        cursor = capture_w4_collector_cursor(path)

        # The commands are *recorded*, never sent to Minecraft.
        for event_name, digest in (
            ("server_summon_write", commands.summon_sha256),
            ("server_summon_drain", commands.summon_sha256),
            ("server_confirm_write", commands.confirm_sha256),
            ("server_confirm_drain", commands.confirm_sha256),
        ):
            receipt(event_name, "existing_world_experimenter", digest, True)

        async def fake_collector() -> None:
            await asyncio.sleep(0)
            if marker_mode != "missing":
                with path.open("ab") as f:
                    f.write(to_append)
                    f.flush()

        task = asyncio.create_task(fake_collector())
        try:
            marker = await wait_for_w4_collector_marker(
                cursor, commands, timeout_s=0.06, poll_s=0.001,
            )
        finally:
            await task

        next_order += 1
        # Preserve actual local log-read time, never use an invented server tick.
        if marker.read_monotonic_ns <= last_clock:
            raise W4PreworldBlocked("synthetic log observation order reversed")
        events.append(marker_as_w4_window_event(
            marker, order=next_order, server_pid=fake_server_pid,
        ))
        last_clock = marker.read_monotonic_ns

    receipt("native_after_probe", "sole_native_reader",
            after.provenance.reference, False)
    kwargs = dict(
        expected_session=expected_session,
        before_request_id=before_request_id,
        after_request_id=after_request_id,
        minimum_seq=minimum_seq,
        slot=slot,
        one_time_token=one_time_token,
        events=tuple(events),
        seen_tokens=seen_tokens,
    )
    # All integrity checks run after the two synthetic probe deliveries.
    window = reconcile_w4_window_offline(before, after, **kwargs)
    joined = None
    if closed is not None:
        joined = join_w4_window_and_s16_offline(
            before, closed,
            expected_session=expected_session,
            before_request_id=before_request_id,
            minimum_seq=minimum_seq,
            slot=slot, one_time_token=one_time_token,
            events=tuple(events), seen_tokens=seen_tokens,
        )
    return {
        "schema": "W4_WIN_HANDOFF_SYNTHETIC_DEV_V0",
        "native_probe_deliveries": 2,
        "native_reader_owners": 1,
        "java_stdout_consumers": 0,
        "physical_server_commands_sent": 0,
        "synthetic_server_write_records": 2,
        "captured_marker": asdict(marker),
        "world_window": window,
        "original_s16_stage_s_join": joined,
        "evidence_scope": "SYNTHETIC_OFFLINE_ONLY",
        "placement_window": "UNATTESTED_PREWORLD_BLOCKED",
        "external_custody_qualified": False,
        "real_world_attested": False,
        "physical_run_permitted": False,
        "s10_permission": False,
        "science_qualified": False,
    }
