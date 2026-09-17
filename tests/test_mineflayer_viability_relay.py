import json

from experiments.mineflayer_viability_relay import (
    MINEFLAYER_REVISION,
    HurtSource,
    MineflayerEvent,
    MineflayerObservation,
    Vec3,
    build_ablation,
    compile_cognition_payload,
    health_gradient,
    respawn_trace,
)


def test_damage_and_fatal_health_loss_are_negative_without_extra_death_penalty() -> None:
    trace = respawn_trace()

    assert health_gradient(trace[0], trace[1]).delta == -8.0
    assert health_gradient(trace[1], trace[2]).delta == -12.0


def test_respawn_restores_health_without_hiding_respawn_event() -> None:
    trace = respawn_trace()
    gradient = health_gradient(trace[2], trace[3])
    payload = compile_cognition_payload(trace, include_gradient=True)

    assert gradient.delta == 20.0
    assert payload["frames"][3]["observation"]["events"] == ["respawn", "health"]


def test_food_and_oxygen_changes_do_not_change_first_health_only_gradient() -> None:
    previous = MineflayerObservation(
        tick=0,
        health=10.0,
        food=20.0,
        oxygen_level=20.0,
        position=Vec3(0.0, 64.0, 0.0),
    )
    current = MineflayerObservation(
        tick=1,
        health=10.0,
        food=0.0,
        oxygen_level=0.0,
        position=Vec3(0.0, 64.0, 0.0),
    )

    assert health_gradient(previous, current).delta == 0.0


def test_observations_only_condition_has_no_gradient() -> None:
    payload = compile_cognition_payload(respawn_trace(), include_gradient=False)

    assert all("valueGradient" not in frame for frame in payload["frames"])


def test_hurt_source_remains_observation_provenance() -> None:
    trace = respawn_trace()
    payload = compile_cognition_payload(trace, include_gradient=True)
    hurt_observation = payload["frames"][1]["observation"]
    gradient = payload["frames"][1]["valueGradient"]

    assert hurt_observation["hurtSource"]["entityId"] == 41
    assert gradient == {"tick": 1, "field": "bot.health", "delta": -8.0}


def test_entity_hurt_event_requires_a_source_and_source_requires_event() -> None:
    source = HurtSource(entity_id=7, position=Vec3(1.0, 64.0, 0.0))

    try:
        MineflayerObservation(
            tick=0,
            health=20.0,
            food=20.0,
            oxygen_level=20.0,
            position=Vec3(0.0, 64.0, 0.0),
            events=(MineflayerEvent.ENTITY_HURT,),
        )
    except ValueError as error:
        assert str(error) == "entityHurt event and hurt_source must appear together"
    else:
        raise AssertionError("expected missing hurt source to fail closed")

    try:
        MineflayerObservation(
            tick=0,
            health=20.0,
            food=20.0,
            oxygen_level=20.0,
            position=Vec3(0.0, 64.0, 0.0),
            hurt_source=source,
        )
    except ValueError as error:
        assert str(error) == "entityHurt event and hurt_source must appear together"
    else:
        raise AssertionError("expected ungrounded hurt source to fail closed")


def test_ablation_is_deterministic_and_pins_mineflayer_revision() -> None:
    first = build_ablation()
    second = build_ablation()

    assert first == second
    assert first["withHealthGradient"]["source"]["revision"] == MINEFLAYER_REVISION


def test_payload_does_not_hand_author_emotion_or_survival_labels() -> None:
    encoded = json.dumps(build_ablation()).lower()

    for label in ("fear", "danger", "safety", "hunger", "courage", "emotion"):
        assert label not in encoded
