"""Target semantics and gait choice: pure CPU, no physical Action authority."""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import MineflayerPosition as Pos
from experiments.cognitive_move_target_resolution import (
    propose_arrival_contract_for_selected_move,
    resolve_selected_move_target,
)
from relay_self.approach_controller import (
    ApproachPhase,
    BodyApproachCapabilities,
    GaitCalibration,
    GaitMode,
    recommend_approach,
)
from relay_self.common_io import ScopeRef
from relay_self.provenance import Provenance
from relay_self.target_contract import (
    ArrivalCondition,
    ReferenceFrame,
    TargetBodyObservation,
    TargetConditionStatus,
    TargetContract,
    TargetContractRefusal,
    TargetKind,
    evaluate_target,
)
from test_cognitive_move_target_resolution import prepare, select

SCOPE = ScopeRef("self-A", "world-A")
SOURCE = Provenance("configured-destination", "world-model-1")
NATIVE = Provenance("mineflayer", "probe-20")
CALIBRATION = Provenance("worldbody-calibration-dev", "source-rev-3")


def condition(*, radius=.75, still=8, drift=.05, speed=.03):
    return ArrivalCondition(
        min_horizontal_m=0, max_horizontal_m=radius,
        max_vertical_error_m=.25, still_ticks=still,
        max_still_drift_m=drift if still else None,
        max_speed_mps=speed,
    )


def place(*, radius=.75, still=8, drift=.05, speed=.03):
    return TargetContract(
        scope=SCOPE, goal_id="EXPLORE_WORLD",
        target_ref="destination:test@aabbcc",
        kind=TargetKind.PLACE, reference_frame=ReferenceFrame.WORLD,
        provenance=SOURCE, condition=condition(
            radius=radius, still=still, drift=drift, speed=speed,
        ), bound_seq=10, anchor=Pos(10, 64, 0),
    )


def step():
    return TargetContract(
        scope=SCOPE, goal_id="STEP_FORWARD",
        target_ref="step:short@ddee",
        kind=TargetKind.RELATIVE_STEP,
        reference_frame=ReferenceFrame.SELF_AT_BIND,
        provenance=SOURCE,
        condition=condition(radius=.08, speed=.02),
        bound_seq=10, bound_origin=Pos(0, 64, 0),
        anchor=Pos(1, 64, 0),
    )


def attack():
    return TargetContract(
        scope=SCOPE, goal_id="ATTACK_FROM_REACH",
        target_ref="entity:zombie@eeff",
        kind=TargetKind.ENTITY_RANGE,
        reference_frame=ReferenceFrame.ENTITY_LIVE,
        provenance=Provenance("mineflayer", "entity-observation-10"),
        condition=ArrivalCondition(
            1.5, 2.5, .5, require_line_of_sight=True,
            max_facing_error_rad=.3,
        ),
        bound_seq=10, entity_id="zombie-17", max_entity_age_seq=2,
    )


def body(x=0, *, speed=0, still=8, drift=0, seq=20, **extra):
    return TargetBodyObservation(
        scope=SCOPE, seq=seq, provenance=NATIVE,
        position=Pos(x, 64, 0), speed_mps=speed,
        still_ticks=still, max_still_drift_m=drift, **extra,
    )


def capabilities(*, uncertainty=.005, seq=20):
    return BodyApproachCapabilities(
        scope=SCOPE, observed_seq=seq, max_age_seq=2,
        position_uncertainty_m=uncertainty,
        gaits=(
            GaitCalibration(GaitMode.RUN, 4.0, 1.0, CALIBRATION),
            GaitCalibration(GaitMode.WALK, 1.6, .3, CALIBRATION),
            GaitCalibration(GaitMode.SNEAK, .35, .025, CALIBRATION),
        ),
        provenance=CALIBRATION,
    )


def test_place_target_separates_arrival_envelope_from_stop_stability():
    c = place()
    assert evaluate_target(c, body(x=9.5, still=8, drift=.02)).status is (
        TargetConditionStatus.CONDITION_OBSERVED
    )
    assert evaluate_target(c, body(x=9.5, still=8, drift=.06)).status is (
        TargetConditionStatus.SETTLING
    )
    assert evaluate_target(c, body(x=9.5, still=7, drift=.01)).status is (
        TargetConditionStatus.SETTLING
    )
    assert evaluate_target(c, body(x=9.5, still=None, drift=None)).status is (
        TargetConditionStatus.UNKNOWN
    )
    assert evaluate_target(c, body(x=9.5, speed=.04)).status is (
        TargetConditionStatus.SETTLING
    )
    assert evaluate_target(c, body(x=7)).status is (
        TargetConditionStatus.OUTSIDE
    )
    assert evaluate_target(c, body(x=9.5, speed=None)).status is (
        TargetConditionStatus.UNKNOWN
    )


