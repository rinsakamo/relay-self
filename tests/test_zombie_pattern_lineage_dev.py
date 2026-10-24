"""Offline contract tests: fixed scaffold != a Self-learned zombie reflex."""
from dataclasses import replace

import pytest

from experiments.zombie_melee_perception_dev import (
    L0ContactStatus,
    L1MotionStatus,
    ZombieMeleeCueReview,
)
from experiments.zombie_pattern_lineage_dev import (
    PatternLane,
    PatternLineageRejected,
    PatternOrigin,
    compare_manual_and_synthetic,
    manual_zombie_pattern,
    select_zombie_pattern,
    synthetic_proposal_example,
)
from relay_self.habit import CueFeature, HabitSelectionStatus
from relay_self.provenance import Provenance


def _review(
    *,
    l0=L0ContactStatus.POSSIBLE_CONTACT,
    l1=L1MotionStatus.UNKNOWN,
    self_id="self-a",
):
    # This is a typed DEV fixture, not a native or physical attack receipt.
    return ZombieMeleeCueReview(
        self_id=self_id,
        session_id="session-a",
        target_entity_id=7,
        current_source_ref="present:session-a:2:probe-2",
        prior_source_ref="present:session-a:1:probe-1",
        arm_source_ref=None,
        l0_contact=l0,
        l1_motion=l1,
        observed_distance_m=1.0,
        contact_radius_m=1.8,
    )


def _proposal(*, lane=PatternLane.L0, refs=None):
    if refs is None:
        refs = ("synthetic-dev:example-a", "synthetic-dev:example-b")
    return synthetic_proposal_example(
        self_id="self-a", lane=lane, supporting_source_refs=refs,
    )


def _manual(*, lane=PatternLane.L0):
    return manual_zombie_pattern(self_id="self-a", lane=lane)


def test_scaffold_can_match_existing_habit_without_learning():
    p = _manual()
    selected = select_zombie_pattern(review=_review(), pattern=p)
    assert selected.status is HabitSelectionStatus.SELECTED
    assert selected.selected_candidate_ref == "dev_only_dodge_l0"
    assert selected.origin is PatternOrigin.DEVELOPER_SCAFFOLD
    assert not p.verified_self_learned
    assert not selected.learned_from_world
    assert not selected.authorized_for_action
    assert not selected.admitted_to_l0


def test_synthetic_proposal_can_match_without_becoming_a_self_skill():
    p = _proposal()
    selected = select_zombie_pattern(review=_review(), pattern=p)
    assert selected.status is HabitSelectionStatus.SELECTED
    assert selected.origin is PatternOrigin.SYNTHETIC_PROPOSAL_EXAMPLE
    assert selected.selected_candidate_ref == "dev_only_dodge_l0"
    assert not p.verified_self_learned
    assert not selected.learned_from_world


def test_same_choice_is_not_evidence_of_learned_cognition():
    a, b = compare_manual_and_synthetic(
        review=_review(), manual=_manual(), proposal=_proposal(),
    )
    assert a.selected_candidate_ref == b.selected_candidate_ref
    assert a.origin is PatternOrigin.DEVELOPER_SCAFFOLD
    assert b.origin is PatternOrigin.SYNTHETIC_PROPOSAL_EXAMPLE
    assert not a.learned_from_world and not b.learned_from_world


def test_l1_fixture_arm_motion_match_is_not_native_attack_windup():
    p = _manual(lane=PatternLane.L1)
    b = select_zombie_pattern(
        review=_review(l1=L1MotionStatus.ARM_SWING_OBSERVED_SYNTHETIC),
        pattern=p,
    )
    assert b.status is HabitSelectionStatus.SELECTED
    assert b.lane is PatternLane.L1
    assert b.selected_candidate_ref == "dev_only_dodge_l1"
    assert not b.admitted_to_l0


@pytest.mark.parametrize("l0", (
    L0ContactStatus.UNKNOWN, L0ContactStatus.NOT_INDICATED,
))
def test_l0_unknown_or_absent_cue_does_not_select_a_habit(l0):
    s = select_zombie_pattern(review=_review(l0=l0), pattern=_manual())
    assert s.status is HabitSelectionStatus.NO_MATCH
    assert s.selected_candidate_ref is None


def test_l1_unknown_does_not_silently_assume_arm_motion():
    s = select_zombie_pattern(
        review=_review(), pattern=_manual(lane=PatternLane.L1),
    )
    assert s.status is HabitSelectionStatus.NO_MATCH
    assert s.selected_candidate_ref is None


