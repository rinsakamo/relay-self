from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace

from adapters.llama_cpp.relay_engine import (
    BOUNDED_MAX_TOKENS,
    THINK_MAX_TOKENS,
    render_llama_cpp_request,
)
from adapters.mineflayer.python_protocol import (
    MineflayerEntityFact,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from experiments.controlled_minecraft_vertical import (
    ControlledDestination,
    ControlledScenario,
    ControlledSkill,
    ScenarioDecision,
    build_flee_destination_request,
    decide_skill,
)
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
)

REPORT_SCHEMA_VERSION = 1
IDENTITY_CONTEXT_KEY = "identity_specification"
INTENT_ID = "intent-220-reach-safety"
SELF_ID = "relay-self-220"
MODEL_RENDER_ID = "relay-self-220-model"

COMMON_DIRECTIVES = (
    "Preserve current evidence, authority, viability, and action-authorization boundaries.",
)
EXPLORATION_PRIOR = (
    "Place somewhat greater value on reducing relevant uncertainty and expanding "
    "well-grounded knowledge of the environment."
)
CAUTION_PRIOR = (
    "Place somewhat greater value on preserving known-safe options and avoiding "
    "poorly understood risk."
)

CONDITION_PRIORS: dict[str, tuple[str, ...]] = {
    "A": (),
    "B": (EXPLORATION_PRIOR,),
    "C": (CAUTION_PRIOR,),
}

AVAILABLE_SKILLS = (
    ControlledSkill.WAIT.value,
    ControlledSkill.EAT.value,
    ControlledSkill.FLEE.value,
)
ACTION_CAPABILITIES = (
    "equip_item",
    "consume_held",
    "look",
    "set_control",
    "clear_controls",
)
FORBIDDEN_MODEL_VISIBLE_LABELS = (
    "neutral",
    "explorer",
    "cautious",
    "expected_choice",
    "preferred_destination",
)

PLANNED_CONDITION_ORDER = (
    ("A", "B", "C"),
    ("B", "C", "A"),
    ("C", "A", "B"),
)
PLANNED_REPETITIONS_PER_CONDITION = 3
PLANNED_LLAMA_CPP_REVISION = "e2d2c0d6a"
PLANNED_LLAMA_CPP_BUILD = 10874
PLANNED_GGUF_SHA256 = (
    "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
)


class IdentityPriorApparatusError(ValueError):
    """Raised when the #220 preparation apparatus violates its frozen controls."""


@dataclass(frozen=True, slots=True)
class IdentityPriorCondition:
    """Evidence-bookkeeping condition; the id is never added to model context."""

    condition_id: str
    cognition: PersistentCognition
    observation: MineflayerObservation
    scenario: ControlledScenario
    pre_cognition_decision: ScenarioDecision
    request: BoundedChoiceRequest


@dataclass(frozen=True, slots=True)
class IdentityPriorPreparation:
    observation: MineflayerObservation
    scenario: ControlledScenario
    conditions: tuple[IdentityPriorCondition, ...]


def identity_for_condition(condition_id: str) -> IdentitySpecification:
    try:
        prior = CONDITION_PRIORS[condition_id]
    except KeyError as exc:
        raise IdentityPriorApparatusError(
            f"unknown condition id: {condition_id}"
        ) from exc

    return IdentitySpecification(
        self_id=SELF_ID,
        directives=(*COMMON_DIRECTIVES, *prior),
        provenance=Provenance(
            source="experiment.identity-specification",
            reference="identity-specification:initial",
        ),
    )


