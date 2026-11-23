"""Q independent post-fix R2-3g adversarial tests.

Runs actual original Owner, inference lane and reJOIN Question store on
synthetic Native/Paper/provider; never represents actual World/Gemma evidence.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from relay_self.persistent_cognition import Memory, load_persistent_cognition
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionMode, ProviderDecision
from relay_self.resident_llama_inference_lane_dev import ResidentGpuLaneError
from test_b_np1b_current_composite_source_dev import current as current_fixture
from test_b_np1b_normal_present_poll_dev import pair as original_pair
from test_b_np1b_owner_bound_rejoin_dev import rejoined
from test_b_np1b_rejoin_present_dev import rejoined_present
from test_r2_3e_original_rejoin_question_issuer_dev import _issue, _setup
from test_r2_3e_original_rejoin_question_issuer_dev import pair as pair


def _memory(tag):
    return Memory(
        f"q-r23g-{tag}", "unobserved synthetic diagnostic",
        Provenance("q-source", "independent-test"),
        Provenance("q-integration", "manual-memory-attempt"),
    )


@pytest.mark.parametrize("decision,selection", (
    (ProviderDecision.resolved("1"), "ADOPT"),
    (ProviderDecision.resolved("2"), "HOLD"),
    (ProviderDecision.resolved("3"), "DECLINE"),
    (ProviderDecision.unresolved(reason="uncertain"), "UNRESOLVED"),
))
def test_q_r23g_original_question_ticket_denies_memory_before_and_after_decision(
    pair, monkeypatch, decision, selection,
):
    assert all(x is not None for x in (
        current_fixture, original_pair, rejoined, rejoined_present,
    ))
    f, lane, turns = _setup(pair, monkeypatch, decision=decision)
    try:
        turn = turns["A"]
        original_owner = f.owners["A"]
        issued = asyncio.run(_issue(f, lane, turn))
        assert issued.selection == selection
        ticket = issued.ticket
        assert ticket.purpose == "original_rejoin_question"
        job = lane._jobs[("A", turn.work_ref)]
        assert job.ticket is ticket and not job.result_adopted
        initial_memory = original_owner.retained.memories
        old_disk = load_persistent_cognition(original_owner.files.cognition_file)

        # Q original #1143 reproduced the violation here on R2-3f.
        with pytest.raises(ResidentGpuLaneError):
            lane.adopt_memory(ticket, _memory("before-" + selection))
        assert original_owner.retained.memories == initial_memory
        assert load_persistent_cognition(original_owner.files.cognition_file) == old_disk
        assert not job.result_adopted

        committed = f.cognitive.commit_rejoined_original_question_dev(
            bridge=f.bridge, lane=lane, turn=turn, outcome=issued,
        )
        assert committed.selection == selection
        assert committed.question_adopted == (selection == "ADOPT")
        retained = original_owner.retained
        disk_after = load_persistent_cognition(original_owner.files.cognition_file)
        assert disk_after == retained if selection == "ADOPT" else disk_after == old_disk

        # Same exact original ticket cannot be repurposed after any result.
        for _ in range(2):
            with pytest.raises(ResidentGpuLaneError):
                lane.adopt_memory(ticket, _memory("after-" + selection))
        assert original_owner.retained is retained
        assert original_owner.retained.memories == initial_memory
        assert load_persistent_cognition(original_owner.files.cognition_file) == disk_after
        assert not job.result_adopted
        assert "A" not in lane._fenced
        assert f.cognitive.current_scope("B")
        assert not f.bridge.physical.active_action_ids

        # Counterfeit ticket with general purpose does NOT inherit original job.
        counterfeit = replace(ticket, purpose="general")
        with pytest.raises(ResidentGpuLaneError):
            lane.adopt_memory(counterfeit, _memory("forged-" + selection))
    finally:
        lane._pool.shutdown(wait=True)


def test_q_r23g_separate_generic_work_keeps_existing_memory_consumption(
    pair, monkeypatch,
):
    f, lane, turns = _setup(
        pair, monkeypatch, decision=ProviderDecision.resolved("2"),
    )
    try:
        turn = turns["A"]
        question = asyncio.run(_issue(f, lane, turn))
        with pytest.raises(ResidentGpuLaneError):
            lane.adopt_memory(question.ticket, _memory("question"))

        # Independently submit a DIFFERENT generic original lane job.
        # Same question-shaped request is not automatically a Question ticket.
        general = lane.submit(
            "A", work_ref="q-r23g-separate-generic",
            request=turn.request, mode=CognitionMode.BOUNDED,
        )
        assert general.purpose == "general"
        asyncio.run(lane.await_result(general, timeout_s=2.0))
        earlier = f.owners["A"].retained.memories
        memo = _memory("independent-general-work")
        lane.adopt_memory(general, memo)
        assert f.owners["A"].retained.memories == (*earlier, memo)
        with pytest.raises(ResidentGpuLaneError):
            lane.adopt_memory(general, _memory("duplicate"))
        assert lane._jobs[("A", question.ticket.work_ref)].result_adopted is False
    finally:
        lane._pool.shutdown(wait=True)
