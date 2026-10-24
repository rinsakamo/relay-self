"""Offline DEV contracts for #632: timing hypotheses != actual motor capability."""
from dataclasses import FrozenInstanceError, replace

import pytest

from experiments.self_body_timing_dev import (
    BodyDisplacementStatus,
    BodyTimingHypothesis,
    DodgeBudgetStatus,
    TimingEvidenceOrigin,
    TimingReviewRejected,
    predict_hypothetical_dodge,
    review_body_position_delta,
)
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    ActionOutcomeInterpretation,
)
from relay_self.provenance import Provenance
from relay_self.self_body import (
    BodyField,
    BodyObservation,
    SelfBodyView,
    compose_self_body_view,
)


def observation(seq=1, *, session="S", position=(0.0, 64.0, 0.0)):
    return BodyObservation(
        session_id=session, native_seq=seq, request_id=f"probe-{seq}",
        fields=(
            BodyField("position_x", position[0]),
            BodyField("position_y", position[1]),
            BodyField("position_z", position[2]),
            BodyField("health", 20),
        ),
        source_provenance=Provenance("mineflayer", f"{session}:{seq}"),
    )


def action_outcome(*, disposition=ActionOutcomeDisposition.OUTCOME):
    executed = disposition is ActionOutcomeDisposition.OUTCOME
    return ActionOutcomeInterpretation(
        action_id="move1", binding_id="bind1", action_ref="MOVE_BACKWARD",
        skill_execution_id="skill1", intent_id="intent1", session_id="S",
        source_status="executed" if executed else "undetermined",
        disposition=disposition,
        reason_code=(
            "observed_execution" if executed
            else "world_consequence_undetermined"
        ),
        world_provenance=Provenance("synthetic-s16", "world-consequence"),
        provenance=Provenance("synthetic-dev", "S16"),
    )


def body(seq=1, *, position=(0.0, 64.0, 0.0), self_id="self-a",
         session="S", present=True, result=None, readback=False):
    obs = observation(seq, session=session, position=position) if present else None
    if readback:
        obs = replace(
            obs, action_id="move1",
            consequence_provenance=Provenance(
                "synthetic-s16", "world-consequence",
            ),
        )
        result = action_outcome()
    return compose_self_body_view(
        session_id=session, epoch_id=f"epoch-{seq}",
        observation=obs, outcome=result, self_id=self_id,
    )


def hypothesis(
    body_view=None, *,
    impact=500.0, detect=50.0, cognition=70.0, issue=30.0,
    actuator=20.0, distance=0.2, speed=2.0,
):
    if body_view is None:
        body_view = body()
    ref = (
        body_view.observation.source_ref
        if body_view.observation is not None else "UNKNOWN"
    )
    return BodyTimingHypothesis(
        self_id=body_view.self_id, session_id=body_view.session_id,
        body_source_ref=ref, attack_horizon_ms=impact, detection_ms=detect,
        cognition_ms=cognition, authorization_issue_ms=issue,
        actuator_start_ms=actuator, required_clearance_m=distance,
        assumed_body_speed_mps=speed,
    )


def test_only_synthetic_feasible_dodge_never_certifies_physical_success():
    b = body()
    result = predict_hypothetical_dodge(b, hypothesis(b))
    assert result.status is DodgeBudgetStatus.WITHIN_HYPOTHETICAL_BUDGET
    assert result.travel_ms == pytest.approx(100)
    assert result.total_response_ms == pytest.approx(270)
    assert result.headroom_ms == pytest.approx(230)
    assert result.origin is TimingEvidenceOrigin.SYNTHETIC_DEV_HYPOTHESIS
    assert not result.allowed_to_act
    assert not result.physical_success_attested


def test_l2_slower_than_l0_same_body_and_world_deadline():
    b = body()
    fast = predict_hypothetical_dodge(b, hypothesis(b, cognition=5))
    slow = predict_hypothetical_dodge(b, hypothesis(b, cognition=350))
    assert fast.status is DodgeBudgetStatus.WITHIN_HYPOTHETICAL_BUDGET
    assert slow.status is DodgeBudgetStatus.LATE_UNDER_HYPOTHESIS
    assert slow.total_response_ms > fast.total_response_ms


