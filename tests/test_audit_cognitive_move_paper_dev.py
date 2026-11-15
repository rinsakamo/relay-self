"""Offline-only replay of full L0 MOVE + native/WAL + Paper tick originals."""
from __future__ import annotations

import copy
import json
import sys
from dataclasses import asdict

import pytest

from experiments.audit_cognitive_move_paper_dev import (
    audit_move_paper_bundle,
    main,
)
from experiments.cognitive_move_paper_witness_dev import qualify_paper_move_trace
from experiments.run_cognitive_minimal_world import _native_observation_record
from relay_self.physical_action_journal import PhysicalActionJournal
from test_cognitive_move_paper_witness_dev import (
    ACTION,
    ACTOR,
    BOOT,
    NONCE,
    SESSION,
    WORLD,
    _data,
    _with_actor_join,
)
from test_cognitive_physical_move_issue_dev import run, setup


def bundle(tmp_path):
    kw, session = setup(tmp_path)
    result = run(kw, session)
    journal = PhysicalActionJournal.restore(
        kw["journal"].path, self_id="self-A",
    )
    row = journal.records[-1]
    raw, log = _data()
    raw = raw.replace(ACTION.encode(), b"action-M").replace(
        SESSION.encode(), b"world-A",
    )
    log = _with_actor_join(log).replace(
        ACTION.encode(), b"action-M",
    )
    paper = qualify_paper_move_trace(
        raw, nonce=NONCE, world_uuid=WORLD, actor_uuid=ACTOR,
        action_id="action-M", native_session_id="world-A",
        native_start=kw["target"].native_position,
        native_target=kw["target"].destination_position,
        paper_owned_log=log, expected_username="RelaySelf",
    )
    effects = [result.look, result.forward, result.stop]
    data = {
        "evidence_class": "REAL_LLM_AND_NATIVE_WORLD_DEV_ATTEMPT",
        "qualification": "NOT_CLAIMED",
        "status": "NATIVE_MOVE_PROGRESS_STOP_READBACK_DEV_ONLY",
        "physical_move_dev_selected": True,
        "initial_skill_ir": "MOVE@1",
        "initial_skill_step_status": "PROPOSED_NOT_ISSUED",
        "initial_skill_evaluation_status": "YIELD_EVALUATION",
        "action_outcome_count": 1,
        "physical_journal_unresolved": False,
        "paper_move_position_stable_8_ticks": True,
        "native_move_paper_settled_attested": False,
        "native_move_arrival_attested": False,
        "physical_fence": "PREISSUE_WAL_MOVE_DEV",
        "physical_actionport_preissue_wal": "FSYNC_CAS_MOVE_DEV",
        "physical_journal_records": list(journal.records),
        "physical_move_parent_action_id": row["action_id"],
        "world_session": row["session_id"],
        "native_actions": [{"action_id": row["action_id"], "state": "outcome"}],
        "selected": {
            "skill_id": "MOVE", "skill_version": 1,
            "goal_id": "EXPLORE_WORLD", "target_ref": row["target_ref"],
        },
        "move_target": asdict(kw["target"]),
        "native_effect_receipts": [
            {
                "action_id": e.action_id, "effect": e.effect,
                "result": e.result, "session_id": e.session_id,
                "native_seq": e.seq,
            } for e in effects
        ],
        "native_move_progress_observation": _native_observation_record(
            result.progress,
        ),
        "native_move_stop_probes": [
            _native_observation_record(result.first_stop),
            _native_observation_record(result.final_stop),
        ],
        "paper_move_tick_proof": asdict(paper),
        "native_move_progress_m": result.distance_advanced,
        "native_move_stop_residual_m": result.residual_motion,
    }
    return data, journal, raw, log


def replay(data, journal, raw, log):
    return audit_move_paper_bundle(
        data, journal=journal, prepared_journal=PhysicalActionJournal.restore(
            journal.path.with_name(journal.path.name + ".move-prepared"), self_id="self-A"),
        raw_trace=raw, raw_paper_log=log,
        expected_self_id="self-A", expected_actor_uuid=ACTOR,
        expected_world_uuid=WORLD, expected_username="RelaySelf",
    )


def test_full_move_audit_independently_replays_four_original_sources(tmp_path):
    data, journal, raw, log = bundle(tmp_path)
    result = replay(data, journal, raw, log)
    assert result["classification"] == (
        "PAPER_8TICK_POSITION_STABILITY_DEV_BUNDLE_RECHECKED"
    )
    assert result["action_id"] == "action-M"
    assert result["paper_boot_id"] == BOOT
    assert result["paper_arm_tick"] == 100
    assert result["paper_stop_mark_tick"] == 110
    assert result["paper_stable_end_tick"] == 126
    assert result["paper_stable_max_3d_drift_m"] == 0
    assert result["qualifying_real_world"] is False
    assert result["causal_paper_stop_ack_attested"] is False
    assert result["checkpoint_resume_authorized"] is False
    assert journal.unresolved is False