def test_same_place_with_different_precision_changes_contract_reference_and_control():
    wide = place(radius=1.5, still=0, speed=None)
    precise = place(radius=.08)
    assert wide.contract_ref != precise.contract_ref
    sample = body(x=9, speed=1.2, still=0, drift=None)
    assert evaluate_target(wide, sample).status is TargetConditionStatus.CONDITION_OBSERVED
    assert evaluate_target(precise, sample).status is TargetConditionStatus.OUTSIDE
    # Observed condition is not a qualified physical Action nor Goal success.
    checked = evaluate_target(wide, sample)
    assert checked.condition_observed
    assert checked.goal_succeeded is False
    assert checked.physical_authorized is False


def test_one_step_means_body_relative_snapshot_not_current_world_origin():
    c = step()
    assert c.bound_origin == Pos(0, 64, 0)
    assert c.anchor == Pos(1, 64, 0)
    assert evaluate_target(c, body(x=.95, speed=.01)).condition_observed
    assert evaluate_target(c, body(x=.7)).status is TargetConditionStatus.OUTSIDE
    assert c.contract_ref != replace(c, anchor=Pos(1.1, 64, 0)).contract_ref


def test_live_enemy_requires_source_fresh_entity_id_los_and_facing():
    c = attack()
    valid = body(
        x=2, seq=20, entity_id="zombie-17",
        entity_position=Pos(4, 64, 0), entity_observed_seq=20,
        facing_error_rad=.1, line_of_sight=True,
    )
    assert evaluate_target(c, valid).status is TargetConditionStatus.CONDITION_OBSERVED
    assert evaluate_target(
        c, replace(valid, entity_observed_seq=17),
    ).status is TargetConditionStatus.UNKNOWN
    assert evaluate_target(
        c, replace(valid, entity_id="another-zombie"),
    ).status is TargetConditionStatus.UNKNOWN
    assert evaluate_target(
        c, replace(valid, entity_position=Pos(7, 64, 0)),
    ).status is TargetConditionStatus.OUTSIDE
    assert evaluate_target(
        c, replace(valid, line_of_sight=None),
    ).status is TargetConditionStatus.UNKNOWN
    assert evaluate_target(
        c, replace(valid, line_of_sight=False),
    ).status is TargetConditionStatus.BLOCKED
    assert evaluate_target(
        c, replace(valid, facing_error_rad=.8),
    ).status is TargetConditionStatus.ALIGN_REQUIRED
    assert evaluate_target(
        c, replace(valid, position=Pos(4, 64, 0)),
    ).status is TargetConditionStatus.TOO_CLOSE


def test_gait_selection_depends_on_target_envelope_and_stopping_margin():
    c = place()
    cap = capabilities()
    far = recommend_approach(
        c, body(x=5), cap, route_clear=True,
    )
    assert (far.phase, far.requested_gait) == (
        ApproachPhase.APPROACH, GaitMode.RUN,
    )
    near = recommend_approach(
        c, body(x=8.8), cap, current_gait=GaitMode.RUN, route_clear=True,
    )
    assert (near.phase, near.requested_gait) == (
        ApproachPhase.DECELERATE, GaitMode.WALK,
    )
    almost = recommend_approach(c, body(x=9.22), cap, route_clear=True)
    assert almost.phase is ApproachPhase.STOP_RECOMMENDED
    stable = recommend_approach(c, body(x=9.5), cap)
    assert stable.phase is ApproachPhase.TARGET_CONDITION_OBSERVED
    for output in (far, near, almost, stable):
        assert output.physical_issued is False
        assert output.action_authorized is False
        assert output.goal_succeeded is False


def test_precise_step_selects_sneak_when_calibration_allows_it():
    c = step()
    cap = capabilities()
    suggested = recommend_approach(
        c, body(x=.83), cap, current_gait=GaitMode.WALK,
        route_clear=True,
    )
    assert suggested.phase is ApproachPhase.DECELERATE
    assert suggested.requested_gait is GaitMode.SNEAK
    assert recommend_approach(
        c, body(x=.9, speed=.2, still=0), cap, route_clear=True,
    ).phase is ApproachPhase.VERIFY_STILLNESS


def test_attack_envelope_can_be_satisfied_while_body_is_moving():
    c = attack()
    obs = body(
        x=2, speed=2.0, still=None, drift=None, entity_id="zombie-17",
        entity_position=Pos(4, 64, 0), entity_observed_seq=20,
        facing_error_rad=.1, line_of_sight=True,
    )
    assert evaluate_target(c, obs).status is TargetConditionStatus.CONDITION_OBSERVED
    assert recommend_approach(
        c, obs, capabilities(), route_clear=True,
    ).phase is ApproachPhase.TARGET_CONDITION_OBSERVED


