"""M read-only handoff after *actual original* S coordinator returns a choice.

Use pinned #634 product types and its real S42 scorer and B0 producer;
the fixtures are synthetic native probes, not native-source attestation.
"""
from dataclasses import replace

import pytest
from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from adapters.mineflayer.s34_native_world_cognition_ci import _native_threat
from adapters.mineflayer.self_body_m0_projection import compose_b0_cognition_views
from relay_self.epoch_plan import PlannedDecisionEpochResult
from relay_self.learning import LearningPreferenceState
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    select_world_conditioned_choice,
)
from test_self_live_think import native_probe

from experiments.metabolism_b0_cognition import read_b0_resource_context
from experiments.metabolism_s_epoch_resource import observe_completed_s_resource_epoch
from experiments.metabolism_viability import Interoception
from relay_self.action_supervision import ActionSupervisor
from relay_self.provenance import Provenance
from relay_self.runtime_coordination import coordinate_decision_epoch


def prepared(*, energy=12.0, distance=3.0, quantum=0.1, gain=1.0):
    sid = "dev-s-post-m"
    probe = native_probe(8, distance, sid=sid)
    entity = probe.snapshot.nearby_entities[0]
    native = _native_threat(
        probe, probe.request_id, expected_entity_id=entity.entity_id,
    )
    retained = LearningPreferenceState(
        "risk_weight", 4, 0, 10, 1, Provenance("s10-dev", "revision-one"),
    )
    sensor = Interoception(quantum=quantum, gain=gain)
    owner = B0EnergyLedger(sid, sensor=sensor)
    owner.body = replace(owner.body, energy=energy)
    original_decision = owner.decide(probe)
    body_world = compose_b0_cognition_views(
        probe, owner, original_decision,
        self_id="self-s", epoch_id="epoch-s",
    )
    resource = read_b0_resource_context(
        body_world, owner_decision=original_decision,
        config=owner.config, sensor=owner.sensor, noise_bound=0,
    )
    supervisor = ActionSupervisor()
    called = []

    def cognition(request):
        called.append(request)
        return select_world_conditioned_choice(
            request, retained,
            expected_session_id=sid, expected_entity_id=entity.entity_id,
        )

    s_epoch = coordinate_decision_epoch(
        supervisor,
        at_ns=100,
        provenance=Provenance("s-epoch-dev", "epoch-s"),
        decision_step=lambda: native,
        relay_engine=cognition,
    )
    assert len(called) == 1
    return s_epoch, native, retained, resource, original_decision, body_world, owner


def join(data, *, s_epoch=None, native=None, retained=None, body=None):
    s, n, r, b, *_ = data
    return observe_completed_s_resource_epoch(
        s if s_epoch is None else s_epoch,
        native=n if native is None else native,
        retained=r if retained is None else retained,
        body=b if body is None else body,
    )


def test_actual_s_coordination_and_b0_owner_near_threat_cost_tension():
    data = prepared(energy=0.6, distance=3.0)
    original, native, retained, resource, decision, view, owner = data
    readout = join(data)
    assert readout.s_epoch is original
    assert original.cognition_result.selection is WorldChoiceKind.MOVE_AWAY
    assert readout.choice is WorldChoiceKind.MOVE_AWAY
    assert readout.modeled_tension == "MOVE_MODEL_INSUFFICIENT"
    assert resource.facts[1].affordability == "MODEL_INSUFFICIENT"
    assert readout.body is resource
    assert readout.s_choice_kept
    assert readout.action_authority is False
    assert readout.action_issues == readout.learning_updates == readout.habit_grants == 0
    assert decision.body_tick == resource.owner_tick
    assert view.body.sensed("m0_energy_sensor").value == decision.sensor_reading
    assert owner.body.energy == 0.6
    assert owner.credit_count == 0
    assert not hasattr(readout, "selected_action")
    assert not hasattr(readout, "authorize_action")


def test_unchanged_s_choice_when_energy_high_vs_low():
    high = prepared(energy=12.0)
    low = prepared(energy=0.6)
    assert high[0].cognition_result.selection == low[0].cognition_result.selection
    assert join(high).modeled_tension == "NO_MODEL_TENSION"
    assert join(low).modeled_tension == "MOVE_MODEL_INSUFFICIENT"
    assert join(high).choice == join(low).choice is WorldChoiceKind.MOVE_AWAY
    # S action policy is the same; M never substitutes its own selection.