def build_candidate_world() -> tuple[MineflayerObservation, ControlledScenario]:
    """Return the single frozen ambiguous embodied fixture for preparation.

    A current hazard makes FLEE admission deterministic before the Identity
    prior is consulted. The two equal-distance destinations then differ only
    in factual uncertainty/resource information, leaving either route
    admissible for the later model-backed matched experiment.
    """

    observation = MineflayerObservation(
        session_id="fixture-session",
        seq=1,
        kind="entities",
        snapshot=MineflayerSnapshot(
            health=20,
            food=20,
            oxygen_level=20,
            position=MineflayerPosition(x=0, y=64, z=0),
            time=None,
            inventory=(),
            nearby_entities=(
                MineflayerEntityFact(
                    entity_id=7,
                    name="zombie",
                    entity_type="mob",
                    distance=4.0,
                    position=MineflayerPosition(x=4, y=64, z=0),
                ),
            ),
        ),
    )

    scenario = ControlledScenario(
        hazard_entity_names=frozenset({"zombie"}),
        food_threshold=10,
        edible_item_names=("bread",),
        destinations=(
            ControlledDestination(
                destination_id="route-17",
                position=MineflayerPosition(x=0, y=64, z=-10),
                description=(
                    "Waypoint is ten blocks north. The corridor and waypoint "
                    "are currently visible from this position; no exposed "
                    "resource block is visible along the corridor."
                ),
                provenance=Provenance(
                    source="experiment.world-fixture",
                    reference="destination:17",
                ),
            ),
            ControlledDestination(
                destination_id="route-42",
                position=MineflayerPosition(x=0, y=64, z=10),
                description=(
                    "Waypoint is ten blocks south. Terrain beyond a bend is "
                    "outside current observation; an exposed coal ore block is "
                    "visible before the bend."
                ),
                provenance=Provenance(
                    source="experiment.world-fixture",
                    reference="destination:42",
                ),
            ),
        ),
        flee_min_progress=0.25,
        evidence_timeout_s=3.0,
        max_evidence_messages=32,
        cognition_soft_wall_time_budget_s=None,
        cognition_think_allowed=True,
    )
    return observation, scenario


def build_preparation() -> IdentityPriorPreparation:
    observation, scenario = build_candidate_world()
    conditions = tuple(
        _build_condition(
            condition_id,
            observation=observation,
            scenario=scenario,
        )
        for condition_id in CONDITION_PRIORS
    )
    preparation = IdentityPriorPreparation(
        observation=observation,
        scenario=scenario,
        conditions=conditions,
    )
    validate_preparation(preparation)
    return preparation


def _build_condition(
    condition_id: str,
    *,
    observation: MineflayerObservation,
    scenario: ControlledScenario,
) -> IdentityPriorCondition:
    identity = identity_for_condition(condition_id)
    cognition = PersistentCognition(identity=identity)

    pre_cognition = decide_skill(
        observation,
        scenario,
        intent_id=INTENT_ID,
        relay_engine=None,
    )
    if pre_cognition.skill is not ControlledSkill.FLEE:
        raise IdentityPriorApparatusError(
            "candidate world must deterministically admit FLEE before prior use"
        )
    if pre_cognition.destination is not None:
        raise IdentityPriorApparatusError(
            "candidate world must preserve a bounded destination decision"
        )

    base = build_flee_destination_request(
        observation,
        scenario,
        intent_id=INTENT_ID,
        retained_memories=cognition.memories,
    )
    identity_datum = CognitionDatum.from_value(
        IDENTITY_CONTEXT_KEY,
        {
            "semantic_type": "IdentitySpecification",
            "self_id": identity.self_id,
            "directives": list(identity.directives),
        },
        identity.provenance,
    )
    request = replace(
        base,
        context=(*base.context, identity_datum),
    )
    return IdentityPriorCondition(
        condition_id=condition_id,
        cognition=cognition,
        observation=observation,
        scenario=scenario,
        pre_cognition_decision=pre_cognition,
        request=request,
    )


def provider_visible_user_payload(
    request: BoundedChoiceRequest,
) -> dict[str, object]:
    rendered = render_llama_cpp_request(
        request,
        mode=CognitionMode.BOUNDED,
        model=MODEL_RENDER_ID,
    )
    messages = rendered["messages"]
    if not isinstance(messages, list) or len(messages) != 2:
        raise IdentityPriorApparatusError(
            "unexpected llama.cpp request message shape"
        )
    user = messages[1]
    if not isinstance(user, dict):
        raise IdentityPriorApparatusError(
            "unexpected llama.cpp user message shape"
        )
    content = user.get("content")
    if not isinstance(content, str):
        raise IdentityPriorApparatusError(
            "llama.cpp user message content must be text"
        )
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise IdentityPriorApparatusError(
            "llama.cpp user message must encode a JSON object"
        )
    return payload


