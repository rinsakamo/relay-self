from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    MineflayerPosition,
)
from experiments.controlled_minecraft_restart import retain_successful_flee_memory
from experiments.controlled_minecraft_vertical import (
    ControlledDestination,
    ControlledScenario,
    ControlledSkill,
    ScenarioDecision,
    SkillRunResult,
    decide_skill,
    execute_decision,
)
from experiments.identity_prior_trajectory import (
    CAUTION_PRIOR,
    COMMON_DIRECTIVES,
    CONDITION_PRIORS,
    EXPLORATION_PRIOR,
    FORBIDDEN_MODEL_VISIBLE_LABELS,
    IDENTITY_CONTEXT_KEY,
    INTENT_ID,
    PLANNED_CONDITION_ORDER,
    PLANNED_REPETITIONS_PER_CONDITION,
    SELF_ID,
    build_candidate_world,
    build_preparation,
    canonical_request_sha256,
    provider_visible_user_payload,
)
from experiments.minecraft_terminal_qualification import (
    RecordedMineflayerSession,
    StageTracker,
    cognition_result_json,
    jsonable,
    launch_recorded_session,
    message_json,
    provider_engine,
    provenance_json,
    run_preflight as run_minecraft_runtime_preflight,
    sha256_file,
    skill_run_json,
    utc_now,
    write_json,
    write_server_command,
)
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    Memory,
    PersistentCognition,
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    DecisionStatus,
    RelayEngineResult,
)
from relay_self.skill import SkillState

TRANSACTION_NAME = "relay-self-220-identity-prior-trajectory"
REPORT_SCHEMA_VERSION = 1
RESET_POSITION_TOLERANCE = 0.08
RESET_ZOMBIE_DISTANCE_MIN = 3.5
RESET_ZOMBIE_DISTANCE_MAX = 4.5
FIRST_REQUEST_ID = "identity-prior:first-decision"
LATER_REQUEST_ID = "identity-prior:later-decision"


class IdentityPriorTransactionError(RuntimeError):
    """Raised when the frozen #220 matched transaction cannot remain qualified."""


@dataclass(frozen=True, slots=True)
class InvocationResult:
    condition_id: str
    block_index: int
    ordinal: int
    report: dict[str, object]


RelayEngineCallable = Callable[[BoundedChoiceRequest], RelayEngineResult]


def condition_sequence() -> tuple[str, ...]:
    flattened = tuple(
        condition
        for block in PLANNED_CONDITION_ORDER
        for condition in block
    )
    if len(flattened) != (
        len(CONDITION_PRIORS) * PLANNED_REPETITIONS_PER_CONDITION
    ):
        raise IdentityPriorTransactionError(
            "predeclared condition order does not match repetition count"
        )
    return flattened


def commit_intent() -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        INTENT_ID,
        objective="reach a viable route under bounded uncertainty",
        at_ns=1,
        provenance=Provenance(
            source=TRANSACTION_NAME,
            reference="current-intent:bounded-route",
        ),
    )
    return owner


def _fixture_descriptions() -> dict[str, str]:
    _, fixture = build_candidate_world()
    return {
        destination.destination_id: destination.description
        for destination in fixture.destinations
    }


def live_scenario(
    observation: MineflayerObservation,
    *,
    evidence_timeout_s: float,
) -> ControlledScenario:
    position = observation.snapshot.position
    descriptions = _fixture_descriptions()
    return ControlledScenario(
        hazard_entity_names=frozenset({"zombie"}),
        food_threshold=10,
        edible_item_names=("bread",),
        destinations=(
            ControlledDestination(
                destination_id="route-17",
                position=MineflayerPosition(
                    x=position.x,
                    y=position.y,
                    z=position.z - 10,
                ),
                description=descriptions["route-17"],
                provenance=Provenance(
                    source="experiment.world-fixture",
                    reference="destination:17",
                ),
            ),
            ControlledDestination(
                destination_id="route-42",
                position=MineflayerPosition(
                    x=position.x,
                    y=position.y,
                    z=position.z + 10,
                ),
                description=descriptions["route-42"],
                provenance=Provenance(
                    source="experiment.world-fixture",
                    reference="destination:42",
                ),
            ),
        ),
        flee_min_progress=0.25,
        evidence_timeout_s=evidence_timeout_s,
        max_evidence_messages=32,
        cognition_soft_wall_time_budget_s=None,
        cognition_think_allowed=True,
    )


