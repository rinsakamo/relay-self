"""Synthetic provider and slot; original owner, source, and lane classes."""

from concurrent.futures import Future
from dataclasses import replace

import pytest

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from relay_self.bd1b_coverage_adoption_turn_dev import prepare_coverage_adoption_turn
from relay_self.bd1b_issuer_readback_dev import read_issuer_result
from relay_self.bd1b_owner_source_dev import BD1bSourceHold
from relay_self.relay_engine import CognitionMode, ProviderDecision
from relay_self.resident_llama_inference_lane_dev import ResidentGpuLaneError, _request_sha256
from test_bd1b_coverage_adoption_turn_dev import arguments
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files
from test_bd1b_post_gpu_source_dev import attach


def setup(tmp_path, monkeypatch, decision):
    case = _configured(tmp_path, monkeypatch, need=True)
    turns = [prepare_coverage_adoption_turn(**arguments(case, sid)) for sid in ("A", "B")]
    monkeypatch.setattr(LlamaCppRelayProvider, "__call__", lambda self, request, mode: decision)
    lane = attach(case[1], monkeypatch)
    return case, turns, lane


def submit(lane, turn):
    ticket = lane.submit(
        turn.self_id, work_ref=turn.work_ref, request=turn.request, mode=CognitionMode.BOUNDED
    )
    lane._jobs[(turn.self_id, turn.work_ref)].future.result(timeout=5)
    return ticket


def read(case, lane, turn, ticket):
    kw = arguments(case, turn.self_id)
    kw.pop("self_id")
    return read_issuer_result(**kw, lane=lane, turn=turn, ticket=ticket)


def snapshot(case):
    bridge = case[1]
    return (
        _files(bridge),
        {
            s: (o.retained, o.intent.events, dict(o.skills), set(o.pending_questions))
            for s, o in bridge.owners.items()
        },
    )


@pytest.mark.parametrize(
    "sid,decision,selection",
    [
        ("A", ProviderDecision.resolved("1"), "ADOPT"),
        ("B", ProviderDecision.resolved("2"), "HOLD"),
        ("A", ProviderDecision.resolved("3"), "DECLINE"),
        ("B", ProviderDecision.unresolved(reason="unknown"), "UNRESOLVED"),
        ("A", ProviderDecision.resolved("99"), "UNRESOLVED"),
    ],
)
def test_completed_job_readonly(tmp_path, monkeypatch, sid, decision, selection):
    case, turns, lane = setup(tmp_path, monkeypatch, decision)
    try:
        turn = turns[0 if sid == "A" else 1]
        before = snapshot(case)
        ticket = submit(lane, turn)
        result = read(case, lane, turn, ticket)
        assert result == read(case, lane, turn, ticket)
        assert result.selection == selection and result.provider_status == decision.status
        assert result.ticket == ticket and result.source == turn.source
        assert result.inquiry_ref == turn.inquiry.question_ref
        assert result.candidate_set_sha256 == turn.candidate_set_sha256
        assert result.verified_submitted_request_sha256 == _request_sha256(
            turn.request, ticket.mode
        )
        assert result.verified_submitted_request_sha256 != result.candidate_set_sha256
        assert snapshot(case) == before
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize(
    "variant",
    [
        "unregistered",
        "copied_ticket",
        "self",
        "work",
        "request",
        "backend",
        "mode",
        "epoch",
        "unfinished",
        "idle",
        "uncertain",
        "lane",
        "request_content",
        "request_digest",
        "candidate",
        "cross_turn",
        "source_during",
    ],
)
def test_reject_job_and_source_tampering(tmp_path, monkeypatch, variant):
    case, turns, lane = setup(tmp_path, monkeypatch, ProviderDecision.resolved("1"))
    try:
        turn = turns[0]
        ticket = submit(lane, turn)
        job = lane._jobs[(turn.self_id, turn.work_ref)]
        if variant == "copied_ticket":
            ticket = replace(ticket)
        elif variant == "unregistered":
            ticket = replace(ticket, work_ref="unregistered")
        elif variant == "self":
            ticket = replace(ticket, self_id="B")
        elif variant == "work":
            ticket = replace(ticket, work_ref=turns[1].work_ref)
        elif variant == "request":
            ticket = replace(ticket, request_id="other")
        elif variant == "backend":
            ticket = replace(ticket, backend_ref="other")
        elif variant == "mode":
            ticket = replace(ticket, mode=CognitionMode.THINK)
        elif variant == "epoch":
            ticket = replace(ticket, self_epoch=ticket.self_epoch + 1)
        elif variant == "unfinished":
            job.future = Future()
        elif variant == "idle":
            job.terminal_slot_idle = False
        elif variant == "uncertain":
            lane._uncertain = True
        elif variant == "lane":
            case[1].inference_lane = None
        elif variant == "request_content":
            job.request = replace(turn.request, choices=tuple(reversed(turn.request.choices)))
        elif variant == "request_digest":
            job.request_sha256 = "0" * 64
        elif variant == "candidate":
            turn = replace(turn, candidate_set_sha256="0" * 64)
        elif variant == "cross_turn":
            turn = turns[1]
        elif variant == "source_during":
            original = lane.verify_submitted_bounded_request

            def changing(*args):
                result = original(*args)
                case[1].paper._session_id = "changed"
                return result

            monkeypatch.setattr(lane, "verify_submitted_bounded_request", changing)
        before = snapshot(case)
        with pytest.raises((BD1bSourceHold, ResidentGpuLaneError)):
            read(case, lane, turn, ticket)
        assert snapshot(case) == before
    finally:
        lane._pool.shutdown(wait=True)
