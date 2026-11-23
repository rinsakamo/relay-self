"""R2-3e CPU DEV: one-shot Original reJOIN Question issuer and per-Self fence.

The ORIGINAL Owner, Bridge, lane and fake Native/Paper are exercised. A stub
provider returns decisions or blocks/fails; no real llama-server/World/Gemma.
"""
from __future__ import annotations

import asyncio
import threading
from dataclasses import replace

import pytest

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from relay_self.r2_3d_original_rejoin_gpu_fence_dev import R23DOriginalRejoinSourceHold
from relay_self.r2_3e_original_rejoin_question_issuer_dev import (
    R23EOriginalRejoinIssueHold,
    R23EOriginalRejoinQuestionOutcome,
)
from relay_self.relay_engine import ProviderDecision
from relay_self.resident_llama_inference_lane_dev import ResidentGpuLaneError
from test_b_np1b_current_composite_source_dev import current as current_fixture
from test_b_np1b_fresh_native_update_dev import files
from test_b_np1b_normal_present_poll_dev import pair as original_pair
from test_b_np1b_owner_bound_rejoin_dev import rejoined as rejoined
from test_b_np1b_rejoin_present_dev import rejoined_present as rejoined_present
from test_r2_3c_original_rejoin_frozen_l1_dev import _state
from test_r2_3d_original_rejoin_gpu_fence_dev import _setup
from test_r2_3d_original_rejoin_gpu_fence_dev import pair as pair


async def _issue(f, lane, turn, *, timeout_s=2.0):
    return await f.cognitive.issue_rejoined_original_question_once_dev(
        bridge=f.bridge, lane=lane, turn=turn, timeout_s=timeout_s,
    )


def _unmodified(f, state, file_state):
    assert _state(f) == state
    assert files(f) == file_state
    assert not f.bridge.physical.active_action_ids


def _assert_one_fenced(f, lane, turn):
    assert turn.self_id in lane._fenced
    assert f.cognitive._state(turn.self_id).mode == "QUARANTINED"
    other = "B" if turn.self_id == "A" else "A"
    assert other not in lane._fenced
    assert f.cognitive.current_scope(other)
    job = lane._jobs.get((turn.self_id, turn.work_ref))
    if job is not None:
        assert job.question_adoption_state == "unused"
        assert job.question_adoption_binding is None
        assert not job.result_adopted


@pytest.mark.parametrize("sid,decision,selection", [
    ("A", ProviderDecision.resolved("1"), "ADOPT"),
    ("B", ProviderDecision.resolved("2"), "HOLD"),
    ("A", ProviderDecision.resolved("3"), "DECLINE"),
    ("B", ProviderDecision.unresolved(reason="unknown"), "UNRESOLVED"),
    ("A", ProviderDecision.resolved("99"), "UNRESOLVED"),
])
def test_r23e_original_owner_issues_once_without_question_adoption(
    pair, monkeypatch, sid, decision, selection,
):
    assert current_fixture is not None and original_pair is not None
    assert rejoined is not None and rejoined_present is not None
    f, lane, turns = _setup(pair, monkeypatch, decision=decision)
    try:
        turn = turns[sid]
        state_before, file_before = _state(f), files(f)
        result = asyncio.run(_issue(f, lane, turn))
        assert type(result) is R23EOriginalRejoinQuestionOutcome
        assert result.selection == selection
        assert result.readback.selection == selection
        assert result.ticket is result.readback.ticket
        assert result.ticket.request_id == turn.request.request_id
        assert result.ticket.work_ref == turn.work_ref
        job = lane._jobs[(sid, turn.work_ref)]
        assert job.ticket is result.ticket
        assert job.request is turn.request
        assert job.future.done() and job.terminal_slot_idle
        assert job.question_adoption_state == "unused"
        assert job.question_adoption_binding is None
        assert not job.result_adopted
        assert result.original_job_submitted
        assert not result.question_adopted
        assert not result.intent_committed
        assert not result.memory_written
        assert not result.skill_issued
        assert not result.physical_issue_authorized
        assert not result.product_l1_input_switched
        assert not result.ticket.action_issue_authorized
        assert f.cognitive._state(sid).mode == "ONLINE"
        assert sid not in lane._fenced
        assert len(lane._jobs) == 1
        _unmodified(f, state_before, file_before)
    finally:
        lane._pool.shutdown(wait=True)


