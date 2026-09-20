import asyncio
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer.python_protocol import (
    MineflayerEntityFact,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from experiments import identity_prior_trajectory_transaction as transaction
from experiments.controlled_minecraft_vertical import ControlledSkill
from experiments.identity_prior_trajectory import build_candidate_world
from experiments.identity_prior_trajectory_transaction import (
    FIRST_REQUEST_ID,
    LATER_REQUEST_ID,
    IdentityPriorTransactionError,
    InvocationResult,
    ResetEvidence,
    build_later_request,
    classify,
    condition_sequence,
    decide_from_predeclared_request,
    live_scenario,
    transaction_plan,
)
from relay_self.persistent_cognition import Memory
from relay_self.provenance import Provenance
from relay_self.relay_engine import ProviderDecision, RelayEngine


def _provenance(reference: str) -> Provenance:
    return Provenance(source="test", reference=reference)


def _memory(destination_id: str = "route-42") -> Memory:
    anchor = _reset_anchor()
    destination_z = anchor.z + (10 if destination_id == "route-42" else -10)
    return Memory(
        memory_id="first-grounded",
        content=json.dumps(
            {
                "kind": "controlled_flee_destination_outcome",
                "destination_id": destination_id,
                "destination_position": {
                    "x": anchor.x,
                    "y": anchor.y,
                    "z": destination_z,
                },
                "observed_outcome": "progress_toward_destination",
                "semantic_type": "Memory",
            },
            sort_keys=True,
        ),
        source_provenance=_provenance("first-world-consequence"),
        integration_provenance=_provenance("explicit-integration"),
    )


def test_transaction_plan_preserves_predeclared_order_and_zero_spend() -> None:
    plan = transaction_plan()

    assert plan["scientific_spend"] == {
        "model_calls": 0,
        "minecraft_sessions": 0,
    }
    assert condition_sequence() == (
        "A",
        "B",
        "C",
        "B",
        "C",
        "A",
        "C",
        "A",
        "B",
    )
    assert plan["condition_order"] == list(condition_sequence())
    assert plan["repetitions_per_condition"] == 3
    assert "experiment-authored" in plan["route_description_grounding"]
    assert "Mineflayer" in plan["route_description_grounding"]


def test_frozen_initial_provider_request_hashes_remain_unchanged() -> None:
    assert transaction_plan()["initial_request_sha256"] == {
        "A": "896f93292909ee3e7ef9f2287ad3605497bffefa292131b10ef11be05aac7676",
        "B": "b5125d2970b2bf8e0a4f32f4f7877d5d04813097f91a957d283e0dffaad3905a",
        "C": "8391ba19d214b3185412b38402f08385a768af1873202b787eaba5d42a82a8f9",
    }


def _reset_anchor() -> MineflayerPosition:
    return MineflayerPosition(x=10.5, y=-60.0, z=-0.5)


def _zombie(*, entity_id: int, distance: float) -> MineflayerEntityFact:
    anchor = _reset_anchor()
    return MineflayerEntityFact(
        entity_id=entity_id,
        name="zombie",
        entity_type="hostile",
        distance=distance,
        position=MineflayerPosition(
            x=anchor.x + distance,
            y=anchor.y,
            z=anchor.z,
        ),
    )


def _passive_entity(
    *,
    entity_id: int,
    distance: float,
) -> MineflayerEntityFact:
    anchor = _reset_anchor()
    return MineflayerEntityFact(
        entity_id=entity_id,
        name="cow",
        entity_type="animal",
        distance=distance,
        position=MineflayerPosition(
            x=anchor.x,
            y=anchor.y,
            z=anchor.z + distance,
        ),
    )


def _reset_observation(
    *,
    seq: int,
    kind: str,
    entities: tuple[MineflayerEntityFact, ...],
    position: MineflayerPosition | None = None,
) -> MineflayerObservation:
    return MineflayerObservation(
        session_id="reset-session",
        seq=seq,
        kind=kind,
        snapshot=MineflayerSnapshot(
            health=20,
            food=20,
            oxygen_level=None,
            position=position or _reset_anchor(),
            time=None,
            inventory=(),
            nearby_entities=entities,
        ),
    )


def _cleanup_sentinel() -> MineflayerPosition:
    anchor = _reset_anchor()
    return MineflayerPosition(
        x=anchor.x + transaction.RESET_CLEANUP_SENTINEL_OFFSET_X,
        y=anchor.y,
        z=anchor.z,
    )


def _summon_sentinel() -> MineflayerPosition:
    anchor = _reset_anchor()
    return MineflayerPosition(
        x=anchor.x,
        y=anchor.y,
        z=anchor.z + transaction.RESET_SUMMON_SENTINEL_OFFSET_Z,
    )


def _successful_reset_messages(
    *,
    queued_pre_summon_one: bool = False,
) -> tuple[MineflayerObservation, ...]:
    old = _zombie(entity_id=81, distance=4.0)
    controlled = _zombie(entity_id=161, distance=4.0)
    messages = [
        _reset_observation(seq=1, kind="spawn", entities=(old,)),
        _reset_observation(
            seq=2,
            kind="forcedMove",
            entities=(),
            position=_cleanup_sentinel(),
        ),
        _reset_observation(
            seq=3,
            kind="forcedMove",
            entities=(),
            position=_reset_anchor(),
        ),
    ]
    if queued_pre_summon_one:
        messages.append(
            _reset_observation(
                seq=4,
                kind="entities",
                entities=(controlled,),
                position=_reset_anchor(),
            )
        )
        next_seq = 5
    else:
        next_seq = 4
    messages.extend(
        (
            _reset_observation(
                seq=next_seq,
                kind="forcedMove",
                entities=(controlled,),
                position=_summon_sentinel(),
            ),
            _reset_observation(
                seq=next_seq + 1,
                kind="forcedMove",
                entities=(controlled,),
                position=_reset_anchor(),
            ),
        )
    )
    return tuple(messages)


class _ResetSession:
    def __init__(
        self,
        messages: tuple[MineflayerObservation, ...],
        *,
        repeat_last: bool = False,
    ) -> None:
        self._messages = messages
        self._repeat_last = repeat_last
        self._index = 0

    async def receive(self) -> MineflayerObservation:
        if self._index < len(self._messages):
            message = self._messages[self._index]
            self._index += 1
        elif self._repeat_last:
            message = self._messages[-1]
        else:
            raise AssertionError("reset consumed more observations than declared")
        await asyncio.sleep(0)
        return message


def _reset_args(*, timeout_s: float = 0.02) -> SimpleNamespace:
    return SimpleNamespace(
        evidence_timeout_s=timeout_s,
        server_control="unused-server-control",
        username="RelaySelf",
    )


def _run_reset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    session: _ResetSession,
) -> tuple[ResetEvidence, list[dict[str, object]]]:
    commands: list[dict[str, object]] = []

    async def record_command(**kwargs: object) -> None:
        commands.append(kwargs)

    monkeypatch.setattr(transaction, "write_server_command", record_command)
    result = asyncio.run(
        transaction.reset_live_world(
            session,
            args=_reset_args(),
            anchor=_reset_anchor(),
            evidence_path=tmp_path / "server-commands.jsonl",
        )
    )
    return result, commands


