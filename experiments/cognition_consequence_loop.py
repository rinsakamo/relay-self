from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from enum import Enum

from experiments.present_skill_epoch import (
    DecisionKind,
    PresentFact,
    PresentProjection,
    bind_flee_destination,
    build_present,
    narrow_for_flee,
    projection_is_current,
    start_flee_execution,
)
from experiments.reconsideration_admission import (
    admit_reach_safety_reconsideration,
    reach_safety_facts,
)
from relay_self.action import ActionLifecycle
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


class ConsequenceComparisonKind(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExpectedEvidence:
    key: str
    value: object


@dataclass(frozen=True, slots=True)
class ObservedEvidence:
    key: str
    value: object
    provenance: Provenance


@dataclass(frozen=True, slots=True)
class ConsequenceComparison:
    kind: ConsequenceComparisonKind
    expected: ExpectedEvidence
    observed: ObservedEvidence | None


def compare_consequence(
    expected: ExpectedEvidence,
    observed: ObservedEvidence | None,
) -> ConsequenceComparison:
    if observed is None:
        return ConsequenceComparison(
            kind=ConsequenceComparisonKind.UNKNOWN,
            expected=expected,
            observed=None,
        )
    if observed.key == expected.key and observed.value == expected.value:
        return ConsequenceComparison(
            kind=ConsequenceComparisonKind.MATCH,
            expected=expected,
            observed=observed,
        )
    return ConsequenceComparison(
        kind=ConsequenceComparisonKind.MISMATCH,
        expected=expected,
        observed=observed,
    )


def _commit_reach_safety(case_id: str) -> IntentCommitment:
    commitment = IntentCommitment()
    commitment.commit(
        f"intent-{case_id}",
        objective="reach safety",
        at_ns=1,
        provenance=Provenance(source="fixture", reference=f"{case_id}:intent"),
    )
    return commitment


def _flee_facts(
    *,
    revision: int,
    cave_open: bool,
    ridge_open: bool,
    route_source: str = "fixture.world",
) -> tuple[PresentFact, ...]:
    return (
        PresentFact(
            "threat_nearby",
            True,
            Provenance(source="fixture.world", reference=f"rev:{revision}:threat"),
        ),
        PresentFact(
            "health",
            8,
            Provenance(source="fixture.body", reference=f"rev:{revision}:health"),
        ),
        PresentFact(
            "safe_destinations",
            ("cave", "ridge"),
            Provenance(
                source="fixture.memory",
                reference=f"rev:{revision}:safe-destinations",
            ),
        ),
        PresentFact(
            "route_open:cave",
            cave_open,
            Provenance(source=route_source, reference=f"rev:{revision}:route:cave"),
        ),
        PresentFact(
            "route_open:ridge",
            ridge_open,
            Provenance(source=route_source, reference=f"rev:{revision}:route:ridge"),
        ),
    )


def _present(
    commitment: IntentCommitment,
    *,
    revision: int,
    cave_open: bool,
    ridge_open: bool,
    route_source: str = "fixture.world",
) -> PresentProjection:
    return build_present(
        intent_commitment=commitment,
        source_revision=revision,
        facts=_flee_facts(
            revision=revision,
            cave_open=cave_open,
            ridge_open=ridge_open,
            route_source=route_source,
        ),
    )


def _start_cave_path(
    *,
    case_id: str,
    commitment: IntentCommitment,
    present: PresentProjection,
) -> tuple[SkillExecution, ActionLifecycle]:
    local = narrow_for_flee(present)
    decision = bind_flee_destination(local)
    if decision.kind is not DecisionKind.START or decision.destination != "cave":
        raise ValueError("fixture expected a resolved FLEE(cave) decision")

    skill = start_flee_execution(
        decision=decision,
        intent_commitment=commitment,
        execution_id=f"skill-{case_id}",
        at_ns=2,
        provenance=Provenance(source="fixture", reference=f"{case_id}:skill:start"),
    )
    action = ActionLifecycle.propose(
        f"action-{case_id}",
        skill_execution=skill,
        intent_commitment=commitment,
        at_ns=3,
        provenance=Provenance(source="fixture", reference=f"{case_id}:action:propose"),
    )
    action = action.authorize(
        at_ns=4,
        provenance=Provenance(
            source="fixture.authority",
            reference=f"{case_id}:action:authorize",
        ),
        authority="fixture.authority",
    )
    action = action.issue(
        at_ns=5,
        deadline_ns=20,
        provenance=Provenance(source="fixture", reference=f"{case_id}:action:issue"),
    )
    return skill, action


def run_non_convergence_case() -> dict[str, object]:
    case_id = "non-convergence"
    commitment = _commit_reach_safety(case_id)
    present = _present(
        commitment,
        revision=1,
        cave_open=True,
        ridge_open=False,
    )
    local = narrow_for_flee(present, include_route_status=False)
    decision = bind_flee_destination(local)

    return {
        "case": case_id,
        "decision": decision.kind.value,
        "missing_keys": decision.missing_keys,
        "skill_started": False,
        "action_created": False,
        "intent_id": commitment.current_intent.intent_id,
        "training_label_created": False,
    }


def run_expected_consequence_case() -> dict[str, object]:
    case_id = "expected-consequence"
    commitment = _commit_reach_safety(case_id)
    present = _present(
        commitment,
        revision=1,
        cave_open=True,
        ridge_open=False,
    )
    skill, action = _start_cave_path(
        case_id=case_id,
        commitment=commitment,
        present=present,
    )
    observed = ObservedEvidence(
        key="arrived:cave",
        value=True,
        provenance=Provenance(
            source="fixture.world",
            reference=f"{case_id}:arrived:cave",
        ),
    )
    comparison = compare_consequence(
        ExpectedEvidence(key="arrived:cave", value=True),
        observed,
    )
    action = action.record_outcome(
        at_ns=6,
        provenance=observed.provenance,
    )
    skill = skill.succeed(
        reason="observed expected arrival evidence",
        at_ns=7,
        provenance=observed.provenance,
    )

    return {
        "case": case_id,
        "comparison": comparison.kind.value,
        "action_state": action.state.value,
        "skill_state": skill.state.value,
        "intent_id": commitment.current_intent.intent_id,
        "present_revision": present.source_revision,
        "training_label_created": False,
    }


def run_stale_present_mismatch_case() -> dict[str, object]:
    case_id = "stale-present-mismatch"
    commitment = _commit_reach_safety(case_id)
    stale_present = _present(
        commitment,
        revision=1,
        cave_open=True,
        ridge_open=False,
        route_source="fixture.estimate",
    )
    skill, action = _start_cave_path(
        case_id=case_id,
        commitment=commitment,
        present=stale_present,
    )
    observed = ObservedEvidence(
        key="route_open:cave",
        value=False,
        provenance=Provenance(
            source="fixture.world",
            reference=f"{case_id}:rev:2:route:cave",
        ),
    )
    comparison = compare_consequence(
        ExpectedEvidence(key="route_open:cave", value=True),
        observed,
    )
    action = action.record_outcome(at_ns=6, provenance=observed.provenance)
    skill = skill.fail(
        reason="consequence contradicted the route assumption used by this path",
        at_ns=7,
        provenance=observed.provenance,
    )

    reopened = build_present(
        intent_commitment=commitment,
        source_revision=2,
        facts=reach_safety_facts(
            revision=2,
            current_destination="cave",
            routes={"cave": False, "ridge": True},
        ),
    )
    admission, request = admit_reach_safety_reconsideration(
        present=reopened,
        commitment=commitment,
        material_change_key="route_open:cave",
        at_ns=8,
    )

    return {
        "case": case_id,
        "comparison": comparison.kind.value,
        "decision_input_source": stale_present.fact("route_open:cave").provenance.source,
        "consequence_source": observed.provenance.source,
        "old_present_current": projection_is_current(
            stale_present,
            current_source_revision=2,
        ),
        "reopened_present_revision": reopened.source_revision,
        "action_state": action.state.value,
        "skill_state": skill.state.value,
        "reconsideration_admission": admission.kind.value,
        "reconsideration_request_created": request is not None,
        "intent_id": commitment.current_intent.intent_id,
        "training_label_created": False,
    }


def run_unknown_consequence_case() -> dict[str, object]:
    case_id = "unknown-consequence"
    commitment = _commit_reach_safety(case_id)
    present = _present(
        commitment,
        revision=1,
        cave_open=True,
        ridge_open=False,
    )
    skill, action = _start_cave_path(
        case_id=case_id,
        commitment=commitment,
        present=present,
    )
    comparison = compare_consequence(
        ExpectedEvidence(key="arrived:cave", value=True),
        None,
    )
    action = action.mark_unknown(
        at_ns=6,
        provenance=Provenance(
            source="fixture.execution",
            reference=f"{case_id}:consequence:unknown",
        ),
    )

    return {
        "case": case_id,
        "comparison": comparison.kind.value,
        "action_state": action.state.value,
        "skill_state": skill.state.value,
        "intent_id": commitment.current_intent.intent_id,
        "present_revision": present.source_revision,
        "training_label_created": False,
    }


def run_world_changed_case() -> dict[str, object]:
    case_id = "world-changed"
    commitment = _commit_reach_safety(case_id)
    present = _present(
        commitment,
        revision=1,
        cave_open=True,
        ridge_open=False,
        route_source="fixture.world",
    )
    skill, action = _start_cave_path(
        case_id=case_id,
        commitment=commitment,
        present=present,
    )
    observed = ObservedEvidence(
        key="route_open:cave",
        value=False,
        provenance=Provenance(
            source="fixture.world",
            reference=f"{case_id}:rev:2:external-change:route:cave",
        ),
    )
    comparison = compare_consequence(
        ExpectedEvidence(key="route_open:cave", value=True),
        observed,
    )
    action = action.record_outcome(at_ns=6, provenance=observed.provenance)
    skill = skill.fail(
        reason="the World changed and invalidated the selected route",
        at_ns=7,
        provenance=observed.provenance,
    )
    reopened = build_present(
        intent_commitment=commitment,
        source_revision=2,
        facts=reach_safety_facts(
            revision=2,
            current_destination="cave",
            routes={"cave": False, "ridge": True},
        ),
    )
    admission, request = admit_reach_safety_reconsideration(
        present=reopened,
        commitment=commitment,
        material_change_key="route_open:cave",
        at_ns=8,
    )

    return {
        "case": case_id,
        "comparison": comparison.kind.value,
        "decision_input_source": present.fact("route_open:cave").provenance.source,
        "world_change_reference": observed.provenance.reference,
        "old_present_current": projection_is_current(
            present,
            current_source_revision=2,
        ),
        "action_state": action.state.value,
        "skill_state": skill.state.value,
        "reconsideration_admission": admission.kind.value,
        "reconsideration_request_created": request is not None,
        "intent_id": commitment.current_intent.intent_id,
        "training_label_created": False,
    }


def run_controller_failure_case() -> dict[str, object]:
    case_id = "controller-failure"
    commitment = _commit_reach_safety(case_id)
    present = _present(
        commitment,
        revision=1,
        cave_open=True,
        ridge_open=False,
        route_source="fixture.world",
    )
    skill, action = _start_cave_path(
        case_id=case_id,
        commitment=commitment,
        present=present,
    )
    observed = ObservedEvidence(
        key="movement_progress",
        value=False,
        provenance=Provenance(
            source="fixture.controller",
            reference=f"{case_id}:movement:stalled",
        ),
    )
    comparison = compare_consequence(
        ExpectedEvidence(key="movement_progress", value=True),
        observed,
    )
    action = action.record_outcome(at_ns=6, provenance=observed.provenance)
    skill = skill.fail(
        reason="controller reported no movement progress",
        at_ns=7,
        provenance=observed.provenance,
    )

    route_fact = present.fact("route_open:cave")
    assert route_fact is not None
    return {
        "case": case_id,
        "comparison": comparison.kind.value,
        "route_remains_open": route_fact.value,
        "route_provenance_source": route_fact.provenance.source,
        "failure_provenance_source": observed.provenance.source,
        "action_state": action.state.value,
        "skill_state": skill.state.value,
        "reconsideration_request_created": (
            commitment.pending_reconsideration is not None
        ),
        "intent_id": commitment.current_intent.intent_id,
        "training_label_created": False,
    }


def run_reference_fixture() -> dict[str, object]:
    cases = (
        run_non_convergence_case(),
        run_expected_consequence_case(),
        run_stale_present_mismatch_case(),
        run_unknown_consequence_case(),
        run_world_changed_case(),
        run_controller_failure_case(),
    )
    return {
        "cases": cases,
        "case_count": len(cases),
        "automatic_training_labels": sum(
            1 for case in cases if case["training_label_created"]
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the deterministic cognition/consequence closed-loop fixture."
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    result = run_reference_fixture()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Cognition / consequence closed-loop fixture")
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
