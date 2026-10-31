"""Original S49 after-closure observer -> SelfBody typed S16/native Present.

All constructed Action lifecycles and Mineflayer probes here are synthetic;
the source object types and projection functions are the ORIGINAL owners.
No physical World or new issuer is run by these tests.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer import normal_action
from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.normal_action import (
    NormalActionClosedReadback,
    observe_closed_native_actions,
)
from adapters.mineflayer.python_protocol import MineflayerEffectResult
from adapters.mineflayer.self_body_s50_original_closure import (
    SelfBodyS50ClosedOwnerLease,
    SelfBodyS50ClosedOwnerRejected,
    observe_original_s49_selfbody_closure,
)
from relay_self.action import ActionEvent, ActionLifecycle, ActionState, _ActionLineage
from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.self_body import BodyOrigin
from test_self_body import outcome, prov
from test_self_body_s50_motion_companion import s50
from test_self_live_think import native_probe


def synthetic_original_closed(
    *, status=WorldConsequenceStatus.EXECUTED, interpretation=None,
    action="move1", session="S", before_seq=8, after_seq=12,
) -> NormalActionClosedReadback:
    # Synthetic but structurally owner-native lifecycle; never imply World run.
    states = (
        ActionEvent(ActionState.PROPOSED, 100, prov("p")),
        ActionEvent(ActionState.AUTHORIZED, 101, prov("a"), authority="grant"),
        ActionEvent(ActionState.ISSUED, 102, prov("i"), deadline_ns=200),
        ActionEvent(ActionState.OUTCOME, 103, prov("o")),
    )
    terminal = ActionLifecycle(
        action_id=action, skill_execution_id="skill1",
        intent_id="intent1", _events=states, _revision=3,
        _lineage=_ActionLineage(current_revision=3),
    )
    before = native_probe(before_seq, 2.0, sid=session)
    after = native_probe(after_seq, 2.0, sid=session)
    consequence = WorldConsequence(
        action_id=action, binding_id="bind1", action_ref="MOVE_BACKWARD",
        status=status, session_id=session,
        before_observation=before,
        dispatch_receipt=MineflayerEffectResult(
            session, before_seq+1, action, "set_control", "applied", None,
        ),
        cleanup_receipt=MineflayerEffectResult(
            session, before_seq+2, action + "-clear",
            "clear_controls", "applied", None,
        ),
        after_observation=after, movement_distance=0.627,
        cleanup_attempted=True, error=None,
        provenance=prov("world-consequence"),
    )
    return NormalActionClosedReadback(
        terminal=terminal,
        interpretation=outcome(ActionOutcomeDisposition.OUTCOME)
        if interpretation is None else interpretation,
        consequence=consequence,
        original_probe=native_probe(5, 2.0, sid=session),
    )


def test_original_s49_closure_sealed_once_and_joined_without_new_present():
    lease = SelfBodyS50ClosedOwnerLease(self_id="self")
    original = synthetic_original_closed()
    with observe_original_s49_selfbody_closure(lease):
        # Same API the ORIGINAL normal_action.execute invokes after S16 closure;
        # here we supply a synthetic ORIGINAL-TYPED readback offline.
        lease.observe_original_closed(original)
    assert lease.status()["status"] == "ONE_ORIGINAL_TYPED_S16_ACTION_READY"
    assert lease.status()["original_closures_seen"] == 1
    result = lease.consume_s50_once(s50())
    assert result.self_body.outcome is original.interpretation
    assert result.self_body.observation.action_id == "move1"
    assert result.self_body.observation.native_seq == 12
    assert result.self_body.observation.request_id == original.consequence.after_observation.request_id
    assert result.self_body.observation.source_provenance == (
        original.consequence.after_observation.provenance
    )
    assert result.self_body.observed("health").origin is BodyOrigin.OBSERVATION
    assert result.self_body.observed("paper_motion").origin is BodyOrigin.UNKNOWN
    assert result.cognitive_summary()["changed_with_last_reported_input_off"] == (251,252)
    assert not result.physically_stopped_attested
    assert result.effective_clear_world_tick == "NOT_ATTESTED"
    assert result.p1_wait_granted is False
    assert lease.status()["status"] == "ONE_S50_DIAGNOSTIC_JOIN_CONSUMED"
    assert lease.status()["typed_original_ready"] is False
    with pytest.raises(SelfBodyS50ClosedOwnerRejected):
        lease.consume_s50_once(s50())


def test_duplicate_owner_closure_revokes_one_slot_and_does_not_veto_original():
    lease = SelfBodyS50ClosedOwnerLease(self_id="self")
    original = synthetic_original_closed()
    lease.observe_original_closed(original)
    lease.observe_original_closed(original)
    assert lease.status()["status"] == "REVOKED_ON_BAD_OR_MULTIPLE_ORIGINAL_CLOSURE"
    assert lease.status()["original_closures_seen"] == 2
    with pytest.raises(SelfBodyS50ClosedOwnerRejected):
        lease.consume_s50_once(s50())


@pytest.mark.parametrize("attack", [
    "unknown_s16", "missing_before", "foreign_original", "wrong_action",
    "before_not_after", "invalid_decision_probe", "foreign_world_consequence",
    "missing_callback", "observer_non_typed",
])
def test_undetermined_or_foreign_original_never_mints_native_view(attack):
    lease = SelfBodyS50ClosedOwnerLease(self_id="self", expected_action_id="move1")
    original = synthetic_original_closed()
    if attack == "unknown_s16":
        original = replace(
            original, interpretation=outcome(ActionOutcomeDisposition.UNKNOWN),
        )
    elif attack == "missing_before":
        original = replace(original, consequence=replace(
            original.consequence, status=WorldConsequenceStatus.FAILED,
            before_observation=None, after_observation=None,
            dispatch_receipt=None, cleanup_receipt=None,
            movement_distance=None, cleanup_attempted=False, error="simulated",
        ))
    elif attack == "foreign_original":
        original = replace(original, original_probe=native_probe(5, 2, sid="other"))
    elif attack == "wrong_action":
        lease = SelfBodyS50ClosedOwnerLease(
            self_id="self", expected_action_id="not-this-action",
        )
    elif attack == "before_not_after":
        original = replace(original, original_probe=native_probe(11, 2, sid="S"))
    elif attack == "invalid_decision_probe":
        original = replace(
            original, original_probe=replace(
                original.original_probe, request_id=None, kind="health",
            ),
        )
    elif attack == "foreign_world_consequence":
        original = replace(original, consequence=replace(
            original.consequence, session_id="other",
        ))
    elif attack == "missing_callback":
        pass
    elif attack == "observer_non_typed":
        original = object()
    if attack != "missing_callback":
        lease.observe_original_closed(original)
    assert lease.status()["typed_original_ready"] is False
    with pytest.raises(SelfBodyS50ClosedOwnerRejected):
        lease.consume_s50_once(s50())


def test_invalid_s50_consumes_and_revokes_original_one_slot():
    lease = SelfBodyS50ClosedOwnerLease(self_id="self")
    lease.observe_original_closed(synthetic_original_closed())
    malformed = s50()
    malformed["physically_stopped_attested"] = True
    with pytest.raises(ValueError):
        lease.consume_s50_once(malformed)
    assert lease.status()["status"] == "REVOKED_ON_INVALID_S50_SOURCE"
    with pytest.raises(SelfBodyS50ClosedOwnerRejected):
        lease.consume_s50_once(s50())


def test_expire_clears_typed_source_and_does_not_leak_across_epoch():
    lease = SelfBodyS50ClosedOwnerLease(self_id="self")
    lease.observe_original_closed(synthetic_original_closed())
    lease.close()
    assert lease.status()["status"] == "EXPIRED_WITHOUT_S50_SOURCE"
    assert lease.status()["typed_original_ready"] is False
    with pytest.raises(SelfBodyS50ClosedOwnerRejected):
        lease.consume_s50_once(s50())


def test_original_context_callback_slot_resets_without_installing_issuer():
    lease = SelfBodyS50ClosedOwnerLease(self_id="self")
    with observe_original_s49_selfbody_closure(lease):
        lease.observe_original_closed(synthetic_original_closed())
    # Existing original callback context can be reused after this separate lease.
    with observe_closed_native_actions(lambda _: None):
        pass
    assert lease.status()["new_action_issuers"] == 0
    assert lease.status()["new_native_probes"] == 0
    assert lease.status()["new_packet_writes"] == 0
    assert lease.status()["new_s16_outcome_owners"] == 0
    lease.close()

def test_existing_owner_callback_context_holds_the_exact_one_slot_source():
    # The original normal_action module, not a replacement executor, owns this
    # ContextVar and reads it only after its ActionSupervisor terminal.
    assert normal_action._READ_ONLY_CLOSURE.get() is None
    lease = SelfBodyS50ClosedOwnerLease(self_id="self")
    original = synthetic_original_closed()
    with observe_original_s49_selfbody_closure(lease):
        registered = normal_action._READ_ONLY_CLOSURE.get()
        assert callable(registered)
        assert registered.__self__ is lease
        registered(original)
        assert lease.status()["typed_original_ready"] is True
    assert normal_action._READ_ONLY_CLOSURE.get() is None
    result = lease.consume_s50_once(s50())
    assert result.self_body.outcome is original.interpretation
    assert not result.native_present_minted


