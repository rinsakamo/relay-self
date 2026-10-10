"""AC-B B22: test-only SINGLE-WRITER SQLite S11 owner boundary.

Actual frozen S11 HabitRule/HabitRepertoire are retained and selected;
no modification to frozen S11. SQLite BEGIN IMMEDIATE and an owner-state
HMAC seal provide local test-only atomic CAS, restart and replay evidence.

Threat limitation: signer and writer share a test key. Key/file access or
calls to prior B11 experiment helpers bypass this boundary. No live S16,
C15, exclusive OS service, production issuer or physical World proof.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from relay_self.habit import (
    CueFeature,
    HabitRepertoire,
    HabitRule,
)
from relay_self.provenance import Provenance

SCOPE = "B22_OFFLINE_TEST_ONLY"
KIND = "B22_SQLITE_S11_APPROVAL_V1"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class RejectedHabitTransaction(ValueError):
    """No committed S11 transition through this experimental owner."""


def _secret(raw: bytes) -> bytes:
    if type(raw) is not bytes or len(raw) < 32:
        raise RejectedHabitTransaction("external offline test key must be 32+ bytes")
    return raw


def _canonical(v: object) -> str:
    return json.dumps(
        v, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    )


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RejectedHabitTransaction("duplicate JSON property")
        result[key] = value
    return result


def _decode(raw: str) -> object:
    if type(raw) is not str:
        raise RejectedHabitTransaction("JSON must be original canonical text")
    try:
        v = json.loads(raw, object_pairs_hook=_unique_pairs)
        if _canonical(v) != raw:
            raise RejectedHabitTransaction("noncanonical JSON text")
    except (TypeError, ValueError) as exc:
        raise RejectedHabitTransaction("invalid, duplicate or noncanonical JSON") from exc
    return v


def _check_exact(v: object, fields: set[str]) -> dict[str, object]:
    if type(v) is not dict or set(v) != fields:
        raise RejectedHabitTransaction("missing or unknown serialized fields")
    return v


def _prov_data(p: Provenance) -> dict[str, object]:
    if not isinstance(p, Provenance):
        raise RejectedHabitTransaction("real typed Provenance required")
    return asdict(p)


def _prov_from(v: object) -> Provenance:
    p = _check_exact(v, {"source", "reference"})
    return Provenance(**p)


def _rule_data(rule: HabitRule) -> dict[str, object]:
    if not isinstance(rule, HabitRule):
        raise RejectedHabitTransaction("actual frozen S11 HabitRule required")
    return {
        "habit_id": rule.habit_id,
        "cue_requirements": [asdict(feature) for feature in rule.cue_requirements],
        "candidate_ref": rule.candidate_ref,
        "priority": rule.priority,
        "provenance": _prov_data(rule.provenance),
    }


def _rule_from(v: object) -> HabitRule:
    d = _check_exact(v, {
        "habit_id", "cue_requirements", "candidate_ref", "priority", "provenance",
    })
    features = d["cue_requirements"]
    if not isinstance(features, list):
        raise RejectedHabitTransaction("serialized features must be list")
    try:
        return HabitRule(
            habit_id=d["habit_id"],
            cue_requirements=tuple(
                CueFeature(**_check_exact(f, {"key", "value"}))
                for f in features
            ),
            candidate_ref=d["candidate_ref"],
            priority=d["priority"],
            provenance=_prov_from(d["provenance"]),
        )
    except (TypeError, ValueError) as exc:
        raise RejectedHabitTransaction("invalid frozen S11 HabitRule") from exc


def _snapshot_doc(owner: HabitRepertoire) -> str:
    if not isinstance(owner, HabitRepertoire):
        raise RejectedHabitTransaction("actual frozen S11 owner required")
    return _canonical({
        "repertoire_id": owner.repertoire_id,
        "revision": owner.revision,
        "rules": [_rule_data(rule) for rule in owner.rules],
        "provenance": _prov_data(owner.provenance),
    })


def _snapshot_from(doc: str) -> HabitRepertoire:
    d = _check_exact(
        _decode(doc), {"repertoire_id", "revision", "rules", "provenance"}
    )
    if not isinstance(d["rules"], list):
        raise RejectedHabitTransaction("owner rules must be list")
    try:
        result = HabitRepertoire(
            repertoire_id=d["repertoire_id"],
            revision=d["revision"],
            rules=tuple(_rule_from(r) for r in d["rules"]),
            provenance=_prov_from(d["provenance"]),
        )
    except (TypeError, ValueError) as exc:
        raise RejectedHabitTransaction("invalid persisted S11 owner") from exc
    if _snapshot_doc(result) != doc:
        raise RejectedHabitTransaction("noncanonical persisted S11 owner")
    return result


def _mac(key: bytes, domain: str, payload: str) -> str:
    return hmac.new(
        _secret(key), (domain + ":" + payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _valid_hex(value: object) -> bool:
    return type(value) is str and HEX64.fullmatch(value) is not None


@dataclass(frozen=True, slots=True)
class HabitProposal:
    grant_id: str
    owner_id: str
    expected_revision: int
    expected_state_seal: str
    source_digest: str
    rule: HabitRule
    scope: str = SCOPE


@dataclass(frozen=True, slots=True)
class SignedTestApproval:
    payload: str
    mac: str


def _proposal_body(p: HabitProposal) -> dict[str, object]:
    if (
        not isinstance(p, HabitProposal)
        or p.scope != SCOPE
        or type(p.grant_id) is not str
        or not p.grant_id
        or any(ch.isspace() for ch in p.grant_id)
        or type(p.owner_id) is not str
        or not p.owner_id
        or any(ch.isspace() for ch in p.owner_id)
        or type(p.expected_revision) is not int
        or p.expected_revision < 0
        or not _valid_hex(p.expected_state_seal)
        or not _valid_hex(p.source_digest)
    ):
        raise RejectedHabitTransaction("invalid exact offline Habit proposal scope")
    return {
        "grant_id": p.grant_id,
        "owner_id": p.owner_id,
        "expected_revision": p.expected_revision,
        "expected_state_seal": p.expected_state_seal,
        "source_digest": p.source_digest,
        "rule": _rule_data(p.rule),
        "scope": p.scope,
    }


class OfflineTestIssuer:
    """Caller-held test key is NOT exclusive production signing custody."""

    def __init__(self, key: bytes) -> None:
        self._key = _secret(key)

    def sign(
        self, proposal: HabitProposal, *, granted: bool = True,
    ) -> SignedTestApproval:
        if type(granted) is not bool:
            raise RejectedHabitTransaction("typed grant flag required")
        payload = _canonical({
            "kind": KIND,
            "proposal": _proposal_body(proposal),
            "granted": granted,
        })
        return SignedTestApproval(
            payload=payload,
            mac=_mac(self._key, "offline-grant", payload),
        )


def _verify_approval(
    key: bytes, proposal: HabitProposal, approval: SignedTestApproval,
) -> None:
    if not isinstance(approval, SignedTestApproval):
        raise RejectedHabitTransaction("independent signed test approval required")
    data = _check_exact(
        _decode(approval.payload), {"kind", "proposal", "granted"}
    )
    if data != {
        "kind": KIND, "proposal": _proposal_body(proposal), "granted": True,
    }:
        raise RejectedHabitTransaction("denied or altered approval scope")
    if not _valid_hex(approval.mac) or not hmac.compare_digest(
        approval.mac, _mac(key, "offline-grant", approval.payload),
    ):
        raise RejectedHabitTransaction("invalid offline test approval signature")


@dataclass(frozen=True, slots=True)
class OwnedSnapshot:
    repertoire: HabitRepertoire
    state_seal: str


class SqliteTestHabitOwner:
    """An atomic test owner interface; DB/key access is outside its threat model."""

    def __init__(self, db_path: str | Path, test_key: bytes) -> None:
        if str(db_path) == ":memory:":
            raise RejectedHabitTransaction("persistent filename required")
        self._key = _secret(test_key)
        self._conn = sqlite3.connect(str(db_path), timeout=5, isolation_level=None)
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS owner_state("
            "owner_id TEXT PRIMARY KEY, revision INTEGER NOT NULL,"
            "doc TEXT NOT NULL, seal TEXT NOT NULL)"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS spent("
            "grant_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL,"
            "source_digest TEXT NOT NULL, resulting_revision INTEGER NOT NULL,"
            "UNIQUE(owner_id, source_digest))"
        )

    def close(self) -> None:
        self._conn.close()

    def _state_seal(self, owner_id: str, revision: int, doc: str) -> str:
        return _mac(
            self._key, "sealed-owner-state",
            _canonical([owner_id, revision, doc]),
        )

    def initialize(self, initial: HabitRepertoire) -> OwnedSnapshot:
        if not isinstance(initial, HabitRepertoire) or initial.revision != 0:
            raise RejectedHabitTransaction("initial owner must be S11 revision 0")
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            if self._conn.execute("SELECT 1 FROM owner_state LIMIT 1").fetchone():
                raise RejectedHabitTransaction("test database already owns S11")
            doc = _snapshot_doc(initial)
            seal = self._state_seal(initial.repertoire_id, 0, doc)
            self._conn.execute(
                "INSERT INTO owner_state(owner_id,revision,doc,seal) VALUES(?,?,?,?)",
                (initial.repertoire_id, 0, doc, seal),
            )
            self._conn.execute("COMMIT")
            return OwnedSnapshot(initial, seal)
        except BaseException:
            self._conn.execute("ROLLBACK")
            raise

    def _read(self, owner_id: str) -> OwnedSnapshot:
        row = self._conn.execute(
            "SELECT revision,doc,seal FROM owner_state WHERE owner_id=?",
            (owner_id,),
        ).fetchone()
        if row is None:
            raise RejectedHabitTransaction("unknown exclusive test owner")
        rev, doc, seal = row
        if not _valid_hex(seal) or not hmac.compare_digest(
            seal, self._state_seal(owner_id, rev, doc),
        ):
            raise RejectedHabitTransaction("tampered stored owner state seal")
        state = _snapshot_from(doc)
        if state.repertoire_id != owner_id or state.revision != rev:
            raise RejectedHabitTransaction("stored revision/identity mismatch")
        return OwnedSnapshot(state, seal)

    def read(self, owner_id: str) -> OwnedSnapshot:
        return self._read(owner_id)

    def prepare(
        self, owner_id: str, rule: HabitRule, *,
        grant_id: str, source_digest: str,
    ) -> HabitProposal:
        snapshot = self.read(owner_id)
        proposal = HabitProposal(
            grant_id=grant_id, owner_id=owner_id,
            expected_revision=snapshot.repertoire.revision,
            expected_state_seal=snapshot.state_seal,
            source_digest=source_digest, rule=rule,
        )
        _proposal_body(proposal)
        return proposal

    def _before_state_write(self) -> None:
        """No-op seam for rollback fault-injection in isolated tests."""

    def commit(
        self, proposal: HabitProposal, approval: SignedTestApproval,
    ) -> OwnedSnapshot:
        _verify_approval(self._key, proposal, approval)
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            current = self._read(proposal.owner_id)
            old = current.repertoire
            if (
                old.revision != proposal.expected_revision
                or current.state_seal != proposal.expected_state_seal
            ):
                raise RejectedHabitTransaction("stale owner revision/seal")
            if any(
                r.habit_id == proposal.rule.habit_id
                or r.cue_requirements == proposal.rule.cue_requirements
                for r in old.rules
            ):
                raise RejectedHabitTransaction("duplicate or conflicting cue rule")
            next_state = HabitRepertoire(
                repertoire_id=old.repertoire_id,
                revision=old.revision + 1,
                rules=old.rules + (proposal.rule,),
                provenance=old.provenance,
            )
            doc = _snapshot_doc(next_state)
            seal = self._state_seal(old.repertoire_id, next_state.revision, doc)
            try:
                self._conn.execute(
                    "INSERT INTO spent(grant_id,owner_id,source_digest,"
                    "resulting_revision) VALUES(?,?,?,?)",
                    (proposal.grant_id, proposal.owner_id,
                     proposal.source_digest, next_state.revision),
                )
            except sqlite3.IntegrityError as exc:
                raise RejectedHabitTransaction(
                    "replayed grant or source evidence"
                ) from exc
            self._before_state_write()
            written = self._conn.execute(
                "UPDATE owner_state SET revision=?,doc=?,seal=? "
                "WHERE owner_id=? AND revision=? AND seal=?",
                (next_state.revision, doc, seal, old.repertoire_id,
                 old.revision, current.state_seal),
            )
            if written.rowcount != 1:
                raise RejectedHabitTransaction("owner compare-and-swap lost")
            self._conn.execute("COMMIT")
            return OwnedSnapshot(next_state, seal)
        except BaseException:
            self._conn.execute("ROLLBACK")
            raise