def test_same_cognition_slower_body_changes_feasibility():
    b = body()
    normal = predict_hypothetical_dodge(b, hypothesis(b, speed=2.0))
    slow = predict_hypothetical_dodge(b, hypothesis(b, speed=0.4))
    assert normal.status is DodgeBudgetStatus.WITHIN_HYPOTHETICAL_BUDGET
    assert slow.status is DodgeBudgetStatus.LATE_UNDER_HYPOTHESIS


def test_equal_deadline_is_not_a_guaranteed_dodge():
    b = body()
    result = predict_hypothetical_dodge(b, hypothesis(b, impact=270))
    assert result.status is DodgeBudgetStatus.LATE_UNDER_HYPOTHESIS
    assert result.headroom_ms == pytest.approx(0)


@pytest.mark.parametrize("missing", (
    "impact", "detect", "cognition", "issue", "actuator",
    "distance", "speed",
))
def test_missing_timing_or_body_assumption_is_unknown(missing):
    b = body()
    settings = {missing: None}
    result = predict_hypothetical_dodge(b, hypothesis(b, **settings))
    assert result.status is DodgeBudgetStatus.UNKNOWN
    assert result.travel_ms is None
    assert result.headroom_ms is None


def test_missing_self_body_observation_cannot_claim_feasible():
    b = body(present=False)
    result = predict_hypothetical_dodge(b, hypothesis(b))
    assert result.status is DodgeBudgetStatus.UNKNOWN
    assert result.body_source_ref == "UNKNOWN"


def test_bad_source_ref_cannot_adopt_another_body():
    b = body()
    wrong = replace(hypothesis(b), body_source_ref="native-probe:S:999:forged")
    with pytest.raises(TimingReviewRejected, match="foreign or stale"):
        predict_hypothetical_dodge(b, wrong)


def test_foreign_self_and_session_rejected():
    b = body()
    h = hypothesis(b)
    with pytest.raises(TimingReviewRejected, match="foreign or unspecified"):
        predict_hypothetical_dodge(replace(b, self_id="other"), h)
    with pytest.raises(TimingReviewRejected, match="foreign session"):
        predict_hypothetical_dodge(b, replace(h, session_id="T"))


def test_uncorrelated_native_provenance_rejected():
    b = body()
    bad_obs = replace(
        b.observation,
        source_provenance=Provenance("synthetic", "S:1"),
    )
    with pytest.raises(TimingReviewRejected, match="uncorrelated"):
        predict_hypothetical_dodge(
            replace(b, observation=bad_obs), hypothesis(b),
        )


@pytest.mark.parametrize("bad", (-1, float("inf"), float("nan"), True))
def test_invalid_times_cannot_be_used(bad):
    with pytest.raises(TimingReviewRejected, match="invalid cognition_ms"):
        replace(hypothesis(), cognition_ms=bad)


def test_zero_or_negative_speed_rejected():
    with pytest.raises(TimingReviewRejected, match="assumed_body_speed"):
        replace(hypothesis(), assumed_body_speed_mps=0)
    with pytest.raises(TimingReviewRejected, match="assumed_body_speed"):
        replace(hypothesis(), assumed_body_speed_mps=-2)


def test_unknown_timing_origin_cannot_be_claimed_native():
    with pytest.raises(TimingReviewRejected, match="cannot claim native"):
        replace(hypothesis(), origin="NATIVE_ATTESTED")


@pytest.mark.parametrize("field", (
    "allowed_to_act", "physical_success_attested",
))
def test_timing_review_cannot_be_upgraded_to_motor_authority(field):
    b = body()
    result = predict_hypothetical_dodge(b, hypothesis(b))
    with pytest.raises(TimingReviewRejected, match="cannot grant Action"):
        replace(result, **{field: True})


def test_timing_result_immutable():
    result = predict_hypothetical_dodge(body(), hypothesis())
    with pytest.raises(FrozenInstanceError):
        result.total_response_ms = 0


def test_body_position_readback_distance_has_no_speed_or_latency():
    first = body(seq=1, position=(0.0, 64.0, 0.0))
    after = body(
        seq=4, position=(0.3, 64.0, 0.4), readback=True,
    )
    result = review_body_position_delta(first, after, self_id="self-a")
    assert result.status is BodyDisplacementStatus.SOURCE_CORRELATED_POSITION_DELTA
    assert result.horizontal_distance_m == pytest.approx(0.5)
    assert result.action_id == "move1"
    assert result.elapsed_s is None and result.speed_mps is None
    assert not result.authorized_to_move


