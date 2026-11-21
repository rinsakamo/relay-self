"""CPU synthetic end-to-end tests of the live-capable original issuer API.

The synthetic provider is not an actual model/Paper/GPU attestation.
"""
import asyncio
import threading
from dataclasses import replace

import pytest

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from relay_self.bd1b_original_issuer_once_dev import issue_original_adoption_once
from relay_self.bd1b_owner_source_dev import BD1bSourceHold
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.relay_engine import ProviderDecision
from relay_self.resident_llama_inference_lane_dev import ResidentGpuLaneError
from test_bd1b_coverage_adoption_turn_dev import arguments
from test_bd1b_issuer_readback_dev import setup, snapshot


async def _issue(case, lane, turn, **options):
    kw = arguments(case, turn.self_id)
    kw.pop("self_id")
    return await issue_original_adoption_once(**kw, lane=lane, turn=turn, **options)


@pytest.mark.parametrize("self_id,decision,expected", [
    ("A", ProviderDecision.resolved("1"), "ADOPT"),
    ("B", ProviderDecision.resolved("2"), "HOLD"),
    ("A", ProviderDecision.resolved("3"), "DECLINE"),
    ("B", ProviderDecision.unresolved(reason="none"), "UNRESOLVED"),
    ("A", ProviderDecision.resolved("99"), "UNRESOLVED"),
])
def test_original_issuer_executes_one_registered_job(tmp_path, monkeypatch,
                                                     self_id, decision, expected):
    case, turns, lane = setup(tmp_path, monkeypatch, decision)
    try:
        turn = turns[0 if self_id == "A" else 1]
        before = snapshot(case)
        result = asyncio.run(_issue(case, lane, turn))
        assert result.selection == expected == result.readback.selection
        assert result.ticket.self_id == self_id
        assert result.ticket.work_ref == turn.work_ref
        assert result.readback.ticket is result.ticket
        job = lane._jobs[(self_id, turn.work_ref)]
        assert job.ticket is result.ticket
        assert job.request is turn.request
        assert job.terminal_slot_idle
        assert result.ticket.action_issue_authorized is False
        if expected == "ADOPT":
            owner = turn.owner
            assert job.question_adoption_state == "committed"
            assert len(owner.retained.exploration_continuity.questions) == 1
            assert load_persistent_cognition(owner.files.cognition_file) == owner.retained
            assert turn.inquiry.question_ref in owner.pending_questions
        else:
            assert job.question_adoption_state == "unused"
            assert snapshot(case) == before
    finally:
        lane._pool.shutdown(wait=True)


def test_second_caller_cannot_resubmit_same_frozen_turn(tmp_path, monkeypatch):
    case, turns, lane = setup(tmp_path, monkeypatch, ProviderDecision.resolved("2"))
    try:
        turn = turns[0]
        first = asyncio.run(_issue(case, lane, turn))
        assert first.selection == "HOLD"
        before = snapshot(case)
        with pytest.raises(ResidentGpuLaneError):
            asyncio.run(_issue(case, lane, turn))
        assert snapshot(case) == before
        assert len(lane._jobs) == 1
    finally:
        lane._pool.shutdown(wait=True)


def test_forged_turn_never_submits_provider_job(tmp_path, monkeypatch):
    case, turns, lane = setup(tmp_path, monkeypatch, ProviderDecision.resolved("1"))
    try:
        forged = replace(turns[0], candidate_set_sha256="0" * 64)
        before = snapshot(case)
        with pytest.raises(BD1bSourceHold):
            asyncio.run(_issue(case, lane, forged))
        assert lane._jobs == {}
        assert snapshot(case) == before
        assert not case[1].cognitive_work._state("A").mode == "QUARANTINED"
    finally:
        lane._pool.shutdown(wait=True)


def test_submitted_request_tampering_fences_a_only(tmp_path, monkeypatch):
    case, turns, lane = setup(tmp_path, monkeypatch, ProviderDecision.resolved("1"))
    turn = turns[0]

    def tamper(self, request, mode):
        job = lane._jobs[(turn.self_id, turn.work_ref)]
        job.request = replace(request, choices=tuple(reversed(request.choices)))
        return ProviderDecision.resolved("1")

    monkeypatch.setattr(LlamaCppRelayProvider, "__call__", tamper)
    try:
        before = snapshot(case)
        with pytest.raises(ResidentGpuLaneError):
            asyncio.run(_issue(case, lane, turn))
        assert snapshot(case) == before
        assert case[1].cognitive_work.quarantined_scope("A")
        assert case[1].cognitive_work.current_scope("B")
        assert "A" in lane._fenced and "B" not in lane._fenced
        assert lane._jobs[("A", turn.work_ref)].question_adoption_state == "unused"
    finally:
        lane._pool.shutdown(wait=True)