def _route_destination(
    scenario: ControlledScenario,
    choice_id: str,
) -> ControlledDestination:
    for destination in scenario.destinations:
        if destination.destination_id == choice_id:
            return destination
    raise IdentityPriorTransactionError(
        f"RelayEngine resolved non-admissible destination: {choice_id}"
    )


def decide_from_predeclared_request(
    *,
    observation: MineflayerObservation,
    scenario: ControlledScenario,
    request: BoundedChoiceRequest,
    relay_engine: RelayEngineCallable,
) -> ScenarioDecision:
    """Use the frozen provider-visible request, then bind its result to live geometry."""

    pre_cognition = decide_skill(
        observation,
        scenario,
        intent_id=INTENT_ID,
        relay_engine=None,
    )
    if (
        pre_cognition.skill is not ControlledSkill.FLEE
        or pre_cognition.destination is not None
    ):
        raise IdentityPriorTransactionError(
            "live World did not preserve prior-independent ambiguous FLEE admission"
        )

    result = relay_engine(request)
    if not isinstance(result, RelayEngineResult):
        raise IdentityPriorTransactionError(
            "RelayEngine must return RelayEngineResult"
        )
    if result.status is not DecisionStatus.RESOLVED or result.choice_id is None:
        return ScenarioDecision(
            skill=ControlledSkill.FLEE,
            reason="matched cognition remained unresolved",
            cognition_result=result,
        )

    return ScenarioDecision(
        skill=ControlledSkill.FLEE,
        reason="matched Identity-prior cognition resolved a destination",
        destination=_route_destination(scenario, result.choice_id),
        cognition_result=result,
    )


def _relative_position(
    value: MineflayerPosition,
    anchor: MineflayerPosition,
) -> dict[str, float]:
    return {
        "x": round(value.x - anchor.x, 6),
        "y": 64.0,
        "z": round(value.z - anchor.z, 6),
    }


def build_later_request(
    *,
    identity_request: BoundedChoiceRequest,
    observation: MineflayerObservation,
    anchor: MineflayerPosition,
    memory: Memory | None,
) -> BoundedChoiceRequest:
    """Project later live evidence into the same local frame used by the frozen fixture."""

    descriptions = _fixture_descriptions()
    world_provenance = Provenance(
        source="mineflayer",
        reference="matched-later-observation",
    )
    destination_provenance = Provenance(
        source="experiment.world-fixture",
        reference="later-destination-catalog",
    )
    position = observation.snapshot.position
    context: list[CognitionDatum] = [
        CognitionDatum.from_value(
            "health",
            observation.snapshot.health,
            world_provenance,
        ),
        CognitionDatum.from_value(
            "food",
            observation.snapshot.food,
            world_provenance,
        ),
        CognitionDatum.from_value(
            "position",
            _relative_position(position, anchor),
            world_provenance,
        ),
        CognitionDatum.from_value(
            "nearby_entities",
            [
                {
                    "name": entity.name,
                    "type": entity.entity_type,
                    "distance": round(entity.distance, 6),
                    "position": _relative_position(entity.position, anchor),
                }
                for entity in observation.snapshot.nearby_entities
            ],
            world_provenance,
        ),
        CognitionDatum.from_value(
            "destination:route-17",
            {
                "position": {
                    "x": round(position.x - anchor.x, 6),
                    "y": 64.0,
                    "z": round(position.z - anchor.z - 10, 6),
                },
                "description": descriptions["route-17"],
            },
            destination_provenance,
        ),
        CognitionDatum.from_value(
            "destination:route-42",
            {
                "position": {
                    "x": round(position.x - anchor.x, 6),
                    "y": 64.0,
                    "z": round(position.z - anchor.z + 10, 6),
                },
                "description": descriptions["route-42"],
            },
            destination_provenance,
        ),
    ]

    identity = next(
        (
            datum
            for datum in identity_request.context
            if datum.key == IDENTITY_CONTEXT_KEY
        ),
        None,
    )
    if identity is None:
        raise IdentityPriorTransactionError(
            "frozen Identity datum is missing from later request source"
        )
    context.append(identity)

    if memory is not None:
        context.append(
            CognitionDatum.from_value(
                "memory:first-grounded-flee",
                {
                    "semantic_type": "Memory",
                    "content": memory.content,
                    "source_provenance": {
                        "source": "mineflayer",
                        "reference": "first-grounded-consequence",
                    },
                },
                Provenance(
                    source=TRANSACTION_NAME,
                    reference="explicit-memory-integration:first-grounded-flee",
                ),
            )
        )

    request = BoundedChoiceRequest(
        request_id=LATER_REQUEST_ID,
        instruction=identity_request.instruction,
        intent_id=identity_request.intent_id,
        focus=identity_request.focus,
        choices=(
            BoundedChoice("route-17", descriptions["route-17"]),
            BoundedChoice("route-42", descriptions["route-42"]),
        ),
        context=tuple(context),
        soft_wall_time_budget_s=identity_request.soft_wall_time_budget_s,
        think_allowed=identity_request.think_allowed,
    )
    assert_no_condition_leakage(request)
    return request