def test_native_seq_difference_is_not_elapsed_seconds():
    first = body(seq=2)
    later = body(seq=900, position=(1.0, 64.0, 0.0), readback=True)
    result = review_body_position_delta(first, later, self_id="self-a")
    assert result.speed_mps is None and result.elapsed_s is None


def test_no_action_readback_cannot_prove_move_outcome():
    first = body(seq=1)
    later = body(seq=2, position=(1.0, 64.0, 0.0))
    result = review_body_position_delta(first, later, self_id="self-a")
    assert result.status is BodyDisplacementStatus.UNKNOWN
    assert result.horizontal_distance_m is None


def test_unknown_outcome_keeps_body_displacement_unknown():
    first = body(seq=1)
    later = body(
        seq=2, position=(1.0, 64.0, 0.0),
        result=action_outcome(
            disposition=ActionOutcomeDisposition.UNAVAILABLE
        ),
    )
    result = review_body_position_delta(first, later, self_id="self-a")
    assert result.status is BodyDisplacementStatus.UNKNOWN


def test_out_of_order_and_replayed_native_pair_rejected():
    first = body(seq=2)
    later = body(seq=2, readback=True)
    with pytest.raises(TimingReviewRejected, match="stale, duplicate"):
        review_body_position_delta(first, later, self_id="self-a")
    with pytest.raises(TimingReviewRejected, match="stale, duplicate"):
        review_body_position_delta(
            body(seq=5), body(seq=4, readback=True), self_id="self-a",
        )


def test_cross_self_or_session_pair_rejected():
    with pytest.raises(TimingReviewRejected, match="foreign or unspecified"):
        review_body_position_delta(
            body(seq=1), body(seq=2, self_id="other"), self_id="self-a",
        )
    with pytest.raises(TimingReviewRejected, match="cross-session"):
        review_body_position_delta(
            body(seq=1), body(seq=2, session="T"), self_id="self-a",
        )


def test_readback_distance_does_not_allow_forged_speed():
    first = body(seq=1)
    later = body(seq=2, readback=True)
    result = review_body_position_delta(first, later, self_id="self-a")
    with pytest.raises(TimingReviewRejected, match="do not measure"):
        replace(result, speed_mps=5.0)
    with pytest.raises(TimingReviewRejected, match="do not measure"):
        replace(result, authorized_to_move=True)


def test_incomplete_body_fields_do_not_prove_motion():
    first = body(seq=1)
    after = body(seq=2, readback=True)
    incomplete = replace(
        after,
        observation=replace(
            after.observation,
            fields=(BodyField("health", 20),),
        ),
    )
    result = review_body_position_delta(first, incomplete, self_id="self-a")
    assert result.status is BodyDisplacementStatus.UNKNOWN


def test_no_new_authority_methods_created():
    review = predict_hypothetical_dodge(body(), hypothesis())
    for key in (
        "issue_action", "commit_learning", "install_reflex",
        "motor_owner", "grant_action", "update_world",
    ):
        assert not hasattr(review, key)


@pytest.mark.parametrize("bad_status", ("PHYSICAL_SUCCESS", "QUALIFIED_L0"))
def test_hypothetical_review_cannot_be_relabeled_physical(bad_status):
    result = predict_hypothetical_dodge(body(), hypothesis())
    with pytest.raises(TimingReviewRejected, match="unsupported timing"):
        replace(result, status=bad_status)


def test_position_delta_status_cannot_claim_native_velocity():
    result = review_body_position_delta(
        body(seq=1), body(seq=2, readback=True), self_id="self-a",
    )
    with pytest.raises(TimingReviewRejected, match="unsupported displacement"):
        replace(result, status="VELOCITY_MEASURED")


@pytest.mark.parametrize("settings", (
    {"distance": 1e308, "speed": 1e-308},
    {"detect": 1e308, "cognition": 1e308},
))
def test_nonfinite_derived_budget_is_rejected(settings):
    with pytest.raises(TimingReviewRejected, match="nonfinite"):
        predict_hypothetical_dodge(body(), hypothesis(**settings))