def test_far_s_wait_is_not_relabelled_as_move_or_food_choice():
    data = prepared(energy=0.6, distance=10.0)
    result = join(data)
    assert result.choice is WorldChoiceKind.WAIT
    assert result.modeled_tension == "NO_MODEL_TENSION"
    assert result.body.facts[0].affordability == "MODEL_AFFORDABLE"
    assert not hasattr(result, "eat")
    assert not hasattr(result, "forage_priority")


def test_blind_sensor_remains_unknown_and_s_source_is_kept():
    data = prepared(energy=0.6, gain=0)
    result = join(data)
    assert result.choice is WorldChoiceKind.MOVE_AWAY
    assert result.modeled_tension == "MOVE_MODEL_UNKNOWN"
    assert result.body.energy_lower is None


def test_coarse_sensor_overlap_does_not_mint_unsafe_infeasibility():
    data = prepared(energy=0.6, quantum=1)
    result = join(data)
    assert result.body.facts[1].affordability == "MODEL_AMBIGUOUS"
    assert result.modeled_tension == "MOVE_MODEL_AMBIGUOUS"


def test_reads_completed_s_epoch_once_without_new_call_or_state_mutation():
    data = prepared(energy=0.6)
    initial = data[0]
    ledger_before = data[6].body
    first = join(data)
    second = join(data)
    assert first == second
    assert first.s_epoch is second.s_epoch is initial
    assert data[6].body == ledger_before
    assert data[6].credit_count == 0


def test_planned_epoch_requires_real_work_ids_and_never_changes_choice():
    data = prepared(energy=0.6)
    original = data[0]
    planned = PlannedDecisionEpochResult(original, ("cognition-work",), ())
    observation = join(data, s_epoch=planned)
    assert observation.executed_work_ids == ("cognition-work",)
    assert observation.s_epoch is original
    assert observation.action_issues == 0
    with pytest.raises(ValueError):
        join(data, s_epoch=replace(planned, executed_work_ids=()))
    with pytest.raises(ValueError):
        join(data, s_epoch=replace(planned, executed_work_ids=("same", "same")))


@pytest.mark.parametrize("change", [
    "no_cognition", "missing_choice", "pending_deadline",
    "timed_out_action", "foreign_session", "foreign_seq",
    "foreign_request", "altered_choice", "retained_revision",
    "foreign_native_provenance", "body_authority", "body_cost_source",
    "body_count", "body_label", "body_resource_action",
])
def test_dangerous_cross_epoch_or_foreign_model_rejected(change):
    data = prepared(energy=0.6)
    s, native, retained, body, *_ = data
    if change == "no_cognition":
        s = replace(s, cognition_requested=False)
    elif change == "missing_choice":
        s = replace(s, cognition_result=None)
    elif change == "pending_deadline":
        s = replace(s, next_action_deadline_ns=1000)
    elif change == "timed_out_action":
        s = replace(s, timed_out_actions=(object(),))
    elif change == "foreign_session":
        body = replace(body, session_id="foreign")
    elif change == "foreign_seq":
        body = replace(body, native_seq=body.native_seq + 1)
    elif change == "foreign_request":
        body = replace(body, native_source_ref="native-probe:forged")
    elif change == "altered_choice":
        s = replace(s, cognition_result=replace(
            s.cognition_result, selection=WorldChoiceKind.WAIT,
        ))
    elif change == "retained_revision":
        retained = replace(retained, revision=0)
    elif change == "foreign_native_provenance":
        native = replace(native, observation=replace(
            native.observation,
            session_id="foreign",
        ))
    elif change == "body_authority":
        body = replace(body, action_authority=True)
    elif change == "body_cost_source":
        body = replace(body, source_scope="PHYSICAL_ATTESTATION")
    elif change == "body_count":
        body = replace(body, facts=())
    elif change == "body_label":
        body = replace(body, facts=(
            replace(body.facts[0], activity="MOVE"), body.facts[1],
        ))
    else:
        body = replace(body, action_issues=1)
    with pytest.raises(ValueError):
        join(data, s_epoch=s, native=native, retained=retained, body=body)


def test_no_s_model_cognition_does_not_join_spontaneously():
    data = prepared()
    original = data[0]
    assert original.cognition_requested
    with pytest.raises(ValueError):
        join(data, s_epoch="not an S epoch")
