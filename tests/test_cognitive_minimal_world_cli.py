"""CLI grant and fake native bridge evidence: no real GPU/World calls in CI."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerAdapterStarted,
    MineflayerEffectResult,
    MineflayerEntityFact,
    MineflayerInventoryItem,
    MineflayerLaunchConfig,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from experiments import run_cognitive_minimal_world as cli
from experiments.cognitive_minimal_minecraft_dev import (
    NativeProbeFailure,
    read_correlated_native_probe,
)
from experiments.run_cognitive_minimal_world import parser, run
from relay_self.cognitive_minimal_dev import MinimalCognitionError
from relay_self.physical_action_journal import (
    PhysicalActionJournal,
    PhysicalJournalUnresolved,
)
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


def _observation(
    seq: int, *, kind: str, food: float = 7, bread_count: int = 2,
) -> MineflayerObservation:
    return MineflayerObservation(
        "session-1", seq, kind,
        MineflayerSnapshot(
            health=20, food=food, food_saturation=5,
            oxygen_level=None, position=MineflayerPosition(0, 64, 0),
            time=None, inventory=(MineflayerInventoryItem("bread", bread_count, 9),),
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
        self.probe_request_id = None

    async def receive(self):
        if not self.messages:
            raise RuntimeError("SIMULATED_CONNECTION_LOSS")
        result = self.messages.pop(0)
        if (isinstance(result, MineflayerObservation)
                and result.kind == "probe" and result.request_id is None):
            # Explicit mock server echoes the requested correlation ID.
            result = replace(result, request_id=self.probe_request_id)
        return result

    async def send_observe(self, request_id=None):
        self.probe_request_id = request_id
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
    assert receipt["correlated_probe_request_id"].startswith("cognitive-")
    assert receipt["correlated_probe_seq"] == 2
    assert receipt["action_outcome_count"] == 0
    assert receipt["initial_native_observation"]["native_source_ref"] == "session-1:1"
    assert receipt["initial_native_observation"]["observation"]["snapshot"]["food"] == 7
    assert len(receipt["native_probe_trace"]) == 1
    assert receipt["native_probe_trace"][0]["observation"]["request_id"] == (
        receipt["correlated_probe_request_id"]
    )
    assert receipt["initial_schema_frame"]["options"]
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
        _observation(5, kind="health", food=13, bread_count=1),
    ])
    receipt = asyncio.run(run(_granted_args(native=True)))
    assert receipt["status"] == "ACTION_ATTEMPTED"
    assert receipt["action_outcome_count"] == 2
    assert receipt["native_eat_consequence_attested"] is True
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
    assert audit["initial_native_observation"]["native_source_ref"] == "session-1:1"
    assert audit["initial_native_observation"]["observation"]["snapshot"]["food"] == 7
    assert audit["open_action_ids"] == [prefix + ":equip"]
    assert audit["open_action_states"] == ["issued"]
    assert audit["recorded_actions"] == [
        {"action_id": prefix + ":equip", "state": "issued"},
    ]
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
            return await super().receive()

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
    assert audit["recorded_actions"][0]["state"] == "issued"
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


def test_cli_disconnect_after_equip_ack_keeps_both_child_action_records(
    monkeypatch,
) -> None:
    prefix = "skill:eat:session-1:2"
    session = _inject_fake_runtime(monkeypatch, [
        _observation(1, kind="spawn"),
        _observation(2, kind="probe"),
        MineflayerEffectResult(
            "session-1", 3, prefix + ":equip", "equip_item", "applied", None,
        ),
        # No consume ACK: connection loss after the second ISSUE.
    ])
    with pytest.raises(cli.CognitiveWorldRunError) as exc:
        asyncio.run(run(_granted_args(native=True)))
    audit = exc.value.audit
    assert audit["open_action_ids"] == [prefix + ":consume"]
    assert audit["recorded_actions"] == [
        {"action_id": prefix + ":consume", "state": "issued"},
        {"action_id": prefix + ":equip", "state": "outcome"},
    ]
    assert audit["action_consequence"] == "UNKNOWN_POSSIBLY_ISSUED"
    assert audit["native_success_claim"] is False
    assert session.closed


def test_cli_two_correlated_native_probes_yield_nonissuing_s49_handoff(
    monkeypatch,
) -> None:
    session = _inject_fake_runtime(monkeypatch, [
        _observation(1, kind="spawn"),
        _observation(2, kind="probe"),
        _observation(3, kind="probe"),
    ])
    args = _granted_args(native=False)
    args.s49_readonly_shadow = True
    result = asyncio.run(run(args))
    assert result["status"] == "S49_SHADOW_READY"
    assert result["action_outcome_count"] == 0
    assert result["native_actions"] == []
    assert result["skill_final_state"] is None
    assert result["s49_shadow_refusal"] is None
    witness = result["s49_readonly_handoff"]
    assert witness["skill_id"] == "EAT"
    assert witness["target_ref"] == "inventory:bread"
    assert witness["self_id"] == "relay-self-cognitive-dev"
    assert witness["proposed_intent_id"] == "intent-cognitive-dev-1"
    assert witness["original_s49_intent_committed"] is False
    assert witness["original_s49_policy_verified"] is False
    assert witness["food_slot"] == 9
    assert witness["previous_probe_seq"] == 2
    assert witness["current_probe_seq"] == 3
    assert witness["previous_probe_request_id"] != witness["current_probe_request_id"]
    assert witness["original_s49_authorized"] is False
    assert witness["physical_action_issued"] is False
    assert result["correlated_probe_request_id"] == witness["current_probe_request_id"]
    assert result["correlated_probe_seq"] == 3
    assert session.sent == [("observe",), ("observe",)]
    assert session.closed


def test_cli_two_probe_shadow_target_lost_never_issues(
    monkeypatch,
) -> None:
    session = _inject_fake_runtime(monkeypatch, [
        _observation(1, kind="spawn"),
        _observation(2, kind="probe"),
        _observation(3, kind="probe", bread_count=0),
    ])
    args = _granted_args(native=False)
    args.s49_readonly_shadow = True
    result = asyncio.run(run(args))
    assert result["status"] == "REJECTED"
    assert result["s49_readonly_handoff"] is None
    assert result["native_actions"] == []
    assert session.sent == [("observe",), ("observe",)]
    assert session.closed


def test_cli_shadow_and_physical_issue_conflict_rejected_before_native(
    monkeypatch,
) -> None:
    launched = []

    async def fake_launch(*args, **kwargs):
        launched.append(True)
        raise AssertionError("should not launch")

    monkeypatch.setattr(cli.MineflayerProcessSession, "launch", fake_launch)
    args = _granted_args(native=True)
    args.s49_readonly_shadow = True
    with pytest.raises(MinimalCognitionError, match="cannot issue any physical Action"):
        asyncio.run(run(args))
    assert not launched


def test_cli_two_probe_s49_shadow_attack_stable_same_zombie_without_action(
    monkeypatch,
) -> None:
    def zombie_frame(seq: int, *, kind: str):
        native = _observation(seq, kind=kind, food=20)
        mob = MineflayerEntityFact(
            7, "zombie", "mob", 2.0, MineflayerPosition(2, 64, 0),
        )
        return replace(native, snapshot=replace(
            native.snapshot, inventory=(), nearby_entities=(mob,),
            nearby_entities_coverage=replace(
                native.snapshot.nearby_entities_coverage, candidate_count=1,
            ),
        ))

    session = _inject_fake_runtime(monkeypatch, [
        zombie_frame(1, kind="spawn"),
        zombie_frame(2, kind="probe"),
        zombie_frame(3, kind="probe"),
    ])
    args = _granted_args(native=False)
    args.hazard_name = ["zombie"]
    args.fight_max_distance = 4
    args.s49_readonly_shadow = True
    receipt = asyncio.run(run(args))
    witness = receipt["s49_readonly_handoff"]
    assert receipt["status"] == "S49_SHADOW_READY"
    assert witness["target_entity_id"] == 7
    assert witness["skill_id"] == "ATTACK"
    assert witness["self_id"] == "relay-self-cognitive-dev"
    assert witness["proposed_intent_id"] == "intent-cognitive-dev-1"
    assert witness["original_s49_intent_committed"] is False
    assert witness["original_s49_policy_verified"] is False
    assert witness["original_s49_authorized"] is False
    assert receipt["native_actions"] == []
    assert session.sent == [("observe",), ("observe",)]


def test_cli_two_probe_s49_shadow_movement_refused_without_issuer(
    monkeypatch,
) -> None:
    first = _observation(1, kind="spawn")
    before = _observation(2, kind="probe")
    after = _observation(3, kind="probe")
    after = replace(after, snapshot=replace(
        after.snapshot, position=replace(after.snapshot.position, z=.1),
    ))
    session = _inject_fake_runtime(monkeypatch, [first, before, after])
    args = _granted_args(native=False)
    args.s49_readonly_shadow = True
    receipt = asyncio.run(run(args))
    assert receipt["status"] == "S49_SHADOW_REJECTED"
    assert "steady" in receipt["s49_shadow_refusal"]
    assert receipt["s49_readonly_handoff"] is None
    assert receipt["native_actions"] == []
    assert session.sent == [("observe",), ("observe",)]


def test_no_target_s49_shadow_still_probes_without_inventing_l1_target(
    monkeypatch, tmp_path: Path,
) -> None:
    session = _inject_fake_runtime(monkeypatch, [
        _observation(1, kind="spawn", food=20, bread_count=0),
        _observation(2, kind="probe", food=20, bread_count=0),
        _observation(3, kind="probe", food=20, bread_count=0),
    ])
    args = _granted_args(native=False)
    args.s49_readonly_shadow = True
    args.evidence_path = str(tmp_path / "native-checkpoint.json")
    receipt = asyncio.run(run(args))
    assert receipt["status"] == "ESCALATE_L2"
    assert receipt["selection_reason"] == "L1 requested cognitive escalation"
    assert receipt["l1_choice_id"] == "1"
    assert receipt["initial_schema_frame"]["options"] == ()
    assert receipt["initial_schema_frame"]["goals"] == ()
    assert receipt["current_schema_frame"]["options"] == ()
    assert receipt["initial_native_observation"]["evidence_format"] == (
        "TYPED_DECODED_MINEFLAYER_OBSERVATION_V1"
    )
    assert receipt["initial_native_observation"]["observation"]["snapshot"]["food"] == 20
    assert receipt["initial_native_observation"]["observation"]["snapshot"][
        "inventory"
    ][0]["count"] == 0
    assert receipt["scenario_inputs"]["edible_item_names"] == ["bread"]
    assert len(receipt["native_probe_trace"]) == 2
    ids = [x["observation"]["request_id"] for x in receipt["native_probe_trace"]]
    assert all(x.startswith("cognitive-") for x in ids)
    assert ids[0] != ids[1]
    assert [x["observation"]["seq"] for x in receipt["native_probe_trace"]] == [2, 3]
    assert receipt["correlated_probe_request_id"] == ids[1]
    assert receipt["s49_readonly_handoff"] is None
    assert receipt["selected"] is None
    assert receipt["native_actions"] == []
    assert receipt["action_outcome_count"] == 0
    assert receipt["physical_fence"] == "NOT_ISSUED"
    assert session.sent == [("observe",), ("observe",)]
    assert session.closed
    # Direct run() leaves the early checkpoint in place until main() writes
    # the final outcome, so even interruption after L1 can leave native facts.
    saved = json.loads(Path(args.evidence_path).read_text())
    assert saved["stage"] == "INITIAL_NATIVE_OBSERVED_BEFORE_L1"
    assert saved["initial_native_observation"] == receipt["initial_native_observation"]


def test_no_target_without_shadow_keeps_original_no_probe_behavior(
    monkeypatch,
) -> None:
    session = _inject_fake_runtime(monkeypatch, [
        _observation(1, kind="spawn", food=20, bread_count=0),
    ])
    args = _granted_args(native=False)
    result = asyncio.run(run(args))
    assert result["status"] == "ESCALATE_L2"
    assert result["initial_schema_frame"]["options"] == ()
    assert result["initial_native_observation"]["observation"]["snapshot"]["food"] == 20
    assert result["native_probe_trace"] == []
    assert result["current_schema_frame"] is None
    assert result["s49_readonly_handoff"] is None
    assert result["correlated_probe_request_id"] is None
    assert session.sent == []


def test_initial_native_checkpoint_precedes_llm_and_survives_model_error(
    monkeypatch, tmp_path: Path,
) -> None:
    output = tmp_path / "run.json"
    session = FakeProcessSession([
        _observation(1, kind="spawn", food=19, bread_count=1),
    ])
    called: list[bool] = []

    class FailingProvider:
        def __init__(self, **kwargs):
            assert kwargs["model"] == "model-example"

        def __call__(self, request, *, mode):
            called.append(True)
            before = json.loads(output.read_text())
            assert before["stage"] == "INITIAL_NATIVE_OBSERVED_BEFORE_L1"
            assert before["native_success_claim"] is False
            assert before["physical_action_issued"] is False
            native = before["initial_native_observation"]
            assert native["native_source_ref"] == "session-1:1"
            assert native["observation"]["snapshot"]["food"] == 19
            assert native["observation"]["snapshot"]["inventory"][0]["count"] == 1
            raise RuntimeError("SIMULATED_MODEL_UNAVAILABLE")

    async def fake_launch(*args, **kwargs):
        return session

    monkeypatch.setattr(cli, "LlamaCppRelayProvider", FailingProvider)
    monkeypatch.setattr(cli.MineflayerProcessSession, "launch", fake_launch)
    monkeypatch.setattr("sys.argv", [
        "run_cognitive_minimal_world",
        "--grant-real-world", "--grant-real-llm",
        "--model", "model-example",
        "--edible-item", "bread",
        "--s49-readonly-shadow",
        "--evidence-path", str(output),
    ])
    assert cli.main() == 1
    final = json.loads(output.read_text())
    assert len(called) == 1
    assert "SIMULATED_MODEL_UNAVAILABLE" in final["error"]
    assert final["initial_native_observation"]["native_source_ref"] == "session-1:1"
    assert final["initial_native_observation"]["observation"]["snapshot"]["food"] == 19
    assert final["action_consequence"] == "NO_SUPERVISED_ISSUE_RECORDED"
    assert final["native_success_claim"] is False
    assert session.sent == []
    assert session.closed
    assert not output.with_name(output.name + ".tmp").exists()


def test_pre_l1_probe_uses_controlled_world_after_spawn_for_eat_positive(
    monkeypatch, tmp_path: Path,
) -> None:
    # Fake server state *changes between spawn and first correlated probe*.
    # That probe, not the early spawn snapshot, must seed real L1 selection.
    session = _inject_fake_runtime(monkeypatch, [
        _observation(1, kind="spawn", food=20, bread_count=0),
        _observation(2, kind="probe", food=7, bread_count=2),
        _observation(3, kind="probe", food=7, bread_count=2),
        _observation(4, kind="probe", food=7, bread_count=2),
    ])
    args = _granted_args(native=False)
    args.s49_readonly_shadow = True
    args.pre_l1_native_probe = True
    args.evidence_path = str(tmp_path / "pre-l1.json")

    receipt = asyncio.run(run(args))
    assert receipt["status"] == "S49_SHADOW_READY"
    assert receipt["l1_choice_id"] == "1"
    assert receipt["target_count"] == 1
    assert receipt["selected"]["target_ref"] == "inventory:bread"
    assert receipt["selected"]["skill_id"] == "EAT"
    assert receipt["spawn_native_observation"]["observation"]["kind"] == "spawn"
    assert receipt["spawn_native_observation"]["observation"]["snapshot"]["food"] == 20
    assert receipt["spawn_native_observation"]["observation"]["snapshot"][
        "inventory"
    ][0]["count"] == 0
    first = receipt["initial_native_observation"]["observation"]
    assert first["kind"] == "probe"
    assert first["request_id"].startswith("cognitive-pre-l1-")
    assert first["seq"] == 2
    assert first["snapshot"]["food"] == 7
    assert first["snapshot"]["inventory"][0]["count"] == 2
    assert receipt["pre_l1_probe_requested"] is True
    assert receipt["initial_schema_frame"]["options"][0]["target_ref"] == "inventory:bread"
    assert receipt["initial_schema_frame"]["goals"][0]["goal_id"] == "HUNGER_RELIEF"
    native = receipt["native_probe_trace"]
    assert len(native) == 2
    assert [x["observation"]["seq"] for x in native] == [3, 4]
    ids = [first["request_id"]] + [x["observation"]["request_id"] for x in native]
    assert len(set(ids)) == 3
    assert all(x is not None for x in ids)
    witness = receipt["s49_readonly_handoff"]
    assert witness["skill_id"] == "EAT"
    assert witness["food_item"] == "bread" and witness["food_slot"] == 9
    assert witness["previous_probe_seq"] == 3
    assert witness["current_probe_seq"] == 4
    assert not witness["original_s49_authorized"]
    assert not witness["physical_action_issued"]
    assert receipt["action_outcome_count"] == 0
    assert receipt["native_actions"] == []
    assert receipt["physical_fence"] == "NOT_ISSUED"
    assert session.sent == [("observe",), ("observe",), ("observe",)]
    assert session.closed
    # run() alone leaves the second checkpoint until main() writes final JSON.
    checkpoint = json.loads(Path(args.evidence_path).read_text())
    assert checkpoint["stage"] == "PRE_L1_NATIVE_PROBE_OBSERVED_BEFORE_L1"
    assert checkpoint["spawn_native_observation"] == receipt["spawn_native_observation"]
    assert checkpoint["initial_native_observation"] == receipt["initial_native_observation"]


def test_pre_l1_native_probe_rejected_without_read_only_shadow_before_launch(
    monkeypatch,
) -> None:
    launched = []

    async def forbidden_launch(*args, **kwargs):
        launched.append(True)
        raise AssertionError("must reject before any native session")

    monkeypatch.setattr(cli.MineflayerProcessSession, "launch", forbidden_launch)
    args = _granted_args(native=False)
    args.pre_l1_native_probe = True
    with pytest.raises(MinimalCognitionError, match="requires read-only shadow"):
        asyncio.run(run(args))
    args = _granted_args(native=True)
    args.pre_l1_native_probe = True
    with pytest.raises(MinimalCognitionError):
        asyncio.run(run(args))
    assert not launched


@pytest.mark.parametrize("value", ["0.1", "61", "-1", "nan", "inf"])
def test_pre_l1_world_setup_wait_refuses_missing_probe_or_invalid_interval(
    monkeypatch, value: str,
) -> None:
    launched = []

    async def forbidden_launch(*args, **kwargs):
        launched.append(True)
        raise AssertionError("must reject before any native session")

    monkeypatch.setattr(cli.MineflayerProcessSession, "launch", forbidden_launch)
    args = _granted_args(native=False)
    args.s49_readonly_shadow = True
    args.pre_l1_wait_s = float(value)
    if value != "0.1":
        args.pre_l1_native_probe = True
    with pytest.raises(MinimalCognitionError, match="pre-L1 World setup wait"):
        asyncio.run(run(args))
    assert not launched


def test_pre_l1_probe_rejects_foreign_session_before_llm_and_retains_spawn(
    monkeypatch,
) -> None:
    other = replace(
        _observation(2, kind="probe", food=7, bread_count=2),
        session_id="unexpected-session",
    )
    session = _inject_fake_runtime(monkeypatch, [
        _observation(1, kind="spawn", food=20, bread_count=0),
        other,
    ])
    args = _granted_args(native=False)
    args.s49_readonly_shadow = True
    args.pre_l1_native_probe = True
    with pytest.raises(cli.CognitiveWorldRunError) as exc:
        asyncio.run(run(args))
    audit = exc.value.audit
    assert "World session changed" in audit["error"]
    assert audit["initial_native_observation"]["native_source_ref"] == "session-1:1"
    assert audit["spawn_native_observation"]["native_source_ref"] == "session-1:1"
    assert audit["recorded_actions"] == []
    assert audit["native_success_claim"] is False
    assert session.sent == [("observe",)]
    assert session.closed


def test_pre_l1_observe_drains_more_than_32_queued_passive_events_before_eat(
    monkeypatch,
) -> None:
    # Model a 30-second local setup wait that buffered >32 native events.
    # Transport may see move/inventory messages before its own probe response.
    initial = _observation(1, kind="spawn", food=20, bread_count=0)
    queued = [
        _observation(seq, kind="move", food=20, bread_count=0)
        for seq in range(2, 53)
    ]
    session = _inject_fake_runtime(monkeypatch, [
        initial, *queued,
        _observation(53, kind="probe", food=7, bread_count=2),
        _observation(54, kind="probe", food=7, bread_count=2),
        _observation(55, kind="probe", food=7, bread_count=2),
    ])
    args = _granted_args(native=False)
    args.s49_readonly_shadow = True
    args.pre_l1_native_probe = True
    receipt = asyncio.run(run(args))
    assert receipt["status"] == "S49_SHADOW_READY"
    assert receipt["initial_native_observation"]["observation"]["seq"] == 53
    assert receipt["selected"]["target_ref"] == "inventory:bread"
    assert receipt["s49_readonly_handoff"]["food_slot"] == 9
    diag = receipt["pre_l1_probe_diagnostics"]
    assert diag["response_matched"] is True
    assert diag["terminal_reason"] == "MATCHED"
    assert diag["max_messages"] == 4096
    assert diag["received_count"] == 52
    assert diag["last_received_seq"] == 53
    assert diag["event_kind_counts"] == {
        "observation:move": 51, "observation:probe": 1,
    }
    assert diag["last_observed_snapshot"]["snapshot"]["food"] == 7
    assert diag["first_events"][0]["seq"] == 2
    assert diag["first_events"][0]["session_id"] == "session-1"
    assert diag["last_events"][-1]["seq"] == 53
    assert receipt["native_actions"] == []
    assert receipt["action_outcome_count"] == 0
    assert session.sent == [("observe",), ("observe",), ("observe",)]


def test_strict_post_l1_horizon_does_not_expand_for_backlog() -> None:
    # Existing post-L1 limit is intentionally not changed by pre-L1 catchup.
    initial = _observation(1, kind="spawn", food=20, bread_count=0)
    queued = [
        _observation(seq, kind="move", food=20, bread_count=0)
        for seq in range(2, 40)
    ]
    session = FakeProcessSession(queued)
    report: dict[str, object] = {}
    cfg = cli.ControlledScenario(
        hazard_entity_names=frozenset(),
        food_threshold=10,
        edible_item_names=("bread",),
        destinations=(),
        evidence_timeout_s=1,
        max_evidence_messages=32,
    )
    with pytest.raises(NativeProbeFailure, match="bounded event horizon") as exc:
        asyncio.run(read_correlated_native_probe(
            session, initial, cfg, request_id="strict-probe",
            diagnostics=report,
        ))
    assert report["request_id"] == "strict-probe"
    assert report["received_count"] == 32
    assert report["max_messages"] == 32
    assert report["last_received_seq"] == 33
    assert report["event_kind_counts"] == {"observation:move": 32}
    assert report["response_matched"] is False
    assert report["terminal_reason"] == "no qualified probe within bounded event horizon"
    assert exc.value.diagnostics["first_events"][0]["seq"] == 2
    assert exc.value.diagnostics["last_events"][-1]["seq"] == 33
    assert session.sent == [("observe",)]


def test_pre_l1_probe_failure_preserves_request_id_and_buffered_event_types(
    monkeypatch,
) -> None:
    session = _inject_fake_runtime(monkeypatch, [
        _observation(1, kind="spawn", food=20, bread_count=0),
        _observation(2, kind="inventory", food=7, bread_count=2),
        _observation(3, kind="move", food=7, bread_count=2),
        # No qualified echo; native receive ends inside bounded horizon.
    ])
    args = _granted_args(native=False)
    args.s49_readonly_shadow = True
    args.pre_l1_native_probe = True
    with pytest.raises(cli.CognitiveWorldRunError) as exc:
        asyncio.run(run(args))
    audit = exc.value.audit
    diag = audit["pre_l1_probe_diagnostics"]
    assert "native stream failed before correlated probe" in audit["error"]
    assert diag["request_id"].startswith("cognitive-pre-l1-")
    assert diag["send_completed"] is True
    assert diag["received_count"] == 2
    assert diag["last_received_seq"] == 3
    assert diag["receive_error_class"] == "RuntimeError"
    assert diag["receive_error"] == "SIMULATED_CONNECTION_LOSS"
    assert diag["event_kind_counts"] == {
        "observation:inventory": 1, "observation:move": 1,
    }
    assert diag["last_observed_snapshot"]["snapshot"]["food"] == 7
    assert diag["last_observed_snapshot"]["snapshot"]["inventory"][0]["count"] == 2
    assert diag["response_matched"] is False
    assert audit["initial_native_observation"]["observation"]["seq"] == 1
    assert audit["action_consequence"] == "NO_SUPERVISED_ISSUE_RECORDED"
    assert audit["recorded_actions"] == []
    assert session.sent == [("observe",)]
    assert session.closed


class FakePhysicalProcessSession(FakeProcessSession, MineflayerProcessSession):
    """CLI-complete scripted DEV transport; never spawns a Minecraft process."""

    def __init__(self, *, fail_at: str | None = None):
        super().__init__([_observation(1, kind="spawn", food=20, bread_count=0)])
        self._started = MineflayerAdapterStarted(
            "session-1", 0, "4.39.0", MineflayerLaunchConfig(),
        )
        self.fail_at = fail_at
        self.observation_no = 0
        self.first_wal_status = None
        self.wal_path: Path | None = None

    @property
    def process_returncode(self):
        return None

    async def send_observe(self, request_id=None):
        self.observation_no += 1
        self.sent.append(("observe", request_id))
        if self.observation_no <= 3:
            # pre-L1 then two post-L1 source-qualified *World* observations.
            no_target = self.fail_at == "no_target"
            stale_target = self.fail_at == "stale_target" and self.observation_no == 3
            self.messages.append(replace(
                _observation(
                    self.observation_no + 1, kind="probe",
                    food=20 if no_target else 7,
                    bread_count=0 if no_target or stale_target else 2,
                ),
                request_id=request_id,
            ))
        else:
            if self.fail_at == "after_probe":
                return
            self.messages.append(replace(
                _observation(7, kind="probe", food=13, bread_count=1),
                request_id=request_id,
            ))

    async def send_equip_item(self, action_id, *, item_name):
        assert self.wal_path is not None
        raw = json.loads(self.wal_path.read_text())
        self.first_wal_status = raw["body"]["actions"][-1]["status"]
        self.sent.append(("equip_item", action_id, item_name))
        if self.fail_at == "equip":
            return
        self.messages.append(MineflayerEffectResult(
            "session-1", 5, action_id, "equip_item", "applied", None,
        ))

    async def send_consume_held(self, action_id):
        self.sent.append(("consume_held", action_id))
        if self.fail_at == "consume":
            return
        self.messages.append(MineflayerEffectResult(
            "session-1", 6, action_id, "consume_held", "applied", None,
        ))


def _physical_args(tmp_path, *, create=True):
    args = [
        "--grant-real-world", "--grant-real-llm",
        "--model", "model-example", "--llama-timeout-s", "1.5",
        "--edible-item", "bread",
        "--physical-eat-dev", "--physical-journal-path",
        str(tmp_path / "owned-physical-wal.json"),
        "--acknowledge-physical-dev-unverified-grants",
        "--physical-propose-authority", "DEV_OPERATOR_PROPOSE",
        "--physical-issue-authority", "DEV_OPERATOR_ISSUE",
        "--pre-l1-native-probe",
    ]
    if create:
        args.append("--physical-create-journal")
    return parser().parse_args(args)


def _inject_physical_transport(monkeypatch, session):
    async def fake_launch(*args, **kwargs):
        return session

    monkeypatch.setattr(cli, "LlamaCppRelayProvider", FakeProvider)
    monkeypatch.setattr(cli.MineflayerProcessSession, "launch", fake_launch)


def test_cli_real_shaped_l1_eat_to_exact_one_fsynced_physical_parent(
    monkeypatch, tmp_path,
):
    session = FakePhysicalProcessSession()
    args = _physical_args(tmp_path)
    session.wal_path = Path(args.physical_journal_path)
    _inject_physical_transport(monkeypatch, session)
    result = asyncio.run(run(args))
    assert result["status"] == "NATIVE_EAT_OUTCOME_DEV_ONLY"
    assert result["existing_issuer"].endswith("issue_eat_from_selected_l1_dev")
    assert result["l1_choice_id"] == "1"
    assert result["initial_native_observation"]["observation"]["snapshot"]["food"] == 7
    assert result["selected"]["target_ref"] == "inventory:bread"
    assert result["physical_fence"] == "PREISSUE_WAL_EAT_DEV"
    assert result["physical_eat_dev_selected"] is True
    assert result["physical_journal_unresolved"] is False
    assert result["physical_journal_records"][0]["status"] == "NATIVE_EAT_OUTCOME"
    assert result["action_outcome_count"] == 1
    assert result["native_eat_consequence_attested"] is True
    assert result["skill_final_state"] == "started"  # Not semantic Skill success.
    assert session.first_wal_status == "PREPARED_UNRESOLVED"
    assert len(result["native_actions"]) == 1
    assert result["native_actions"][0]["state"] == "outcome"
    assert len(result["native_effect_receipts"]) == 2
    assert [x["effect"] for x in result["native_effect_receipts"]] == [
        "equip_item", "consume_held",
    ]
    assert len([x for x in session.sent if x[0] == "equip_item"]) == 1
    assert len([x for x in session.sent if x[0] == "consume_held"]) == 1
    assert [x["observation"]["seq"] for x in result["native_probe_trace"]] == [3, 4]
    assert session.closed


@pytest.mark.parametrize("where", ["equip", "consume", "after_probe"])
def test_cli_ambiguous_native_failure_is_persisted_unknown_and_no_replay(
    monkeypatch, tmp_path, where,
):
    session = FakePhysicalProcessSession(fail_at=where)
    args = _physical_args(tmp_path)
    session.wal_path = Path(args.physical_journal_path)
    _inject_physical_transport(monkeypatch, session)
    with pytest.raises(cli.CognitiveWorldRunError) as exc:
        asyncio.run(run(args))
    audit = exc.value.audit
    assert audit["physical_eat_dev_selected"] is True
    assert audit["action_consequence"] == "UNKNOWN_POSSIBLY_ISSUED"
    assert audit["physical_journal_unresolved"] is True
    assert audit["physical_journal_records"][0]["status"] == "PREPARED_UNRESOLVED"
    assert audit["recorded_actions"][0]["state"] == "unknown"
    assert session.first_wal_status == "PREPARED_UNRESOLVED"
    assert session.closed
    restored = PhysicalActionJournal.restore(args.physical_journal_path,
                                             self_id=args.self_id)
    with pytest.raises(PhysicalJournalUnresolved):
        restored.require_clear()

    # A NEW process / same Self must refuse even before launching a World.
    second = FakePhysicalProcessSession()
    second.wal_path = session.wal_path
    _inject_physical_transport(monkeypatch, second)
    second_args = _physical_args(tmp_path, create=False)
    with pytest.raises(cli.CognitiveWorldRunError) as new_exc:
        asyncio.run(run(second_args))
    assert "STOP/UNKNOWN" in new_exc.value.audit["error"]
    assert new_exc.value.audit["physical_journal_unresolved"] is True
    assert second.sent == []
    assert not second.closed  # No session started on the failed restart.


@pytest.mark.parametrize("badflag", [
    "--execute-native",
    "--s49-readonly-shadow",
])
def test_cli_refuses_concurrent_or_implicit_physical_issuers_before_launch(
    monkeypatch, tmp_path, badflag,
):
    called = []

    async def forbidden_launch(*args, **kwargs):
        called.append(True)
        raise AssertionError("World must not be reached")

    monkeypatch.setattr(cli.MineflayerProcessSession, "launch", forbidden_launch)
    args = _physical_args(tmp_path)
    if badflag == "--execute-native":
        args.execute_native = True
    else:
        args.s49_readonly_shadow = True
    with pytest.raises(MinimalCognitionError):
        asyncio.run(run(args))
    assert called == []


def test_cli_uninitialized_journal_is_not_created_without_explicit_flag(
    monkeypatch, tmp_path,
):
    called = []

    async def forbidden_launch(*args, **kwargs):
        called.append(True)
        raise AssertionError("World must not be reached")

    monkeypatch.setattr(cli.MineflayerProcessSession, "launch", forbidden_launch)
    args = _physical_args(tmp_path, create=False)
    with pytest.raises(cli.CognitiveWorldRunError) as exc:
        asyncio.run(run(args))
    assert "existing regular journal required" in exc.value.audit["error"]
    assert called == []
    assert not Path(args.physical_journal_path).exists()


def test_cli_journal_created_once_must_not_be_reset(monkeypatch, tmp_path):
    called = []

    async def forbidden_launch(*args, **kwargs):
        called.append(True)
        raise RuntimeError("simulated launch refusal")

    monkeypatch.setattr(cli.MineflayerProcessSession, "launch", forbidden_launch)
    args = _physical_args(tmp_path)
    with pytest.raises(cli.CognitiveWorldRunError):
        asyncio.run(run(args))
    assert Path(args.physical_journal_path).exists()
    with pytest.raises(cli.CognitiveWorldRunError) as exc:
        asyncio.run(run(args))
    assert "existing physical history" in exc.value.audit["error"]
    assert called == [True]


@pytest.mark.parametrize("no_issue_case", ["no_target", "stale_target"])
def test_cli_l1_no_target_or_stale_eat_does_not_create_physical_reservation(
    monkeypatch, tmp_path, no_issue_case,
):
    session = FakePhysicalProcessSession(fail_at=no_issue_case)
    args = _physical_args(tmp_path)
    session.wal_path = Path(args.physical_journal_path)
    _inject_physical_transport(monkeypatch, session)
    result = asyncio.run(run(args))
    assert result["status"] in ("ESCALATE_L2", "S49_SHADOW_REJECTED", "REJECTED")
    assert result["physical_eat_parent_action_id"] is None
    assert result["physical_fence"] == "WAL_READY_NO_ISSUE"
    assert result["physical_journal_unresolved"] is False
    assert result["physical_journal_records"] == []
    assert result["native_actions"] == []
    assert result["native_effect_receipts"] == []
    assert result["action_outcome_count"] == 0
    assert not any(x[0] == "equip_item" for x in session.sent)
    assert not any(x[0] == "consume_held" for x in session.sent)
    assert session.closed


def test_cli_selected_l1_eat_via_l0_ir_still_uses_single_existing_wal_issuer(
    monkeypatch, tmp_path,
):
    """Scripted native/LLM transport; not a real World or Skill qualification."""
    session = FakePhysicalProcessSession()
    args = _physical_args(tmp_path)
    args.l0_skill_ir_dev = True
    session.wal_path = Path(args.physical_journal_path)
    _inject_physical_transport(monkeypatch, session)
    result = asyncio.run(run(args))

    assert result["l1_choice_id"] == "1"
    assert result["selected"]["skill_id"] == "EAT"
    assert result["selected"]["target_ref"] == "inventory:bread"
    assert result["l0_skill_ir_dev_selected"] is True
    assert result["existing_issuer"].endswith("issue_eat_from_selected_l1_dev")
    assert result["status"] == "NATIVE_EAT_OUTCOME_DEV_ONLY"
    assert result["l0_skill_ir_terminal_candidate_only"] is True
    trace = result["l0_skill_ir_trace"]
    assert [item["status"] for item in trace] == [
        "PROPOSE_ACTION", "AWAIT_ACTION", "ADVANCED", "TERMINAL_CANDIDATE",
    ]
    assert trace[0]["capability_ref"] == "EAT"
    assert trace[0]["action_id"] == result["physical_eat_parent_action_id"]
    assert trace[0]["action_id"].endswith("-l0-1")
    assert result["action_outcome_count"] == 1
    assert result["skill_final_state"] == "started"
    assert result["native_eat_consequence_attested"] is True
    assert result["physical_journal_unresolved"] is False
    assert result["physical_journal_records"][-1]["status"] == "NATIVE_EAT_OUTCOME"
    assert session.first_wal_status == "PREPARED_UNRESOLVED"
    assert len([x for x in session.sent if x[0] == "equip_item"]) == 1
    assert len([x for x in session.sent if x[0] == "consume_held"]) == 1
    assert len(result["native_actions"]) == 1
    assert session.closed


@pytest.mark.parametrize("case", ["no_target", "stale_target"])
def test_cli_l0_ir_cannot_override_l1_missing_or_stale_food(
    monkeypatch, tmp_path, case,
):
    session = FakePhysicalProcessSession(fail_at=case)
    args = _physical_args(tmp_path)
    args.l0_skill_ir_dev = True
    session.wal_path = Path(args.physical_journal_path)
    _inject_physical_transport(monkeypatch, session)
    result = asyncio.run(run(args))
    assert result["l0_skill_ir_dev_selected"] is True
    assert result["l0_skill_ir_trace"] == []
    assert result["physical_eat_parent_action_id"] is None
    assert result["action_outcome_count"] == 0
    assert result["physical_journal_records"] == []
    assert not any(x[0] == "equip_item" for x in session.sent)
    assert session.closed


@pytest.mark.parametrize("failed_effect", ["equip", "consume", "after_probe"])
def test_cli_l0_ir_ambiguous_native_effect_keeps_wal_stop(
    monkeypatch, tmp_path, failed_effect,
):
    session = FakePhysicalProcessSession(fail_at=failed_effect)
    args = _physical_args(tmp_path)
    args.l0_skill_ir_dev = True
    session.wal_path = Path(args.physical_journal_path)
    _inject_physical_transport(monkeypatch, session)
    with pytest.raises(cli.CognitiveWorldRunError) as raised:
        asyncio.run(run(args))
    audit = raised.value.audit
    assert audit["l0_skill_ir_dev_selected"] is True
    assert audit["physical_journal_unresolved"] is True
    assert audit["physical_journal_records"][-1]["status"] == "PREPARED_UNRESOLVED"
    assert audit["action_consequence"] == "UNKNOWN_POSSIBLY_ISSUED"
    assert session.first_wal_status == "PREPARED_UNRESOLVED"
    assert session.closed
    resumed = PhysicalActionJournal.restore(
        args.physical_journal_path, self_id=args.self_id,
    )
    with pytest.raises(PhysicalJournalUnresolved):
        resumed.require_clear()


@pytest.mark.parametrize("mode", [
    "none", "legacy", "shadow",
])
def test_cli_l0_ir_requires_single_wal_owned_eat_mode_before_world_launch(
    monkeypatch, tmp_path, mode,
):
    launched = []

    async def forbidden_launch(*args, **kwargs):
        launched.append(True)
        raise AssertionError("no World should launch")

    monkeypatch.setattr(cli.MineflayerProcessSession, "launch", forbidden_launch)
    args = _physical_args(tmp_path)
    args.l0_skill_ir_dev = True
    if mode == "none":
        args.physical_eat_dev = False
    elif mode == "legacy":
        args.execute_native = True
    else:
        args.s49_readonly_shadow = True
    with pytest.raises(MinimalCognitionError):
        asyncio.run(run(args))
    assert launched == []
