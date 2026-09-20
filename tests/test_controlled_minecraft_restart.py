import asyncio
import json

import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerEffectResult,
    MineflayerEntityFact,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from experiments.controlled_minecraft_restart import (
    ControlledRestartError,
    choose_memory_matching_destination,
    memory_destination_id,
    retain_successful_flee_memory,
    save_restart_and_decide,
)
from experiments.controlled_minecraft_vertical import (
    ControlledDestination,
    ControlledScenario,
    decide_skill,
    execute_decision,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    ProviderDecision,
    RelayEngine,
)
from relay_self.skill import SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(
        source="controlled-restart-test",
        reference=reference,
    )


def destination(
    destination_id: str,
    x: float,
    z: float,
) -> ControlledDestination:
    return ControlledDestination(
        destination_id=destination_id,
        position=MineflayerPosition(x=x, y=64, z=z),
        description=f"controlled destination {destination_id}",
        provenance=provenance(f"destination:{destination_id}"),
    )


def first_scenario() -> ControlledScenario:
    return ControlledScenario(
        hazard_entity_names=frozenset({"zombie"}),
        food_threshold=10,
        edible_item_names=("bread",),
        destinations=(destination("cave", 10, 0),),
        flee_min_progress=0.25,
        evidence_timeout_s=1.0,
        max_evidence_messages=4,
    )


def later_scenario() -> ControlledScenario:
    return ControlledScenario(
        hazard_entity_names=frozenset({"zombie"}),
        food_threshold=10,
        edible_item_names=("bread",),
        destinations=(
            destination("cave", 10, 0),
            destination("ridge", 0, -10),
        ),
        flee_min_progress=0.25,
        evidence_timeout_s=1.0,
        max_evidence_messages=4,
    )


def zombie() -> MineflayerEntityFact:
    return MineflayerEntityFact(
        entity_id=7,
        name="zombie",
        entity_type="mob",
        distance=3,
        position=MineflayerPosition(x=3, y=64, z=0),
    )


def observation(
    session_id: str,
    seq: int,
    *,
    x: float = 0,
    z: float = 0,
    entities: tuple[MineflayerEntityFact, ...] = (),
) -> MineflayerObservation:
    return MineflayerObservation(
        session_id=session_id,
        seq=seq,
        kind="entities",
        snapshot=MineflayerSnapshot(
            health=20,
            food=20,
            food_saturation=5,
            oxygen_level=20,
            position=MineflayerPosition(x=x, y=64, z=z),
            time=None,
            inventory=(),
            nearby_entities=entities,
            nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
                source_scope=MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                max_distance=MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                max_entities=MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
                candidate_count=len(entities),
                truncated=False,
            ),
        ),
    )


def effect(
    seq: int,
    action_id: str,
    effect_name: str,
) -> MineflayerEffectResult:
    return MineflayerEffectResult(
        session_id="session-1",
        seq=seq,
        action_id=action_id,
        effect=effect_name,
        result="applied",
        error=None,
    )


def commitment() -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        "intent-survive",
        objective="survive controlled interval",
        at_ns=1,
        provenance=provenance("intent"),
    )
    return owner


def cognition() -> PersistentCognition:
    return PersistentCognition(
        identity=IdentitySpecification(
            self_id="homunculus-1",
            directives=("continue observing and surviving",),
            provenance=provenance("identity"),
        )
    )


class FakeSession:
    def __init__(self, messages) -> None:
        self.messages = list(messages)
        self.sent = []

    async def receive(self):
        if not self.messages:
            raise AssertionError("fake Mineflayer evidence exhausted")
        return self.messages.pop(0)

    async def send_equip_item(self, action_id, *, item_name):
        self.sent.append(("equip_item", action_id, item_name))

    async def send_consume_held(self, action_id):
        self.sent.append(("consume_held", action_id))

    async def send_look(self, action_id, *, yaw, pitch):
        self.sent.append(("look", action_id, yaw, pitch))

    async def send_set_control(self, action_id, *, control, state):
        self.sent.append(("set_control", action_id, control, state))

    async def send_clear_controls(self, action_id):
        self.sent.append(("clear_controls", action_id))


class MemoryAwareProvider:
    def __init__(self) -> None:
        self.requests = []
        self.modes = []

    def __call__(self, request, *, mode):
        self.requests.append(request)
        self.modes.append(mode)
        remembered = choose_memory_matching_destination(request)
        return ProviderDecision.resolved(remembered or "ridge")


