"""R2-3d: original post-reJOIN pre-submit and terminal-result CPU fences.

The real Original Owner and ResidentLlamaInferenceLane classes run against
synthetic CPU fixture provider and synthetic Paper/native event sources.
NO live Gemma, real Minecraft World, model input switch or issuer commit.
"""
from concurrent.futures import Future
from dataclasses import replace

import pytest

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from relay_self.r2_3c_original_rejoin_frozen_l1_dev import (
    R23COriginalRejoinRequestHold,
    compare_r23c_registered_l1_context,
)
from relay_self.r2_3d_original_rejoin_gpu_fence_dev import (
    R23DOriginalRejoinPreflight,
    R23DOriginalRejoinResultReadback,
    R23DOriginalRejoinSourceHold,
    preflight_r23d_original_rejoin_cpu,
    read_r23d_original_rejoin_result_cpu,
)
from relay_self.relay_engine import CognitionMode, ProviderDecision
from relay_self.resident_llama_inference_lane_dev import _request_sha256
from test_b_np1b_fresh_native_update_dev import files
from test_b_np1b_normal_present_poll_dev import pair as pair
from test_bd1b_post_gpu_source_dev import attach
from test_r2_3c_original_rejoin_frozen_l1_dev import _bind, _state


def _setup(pair, monkeypatch, *, decision=None):
    f = _bind(pair)
    turn_a = f.cognitive.prepare_rejoined_original_l1_request_cpu(
        bridge=f.bridge, self_id="A",
    )
    turn_b = f.cognitive.prepare_rejoined_original_l1_request_cpu(
        bridge=f.bridge, self_id="B",
    )
    monkeypatch.setattr(
        LlamaCppRelayProvider, "__call__",
        lambda self, request, mode: (
            ProviderDecision.resolved("2") if decision is None else decision
        ),
    )
    lane = attach(f.bridge, monkeypatch)
    return f, lane, {"A": turn_a, "B": turn_b}


def _submit(lane, turn):
    ticket = lane.submit(
        turn.self_id, work_ref=turn.work_ref, request=turn.request,
        mode=CognitionMode.BOUNDED,
    )
    lane._jobs[(turn.self_id, turn.work_ref)].future.result(timeout=5)
    return ticket


