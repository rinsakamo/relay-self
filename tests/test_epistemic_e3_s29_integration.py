"""Lane A E3 exact S29/S24 existing typed interface controls (offline doubles)."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
from itertools import permutations

import pytest

import test_postmain_correlated_probe as s29
from experiments import epistemic_e3_s29_integration as e3
from relay_self.action import ActionLifecycle, ActionState
from relay_self.correlated_probe import CorrelatedProbeGrant, InvalidCorrelatedProbe
from relay_self.explicit_probe import ExclusiveProbeCursor
from relay_self.provenance import Provenance

EXPECTED_STAGES = (
    "s24-att", "s24-blf", "s24-cnc", "s24-prd-wait", "s24-prd-move",
    "s24-plan", "s24-route", "s24-admit",
)
ARMS = ("NO_OBSERVE", "CHEAP_EXACT", "OBSERVE")
COSTS = (1, 4)
DISTANCES = ((0.2, "MOVE_AWAY", 7), (1.8, "WAIT", 4))


def subject(distance: float):
    data, failed, inputs, args, kwargs = s29._subject(distance=distance)
    return data, failed, inputs, args, kwargs


def run(distance: float, quarters: int, arm: str):
    data, failed, inputs, args, kwargs = subject(distance)
    original = kwargs["cursor"]
    original_revisions = data["commit"].new_state
    parent_action = args["action"]
    outcome_count = len(parent_action.events)
    result = asyncio.run(e3.continue_with_existing_owners(
        arm=arm, price_quarters=quarters,
        recovery_skill=inputs["recovery_skill"], intent=data["intent"],
        retained=data["commit"].new_state,
        at_ns=70, provenance=Provenance("e3.caller", "explicit-new-epoch"),
        **kwargs,
    ))
    assert data["supervisor"].open_actions == ()
    assert args["action"] is parent_action
    assert len(parent_action.events) == outcome_count
    assert parent_action.state is ActionState.OUTCOME
    assert data["commit"].new_state is original_revisions
    assert data["commit"].new_state.revision == 1
    assert failed.is_terminal and inputs["recovery_skill"].is_current_snapshot
    assert result.model_calls == result.issued_actions == 0
    if result.observation_count:
        assert original.consumed
        assert kwargs["adapter"].sent_ids == [kwargs["grant"].request_id]
        assert result.epoch is not None
        assert result.receipt is not None
        assert result.correlated_request_id == kwargs["grant"].request_id
        assert result.epoch.world_evidence.provenance in result.epoch.source_provenance
        assert result.stage_ids == EXPECTED_STAGES
        assert result.epoch.epoch.cognition_requested is False if hasattr(
            result.epoch.epoch, "cognition_requested"
        ) else True
    else:
        assert not original.consumed
        assert kwargs["adapter"].sent_ids == []
        assert result.epoch is None and result.receipt is None
        assert result.selected_score_with_cost is None
        assert result.stage_ids == ()
    return result


def test_manifest_hash_and_no_model_no_physical_authorization():
    assert e3.digest() == e3.MANIFEST_SHA256
    assert e3.MANIFEST["source_base"] == "5424669a09a69eb364da559e38b9999fee7b6680"
    assert e3.MANIFEST["parent_e2_head"] == "78be9d74950fd6b341bea40865b11f3bfdbfb320"
    assert e3.MANIFEST["model_calls"] == 0
    assert e3.MANIFEST["physical_minecraft_actions"] == 0
    assert e3.MANIFEST["no_new_action"] is True
    mutated = dict(e3.MANIFEST)
    mutated["model_calls"] = 1
    assert e3.digest(mutated) != e3.MANIFEST_SHA256


def test_frozen_information_value_and_decision_threshold():
    cheap = e3.plan_epistemic(1)
    dear = e3.plan_epistemic(4)
    assert cheap.no_observe_expected_score == dear.no_observe_expected_score == 6
    assert cheap.observe_expected_score == Fraction(23, 4)
    assert dear.observe_expected_score == Fraction(13, 2)
    assert cheap.net_information_value == Fraction(1, 4)
    assert dear.net_information_value == -Fraction(1, 2)
    assert cheap.first == "OBSERVE" and dear.first == "WAIT"
    for invalid in (0, True, False, -1, 2, "1", None):
        with pytest.raises(e3.EpistemicE3Rejected, match="price"):
            e3.plan_epistemic(invalid)


@pytest.mark.parametrize("distance,choice,score", DISTANCES)
@pytest.mark.parametrize("quarters", COSTS)
@pytest.mark.parametrize("arm", ARMS)
def test_all_twelve_offline_source_matched_arm_comparisons(
    distance, choice, score, quarters, arm,
):
    result = run(distance, quarters, arm)
    observe = arm == "OBSERVE" or (arm == "CHEAP_EXACT" and quarters == 1)
    assert result.observation_count == int(observe)
    assert result.next_epoch_count == int(observe)
    assert result.first == ("OBSERVE" if observe else "WAIT")
    assert result.selected == (choice if observe else "WAIT")
    if observe:
        assert result.selected_score_with_cost == Fraction(score) + Fraction(quarters, 4)
        assert result.source_evidence_id
    else:
        assert result.source_evidence_id is None
    assert result.net_information_value == (
        Fraction(1, 4) if quarters == 1 else -Fraction(1, 2)
    )


def test_12_independently_reset_reference_arms_are_order_invariant():
    for distance, _choice, _score in DISTANCES:
        for quarters in COSTS:
            comparison = {
                arm: (r.first, r.selected, r.observation_count)
                for arm in ARMS
                for r in (run(distance, quarters, arm),)
            }
            for order in permutations(ARMS):
                repeated = {
                    arm: (r.first, r.selected, r.observation_count)
                    for arm in order
                    for r in (run(distance, quarters, arm),)
                }
                assert repeated == comparison


def test_actual_S29_provenance_and_S24_eight_stage_source_admission():
    for distance, choice, score in DISTANCES:
        outcome = run(distance, 1, "CHEAP_EXACT")
        assert outcome.selected == choice
        assert outcome.epoch.selected_candidate == choice
        assert outcome.epoch.admission_status.value == "admitted"
        assert outcome.receipt.source_receipt.source.request_id == outcome.correlated_request_id
        assert outcome.epoch.world_evidence.evidence_id == outcome.source_evidence_id
        assert outcome.selected_score_with_cost == Fraction(score) + Fraction(1, 4)


@pytest.mark.parametrize("variant", (
    "wrong-id", "duplicate", "wrong-session", "wrong-cursor", "denied",
    "old-parent", "stale-clock", "missing-target",
))
def test_correlated_failure_never_enters_new_S24_epoch(variant):
    data, _failed, inputs, args, kwargs = subject(0.2)
    original = kwargs["adapter"].frames[0]
    if variant == "wrong-id":
        kwargs["adapter"].frames = deque((
            replace(original, request_id="foreign-probe"),
        ))
    elif variant == "wrong-session":
        kwargs["adapter"].frames = deque((
            replace(original, session_id="foreign-session"),
        ))
    elif variant == "wrong-cursor":
        kwargs["cursor"] = ExclusiveProbeCursor(
            kwargs["cursor"].session_id, 6,
        )
    elif variant == "denied":
        kwargs["grant"] = CorrelatedProbeGrant(
            replace(kwargs["grant"].authority, granted=False),
            kwargs["grant"].request_id,
        )
    elif variant == "old-parent":
        kwargs["action"] = data["closed1"]
    elif variant == "stale-clock":
        kwargs["observed_at_ns"] = 60
    elif variant == "missing-target":
        snap = original.snapshot
        kwargs["adapter"].frames = deque((replace(
            original, snapshot=replace(
                snap, nearby_entities=(),
                nearby_entities_coverage=replace(
                    snap.nearby_entities_coverage, candidate_count=0,
                ),
            ),
        ),))
    call_kwargs = dict(
        arm="CHEAP_EXACT", price_quarters=1, at_ns=70,
        recovery_skill=inputs["recovery_skill"], intent=data["intent"],
        retained=data["commit"].new_state,
        provenance=Provenance("e3.caller", "fail-closed"),
        **kwargs,
    )
    if variant == "duplicate":
        asyncio.run(e3.continue_with_existing_owners(**call_kwargs))
        with pytest.raises((InvalidCorrelatedProbe, e3.EpistemicE3Rejected)):
            asyncio.run(e3.continue_with_existing_owners(**call_kwargs))
        assert kwargs["adapter"].sent_ids == [kwargs["grant"].request_id]
        return
    with pytest.raises((InvalidCorrelatedProbe, ValueError, RuntimeError)):
        asyncio.run(e3.continue_with_existing_owners(**call_kwargs))
    assert data["supervisor"].open_actions == ()
    assert args["action"].state is ActionState.OUTCOME
    if variant in ("wrong-cursor", "denied", "old-parent", "stale-clock"):
        assert kwargs["adapter"].sent_ids == []


def test_no_observe_when_expensive_never_consumes_grant_or_generates_cognition():
    data, _failed, inputs, _args, kwargs = subject(0.2)
    # Even with a forged response queued, the E0 policy must NOT inspect it.
    kwargs["adapter"].frames = deque((replace(
        kwargs["adapter"].frames[0], request_id="alien",
    ),))
    result = asyncio.run(e3.continue_with_existing_owners(
        arm="CHEAP_EXACT", price_quarters=4,
        recovery_skill=inputs["recovery_skill"], intent=data["intent"],
        retained=data["commit"].new_state,
        at_ns=70, provenance=Provenance("e3.caller", "stay"),
        **kwargs,
    ))
    assert result.first == "WAIT" and result.next_epoch_count == 0
    assert result.receipt is None
    assert kwargs["adapter"].sent == 0
    assert kwargs["cursor"].consumed is False
    assert data["supervisor"].last_at_ns == 60


def test_no_authority_from_cognition_and_immutable_result():
    result = run(0.2, 1, "OBSERVE")
    assert result.epoch.admission_status.value == "admitted"
    assert result.issued_actions == 0
    with pytest.raises(FrozenInstanceError):
        result.selected = "WAIT"
    data, _failed, inputs, args, kwargs = subject(0.2)
    proof = Provenance("e3.test", "other")
    proposed = ActionLifecycle.propose(
        "conflict-action", skill_execution=inputs["recovery_skill"],
        intent_commitment=data["intent"], at_ns=61, provenance=proof,
    )
    authorized = proposed.authorize(
        at_ns=62, provenance=proof, authority="explicit-conflict-test",
    )
    data["supervisor"].issue(
        authorized, at_ns=63, deadline_ns=100, provenance=proof,
    )
    with pytest.raises(e3.EpistemicE3Rejected, match="in-flight"):
        asyncio.run(e3.continue_with_existing_owners(
            arm="CHEAP_EXACT", price_quarters=1, at_ns=70,
            recovery_skill=inputs["recovery_skill"], intent=data["intent"],
            retained=data["commit"].new_state,
            provenance=Provenance("e3.caller", "conflict"),
            **kwargs,
        ))
    assert kwargs["adapter"].sent_ids == []
    assert len(data["supervisor"].open_actions) == 1
