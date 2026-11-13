"""CLI grant and fake native bridge evidence: no real GPU/World calls in CI."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerEffectResult,
    MineflayerInventoryItem,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from experiments import run_cognitive_minimal_world as cli
from experiments.run_cognitive_minimal_world import parser, run
from relay_self.cognitive_minimal_dev import MinimalCognitionError
from relay_self.relay_engine import CognitionMode, ProviderDecision

# Exercise the entire CLI composition with source-typed fake messages.

def test_cli_default_is_shadow_and_refuses_all_real_ends_without_grants() -> None:
    args = parser().parse_args(["--model", "synthetic-model"])
    assert not args.execute_native
    assert not args.grant_real_llm and not args.grant_real_world
    with pytest.raises(MinimalCognitionError, match="both explicit"):
        asyncio.run(run(args))


def test_cli_native_execution_flag_is_not_a_grant_for_real_model_or_world() -> None:
    args = parser().parse_args(["--model", "synthetic-model", "--execute-native"])
    with pytest.raises(MinimalCognitionError, match="both explicit"):
        asyncio.run(run(args))


def _observation(seq: int, *, kind: str, food: float = 7) -> MineflayerObservation:
    return MineflayerObservation(
        "session-1", seq, kind,
        MineflayerSnapshot(
            health=20, food=food, food_saturation=5,
            oxygen_level=None, position=MineflayerPosition(0, 64, 0),
            time=None, inventory=(MineflayerInventoryItem("bread", 2, 9),),
            nearby_entities=(),
            nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
                source_scope=MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                max_distance=MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                max_entities=MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
                candidate_count=0, truncated=False,
            ),
        ),
    )


class FakeProvider:
    def __init__(self, **kwargs):
        assert kwargs["model"] == "model-example"
        assert kwargs["timeout"] == 1.5

    def __call__(self, request, *, mode):
        assert mode is CognitionMode.BOUNDED
        assert request.think_allowed is False
        return ProviderDecision.resolved("1")


class FakeProcessSession:
    def __init__(self, messages):
        self.messages = list(messages)
        self.sent: list[tuple[str, ...]] = []
        self.closed = False

    async def receive(self):
        if not self.messages:
            raise RuntimeError("SIMULATED_CONNECTION_LOSS")
        return self.messages.pop(0)

    async def send_observe(self):
        self.sent.append(("observe",))

    async def send_equip_item(self, action_id, *, item_name):
        self.sent.append(("equip_item", action_id, item_name))

    async def send_consume_held(self, action_id):
        self.sent.append(("consume_held", action_id))

    async def shutdown(self, *, timeout_s):
        self.closed = True

    async def terminate(self):
        self.closed = True


def _inject_fake_runtime(monkeypatch, messages) -> FakeProcessSession:
    fake_session = FakeProcessSession(messages)

    async def fake_launch(*args, **kwargs):
        return fake_session

    monkeypatch.setattr(cli, "LlamaCppRelayProvider", FakeProvider)
    monkeypatch.setattr(cli.MineflayerProcessSession, "launch", fake_launch)
    return fake_session


def _granted_args(*, native: bool):
    flags = [
        "--model", "model-example",
        "--grant-real-world", "--grant-real-llm",
        "--edible-item", "bread",
        "--llama-timeout-s", "1.5",
    ]
    if native:
        flags.extend(("--execute-native", "--acknowledge-unfenced-dev"))
    return parser().parse_args(flags)


def test_cli_fake_live_shadow_full_path_never_issues(monkeypatch) -> None:
    session = _inject_fake_runtime(monkeypatch, [
        _observation(1, kind="spawn"),
        _observation(2, kind="probe"),
    ])
    receipt = asyncio.run(run(_granted_args(native=False)))
    assert receipt["evidence_class"] == "REAL_LLM_AND_NATIVE_WORLD_DEV_ATTEMPT"
    # This is a MOCK runtime; evidence_class is a CLI label, not a test claim.
    assert receipt["status"] == "READY_NO_ISSUE"
    assert receipt["l1_choice_id"] == "1"
    assert receipt["action_outcome_count"] == 0
    assert session.sent == [("observe",)]
    assert session.closed


def test_cli_fake_native_eat_through_existing_issuer(monkeypatch) -> None:
    prefix = "skill:eat:session-1:2"
    session = _inject_fake_runtime(monkeypatch, [
        _observation(1, kind="spawn"),
        _observation(2, kind="probe"),
        MineflayerEffectResult(
            "session-1", 3, prefix + ":equip", "equip_item", "applied", None,
        ),
        MineflayerEffectResult(
            "session-1", 4, prefix + ":consume", "consume_held", "applied", None,
        ),
        _observation(5, kind="health", food=13),
    ])
    receipt = asyncio.run(run(_granted_args(native=True)))
    assert receipt["status"] == "ACTION_ATTEMPTED"
    assert receipt["action_outcome_count"] == 2
    assert receipt["physical_fence"] == "UNFENCED_DEV_ONLY"
    assert receipt["original_s49_preissue_wal"] == "NOT_CONNECTED"
    assert receipt["skill_final_state"] == "succeeded"
    assert receipt["intent_to_action_issued_ns"] is not None
    assert len(receipt["native_effect_receipts"]) == 2
    assert session.sent == [
        ("observe",),
        ("equip_item", prefix + ":equip", "bread"),
        ("consume_held", prefix + ":consume"),
    ]


def test_cli_disconnected_after_native_issue_preserves_unknown_action(
    monkeypatch,
) -> None:
    prefix = "skill:eat:session-1:2"
    session = _inject_fake_runtime(monkeypatch, [
        _observation(1, kind="spawn"), _observation(2, kind="probe"),
    ])
    with pytest.raises(cli.CognitiveWorldRunError) as exc:
        asyncio.run(run(_granted_args(native=True)))
    audit = exc.value.audit
    assert audit["native_success_claim"] is False
    assert audit["world_session"] == "session-1"
    assert audit["open_action_ids"] == [prefix + ":equip"]
    assert audit["open_action_states"] == ["issued"]
    assert audit["action_consequence"] == "UNKNOWN_POSSIBLY_ISSUED"
    assert "SIMULATED_CONNECTION_LOSS" in audit["error"]
    assert session.closed


def test_cli_atomic_failure_evidence_persists_unknown_state(
    monkeypatch, tmp_path: Path,
) -> None:
    output = tmp_path / "run-failed.json"
    audit = {
        "evidence_class": "DEV_FAILED_NOT_QUALIFIED",
        "error": "mock failure",
        "open_action_ids": ["action-under-test"],
        "action_consequence": "UNKNOWN_POSSIBLY_ISSUED",
        "native_success_claim": False,
    }

    async def failed_run(args):
        raise cli.CognitiveWorldRunError(audit)

    monkeypatch.setattr(cli, "run", failed_run)
    monkeypatch.setattr(
        "sys.argv",
        ["run_cognitive_minimal_world", "--model", "mock",
         "--evidence-path", str(output)],
    )
    assert cli.main() == 1
    assert json.loads(output.read_text()) == audit
    assert not output.with_name(output.name + ".tmp").exists()


def test_cli_task_cancel_after_native_issue_preserves_uncertainty(
    monkeypatch,
) -> None:
    class CancelledProcessSession(FakeProcessSession):
        async def receive(self):
            if not self.messages:
                raise asyncio.CancelledError("simulated cancelled native wait")
            return self.messages.pop(0)

    session = CancelledProcessSession([
        _observation(1, kind="spawn"),
        _observation(2, kind="probe"),
    ])

    async def fake_launch(*args, **kwargs):
        return session

    monkeypatch.setattr(cli, "LlamaCppRelayProvider", FakeProvider)
    monkeypatch.setattr(cli.MineflayerProcessSession, "launch", fake_launch)
    with pytest.raises(cli.CognitiveWorldRunError) as exc:
        asyncio.run(run(_granted_args(native=True)))
    audit = exc.value.audit
    assert audit["native_success_claim"] is False
    assert audit["action_consequence"] == "UNKNOWN_POSSIBLY_ISSUED"
    assert audit["open_action_ids"] == ["skill:eat:session-1:2:equip"]
    assert "CancelledError" in audit["error"]
    assert session.closed


def test_cli_refuses_native_without_unfenced_ack_before_any_connection(
    monkeypatch,
) -> None:
    called = []

    async def no_connection(*args, **kwargs):
        called.append("launched")
        raise AssertionError("should not launch")

    monkeypatch.setattr(cli.MineflayerProcessSession, "launch", no_connection)
    args = parser().parse_args([
        "--model", "mock", "--grant-real-world", "--grant-real-llm",
        "--execute-native",
    ])
    with pytest.raises(MinimalCognitionError, match="UNFENCED_DEV_ONLY"):
        asyncio.run(run(args))
    assert not called


def test_unfenced_ack_alone_does_not_authorize_world_execution() -> None:
    args = parser().parse_args([
        "--model", "mock", "--acknowledge-unfenced-dev", "--execute-native",
    ])
    with pytest.raises(MinimalCognitionError, match="both explicit"):
        asyncio.run(run(args))
