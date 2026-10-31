"""L17 source-shaped independent Goal handoff: no real World / no training."""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

import test_l13_independent_goal_receipt as l13
import test_l15_s49_original_goal_preflight as l15
import test_l16_s49_first_action_original_capture as l16
from relay_self.l13_independent_goal_receipt import L13ReceiptStatus
from relay_self.l17_first_action_goal_handoff import (
    L17HandoffRejected,
    L17HandoffStatus,
    L17IndependentInputs,
    review_l17_first_action_goal,
)


def source(external=True):
    """All bytes below are deterministic synthetic fixture originals."""
    args = l16.fixture()
    item = l15.s49_original_source()
    assert args["received_original"] == item["received_original"]
    assert args["sent_original"] == item["sent_original"]
    assert args["plan_original"] == args["plan"].original_bytes()
    if external:
        args["external"] = L17IndependentInputs(
            criterion_original=item["external_criterion_original"],
            admitted_criterion_sha256=item[
                "independently_admitted_criterion_sha256"
            ],
            receipt_triplet=item["item"],
            admission=item["admission"],
            current=item["current"],
        )
    return args


def test_l16_only_source_waits_for_real_independent_originals():
    args = source(external=False)
    result = review_l17_first_action_goal(**args)
    assert result.status is L17HandoffStatus.WAITING_FOR_EXTERNAL_ORIGINALS
    assert result.l16_first_action.observed_goal_status == "REACHED"
    assert result.l14_independent_goal is None
    assert not result.l10_previous_epoch_candidate_available
    assert result.pending_external_s16_original
    assert result.pending_independent_goal_original
    assert result.qualified_real_training_pairs == 0
    assert result.s10_updates == result.s11_habit_grants == 0


def test_independent_source_shaped_goal_only_candidate_not_physical_learning():
    r = review_l17_first_action_goal(**source())
    assert r.status is L17HandoffStatus.SOURCE_SHAPED_L10_CANDIDATE
    assert r.l14_independent_goal is not None
    assert r.l10_previous_epoch_candidate_available
    assert r.l14_independent_goal.l13_source_shaped_candidate.status is (
        L13ReceiptStatus.SOURCE_SHAPED_GOAL_CANDIDATE
    )
    assert r.l14_independent_goal.l13_source_shaped_candidate.prior_l10 is not None
    assert not r.l14_independent_goal.independent_physical_goal_authenticated
    assert not r.l14_independent_goal.actual_intervention_absence_proven
    assert r.pending_independent_original_authentication
    assert r.pending_physical_nonintervention_review
    assert r.qualified_real_training_pairs == r.real_l10_adoptions == 0
    assert r.s10_updates == r.s11_habit_grants == 0
    assert r.new_actions == r.new_worlds == 0
    assert r.l14_independent_goal.original_sent_sha256 == hashlib.sha256(
        source()["sent_original"],
    ).hexdigest()


def _stable_negative(args):
    goal = args["external"].receipt_triplet.raw_external_goal
    data = json.loads(goal)
    data["goal_status"] = "NOT_REACHED"
    raw_goal = l13.raw(data)
    inp = args["external"]
    args["external"] = replace(
        inp,
        receipt_triplet=replace(
            inp.receipt_triplet, raw_external_goal=raw_goal,
        ),
        admission=replace(
            inp.admission,
            admitted_goal_sha256=frozenset({l13.sha(raw_goal)}),
        ),
    )
    # Shift the original target and independently supplied criterion *and*
    # the pre-World operator plan in agreement. A different status is now
    # observationally consistent, but none of these fixtures is real.
    plan = replace(args["plan"], target_x=args["plan"].target_x + 30)
    args["plan"] = plan
    args["plan_original"] = plan.original_bytes()
    criterion = json.loads(inp.criterion_original)
    criterion["target_x"] = plan.target_x
    raw_criterion = l13.raw(criterion)
    args["external"] = replace(
        args["external"],
        criterion_original=raw_criterion,
        admitted_criterion_sha256=frozenset({l13.sha(raw_criterion)}),
    )


def test_source_shaped_not_reached_still_no_physical_reward():
    args = source()
    _stable_negative(args)
    r = review_l17_first_action_goal(**args)
    assert r.status is L17HandoffStatus.SOURCE_SHAPED_L10_CANDIDATE
    assert r.l16_first_action.observed_goal_status == "NOT_REACHED"
    assert r.l14_independent_goal.l13_source_shaped_candidate.goal_label.goal_reached is False
    assert r.qualified_real_training_pairs == r.s10_updates == 0


