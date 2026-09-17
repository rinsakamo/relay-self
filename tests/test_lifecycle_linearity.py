import pytest

from relay_self.action import ActionLifecycle, InvalidTransition, Provenance
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.skill import InvalidSkillTransition, SkillExecution, SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(source="linearity-test", reference=reference)


def committed() -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        "intent-1",
        objective="exercise lifecycle linearity",
        at_ns=1,
        provenance=provenance("intent-commit"),
    )
    return owner


def started_skill(owner: IntentCommitment) -> SkillExecution:
    return SkillExecution.start(
        "skill-exec-1",
        skill_id="test-skill",
        intent_commitment=owner,
        at_ns=2,
        provenance=provenance("skill-start"),
    )


def proposed_action(owner: IntentCommitment, skill: SkillExecution) -> ActionLifecycle:
    return ActionLifecycle.propose(
        "action-1",
        skill_execution=skill,
        intent_commitment=owner,
        at_ns=3,
        provenance=provenance("action-propose"),
    )


def test_stale_started_skill_snapshot_cannot_propose_after_cancellation() -> None:
    owner = committed()
    started = started_skill(owner)
    cancelled = started.cancel(
        reason="execution no longer needed",
        at_ns=4,
        provenance=provenance("skill-cancel"),
    )

    assert started.state is SkillState.STARTED
    assert cancelled.state is SkillState.CANCELLED

    with pytest.raises(InvalidTransition, match="current Skill execution snapshot"):
        ActionLifecycle.propose(
            "action-after-cancel",
            skill_execution=started,
            intent_commitment=owner,
            at_ns=5,
            provenance=provenance("stale-skill-proposal"),
        )


def test_stale_skill_snapshot_cannot_create_second_terminal_branch() -> None:
    owner = committed()
    started = started_skill(owner)
    started.cancel(
        reason="execution no longer needed",
        at_ns=4,
        provenance=provenance("skill-cancel"),
    )

    with pytest.raises(InvalidSkillTransition, match="stale Skill execution snapshot"):
        started.fail(
            reason="alternate terminal branch",
            at_ns=5,
            provenance=provenance("stale-skill-fail"),
        )


def test_action_proposal_snapshot_cannot_fork_authorize_and_deny() -> None:
    owner = committed()
    skill = started_skill(owner)
    proposed = proposed_action(owner, skill)
    proposed.authorize(
        at_ns=4,
        provenance=provenance("authorize"),
        authority="test-policy",
    )

    with pytest.raises(InvalidTransition, match="stale Action lifecycle snapshot"):
        proposed.deny(
            at_ns=5,
            provenance=provenance("deny-stale-branch"),
            authority="test-policy",
        )


def test_action_supervisor_rejects_stale_authorized_snapshot() -> None:
    owner = committed()
    skill = started_skill(owner)
    authorized = proposed_action(owner, skill).authorize(
        at_ns=4,
        provenance=provenance("authorize"),
        authority="test-policy",
    )
    authorized.issue(
        at_ns=5,
        deadline_ns=10,
        provenance=provenance("direct-issue"),
    )

    with pytest.raises(InvalidTransition, match="stale Action lifecycle snapshot"):
        ActionSupervisor().issue(
            authorized,
            at_ns=6,
            deadline_ns=11,
            provenance=provenance("supervisor-stale-issue"),
        )
