"""Bug-0: existing S51 eating cannot repurpose another Skill's issued Action.

All observations are synthetic existing test fixtures. No Minecraft, GPU, native
IO, Action grant or learning mutation. This is a lineage gate, NOT attestation
of the external authorization principal or a full S49-to-S51 product join.
"""
from dataclasses import replace

import pytest

import test_feature_s46_eat as s46
from adapters.mineflayer.eat_execution import (
    EatingExecutionRejected,
    validate_issued_eating_binding,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.eat_hunger import EatCursor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


def source(label: str) -> Provenance:
    return Provenance("bug0-independent-offline-fixture", label)


def owner(*, skill_name: str = "eat"):
    before = s46.case()
    choice = EatCursor(before.session_id).choose(before)
    intent = IntentCommitment()
    intent.commit("bug0-eat-intent", objective="eat after threat", at_ns=1,
                  provenance=source("intent"))
    skill = SkillExecution.start(
        "bug0-eat-execution", skill_id=skill_name, intent_commitment=intent,
        at_ns=2, provenance=source("skill"),
    )
    proposed = ActionLifecycle.propose(
        "bug0-eat-action", skill_execution=skill, intent_commitment=intent,
        at_ns=3, provenance=source("proposed"),
    )
    authorized = proposed.authorize(
        at_ns=4, authority="offline-grant-placeholder",
        provenance=source("authorized"),
    )
    supervisor = ActionSupervisor()
    issued = supervisor.issue(
        authorized, at_ns=5, deadline_ns=200, provenance=source("issued"),
    )
    return before, choice, intent, skill, supervisor, issued


def validate(before, choice, intent, skill, supervisor, issued):
    return validate_issued_eating_binding(
        supervisor, issued, skill, intent, choice, before,
    )


def test_real_owner_types_allow_only_existing_eat_skill_and_current_intent():
    before, choice, intent, skill, supervisor, issued = owner()
    assert validate(before, choice, intent, skill, supervisor, issued) is None
    assert supervisor.open_actions == (issued,)
    assert issued.state is ActionState.ISSUED


@pytest.mark.parametrize("skill_name", ["MOVE_BACKWARD", "FIGHT", "REST", "WAIT"])
def test_other_issued_skill_cannot_be_repurposed_as_eat(skill_name):
    fields = owner(skill_name=skill_name)
    with pytest.raises(EatingExecutionRejected, match="EAT Skill/Intent"):
        validate(*fields)
    assert fields[4].get(fields[5].action_id) is fields[5]


def test_mismatched_skill_execution_identity_cannot_use_issued_action():
    before, choice, intent, skill, supervisor, issued = owner()
    other_skill = SkillExecution.start(
        "different-skill", skill_id="eat", intent_commitment=intent,
        at_ns=6, provenance=source("other-skill"),
    )
    with pytest.raises(EatingExecutionRejected):
        validate(before, choice, intent, other_skill, supervisor, issued)


def test_reconsideration_pending_fences_eating_and_preserves_intent():
    before, choice, intent, skill, supervisor, issued = owner()
    intent.request_reconsideration(
        "bug0-eat-intent", reason="threat reappeared", at_ns=10,
        provenance=source("urgent"),
    )
    with pytest.raises(EatingExecutionRejected):
        validate(before, choice, intent, skill, supervisor, issued)
    assert intent.current_intent is not None
    assert supervisor.open_actions == (issued,)


def test_stale_skill_snapshot_cannot_authorize_eating():
    before, choice, intent, skill, supervisor, issued = owner()
    finished = skill.succeed(
        reason="already completed", at_ns=10, provenance=source("done"),
    )
    assert finished is not skill
    with pytest.raises(EatingExecutionRejected):
        validate(before, choice, intent, skill, supervisor, issued)
    with pytest.raises(EatingExecutionRejected):
        validate(before, choice, intent, finished, supervisor, issued)


def test_closed_or_foreign_action_cannot_be_reused_as_eat():
    before, choice, intent, skill, supervisor, issued = owner()
    foreign = ActionSupervisor()
    with pytest.raises(EatingExecutionRejected):
        validate(before, choice, intent, skill, foreign, issued)
    closed = supervisor.record_outcome(
        issued.action_id, at_ns=10, provenance=source("closed"),
    )
    assert closed.state is ActionState.OUTCOME
    with pytest.raises(EatingExecutionRejected):
        validate(before, choice, intent, skill, supervisor, issued)


def test_stale_or_foreign_food_probes_cannot_be_rebound_to_eat():
    before, choice, intent, skill, supervisor, issued = owner()
    with pytest.raises(EatingExecutionRejected):
        validate(replace(before, seq=before.seq + 1), choice, intent,
                 skill, supervisor, issued)
    with pytest.raises(EatingExecutionRejected):
        validate(
            replace(before, snapshot=replace(before.snapshot, inventory=())),
            choice, intent, skill, supervisor, issued,
        )


def test_synthetic_authority_string_is_not_a_physical_grant():
    """An accepted structural binding is not an independently legitimate issuer."""
    before, choice, intent, skill, supervisor, issued = owner()
    validate(before, choice, intent, skill, supervisor, issued)
    # Deliberately do NOT invoke IssuedEatingExecutor.execute or native IO.
    assert supervisor.open_actions == (issued,)