def test_source_change_during_provider_fences_before_publication(tmp_path, monkeypatch):
    case, turns, lane = setup(tmp_path, monkeypatch, ProviderDecision.resolved("1"))

    def source_drift(self, request, mode):
        case[1].paper._session_id = "changed-during-gpu"
        return ProviderDecision.resolved("1")

    monkeypatch.setattr(LlamaCppRelayProvider, "__call__", source_drift)
    try:
        before = snapshot(case)
        with pytest.raises(BD1bSourceHold):
            asyncio.run(_issue(case, lane, turns[0]))
        assert snapshot(case) == before
        assert case[1].cognitive_work.quarantined_scope("A")
        assert lane._jobs[("A", turns[0].work_ref)].question_adoption_state == "unused"
    finally:
        lane._pool.shutdown(wait=True)


def test_provider_exception_and_backend_uncertainty_fence(tmp_path, monkeypatch):
    case, turns, lane = setup(tmp_path, monkeypatch, ProviderDecision.resolved("1"))

    def fail(self, request, mode):
        raise RuntimeError("fixture provider failed")

    monkeypatch.setattr(LlamaCppRelayProvider, "__call__", fail)
    try:
        before = snapshot(case)
        with pytest.raises(RuntimeError, match="fixture provider failed"):
            asyncio.run(_issue(case, lane, turns[0]))
        assert snapshot(case) == before
        assert case[1].cognitive_work.quarantined_scope("A")
        assert "A" in lane._fenced
    finally:
        lane._pool.shutdown(wait=True)


def test_timeout_fences_without_cancelling_backend_or_writing(tmp_path, monkeypatch):
    case, turns, lane = setup(tmp_path, monkeypatch, ProviderDecision.resolved("1"))
    entered, release = threading.Event(), threading.Event()

    def slow(self, request, mode):
        entered.set()
        assert release.wait(timeout=5)
        return ProviderDecision.resolved("1")

    monkeypatch.setattr(LlamaCppRelayProvider, "__call__", slow)

    async def expire():
        task = asyncio.create_task(_issue(case, lane, turns[0], timeout_s=0.01))
        assert await asyncio.to_thread(entered.wait, 5)
        with pytest.raises(ResidentGpuLaneError, match="result wait elapsed"):
            await task

    try:
        before = snapshot(case)
        asyncio.run(expire())
        assert snapshot(case) == before
        assert case[1].cognitive_work.quarantined_scope("A")
        assert "A" in lane._fenced
        assert lane._jobs[("A", turns[0].work_ref)].question_adoption_state == "unused"
    finally:
        release.set()
        lane._pool.shutdown(wait=True)


def test_two_simultaneous_calls_only_issue_once(tmp_path, monkeypatch):
    case, turns, lane = setup(tmp_path, monkeypatch, ProviderDecision.resolved("2"))
    turn = turns[0]

    async def both():
        return await asyncio.gather(
            _issue(case, lane, turn), _issue(case, lane, turn),
            return_exceptions=True,
        )

    try:
        before = snapshot(case)
        results = asyncio.run(both())
        assert len([x for x in results if getattr(x, "selection", None) == "HOLD"]) == 1
        assert sum(isinstance(x, ResidentGpuLaneError) for x in results) == 1
        assert snapshot(case) == before
        assert len(lane._jobs) == 1
    finally:
        lane._pool.shutdown(wait=True)


def test_invalid_wait_never_issues_job(tmp_path, monkeypatch):
    case, turns, lane = setup(tmp_path, monkeypatch, ProviderDecision.resolved("1"))
    try:
        with pytest.raises(ValueError):
            asyncio.run(_issue(case, lane, turns[0], timeout_s=0))
        assert lane._jobs == {}
    finally:
        lane._pool.shutdown(wait=True)
