"""Stage S synthetic fixed-criterion separation feedback and ON/OFF/sham.

Original Stage R physical evidence is NOT replayed into Action or learning:
all witnesses/permissions below are SYNTHETIC, never scientific samples.
"""
from __future__ import annotations

import math
from dataclasses import replace

import pytest

import test_postmain_s42_world_contrast as s42
import test_self_world_native_feedback as n_fixture
from adapters.mineflayer.self_world_stage_s_feedback import (
    StageSFeedbackRejected,
    StageSPredeclaredSeparationRule,
    StageSSeparationClass,
    assess_stage_s_original_separation,
)
from relay_self.learning import (
    FeedbackDirection,
    LearningUpdateAuthority,
    LearningUpdateRule,
    MissingLearningAuthority,
    ReplayLearningFeedback,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    WorldChoiceRejected,
    select_stage_q_dev_committed_world_choice,
    select_world_conditioned_choice,
)


def _synthetic_targeted_witness(after_dx: float = 0.0, after_dz: float = 1.0):
    witness = n_fixture._synthetic_native_closed()
    _, near, _, _, _ = s42._pair()
    before = witness.consequence.before_observation
    after = witness.consequence.after_observation
    assert before is not None and after is not None
    origin = before.snapshot.position
    e = near.observation.snapshot.nearby_entities[0]
    e = replace(
        e,
        position=replace(
            e.position, x=origin.x + 2.0, y=origin.y, z=origin.z,
        ),
        distance=2.0,
    )
    cover = replace(before.snapshot.nearby_entities_coverage, candidate_count=1)
    near_snap = replace(
        before.snapshot, nearby_entities=(e,),
        nearby_entities_coverage=cover,
    )
    end = replace(
        origin, x=origin.x + after_dx, z=origin.z + after_dz,
    )
    end_distance = math.dist(
        (end.x, end.y, end.z),
        (e.position.x, e.position.y, e.position.z),
    )
    after_snap = replace(
        after.snapshot, position=end, nearby_entities=(
            replace(e, distance=end_distance),
        ), nearby_entities_coverage=cover,
    )
    move_distance = math.hypot(after_dx, after_dz)
    assert move_distance >= 0.05
    world = replace(
        witness.consequence,
        before_observation=replace(before, snapshot=near_snap),
        after_observation=replace(after, snapshot=after_snap),
        movement_distance=move_distance,
    )
    probe = replace(witness.original_probe, snapshot=near_snap)
    return replace(witness, consequence=world, original_probe=probe)


@pytest.mark.parametrize(("dx", "dz", "kind", "direction", "delta"), (
    (0.0, 1.0, StageSSeparationClass.SEPARATION_INCREASED, FeedbackDirection.INCREASE, math.sqrt(5.0) - 2.0),
    (0.5, 0.0, StageSSeparationClass.SEPARATION_DECREASED, FeedbackDirection.DECREASE, -0.5),
    (0.0, 0.2, StageSSeparationClass.NO_RESOLVED_CHANGE, FeedbackDirection.HOLD, math.sqrt(4.04) - 2.0),
))
def test_stage_s_qualified_original_s17_directional_feedback(dx, dz, kind, direction, delta):
    original = _synthetic_targeted_witness(dx, dz)
    result = assess_stage_s_original_separation(original, StageSPredeclaredSeparationRule())
    assert result.status is kind and result.direction is direction
    assert result.distance_before_m == 2.0
    assert result.distance_delta_m == pytest.approx(delta)
    assert result.typed_s17 is not None
    assert result.typed_s17.feedback is not None
    assert result.typed_s17.feedback.direction is direction
    assert result.typed_s17.action_id == original.terminal.action_id
    assert result.typed_s17.binding_id == original.interpretation.binding_id
    assert result.typed_s17.provenance.source == "stage-s-observed-world-only"
    assert result.typed_s17.criterion_provenance.source == (
        "stage-s-dev-preregistered-outcome-separation"
    )
    assert result.readonly and not result.s10_authority_issued
    assert not result.s10_committed and not result.action_issued
    assert not result.claimed_survival_gain


