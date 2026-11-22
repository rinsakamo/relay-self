"""I U3 canonical B WAL v1/v2 compatibility, source-shaped CPU DEV only.

Valid rows are synthetic and written via the existing canonical CAS helper.
No original Native effect, actual S1 terminal, S2 issuer, or trust anchor.
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
from test_i_unified_b_wal_prefix_dev import _eat_row, _original, _seed


def _place(
    *, session: str, seq: int = 5, intent: str = "s2-intent",
    skill: str = "s2-skill", action: str = "s2-action",
    delta: float | None = None, budget_distance: float | None = 2.5,
    gait: str | None = None,
):
    row = {
        "session_id": session,
        "intent_id": intent,
        "skill_execution_id": skill,
        "action_id": action,
        "capability": "MOVE_PLACE",
        "target_ref": "destination:test-waypoint",
        "probe_seq": seq,
        "probe_request_id": f"i-unified-v2-probe-{seq}",
        "source_ref": f"{session}:{seq}",
        "status": "PREPARED_UNRESOLVED",
        "effect_seqs": None,
        "after_seq": None,
        "food_before": None,
        "food_after": None,
        "count_before": None,
        "count_after": None,
        "control": "forward",
        "started_position": {"x": 0.0, "y": 64.0, "z": 0.0},
        "settled_position": None,
        "initial_stop_seq": None,
        "first_stable_seq": None,
        "initial_stop_tick": None,
        "first_stable_tick": None,
        "settled_tick": None,
        "displacement_m": None,
        "invocation_ref": "skill-invocation:v1@test",
        "preset_ref": "skill-preset:v1@test",
        "target_contract_ref": "target-contract:v1@test",
        "aim_yaw_rad": 0.0,
        "target_position": {"x": 3.0, "y": 64.0, "z": 0.0},
        "budget_actions": 4,
        "budget_duration_ms": 2000,
        "budget_distance_m": budget_distance,
    }
    if gait is not None:
        row["gait_mode"] = gait
        row["gait_ack_seq"] = None
    if delta is not None:
        stop = seq + (4 if gait == "SNEAK" else 3)
        row.update(
            status=(
                "NATIVE_PLACE_MOVE_NO_PROGRESS" if delta < 0.1
                else "NATIVE_PLACE_MOVE_OVERSHOOT"
                if budget_distance is not None and delta > budget_distance + 1e-6
                else "NATIVE_PLACE_MOVE_SETTLED"
            ),
            effect_seqs=[seq + 1, stop - 1, stop],
            after_seq=stop + 8,
            settled_position={"x": delta, "y": 64.0, "z": 0.0},
            initial_stop_seq=stop + 1,
            first_stable_seq=stop + 3,
            initial_stop_tick=10,
            first_stable_tick=20,
            settled_tick=30,
            displacement_m=delta,
        )
        if gait == "SNEAK":
            row["gait_ack_seq"] = seq + 2
    return row


def _rewritten(path, corrupt):
    envelope = json.loads(path.read_bytes())
    corrupt(envelope["body"])
    canonical = json.dumps(
        envelope["body"], ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode()
    envelope["sha256"] = hashlib.sha256(canonical).hexdigest()
    path.write_text(json.dumps(envelope), encoding="utf-8")


def test_original_b_v1_history_then_v2_prepared_and_settled_s2(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch)
    owner, witness = _seed(case)
    journal = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id="A",
    )
    s1_rows = journal.records
    assert journal.schema_version == 1
    assert witness.canonical_schema == 1
    journal._commit(
        [*s1_rows, _place(session=owner.native_session_id)],
        upgrade_to_v2=True,
    )
    assert journal.schema_version == 2
    assert journal.unresolved
    assert journal.records[:1] == s1_rows
    assert journal.certified_prefix_digest(
        1, source_schema=1,
    ) == witness.canonical_prefix_sha256
    assert journal.certified_prefix_digest(1) != witness.canonical_prefix_sha256
    with pytest.raises(IUnifiedPhysicalHold):
        audit_i_unified_s2_cpu(
            bridge=case[1], self_id="A", journal=journal, s1=witness,
        )
    journal._commit([
        *s1_rows, _place(session=owner.native_session_id, delta=0.5),
    ])
    restored = PhysicalActionJournal.restore(journal.path, self_id="A")
    assert restored.schema_version == 2
    assert not restored.unresolved
    receipt = audit_i_unified_s2_cpu(
        bridge=case[1], self_id="A", journal=restored, s1=witness,
    )
    assert receipt.s2_action_ids == ("s2-action",)
    assert receipt.original_owner is owner
    assert not receipt.real_physical_s2_attested
    assert not receipt.original_source_authenticated
    assert not receipt.physical_issue_authorized
    assert not receipt.c1_memory_adopted


@pytest.mark.parametrize("delta,budget,gait,expected", [
    (0.5, 2.5, None, "NATIVE_PLACE_MOVE_SETTLED"),
    (0.05, 2.5, "WALK", "NATIVE_PLACE_MOVE_NO_PROGRESS"),
    (0.5, 0.2, "SNEAK", "NATIVE_PLACE_MOVE_OVERSHOOT"),
])
def test_valid_v2_place_terminal_variants_and_second_v2_run(
    tmp_path, monkeypatch, delta, budget, gait, expected,
):
    case = _configured(tmp_path, monkeypatch)
    owner, journal = _original(case)
    first = _place(
        session=owner.native_session_id, seq=1, intent="s1-i",
        skill="s1-s", action="s1-a", delta=0.5,
    )
    journal._commit([first], upgrade_to_v2=True)
    s1 = capture_i_unified_s1_cpu(
        bridge=case[1], self_id="A", journal=journal,
    )
    assert s1.canonical_schema == 2
    assert s1.canonical_prefix_sha256 == journal.digest
    second = _place(
        session=owner.native_session_id, seq=13, delta=delta,
        budget_distance=budget, gait=gait,
    )
    assert second["status"] == expected
    journal._commit([first, second])
    restored = PhysicalActionJournal.restore(journal.path, self_id="A")
    receipt = audit_i_unified_s2_cpu(
        bridge=case[1], self_id="A", journal=restored, s1=s1,
    )
    assert receipt.s2_action_ids == ("s2-action",)
    assert receipt.s2_intent_id == "s2-intent"
    assert receipt.s2_skill_execution_id == "s2-skill"
    assert not receipt.original_source_authenticated
    assert not receipt.physical_issue_authorized


def test_schema_v1_never_accepts_place_and_v2_not_auto_created(tmp_path):
    journal = PhysicalActionJournal.create(tmp_path / "wal.json", self_id="A")
    assert journal.schema_version == 1
    row = _place(session="session-A", seq=1, delta=0.5)
    with pytest.raises(PhysicalJournalError):
        journal._commit([row])
    assert PhysicalActionJournal.restore(
        journal.path, self_id="A",
    ).schema_version == 1
    with pytest.raises(PhysicalJournalError):
        journal.certified_prefix_digest(0, source_schema=2)
    # The writer is an exact-invocation helper, not a new physical issuer.
    with pytest.raises(PhysicalJournalError):
        journal.prepare_place_move(None, None, None, None)
    assert not journal.records


@pytest.mark.parametrize("field,value", (
    ("status", "NATIVE_PLACE_MOVE_NO_PROGRESS"),
    ("capability", "MOVE"),
    ("target_ref", "relative:forward"),
    ("source_ref", "forged:source"),
    ("probe_seq", True),
    ("aim_yaw_rad", 9.0),
    ("budget_actions", 0),
    ("budget_duration_ms", -1),
    ("invocation_ref", "forged"),
    ("preset_ref", "forged"),
    ("target_contract_ref", "forged"),
    ("control", "back"),
    ("displacement_m", 1.0),
    ("effect_seqs", [6, 8, 7]),
    ("after_seq", 7),
    ("initial_stop_tick", 10_000),
))
def test_rechecks_v2_rows_even_with_recomputed_full_checksum(
    tmp_path, field, value,
):
    journal = PhysicalActionJournal.create(tmp_path / "wal.json", self_id="A")
    journal._commit([_place(session="session-A", seq=1, delta=0.5)],
                    upgrade_to_v2=True)
    _rewritten(journal.path, lambda body: body["actions"][0].__setitem__(field, value))
    with pytest.raises(PhysicalJournalError):
        PhysicalActionJournal.restore(journal.path, self_id="A")


@pytest.mark.parametrize("mutation", (
    "partial_gait", "orphan_ack", "bad_prefix", "schema_bool",
    "cross_self", "replayed_seq", "missing_field",
))
def test_rejects_adversarial_v2_envelopes(tmp_path, mutation):
    journal = PhysicalActionJournal.create(tmp_path / "wal.json", self_id="A")
    first = _eat_row(session="session-A")
    second = _place(session="session-A", delta=0.5, gait="WALK")
    journal._commit([first, second], upgrade_to_v2=True)

    def edit(body):
        row = body["actions"][-1]
        if mutation == "partial_gait":
            row.pop("gait_ack_seq")
        elif mutation == "orphan_ack":
            row.pop("gait_mode")
        elif mutation == "bad_prefix":
            row["action_id"] = first["action_id"]
        elif mutation == "schema_bool":
            body["schema"] = True
        elif mutation == "cross_self":
            body["self_id"] = "B"
        elif mutation == "replayed_seq":
            row["probe_seq"] = 1
            row["source_ref"] = "session-A:1"
        elif mutation == "missing_field":
            row.pop("target_contract_ref")
    _rewritten(journal.path, edit)
    with pytest.raises(PhysicalJournalError):
        PhysicalActionJournal.restore(journal.path, self_id="A")


def test_schema_downgrade_or_rewritten_v1_prefix_denied(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch)
    owner, witness = _seed(case)
    journal = PhysicalActionJournal.restore(owner.files.physical_wal_file, self_id="A")
    journal._commit(
        [*journal.records, _place(session=owner.native_session_id, delta=0.5)],
        upgrade_to_v2=True,
    )
    # Historical canonical v1 digest only matches if explicitly revalidated
    # using its *source* schema, not the new full v2 envelope schema.
    assert journal.certified_prefix_digest(
        1, source_schema=1,
    ) == witness.canonical_prefix_sha256
    with pytest.raises(PhysicalJournalError):
        journal.certified_prefix_digest(2, source_schema=1)
    with pytest.raises(PhysicalJournalError):
        journal.certified_prefix_digest(1, source_schema=0)
    with pytest.raises(PhysicalJournalError):
        journal.certified_prefix_digest(1, source_schema=True)
    _rewritten(
        journal.path,
        lambda body: body["actions"][0].__setitem__("action_id", "rewritten-S1"),
    )
    forged = PhysicalActionJournal.restore(journal.path, self_id="A")
    assert forged.certified_prefix_digest(
        1, source_schema=1,
    ) != witness.canonical_prefix_sha256
    with pytest.raises(IUnifiedPhysicalHold):
        audit_i_unified_s2_cpu(
            bridge=case[1], self_id="A", journal=forged, s1=witness,
        )


def test_forced_schema_v2_without_place_does_not_change_old_v1_writer(tmp_path):
    journal = PhysicalActionJournal.create(tmp_path / "wal.json", self_id="A")
    row = _eat_row(session="session-A")
    journal._commit([row])
    assert journal.schema_version == 1
    old_bytes = journal.path.read_bytes()
    old_digest = journal.digest
    assert PhysicalActionJournal.restore(
        journal.path, self_id="A",
    ).digest == old_digest
    journal._commit([row], upgrade_to_v2=True)
    assert journal.schema_version == 2
    assert journal.records == (row,)
    assert journal.certified_prefix_digest(
        1, source_schema=1,
    ) == old_digest
    assert journal.digest != old_digest
    assert journal.path.read_bytes() != old_bytes
