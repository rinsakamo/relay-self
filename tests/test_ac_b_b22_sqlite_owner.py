"""AC-B B22: atomic test S11 writer, persistent replay and explicit bypass limits."""
from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from experiments.ac_b_b11_governed_habit import cue_for, empty_repertoire
from experiments.ac_b_b22_sqlite_owner import (
    OfflineTestIssuer,
    RejectedHabitTransaction,
    SqliteTestHabitOwner,
)
from relay_self.habit import (
    CueFeature,
    HabitRepertoire,
    HabitRule,
    HabitSelectionStatus,
    select_habit,
)
from relay_self.learning import LearningUpdateAuthority
from relay_self.provenance import Provenance

KEY = b"B22-offline-owner-not-production-" + b"0123456789abcdef"
WRONG_KEY = b"other-offline-not-production--" + b"0123456789abcdef"


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def rule(a: int, b: int) -> HabitRule:
    return HabitRule(
        habit_id=f"b22-habit-{a}{b}",
        cue_requirements=(
            CueFeature("a", a), CueFeature("b", b),
        ),
        candidate_ref=f"action:{a ^ b}", priority=10,
        provenance=Provenance("b22.test-only-offline-source", f"{a}{b}"),
    )


def owner(tmp_path, *, name="retained-b22", filename="owner.db"):
    s = SqliteTestHabitOwner(tmp_path / filename, KEY)
    initial = empty_repertoire(label=name)
    receipt = s.initialize(initial)
    assert receipt.repertoire == initial and receipt.repertoire.revision == 0
    return s, initial


def proposal_and_grant(store, *, a=0, b=0, nonce="n1", source=None):
    p = store.prepare(
        "retained-b22", rule(a, b), grant_id=nonce,
        source_digest=source if source is not None else digest(f"case:{a}:{b}"),
    )
    return p, OfflineTestIssuer(KEY).sign(p)


def test_snapshot_persists_across_close_reopen_and_native_readonly_selection(tmp_path):
    s, original = owner(tmp_path)
    proposal, grant = proposal_and_grant(s)
    result = s.commit(proposal, grant)
    assert result.repertoire.revision == 1
    assert len(result.repertoire.rules) == 1
    assert original.rules == () and original.revision == 0
    assert result.repertoire.rules[0] is proposal.rule
    assert select_habit(
        result.repertoire, cue_for(0, 0, trial="new-nuisance")
    ).status is HabitSelectionStatus.SELECTED
    s.close()

    reopened = SqliteTestHabitOwner(tmp_path / "owner.db", KEY)
    loaded = reopened.read("retained-b22")
    assert loaded == result
    assert loaded.repertoire.rules[0] == rule(0, 0)
    selected = select_habit(
        loaded.repertoire, cue_for(0, 0, trial="after-cold-reopen")
    )
    assert selected.status is HabitSelectionStatus.SELECTED
    assert selected.selected_candidate_ref == "action:0"
    assert reopened.read("retained-b22") == loaded
    reopened.close()


def test_cas_two_writer_connections_only_one_commits(tmp_path):
    a, _ = owner(tmp_path)
    b = SqliteTestHabitOwner(tmp_path / "owner.db", KEY)
    pa, ga = proposal_and_grant(a, nonce="writer-a")
    pb, gb = proposal_and_grant(b, a=0, b=1, nonce="writer-b")
    assert pa.expected_state_seal == pb.expected_state_seal
    first = b.commit(pb, gb)
    assert first.repertoire.revision == 1
    with pytest.raises(RejectedHabitTransaction, match="stale"):
        a.commit(pa, ga)
    assert a.read("retained-b22") == first
    assert b.read("retained-b22") == first
    a.close()
    b.close()


def test_lost_replay_across_restart_and_regrant_same_source_denied(tmp_path):
    s, _ = owner(tmp_path)
    p, g = proposal_and_grant(s, nonce="spent-once")
    s.commit(p, g)
    with pytest.raises(RejectedHabitTransaction, match="stale"):
        s.commit(p, g)
    s.close()

    s = SqliteTestHabitOwner(tmp_path / "owner.db", KEY)
    with pytest.raises(RejectedHabitTransaction, match="stale"):
        s.commit(p, g)
    fresh = s.prepare(
        "retained-b22", rule(1, 0),
        grant_id="different-grant", source_digest=p.source_digest,
    )
    with pytest.raises(RejectedHabitTransaction, match="replayed"):
        s.commit(fresh, OfflineTestIssuer(KEY).sign(fresh))
    assert len(s.read("retained-b22").repertoire.rules) == 1
    s.close()