@pytest.mark.parametrize("case", (
    "foreign_after_session", "after_seq_replay", "forged_before_distance",
    "forged_after_distance", "truncated_registry", "wrong_action_binding",
    "wrong_original_request", "foreign_original_session",
    "world_action_swap", "target_duplicate", "bad_world_disposition",
))
def test_stage_s_rejects_sham_or_invalid_native_source(case):
    w = _synthetic_targeted_witness()
    before, after = w.consequence.before_observation, w.consequence.after_observation
    assert before is not None and after is not None
    if case == "foreign_after_session":
        w = replace(w, consequence=replace(
            w.consequence, after_observation=replace(after, session_id="foreign"),
        ))
    elif case == "after_seq_replay":
        w = replace(w, consequence=replace(
            w.consequence, after_observation=replace(after, seq=before.seq),
        ))
    elif case == "forged_before_distance":
        entity = before.snapshot.nearby_entities[0]
        w = replace(w, consequence=replace(
            w.consequence, before_observation=replace(
                before, snapshot=replace(before.snapshot, nearby_entities=(
                    replace(entity, distance=3.0),
                )),
            ),
        ))
    elif case == "forged_after_distance":
        entity = after.snapshot.nearby_entities[0]
        w = replace(w, consequence=replace(
            w.consequence, after_observation=replace(
                after, snapshot=replace(after.snapshot, nearby_entities=(
                    replace(entity, distance=3.0),
                )),
            ),
        ))
    elif case == "truncated_registry":
        # A genuinely truncated Mineflayer registry must have more
        # candidates than max_entities, and as many emitted entities as
        # the cap. Keep the protocol fixture valid before Stage S rejects it.
        cov = replace(
            after.snapshot.nearby_entities_coverage,
            truncated=True, max_entities=1, candidate_count=2,
        )
        w = replace(w, consequence=replace(
            w.consequence, after_observation=replace(
                after, snapshot=replace(
                    after.snapshot, nearby_entities_coverage=cov,
                ),
            ),
        ))
    elif case == "wrong_action_binding":
        w = replace(w, interpretation=replace(
            w.interpretation, binding_id="forged-binding",
        ))
    elif case == "wrong_original_request":
        w = replace(w, original_probe=replace(
            w.original_probe, request_id="different-event",
        ))
    elif case == "foreign_original_session":
        w = replace(w, original_probe=replace(
            w.original_probe, session_id="foreign-session",
        ))
    elif case == "world_action_swap":
        w = replace(w, consequence=replace(w.consequence, action_id="sham-action"))
    elif case == "target_duplicate":
        e = before.snapshot.nearby_entities[0]
        new_cov = replace(before.snapshot.nearby_entities_coverage, candidate_count=2)
        w = replace(w, consequence=replace(
            w.consequence, before_observation=replace(
                before, snapshot=replace(
                    before.snapshot, nearby_entities=(e, e),
                    nearby_entities_coverage=new_cov,
                ),
            ),
        ))
    else:
        w = replace(w, interpretation=replace(
            w.interpretation, reason_code="prediction_match",
        ))
    with pytest.raises((StageSFeedbackRejected, ValueError)):
        assess_stage_s_original_separation(w, StageSPredeclaredSeparationRule())


@pytest.mark.parametrize("case", ("target_missing_before", "target_missing_after", "ambiguous_origin"))
def test_stage_s_missing_or_ambiguous_target_abstains_not_hold(case):
    w = _synthetic_targeted_witness()
    if case == "target_missing_before":
        before = w.consequence.before_observation
        assert before is not None
        w = replace(w, consequence=replace(
            w.consequence, before_observation=replace(
                before, snapshot=replace(
                    before.snapshot, nearby_entities=(),
                    nearby_entities_coverage=replace(
                        before.snapshot.nearby_entities_coverage, candidate_count=0,
                    ),
                ),
            ),
        ))
    elif case == "target_missing_after":
        after = w.consequence.after_observation
        assert after is not None
        w = replace(w, consequence=replace(
            w.consequence, after_observation=replace(
                after, snapshot=replace(
                    after.snapshot, nearby_entities=(),
                    nearby_entities_coverage=replace(
                        after.snapshot.nearby_entities_coverage, candidate_count=0,
                    ),
                ),
            ),
        ))
    else:
        e = w.original_probe.snapshot.nearby_entities[0]
        w = replace(w, original_probe=replace(
            w.original_probe, snapshot=replace(
                w.original_probe.snapshot, nearby_entities=(e, replace(e, entity_id=e.entity_id+1)),
                nearby_entities_coverage=replace(
                    w.original_probe.snapshot.nearby_entities_coverage, candidate_count=2,
                ),
            ),
        ))
    result = assess_stage_s_original_separation(w, StageSPredeclaredSeparationRule())
    assert result.status is StageSSeparationClass.UNDETERMINED
    assert result.typed_s17 is None and result.direction is None
    assert not result.s10_committed