def test_l0_signal_does_not_become_l1_motion():
    s = select_zombie_pattern(
        review=_review(l0=L0ContactStatus.POSSIBLE_CONTACT),
        pattern=_proposal(lane=PatternLane.L1),
    )
    assert s.status is HabitSelectionStatus.NO_MATCH


def test_foreign_self_cannot_use_another_self_pattern():
    with pytest.raises(PatternLineageRejected, match="foreign Self"):
        select_zombie_pattern(
            review=_review(self_id="other"), pattern=_manual(),
        )


def test_spoofed_native_like_current_cue_ref_is_rejected():
    bad = replace(_review(), current_source_ref="faked:test:2")
    with pytest.raises(PatternLineageRejected, match="current cue source"):
        select_zombie_pattern(review=bad, pattern=_manual())


@pytest.mark.parametrize("origin", ("SELF_LEARNED", "QUALIFIED_L0", "L2_REAL"))
def test_unearned_origin_labels_cannot_be_inserted(origin):
    with pytest.raises(PatternLineageRejected, match="unsupported pattern"):
        replace(_manual(), origin=origin)


def test_l2_proxy_cannot_use_physical_or_native_source_as_its_evidence():
    with pytest.raises(PatternLineageRejected, match="synthetic-only"):
        _proposal(refs=("native-session:1", "synthetic-dev:2"))


def test_no_evidence_or_single_evidence_is_not_an_l2_candidate():
    for refs in ((), ("synthetic-dev:1",)):
        with pytest.raises(PatternLineageRejected, match="distinct synthetic"):
            _proposal(refs=refs)


def test_replayed_proposal_example_is_rejected():
    with pytest.raises(PatternLineageRejected, match="distinct synthetic"):
        _proposal(refs=("synthetic-dev:1", "synthetic-dev:1"))


def test_manual_scaffold_cannot_forge_training_evidence():
    with pytest.raises(PatternLineageRejected, match="cannot claim learning"):
        replace(_manual(), supporting_source_refs=("synthetic-dev:1",))


def test_manual_ref_cannot_be_relabeled_synthetic():
    with pytest.raises(PatternLineageRejected, match="forged origin"):
        replace(
            _manual(), origin=PatternOrigin.SYNTHETIC_PROPOSAL_EXAMPLE,
            supporting_source_refs=(
                "synthetic-dev:1", "synthetic-dev:2",
            ),
        )


def test_synthetic_ref_cannot_be_relabeled_scaffold():
    with pytest.raises(PatternLineageRejected, match="forged origin"):
        replace(
            _proposal(), origin=PatternOrigin.DEVELOPER_SCAFFOLD,
            supporting_source_refs=(),
        )


def test_l0_cue_does_not_admit_l1_rule():
    manual = _manual()
    invalid_rule = replace(
        manual.rule,
        cue_requirements=(
            CueFeature(
                "zombie_l1_cue",
                L1MotionStatus.ARM_SWING_OBSERVED_SYNTHETIC.value,
            ),
        ),
    )
    with pytest.raises(PatternLineageRejected, match="unexpected cue"):
        replace(manual, rule=invalid_rule)


def test_fake_rule_origin_reference_rejected():
    manual = _manual()
    with pytest.raises(PatternLineageRejected, match="forged origin"):
        replace(
            manual, rule=replace(
                manual.rule,
                provenance=Provenance("developer_scaffold_dev", "stolen"),
            ),
        )


@pytest.mark.parametrize("flag", (
    "learned_from_world", "authorized_for_action", "admitted_to_l0",
))
def test_offline_review_cannot_be_upgraded_by_dataclass_replace(flag):
    report = select_zombie_pattern(review=_review(), pattern=_proposal())
    with pytest.raises(PatternLineageRejected, match="cannot assert learning"):
        replace(report, **{flag: True})


def test_baseline_and_proposal_swap_rejected():
    with pytest.raises(PatternLineageRejected, match="independent"):
        compare_manual_and_synthetic(
            review=_review(), manual=_proposal(), proposal=_manual(),
        )


def test_different_lanes_not_compared_as_equivalent_choices():
    with pytest.raises(PatternLineageRejected, match="independent"):
        compare_manual_and_synthetic(
            review=_review(),
            manual=_manual(lane=PatternLane.L0),
            proposal=_proposal(lane=PatternLane.L1),
        )


def test_no_action_learning_or_runtime_entry_points_are_created():
    report = select_zombie_pattern(review=_review(), pattern=_manual())
    for key in (
        "issue_action", "commit_learning", "grant", "outcome",
        "install_reflex", "world_attested", "physics_executed",
    ):
        assert not hasattr(report, key)
