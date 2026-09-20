import asyncio
import math

import pytest

from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerEntityFact,
    MineflayerInventoryItem,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from experiments.controlled_minecraft_vertical import (
    ControlledDestination,
    ControlledScenario,
    ControlledScenarioError,
    ControlledSkill,
    decide_skill,
    execute_decision,
    yaw_to_destination,
)
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import Memory
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    DecisionStatus,
    ProviderDecision,
    RelayEngine,
)
from relay_self.skill import SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(
        source="controlled-minecraft-test",
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


def scenario(
    *,
    destinations: tuple[ControlledDestination, ...] | None = None,
    max_evidence_messages: int = 8,
    cognition_soft_wall_time_budget_s: float | None = None,
    cognition_think_allowed: bool = True,
) -> ControlledScenario:
    return ControlledScenario(
        hazard_entity_names=frozenset({"zombie"}),
        food_threshold=10,
        edible_item_names=("bread", "cooked_beef"),
        destinations=(
            (destination("cave", 10, 0),)
            if destinations is None
            else destinations
        ),
        flee_min_progress=0.25,
        evidence_timeout_s=1.0,
        max_evidence_messages=max_evidence_messages,
        cognition_soft_wall_time_budget_s=(
            cognition_soft_wall_time_budget_s
        ),
        cognition_think_allowed=cognition_think_allowed,
    )


def observation(
    *,
    seq: int = 1,
    x: float = 0,
    z: float = 0,
    food: float = 20,
    inventory: tuple[MineflayerInventoryItem, ...] = (),
    entities: tuple[MineflayerEntityFact, ...] = (),
) -> MineflayerObservation:
    return MineflayerObservation(
        session_id="session-1",
        seq=seq,
        kind="health",
        snapshot=MineflayerSnapshot(
            health=20,
            food=food,
            oxygen_level=20,
            position=MineflayerPosition(x=x, y=64, z=z),
            time=None,
            inventory=inventory,
            nearby_entities=entities,
        ),
    )


def zombie(*, distance: float = 3) -> MineflayerEntityFact:
    return MineflayerEntityFact(
        entity_id=7,
        name="zombie",
        entity_type="mob",
        distance=distance,
        position=MineflayerPosition(x=3, y=64, z=0),
    )


def bread() -> MineflayerInventoryItem:
    return MineflayerInventoryItem(
        name="bread",
        count=2,
        slot=9,
    )


def effect_result(
    seq: int,
    action_id: str,
    effect: str,
    *,
    result: str = "applied",
    error: str | None = None,
) -> MineflayerEffectResult:
    return MineflayerEffectResult(
        session_id="session-1",
        seq=seq,
        action_id=action_id,
        effect=effect,
        result=result,
        error=error,
    )


def current_intent() -> IntentCommitment:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-survive",
        objective="survive the controlled interval",
        at_ns=1,
        provenance=provenance("intent"),
    )
    return commitment


class RecordingProvider:
    def __init__(self, decisions: list[ProviderDecision]) -> None:
        self.decisions = list(decisions)
        self.requests = []
        self.modes = []

    def __call__(self, request, *, mode):
        self.requests.append(request)
        self.modes.append(mode)
        return self.decisions.pop(0)


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


def test_wait_is_healthy_inactivity_without_skill_start() -> None:
    obs = observation(food=20)

    decision = decide_skill(
        obs,
        scenario(),
        intent_id="intent-survive",
    )

    assert decision.skill is ControlledSkill.WAIT
    assert decision.resolved is True
    assert decision.item_name is None
    assert decision.destination is None


def test_low_food_with_configured_inventory_selects_eat() -> None:
    obs = observation(
        food=7,
        inventory=(bread(),),
    )

    decision = decide_skill(
        obs,
        scenario(),
        intent_id="intent-survive",
    )

    assert decision.skill is ControlledSkill.EAT
    assert decision.item_name == "bread"
    assert decision.destination is None


def test_configured_hazard_preempts_eat_without_adapter_threat_label() -> None:
    obs = observation(
        food=7,
        inventory=(bread(),),
        entities=(zombie(),),
    )

    decision = decide_skill(
        obs,
        scenario(),
        intent_id="intent-survive",
    )

    assert decision.skill is ControlledSkill.FLEE
    assert decision.destination.destination_id == "cave"
    assert decision.item_name is None