@pytest.mark.parametrize("sid", ("A", "B"))
def test_r23d_original_owner_attached_lane_preflight_is_not_issuer(
    pair, monkeypatch, sid,
):
    f, lane, turns = _setup(pair, monkeypatch)
    try:
        turn = turns[sid]
        before_files, before_owner = files(f), _state(f)
        read = preflight_r23d_original_rejoin_cpu(
            bridge=f.bridge, lane=lane, turn=turn,
        )
        assert type(read) is R23DOriginalRejoinPreflight
        assert read.self_id == sid
        assert read.owner is f.owners[sid]
        assert read.request_id == turn.request.request_id
        assert read.work_ref == turn.work_ref
        assert read.request_sha256 == turn.request_sha256
        assert read.candidate_ids == ("1", "2", "3")
        assert read.question_ref == turn.source.original_inquiry.question_ref
        assert read.need_signal_ref == turn.source.original_inquiry.need_signal_ref
        assert read.source_revision_refs == turn.source.current.source_revision_refs
        assert read.source_pair_revision == turn.source.source_pair_revision
        assert read.owner_scope == turn.cohort_scopes[("A", "B").index(sid)]
        assert read.backend_ref == lane.backend_ref
        assert not read.gpu_issued
        assert not read.product_l1_input_switched
        assert not read.memory_written
        assert not read.physical_issue_authorized
        assert lane._jobs == {}
        assert files(f) == before_files
        assert _state(f) == before_owner
        assert not f.bridge.physical.active_action_ids
        # R2-3c default CPU API is intentionally *disconnected lane only*.
        with pytest.raises(R23COriginalRejoinRequestHold):
            compare_r23c_registered_l1_context(
                bridge=f.bridge, turn=turn,
            )
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("sid,decision,expected", [
    ("A", ProviderDecision.resolved("1"), "ADOPT"),
    ("B", ProviderDecision.resolved("2"), "HOLD"),
    ("A", ProviderDecision.resolved("3"), "DECLINE"),
    ("B", ProviderDecision.unresolved(reason="unknown"), "UNRESOLVED"),
    ("A", ProviderDecision.resolved("99"), "UNRESOLVED"),
])
def test_r23d_original_terminal_job_is_read_only(
    pair, monkeypatch, sid, decision, expected,
):
    f, lane, turns = _setup(pair, monkeypatch, decision=decision)
    try:
        turn = turns[sid]
        files_before, owner_before = files(f), _state(f)
        pre = preflight_r23d_original_rejoin_cpu(
            bridge=f.bridge, lane=lane, turn=turn,
        )
        ticket = _submit(lane, turn)
        readback = read_r23d_original_rejoin_result_cpu(
            bridge=f.bridge, lane=lane, turn=turn, ticket=ticket,
        )
        assert type(readback) is R23DOriginalRejoinResultReadback
        assert readback.preflight == pre
        assert readback.ticket is ticket
        assert readback.submitted_request_sha256 == _request_sha256(
            turn.request, ticket.mode,
        )
        assert readback.selection == expected
        assert readback.choice_id == decision.choice_id
        assert readback.decision_status == decision.status
        assert readback.decision_reason == decision.reason
        assert readback.call_facts == decision.call_facts
        assert not readback.question_adopted
        assert not readback.intent_committed
        assert not readback.memory_written
        assert not readback.physical_issue_authorized
        assert not readback.product_l1_input_switched
        assert files(f) == files_before
        assert _state(f) == owner_before
        assert not f.bridge.physical.active_action_ids
        job = lane._jobs[(sid, turn.work_ref)]
        assert job.question_adoption_state == "unused"
        assert job.question_adoption_binding is None
        assert not job.result_adopted
        with pytest.raises(R23DOriginalRejoinSourceHold):
            # A duplicate cannot pass a new pre-submit check.
            preflight_r23d_original_rejoin_cpu(
                bridge=f.bridge, lane=lane, turn=turn,
            )
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("case", (
    "foreign_ticket", "copy_ticket", "foreign_self", "foreign_work",
    "request_id", "epoch", "backend", "mode", "request_content",
    "request_digest", "job_identity", "unfinished", "not_idle",
    "uncertain", "fenced", "question_consumed", "adopted", "foreign_lane",
))
def test_r23d_terminal_job_rejects_forged_or_uncertain_source(
    pair, monkeypatch, case,
):
    f, lane, turns = _setup(pair, monkeypatch)
    other_lane = None
    try:
        turn = turns["A"]
        ticket = _submit(lane, turn)
        job = lane._jobs[("A", turn.work_ref)]
        if case == "foreign_ticket":
            ticket = replace(ticket, native_session_id="other")
        elif case == "copy_ticket":
            ticket = replace(ticket)
        elif case == "foreign_self":
            ticket = replace(ticket, self_id="B")
        elif case == "foreign_work":
            ticket = replace(ticket, work_ref=turns["B"].work_ref)
        elif case == "request_id":
            ticket = replace(ticket, request_id="foreign-request")
        elif case == "epoch":
            ticket = replace(ticket, self_epoch=ticket.self_epoch + 1)
        elif case == "backend":
            ticket = replace(ticket, backend_ref="forged-backend")
        elif case == "mode":
            ticket = replace(ticket, mode=CognitionMode.OPEN)
        elif case == "request_content":
            job.request = replace(turn.request, focus="foreign-question")
        elif case == "request_digest":
            job.request_sha256 = "0" * 64
        elif case == "job_identity":
            job.ticket = replace(ticket)
        elif case == "unfinished":
            job.future = Future()
        elif case == "not_idle":
            job.terminal_slot_idle = False
        elif case == "uncertain":
            lane._uncertain = True
        elif case == "fenced":
            lane.fence_self("A")
        elif case == "question_consumed":
            job.question_adoption_state = "committed"
        elif case == "adopted":
            job.result_adopted = True
        else:
            from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane
            other_lane = ResidentLlamaInferenceLane(
                provider=lane.provider,
                cognitive_work=f.cognitive, witness=lane.witness,
            )
        before = files(f)
        with pytest.raises(R23DOriginalRejoinSourceHold):
            read_r23d_original_rejoin_result_cpu(
                bridge=f.bridge, lane=other_lane or lane,
                turn=turn, ticket=ticket,
            )
        assert files(f) == before
    finally:
        lane._pool.shutdown(wait=True)
        if other_lane is not None:
            other_lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("case", (
    "native_session", "other_epoch", "paper", "second_rejoin",
    "registry", "original_owner", "replaced_intent", "registration",
    "other_probe", "lane_detached", "gpu_fenced",
))
def test_r23d_post_attach_preflight_fails_closed_on_source_mutation(
    pair, monkeypatch, case,
):
    f, lane, turns = _setup(pair, monkeypatch)
    try:
        turn = turns["A"]
        if case == "native_session":
            native = f.bridge.sessions["A"]
            native._started = replace(
                native.started, session_id="foreign-native",
            )
        elif case == "other_epoch":
            f.cognitive._states["B"].epoch += 1
        elif case == "paper":
            with f.paper._log_path.open("a") as stream:
                stream.write("R23D_PAPER_ADVANCE\n")
        elif case == "second_rejoin":
            f.cognitive._normal_second_rejoin_cut = object()
        elif case == "registry":
            owner = f.owners["A"]
            owner.pattern_registry = replace(
                owner.pattern_registry,
                revision=owner.pattern_registry.revision + 1,
            )
        elif case == "original_owner":
            f.bridge.owners["A"] = f.bridge.owners["B"]
        elif case == "replaced_intent":
            from relay_self.intent import IntentCommitment
            f.owners["A"].intent = IntentCommitment()
        elif case == "registration":
            del f.cognitive._coverage_adoption_turns[turn.work_ref]
        elif case == "other_probe":
            other = f.owners["B"]
            other.current_worldbody_observation = replace(
                other.current_worldbody_observation,
            )
        elif case == "lane_detached":
            f.bridge.inference_lane = None
        else:
            lane.fence_self("A")
        with pytest.raises(R23DOriginalRejoinSourceHold):
            preflight_r23d_original_rejoin_cpu(
                bridge=f.bridge, lane=lane, turn=turn,
            )
        assert lane._jobs == {}
    finally:
        lane._pool.shutdown(wait=True)


