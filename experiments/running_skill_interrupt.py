from __future__ import annotations

from dataclasses import dataclass

from relay_self.action import ActionLifecycle
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


@dataclass(slots=True)
class RunningSkillAction:
    """Experiment-local composition of one started Skill and supervised Action."""

    intent_commitment: IntentCommitment
    skill: SkillExecution
    supervisor: ActionSupervisor
    action_id: str


def build_running_skill_action() -> RunningSkillAction:
    owner = IntentCommitment()
    owner.commit(
        "intent-running-safety",
        objective="reach safety",
        at_ns=1,
        provenance=Provenance(
            source="fixture.intent",
            reference="intent:running-safety",
        ),
    )

    skill = SkillExecution.start(
        "skill-running-flee",
        skill_id="FLEE",
        intent_commitment=owner,
        at_ns=2,
        provenance=Provenance(
            source="fixture.skill",
            reference="skill:start",
        ),
    )

    action = ActionLifecycle.propose(
        "action-running-forward",
        skill_execution=skill,
        intent_commitment=owner,
        at_ns=3,
        provenance=Provenance(
            source="fixture.skill",
            reference="action:propose",
        ),
    )
    authorized = action.authorize(
        at_ns=4,
        provenance=Provenance(
            source="fixture.authorization",
            reference="action:authorize",
        ),
        authority="fixture-authority",
    )

    supervisor = ActionSupervisor()
    supervisor.issue(
        authorized,
        at_ns=5,
        deadline_ns=50,
        provenance=Provenance(
            source="fixture.boundary",
            reference="action:issue",
        ),
    )

    return RunningSkillAction(
        intent_commitment=owner,
        skill=skill,
        supervisor=supervisor,
        action_id=authorized.action_id,
    )


def request_viability_reconsideration(
    running: RunningSkillAction,
    *,
    at_ns: int = 6,
) -> None:
    """Admit an interrupt without silently mutating Skill or Action lifecycles."""

    current = running.intent_commitment.current_intent
    if current is None:
        raise ValueError("running interrupt fixture requires a Current Intent")
    running.intent_commitment.request_reconsideration(
        current.intent_id,
        reason="viability pressure materially challenges the current path",
        at_ns=at_ns,
        provenance=Provenance(
            source="fixture.viability",
            reference="viability:interrupt",
        ),
    )


def explicitly_cancel_skill(
    running: RunningSkillAction,
    *,
    at_ns: int = 7,
) -> SkillExecution:
    """Record an explicit Skill cancellation without claiming the Action stopped."""

    running.skill = running.skill.cancel(
        reason="upstream interrupt chose to stop this Skill path",
        at_ns=at_ns,
        provenance=Provenance(
            source="fixture.orchestration",
            reference="skill:cancel",
        ),
    )
    return running.skill
