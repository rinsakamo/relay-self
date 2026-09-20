from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol

from adapters.mineflayer.python_protocol import (
    MineflayerDecodedMessage,
    MineflayerEffectResult,
    MineflayerObservation,
    MineflayerPosition,
)
from adapters.mineflayer.runtime_admission import coordinate_mineflayer_message
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import Memory
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    DecisionStatus,
    RelayEngineResult,
)
from relay_self.skill import SkillExecution


class ControlledScenarioError(RuntimeError):
    """Raised when the bounded Minecraft MVP scenario cannot proceed safely."""


class ControlledSkill(str, Enum):
    WAIT = "WAIT"
    EAT = "EAT"
    FLEE = "FLEE"


@dataclass(frozen=True, slots=True)
class ControlledDestination:
    destination_id: str
    position: MineflayerPosition
    description: str
    provenance: Provenance

    def __post_init__(self) -> None:
        _require_text("destination_id", self.destination_id)
        if not isinstance(self.position, MineflayerPosition):
            raise ControlledScenarioError(
                "destination position must be MineflayerPosition"
            )
        _require_text("destination description", self.description)
        if not isinstance(self.provenance, Provenance):
            raise ControlledScenarioError(
                "destination provenance must be Provenance"
            )


@dataclass(frozen=True, slots=True)
class ControlledScenario:
    """Scenario specification for the first bounded Minecraft vertical slice."""

    hazard_entity_names: frozenset[str]
    food_threshold: float
    edible_item_names: tuple[str, ...]
    destinations: tuple[ControlledDestination, ...]
    flee_min_progress: float = 0.25
    evidence_timeout_s: float = 5.0
    max_evidence_messages: int = 32
    cognition_soft_wall_time_budget_s: float | None = None
    cognition_think_allowed: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.hazard_entity_names, frozenset):
            raise ControlledScenarioError(
                "hazard_entity_names must be a frozenset"
            )
        for name in self.hazard_entity_names:
            _require_text("hazard entity name", name)
        _require_non_negative_number("food_threshold", self.food_threshold)
        if not isinstance(self.edible_item_names, tuple):
            raise ControlledScenarioError(
                "edible_item_names must be a tuple"
            )
        for name in self.edible_item_names:
            _require_text("edible item name", name)
        if not isinstance(self.destinations, tuple):
            raise ControlledScenarioError(
                "destinations must be a tuple"
            )
        if not all(
            isinstance(destination, ControlledDestination)
            for destination in self.destinations
        ):
            raise ControlledScenarioError(
                "destinations must contain ControlledDestination values"
            )
        ids = tuple(
            destination.destination_id
            for destination in self.destinations
        )
        if len(set(ids)) != len(ids):
            raise ControlledScenarioError(
                "destination ids must be unique"
            )
        _require_positive_number(
            "flee_min_progress",
            self.flee_min_progress,
        )
        _require_positive_number(
            "evidence_timeout_s",
            self.evidence_timeout_s,
        )
        if (
            not isinstance(self.max_evidence_messages, int)
            or isinstance(self.max_evidence_messages, bool)
            or self.max_evidence_messages <= 0
        ):
            raise ControlledScenarioError(
                "max_evidence_messages must be a positive integer"
            )
        if self.cognition_soft_wall_time_budget_s is not None:
            _require_positive_number(
                "cognition_soft_wall_time_budget_s",
                self.cognition_soft_wall_time_budget_s,
            )
        if not isinstance(self.cognition_think_allowed, bool):
            raise ControlledScenarioError(
                "cognition_think_allowed must be bool"
            )


@dataclass(frozen=True, slots=True)
class ScenarioDecision:
    skill: ControlledSkill
    reason: str
    item_name: str | None = None
    destination: ControlledDestination | None = None
    cognition_result: RelayEngineResult | None = None

    @property
    def resolved(self) -> bool:
        if self.skill is ControlledSkill.FLEE:
            return self.destination is not None
        return True


@dataclass(frozen=True, slots=True)
class SkillRunResult:
    decision: ScenarioDecision
    skill_execution: SkillExecution
    actions: tuple[ActionLifecycle, ...]
    messages: tuple[MineflayerDecodedMessage, ...]


