"""Stage P offline-only S10->dual-consumer epoch handoff and negatives.

No Minecraft/Java/Node/model process. All Actions and S10 grants are synthetic;
this deliberately does not modify the original S49 owner or claim O2/O3/O4.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_action_feedback_qualification as s17
import test_postmain_s42_world_contrast as s42
import test_self_world_native_feedback as n_fixture
from adapters.mineflayer.normal_action import NormalWorldL0
from adapters.mineflayer.self_world_epoch_handoff import (
    StagePEpochRejected,
    prepare_stage_p_offline_dual_read,
)
from adapters.mineflayer.self_world_native_feedback import (
    StageNDeclaredPolicy,
    StageNNativeClosureObserver,
)
from relay_self.action_feedback import LearningFeedbackInterpretationStatus
from relay_self.epoch_continuation import (
    StaleRetainedSnapshot,
    read_retained_preference,
)
from relay_self.learning import (
    FeedbackDirection,
    InvalidLearningAuthority,
    LearningUpdateAuthority,
    MissingLearningAuthority,
    ReplayLearningFeedback,
    StaleLearningUpdate,
    propose_learning_update,
)
from relay_self.provenance import Provenance
from relay_self.world_conditioned_choice import (
    WorldChoiceRejected,
    select_world_conditioned_choice,
)


def _rehearsal():
    witness = n_fixture._synthetic_native_closed()
    stage_n = StageNNativeClosureObserver(StageNDeclaredPolicy())
    stage_n.observe_existing_probe(witness.original_probe)
    interpretation = stage_n.observe_closed(witness)
    assert interpretation.feedback is not None
    state = s17.learning_state()
    # The original S49 L0 object still owns this snapshot in the fixture.
    host = NormalWorldL0(
        witness.original_probe.session_id, "escape-threat", state,
    )
    next_probe = replace(
        witness.original_probe,
        seq=witness.consequence.after_observation.seq + 3,
        request_id=(
            f"s49-actual:{witness.original_probe.session_id}:event-47"
        ),
    )
    permission = LearningUpdateAuthority(
        "synthetic-stage-p-grant-NOT-LIVE", "risk_weight",
        Provenance("stage-p-synthetic", "test-only-predeclared"),
    )
    args = {
        "previous_owner": state,
        "current_l0_owner": host.retained,
        "current_s14_owner": state,
        "interpretation": interpretation,
        "proposal": propose_learning_update(
            state, interpretation.feedback, s17.learning_rule(),
        ),
        "authority": permission,
        "original_session_id": witness.original_probe.session_id,
        "after_action_native_seq": (
            witness.consequence.after_observation.seq
        ),
        "next_probe": next_probe,
        "provenance": Provenance("stage-p-synthetic", "offline-dual-read"),
    }
    return host, args


def test_stage_p_offline_hold_commit_produces_one_exact_l0_s14_read():
    host, args = _rehearsal()
    old = host.retained
    result = prepare_stage_p_offline_dual_read(**args)
    assert result.offline_only
    assert not result.real_world_commit_attested
    assert not result.installed_in_original_s49
    assert not result.actual_next_action_changed
    assert result.committed.previous_state is old
    new = result.committed.new_state
    assert new is result.l0_read.snapshot is result.s14_read.snapshot
    assert new is not old
    assert (old.revision, new.revision) == (0, 1)
    assert (old.value, new.value) == (3, 3)  # HOLD never improves policy
    assert result.following_native_seq > args["after_action_native_seq"]
    assert new.last_update is result.committed.record
    assert host.retained is old  # no covert owner takeover
    with pytest.raises(StaleRetainedSnapshot):
        read_retained_preference(
            new, host.retained, required_target_id="risk_weight",
            expected_revision=1,
            provenance=Provenance("stage-p-synthetic", "stale-original"),
        )
    with pytest.raises(ReplayLearningFeedback):
        propose_learning_update(
            new, args["interpretation"].feedback, s17.learning_rule(),
        )


def test_stage_p_frozen_s49_choice_rejects_even_valid_new_revision():
    """True next-epoch S49 cannot consume authorized rev2, even for HOLD."""
    _, args = _rehearsal()
    # Frozen S49 production source is rev1/value4, NOT this rev0 fixture.
    baseline, near, _, _, _ = s42._pair()
    new_proposal = propose_learning_update(
        baseline, args["interpretation"].feedback, s17.learning_rule(),
    )
    args.update(
        previous_owner=baseline,
        current_l0_owner=baseline,
        current_s14_owner=baseline,
        proposal=new_proposal,
    )
    result = prepare_stage_p_offline_dual_read(**args)
    assert result.committed.new_state.revision == 2
    assert result.committed.new_state.value == 4  # HOLD
    # Frozen World choice has explicit (rev1, value4) admission contract.
    with pytest.raises(WorldChoiceRejected, match="frozen governed rev1"):
        select_world_conditioned_choice(
            near, result.l0_read.snapshot,
            expected_session_id=near.observation.session_id,
            expected_entity_id=near.entity_id,
        )


@pytest.mark.parametrize("case", (
    "no_grant", "denied_grant", "wrong_target_grant",
    "reconstructed_l0", "reconstructed_s14",
    "missing_next_probe", "foreign_session", "stale_next_seq",
    "wrong_native_kind", "forged_source", "wrong_request",
    "sham_feedback", "foreign_s17", "directional_reward",
    "mismatched_feedback_instance", "stale_proposal_revision",
))
def test_stage_p_offline_denies_missing_source_or_permission(case):
    host, args = _rehearsal()
    old = host.retained
    typed = args["interpretation"]
    if case == "no_grant":
        args["authority"] = None
    elif case == "denied_grant":
        args["authority"] = replace(args["authority"], granted=False)
    elif case == "wrong_target_grant":
        args["authority"] = replace(args["authority"], target_id="other")
    elif case == "reconstructed_l0":
        args["current_l0_owner"] = replace(old)
    elif case == "reconstructed_s14":
        args["current_s14_owner"] = replace(old)
    elif case == "missing_next_probe":
        args["next_probe"] = None
    elif case == "foreign_session":
        args["next_probe"] = replace(args["next_probe"], session_id="foreign")
    elif case == "stale_next_seq":
        args["next_probe"] = replace(
            args["next_probe"], seq=args["after_action_native_seq"],
        )
    elif case == "wrong_native_kind":
        args["next_probe"] = replace(
            args["next_probe"], kind="entities", request_id=None,
        )
    elif case == "forged_source":
        # MineflayerObservation.provenance is computed from source identity;
        # an untyped forged dict must not impersonate that observation.
        args["next_probe"] = {
            "session_id": args["original_session_id"],
            "seq": args["next_probe"].seq,
            "kind": "probe",
        }
    elif case == "wrong_request":
        args["next_probe"] = replace(args["next_probe"], request_id="user-defined")
    elif case == "sham_feedback":
        args["interpretation"] = replace(
            typed, status=LearningFeedbackInterpretationStatus.NOT_APPLICABLE,
            feedback=None,
        )
    elif case == "foreign_s17":
        args["interpretation"] = replace(
            typed, provenance=Provenance("foreign-stage", "forged"),
        )
    elif case == "directional_reward":
        changed = replace(
            typed.feedback, direction=FeedbackDirection.INCREASE,
        )
        args["interpretation"] = replace(typed, feedback=changed)
    elif case == "mismatched_feedback_instance":
        args["proposal"] = replace(
            args["proposal"], feedback=replace(typed.feedback),
        )
    elif case == "stale_proposal_revision":
        args["proposal"] = replace(args["proposal"], expected_revision=99)
    with pytest.raises((
        StagePEpochRejected,
        MissingLearningAuthority,
        InvalidLearningAuthority,
        StaleLearningUpdate,
        ValueError,
    )):
        prepare_stage_p_offline_dual_read(**args)
    assert host.retained is old and old.revision == 0


def test_stage_p_no_grant_and_no_followup_must_not_mutate_initial_host():
    host, args = _rehearsal()
    args["authority"] = None
    args["next_probe"] = None
    with pytest.raises(StagePEpochRejected):
        prepare_stage_p_offline_dual_read(**args)
    assert host.retained.value == 3
    assert host.retained.revision == 0
    assert host.events == 0
    assert host.action_requests == 0
