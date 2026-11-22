"""I2d adversarial CPU/offline original A/B Self-driven schema adoption.

The fake provider supplies actual results to the *existing* singleton
ResidentLlamaInferenceLane. These tests do not call real llama.cpp or Paper.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import threading
from dataclasses import replace

import pytest

from relay_self import i_lane_i2d_self_schema_adoption_dev as i2d
from relay_self.cognitive_minimal_dev import (
    Origin,
    PatternKind,
    Predicate,
    initial_patterns,
)
from relay_self.i_lane_i2_original_exploration_handoff_dev import (
    prepare_i2_original_goal_handoff,
)
from relay_self.i_lane_i2d_self_schema_adoption_dev import (
    I2dOriginalHold,
    finish_i2d_self_adoption,
    run_i2d_self_adoption,
    submit_i2d_original_l1_acceptance,
    submit_i2d_original_l2,
)
from relay_self.persistent_cognition import (
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    ProviderDecision,
    ProviderExpression,
)
from relay_self.self_owner_checkpoint_dev import (
    SelfOwnerCut,
    load_self_owner_cut,
    rehydrate_self_owner,
    save_self_owner_cut,
)
from test_bd1b_owner_source_dev import _files
from test_i_lane_i2_original_exploration_handoff_dev import _args
from test_i_lane_i2b_original_shared_l1_dev import _fixture


def _model_pattern(pattern_id="learned-explore-A"):
    return json.dumps({
        "pattern_id": pattern_id, "version": 1,
        "schema_id": "exploration", "kind": "GOAL",
        "predicate": "EXPLORE", "goal_id": "EXPLORE_WORLD",
        "skill_id": None, "skill_version": None, "target_kind": None,
    }, separators=(",", ":"), sort_keys=True)


def _case(tmp_path, monkeypatch, *, vote="1", model_text=None,
          model_wait=None, model_release=None):
    case, lane = _fixture(tmp_path, monkeypatch, exploration=False)
    bridge = case[1]
    # This synthetic future Owner already persisted its original innate
    # Registry before the decision. Historical v1 cognition with NO saved
    # Registry is deliberately excluded rather than silently upgraded.
    for sid in ("A", "B"):
        owner = bridge.owners[sid]
        owner.retained = replace(
            owner.retained, pattern_registry=owner.pattern_registry,
        )
        save_persistent_cognition(owner.files.cognition_file, owner.retained)
    bridge.inference_lane = lane
    called = []
    def provider(request, *, mode):
        called.append((mode, request.request_id))
        if model_wait is not None:
            model_wait.set()
        if model_release is not None:
            assert model_release.wait(5)
        if mode is CognitionMode.OPEN:
            return ProviderExpression(
                model_text if model_text is not None else _model_pattern(),
                Provenance("synthetic-l2", request.request_id),
            )
        if vote is None:
            return ProviderDecision.unresolved(reason="synthetic uncertain")
        return ProviderDecision.resolved(vote)
    lane.provider = provider
    return case, lane, called


def _args_no_sid(case):
    return {
        "bridge": case[1], "boot": case[2], "world": case[3],
        "links": case[4],
    }


@pytest.mark.parametrize(("vote", "expected"), [
    ("1", "SELF_ACCEPTED_NONMOTOR_EXPLORATION_SCHEMA"),
    ("2", "DEFER"), (None, "UNRESOLVED"),
])
def test_i2d_real_original_two_model_tickets_self_vote_drives_adoption(
    tmp_path, monkeypatch, vote, expected,
):
    case, lane, called = _case(tmp_path, monkeypatch, vote=vote)
    try:
        before = _files(case[1])
        b_before = (
            case[1].owners["B"].retained, case[1].owners["B"].pattern_registry,
            case[1].owners["B"].intent.events,
        )
        result = asyncio.run(run_i2d_self_adoption(
            **_args(case, "A"), lane=lane, timeout_s=3.0,
        ))
        assert result.outcome == expected
        assert [x[0] for x in called] == [
            CognitionMode.OPEN, CognitionMode.BOUNDED,
        ]
        assert result.l2_ticket.self_id == result.l1_ticket.self_id == "A"
        assert result.l2_ticket.work_ref != result.l1_ticket.work_ref
        assert not result.question_adopted and not result.intent_committed
        assert not result.physical_action_authorized and result.goal_unresolved
        assert case[1].physical.active_action_ids == ()
        owner = case[1].owners["A"]
        if vote == "1":
            assert result.pattern_registry_revision == 1
            assert owner.retained.pattern_registry == owner.pattern_registry
            assert load_persistent_cognition(owner.files.cognition_file) == owner.retained
            learned = owner.pattern_registry.patterns[-1]
            assert learned.origin is Origin.LEARNED
            assert learned.predicate is Predicate.EXPLORE
            assert learned.kind is PatternKind.GOAL
            assert learned.goal_id == "EXPLORE_WORLD"
            assert learned.skill_id is None and learned.target_kind is None
            assert case[1].cognitive_work._present_schemas["A"][0].get(
                "exploratory"
            ).mode.value == "FULL"
            # New source, not old I2: only unresolved exploration Goal.
            h = prepare_i2_original_goal_handoff(
                **_args(case, "A"), i2b_read_attached_lane=True,
            )
            assert h.status == "EXPLORATION_GOAL_UNRESOLVED_TARGET"
            assert h.goal_candidates[0].unresolved
            assert not h.goal_candidates[0].skill_id
            assert h.question_candidate_ref is not None
            assert before != _files(case[1])
        else:
            assert result.pattern_registry_revision == 0
            assert len(owner.pattern_registry.patterns) == 4
            assert case[1].cognitive_work._present_schemas["A"][0].modules == ()
            assert before == _files(case[1])
        b = case[1].owners["B"]
        assert (b.retained, b.pattern_registry, b.intent.events) == b_before
        assert b.pattern_registry == initial_patterns()
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("fault", [
    "missing-durable-registry", "busy-gpu", "physical-enabled",
    "foreign-source", "active-intent", "stale-native",
])
def test_i2d_preflight_no_submission_on_stale_owner(
    tmp_path, monkeypatch, fault,
):
    case, lane, called = _case(tmp_path, monkeypatch)
    try:
        bridge = case[1]
        if fault == "missing-durable-registry":
            bridge.owners["A"].retained = replace(
                bridge.owners["A"].retained, pattern_registry=None,
            )
            save_persistent_cognition(
                bridge.owners["A"].files.cognition_file,
                bridge.owners["A"].retained,
            )
        elif fault == "busy-gpu":
            lane.witness.require_idle = lambda: (_ for _ in ()).throw(
                RuntimeError("synthetic occupied slot")
            )
        elif fault == "physical-enabled":
            bridge.physical._observation_only = False
        elif fault == "foreign-source":
            bridge._i1_correlated_sense["A"] = bridge._i1_correlated_sense["B"]
        elif fault == "active-intent":
            from relay_self.intent import IntentCommitment
            intent = IntentCommitment()
            intent.commit(
                "other-intent", objective="unrelated",
                at_ns=1, provenance=Provenance("synthetic", "test"),
            )
            bridge.owners["A"].intent = intent
        else:
            bridge.cognitive_work.fence_self("A")
        with pytest.raises((I2dOriginalHold, RuntimeError)):
            submit_i2d_original_l2(
                **_args(case, "A"), lane=lane,
            )
        assert not called
        assert len(lane._jobs) == 0
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("model_text", [
    "not-json",
    json.dumps({
        "pattern_id": "wrong-skill", "version": 1,
        "schema_id": "exploration", "kind": "GOAL",
        "predicate": "EXPLORE", "goal_id": "EXPLORE_WORLD",
        "skill_id": "MOVE", "skill_version": 1, "target_kind": "RELATIVE",
    }),
    json.dumps({
        "pattern_id": "wrong-owner", "version": 1,
        "schema_id": "homeostatic", "kind": "GOAL",
        "predicate": "HUNGRY", "goal_id": "EAT",
        "skill_id": "EAT", "skill_version": 1, "target_kind": "FOOD",
    }),
])
def test_i2d_no_l1_ticket_when_open_l2_not_nonmotor_candidate(
    tmp_path, monkeypatch, model_text,
):
    case, lane, called = _case(
        tmp_path, monkeypatch, model_text=model_text,
    )
    try:
        previous = _files(case[1])
        l2 = submit_i2d_original_l2(**_args(case, "A"), lane=lane)
        asyncio.run(lane.await_result(l2.ticket, timeout_s=3.0))
        with pytest.raises(I2dOriginalHold):
            submit_i2d_original_l1_acceptance(
                **_args_no_sid(case), proposed=l2, lane=lane,
            )
        assert [x[0] for x in called] == [CognitionMode.OPEN]
        assert _files(case[1]) == previous
        assert case[1].physical.active_action_ids == ()
    finally:
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("fault", [
    "foreign-l2-ticket", "altered-l2-request", "paper-source",
    "registry", "new-native", "retired", "altered-l1-request",
    "foreign-l1-ticket", "other-self-intent",
])
def test_i2d_model_vote_cannot_override_stale_source_or_tickets(
    tmp_path, monkeypatch, fault,
):
    case, lane, called = _case(tmp_path, monkeypatch)
    try:
        previous = _files(case[1])
        l2 = submit_i2d_original_l2(**_args(case, "A"), lane=lane)
        asyncio.run(lane.await_result(l2.ticket, timeout_s=3.0))
        accept = submit_i2d_original_l1_acceptance(
            **_args_no_sid(case), proposed=l2, lane=lane,
        )
        asyncio.run(lane.await_result(accept.ticket, timeout_s=3.0))
        bridge = case[1]
        if fault == "foreign-l2-ticket":
            l2.ticket = replace(l2.ticket, self_id="B")
        elif fault == "altered-l2-request":
            l2.request = replace(l2.request, instruction="injected L2 instruction")
        elif fault == "paper-source":
            with bridge.paper._log_path.open("ab") as stream:
                stream.write(b"unrelated-new-paper-ACK\n")
        elif fault == "registry":
            owner = bridge.owners["A"]
            owner.pattern_registry = replace(
                owner.pattern_registry, revision=2,
            )
        elif fault == "new-native":
            bridge._i1_correlated_sense["A"] = bridge._i1_correlated_sense["B"]
        elif fault == "retired":
            bridge.cognitive_work.fence_self("A")
            lane.fence_self("A")
        elif fault == "altered-l1-request":
            accept.request = replace(
                accept.request, instruction="forged acceptance",
            )
        elif fault == "foreign-l1-ticket":
            accept.ticket = replace(accept.ticket, self_id="B")
        else:
            owner = bridge.owners["A"]
            owner.intent.commit(
                "other-intent", objective="stale-owner",
                at_ns=1, provenance=Provenance("synthetic", "test"),
            )
        with pytest.raises(I2dOriginalHold):
            finish_i2d_self_adoption(
                **_args_no_sid(case), accepted=accept, lane=lane,
            )
        assert _files(case[1]) == previous
        assert case[1].physical.active_action_ids == ()
    finally:
        lane._pool.shutdown(wait=True)


def test_i2d_same_ticket_cannot_publish_twice_or_accept_after_defer(
    tmp_path, monkeypatch,
):
    case, lane, _ = _case(tmp_path, monkeypatch)
    try:
        l2 = submit_i2d_original_l2(**_args(case, "A"), lane=lane)
        asyncio.run(lane.await_result(l2.ticket, timeout_s=3.0))
        accept = submit_i2d_original_l1_acceptance(
            **_args_no_sid(case), proposed=l2, lane=lane,
        )
        asyncio.run(lane.await_result(accept.ticket, timeout_s=3.0))
        first = finish_i2d_self_adoption(
            **_args_no_sid(case), accepted=accept, lane=lane,
        )
        assert first.outcome == "SELF_ACCEPTED_NONMOTOR_EXPLORATION_SCHEMA"
        with pytest.raises(I2dOriginalHold):
            finish_i2d_self_adoption(
                **_args_no_sid(case), accepted=accept, lane=lane,
            )
        with pytest.raises(I2dOriginalHold):
            submit_i2d_original_l1_acceptance(
                **_args_no_sid(case), proposed=l2, lane=lane,
            )
    finally:
        lane._pool.shutdown(wait=True)


def test_i2d_logout_during_open_l2_does_not_submit_l1_or_commit(
    tmp_path, monkeypatch,
):
    entered, release = threading.Event(), threading.Event()
    case, lane, called = _case(
        tmp_path, monkeypatch, model_wait=entered, model_release=release,
    )
    try:
        before = _files(case[1])
        async def scenario():
            t = asyncio.create_task(run_i2d_self_adoption(
                **_args(case, "A"), lane=lane, timeout_s=3.0,
            ))
            assert await asyncio.to_thread(entered.wait, 2)
            case[1].cognitive_work.fence_self("A")
            lane.fence_self("A")
            release.set()
            with pytest.raises(I2dOriginalHold):
                await t
        asyncio.run(scenario())
        assert len(lane._jobs) == 1
        assert _files(case[1]) == before
        assert case[1].physical.active_action_ids == ()
    finally:
        release.set()
        lane._pool.shutdown(wait=True)


@pytest.mark.parametrize("fault", [
    "failed-save", "postwrite-paper-growth",
])
def test_i2d_owner_persistence_failure_fences_without_live_publication(
    tmp_path, monkeypatch, fault,
):
    case, lane, called = _case(tmp_path, monkeypatch)
    try:
        bridge = case[1]
        owner = bridge.owners["A"]
        before = owner.retained
        old_registry = owner.pattern_registry
        original_save = i2d.save_persistent_cognition

        def hostile_save(path, cognition):
            if fault == "failed-save":
                raise OSError("synthetic disk failure")
            original_save(path, cognition)
            with bridge.paper._log_path.open("ab") as stream:
                stream.write(b"PAPER_CHANGED_DURING_FSYNC\n")

        monkeypatch.setattr(i2d, "save_persistent_cognition", hostile_save)
        with pytest.raises(I2dOriginalHold, match="persistence uncertain"):
            asyncio.run(run_i2d_self_adoption(
                **_args(case, "A"), lane=lane, timeout_s=3,
            ))
        assert len(called) == 2
        assert owner.retained is before
        assert owner.pattern_registry is old_registry
        assert bridge.cognitive_work._states["A"].mode == "QUARANTINED"
        assert "A" in lane._fenced
        assert bridge.physical.active_action_ids == ()
        if fault == "failed-save":
            assert load_persistent_cognition(owner.files.cognition_file) == before
        else:
            # Disk may have changed; never announce an adopted live Owner.
            assert load_persistent_cognition(owner.files.cognition_file) != before
    finally:
        lane._pool.shutdown(wait=True)


def test_i2d_owner_model_adoption_is_compatible_with_future_v3_typed_cut(
    tmp_path, monkeypatch,
):
    case, lane, _ = _case(tmp_path, monkeypatch)
    try:
        result = asyncio.run(run_i2d_self_adoption(
            **_args(case, "A"), lane=lane, timeout_s=3.0,
        ))
        assert result.outcome == "SELF_ACCEPTED_NONMOTOR_EXPLORATION_SCHEMA"
        bridge = case[1]
        owner = bridge.owners["A"]
        snapshot = bridge.cognitive_work._present_schemas["A"][0]
        path = tmp_path / "future-a-owner-state.json"
        cut = SelfOwnerCut(
            generation_id="g-i2d-future-a", self_id="A",
            world_id=case[3].world_id, branch_id=case[3].branch_id,
            former_native_session_id=owner.native_session_id,
            last_observed_world_tick=owner.last_observed_tick,
            intent_events=owner.intent.events,
            skill_executions=(),
            pattern_registry=owner.pattern_registry,
            cognition_sha256=hashlib.sha256(
                owner.files.cognition_file.read_bytes(),
            ).hexdigest(),
            recorded_schema=snapshot,
        )
        save_self_owner_cut(path, cut)
        decoded = load_self_owner_cut(path)
        assert decoded == cut
        assert decoded.recorded_schema == snapshot
        restored = rehydrate_self_owner(decoded)
        assert restored.pattern_registry == owner.pattern_registry
        assert restored.old_skill_resume_authorized is False
        assert restored.new_physical_action_issue_authorized is False
        assert bridge.physical.active_action_ids == ()
    finally:
        lane._pool.shutdown(wait=True)
