"""Source-contract negatives for zombie melee cue DEV; no physical World."""
from dataclasses import replace

import pytest

from adapters.mineflayer.present_projection import (
    MinecraftEntityPresent,
    MinecraftPresent,
)
from experiments.zombie_melee_perception_dev import (
    L0ContactStatus,
    L1MotionStatus,
    MeleeCueRejected,
    SyntheticArmSwing,
    ZombieMeleeFrame,
    review_zombie_melee,
)
from relay_self.provenance import Provenance


def _frame(
    seq: int, d: float | None,
    *,
    self_id: str = "self-a",
    session: str = "session-a",
    request: str | None = None,
    name: str = "zombie",
    entity_id: int = 7,
    truncated: bool = False,
) -> ZombieMeleeFrame:
    if request is None:
        request = f"probe-{seq}"
    entities = () if d is None else (
        MinecraftEntityPresent(
            entity_id=entity_id,
            name=name,
            distance_m=d,
            position=(d, 0.0, 0.0),
        ),
    )
    present = MinecraftPresent(
        session_id=session,
        seq=seq,
        request_id=request,
        body_position=(0.0, 0.0, 0.0),
        health=20.0,
        food=20.0,
        food_saturation=5.0,
        inventory=(),
        observed_entities=entities,
        coverage_scope="mineflayer_entity_registry",
        coverage_radius_m=16.0,
        coverage_cap=16,
        coverage_candidates=len(entities) + (1 if truncated else 0),
        coverage_truncated=truncated,
        provenance=Provenance("mineflayer", f"{session}:{seq}"),
    )
    return ZombieMeleeFrame(self_id, present)


def _swing(seq: int = 2, entity: int = 7):
    return SyntheticArmSwing(
        "self-a", "session-a", entity,
        seq, f"synthetic:entitySwingArm:session-a:{seq}:{entity}",
    )


def _review(current=None, prior=None, **kwargs):
    return review_zombie_melee(
        current=current or _frame(2, 1.25),
        target_entity_id=7,
        prior=prior,
        contact_radius_m=1.8,
        **kwargs,
    )


def test_l0_possible_contact_from_two_positive_closing_distances():
    result = _review(prior=_frame(1, 2.4))
    assert result.l0_contact is L0ContactStatus.POSSIBLE_CONTACT
    assert result.l1_motion is L1MotionStatus.UNKNOWN
    assert result.prior_source_ref == "present:session-a:1:probe-1"
    assert result.observed_distance_m == 1.25


def test_l1_synthetic_arm_swing_not_a_pre_hit_native_claim():
    result = _review(prior=_frame(1, 2.4), arm_swing=_swing())
    assert result.l0_contact is L0ContactStatus.POSSIBLE_CONTACT
    assert result.l1_motion is L1MotionStatus.ARM_SWING_OBSERVED_SYNTHETIC
    assert result.arm_source_ref.startswith("synthetic:entitySwingArm:")


def test_single_current_probe_cannot_prove_closing():
    result = _review(arm_swing=_swing())
    assert result.l0_contact is L0ContactStatus.UNKNOWN
    assert result.l1_motion is L1MotionStatus.ARM_SWING_OBSERVED_SYNTHETIC


@pytest.mark.parametrize("earlier,current", (
    (2.0, 2.3), (1.25, 1.25), (4.0, 2.1),
))
def test_no_approach_or_outside_assumed_contact_range(earlier, current):
    result = _review(_frame(2, current), _frame(1, earlier))
    assert result.l0_contact is L0ContactStatus.NOT_INDICATED
    assert result.l1_motion is L1MotionStatus.UNKNOWN


@pytest.mark.parametrize("missing", ("current", "prior"))
def test_entity_missing_in_bounded_source_never_means_safe(missing):
    current = _frame(2, None if missing == "current" else 1.0)
    previous = _frame(1, None if missing == "prior" else 2.0)
    result = _review(current, previous)
    assert result.l0_contact is L0ContactStatus.UNKNOWN
    assert result.l1_motion is L1MotionStatus.UNKNOWN