class MineflayerScenarioSession(Protocol):
    async def receive(self) -> MineflayerDecodedMessage: ...

    async def send_equip_item(
        self,
        action_id: str,
        *,
        item_name: str,
    ) -> None: ...

    async def send_consume_held(self, action_id: str) -> None: ...

    async def send_look(
        self,
        action_id: str,
        *,
        yaw: float,
        pitch: float,
    ) -> None: ...

    async def send_set_control(
        self,
        action_id: str,
        *,
        control: str,
        state: bool,
    ) -> None: ...

    async def send_clear_controls(self, action_id: str) -> None: ...


RelayEngineCallable = Callable[[BoundedChoiceRequest], RelayEngineResult]


def decide_skill(
    observation: MineflayerObservation,
    scenario: ControlledScenario,
    *,
    intent_id: str,
    relay_engine: RelayEngineCallable | None = None,
    retained_memories: tuple[Memory, ...] = (),
) -> ScenarioDecision:
    """Choose only among the three Skill classes needed by the controlled MVP.

    Hazard interpretation is explicitly scenario-local. The Mineflayer adapter
    supplies entity facts only; this function compares target-native names
    against the controlled-world specification.
    """

    if not isinstance(observation, MineflayerObservation):
        raise ControlledScenarioError(
            "skill decision requires MineflayerObservation"
        )
    if not isinstance(scenario, ControlledScenario):
        raise ControlledScenarioError(
            "scenario must be ControlledScenario"
        )
    _require_text("intent_id", intent_id)
    if not isinstance(retained_memories, tuple) or not all(
        isinstance(memory, Memory)
        for memory in retained_memories
    ):
        raise ControlledScenarioError(
            "retained_memories must be a tuple of Memory values"
        )

    snapshot = observation.snapshot
    hazards = tuple(
        entity
        for entity in snapshot.nearby_entities
        if entity.name in scenario.hazard_entity_names
    )
    if hazards:
        return _decide_flee(
            observation,
            scenario,
            intent_id=intent_id,
            relay_engine=relay_engine,
            retained_memories=retained_memories,
        )

    if snapshot.food <= scenario.food_threshold:
        inventory_names = {
            item.name
            for item in snapshot.inventory
            if item.count > 0
        }
        for item_name in scenario.edible_item_names:
            if item_name in inventory_names:
                return ScenarioDecision(
                    skill=ControlledSkill.EAT,
                    reason=(
                        "food is at or below the controlled scenario "
                        "maintenance threshold and a configured edible item "
                        "is present"
                    ),
                    item_name=item_name,
                )

    return ScenarioDecision(
        skill=ControlledSkill.WAIT,
        reason=(
            "no configured nearby hazard requires FLEE and no configured "
            "food-maintenance action is currently required"
        ),
    )


def _decide_flee(
    observation: MineflayerObservation,
    scenario: ControlledScenario,
    *,
    intent_id: str,
    relay_engine: RelayEngineCallable | None,
    retained_memories: tuple[Memory, ...],
) -> ScenarioDecision:
    if not scenario.destinations:
        return ScenarioDecision(
            skill=ControlledSkill.FLEE,
            reason="configured hazard is present but no destination is available",
        )
    if len(scenario.destinations) == 1:
        return ScenarioDecision(
            skill=ControlledSkill.FLEE,
            reason=(
                "configured hazard is present and exactly one controlled "
                "destination is available"
            ),
            destination=scenario.destinations[0],
        )
    if relay_engine is None:
        return ScenarioDecision(
            skill=ControlledSkill.FLEE,
            reason=(
                "configured hazard is present and multiple destinations "
                "require bounded cognition, but no RelayEngine was supplied"
            ),
        )

    request = build_flee_destination_request(
        observation,
        scenario,
        intent_id=intent_id,
        retained_memories=retained_memories,
    )
    result = relay_engine(request)
    if not isinstance(result, RelayEngineResult):
        raise ControlledScenarioError(
            "RelayEngine must return RelayEngineResult"
        )
    if (
        result.status is not DecisionStatus.RESOLVED
        or result.choice_id is None
    ):
        return ScenarioDecision(
            skill=ControlledSkill.FLEE,
            reason="bounded/THINK cognition did not resolve a FLEE destination",
            cognition_result=result,
        )

    destination = next(
        (
            candidate
            for candidate in scenario.destinations
            if candidate.destination_id == result.choice_id
        ),
        None,
    )
    if destination is None:
        raise ControlledScenarioError(
            "RelayEngine resolved a destination outside the scenario"
        )
    return ScenarioDecision(
        skill=ControlledSkill.FLEE,
        reason="RelayEngine resolved the controlled FLEE destination",
        destination=destination,
        cognition_result=result,
    )