def test_r23e_original_one_shot_rejects_duplicate_without_poisoning_first(
    pair, monkeypatch,
):
    f, lane, turns = _setup(pair, monkeypatch)
    turn = turns["A"]
    try:
        result = asyncio.run(_issue(f, lane, turn))
        assert result.selection == "HOLD"
        before_files, before_state = files(f), _state(f)
        with pytest.raises(R23DOriginalRejoinSourceHold):
            asyncio.run(_issue(f, lane, turn))
        assert len(lane._jobs) == 1
        assert f.cognitive._state("A").mode == "ONLINE"
        assert "A" not in lane._fenced
        _unmodified(f, before_state, before_files)
    finally:
        lane._pool.shutdown(wait=True)


def test_r23e_two_original_selves_issue_separate_jobs_same_lane(pair, monkeypatch):
    f, lane, turns = _setup(pair, monkeypatch)
    try:
        before_files, before_state = files(f), _state(f)
        both = asyncio.run(_both(f, lane, turns))
        assert all(x.selection == "HOLD" for x in both)
        assert len(lane._jobs) == 2
        assert set(lane._jobs) == {
            ("A", turns["A"].work_ref), ("B", turns["B"].work_ref),
        }
        assert "A" not in lane._fenced and "B" not in lane._fenced
        _unmodified(f, before_state, before_files)
    finally:
        lane._pool.shutdown(wait=True)


async def _both(f, lane, turns):
    # The single-slot lane serializes provider calls; two Original Owner
    # frozen Questions have distinct registered Source and ticket identities.
    return await asyncio.gather(
        _issue(f, lane, turns["A"]), _issue(f, lane, turns["B"]),
    )


@pytest.mark.parametrize("failure", (
    "bad_timeout", "missing_turn", "wrong_owner", "stale_paper",
    "not_observation_only", "foreign_lane",
))
def test_r23e_unqualified_before_submission_creates_no_job_or_fence(
    pair, monkeypatch, failure,
):
    f, lane, turns = _setup(pair, monkeypatch)
    other = None
    try:
        turn = turns["A"]
        opts = {}
        if failure == "bad_timeout":
            opts["timeout_s"] = 200
        elif failure == "missing_turn":
            turn = None
        elif failure == "wrong_owner":
            # Corrupt original Bridge identity rather than constructing a
            # forged frozen turn, which its own constructor must reject.
            f.bridge.owners["A"] = f.owners["B"]
        elif failure == "stale_paper":
            with f.paper._log_path.open("a") as stream:
                stream.write("R23E_PRE_SEND_PAPER_GROWTH\n")
        elif failure == "not_observation_only":
            f.bridge.physical._observation_only = False
        else:
            other = object()
        before = files(f)
        with pytest.raises((R23EOriginalRejoinIssueHold, R23DOriginalRejoinSourceHold)):
            asyncio.run(
                f.cognitive.issue_rejoined_original_question_once_dev(
                    bridge=f.bridge, lane=other or lane, turn=turn, **opts,
                )
            )
        assert lane._jobs == {}
        assert "A" not in lane._fenced
        assert f.cognitive._state("A").mode == "ONLINE"
        assert files(f) == before
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("failure", (
    "paper_drift", "request_tamper", "result_type", "result_failure",
    "lane_removed", "original_epoch", "b_epoch", "native_drift",
))
def test_r23e_post_submission_failure_fences_only_original_self(
    pair, monkeypatch, failure,
):
    f, lane, turns = _setup(pair, monkeypatch)
    turn = turns["A"]

    def bad_provider(self, request, mode):
        if failure == "paper_drift":
            with f.paper._log_path.open("a") as stream:
                stream.write("R23E_POST_SUBMISSION_PAPER_CHANGED\n")
        elif failure == "request_tamper":
            lane._jobs[("A", turn.work_ref)].request = replace(
                request, choices=tuple(reversed(request.choices)),
            )
        elif failure == "result_type":
            return object()
        elif failure == "result_failure":
            raise ValueError("synthetic provider fault")
        elif failure == "lane_removed":
            f.bridge.inference_lane = None
        elif failure == "original_epoch":
            f.cognitive._states["A"].epoch += 1
        elif failure == "b_epoch":
            f.cognitive._states["B"].epoch += 1
        elif failure == "native_drift":
            session = f.bridge.sessions["A"]
            session._started = replace(
                session.started, session_id="different-native",
            )
        return ProviderDecision.resolved("1")

    monkeypatch.setattr(LlamaCppRelayProvider, "__call__", bad_provider)
    try:
        before_files, before_state = files(f), _state(f)
        with pytest.raises(BaseException):
            asyncio.run(_issue(f, lane, turn))
        assert len(lane._jobs) == 1
        _assert_one_fenced(f, lane, turn)
        # Neither the returned ADOPT choice nor failure may write cognition.
        _unmodified(f, before_state, before_files)
    finally:
        lane._pool.shutdown(wait=True)


