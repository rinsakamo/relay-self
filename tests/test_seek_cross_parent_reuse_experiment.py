import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerEntityFact,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from experiments.seek_cross_parent_reuse import (
    SEEK_FOCUS,
    SeekExperimentError,
    SeekStatus,
    run_seek,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance


def provenance(reference: str) -> Provenance:
    return Provenance(
        source="seek-cross-parent-test",
        reference=reference,
    )


def entity(
    entity_id: int,
    name: str,
    *,
    entity_type: str,
    distance: float,
) -> MineflayerEntityFact:
    return MineflayerEntityFact(
        entity_id=entity_id,
        name=name,
        entity_type=entity_type,
        distance=distance,
        position=MineflayerPosition(
            x=distance,
            y=64,
            z=0,
        ),
    )


def observation(
    entities: tuple[MineflayerEntityFact, ...],
) -> MineflayerObservation:
    return MineflayerObservation(
        session_id="seek-session",
        seq=7,
        kind="entities",
        snapshot=MineflayerSnapshot(
            health=20,
            food=20,
            food_saturation=5,
            oxygen_level=20,
            position=MineflayerPosition(x=0, y=64, z=0),
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


def commitment(
    intent_id: str,
    objective: str,
) -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        intent_id,
        objective=objective,
        at_ns=1,
        provenance=provenance(f"intent:{intent_id}"),
    )
    return owner


def test_same_seek_operation_reuses_one_local_shape_across_parent_objectives() -> None:
    current = observation(
        (
            entity(
                7,
                "zombie",
                entity_type="mob",
                distance=3,
            ),
            entity(
                8,
                "Alex",
                entity_type="player",
                distance=5,
            ),
        )
    )
    hazard_parent = commitment(
        "intent-hazard",
        "locate the hazard before responding",
    )
    companion_parent = commitment(
        "intent-companion",
        "regroup with the companion",
    )

    hazard_seek = run_seek(
        current,
        intent_commitment=hazard_parent,
        target_name="zombie",
    )
    companion_seek = run_seek(
        current,
        intent_commitment=companion_parent,
        target_name="Alex",
    )

    assert hazard_seek.status is SeekStatus.FOUND
    assert companion_seek.status is SeekStatus.FOUND
    assert hazard_seek.surface.focus == SEEK_FOCUS
    assert companion_seek.surface.focus == SEEK_FOCUS
    assert hazard_seek.surface.binding.target_name == "zombie"
    assert companion_seek.surface.binding.target_name == "Alex"
    assert hazard_seek.surface.parent_intent_id == "intent-hazard"
    assert companion_seek.surface.parent_intent_id == "intent-companion"
    assert hazard_seek.matches[0].entity_id == 7
    assert companion_seek.matches[0].entity_id == 8
    assert hazard_seek.observation_provenance == current.provenance
    assert companion_seek.observation_provenance == current.provenance


def test_seek_target_binding_is_replaceable_without_rewriting_parent_intent() -> None:
    current = observation(
        (
            entity(
                7,
                "zombie",
                entity_type="mob",
                distance=3,
            ),
            entity(
                8,
                "Alex",
                entity_type="player",
                distance=5,
            ),
        )
    )
    parent = commitment(
        "intent-stable-parent",
        "inspect the current local situation",
    )
    before_events = parent.events
    before_intent = parent.current_intent

    first = run_seek(
        current,
        intent_commitment=parent,
        target_name="zombie",
    )
    second = run_seek(
        current,
        intent_commitment=parent,
        target_name="Alex",
    )

    assert first.matches[0].entity_id == 7
    assert second.matches[0].entity_id == 8
    assert first.surface.parent_intent_id == second.surface.parent_intent_id
    assert first.surface.parent_objective == second.surface.parent_objective
    assert parent.events == before_events
    assert parent.current_intent == before_intent


def test_missing_target_remains_unresolved_not_global_absence() -> None:
    current = observation(
        (
            entity(
                7,
                "zombie",
                entity_type="mob",
                distance=3,
            ),
        )
    )
    parent = commitment(
        "intent-find-companion",
        "regroup with the companion",
    )

    result = run_seek(
        current,
        intent_commitment=parent,
        target_name="Alex",
    )

    assert result.status is SeekStatus.UNRESOLVED
    assert result.matches == ()
    assert result.observation_provenance == current.provenance
    assert result.surface.observation.snapshot.nearby_entities_coverage.truncated is False


def test_seek_result_keeps_all_current_matches_without_inventing_a_winner() -> None:
    current = observation(
        (
            entity(
                7,
                "zombie",
                entity_type="mob",
                distance=5,
            ),
            entity(
                9,
                "zombie",
                entity_type="mob",
                distance=2,
            ),
        )
    )
    parent = commitment(
        "intent-find-hazard",
        "locate a hazard before responding",
    )

    result = run_seek(
        current,
        intent_commitment=parent,
        target_name="zombie",
    )

    assert result.status is SeekStatus.FOUND
    assert tuple(match.entity_id for match in result.matches) == (7, 9)


def test_seek_requires_an_existing_parent_current_intent() -> None:
    current = observation(())
    owner = IntentCommitment()

    with pytest.raises(
        SeekExperimentError,
        match="requires a Current Intent",
    ):
        run_seek(
            current,
            intent_commitment=owner,
            target_name="zombie",
        )


@pytest.mark.parametrize("target_name", ["", "   "])
def test_seek_rejects_empty_target_binding(target_name: str) -> None:
    current = observation(())
    parent = commitment(
        "intent-invalid-target",
        "locate something",
    )

    with pytest.raises(
        SeekExperimentError,
        match="target_name must be non-empty text",
    ):
        run_seek(
            current,
            intent_commitment=parent,
            target_name=target_name,
        )
