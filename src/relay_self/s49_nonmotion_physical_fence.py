"""DEV durable PRE-ISSUE ATTACK/EAT fence for the SAME original S49 owner.

This companion to C1's MOVE-specific fence records only source-bound physical
Action admission and verified original S16 terminal. It does NOT mint an Action,
authorize ATTACK/EAT, prove a kill, guarantee exactly-once delivery, or perform
automatic post-crash recovery. After an interrupted PREPARED Action, the only
safe automated decision is STOP/UNKNOWN before a new World or another Action.

ATTACK is sealed at *native applied ATTACK ACK + fresh native after-probe*,
not at a Paper damage/death/loot claim. EAT is sealed only with actual distinct
equip/consume receipts and fresh before/after food/inventory verification.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from adapters.mineflayer.attack_execution import (
    AttackActionReceipt,
    AttackExecutionRejected,
    verify_attack_effect,
)
from adapters.mineflayer.eat_execution import (
    EatingActionReceipt,
    EatingExecutionRejected,
    verify_eating_subactions,
)
from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.c1_motion_journal import (
    C1JournalError,
    _canonical,
    _exclusive,
    _int,
    _number,
    _require_fields,
    _text,
    _write,
)
from relay_self.eat_hunger import EatChoice, EatStatus

_SCHEMA = 1
_ID_FIELDS = {
    "session_id", "intent_id", "action_id", "action_kind",
    "decision_seq", "decision_request_id", "source_reference",
    "target_entity_id", "food_item", "food_slot", "food_before",
}
_RESULT_FIELDS = {
    "status", "terminal_state", "effect_seq", "consume_seq",
    "after_seq", "food_after", "count_before", "count_after",
    "attack_effect_only",
}


class NonmotionFenceError(ValueError):
    """Original ATTACK/EAT fence evidence missing, malformed or inconsistent."""


class NonmotionActionUnknown(NonmotionFenceError):
    """PREPARED Action may have reached the World: no replay or new World."""


class NonmotionActionReplay(NonmotionFenceError):
    """Stale concurrent writer, duplicate Action or original source."""


def _native_source(probe: MineflayerObservation, session: str) -> None:
    if (
        not isinstance(probe, MineflayerObservation)
        or probe.kind != "probe" or not probe.request_id
        or probe.session_id != session
        or probe.provenance.source != "mineflayer"
        or probe.provenance.reference != f"{session}:{probe.seq}"
        or probe.snapshot.nearby_entities_coverage.truncated
    ):
        raise NonmotionFenceError("fresh source-bound original Mineflayer probe required")


def _validate(body: object) -> dict[str, Any]:
    try:
        b = _require_fields(body, {"schema", "self_id", "actions"}, "nonmotion fence")
        if b["schema"] != _SCHEMA:
            raise NonmotionFenceError("unsupported nonmotion fence schema")
        _text(b["self_id"], "original Self")
        if type(b["actions"]) is not list:
            raise NonmotionFenceError("nonmotion ledger actions must be array")
        seen_actions: set[tuple[str, str]] = set()
        seen_sources: set[tuple[str, int]] = set()
        last_seq: dict[str, int] = {}
        for index, row in enumerate(b["actions"]):
            a = _require_fields(row, _ID_FIELDS | _RESULT_FIELDS, "nonmotion row")
            session = _text(a["session_id"], "session_id")
            _text(a["intent_id"], "intent_id")
            action = _text(a["action_id"], "action_id")
            kind = a["action_kind"]
            if kind not in ("ATTACK", "EAT"):
                raise NonmotionFenceError("only original ATTACK/EAT accepted")
            seq = _int(a["decision_seq"], "source seq")
            _text(a["decision_request_id"], "correlated source request")
            if a["source_reference"] != f"{session}:{seq}":
                raise NonmotionFenceError("original native source provenance changed")
            if (
                (session, action) in seen_actions
                or (session, seq) in seen_sources
                or seq <= last_seq.get(session, -1)
            ):
                raise NonmotionActionReplay("duplicate/stale original Action source")
            seen_actions.add((session, action))
            seen_sources.add((session, seq))
            if kind == "ATTACK":
                _int(a["target_entity_id"], "target entity ID")
                if any(a[k] is not None for k in ("food_item", "food_slot", "food_before")):
                    raise NonmotionFenceError("ATTACK cannot assert food data")
            else:
                if a["target_entity_id"] is not None:
                    raise NonmotionFenceError("EAT cannot assert an attack target")
                _text(a["food_item"], "original food item")
                _int(a["food_slot"], "original native food slot")
                if _number(a["food_before"], "food before") > 20:
                    raise NonmotionFenceError("invalid Minecraft food level")
            if a["status"] == "PREPARED_UNRESOLVED":
                if index != len(b["actions"]) - 1:
                    raise NonmotionFenceError("unresolved Action must be last")
                if any(a[k] is not None for k in (
                    "terminal_state", "effect_seq", "consume_seq", "after_seq",
                    "food_after", "count_before", "count_after", "attack_effect_only",
                )):
                    raise NonmotionFenceError("unresolved Action cannot claim physical result")
                last_seq[session] = seq
            elif a["status"] == "S16_OUTCOME":
                if a["terminal_state"] != "outcome":
                    raise NonmotionFenceError("only original supervisor S16 OUTCOME seals")
                effect = _int(a["effect_seq"], "native applied effect seq")
                after = _int(a["after_seq"], "native after probe seq")
                if not seq < effect < after:
                    raise NonmotionFenceError("non-monotonic original effect/after source")
                if kind == "ATTACK":
                    if (
                        a["attack_effect_only"] is not True
                        or any(a[k] is not None for k in (
                            "consume_seq", "food_after", "count_before", "count_after",
                        ))
                    ):
                        raise NonmotionFenceError("ATTACK ACK is not nutrition/death")
                else:
                    consume = _int(a["consume_seq"], "consume_held seq")
                    if not effect < consume < after or a["attack_effect_only"] is not False:
                        raise NonmotionFenceError("EAT equip/consume ordering violated")
                    food_after = _number(a["food_after"], "food after")
                    if food_after > 20 or food_after <= a["food_before"]:
                        raise NonmotionFenceError("nutrition not observed")
                    count_before = _int(a["count_before"], "inventory count before")
                    count_after = _int(a["count_after"], "inventory count after")
                    if not count_before > count_after:
                        raise NonmotionFenceError("consumed inventory not observed")
                last_seq[session] = after
            else:
                raise NonmotionFenceError("unknown nonmotion physical Action lifecycle")
        return b
    except C1JournalError as exc:
        raise NonmotionFenceError(str(exc)) from exc


def _load(path: Path) -> tuple[dict[str, Any], str]:
    if path.is_symlink() or not path.is_file():
        raise NonmotionFenceError("fence file absent or not regular")
    try:
        packet = json.loads(path.read_bytes())
        e = _require_fields(packet, {"body", "sha256"}, "nonmotion envelope")
        body = _validate(e["body"])
        digest = hashlib.sha256(_canonical(body)).hexdigest()
        if e["sha256"] != digest:
            raise NonmotionFenceError("nonmotion fence checksum mismatch")
        return body, digest
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, C1JournalError) as exc:
        raise NonmotionFenceError(f"nonmotion fence invalid: {exc}") from exc


class OriginalS49NonmotionFence:
    """Atomic source + result ledger; never a second ActionSupervisor."""

    def __init__(self, path: Path, body: dict[str, Any], digest: str):
        self.path = path
        self._body = body
        self.sha256 = digest

    @property
    def self_id(self) -> str:
        return self._body["self_id"]

    @property
    def actions(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(row) for row in self._body["actions"])

    @property
    def unresolved(self) -> bool:
        return bool(
            self._body["actions"]
            and self._body["actions"][-1]["status"] == "PREPARED_UNRESOLVED"
        )

    def require_clear(self) -> None:
        if self.unresolved:
            raise NonmotionActionUnknown(
                "original ATTACK/EAT PREPARED may have reached World: STOP/UNKNOWN"
            )

    @classmethod
    def create(cls, path: str | Path, *, self_id: str) -> OriginalS49NonmotionFence:
        target = Path(path)
        if target.parent.is_symlink() or not target.parent.is_dir():
            raise NonmotionFenceError("nonmotion fence parent directory unavailable")
        body = {"schema": _SCHEMA, "self_id": _text(self_id, "self_id"), "actions": []}
        with _exclusive(target):
            if target.exists() or target.is_symlink():
                raise NonmotionActionReplay("existing nonmotion Action history cannot reset")
            _validate(body)
            digest = _write(target, body)
        return cls(target, body, digest)

    @classmethod
    def restore(cls, path: str | Path, *, self_id: str) -> OriginalS49NonmotionFence:
        target = Path(path)
        with _exclusive(target):
            body, digest = _load(target)
        if body["self_id"] != _text(self_id, "self_id"):
            raise NonmotionFenceError("foreign Self cannot acquire original S49 ledger")
        return cls(target, body, digest)

    def _commit(self, rows: list[dict[str, Any]]) -> None:
        candidate = {**self._body, "actions": rows}
        _validate(candidate)
        with _exclusive(self.path):
            actual, digest = _load(self.path)
            if actual != self._body or digest != self.sha256:
                raise NonmotionActionReplay("nonmotion physical fence stale writer CAS: STOP")
            updated = _write(self.path, candidate)
        self._body = candidate
        self.sha256 = updated

    def _prepare(
        self, *, session_id: str, intent_id: str, action_id: str,
        kind: str, probe: MineflayerObservation, target_entity_id: int | None,
        food_item: str | None, food_slot: int | None,
        food_before: float | None,
    ) -> None:
        self.require_clear()
        session = _text(session_id, "session")
        _native_source(probe, session)
        row = {
            "session_id": session,
            "intent_id": _text(intent_id, "current Intent"),
            "action_id": _text(action_id, "original Action"),
            "action_kind": kind,
            "decision_seq": probe.seq,
            "decision_request_id": probe.request_id,
            "source_reference": probe.provenance.reference,
            "target_entity_id": target_entity_id,
            "food_item": food_item,
            "food_slot": food_slot,
            "food_before": food_before,
            "status": "PREPARED_UNRESOLVED",
            "terminal_state": None,
            "effect_seq": None,
            "consume_seq": None,
            "after_seq": None,
            "food_after": None,
            "count_before": None,
            "count_after": None,
            "attack_effect_only": None,
        }
        self._commit([*self._body["actions"], row])

    def prepare_attack(
        self, *, session_id: str, intent_id: str, action_id: str,
        target_entity_id: int, probe: MineflayerObservation,
    ) -> None:
        if type(target_entity_id) is not int or target_entity_id < 0:
            raise NonmotionFenceError("bounded original ATTACK target ID required")
        self._prepare(
            session_id=session_id, intent_id=intent_id,
            action_id=action_id, kind="ATTACK", probe=probe,
            target_entity_id=target_entity_id, food_item=None,
            food_slot=None, food_before=None,
        )

    def prepare_eat(
        self, *, session_id: str, intent_id: str, action_id: str,
        choice: EatChoice, probe: MineflayerObservation,
    ) -> None:
        if (
            not isinstance(choice, EatChoice) or choice.status is not EatStatus.CANDIDATE
            or choice.session_id != session_id or choice.probe_seq != probe.seq
            or choice.provenance != probe.provenance
            or choice.item_name is None or choice.item_slot is None
            or choice.food_before != probe.snapshot.food
        ):
            raise NonmotionFenceError("original qualified current EAT choice required")
        self._prepare(
            session_id=session_id, intent_id=intent_id,
            action_id=action_id, kind="EAT", probe=probe,
            target_entity_id=None, food_item=choice.item_name,
            food_slot=choice.item_slot, food_before=choice.food_before,
        )

    def _original(self, receipt_terminal, supervisor: ActionSupervisor):
        if (
            not self.unresolved
            or not isinstance(supervisor, ActionSupervisor)
            or receipt_terminal.state is not ActionState.OUTCOME
        ):
            raise NonmotionFenceError("original owner S16 OUTCOME must seal PREPARED")
        row = self._body["actions"][-1]
        if (
            row["action_id"] != receipt_terminal.action_id
            or row["intent_id"] != receipt_terminal.intent_id
        ):
            raise NonmotionFenceError("original Action/Intent changed")
        try:
            original = supervisor.get(receipt_terminal.action_id)
        except ValueError as exc:
            raise NonmotionFenceError("original supervisor missing Action") from exc
        if original is not receipt_terminal or supervisor.open_actions:
            raise NonmotionFenceError("copied terminal or unresolved Action not qualified")
        return row

    def close_attack(
        self, receipt: AttackActionReceipt, before: MineflayerObservation,
        *, original_supervisor: ActionSupervisor,
    ) -> None:
        if not isinstance(receipt, AttackActionReceipt):
            raise NonmotionFenceError("original typed ATTACK terminal required")
        pending = self._original(receipt.terminal, original_supervisor)
        if pending["action_kind"] != "ATTACK":
            raise NonmotionFenceError("EAT reservation cannot close as ATTACK")
        _native_source(before, pending["session_id"])
        if (
            receipt.target_entity_id != pending["target_entity_id"]
            or before.seq != pending["decision_seq"]
            or before.request_id != pending["decision_request_id"]
            or before.provenance.reference != pending["source_reference"]
            or receipt.after_probe.session_id != pending["session_id"]
            or receipt.effect.session_id != pending["session_id"]
            or receipt.damage_attested or receipt.target_death_attested
            or receipt.source_independently_attested
        ):
            raise NonmotionFenceError("ATTACK effect is not source-qualified")
        try:
            verify_attack_effect(
                before, receipt.effect, receipt.after_probe,
                action_id=pending["action_id"],
                entity_id=pending["target_entity_id"],
                allow_target_disappearance=receipt.target_missing_in_native_view,
            )
        except AttackExecutionRejected as exc:
            raise NonmotionFenceError("original ATTACK native effect not verified") from exc
        self._commit([*self._body["actions"][:-1], {
            **pending,
            "status": "S16_OUTCOME", "terminal_state": "outcome",
            "effect_seq": receipt.effect.seq,
            "consume_seq": None,
            "after_seq": receipt.after_probe.seq,
            "food_after": None, "count_before": None, "count_after": None,
            "attack_effect_only": True,
        }])

    def close_eat(
        self, receipt: EatingActionReceipt, before: MineflayerObservation,
        choice: EatChoice, *, original_supervisor: ActionSupervisor,
    ) -> None:
        if not isinstance(receipt, EatingActionReceipt):
            raise NonmotionFenceError("original typed EAT terminal required")
        pending = self._original(receipt.terminal, original_supervisor)
        if pending["action_kind"] != "EAT":
            raise NonmotionFenceError("ATTACK reservation cannot close as EAT")
        _native_source(before, pending["session_id"])
        if (
            before.seq != pending["decision_seq"]
            or before.request_id != pending["decision_request_id"]
            or before.provenance.reference != pending["source_reference"]
            or not isinstance(choice, EatChoice)
            or choice.session_id != pending["session_id"]
            or choice.item_name != pending["food_item"]
            or choice.item_slot != pending["food_slot"]
            or choice.food_before != pending["food_before"]
            or receipt.outcome.action_id != pending["action_id"]
            or receipt.outcome.session_id != pending["session_id"]
            or receipt.before_probe is not before
            or receipt.equip_receipt is None
            or receipt.consume_receipt is None
            or receipt.after_probe is None
        ):
            raise NonmotionFenceError("source-bound S51 native child receipts missing")
        try:
            observed = verify_eating_subactions(
                pending["action_id"], choice, before,
                receipt.equip_receipt, receipt.consume_receipt,
                receipt.after_probe,
            )
        except EatingExecutionRejected as exc:
            raise NonmotionFenceError("original S51 equip/consume/readback unverified") from exc
        if observed != receipt.outcome:
            raise NonmotionFenceError("S51 result not equal to original child readback")
        self._commit([*self._body["actions"][:-1], {
            **pending, "status": "S16_OUTCOME", "terminal_state": "outcome",
            "effect_seq": receipt.equip_receipt.seq,
            "consume_seq": receipt.consume_receipt.seq,
            "after_seq": receipt.after_probe.seq,
            "food_after": observed.food_after,
            "count_before": observed.count_before,
            "count_after": observed.count_after,
            "attack_effect_only": False,
        }])