def build_flee_destination_request(
    observation: MineflayerObservation,
    scenario: ControlledScenario,
    *,
    intent_id: str,
    retained_memories: tuple[Memory, ...] = (),
) -> BoundedChoiceRequest:
    """Build one scenario-local finite destination choice.

    Current Mineflayer evidence and retained Memory remain separate cognition
    data. A retained Memory is not promoted to fresh World evidence.
    """

    if len(scenario.destinations) < 2:
        raise ControlledScenarioError(
            "bounded FLEE request requires at least two destinations"
        )

    snapshot = observation.snapshot
    evidence = observation.provenance
    context: list[CognitionDatum] = [
        CognitionDatum.from_value(
            "health",
            snapshot.health,
            evidence,
        ),
        CognitionDatum.from_value(
            "food",
            snapshot.food,
            evidence,
        ),
        CognitionDatum.from_value(
            "position",
            {
                "x": snapshot.position.x,
                "y": snapshot.position.y,
                "z": snapshot.position.z,
            },
            evidence,
        ),
        CognitionDatum.from_value(
            "nearby_entities",
            [
                {
                    "name": entity.name,
                    "type": entity.entity_type,
                    "distance": entity.distance,
                    "position": {
                        "x": entity.position.x,
                        "y": entity.position.y,
                        "z": entity.position.z,
                    },
                }
                for entity in snapshot.nearby_entities
            ],
            evidence,
        ),
    ]

    for destination in scenario.destinations:
        context.append(
            CognitionDatum.from_value(
                f"destination:{destination.destination_id}",
                {
                    "position": {
                        "x": destination.position.x,
                        "y": destination.position.y,
                        "z": destination.position.z,
                    },
                    "description": destination.description,
                },
                destination.provenance,
            )
        )

    for memory in retained_memories:
        context.append(
            CognitionDatum.from_value(
                f"memory:{memory.memory_id}",
                {
                    "semantic_type": "Memory",
                    "content": memory.content,
                    "source_provenance": {
                        "source": memory.source_provenance.source,
                        "reference": memory.source_provenance.reference,
                    },
                },
                memory.integration_provenance,
            )
        )

    return BoundedChoiceRequest(
        request_id=(
            f"controlled-flee:{observation.session_id}:{observation.seq}"
        ),
        instruction=(
            "Choose one controlled destination for the active FLEE Skill. "
            "Treat current Mineflayer facts as current evidence and retained "
            "Memory only as prior experience, not fresh World truth."
        ),
        intent_id=intent_id,
        focus=ControlledSkill.FLEE.value,
        choices=tuple(
            BoundedChoice(
                destination.destination_id,
                destination.description,
            )
            for destination in scenario.destinations
        ),
        context=tuple(context),
        soft_wall_time_budget_s=scenario.cognition_soft_wall_time_budget_s,
        think_allowed=scenario.cognition_think_allowed,
    )


def yaw_to_destination(
    current: MineflayerPosition,
    destination: MineflayerPosition,
) -> float:
    """Return Mineflayer yaw radians from current horizontal position.

    Mineflayer documents yaw 0 as due east and counter-clockwise positive.
    Minecraft +Z is south, therefore atan2(-dz, dx) maps the horizontal
    displacement to that convention.
    """

    dx = destination.x - current.x
    dz = destination.z - current.z
    if dx == 0 and dz == 0:
        raise ControlledScenarioError(
            "cannot compute heading to the current horizontal position"
        )
    return math.atan2(-dz, dx)


async def execute_decision(
    session: MineflayerScenarioSession,
    observation: MineflayerObservation,
    scenario: ControlledScenario,
    decision: ScenarioDecision,
    *,
    intent_commitment: IntentCommitment,
    supervisor: ActionSupervisor,
    authorization: str = "controlled-minecraft-mvp",
) -> SkillRunResult | None:
    """Execute only EAT/FLEE; WAIT is healthy inactivity with no Skill start."""

    if decision.skill is ControlledSkill.WAIT:
        return None
    current = intent_commitment.current_intent
    if current is None:
        raise ControlledScenarioError(
            "controlled Skill execution requires Current Intent"
        )
    if not decision.resolved:
        raise ControlledScenarioError(
            "cannot start an unresolved controlled Skill decision"
        )

    if decision.skill is ControlledSkill.EAT:
        return await _execute_eat(
            session,
            observation,
            scenario,
            decision,
            intent_commitment=intent_commitment,
            supervisor=supervisor,
            authorization=authorization,
        )
    if decision.skill is ControlledSkill.FLEE:
        return await _execute_flee(
            session,
            observation,
            scenario,
            decision,
            intent_commitment=intent_commitment,
            supervisor=supervisor,
            authorization=authorization,
        )
    raise ControlledScenarioError(
        f"unsupported controlled Skill: {decision.skill}"
    )