def test_r23e_ambiguous_submit_raises_after_enqueue_and_fences(pair, monkeypatch):
    f, lane, turns = _setup(pair, monkeypatch)
    turn = turns["A"]
    original_submit = lane.submit

    def uncertain_submit(*args, **kwargs):
        original_submit(*args, **kwargs)
        raise RuntimeError("original lane enqueued but issuer ticket lost")

    monkeypatch.setattr(lane, "submit", uncertain_submit)
    try:
        before_files, before_state = files(f), _state(f)
        with pytest.raises(RuntimeError, match="ticket lost"):
            asyncio.run(_issue(f, lane, turn))
        assert len(lane._jobs) == 1
        _assert_one_fenced(f, lane, turn)
        _unmodified(f, before_state, before_files)
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("kind", ("timeout", "cancel"))
def test_r23e_timeout_or_cancel_cannot_replay_or_adopt(
    pair, monkeypatch, kind,
):
    f, lane, turns = _setup(pair, monkeypatch)
    turn = turns["A"]
    started = threading.Event()
    release = threading.Event()

    def blocked_provider(self, request, mode):
        started.set()
        if not release.wait(timeout=5.0):
            raise RuntimeError("synthetic blocked provider was not released")
        return ProviderDecision.resolved("1")

    monkeypatch.setattr(LlamaCppRelayProvider, "__call__", blocked_provider)
    async def run():
        t = asyncio.create_task(
            _issue(f, lane, turn, timeout_s=0.02 if kind == "timeout" else 5.0)
        )
        for _ in range(1000):
            if started.is_set():
                break
            await asyncio.sleep(0.001)
        assert started.is_set()
        if kind == "cancel":
            t.cancel()
            with pytest.raises(asyncio.CancelledError):
                await t
        else:
            with pytest.raises(ResidentGpuLaneError, match="elapsed"):
                await t

    try:
        before_files, before_state = files(f), _state(f)
        asyncio.run(run())
        _assert_one_fenced(f, lane, turn)
        assert len(lane._jobs) == 1
        _unmodified(f, before_state, before_files)
        with pytest.raises(R23DOriginalRejoinSourceHold):
            asyncio.run(_issue(f, lane, turn))
    finally:
        release.set()
        lane._pool.shutdown(wait=True)


def test_r23e_result_readback_drift_fences_without_commit(pair, monkeypatch):
    from relay_self import r2_3e_original_rejoin_question_issuer_dev as issuer

    f, lane, turns = _setup(pair, monkeypatch)
    turn = turns["A"]
    original = issuer.read_r23d_original_rejoin_result_cpu

    def forged_readback(**kwargs):
        good = original(**kwargs)
        return replace(
            good,
            preflight=replace(
                good.preflight, source_pair_revision="other-source",
            ),
        )

    monkeypatch.setattr(issuer, "read_r23d_original_rejoin_result_cpu", forged_readback)
    try:
        before_files, before_state = files(f), _state(f)
        with pytest.raises(R23DOriginalRejoinSourceHold):
            asyncio.run(_issue(f, lane, turn))
        _assert_one_fenced(f, lane, turn)
        _unmodified(f, before_state, before_files)
    finally:
        lane._pool.shutdown(wait=True)


def test_r23e_simultaneous_same_work_second_refused_no_double_issue(
    pair, monkeypatch,
):
    f, lane, turns = _setup(pair, monkeypatch)
    turn = turns["A"]

    async def race():
        outcomes = await asyncio.gather(
            _issue(f, lane, turn), _issue(f, lane, turn),
            return_exceptions=True,
        )
        good = [o for o in outcomes if type(o) is R23EOriginalRejoinQuestionOutcome]
        bad = [o for o in outcomes if isinstance(o, BaseException)]
        assert len(good) == 1
        assert len(bad) == 1
        assert isinstance(bad[0], R23DOriginalRejoinSourceHold)

    try:
        before_files, before_state = files(f), _state(f)
        asyncio.run(race())
        assert len(lane._jobs) == 1
        assert f.cognitive._state("A").mode == "ONLINE"
        assert "A" not in lane._fenced
        _unmodified(f, before_state, before_files)
    finally:
        lane._pool.shutdown(wait=True)