def canonical_request_sha256(request: BoundedChoiceRequest) -> str:
    rendered = render_llama_cpp_request(
        request,
        mode=CognitionMode.BOUNDED,
        model=MODEL_RENDER_ID,
    )
    raw = json.dumps(
        rendered,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_preparation(preparation: IdentityPriorPreparation) -> None:
    if tuple(item.condition_id for item in preparation.conditions) != tuple(
        CONDITION_PRIORS
    ):
        raise IdentityPriorApparatusError(
            "condition bookkeeping order changed"
        )

    common_world = preparation.observation
    common_scenario = preparation.scenario
    requests = [item.request for item in preparation.conditions]
    identities = [item.cognition.identity for item in preparation.conditions]

    if not all(item.observation is common_world for item in preparation.conditions):
        raise IdentityPriorApparatusError(
            "conditions must share the same World fixture object"
        )
    if not all(item.scenario is common_scenario for item in preparation.conditions):
        raise IdentityPriorApparatusError(
            "conditions must share the same scenario fixture object"
        )

    for identity in identities:
        if identity.self_id != SELF_ID:
            raise IdentityPriorApparatusError(
                "all conditions must share the same self_id"
            )
        if identity.directives[: len(COMMON_DIRECTIVES)] != COMMON_DIRECTIVES:
            raise IdentityPriorApparatusError(
                "all conditions must share identical common directives"
            )
        if identity.provenance != identities[0].provenance:
            raise IdentityPriorApparatusError(
                "identity provenance must not encode condition identity"
            )

    expected_directives = tuple(
        (*COMMON_DIRECTIVES, *CONDITION_PRIORS[item.condition_id])
        for item in preparation.conditions
    )
    if tuple(identity.directives for identity in identities) != expected_directives:
        raise IdentityPriorApparatusError(
            "more than the declared Identity prior changed"
        )

    common = _request_without_identity(requests[0])
    for request in requests:
        if _request_without_identity(request) != common:
            raise IdentityPriorApparatusError(
                "non-Identity provider-visible request content changed"
            )
        if request.think_allowed is not True:
            raise IdentityPriorApparatusError(
                "THINK permission must be identical and enabled"
            )
        if request.soft_wall_time_budget_s is not None:
            raise IdentityPriorApparatusError(
                "soft cognition budget must remain identical and unset"
            )

        visible = provider_visible_user_payload(request)
        visible_text = json.dumps(
            visible,
            ensure_ascii=False,
            sort_keys=True,
        ).lower()
        for label in FORBIDDEN_MODEL_VISIBLE_LABELS:
            if label in visible_text:
                raise IdentityPriorApparatusError(
                    f"provider-visible condition leakage: {label}"
                )
        if "condition_id" in visible:
            raise IdentityPriorApparatusError(
                "condition bookkeeping leaked into provider payload"
            )

    if any(item.cognition.memories for item in preparation.conditions):
        raise IdentityPriorApparatusError(
            "preparation must not create durable Memory"
        )
    if any(
        item.pre_cognition_decision.skill is not ControlledSkill.FLEE
        for item in preparation.conditions
    ):
        raise IdentityPriorApparatusError(
            "Identity prior must not alter mandatory Skill admission"
        )


def preparation_report() -> dict[str, object]:
    preparation = build_preparation()
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "phase": "apparatus_preparation",
        "scientific_result": None,
        "scientific_spend": {
            "model_calls": 0,
            "minecraft_sessions": 0,
        },
        "future_spend_protocol": {
            "condition_order_by_block": [
                list(block) for block in PLANNED_CONDITION_ORDER
            ],
            "repetitions_per_condition": PLANNED_REPETITIONS_PER_CONDITION,
            "seed_randomness_policy": (
                "Do not add a seed field absent from the qualified adapter. "
                "Use current temperature=0, reasoning_effort=none, "
                "cache_prompt=false semantics and preserve backend variation "
                "as observed evidence."
            ),
            "bounded_max_output_tokens": BOUNDED_MAX_TOKENS,
            "think_max_output_tokens": THINK_MAX_TOKENS,
            "planned_llama_cpp_revision": PLANNED_LLAMA_CPP_REVISION,
            "planned_llama_cpp_build": PLANNED_LLAMA_CPP_BUILD,
            "planned_gguf_sha256": PLANNED_GGUF_SHA256,
            "world_reset_policy": (
                "Reset each condition to the exact frozen observation/scenario "
                "state before the first scientific invocation."
            ),
            "persistent_reset_policy": (
                "Begin each condition from its declared IdentitySpecification "
                "with zero retained Memories; retain experience only through "
                "the existing explicit integration seam after grounded success."
            ),
            "one_scientific_invocation": (
                "One condition from reset through first decision, grounded "
                "Action consequence, any declared explicit Memory integration, "
                "and one later decision."
            ),
            "failure_retry_policy": (
                "Preserve the failure; no hidden retry, replay, alternate "
                "condition, or same-run fixture tuning."
            ),
        },
        "common_state": {
            "available_skills": list(AVAILABLE_SKILLS),
            "action_capabilities": list(ACTION_CAPABILITIES),
            "world": _world_record(preparation.observation, preparation.scenario),
            "intent_id": INTENT_ID,
            "cognition": {
                "think_allowed": True,
                "soft_wall_time_budget_s": None,
                "bounded_max_output_tokens": BOUNDED_MAX_TOKENS,
                "think_max_output_tokens": THINK_MAX_TOKENS,
            },
        },
        "conditions": [
            _condition_record(item)
            for item in preparation.conditions
        ],
    }


