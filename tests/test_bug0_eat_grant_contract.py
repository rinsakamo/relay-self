"""Offline original-S49/S51 Bug-0 operator-signature contract (no World IO).

Keys exist only in test fixtures. The product verifier must never mint keys,
Action grants or physical EAT authority.
"""
from dataclasses import replace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import test_bug0_first_eat_shadow as original
from adapters.mineflayer.bug0_eat_grant_contract import (
    Bug0EatGrantRejected,
    EatOperatorStatement,
    SignedEatOperatorStatement,
    operator_statement_bytes,
    verify_external_first_eat_pair,
)
from adapters.mineflayer.bug0_first_eat_shadow import inspect_bug0_first_eat_shadow


NOW = 1_800_000_000_000


def _sign(claim, key):
    return SignedEatOperatorStatement(
        claim, key.sign(operator_statement_bytes(claim)).hex(),
    )


def _pub(key):
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def case():
    owner, earlier, current = original.pair()
    shadow = inspect_bug0_first_eat_shadow(owner, earlier, current)
    first, second = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    scope = dict(
        grant_id="grant-one", session_id=shadow.session_id,
        intent_id=shadow.intent_id, action_id="bug0-first-eat-action",
        earlier_probe_seq=shadow.earlier_probe_seq,
        current_probe_seq=shadow.current_probe_seq,
        current_probe_request_id=shadow.current_probe_request_id,
        food_item=shadow.candidate_item, food_slot=shadow.candidate_slot,
        food_before=shadow.food_before, issued_at_utc_ms=NOW - 500,
        expires_at_utc_ms=NOW + 500,
    )
    p = _sign(EatOperatorStatement(
        stage="PROPOSE", authority_id="operator-approval",
        nonce="external-propose-once", **scope,
    ), first)
    i = _sign(EatOperatorStatement(
        stage="ISSUE", authority_id="operator-issue",
        nonce="external-issue-once", **scope,
    ), second)
    keys = dict(
        propose_public_keys={"operator-approval": _pub(first)},
        issue_public_keys={"operator-issue": _pub(second)},
    )
    return owner, shadow, p, i, keys, first, second


def verify(shadow, p, i, keys, now=NOW):
    return verify_external_first_eat_pair(
        shadow, p, i, **keys, now_utc_ms=now,
    )


def test_two_separate_pinned_external_signatures_verify_but_never_authorize_action():
    owner, shadow, propose, issue, keys, _, _ = case()
    proof = verify(shadow, propose, issue, keys)
    assert proof.action_id == "bug0-first-eat-action"
    assert proof.grant_id == "grant-one"
    assert proof.status == "SIGNED_OPERATOR_PAIR_VERIFIED_READ_ONLY"
    assert len(proof.signed_scope_sha256) == 64
    assert not proof.source_independently_attested
    assert not proof.sole_physical_issuer_attested
    assert not proof.consumed_once_attested
    assert not proof.physical_eat_authorized
    assert owner._count == 0
    assert owner._dispatched == set()
    assert owner.supervisor.open_actions == ()


@pytest.mark.parametrize("fault", (
    "bad-propose-signature", "bad-issue-signature", "unknown-propose-key",
    "unknown-issue-key", "swapped-keys", "tampered-propose-scope",
    "tampered-issue-scope", "both-signed-foreign-world",
    "both-signed-wrong-food", "stage-mismatch", "same-principal",
    "same-nonce", "action-mismatch", "expired", "future",
))
def test_independent_operator_proof_rejects_untrusted_or_stale_scope(fault):
    owner, shadow, p, i, keys, first, second = case()
    now = NOW
    if fault == "bad-propose-signature":
        p = replace(p, signature_hex=("0" if p.signature_hex[0] != "0" else "1") + p.signature_hex[1:])
    elif fault == "bad-issue-signature":
        i = replace(i, signature_hex=("0" if i.signature_hex[0] != "0" else "1") + i.signature_hex[1:])
    elif fault == "unknown-propose-key":
        keys["propose_public_keys"] = {}
    elif fault == "unknown-issue-key":
        keys["issue_public_keys"] = {}
    elif fault == "swapped-keys":
        keys = dict(
            propose_public_keys={"operator-approval": _pub(second)},
            issue_public_keys={"operator-issue": _pub(first)},
        )
    elif fault == "tampered-propose-scope":
        p = replace(p, statement=replace(p.statement, action_id="tampered"))
    elif fault == "tampered-issue-scope":
        i = replace(i, statement=replace(i.statement, food_slot=i.statement.food_slot + 1))
    elif fault == "both-signed-foreign-world":
        p = _sign(replace(p.statement, session_id="another-world"), first)
        i = _sign(replace(i.statement, session_id="another-world"), second)
    elif fault == "both-signed-wrong-food":
        p = _sign(replace(p.statement, food_item="rotten_flesh"), first)
        i = _sign(replace(i.statement, food_item="rotten_flesh"), second)
    elif fault == "stage-mismatch":
        i = _sign(replace(i.statement, stage="PROPOSE"), second)
    elif fault == "same-principal":
        i = _sign(replace(i.statement, authority_id=p.statement.authority_id), second)
    elif fault == "same-nonce":
        i = _sign(replace(i.statement, nonce=p.statement.nonce), second)
    elif fault == "action-mismatch":
        i = _sign(replace(i.statement, action_id="other-action"), second)
    elif fault == "expired":
        now = NOW + 501
    elif fault == "future":
        now = NOW - 501
    with pytest.raises(Bug0EatGrantRejected):
        verify(shadow, p, i, keys, now)
    assert owner._count == 0
    assert owner.supervisor.open_actions == ()


def test_overlong_operator_window_and_noncanonical_signature_reject():
    _, _, p, _, _, _, _ = case()
    with pytest.raises(Bug0EatGrantRejected):
        replace(p.statement, expires_at_utc_ms=NOW + 120_000)
    with pytest.raises(Bug0EatGrantRejected):
        replace(p, signature_hex=p.signature_hex.upper().replace("A", "G"))


def test_verifier_is_read_only_and_does_not_claim_replay_prevention():
    _, shadow, p, i, keys, _, _ = case()
    a = verify(shadow, p, i, keys)
    b = verify(shadow, p, i, keys)
    assert a == b
    assert not a.consumed_once_attested
    assert not b.physical_eat_authorized
