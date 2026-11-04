"""Bug-0 read-only verifier for externally signed first-EAT operator decisions.

This module never creates a signing key, NormalEatingAuthorization, Action,
native command, or physical-ISSUE permission. The S49 owner must separately
own currentness, source custody, single-use admission and Action issuance.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from adapters.mineflayer.bug0_first_eat_shadow import Bug0FirstEatShadow


_DOMAIN = b"relay-self/bug0-first-eat-operator-v1\x00"
_MAX_WINDOW_MS = 60_000


class Bug0EatGrantRejected(ValueError):
    """An operator statement is malformed, untrusted, expired or out of scope."""


@dataclass(frozen=True, slots=True)
class EatOperatorStatement:
    """Signed statement schema. Only the external principal owns the key.

    Two independently pinned principals must authorize PROPOSE and ISSUE.
    Matching source fields are necessary but do not independently attest
    that the native observation or the S49 sole-issuer process is genuine.
    """

    stage: str
    authority_id: str
    grant_id: str
    nonce: str
    session_id: str
    intent_id: str
    action_id: str
    earlier_probe_seq: int
    current_probe_seq: int
    current_probe_request_id: str
    food_item: str
    food_slot: int
    food_before: float
    issued_at_utc_ms: int
    expires_at_utc_ms: int

    def __post_init__(self) -> None:
        identifiers = (
            self.authority_id, self.grant_id, self.nonce, self.session_id,
            self.intent_id, self.action_id, self.current_probe_request_id,
            self.food_item,
        )
        if (
            self.stage not in ("PROPOSE", "ISSUE")
            or any(type(s) is not str or not 1 <= len(s) <= 256 for s in identifiers)
            or any(
                type(x) is not int or x < 0
                for x in (
                    self.earlier_probe_seq, self.current_probe_seq, self.food_slot,
                    self.issued_at_utc_ms, self.expires_at_utc_ms,
                )
            )
            or self.earlier_probe_seq >= self.current_probe_seq
            or type(self.food_before) not in (int, float)
            or not math.isfinite(self.food_before)
            or self.expires_at_utc_ms <= self.issued_at_utc_ms
            or self.expires_at_utc_ms - self.issued_at_utc_ms > _MAX_WINDOW_MS
        ):
            raise Bug0EatGrantRejected("malformed bounded first-EAT operator statement")


@dataclass(frozen=True, slots=True)
class SignedEatOperatorStatement:
    statement: EatOperatorStatement
    signature_hex: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.statement, EatOperatorStatement)
            or type(self.signature_hex) is not str
            or len(self.signature_hex) != 128
            or any(c not in "0123456789abcdef" for c in self.signature_hex)
        ):
            raise Bug0EatGrantRejected("Ed25519 signature must be canonical lowercase hex")


@dataclass(frozen=True, slots=True)
class VerifiedEatOperatorPair:
    """Diagnostic only: verification does not grant physical EAT authority."""

    action_id: str
    grant_id: str
    session_id: str
    propose_authority_id: str
    issue_authority_id: str
    signed_scope_sha256: str
    status: str = "SIGNED_OPERATOR_PAIR_VERIFIED_READ_ONLY"
    source_independently_attested: bool = False
    sole_physical_issuer_attested: bool = False
    consumed_once_attested: bool = False
    physical_eat_authorized: bool = False


def operator_statement_bytes(statement: EatOperatorStatement) -> bytes:
    """Canonical domain-separated bytes for an OUT-OF-PROCESS signer.

    This is a serialization operation, not a grant minting operation.
    """
    if not isinstance(statement, EatOperatorStatement):
        raise Bug0EatGrantRejected("typed operator statement required")
    return _DOMAIN + json.dumps(
        asdict(statement), sort_keys=True, ensure_ascii=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def _scope(statement: EatOperatorStatement) -> tuple[object, ...]:
    return (
        statement.grant_id, statement.session_id, statement.intent_id,
        statement.action_id, statement.earlier_probe_seq,
        statement.current_probe_seq, statement.current_probe_request_id,
        statement.food_item, statement.food_slot, statement.food_before,
    )


def _verify_one(
    signed: SignedEatOperatorStatement,
    stage: str,
    trusted_keys: Mapping[str, bytes],
    now_utc_ms: int,
) -> None:
    if (
        not isinstance(signed, SignedEatOperatorStatement)
        or signed.statement.stage != stage
        or not isinstance(trusted_keys, Mapping)
    ):
        raise Bug0EatGrantRejected("wrong operator decision stage or trust store")
    statement = signed.statement
    key = trusted_keys.get(statement.authority_id)
    if (
        type(key) is not bytes or len(key) != 32
        or not statement.issued_at_utc_ms <= now_utc_ms < statement.expires_at_utc_ms
    ):
        raise Bug0EatGrantRejected("unknown pinned principal or expired decision")
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(
            bytes.fromhex(signed.signature_hex),
            operator_statement_bytes(statement),
        )
    except (InvalidSignature, ValueError) as exc:
        raise Bug0EatGrantRejected("operator Ed25519 signature invalid") from exc


def verify_external_first_eat_pair(
    shadow: Bug0FirstEatShadow,
    propose: SignedEatOperatorStatement,
    issue: SignedEatOperatorStatement,
    *,
    propose_public_keys: Mapping[str, bytes],
    issue_public_keys: Mapping[str, bytes],
    now_utc_ms: int,
) -> VerifiedEatOperatorPair:
    """Read-only independent principal check, NOT an S49 ISSUE admission.

    Trust keys MUST arrive from operator-controlled configuration, never
    from the signed message, local fixture or shadow source. The S49 owner
    must re-observe at ISSUE, enforce one-time use across processes/restarts,
    and independently qualify the World source and physical occupancy.
    """
    if (
        not isinstance(shadow, Bug0FirstEatShadow)
        or not isinstance(propose, SignedEatOperatorStatement)
        or not isinstance(issue, SignedEatOperatorStatement)
        or type(now_utc_ms) is not int or now_utc_ms < 0
    ):
        raise Bug0EatGrantRejected("read-only signed pair requires exact typed inputs")
    p, i = propose.statement, issue.statement
    if (
        _scope(p) != _scope(i)
        or p.stage != "PROPOSE" or i.stage != "ISSUE"
        or p.authority_id == i.authority_id
        or p.nonce == i.nonce
        or p.issued_at_utc_ms > i.issued_at_utc_ms
        or i.issued_at_utc_ms >= p.expires_at_utc_ms
        or p.session_id != shadow.session_id
        or p.intent_id != shadow.intent_id
        or p.earlier_probe_seq != shadow.earlier_probe_seq
        or p.current_probe_seq != shadow.current_probe_seq
        or p.current_probe_request_id != shadow.current_probe_request_id
        or p.food_item != shadow.candidate_item
        or p.food_slot != shadow.candidate_slot
        or p.food_before != shadow.food_before
    ):
        raise Bug0EatGrantRejected("signed stages or exact current first-EAT scope differ")
    _verify_one(propose, "PROPOSE", propose_public_keys, now_utc_ms)
    _verify_one(issue, "ISSUE", issue_public_keys, now_utc_ms)
    digest = hashlib.sha256(
        json.dumps(_scope(p), ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return VerifiedEatOperatorPair(
        action_id=p.action_id,
        grant_id=p.grant_id,
        session_id=p.session_id,
        propose_authority_id=p.authority_id,
        issue_authority_id=i.authority_id,
        signed_scope_sha256=digest,
    )
