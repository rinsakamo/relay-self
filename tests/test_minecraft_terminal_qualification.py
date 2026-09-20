from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from adapters.mineflayer.python_protocol import (
    MineflayerEntityFact,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from experiments.minecraft_terminal_qualification import (
    EXPECTED_MINECRAFT_SHA256,
    EXPECTED_MODEL_SHA256,
    TerminalQualificationError,
    make_recovery_present,
    memory_destination_id_from_content,
    parse_properties,
    receive_until,
    resource_hunger_commands,
    server_properties_text,
)
from experiments.reconsideration_admission import (
    ReconsiderationAdmissionKind,
    admit_reach_safety_reconsideration,
)
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import Memory
from relay_self.provenance import Provenance


def provenance(reference: str) -> Provenance:
    return Provenance(source="terminal-test", reference=reference)


def observation() -> MineflayerObservation:
    return MineflayerObservation(
        session_id="fresh-session",
        seq=41,
        kind="entities",
        snapshot=MineflayerSnapshot(
            health=20,
            food=18,
            oxygen_level=20,
            position=MineflayerPosition(x=4.5, y=4.0, z=-3.5),
            time=None,
            inventory=(),
            nearby_entities=(
                MineflayerEntityFact(
                    entity_id=7,
                    name="zombie",
                    entity_type="mob",
                    distance=3.0,
                    position=MineflayerPosition(x=7.5, y=4.0, z=-3.5),
                ),
            ),
        ),
    )


def test_server_properties_keep_controlled_world_contract() -> None:
    rendered = server_properties_text(25565)
    values = dict(
        line.split("=", 1)
        for line in rendered.splitlines()
        if line and not line.startswith("#")
    )

    assert values["server-port"] == "25565"
    assert values["online-mode"] == "false"
    assert values["level-type"] == "minecraft:flat"
    assert values["spawn-protection"] == "0"
    assert values["gamemode"] == "survival"
    assert values["pvp"] == "false"
    assert values["generate-structures"] == "false"
    assert values["spawn-animals"] == "false"
    assert values["spawn-monsters"] == "false"
    assert values["spawn-npcs"] == "false"


def test_recovery_projection_preserves_current_intent_and_admits_local_recovery() -> None:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-terminal-reach-safety",
        objective="reach safety",
        at_ns=1,
        provenance=provenance("intent"),
    )

    present = make_recovery_present(
        commitment=commitment,
        observation=observation(),
        blocked_destination="cave",
        recovery_destination="ridge",
    )
    admission, request = admit_reach_safety_reconsideration(
        present=present,
        commitment=commitment,
        material_change_key="route_open:cave",
        at_ns=2,
    )

    assert admission.kind is ReconsiderationAdmissionKind.LOCAL_RECOVERY
    assert request is None
    assert commitment.current_intent is not None
    assert commitment.current_intent.intent_id == "intent-terminal-reach-safety"


def test_memory_destination_is_read_without_promoting_memory_to_world_truth() -> None:
    memory = Memory(
        memory_id="flee-ridge",
        content=json.dumps(
            {
                "kind": "controlled_flee_destination_outcome",
                "destination_id": "ridge",
                "semantic_type": "Memory",
            }
        ),
        source_provenance=provenance("old-session:41"),
        integration_provenance=provenance("explicit-integration"),
    )

    assert memory_destination_id_from_content(memory) == "ridge"
    assert memory.source_provenance.reference == "old-session:41"
    assert memory.integration_provenance.reference == "explicit-integration"


def test_runtime_identity_constants_are_pinned_for_preflight() -> None:
    assert len(EXPECTED_MINECRAFT_SHA256) == 64
    assert len(EXPECTED_MODEL_SHA256) == 64
    assert EXPECTED_MINECRAFT_SHA256 != EXPECTED_MODEL_SHA256


def test_server_properties_accept_minecraft_java_property_escape(tmp_path) -> None:
    properties = tmp_path / "server.properties"
    properties.write_text("level-type=minecraft\\:flat\n", encoding="utf-8")

    assert parse_properties(properties)["level-type"] == "minecraft:flat"


@pytest.mark.parametrize("port", [0, 65536, -1])
def test_server_properties_reject_invalid_ports(port: int) -> None:
    with pytest.raises(Exception):
        server_properties_text(port)

def test_resource_intervention_uses_vanilla_hunger_not_player_nbt_mutation() -> None:
    apply_command, clear_command = resource_hunger_commands("RelaySelf")

    assert apply_command == "effect give RelaySelf minecraft:hunger 30 255 true"
    assert clear_command == "effect clear RelaySelf minecraft:hunger"
    assert "data modify" not in apply_command
    assert "data modify" not in clear_command


def test_receive_until_has_overall_deadline_despite_high_frequency_messages() -> None:
    class BusySession:
        async def receive(self):
            await asyncio.sleep(0)
            return observation()

    async def exercise() -> None:
        with pytest.raises(
            TerminalQualificationError,
            match="timed out waiting for required Mineflayer observation",
        ):
            await asyncio.wait_for(
                receive_until(
                    BusySession(),
                    lambda _observation: False,
                    timeout_s=0.01,
                ),
                timeout=0.2,
            )

    asyncio.run(exercise())


def test_launcher_stops_after_first_phase_failure_before_restart() -> None:
    launcher = Path("experiments/run_minecraft_terminal_qualification.sh").read_text(
        encoding="utf-8"
    )

    assert "set -euo pipefail" in launcher
    first = launcher.index("--phase first")
    restart = launcher.index("--phase restart")
    assert first < restart
    assert "||" not in launcher[first:restart]

