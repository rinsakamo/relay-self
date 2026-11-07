"""DEV durable PRE-ISSUE ATTACK/EAT fence for the SAME S49 ActionSupervisor.

Typed Action/S15-native evidence, not proof of zombie death, damage attribution,
hunger effects or physical exactly-once delivery. Unresolved = STOP, never retry.
This ledger is distinct from C1's MOVE-only ledger and S10 learning journal.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from adapters.mineflayer.attack_execution import (
    AttackActionReceipt,
    verify_attack_effect,
)
from adapters.mineflayer.eat_execution import (
    EatingActionReceipt,
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
    _require_fields,
    _text,
    _write,
)

_SCHEMA = 1
_KIND = {"ATTACK", "EAT"}
_REQUIRED = {
    "session_id", "intent_id", "action_id", "kind", "probe_seq",
    "probe_request_id", "source_ref", "subject", "status",
    "terminal", "effect_seqs", "after_seq", "result",
}


class NonMotionFenceError(ValueError):
    """A new physical Action may not be issued or closed."""


class NonMotionUnresolved(NonMotionFenceError):
    """A prior potentially physical ATTACK/EAT is UNKNOWN after restart."""


class NonMotionReplay(NonMotionFenceError):
    """Source/Action identity or a CAS writer is stale."""


def _valid(body: object) -> dict[str, Any]:
    b = _require_fields(body, {"schema", "self_id", "actions"}, "non-motion fence")
    if b["schema"] != _SCHEMA:
        raise NonMotionFenceError("unsupported non-motion fence schema")
    _text(b["self_id"], "Self")
    if type(b["actions"]) is not list:
        raise NonMotionFenceError("action rows required")
    seen: set[tuple[str, str]] = set()
    last_seq: dict[str, int] = {}
    for i, entry in enumerate(b["actions"]):
        a = _require_fields(entry, _REQUIRED, "non-motion Action")
        session = _text(a["session_id"], "session")
        _text(a["intent_id"], "intent")
        action = _text(a["action_id"], "action")
        if a["kind"] not in _KIND:
            raise NonMotionFenceError("only ATTACK/EAT are supported")
        probe_seq = _int(a["probe_seq"], "probe seq")
        _text(a["probe_request_id"], "probe request")
        if a["source_ref"] != f"{session}:{probe_seq}":
            raise NonMotionFenceError("source provenance mismatched")
        if (session, action) in seen:
            raise NonMotionReplay("duplicate original Action ID")
        seen.add((session, action))
        if probe_seq <= last_seq.get(session, -1):
            raise NonMotionReplay("stale original native source")
        subject = a["subject"]
        if a["kind"] == "ATTACK":
            _int(subject, "native target entity ID")
        else:
            _text(subject, "consumed food item")
        if a["status"] == "PREPARED_UNRESOLVED":
            if i != len(b["actions"]) - 1 or any(
                a[k] is not None
                for k in ("terminal", "effect_seqs", "after_seq", "result")
            ):
                raise NonMotionFenceError("pending Action must be last and UNKNOWN")
            last_seq[session] = probe_seq
        elif a["status"] == "S16_OUTCOME":
            if a["terminal"] != "outcome":
                raise NonMotionFenceError("only real S16 OUTCOME can seal")
            if type(a["effect_seqs"]) is not list:
                raise NonMotionFenceError("effect seq list required")
            n = 1 if a["kind"] == "ATTACK" else 2
            if len(a["effect_seqs"]) != n:
                raise NonMotionFenceError("wrong effect cardinality")
            effect_seqs = [_int(x, "native effect seq") for x in a["effect_seqs"]]
            after = _int(a["after_seq"], "native after seq")
            if any(x >= y for x, y in zip(
                [probe_seq, *effect_seqs], [*effect_seqs, after],
            )):
                raise NonMotionFenceError("original native effect order broken")
            result = a["result"]
            if a["kind"] == "ATTACK":
                if result != {"effect": "attack_entity", "applied": True,
                              "death_attested": False}:
                    raise NonMotionFenceError("ATTACK ACK cannot claim death")
            else:
                v = _require_fields(
                    result, {"food_before", "food_after", "item_count_before",
                             "item_count_after"}, "EAT native result",
                )
                for x in v.values():
                    _int(x, "EAT count/food integer")
                if not (v["food_before"] < v["food_after"] <= 20
                        and v["item_count_after"] < v["item_count_before"]):
                    raise NonMotionFenceError("EAT consumption change unverified")
            last_seq[session] = after
        else:
            raise NonMotionFenceError("unknown physical action status")
    return b


def _load(path: Path) -> tuple[dict[str, Any], str]:
    if path.is_symlink() or not path.is_file():
        raise NonMotionFenceError("non-motion fence file missing or symlink")
    try:
        env = json.loads(path.read_bytes())
        record = _require_fields(env, {"body", "sha256"}, "fence envelope")
        body = _valid(record["body"])
        digest = hashlib.sha256(_canonical(body)).hexdigest()
        if record["sha256"] != digest:
            raise NonMotionFenceError("physical fence SHA mismatch")
        return body, digest
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, C1JournalError) as e:
        raise NonMotionFenceError(f"invalid persistent physical fence: {e}") from e


class OriginalS49NonMotionFence:
    """Conservative fsynced ATTACK/EAT journal; NEVER issues an Action."""

    def __init__(self, path: Path, body: dict[str, Any], digest: str):
        self.path = path
        self._body = body
        self.sha256 = digest

    @property
    def actions(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(x) for x in self._body["actions"])

    @property
    def unresolved(self) -> bool:
        return bool(self.actions and self.actions[-1]["status"] == "PREPARED_UNRESOLVED")

    def require_clear(self) -> None:
        if self.unresolved:
            raise NonMotionUnresolved("original ATTACK/EAT may have reached World: STOP/UNKNOWN")

    @classmethod
    def create(cls, path: str | Path, *, self_id: str):
        p = Path(path)
        if not p.parent.is_dir() or p.parent.is_symlink():
            raise NonMotionFenceError("directory must preexist")
        body = {"schema": _SCHEMA, "self_id": _text(self_id, "Self"), "actions": []}
        with _exclusive(p):
            if p.exists() or p.is_symlink():
                raise NonMotionReplay("existing original physical fence cannot be reset")
            digest = _write(p, _valid(body))
        return cls(p, body, digest)

    @classmethod
    def restore(cls, path: str | Path, *, self_id: str):
        p = Path(path)
        with _exclusive(p):
            body, digest = _load(p)
        if body["self_id"] != _text(self_id, "Self"):
            raise NonMotionFenceError("foreign Self cannot restore physical history")
        return cls(p, body, digest)

    def _commit(self, actions: list[dict[str, Any]]) -> None:
        updated = _valid({**self._body, "actions": actions})
        with _exclusive(self.path):
            body, digest = _load(self.path)
            if body != self._body or digest != self.sha256:
                raise NonMotionReplay("physical fence CAS mismatch")
            new_digest = _write(self.path, updated)
        self._body = updated
        self.sha256 = new_digest

    def _prepare(
        self, *, kind: str, probe: MineflayerObservation,
        intent_id: str, action_id: str, subject: int | str,
    ) -> None:
        self.require_clear()
        if (
            kind not in _KIND
            or not isinstance(probe, MineflayerObservation)
            or probe.kind != "probe" or not probe.request_id
            or probe.provenance.source != "mineflayer"
            or probe.provenance.reference != f"{probe.session_id}:{probe.seq}"
        ):
            raise NonMotionFenceError("fresh correlated original native source required")
        self._commit([*self._body["actions"], {
            "session_id": probe.session_id, "intent_id": _text(intent_id, "Intent"),
            "action_id": _text(action_id, "Action"), "kind": kind,
            "probe_seq": probe.seq, "probe_request_id": probe.request_id,
            "source_ref": probe.provenance.reference, "subject": subject,
            "status": "PREPARED_UNRESOLVED", "terminal": None,
            "effect_seqs": None, "after_seq": None, "result": None,
        }])

    def prepare_attack(
        self, *, probe: MineflayerObservation,
        intent_id: str, action_id: str, target_entity_id: int,
    ) -> None:
        self._prepare(kind="ATTACK", probe=probe, intent_id=intent_id,
                      action_id=action_id, subject=target_entity_id)

    def prepare_eat(
        self, *, probe: MineflayerObservation,
        intent_id: str, action_id: str, food_item: str,
    ) -> None:
        self._prepare(kind="EAT", probe=probe, intent_id=intent_id,
                      action_id=action_id, subject=food_item)

    def _owned(
        self, *, kind: str, probe: MineflayerObservation,
        supervisor: ActionSupervisor, terminal: object,
    ) -> dict[str, Any]:
        if (
            not self.unresolved
            or not isinstance(probe, MineflayerObservation)
            or not isinstance(supervisor, ActionSupervisor)
            or not isinstance(terminal, object)
        ):
            raise NonMotionFenceError("pending original physical Action required")
        a = self._body["actions"][-1]
        if a["kind"] != kind:
            raise NonMotionFenceError("physical Action kind changed")
        try:
            true_owner = supervisor.get(a["action_id"])
        except ValueError as e:
            raise NonMotionFenceError("Action not in original supervisor") from e
        if (
            true_owner is not terminal
            or getattr(terminal, "state", None) is not ActionState.OUTCOME
            or getattr(terminal, "intent_id", None) != a["intent_id"]
            or probe.session_id != a["session_id"]
            or probe.seq != a["probe_seq"]
            or probe.request_id != a["probe_request_id"]
            or probe.provenance.reference != a["source_ref"]
        ):
            raise NonMotionFenceError("S16 terminal or native source not original")
        return a

    def close_attack(
        self, *, receipt: AttackActionReceipt,
        probe: MineflayerObservation, supervisor: ActionSupervisor,
        allow_target_disappearance: bool = False,
    ) -> None:
        if not isinstance(receipt, AttackActionReceipt):
            raise NonMotionFenceError("original ATTACK receipt required")
        a = self._owned(kind="ATTACK", probe=probe, supervisor=supervisor,
                        terminal=receipt.terminal)
        if receipt.target_entity_id != a["subject"]:
            raise NonMotionFenceError("original ATTACK target mismatch")
        try:
            verify_attack_effect(
                probe, receipt.effect, receipt.after_probe,
                action_id=a["action_id"], entity_id=a["subject"],
                allow_target_disappearance=allow_target_disappearance,
            )
        except ValueError as e:
            raise NonMotionFenceError("original ATTACK ACK invalid") from e
        closed = {**a, "status": "S16_OUTCOME", "terminal": "outcome",
                  "effect_seqs": [receipt.effect.seq],
                  "after_seq": receipt.after_probe.seq,
                  "result": {"effect": "attack_entity", "applied": True,
                             "death_attested": False}}
        self._commit([*self._body["actions"][:-1], closed])

    def close_eat(
        self, *, receipt: EatingActionReceipt, choice: object,
        probe: MineflayerObservation, supervisor: ActionSupervisor,
    ) -> None:
        from relay_self.eat_hunger import EatChoice

        if not isinstance(receipt, EatingActionReceipt) or not isinstance(choice, EatChoice):
            raise NonMotionFenceError("original EAT receipt and choice required")
        a = self._owned(kind="EAT", probe=probe, supervisor=supervisor,
                        terminal=receipt.terminal)
        if (
            choice.item_name != a["subject"]
            or receipt.equip_receipt is None
            or receipt.consume_receipt is None
            or receipt.after_probe is None
            or receipt.outcome.action_id != a["action_id"]
        ):
            raise NonMotionFenceError("native EAT child effect evidence missing")
        try:
            verified = verify_eating_subactions(
                a["action_id"], choice, probe,
                receipt.equip_receipt, receipt.consume_receipt, receipt.after_probe,
            )
        except ValueError as e:
            raise NonMotionFenceError("original EAT effects unverified") from e
        if verified != receipt.outcome:
            raise NonMotionFenceError("EAT source/outcome changed")
        closed = {**a, "status": "S16_OUTCOME", "terminal": "outcome",
                  "effect_seqs": [
                      receipt.equip_receipt.seq, receipt.consume_receipt.seq,
                  ], "after_seq": receipt.after_probe.seq,
                  "result": {
                      "food_before": int(verified.food_before),
                      "food_after": int(verified.food_after),
                      "item_count_before": verified.count_before,
                      "item_count_after": verified.count_after,
                  }}
        self._commit([*self._body["actions"][:-1], closed])
