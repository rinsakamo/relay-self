from __future__ import annotations

import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MINEFLAYER_VERSION,
    MineflayerAdapterStarted,
    MineflayerEffectResult,
    MineflayerEntityFact,
    MineflayerLaunchConfig,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from observability.activity_summary import (
    ActivitySummaryError,
    reduce_activity,
    render_activity_markdown,
)
from relay_self.action import ActionLifecycle
from relay_self.intent import IntentCommitment, ReconsiderationDecision
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
)
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


def provenance(reference: str) -> Provenance:
    return Provenance(source="activity-summary-test", reference=reference)


def snapshot(
    x: float,
    *,
    health: float = 20,
    food: float = 20,
    entities: tuple[MineflayerEntityFact, ...] = (),
) -> MineflayerSnapshot:
    return MineflayerSnapshot(
        health=health,
        food=food,
        food_saturation=5,
        oxygen_level=20,
        position=MineflayerPosition(x=x, y=64, z=0),
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
    )


def observation(
    seq: int,
    kind: str,
    x: float,
    *,
    health: float = 20,
    food: float = 20,
    entities: tuple[MineflayerEntityFact, ...] = (),
) -> MineflayerObservation:
    return MineflayerObservation(
        session_id="session-1",
        seq=seq,
        kind=kind,
        snapshot=snapshot(
            x,
            health=health,
            food=food,
            entities=entities,
        ),
    )


def identity() -> IdentitySpecification:
    return IdentitySpecification(
        self_id="homunculus-1",
        directives=("observe the world",),
        provenance=provenance("identity"),
    )


def test_move_spam_is_compacted_into_bounded_spans_with_source_provenance() -> None:
    messages: list[object] = [
        MineflayerAdapterStarted(
            session_id="session-1",
            seq=0,
            mineflayer_version=MINEFLAYER_VERSION,
            config=MineflayerLaunchConfig(),
        ),
        observation(1, "spawn", 0.0),
    ]
    messages.extend(
        observation(seq, "move", (seq - 1) * 0.1)
        for seq in range(2, 22)
    )
    messages.append(
        observation(
            22,
            "health",
            2.0,
            health=14,
            food=17,
        )
    )
    messages.extend(
        observation(seq, "move", 2.0 + (seq - 22) * 0.1)
        for seq in range(23, 33)
    )
    messages.append(
        MineflayerEffectResult(
            session_id="session-1",
            seq=33,
            action_id="action-forward",
            effect="set_control",
            result="applied",
            error=None,
        )
    )

    digest = reduce_activity(mineflayer_messages=messages)

    assert digest.mineflayer_supplied is True
    assert digest.source_move_observation_count == 30
    assert len(digest.movement_spans) == 2
    assert digest.movement_spans[0].observation_count == 20
    assert digest.movement_spans[0].first_provenance.reference == "session-1:2"
    assert digest.movement_spans[0].last_provenance.reference == "session-1:21"
    assert digest.movement_spans[0].path_distance > 1.8
    assert digest.movement_spans[0].displacement > 1.8
    assert digest.movement_spans[1].observation_count == 10
    assert all(
        not (
            isinstance(message, MineflayerObservation)
            and message.kind == "move"
        )
        for message in digest.mineflayer_events
    )
    assert len(digest.mineflayer_events) == 4


def test_non_move_body_and_entity_facts_survive_without_appraisal_labels() -> None:
    zombie = MineflayerEntityFact(
        entity_id=7,
        name="zombie",
        entity_type="mob",
        distance=3.0,
        position=MineflayerPosition(x=3, y=64, z=0),
    )
    messages = [
        observation(
            1,
            "entities",
            0.0,
            health=9,
            food=6,
            entities=(zombie,),
        )
    ]

    digest = reduce_activity(mineflayer_messages=messages)
    rendered = render_activity_markdown(digest)

    assert "health=9" in rendered
    assert "food=6" in rendered
    assert "zombie" in rendered
    assert "distance=3" in rendered
    assert "session-1:1" in rendered
    assert "hostile" not in rendered.lower()
    assert "danger" not in rendered.lower()
    assert "fear" not in rendered.lower()


