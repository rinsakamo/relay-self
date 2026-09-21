from experiments.controlled_minecraft_vertical import ControlledSkill
from experiments.reduction_recurrence import reference_analysis
from relay_self.appraisal import (
    AppraisalAspect,
    AppraisalBias,
    AppraisalTargetKind,
)


def test_same_exact_world_changes_reduction_after_instance_experience() -> None:
    analysis = reference_analysis()
    prior = analysis.class_prior_a
    experienced = analysis.experienced_a

    assert prior.world_signature == experienced.world_signature
    assert prior.raw_body_signature == experienced.raw_body_signature
    assert prior.observation_reference == experienced.observation_reference
    assert prior.scenario_hazard_names == experienced.scenario_hazard_names == ()

    assert prior.appraisal_structure == (
        (
            AppraisalTargetKind.ENTITY_CLASS.value,
            AppraisalAspect.HARM_LIKELIHOOD.value,
            AppraisalBias.UP.value,
        ),
    )
    assert experienced.appraisal_structure == (
        (
            AppraisalTargetKind.ENTITY_INSTANCE.value,
            AppraisalAspect.HARM_LIKELIHOOD.value,
            AppraisalBias.NEUTRAL.value,
        ),
    )
    assert prior.selected_skill == ControlledSkill.FLEE.value
    assert experienced.selected_skill == ControlledSkill.WAIT.value
    assert prior.parameter_topology == "DIRECT_DESTINATION"
    assert experienced.parameter_topology == "NO_PARAMETER"

    assert analysis.same_world_history_changes_reduction
    assert analysis.current_state_only_falsified
    assert analysis.raw_body_only_falsified


def test_class_prior_reduction_recurs_across_materially_different_worlds() -> None:
    analysis = reference_analysis()
    first = analysis.class_prior_a
    second = analysis.class_prior_b

    assert first.world_signature != second.world_signature
    assert first.observation_reference != second.observation_reference
    assert first.active_appraisal != second.active_appraisal
    assert first.appraisal_structure == second.appraisal_structure
    assert first.reduction_signature == second.reduction_signature
    assert first.selected_skill == second.selected_skill == ControlledSkill.FLEE.value
    assert first.scenario_hazard_names == second.scenario_hazard_names == ()

    assert analysis.different_world_same_reduction


def test_independent_instance_histories_recur_as_same_structural_reduction() -> None:
    analysis = reference_analysis()
    first = analysis.experienced_a
    second = analysis.experienced_b

    assert first.world_signature != second.world_signature
    assert first.active_appraisal != second.active_appraisal
    assert first.active_appraisal[0].target_key != second.active_appraisal[0].target_key
    assert (
        first.active_appraisal[0].source_reference
        != second.active_appraisal[0].source_reference
    )
    assert (
        first.active_appraisal[0].integration_reference
        != second.active_appraisal[0].integration_reference
    )

    assert first.appraisal_structure == second.appraisal_structure
    assert first.reduction_signature == second.reduction_signature
    assert first.selected_skill == second.selected_skill == ControlledSkill.WAIT.value

    assert analysis.history_shaped_reduction_recurs


def test_exact_recurrent_structure_has_downstream_real_skill_relevance() -> None:
    analysis = reference_analysis()

    assert analysis.recurring_structure_has_downstream_skill_relevance
    assert (
        analysis.class_prior_a.appraisal_structure
        == analysis.class_prior_b.appraisal_structure
    )
    assert (
        analysis.experienced_a.appraisal_structure
        == analysis.experienced_b.appraisal_structure
    )
    assert (
        analysis.class_prior_a.appraisal_structure
        != analysis.experienced_a.appraisal_structure
    )

    assert analysis.class_prior_a.selected_skill == ControlledSkill.FLEE.value
    assert analysis.class_prior_b.selected_skill == ControlledSkill.FLEE.value
    assert analysis.experienced_a.selected_skill == ControlledSkill.WAIT.value
    assert analysis.experienced_b.selected_skill == ControlledSkill.WAIT.value


def test_reference_surface_requires_no_model_or_emotion_label() -> None:
    analysis = reference_analysis()

    traces = (
        analysis.class_prior_a,
        analysis.class_prior_b,
        analysis.experienced_a,
        analysis.experienced_b,
    )
    for trace in traces:
        assert trace.parameter_topology in {
            "DIRECT_DESTINATION",
            "NO_PARAMETER",
        }
        rendered = repr(trace).lower()
        assert "fear" not in rendered
        assert "anger" not in rendered
        assert "emotion" not in rendered
