"""Synthetic HTTP through the original resident lane, never a real model."""
from relay_self.c_lane_l1_evaluation_engine_dev import execute_evaluation
from relay_self.c_lane_stage27hi_multi_action_review_dev import prepare_stage27hi_multi_review
from relay_self.skill import SkillState
from test_c_lane_stage27hi_multi_action_review_dev import _fixture, _run_multi


def test_five_axes_use_resident_lane_and_preserve_owner(tmp_path):
    async def scenario(f, lane, server):
        loop, step, first, receipts, before = await _run_multi(f, lane, server)
        last = receipts[-1].settled_probe
        common = dict(physical=f.physical, lane=lane, bridge=f.bridge,
                      first_action_probe=first, last_settled_probe=last)
        current = common["last_settled_probe"]
        loop.owner.observe_world_tick(
            session_id=current.session_id,
            world_tick=current.snapshot.time.day * 24000 + current.snapshot.time.time_of_day,
        )
        loop.owner.accept_rejoined_worldbody(current, request_id=current.request_id)
        frame = prepare_stage27hi_multi_review(
            loop, step, world_id=f.lifecycle.world.world_id, **common,
        )
        server.choice_id = "1"
        evaluation = await execute_evaluation(frame, loop, task_id="five-axis-test", **common)
        assert len(server.calls) == before + 5
        assert len(evaluation.receipts) == len(evaluation.readout.axes) == 5
        assert all(a.choice_id == "1" and a.evidence_refs for a in evaluation.readout.axes)
        assert all(r.request_sha256 and r.response_sha256 for r in evaluation.receipts)
        assert loop.owner.skills[frame.skill_execution_id].state is SkillState.STARTED
        assert loop.owner.retained.memories == ()
        assert len(loop._seen_action_ids) == 3
    _fixture(tmp_path, scenario)


def test_duplicate_task_is_rejected(tmp_path):
    import pytest

    from relay_self.resident_llama_inference_lane_dev import ResidentGpuLaneError

    async def scenario(f, lane, server):
        loop, step, first, receipts, _ = await _run_multi(f, lane, server)
        common = dict(physical=f.physical, lane=lane, bridge=f.bridge,
                      first_action_probe=first, last_settled_probe=receipts[-1].settled_probe)
        current = common["last_settled_probe"]
        loop.owner.observe_world_tick(
            session_id=current.session_id,
            world_tick=current.snapshot.time.day * 24000 + current.snapshot.time.time_of_day,
        )
        loop.owner.accept_rejoined_worldbody(current, request_id=current.request_id)
        frame = prepare_stage27hi_multi_review(
            loop, step, world_id=f.lifecycle.world.world_id, **common,
        )
        server.choice_id = "1"
        await execute_evaluation(frame, loop, task_id="duplicate", **common)
        with pytest.raises(ResidentGpuLaneError):
            await execute_evaluation(frame, loop, task_id="duplicate", **common)
        assert loop.owner.skills[frame.skill_execution_id].state is SkillState.STARTED
        assert loop.owner.retained.memories == ()
        assert len(loop._seen_action_ids) == 3
    _fixture(tmp_path, scenario)


def test_changed_current_during_inference_holds(tmp_path, monkeypatch):
    from dataclasses import replace

    import pytest

    from relay_self.c_lane_stage27g_original_owner_review_dev import C1OwnerReviewHold
    from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane

    original = ResidentLlamaInferenceLane.await_result

    async def scenario(f, lane, server):
        loop, step, first, receipts, _ = await _run_multi(f, lane, server)
        last = receipts[-1].settled_probe
        common = dict(physical=f.physical, lane=lane, bridge=f.bridge,
                      first_action_probe=first, last_settled_probe=last)
        current = common["last_settled_probe"]
        loop.owner.observe_world_tick(
            session_id=current.session_id,
            world_tick=current.snapshot.time.day * 24000 + current.snapshot.time.time_of_day,
        )
        loop.owner.accept_rejoined_worldbody(current, request_id=current.request_id)
        frame = prepare_stage27hi_multi_review(
            loop, step, world_id=f.lifecycle.world.world_id, **common,
        )
        count = 0
        async def altered(self, ticket, **kwargs):
            nonlocal count
            result = await original(self, ticket, **kwargs)
            count += 1
            if count == 3:
                loop.owner.current_worldbody_observation = replace(last, seq=last.seq + 1)
            return result
        monkeypatch.setattr(ResidentLlamaInferenceLane, "await_result", altered)
        with pytest.raises(C1OwnerReviewHold) as failure:
            await execute_evaluation(frame, loop, task_id="changed-current", **common)
        assert len(failure.value.evaluation_audit.receipts) == 3
        assert len(failure.value.evaluation_audit.axes) == 2
        assert loop.owner.skills[frame.skill_execution_id].state is SkillState.STARTED
        assert loop.owner.retained.memories == ()
        assert len(loop._seen_action_ids) == 3
    _fixture(tmp_path, scenario)


