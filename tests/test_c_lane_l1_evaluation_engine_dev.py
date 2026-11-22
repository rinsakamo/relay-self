"""Synthetic HTTP through the original resident lane, never a real model."""
from relay_self.c_lane_l1_evaluation_engine_dev import execute_evaluation
from relay_self.c_lane_stage27hi_multi_action_review_dev import prepare_stage27hi_multi_review
from relay_self.skill import SkillState
from test_c_lane_stage27hi_multi_action_review_dev import _fixture, _run_multi


def test_source_admission_and_bounded_uncertainty(tmp_path):
    from dataclasses import replace

    import pytest

    from relay_self.c_lane_l1_evaluation_engine_dev import build_evaluation_steps
    from relay_self.c_lane_stage27g_original_owner_review_dev import C1OwnerReviewHold

    async def scenario(f, lane, server):
        loop, step, first, actions, _ = await _run_multi(f, lane, server)
        last = actions[-1].settled_probe
        common = dict(physical=f.physical, lane=lane, bridge=f.bridge,
                      first_action_probe=first, last_settled_probe=last,
                      world_id=f.lifecycle.world.world_id)
        frame = prepare_stage27hi_multi_review(loop, step, **common)
        steps = build_evaluation_steps(frame)
        assert len(steps) == 5
        assert all(any(c.choice.description == "UNKNOWN" for c in s.candidates) for s in steps)
        assert "novelty is unknown" in steps[2].candidates[0].choice.description
        assert "not established" in steps[1].candidates[0].choice.description
        assert "cause is not established" in steps[3].candidates[0].choice.description
        position = replace(last.snapshot.position, x=last.snapshot.position.x + 1)
        for bad_first, bad_last in (
            (replace(first, session_id="foreign"), last),
            (first, replace(last, session_id="foreign")),
            (first, replace(last, snapshot=replace(last.snapshot, position=position))),
        ):
            with pytest.raises(C1OwnerReviewHold):
                prepare_stage27hi_multi_review(
                    loop, step, **{**common, "first_action_probe": bad_first,
                                   "last_settled_probe": bad_last})
    _fixture(tmp_path, scenario)


def test_source_admission_tracks_settled_native_progress(tmp_path):
    import json

    import pytest

    from relay_self.c_lane_l1_evaluation_engine_dev import build_evaluation_steps
    from relay_self.c_lane_stage27g_original_owner_review_dev import C1OwnerReviewHold
    from test_p0d_stage27c_place_move_wal_issuer_dev import ScriptedPlaceNative
    from test_p0d_stage27h_bounded_l0_move_dev import _issue, _start

    class MotionNative(ScriptedPlaceNative):
        async def send_set_control(self, action_id, *, control, state):
            await super().send_set_control(action_id, control=control, state=state)
            self.x += self.delta - 0.8

    async def scenario(f, lane, server, delta, expected):
        pre, handoff, former, first, loop = await _start(f, lane)
        native = MotionNative(handoff.native_session_id)
        native.delta = delta
        assert loop.pre_action(first, now_ns=150).status == "L0_CONTINUE_MOVE"
        receipt = await _issue(f, pre, handoff, loop, former, first, native)
        step = loop.observe_terminal_action(
            receipt, source_probe=first,
            now_ns=loop.start_ns + loop.invocation.budget.max_duration_ms * 1_000_000,
        )
        args = dict(physical=f.physical, lane=lane, bridge=f.bridge,
                    first_action_probe=first, last_settled_probe=receipt.settled_probe,
                    world_id=f.lifecycle.world.world_id)
        if delta == 0:
            assert receipt.journal_status == "NATIVE_PLACE_MOVE_NO_PROGRESS"
            with pytest.raises(C1OwnerReviewHold):
                prepare_stage27hi_multi_review(loop, step, **args)
            return
        frame = prepare_stage27hi_multi_review(loop, step, **args)
        facts = json.loads(frame.request.context[0].value_json)
        assert facts["original_action_ids"] == [receipt.action_id]
        assert facts["executed_actions"][0]["status"] == "NATIVE_PLACE_MOVE_SETTLED"
        steps = build_evaluation_steps(frame)
        assert expected in steps[0].candidates[0].choice.description
        assert steps[0].candidates[0].evidence_refs
        assert "Skill success is not established" in steps[1].candidates[0].choice.description
        assert "novelty is unknown" in steps[2].candidates[0].choice.description
        assert loop.owner.retained.memories == ()

    for index, (delta, expected) in enumerate((
        (0.2, "decreased"), (0.0, "did not change"), (-0.2, "increased"),
    )):
        case_root = tmp_path / str(index)
        case_root.mkdir()
        _fixture(case_root,
                 lambda f, lane, server: scenario(f, lane, server, delta, expected))


