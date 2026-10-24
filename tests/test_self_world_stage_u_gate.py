"""Stage U source-attested in-process issuer and nonexecuting WAIT gate.

Every input below is explicitly SYNTHETIC: priming the original executor
supervisor simulates its in-process registry, NOT a physical qualification.
"""
from __future__ import annotations

from dataclasses import replace
from unittest.mock import PropertyMock, patch

import pytest

import test_postmain_s42_world_contrast as s42
import test_self_world_stage_s_feedback as s_fixture
from adapters.mineflayer.normal_action import (
    NormalActionReceipt,
    NormalSessionActionExecutor,
    NormalWorldL0,
)
from adapters.mineflayer.self_world_stage_u_gate import (
    StageUDevOriginalExecutorIssuer,
    StageUDevRejected,
    StageUWaitBoundary,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant
from relay_self.world_conditioned_choice import WorldChoiceKind


def _fixture(*, increase: bool = False):
    original, _, _, event, _ = s42._pair()
    w = s_fixture._synthetic_targeted_witness(
        0.0 if increase else 0.5,
        1.0 if increase else 0.0,
    )
    sid = w.original_probe.session_id
    old_entity = w.original_probe.snapshot.nearby_entities[0]
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="synthetic safe-route test",
        at_ns=1, provenance=Provenance("stage-u-synthetic", "intent"),
    )
    host = NormalWorldL0(
        sid, "escape-threat", original,
        max_events=3, max_action_requests=2,
    )
    token = object()
    host.bind_stage_t_dev_preview(token=token)
    executor = NormalSessionActionExecutor(sid, intent)
    issuer = StageUDevOriginalExecutorIssuer(
        host, executor, intent, preview_token=token,
    )
    first = replace(event, session_id=sid, seq=8, snapshot=w.original_probe.snapshot)
    probe = replace(w.original_probe, seq=9)
    step = host.decide(
        first, probe, grant=L0ActionGrant(
            authority_id="stage-u-synthetic-original-action-only",
            action_id=w.terminal.action_id,
            intent_id="escape-threat", session_id=sid,
            event_seq=8, probe_seq=9, entity_id=old_entity.entity_id,
            granted=True, provenance=Provenance(
                "stage-u-synthetic", "action-grant-not-real",
            ),
        ),
    )
    assert step.asks_for_action
    before = w.consequence.before_observation
    after = w.consequence.after_observation
    assert before is not None and after is not None
    consequence = replace(
        w.consequence, before_observation=replace(before, seq=11),
        after_observation=replace(after, seq=14),
    )
    w = replace(w, original_probe=probe, consequence=consequence)
    receipt = NormalActionReceipt(w.terminal, consequence, probe.provenance)
    # Explicit synthetic stand-in for the actual executor registry and
    # one physically dispatched Action. No new physical Action is issued.
    executor.supervisor._lifecycles[step.action_request_id] = w.terminal
    executor._dispatched.add(step.action_request_id)

    next_target = replace(old_entity, entity_id=old_entity.entity_id + 8)
    snap = replace(
        probe.snapshot, nearby_entities=(next_target,),
    )
    event2 = replace(
        first, seq=16, snapshot=snap,
    )
    probe2 = replace(
        probe, seq=17, request_id=f"s49-actual:{sid}:event-16",
        snapshot=snap,
    )
    inputs = {
        "step": step,
        "original_closed": w,
        "original_receipt": receipt,
        "next_native_event": event2,
        "next_native_probe": probe2,
    }
    return issuer, host, executor, intent, inputs


@pytest.mark.parametrize(("increase","value","expected","boundary"), (
    (
        False, 3, "WAIT",
        StageUWaitBoundary.NEAR_WAIT_READ_ONLY_NO_ACTION,
    ),
    (
        True, 5, "MOVE_AWAY",
        StageUWaitBoundary.MOVE_NEEDS_SEPARATE_ACTION_GRANTS,
    ),
))
def test_u_local_issuer_exact_terminal_and_nonexecuting_original_s14_preview(
    increase, value, expected, boundary,
):
    issuer, host, executor, _, inputs = _fixture(increase=increase)
    old = host.retained
    result = issuer.commit_once(**inputs)
    assert result.exact_supervised_terminal
    assert result.exact_s10_owner
    assert result.action_executor_same_owner
    assert result.local_issuer_separate_from_s17
    assert result.commit.previous_state is old
    assert result.commit.new_state is host.retained
    assert result.commit.new_state.revision == 2
    assert result.commit.new_state.value == value
    assert result.commit.record.authority_provenance.source == (
        "stage-u-original-executor-local-issuer"
    )
    assert result.preview.original_l0_candidate == "MOVE_AWAY"
    assert result.preview.new_l0_candidate == expected
    assert result.preview.new_s14_candidate == expected
    assert result.preview.s14_admission == "admitted"
    assert result.wait_boundary is boundary
    assert not result.physical_wait_permitted
    assert not result.near_wait_safety_attested
    assert not result.external_issuer_attested
    assert not result.action_issued
    assert not result.minecraft_session_started
    assert not result.on_off_sham_causal_gain_attested
    assert executor.supervisor.open_actions == ()
    assert host.action_requests == 1 and host.events == 1
    # Neither grant nor callback can mint a second session S10 update.
    with pytest.raises(StageUDevRejected, match="consumed"):
        issuer.commit_once(**inputs)


