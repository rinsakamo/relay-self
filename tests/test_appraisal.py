import pytest

from relay_self.appraisal import (
    AppraisalAspect,
    AppraisalBias,
    AppraisalDisposition,
    AppraisalTargetKind,
    InvalidAppraisalData,
    project_entity_appraisal,
)
from relay_self.provenance import Provenance


def provenance(reference: str) -> Provenance:
    return Provenance(source="appraisal-test", reference=reference)


def disposition(
    *,
    target_kind: AppraisalTargetKind,
    target_key: str,
    aspect: AppraisalAspect,
    bias: AppraisalBias,
    reference: str,
) -> AppraisalDisposition:
    return AppraisalDisposition(
        target_kind=target_kind,
        target_key=target_key,
        aspect=aspect,
        bias=bias,
        source_provenance=provenance(f"source:{reference}"),
        integration_provenance=provenance(f"integration:{reference}"),
    )


def test_class_prior_projects_without_becoming_enemy_truth() -> None:
    prior = disposition(
        target_kind=AppraisalTargetKind.ENTITY_CLASS,
        target_key="zombie",
        aspect=AppraisalAspect.HARM_LIKELIHOOD,
        bias=AppraisalBias.UP,
        reference="zombie-prior",
    )

    current = project_entity_appraisal(
        entity_class="zombie",
        entity_instance="session-1:entity-7",
        observation_provenance=provenance("observation"),
        dispositions=(prior,),
    )

    assert current.bias_for(AppraisalAspect.HARM_LIKELIHOOD) is AppraisalBias.UP
    assert current.entity_class == "zombie"
    assert current.entity_instance == "session-1:entity-7"
    assert not hasattr(current, "enemy")
    assert not hasattr(current, "should_flee")


def test_individual_experience_can_weaken_class_prior_without_rewriting_class() -> None:
    class_prior = disposition(
        target_kind=AppraisalTargetKind.ENTITY_CLASS,
        target_key="zombie",
        aspect=AppraisalAspect.HARM_LIKELIHOOD,
        bias=AppraisalBias.UP,
        reference="class-prior",
    )
    harmless_individual = disposition(
        target_kind=AppraisalTargetKind.ENTITY_INSTANCE,
        target_key="session-1:entity-7",
        aspect=AppraisalAspect.HARM_LIKELIHOOD,
        bias=AppraisalBias.NEUTRAL,
        reference="harmless-history",
    )

    experienced = project_entity_appraisal(
        entity_class="zombie",
        entity_instance="session-1:entity-7",
        observation_provenance=provenance("experienced-observation"),
        dispositions=(class_prior, harmless_individual),
    )
    novel = project_entity_appraisal(
        entity_class="zombie",
        entity_instance="session-1:entity-8",
        observation_provenance=provenance("novel-observation"),
        dispositions=(class_prior, harmless_individual),
    )

    assert experienced.bias_for(
        AppraisalAspect.HARM_LIKELIHOOD
    ) is AppraisalBias.NEUTRAL
    assert novel.bias_for(
        AppraisalAspect.HARM_LIKELIHOOD
    ) is AppraisalBias.UP
    assert class_prior.bias is AppraisalBias.UP


def test_individual_harm_can_raise_initially_neutral_class_appraisal() -> None:
    harmful_individual = disposition(
        target_kind=AppraisalTargetKind.ENTITY_INSTANCE,
        target_key="session-1:entity-7",
        aspect=AppraisalAspect.HARM_LIKELIHOOD,
        bias=AppraisalBias.UP,
        reference="harm-history",
    )

    experienced = project_entity_appraisal(
        entity_class="cow",
        entity_instance="session-1:entity-7",
        observation_provenance=provenance("experienced-observation"),
        dispositions=(harmful_individual,),
    )
    novel = project_entity_appraisal(
        entity_class="cow",
        entity_instance="session-1:entity-8",
        observation_provenance=provenance("novel-observation"),
        dispositions=(harmful_individual,),
    )

    assert experienced.bias_for(
        AppraisalAspect.HARM_LIKELIHOOD
    ) is AppraisalBias.UP
    assert novel.bias_for(
        AppraisalAspect.HARM_LIKELIHOOD
    ) is AppraisalBias.NEUTRAL


def test_affiliation_prior_does_not_create_kinship_or_ally_truth() -> None:
    prior = disposition(
        target_kind=AppraisalTargetKind.ENTITY_CLASS,
        target_key="self-like",
        aspect=AppraisalAspect.AFFILIATION_LIKELIHOOD,
        bias=AppraisalBias.UP,
        reference="affiliation-prior",
    )

    current = project_entity_appraisal(
        entity_class="self-like",
        entity_instance=None,
        observation_provenance=provenance("observation"),
        dispositions=(prior,),
    )

    assert current.bias_for(
        AppraisalAspect.AFFILIATION_LIKELIHOOD
    ) is AppraisalBias.UP
    assert not hasattr(current, "ally")
    assert not hasattr(current, "kinship")


def test_duplicate_exact_scope_fails_closed() -> None:
    first = disposition(
        target_kind=AppraisalTargetKind.ENTITY_CLASS,
        target_key="zombie",
        aspect=AppraisalAspect.HARM_LIKELIHOOD,
        bias=AppraisalBias.UP,
        reference="first",
    )
    duplicate = disposition(
        target_kind=AppraisalTargetKind.ENTITY_CLASS,
        target_key="zombie",
        aspect=AppraisalAspect.HARM_LIKELIHOOD,
        bias=AppraisalBias.DOWN,
        reference="duplicate",
    )

    with pytest.raises(InvalidAppraisalData, match="duplicate"):
        project_entity_appraisal(
            entity_class="zombie",
            entity_instance=None,
            observation_provenance=provenance("observation"),
            dispositions=(first, duplicate),
        )