def test_reuse_grant_id_with_new_world_source_denied(tmp_path):
    s, _ = owner(tmp_path)
    p, g = proposal_and_grant(s, nonce="same-id")
    s.commit(p, g)
    q = s.prepare(
        "retained-b22", rule(0, 1),
        source_digest=digest("completely-different-source"),
        grant_id="same-id",
    )
    with pytest.raises(RejectedHabitTransaction, match="replayed"):
        s.commit(q, OfflineTestIssuer(KEY).sign(q))
    assert s.read("retained-b22").repertoire.revision == 1
    s.close()


def test_rollback_all_or_nothing_after_spent_receipt_insertion(tmp_path, monkeypatch):
    s, _ = owner(tmp_path)
    proposal, approval = proposal_and_grant(s)
    def fail_after_spent():
        raise RuntimeError("injected-failure-after-spent-before-owner-write")

    monkeypatch.setattr(s, "_before_state_write", fail_after_spent)
    with pytest.raises(RuntimeError, match="injected-failure"):
        s.commit(proposal, approval)
    assert s.read("retained-b22").repertoire.revision == 0
    monkeypatch.undo()
    receipt = s.commit(proposal, approval)
    assert receipt.repertoire.revision == 1
    s.close()


@pytest.mark.parametrize("alteration", ["owner", "revision", "seal", "source", "scope", "rule"])
def test_signed_exact_proposal_scope_wrong_field_denied(tmp_path, alteration):
    s, _ = owner(tmp_path)
    p, approval = proposal_and_grant(s)
    v = {
        "owner": replace(p, owner_id="attacker"),
        "revision": replace(p, expected_revision=3),
        "seal": replace(p, expected_state_seal="0" * 64),
        "source": replace(p, source_digest=digest("different")),
        "scope": replace(p, scope="PRODUCTION_S11"),
        "rule": replace(p, rule=rule(1, 1)),
    }[alteration]
    with pytest.raises(RejectedHabitTransaction):
        s.commit(v, approval)
    assert s.read("retained-b22").repertoire.rules == ()
    s.close()


def test_denied_grant_and_wrong_key_and_old_plain_bypass_denied(tmp_path):
    s, _ = owner(tmp_path)
    p, _ = proposal_and_grant(s)
    denied = OfflineTestIssuer(KEY).sign(p, granted=False)
    with pytest.raises(RejectedHabitTransaction, match="denied"):
        s.commit(p, denied)
    wrong = OfflineTestIssuer(WRONG_KEY).sign(p)
    with pytest.raises(RejectedHabitTransaction, match="signature"):
        s.commit(p, wrong)
    plain_s10 = LearningUpdateAuthority(
        authority_id="not-S11",
        target_id="retained-b22",
        provenance=Provenance("b22-test", "s10-approval"),
    )
    for approval in (
        None, plain_s10, {"granted": True}, True,
        object(),
    ):
        with pytest.raises(RejectedHabitTransaction, match="signed test"):
            s.commit(p, approval)
    assert s.read("retained-b22").repertoire.revision == 0
    s.close()


@pytest.mark.parametrize("mutation", [
    "extra", "duplicate", "noncanonical", "wrong-kind",
    "denied-text", "wrong-mac", "missing-field",
])
def test_serialized_grant_fields_are_canonical_and_fail_closed(tmp_path, mutation):
    s, _ = owner(tmp_path)
    p, approval = proposal_and_grant(s)
    raw = approval.payload
    if mutation == "extra":
        raw = raw[:-1] + ',"rogue":true}'
    elif mutation == "duplicate":
        raw = raw.replace('"kind":', '"kind":"x","kind":', 1)
    elif mutation == "noncanonical":
        raw = raw.replace(",", ", ", 1)
    elif mutation == "wrong-kind":
        raw = raw.replace("B22_SQLITE_S11_APPROVAL_V1", "PRODUCTION_GRANTED")
    elif mutation == "denied-text":
        raw = raw.replace('"granted":true', '"granted":false')
    elif mutation == "missing-field":
        raw = raw.replace('"kind":"B22_SQLITE_S11_APPROVAL_V1",', "", 1)
    elif mutation == "wrong-mac":
        approval = replace(approval, mac="0" * 64)
    if mutation != "wrong-mac":
        approval = replace(approval, payload=raw)
    with pytest.raises(RejectedHabitTransaction):
        s.commit(p, approval)
    assert s.read("retained-b22").repertoire.revision == 0
    s.close()


def test_db_tamper_without_key_is_detected_on_read_and_commit(tmp_path):
    s, _ = owner(tmp_path)
    p, approval = proposal_and_grant(s)
    s._conn.execute(
        "UPDATE owner_state SET doc=REPLACE(doc,'action:','forged:') "
        "WHERE owner_id='retained-b22'"
    )
    # Initial snapshot is empty, so instead alter original S11 provenance.
    s._conn.execute(
        "UPDATE owner_state SET revision=7 WHERE owner_id='retained-b22'"
    )
    with pytest.raises(RejectedHabitTransaction, match="seal"):
        s.read("retained-b22")
    with pytest.raises(RejectedHabitTransaction, match="seal"):
        s.commit(p, approval)
    s.close()