def test_r23d_no_request_or_ticket_is_never_authorized(pair, monkeypatch):
    f, lane, turns = _setup(pair, monkeypatch)
    try:
        with pytest.raises(R23DOriginalRejoinSourceHold):
            preflight_r23d_original_rejoin_cpu(
                bridge=f.bridge, lane=lane, turn=None,
            )
        with pytest.raises(R23DOriginalRejoinSourceHold):
            read_r23d_original_rejoin_result_cpu(
                bridge=f.bridge, lane=lane, turn=turns["A"],
                ticket=None,
            )
        assert lane._jobs == {}
    finally:
        lane._pool.shutdown(wait=True)


def test_r23d_paper_source_change_between_terminal_reads_holds(pair, monkeypatch):
    f, lane, turns = _setup(pair, monkeypatch)
    try:
        turn = turns["A"]
        ticket = _submit(lane, turn)
        original = lane.verify_submitted_bounded_request
        calls = 0

        def advance(ticket, request):
            nonlocal calls
            result = original(ticket, request)
            calls += 1
            if calls == 1:
                with f.paper._log_path.open("a") as stream:
                    stream.write("R23D_PAPER_RACE\n")
            return result

        monkeypatch.setattr(lane, "verify_submitted_bounded_request", advance)
        with pytest.raises(R23DOriginalRejoinSourceHold):
            read_r23d_original_rejoin_result_cpu(
                bridge=f.bridge, lane=lane, turn=turn, ticket=ticket,
            )
        assert calls >= 1
        assert lane._jobs[("A", turn.work_ref)].question_adoption_state == "unused"
    finally:
        lane._pool.shutdown(wait=True)
