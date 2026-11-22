"""Independent, read-only S1 canonical WAL vs original Native stdout correlation.

Checks the actual Mineflayer JSONL *protocol* and original parent/child
identities, observation source, position and Native clock. A source-shaped
offline fixture can pass; this is NOT Paper/World attribution, capture custody
authentication, cross-restart WAL authentication or a physical grant.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterProtocolError,
    MineflayerEffectResult,
    MineflayerObservation,
    MineflayerStreamDecoder,
)
from relay_self.i_lane_i4a_s1_source_capture_dev import (
    I4AS1SourceCapture,
    I4AS1SourceHold,
    _raw,
)
from relay_self.physical_action_journal import PhysicalActionJournal, PhysicalJournalError


class I4AS1NativeSourceHold(ValueError):
    """Original captured Native stdout does not match canonical S1 MOVE rows."""


@dataclass(frozen=True, slots=True)
class I4AS1NativeReadback:
    classification: str
    original_stdout_sha256: str
    original_stdout_length: int
    native_session_id: str
    parent_action_ids: tuple[str, ...]
    exact_child_acks: int
    checked_native_probes: int
    independent_paper_attested: bool = False
    restart_authenticated: bool = False
    physical_authorized: bool = False


def _position_equal(pos: object, saved: object) -> bool:
    return (
        isinstance(saved, dict) and set(saved) == {"x", "y", "z"}
        and all(type(saved[k]) in (int, float) and math.isfinite(saved[k])
                for k in ("x", "y", "z"))
        and all(abs(getattr(pos, k) - saved[k]) <= 1e-6
                for k in ("x", "y", "z"))
    )


def _tick(probe: MineflayerObservation) -> int | None:
    observed = probe.snapshot.time
    return None if observed is None else (
        observed.day * 24000 + observed.time_of_day
    )


def audit_i4a_original_s1_native_stdout(
    captured: I4AS1SourceCapture, *, native_stdout: Path,
    expected_native_stdout_sha256: str,
) -> I4AS1NativeReadback:
    """Reparse a complete original Native stream, never invoke model or issuer.

    The expected SHA is supplied from a distinct original Native capture.
    It is a content-address comparison, not a trustworthy capture principal.
    """
    if (
        not isinstance(captured, I4AS1SourceCapture)
        or captured.classification != "I4A_S1_RAW_SOURCE_CAPTURE_ONLY"
        or captured.physical_authorized or captured.restart_authenticated
        or not isinstance(native_stdout, Path)
        or type(expected_native_stdout_sha256) is not str
        or len(expected_native_stdout_sha256) != 64
        or any(ch not in "0123456789abcdef"
               for ch in expected_native_stdout_sha256)
    ):
        raise I4AS1NativeSourceHold("captured S1/native source not qualified")
    try:
        original = _raw(Path(captured.path))
        wire = _raw(native_stdout)
    except I4AS1SourceHold as exc:
        raise I4AS1NativeSourceHold("original S1/raw Native source absent") from exc
    digest = hashlib.sha256(wire).hexdigest()
    if (
        digest != expected_native_stdout_sha256
        or len(original) != captured.raw_length
        or hashlib.sha256(original).hexdigest() != captured.raw_sha256
        or not wire.endswith(b"\n")
    ):
        raise I4AS1NativeSourceHold("original Native/S1 captured bytes mismatch")
    try:
        journal = PhysicalActionJournal.restore(
            Path(captured.path), self_id=captured.self_id,
        )
    except PhysicalJournalError as exc:
        raise I4AS1NativeSourceHold("original S1 journal malformed") from exc
    rows = journal.records
    if (
        journal.digest != captured.wal_sha256
        or len(rows) < 1
        or tuple(row["action_id"] for row in rows) != captured.action_ids
    ):
        raise I4AS1NativeSourceHold("original Owner-held S1 prefix differed")
    decoder = MineflayerStreamDecoder()
    messages = {}
    try:
        for line in wire.splitlines():
            event = decoder.decode(line.decode("utf-8"))
            messages[event.seq] = event
    except (UnicodeError, MineflayerAdapterProtocolError) as exc:
        raise I4AS1NativeSourceHold(
            "original Native session stream invalid or interrupted"
        ) from exc
    if decoder.session_id != captured.native_session_id:
        raise I4AS1NativeSourceHold("foreign original Native session")
    checked_acks = set()
    checked_probes = set()
    for row in rows:
        if (
            row["session_id"] != captured.native_session_id
            or row["skill_execution_id"] != captured.old_skill_id
            or row["intent_id"] != captured.old_intent_id
            or row["capability"] != "MOVE_PLACE"
            or row["status"] != "NATIVE_PLACE_MOVE_SETTLED"
            or type(row["effect_seqs"]) is not list
            or len(row["effect_seqs"]) != 3
        ):
            raise I4AS1NativeSourceHold("S1 row is not the original settled MOVE")
        parent = row["action_id"]
        events = [
            (row["effect_seqs"][0], parent + "-look", "look"),
            (row["effect_seqs"][1], parent + "-start", "set_control"),
            (row["effect_seqs"][2], parent + "-stop", "clear_controls"),
        ]
        gait = row.get("gait_ack_seq")
        if gait is not None:
            if row.get("gait_mode") != "SNEAK":
                raise I4AS1NativeSourceHold("unqualified additional native gait")
            events.append((gait, parent + "-sneak", "set_control"))
        for seq, action_id, effect in events:
            matched = messages.get(seq)
            if (
                not isinstance(matched, MineflayerEffectResult)
                or matched.action_id != action_id
                or matched.effect != effect
                or matched.result != "applied"
                or seq in checked_acks
            ):
                raise I4AS1NativeSourceHold(
                    "S1 original child effect ACK not exact-once applied"
                )
            checked_acks.add(seq)
        probes = [
            (row["probe_seq"], row["probe_request_id"],
             row["started_position"], None),
            (row["initial_stop_seq"], None, None, row["initial_stop_tick"]),
            (row["first_stable_seq"], None, None, row["first_stable_tick"]),
            (row["after_seq"], None, row["settled_position"], row["settled_tick"]),
        ]
        for seq, request_id, position, tick in probes:
            matched = messages.get(seq)
            if (
                not isinstance(matched, MineflayerObservation)
                or matched.kind != "probe"
                or not matched.request_id
                or (request_id is not None and matched.request_id != request_id)
                or (position is not None and not _position_equal(
                    matched.snapshot.position, position,
                ))
                or (tick is not None and _tick(matched) != tick)
                or seq in checked_probes
            ):
                raise I4AS1NativeSourceHold(
                    "S1 original probe/position/Native clock not exact"
                )
            checked_probes.add(seq)
    # Refuse any unaccounted native effect: the S1 transcript must not hide
    # another physical command outside the original canonical ActionPort.
    raw_effects = {
        seq for seq, item in messages.items()
        if isinstance(item, MineflayerEffectResult)
    }
    if raw_effects != checked_acks:
        raise I4AS1NativeSourceHold("original Native stream has unowned physical effects")
    return I4AS1NativeReadback(
        "I4A_S1_NATIVE_WAL_SOURCE_CORRELATION_CPU_OFFLINE_ONLY",
        digest, len(wire), captured.native_session_id,
        captured.action_ids, len(checked_acks), len(checked_probes),
    )