@pytest.mark.parametrize("tamper", [
    "paper_wrong_action", "wrong_boot", "wrong_paper_username",
    "paper_drift", "wrong_world_uuid", "fake_claim", "wrong_wal_record",
    "wrong_target", "wrong_position", "wrong_native_receipt",
    "changed_receipt_seq", "wrong_native_progress", "wrong_stop_probe",
    "missing_after_probe", "wrong_self", "wrong_native_action",
    "wrong_native_world", "wrong_paper_proof", "missing_proof",
])
def test_cross_source_tampering_or_claim_inflation_never_passes(tmp_path, tamper):
    data, journal, raw, log = bundle(tmp_path)
    data = copy.deepcopy(data)
    expected_self = "self-A"
    expected_world = WORLD
    if tamper == "paper_wrong_action":
        raw = raw.replace(b"action-M", b"other-action")
    elif tamper == "wrong_boot":
        log = log.replace(BOOT.encode(), b"00000000-0000-4000-8000-000000000000")
    elif tamper == "wrong_paper_username":
        log = log.replace(b"name=RelaySelf", b"name=OtherSelf")
    elif tamper == "paper_drift":
        raw = raw.replace(
            b"sample=125,0.6,64.0,0.0", b"sample=125,0.9,64.0,0.0",
        )
    elif tamper == "wrong_world_uuid":
        expected_world = "00000000-0000-4000-8000-000000000000"
    elif tamper == "fake_claim":
        data["native_move_paper_settled_attested"] = True
    elif tamper == "wrong_wal_record":
        data["physical_journal_records"][-1]["motion"]["start"][0] = 1
    elif tamper == "wrong_target":
        data["move_target"]["target_ref"] = "destination:forged"
    elif tamper == "wrong_position":
        data["move_target"]["native_position"]["x"] = 1
    elif tamper == "wrong_native_receipt":
        data["native_effect_receipts"][1]["effect"] = "clear_controls"
    elif tamper == "changed_receipt_seq":
        data["native_effect_receipts"][2]["native_seq"] = 999
    elif tamper == "wrong_native_progress":
        data["native_move_progress_observation"]["observation"]["seq"] = 456
    elif tamper == "wrong_stop_probe":
        data["native_move_stop_probes"][1]["observation"]["snapshot"]["position"]["x"] = 9
    elif tamper == "missing_after_probe":
        data["native_move_stop_probes"] = data["native_move_stop_probes"][:1]
    elif tamper == "wrong_self":
        expected_self = "another-self"
    elif tamper == "wrong_native_action":
        data["native_actions"][0]["action_id"] = "wrong-action"
    elif tamper == "wrong_native_world":
        data["world_session"] = "another-world"
    elif tamper == "wrong_paper_proof":
        data["paper_move_tick_proof"]["paper_residual_max_m"] = 0.02
    elif tamper == "missing_proof":
        data["paper_move_tick_proof"] = None
    with pytest.raises(ValueError):
        audit_move_paper_bundle(
            data, journal=journal, prepared_journal=PhysicalActionJournal.restore(
            journal.path.with_name(journal.path.name + ".move-prepared"), self_id="self-A"),
        raw_trace=raw, raw_paper_log=log,
            expected_self_id=expected_self, expected_actor_uuid=ACTOR,
            expected_world_uuid=expected_world, expected_username="RelaySelf",
        )


def test_readonly_audit_cli_checks_original_hashes_and_never_overwrites(tmp_path, monkeypatch):
    data, journal, raw, log = bundle(tmp_path)
    manifest = tmp_path / "recheck.json"
    evidence = tmp_path / "evidence.json"
    paper_trace = tmp_path / "trace.raw"
    paper_log = tmp_path / "paper-owned.log"
    evidence.write_text(json.dumps(data))
    paper_trace.write_bytes(raw)
    paper_log.write_bytes(log)
    arguments = [
        "audit", "--evidence", str(evidence), "--wal", str(journal.path),
        "--prepared-wal", str(journal.path.with_name(journal.path.name + ".move-prepared")),
        "--paper-trace", str(paper_trace), "--paper-owned-log", str(paper_log),
        "--self-id", "self-A", "--actor-uuid", ACTOR, "--world-uuid", WORLD,
        "--mc-username", "RelaySelf", "--output", str(manifest),
    ]
    monkeypatch.setattr(sys, "argv", arguments)
    assert main() == 0
    result = json.loads(manifest.read_text())
    assert result["qualifying_real_world"] is False
    assert len(result["wal_json_sha256"]) == 64
    assert len(result["evidence_json_sha256"]) == 64
    assert main() == 1
    assert json.loads(manifest.read_text()) == result


def test_audit_rejects_terminal_wal_as_prepared_original(tmp_path):
    data, journal, raw, log = bundle(tmp_path)
    with pytest.raises(ValueError):
        audit_move_paper_bundle(
            data, journal=journal, prepared_journal=journal, raw_trace=raw,
            raw_paper_log=log, expected_self_id="self-A", expected_actor_uuid=ACTOR,
            expected_world_uuid=WORLD, expected_username="RelaySelf",
        )