def assert_no_condition_leakage(request: BoundedChoiceRequest) -> None:
    visible = provider_visible_user_payload(request)
    rendered = json.dumps(
        visible,
        ensure_ascii=False,
        sort_keys=True,
    ).lower()
    for label in FORBIDDEN_MODEL_VISIBLE_LABELS:
        if label in rendered:
            raise IdentityPriorTransactionError(
                f"provider-visible condition leakage: {label}"
            )
    if "condition_id" in rendered:
        raise IdentityPriorTransactionError(
            "provider-visible condition bookkeeping leakage"
        )


def _last_observation(run: SkillRunResult) -> MineflayerObservation:
    observations = [
        message
        for message in run.messages
        if isinstance(message, MineflayerObservation)
    ]
    if not observations:
        raise IdentityPriorTransactionError(
            "grounded Skill run did not record a consequence observation"
        )
    return observations[-1]


def _position_matches(
    value: MineflayerPosition,
    expected: MineflayerPosition,
) -> bool:
    return (
        abs(value.x - expected.x) <= RESET_POSITION_TOLERANCE
        and abs(value.y - expected.y) <= RESET_POSITION_TOLERANCE
        and abs(value.z - expected.z) <= RESET_POSITION_TOLERANCE
    )


def _reset_observation_matches(
    observation: MineflayerObservation,
    anchor: MineflayerPosition,
) -> bool:
    zombies = [
        entity
        for entity in observation.snapshot.nearby_entities
        if entity.name == "zombie"
    ]
    return (
        observation.snapshot.health == 20
        and observation.snapshot.food == 20
        and _position_matches(observation.snapshot.position, anchor)
        and len(zombies) == 1
        and RESET_ZOMBIE_DISTANCE_MIN
        <= zombies[0].distance
        <= RESET_ZOMBIE_DISTANCE_MAX
    )


async def reset_live_world(
    session: RecordedMineflayerSession,
    *,
    args: argparse.Namespace,
    anchor: MineflayerPosition,
    evidence_path: Path,
) -> MineflayerObservation:
    commands = (
        (
            "kill @e[type=minecraft:zombie]",
            "matched reset: remove prior controlled threat",
        ),
        (
            f"effect clear {args.username}",
            "matched reset: clear prior effects",
        ),
        (
            f"clear {args.username}",
            "matched reset: clear inventory",
        ),
        (
            f"tp {args.username} {anchor.x:.6f} {anchor.y:.6f} {anchor.z:.6f} 0 0",
            "matched reset: restore anchor position and orientation",
        ),
        (
            f"effect give {args.username} minecraft:instant_health 1 255 true",
            "matched reset: restore full health",
        ),
        (
            f"effect give {args.username} minecraft:saturation 2 255 true",
            "matched reset: restore sufficient food",
        ),
        (
            "time set noon",
            "matched reset: common server time",
        ),
        (
            (
                f"execute at {args.username} run summon minecraft:zombie "
                "~4 ~ ~ {NoAI:1b,PersistenceRequired:1b,Silent:1b}"
            ),
            "matched reset: non-terminal static uncertainty/threat fixture",
        ),
    )
    for command, reason in commands:
        await write_server_command(
            control_path=Path(args.server_control),
            evidence_path=evidence_path,
            command=command,
            reason=reason,
            settle_s=0.1,
        )

    observation = await _receive_until_reset(
        session,
        anchor=anchor,
        timeout_s=args.evidence_timeout_s,
    )
    await write_server_command(
        control_path=Path(args.server_control),
        evidence_path=evidence_path,
        command=f"effect clear {args.username} minecraft:saturation",
        reason="matched reset: remove temporary saturation effect",
        settle_s=0.05,
    )
    return observation