def test_single_action_budget_stop_with_unknowns(tmp_path):
    from test_p0d_stage27h_bounded_l0_move_dev import SlowPlaceNative, _issue, _start

    async def scenario(f, lane, server):
        pre, handoff, former, first, loop = await _start(f, lane)
        native = SlowPlaceNative(handoff.native_session_id)
        assert loop.pre_action(first, now_ns=150).status == "L0_CONTINUE_MOVE"
        receipt = await _issue(f, pre, handoff, loop, former, first, native)
        step = loop.observe_terminal_action(
            receipt, source_probe=first,
            now_ns=loop.start_ns + loop.invocation.budget.max_duration_ms * 1_000_000,
        )
        last = receipt.settled_probe
        loop.owner.observe_world_tick(
            session_id=last.session_id,
            world_tick=last.snapshot.time.day * 24000 + last.snapshot.time.time_of_day,
        )
        loop.owner.accept_rejoined_worldbody(last, request_id=last.request_id)
        common = dict(physical=f.physical, lane=lane, bridge=f.bridge,
                      first_action_probe=first, last_settled_probe=last)
        frame = prepare_stage27hi_multi_review(
            loop, step, world_id=f.lifecycle.world.world_id, **common,
        )
        before = len(server.calls)
        server.choice_id = "2"
        result = await execute_evaluation(frame, loop, task_id="budget-unknown", **common)
        assert len(server.calls) == before + 5
        assert all(axis.choice_id == "2" for axis in result.readout.axes)
        assert not frame.completion_review_offered
        assert loop.owner.skills[frame.skill_execution_id].state is SkillState.STARTED
        assert loop.owner.retained.memories == ()
        assert len(loop._seen_action_ids) == 1
    _fixture(tmp_path, scenario)


def test_wal_tampering_during_inference_holds(tmp_path, monkeypatch):
    import pytest

    from relay_self.c_lane_stage27g_original_owner_review_dev import C1OwnerReviewHold
    from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane

    original = ResidentLlamaInferenceLane.await_result

    async def scenario(f, lane, server):
        loop, step, first, receipts, _ = await _run_multi(f, lane, server)
        last = receipts[-1].settled_probe
        loop.owner.observe_world_tick(
            session_id=last.session_id,
            world_tick=last.snapshot.time.day * 24000 + last.snapshot.time.time_of_day,
        )
        loop.owner.accept_rejoined_worldbody(last, request_id=last.request_id)
        common = dict(physical=f.physical, lane=lane, bridge=f.bridge,
                      first_action_probe=first, last_settled_probe=last)
        frame = prepare_stage27hi_multi_review(
            loop, step, world_id=f.lifecycle.world.world_id, **common,
        )
        async def altered(self, ticket, **kwargs):
            result = await original(self, ticket, **kwargs)
            loop.owner.files.physical_wal_file.write_bytes(b"tampered")
            return result
        monkeypatch.setattr(ResidentLlamaInferenceLane, "await_result", altered)
        with pytest.raises(C1OwnerReviewHold):
            await execute_evaluation(frame, loop, task_id="changed-wal", **common)
        assert loop.owner.skills[frame.skill_execution_id].state is SkillState.STARTED
        assert loop.owner.retained.memories == ()
        assert len(loop._seen_action_ids) == 3
    _fixture(tmp_path, scenario)


