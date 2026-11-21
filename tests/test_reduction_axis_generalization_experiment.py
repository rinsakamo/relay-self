from experiments.controlled_minecraft_vertical import ControlledSkill
from experiments.reduction_axis_generalization import reference_axis_generalization
from relay_self.appraisal import (
    AppraisalAspect,
    AppraisalBias,
    AppraisalTargetKind,
)


def _aspect_map(trace) -> dict[str, tuple[str, str]]:
    return {
        aspect: (target_kind, bias)
        for target_kind, aspect, bias in trace.appraisal_structure
    }


def test_harm_and_body_maintenance_axes_span_three_real_skills() -> None:
    analysis = reference_axis_generalization()

    assert analysis.harm_satiated.selected_skill == ControlledSkill.FLEE.value
    assert analysis.harm_satiated.parameter_topology == "DIRECT_DESTINATION"

    assert analysis.harm_hungry.selected_skill == ControlledSkill.FLEE.value
    assert analysis.harm_hungry.parameter_topology == "DIRECT_DESTINATION"

    assert analysis.experienced_hungry.selected_skill == ControlledSkill.EAT.value
    assert analysis.experienced_hungry.parameter_topology == "DIRECT_ITEM"

    assert analysis.experienced_satiated.selected_skill == ControlledSkill.WAIT.value
    assert analysis.experienced_satiated.parameter_topology == "NO_PARAMETER"

    assert analysis.multi_skill_matrix_survives


def test_same_hungry_world_history_changes_flee_to_eat() -> None:
    analysis = reference_axis_generalization()
    prior = analysis.harm_hungry
    experienced = analysis.experienced_hungry

    assert prior.world_signature == experienced.world_signature
    assert prior.raw_body_signature == experienced.raw_body_signature
    assert prior.observation_reference == experienced.observation_reference
    assert prior.scenario_hazard_names == experienced.scenario_hazard_names == ()

    assert prior.selected_skill == ControlledSkill.FLEE.value
    assert experienced.selected_skill == ControlledSkill.EAT.value

    prior_harm = _aspect_map(prior)[AppraisalAspect.HARM_LIKELIHOOD.value]
    experienced_harm = _aspect_map(experienced)[
        AppraisalAspect.HARM_LIKELIHOOD.value
    ]
    assert prior_harm == (
        AppraisalTargetKind.ENTITY_CLASS.value,
        AppraisalBias.UP.value,
    )
    assert experienced_harm == (
        AppraisalTargetKind.ENTITY_INSTANCE.value,
        AppraisalBias.NEUTRAL.value,
    )

    assert analysis.same_hungry_world_history_changes_skill


def test_affiliation_is_an_orthogonal_non_consumed_negative_control() -> None:
    analysis = reference_axis_generalization()

    assert len(analysis.affiliation_controls) == len(AppraisalBias)
    assert {
        _aspect_map(trace)[AppraisalAspect.AFFILIATION_LIKELIHOOD.value][1]
        for trace in analysis.affiliation_controls
    } == {bias.value for bias in AppraisalBias}

    for trace in analysis.affiliation_controls:
        aspects = _aspect_map(trace)
        assert aspects[AppraisalAspect.HARM_LIKELIHOOD.value] == (
            AppraisalTargetKind.ENTITY_CLASS.value,
            AppraisalBias.UP.value,
        )
        assert trace.selected_skill == ControlledSkill.FLEE.value
        assert trace.parameter_topology == "DIRECT_DESTINATION"

    assert analysis.affiliation_is_non_consumed_control


def test_mixed_appraisal_overrides_are_aspect_local() -> None:
    analysis = reference_axis_generalization()

    harm_override = _aspect_map(analysis.mixed_harm_override)
    assert harm_override[AppraisalAspect.HARM_LIKELIHOOD.value] == (
        AppraisalTargetKind.ENTITY_INSTANCE.value,
        AppraisalBias.NEUTRAL.value,
    )
    assert harm_override[AppraisalAspect.AFFILIATION_LIKELIHOOD.value] == (
        AppraisalTargetKind.ENTITY_CLASS.value,
        AppraisalBias.DOWN.value,
    )
    assert analysis.mixed_harm_override.selected_skill == ControlledSkill.EAT.value

    affiliation_override = _aspect_map(analysis.mixed_affiliation_override)
    assert affiliation_override[AppraisalAspect.HARM_LIKELIHOOD.value] == (
        AppraisalTargetKind.ENTITY_CLASS.value,
        AppraisalBias.UP.value,
    )
    assert affiliation_override[AppraisalAspect.AFFILIATION_LIKELIHOOD.value] == (
        AppraisalTargetKind.ENTITY_INSTANCE.value,
        AppraisalBias.UP.value,
    )
    assert (
        analysis.mixed_affiliation_override.selected_skill
        == ControlledSkill.FLEE.value
    )

    assert analysis.mixed_projection_is_aspect_local


def test_generalization_surface_requires_no_affiliation_to_talk_or_model_path() -> None:
    analysis = reference_axis_generalization()

    traces = (
        analysis.harm_satiated,
        analysis.harm_hungry,
        analysis.experienced_hungry,
        analysis.experienced_satiated,
        *analysis.affiliation_controls,
        analysis.mixed_harm_override,
        analysis.mixed_affiliation_override,
    )
    assert {trace.selected_skill for trace in traces} <= {
        ControlledSkill.FLEE.value,
        ControlledSkill.EAT.value,
        ControlledSkill.WAIT.value,
    }

    for trace in traces:
        rendered = repr(trace).lower()
        assert "talk" not in rendered
        assert "fear" not in rendered
        assert "emotion" not in rendered