async def _receive_until_reset(
    session: RecordedMineflayerSession,
    *,
    anchor: MineflayerPosition,
    timeout_s: float,
) -> MineflayerObservation:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise IdentityPriorTransactionError(
                "timed out waiting for matched reset observation"
            )
        try:
            message = await asyncio.wait_for(
                session.receive(),
                timeout=remaining,
            )
        except TimeoutError as exc:
            raise IdentityPriorTransactionError(
                "timed out waiting for matched reset observation"
            ) from exc
        if isinstance(message, MineflayerObservation):
            if _reset_observation_matches(message, anchor):
                return message


def _initial_request_for_condition(condition_id: str) -> BoundedChoiceRequest:
    preparation = build_preparation()
    condition = next(
        item
        for item in preparation.conditions
        if item.condition_id == condition_id
    )
    request = replace(condition.request, request_id=FIRST_REQUEST_ID)
    assert_no_condition_leakage(request)
    return request


def _identity_cognition_for_condition(condition_id: str) -> PersistentCognition:
    preparation = build_preparation()
    condition = next(
        item
        for item in preparation.conditions
        if item.condition_id == condition_id
    )
    return condition.cognition


def _provider_request_record(
    request: BoundedChoiceRequest,
) -> dict[str, object]:
    return {
        "sha256": canonical_request_sha256(request),
        "user_payload": provider_visible_user_payload(request),
    }


def _memory_record(memory: Memory) -> dict[str, object]:
    return {
        "memory_id": memory.memory_id,
        "content": memory.content,
        "source_provenance": provenance_json(memory.source_provenance),
        "integration_provenance": provenance_json(
            memory.integration_provenance
        ),
        "semantic_type": "Memory",
    }


def _cognition_signature(
    result: RelayEngineResult | None,
) -> list[dict[str, object]]:
    if result is None:
        return []
    return [
        {
            "mode": attempt.mode.value,
            "status": attempt.status.value,
            "choice_id": attempt.choice_id,
        }
        for attempt in result.attempts
    ]


