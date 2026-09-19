import json

import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_PROVENANCE_SOURCE,
    MINEFLAYER_VERSION,
    MineflayerAdapterProtocolError,
    MineflayerAdapterStarted,
    MineflayerEffectResult,
    MineflayerLaunchConfig,
    MineflayerObservation,
    MineflayerStreamDecoder,
    encode_clear_controls,
    encode_consume_held,
    encode_equip_item,
    encode_look,
    encode_set_control,
    encode_shutdown,
    parse_mineflayer_line,
)


def started_line(
    *,
    session_id: str = "session-1",
    seq: int = 0,
    version: str = MINEFLAYER_VERSION,
) -> str:
    return json.dumps(
        {
            "type": "adapter_started",
            "session_id": session_id,
            "seq": seq,
            "mineflayer_version": version,
            "config": {
                "host": "127.0.0.1",
                "port": 25565,
                "username": "RelaySelf",
                "version": None,
            },
        }
    )


def observation_line(
    *,
    session_id: str = "session-1",
    seq: int = 1,
    kind: str = "health",
    time: object = ...,
) -> str:
    time_value = (
        {"time_of_day": 13000, "day": 2, "is_day": False}
        if time is ...
        else time
    )
    return json.dumps(
        {
            "type": "observation",
            "session_id": session_id,
            "seq": seq,
            "kind": kind,
            "snapshot": {
                "health": 12,
                "food": 7,
                "oxygen_level": 20,
                "position": {"x": 1.5, "y": 64, "z": -2.25},
                "time": time_value,
                "inventory": [
                    {"name": "bread", "count": 3, "slot": 10},
                ],
                "nearby_entities": [
                    {
                        "id": 2,
                        "name": "zombie",
                        "type": "mob",
                        "distance": 3.0,
                        "position": {"x": 4.5, "y": 64, "z": -2.25},
                    }
                ],
            },
        }
    )


def test_launch_config_builds_explicit_offline_bridge_argv_without_hidden_auth() -> None:
    config = MineflayerLaunchConfig(
        host="localhost",
        port=25566,
        username="Rin",
        version="1.21.8",
    )

    assert config.argv("/repo/adapters/mineflayer/bridge.mjs") == (
        "node",
        "/repo/adapters/mineflayer/bridge.mjs",
        "--host",
        "localhost",
        "--port",
        "25566",
        "--username",
        "Rin",
        "--version",
        "1.21.8",
    )


def test_stream_requires_started_seq_zero_then_preserves_survival_facts() -> None:
    decoder = MineflayerStreamDecoder()

    started = decoder.decode(started_line())
    observation = decoder.decode(observation_line())

    assert isinstance(started, MineflayerAdapterStarted)
    assert isinstance(observation, MineflayerObservation)
    assert started.mineflayer_version == MINEFLAYER_VERSION
    assert observation.snapshot.health == 12.0
    assert observation.snapshot.position.z == -2.25
    assert observation.snapshot.time is not None
    assert observation.snapshot.time.time_of_day == 13000
    assert observation.snapshot.time.is_day is False
    assert observation.snapshot.inventory[0].name == "bread"
    assert observation.snapshot.inventory[0].count == 3
    assert observation.snapshot.nearby_entities[0].name == "zombie"
    assert observation.snapshot.nearby_entities[0].entity_type == "mob"
    assert observation.snapshot.nearby_entities[0].distance == 3.0
    assert not hasattr(observation.snapshot.nearby_entities[0], "hostile")
    assert observation.provenance.source == MINEFLAYER_PROVENANCE_SOURCE
    assert observation.provenance.reference == "session-1:1"
    assert decoder.next_seq == 2


def test_snapshot_allows_time_to_be_null_before_server_time_sync() -> None:
    observation = parse_mineflayer_line(observation_line(time=None))

    assert isinstance(observation, MineflayerObservation)
    assert observation.snapshot.time is None


def test_stream_rejects_non_started_first_message_without_consuming_sequence() -> None:
    decoder = MineflayerStreamDecoder()

    with pytest.raises(
        MineflayerAdapterProtocolError,
        match="first bridge message",
    ):
        decoder.decode(observation_line(seq=0))

    assert decoder.session_id is None
    assert decoder.next_seq == 0


def test_stream_rejects_gap_and_session_change_without_advancing() -> None:
    decoder = MineflayerStreamDecoder()
    decoder.decode(started_line())

    with pytest.raises(MineflayerAdapterProtocolError, match="expected 1, got 2"):
        decoder.decode(observation_line(seq=2))

    assert decoder.next_seq == 1

    with pytest.raises(MineflayerAdapterProtocolError, match="session_id changed"):
        decoder.decode(observation_line(session_id="session-2", seq=1))

    assert decoder.next_seq == 1


