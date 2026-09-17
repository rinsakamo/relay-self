import pytest

import relay_self
from relay_self.action import Provenance as ActionProvenance
from relay_self.intent import IntentCommitment
from relay_self.provenance import InvalidProvenanceData, Provenance
from relay_self.skill import SkillExecution


def test_package_and_action_alias_share_neutral_provenance_type() -> None:
    assert relay_self.Provenance is Provenance
    assert ActionProvenance is Provenance


def test_provenance_validates_its_own_fields_with_shared_error() -> None:
    with pytest.raises(InvalidProvenanceData, match="provenance source"):
        Provenance(source="", reference="ref")

    with pytest.raises(InvalidProvenanceData, match="provenance reference"):
        Provenance(source="test", reference="")


def test_same_provenance_value_crosses_intent_skill_and_action_seams() -> None:
    provenance = Provenance(source="shared-test", reference="root")
    intent = IntentCommitment()
    intent.commit(
        "intent-1",
        objective="exercise shared provenance",
        at_ns=1,
        provenance=provenance,
    )
    skill = SkillExecution.start(
        "skill-1",
        skill_id="test-skill",
        intent_commitment=intent,
        at_ns=2,
        provenance=provenance,
    )

    assert intent.events[0].provenance is provenance
    assert skill.events[0].provenance is provenance
