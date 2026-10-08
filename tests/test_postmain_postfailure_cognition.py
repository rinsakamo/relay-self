"""S24: explicit postfailure cognition with controlled World-evidence A/B."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_local_recovery_action as s23
from relay_self.action import ActionState
from relay_self.execution_admission import AdmissionDecisionStatus
from relay_self.postfailure_cognition import (
    InvalidPostFailureEvidence,
    PostFailureWorldEvidence,
    run_explicit_postfailure_epoch,
)
from relay_self.skill import SkillState

ROOT = Path(__file__).resolve().parents[1]


def _prepared(clearance_cm=180):
    (
        data, failed, inputs, _proposed, _authorized, issued, result, _handoff,
        consequence, interpretation, closed,
    ) = s23._completed()
    assert issued.action_id == closed.action_id == s23.ACTION3
    assert result.binding_id == s23.BINDING3
    assert closed.state is ActionState.OUTCOME
    assert inputs["recovery_skill"].state is SkillState.STARTED
    assert failed.state is SkillState.FAILED
    assert interpretation.world_provenance == consequence.provenance
    evidence = PostFailureWorldEvidence(
        evidence_id=f"s24-threat-distance-{clearance_cm}",
        action_id=closed.action_id,
        binding_id=result.binding_id,
        session_id=consequence.session_id,
        consequence_provenance=consequence.provenance,
        threat_clearance_cm=clearance_cm,
        observed_at_ns=65,
        provenance=s23.p(f"postfailure-distance-{clearance_cm}"),
    )
    args = {
        "supervisor": data["supervisor"],
        "action3": closed,
        "consequence3": consequence,
        "recovery_skill": inputs["recovery_skill"],
        "intent": data["intent"],
        "owner_snapshot": data["commit"].new_state,
        "evidence": evidence,
    }
    return data, failed, inputs, args


def _run(args, **changes):
    return run_explicit_postfailure_epoch(
        **{**args, **changes},
        at_ns=70,
        provenance=s23.p("explicit-s24-epoch3"),
    )


def test_postfailure_new_evidence_changes_fresh_cognitive_selection():
    baseline_data, failed1, inputs1, original = _prepared(clearance_cm=20)
    actual_data, failed2, inputs2, updated = _prepared(clearance_cm=180)

    a = _run(original)
    b = _run(updated)

    assert a.selected_candidate == "MOVE_AWAY"
    assert b.selected_candidate == "WAIT"
    assert (a.wait_score, a.move_score) == (8, 7)
    assert (b.wait_score, b.move_score) == (4, 7)
    assert a.retained_revision == b.retained_revision == 1
    assert a.admission_status is b.admission_status is AdmissionDecisionStatus.ADMITTED
    assert a.epoch.cognition_requested is False and b.epoch.cognition_requested is False
    assert a.epoch.timed_out_actions == b.epoch.timed_out_actions == ()
    assert a.stage_ids == b.stage_ids == (
        "s24-att", "s24-blf", "s24-cnc", "s24-prd-wait", "s24-prd-move",
        "s24-plan", "s24-route", "s24-admit",
    )
    assert original["evidence"].provenance in a.source_provenance
    assert updated["evidence"].provenance in b.source_provenance
    assert a.world_evidence.threat_clearance_cm != b.world_evidence.threat_clearance_cm
    assert a.world_evidence.evidence_id != b.world_evidence.evidence_id
    assert a.world_evidence.provenance != b.world_evidence.provenance

    for data, failed, inputs in (
        (baseline_data, failed1, inputs1), (actual_data, failed2, inputs2)
    ):
        assert failed.is_current_snapshot and failed.state is SkillState.FAILED
        assert inputs["recovery_skill"].is_current_snapshot
        assert inputs["recovery_skill"].state is SkillState.STARTED
        assert data["intent"].current_intent.intent_id == failed.intent_id
        assert data["intent"].pending_reconsideration is None
        assert data["commit"].new_state.value == 4
        assert data["commit"].new_state.revision == 1
        assert data["supervisor"].open_actions == ()
        for action_id in (data["closed1"].action_id, s23.s20.ACTION2, s23.ACTION3):
            assert data["supervisor"].get(action_id).state is ActionState.OUTCOME

    record = json.loads(
        (ROOT / "docs/postmain-s24-counterfactual-ab.json").read_text(encoding="utf-8")
    )
    assert record["A"]["clearance_cm"] == a.world_evidence.threat_clearance_cm
    assert record["A"]["selection"] == a.selected_candidate
    assert record["B"]["clearance_cm"] == b.world_evidence.threat_clearance_cm
    assert record["B"]["selection"] == b.selected_candidate
    assert record["controlled"]["retained_value"] == 4
    assert record["controlled"]["retained_revision"] == 1


def test_explicit_caller_invocation_is_required_no_automatic_epoch4():
    data, _failed, _inputs, args = _prepared()
    previous_supervisor_time = data["supervisor"].last_at_ns
    assert previous_supervisor_time == 60
    assert data["supervisor"].open_actions == ()
    assert data["supervisor"].get(s23.ACTION3).state is ActionState.OUTCOME
    assert data["supervisor"].last_at_ns == previous_supervisor_time
    _run(args)
    assert data["supervisor"].last_at_ns == 70
    assert data["supervisor"].advance(
        at_ns=71, provenance=s23.p("no-next-epoch"),
    ) == ()
    assert data["supervisor"].open_actions == ()


@pytest.mark.parametrize(
    "field,value",
    [
        ("action_id", "wrong-action"),
        ("binding_id", "wrong-binding"),
        ("session_id", "wrong-session"),
        ("consequence_provenance", s23.p("wrong-parent")),
        ("observed_at_ns", 60),
    ],
)
def test_world_evidence_wrong_lineage_or_stale_rejects(field, value):
    data, _failed, _inputs, args = _prepared()
    last = data["supervisor"].last_at_ns
    with pytest.raises(InvalidPostFailureEvidence):
        _run(args, evidence=replace(args["evidence"], **{field: value}))
    assert data["supervisor"].last_at_ns == last


@pytest.mark.parametrize("value", [-1, True, 0.1, "far"])
def test_invalid_hazard_distance_fails_closed(value):
    with pytest.raises(InvalidPostFailureEvidence):
        _ = PostFailureWorldEvidence(
            "E", s23.ACTION3, s23.BINDING3, s23.SESSION3, s23.p("world3"),
            value, 65, s23.p("observation"),
        )


def test_old_retained_revision_does_not_silently_pass_as_current():
    data, _failed, _inputs, args = _prepared()
    previous = data["commit"].previous_state
    with pytest.raises(InvalidPostFailureEvidence):
        _run(args, owner_snapshot=previous)
    assert data["supervisor"].last_at_ns == 60


def test_skill_closure_after_evidence_invalidates_explicit_cognition():
    data, _failed, inputs, args = _prepared()
    _closed = inputs["recovery_skill"].fail(
        reason="separate-caller-closure", at_ns=66,
        provenance=s23.p("no-longer-started"),
    )
    with pytest.raises(InvalidPostFailureEvidence):
        _run(args)
    assert data["supervisor"].last_at_ns == 60


def test_pending_or_released_intent_rejects_new_epoch():
    for kind in ("pending", "released"):
        data, failed, _inputs, args = _prepared()
        if kind == "pending":
            data["intent"].request_reconsideration(
                failed.intent_id,
                reason="separate-world-challenge", at_ns=67,
                provenance=s23.p("intent-pending"),
            )
        else:
            data["intent"].invalidate(
                failed.intent_id,
                reason="separate-world-challenge", at_ns=67,
                provenance=s23.p("intent-released"),
            )
        with pytest.raises(InvalidPostFailureEvidence):
            _run(args)
        assert data["supervisor"].last_at_ns == 60


def test_stale_action3_or_undetermined_consequence_rejected():
    data, _failed, _inputs, args = _prepared()
    with pytest.raises(InvalidPostFailureEvidence):
        _run(args, action3=data["closed1"])
    with pytest.raises(InvalidPostFailureEvidence):
        _run(
            args, consequence3=replace(
                args["consequence3"],
                status=type(args["consequence3"].status).UNDETERMINED,
            ),
        )


def test_provenance_cannot_be_same_as_original_world_consequence():
    data, _failed, _inputs, args = _prepared()
    with pytest.raises(InvalidPostFailureEvidence):
        _run(
            args, evidence=replace(
                args["evidence"], provenance=args["consequence3"].provenance,
            ),
        )


def test_early_caller_epoch_time_rejected():
    data, _failed, _inputs, args = _prepared()
    with pytest.raises(InvalidPostFailureEvidence):
        run_explicit_postfailure_epoch(
            **args, at_ns=64, provenance=s23.p("early-epoch"),
        )
    assert data["supervisor"].last_at_ns == 60


def test_s24_receipt_scope():
    receipt = json.loads(
        (ROOT / "docs/postmain-s24-receipt.json").read_text(encoding="utf-8")
    )
    assert receipt["base_head"] == "e519af52d2b7aa8a910f096df04d0a4802ccc823"
    assert receipt["classification"] == "EXPLICIT_POSTFAILURE_WORLD_EVIDENCE_RECOGNITION_QUALIFIED"
    assert receipt["explicit_third_epoch"] is True
    assert receipt["automatic_reentry"] is False
    assert receipt["fresh_att_blf_cnc_prd_plan"] is True
    assert receipt["new_physical_primitive"] is False
    assert receipt["live_minecraft"] == "NOT_RUN"
