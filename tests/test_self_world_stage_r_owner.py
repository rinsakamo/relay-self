"""Stage R offline-only single writer: synthetic original S49-shaped frames.

The positive fixture synthesizes Action closures; ONLY a new separate, single
explicit DEV World run could attest the physical terminal/source/issuer.
"""
from __future__ import annotations

from dataclasses import replace
from unittest.mock import PropertyMock, patch

import pytest

import test_postmain_s42_world_contrast as s42
import test_self_world_native_feedback as n_fixture
from adapters.mineflayer.normal_action import (
    NormalActionReceipt,
    NormalActionRejected,
    NormalSessionActionExecutor,
    NormalWorldL0,
)
from adapters.mineflayer.self_world_stage_r_owner import (
    StageRDevOperatorLearningIssuer,
    StageRDevRejected,
    StageRDevSingleWriter,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    WorldChoiceRejected,
    select_world_conditioned_choice,
)


def _prepared():
    owner, near, _, event, _ = s42._pair()
    witness = n_fixture._synthetic_native_closed()
    sid = witness.original_probe.session_id
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="synthetic fixture",
        at_ns=1, provenance=Provenance("stage-r-test", "intent"),
    )
    host = NormalWorldL0(
        sid, "escape-threat", owner, max_events=3, max_action_requests=2,
    )
    executor = NormalSessionActionExecutor(sid, intent)
    issuer = StageRDevOperatorLearningIssuer(host, executor, intent)
    operator = StageRDevSingleWriter(host, executor, intent, issuer)
    frame = replace(
        event, session_id=sid, seq=8,
        snapshot=near.observation.snapshot,
    )
    probe = replace(
        near.observation, session_id=sid, seq=9,
        request_id=f"s49-actual:{sid}:event-8",
    )
    frame = replace(frame, snapshot=probe.snapshot)
    operator.observe_original_probe(probe)
    grant = L0ActionGrant(
        authority_id="synthetic-action-only", action_id="s49-native-move-8",
        intent_id="escape-threat", session_id=sid, event_seq=frame.seq,
        probe_seq=probe.seq, entity_id=near.entity_id, granted=True,
        provenance=Provenance("stage-r-test", "synthetic-l0-grant"),
    )
    step = host.decide(frame, probe, grant=grant)
    assert step.asks_for_action
    consequence = replace(
        witness.consequence,
        after_observation=replace(
            witness.consequence.after_observation, seq=20,
        ),
    )
    witness = replace(
        witness, consequence=consequence, original_probe=probe,
    )
    receipt = NormalActionReceipt(
        witness.terminal, witness.consequence, probe.provenance,
    )
    next_probe = replace(
        probe, seq=23, request_id=f"s49-actual:{sid}:event-21",
    )
    return operator, host, executor, step, witness, receipt, next_probe


def _sealed():
    operator, host, executor, step, witness, receipt, following = _prepared()
    operator.observe_original_closed(witness)
    operator.seal_original_action(step, receipt)
    return operator, host, executor, step, witness, receipt, following


def test_stage_r_s49_single_writer_uses_later_source_and_keeps_one_action_owner():
    operator, host, executor, step, witness, receipt, following = _sealed()
    previous = host.retained
    assert previous.revision == 1 and previous.value == 4
    assert operator.committed is None
    assert operator.current is previous
    operator.observe_original_probe(following)
    assert operator.committed is not None
    assert operator.committed.previous_state is previous
    assert host.retained is operator.current is operator.committed.new_state
    assert host.retained.revision == 2
    assert host.retained.value == 4  # HOLD, no positive reward
    assert operator.committed.record.feedback_id == operator.committed.proposal.feedback.feedback_id
    assert operator.committed.record.authority_provenance.source == "s49-dev-learning-owner"
    # The previous Action step cannot be admitted against the new owner.
    with pytest.raises(StageRDevRejected):
        operator.require_joint_admission_owner(step)
    summary = operator.summary()
    assert summary["joint_l0_s14_owner_identity"]
    assert summary["operator_s10_grants"] == 1
    assert summary["s10_hold_commits"] == 1
    assert summary["original_action_closures"] == 1
    assert not summary["grant_independent_external_attestation"]
    assert not summary["hold_reward_or_policy_gain"]
    assert not summary["additional_action_issuer"]
    assert executor.supervisor.open_actions == ()
    assert host.action_requests == 1


