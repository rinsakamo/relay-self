"""End-to-end hostile coverage for the original, CPU-synthetic ADOPT commit.

These checks traverse commit_issuer_adoption, not just its read-only precursors.
No real inference, Paper or autonomous Self decision is attested here.
"""
from dataclasses import replace

import pytest

import relay_self.bd1b_question_store_dev as storage
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.relay_engine import CognitionMode, ProviderDecision
from test_bd1b_adopt_commit_dev import commit
from test_bd1b_coverage_adoption_turn_dev import arguments
from test_bd1b_issuer_readback_dev import setup, snapshot, submit


@pytest.mark.parametrize("variant", [
    "ticket_copy", "ticket_self", "ticket_work", "ticket_request",
    "ticket_backend", "ticket_mode", "ticket_epoch", "turn_swap",
    "candidate_digest", "request_choices", "request_context", "request_identity",
    "request_digest", "probe", "paper_session", "paper_log", "paper_ack",
    "other_self_epoch", "registry", "continuity", "intent", "lane_detached",
    "gpu_uncertain", "gpu_unfinished", "gpu_no_idle", "fence",
    "request_provenance", "native", "paper_nonce", "paper_pid", "actor",
    "world", "lane_resident", "physical_action",
])
def test_hostile_adopt_never_publishes(tmp_path, monkeypatch, variant):
    case, turns, lane = setup(tmp_path, monkeypatch, ProviderDecision.resolved("1"))
    try:
        turn = turns[0]
        ticket = submit(lane, turn)
        owner = turn.owner
        bridge = case[1]
        job = lane._jobs[(turn.self_id, turn.work_ref)]
        if variant == "ticket_copy":
            ticket = replace(ticket)
        elif variant == "ticket_self":
            ticket = replace(ticket, self_id="B")
        elif variant == "ticket_work":
            ticket = replace(ticket, work_ref="unregistered-work")
        elif variant == "ticket_request":
            ticket = replace(ticket, request_id="unregistered-request")
        elif variant == "ticket_backend":
            ticket = replace(ticket, backend_ref="wrong-backend")
        elif variant == "ticket_mode":
            ticket = replace(ticket, mode=CognitionMode.THINK)
        elif variant == "ticket_epoch":
            ticket = replace(ticket, self_epoch=ticket.self_epoch + 1)
        elif variant == "turn_swap":
            turn = turns[1]
        elif variant == "candidate_digest":
            turn = replace(turn, candidate_set_sha256="0" * 64)
        elif variant == "request_choices":
            job.request = replace(turn.request, choices=tuple(reversed(turn.request.choices)))
        elif variant == "request_context":
            job.request = replace(turn.request, context=())
        elif variant == "request_identity":
            job.request = replace(turn.request, identity_context=None)
        elif variant == "request_digest":
            job.request_sha256 = "0" * 64
        elif variant == "request_provenance":
            from relay_self.provenance import Provenance
            forged = replace(turn.request.context[0],
                             provenance=Provenance("forged", "foreign-inquiry"))
            job.request = replace(turn.request, context=(forged,))
        elif variant == "probe":
            owner.current_worldbody_observation = replace(owner.current_worldbody_observation)
        elif variant == "paper_session":
            bridge.paper._session_id = "changed"
        elif variant == "native":
            bridge.sessions["A"].started.session_id = "changed"
        elif variant == "paper_pid":
            case = (*case[:2], replace(case[2], paper_pid=case[2].paper_pid + 1),
                    *case[3:])
        elif variant == "actor":
            case = (*case[:4], (replace(case[4][0], paper_actor_uuid="foreign"),
                                case[4][1]), *case[5:])
        elif variant == "world":
            case = (*case[:3], replace(case[3], epoch=case[3].epoch + 1),
                    *case[4:])
        elif variant in ("paper_log", "paper_ack", "paper_nonce"):
            original = bridge.paper.read_owned_log
            def changed(sid):
                raw = original(sid)
                if variant == "paper_log":
                    return raw + b"unexpected-growth\\n"
                if variant == "paper_nonce":
                    return raw.replace(b"nonce=next-nonce", b"nonce=foreign")
                return raw.replace(b"P0D_TICK_ACK", b"P0D_TICK_BAD")
            monkeypatch.setattr(bridge.paper, "read_owned_log", changed)
        elif variant == "other_self_epoch":
            bridge.cognitive_work._states["B"].epoch += 1
        elif variant == "registry":
            owner.pattern_registry = replace(owner.pattern_registry, revision=2)
        elif variant == "continuity":
            from relay_self.exploration_continuity_dev import ExplorationContinuity
            owner.retained = replace(owner.retained, exploration_continuity=ExplorationContinuity("A", 1))
        elif variant == "intent":
            from relay_self.provenance import Provenance
            owner.intent.commit("hostile", objective="test", at_ns=1,
                                provenance=Provenance("test", "hostile-intent"))
        elif variant == "lane_detached":
            bridge.inference_lane = None
        elif variant == "lane_resident":
            lane.cognitive_work = object()
        elif variant == "physical_action":
            bridge.physical._observation_only = False
        elif variant == "gpu_uncertain":
            lane._uncertain = True
        elif variant == "gpu_unfinished":
            from concurrent.futures import Future
            job.future = Future()
        elif variant == "gpu_no_idle":
            job.terminal_slot_idle = False
        else:
            bridge.cognitive_work.fence_self("A")

        before = snapshot(case)
        with pytest.raises((ValueError, RuntimeError, OSError)):
            commit(case, lane, turn, ticket)
        assert snapshot(case) == before
        # Rejection before admission must not burn a fresh, unsubmitted result.
        assert job.question_adoption_state == "unused"
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("choice", [
    ProviderDecision.resolved("2"), ProviderDecision.resolved("3"),
    ProviderDecision.unresolved(reason="none"), ProviderDecision.resolved("99"),
])
def test_non_adopt_choices_are_pure(tmp_path, monkeypatch, choice):
    case, turns, lane = setup(tmp_path, monkeypatch, choice)
    try:
        turn = turns[0]
        ticket = submit(lane, turn)
        before = snapshot(case)
        assert commit(case, lane, turn, ticket) in ("HOLD", "DECLINE", "UNRESOLVED")
        assert snapshot(case) == before
        assert lane._jobs[(turn.self_id, turn.work_ref)].question_adoption_state == "unused"
    finally:
        lane._pool.shutdown(wait=True)


