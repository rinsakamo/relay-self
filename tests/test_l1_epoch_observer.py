"""L8: actual existing S coordinator return -> L1 read-only comparison, offline."""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_epoch_plan as s3
import test_l1_s_choice_shadow as l7
from relay_self.action_supervision import ActionSupervisor
from relay_self.epoch_plan import (
    CognitionInvocation,
    EpochBinding,
    EpochWorkItem,
    compile_epoch_plan,
    coordinate_planned_epoch,
)
from relay_self.execution_descriptor import S2_DESCRIPTOR_SET, s2_capability_plan
from relay_self.l1_epoch_observer import SEpochObservationRejected, observe_s_epoch_l1
from relay_self.l1_s_choice_shadow import SChoiceContrastStatus
from relay_self.provenance import Provenance
from relay_self.runtime_coordination import coordinate_decision_epoch
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    select_world_conditioned_choice,
)


@pytest.fixture(scope="module")
def near():
    return l7.scenario()


@pytest.fixture(scope="module")
def far():
    return l7.scenario(near=False, tags=("alpha", "novel_cue"))


def run_s_epoch(native, retained, *, supervisor=None, at_ns=10):
    """Execute S's original coordinator, not the L comparison."""
    owner = supervisor or ActionSupervisor()
    calls = []

    def runner(observation):
        calls.append(observation)
        return select_world_conditioned_choice(
            observation, retained,
            expected_session_id=observation.observation.session_id,
            expected_entity_id=observation.entity_id,
        )

    result = coordinate_decision_epoch(
        owner, at_ns=at_ns,
        provenance=Provenance("synthetic-s-epoch", "S-owned-test-request"),
        decision_step=lambda: native,
        relay_engine=runner,
    )
    assert calls == [native]
    return owner, result


def test_actual_s_coordinator_result_compares_with_retained_l1_without_override(near):
    initial, retained, native, s_choice, learned = near
    owner, epoch = run_s_epoch(native, retained)
    assert epoch.cognition_requested
    assert epoch.cognition_result == s_choice
    before_owner = owner.last_at_ns
    before_memory = learned.cognition
    observed = observe_s_epoch_l1(
        epoch, native=native, retained=retained,
        learning=learned, retention_enabled=True,
    )
    assert observed.s_epoch is epoch
    assert observed.comparison.status is SChoiceContrastStatus.L1_DIFFERS
    assert observed.comparison.s_choice is WorldChoiceKind.MOVE_AWAY
    assert observed.comparison.l1_shadow_ref == "WAIT"
    assert observed.comparison.s_choice_kept
    assert observed.action_issues == observed.habit_grants == observed.learning_updates == 0
    assert not observed.action_authority
    assert owner.last_at_ns == before_owner
    assert owner.open_actions == ()
    assert learned.cognition is before_memory
    assert initial.memories == ()


def test_same_s_epoch_retention_off_has_no_shadow_and_no_new_cognition(near):
    _, retained, native, choice, learned = near
    _, epoch = run_s_epoch(native, retained)
    assert epoch.cognition_result == choice
    # L6 retention-OFF is a different immutable Memory result from the same S source.
    _, _, _, off_choice, off_learned = l7.scenario(enabled=False)
    assert off_choice == choice
    off = observe_s_epoch_l1(
        epoch, native=native, retained=retained,
        learning=off_learned, retention_enabled=False,
    )
    on = observe_s_epoch_l1(
        epoch, native=native, retained=retained,
        learning=learned, retention_enabled=True,
    )
    assert off.comparison.status is SChoiceContrastStatus.WITHHELD
    assert off.comparison.l1_shadow_ref is None
    assert on.comparison.l1_shadow_ref == "WAIT"
    assert off.s_epoch is on.s_epoch is epoch
    assert off.action_issues == on.action_issues == 0


def test_far_s_epoch_still_waits_when_l1_disagrees(far):
    _, retained, native, expected, learned = far
    _, epoch = run_s_epoch(native, retained)
    assert epoch.cognition_result == expected
    result = observe_s_epoch_l1(
        epoch, native=native, retained=retained,
        learning=learned, retention_enabled=True,
    )
    assert result.comparison.status is SChoiceContrastStatus.L1_DIFFERS
    assert result.comparison.s_choice is WorldChoiceKind.WAIT
    assert result.comparison.l1_shadow_ref == "MOVE_AWAY"
    assert result.action_issues == 0


