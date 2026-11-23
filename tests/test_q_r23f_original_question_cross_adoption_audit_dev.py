"""Q independent R2-3f double-consumption reproduction on exact original code.

These are *finding reproduction* tests, NOT desired admission behavior.
They use the real Original Owner, inference lane and Question writer with
synthetic provider/Paper. A future R fix should invert these expectations
into refusal tests. No real World/Gemma, physical Action or capability grant.
"""
from __future__ import annotations

import asyncio

import pytest

from relay_self.persistent_cognition import Memory, load_persistent_cognition
from relay_self.provenance import Provenance
from relay_self.r2_3f_original_rejoin_question_adoption_dev import (
    R23FOriginalRejoinCommitHold,
)
from relay_self.relay_engine import ProviderDecision
from test_b_np1b_current_composite_source_dev import current as current_fixture
from test_b_np1b_normal_present_poll_dev import pair as original_pair
from test_b_np1b_owner_bound_rejoin_dev import rejoined as rejoined_fixture
from test_b_np1b_rejoin_present_dev import rejoined_present as present_fixture
from test_r2_3e_original_rejoin_question_issuer_dev import _issue, _setup
from test_r2_3e_original_rejoin_question_issuer_dev import pair as pair


def _memory(tag: str) -> Memory:
    return Memory(
        f"q-r23f-{tag}", "Q diagnosis: no actual observation",
        Provenance("q-synthetic", "provider-call"),
        Provenance("q-synthetic", "manual-gpu-memory-adoption"),
    )


def _start(pair, monkeypatch, choice: str):
    assert all(x is not None for x in (
        current_fixture, original_pair, rejoined_fixture, present_fixture,
    ))
    return _setup(pair, monkeypatch, decision=ProviderDecision.resolved(choice))


@pytest.mark.parametrize("choice,selection", (("1", "ADOPT"), ("2", "HOLD")))
def test_q_r23f_original_question_job_can_still_be_adopted_as_memory(
    pair, monkeypatch, choice, selection,
):
    """Reproduces *unexpectedly permitted* cross-API use of one GPU ticket."""
    f, lane, turns = _start(pair, monkeypatch, choice)
    try:
        turn = turns["A"]
        outcome = asyncio.run(_issue(f, lane, turn))
        assert outcome.selection == selection
        commit = f.cognitive.commit_rejoined_original_question_dev(
            bridge=f.bridge, lane=lane, turn=turn, outcome=outcome,
        )
        assert commit.selection == selection
        job = lane._jobs[("A", turn.work_ref)]
        assert job.ticket is outcome.ticket and not job.result_adopted
        assert job.question_adoption_state == (
            "committed" if selection == "ADOPT" else "unused"
        )
        owner = f.owners["A"]
        earlier = owner.retained.memories
        original_disk = load_persistent_cognition(owner.files.cognition_file)
        if selection == "ADOPT":
            assert commit.question_adopted
            assert original_disk == owner.retained
        else:
            assert not commit.question_adopted
        # Reuses SAME terminal Question-choice ticket through generic Memory
        # adopter, despite the declared Question-only / HOLD no-write path.
        memory = _memory(selection.lower())
        lane.adopt_memory(outcome.ticket, memory)
        assert owner.retained.memories == (*earlier, memory)
        assert job.result_adopted
        # Memory write is in-memory only. No new Source readback/Question fence
        # was performed by the generic lane.adopt_memory method.
        assert load_persistent_cognition(owner.files.cognition_file) == original_disk
        assert "A" not in lane._fenced
        assert f.cognitive._state("A").mode == "ONLINE"
        assert not f.bridge.physical.active_action_ids
        print(f"Q_R23F_{selection}_SAME_TICKET_MEMORY_ADOPTION_REPRODUCED")
    finally:
        lane._pool.shutdown(wait=True)


def test_q_r23f_reverse_order_refuses_question_after_memory_consumption(
    pair, monkeypatch,
):
    """Asymmetric guard: Question correctly checks memory first, not reverse."""
    f, lane, turns = _start(pair, monkeypatch, "1")
    try:
        turn = turns["A"]
        outcome = asyncio.run(_issue(f, lane, turn))
        lane.adopt_memory(outcome.ticket, _memory("first"))
        job = lane._jobs[("A", turn.work_ref)]
        assert job.result_adopted
        with pytest.raises(R23FOriginalRejoinCommitHold):
            f.cognitive.commit_rejoined_original_question_dev(
                bridge=f.bridge, lane=lane, turn=turn, outcome=outcome,
            )
        assert job.question_adoption_state == "unused"
        assert f.owners["A"].retained.exploration_continuity is None
        print("Q_R23F_REVERSE_ORDER_REFUSES_AS_EXPECTED")
    finally:
        lane._pool.shutdown(wait=True)
