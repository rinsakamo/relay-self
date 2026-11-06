"""C1/S10 atomic durability: restart, duplicate, CAS, corruption and write failure.

All original S49/S16 receipts are typed synthetic fixtures, not a Minecraft
or independent source-truth claim. No physical Action, LLM or authority minted.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

import relay_self.c1_motion_journal as store
from adapters.mineflayer.bug0_intent_motion_learning import (
    forecast_from_retained,
    learn_from_motion_experience,
)
from relay_self.c1_motion_journal import (
    C1JournalConflict,
    C1JournalError,
    C1MotionJournal,
)
from relay_self.learning import LearningUpdateAuthority, LearningUpdateRule
from relay_self.provenance import Provenance
from test_s49_c1_motion_owner_dev import (
    _joined_original_owner,
    _record_synthetic_original_terminal,
)


def _first(path):
    owner, executor, intent, step, selected, receipt, auth, p = _joined_original_owner()
    journal = C1MotionJournal.create(
        path, self_id=owner.self_id, seed=owner.retained_motion,
    )
    owner.journal = journal
    original = journal.state
    _, receipt = _record_synthetic_original_terminal(
        owner, executor, step, selected, receipt, auth, p,
    )
    terminal = owner.close_original_intent()
    return owner, executor, intent, selected, receipt, terminal, journal, original


def test_one_c1_experience_and_s10_revision_commit_as_single_recoverable_file(tmp_path):
    path = tmp_path / "c1-motion-journal.json"
    owner, _, _, selected, receipt, terminal, journal, original = _first(path)
    assert path.exists()
    assert journal.state is owner.retained_motion
    assert journal.state.revision == 1
    assert journal.state.value == 6
    assert journal.experience_ids == (terminal.experience.experience_id,)
    assert terminal.learning.previous_state is original

    # A fresh process would restore this exact historical S10 value/lineage.
    loaded = C1MotionJournal.restore(path, self_id=owner.self_id)
    assert loaded.state is not journal.state
    assert loaded.state == journal.state
    assert loaded.state.last_update == terminal.learning.record
    assert loaded.experience_ids == journal.experience_ids
    assert loaded.sha256 == journal.sha256
    assert (
        forecast_from_retained(
            loaded.state, loaded.state,
            self_id=owner.self_id, intent_id="fresh-third-intent",
            session_id=selected.session_id,
            native_probe_seq=receipt.consequence.after_observation.seq + 2,
            expected_revision=loaded.state.revision,
            source_provenance=Provenance("mineflayer", "source-after-restart"),
        ).predicted_total_m
        == 0.6
    )

    with pytest.raises(C1JournalConflict):
        loaded.commit(terminal.experience, terminal.learning)
    with pytest.raises(C1JournalConflict):
        C1MotionJournal.create(
            path, self_id=owner.self_id, seed=original,
        )
    with pytest.raises(C1JournalError):
        C1MotionJournal.restore(path, self_id="different-self")


def test_stale_writer_after_real_owner_save_does_not_double_apply(tmp_path):
    path = tmp_path / "c1-journal.json"
    owner, executor, _, step, selected, receipt, auth, p = _joined_original_owner()
    journal = C1MotionJournal.create(
        path, self_id=owner.self_id, seed=owner.retained_motion,
    )
    stale = C1MotionJournal.restore(path, self_id=owner.self_id)
    owner.journal = journal
    _, receipt = _record_synthetic_original_terminal(
        owner, executor, step, selected, receipt, auth, p,
    )
    terminal = owner.close_original_intent()
    guessed_result = learn_from_motion_experience(
        terminal.experience, stale.state,
        LearningUpdateRule("offline-stale-copy", 1, 1),
        LearningUpdateAuthority(
            "offline-stale-owner", "motion_decimeters", p,
        ),
        provenance=p,
    )
    with pytest.raises(C1JournalConflict):
        stale.commit(terminal.experience, guessed_result)
    assert C1MotionJournal.restore(path, self_id=owner.self_id).state.revision == 1
    assert len(journal.experience_ids) == 1


@pytest.mark.parametrize("corruption", [
    "invalid_json", "bad_checksum", "wrong_last_feedback",
    "wrong_revision_chain", "duplicate_history", "duplicate_action",
])
def test_restart_never_accepts_corrupted_or_forged_journal(tmp_path, corruption):
    path = tmp_path / "c1.json"
    owner, _, _, _, _, _, _, _ = _first(path)
    data = json.loads(path.read_text())
    if corruption == "invalid_json":
        path.write_text('{"bad":', encoding="utf-8")
    elif corruption == "bad_checksum":
        data["body"]["retained"]["value"] = 4
        path.write_text(json.dumps(data), encoding="utf-8")
    else:
        body = data["body"]
        if corruption == "wrong_last_feedback":
            body["retained"]["last_update"]["feedback_id"] = "different-feedback"
        elif corruption == "wrong_revision_chain":
            body["entries"][0]["after_revision"] = 9
        elif corruption == "duplicate_history":
            body["entries"].append(body["entries"][0])
        else:
            body["entries"][0]["action_ids"].append(
                body["entries"][0]["action_ids"][0],
            )
            body["entries"][0]["decision_probe_seqs"].append(
                body["entries"][0]["decision_probe_seqs"][0] + 1,
            )
        data["sha256"] = hashlib.sha256(store._canonical(body)).hexdigest()
        path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(C1JournalError):
        C1MotionJournal.restore(path, self_id=owner.self_id)


def test_disk_commit_failure_leaves_no_applied_s10_or_next_intent(
    monkeypatch, tmp_path,
):
    path = tmp_path / "c1.json"
    owner, executor, intent, step, selected, receipt, auth, p = _joined_original_owner()
    journal = C1MotionJournal.create(
        path, self_id=owner.self_id, seed=owner.retained_motion,
    )
    owner.journal = journal
    _record_synthetic_original_terminal(
        owner, executor, step, selected, receipt, auth, p,
    )
    original = store._write

    def refuse_after_seed(*_args, **_kwargs):
        raise OSError("simulated fsync failure before replacing journal")

    monkeypatch.setattr(store, "_write", refuse_after_seed)
    with pytest.raises(OSError, match="simulated"):
        owner.close_original_intent()
    monkeypatch.setattr(store, "_write", original)
    assert owner.retained_motion.revision == 0
    assert owner.terminal is None
    assert intent.current_intent is None
    reloaded = C1MotionJournal.restore(path, self_id=owner.self_id)
    assert reloaded.state.revision == 0
    assert reloaded.experience_ids == ()
    with pytest.raises(Exception):
        owner.start_next_original_intent(
            replace(selected, seq=selected.seq + 20),
            next_intent_id="no-resurrection",
        )


def test_no_reseeding_while_existing_legacy_cognition_snapshot_is_separate(tmp_path):
    # C1 sidecar cannot overwrite general Persistent Cognition (Self ID,
    # memories and appraisals) or a prior journal.
    from relay_self.persistent_cognition import (
        IdentitySpecification,
        PersistentCognition,
        load_persistent_cognition,
        save_persistent_cognition,
    )

    identity = IdentitySpecification(
        "dev-self", ("retain identity",), Provenance("test", "identity"),
    )
    general = tmp_path / "self.json"
    save_persistent_cognition(general, PersistentCognition(identity))
    _first(tmp_path / "c1.json")
    assert load_persistent_cognition(general) == PersistentCognition(identity)



def test_original_s49_journal_requires_its_own_dev_gate_before_world(
    monkeypatch, tmp_path,
):
    import asyncio

    from adapters.mineflayer.s49_normal_session_real_ci import qualify

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_UNIFIED_C1_DEV_ONLY", "1")
    monkeypatch.setenv("S49_UNIFIED_C1_TWO_INTENTS_DEV_ONLY", "1")
    monkeypatch.delenv("S49_C1_JOURNAL_DEV_ONLY", raising=False)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    path = tmp_path / "blocked.json"
    rc = asyncio.run(qualify(
        path, tmp_path / "absent-server.log",
        unified_c1_dev=True, unified_c1_two_intents_dev=True,
        unified_c1_journal_dev=True,
    ))
    report = json.loads(path.read_text(encoding="utf-8"))
    assert rc == 2
    assert report["stage"] == "START"
    assert report["status"] == "BLOCKED"
    assert "durable journal" in report["error"]
    assert report["actual_native_actions"] == []
    assert report["learning_in_world"] is False
    assert not (tmp_path / "c1_motion_journal.json").exists()