async def _execute_eat(
    session: MineflayerScenarioSession,
    observation: MineflayerObservation,
    scenario: ControlledScenario,
    decision: ScenarioDecision,
    *,
    intent_commitment: IntentCommitment,
    supervisor: ActionSupervisor,
    authorization: str,
) -> SkillRunResult:
    if decision.item_name is None:
        raise ControlledScenarioError("EAT decision requires item_name")

    messages: list[MineflayerDecodedMessage] = []
    action_ids: list[str] = []
    skill = _start_skill(
        ControlledSkill.EAT,
        observation,
        intent_commitment,
    )

    equip_id = f"{skill.execution_id}:equip"
    _issue_action(
        equip_id,
        skill,
        intent_commitment,
        supervisor,
        authorization=authorization,
        timeout_s=scenario.evidence_timeout_s,
    )
    action_ids.append(equip_id)
    await session.send_equip_item(
        equip_id,
        item_name=decision.item_name,
    )
    equip_result = await _await_effect_result(
        session,
        equip_id,
        supervisor,
        messages,
        scenario=scenario,
    )
    if equip_result.result != "applied":
        skill = skill.fail(
            reason=f"equip_item rejected: {equip_result.error}",
            at_ns=_next_owner_time(skill.events[-1].at_ns),
            provenance=equip_result.provenance,
        )
        return _run_result(
            decision,
            skill,
            supervisor,
            action_ids,
            messages,
        )

    consume_id = f"{skill.execution_id}:consume"
    _issue_action(
        consume_id,
        skill,
        intent_commitment,
        supervisor,
        authorization=authorization,
        timeout_s=scenario.evidence_timeout_s,
    )
    action_ids.append(consume_id)
    await session.send_consume_held(consume_id)
    consume_result = await _await_effect_result(
        session,
        consume_id,
        supervisor,
        messages,
        scenario=scenario,
    )
    if consume_result.result != "applied":
        skill = skill.fail(
            reason=f"consume_held rejected: {consume_result.error}",
            at_ns=_next_owner_time(skill.events[-1].at_ns),
            provenance=consume_result.provenance,
        )
        return _run_result(
            decision,
            skill,
            supervisor,
            action_ids,
            messages,
        )

    initial_food = observation.snapshot.food
    food_evidence: MineflayerObservation | None = None
    for _ in range(scenario.max_evidence_messages):
        message = await _receive(
            session,
            timeout_s=scenario.evidence_timeout_s,
        )
        messages.append(message)
        _coordinate_if_material(message, supervisor)
        if (
            isinstance(message, MineflayerObservation)
            and message.snapshot.food > initial_food
        ):
            food_evidence = message
            break

    if food_evidence is None:
        skill = skill.fail(
            reason=(
                "consume_held was applied but no later observation "
                "showed increased food"
            ),
            at_ns=_next_owner_time(skill.events[-1].at_ns),
            provenance=consume_result.provenance,
        )
    else:
        skill = skill.succeed(
            reason="later Mineflayer observation showed increased food",
            at_ns=_next_owner_time(skill.events[-1].at_ns),
            provenance=food_evidence.provenance,
        )

    return _run_result(
        decision,
        skill,
        supervisor,
        action_ids,
        messages,
    )


