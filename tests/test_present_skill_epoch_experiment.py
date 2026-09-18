from experiments.present_skill_epoch import (
    DecisionKind,
    EpochDisposition,
    FixtureEvent,
    admit_flee_candidate,
    bind_flee_destination,
    broaden_flee,
    build_present,
    classify_event,
    narrow_for_flee,
    projection_is_current,
    reference_facts,
    run_reference_fixture,
    start_flee_execution,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillState


def _commit_reach_safety() -> IntentCommitment:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-safe-test",
        objective="reach safety",
        at_ns=1,
        provenance=Provenance(source="test", reference="intent"),
    )
    return commitment


def test_flee_narrowing_preserves_relevant_provenance_and_reduces_surface() -> None:
    commitment = _commit_reach_safety()
    broad = build_present(
        intent_commitment=commitment,
        source_revision=1,
        facts=reference_facts(),
    )

    assert admit_flee_candidate(broad) is True

    local = narrow_for_flee(broad)

    assert len(broad.facts) == 7
    assert len(local.facts) == 5
    assert local.focus == "FLEE"
    assert local.fact("hunger") is None
    assert local.fact("companion_speaking") is None
    assert local.fact("route_open:cave") is not None
    assert local.fact("route_open:cave").provenance == broad.fact(
        "route_open:cave"
    ).provenance


def test_resolved_flee_binding_hands_off_to_existing_skill_execution() -> None:
    commitment = _commit_reach_safety()
    broad = build_present(
        intent_commitment=commitment,
        source_revision=1,
        facts=reference_facts(),
    )
    local = narrow_for_flee(broad)
    decision = bind_flee_destination(local)

    assert decision.kind is DecisionKind.START
    assert decision.destination == "cave"

    execution = start_flee_execution(
        decision=decision,
        intent_commitment=commitment,
        execution_id="flee-test-1",
        at_ns=2,
        provenance=Provenance(source="test", reference="skill-start"),
    )

    assert execution.skill_id == "FLEE"
    assert execution.intent_id == "intent-safe-test"
    assert execution.state is SkillState.STARTED


def test_omitted_route_evidence_escalates_instead_of_becoming_false() -> None:
    commitment = _commit_reach_safety()
    broad = build_present(
        intent_commitment=commitment,
        source_revision=1,
        facts=reference_facts(),
    )
    misleading = narrow_for_flee(broad, include_route_status=False)

    decision = bind_flee_destination(misleading)

    assert decision.kind is DecisionKind.ESCALATE
    assert decision.destination is None
    assert decision.missing_keys == (
        "route_open:cave",
        "route_open:ridge",
    )

    recovered = bind_flee_destination(broaden_flee(misleading, broad))

    assert recovered.kind is DecisionKind.START
    assert recovered.destination == "cave"


def test_present_projection_is_stale_after_material_source_revision_change() -> None:
    commitment = _commit_reach_safety()
    broad = build_present(
        intent_commitment=commitment,
        source_revision=1,
        facts=reference_facts(revision=1),
    )
    local = narrow_for_flee(broad)

    assert projection_is_current(local, current_source_revision=1) is True
    assert projection_is_current(local, current_source_revision=2) is False


def test_event_fixture_does_not_turn_every_event_into_a_model_call() -> None:
    assert classify_event(FixtureEvent.AMBIENT_OBSERVATION) is EpochDisposition.IGNORE
    assert classify_event(FixtureEvent.QUIET) is EpochDisposition.IGNORE
    assert (
        classify_event(FixtureEvent.ROUTE_OBSERVATION)
        is EpochDisposition.DECISION_EPOCH_NO_MODEL
    )
    assert (
        classify_event(FixtureEvent.SUPERVISION_DEADLINE)
        is EpochDisposition.DECISION_EPOCH_NO_MODEL
    )
    assert (
        classify_event(FixtureEvent.SKILL_LOCAL_UNCERTAINTY)
        is EpochDisposition.DECISION_EPOCH_WITH_RELAYENGINE
    )
    assert (
        classify_event(FixtureEvent.CONSEQUENCE_MISMATCH)
        is EpochDisposition.DECISION_EPOCH_WITH_RELAYENGINE
    )


def test_reference_fixture_reports_reversible_narrowing_and_skill_handoff() -> None:
    result = run_reference_fixture()

    assert result["candidate_admitted"] is True
    assert result["broad_fact_count"] == 7
    assert result["narrow_fact_count"] == 5
    assert result["decision"]["kind"] == "start"
    assert result["decision"]["destination"] == "cave"
    assert result["misleading_narrow"]["kind"] == "escalate"
    assert result["misleading_narrow"]["recovered_kind"] == "start"
    assert result["skill_execution"]["state"] == "started"
    assert result["old_projection_is_current_after_revision_advance"] is False
