"""I2b: real original lane methods with a controlled CPU-only provider stub.

No real llama-server/Gemma/Paper process/World is created by these tests.
"""
from __future__ import annotations

import asyncio
import threading
from dataclasses import replace

import pytest

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from relay_self.i_lane_i2_original_exploration_handoff_dev import (
    prepare_i2_original_goal_handoff,
)
from relay_self.i_lane_i2b_original_shared_l1_dev import (
    I2bSharedL1Hold,
    read_i2b_original_shared_l1_result,
    run_i2b_original_shared_l1,
    submit_i2b_original_shared_l1,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionMode, ProviderDecision
from relay_self.resident_llama_inference_lane_dev import (
    LlamaCppSingleSlotWitness,
    ResidentGpuLaneError,
    ResidentLlamaInferenceLane,
)
from test_bd1b_owner_source_dev import _files
from test_i_lane_i2_original_exploration_handoff_dev import (
    _args,
    _configured_both,
)


def _fixture(tmp_path, monkeypatch, *, exploration=True, selection="1",
             entered=None, released=None, busy=False):
    case = _configured_both(tmp_path, monkeypatch, exploration=exploration)
    bridge = case[1]
    provider = LlamaCppRelayProvider(
        endpoint="http://127.0.0.1:18999/v1/chat/completions",
        model="synthetic-no-http", timeout=1.0,
    )
    witness = LlamaCppSingleSlotWitness(
        provider=provider, backend_ref="i2b-synthetic-backend",
    )
    lane = ResidentLlamaInferenceLane(
        provider=provider, cognitive_work=bridge.cognitive_work, witness=witness,
    )
    # Replace ONLY the provider and idle witness (not submit/result/lock/ticket
    # methods), so these tests exercise the original resident lane machinery.
    def mock_idle():
        if busy:
            raise ResidentGpuLaneError("synthetic busy slot")
        from relay_self.resident_llama_inference_lane_dev import LlamaSlotIdleReceipt
        return LlamaSlotIdleReceipt(lane.backend_ref, 0, 1, False, "cpu-stub")
    def mock_provider(request, *, mode):
        assert mode is CognitionMode.BOUNDED
        assert not request.think_allowed
        if entered is not None:
            entered.set()
        if released is not None:
            assert released.wait(4.0)
        if selection is None:
            return ProviderDecision.unresolved(reason="synthetic unresolved")
        return ProviderDecision.resolved(selection)
    lane.witness.require_idle = mock_idle
    lane.provider = mock_provider
    # The original I2 CPU-only entry must still run before lane attachment.
    # _prepared below simulates the existing bridge's owned attach transition.
    return case, lane


def _prepared(case, lane, sid="A"):
    attached = case[1].inference_lane is lane
    h = prepare_i2_original_goal_handoff(
        **_args(case, sid), i2b_read_attached_lane=attached,
    )
    if not attached:
        case[1].inference_lane = lane  # synthetic prior bridge attachment
    return h


def _submit(case, lane, sid="A"):
    h = _prepared(case, lane, sid)
    return submit_i2b_original_shared_l1(
        **{k: v for k, v in _args(case, sid).items() if k != "self_id"},
        handoff=h, lane=lane,
    )


def _read(case, lane, item):
    return read_i2b_original_shared_l1_result(
        bridge=case[1], boot=case[2], world=case[3], links=case[4],
        submission=item, lane=lane,
    )


@pytest.mark.parametrize(("selection", "status"), [
    ("1", "ESCALATE_L2"), ("2", "DEFER"),
    (None, "UNRESOLVED"), ("999", "UNRESOLVED"),
])
def test_i2b_real_shared_lane_methods_bound_to_source_and_no_adoption(
    tmp_path, monkeypatch, selection, status,
):
    case, lane = _fixture(tmp_path, monkeypatch, selection=selection)
    try:
        before = _files(case[1])
        existing = {
            s: (case[1].owners[s].retained, case[1].owners[s].intent,
                tuple(case[1].owners[s].pending_questions),
                case[1].owners[s].pattern_registry)
            for s in ("A", "B")
        }
        h = _prepared(case, lane)
        out = asyncio.run(run_i2b_original_shared_l1(
            bridge=case[1], boot=case[2], world=case[3],
            links=case[4], handoff=h, lane=lane, timeout_s=3.0,
        ))
        assert out.selection_status == status
        assert out.ticket.self_id == "A"
        assert out.ticket.request_id == h.bounded_request.request_id
        assert out.ticket.mode is CognitionMode.BOUNDED
        assert out.work_ref == "i2b:" + h.bounded_request.request_id
        assert out.model_invoked  # synthetic provider WAS called
        assert not out.goal_adopted and not out.question_adopted
        assert not out.intent_committed and not out.physical_action_authorized
        assert len(lane._jobs) == 1
        assert _files(case[1]) == before
        for s in ("A", "B"):
            o = case[1].owners[s]
            assert (o.retained, o.intent, tuple(o.pending_questions),
                    o.pattern_registry) == existing[s]
        assert case[1].physical.active_action_ids == ()
    finally:
        lane._pool.shutdown(wait=True)


def test_i2b_two_selfs_never_reuse_same_ticket_and_only_original_lane(
    tmp_path, monkeypatch,
):
    case, lane = _fixture(tmp_path, monkeypatch)
    try:
        a = _submit(case, lane, "A")
        asyncio.run(lane.await_result(a.ticket, timeout_s=3.0))
        assert _read(case, lane, a).self_id == "A"
        b = _submit(case, lane, "B")
        asyncio.run(lane.await_result(b.ticket, timeout_s=3.0))
        assert _read(case, lane, b).self_id == "B"
        assert a.ticket != b.ticket
        assert len(lane._jobs) == 2
        with pytest.raises(I2bSharedL1Hold):
            _read(case, lane, a)  # double consumption
        with pytest.raises(I2bSharedL1Hold):
            _submit_again(case, lane, a.handoff)  # duplicate work_ref
    finally:
        lane._pool.shutdown(wait=True)


def _submit_again(case, lane, handoff):
    return submit_i2b_original_shared_l1(
        bridge=case[1], boot=case[2], world=case[3], links=case[4],
        handoff=handoff, lane=lane,
    )


@pytest.mark.parametrize("fault", [
    "foreign-ticket", "other-backend", "foreign-request",
    "altered-context", "retired", "new-source", "registry",
    "paper-growth", "passive-source", "physical-open", "rejoin-epoch",
    "stale-intent",
])
def test_i2b_result_rejects_foreign_or_changed_live_sources(
    tmp_path, monkeypatch, fault,
):
    case, lane = _fixture(tmp_path, monkeypatch)
    try:
        item = _submit(case, lane)
        asyncio.run(lane.await_result(item.ticket, timeout_s=3.0))
        bridge = case[1]
        if fault == "foreign-ticket":
            item.ticket = replace(item.ticket, self_id="B")
        elif fault == "other-backend":
            item.ticket = replace(item.ticket, backend_ref="foreign")
        elif fault == "foreign-request":
            item.ticket = replace(item.ticket, request_id="i2-original-B-" + "a" * 32)
        elif fault == "altered-context":
            item.handoff = replace(item.handoff, bounded_request=replace(
                item.handoff.bounded_request, instruction="altered",
            ))
        elif fault == "retired":
            bridge.cognitive_work.fence_self("A")
            lane.fence_self("A")
        elif fault == "new-source":
            bridge._i1_correlated_sense["A"] = replace(
                bridge._i1_correlated_sense["A"], source_revision_ref="mineflayer:stale",
            )
        elif fault == "registry":
            o = bridge.owners["A"]
            o.pattern_registry = replace(
                o.pattern_registry, revision=o.pattern_registry.revision + 1,
            )
        elif fault == "paper-growth":
            with bridge.paper._log_path.open("ab") as f:
                f.write(b"new complete Paper line\n")
        elif fault == "rejoin-epoch":
            bridge.cognitive_work._states["A"].epoch += 1
        elif fault == "stale-intent":
            intent = bridge.owners["A"].intent
            assert intent.current_intent is None
            intent.commit(
                "i2b-conflicting-intent", objective="foreign task",
                at_ns=(intent.last_at_ns or 0) + 1,
                provenance=Provenance("synthetic", "stale-intent"),
            )
        elif fault == "passive-source":
            # Only a matched probe may be consumed; newer passive SENSE may
            # exist but cannot be substituted for the frozen correlated one.
            bridge._i1_correlated_sense["A"] = bridge._sense["A"]
        else:
            bridge.physical._observation_only = False
        with pytest.raises(I2bSharedL1Hold):
            _read(case, lane, item)
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("fault", [
    "no-pattern", "busy-slot", "no-bridge-attachment",
    "different-owner", "altered-request", "stale-schema",
    "physical-open", "retired-before-submit",
])
def test_i2b_preflight_refuses_unqualified_model_submission(
    tmp_path, monkeypatch, fault,
):
    case, lane = _fixture(
        tmp_path, monkeypatch,
        exploration=fault != "no-pattern",
        busy=fault == "busy-slot",
    )
    try:
        h = _prepared(case, lane)
        if fault == "no-bridge-attachment":
            case[1].inference_lane = None
        elif fault == "different-owner":
            lane.cognitive_work = object()
        elif fault == "altered-request":
            h = replace(h, bounded_request=replace(
                h.bounded_request, instruction="fabricated",
            ))
        elif fault == "stale-schema":
            case[1].cognitive_work._present_schemas.pop("A")
        elif fault == "physical-open":
            case[1].physical._observation_only = False
        elif fault == "retired-before-submit":
            case[1].cognitive_work.fence_self("A")
        with pytest.raises((I2bSharedL1Hold, RuntimeError, AttributeError)):
            _submit_again(case, lane, h)
        assert len(lane._jobs) == 0
    finally:
        lane._pool.shutdown(wait=True)


def test_i2b_logout_during_actual_shared_provider_discards_late_result(
    tmp_path, monkeypatch,
):
    entered, release = threading.Event(), threading.Event()
    case, lane = _fixture(
        tmp_path, monkeypatch, entered=entered, released=release,
    )
    try:
        async def scenario():
            h = _prepared(case, lane)
            pending = asyncio.create_task(run_i2b_original_shared_l1(
                bridge=case[1], boot=case[2], world=case[3],
                links=case[4], handoff=h, lane=lane, timeout_s=3.0,
            ))
            assert await asyncio.to_thread(entered.wait, 2.0)
            case[1].cognitive_work.fence_self("A")
            lane.fence_self("A")
            release.set()
            with pytest.raises(I2bSharedL1Hold):
                await pending
        asyncio.run(scenario())
        assert case[1].physical.active_action_ids == ()
    finally:
        release.set()
        lane._pool.shutdown(wait=True)


def test_i2b_timeout_never_resubmits_or_adopts(
    tmp_path, monkeypatch,
):
    entered, release = threading.Event(), threading.Event()
    case, lane = _fixture(
        tmp_path, monkeypatch, entered=entered, released=release,
    )
    try:
        h = _prepared(case, lane)
        with pytest.raises(I2bSharedL1Hold, match="timeout"):
            asyncio.run(run_i2b_original_shared_l1(
                bridge=case[1], boot=case[2], world=case[3],
                links=case[4], handoff=h, lane=lane, timeout_s=0.01,
            ))
        assert entered.is_set()
        assert len(lane._jobs) == 1
        with pytest.raises(I2bSharedL1Hold):
            _submit_again(case, lane, h)
    finally:
        release.set()
        lane._pool.shutdown(wait=True)


def test_i2b_explicit_attached_read_preserves_original_cpu_only_gate(
    tmp_path, monkeypatch,
):
    case, lane = _fixture(tmp_path, monkeypatch)
    try:
        _prepared(case, lane)
        # The original I2/I1 CPU entry still rejects GPU attachment unless
        # the caller explicitly qualifies the original attached-lane read.
        with pytest.raises(RuntimeError):
            prepare_i2_original_goal_handoff(**_args(case, "A"))
        current = prepare_i2_original_goal_handoff(
            **_args(case, "A"), i2b_read_attached_lane=True,
        )
        assert current.status == "EXPLORATION_GOAL_UNRESOLVED_TARGET"
        assert not current.model_invoked
        assert case[1].physical.active_action_ids == ()
    finally:
        lane._pool.shutdown(wait=True)


def test_i2b_same_intent_id_but_new_reconsideration_event_is_stale(
    tmp_path, monkeypatch,
):
    case, lane = _fixture(tmp_path, monkeypatch)
    try:
        intent = case[1].owners["A"].intent
        assert intent.current_intent is None
        start = (intent.last_at_ns or 0) + 1
        provenance = Provenance("synthetic", "intent-event-lifecycle")
        intent.commit(
            "i2b-existing-intent", objective="existing intent",
            at_ns=start, provenance=provenance,
        )
        item = _submit(case, lane)
        asyncio.run(lane.await_result(item.ticket, timeout_s=3.0))
        # No new Intent ID: a pending reconsideration of the very same
        # CurrentIntent must still invalidate the frozen earlier L1 request.
        intent.request_reconsideration(
            "i2b-existing-intent", reason="body changed",
            at_ns=start + 1, provenance=provenance,
        )
        assert intent.current_intent.intent_id == "i2b-existing-intent"
        with pytest.raises(I2bSharedL1Hold):
            _read(case, lane, item)
        assert case[1].physical.active_action_ids == ()
    finally:
        lane._pool.shutdown(wait=True)