def test_truncated_snapshot_with_positive_entity_can_be_used():
    result = _review(_frame(2, 1.0, truncated=True), _frame(1, 2.0))
    assert result.l0_contact is L0ContactStatus.POSSIBLE_CONTACT


def test_foreign_type_never_promotes_to_zombie():
    result = _review(_frame(2, 1.0, name="skeleton"), _frame(1, 2.0))
    assert result.l0_contact is L0ContactStatus.UNKNOWN
    assert result.l1_motion is L1MotionStatus.UNKNOWN


def test_other_entity_id_never_counts_as_target():
    result = _review(_frame(2, 1.0, entity_id=99), _frame(1, 2.0))
    assert result.l0_contact is L0ContactStatus.UNKNOWN


def test_source_gap_is_not_physical_speed_or_safe():
    result = _review(_frame(100, 1.0), _frame(1, 2.0))
    assert result.l0_contact is L0ContactStatus.UNKNOWN


@pytest.mark.parametrize("prior,current,pattern", (
    (_frame(2, 2.0), _frame(2, 1.0), "stale or repeated"),
    (_frame(3, 2.0), _frame(2, 1.0), "stale or repeated"),
    (_frame(1, 2.0, session="other"), _frame(2, 1.0),
     "cross-Self/session"),
    (_frame(1, 2.0, self_id="other"), _frame(2, 1.0),
     "cross-Self/session"),
    (_frame(1, 2.0, request="same"),
     _frame(2, 1.0, request="same"), "repeated probe"),
))
def test_stale_repeated_and_foreign_probes_rejected(prior, current, pattern):
    with pytest.raises(MeleeCueRejected, match=pattern):
        _review(current, prior)


def test_non_native_source_provenance_rejected():
    frame = _frame(1, 1.0)
    with pytest.raises(MeleeCueRejected, match="uncorrelated"):
        replace(
            frame, present=replace(
                frame.present,
                provenance=Provenance("synthetic", "session-a:1"),
            ),
        )


def test_inconsistent_distances_rejected():
    frame = _frame(2, 1.0)
    broken = replace(
        frame, present=replace(
            frame.present,
            observed_entities=(
                replace(
                    frame.present.observed_entities[0], distance_m=10.0,
                ),
            ),
        ),
    )
    with pytest.raises(MeleeCueRejected, match="inconsistent"):
        _review(broken, _frame(1, 2.0))


@pytest.mark.parametrize("swing,pattern", (
    (replace(_swing(), self_id="other"), "foreign arm"),
    (replace(_swing(), session_id="other"), "foreign arm"),
    (_swing(entity=99), "foreign arm"),
    (_swing(seq=999), "future/stale"),
    (_swing(seq=1), "future/stale"),
))
def test_foreign_stale_future_and_wrong_target_swing_rejected(swing, pattern):
    with pytest.raises(MeleeCueRejected, match=pattern):
        _review(prior=_frame(1, 2.0), arm_swing=swing)


def test_synthetic_arm_event_cannot_be_forged_as_native():
    with pytest.raises(MeleeCueRejected, match="not established"):
        replace(_swing(), source_scope="mineflayer")


def test_native_probe_ref_replay_cannot_be_swing_evidence():
    with pytest.raises(MeleeCueRejected, match="replayed"):
        _review(arm_swing=replace(
            _swing(), event_ref="present:session-a:2:probe-2",
        ))


def test_unbounded_or_negative_radius_fail_closed():
    with pytest.raises(MeleeCueRejected, match="finite contact"):
        _review(contact_radius_m=float("nan"))
    with pytest.raises(MeleeCueRejected, match="finite contact"):
        _review(contact_radius_m=-1.0)


def test_no_action_authority_or_attack_outcome_in_review():
    report = _review(prior=_frame(1, 2.0), arm_swing=_swing())
    for forbidden in (
        "action", "authorization", "outcome", "hit_confirmed",
        "safe_direction", "attack_windup", "physical_action",
    ):
        assert not hasattr(report, forbidden)


def test_source_and_arm_cues_do_not_claim_animation_is_windup():
    result = _review(arm_swing=_swing())
    assert result.l1_motion.value == "ARM_SWING_OBSERVED_SYNTHETIC"
    assert result.l0_contact is L0ContactStatus.UNKNOWN