async def run_invocation(
    *,
    args: argparse.Namespace,
    condition_id: str,
    block_index: int,
    ordinal: int,
    anchor: MineflayerPosition,
    engine: RelayEngineCallable,
) -> InvocationResult:
    invocation_name = f"block-{block_index + 1:02d}-{ordinal + 1:02d}-{condition_id}"
    invocation_root = Path(args.evidence_root) / "invocations" / invocation_name
    invocation_root.mkdir(parents=True, exist_ok=False)
    persistent_path = invocation_root / "persistent-cognition.json"
    commands_path = invocation_root / "server-commands.jsonl"
    cognition = _identity_cognition_for_condition(condition_id)
    save_persistent_cognition(persistent_path, cognition)

    session: RecordedMineflayerSession | None = None
    try:
        session = await launch_recorded_session(
            args,
            phase=invocation_name,
        )
        reset_observation = await reset_live_world(
            session,
            args=args,
            anchor=anchor,
            evidence_path=commands_path,
        )
        common_scenario = live_scenario(
            reset_observation,
            evidence_timeout_s=args.evidence_timeout_s,
        )
        first_request = _initial_request_for_condition(condition_id)
        first_decision = decide_from_predeclared_request(
            observation=reset_observation,
            scenario=common_scenario,
            request=first_request,
            relay_engine=engine,
        )

        report: dict[str, object] = {
            "condition_id": condition_id,
            "block_index": block_index,
            "ordinal_in_block": ordinal,
            "invocation_name": invocation_name,
            "identity_specification": {
                "self_id": cognition.identity.self_id,
                "directives": list(cognition.identity.directives),
                "provenance": provenance_json(cognition.identity.provenance),
            },
            "initial_present": message_json(reset_observation),
            "initial_provider_request": _provider_request_record(first_request),
            "initial_cognition": cognition_result_json(
                first_decision.cognition_result
            ),
            "initial_cognition_signature": _cognition_signature(
                first_decision.cognition_result
            ),
            "first_selected_skill": first_decision.skill.value,
            "first_bound_destination": (
                first_decision.destination.destination_id
                if first_decision.destination is not None
                else None
            ),
            "first_skill_run": None,
            "first_world_consequence": None,
            "durable_memory": None,
            "persistent_sha256": None,
            "later_present": None,
            "later_provider_request": None,
            "later_cognition": None,
            "later_cognition_signature": [],
            "later_bound_destination": None,
            "later_skill_run": None,
            "status": "completed",
        }

        if not first_decision.resolved:
            report["status"] = "completed_unresolved_before_action"
            report["event_driven"] = {
                "raw_received_events": session.raw_received_events,
                "admitted_decision_epochs": session.admitted_decision_epochs,
                "received_by_type": dict(session.received_by_type),
            }
            write_json(invocation_root / "report.json", report)
            return InvocationResult(
                condition_id=condition_id,
                block_index=block_index,
                ordinal=ordinal,
                report=report,
            )

        commitment = commit_intent()
        first_run = await execute_decision(
            session,
            reset_observation,
            common_scenario,
            first_decision,
            intent_commitment=commitment,
            supervisor=_new_supervisor(),
            authorization=TRANSACTION_NAME,
        )
        if (
            first_run is None
            or first_run.skill_execution.state is not SkillState.SUCCEEDED
        ):
            raise IdentityPriorTransactionError(
                "first resolved FLEE did not close from grounded progress"
            )
        consequence = _last_observation(first_run)

        integrated = retain_successful_flee_memory(
            cognition,
            first_run,
            integration_provenance=Provenance(
                source=TRANSACTION_NAME,
                reference="explicit-memory-integration:first-grounded-flee",
            ),
        )
        save_persistent_cognition(persistent_path, integrated)
        reloaded = load_persistent_cognition(persistent_path)
        if reloaded.identity != cognition.identity or len(reloaded.memories) != 1:
            raise IdentityPriorTransactionError(
                "explicit retained experience did not round-trip correctly"
            )
        memory = reloaded.memories[0]

        later_request = build_later_request(
            identity_request=first_request,
            observation=consequence,
            anchor=anchor,
            memory=memory,
        )
        later_scenario = live_scenario(
            consequence,
            evidence_timeout_s=args.evidence_timeout_s,
        )
        later_decision = decide_from_predeclared_request(
            observation=consequence,
            scenario=later_scenario,
            request=later_request,
            relay_engine=engine,
        )

        later_run: SkillRunResult | None = None
        if later_decision.resolved:
            later_run = await execute_decision(
                session,
                consequence,
                later_scenario,
                later_decision,
                intent_commitment=commitment,
                supervisor=_new_supervisor(),
                authorization=TRANSACTION_NAME,
            )
            if (
                later_run is None
                or later_run.skill_execution.state is not SkillState.SUCCEEDED
            ):
                raise IdentityPriorTransactionError(
                    "later resolved FLEE did not close from grounded progress"
                )

        report.update(
            {
                "first_skill_run": skill_run_json(first_run),
                "first_world_consequence": message_json(consequence),
                "durable_memory": _memory_record(memory),
                "persistent_sha256": sha256_file(persistent_path),
                "later_present": message_json(consequence),
                "later_provider_request": _provider_request_record(
                    later_request
                ),
                "later_cognition": cognition_result_json(
                    later_decision.cognition_result
                ),
                "later_cognition_signature": _cognition_signature(
                    later_decision.cognition_result
                ),
                "later_bound_destination": (
                    later_decision.destination.destination_id
                    if later_decision.destination is not None
                    else None
                ),
                "later_skill_run": (
                    skill_run_json(later_run)
                    if later_run is not None
                    else None
                ),
                "status": (
                    "completed_grounded_trajectory"
                    if later_run is not None
                    else "completed_later_unresolved"
                ),
                "event_driven": {
                    "raw_received_events": session.raw_received_events,
                    "admitted_decision_epochs": (
                        session.admitted_decision_epochs
                    ),
                    "received_by_type": dict(session.received_by_type),
                },
            }
        )
        write_json(invocation_root / "report.json", report)
        return InvocationResult(
            condition_id=condition_id,
            block_index=block_index,
            ordinal=ordinal,
            report=report,
        )
    finally:
        if session is not None:
            try:
                await session.shutdown()
            except Exception:
                try:
                    await session.terminate()
                except Exception:
                    pass


def _new_supervisor():
    from relay_self.action_supervision import ActionSupervisor

    return ActionSupervisor()


def _choice_vector(
    records: list[InvocationResult],
    key: str,
) -> dict[str, list[object]]:
    result = {condition: [] for condition in CONDITION_PRIORS}
    for item in records:
        result[item.condition_id].append(item.report.get(key))
    return result


def _signature_vector(
    records: list[InvocationResult],
) -> dict[str, list[str]]:
    result = {condition: [] for condition in CONDITION_PRIORS}
    for item in records:
        signature = json.dumps(
            item.report.get("initial_cognition_signature"),
            sort_keys=True,
            separators=(",", ":"),
        )
        result[item.condition_id].append(signature)
    return result