def test_source_admission_equal_gap_and_vertical_mismatch(tmp_path):
    import json
    import math
    from dataclasses import replace

    import pytest

    from relay_self.c_lane_l1_evaluation_engine_dev import build_evaluation_steps
    from test_p0d_stage27c_place_move_wal_issuer_dev import ScriptedPlaceNative
    from test_p0d_stage27h_bounded_l0_move_dev import _issue, _start

    class DisplacedNative(ScriptedPlaceNative):
        async def send_set_control(self, action_id, *, control, state):
            await super().send_set_control(action_id, control=control, state=state)
            self.x -= 0.6

        async def send_observe(self, request_id):
            await super().send_observe(request_id)
            probe = self.events[-1]
            position = probe.snapshot.position
            position = replace(position, y=position.y + self.dy, z=position.z + self.dz)
            self.events[-1] = replace(probe, snapshot=replace(probe.snapshot, position=position))

    async def scenario(f, lane, server, vertical):
        pre, handoff, former, first, loop = await _start(f, lane)
        native = DisplacedNative(handoff.native_session_id)
        anchor = loop.invocation.target.contract.anchor
        distance = anchor.x - first.snapshot.position.x
        native.dy = 1.5 if vertical else 0.0
        native.dz = 0.0 if vertical else math.sqrt(0.4 * distance - 0.04)
        assert loop.pre_action(first, now_ns=150).status == "L0_CONTINUE_MOVE"
        receipt = await _issue(f, pre, handoff, loop, former, first, native)
        assert receipt.journal_status == "NATIVE_PLACE_MOVE_SETTLED"
        step = loop.observe_terminal_action(
            receipt, source_probe=first,
            now_ns=loop.start_ns + loop.invocation.budget.max_duration_ms * 1_000_000,
        )
        frame = prepare_stage27hi_multi_review(
            loop, step, physical=f.physical, lane=lane, bridge=f.bridge,
            first_action_probe=first, last_settled_probe=receipt.settled_probe,
            world_id=f.lifecycle.world.world_id,
        )
        facts = json.loads(frame.request.context[0].value_json)
        choices = build_evaluation_steps(frame)
        assert receipt.displacement_m >= 0.1
        if vertical:
            assert facts["target_status"] == "VERTICAL_MISMATCH"
            assert facts["target_gap_m"] is None
            assert "comparison unavailable" in choices[0].candidates[0].choice.description
        else:
            assert facts["target_gap_m"] == pytest.approx(facts["initial_target_gap_m"])
            assert "did not change" in choices[0].candidates[0].choice.description
        assert "novelty is unknown" in choices[2].candidates[0].choice.description
        assert "success is not established" in choices[1].candidates[0].choice.description
        assert "cause is not established" in choices[3].candidates[0].choice.description

    for vertical in (False, True):
        case_root = tmp_path / str(vertical)
        case_root.mkdir()
        _fixture(case_root, lambda f, lane, server: scenario(f, lane, server, vertical))