def test_original_planned_epoch_cognition_is_consumed_without_new_binding(near):
    _, retained, native, _, learned = near
    calls = []
    bound = EpochBinding(
        work_id="bounded-1", operator_id="ctl.bounded_cognition",
        invoke=lambda: CognitionInvocation(
            request=native,
            runner=lambda observed: (
                calls.append(observed),
                select_world_conditioned_choice(
                    observed, retained,
                    expected_session_id=observed.observation.session_id,
                    expected_entity_id=observed.entity_id,
                ),
            )[1],
        ),
    )
    plan = compile_epoch_plan(
        s2_capability_plan(enabled_ids=frozenset({"CTL"})),
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                work_id="bounded-1", operator_id="ctl.bounded_cognition",
                trigger_ref="s-owner-source-qualified-native",
            ),
        ),
        bindings=(bound,),
    )
    supervisor = ActionSupervisor()
    epoch = coordinate_planned_epoch(
        supervisor, plan, bindings=(bound,), at_ns=10,
        provenance=Provenance("synthetic-s-epoch", "planned-s-epoch"),
    )
    assert calls == [native]  # One S invocation, no second L invocation.
    before_clock = supervisor.last_at_ns
    observed = observe_s_epoch_l1(
        epoch, native=native, retained=retained,
        learning=learned, retention_enabled=True,
    )
    assert observed.planned_work_ids == ("bounded-1",)
    assert observed.s_epoch is epoch.decision
    assert observed.comparison.status is SChoiceContrastStatus.L1_DIFFERS
    assert calls == [native]
    assert supervisor.last_at_ns == before_clock
    assert observed.action_issues == 0


@pytest.mark.parametrize("fault", [
    "not_requested", "non_s_result", "missing_s_result",
    "fake_s_selection", "wrong_native", "unadmitted_probe",
    "foreign_session", "off_switch_with_on_learning",
    "false_authority", "fake_planned_work", "not_an_epoch",
])
def test_invalid_epoch_or_foreign_source_cannot_cross_l1_seam(near, far, fault):
    _, retained, native, _, learned = near
    _, epoch = run_s_epoch(native, retained)
    enabled = True
    if fault == "not_requested":
        epoch = replace(epoch, cognition_requested=False)
    elif fault == "non_s_result":
        epoch = replace(epoch, cognition_result={"choice": "WAIT"})
    elif fault == "missing_s_result":
        epoch = replace(epoch, cognition_result=None)
    elif fault == "fake_s_selection":
        epoch = replace(epoch, cognition_result=replace(
            epoch.cognition_result, selection=WorldChoiceKind.WAIT,
        ))
    elif fault == "wrong_native":
        native = far[2]
    elif fault == "unadmitted_probe":
        learned = replace(learned, admitted_current_probe_sha256=frozenset())
    elif fault == "foreign_session":
        learned = replace(learned, current=replace(
            learned.current, session_id="foreign",
        ))
    elif fault == "off_switch_with_on_learning":
        enabled = False
    elif fault == "false_authority":
        learned = replace(learned, action_authority=True)
    elif fault == "fake_planned_work":
        from relay_self.epoch_plan import PlannedDecisionEpochResult
        epoch = PlannedDecisionEpochResult(epoch, (), ())
    elif fault == "not_an_epoch":
        epoch = epoch.cognition_result
    with pytest.raises(SEpochObservationRejected):
        observe_s_epoch_l1(
            epoch, native=native, retained=retained,
            learning=learned, retention_enabled=enabled,
        )


@pytest.mark.parametrize("case", ["timeout", "still_in_flight"])
def test_original_s_supervisor_action_boundary_is_checked_first(near, case):
    _, retained, native, _, learned = near
    supervisor = s3.running_supervisor(deadline_ns=50)
    _, epoch = run_s_epoch(
        native, retained, supervisor=supervisor,
        at_ns=50 if case == "timeout" else 10,
    )
    if case == "timeout":
        assert len(epoch.timed_out_actions) == 1
    else:
        assert epoch.next_action_deadline_ns == 50
    with pytest.raises(SEpochObservationRejected, match="quiescent"):
        observe_s_epoch_l1(
            epoch, native=native, retained=retained,
            learning=learned, retention_enabled=True,
        )
    assert supervisor.get("action-1").state.value in ("timeout", "issued")


def test_mutating_l1_comparison_never_issues_s_action(near):
    _, retained, native, _, learned = near
    supervisor, epoch = run_s_epoch(native, retained)
    before = (supervisor.last_at_ns, supervisor.open_actions, learned.cognition)
    a = observe_s_epoch_l1(
        epoch, native=native, retained=retained,
        learning=learned, retention_enabled=True,
    )
    b = observe_s_epoch_l1(
        epoch, native=native, retained=retained,
        learning=learned, retention_enabled=True,
    )
    assert a == b
    assert a.action_issues == 0
    assert (supervisor.last_at_ns, supervisor.open_actions, learned.cognition) == before
    assert not hasattr(a, "issue") and not hasattr(a, "grant")
