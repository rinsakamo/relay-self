"""Original Owner S1 WAL byte capture and later S2 prefix readback (DEV).

A local raw-file receipt is not cross-restart authentication. The caller
must independently preserve the in-process receipt and authenticate original
Native/Paper/Owner provenance. This module grants no Physical or GPU rights.
"""
from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.i_lane_i4a_live_wal_anchor_dev import (
    I4ALiveAnchorHold,
    LiveWalHistoryAnchor,
    verify_live_wal_history_anchor,
)
from relay_self.physical_action_journal import PhysicalActionJournal, PhysicalJournalError
from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)
from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane


class I4AS1SourceHold(RuntimeError):
    """Original S1 source capture or S2 source consistency unavailable."""


_MAX_SIZE = 8 * 1024 * 1024
_NAME = "i4a-original-s1-wal.json"


@dataclass(frozen=True, slots=True)
class I4AS1SourceCapture:
    path: str
    raw_sha256: str
    raw_length: int
    wal_sha256: str
    self_id: str
    native_session_id: str
    world_epoch: int
    old_skill_id: str
    old_intent_id: str
    action_ids: tuple[str, ...]
    classification: str = "I4A_S1_RAW_SOURCE_CAPTURE_ONLY"
    physical_authorized: bool = False
    restart_authenticated: bool = False


@dataclass(frozen=True, slots=True)
class I4AS1S2PrefixReadback:
    classification: str
    old_action_ids: tuple[str, ...]
    s2_action_id: str
    s2_status: str
    s1_sha256: str
    s2_sha256: str
    physical_authorized: bool = False
    restart_authenticated: bool = False
    world_source_attested: bool = False


def _no_symlinks(path: Path) -> None:
    if not isinstance(path, Path) or not path.is_absolute() or any(
        item.is_symlink() for item in (path, *path.parents)
    ):
        raise I4AS1SourceHold("absolute, non-symlink evidence path required")


def _raw(path: Path) -> bytes:
    _no_symlinks(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            meta = os.fstat(fd)
            if not stat.S_ISREG(meta.st_mode) or meta.st_size > _MAX_SIZE:
                raise I4AS1SourceHold("WAL source not a bounded regular file")
            with os.fdopen(os.dup(fd), "rb") as stream:
                raw = stream.read(_MAX_SIZE + 1)
        finally:
            os.close(fd)
    except OSError as exc:
        raise I4AS1SourceHold("original WAL source unavailable") from exc
    if not raw or len(raw) > _MAX_SIZE:
        raise I4AS1SourceHold("invalid WAL source byte length")
    return raw


def _freeze(path: Path, raw: bytes) -> None:
    _no_symlinks(path)
    if not path.parent.is_dir() or path.exists():
        raise I4AS1SourceHold("write-once S1 archive already used or absent")
    try:
        fd = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
        )
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except OSError as exc:
        raise I4AS1SourceHold("S1 evidence partial/write failure: never overwrite") from exc
    if _raw(path) != raw:
        raise I4AS1SourceHold("frozen S1 raw-byte readback mismatch")


def freeze_original_s1_wal(
    owner: CheckpointedCognitiveOwner, *,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    anchor: LiveWalHistoryAnchor,
    evidence_dir: Path,
) -> I4AS1SourceCapture:
    """Capture under existing Owner + original Physical + canonical WAL locks."""
    if (
        not isinstance(owner, CheckpointedCognitiveOwner)
        or owner.cohort is None
        or not isinstance(physical, PhysicalIssueAdmission)
        or not isinstance(lane, ResidentLlamaInferenceLane)
        or not isinstance(anchor, LiveWalHistoryAnchor)
        or not isinstance(evidence_dir, Path)
    ):
        raise I4AS1SourceHold("original Owner/issuer/source required")
    path = evidence_dir / _NAME
    _no_symlinks(path)
    with owner.cohort.lock:
        try:
            verify_live_wal_history_anchor(
                owner, physical=physical, lane=lane, anchor=anchor,
            )
            with physical.quiescent_wal_history_window(
                self_id=owner.self_id, native_session_id=anchor.native_session_id,
            ):
                wal = PhysicalActionJournal.restore(
                    owner.files.physical_wal_file, self_id=owner.self_id,
                )
                raw = _raw(owner.files.physical_wal_file)
                rows = wal.records
                if (
                    wal.digest != anchor.wal_sha256
                    or len(rows) != anchor.wal_row_count
                    or tuple(row["action_id"] for row in rows) != anchor.action_ids
                    or any(
                        row["intent_id"] != anchor.intent_id
                        or row["skill_execution_id"] != anchor.skill_execution_id
                        or row["session_id"] != anchor.native_session_id
                        or row["status"] != "NATIVE_PLACE_MOVE_SETTLED"
                        for row in rows
                    )
                ):
                    raise I4AS1SourceHold("original S1 history no longer sealed")
                _freeze(path, raw)
        except (I4ALiveAnchorHold, PhysicalIssueFenceError, PhysicalJournalError) as exc:
            raise I4AS1SourceHold("S1 Owner/physical source is not quiescent") from exc
    return I4AS1SourceCapture(
        str(path), hashlib.sha256(raw).hexdigest(), len(raw),
        anchor.wal_sha256, anchor.self_id, anchor.native_session_id,
        anchor.world_epoch, anchor.skill_execution_id, anchor.intent_id,
        anchor.action_ids,
    )