def test_multiple_flee_destinations_use_relay_engine_and_preserve_memory_type() -> None:
    obs = observation(
        entities=(zombie(),),
    )
    memory = Memory(
        memory_id="prior-cave",
        content="The cave provided shelter in a prior observed episode.",
        source_provenance=Provenance(
            source="mineflayer",
            reference="old-session:20",
        ),
        integration_provenance=provenance("memory-integration"),
    )
    provider = RecordingProvider(
        [ProviderDecision.resolved("ridge")]
    )
    engine = RelayEngine(provider)

    decision = decide_skill(
        obs,
        scenario(
            destinations=(
                destination("cave", 10, 0),
                destination("ridge", 0, -10),
            )
        ),
        intent_id="intent-survive",
        relay_engine=engine,
        retained_memories=(memory,),
    )

    assert decision.skill is ControlledSkill.FLEE
    assert decision.destination.destination_id == "ridge"
    assert decision.cognition_result is not None
    assert decision.cognition_result.escalated is False
    assert provider.modes == [CognitionMode.BOUNDED]
    request = provider.requests[0]
    memory_datum = next(
        datum
        for datum in request.context
        if datum.key == "memory:prior-cave"
    )
    assert '"semantic_type":"Memory"' in memory_datum.value_json
    assert memory_datum.provenance.reference == "memory-integration"
    current_entity_datum = next(
        datum
        for datum in request.context
        if datum.key == "nearby_entities"
    )
    assert current_entity_datum.provenance.reference == "session-1:1"


def test_unresolved_flee_cognition_does_not_start_execution_path() -> None:
    obs = observation(entities=(zombie(),))
    provider = RecordingProvider(
        [
            ProviderDecision.unresolved(reason="bounded uncertainty"),
            ProviderDecision.unresolved(reason="think uncertainty"),
        ]
    )

    decision = decide_skill(
        obs,
        scenario(
            destinations=(
                destination("cave", 10, 0),
                destination("ridge", 0, -10),
            )
        ),
        intent_id="intent-survive",
        relay_engine=RelayEngine(provider),
    )

    assert decision.skill is ControlledSkill.FLEE
    assert decision.destination is None
    assert decision.resolved is False
    assert decision.cognition_result.escalated is True


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (MineflayerPosition(x=10, y=64, z=0), 0.0),
        (MineflayerPosition(x=0, y=64, z=-10), math.pi / 2),
        (MineflayerPosition(x=-10, y=64, z=0), math.pi),
        (MineflayerPosition(x=0, y=64, z=10), -math.pi / 2),
    ],
)
def test_yaw_uses_mineflayer_due_east_counter_clockwise_convention(
    target: MineflayerPosition,
    expected: float,
) -> None:
    actual = yaw_to_destination(
        MineflayerPosition(x=0, y=64, z=0),
        target,
    )
    assert actual == pytest.approx(expected)


def test_yaw_rejects_same_horizontal_position() -> None:
    with pytest.raises(ControlledScenarioError, match="current horizontal"):
        yaw_to_destination(
            MineflayerPosition(x=0, y=64, z=0),
            MineflayerPosition(x=0, y=70, z=0),
        )


def test_eat_skill_requires_later_food_increase_not_only_effect_acks() -> None:
    obs = observation(
        food=7,
        inventory=(bread(),),
    )
    decision = decide_skill(
        obs,
        scenario(),
        intent_id="intent-survive",
    )
    prefix = "skill:eat:session-1:1"
    session = FakeSession(
        [
            effect_result(
                2,
                f"{prefix}:equip",
                "equip_item",
            ),
            effect_result(
                3,
                f"{prefix}:consume",
                "consume_held",
            ),
            observation(
                seq=4,
                food=13,
                inventory=(bread(),),
            ),
        ]
    )
    supervisor = ActionSupervisor()

    result = asyncio.run(
        execute_decision(
            session,
            obs,
            scenario(),
            decision,
            intent_commitment=current_intent(),
            supervisor=supervisor,
        )
    )

    assert result is not None
    assert result.skill_execution.state is SkillState.SUCCEEDED
    assert [action.state for action in result.actions] == [
        ActionState.OUTCOME,
        ActionState.OUTCOME,
    ]
    assert session.sent == [
        ("equip_item", f"{prefix}:equip", "bread"),
        ("consume_held", f"{prefix}:consume"),
    ]
    assert supervisor.open_actions == ()


def test_eat_ack_without_food_increase_fails_skill_not_action_outcome() -> None:
    obs = observation(
        food=7,
        inventory=(bread(),),
    )
    decision = decide_skill(
        obs,
        scenario(max_evidence_messages=1),
        intent_id="intent-survive",
    )
    prefix = "skill:eat:session-1:1"
    session = FakeSession(
        [
            effect_result(
                2,
                f"{prefix}:equip",
                "equip_item",
            ),
            effect_result(
                3,
                f"{prefix}:consume",
                "consume_held",
            ),
            observation(
                seq=4,
                food=7,
                inventory=(bread(),),
            ),
        ]
    )

    result = asyncio.run(
        execute_decision(
            session,
            obs,
            scenario(max_evidence_messages=1),
            decision,
            intent_commitment=current_intent(),
            supervisor=ActionSupervisor(),
        )
    )

    assert result is not None
    assert result.skill_execution.state is SkillState.FAILED
    assert all(
        action.state is ActionState.OUTCOME
        for action in result.actions
    )


