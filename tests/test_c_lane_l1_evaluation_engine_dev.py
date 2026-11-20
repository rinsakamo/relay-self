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
        async def altered(self, ticket, **kwargs):
            result = await original(self, ticket, **kwargs)
            loop.owner.current_worldbody_observation = replace(last, seq=last.seq + 1)
            return result
        monkeypatch.setattr(ResidentLlamaInferenceLane, "await_result", altered)
        with pytest.raises(C1OwnerReviewHold):
            await execute_evaluation(frame, loop, task_id="changed-current", **common)
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