def test_unstable_native_goal_is_unknown_and_never_negative_reward():
    args = source()
    lines = args["received_original"].splitlines(keepends=True)
    d = json.loads(lines[-1])
    d["snapshot"]["position"]["x"] += 0.3
    lines[-1] = l13.raw(d)
    args["received_original"] = b"".join(lines)
    args["s7_receipt"] = l15.l14._index(
        args["received_original"], args["sent_original"],
    )
    inp = args["external"]
    goal = json.loads(inp.receipt_triplet.raw_external_goal)
    goal["goal_status"] = "UNDETERMINED"
    goal_original = l13.raw(goal)
    args["external"] = replace(
        inp,
        receipt_triplet=replace(
            inp.receipt_triplet, raw_external_goal=goal_original,
        ),
        admission=replace(
            inp.admission,
            admitted_goal_sha256=frozenset({l13.sha(goal_original)}),
        ),
    )
    result = review_l17_first_action_goal(**args)
    assert result.status is L17HandoffStatus.UNDETERMINED_NO_GOAL_LABEL
    assert result.l14_independent_goal.l13_source_shaped_candidate.prior_l10 is None
    assert not result.l10_previous_epoch_candidate_available
    assert result.qualified_real_training_pairs == 0


@pytest.mark.parametrize("fault", [
    "external_wrong_type", "criterion_missing_sha", "criterion_wrong_target",
    "criterion_wrong_action", "criterion_wrong_session", "criterion_wrong_owner",
    "criterion_retroactive", "criterion_duplicate_key",
    "s16_mixed_pre", "s16_mixed_action", "s16_wrong_session",
    "external_goal_wrong_label", "goal_wrong_owner", "goal_wrong_probe",
    "current_replayed", "wrong_l16_action", "wrong_l16_session",
    "wrong_s7_hash", "plan_changed", "other_motor",
])
def test_adversarial_l16_l14_l13_cross_source_rejection(fault):
    args = source()
    inp = args["external"]
    if fault == "external_wrong_type":
        args["external"] = {}
    elif fault == "criterion_missing_sha":
        args["external"] = replace(inp, admitted_criterion_sha256=frozenset())
    elif fault == "current_replayed":
        args["external"] = replace(
            inp, current=replace(
                inp.current, session_id=args["session_id"],
            ),
        )
    elif fault in ("wrong_l16_action", "wrong_l16_session", "wrong_s7_hash",
                  "plan_changed", "other_motor"):
        if fault == "wrong_l16_action":
            args["action_id"] = "wrong-id"
        elif fault == "wrong_l16_session":
            args["session_id"] = "wrong-session"
        elif fault == "wrong_s7_hash":
            args["s7_receipt"] = {
                **args["s7_receipt"],
                "sent_sha256": "0" * 64,
            }
        elif fault == "plan_changed":
            args["plan"] = replace(args["plan"], target_z=999)
            args["plan_original"] = args["plan"].original_bytes()
        else:
            args["sent_original"] += (
                b'{"type":"effect","action_id":"foreign",'
                b'"effect":"clear_controls"}\n'
            )
            args["s7_receipt"] = l15.l14._index(
                args["received_original"], args["sent_original"],
            )
    elif fault.startswith("criterion_"):
        data = json.loads(inp.criterion_original)
        if fault == "criterion_wrong_target":
            data["target_x"] += 1
        elif fault == "criterion_wrong_action":
            data["action_id"] = "foreign"
        elif fault == "criterion_wrong_session":
            data["session_id"] = "foreign"
        elif fault == "criterion_wrong_owner":
            data["owner_ref"] = "foreign"
        elif fault == "criterion_retroactive":
            data["created_before_seq"] = 2
        elif fault == "criterion_duplicate_key":
            raw = inp.criterion_original.replace(
                b'"target_x":',
                b'"target_x":0,"target_x":',
            )
            assert raw != inp.criterion_original
        if fault != "criterion_duplicate_key":
            raw = l13.raw(data)
        args["external"] = replace(
            inp, criterion_original=raw,
            admitted_criterion_sha256=frozenset({l13.sha(raw)}),
        )
    elif fault.startswith("s16_"):
        a = json.loads(inp.receipt_triplet.raw_s16_action)
        if fault == "s16_mixed_pre":
            a["pre_probe_sha256"] = "f"*64
        elif fault == "s16_mixed_action":
            a["action_id"] = "foreign"
        else:
            a["session_id"] = "foreign"
        raw = l13.raw(a)
        args["external"] = replace(
            inp,
            receipt_triplet=replace(
                inp.receipt_triplet, raw_s16_action=raw,
            ),
            admission=replace(
                inp.admission,
                admitted_action_sha256=frozenset({l13.sha(raw)}),
            ),
        )
    else:
        data = json.loads(inp.receipt_triplet.raw_external_goal)
        if fault == "external_goal_wrong_label":
            data["goal_status"] = "NOT_REACHED"
        elif fault == "goal_wrong_owner":
            data["external_goal_owner_ref"] = "foreign"
        elif fault == "goal_wrong_probe":
            data["goal_observed_seq"] += 1
        raw = l13.raw(data)
        args["external"] = replace(
            inp,
            receipt_triplet=replace(
                inp.receipt_triplet, raw_external_goal=raw,
            ),
            admission=replace(
                inp.admission,
                admitted_goal_sha256=frozenset({l13.sha(raw)}),
            ),
        )
    with pytest.raises((ValueError, TypeError)):
        review_l17_first_action_goal(**args)
