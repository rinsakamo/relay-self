from experiments.present_skill_epoch import build_present
from experiments.reconsideration_admission import (
    ReconsiderationAdmissionKind,
    admit_reach_safety_reconsideration,
    assess_reach_safety_reconsideration,
    reach_safety_facts,
    run_reference_fixture,
)
from relay_self.intent import (
    IntentCommitment,
    IntentEventKind,
    ReconsiderationDecision,
)
from relay_self.provenance import Provenance


def _commit_reach_safety() -> IntentCommitment:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-safe-test-107",
        objective="reach safety",
        at_ns=1,
        provenance=Provenance(source="test", reference="intent"),
    )
    return commitment


def _present(
    commitment: IntentCommitment,
    *,
    revision: int,
    current_destination: str,
    routes: dict[str, bool],
    viability_acceptable: bool = True,
    route_catalog_complete: bool = True,
):
    return build_present(
        intent_commitment=commitment,
        source_revision=revision,
        facts=reach_safety_facts(
            revision=revision,
            current_destination=current_destination,
            routes=routes,
            viability_acceptable=viability_acceptable,
            route_catalog_complete=route_catalog_complete,
        ),
    )


def test_blocked_local_route_recovers_without_intent_reconsideration() -> None:
    commitment = _commit_reach_safety()
    present = _present(
        commitment,
        revision=1,
        current_destination="cave",
        routes={"cave": False, "ridge": True},
    )

    admission, request = admit_reach_safety_reconsideration(
        present=present,
        commitment=commitment,
        material_change_key="route_open:cave",
        at_ns=2,
    )

    assert admission.kind is ReconsiderationAdmissionKind.LOCAL_RECOVERY
    assert request is None
    assert commitment.pending_reconsideration is None
    assert [event.kind for event in commitment.events] == [IntentEventKind.COMMITTED]


def test_grounded_loss_of_all_local_routes_requests_reconsideration() -> None:
    commitment = _commit_reach_safety()
    present = _present(
        commitment,
        revision=2,
        current_destination="ridge",
        routes={"cave": False, "ridge": False},
    )

    admission, request = admit_reach_safety_reconsideration(
        present=present,
        commitment=commitment,
        material_change_key="route_open:ridge",
        at_ns=2,
    )

    assert admission.kind is ReconsiderationAdmissionKind.REQUEST_RECONSIDERATION
    assert request is not None
    assert request.kind is IntentEventKind.RECONSIDERATION_REQUESTED
    assert request.provenance == present.fact("route_open:ridge").provenance
    assert commitment.current_intent is not None


def test_incomplete_route_catalog_broadens_locally_instead_of_requesting() -> None:
    commitment = _commit_reach_safety()
    present = _present(
        commitment,
        revision=3,
        current_destination="ridge",
        routes={"cave": False, "ridge": False},
        route_catalog_complete=False,
    )

    admission = assess_reach_safety_reconsideration(
        present,
        material_change_key="route_open:ridge",
    )

    assert admission.kind is ReconsiderationAdmissionKind.LOCAL_RECOVERY
    assert "incomplete" in admission.reason


def test_new_affordance_does_not_automatically_break_current_intent() -> None:
    commitment = _commit_reach_safety()
    present = _present(
        commitment,
        revision=4,
        current_destination="ridge",
        routes={"cave": False, "ridge": False, "tower": True},
    )

    admission, request = admit_reach_safety_reconsideration(
        present=present,
        commitment=commitment,
        material_change_key="route_open:tower",
        at_ns=2,
    )

    assert admission.kind is ReconsiderationAdmissionKind.LOCAL_RECOVERY
    assert request is None
    assert commitment.current_intent is not None


def test_viability_can_request_reconsideration_even_with_local_route() -> None:
    commitment = _commit_reach_safety()
    present = _present(
        commitment,
        revision=5,
        current_destination="tower",
        routes={"tower": True},
        viability_acceptable=False,
    )

    admission, request = admit_reach_safety_reconsideration(
        present=present,
        commitment=commitment,
        material_change_key="viability_acceptable",
        at_ns=2,
    )

    assert admission.kind is ReconsiderationAdmissionKind.REQUEST_RECONSIDERATION
    assert request is not None
    assert request.provenance == present.fact("viability_acceptable").provenance


def test_request_and_later_decision_keep_distinct_provenance() -> None:
    commitment = _commit_reach_safety()
    present = _present(
        commitment,
        revision=6,
        current_destination="ridge",
        routes={"cave": False, "ridge": False},
    )
    _, request = admit_reach_safety_reconsideration(
        present=present,
        commitment=commitment,
        material_change_key="route_open:ridge",
        at_ns=2,
    )
    assert request is not None

    commitment.reconsider(
        "intent-safe-test-107",
        decision=ReconsiderationDecision.CONTINUE,
        reason="wait for new evidence",
        at_ns=3,
        provenance=Provenance(source="test.policy", reference="decision"),
    )

    assert commitment.events[-2].provenance.source == "fixture.world"
    assert commitment.events[-1].provenance.source == "test.policy"
    assert commitment.events[-2].provenance != commitment.events[-1].provenance


def test_reference_fixture_preserves_local_recovery_and_explicit_release() -> None:
    result = run_reference_fixture()

    assert [step["admission"] for step in result["steps"]] == [
        "local_recovery",
        "keep_intent",
        "request_reconsideration",
        "local_recovery",
        "request_reconsideration",
    ]
    assert [event["kind"] for event in result["intent_events"]] == [
        "committed",
        "reconsideration_requested",
        "reconsidered_continue",
        "reconsideration_requested",
        "reconsidered_release",
    ]
    assert result["first_request_reference"] == "rev:3:route:ridge"
    assert result["first_decision_reference"] == "decision:continue:wait-for-route"
    assert result["second_request_reference"] == "rev:5:viability"
    assert result["second_decision_reference"] == "decision:release:viability"
    assert result["final_current_intent"] is None