def test_missing_target_contract_holds_before_action_admission(tmp_path):
    from dataclasses import replace

    import pytest

    from relay_self.p0d_stage27h_bounded_l0_move_dev import (
        Stage27hBoundedMoveLoop,
        Stage27hLoopRefusal,
    )
    from test_p0d_stage27h_bounded_l0_move_dev import _start

    async def scenario(f, lane, server):
        pre, handoff, _, _, loop = await _start(f, lane)
        option = pre.round.frame.options[0]
        invocation = replace(option.invocation, target=replace(option.invocation.target,
                                                               contract=None))
        option = replace(option, invocation=invocation, arrival_contract=None)
        frame = replace(pre.round.frame, options=(option,))
        missing_target = replace(pre, round=replace(pre.round, frame=frame))
        wal = loop.owner.files.physical_wal_file.read_bytes()
        with pytest.raises(Stage27hLoopRefusal, match="Preset/Target required"):
            Stage27hBoundedMoveLoop(missing_target, handoff, owner=loop.owner,
                                    physical=f.physical, world_epoch=pre.world_epoch,
                                    start_ns=100)
        assert loop.owner.files.physical_wal_file.read_bytes() == wal
        assert loop.action_count == 0
    _fixture(tmp_path, scenario)


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


def test_new_current_alone_cannot_requalify_old_settled_run(tmp_path):
    import pytest

    from relay_self.c_lane_l1_evaluation_engine_dev import EvaluationSourceStale
    from test_p0d_stage27g_real_l1_evaluation_dev import _new_probe

    async def scenario(f, lane, server):
        loop, step, first, actions, _ = await _run_multi(f, lane, server)
        last = actions[-1].settled_probe
        common = dict(physical=f.physical, lane=lane, bridge=f.bridge,
                      first_action_probe=first, last_settled_probe=last)
        frame = prepare_stage27hi_multi_review(loop, step, world_id=frame_world(f), **common)
        fresh = _new_probe(actions[-1])
        loop.owner.observe_world_tick(session_id=fresh.session_id, world_tick=(
            fresh.snapshot.time.day * 24000 + fresh.snapshot.time.time_of_day))
        loop.owner.accept_rejoined_worldbody(fresh, request_id=fresh.request_id)
        with pytest.raises(EvaluationSourceStale) as failure:
            await execute_evaluation(frame, loop, task_id="new-current-old-run", **common)
        assert failure.value.evaluation_audit.receipts == ()
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

    def descriptions(before, after, reached=False, after_status="OUTSIDE"):
        facts = {"original_action_ids": ["a"], "initial_target_gap_m": before,
                 "initial_target_status": "OUTSIDE", "target_status": after_status,
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
    assert "comparison unavailable" in descriptions(3, 1, after_status="TOO_CLOSE")[0]


def test_failure_positions_preserve_only_completed_axes(tmp_path, monkeypatch):
    import pytest

    from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane

    original = ResidentLlamaInferenceLane.await_result

    async def scenario(f, lane, server):
        loop, step, first, actions, _ = await _run_multi(f, lane, server)
        last = actions[-1].settled_probe
        loop.owner.observe_world_tick(session_id=last.session_id, world_tick=(
            last.snapshot.time.day * 24000 + last.snapshot.time.time_of_day))
        loop.owner.accept_rejoined_worldbody(last, request_id=last.request_id)
        common = dict(physical=f.physical, lane=lane, bridge=f.bridge,
                      first_action_probe=first, last_settled_probe=last)
        frame = prepare_stage27hi_multi_review(loop, step, world_id=frame_world(f), **common)
        original_wal = loop.owner.files.physical_wal_file.read_bytes()
        skills, intents, retained = (dict(loop.owner.skills), loop.owner.intent.events,
                                     loop.owner.retained)
        server.choice_id = "1"
        for fail_at in (1, 3, 5):
            count = 0

            async def fail(self, ticket, **kwargs):
                nonlocal count
                count += 1
                if count == fail_at:
                    await original(self, ticket, **kwargs)
                    raise RuntimeError("synthetic inference resource loss")
                return await original(self, ticket, **kwargs)

            monkeypatch.setattr(ResidentLlamaInferenceLane, "await_result", fail)
            with pytest.raises(RuntimeError, match="resource loss") as exc:
                await execute_evaluation(frame, loop, task_id=f"failure-{fail_at}", **common)
            audit = exc.value.evaluation_audit
            assert audit.status == "INTERRUPTED"
            assert len(audit.axes) == len(audit.receipts) == fail_at - 1
            assert loop.owner.skills == skills and loop.owner.intent.events == intents
            assert loop.owner.retained == retained and len(loop._seen_action_ids) == 3
            assert loop.owner.files.physical_wal_file.read_bytes() == original_wal
    _fixture(tmp_path, scenario)


def frame_world(f):
    return f.lifecycle.world.world_id


def test_scope_and_http_tampering_interrupt_evaluation(tmp_path, monkeypatch):
    from dataclasses import replace
    from pathlib import Path

    import pytest

    from adapters.llama_cpp.relay_engine import LlamaCppProviderError
    from relay_self.c_lane_stage27g_original_owner_review_dev import C1OwnerReviewHold
    from relay_self.relay_engine import CognitionMode
    from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane

    original_await = ResidentLlamaInferenceLane.await_result
    original_submit = ResidentLlamaInferenceLane.submit

    async def scenario(f, lane, server):
        loop, step, first, actions, _ = await _run_multi(f, lane, server)
        last = actions[-1].settled_probe
        loop.owner.observe_world_tick(session_id=last.session_id, world_tick=(
            last.snapshot.time.day * 24000 + last.snapshot.time.time_of_day))
        loop.owner.accept_rejoined_worldbody(last, request_id=last.request_id)
        common = dict(physical=f.physical, lane=lane, bridge=f.bridge,
                      first_action_probe=first, last_settled_probe=last)
        frame = prepare_stage27hi_multi_review(loop, step, world_id=frame_world(f), **common)
        wal = loop.owner.files.physical_wal_file.read_bytes()
        skills, intents, retained = (dict(loop.owner.skills), loop.owner.intent.events,
                                     loop.owner.retained)
        other = f.owners[f.names[1]]
        other_state = (dict(other.skills), other.intent.events, other.retained)
        server.choice_id = "2"
        foreign_request = replace(frame.request, request_id="foreign-self-work")
        foreign_ticket = original_submit(lane, other.self_id, work_ref="foreign-self-work",
                                         request=foreign_request, mode=CognitionMode.BOUNDED)
        foreign_result = await original_await(lane, foreign_ticket)
        server.choice_id = "1"
        for case in ("session", "epoch", "current-final", "foreign", "foreign-result",
                     "request", "response", "old-response"):
            count = 0
            first_ref = None
            submitted = []

            def submit(self, *args, **kwargs):
                nonlocal count, first_ref
                ticket = original_submit(self, *args, **kwargs)
                submitted.append(ticket)
                count += 1
                if count == 1:
                    first_ref = ticket.request_id
                if count == 3 and case == "foreign":
                    return foreign_ticket
                return ticket

            async def altered(self, ticket, **kwargs):
                result = await original_await(self, ticket, **kwargs)
                if case == "current-final" and count == 5:
                    loop.owner.current_worldbody_observation = replace(last, seq=last.seq + 1)
                if count == 3:
                    if case == "foreign-result":
                        return foreign_result
                    if case == "session":
                        loop.owner.native_session_id = "foreign-session"
                    elif case == "epoch":
                        object.__setattr__(f.lifecycle.world, "epoch", frame.world_epoch + 1)
                    elif case in ("request", "response", "old-response"):
                        ref = first_ref if case == "old-response" else ticket.request_id
                        raw = self.provider.stage26_raw_receipt(ref)
                        path = raw.request_path if case == "request" else raw.response_path
                        Path(path).write_bytes(b"tampered")
                return result

            monkeypatch.setattr(ResidentLlamaInferenceLane, "submit", submit)
            monkeypatch.setattr(ResidentLlamaInferenceLane, "await_result", altered)
            with pytest.raises((C1OwnerReviewHold, LlamaCppProviderError)) as exc:
                await execute_evaluation(frame, loop, task_id=f"adversary-{case}", **common)
            audit = exc.value.evaluation_audit
            if case == "foreign":
                await original_await(lane, submitted[-1])
            assert len(audit.axes) == (5 if case == "old-response" else
                                       4 if case == "current-final" else 2)
            assert len(audit.receipts) == (5 if case in ("old-response", "current-final") else
                                           3 if case in ("session", "epoch") else 2)
            if case == "current-final":
                loop.owner.current_worldbody_observation = last
            if case == "session":
                loop.owner.native_session_id = frame.native_session_id
            if case == "epoch":
                object.__setattr__(f.lifecycle.world, "epoch", frame.world_epoch)
            assert loop.owner.skills == skills and loop.owner.intent.events == intents
            assert loop.owner.retained == retained and len(loop._seen_action_ids) == 3
            assert (dict(other.skills), other.intent.events, other.retained) == other_state
            assert loop.owner.files.physical_wal_file.read_bytes() == wal
    _fixture(tmp_path, scenario)


def test_candidate_options_remain_bounded_by_observed_motion_and_sources():
    import json
    from types import SimpleNamespace

    from relay_self.c_lane_l1_evaluation_engine_dev import build_evaluation_steps

    for movement, before, after in ((0, 2, 1), (1, 2, 1), (1, None, 1)):
        facts = {"original_action_ids": ["a"], "initial_target_gap_m": before,
                 "initial_target_status": "OUTSIDE", "target_status": "OUTSIDE",
                 "target_gap_m": after, "executed_actions": [{"displacement_m": movement}]}
        frame = SimpleNamespace(
            request=SimpleNamespace(context=[SimpleNamespace(value_json=json.dumps(facts))]),
            wal_digest="a" * 64, native_session_id="session", last_probe_seq=2,
            target_contract_ref="target", terminal_status="budget", action_ids=("a",),
            completion_review_offered=False,
        )
        steps = build_evaluation_steps(frame)
        assert all(any(c.choice.description == "UNKNOWN" and not c.evidence_refs
                       for c in step.candidates) for step in steps)
        skill = [c.choice.description for c in steps[1].candidates]
        assert ("No movement was measured" in skill[2]) == (movement == 0)
        assert (len(skill) == 4) == (movement > 0 and before is not None and after < before)
        assert "success is not established" in skill[0]
        assert "novelty is unknown" in steps[2].candidates[0].choice.description
        assert "cause is not established" in steps[3].candidates[0].choice.description
        assert all(c.evidence_refs for step in steps for c in step.candidates
                   if c.choice.description != "UNKNOWN")


def test_provider_inference_error_preserves_completed_receipts(tmp_path, monkeypatch):
    import pytest

    from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider

    original = LlamaCppRelayProvider.__call__

    async def scenario(f, lane, server):
        loop, step, first, actions, _ = await _run_multi(f, lane, server)
        last = actions[-1].settled_probe
        loop.owner.observe_world_tick(session_id=last.session_id, world_tick=(
            last.snapshot.time.day * 24000 + last.snapshot.time.time_of_day))
        loop.owner.accept_rejoined_worldbody(last, request_id=last.request_id)
        common = dict(physical=f.physical, lane=lane, bridge=f.bridge,
                      first_action_probe=first, last_settled_probe=last)
        frame = prepare_stage27hi_multi_review(loop, step, world_id=frame_world(f), **common)
        wal = loop.owner.files.physical_wal_file.read_bytes()
        skills, intent, retained = dict(loop.owner.skills), loop.owner.intent.events, loop.owner.retained
        count = 0

        def failed_provider(self, request, **kwargs):
            nonlocal count
            count += 1
            if count == 3:
                raise RuntimeError("injected provider inference error")
            return original(self, request, **kwargs)

        monkeypatch.setattr(LlamaCppRelayProvider, "__call__", failed_provider)
        server.choice_id = "1"
        with pytest.raises(RuntimeError, match="injected provider") as exc:
            await execute_evaluation(frame, loop, task_id="provider-failure", **common)
        assert len(exc.value.evaluation_audit.axes) == 2
        assert len(exc.value.evaluation_audit.receipts) == 2
        assert loop.owner.skills == skills and loop.owner.intent.events == intent
        assert loop.owner.retained == retained and len(loop._seen_action_ids) == 3
        assert loop.owner.files.physical_wal_file.read_bytes() == wal
    _fixture(tmp_path, scenario)


def test_session_and_epoch_change_while_third_provider_call_is_running(tmp_path, monkeypatch):
    import asyncio
    import threading

    import pytest

    from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
    from relay_self.c_lane_stage27g_original_owner_review_dev import C1OwnerReviewHold
    from relay_self.resident_llama_inference_lane_dev import (
        ResidentGpuLaneError,
        ResidentLlamaInferenceLane,
    )

    provider_call = LlamaCppRelayProvider.__call__
    await_call = ResidentLlamaInferenceLane.await_result

    async def scenario(f, lane, server):
        loop, step, first, actions, _ = await _run_multi(f, lane, server)
        last = actions[-1].settled_probe
        loop.owner.observe_world_tick(session_id=last.session_id, world_tick=(
            last.snapshot.time.day * 24000 + last.snapshot.time.time_of_day))
        loop.owner.accept_rejoined_worldbody(last, request_id=last.request_id)
        common = dict(physical=f.physical, lane=lane, bridge=f.bridge,
                      first_action_probe=first, last_settled_probe=last)
        frame = prepare_stage27hi_multi_review(loop, step, world_id=frame_world(f), **common)
        wal = loop.owner.files.physical_wal_file.read_bytes()
        before = (dict(loop.owner.skills), loop.owner.intent.events, loop.owner.retained)
        server.choice_id = "1"
        for changed in ("session", "epoch"):
            entered, release = threading.Event(), threading.Event()
            calls = 0
            waits = 0

            def blocked_provider(self, request, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 3:
                    entered.set()
                    if not release.wait(10):
                        raise RuntimeError("test did not release provider")
                return provider_call(self, request, **kwargs)

            async def change_in_flight(self, ticket, **kwargs):
                nonlocal waits
                waits += 1
                if waits == 3:
                    assert await asyncio.to_thread(entered.wait, 10)
                    try:
                        if changed == "session":
                            loop.owner.native_session_id = "new-session"
                        else:
                            object.__setattr__(f.lifecycle.world, "epoch", frame.world_epoch + 1)
                    finally:
                        release.set()
                return await await_call(self, ticket, **kwargs)

            monkeypatch.setattr(LlamaCppRelayProvider, "__call__", blocked_provider)
            monkeypatch.setattr(ResidentLlamaInferenceLane, "await_result", change_in_flight)
            with pytest.raises((C1OwnerReviewHold, ResidentGpuLaneError)) as exc:
                await execute_evaluation(frame, loop, task_id=f"inflight-{changed}", **common)
            assert len(exc.value.evaluation_audit.axes) == 2
            assert len(exc.value.evaluation_audit.receipts) >= 2
            loop.owner.native_session_id = frame.native_session_id
            object.__setattr__(f.lifecycle.world, "epoch", frame.world_epoch)
            assert (dict(loop.owner.skills), loop.owner.intent.events, loop.owner.retained) == before
            assert loop.owner.files.physical_wal_file.read_bytes() == wal
            assert len(loop._seen_action_ids) == 3
    _fixture(tmp_path, scenario)