def successful_flee_run():
    initial = observation(
        "session-1",
        1,
        entities=(zombie(),),
    )
    decision = decide_skill(
        initial,
        first_scenario(),
        intent_id="intent-survive",
    )
    prefix = "skill:flee:session-1:1"
    session = FakeSession(
        [
            effect(2, f"{prefix}:look", "look"),
            effect(3, f"{prefix}:forward", "set_control"),
            observation(
                "session-1",
                4,
                x=1.0,
                entities=(zombie(),),
            ),
            effect(5, f"{prefix}:stop", "clear_controls"),
        ]
    )
    result = asyncio.run(
        execute_decision(
            session,
            initial,
            first_scenario(),
            decision,
            intent_commitment=commitment(),
            supervisor=ActionSupervisor(),
        )
    )
    assert result is not None
    assert result.skill_execution.state is SkillState.SUCCEEDED
    return result


def test_successful_skill_does_not_persist_until_explicit_integration() -> None:
    before = cognition()
    run_result = successful_flee_run()

    assert before.memories == ()
    assert run_result.skill_execution.state is SkillState.SUCCEEDED

    after = retain_successful_flee_memory(
        before,
        run_result,
        integration_provenance=provenance("memory-accept"),
    )

    assert before.memories == ()
    assert len(after.memories) == 1
    memory = after.memories[0]
    assert memory.source_provenance.source == "mineflayer"
    assert memory.source_provenance.reference == "session-1:4"
    assert memory.integration_provenance.reference == "memory-accept"
    assert memory_destination_id(memory) == "cave"


def test_restart_preserves_identity_and_memory_changes_later_bounded_choice(
    tmp_path,
) -> None:
    before = cognition()
    run_result = successful_flee_run()
    later = observation(
        "session-2",
        1,
        entities=(zombie(),),
    )

    without_memory_provider = MemoryAwareProvider()
    without_memory = decide_skill(
        later,
        later_scenario(),
        intent_id="intent-survive-2",
        relay_engine=RelayEngine(without_memory_provider),
    )
    assert without_memory.destination.destination_id == "ridge"

    provider = MemoryAwareProvider()
    result = save_restart_and_decide(
        tmp_path / "persistent-cognition.json",
        before,
        run_result,
        later,
        later_scenario(),
        integration_provenance=provenance("memory-accept"),
        intent_id="intent-survive-2",
        relay_engine=RelayEngine(provider),
    )

    assert result.reloaded == result.integrated
    assert result.reloaded.identity == before.identity
    assert len(result.reloaded.memories) == 1
    assert result.later_decision.destination.destination_id == "cave"
    assert provider.modes == [CognitionMode.BOUNDED]

    request = provider.requests[0]
    current_entities = next(
        datum
        for datum in request.context
        if datum.key == "nearby_entities"
    )
    memory_datum = next(
        datum
        for datum in request.context
        if datum.key.startswith("memory:")
    )

    assert current_entities.provenance.reference == "session-2:1"
    assert memory_datum.provenance.reference == "memory-accept"

    wrapped_memory = json.loads(memory_datum.value_json)
    assert wrapped_memory["semantic_type"] == "Memory"
    assert wrapped_memory["source_provenance"] == {
        "source": "mineflayer",
        "reference": "session-1:4",
    }
    assert "session-1:4" in result.activity_markdown
    assert "memory-accept" in result.activity_markdown
    assert "Memory retained" in result.activity_markdown


def test_integration_rejects_non_flee_outcome() -> None:
    run_result = successful_flee_run()
    fake_eat_decision = run_result.decision.__class__(
        skill=run_result.decision.skill.__class__.EAT,
        reason="fixture",
        item_name="bread",
    )
    fake_eat_result = run_result.__class__(
        decision=fake_eat_decision,
        skill_execution=run_result.skill_execution,
        actions=run_result.actions,
        messages=run_result.messages,
    )

    with pytest.raises(
        ControlledRestartError,
        match="only the controlled FLEE",
    ):
        retain_successful_flee_memory(
            cognition(),
            fake_eat_result,
            integration_provenance=provenance("memory-accept"),
        )


def test_memory_reader_does_not_treat_arbitrary_text_as_destination_truth() -> None:
    after = retain_successful_flee_memory(
        cognition(),
        successful_flee_run(),
        integration_provenance=provenance("memory-accept"),
    )
    memory = after.memories[0]
    malformed = memory.__class__(
        memory_id="other",
        content="cave is definitely safe forever",
        source_provenance=memory.source_provenance,
        integration_provenance=memory.integration_provenance,
    )

    assert memory_destination_id(memory) == "cave"
    assert memory_destination_id(malformed) is None