async def _execute_flee(
    session: MineflayerScenarioSession,
    observation: MineflayerObservation,
    scenario: ControlledScenario,
    decision: ScenarioDecision,
    *,
    intent_commitment: IntentCommitment,
    supervisor: ActionSupervisor,
    authorization: str,
) -> SkillRunResult:
    destination = decision.destination
    if destination is None:
        raise ControlledScenarioError(
            "FLEE decision requires resolved destination"
        )

    messages: list[MineflayerDecodedMessage] = []
    action_ids: list[str] = []
    skill = _start_skill(
        ControlledSkill.FLEE,
        observation,
        intent_commitment,
    )
    start_position = observation.snapshot.position
    start_distance = _horizontal_distance(
        start_position,
        destination.position,
    )
    if start_distance == 0:
        raise ControlledScenarioError(
            "FLEE destination equals current horizontal position"
        )

    look_id = f"{skill.execution_id}:look"
    _issue_action(
        look_id,
        skill,
        intent_commitment,
        supervisor,
        authorization=authorization,
        timeout_s=scenario.evidence_timeout_s,
    )
    action_ids.append(look_id)
    await session.send_look(
        look_id,
        yaw=yaw_to_destination(
            start_position,
            destination.position,
        ),
        pitch=0.0,
    )
    look_result = await _await_effect_result(
        session,
        look_id,
        supervisor,
        messages,
        scenario=scenario,
    )
    if look_result.result != "applied":
        skill = skill.fail(
            reason=f"look rejected: {look_result.error}",
            at_ns=_next_owner_time(skill.events[-1].at_ns),
            provenance=look_result.provenance,
        )
        return _run_result(
            decision,
            skill,
            supervisor,
            action_ids,
            messages,
        )

    forward_id = f"{skill.execution_id}:forward"
    _issue_action(
        forward_id,
        skill,
        intent_commitment,
        supervisor,
        authorization=authorization,
        timeout_s=scenario.evidence_timeout_s,
    )
    action_ids.append(forward_id)
    await session.send_set_control(
        forward_id,
        control="forward",
        state=True,
    )
    forward_result = await _await_effect_result(
        session,
        forward_id,
        supervisor,
        messages,
        scenario=scenario,
    )

    progress_evidence: MineflayerObservation | None = None
    if forward_result.result == "applied":
        loop = asyncio.get_running_loop()
        progress_deadline = loop.time() + scenario.evidence_timeout_s
        while True:
            remaining = progress_deadline - loop.time()
            if remaining <= 0:
                break
            try:
                message = await asyncio.wait_for(
                    session.receive(),
                    timeout=remaining,
                )
            except TimeoutError:
                break
            messages.append(message)
            _coordinate_if_material(message, supervisor)
            if not isinstance(message, MineflayerObservation):
                continue
            current_distance = _horizontal_distance(
                message.snapshot.position,
                destination.position,
            )
            if (
                start_distance - current_distance
                >= scenario.flee_min_progress
            ):
                progress_evidence = message
                break

    stop_id = f"{skill.execution_id}:stop"
    _issue_action(
        stop_id,
        skill,
        intent_commitment,
        supervisor,
        authorization=authorization,
        timeout_s=scenario.evidence_timeout_s,
    )
    action_ids.append(stop_id)
    await session.send_clear_controls(stop_id)
    stop_result = await _await_effect_result(
        session,
        stop_id,
        supervisor,
        messages,
        scenario=scenario,
    )

    if forward_result.result != "applied":
        skill = skill.fail(
            reason=f"forward control rejected: {forward_result.error}",
            at_ns=_next_owner_time(skill.events[-1].at_ns),
            provenance=forward_result.provenance,
        )
    elif stop_result.result != "applied":
        skill = skill.fail(
            reason=f"clear_controls rejected: {stop_result.error}",
            at_ns=_next_owner_time(skill.events[-1].at_ns),
            provenance=stop_result.provenance,
        )
    elif progress_evidence is None:
        skill = skill.fail(
            reason=(
                "forward control was applied but no later observation "
                "showed progress toward the selected destination"
            ),
            at_ns=_next_owner_time(skill.events[-1].at_ns),
            provenance=forward_result.provenance,
        )
    else:
        skill = skill.succeed(
            reason=(
                "later Mineflayer observation showed horizontal progress "
                "toward the selected destination"
            ),
            at_ns=_next_owner_time(skill.events[-1].at_ns),
            provenance=progress_evidence.provenance,
        )

    return _run_result(
        decision,
        skill,
        supervisor,
        action_ids,
        messages,
    )


def _start_skill(
    skill: ControlledSkill,
    observation: MineflayerObservation,
    commitment: IntentCommitment,
) -> SkillExecution:
    return SkillExecution.start(
        f"skill:{skill.value.lower()}:{observation.session_id}:{observation.seq}",
        skill_id=skill.value,
        intent_commitment=commitment,
        at_ns=_monotonic_ns(),
        provenance=observation.provenance,
    )