def classify(records: list[InvocationResult]) -> dict[str, object]:
    if len(records) != len(condition_sequence()):
        raise IdentityPriorTransactionError(
            "cannot classify an incomplete matched transaction"
        )

    first = _choice_vector(records, "first_bound_destination")
    later = _choice_vector(records, "later_bound_destination")
    signatures = _signature_vector(records)

    stable_first: dict[str, object | None] = {}
    for condition_id, choices in first.items():
        unique = set(choices)
        stable_first[condition_id] = (
            choices[0]
            if len(unique) == 1 and choices[0] is not None
            else None
        )

    grounded = all(
        item.report.get("status") == "completed_grounded_trajectory"
        for item in records
    )
    stable_non_null = {
        choice
        for choice in stable_first.values()
        if choice is not None
    }
    if grounded and len(stable_non_null) >= 2:
        interpretation = "A"
        label = "embodied prior effect"
        rationale = (
            "At least two conditions produced different within-condition "
            "stable first embodied destinations across all predeclared "
            "repetitions, with grounded Action consequences and later "
            "trajectory evidence."
        )
    else:
        first_vectors = {
            condition: tuple(choices)
            for condition, choices in first.items()
        }
        signature_vectors = {
            condition: tuple(values)
            for condition, values in signatures.items()
        }
        if (
            len(set(first_vectors.values())) > 1
            or len(set(signature_vectors.values())) > 1
        ):
            interpretation = "B"
            label = "transient cognition-only effect"
            rationale = (
                "The matched cognition outcomes differ across conditions, "
                "but the strict reproducible grounded-trajectory criterion "
                "for class A was not met."
            )
        else:
            interpretation = "E"
            label = "no discriminating effect"
            rationale = (
                "The predeclared matched conditions were indistinguishable "
                "on the bounded cognition/first-destination surface under "
                "this transaction."
            )

    return {
        "class": interpretation,
        "label": label,
        "rationale": rationale,
        "first_destination_by_condition": first,
        "later_destination_by_condition": later,
        "initial_cognition_signature_by_condition": signatures,
        "presentation_only_class_c_observable": False,
        "policy_leakage_class_d": False,
        "strict_grounded_trajectory_complete": grounded,
    }


def transaction_plan() -> dict[str, object]:
    preparation = build_preparation()
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "transaction": TRANSACTION_NAME,
        "phase": "plan",
        "scientific_spend": {
            "model_calls": 0,
            "minecraft_sessions": 0,
        },
        "condition_order": list(condition_sequence()),
        "blocks": [
            list(block)
            for block in PLANNED_CONDITION_ORDER
        ],
        "repetitions_per_condition": PLANNED_REPETITIONS_PER_CONDITION,
        "identity_priors": {
            "A": list(COMMON_DIRECTIVES),
            "B": [*COMMON_DIRECTIVES, EXPLORATION_PRIOR],
            "C": [*COMMON_DIRECTIVES, CAUTION_PRIOR],
        },
        "initial_request_sha256": {
            item.condition_id: canonical_request_sha256(
                replace(item.request, request_id=FIRST_REQUEST_ID)
            )
            for item in preparation.conditions
        },
        "execution_boundary": (
            "Nine predeclared condition invocations. Each begins from a "
            "matched live reset and zero Memory. A resolved first FLEE must "
            "close from live progress before explicit Memory integration. "
            "The later decision then uses the retained experience beside "
            "fresh consequence evidence."
        ),
        "failure_policy": (
            "Stop at the first operational/protocol/grounding failure. "
            "Preserve all prior evidence. No retry, replay, alternate "
            "condition, or same-run fixture tuning."
        ),
    }


def run_preflight(args: argparse.Namespace) -> dict[str, object]:
    build_preparation()
    base = run_minecraft_runtime_preflight(args)
    base["qualification"] = TRANSACTION_NAME
    base["source_runtime_preflight"] = (
        "experiments.minecraft_terminal_qualification.run_preflight"
    )
    base["scientific_transaction_started"] = False
    base["matched_protocol"] = transaction_plan()
    base["scenario"] = {
        "world_reset": (
            "same anchor, full health/food, empty inventory, noon, one "
            "NoAI persistent zombie at approximately four blocks"
        ),
        "first_decision": (
            "frozen provider-visible local-frame route-17/route-42 request"
        ),
        "embodiment": (
            "selected route is mapped to live geometry and executed through "
            "the existing supervised FLEE Action path"
        ),
        "experience": (
            "only grounded successful FLEE is explicitly retained and "
            "save/load round-tripped"
        ),
        "later_decision": (
            "later live consequence is projected in the same local frame "
            "beside the retained Memory"
        ),
    }
    write_json(Path(args.evidence_root) / "preflight.json", base)
    return base


