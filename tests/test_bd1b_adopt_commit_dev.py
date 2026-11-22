"""CPU-only synthetic decisions through the original resident lane."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from relay_self.bd1b_adopt_commit_dev import commit_issuer_adoption
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.relay_engine import ProviderDecision
from test_bd1b_coverage_adoption_turn_dev import arguments
from test_bd1b_issuer_readback_dev import setup, snapshot, submit


def commit(case, lane, turn, ticket):
    kw = arguments(case, turn.self_id)
    kw.pop("self_id")
    return commit_issuer_adoption(**kw, lane=lane, turn=turn, ticket=ticket)


@pytest.mark.parametrize("decision,selection", [
    (ProviderDecision.resolved("1"), "ADOPT"),
    (ProviderDecision.resolved("2"), "HOLD"),
    (ProviderDecision.resolved("3"), "DECLINE"),
    (ProviderDecision.unresolved(reason="unknown"), "UNRESOLVED"),
])
def test_commit_result(tmp_path, monkeypatch, decision, selection):
    case, turns, lane = setup(tmp_path, monkeypatch, decision)
    try:
        turn = turns[0] if selection == "ADOPT" else turns[1]
        owner = turn.owner
        before = snapshot(case)
        ticket = submit(lane, turn)
        assert commit(case, lane, turn, ticket) == selection
        if selection != "ADOPT":
            assert snapshot(case) == before
            return
        state = owner.retained.exploration_continuity
        assert state.revision == turn.continuity_revision + 1
        record = state.questions[-1]
        assert record.question_ref == turn.inquiry.question_ref and record.open
        assert ticket.work_ref in record.origin.reference and ticket.request_id in record.origin.reference
        assert load_persistent_cognition(owner.files.cognition_file) == owner.retained
        assert record.question_ref in owner.pending_questions
        assert lane._jobs[(turn.self_id, turn.work_ref)].question_adoption_state == "committed"
        with pytest.raises(Exception):
            commit(case, lane, turn, ticket)
    finally:
        lane._pool.shutdown(wait=True)


def test_concurrent_commit_and_forged_ticket(tmp_path, monkeypatch):
    case, turns, lane = setup(tmp_path, monkeypatch, ProviderDecision.resolved("1"))
    try:
        turn = turns[0]
        ticket = submit(lane, turn)
        with pytest.raises(Exception):
            commit(case, lane, turn, replace(ticket))
        def attempt():
            try:
                return commit(case, lane, turn, ticket)
            except Exception:
                return "rejected"
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(lambda _: attempt(), range(2))) == ["ADOPT", "rejected"]
        assert len(turn.owner.retained.exploration_continuity.questions) == 1
    finally:
        lane._pool.shutdown(wait=True)


def test_post_save_source_loss_fences_and_prevents_retry(tmp_path, monkeypatch):
    import relay_self.bd1b_question_store_dev as store
    case, turns, lane = setup(tmp_path, monkeypatch, ProviderDecision.resolved("1"))
    try:
        turn = turns[0]
        ticket = submit(lane, turn)
        previous = turn.owner.retained
        original = store.save_persistent_cognition
        def changing(path, value):
            original(path, value)
            case[1].paper._session_id = "changed"
        monkeypatch.setattr(store, "save_persistent_cognition", changing)
        with pytest.raises(Exception):
            commit(case, lane, turn, ticket)
        assert turn.owner.retained == previous
        assert load_persistent_cognition(turn.owner.files.cognition_file) != previous
        assert lane._jobs[(turn.self_id, turn.work_ref)].question_adoption_state == "failed"
        assert case[1].cognitive_work.quarantined_scope(turn.self_id)
        with pytest.raises(Exception):
            commit(case, lane, turn, ticket)
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("failure", ["missing", "symlink", "write", "readback"])
def test_storage_failures_quarantine_and_never_retry(tmp_path, monkeypatch, failure):
    import relay_self.bd1b_question_store_dev as store
    case, turns, lane = setup(tmp_path, monkeypatch, ProviderDecision.resolved("1"))
    try:
        turn = turns[0]
        ticket = submit(lane, turn)
        previous = turn.owner.retained
        path = turn.owner.files.cognition_file
        if failure == "missing":
            path.unlink()
        elif failure == "symlink":
            target = tmp_path / "foreign.json"
            path.rename(target)
            path.symlink_to(target)
        elif failure == "write":
            def fail(*args):
                raise OSError("injected write failure")
            monkeypatch.setattr(store, "save_persistent_cognition", fail)
        else:
            original = store.load_persistent_cognition
            calls = 0
            def fail_readback(path):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("injected readback failure")
                return original(path)
            monkeypatch.setattr(store, "load_persistent_cognition", fail_readback)
        with pytest.raises(Exception):
            commit(case, lane, turn, ticket)
        assert turn.owner.retained == previous
        assert case[1].cognitive_work.quarantined_scope(turn.self_id)
        assert lane._jobs[(turn.self_id, turn.work_ref)].question_adoption_state == "failed"
        with pytest.raises(Exception):
            commit(case, lane, turn, ticket)
    finally:
        lane._pool.shutdown(wait=True)