def _condition_record(item: IdentityPriorCondition) -> dict[str, object]:
    return {
        "condition_id": item.condition_id,
        "identity_specification": {
            "self_id": item.cognition.identity.self_id,
            "directives": list(item.cognition.identity.directives),
            "provenance": {
                "source": item.cognition.identity.provenance.source,
                "reference": item.cognition.identity.provenance.reference,
            },
        },
        "provider_visible_request_sha256": canonical_request_sha256(item.request),
        "provider_visible_request": provider_visible_user_payload(item.request),
        "present_facts": _observation_record(item.observation),
        "available_skills": list(AVAILABLE_SKILLS),
        "selected_skill": item.pre_cognition_decision.skill.value,
        "cognition_path": ["BOUNDED", "THINK_IF_UNRESOLVED"],
        "provider_calls": 0,
        "input_tokens": None,
        "output_tokens": None,
        "latency_ns": None,
        "bound_destination": None,
        "issued_actions": [],
        "world_consequences": [],
        "durable_memory": [],
        "later_present": None,
        "later_decision": None,
        "interpretation_class": None,
    }


def _request_without_identity(
    request: BoundedChoiceRequest,
) -> dict[str, object]:
    payload = provider_visible_user_payload(request)
    context = payload.get("context")
    if not isinstance(context, list):
        raise IdentityPriorApparatusError(
            "provider-visible context must be a list"
        )
    return {
        **payload,
        "context": [
            datum
            for datum in context
            if not (
                isinstance(datum, dict)
                and datum.get("key") == IDENTITY_CONTEXT_KEY
            )
        ],
    }


def _world_record(
    observation: MineflayerObservation,
    scenario: ControlledScenario,
) -> dict[str, object]:
    return {
        "observation": _observation_record(observation),
        "hazard_entity_names": sorted(scenario.hazard_entity_names),
        "food_threshold": scenario.food_threshold,
        "destinations": [
            {
                "destination_id": destination.destination_id,
                "position": {
                    "x": destination.position.x,
                    "y": destination.position.y,
                    "z": destination.position.z,
                },
                "description": destination.description,
                "provenance": {
                    "source": destination.provenance.source,
                    "reference": destination.provenance.reference,
                },
            }
            for destination in scenario.destinations
        ],
    }


def _observation_record(
    observation: MineflayerObservation,
) -> dict[str, object]:
    snapshot = observation.snapshot
    return {
        "session_id": observation.session_id,
        "seq": observation.seq,
        "kind": observation.kind,
        "provenance": {
            "source": observation.provenance.source,
            "reference": observation.provenance.reference,
        },
        "health": snapshot.health,
        "food": snapshot.food,
        "oxygen_level": snapshot.oxygen_level,
        "position": {
            "x": snapshot.position.x,
            "y": snapshot.position.y,
            "z": snapshot.position.z,
        },
        "nearby_entities": [
            {
                "entity_id": entity.entity_id,
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
    }


def main() -> None:
    print(
        json.dumps(
            preparation_report(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
