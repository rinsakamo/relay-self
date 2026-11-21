from experiments.present_skill_epoch import DecisionKind
from experiments.skill_cognition_allocation import (
    AllocationPath,
    broaden_without_open_observation,
    closed_system_one_observation,
    closed_system_two_observation,
    direct_binding_observation,
    run_reference_fixture,
)
from relay_self.relay_engine import CognitionMode, DecisionStatus


def test_direct_skill_binding_avoids_model_cognition() -> None:
    observation = direct_binding_observation()

    assert observation.path is AllocationPath.DIRECT_SKILL_BINDING
    assert observation.local_decision.kind is DecisionKind.START
    assert observation.final_decision.kind is DecisionKind.START
    assert observation.final_decision.destination == "cave"
    assert observation.provider_modes == ()
    assert observation.relay_result is None


def test_multiple_grounded_candidates_can_resolve_in_closed_system_one() -> None:
    observation = closed_system_one_observation()

    assert observation.path is AllocationPath.CLOSED_SYSTEM_ONE
    assert observation.local_decision.kind is DecisionKind.ESCALATE
    assert observation.provider_modes == (CognitionMode.BOUNDED,)
    assert observation.request_choice_ids == ("cave", "ridge")
    assert observation.relay_result is not None
    assert observation.relay_result.status is DecisionStatus.RESOLVED
    assert observation.relay_result.escalated is False
    assert observation.final_decision.kind is DecisionKind.START
    assert observation.final_decision.destination == "cave"


def test_unresolved_closed_system_one_preserves_topology_into_system_two() -> None:
    observation = closed_system_two_observation()

    assert observation.path is AllocationPath.CLOSED_SYSTEM_TWO
    assert observation.local_decision.kind is DecisionKind.ESCALATE
    assert observation.provider_modes == (
        CognitionMode.BOUNDED,
        CognitionMode.THINK,
    )
    assert observation.request_choice_ids == ("cave", "ridge")
    assert observation.relay_result is not None
    assert observation.relay_result.status is DecisionStatus.RESOLVED
    assert observation.relay_result.escalated is True
    assert tuple(
        attempt.mode for attempt in observation.relay_result.attempts
    ) == (CognitionMode.BOUNDED, CognitionMode.THINK)
    assert observation.final_decision.destination == "cave"


def test_missing_local_evidence_broadens_before_any_open_cognition() -> None:
    observation = broaden_without_open_observation()

    assert observation.path is AllocationPath.BROADEN_WITHOUT_OPEN
    assert observation.local_decision.kind is DecisionKind.ESCALATE
    assert observation.local_decision.missing_keys == (
        "route_open:cave",
        "route_open:ridge",
    )
    assert observation.final_decision.kind is DecisionKind.START
    assert observation.final_decision.destination == "cave"
    assert observation.provider_modes == ()
    assert CognitionMode.OPEN not in observation.provider_modes


def test_reference_fixture_preserves_distinct_allocation_paths() -> None:
    observations = run_reference_fixture()

    assert tuple(observation.path for observation in observations) == (
        AllocationPath.DIRECT_SKILL_BINDING,
        AllocationPath.CLOSED_SYSTEM_ONE,
        AllocationPath.CLOSED_SYSTEM_TWO,
        AllocationPath.BROADEN_WITHOUT_OPEN,
    )
    assert all(
        CognitionMode.OPEN not in observation.provider_modes
        for observation in observations
    )