def _issue_action(
    action_id: str,
    skill: SkillExecution,
    commitment: IntentCommitment,
    supervisor: ActionSupervisor,
    *,
    authorization: str,
    timeout_s: float,
) -> ActionLifecycle:
    proposed = ActionLifecycle.propose(
        action_id,
        skill_execution=skill,
        intent_commitment=commitment,
        at_ns=_monotonic_ns(),
        provenance=Provenance(
            source="controlled-minecraft-mvp",
            reference=f"{action_id}:proposal",
        ),
    )
    authorized = proposed.authorize(
        at_ns=_monotonic_ns(),
        provenance=Provenance(
            source="controlled-minecraft-mvp",
            reference=f"{action_id}:authorization",
        ),
        authority=authorization,
    )
    issued_at = _monotonic_ns()
    return supervisor.issue(
        authorized,
        at_ns=issued_at,
        deadline_ns=issued_at + int(timeout_s * 1_000_000_000),
        provenance=Provenance(
            source="controlled-minecraft-mvp",
            reference=f"{action_id}:issue",
        ),
    )


async def _await_effect_result(
    session: MineflayerScenarioSession,
    action_id: str,
    supervisor: ActionSupervisor,
    messages: list[MineflayerDecodedMessage],
    *,
    scenario: ControlledScenario,
) -> MineflayerEffectResult:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + scenario.evidence_timeout_s

    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise ControlledScenarioError(
                "timed out waiting for effect result for supervised action: "
                f"{action_id}"
            )
        try:
            message = await asyncio.wait_for(
                session.receive(),
                timeout=remaining,
            )
        except TimeoutError as exc:
            raise ControlledScenarioError(
                "timed out waiting for effect result for supervised action: "
                f"{action_id}"
            ) from exc

        messages.append(message)
        if (
            isinstance(message, MineflayerEffectResult)
            and message.action_id != action_id
        ):
            raise ControlledScenarioError(
                "controlled runner received effect result for unexpected "
                f"action: {message.action_id}"
            )
        result = coordinate_mineflayer_message(
            message,
            supervisor,
            at_ns=_monotonic_ns(),
        )
        if (
            isinstance(message, MineflayerEffectResult)
            and message.action_id == action_id
        ):
            if result is None or result.action_closure is None:
                raise ControlledScenarioError(
                    "effect result did not close supervised Action"
                )
            if result.action_closure.state is not ActionState.OUTCOME:
                raise ControlledScenarioError(
                    "effect result did not close Action as OUTCOME"
                )
            return message


def _coordinate_if_material(
    message: MineflayerDecodedMessage,
    supervisor: ActionSupervisor,
) -> None:
    if isinstance(message, MineflayerEffectResult):
        raise ControlledScenarioError(
            "unexpected effect result while awaiting consequence evidence"
        )
    coordinate_mineflayer_message(
        message,
        supervisor,
        at_ns=_monotonic_ns(),
    )


async def _receive(
    session: MineflayerScenarioSession,
    *,
    timeout_s: float,
) -> MineflayerDecodedMessage:
    try:
        return await asyncio.wait_for(
            session.receive(),
            timeout=timeout_s,
        )
    except TimeoutError as exc:
        raise ControlledScenarioError(
            "timed out waiting for controlled Minecraft evidence"
        ) from exc


def _run_result(
    decision: ScenarioDecision,
    skill: SkillExecution,
    supervisor: ActionSupervisor,
    action_ids: list[str],
    messages: list[MineflayerDecodedMessage],
) -> SkillRunResult:
    return SkillRunResult(
        decision=decision,
        skill_execution=skill,
        actions=tuple(
            supervisor.get(action_id)
            for action_id in action_ids
        ),
        messages=tuple(messages),
    )


def _horizontal_distance(
    left: MineflayerPosition,
    right: MineflayerPosition,
) -> float:
    return math.hypot(
        left.x - right.x,
        left.z - right.z,
    )


def _monotonic_ns() -> int:
    return time.monotonic_ns()


def _next_owner_time(previous: int) -> int:
    return max(previous + 1, _monotonic_ns())


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ControlledScenarioError(
            f"{name} must be a non-empty string"
        )


def _require_non_negative_number(name: str, value: object) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < 0
    ):
        raise ControlledScenarioError(
            f"{name} must be a finite non-negative number"
        )


def _require_positive_number(name: str, value: object) -> None:
    _require_non_negative_number(name, value)
    if value == 0:
        raise ControlledScenarioError(
            f"{name} must be positive"
        )