def test_effect_result_wait_ignores_raw_message_count_until_deadline() -> None:
    obs = observation(entities=(zombie(),))
    decision = decide_skill(
        obs,
        scenario(max_evidence_messages=1),
        intent_id="intent-survive",
    )
    prefix = "skill:flee:session-1:1"
    noisy_messages = [
        MineflayerObservation(
            session_id="session-1",
            seq=seq,
            kind="move",
            snapshot=observation(seq=seq).snapshot,
        )
        for seq in range(2, 42)
    ]
    session = FakeSession(
        noisy_messages
        + [
            effect_result(
                42,
                f"{prefix}:look",
                "look",
            ),
            effect_result(
                43,
                f"{prefix}:forward",
                "set_control",
            ),
            observation(
                seq=44,
                x=1.0,
                entities=(zombie(distance=2),),
            ),
            effect_result(
                45,
                f"{prefix}:stop",
                "clear_controls",
            ),
        ]
    )

    result = asyncio.run(
        execute_decision(
            session,
            obs,
            scenario(max_evidence_messages=1),
            decision,
            intent_commitment=current_intent(),
            supervisor=ActionSupervisor(),
        )
    )

    assert result is not None
    assert result.skill_execution.state is SkillState.SUCCEEDED
    assert len(result.messages) >= 44


def test_flee_skill_looks_moves_and_requires_progress_toward_destination() -> None:
    obs = observation(entities=(zombie(),))
    decision = decide_skill(
        obs,
        scenario(),
        intent_id="intent-survive",
    )
    prefix = "skill:flee:session-1:1"
    session = FakeSession(
        [
            effect_result(
                2,
                f"{prefix}:look",
                "look",
            ),
            effect_result(
                3,
                f"{prefix}:forward",
                "set_control",
            ),
            observation(
                seq=4,
                x=1.0,
                entities=(zombie(distance=2),),
            ),
            effect_result(
                5,
                f"{prefix}:stop",
                "clear_controls",
            ),
        ]
    )
    supervisor = ActionSupervisor()

    result = asyncio.run(
        execute_decision(
            session,
            obs,
            scenario(),
            decision,
            intent_commitment=current_intent(),
            supervisor=supervisor,
        )
    )

    assert result is not None
    assert result.skill_execution.state is SkillState.SUCCEEDED
    assert [action.state for action in result.actions] == [
        ActionState.OUTCOME,
        ActionState.OUTCOME,
        ActionState.OUTCOME,
    ]
    assert session.sent[0][0:2] == (
        "look",
        f"{prefix}:look",
    )
    assert session.sent[0][2] == pytest.approx(0.0)
    assert session.sent[0][3] == 0.0
    assert session.sent[1] == (
        "set_control",
        f"{prefix}:forward",
        "forward",
        True,
    )
    assert session.sent[2] == (
        "clear_controls",
        f"{prefix}:stop",
    )
    assert supervisor.open_actions == ()


def test_flee_sideways_motion_does_not_count_as_destination_progress() -> None:
    obs = observation(entities=(zombie(),))
    decision = decide_skill(
        obs,
        scenario(max_evidence_messages=1),
        intent_id="intent-survive",
    )
    prefix = "skill:flee:session-1:1"
    session = FakeSession(
        [
            effect_result(
                2,
                f"{prefix}:look",
                "look",
            ),
            effect_result(
                3,
                f"{prefix}:forward",
                "set_control",
            ),
            observation(
                seq=4,
                x=0,
                z=1,
                entities=(zombie(),),
            ),
            effect_result(
                5,
                f"{prefix}:stop",
                "clear_controls",
            ),
        ]
    )

    result = asyncio.run(
        execute_decision(
            session,
            obs,
            scenario(max_evidence_messages=1),
            decision,
            intent_commitment=current_intent(),
            supervisor=ActionSupervisor(),
        )
    )

    assert result is not None
    assert result.skill_execution.state is SkillState.FAILED
    assert all(
        action.state is ActionState.OUTCOME
        for action in result.actions
    )


def test_wait_execution_creates_no_skill_or_action() -> None:
    obs = observation()
    decision = decide_skill(
        obs,
        scenario(),
        intent_id="intent-survive",
    )
    session = FakeSession([])

    result = asyncio.run(
        execute_decision(
            session,
            obs,
            scenario(),
            decision,
            intent_commitment=current_intent(),
            supervisor=ActionSupervisor(),
        )
    )

    assert result is None
    assert session.sent == []


def test_controlled_flee_passes_caller_owned_cognition_envelope() -> None:
    obs = observation(entities=(zombie(),))
    provider = RecordingProvider(
        [ProviderDecision.unresolved(reason="bounded uncertainty")]
    )

    decision = decide_skill(
        obs,
        scenario(
            destinations=(
                destination("cave", 10, 0),
                destination("ridge", 0, -10),
            ),
            cognition_soft_wall_time_budget_s=0.75,
            cognition_think_allowed=False,
        ),
        intent_id="intent-survive",
        relay_engine=RelayEngine(provider),
    )

    assert decision.cognition_result is not None
    assert decision.cognition_result.status is DecisionStatus.UNRESOLVED
    request = provider.requests[0]
    assert request.soft_wall_time_budget_s == 0.75
    assert request.think_allowed is False
    assert provider.modes == [CognitionMode.BOUNDED]