@pytest.mark.parametrize("change", [
    "wrong_world", "wrong_self", "stale_native", "untrusted_source",
    "stale_capability", "no_route", "unknown_route",
    "unknown_speed", "unobserved_gait",
])
def test_approach_never_uses_foreign_or_missing_evidence(change):
    c = place()
    obs = body(x=5)
    cap = capabilities()
    route = True
    gait = None
    if change == "wrong_world":
        obs = replace(obs, scope=ScopeRef("self-A", "world-B"))
    elif change == "wrong_self":
        obs = replace(obs, scope=ScopeRef("self-B", "world-A"))
    elif change == "stale_native":
        obs = replace(obs, seq=9)
    elif change == "untrusted_source":
        obs = replace(obs, provenance=SOURCE)
    elif change == "stale_capability":
        cap = capabilities(seq=10)
    elif change == "no_route":
        route = False
    elif change == "unknown_route":
        route = None
    elif change == "unknown_speed":
        obs = replace(obs, speed_mps=None)
    elif change == "unobserved_gait":
        gait = GaitMode.DASH
    out = recommend_approach(
        c, obs, cap, route_clear=route, current_gait=gait,
    )
    assert out.phase is ApproachPhase.HOLD_UNKNOWN
    assert out.requested_gait is None


def test_no_gait_can_stop_before_goal_envelope_means_stop_not_forward():
    c = step()
    cap = capabilities(uncertainty=.2)
    out = recommend_approach(c, body(x=.7), cap, route_clear=True)
    assert out.phase is ApproachPhase.STOP_RECOMMENDED
    assert out.requested_gait is None


@pytest.mark.parametrize("invalid", [
    {"kind": TargetKind.PLACE, "reference_frame": ReferenceFrame.ENTITY_LIVE},
    {"kind": TargetKind.RELATIVE_STEP, "reference_frame": ReferenceFrame.SELF_AT_BIND},
    {"kind": TargetKind.ENTITY_RANGE, "reference_frame": ReferenceFrame.ENTITY_LIVE},
    {"scope": ScopeRef("self-A", None)},
    {"bound_seq": -1},
    {"target_ref": "../../escape"},
])
def test_invalid_target_kind_or_source_cannot_bind(invalid):
    c = place()
    with pytest.raises(TargetContractRefusal):
        replace(c, **invalid)


@pytest.mark.parametrize("invalid", [
    {"max_horizontal_m": -1},
    {"min_horizontal_m": 2},
    {"still_ticks": 8, "max_still_drift_m": None},
    {"still_ticks": 0, "max_still_drift_m": .05},
    {"max_speed_mps": float("nan")},
    {"max_vertical_error_m": float("inf")},
    {"max_facing_error_rad": 4},
])
def test_unknown_or_incoherent_target_precision_never_silently_defaults(invalid):
    with pytest.raises(TargetContractRefusal):
        replace(condition(), **invalid)


def test_target_calibration_is_bounded_source_qualified_and_unique():
    good = capabilities()
    with pytest.raises(TargetContractRefusal):
        replace(good, gaits=good.gaits + good.gaits[:1])
    with pytest.raises(TargetContractRefusal):
        replace(good, max_age_seq=-1)
    with pytest.raises(TargetContractRefusal):
        GaitCalibration(GaitMode.WALK, 1.5, -0.2, CALIBRATION)
    with pytest.raises(TargetContractRefusal):
        GaitCalibration(GaitMode.WALK, float("nan"), .3, CALIBRATION)


def test_existing_l1_move_target_can_propose_precision_without_issuing_motor():
    native, scenario, percept, frame = prepare()
    selected = select(frame)
    bound = resolve_selected_move_target(
        selected, frame=frame, percept=percept,
        current_probe=native, scenario=scenario,
    )
    wide = propose_arrival_contract_for_selected_move(
        bound, condition(radius=1, still=0, speed=None),
    )
    tight = propose_arrival_contract_for_selected_move(
        bound, condition(radius=.1, still=8),
    )
    assert wide.scope == bound.scope
    assert wide.target_ref == selected.option.target_ref
    assert wide.anchor == bound.destination_position
    assert wide.bound_seq == bound.native_seq
    assert wide.contract_ref != tight.contract_ref
    assert bound.physical_issued is False
    assert bound.reached is False
    assert selected.option.skill_id == "MOVE"
    with pytest.raises(TargetContractRefusal):
        propose_arrival_contract_for_selected_move(
            replace(bound, reached=True), condition(radius=.1),
        )
    with pytest.raises(TargetContractRefusal):
        propose_arrival_contract_for_selected_move(
            replace(bound, destination_position=Pos(20, 64, 0)),
            condition(radius=.1),
        )
