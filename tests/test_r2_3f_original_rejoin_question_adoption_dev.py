"""R2-3f original Question ADOPT persistence after first reJOIN; CPU synthetic.

Tests exercise the actual original Resident Owner, original bounded lane,
Native/Paper fixtures and the existing persistent Question writer.
The provider and backend idle witness are synthetic; no real LLM/World.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from relay_self.persistent_cognition import load_persistent_cognition, save_persistent_cognition
from relay_self.r2_3d_original_rejoin_gpu_fence_dev import (
    read_r23d_original_rejoin_result_cpu,
)
from relay_self.r2_3e_original_rejoin_question_issuer_dev import (
    R23EOriginalRejoinQuestionOutcome,
)
from relay_self.r2_3f_original_rejoin_question_adoption_dev import (
    R23FOriginalRejoinCommitHold,
    R23FOriginalRejoinQuestionCommit,
)
from relay_self.relay_engine import CognitionMode, ProviderDecision
from test_b_np1b_current_composite_source_dev import current as current_fixture
from test_b_np1b_fresh_native_update_dev import files
from test_b_np1b_normal_present_poll_dev import pair as original_pair
from test_b_np1b_owner_bound_rejoin_dev import rejoined as rejoined
from test_b_np1b_rejoin_present_dev import rejoined_present as rejoined_present
from test_r2_3c_original_rejoin_frozen_l1_dev import _state
from test_r2_3e_original_rejoin_question_issuer_dev import _issue, _setup
from test_r2_3e_original_rejoin_question_issuer_dev import pair as pair


def _commit(f, lane, turn, outcome):
    return f.cognitive.commit_rejoined_original_question_dev(
        bridge=f.bridge, lane=lane, turn=turn, outcome=outcome,
    )


def _question(f, turn):
    owner = f.owners[turn.self_id]
    state = owner.retained.exploration_continuity
    return owner, state, owner.files.cognition_file


def _assert_peer_unmodified(f, other, before):
    owner = f.owners[other]
    assert (
        owner.retained, owner.intent, owner.pattern_registry,
        dict(owner.skills), set(owner.pending_questions),
    ) == before
    assert f.cognitive.current_scope(other)


@pytest.mark.parametrize("sid", ("A", "B"))
def test_r23f_real_original_adopt_persists_once_and_not_a_skill(
    pair, monkeypatch, sid,
):
    assert current_fixture is not None and original_pair is not None
    assert rejoined is not None and rejoined_present is not None
    f, lane, turns = _setup(pair, monkeypatch, decision=ProviderDecision.resolved("1"))
    turn = turns[sid]
    try:
        if sid == "B":
            # This Native reJOIN source fixture legitimately has no
            # persisted B cognition file. Give the positive B path a
            # source-equivalent pre-existing canonical checkpoint.
            # The production Question writer must NEVER create this
            # missing file on its own; a separate negative test checks HOLD.
            owner = f.owners[sid]
            assert not owner.files.cognition_file.exists()
            save_persistent_cognition(owner.files.cognition_file, owner.retained)
            assert load_persistent_cognition(owner.files.cognition_file) == owner.retained
        before_files = files(f)
        other = "B" if sid == "A" else "A"
        before_peer = (
            f.owners[other].retained,
            f.owners[other].intent,
            f.owners[other].pattern_registry,
            dict(f.owners[other].skills),
            set(f.owners[other].pending_questions),
        )
        result = asyncio.run(_issue(f, lane, turn))
        assert result.selection == "ADOPT"
        assert f.cognitive._rejoin_question_outcomes[turn.work_ref] is result
        before_memory = f.owners[sid].retained
        commit = _commit(f, lane, turn, result)
        assert type(commit) is R23FOriginalRejoinQuestionCommit
        assert commit.ticket is result.ticket
        assert commit.selection == "ADOPT" and commit.question_adopted
        assert commit.persisted_continuity_revision == turn.continuity_revision + 1
        assert commit.question_ref == turn.source.original_inquiry.question_ref
        assert not commit.intent_committed
        assert not commit.memory_written
        assert not commit.skill_issued
        assert not commit.physical_issue_authorized
        assert not commit.product_l1_input_switched
        owner, state, path = _question(f, turn)
        assert state.revision == turn.continuity_revision + 1
        assert len(state.questions) == 1
        assert state.questions[0].question_ref == turn.source.original_inquiry.question_ref
        assert state.questions[0].open
        assert result.ticket.work_ref in state.questions[0].origin.reference
        assert result.ticket.request_id in state.questions[0].origin.reference
        assert load_persistent_cognition(path) == owner.retained
        assert owner.retained != before_memory
        assert state.questions[0].question_ref in owner.pending_questions
        assert owner.intent is turn.intent_owner
        assert owner.intent.events == turn.intent_events
        assert not f.bridge.physical.active_action_ids
        assert lane._jobs[(sid, turn.work_ref)].question_adoption_state == "committed"
        assert not lane._jobs[(sid, turn.work_ref)].result_adopted
        assert lane._jobs[(sid, turn.work_ref)].question_adoption_binding is not None
        assert sid not in lane._fenced
        assert f.cognitive._state(sid).mode == "ONLINE"
        _assert_peer_unmodified(f, other, before_peer)
        changed_paths = {
            k for k, v in files(f).items() if before_files.get(k) != v
        }
        assert changed_paths == {str(path)}
        with pytest.raises(R23FOriginalRejoinCommitHold):
            _commit(f, lane, turn, result)
        assert len(owner.retained.exploration_continuity.questions) == 1
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("sid,decision,selection", [
    ("A", ProviderDecision.resolved("2"), "HOLD"),
    ("B", ProviderDecision.resolved("3"), "DECLINE"),
    ("A", ProviderDecision.unresolved(reason="unknown"), "UNRESOLVED"),
    ("B", ProviderDecision.resolved("99"), "UNRESOLVED"),
])
def test_r23f_non_adopt_never_writes_or_fences(
    pair, monkeypatch, sid, decision, selection,
):
    f, lane, turns = _setup(pair, monkeypatch, decision=decision)
    try:
        turn = turns[sid]
        before_state, before_files = _state(f), files(f)
        result = asyncio.run(_issue(f, lane, turn))
        for _ in range(2):
            commit = _commit(f, lane, turn, result)
            assert commit.selection == selection
            assert commit.question_ref == turn.source.original_inquiry.question_ref
            assert not commit.question_adopted
            assert commit.persisted_continuity_revision is None
            assert not commit.memory_written
            assert not commit.intent_committed
            assert not commit.physical_issue_authorized
            assert lane._jobs[(sid, turn.work_ref)].question_adoption_state == "unused"
            assert "A" not in lane._fenced and "B" not in lane._fenced
        assert _state(f) == before_state
        assert files(f) == before_files
    finally:
        lane._pool.shutdown(wait=True)


def test_r23f_original_one_call_issue_and_commit(pair, monkeypatch):
    f, lane, turns = _setup(pair, monkeypatch, decision=ProviderDecision.resolved("1"))
    turn = turns["A"]
    try:
        commit = asyncio.run(
            f.cognitive.issue_and_commit_rejoined_original_question_dev(
                bridge=f.bridge, lane=lane, turn=turn, timeout_s=2.0,
            )
        )
        assert commit.selection == "ADOPT" and commit.question_adopted
        owner, state, path = _question(f, turn)
        assert state.revision == turn.continuity_revision + 1
        assert state.questions[0].question_ref == turn.source.original_inquiry.question_ref
        assert load_persistent_cognition(path) == owner.retained
        assert len(lane._jobs) == 1
        assert lane._jobs[("A", turn.work_ref)].question_adoption_state == "committed"
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("variant", (
    "copy", "choice_forgery", "ticket_forgery", "foreign_turn",
    "forgotten_outcome", "other_self",
))
def test_r23f_caller_supplied_outcome_is_not_adoption_authority(
    pair, monkeypatch, variant,
):
    f, lane, turns = _setup(pair, monkeypatch, decision=ProviderDecision.resolved("2"))
    try:
        turn = turns["A"]
        valid = asyncio.run(_issue(f, lane, turn))
        fake = valid
        if variant == "copy":
            fake = replace(valid)
        elif variant == "choice_forgery":
            forged_readback = replace(valid.readback, selection="ADOPT", choice_id="1")
            fake = replace(valid, selection="ADOPT", readback=forged_readback)
        elif variant == "ticket_forgery":
            ticket = replace(valid.ticket)
            forged_readback = replace(valid.readback, ticket=ticket)
            fake = replace(valid, ticket=ticket, readback=forged_readback)
        elif variant == "foreign_turn":
            turn = turns["B"]
        elif variant == "forgotten_outcome":
            del f.cognitive._rejoin_question_outcomes[turn.work_ref]
        else:
            from relay_self.r2_3e_original_rejoin_question_issuer_dev import (
                R23EOriginalRejoinQuestionOutcome as OriginalOutcome,
            )
            # Same genuine job, different registered Self ID in the turn.
            fake = OriginalOutcome(
                ticket=valid.ticket,
                readback=valid.readback,
                selection=valid.selection,
            )
        before_state, before_files = _state(f), files(f)
        with pytest.raises((R23FOriginalRejoinCommitHold, RuntimeError)):
            _commit(f, lane, turn, fake)
        assert _state(f) == before_state
        assert files(f) == before_files
        assert lane._jobs[("A", valid.ticket.work_ref)].question_adoption_state == "unused"
        assert "A" not in lane._fenced
    finally:
        lane._pool.shutdown(wait=True)


def test_r23f_direct_lane_submit_cannot_fake_original_issuer_outcome(
    pair, monkeypatch,
):
    f, lane, turns = _setup(pair, monkeypatch, decision=ProviderDecision.resolved("1"))
    try:
        turn = turns["A"]
        ticket = lane.submit(
            "A", work_ref=turn.work_ref,
            request=turn.request, mode=CognitionMode.BOUNDED,
        )
        lane._jobs[("A", turn.work_ref)].future.result(timeout=5)
        readback = read_r23d_original_rejoin_result_cpu(
            bridge=f.bridge, lane=lane, turn=turn, ticket=ticket,
        )
        forged = R23EOriginalRejoinQuestionOutcome(
            ticket=ticket, readback=readback, selection=readback.selection,
        )
        before = files(f)
        with pytest.raises(R23FOriginalRejoinCommitHold):
            _commit(f, lane, turn, forged)
        assert files(f) == before
        assert f.owners["A"].retained.exploration_continuity is None
        assert lane._jobs[("A", turn.work_ref)].question_adoption_state == "unused"
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("kind", (
    "paper", "native", "peer_epoch", "self_epoch", "schema",
    "intent", "other_probe", "second_rejoin", "request",
    "registration", "lane_uncertain", "physical_disabled",
))
def test_r23f_stale_original_source_or_submitted_request_never_writes(
    pair, monkeypatch, kind,
):
    f, lane, turns = _setup(pair, monkeypatch, decision=ProviderDecision.resolved("1"))
    turn = turns["A"]
    try:
        outcome = asyncio.run(_issue(f, lane, turn))
        assert outcome.selection == "ADOPT"
        if kind == "paper":
            with f.paper._log_path.open("a") as out:
                out.write("R23F_PAPER_GROWTH_AFTER_L1\n")
        elif kind == "native":
            f.bridge.sessions["A"]._started = replace(
                f.bridge.sessions["A"].started, session_id="foreign",
            )
        elif kind == "peer_epoch":
            f.cognitive._states["B"].epoch += 1
        elif kind == "self_epoch":
            f.cognitive._states["A"].epoch += 1
        elif kind == "schema":
            f.owners["A"].pattern_registry = replace(
                f.owners["A"].pattern_registry,
                revision=f.owners["A"].pattern_registry.revision + 1,
            )
        elif kind == "intent":
            from relay_self.intent import IntentCommitment
            f.owners["A"].intent = IntentCommitment()
        elif kind == "other_probe":
            f.owners["B"].current_worldbody_observation = replace(
                f.owners["B"].current_worldbody_observation,
            )
        elif kind == "second_rejoin":
            f.cognitive._normal_second_rejoin_cut = object()
        elif kind == "request":
            lane._jobs[("A", turn.work_ref)].request = replace(
                turn.request, choices=tuple(reversed(turn.request.choices)),
            )
        elif kind == "registration":
            del f.cognitive._coverage_adoption_turns[turn.work_ref]
        elif kind == "lane_uncertain":
            lane._uncertain = True
        else:
            f.bridge.physical._observation_only = False
        before_files = files(f)
        previous_cognition = f.owners["A"].retained
        with pytest.raises(Exception):
            _commit(f, lane, turn, outcome)
        assert f.owners["A"].retained is previous_cognition
        assert files(f) == before_files
        assert lane._jobs[("A", turn.work_ref)].question_adoption_state in (
            "unused", "failed",
        )
        assert len(lane._jobs) == 1
    finally:
        lane._pool.shutdown(wait=True)


def test_r23f_concurrent_original_commit_at_most_once(pair, monkeypatch):
    f, lane, turns = _setup(pair, monkeypatch, decision=ProviderDecision.resolved("1"))
    turn = turns["A"]
    try:
        result = asyncio.run(_issue(f, lane, turn))
        def commit_once(_):
            try:
                return _commit(f, lane, turn, result).selection
            except R23FOriginalRejoinCommitHold:
                return "REJECTED"
        with ThreadPoolExecutor(max_workers=2) as pool:
            answers = sorted(pool.map(commit_once, range(2)))
        assert answers == ["ADOPT", "REJECTED"]
        state = f.owners["A"].retained.exploration_continuity
        assert state.revision == 1 and len(state.questions) == 1
        assert lane._jobs[("A", turn.work_ref)].question_adoption_state == "committed"
        assert f.cognitive._state("A").mode == "ONLINE"
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("failure", ("missing_disk", "write_error", "readback_error"))
def test_r23f_storage_failure_fences_one_self_and_never_retries(
    pair, monkeypatch, failure,
):
    import relay_self.bd1b_question_store_dev as store

    f, lane, turns = _setup(pair, monkeypatch, decision=ProviderDecision.resolved("1"))
    turn = turns["A"]
    try:
        result = asyncio.run(_issue(f, lane, turn))
        owner, _, path = _question(f, turn)
        previous = owner.retained
        if failure == "missing_disk":
            path.unlink()
        elif failure == "write_error":
            monkeypatch.setattr(
                store, "save_persistent_cognition",
                lambda path, cognition: (_ for _ in ()).throw(
                    OSError("synthetic write failure")
                ),
            )
        else:
            original = store.load_persistent_cognition
            calls = 0
            def fail_readback(path):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("synthetic readback failure")
                return original(path)
            monkeypatch.setattr(store, "load_persistent_cognition", fail_readback)

        with pytest.raises(Exception):
            _commit(f, lane, turn, result)
        assert owner.retained is previous
        assert lane._jobs[("A", turn.work_ref)].question_adoption_state == "failed"
        assert "A" in lane._fenced
        assert f.cognitive._state("A").mode == "QUARANTINED"
        assert f.cognitive.current_scope("B")
        with pytest.raises(R23FOriginalRejoinCommitHold):
            _commit(f, lane, turn, result)
    finally:
        lane._pool.shutdown(wait=True)


def test_r23f_post_save_source_drift_is_uncertain_not_success(pair, monkeypatch):
    import relay_self.bd1b_question_store_dev as store

    f, lane, turns = _setup(pair, monkeypatch, decision=ProviderDecision.resolved("1"))
    turn = turns["A"]
    try:
        result = asyncio.run(_issue(f, lane, turn))
        owner, _, path = _question(f, turn)
        old = owner.retained
        original = store.save_persistent_cognition
        def after_write(path, value):
            original(path, value)
            with f.paper._log_path.open("a") as out:
                out.write("R23F_PAPER_CHANGE_POST_SAVE\n")
        monkeypatch.setattr(store, "save_persistent_cognition", after_write)
        with pytest.raises(Exception):
            _commit(f, lane, turn, result)
        assert owner.retained is old
        assert load_persistent_cognition(path) != old
        assert lane._jobs[("A", turn.work_ref)].question_adoption_state == "failed"
        assert "A" in lane._fenced
        assert f.cognitive._state("A").mode == "QUARANTINED"
        assert f.cognitive.current_scope("B")
        # A persisted file is not silently claimed rolled back by a failed
        # post-save check. Recovery requires separately qualified readback.
    finally:
        lane._pool.shutdown(wait=True)
