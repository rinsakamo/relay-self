"""I Unified: read-only S1->S2 consistency over B's ORIGINAL WAL.

The original PhysicalActionJournal remains the sole WAL and write authority.
This adapter never grants an S2 issuer, authenticates source custody, or
produces an Outcome / C1 Memory acceptance. No native, GPU or World IO.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from relay_self.i_unified_original_context_dev import IUnifiedSourceHold, _owner
from relay_self.physical_action_journal import PhysicalActionJournal, PhysicalJournalError


class IUnifiedPhysicalHold(IUnifiedSourceHold):
    """Original B journal, S1 boundary or S2 provenance is not qualified."""


_TERMINAL = frozenset((
    "NATIVE_EAT_OUTCOME",
    "NATIVE_ATTACK_HURT_OBSERVED",
    "NATIVE_MOVE_SETTLED",
    "NATIVE_MOVE_NO_NET_DISPLACEMENT",
))


def _digest(rows: tuple[dict, ...]) -> str:
    return hashlib.sha256(json.dumps(
        rows, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode()).hexdigest()


def _status_ok(rows: tuple[dict, ...], session: str) -> bool:
    return bool(rows) and all(
        type(row) is dict and row.get("session_id") == session
        and row.get("status") in _TERMINAL
        for row in rows
    )


def _distinct_runs(s1: tuple[dict, ...], s2: tuple[dict, ...], session: str) -> bool:
    """Source consistency only, not authenticated Original Writer custody."""
    if not _status_ok(s1, session) or not _status_ok(s2, session):
        return False
    for rows in (s1, s2):
        if (
            len({r.get("intent_id") for r in rows}) != 1
            or len({r.get("skill_execution_id") for r in rows}) != 1
            or any(
                not isinstance(r.get(k), str) or not r[k]
                for r in rows for k in ("intent_id", "skill_execution_id", "action_id")
            )
        ):
            return False
    return bool(
        s1[0]["intent_id"] != s2[0]["intent_id"]
        and s1[0]["skill_execution_id"] != s2[0]["skill_execution_id"]
        and not (
            {r["action_id"] for r in s1} & {r["action_id"] for r in s2}
        )
    )


@dataclass(frozen=True, slots=True)
class IUnifiedS1Witness:
    """Volatile, in-process prefix; not an independently authenticated anchor."""

    self_id: str
    owner: Any
    resident_epoch: int
    native_session_id: str
    s1_rows: tuple[dict, ...]
    s1_digest: str
    source_custody_authenticated: bool = False
    physical_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class IUnifiedS2Readback:
    self_id: str
    original_owner: Any
    s1_digest: str
    s2_intent_id: str
    s2_skill_execution_id: str
    s2_action_ids: tuple[str, ...]
    original_wal_readback: bool = True
    original_source_authenticated: bool = False
    real_physical_s2_attested: bool = False
    c1_memory_adopted: bool = False
    physical_issue_authorized: bool = False


def _read_wal(journal: PhysicalActionJournal, self_id: str) -> tuple[dict, ...]:
    if type(journal) is not PhysicalActionJournal:
        raise IUnifiedPhysicalHold("existing original B WAL required")
    try:
        fresh = PhysicalActionJournal.restore(journal.path, self_id=self_id)
        if fresh.digest != journal.digest or fresh.unresolved:
            raise IUnifiedPhysicalHold("journal drift or PREPARED_UNRESOLVED")
        rows = fresh.records
        if not rows or not all(type(r) is dict for r in rows):
            raise IUnifiedPhysicalHold("nonempty original WAL required")
        return rows
    except (PhysicalJournalError, ValueError, OSError) as exc:
        raise IUnifiedPhysicalHold("original B journal readback unqualified") from exc


def _scope(bridge: Any, self_id: str) -> tuple[Any, int, str]:
    owner = _owner(bridge, self_id)
    resident = bridge.cognitive_work
    try:
        epoch, native, _world_epoch = resident.current_scope(self_id)
        if (
            type(epoch) is not int or epoch < 0
            or type(native) is not str or not native
        ):
            raise IUnifiedPhysicalHold("original B scope incomplete")
        return owner, epoch, native
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise IUnifiedPhysicalHold("original B current scope unavailable") from exc


def capture_i_unified_s1_cpu(
    *, bridge: Any, self_id: str, journal: PhysicalActionJournal,
) -> IUnifiedS1Witness:
    """Freeze terminal S1 before S2 on the original B Owner, CPU DEV only."""
    try:
        owner, epoch, native = _scope(bridge, self_id)
        rows = _read_wal(journal, self_id)
        if not _status_ok(rows, native):
            raise IUnifiedPhysicalHold("S1 terminal original Native session absent")
        return IUnifiedS1Witness(self_id, owner, epoch, native, rows, _digest(rows))
    except (IUnifiedSourceHold, IUnifiedPhysicalHold) as exc:
        raise IUnifiedPhysicalHold("original terminal S1 not ready") from exc


def audit_i_unified_s2_cpu(
    *, bridge: Any, self_id: str, journal: PhysicalActionJournal,
    s1: IUnifiedS1Witness,
) -> IUnifiedS2Readback:
    """Only read back distinct S2 append on the same original B producer."""
    if type(s1) is not IUnifiedS1Witness or s1.self_id != self_id:
        raise IUnifiedPhysicalHold("typed same-Self S1 witness required")
    try:
        owner, epoch, native = _scope(bridge, self_id)
        if (
            owner is not s1.owner or epoch != s1.resident_epoch
            or native != s1.native_session_id
            or s1.source_custody_authenticated or s1.physical_issue_authorized
            or _digest(s1.s1_rows) != s1.s1_digest
        ):
            raise IUnifiedPhysicalHold("S1 Owner epoch, source or prefix changed")
        rows = _read_wal(journal, self_id)
        prefix = rows[:len(s1.s1_rows)]
        s2 = rows[len(s1.s1_rows):]
        if (
            prefix != s1.s1_rows or _digest(prefix) != s1.s1_digest
            or not _distinct_runs(prefix, s2, native)
        ):
            raise IUnifiedPhysicalHold("unqualified S1/S2 prefix, run identity or terminal")
        return IUnifiedS2Readback(
            self_id, owner, s1.s1_digest,
            s2[0]["intent_id"], s2[0]["skill_execution_id"],
            tuple(r["action_id"] for r in s2),
        )
    except (IUnifiedSourceHold, PhysicalJournalError, OSError, ValueError) as exc:
        raise IUnifiedPhysicalHold("S2 original WAL readback unqualified") from exc
