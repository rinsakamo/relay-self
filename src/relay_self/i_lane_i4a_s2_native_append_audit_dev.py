"""Offline original S1->S2 Native stdout append audit. Never a grant or World audit."""
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
from relay_self.i_lane_i4a_s1_native_source_audit_dev import (
    I4AS1NativeSourceHold,
    _position_equal,
    _tick,
    audit_i4a_original_s1_native_stdout,
)
from relay_self.i_lane_i4a_s1_source_capture_dev import (
    I4AS1SourceCapture,
    I4AS1SourceHold,
    _raw,
    audit_s1_prefix_after_s2,
)
from relay_self.physical_action_journal import PhysicalActionJournal, PhysicalJournalError


class I4AS2NativeAppendHold(ValueError):
    """The original S2 source cannot independently corroborate a settled WAL."""


@dataclass(frozen=True, slots=True)
class I4AS2NativeAppendReadback:
    classification: str
    original_s1_stdout_sha256: str
    original_s2_stdout_sha256: str
    s2_action_id: str
    s2_status: str
    s2_effect_count: int
    native_probe_count: int
    world_attested: bool = False
    paper_attested: bool = False
    physical_authorized: bool = False
    restart_authenticated: bool = False


def audit_i4a_s2_native_append(
    captured: I4AS1SourceCapture, *, s2_wal: Path,
    before_stdout: Path, after_stdout: Path,
    before_sha256: str, after_sha256: str,
    action_id: str, skill_id: str, intent_id: str,
) -> I4AS2NativeAppendReadback:
    """Re-read both original source snapshots and one new canonical S2 suffix.

    All hashes are caller supplied: neither storage custody nor Native/Paper
    runtime ownership is authenticated by the result.
    """
    try:
        compared = audit_s1_prefix_after_s2(
            captured, current_wal=s2_wal,
            new_action_id=action_id, new_skill_id=skill_id,
            new_intent_id=intent_id,
        )
    except I4AS1SourceHold as exc:
        raise I4AS2NativeAppendHold("original S1/S2 WAL prefix mismatch") from exc
    if compared.s2_status == "PREPARED_UNRESOLVED":
        raise I4AS2NativeAppendHold("unresolved S2 cannot claim Native outcome")
    try:
        s1 = audit_i4a_original_s1_native_stdout(
            captured, native_stdout=before_stdout,
            expected_native_stdout_sha256=before_sha256,
        )
        earlier, later = _raw(before_stdout), _raw(after_stdout)
        journal = PhysicalActionJournal.restore(s2_wal, self_id=captured.self_id)
    except (I4AS1NativeSourceHold, I4AS1SourceHold, PhysicalJournalError) as exc:
        raise I4AS2NativeAppendHold("untrusted S1/Native/WAL source") from exc
    if (
        type(after_sha256) is not str or len(after_sha256) != 64
        or any(x not in "0123456789abcdef" for x in after_sha256)
        or before_stdout == after_stdout
        or len(later) <= len(earlier)
        or not later.startswith(earlier)
        or not later.endswith(b"\n")
        or hashlib.sha256(later).hexdigest() != after_sha256
    ):
        raise I4AS2NativeAppendHold("original Native stdout prefix not append-only")
    decoder = MineflayerStreamDecoder()
    entries = {}
    try:
        for raw in later.splitlines():
            item = decoder.decode(raw.decode("utf-8"))
            entries[item.seq] = item
    except (UnicodeError, MineflayerAdapterProtocolError) as exc:
        raise I4AS2NativeAppendHold("original S2 Native stream invalid") from exc
    if decoder.session_id != s1.native_session_id:
        raise I4AS2NativeAppendHold("S2 switched original Native session")
    old_last = len(earlier.splitlines()) - 1
    row = journal.records[-1]
    if row["probe_seq"] <= old_last:
        raise I4AS2NativeAppendHold("replayed S2 pre-S1 Native observation")
    expected = [
        (row["effect_seqs"][0], action_id + "-look", "look"),
        (row["effect_seqs"][1], action_id + "-start", "set_control"),
        (row["effect_seqs"][2], action_id + "-stop", "clear_controls"),
    ]
    if row.get("gait_ack_seq") is not None:
        if row.get("gait_mode") != "SNEAK":
            raise I4AS2NativeAppendHold("foreign S2 gait")
        expected.append((row["gait_ack_seq"], action_id + "-sneak", "set_control"))
    seen = set()
    for seq, child, effect in expected:
        item = entries.get(seq)
        if (
            seq <= old_last or seq in seen
            or not isinstance(item, MineflayerEffectResult)
            or item.action_id != child or item.effect != effect
            or item.result != "applied"
        ):
            raise I4AS2NativeAppendHold("S2 native child ACK mismatch")
        seen.add(seq)
    additional = {
        seq for seq, item in entries.items()
        if seq > old_last and isinstance(item, MineflayerEffectResult)
    }
    if additional != seen:
        raise I4AS2NativeAppendHold("unowned S2 original Native effects")
    probes = [
        (row["probe_seq"], row["probe_request_id"], row["started_position"], None),
        (row["initial_stop_seq"], None, None, row["initial_stop_tick"]),
        (row["first_stable_seq"], None, None, row["first_stable_tick"]),
        (row["after_seq"], None, row["settled_position"], row["settled_tick"]),
    ]
    for seq, req, pos, tick in probes:
        event = entries.get(seq)
        if (
            seq <= old_last
            or not isinstance(event, MineflayerObservation)
            or event.kind != "probe" or not event.request_id
            or (req is not None and event.request_id != req)
            or (pos is not None and not _position_equal(event.snapshot.position, pos))
            or (tick is not None and _tick(event) != tick)
        ):
            raise I4AS2NativeAppendHold("S2 original probe/position/tick mismatch")
    first_stable = entries[row["first_stable_seq"]].snapshot.position
    last_settled = entries[row["after_seq"]].snapshot.position
    if math.dist(
        (first_stable.x, first_stable.y, first_stable.z),
        (last_settled.x, last_settled.y, last_settled.z),
    ) > 0.06:
        raise I4AS2NativeAppendHold("S2 Native STOP residual drift exceeds 0.06m")
    if len({entries[seq].request_id for seq, _, _, _ in probes}) != len(probes):
        raise I4AS2NativeAppendHold("S2 duplicate original STOP/probe request")
    return I4AS2NativeAppendReadback(
        "I4A_S1_S2_NATIVE_APPEND_SOURCE_CPU_OFFLINE_ONLY",
        s1.original_stdout_sha256, after_sha256, action_id,
        compared.s2_status, len(seen), len(probes),
    )