def test_observation_schema_rejects_top_level_appraisal_injection() -> None:
    payload = json.loads(observation_line())
    payload["snapshot"]["danger"] = True

    with pytest.raises(MineflayerAdapterProtocolError, match="snapshot fields"):
        parse_mineflayer_line(json.dumps(payload))


def test_entity_fact_schema_rejects_hostile_appraisal_injection() -> None:
    payload = json.loads(observation_line())
    payload["snapshot"]["nearby_entities"][0]["hostile"] = True

    with pytest.raises(MineflayerAdapterProtocolError, match="nearby entity fields"):
        parse_mineflayer_line(json.dumps(payload))


def test_effect_result_preserves_action_identity_without_implying_skill_success() -> None:
    message = parse_mineflayer_line(
        json.dumps(
            {
                "type": "effect_result",
                "session_id": "session-1",
                "seq": 2,
                "action_id": "action-forward-on",
                "effect": "set_control",
                "result": "applied",
                "error": None,
            }
        )
    )

    assert isinstance(message, MineflayerEffectResult)
    assert message.action_id == "action-forward-on"
    assert message.result == "applied"
    assert not hasattr(message, "skill_state")
    assert not hasattr(message, "world_success")


def test_effect_result_rejected_requires_error_and_applied_forbids_error() -> None:
    with pytest.raises(MineflayerAdapterProtocolError, match="requires an error"):
        MineflayerEffectResult(
            session_id="s",
            seq=1,
            action_id="a",
            effect="set_control",
            result="rejected",
            error=None,
        )

    with pytest.raises(MineflayerAdapterProtocolError, match="cannot carry"):
        MineflayerEffectResult(
            session_id="s",
            seq=1,
            action_id="a",
            effect="set_control",
            result="applied",
            error="unexpected",
        )


def test_control_commands_are_closed_and_duration_is_not_part_of_adapter_effect() -> None:
    encoded = json.loads(
        encode_set_control(
            "action-1",
            control="forward",
            state=True,
        )
    )
    assert encoded == {
        "type": "effect",
        "action_id": "action-1",
        "effect": "set_control",
        "control": "forward",
        "state": True,
    }
    assert "duration" not in encoded

    with pytest.raises(MineflayerAdapterProtocolError, match="unsupported"):
        encode_set_control("action-2", control="teleport", state=True)


def test_food_commands_keep_item_selection_and_consumption_separate() -> None:
    assert json.loads(
        encode_equip_item(
            "action-equip",
            item_name="bread",
        )
    ) == {
        "type": "effect",
        "action_id": "action-equip",
        "effect": "equip_item",
        "item_name": "bread",
    }
    assert json.loads(encode_consume_held("action-consume")) == {
        "type": "effect",
        "action_id": "action-consume",
        "effect": "consume_held",
    }


def test_look_command_is_only_a_finite_heading_primitive() -> None:
    assert json.loads(
        encode_look(
            "action-look",
            yaw=1.5,
            pitch=-0.25,
        )
    ) == {
        "type": "effect",
        "action_id": "action-look",
        "effect": "look",
        "yaw": 1.5,
        "pitch": -0.25,
    }

    with pytest.raises(MineflayerAdapterProtocolError, match="finite number"):
        encode_look(
            "action-look-bad",
            yaw=float("inf"),
            pitch=0,
        )


def test_clear_and_shutdown_commands_are_minimal_jsonl() -> None:
    assert json.loads(encode_clear_controls("action-3")) == {
        "type": "effect",
        "action_id": "action-3",
        "effect": "clear_controls",
    }
    assert json.loads(encode_shutdown()) == {"type": "shutdown"}
    assert encode_clear_controls("action-3").endswith("\n")
    assert encode_shutdown().endswith("\n")


def test_protocol_rejects_unqualified_mineflayer_version() -> None:
    with pytest.raises(
        MineflayerAdapterProtocolError,
        match="unexpected Mineflayer version",
    ):
        parse_mineflayer_line(started_line(version="4.38.0"))


@pytest.mark.parametrize(
    "kind",
    [
        "spawn",
        "health",
        "time",
        "inventory",
        "entities",
        "move",
        "forcedMove",
        "death",
        "respawn",
    ],
)
def test_survival_observation_kinds_are_explicit(kind: str) -> None:
    message = parse_mineflayer_line(observation_line(kind=kind))
    assert isinstance(message, MineflayerObservation)
    assert message.kind == kind