def test_reset_ignores_queued_zero_without_causal_watermark(
    monkeypatch,
    tmp_path: Path,
) -> None:
    stale = _zombie(entity_id=81, distance=4.0)
    session = _ResetSession(
        (
            _reset_observation(seq=1, kind="spawn", entities=(stale,)),
            _reset_observation(seq=2, kind="entities", entities=()),
            _reset_observation(seq=3, kind="entities", entities=(stale,)),
        ),
        repeat_last=True,
    )
    commands: list[dict[str, object]] = []

    async def record_command(**kwargs: object) -> None:
        commands.append(kwargs)

    monkeypatch.setattr(transaction, "write_server_command", record_command)

    with pytest.raises(IdentityPriorTransactionError, match="causal watermark"):
        asyncio.run(
            transaction.reset_live_world(
                session,
                args=_reset_args(timeout_s=0.005),
                anchor=_reset_anchor(),
                evidence_path=tmp_path / "server-commands.jsonl",
            )
        )

    assert len(commands) == 8
    assert "type=!minecraft:player" in str(commands[-1]["command"])
    assert not any("summon" in str(command["command"]) for command in commands)


def test_reset_requires_causal_zero_then_single_summon(
    monkeypatch,
    tmp_path: Path,
) -> None:
    session = _ResetSession(_successful_reset_messages())

    result, commands = _run_reset(monkeypatch, tmp_path, session)

    assert result.cleanup_server_zero_watermark.kind == "forcedMove"
    assert result.cleanup_server_zero_watermark.snapshot.position == (
        _cleanup_sentinel()
    )
    assert result.cleanup_zero_observation.snapshot.nearby_entities == ()
    assert result.summon_processed_watermark.kind == "forcedMove"
    assert result.summon_processed_watermark.snapshot.position == (
        _summon_sentinel()
    )
    assert len(result.matched_observation.snapshot.nearby_entities) == 1
    assert result.matched_observation.snapshot.position == _reset_anchor()
    assert result.matched_observation.seq > result.summon_processed_watermark.seq
    assert [command["command"] for command in commands].count(
        result.summon_command
    ) == 1
    assert "Invulnerable:1b" in result.summon_command
    assert "execute unless entity" in result.cleanup_server_zero_barrier_command
    assert len(commands) == 13


