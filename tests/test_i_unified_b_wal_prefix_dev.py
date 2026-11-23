"""U2 read-only B canonical WAL prefix: no Native effect or physical grant.

The rows are *constructed fixtures* via the existing canonical WAL validator.
They are not a witnessed ActionPort operation or authenticated S1 custody.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from relay_self.i_unified_physical_source_dev import (
    IUnifiedPhysicalHold,
    audit_i_unified_s2_cpu,
    capture_i_unified_s1_cpu,
)
from relay_self.physical_action_journal import (
    PhysicalActionJournal,
    PhysicalJournalError,
)
from test_bd1b_owner_present_dev import _configured


def _eat_row(
    *, session: str, intent="s1-intent", skill="s1-skill",
    action="s1-action", probe_seq=1,
):
    return {
        "session_id": session,
        "intent_id": intent,
        "skill_execution_id": skill,
        "action_id": action,
        "capability": "EAT",
        "target_ref": "inventory:bread",
        "probe_seq": probe_seq,
        "probe_request_id": f"request-{probe_seq}",
        "source_ref": f"{session}:{probe_seq}",
        "status": "NATIVE_EAT_OUTCOME",
        "effect_seqs": [probe_seq + 1, probe_seq + 2],
        "after_seq": probe_seq + 3,
        "food_before": 10,
        "food_after": 16,
        "count_before": 2,
        "count_after": 1,
    }


def _original(case):
    owner = case[1].owners["A"]
    journal = PhysicalActionJournal.restore(owner.files.physical_wal_file, self_id="A")
    assert journal.records == ()
    return owner, journal


def _seed(case):
    owner, journal = _original(case)
    journal._commit([_eat_row(session=owner.native_session_id)])
    canonical = PhysicalActionJournal.restore(journal.path, self_id="A")
    witness = capture_i_unified_s1_cpu(
        bridge=case[1], self_id="A", journal=canonical,
    )
    assert witness.canonical_prefix_sha256 == canonical.digest
    assert witness.s1_digest != canonical.digest
    return owner, witness


def _append(case, *, intent="s2-intent", skill="s2-skill",
            action="s2-action"):
    owner = case[1].owners["A"]
    journal = PhysicalActionJournal.restore(owner.files.physical_wal_file, self_id="A")
    journal._commit([*journal.records, _eat_row(
        session=owner.native_session_id, intent=intent, skill=skill,
        action=action, probe_seq=5,
    )])
    return PhysicalActionJournal.restore(journal.path, self_id="A")


def _tamper_and_rechecksum(path):
    envelope = json.loads(path.read_bytes())
    envelope["body"]["actions"][0]["action_id"] = "altered-history"
    canonical = json.dumps(
        envelope["body"], ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode()
    envelope["sha256"] = hashlib.sha256(canonical).hexdigest()
    path.write_text(json.dumps(envelope), encoding="utf-8")


def test_b_canonical_prefix_is_stable_under_append_not_a_seal(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch)
    owner, witness = _seed(case)
    current = _append(case)
    assert current.certified_prefix_digest(1) == witness.canonical_prefix_sha256
    assert current.digest != witness.canonical_prefix_sha256
    before = owner.retained, owner.intent.events, tuple(owner.skills.items())
    readback = audit_i_unified_s2_cpu(
        bridge=case[1], self_id="A", journal=current, s1=witness,
    )
    assert readback.s2_action_ids == ("s2-action",)
    assert readback.s2_intent_id == "s2-intent"
    assert readback.s2_skill_execution_id == "s2-skill"
    assert readback.original_owner is owner
    assert not readback.original_source_authenticated
    assert not readback.real_physical_s2_attested
    assert not readback.c1_memory_adopted
    assert not readback.physical_issue_authorized
    assert (owner.retained, owner.intent.events, tuple(owner.skills.items())) == before


def test_prefix_digest_rejects_empty_boolean_fraction_and_overflow(tmp_path):
    journal = PhysicalActionJournal.create(tmp_path / "wal.json", self_id="A")
    for count in (0, 1, -1, True, False, 1.0, "1", None):
        with pytest.raises(PhysicalJournalError):
            journal.certified_prefix_digest(count)
    journal._commit([_eat_row(session="session-A")])
    for count in (0, -1, True, False, 1.0, "1", 2):
        with pytest.raises(PhysicalJournalError):
            journal.certified_prefix_digest(count)
    assert journal.certified_prefix_digest(1) == journal.digest
    assert PhysicalActionJournal.restore(
        journal.path, self_id="A",
    ).certified_prefix_digest(1) == journal.digest


def test_original_b_prefix_denies_s1_rechecksum_forgery(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch)
    _, witness = _seed(case)
    journal = _append(case)
    _tamper_and_rechecksum(journal.path)
    forged = PhysicalActionJournal.restore(journal.path, self_id="A")
    assert forged.digest != journal.digest
    assert forged.certified_prefix_digest(1) != witness.canonical_prefix_sha256
    with pytest.raises(IUnifiedPhysicalHold):
        audit_i_unified_s2_cpu(
            bridge=case[1], self_id="A", journal=forged, s1=witness,
        )


@pytest.mark.parametrize("variant", (
    "same_intent", "same_skill", "same_action", "foreign_owner",
    "world_epoch", "native_session", "wrong_wal", "forged_witness",
    "replay_witness", "wal_drift", "self_fenced",
))
def test_original_b_s2_cpu_rejects_stale_or_foreign(
    tmp_path, monkeypatch, variant,
):
    case = _configured(tmp_path, monkeypatch)
    owner, witness = _seed(case)
    if variant == "same_intent":
        latest = _append(case, intent="s1-intent")
    elif variant == "same_skill":
        latest = _append(case, skill="s1-skill")
    elif variant == "same_action":
        journal = PhysicalActionJournal.restore(owner.files.physical_wal_file, self_id="A")
        with pytest.raises(PhysicalJournalError):
            journal._commit([*journal.records, _eat_row(
                session=owner.native_session_id, intent="s2-intent",
                skill="s2-skill", action="s1-action", probe_seq=5,
            )])
        return
    else:
        latest = _append(case)
    if variant == "foreign_owner":
        witness = replace(witness, owner=case[1].owners["B"])
    elif variant == "world_epoch":
        case[1].cognitive_work._states["A"].world_epoch += 1
    elif variant == "native_session":
        owner.native_session_id = "different-session"
    elif variant == "wrong_wal":
        copy = tmp_path / "foreign-copy.json"
        copy.write_bytes(latest.path.read_bytes())
        latest = PhysicalActionJournal.restore(copy, self_id="A")
    elif variant == "forged_witness":
        witness = replace(witness, canonical_prefix_sha256="f" * 64)
    elif variant == "replay_witness":
        witness = replace(witness, resident_epoch=witness.resident_epoch + 1)
    elif variant == "wal_drift":
        newest = PhysicalActionJournal.restore(latest.path, self_id="A")
        newest._commit([*newest.records, _eat_row(
            session=owner.native_session_id, intent="s3-intent",
            skill="s3-skill", action="s3-action", probe_seq=9,
        )])
    elif variant == "self_fenced":
        case[1].cognitive_work.fence_self("A")
    with pytest.raises(IUnifiedPhysicalHold):
        audit_i_unified_s2_cpu(
            bridge=case[1], self_id="A", journal=latest, s1=witness,
        )


def test_b_s1_capture_rejects_foreign_same_content_wal_copy(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch)
    owner, journal = _original(case)
    journal._commit([_eat_row(session=owner.native_session_id)])
    clone = tmp_path / "forged-copy.json"
    clone.write_bytes(journal.path.read_bytes())
    copied = PhysicalActionJournal.restore(clone, self_id="A")
    with pytest.raises(IUnifiedPhysicalHold):
        capture_i_unified_s1_cpu(
            bridge=case[1], self_id="A", journal=copied,
        )


def test_b_s1_capture_rejects_prepared_unresolved(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch)
    owner, journal = _original(case)
    row = _eat_row(session=owner.native_session_id)
    row["status"] = "PREPARED_UNRESOLVED"
    for key in ("effect_seqs", "after_seq", "food_before", "food_after",
                "count_before", "count_after"):
        row[key] = None
    journal._commit([row])
    with pytest.raises(IUnifiedPhysicalHold):
        capture_i_unified_s1_cpu(
            bridge=case[1], self_id="A", journal=journal,
        )