async def run_transaction(
    args: argparse.Namespace,
    tracker: StageTracker,
) -> dict[str, object]:
    evidence_root = Path(args.evidence_root)
    engine = provider_engine(args)
    records: list[InvocationResult] = []
    anchor: MineflayerPosition | None = None

    for block_index, block in enumerate(PLANNED_CONDITION_ORDER):
        for ordinal, condition_id in enumerate(block):
            tracker.set(
                f"matched_invocation:block-{block_index + 1}:"
                f"ordinal-{ordinal + 1}:condition-{condition_id}"
            )

            if anchor is None:
                anchor_session: RecordedMineflayerSession | None = None
                try:
                    anchor_session = await launch_recorded_session(
                        args,
                        phase="anchor",
                    )
                    anchor_observation = await _receive_spawn(
                        anchor_session,
                        timeout_s=args.evidence_timeout_s,
                    )
                    anchor = anchor_observation.snapshot.position
                    write_json(
                        evidence_root / "anchor.json",
                        {
                            "position": jsonable(anchor),
                            "observation": message_json(anchor_observation),
                            "session_id": anchor_session.started.session_id,
                            "scientific_condition": None,
                            "provider_calls": 0,
                        },
                    )
                finally:
                    if anchor_session is not None:
                        try:
                            await anchor_session.shutdown()
                        except Exception:
                            try:
                                await anchor_session.terminate()
                            except Exception:
                                pass

            result = await run_invocation(
                args=args,
                condition_id=condition_id,
                block_index=block_index,
                ordinal=ordinal,
                anchor=anchor,
                engine=engine,
            )
            records.append(result)

    interpretation = classify(records)
    total_calls = sum(
        _provider_call_count(item.report.get("initial_cognition"))
        + _provider_call_count(item.report.get("later_cognition"))
        for item in records
    )
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "transaction": TRANSACTION_NAME,
        "status": "SCIENTIFIC TRANSACTION COMPLETED",
        "completed": True,
        "started_at": args.transaction_started_at,
        "completed_at": utc_now(),
        "repository": read_json_required(
            Path(args.evidence_root) / "preflight.json",
            "repository",
        ),
        "runtime": read_json_required(
            Path(args.evidence_root) / "preflight.json",
            "runtime",
        ),
        "condition_order": list(condition_sequence()),
        "repetitions_per_condition": PLANNED_REPETITIONS_PER_CONDITION,
        "scientific_spend": {
            "matched_condition_invocations": len(records),
            "model_provider_calls": total_calls,
            "minecraft_condition_sessions": len(records),
            "anchor_sessions": 1,
        },
        "invocations": [item.report for item in records],
        "interpretation": interpretation,
        "retry_count": 0,
        "replay_count": 0,
        "same_run_fixture_tuning": False,
        "evidence_root": str(evidence_root.resolve()),
    }
    write_json(evidence_root / "scientific-report.json", report)
    return report


async def _receive_spawn(
    session: RecordedMineflayerSession,
    *,
    timeout_s: float,
) -> MineflayerObservation:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise IdentityPriorTransactionError(
                "timed out waiting for anchor spawn observation"
            )
        try:
            message = await asyncio.wait_for(
                session.receive(),
                timeout=remaining,
            )
        except TimeoutError as exc:
            raise IdentityPriorTransactionError(
                "timed out waiting for anchor spawn observation"
            ) from exc
        if (
            isinstance(message, MineflayerObservation)
            and message.kind == "spawn"
        ):
            return message


def _provider_call_count(value: object) -> int:
    if not isinstance(value, dict):
        return 0
    count = value.get("provider_call_count")
    return count if isinstance(count, int) else 0