def test_two_distinct_tickets_cannot_adopt_same_inquiry(tmp_path, monkeypatch):
    from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
    from relay_self.bd1b_coverage_adoption_turn_dev import prepare_coverage_adoption_turn
    from test_bd1b_owner_present_dev import _configured
    from test_bd1b_post_gpu_source_dev import attach

    case = _configured(tmp_path, monkeypatch, need=True)
    a = prepare_coverage_adoption_turn(**arguments(case, "A"))
    b = prepare_coverage_adoption_turn(**arguments(case, "A"))
    assert a.inquiry == b.inquiry and a.request.request_id != b.request.request_id
    monkeypatch.setattr(
        LlamaCppRelayProvider, "__call__",
        lambda self, request, mode: ProviderDecision.resolved("1"),
    )
    lane = attach(case[1], monkeypatch)
    try:
        ta = submit(lane, a)
        tb = submit(lane, b)
        assert commit(case, lane, a, ta) == "ADOPT"
        before = snapshot(case)
        with pytest.raises((ValueError, RuntimeError)):
            commit(case, lane, b, tb)
        assert snapshot(case) == before
        assert lane._jobs[("A", b.work_ref)].question_adoption_state == "unused"
        assert len(a.owner.retained.exploration_continuity.questions) == 1
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("variant", ["tampered_file", "tmp_file", "after_replace"])
def test_hostile_storage_fences_without_memory_publication(tmp_path, monkeypatch, variant):
    case, turns, lane = setup(tmp_path, monkeypatch, ProviderDecision.resolved("1"))
    try:
        turn = turns[0]
        ticket = submit(lane, turn)
        owner = turn.owner
        path = owner.files.cognition_file
        original_retained = owner.retained
        before_pending = set(owner.pending_questions)
        if variant == "tampered_file":
            path.write_text("{}")
        elif variant == "tmp_file":
            path.with_name("." + path.name + ".tmp").write_text("not-original")
        else:
            save = storage.save_persistent_cognition
            def save_then_fail(p, cognition):
                save(p, cognition)
                raise OSError("fault after atomic replace")
            monkeypatch.setattr(storage, "save_persistent_cognition", save_then_fail)
        with pytest.raises((ValueError, RuntimeError, OSError)):
            commit(case, lane, turn, ticket)
        assert owner.retained == original_retained
        assert owner.pending_questions == before_pending
        assert case[1].cognitive_work.quarantined_scope(turn.self_id)
        assert lane._jobs[(turn.self_id, turn.work_ref)].question_adoption_state == "failed"
        with pytest.raises((ValueError, RuntimeError, OSError)):
            commit(case, lane, turn, ticket)
        if variant == "after_replace":
            assert load_persistent_cognition(path) != original_retained
    finally:
        lane._pool.shutdown(wait=True)


def test_native_paper_change_during_result_readback_refuses(tmp_path, monkeypatch):
    case, turns, lane = setup(tmp_path, monkeypatch, ProviderDecision.resolved("1"))
    try:
        turn = turns[0]
        ticket = submit(lane, turn)
        original = lane.verify_submitted_bounded_request
        def change_after_result(*args):
            result = original(*args)
            case[1].paper._session_id = "changed-during-readback"
            return result
        monkeypatch.setattr(lane, "verify_submitted_bounded_request", change_after_result)
        before = snapshot(case)
        with pytest.raises((ValueError, RuntimeError)):
            commit(case, lane, turn, ticket)
        assert snapshot(case) == before
        assert lane._jobs[(turn.self_id, turn.work_ref)].question_adoption_state == "unused"
    finally:
        lane._pool.shutdown(wait=True)
