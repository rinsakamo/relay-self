from __future__ import annotations

import argparse
import json

from experiments.present_skill_epoch import (
    EpochDisposition,
    FixtureEvent,
    bind_flee_destination,
    build_present,
    classify_event,
    narrow_for_flee,
    projection_is_current,
    reference_facts,
    start_flee_execution,
)
from experiments.reconsideration_admission import (
    ReconsiderationAdmissionKind,
    admit_reach_safety_reconsideration,
    reach_safety_facts,
)
from relay_self.action import ActionLifecycle
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance


def _snapshot(
    *,
    event: str,
    disposition: EpochDisposition,
    effects: tuple[str, ...],
    present_revision: int,
    commitment: IntentCommitment,
    skill_state: str,
    supervisor: ActionSupervisor,
) -> dict[str, object]:
    current_intent = commitment.current_intent
    action = supervisor.get("action-flee-106")
    return {
        "event": event,
        "disposition": disposition.value,
        "relayengine_requested": (
            disposition is EpochDisposition.DECISION_EPOCH_WITH_RELAYENGINE
        ),
        "effects": effects,
        "present_revision": present_revision,
        "intent_id": current_intent.intent_id if current_intent is not None else None,
        "pending_reconsideration": commitment.pending_reconsideration is not None,
        "skill_state": skill_state,
        "action_state": action.state.value,
    }


def run_multi_owner_trace() -> dict[str, object]:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-safe-106",
        objective="reach safety",
        at_ns=1,
        provenance=Provenance(source="fixture", reference="intent:reach-safety"),
    )

    broad = build_present(
        intent_commitment=commitment,
        source_revision=1,
        facts=reference_facts(revision=1),
    )
    local = narrow_for_flee(broad)
    decision = bind_flee_destination(local)
    skill = start_flee_execution(
        decision=decision,
        intent_commitment=commitment,
        execution_id="flee-exec-106",
        at_ns=2,
        provenance=Provenance(source="fixture", reference="skill:start"),
    )

    action = ActionLifecycle.propose(
        "action-flee-106",
        skill_execution=skill,
        intent_commitment=commitment,
        at_ns=3,
        provenance=Provenance(source="fixture", reference="action:propose"),
    )
    action = action.authorize(
        at_ns=4,
        provenance=Provenance(source="fixture.authority", reference="action:authorize"),
        authority="fixture.authority",
    )
    supervisor = ActionSupervisor()
    supervisor.issue(
        action,
        at_ns=5,
        deadline_ns=10,
        provenance=Provenance(source="fixture", reference="action:issue"),
    )

    trace: list[dict[str, object]] = []

    trace.append(
        _snapshot(
            event="irrelevant_observation",
            disposition=classify_event(FixtureEvent.AMBIENT_OBSERVATION),
            effects=(),
            present_revision=1,
            commitment=commitment,
            skill_state=skill.state.value,
            supervisor=supervisor,
        )
    )

    present = build_present(
        intent_commitment=commitment,
        source_revision=2,
        facts=reach_safety_facts(
            revision=2,
            current_destination="cave",
            routes={"cave": False, "ridge": True},
        ),
    )
    trace.append(
        _snapshot(
            event="material_route_observation",
            disposition=classify_event(FixtureEvent.ROUTE_OBSERVATION),
            effects=("present_reprojected",),
            present_revision=present.source_revision,
            commitment=commitment,
            skill_state=skill.state.value,
            supervisor=supervisor,
        )
    )

    timed_out = supervisor.advance(
        at_ns=10,
        provenance=Provenance(source="fixture.clock", reference="deadline:10"),
    )
    trace.append(
        _snapshot(
            event="action_supervision_deadline",
            disposition=classify_event(FixtureEvent.SUPERVISION_DEADLINE),
            effects=("action_timeout",),
            present_revision=present.source_revision,
            commitment=commitment,
            skill_state=skill.state.value,
            supervisor=supervisor,
        )
    )

    trace.append(
        _snapshot(
            event="skill_local_control_step",
            disposition=EpochDisposition.DECISION_EPOCH_NO_MODEL,
            effects=("skill_execution_continues",),
            present_revision=present.source_revision,
            commitment=commitment,
            skill_state=skill.state.value,
            supervisor=supervisor,
        )
    )

    present = build_present(
        intent_commitment=commitment,
        source_revision=3,
        facts=reach_safety_facts(
            revision=3,
            current_destination="cave",
            routes={"cave": False, "ridge": True},
        ),
    )
    admission, request = admit_reach_safety_reconsideration(
        present=present,
        commitment=commitment,
        material_change_key="route_open:cave",
        at_ns=11,
    )
    assert admission.kind is ReconsiderationAdmissionKind.LOCAL_RECOVERY
    assert request is None
    trace.append(
        _snapshot(
            event="consequence_mismatch",
            disposition=classify_event(FixtureEvent.CONSEQUENCE_MISMATCH),
            effects=("present_reopened", "local_recovery", "intent_unchanged"),
            present_revision=present.source_revision,
            commitment=commitment,
            skill_state=skill.state.value,
            supervisor=supervisor,
        )
    )

    trace.append(
        _snapshot(
            event="skill_local_uncertainty",
            disposition=classify_event(FixtureEvent.SKILL_LOCAL_UNCERTAINTY),
            effects=("cognition_request_required",),
            present_revision=present.source_revision,
            commitment=commitment,
            skill_state=skill.state.value,
            supervisor=supervisor,
        )
    )

    trace.append(
        _snapshot(
            event="quiet_interval",
            disposition=classify_event(FixtureEvent.QUIET),
            effects=(),
            present_revision=present.source_revision,
            commitment=commitment,
            skill_state=skill.state.value,
            supervisor=supervisor,
        )
    )

    current_intent = commitment.current_intent
    return {
        "trace": trace,
        "old_present_is_current_after_material_update": projection_is_current(
            broad,
            current_source_revision=2,
        ),
        "timed_out_action_ids": [lifecycle.action_id for lifecycle in timed_out],
        "next_action_deadline_ns": supervisor.next_deadline_ns,
        "mismatch_admission": admission.kind.value,
        "final_intent_id": (
            current_intent.intent_id if current_intent is not None else None
        ),
        "final_skill_state": skill.state.value,
        "final_action_state": supervisor.get("action-flee-106").state.value,
        "relayengine_request_count": sum(
            1 for row in trace if row["relayengine_requested"]
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the deterministic multi-owner decision-epoch trace."
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    result = run_multi_owner_trace()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Multi-owner decision-epoch trace")
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