def test_existing_intent_skill_and_action_histories_are_projected_read_only() -> None:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-safe",
        objective="reach safety",
        at_ns=1,
        provenance=provenance("intent-commit"),
    )
    commitment.request_reconsideration(
        "intent-safe",
        reason="route changed",
        at_ns=2,
        provenance=provenance("intent-reconsider-request"),
    )
    commitment.reconsider(
        "intent-safe",
        decision=ReconsiderationDecision.CONTINUE,
        reason="objective still valid",
        at_ns=3,
        provenance=provenance("intent-continue"),
    )

    skill = SkillExecution.start(
        "skill-flee-1",
        skill_id="FLEE",
        intent_commitment=commitment,
        at_ns=4,
        provenance=provenance("skill-start"),
    )
    action = ActionLifecycle.propose(
        "action-forward",
        skill_execution=skill,
        intent_commitment=commitment,
        at_ns=5,
        provenance=provenance("action-propose"),
    )
    action = action.authorize(
        at_ns=6,
        provenance=provenance("action-authorize"),
        authority="fixture-policy",
    )
    action = action.issue(
        at_ns=7,
        deadline_ns=20,
        provenance=provenance("action-issue"),
    )
    action = action.record_outcome(
        at_ns=8,
        provenance=provenance("action-outcome"),
    )
    skill = skill.succeed(
        reason="safe location reached",
        at_ns=9,
        provenance=provenance("skill-success"),
    )

    before_intent_events = commitment.events
    before_skill_events = skill.events
    before_action_events = action.events

    digest = reduce_activity(
        intent_commitment=commitment,
        skill_executions=(skill,),
        action_lifecycles=(action,),
    )
    rendered = render_activity_markdown(digest)

    assert [item.event.kind.value for item in digest.intent_events] == [
        "committed",
        "reconsideration_requested",
        "reconsidered_continue",
    ]
    assert [item.event.state.value for item in digest.skill_events] == [
        "started",
        "succeeded",
    ]
    assert [item.event.state.value for item in digest.action_events] == [
        "proposed",
        "authorized",
        "issued",
        "outcome",
    ]
    assert "intent-safe" in rendered
    assert "reach safety" in rendered
    assert "FLEE" in rendered
    assert "action-forward" in rendered
    assert "fixture-policy" in rendered
    assert "action-outcome" in rendered

    assert commitment.events == before_intent_events
    assert skill.events == before_skill_events
    assert action.events == before_action_events


def test_persistent_memory_delta_reports_only_new_governed_memories() -> None:
    before = PersistentCognition(identity=identity())
    memory = Memory(
        memory_id="safe-cave",
        content="A cave was useful shelter in the observed episode.",
        source_provenance=Provenance(
            source="mineflayer",
            reference="session-1:44",
        ),
        integration_provenance=provenance("memory-integration"),
    )
    after = before.retain_memory(memory)

    digest = reduce_activity(
        persistent_before=before,
        persistent_after=after,
    )
    rendered = render_activity_markdown(digest)

    assert digest.persistent_cognition_supplied is True
    assert len(digest.retained_memories) == 1
    retained = digest.retained_memories[0]
    assert retained.memory_id == "safe-cave"
    assert retained.source_provenance.reference == "session-1:44"
    assert retained.integration_provenance.reference == "memory-integration"
    assert "safe-cave" in rendered
    assert "session-1:44" in rendered
    assert "memory-integration" in rendered


def test_missing_source_surfaces_render_as_not_supplied_not_as_negative_facts() -> None:
    digest = reduce_activity()
    rendered = render_activity_markdown(digest)

    assert digest.mineflayer_supplied is False
    assert digest.intent_supplied is False
    assert digest.skill_supplied is False
    assert digest.action_supplied is False
    assert digest.persistent_cognition_supplied is False
    assert rendered.count("not supplied") >= 5
    assert "no movement occurred" not in rendered.lower()
    assert "no skill occurred" not in rendered.lower()
    assert "no memory changed" not in rendered.lower()


def test_reducer_rejects_ambiguous_duplicate_skill_or_action_snapshots() -> None:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-safe",
        objective="reach safety",
        at_ns=1,
        provenance=provenance("intent"),
    )
    skill = SkillExecution.start(
        "skill-1",
        skill_id="FLEE",
        intent_commitment=commitment,
        at_ns=2,
        provenance=provenance("skill"),
    )
    action = ActionLifecycle.propose(
        "action-1",
        skill_execution=skill,
        intent_commitment=commitment,
        at_ns=3,
        provenance=provenance("action"),
    )

    with pytest.raises(ActivitySummaryError, match="duplicate Skill execution"):
        reduce_activity(skill_executions=(skill, skill))

    with pytest.raises(ActivitySummaryError, match="duplicate Action lifecycle"):
        reduce_activity(action_lifecycles=(action, action))


def test_persistent_delta_rejects_identity_change_as_outside_summary_scope() -> None:
    before = PersistentCognition(identity=identity())
    after = PersistentCognition(
        identity=IdentitySpecification(
            self_id="different-self",
            directives=("observe the world",),
            provenance=provenance("different-identity"),
        )
    )

    with pytest.raises(ActivitySummaryError, match="same identity"):
        reduce_activity(
            persistent_before=before,
            persistent_after=after,
        )