@pytest.mark.parametrize("case", (
    "missing_original_supervisor", "copied_terminal", "copied_receipt_terminal",
    "undispatched_action", "foreign_next_session", "replayed_next_probe",
    "wrong_next_request", "wrong_next_event", "no_original_action",
    "copied_original_receipt_consequence", "foreign_terminal_intent",
    "unknown_original_action", "incomplete_world_frame", "wrong_target",
    "open_original_action", "foreign_intent", "cross_host_owner",
    "s16_world_forgery", "no_original_terminal_outcome",
))
def test_u_rejects_synthetic_sham_original_action_or_next_source(case):
    issuer, host, executor, intent, inputs = _fixture()
    original = host.retained
    w = inputs["original_closed"]
    receipt = inputs["original_receipt"]
    probe = inputs["next_native_probe"]
    event = inputs["next_native_event"]
    if case == "missing_original_supervisor":
        executor.supervisor._lifecycles.clear()
    elif case == "copied_terminal":
        clone = replace(w.terminal)
        inputs["original_closed"] = replace(w, terminal=clone)
        inputs["original_receipt"] = replace(receipt, terminal=clone)
    elif case == "copied_receipt_terminal":
        inputs["original_receipt"] = replace(receipt, terminal=replace(w.terminal))
    elif case == "undispatched_action":
        executor._dispatched.clear()
    elif case == "foreign_next_session":
        inputs["next_native_probe"] = replace(probe, session_id="other")
    elif case == "replayed_next_probe":
        inputs["next_native_probe"] = replace(probe, seq=14)
    elif case == "wrong_next_request":
        inputs["next_native_probe"] = replace(probe, request_id="sham")
    elif case == "wrong_next_event":
        inputs["next_native_event"] = replace(event, seq=18)
    elif case == "no_original_action":
        host._used_action_ids.clear()
    elif case == "copied_original_receipt_consequence":
        inputs["original_receipt"] = replace(
            receipt, consequence=replace(w.consequence),
        )
    elif case == "foreign_terminal_intent":
        inputs["original_closed"] = replace(
            w, terminal=replace(w.terminal, intent_id="different"),
        )
    elif case == "unknown_original_action":
        inputs["original_closed"] = replace(
            w, terminal=replace(w.terminal, action_id="fake-action"),
        )
    elif case == "incomplete_world_frame":
        cov = replace(
            probe.snapshot.nearby_entities_coverage,
            truncated=True, candidate_count=17,
        )
        # A valid protocol-truncated reading emits the full native cap.
        limit = cov.max_entities
        entity = probe.snapshot.nearby_entities[0]
        facts = (entity,) + tuple(
            replace(entity, entity_id=entity.entity_id + i, name="item")
            for i in range(1, limit)
        )
        cov = replace(cov, candidate_count=limit + 1)
        inputs["next_native_probe"] = replace(
            probe, snapshot=replace(
                probe.snapshot, nearby_entities=facts,
                nearby_entities_coverage=cov,
            ),
        )
    elif case == "wrong_target":
        snapshot = replace(
            probe.snapshot,
            nearby_entities=(),
            nearby_entities_coverage=replace(
                probe.snapshot.nearby_entities_coverage, candidate_count=0,
            ),
        )
        inputs["next_native_probe"] = replace(probe, snapshot=snapshot)
    elif case == "foreign_intent":
        intent.complete(
            "escape-threat", reason="expired", at_ns=2,
            provenance=Provenance("stage-u-synthetic", "expired"),
        )
    elif case == "cross_host_owner":
        host.retained = replace(host.retained)
    elif case == "s16_world_forgery":
        inputs["original_closed"] = replace(
            w, interpretation=replace(
                w.interpretation, reason_code="prediction_match",
            ),
        )
    elif case == "no_original_terminal_outcome":
        inputs["original_closed"] = replace(
            w, terminal=replace(w.terminal, action_id="other-action"),
        )
    if case == "open_original_action":
        with patch.object(
            type(executor.supervisor), "open_actions",
            new_callable=PropertyMock, return_value=(object(),),
        ):
            with pytest.raises((StageUDevRejected, ValueError)):
                issuer.commit_once(**inputs)
    else:
        with pytest.raises((StageUDevRejected, ValueError, StopIteration)):
            issuer.commit_once(**inputs)
    if case == "cross_host_owner":
        # This negative deliberately replaces the host reference itself.
        # The issuer must reject and leave that copy uncommitted.
        assert host.retained is not original
        assert host.retained.revision == original.revision
        assert host.retained.value == original.value
    else:
        assert host.retained is original
    assert host._stage_t_dev_commit is None


def test_u_wait_plan_admitted_does_not_authorize_near_wait_in_world():
    issuer, _, executor, _, data = _fixture(increase=False)
    out = issuer.commit_once(**data)
    assert out.preview.new_l0_candidate == WorldChoiceKind.WAIT.value
    assert out.preview.s14_admission == "admitted"
    assert out.wait_boundary is StageUWaitBoundary.NEAR_WAIT_READ_ONLY_NO_ACTION
    assert out.near_wait_safety_attested is False
    assert out.physical_wait_permitted is False
    assert out.action_issued is False
    assert executor._count == 0  # no original execute() invoked