def read_json_required(path: Path, key: str) -> object:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IdentityPriorTransactionError(
            f"could not read required evidence {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict) or key not in payload:
        raise IdentityPriorTransactionError(
            f"required evidence key {key!r} missing from {path}"
        )
    return payload[key]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run the predeclared RelaySelf #220 matched trajectory transaction."
    )
    result.add_argument(
        "--phase",
        choices=("plan", "preflight", "run"),
        required=True,
    )
    result.add_argument("--repo-root", default=".")
    result.add_argument("--evidence-root", required=True)
    result.add_argument("--server-root")
    result.add_argument("--server-log")
    result.add_argument("--authority-path")
    result.add_argument("--runtime-artifacts-path")
    result.add_argument("--minecraft-version", default="26.1")
    result.add_argument("--minecraft-host", default="127.0.0.1")
    result.add_argument("--minecraft-port", type=int, default=25565)
    result.add_argument("--minecraft-protocol-version")
    result.add_argument("--minecraft-pid", type=int)
    result.add_argument("--server-control")
    result.add_argument("--node", default="node")
    result.add_argument("--npm", default="npm")
    result.add_argument("--java")
    result.add_argument("--llama")
    result.add_argument("--llama-origin", default="http://127.0.0.1:8080")
    result.add_argument("--llama-port", type=int, default=8080)
    result.add_argument("--llama-pid", type=int)
    result.add_argument("--model", required=True)
    result.add_argument("--served-model")
    result.add_argument("--llama-timeout", type=float, default=60.0)
    result.add_argument("--self-id", default=SELF_ID)
    result.add_argument("--username", default="RelaySelf")
    result.add_argument("--persistent-path")
    result.add_argument("--startup-timeout-s", type=float, default=15.0)
    result.add_argument("--evidence-timeout-s", type=float, default=8.0)
    return result


def validate_args(args: argparse.Namespace) -> None:
    args.repo_root = str(Path(args.repo_root).resolve())
    args.evidence_root = str(Path(args.evidence_root).resolve())
    Path(args.evidence_root).mkdir(parents=True, exist_ok=True)
    if args.persistent_path is None:
        args.persistent_path = str(
            Path(args.evidence_root) / "preflight-persistent.json"
        )
    if args.self_id != SELF_ID:
        raise IdentityPriorTransactionError(
            f"#220 frozen self_id must remain {SELF_ID}"
        )
    if args.phase == "preflight":
        required = (
            "server_root",
            "server_log",
            "authority_path",
            "runtime_artifacts_path",
            "minecraft_pid",
            "server_control",
            "java",
            "llama",
            "llama_pid",
            "served_model",
        )
        for name in required:
            if not getattr(args, name, None):
                raise IdentityPriorTransactionError(
                    f"preflight requires --{name.replace('_', '-')}"
                )
    if args.phase == "run":
        required = (
            "server_control",
            "served_model",
        )
        for name in required:
            if not getattr(args, name, None):
                raise IdentityPriorTransactionError(
                    f"run requires --{name.replace('_', '-')}"
                )


async def async_main(args: argparse.Namespace) -> int:
    validate_args(args)
    if args.phase == "plan":
        plan = transaction_plan()
        write_json(Path(args.evidence_root) / "transaction-plan.json", plan)
        print(json.dumps(plan, ensure_ascii=False, sort_keys=True))
        return 0
    if args.phase == "preflight":
        preflight = run_preflight(args)
        print(json.dumps(preflight, ensure_ascii=False, sort_keys=True))
        return 0

    tracker = StageTracker("run")
    args.transaction_started_at = utc_now()
    try:
        report = await run_transaction(args, tracker)
    except Exception as exc:
        failure = {
            "transaction": TRANSACTION_NAME,
            "status": "FAIL_NOT_QUALIFIED",
            "scientific_transaction_started": True,
            "first_concrete_failure_stage": tracker.stage,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "timestamp": utc_now(),
            "retry_count": 0,
            "replay_count": 0,
            "same_run_fixture_tuning": False,
        }
        write_json(
            Path(args.evidence_root) / "failure-report.json",
            failure,
        )
        print(
            json.dumps(failure, ensure_ascii=False, sort_keys=True),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


def main() -> int:
    args = parser().parse_args()
    try:
        return asyncio.run(async_main(args))
    except Exception as exc:
        evidence_root = Path(args.evidence_root).resolve()
        evidence_root.mkdir(parents=True, exist_ok=True)
        failure = {
            "transaction": TRANSACTION_NAME,
            "status": "PRE_SPEND_BLOCKED",
            "scientific_transaction_started": False,
            "phase": args.phase,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "timestamp": utc_now(),
            "retry_count": 0,
            "replay_count": 0,
        }
        write_json(evidence_root / "pre-spend-failure.json", failure)
        print(
            json.dumps(failure, ensure_ascii=False, sort_keys=True),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
