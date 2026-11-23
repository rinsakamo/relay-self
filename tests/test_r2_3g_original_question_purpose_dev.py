"""R2-3g: Question inference ticket is never a generic Memory adoption permit.

Original Owner / original Resident GPU lane with synthetic provider/Paper.
No World, Gemma, or physical action is performed here.
"""
from __future__ import annotations

import asyncio

import pytest

from relay_self.persistent_cognition import Memory
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionMode, ProviderDecision
from relay_self.resident_llama_inference_lane_dev import ResidentGpuLaneError
from test_b_np1b_current_composite_source_dev import current as current_fixture
from test_b_np1b_normal_present_poll_dev import pair as original_pair
from test_b_np1b_owner_bound_rejoin_dev import rejoined
from test_b_np1b_rejoin_present_dev import rejoined_present
from test_r2_3e_original_rejoin_question_issuer_dev import _issue, _setup
from test_r2_3e_original_rejoin_question_issuer_dev import pair as pair


def _memory(tag: str) -> Memory:
    return Memory(
        f"r23g-{tag}",
        "CPU synthetic Memory: not an observed World fact",
        Provenance("synthetic-q", "provider"),
        Provenance("synthetic-q", "memory-consumer"),
    )


@pytest.mark.parametrize("decision,selection", [
    (ProviderDecision.resolved("1"), "ADOPT"),
    (ProviderDecision.resolved("2"), "HOLD"),
    (ProviderDecision.resolved("3"), "DECLINE"),
    (ProviderDecision.unresolved(reason="unknown"), "UNRESOLVED"),
])
def test_r23g_original_question_cannot_be_adopted_as_memory_before_or_after_commit(
    pair, monkeypatch, decision, selection,
):
    assert all(x is not None for x in (
        current_fixture, original_pair, rejoined, rejoined_present,
    ))
    f, lane, turns = _setup(pair, monkeypatch, decision=decision)
    try:
        turn = turns["A"]
        owner = f.owners["A"]
        outcome = asyncio.run(_issue(f, lane, turn))
        assert outcome.selection == selection
        assert outcome.ticket.purpose == "original_rejoin_question"
        job = lane._jobs[("A", turn.work_ref)]
        assert job.ticket is outcome.ticket
        assert job.result_adopted is False

        before = owner.retained
        with pytest.raises(ResidentGpuLaneError, match="not adoptable"):
            lane.adopt_memory(outcome.ticket, _memory("before-" + selection))
        assert owner.retained is before
        assert not job.result_adopted
        assert f.cognitive._state("A").mode == "ONLINE"

        result = f.cognitive.commit_rejoined_original_question_dev(
            bridge=f.bridge, lane=lane, turn=turn, outcome=outcome,
        )
        assert result.selection == selection
        assert result.question_adopted == (selection == "ADOPT")
        retained = owner.retained
        assert (retained is not before) == (selection == "ADOPT")
        assert job.question_adoption_state == (
            "committed" if selection == "ADOPT" else "unused"
        )
        for _ in range(2):
            with pytest.raises(ResidentGpuLaneError, match="not adoptable"):
                lane.adopt_memory(outcome.ticket, _memory("after-" + selection))
        assert owner.retained is retained
        assert not job.result_adopted
        assert f.cognitive._state("A").mode == "ONLINE"
        assert "B" not in lane._fenced and "A" not in lane._fenced
        assert not f.bridge.physical.active_action_ids
    finally:
        lane._pool.shutdown(wait=True)


def test_r23g_separate_generic_memory_ticket_still_works(pair, monkeypatch):
    """Question restriction must not disable genuine separate Memory work."""
    f, lane, turns = _setup(
        pair, monkeypatch, decision=ProviderDecision.resolved("2"),
    )
    try:
        turn = turns["A"]
        question = asyncio.run(_issue(f, lane, turn))
        assert question.ticket.purpose == "original_rejoin_question"
        with pytest.raises(ResidentGpuLaneError):
            lane.adopt_memory(question.ticket, _memory("wrong-purpose"))

        generic = lane.submit(
            "A", work_ref="r23g-explicit-generic-memory",
            request=turn.request, mode=CognitionMode.BOUNDED,
        )
        assert generic.purpose == "general"
        asyncio.run(lane.await_result(generic, timeout_s=2.0))
        owner = f.owners["A"]
        earlier = owner.retained.memories
        remembered = _memory("separate-valid-job")
        lane.adopt_memory(generic, remembered)
        assert owner.retained.memories == (*earlier, remembered)
        assert lane._jobs[("A", generic.work_ref)].result_adopted
        with pytest.raises(ResidentGpuLaneError):
            lane.adopt_memory(generic, _memory("duplicate"))
        assert not lane._jobs[("A", question.ticket.work_ref)].result_adopted
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("purpose,mode", [
    ("action", CognitionMode.BOUNDED),
    ("", CognitionMode.BOUNDED),
    (None, CognitionMode.BOUNDED),
    (True, CognitionMode.BOUNDED),
    ("original_rejoin_question", CognitionMode.OPEN),
])
def test_r23g_invalid_purpose_is_rejected_before_gpu_enqueue(
    pair, monkeypatch, purpose, mode,
):
    f, lane, turns = _setup(pair, monkeypatch)
    try:
        turn = turns["A"]
        jobs_before = dict(lane._jobs)
        with pytest.raises(ResidentGpuLaneError):
            lane.submit(
                "A", work_ref="r23g-invalid-purpose",
                request=turn.request, mode=mode, purpose=purpose,
            )
        assert lane._jobs == jobs_before
        assert not lane.uncertain
        assert f.cognitive._state("A").mode == "ONLINE"
    finally:
        lane._pool.shutdown(wait=True)