def test_reset_qualification_does_not_construct_provider(
    monkeypatch,
    tmp_path: Path,
) -> None:
    session = _ResetSession(_successful_reset_messages())

    def unexpected_provider(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("reset qualification must not construct a provider")

    monkeypatch.setattr(transaction, "provider_engine", unexpected_provider)
    result, _ = _run_reset(monkeypatch, tmp_path, session)

    assert len(result.matched_observation.snapshot.nearby_entities) == 1


def test_reset_ignores_pre_watermark_one_zombie_observation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    session = _ResetSession(
        _successful_reset_messages(queued_pre_summon_one=True)
    )

    result, _ = _run_reset(monkeypatch, tmp_path, session)

    assert result.summon_processed_watermark.seq == 5
    assert result.matched_observation.seq == 6


def test_reset_unexpected_passive_entity_does_not_qualify(
    monkeypatch,
    tmp_path: Path,
) -> None:
    controlled = _zombie(entity_id=161, distance=4.0)
    passive = _passive_entity(entity_id=170, distance=3.0)
    session = _ResetSession(
        (
            _reset_observation(seq=1, kind="spawn", entities=()),
            _reset_observation(
                seq=2,
                kind="forcedMove",
                entities=(),
                position=_cleanup_sentinel(),
            ),
            _reset_observation(
                seq=3,
                kind="forcedMove",
                entities=(),
                position=_reset_anchor(),
            ),
            _reset_observation(
                seq=4,
                kind="forcedMove",
                entities=(controlled,),
                position=_summon_sentinel(),
            ),
            _reset_observation(
                seq=5,
                kind="forcedMove",
                entities=(controlled, passive),
                position=_reset_anchor(),
            ),
        ),
        repeat_last=True,
    )

    commands: list[dict[str, object]] = []

    async def record_command(**kwargs: object) -> None:
        commands.append(kwargs)

    monkeypatch.setattr(transaction, "write_server_command", record_command)
    with pytest.raises(IdentityPriorTransactionError, match="one-zombie"):
        asyncio.run(
            transaction.reset_live_world(
                session,
                args=_reset_args(timeout_s=0.005),
                anchor=_reset_anchor(),
                evidence_path=tmp_path / "server-commands.jsonl",
            )
        )

    assert sum("summon" in str(item["command"]) for item in commands) == 1


def test_reset_duplicate_after_summon_does_not_succeed(
    monkeypatch,
    tmp_path: Path,
) -> None:
    first = _zombie(entity_id=161, distance=4.0)
    duplicate = (
        first,
        _zombie(entity_id=162, distance=4.05),
    )
    session = _ResetSession(
        (
            _reset_observation(seq=1, kind="spawn", entities=()),
            _reset_observation(
                seq=2,
                kind="forcedMove",
                entities=(),
                position=_cleanup_sentinel(),
            ),
            _reset_observation(
                seq=3,
                kind="forcedMove",
                entities=(),
                position=_reset_anchor(),
            ),
            _reset_observation(
                seq=4,
                kind="forcedMove",
                entities=duplicate,
                position=_summon_sentinel(),
            ),
            _reset_observation(
                seq=5,
                kind="forcedMove",
                entities=duplicate,
                position=_reset_anchor(),
            ),
        ),
        repeat_last=True,
    )

    commands: list[dict[str, object]] = []

    async def record_command(**kwargs: object) -> None:
        commands.append(kwargs)

    monkeypatch.setattr(transaction, "write_server_command", record_command)
    with pytest.raises(IdentityPriorTransactionError, match="one-zombie"):
        asyncio.run(
            transaction.reset_live_world(
                session,
                args=_reset_args(timeout_s=0.005),
                anchor=_reset_anchor(),
                evidence_path=tmp_path / "server-commands.jsonl",
            )
        )

    summon_commands = [
        command
        for command in commands
        if "summon" in str(command["command"])
    ]
    assert len(summon_commands) == 1
    assert len(commands) == 13


def test_live_scenario_maps_neutral_route_ids_to_live_geometry() -> None:
    observation, _ = build_candidate_world()
    scenario = live_scenario(observation, evidence_timeout_s=1.0)

    assert [item.destination_id for item in scenario.destinations] == [
        "route-17",
        "route-42",
    ]
    assert scenario.destinations[0].position.z == -10
    assert scenario.destinations[1].position.z == 10
    assert "safe" not in scenario.destinations[0].description.lower()
    assert "explor" not in scenario.destinations[1].description.lower()


def test_frozen_request_resolves_then_binds_to_live_destination() -> None:
    from experiments.identity_prior_trajectory_transaction import (
        _initial_request_for_condition,
    )

    observation, _ = build_candidate_world()
    scenario = live_scenario(observation, evidence_timeout_s=1.0)
    engine = RelayEngine(
        lambda request, *, mode: ProviderDecision.resolved("route-42")
    )

    decision = decide_from_predeclared_request(
        observation=observation,
        scenario=scenario,
        request=_initial_request_for_condition("B"),
        relay_engine=engine,
    )

    assert decision.skill is ControlledSkill.FLEE
    assert decision.destination is not None
    assert decision.destination.destination_id == "route-42"
    assert decision.cognition_result is not None
    assert decision.cognition_result.provider_call_count == 1


def test_later_request_projects_memory_into_same_local_frame() -> None:
    from experiments.identity_prior_trajectory_transaction import (
        _initial_request_for_condition,
    )

    anchor = _reset_anchor()
    observation = _reset_observation(
        seq=99,
        kind="move",
        entities=(),
        position=MineflayerPosition(
            x=anchor.x,
            y=anchor.y,
            z=anchor.z + 1,
        ),
    )
    memory = _memory()
    durable_before = memory.content

    request = build_later_request(
        identity_request=_initial_request_for_condition("C"),
        observation=observation,
        anchor=anchor,
        memory=memory,
    )

    assert request.request_id == LATER_REQUEST_ID
    assert FIRST_REQUEST_ID not in request.request_id
    by_key = {datum.key: datum for datum in request.context}
    assert "identity_specification" in by_key
    assert "memory:first-grounded-flee" in by_key

    memory_datum = by_key["memory:first-grounded-flee"]
    wrapper = json.loads(memory_datum.value_json)
    projected_memory = json.loads(wrapper["content"])

    assert projected_memory["destination_id"] == "route-42"
    assert projected_memory["destination_position"] == {
        "x": 0.0,
        "y": 64.0,
        "z": 10.0,
    }
    assert projected_memory["coordinate_frame"] == "matched-local"
    assert wrapper["source_provenance"] == {
        "source": memory.source_provenance.source,
        "reference": "matched-first-grounded-consequence",
    }
    assert memory.source_provenance.reference not in memory_datum.value_json
    assert memory_datum.provenance == memory.integration_provenance
    assert memory.content == durable_before
    assert json.loads(memory.content)["destination_position"]["y"] == anchor.y

    rendered = json.dumps(
        {
            datum.key: json.loads(datum.value_json)
            for datum in request.context
        },
        sort_keys=True,
    ).lower()
    assert "cautious" not in rendered
    assert "explorer" not in rendered
    assert "condition_id" not in rendered
    assert "route-42" in rendered


def _records(
    first_by_condition: dict[str, object],
    signature_by_condition: dict[str, object] | None = None,
    *,
    later_by_condition: dict[str, object] | None = None,
    later_signature_by_condition: dict[str, object] | None = None,
) -> list[InvocationResult]:
    initial_signatures = signature_by_condition or {
        "A": [{"mode": "bounded", "status": "resolved"}],
        "B": [{"mode": "bounded", "status": "resolved"}],
        "C": [{"mode": "bounded", "status": "resolved"}],
    }
    later_destinations = later_by_condition or first_by_condition
    later_signatures = later_signature_by_condition or initial_signatures
    result = []
    for block_index, block in enumerate(
        (("A", "B", "C"), ("B", "C", "A"), ("C", "A", "B"))
    ):
        for ordinal, condition_id in enumerate(block):
            first_destination = first_by_condition[condition_id]
            later_destination = later_destinations[condition_id]
            if first_destination is None:
                status = "completed_unresolved_before_action"
                later_destination = None
            elif later_destination is None:
                status = "completed_later_unresolved"
            else:
                status = "completed_grounded_trajectory"

            result.append(
                InvocationResult(
                    condition_id=condition_id,
                    block_index=block_index,
                    ordinal=ordinal,
                    report={
                        "status": status,
                        "first_bound_destination": first_destination,
                        "first_skill_run": (
                            {"skill_execution": {"state": "SUCCEEDED"}}
                            if first_destination is not None
                            else None
                        ),
                        "later_bound_destination": later_destination,
                        "later_skill_run": (
                            {"skill_execution": {"state": "SUCCEEDED"}}
                            if later_destination is not None
                            else None
                        ),
                        "initial_cognition_signature": initial_signatures[
                            condition_id
                        ],
                        "later_cognition_signature": later_signatures[
                            condition_id
                        ],
                    },
                )
            )
    return result


def test_classifier_requires_repeated_grounded_divergence_for_class_a() -> None:
    result = classify(
        _records(
            {
                "A": "route-17",
                "B": "route-42",
                "C": "route-17",
            }
        )
    )

    assert result["class"] == "A"
    assert result["all_grounded_trajectories"] is True


def test_classifier_rejects_non_grounded_skill_run_payload() -> None:
    records = _records(
        {
            "A": "route-17",
            "B": "route-42",
            "C": "route-17",
        }
    )
    records[0].report["first_skill_run"] = {
        "skill_execution": {"state": "FAILED"}
    }

    with pytest.raises(
        IdentityPriorTransactionError,
        match="grounded successful Action outcome",
    ):
        classify(records)


def test_partial_scientific_spend_is_conservative_lower_bound(
    tmp_path: Path,
) -> None:
    evidence_root = tmp_path
    invocation_root = (
        evidence_root
        / "invocations"
        / "block-01-01-A"
    )
    invocation_root.mkdir(parents=True)
    (invocation_root / "report.json").write_text(
        json.dumps(
            {
                "initial_cognition": {"provider_call_count": 2},
                "later_cognition": {"provider_call_count": 1},
            }
        ),
        encoding="utf-8",
    )
    (evidence_root / "mineflayer-anchor.jsonl").write_text(
        "{}\n",
        encoding="utf-8",
    )
    (evidence_root / "mineflayer-block-01-01-A.jsonl").write_text(
        "{}\n",
        encoding="utf-8",
    )

    spend = transaction._partial_scientific_spend(evidence_root)

    assert spend["minimum_recorded_model_provider_calls"] == 3
    assert spend["provider_call_count_is_lower_bound"] is True
    assert spend["minecraft_condition_sessions_started"] == 1
    assert spend["anchor_sessions_started"] == 1
    assert spend["checkpointed_invocation_reports"] == 1


def test_classifier_keeps_grand_null_when_conditions_match() -> None:
    result = classify(
        _records(
            {
                "A": "route-17",
                "B": "route-17",
                "C": "route-17",
            }
        )
    )

    assert result["class"] == "E"
    assert result["label"] == "no reproducible discriminating effect"


def test_classifier_treats_unresolved_vs_grounded_as_behavioral_divergence() -> None:
    result = classify(
        _records(
            {
                "A": None,
                "B": "route-17",
                "C": "route-42",
            }
        )
    )

    assert result["class"] == "A"
    assert result["first_embodied_divergence"] is True
    assert result["first_destination_by_condition"]["A"] == [None, None, None]
    assert result["stable_first_behavioral_outcome_by_condition"]["A"] == (
        "unresolved_no_action"
    )


def test_classifier_does_not_promote_within_condition_variability() -> None:
    records = _records(
        {
            "A": "route-17",
            "B": "route-42",
            "C": "route-17",
        }
    )
    changed = False
    for item in records:
        if item.condition_id == "B" and not changed:
            item.report["first_bound_destination"] = "route-17"
            item.report["later_bound_destination"] = "route-17"
            changed = True

    result = classify(records)

    assert result["class"] == "E"
    assert result["first_embodied_divergence"] is False
    assert result["later_embodied_divergence"] is False
    assert "variability" in result["rationale"].lower()


def test_classifier_reports_initial_cognition_only_when_behavior_matches() -> None:
    result = classify(
        _records(
            {
                "A": "route-17",
                "B": "route-17",
                "C": "route-17",
            },
            {
                "A": [{"mode": "bounded", "status": "resolved"}],
                "B": [
                    {"mode": "bounded", "status": "unresolved"},
                    {"mode": "think", "status": "resolved"},
                ],
                "C": [{"mode": "bounded", "status": "resolved"}],
            },
        )
    )

    assert result["class"] == "B"
    assert result["behaviorally_indistinguishable"] is True


def test_classifier_does_not_call_unstable_later_behavior_cognition_only() -> None:
    records = _records(
        {
            "A": "route-17",
            "B": "route-17",
            "C": "route-17",
        },
        {
            "A": [{"mode": "bounded", "status": "resolved"}],
            "B": [
                {"mode": "bounded", "status": "unresolved"},
                {"mode": "think", "status": "resolved"},
            ],
            "C": [{"mode": "bounded", "status": "resolved"}],
        },
    )
    changed = False
    for item in records:
        if item.condition_id == "B" and not changed:
            item.report["later_bound_destination"] = "route-42"
            changed = True

    result = classify(records)

    assert result["class"] == "E"
    assert result["behaviorally_indistinguishable"] is False


def test_classifier_reports_later_cognition_only_when_behavior_matches() -> None:
    result = classify(
        _records(
            {
                "A": "route-17",
                "B": "route-17",
                "C": "route-17",
            },
            later_signature_by_condition={
                "A": [{"mode": "bounded", "status": "resolved"}],
                "B": [
                    {"mode": "bounded", "status": "unresolved"},
                    {"mode": "think", "status": "resolved"},
                ],
                "C": [{"mode": "bounded", "status": "resolved"}],
            },
        )
    )

    assert result["class"] == "B"
    assert result["behaviorally_indistinguishable"] is True


def test_classifier_rejects_records_outside_predeclared_schedule() -> None:
    records = _records(
        {
            "A": "route-17",
            "B": "route-17",
            "C": "route-17",
        }
    )
    records[0], records[1] = records[1], records[0]

    with pytest.raises(
        IdentityPriorTransactionError,
        match="predeclared block/order schedule",
    ):
        classify(records)


def test_canonical_launcher_is_one_shot_and_blocks_before_run() -> None:
    launcher = Path(
        "experiments/run_identity_prior_trajectory_transaction.sh"
    ).read_text(encoding="utf-8")

    assert launcher.count("--phase run") == 1
    assert "--phase plan" in launcher
    assert "--phase preflight" in launcher
    assert launcher.count("capture_authority initial") == 1
    assert launcher.count("capture_authority final") == 1
    assert "QUALIFIED_FOR_NEW_TRANSACTION_SUBJECT" in launcher
    assert "NOT_REQUALIFIED" in launcher
    assert "subject_head:" in launcher
    assert "subject_tree:" in launcher
    assert "grep -q 'NO MATERIAL CONFLICT'" not in launcher
    assert "--phase first" not in launcher
    assert "--phase restart" not in launcher
    assert "same-run fixture tuning" not in launcher

    preflight_index = launcher.index("--phase preflight")
    final_gate_index = launcher.index("capture_authority final")
    run_index = launcher.index("--phase run")
    assert preflight_index < final_gate_index < run_index

    syntax = subprocess.run(
        [
            "bash",
            "-n",
            "experiments/run_identity_prior_trajectory_transaction.sh",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert syntax.returncode == 0, syntax.stderr