def test_stage_s_preregistered_rule_cannot_be_changed_after_outcome():
    with pytest.raises(StageSFeedbackRejected):
        StageSPredeclaredSeparationRule(delta_m=0.0)
    with pytest.raises(StageSFeedbackRejected):
        StageSPredeclaredSeparationRule(criterion_name="prediction-match")
    with pytest.raises(StageSFeedbackRejected):
        StageSPredeclaredSeparationRule(target_id="habit")


def test_stage_s_s10_on_off_sham_and_frozen_s49_admission_blocker():
    """A scalar update can be valid without demonstrably changing an Action."""
    state, near, _, _, _ = s42._pair()  # governed original rev1/value4
    rule = StageSPredeclaredSeparationRule()
    bounded = LearningUpdateRule("stage-s-test-only-bounded-delta", 1, 1)
    on = assess_stage_s_original_separation(_synthetic_targeted_witness(), rule)
    off = state  # OFF cannot call S10, original identity and revision preserved
    assert off is state and off.value == 4 and off.revision == 1
    assert on.typed_s17 is not None and on.typed_s17.feedback is not None
    proposal = propose_learning_update(state, on.typed_s17.feedback, bounded)
    assert proposal.proposed_value == 5
    with pytest.raises(MissingLearningAuthority):
        commit_learning_update(
            state, proposal, None,
            provenance=Provenance("stage-s-synthetic", "missing-grant"),
        )
    grant = LearningUpdateAuthority(
        "stage-s-synthetic-test-only-not-physical", "risk_weight",
        Provenance("stage-s-synthetic", "test-authority-only"),
    )
    result = commit_learning_update(
        state, proposal, grant,
        provenance=Provenance("stage-s-synthetic", "on"),
    )
    assert result.new_state.value == 5 and result.new_state.revision == 2
    assert state.value == 4 and state.revision == 1
    new_choice = select_stage_q_dev_committed_world_choice(
        near, result.new_state, commit=result, original_owner=state,
        expected_session_id=near.observation.session_id,
        expected_entity_id=near.entity_id,
    )
    old_choice = select_world_conditioned_choice(
        near, state, expected_session_id=near.observation.session_id,
        expected_entity_id=near.entity_id,
    )
    assert old_choice.selection is new_choice.selection is WorldChoiceKind.MOVE_AWAY
    assert old_choice.wait_score == 8 and new_choice.wait_score == 10
    with pytest.raises(ReplayLearningFeedback):
        propose_learning_update(result.new_state, on.typed_s17.feedback, bounded)
    sham = replace(
        on.typed_s17.feedback, feedback_id="stage-s-sham-not-an-original-outcome",
    )
    assert sham is not on.typed_s17.feedback
    # An S10 proposal alone cannot prove the sham is genuine; keep this
    # separate from the typed S17 / issuer checks in Stage R.
    assert propose_learning_update(state, sham, bounded).feedback is sham

    decrease = assess_stage_s_original_separation(
        _synthetic_targeted_witness(0.5, 0.0), rule,
    )
    assert decrease.typed_s17 is not None and decrease.typed_s17.feedback is not None
    dprop = propose_learning_update(state, decrease.typed_s17.feedback, bounded)
    dresult = commit_learning_update(
        state, dprop, grant,
        provenance=Provenance("stage-s-synthetic", "separate-decrease"),
    )
    assert dresult.new_state.value == 3
    with pytest.raises(WorldChoiceRejected, match="World geometry"):
        select_stage_q_dev_committed_world_choice(
            near, dresult.new_state, commit=dresult, original_owner=state,
            expected_session_id=near.observation.session_id,
            expected_entity_id=near.entity_id,
        )
