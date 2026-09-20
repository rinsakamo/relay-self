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
    return Memory(
        memory_id="first-grounded",
        content=json.dumps(
            {
                "kind": "controlled_flee_destination_outcome",
                "destination_id": destination_id,
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


def _reset_observation(
    *,
    seq: int,
    kind: str,
    entities: tuple[MineflayerEntityFact, ...],
) -> MineflayerObservation:
    return MineflayerObservation(
        session_id="reset-session",
        seq=seq,
        kind=kind,
        snapshot=MineflayerSnapshot(
            health=20,
            food=20,
            oxygen_level=None,
            position=_reset_anchor(),
            time=None,
            inventory=(),
            nearby_entities=entities,
        ),
    )


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


def test_reset_stale_zombie_never_summons(monkeypatch, tmp_path: Path) -> None:
    stale = _zombie(entity_id=81, distance=4.0)
    session = _ResetSession(
        (
            _reset_observation(seq=1, kind="spawn", entities=(stale,)),
            _reset_observation(seq=2, kind="entities", entities=(stale,)),
        ),
        repeat_last=True,
    )
    commands: list[dict[str, object]] = []

    async def record_command(**kwargs: object) -> None:
        commands.append(kwargs)

    monkeypatch.setattr(transaction, "write_server_command", record_command)

    with pytest.raises(IdentityPriorTransactionError, match="zero-zombie"):
        asyncio.run(
            transaction.reset_live_world(
                session,
                args=_reset_args(timeout_s=0.005),
                anchor=_reset_anchor(),
                evidence_path=tmp_path / "server-commands.jsonl",
            )
        )

    assert len(commands) == 7
    assert not any("summon" in str(command["command"]) for command in commands)


def test_reset_requires_zero_barrier_before_one_summon(
    monkeypatch,
    tmp_path: Path,
) -> None:
    old = _zombie(entity_id=81, distance=4.0)
    controlled = _zombie(entity_id=161, distance=4.0)
    session = _ResetSession(
        (
            _reset_observation(seq=1, kind="spawn", entities=(old,)),
            _reset_observation(seq=2, kind="entities", entities=()),
            _reset_observation(seq=3, kind="entities", entities=(controlled,)),
        )
    )

    result, commands = _run_reset(monkeypatch, tmp_path, session)

    assert result.cleanup_zero_observation.snapshot.nearby_entities == ()
    assert result.matched_observation.snapshot.nearby_entities == (controlled,)
    assert [command["command"] for command in commands].count(
        result.summon_command
    ) == 1
    assert "phase 1 cleanup" in str(commands[0]["reason"])
    assert "phase 2 fixture" in str(commands[7]["reason"])


def test_reset_qualification_does_not_construct_provider(
    monkeypatch,
    tmp_path: Path,
) -> None:
    controlled = _zombie(entity_id=161, distance=4.0)
    session = _ResetSession(
        (
            _reset_observation(seq=1, kind="spawn", entities=()),
            _reset_observation(seq=2, kind="entities", entities=()),
            _reset_observation(seq=3, kind="entities", entities=(controlled,)),
        )
    )

    def unexpected_provider(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("reset qualification must not construct a provider")

    monkeypatch.setattr(transaction, "provider_engine", unexpected_provider)
    result, _ = _run_reset(monkeypatch, tmp_path, session)

    assert result.matched_observation.snapshot.nearby_entities == (controlled,)


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
            _reset_observation(seq=2, kind="entities", entities=()),
            _reset_observation(seq=3, kind="entities", entities=duplicate),
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
    assert len(commands) == 8


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


def test_later_request_uses_consequence_and_memory_without_condition_label() -> None:
    from experiments.identity_prior_trajectory_transaction import (
        _initial_request_for_condition,
    )

    observation, _ = build_candidate_world()
    request = build_later_request(
        identity_request=_initial_request_for_condition("C"),
        observation=observation,
        anchor=observation.snapshot.position,
        memory=_memory(),
    )

    assert request.request_id == LATER_REQUEST_ID
    assert FIRST_REQUEST_ID not in request.request_id
    by_key = {datum.key: datum for datum in request.context}
    assert "identity_specification" in by_key
    assert "memory:first-grounded-flee" in by_key

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
    status: str = "completed_grounded_trajectory",
) -> list[InvocationResult]:
    signatures = signature_by_condition or {
        "A": [{"mode": "bounded", "status": "resolved"}],
        "B": [{"mode": "bounded", "status": "resolved"}],
        "C": [{"mode": "bounded", "status": "resolved"}],
    }
    result = []
    for block_index, block in enumerate((("A", "B", "C"), ("B", "C", "A"), ("C", "A", "B"))):
        for ordinal, condition_id in enumerate(block):
            result.append(
                InvocationResult(
                    condition_id=condition_id,
                    block_index=block_index,
                    ordinal=ordinal,
                    report={
                        "status": status,
                        "first_bound_destination": first_by_condition[
                            condition_id
                        ],
                        "later_bound_destination": first_by_condition[
                            condition_id
                        ],
                        "initial_cognition_signature": signatures[
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


def test_classifier_does_not_count_unresolved_as_embodied_destination() -> None:
    result = classify(
        _records(
            {
                "A": None,
                "B": "route-17",
                "C": "route-42",
            }
        )
    )

    assert result["class"] == "E"
    assert result["first_embodied_divergence"] is False
    assert result["later_embodied_divergence"] is False


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


def test_classifier_reports_cognition_only_when_signatures_differ() -> None:
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


def test_canonical_launcher_is_one_shot_and_blocks_before_run() -> None:
    launcher = Path(
        "experiments/run_identity_prior_trajectory_transaction.sh"
    ).read_text(encoding="utf-8")

    assert launcher.count("--phase run") == 1
    assert "--phase plan" in launcher
    assert "--phase preflight" in launcher
    assert "capture_authority initial" in launcher
    assert "capture_authority final" in launcher
    assert "NO MATERIAL CONFLICT" in launcher
    assert "--phase first" not in launcher
    assert "--phase restart" not in launcher
    assert "same-run fixture tuning" not in launcher

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