def test_nonfinite_position_delta_is_rejected():
    with pytest.raises(TimingReviewRejected, match="nonfinite"):
        review_body_position_delta(
            body(seq=1, position=(-1e308, 64, 0)),
            body(seq=2, position=(1e308, 64, 0), readback=True),
            self_id="self-a",
        )


def test_overridden_read_only_view_cannot_supply_invented_position():
    class InventedPosition(SelfBodyView):
        def observed(self, key):
            return replace(super().observed(key), value=999)

    original = body()
    forged = InventedPosition(**{
        name: getattr(original, name)
        for name in original.__dataclass_fields__
    })
    with pytest.raises(TimingReviewRejected, match="typed SelfBodyView"):
        predict_hypothetical_dodge(forged, hypothesis(original))


@pytest.mark.parametrize("cognition,speed,expected", (
    (5, 0.4, DodgeBudgetStatus.LATE_UNDER_HYPOTHESIS),
    (350, 20, DodgeBudgetStatus.WITHIN_HYPOTHETICAL_BUDGET),
    (450, 20, DodgeBudgetStatus.LATE_UNDER_HYPOTHESIS),
))
def test_cognition_and_body_remain_independent(cognition, speed, expected):
    result = predict_hypothetical_dodge(
        body(), hypothesis(cognition=cognition, speed=speed),
    )
    assert result.status is expected
    assert result.travel_ms == pytest.approx(200 / speed)
    assert not result.allowed_to_act and not result.physical_success_attested


@pytest.mark.parametrize("disposition", (
    ActionOutcomeDisposition.UNKNOWN, ActionOutcomeDisposition.UNAVAILABLE,
))
def test_unknown_and_unavailable_readbacks_cannot_measure_movement(disposition):
    later = replace(
        body(seq=2, readback=True), outcome=action_outcome(disposition=disposition),
    )
    result = review_body_position_delta(body(), later, self_id="self-a")
    assert result.status is BodyDisplacementStatus.UNKNOWN
    assert result.horizontal_distance_m is None and result.speed_mps is None


@pytest.mark.parametrize("change", (
    {"source_status": "applied"}, {"session_id": "foreign"},
    {"action_id": "other"}, {"reason_code": "acknowledged"},
    {"world_provenance": Provenance("foreign", "result")},
))
def test_ack_and_foreign_action_lineage_cannot_attest_displacement(change):
    after = body(seq=2, readback=True)
    after = replace(after, outcome=replace(after.outcome, **change))
    result = review_body_position_delta(body(), after, self_id="self-a")
    assert result.status is BodyDisplacementStatus.UNKNOWN


def test_duplicate_request_with_advancing_seq_rejected():
    before, after = body(), body(seq=2, readback=True)
    after = replace(after, observation=replace(
        after.observation, request_id=before.observation.request_id,
    ))
    with pytest.raises(TimingReviewRejected, match="duplicate"):
        review_body_position_delta(before, after, self_id="self-a")


@pytest.mark.parametrize("clock_input", (
    {"elapsed_s": 1}, {"elapsed_s": -1},
    {"clock_domain": "node-monotonic"},
))
def test_no_clock_input_can_be_smuggled_into_source_seq_review(clock_input):
    # No measured-clock seam exists: missing clocks stay UNKNOWN; neither
    # inverted time nor an unvalidated foreign domain is admitted as a duration.
    with pytest.raises(TypeError):
        review_body_position_delta(body(), body(seq=2), self_id="self-a", **clock_input)


def test_synthetic_success_is_not_existing_learning_feedback():
    from relay_self.action_feedback import (
        InvalidActionFeedbackData,
        LearningFeedbackInterpretation,
        interpret_action_outcome_as_learning_feedback,
    )
    from relay_self.learning import LearningFeedback

    result = predict_hypothetical_dodge(body(), hypothesis())
    assert not isinstance(result, (LearningFeedbackInterpretation, LearningFeedback))
    assert not hasattr(result, "commit_learning")
    with pytest.raises(InvalidActionFeedbackData, match="action must be"):
        interpret_action_outcome_as_learning_feedback(
            result, None, None,
            provenance=Provenance("synthetic-dev", "prediction"),
        )