def audit_s1_prefix_after_s2(
    captured: I4AS1SourceCapture, *, current_wal: Path,
    new_action_id: str, new_skill_id: str, new_intent_id: str,
) -> I4AS1S2PrefixReadback:
    """Read-only source consistency; a mutable receipt is NOT an auth root."""
    if (
        not isinstance(captured, I4AS1SourceCapture)
        or captured.classification != "I4A_S1_RAW_SOURCE_CAPTURE_ONLY"
        or captured.physical_authorized or captured.restart_authenticated
        or not isinstance(current_wal, Path)
        or any(type(x) is not str or not x for x in (
            new_action_id, new_skill_id, new_intent_id,
        ))
        or new_skill_id == captured.old_skill_id
        or new_intent_id == captured.old_intent_id
        or new_action_id in captured.action_ids
    ):
        raise I4AS1SourceHold("untrusted S1/S2 identity or claimed authority")
    original = Path(captured.path)
    _no_symlinks(original)
    _no_symlinks(current_wal)
    if original == current_wal:
        raise I4AS1SourceHold("S1 archive is not an independent S2 WAL")
    raw = _raw(original)
    if (
        len(raw) != captured.raw_length
        or hashlib.sha256(raw).hexdigest() != captured.raw_sha256
    ):
        raise I4AS1SourceHold("frozen S1 bytes changed")
    try:
        before = PhysicalActionJournal.restore(original, self_id=captured.self_id)
        after = PhysicalActionJournal.restore(current_wal, self_id=captured.self_id)
        older, all_rows = before.records, after.records
        n = len(captured.action_ids)
        if (
            n < 1 or len(older) != n or len(all_rows) != n + 1
            or before.digest != captured.wal_sha256
            or tuple(row["action_id"] for row in older) != captured.action_ids
            or all_rows[:n] != older
            or after.certified_prefix_digest(n) != captured.wal_sha256
            or any(
                row["session_id"] != captured.native_session_id
                or row["intent_id"] != captured.old_intent_id
                or row["skill_execution_id"] != captured.old_skill_id
                or row["status"] != "NATIVE_PLACE_MOVE_SETTLED"
                for row in older
            )
        ):
            raise I4AS1SourceHold("S1 history differs from captured prefix")
        row = all_rows[-1]
        if (
            row["action_id"] != new_action_id
            or row["intent_id"] != new_intent_id
            or row["skill_execution_id"] != new_skill_id
            or row["session_id"] != captured.native_session_id
            or row["capability"] != "MOVE_PLACE"
            or row["probe_seq"] <= older[-1]["after_seq"]
            or row["status"] not in {
                "PREPARED_UNRESOLVED", "NATIVE_PLACE_MOVE_SETTLED",
                "NATIVE_PLACE_MOVE_NO_PROGRESS", "NATIVE_PLACE_MOVE_OVERSHOOT",
            }
        ):
            raise I4AS1SourceHold("S2 suffix is foreign, old or mismatched")
        return I4AS1S2PrefixReadback(
            "I4A_S1_S2_WAL_PREFIX_READBACK_ONLY",
            captured.action_ids, new_action_id, row["status"],
            before.digest, after.digest,
        )
    except PhysicalJournalError as exc:
        raise I4AS1SourceHold("original canonical S1/S2 WAL invalid") from exc
