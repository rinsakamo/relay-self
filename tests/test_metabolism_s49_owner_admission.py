"""M S49 original completion admission versus pinned S49 product #674.

All positive inputs are built from typed original S49 fixture objects. The
saved JSON report is SYNTHETIC even though its field shapes and decoded native
evidence verifier are the actual S49 product implementations. This test does
NOT read the user's real stored /home/rinsa/work evidence directory.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_s49_completed_decision_bridge as s49_original_test
from adapters.mineflayer.s49_completed_decision_bridge import (
    bounded_original_s49_completion_row,
    read_original_s49_completions,
)
from adapters.mineflayer.self_action_evidence import capture_native_action_evidence
from experiments.metabolism_s49_owner_admission import (
    S49MAdmissionLease,
    S49MAdmissionRejected,
    admit_original_s49_batch,
    admit_saved_s49_report,
    bounded_s49_m_admission_row,
)


def _owner_batch():
    steps, probes, receipts = s49_original_test._synthetic_original_shape()
    new_steps = []
    new_probes = {}
    for step in steps:
        native = probes[step.choice.probe_seq]
        rid = f"s49-actual:{native.session_id}:event-{step.event_seq}"
        new_probe = replace(native, request_id=rid)
        new_step = replace(step, choice=replace(step.choice, request_id=rid))
        new_steps.append(new_step)
        new_probes[new_probe.seq] = new_probe
    move = new_steps[0]
    original = receipts[move.action_request_id]
    # Same structurally valid S16 receipt, but original S49 source frames
    # require an Action-specific clear ID and a matching true x/z movement.
    consequence = original.consequence
    before = new_probes[move.choice.probe_seq]
    shifted = replace(
        before,
        seq=consequence.after_observation.seq,
        snapshot=replace(
            before.snapshot,
            position=replace(
                before.snapshot.position,
                x=before.snapshot.position.x + 0.31,
            ),
        ),
    )
    consequence = replace(
        consequence,
        before_observation=before,
        after_observation=shifted,
        cleanup_receipt=replace(
            consequence.cleanup_receipt,
            action_id=move.action_request_id + "-s15-clear",
        ),
    )
    new_receipt = replace(original, consequence=consequence)
    new_receipts = {move.action_request_id: new_receipt}
    batch = read_original_s49_completions(
        tuple(new_steps), new_probes, new_receipts,
    )
    return batch


def _saved_report(batch):
    row = bounded_original_s49_completion_row(batch)
    decisions = []
    pairs = []
    actions = []
    for item in batch.steps:
        d = item.step
        decisions.append({
            "event_seq": d.event_seq, "probe_seq": item.probe.seq,
            "selected": d.choice.selection.value,
            "issued": d.asks_for_action,
            "entity_id": d.choice.entity_id,
            "distance_m": d.choice.distance_m,
        })
        pairs.append({
            "event_seq": d.event_seq,
            "probe_seq": item.probe.seq,
            "event_kind": "entities", "event_entities": [],
            "probe_entities": [],
        })
        if item.action_receipt is not None:
            consequence = item.action_receipt.consequence
            actions.append({
                "event_seq": d.event_seq, "probe_seq": item.probe.seq,
                "action": d.action_request_id, "terminal": "outcome",
                "source": batch.session_id,
                "movement_m": consequence.movement_distance,
                "execution_evidence": capture_native_action_evidence(consequence),
            })
    return {
        "status": "PASS",
        "session_id": batch.session_id,
        "original_completion_observer": "CALLBACK_RETURNED",
        "node_exit": 0, "server_exit": 0,
        "original_completion_readback": row,
        "decisions": decisions,
        "source_pair_trace": pairs,
        "actual_native_actions": actions,
        "classification": "DEV_ORIGINAL_S49_SHAPE_NOT_QUALIFIED",
    }


def test_typed_source_owner_admitted_without_s42_b0_l8_or_model_cost():
    batch = _owner_batch()
    seen = tuple((id(x.step), id(x.probe), id(x.action_receipt))
                 for x in batch.steps)
    lease = S49MAdmissionLease(enabled=True)
    out = lease.admit_batch(batch)
    assert out.status == "RECORDED"
    assert out.admission.kind == "ORIGINAL_PYTHON_BATCH"
    assert out.admission.outcome_count == 1
    assert out.admission.wait_count == 1
    assert tuple((id(x.step), id(x.probe), id(x.action_receipt))
                 for x in batch.steps) == seen
    row = bounded_s49_m_admission_row(out)
    assert row["provider_calls"] is None
    assert row["input_tokens"] is None
    assert row["metabolic_energy"] == "UNKNOWN_NO_B0_OWNER"
    assert row["l8_learning"] == "UNKNOWN_NO_L8_OWNER"
    assert not row["real_s42_epoch_supplied"]
    assert not row["source_attested"] and not row["action_authority"]
    assert row["new_native_reads"] == row["new_model_calls"] == 0
    assert lease.admit_batch(batch).status == "DEFERRED"


def test_serialized_saved_report_is_only_internal_consistency_not_python_identity():
    batch = _owner_batch()
    report = _saved_report(batch)
    out = S49MAdmissionLease(enabled=True).admit_report(report)
    assert out.status == "RECORDED"
    assert out.admission.kind == "SAVED_REPORT_JSON"
    assert out.admission.session_id == batch.session_id
    assert out.admission.outcome_count == 1
    assert bounded_s49_m_admission_row(out)["source_attested"] is False
    assert "snapshot" not in repr(bounded_s49_m_admission_row(out))
    assert "movement_m" not in repr(bounded_s49_m_admission_row(out))


def test_cross_kind_replay_rejected_on_same_lease():
    batch = _owner_batch()
    lease = S49MAdmissionLease(enabled=True)
    assert lease.admit_batch(batch).status == "RECORDED"
    assert lease.admit_report(_saved_report(batch)).status == "DEFERRED"


@pytest.mark.parametrize("attack", (
    "no_status", "no_callback", "node_unclean", "foreign_session",
    "false_s42", "false_b0", "false_l8", "forged_action_authority",
    "nonzero_model", "replayed_source", "missing_decision",
    "foreign_probe", "wrong_choice", "wrong_source_pair",
    "wrong_action_id", "no_movement_evidence", "no_clear",
    "reordered_native", "wrong_native_movement", "wrong_terminal",
    "missing_action", "extra_action", "wrong_action_probe",
    "forged_native_provenance", "foreign_action_source",
))
def test_bad_saved_report_does_not_mint_s49_admission(attack):
    report = _saved_report(_owner_batch())
    row = report["original_completion_readback"]
    action = report["actual_native_actions"][0]
    evidence = action["execution_evidence"]
    if attack == "no_status":
        report["status"] = "FAIL"
    elif attack == "no_callback":
        report["original_completion_observer"] = "OBSERVER_ERROR"
    elif attack == "node_unclean":
        report["node_exit"] = 1
    elif attack == "foreign_session":
        report["session_id"] = "forged-session"
    elif attack == "false_s42":
        row["real_s42_epoch_supplied"] = True
    elif attack == "false_b0":
        row["real_b0_decision_supplied"] = True
    elif attack == "false_l8":
        row["real_l8_epoch_supplied"] = True
    elif attack == "forged_action_authority":
        row["action_authority"] = True
    elif attack == "nonzero_model":
        row["new_model_calls"] = 1
    elif attack == "replayed_source":
        row["decisions"][1]["event_seq"] = row["decisions"][0]["event_seq"]
    elif attack == "missing_decision":
        row["decisions"].pop()
    elif attack == "foreign_probe":
        row["decisions"][0]["probe_seq"] += 1
    elif attack == "wrong_choice":
        row["decisions"][0]["choice"] = "WAIT"
    elif attack == "wrong_source_pair":
        report["source_pair_trace"][0]["probe_seq"] += 1
    elif attack == "wrong_action_id":
        action["action"] = "other-action"
    elif attack == "no_movement_evidence":
        action["execution_evidence"] = None
    elif attack == "no_clear":
        evidence["cleanup_receipt"]["result"] = "rejected"
    elif attack == "reordered_native":
        evidence["cleanup_receipt"]["seq"] = evidence["dispatch_receipt"]["seq"]
    elif attack == "wrong_native_movement":
        evidence["movement_m"] = 8.0
    elif attack == "wrong_terminal":
        action["terminal"] = "unknown"
    elif attack == "missing_action":
        report["actual_native_actions"] = []
    elif attack == "extra_action":
        report["actual_native_actions"].append(action)
    elif attack == "wrong_action_probe":
        action["probe_seq"] += 1
    elif attack == "forged_native_provenance":
        evidence["before_observation"]["provenance"]["source"] = "other"
    elif attack == "foreign_action_source":
        action["source"] = "other"
    lease = S49MAdmissionLease(enabled=True)
    assert lease.admit_report(report).status == "DEFERRED"


def test_replayed_typed_objects_and_forged_metadata_are_rejected():
    batch = _owner_batch()
    mutated = replace(batch, real_l8_epoch_supplied=True)
    with pytest.raises(S49MAdmissionRejected):
        admit_original_s49_batch(mutated)
    wrong_items = tuple(
        replace(s, action_authority=True) if i == 0 else s
        for i, s in enumerate(batch.steps)
    )
    with pytest.raises(S49MAdmissionRejected):
        admit_original_s49_batch(replace(batch, steps=wrong_items))


def test_report_validator_does_not_change_input():
    report = _saved_report(_owner_batch())
    before = repr(report)
    result = admit_saved_s49_report(report)
    assert result.kind == "SAVED_REPORT_JSON"
    assert repr(report) == before


def test_disabled_does_not_examine_world_or_source():
    class NoAccess:
        def __getattribute__(self, name):
            raise AssertionError("M default-OFF observed owner " + name)

    lease = S49MAdmissionLease()
    obj = NoAccess()
    assert lease.admit_batch(obj).status == "DISABLED"
    assert lease.admit_report(obj).status == "DISABLED"


@pytest.mark.parametrize("attack", [
    {"source_attested": True}, {"action_authority": True},
])
def test_bounded_M_export_rejects_forged_authority(attack):
    out = S49MAdmissionLease().admit_report(object())
    with pytest.raises(S49MAdmissionRejected):
        bounded_s49_m_admission_row(replace(out, **attack))


def test_invalid_lease_fails_before_source():
    with pytest.raises(ValueError):
        S49MAdmissionLease(enabled=1)
    with pytest.raises(ValueError):
        S49MAdmissionLease(enabled=True, max_batches=0)
    with pytest.raises(ValueError):
        S49MAdmissionLease(enabled=True, max_batches=9)