def test_third_axis_interruption_preserves_first_two_receipts(tmp_path, monkeypatch):
    import asyncio

    import pytest

    from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane

    original = ResidentLlamaInferenceLane.await_result

    async def scenario(f, lane, server):
        loop, step, first, actions, _ = await _run_multi(f, lane, server)
        last = actions[-1].settled_probe
        loop.owner.observe_world_tick(
            session_id=last.session_id,
            world_tick=last.snapshot.time.day * 24000 + last.snapshot.time.time_of_day,
        )
        loop.owner.accept_rejoined_worldbody(last, request_id=last.request_id)
        common = dict(physical=f.physical, lane=lane, bridge=f.bridge,
                      first_action_probe=first, last_settled_probe=last)
        frame = prepare_stage27hi_multi_review(
            loop, step, world_id=f.lifecycle.world.world_id, **common,
        )
        count = 0

        async def interrupted(self, ticket, **kwargs):
            nonlocal count
            count += 1
            if count == 3:
                raise asyncio.CancelledError()
            return await original(self, ticket, **kwargs)

        monkeypatch.setattr(ResidentLlamaInferenceLane, "await_result", interrupted)
        server.choice_id = "1"
        with pytest.raises(asyncio.CancelledError) as failure:
            await execute_evaluation(frame, loop, task_id="interrupted", **common)
        audit = failure.value.evaluation_audit
        assert len(audit.axes) == len(audit.receipts) == 2
        assert all(r.request_sha256 and r.response_sha256 for r in audit.receipts)
        assert loop.owner.skills[frame.skill_execution_id].state is SkillState.STARTED
        assert loop.owner.retained.memories == ()
        assert len(loop._seen_action_ids) == 3
    _fixture(tmp_path, scenario)


def test_mixed_unknown_and_unresolved_through_http(tmp_path, monkeypatch):
    from relay_self.c_lane_evaluation_readout_dev import AxisStatus
    from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane

    original = ResidentLlamaInferenceLane.submit

    async def scenario(f, lane, server):
        loop, step, first, actions, _ = await _run_multi(f, lane, server)
        last = actions[-1].settled_probe
        loop.owner.observe_world_tick(
            session_id=last.session_id,
            world_tick=last.snapshot.time.day * 24000 + last.snapshot.time.time_of_day,
        )
        loop.owner.accept_rejoined_worldbody(last, request_id=last.request_id)
        common = dict(physical=f.physical, lane=lane, bridge=f.bridge,
                      first_action_probe=first, last_settled_probe=last)
        frame = prepare_stage27hi_multi_review(
            loop, step, world_id=f.lifecycle.world.world_id, **common,
        )
        responses = iter(("1", "2", None, "1", "1"))

        def submit(self, *args, **kwargs):
            server.choice_id = next(responses)
            return original(self, *args, **kwargs)

        monkeypatch.setattr(ResidentLlamaInferenceLane, "submit", submit)
        result = await execute_evaluation(frame, loop, task_id="mixed", **common)
        assert [a.status for a in result.readout.axes] == [
            AxisStatus.RESOLVED, AxisStatus.UNKNOWN, AxisStatus.UNRESOLVED,
            AxisStatus.RESOLVED, AxisStatus.RESOLVED,
        ]
        assert not result.readout.complete
        assert len(result.receipts) == 5
        assert loop.owner.skills[frame.skill_execution_id].state is SkillState.STARTED
        assert loop.owner.retained.memories == ()
        assert len(loop._seen_action_ids) == 3
    _fixture(tmp_path, scenario)


def test_progress_candidates_follow_comparable_observations():
    import json
    from types import SimpleNamespace

    from relay_self.c_lane_l1_evaluation_engine_dev import build_evaluation_steps

    def descriptions(before, after, reached=False):
        facts = {"original_action_ids": ["a"], "initial_target_gap_m": before,
                 "target_gap_m": after, "executed_actions": [{"displacement_m": 1.0}]}
        frame = SimpleNamespace(
            request=SimpleNamespace(context=[SimpleNamespace(value_json=json.dumps(facts))]),
            wal_digest="a" * 64, native_session_id="session", last_probe_seq=2,
            target_contract_ref="target", terminal_status="budget", action_ids=("a",),
            completion_review_offered=reached,
        )
        steps = build_evaluation_steps(frame)
        return [c.choice.description for c in steps[0].candidates]

    for before, after, fragment in [(3, 1, "decreased"), (1, 1, "did not change"),
                                    (1, 3, "increased"), (None, 3, "unavailable")]:
        choices = descriptions(before, after)
        assert fragment in choices[0]
        assert choices[1] == "UNKNOWN"
    assert "arrival condition observed" in descriptions(3, 0, reached=True)[0]
