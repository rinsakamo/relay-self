"""I6: real S15/S16/S17 Python types, deliberately fake Mineflayer input.

Each positive only shows coherent existing owner/type logic, never physical
source authentication, genuine competing actions or production S11 acquisition.
"""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

import test_action_feedback_qualification as s17
from adapters.mineflayer.execution import (
    MOVE_BACKWARD_DURATION_S,
    MineflayerCommand,
)
from experiments import ac_integration_i6_native_interlock as i6
from experiments.ac_b_b11_governed_habit import CurrentWorld
from experiments.ac_b_b16_quorum import (
    BatchLedger,
    QuorumNotQualified,
    issue_observed_trial,
)
from relay_self.action_feedback import (
    LearningFeedbackInterpretationStatus,
    interpret_action_outcome_as_learning_feedback,
)
from relay_self.action_outcome import ActionOutcomeDisposition


def _subject(*, noisy=False):
    chain = s17.executed_closed_chain()
    binding, supervisor, issued, consequence, outcome, closed = (
        chain[15],
        chain[17],
        chain[18],
        chain[19],
        chain[20],
        chain[21],
    )
    command = MineflayerCommand(
        action_id=issued.action_id,
        binding_id=binding.binding_id,
        action_ref=binding.action_ref,
        effect="set_control",
        control="back",
        state=True,
        duration_s=MOVE_BACKWARD_DURATION_S,
        cleanup_action_id=f"{issued.action_id}-s15-clear",
    )
    criterion = s17.feedback_criterion()
    fb = interpret_action_outcome_as_learning_feedback(
        closed, outcome, criterion,
        provenance=s17.provenance("i6-synthetic-s17-feedback"),
    )
    native = i6.NativeShape(
        issued=issued, command=command, binding=binding,
        consequence=consequence, outcome=outcome, closed=closed,
        supervisor=supervisor, criterion=criterion, feedback=fb,
    )
    session = "b16-offline-noisy" if noisy else "b16-offline-clean"
    world = CurrentWorld(session=session)
    batch = BatchLedger(
        world, 0, 0,
        tuple(issue_observed_trial(world, 0, 0, idx, noisy=noisy)
              for idx in range(5)),
    )
    return native, batch


def _audit(native, batch, **overrides):
    roots = {
        "caller_source_consequence": native.consequence,
        "caller_current_closed": native.closed,
        "caller_current_feedback": native.feedback,
        "caller_current_b16": batch,
    }
    roots.update(overrides)
    return i6.adjudicate_i6(
        native, roots.pop("caller_source_consequence"),
        roots.pop("caller_current_closed"),
        roots.pop("caller_current_feedback"),
        batch, roots.pop("caller_current_b16"), **roots,
    )


def test_i6_prospective_manifest_and_causal_source_gaps_are_frozen():
    m = i6.read_manifest()
    assert m["issue"] == 529
    assert m["native_s15_action_refs"] == ["MOVE_BACKWARD"]
    assert m["physical_source_attested"] is False
    assert m["true_native_s15_competing_actions"] is False
    assert m["c15_spatial_label_signed"] is False
    assert m["s11_production_grant"] is False
    assert m["production_go"] is False
    assert m["b16_matched_cheap_outcomes"] == {
        "s11_success": 6, "cheap_success": 6,
    }


@pytest.mark.parametrize("noisy", [False, True])
def test_actual_s15_s16_s17_fake_source_types_and_foreign_b16_denied(noisy):
    native, batch = _subject(noisy=noisy)
    old_snapshot = native.supervisor.get(native.closed.action_id)
    old_batch = batch.trials
    old_world_count = batch.world.actions_executed
    assert native.issued.is_current_snapshot is False
    assert native.closed.is_current_snapshot is True
    assert native.feedback.status is LearningFeedbackInterpretationStatus.PRODUCED
    verdict = _audit(native, batch)
    assert verdict.classification == (
        "I6_OFFLINE_NATIVE_SHAPED_LINEAGE_AND_FOREIGN_SOURCE_DENIAL_QUALIFIED"
    )
    assert verdict.native_action_id == "action-move-backward-1"
    assert verdict.native_s17_target == "risk_weight"
    assert verdict.b16_foreign_session == batch.session
    assert verdict.b16_source_pairs == 5
    assert verdict.syntactic_native_lineage is True
    assert verdict.foreign_simulator_ledger_well_typed is True
    for field in (
        "shared_causal_world", "native_competing_action_witnesses",
        "native_goal_success_signed", "physical_source_attested",
        "production_s11_grant", "durable_replay_ledger",
        "matched_native_cost_gain", "production_go",
    ):
        assert getattr(verdict, field) is False
    assert native.supervisor.get(native.closed.action_id) is old_snapshot
    assert batch.trials == old_batch
    assert batch.world.actions_executed == old_world_count


@pytest.mark.parametrize("requested", [
    "production", "physical", "native_minecraft", "authorize_action",
    "issue", "commit_habit", "commit_learning", "L0", "L2",
    "join_b16_by_CI", "join_by_matching_action_label", "attested",
])
def test_all_runtime_promotions_are_explicitly_denied(requested):
    native, batch = _subject()
    with pytest.raises(i6.I6PromotionDenied):
        _audit(native, batch, requested_mode=requested)