def test_wrong_key_after_process_reopen_denied(tmp_path):
    s, _ = owner(tmp_path)
    s.close()
    other = SqliteTestHabitOwner(tmp_path / "owner.db", WRONG_KEY)
    with pytest.raises(RejectedHabitTransaction, match="seal"):
        other.read("retained-b22")
    other.close()


def test_second_bootstrap_or_memory_database_denied(tmp_path):
    s, _ = owner(tmp_path)
    with pytest.raises(RejectedHabitTransaction, match="already"):
        s.initialize(empty_repertoire(label="second-owner"))
    assert s.read("retained-b22").repertoire.revision == 0
    s.close()
    with pytest.raises(RejectedHabitTransaction, match="filename"):
        SqliteTestHabitOwner(":memory:", KEY)


def test_two_owner_snapshots_append_without_mutating_predecessor(tmp_path):
    s, original = owner(tmp_path)
    p0, g0 = proposal_and_grant(s)
    first = s.commit(p0, g0)
    p1, g1 = proposal_and_grant(s, a=1, b=1, nonce="n2")
    second = s.commit(p1, g1)
    assert (original.revision, first.repertoire.revision,
            second.repertoire.revision) == (0, 1, 2)
    assert original.rules == ()
    assert len(first.repertoire.rules) == 1
    assert len(second.repertoire.rules) == 2
    assert second.repertoire.rules[0] == first.repertoire.rules[0]
    assert p1.expected_state_seal == first.state_seal
    assert second.state_seal != first.state_seal
    s.close()


def test_same_cue_conflicts_or_duplicate_habit_id_denied(tmp_path):
    s, _ = owner(tmp_path)
    p, g = proposal_and_grant(s)
    s.commit(p, g)
    duplicate_cue = replace(rule(0, 0), habit_id="distinct-id")
    for rule_again in (rule(0, 0), duplicate_cue):
        q = s.prepare(
            "retained-b22", rule_again, grant_id=f"new-{rule_again.habit_id}",
            source_digest=digest(f"new-evidence-{rule_again.habit_id}"),
        )
        with pytest.raises(RejectedHabitTransaction, match="duplicate or conflicting"):
            s.commit(q, OfflineTestIssuer(KEY).sign(q))
    s.close()


def test_invalid_scope_types_digest_or_short_key_denied(tmp_path):
    s, _ = owner(tmp_path)
    p, _ = proposal_and_grant(s)
    for invalid in (
        replace(p, source_digest="not-a-digest"),
        replace(p, grant_id="contains space"),
        replace(p, expected_revision=True),
        replace(p, scope="LIVE_REAL_WORLD"),
        replace(p, expected_state_seal="z" * 64),
    ):
        with pytest.raises(RejectedHabitTransaction):
            OfflineTestIssuer(KEY).sign(invalid)
    with pytest.raises(RejectedHabitTransaction, match="32+"):
        OfflineTestIssuer(b"weak")
    s.close()


def test_explicit_signer_and_storage_bypass_still_possible_with_key(tmp_path):
    # This proves the boundary CANNOT honestly be called exclusive production
    # authority. A caller with the shared test KEY can forge its own grant.
    s, original = owner(tmp_path)
    proposal = s.prepare(
        "retained-b22", rule(0, 1),
        grant_id="caller-forged", source_digest=digest("fabricated-source"),
    )
    independently_reconstructed = OfflineTestIssuer(KEY).sign(proposal)
    updated = s.commit(proposal, independently_reconstructed)
    assert updated.repertoire.revision == 1
    # A separate value-only S11 owner object can be constructed even
    # without the SQLite store: no exclusive global owner yet exists.
    outside = HabitRepertoire(
        repertoire_id=original.repertoire_id,
        revision=1, rules=(rule(1, 1),), provenance=original.provenance,
    )
    assert outside != updated.repertoire
    assert select_habit(
        outside, cue_for(1, 1, trial="bypass")
    ).status is HabitSelectionStatus.SELECTED
    assert len(s.read("retained-b22").repertoire.rules) == 1
    s.close()


def test_signature_integrity_verification_does_not_authenticate_world_source(tmp_path):
    s, _ = owner(tmp_path)
    fake_digest = digest("made-up-physical-success")
    p = s.prepare("retained-b22", rule(0, 0), grant_id="untrusted",
                  source_digest=fake_digest)
    assert s.commit(p, OfflineTestIssuer(KEY).sign(p)).repertoire.revision == 1
    # The API accepted fabricated metadata under an authorized test key.
    # No S17/S16/C15 truth or L2->L1 autonomous learning was established.
    assert p.scope == "B22_OFFLINE_TEST_ONLY"
    s.close()
