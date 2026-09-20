import json
import subprocess
from pathlib import Path

from experiments.controlled_minecraft_vertical import ControlledSkill
from experiments.identity_prior_trajectory import build_candidate_world
from experiments.identity_prior_trajectory_transaction import (
    FIRST_REQUEST_ID,
    LATER_REQUEST_ID,
    InvocationResult,
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