@pytest.mark.parametrize("mutation", [
    "source_copy",
    "closed_copy",
    "feedback_copy",
    "wrong_consequence_session",
    "wrong_consequence_status",
    "wrong_consequence_action",
    "missing_dispatch",
    "cloned_after_observation",
    "source_sequence_swap",
    "outcome_wrong_session",
    "outcome_wrong_disposition",
    "outcome_wrong_reason",
    "feedback_wrong_target",
    "feedback_wrong_status",
    "criterion_wrong_target",
    "criterion_wrong_orientation",
    "wrong_issued_history",
    "wrong_command_binding",
])
def test_s15_s16_s17_source_grant_and_outcome_tamper_fails_closed(mutation):
    native, batch = _subject()
    if mutation == "source_copy":
        with pytest.raises(i6.I6Rejected):
            _audit(
                native, batch,
                caller_source_consequence=replace(native.consequence),
            )
        return
    if mutation == "closed_copy":
        with pytest.raises(i6.I6Rejected):
            _audit(native, batch, caller_current_closed=replace(native.closed))
        return
    if mutation == "feedback_copy":
        with pytest.raises(i6.I6Rejected):
            _audit(native, batch, caller_current_feedback=replace(native.feedback))
        return

    if mutation.startswith("wrong_consequence"):
        field = "session_id" if mutation.endswith("session") else (
            "action_id" if mutation.endswith("action") else "status"
        )
        value = "not-source" if field == "session_id" else (
            "not-action" if field == "action_id" else "undetermined"
        )
        replaced = replace(native.consequence, **{field: value})
        native = replace(native, consequence=replaced)
    elif mutation == "missing_dispatch":
        native = replace(
            native, consequence=replace(native.consequence, dispatch_receipt=None),
        )
    elif mutation == "cloned_after_observation":
        native = replace(
            native, consequence=replace(
                native.consequence,
                after_observation=replace(native.consequence.after_observation),
            ),
        )
        # An equal-valued clone is not a physical source attestation.
        # This controls source-root check; the structural check may pass,
        # but the public verdict never grants physical provenance.
        assert _audit(native, batch).physical_source_attested is False
        return
    elif mutation == "source_sequence_swap":
        before = native.consequence.before_observation
        after = native.consequence.after_observation
        native = replace(
            native, consequence=replace(
                native.consequence,
                before_observation=after,
                after_observation=before,
            ),
        )
    elif mutation.startswith("outcome_wrong"):
        field = {
            "outcome_wrong_session": "session_id",
            "outcome_wrong_disposition": "disposition",
            "outcome_wrong_reason": "reason_code",
        }[mutation]
        value = {
            "session_id": "other-session",
            "disposition": ActionOutcomeDisposition.UNKNOWN,
            "reason_code": "pretend_success",
        }[field]
        native = replace(native, outcome=replace(native.outcome, **{field: value}))
    elif mutation == "feedback_wrong_target":
        native = replace(
            native, feedback=replace(native.feedback, target_id="other-target"),
        )
    elif mutation == "feedback_wrong_status":
        native = replace(
            native, feedback=replace(
                native.feedback, status=LearningFeedbackInterpretationStatus.NOT_APPLICABLE,
                feedback=None,
            ),
        )
    elif mutation == "criterion_wrong_target":
        native = replace(
            native, criterion=replace(native.criterion, target_id="other-target"),
        )
    elif mutation == "criterion_wrong_orientation":
        native = replace(
            native, criterion=replace(
                native.criterion, required_outcome_reason="goal_safe_and_correct",
            ),
        )
    elif mutation == "wrong_issued_history":
        native = replace(native, issued=replace(native.issued, action_id="foreign-id"))
    else:
        native = replace(
            native, command=replace(
                native.command, binding_id="foreign-binding",
            ),
        )
    with pytest.raises(ValueError):
        _audit(native, batch)


def test_current_b16_ledger_cannot_be_reconstructed_or_pretend_same_source():
    native, batch = _subject()
    with pytest.raises(i6.I6Rejected):
        _audit(native, batch, caller_current_b16=object())
    foreign = CurrentWorld(session=batch.session)
    with pytest.raises(QuorumNotQualified):
        BatchLedger(foreign, 0, 0, batch.trials)
    with pytest.raises(i6.I6Rejected):
        _audit(native, batch, requested_mode="physical")


def test_one_s15_action_ref_and_synthetic_C15_goal_cannot_license_competitor():
    native, batch = _subject()
    with pytest.raises(ValueError):
        replace(native.command, action_ref="MOVE_FORWARD")
    verdict = _audit(native, batch)
    assert verdict.native_competing_action_witnesses is False
    assert verdict.native_goal_success_signed is False


def test_frozen_manifest_tamper_and_duplicate_json_rejected(tmp_path, monkeypatch):
    original = i6.read_manifest()
    original["true_native_s15_competing_actions"] = True
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setattr(i6, "MANIFEST", bad)
    with pytest.raises(i6.I6Rejected):
        i6.read_manifest()
    bad.write_text('{"issue":529,"issue":529}', encoding="utf-8")
    with pytest.raises(i6.I6Rejected):
        i6.read_manifest()


def test_no_world_execution_or_learning_side_effects_in_gate():
    with open(i6.__file__, encoding="utf-8") as stream:
        source = stream.read()
    for banned in (
        "execute_mineflayer_command(", "record_interpreted_action_outcome(",
        "commit_learning_update(", "commit_test_quorum_habit(",
        ".authorize(", ".issue(", "world.act(",
        "asyncio.create_task(", "heldout_score(",
    ):
        assert banned not in source
