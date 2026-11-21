from experiments.controlled_minecraft_vertical import ControlledSkill
from experiments.fixed_candidate_cognition_modes import (
    closed_system_one_case,
    closed_system_two_case,
    direct_no_model_case,
    reference_cases,
)
from relay_self.relay_engine import CognitionMode, DecisionStatus


def test_same_real_candidate_set_can_need_no_model() -> None:
    case = direct_no_model_case()

    assert case.candidates.candidates == (
        ControlledSkill.FLEE,
        ControlledSkill.EAT,
    )
    assert case.decision.skill is ControlledSkill.FLEE
    assert case.decision.destination is not None
    assert case.decision.destination.destination_id == "cave"
    assert case.decision.cognition_result is None
    assert case.provider_modes == ()
    assert case.provider_requests == ()


def test_same_real_candidate_set_can_resolve_in_closed_system_one() -> None:
    case = closed_system_one_case()

    assert case.candidates.candidates == (
        ControlledSkill.FLEE,
        ControlledSkill.EAT,
    )
    assert case.decision.skill is ControlledSkill.FLEE
    assert case.decision.destination is not None
    assert case.decision.destination.destination_id == "cave"
    assert case.provider_modes == (CognitionMode.BOUNDED,)
    assert len(case.provider_requests) == 1
    assert tuple(
        choice.choice_id for choice in case.provider_requests[0].choices
    ) == ("cave", "ridge")

    result = case.decision.cognition_result
    assert result is not None
    assert result.status is DecisionStatus.RESOLVED
    assert result.escalated is False
    assert tuple(attempt.mode for attempt in result.attempts) == (
        CognitionMode.BOUNDED,
    )


def test_same_real_candidate_set_can_escalate_closed_s1_to_closed_s2() -> None:
    case = closed_system_two_case()

    assert case.candidates.candidates == (
        ControlledSkill.FLEE,
        ControlledSkill.EAT,
    )
    assert case.decision.skill is ControlledSkill.FLEE
    assert case.decision.destination is not None
    assert case.decision.destination.destination_id == "cave"
    assert case.provider_modes == (
        CognitionMode.BOUNDED,
        CognitionMode.THINK,
    )
    assert len(case.provider_requests) == 2
    assert case.provider_requests[0] is case.provider_requests[1]
    assert tuple(
        choice.choice_id for choice in case.provider_requests[0].choices
    ) == ("cave", "ridge")

    result = case.decision.cognition_result
    assert result is not None
    assert result.status is DecisionStatus.RESOLVED
    assert result.escalated is True
    assert tuple(attempt.mode for attempt in result.attempts) == (
        CognitionMode.BOUNDED,
        CognitionMode.THINK,
    )


def test_fixed_candidate_fixture_falsifies_one_to_one_candidate_mode_mapping() -> None:
    direct, system_one, system_two = reference_cases()

    assert (
        direct.candidates.candidates
        == system_one.candidates.candidates
        == system_two.candidates.candidates
        == (ControlledSkill.FLEE, ControlledSkill.EAT)
    )
    assert (
        direct.decision.skill
        is system_one.decision.skill
        is system_two.decision.skill
        is ControlledSkill.FLEE
    )
    assert direct.provider_modes == ()
    assert system_one.provider_modes == (CognitionMode.BOUNDED,)
    assert system_two.provider_modes == (
        CognitionMode.BOUNDED,
        CognitionMode.THINK,
    )
    assert all(
        CognitionMode.OPEN not in case.provider_modes
        for case in (direct, system_one, system_two)
    )
