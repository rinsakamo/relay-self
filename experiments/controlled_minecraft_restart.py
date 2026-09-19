from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from adapters.mineflayer.python_protocol import MineflayerObservation
from experiments.controlled_minecraft_vertical import (
    ControlledScenario,
    ControlledScenarioError,
    ControlledSkill,
    ScenarioDecision,
    SkillRunResult,
    decide_skill,
)
from observability.activity_summary import (
    reduce_activity,
    render_activity_markdown,
)
from relay_self.persistent_cognition import (
    Memory,
    PersistentCognition,
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoiceRequest, RelayEngineResult
from relay_self.skill import SkillState


class ControlledRestartError(RuntimeError):
    """Raised when the bounded restart/Memory transaction is not grounded."""


RelayEngineCallable = Callable[[BoundedChoiceRequest], RelayEngineResult]


@dataclass(frozen=True, slots=True)
class RestartDecisionResult:
    """Deterministic trace for one explicit Memory -> restart -> later decision."""

    integrated: PersistentCognition
    reloaded: PersistentCognition
    later_decision: ScenarioDecision
    retained_memory: Memory
    activity_markdown: str


def retain_successful_flee_memory(
    cognition: PersistentCognition,
    run_result: SkillRunResult,
    *,
    integration_provenance: Provenance,
) -> PersistentCognition:
    """Explicitly retain one grounded FLEE outcome as Memory.

    This function is the governed integration step for the controlled MVP.
    Merely completing a SkillRunResult does not invoke it automatically.
    """

    if not isinstance(cognition, PersistentCognition):
        raise ControlledRestartError(
            "cognition must be PersistentCognition"
        )
    if not isinstance(run_result, SkillRunResult):
        raise ControlledRestartError(
            "run_result must be SkillRunResult"
        )
    if not isinstance(integration_provenance, Provenance):
        raise ControlledRestartError(
            "integration_provenance must be Provenance"
        )
    if run_result.decision.skill is not ControlledSkill.FLEE:
        raise ControlledRestartError(
            "only the controlled FLEE outcome is supported by this integration"
        )
    if run_result.decision.destination is None:
        raise ControlledRestartError(
            "FLEE memory integration requires a resolved destination"
        )
    if run_result.skill_execution.state is not SkillState.SUCCEEDED:
        raise ControlledRestartError(
            "FLEE memory integration requires observed Skill success"
        )

    terminal_event = run_result.skill_execution.events[-1]
    if terminal_event.state is not SkillState.SUCCEEDED:
        raise ControlledRestartError(
            "FLEE terminal event must be SUCCEEDED"
        )

    destination = run_result.decision.destination
    content = json.dumps(
        {
            "kind": "controlled_flee_destination_outcome",
            "destination_id": destination.destination_id,
            "destination_position": {
                "x": destination.position.x,
                "y": destination.position.y,
                "z": destination.position.z,
            },
            "observed_outcome": "progress_toward_destination",
            "semantic_type": "Memory",
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    memory = Memory(
        memory_id=(
            "controlled-flee:"
            f"{destination.destination_id}:"
            f"{terminal_event.provenance.reference}"
        ),
        content=content,
        source_provenance=terminal_event.provenance,
        integration_provenance=integration_provenance,
    )
    return cognition.retain_memory(memory)


def save_restart_and_decide(
    path: str | Path,
    cognition: PersistentCognition,
    run_result: SkillRunResult,
    later_observation: MineflayerObservation,
    scenario: ControlledScenario,
    *,
    integration_provenance: Provenance,
    intent_id: str,
    relay_engine: RelayEngineCallable | None,
) -> RestartDecisionResult:
    """Persist one explicitly accepted Memory, reload, and decide from new evidence."""

    if not isinstance(later_observation, MineflayerObservation):
        raise ControlledRestartError(
            "later_observation must be MineflayerObservation"
        )
    if not isinstance(scenario, ControlledScenario):
        raise ControlledRestartError(
            "scenario must be ControlledScenario"
        )
    if not isinstance(intent_id, str) or not intent_id.strip():
        raise ControlledRestartError(
            "intent_id must be a non-empty string"
        )

    integrated = retain_successful_flee_memory(
        cognition,
        run_result,
        integration_provenance=integration_provenance,
    )
    retained_memory = integrated.memories[-1]

    save_persistent_cognition(path, integrated)
    reloaded = load_persistent_cognition(path)
    if reloaded.identity != cognition.identity:
        raise ControlledRestartError(
            "reloaded Persistent Cognition identity changed"
        )
    if retained_memory not in reloaded.memories:
        raise ControlledRestartError(
            "reloaded Persistent Cognition lost the retained Memory"
        )

    later_decision = decide_skill(
        later_observation,
        scenario,
        intent_id=intent_id,
        relay_engine=relay_engine,
        retained_memories=reloaded.memories,
    )

    digest = reduce_activity(
        mineflayer_messages=run_result.messages,
        skill_executions=(run_result.skill_execution,),
        action_lifecycles=run_result.actions,
        persistent_before=cognition,
        persistent_after=integrated,
    )
    activity_markdown = render_activity_markdown(digest)

    return RestartDecisionResult(
        integrated=integrated,
        reloaded=reloaded,
        later_decision=later_decision,
        retained_memory=retained_memory,
        activity_markdown=activity_markdown,
    )


def memory_destination_id(memory: Memory) -> str | None:
    """Read only this controlled-MVP Memory payload; do not infer World truth."""

    if not isinstance(memory, Memory):
        raise ControlledRestartError("memory must be Memory")
    try:
        payload = json.loads(memory.content)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("kind") != "controlled_flee_destination_outcome":
        return None
    destination_id = payload.get("destination_id")
    if not isinstance(destination_id, str) or not destination_id.strip():
        return None
    return destination_id


def choose_memory_matching_destination(
    request: BoundedChoiceRequest,
) -> str | None:
    """Deterministic test/helper read of a prior Memory in one bounded request.

    This exists only to demonstrate that reloaded Memory can affect a later
    decision while remaining distinguishable from current evidence. Product
    model quality still belongs to #140/#141 external evaluation.
    """

    allowed = {
        choice.choice_id
        for choice in request.choices
    }
    for datum in request.context:
        if not datum.key.startswith("memory:"):
            continue
        try:
            wrapper = json.loads(datum.value_json)
        except json.JSONDecodeError:
            continue
        if not isinstance(wrapper, dict):
            continue
        if wrapper.get("semantic_type") != "Memory":
            continue
        content = wrapper.get("content")
        if not isinstance(content, str):
            continue
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("kind") != "controlled_flee_destination_outcome":
            continue
        destination_id = payload.get("destination_id")
        if isinstance(destination_id, str) and destination_id in allowed:
            return destination_id
    return None


def require_restart_flee_decision(
    result: RestartDecisionResult,
) -> ScenarioDecision:
    """Fail closed unless the later decision is a resolved FLEE path."""

    decision = result.later_decision
    if decision.skill is not ControlledSkill.FLEE:
        raise ControlledRestartError(
            "later restart decision did not select FLEE"
        )
    if not decision.resolved or decision.destination is None:
        raise ControlledRestartError(
            "later restart FLEE decision remained unresolved"
        )
    return decision
