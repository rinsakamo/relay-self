"""DEV pre-ISSUE durable physical Action fence for the SAME original S49 issuer.

This is deliberately a conservative replay fence, NOT physical exactly-once
delivery. A PREPARED entry is fsynced before original supervisor.issue and
before Mineflayer IO. Any crash/exception before a verified original S16
OUTCOME leaves it unresolved; a new process must BLOCK before making a World.
No autonomous retry, rollback or inferred physical result is ever granted.

The existing C1/S10 journal is a separate learning owner snapshot. These two
files are not a cross-file atomic transaction.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.normal_action import NormalActionReceipt
from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.c1_motion_journal import (
    C1JournalError,
    _canonical,
    _exclusive,
    _int,
    _require_fields,
    _text,
    _write,
)

_SCHEMA = 1


class PhysicalFenceError(ValueError):
    """Malformed original source, journal or resolved Action."""


class UnresolvedPhysicalAction(PhysicalFenceError):
    """An Action may already have reached the World: NEVER auto-reissue."""


class PhysicalReplay(PhysicalFenceError):
    """Original S49 Action ID/source/owner reused or stale writer detected."""


def _state(body: object) -> dict[str, Any]:
    b = _require_fields(
        body, {"schema", "self_id", "actions"}, "physical Action fence",
    )
    if b["schema"] != _SCHEMA:
        raise PhysicalFenceError("unsupported physical Action fence schema")
    _text(b["self_id"], "physical owner Self")
    if type(b["actions"]) is not list:
        raise PhysicalFenceError("physical Action ledger must be list")
    seen: set[tuple[str, str]] = set()
    prior_after: dict[str, int] = {}
    unresolved = False
    for index, entry in enumerate(b["actions"]):
        e = _require_fields(entry, {
            "session_id", "intent_id", "action_id", "action_ref",
            "decision_seq", "decision_request_id", "source_reference",
            "status", "terminal_state", "before_seq", "dispatch_seq",
            "cleanup_seq", "after_seq", "movement_m",
        }, f"Action fence entry {index}")
        session = _text(e["session_id"], "source session")
        _text(e["intent_id"], "current Intent")
        action = _text(e["action_id"], "original Action")
        if e["action_ref"] != "MOVE_BACKWARD":
            raise PhysicalFenceError("fence applies to original S49 MOVE only")
        decision_seq = _int(e["decision_seq"], "decision native seq")
        request = _text(e["decision_request_id"], "correlated native request")
        if e["source_reference"] != f"{session}:{decision_seq}":
            raise PhysicalFenceError("selected Mineflayer provenance is not exact")
        if not request:
            raise PhysicalFenceError("correlated request required")
        if (session, action) in seen:
            raise PhysicalReplay("original physical Action ID reused in session")
        seen.add((session, action))
        if decision_seq <= prior_after.get(session, -1):
            raise PhysicalReplay("original decision source is stale/replayed")
        if e["status"] == "PREPARED_UNRESOLVED":
            if index != len(b["actions"]) - 1 or unresolved:
                raise PhysicalFenceError("unresolved Action must be last")
            if any(e[k] is not None for k in (
                "terminal_state", "before_seq", "dispatch_seq",
                "cleanup_seq", "after_seq", "movement_m",
            )):
                raise PhysicalFenceError("unresolved Action cannot assert physical outcome")
            unresolved = True
            prior_after[session] = decision_seq
        elif e["status"] == "S16_OUTCOME":
            if e["terminal_state"] != "outcome":
                raise PhysicalFenceError("physical fence cannot fabricate S16 closure")
            before = _int(e["before_seq"], "S15 before")
            dispatch = _int(e["dispatch_seq"], "set_control")
            clear = _int(e["cleanup_seq"], "clear_controls")
            after = _int(e["after_seq"], "S15 after")
            if not decision_seq < before < dispatch < clear < after:
                raise PhysicalFenceError("S49 original native effect sequence broken")
            amount = e["movement_m"]
            if (
                type(amount) not in (int, float)
                or not 0 <= amount < 100
                or amount != amount
            ):
                raise PhysicalFenceError("invalid physical outcome magnitude")
            prior_after[session] = after
        else:
            raise PhysicalFenceError("unrecognized physical Action state")
    return b


def _load(path: Path) -> tuple[dict[str, Any], str]:
    if path.is_symlink() or not path.is_file():
        raise PhysicalFenceError("physical fence path is not regular file")
    try:
        envelope = json.loads(path.read_bytes())
        e = _require_fields(envelope, {"body", "sha256"}, "fence envelope")
        body = _state(e["body"])
        digest = hashlib.sha256(_canonical(body)).hexdigest()
        if e["sha256"] != digest:
            raise PhysicalFenceError("physical Action journal checksum mismatch")
        return body, digest
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, C1JournalError) as exc:
        raise PhysicalFenceError(f"invalid durable physical fence: {exc}") from exc


class OriginalS49PhysicalFence:
    """One durable pre-ISSUE authorization record, never an Action issuer."""

    def __init__(self, path: Path, body: dict[str, Any], digest: str) -> None:
        self.path = path
        self._body = body
        self.sha256 = digest

    @property
    def self_id(self) -> str:
        return self._body["self_id"]

    @property
    def actions(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(item) for item in self._body["actions"])

    @property
    def unresolved(self) -> bool:
        return bool(
            self._body["actions"]
            and self._body["actions"][-1]["status"] == "PREPARED_UNRESOLVED"
        )

    def require_clear(self) -> None:
        if self.unresolved:
            raise UnresolvedPhysicalAction(
                "prior PREPARED physical Action may have reached World: STOP/UNKNOWN"
            )

    @classmethod
    def create(
        cls, path: str | Path, *, self_id: str,
    ) -> OriginalS49PhysicalFence:
        target = Path(path)
        if not target.parent.is_dir() or target.parent.is_symlink():
            raise PhysicalFenceError("fence directory must preexist and not be symlink")
        body = {"schema": _SCHEMA, "self_id": _text(self_id, "self_id"), "actions": []}
        with _exclusive(target):
            if target.exists() or target.is_symlink():
                raise PhysicalReplay("existing physical fence cannot be reseeded")
            _state(body)
            digest = _write(target, body)
        return cls(target, body, digest)

    @classmethod
    def restore(
        cls, path: str | Path, *, self_id: str,
    ) -> OriginalS49PhysicalFence:
        target = Path(path)
        with _exclusive(target):
            body, digest = _load(target)
        if body["self_id"] != _text(self_id, "self_id"):
            raise PhysicalFenceError("foreign physical Action Self denied")
        return cls(target, body, digest)

    def _commit(self, action_rows: list[dict[str, Any]]) -> None:
        candidate = {**self._body, "actions": action_rows}
        _state(candidate)
        with _exclusive(self.path):
            actual, digest = _load(self.path)
            if digest != self.sha256 or actual != self._body:
                raise PhysicalReplay("physical Action fence CAS lost: STOP")
            updated = _write(self.path, candidate)
        self._body = candidate
        self.sha256 = updated

    def prepare(
        self, *, session_id: str, intent_id: str, action_id: str,
        probe: MineflayerObservation,
    ) -> None:
        """Persist a non-reissuable Action identity BEFORE original ISSUE."""
        self.require_clear()
        session = _text(session_id, "session_id")
        intent = _text(intent_id, "intent_id")
        action = _text(action_id, "action_id")
        if (
            not isinstance(probe, MineflayerObservation)
            or probe.kind != "probe" or not probe.request_id
            or probe.session_id != session
            or probe.provenance.source != "mineflayer"
            or probe.provenance.reference != f"{session}:{probe.seq}"
        ):
            raise PhysicalFenceError("original correlated native source required")
        self._commit([*self._body["actions"], {
            "session_id": session, "intent_id": intent, "action_id": action,
            "action_ref": "MOVE_BACKWARD",
            "decision_seq": probe.seq,
            "decision_request_id": probe.request_id,
            "source_reference": probe.provenance.reference,
            "status": "PREPARED_UNRESOLVED",
            "terminal_state": None,
            "before_seq": None, "dispatch_seq": None,
            "cleanup_seq": None, "after_seq": None, "movement_m": None,
        }])

    def close(
        self, receipt: NormalActionReceipt,
        probe: MineflayerObservation, *,
        original_supervisor: ActionSupervisor,
    ) -> None:
        """Seal only an original S16 OUTCOME + exact native effect/clear evidence."""
        if (
            not self.unresolved
            or not isinstance(receipt, NormalActionReceipt)
            or not isinstance(probe, MineflayerObservation)
            or not isinstance(original_supervisor, ActionSupervisor)
        ):
            raise PhysicalFenceError("original unresolved S49 Action receipt required")
        pending = self._body["actions"][-1]
        try:
            actual = original_supervisor.get(pending["action_id"])
        except ValueError as exc:
            raise PhysicalFenceError("original supervisor has no such Action") from exc
        if actual is not receipt.terminal:
            raise PhysicalFenceError("replayed/copied S16 terminal is not original owner")
        c = receipt.consequence
        before = c.before_observation
        after = c.after_observation
        dispatch = c.dispatch_receipt
        cleanup = c.cleanup_receipt
        if (
            pending["action_id"] != receipt.terminal.action_id
            or pending["action_id"] != c.action_id
            or pending["intent_id"] != receipt.terminal.intent_id
            or pending["session_id"] != probe.session_id
            or pending["session_id"] != c.session_id
            or pending["decision_seq"] != probe.seq
            or pending["decision_request_id"] != probe.request_id
            or pending["source_reference"] != probe.provenance.reference
            or receipt.source != probe.provenance
            or receipt.terminal.state is not ActionState.OUTCOME
            or c.status is not WorldConsequenceStatus.EXECUTED
            or c.action_ref != "MOVE_BACKWARD"
            or before is None or after is None or dispatch is None or cleanup is None
            or before.session_id != probe.session_id
            or after.session_id != probe.session_id
            or dispatch.session_id != probe.session_id
            or cleanup.session_id != probe.session_id
            or dispatch.action_id != pending["action_id"]
            or dispatch.effect != "set_control" or dispatch.result != "applied"
            or cleanup.effect != "clear_controls" or cleanup.result != "applied"
            or cleanup.action_id != pending["action_id"] + "-s15-clear"
            or not (
                probe.seq < before.seq < dispatch.seq < cleanup.seq < after.seq
            )
        ):
            raise PhysicalFenceError("not a fully original source-bound S49 S16 OUTCOME")
        movement = c.movement_distance
        if (
            type(movement) not in (int, float)
            or not 0 <= movement < 100
            or movement != movement
        ):
            raise PhysicalFenceError("invalid original physical movement")
        closed = {
            **pending, "status": "S16_OUTCOME", "terminal_state": "outcome",
            "before_seq": before.seq, "dispatch_seq": dispatch.seq,
            "cleanup_seq": cleanup.seq, "after_seq": after.seq,
            "movement_m": float(movement),
        }
        self._commit([*self._body["actions"][:-1], closed])
