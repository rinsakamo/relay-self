"""I7: explicit S13/S14 -> S15 dual movement -> S16 terminal; fake session ONLY.

The new opt-in is an extra guard, NOT an authorization source, physical
attestation, two competing real-World causal observations or signed reward.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_action_feedback_qualification as frozen_s17
from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import (
    MOVE_BACKWARD_ACTION_REF,
    MOVE_FORWARD_ACTION_REF,
    InvalidMineflayerExecutionData,
    WorldConsequenceStatus,
    build_mineflayer_command,
    execute_mineflayer_command,
)
from relay_self.action import ActionState
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    record_interpreted_action_outcome,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.execution_admission import (
    AdmissionDecisionStatus,
    AdmissionPolicy,
    ExecutionAdmissionCriterion,
    admit_control_candidate,
)
from relay_self.execution_binding import (
    ExecutionBinding,
    resolve_execution_binding,
    start_and_propose_bound_execution,
)
from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    select_habit,
)
from relay_self.intent import IntentCommitment
from relay_self.planning import (
    PlanningCriterion,
    PlanningDirection,
    plan_candidate_from_prediction,
    select_plan,
)
from relay_self.route_adjudication import (
    adjudicate_routes,
    control_candidate_from_route_decision,
)


def _p(ref: str):
    return frozen_s17.provenance(f"i7:{ref}")


def _forward_owner_chain():
    # This is a DIFFERENT S13 Intent/admission and S14 bound Action, not
    # replace(existing_backward.binding_result, action_ref="MOVE_FORWARD").
    (
        _, _, concept, _, move_prediction, _, _, _,
    ) = frozen_s17.plan_and_habit()
    plan = select_plan(
        (
            plan_candidate_from_prediction(
                move_prediction,
                candidate_id="MOVE_FORWARD",
                feature_keys=("comparison_score",),
                provenance=_p("forward-plan-candidate"),
            ),
        ),
        PlanningCriterion(
            criterion_id="i7-forward-plan-test-only",
            feature_key="comparison_score",
            direction=PlanningDirection.MINIMIZE,
        ),
    )
    repertoire = HabitRepertoire(
        repertoire_id="i7-forward-existing-s11-selection",
        revision=0,
        rules=(
            HabitRule(
                habit_id="i7-forward-rule",
                cue_requirements=(
                    CueFeature("concept", concept.concept.canonical),
                ),
                candidate_ref="MOVE_FORWARD",
                priority=1,
                provenance=_p("forward-habit"),
            ),
        ),
        provenance=_p("forward-repertoire"),
    )
    habit = select_habit(
        repertoire,
        HabitCue(
            cue_id="i7-forward-cue",
            features=(CueFeature("concept", concept.concept.canonical),),
            provenance=_p("forward-cue"),
        ),
    )
    route = adjudicate_routes(
        plan, habit, frozen_s17.route_criterion(),
        provenance=_p("forward-route"),
    )
    candidate = control_candidate_from_route_decision(route)
    assert candidate is not None and candidate.candidate_ref == "MOVE_FORWARD"
    owner = IntentCommitment()
    owner.commit(
        "i7-explicit-test-forward-intent",
        objective="bounded forward movement test in a fake source only",
        at_ns=1,
        provenance=_p("forward-intent"),
    )
    criterion = ExecutionAdmissionCriterion(
        criterion_id="i7-only-forward",
        policy=AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
        required_intent_id="i7-explicit-test-forward-intent",
        allowed_candidate_refs=("MOVE_FORWARD",),
    )
    admitted = admit_control_candidate(
        candidate, route, owner, criterion,
        provenance=_p("forward-admission"),
    )
    assert admitted.status is AdmissionDecisionStatus.ADMITTED
    binding = ExecutionBinding(
        binding_id="i7-forward-binding",
        candidate_ref="MOVE_FORWARD",
        required_intent_id="i7-explicit-test-forward-intent",
        skill_execution_id="i7-forward-skill-exec",
        skill_ref="i7-forward-skill",
        action_id="i7-forward-action",
        action_ref=MOVE_FORWARD_ACTION_REF,
        provenance=_p("forward-binding"),
    )
    bound = resolve_execution_binding(
        admitted, candidate, route, owner, criterion, binding,
        provenance=_p("forward-bound"),
    )
    skill, proposed, binding_result = start_and_propose_bound_execution(
        bound, owner, at_ns=10, provenance=_p("forward-start"),
    )
    authorized = proposed.authorize(
        at_ns=11, provenance=_p("forward-authorization"),
        authority="i7-explicit-fixture-authority",
    )
    supervisor = ActionSupervisor()
    issued = supervisor.issue(
        authorized,
        at_ns=12,
        deadline_ns=100,
        provenance=_p("forward-issue"),
    )
    assert issued.is_current_snapshot and issued.state is ActionState.ISSUED
    assert skill is not None
    return issued, binding_result, supervisor


def _backward_owner_chain():
    *_, binding, _, supervisor, issued = frozen_s17.issued_chain()
    return issued, binding, supervisor


def _execute_fake(issued, binding, supervisor, *, forward: bool):
    cmd = build_mineflayer_command(
        issued, binding, allow_forward=forward,
    )
    fake = frozen_s17.successful_session(cmd)
    receipt = asyncio.run(
        execute_mineflayer_command(
            fake, cmd, provenance=_p("synthetic-world"),
        )
    )
    assert receipt.status is WorldConsequenceStatus.EXECUTED
    outcome = interpret_world_consequence(
        issued, binding, receipt,
        provenance=_p("synthetic-outcome"),
        allow_forward=forward,
    )
    closed = record_interpreted_action_outcome(
        supervisor, outcome, at_ns=20,
    )
    assert closed.state is ActionState.OUTCOME
    return cmd, fake, receipt, outcome, closed


def test_i7_manifest_is_original_frozen_preimplementation_version():
    payload = json.loads(
        (Path(__file__).parents[1] / "experiments/ac_integration_i7_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert digest == "f6459bf6d3b0d05565eaed2771cb17b1d3ae5a997109de6bead4ed36d085a41a"
    assert payload["issue"] == 538
    assert payload["physical_attestation"] is False
    assert payload["native_competing_same_world_causal_reward"] is False
    assert payload["production_go"] is False


@pytest.mark.parametrize("forward", [False, True])
def test_two_independently_s13_admitted_and_s15_issued_actions_close_s16(forward):
    issued, binding, supervisor = (
        _forward_owner_chain() if forward else _backward_owner_chain()
    )
    cmd, fake, receipt, result, closed = _execute_fake(
        issued, binding, supervisor, forward=forward,
    )
    assert cmd.forward_opt_in is forward
    assert cmd.control == ("forward" if forward else "back")
    assert cmd.effect == "set_control"
    assert cmd.duration_s == 0.2
    assert receipt.action_ref == (
        MOVE_FORWARD_ACTION_REF if forward else MOVE_BACKWARD_ACTION_REF
    )
    assert receipt.before_observation.seq == 1
    assert receipt.dispatch_receipt.seq == 2
    assert receipt.cleanup_receipt.seq == 3
    assert receipt.after_observation.seq == 4
    assert fake.sent == [
        ("observe",),
        ("set_control", issued.action_id, cmd.control, True),
        ("clear_controls", f"{issued.action_id}-s15-clear"),
        ("observe",),
    ]
    assert result.disposition is ActionOutcomeDisposition.OUTCOME
    assert result.reason_code == "observed_execution"
    assert supervisor.get(issued.action_id) is closed
    assert closed.is_terminal
    assert not supervisor.open_actions


def test_existing_backward_default_is_byte_compatible_with_explicit_false():
    issued, binding, _ = _backward_owner_chain()
    assert build_mineflayer_command(issued, binding) == build_mineflayer_command(
        issued, binding, allow_forward=False,
    )
    assert build_mineflayer_command(issued, binding).forward_opt_in is False


def test_forward_requires_explicit_optin_at_S15_and_separately_at_S16():
    issued, binding, _ = _forward_owner_chain()
    with pytest.raises(InvalidMineflayerExecutionData):
        build_mineflayer_command(issued, binding)
    cmd = build_mineflayer_command(issued, binding, allow_forward=True)
    assert cmd.forward_opt_in is True
    receipt = asyncio.run(
        execute_mineflayer_command(
            frozen_s17.successful_session(cmd), cmd,
            provenance=_p("forward-fake-consequence"),
        )
    )
    with pytest.raises(InvalidMineflayerExecutionData):
        interpret_world_consequence(
            issued, binding, receipt,
            provenance=_p("forward-default-s16-denial"),
        )
    assert interpret_world_consequence(
        issued, binding, receipt, provenance=_p("opt-in-s16"),
        allow_forward=True,
    ).reason_code == "observed_execution"


@pytest.mark.parametrize(("field", "value"), [
    ("action_ref", "MOVE_LEFT"),
    ("action_ref", "MOVE_BACKWARD"),
    ("control", "back"),
    ("control", "sprint"),
    ("effect", "teleport"),
    ("state", False),
    ("duration_s", 0.21),
    ("duration_s", 0.0),
    ("duration_s", 99.0),
    ("duration_s", 0.2 + 1e-9),
    ("forward_opt_in", False),
    ("forward_opt_in", None),
    ("forward_opt_in", 1),
    ("cleanup_action_id", "i7-forward-action"),
])
def test_unsafe_forward_commands_do_not_become_executable(field, value):
    issued, binding, _ = _forward_owner_chain()
    command = build_mineflayer_command(issued, binding, allow_forward=True)
    with pytest.raises(InvalidMineflayerExecutionData):
        replace(command, **{field: value})


@pytest.mark.parametrize(("field", "value"), [
    ("candidate_ref", "MOVE_AWAY"),
    ("candidate_ref", "WAIT"),
    ("candidate_ref", "MOVE_FORWARD " ),
    ("action_id", "other-action"),
    ("skill_execution_id", "other-skill-exec"),
    ("intent_id", "other-intent"),
    ("action_ref", "MOVE_RIGHT"),
])
def test_forward_cannot_use_foreign_or_unauthorized_s14_binding(field, value):
    issued, binding, _ = _forward_owner_chain()
    # Invalid identifiers can fail at the earlier frozen S14 typed
    # constructor; well-formed unauthorized changes reach S15's own gate.
    with pytest.raises(ValueError):
        wrong = replace(binding, **{field: value})
        build_mineflayer_command(issued, wrong, allow_forward=True)


def test_no_forward_optin_transfer_to_legacy_backwards_and_bool_forgery():
    issued, binding, _ = _backward_owner_chain()
    with pytest.raises(InvalidMineflayerExecutionData):
        build_mineflayer_command(issued, binding, allow_forward=True)
    with pytest.raises(InvalidMineflayerExecutionData):
        build_mineflayer_command(issued, binding, allow_forward=1)
    with pytest.raises(InvalidMineflayerExecutionData):
        build_mineflayer_command(issued, binding, allow_forward=None)


def test_s15_issued_currentness_not_merely_a_s14_proposed_action():
    issued, binding, supervisor = _forward_owner_chain()
    assert issued.events[-1].state is ActionState.ISSUED
    closed_cmd, _, _, _, _ = _execute_fake(
        issued, binding, supervisor, forward=True,
    )
    with pytest.raises(InvalidMineflayerExecutionData):
        build_mineflayer_command(issued, binding, allow_forward=True)
    assert closed_cmd.action_id == issued.action_id


def test_fake_receipts_are_not_real_native_competing_same_world_or_signed_goals():
    a_issued, a_binding, a_supervisor = _backward_owner_chain()
    b_issued, b_binding, b_supervisor = _forward_owner_chain()
    a = _execute_fake(a_issued, a_binding, a_supervisor, forward=False)
    b = _execute_fake(b_issued, b_binding, b_supervisor, forward=True)
    assert a[2].session_id == b[2].session_id == "s15-session"
    # Merely coincident session strings do NOT tie these independent fake
    # adapter process objects into a physically authenticated common World.
    assert a[1] is not b[1]
    assert a[2].action_id != b[2].action_id
    assert a[3].reason_code == b[3].reason_code == "observed_execution"
    # S16 provides no signed task-specific success/negative label.
    assert not hasattr(a[3], "goal_reached")
    assert not hasattr(b[3], "goal_reached")


def test_forward_unknown_movement_is_not_success_or_learning_feedback():
    issued, binding, _ = _forward_owner_chain()
    cmd = build_mineflayer_command(issued, binding, allow_forward=True)
    fake = frozen_s17.FakeSession((
        frozen_s17.observation(1, 0, 0),
        frozen_s17.effect(2, cmd.action_id, "set_control"),
        frozen_s17.effect(3, cmd.cleanup_action_id, "clear_controls"),
        frozen_s17.observation(4, 0, 0),
    ))
    consequence = asyncio.run(
        execute_mineflayer_command(fake, cmd, provenance=_p("no-motion"),
        )
    )
    assert consequence.status is WorldConsequenceStatus.UNDETERMINED
    outcome = interpret_world_consequence(
        issued, binding, consequence, provenance=_p("unavailable"),
        allow_forward=True,
    )
    assert outcome.disposition is ActionOutcomeDisposition.UNAVAILABLE


def test_dispatch_rejection_does_not_fabricate_goal_reward():
    issued, binding, _ = _forward_owner_chain()
    cmd = build_mineflayer_command(issued, binding, allow_forward=True)
    fake = frozen_s17.FakeSession((
        frozen_s17.observation(1, 0, 0),
        frozen_s17.effect(
            2, cmd.action_id, "set_control", result="rejected",
        ),
    ))
    consequence = asyncio.run(
        execute_mineflayer_command(
            fake, cmd, provenance=_p("rejected"),
        )
    )
    assert consequence.status is WorldConsequenceStatus.FAILED
    result = interpret_world_consequence(
        issued, binding, consequence,
        provenance=_p("known-rejection"),
        allow_forward=True,
    )
    assert result.disposition is ActionOutcomeDisposition.OUTCOME
    assert result.reason_code == "known_adapter_rejection"
    assert result.reason_code != "observed_execution"