def test_stage_r_first_closed_requires_later_native_probe_before_commit():
    operator, host, _, _, witness, _, _ = _sealed()
    assert operator.current is host.retained
    assert operator.committed is None
    assert host.retained.revision == 1
    assert operator.summary()["pending_unsealed_or_unknown"]
    with pytest.raises(StageRDevRejected):
        operator.observe_original_closed(witness)


@pytest.mark.parametrize("case", (
    "no_seal", "stale_next_seq", "foreign_session", "bad_event_number",
    "next_event_is_future", "missing_request", "duplicate_probe",
    "foreign_intent", "swapped_l0_owner", "open_action",
))
def test_stage_r_denies_missing_terminal_or_correlated_future_source(case):
    operator, host, executor, step, witness, receipt, next_probe = _prepared()
    old = host.retained
    operator.observe_original_closed(witness)
    if case != "no_seal":
        operator.seal_original_action(step, receipt)
    if case == "stale_next_seq":
        next_probe = replace(next_probe, seq=20)
    elif case == "foreign_session":
        next_probe = replace(next_probe, session_id="elsewhere")
    elif case == "bad_event_number":
        next_probe = replace(next_probe, request_id="forge")
    elif case == "next_event_is_future":
        next_probe = replace(
            next_probe, request_id=f"s49-actual:{next_probe.session_id}:event-24",
        )
    elif case == "missing_request":
        next_probe = replace(next_probe, request_id=None)
    elif case == "duplicate_probe":
        next_probe = replace(next_probe, seq=witness.original_probe.seq)
    elif case == "foreign_intent":
        operator._intent.complete(
            "escape-threat", reason="finished", at_ns=2,
            provenance=Provenance("stage-r-test", "completed"),
        )
    elif case == "swapped_l0_owner":
        host.retained = replace(host.retained)
    elif case == "open_action":
        # Simulate an incomplete ORIGINAL supervisor terminal, not another
        # Action issuer; the Stage R owner must reject its open tuple.
        with patch.object(
            type(executor.supervisor), "open_actions",
            new_callable=PropertyMock, return_value=(object(),),
        ):
            with pytest.raises((StageRDevRejected, ValueError)):
                operator.observe_original_probe(next_probe)
        assert operator.committed is None
        return
    with pytest.raises((StageRDevRejected, ValueError)):
        operator.observe_original_probe(next_probe)
    assert operator.committed is None
    assert operator.summary()["operator_s10_grants"] == 0
    assert operator.current is old


def test_stage_r_default_frozen_and_no_dev_install_grant():
    original, near, _, _, _ = s42._pair()
    host = NormalWorldL0("default-session", "escape-threat", original)
    with pytest.raises(NormalActionRejected):
        host.install_stage_r_dev_successor(token=object(), commit=None)
    native = replace(
        near, observation=replace(
            near.observation, session_id="default-session",
        ),
    )
    default = select_world_conditioned_choice(
        native, original, expected_session_id="default-session",
        expected_entity_id=native.entity_id,
    )
    assert default.selection is WorldChoiceKind.MOVE_AWAY
    with pytest.raises(NormalActionRejected):
        host.bind_stage_r_dev_owner(token="not-a-single-owner-token")
    with pytest.raises(WorldChoiceRejected):
        select_world_conditioned_choice(
            native, replace(original, value=3, last_update=None),
            expected_session_id="default-session",
            expected_entity_id=native.entity_id,
        )
