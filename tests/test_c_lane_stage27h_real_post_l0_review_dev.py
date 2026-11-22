"""C Lane: actual original Stage27h runner opt-in, synthetic DEV sources only.

Runs 3 existing Stage27h original physical issuer/WAL rows then the REAL
post-L0 *function* against one shared resident scripted HTTP slot and a
synthetic native stdout JSONL source. No actual Paper/Gemma/real Self grant.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from experiments.c_lane_stage27h_real_post_l0_review_dev import (
    CStage27RealReadOnlyHold,
    capture_stage27h_real_post_l0_readonly_review,
)
from experiments.p0d_stage27_real_place_move_dev import (
    Stage27RealWorldRefusal,
    run_stage27_real_world,
    stage27h_real_a_motor_hook,
    stage27i_real_a_motor_hook,
)
from relay_self.c_lane_stage27g_original_owner_review_dev import C1OwnerReviewHold
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.skill import SkillState
from test_c_lane_stage27hi_multi_action_review_dev import _issue, _run_multi, _start
from test_p0d_stage27g_real_l1_evaluation_dev import _new_probe
from test_p0d_stage27h_bounded_l0_move_dev import SlowPlaceNative, _fixture


def _setup(stdout: Path, probe):
    event = {
        "type": "observation", "kind": "probe",
        "session_id": probe.session_id,
        "seq": probe.seq, "request_id": probe.request_id,
    }
    stdout.write_bytes((json.dumps(event, sort_keys=True) + "\n").encode())


def test_real_review_entry_accepts_one_settled_budget_stop(tmp_path):
    async def scenario(f, lane, server):
        pre, handoff, former, observed, loop = await _start(f, lane)
        native = SlowPlaceNative(handoff.native_session_id)
        assert loop.pre_action(observed, now_ns=150).status == "L0_CONTINUE_MOVE"
        receipt = await _issue(f, pre, handoff, loop, former, observed, native)
        step = loop.observe_terminal_action(
            receipt, source_probe=observed,
            now_ns=loop.start_ns + loop.invocation.budget.max_duration_ms * 1_000_000,
        )
        assert step.status == "L0_BUDGET_EXHAUSTED_YIELD_EVALUATION"
        post = _new_probe(receipt)
        stdout = tmp_path / "native.jsonl"
        _setup(stdout, post)
        server.choice_id = "2"
        result = await capture_stage27h_real_post_l0_readonly_review(
            loop=loop, step=step, first_action_probe=observed,
            last_settled_probe=receipt.settled_probe, physical=f.physical,
            lane=lane, bridge=f.bridge, evidence=tmp_path,
            world_uuid=f.lifecycle.world.world_id, original_native_stdout=stdout,
            fresh_probe=lambda: asyncio.sleep(0, result=post),
        )
        assert result["original_model_choice_number"] == "2"
        assert not result["review_completion_selected"]
        assert not result["c1_memory_written"]
        assert loop.owner.skills[handoff.skill_execution_id].state is SkillState.STARTED
        before = json.loads((tmp_path / "c-stage27h-before-post-l0-l1.json").read_text())
        assert before["action_count"] == 1
        assert before["settling_observations_reserved"] == 0
    _fixture(tmp_path, scenario)


def test_original_stage27h_live_hook_optin_performs_only_readonly_l1(tmp_path):
    async def scenario(f, lane, server):
        loop, step, first, receipts, initial_calls = await _run_multi(f, lane, server)
        a, b = loop.owner, f.owners[f.names[1]]
        before_a = (a.retained, a.intent.events, dict(a.skills))
        before_b = (b.retained, b.intent.events, dict(b.skills))
        original_journal = PhysicalActionJournal.restore(
            a.files.physical_wal_file, self_id=a.self_id,
        )
        original_actions = tuple(original_journal.records)
        post = _new_probe(receipts[-1])
        stdout = tmp_path / "synthetic-post-l0-owned-native.jsonl"
        _setup(stdout, post)
        server.choice_id = "2"

        async def native_post_model():
            assert (tmp_path / "c-stage27h-before-post-l0-l1.json").is_file()
            frozen = json.loads(
                (tmp_path / "c-stage27h-before-post-l0-l1.json").read_text()
            )
            assert frozen["original_skill_state"] == "started"
            assert frozen["canonical_action_ids"] == [
                r["action_id"] for r in original_actions
            ]
            assert frozen["model_request_issued"] is False
            assert len(server.calls) == initial_calls + 1
            assert lane.require_world_idle().n_slots == 1
            return post

        result = await capture_stage27h_real_post_l0_readonly_review(
            loop=loop, step=step,
            first_action_probe=first,
            last_settled_probe=receipts[-1].settled_probe,
            physical=f.physical, lane=lane, bridge=f.bridge,
            evidence=tmp_path, world_uuid=f.lifecycle.world.world_id,
            original_native_stdout=stdout, fresh_probe=native_post_model,
        )
        assert result["classification"] == "REAL_STAGE27H_C_LANE_L1_REVIEW_READONLY_DEV"
        assert result["original_model_choice_number"] == "2"
        assert result["review_completion_selected"]
        assert result["native_stdout_readback"]["source_readback"] == (
            "EXACT_ONCE_NATIVE_STDOUT_DEV"
        )
        assert result["native_stdout_readback"]["independent_model_vs_native_wallclock_causality"] is False
        assert result["frozen_review"]["readback"] is True
        assert result["original_action_ids"] == [
            r["action_id"] for r in original_actions
        ]
        assert result["original_wal_sha256"] == original_journal.digest
        assert not result["original_skill_terminalized"]
        assert not result["c1_memory_written"]
        assert not result["goal_succeeded"]
        assert not result["action_issue_authorized"]
        assert not result["separate_self_approval_supplied"]
        assert a.skills[loop.handoff.skill_execution_id].state is SkillState.STARTED
        assert a.retained.memories == ()
        assert (a.retained, a.intent.events, dict(a.skills)) == before_a
        assert (b.retained, b.intent.events, dict(b.skills)) == before_b
        assert a.current_worldbody_observation == post
        assert a.last_observed_tick == (
            post.snapshot.time.day * 24000 + post.snapshot.time.time_of_day
        )
        assert PhysicalActionJournal.restore(
            a.files.physical_wal_file, self_id=a.self_id,
        ).digest == original_journal.digest
        assert not f.physical.active_action_ids
        assert not result["actual_paper_vs_model_wallclock_causality_attested"]
        assert json.loads(
            (tmp_path / "c-stage27h-post-l0-l1-witness.json").read_text()
        )["original_model_http_response_sha256"] == (
            result["original_model_http_response_sha256"]
        )
        with pytest.raises(CStage27RealReadOnlyHold, match="freeze"):
            await capture_stage27h_real_post_l0_readonly_review(
                loop=loop, step=step,
                first_action_probe=first,
                last_settled_probe=receipts[-1].settled_probe,
                physical=f.physical, lane=lane, bridge=f.bridge,
                evidence=tmp_path, world_uuid=f.lifecycle.world.world_id,
                original_native_stdout=stdout, fresh_probe=native_post_model,
            )  # read-only sidecar may never be silently overwritten/replayed.
    _fixture(tmp_path, scenario)


@pytest.mark.parametrize("fault", [
    "foreign-world", "foreign-branch", "foreign-native",
    "missing-original-stdout", "stale-first", "skill-already-terminal",
    "wrong-last-l0", "foreign-peer-world",
])
def test_source_gate_rejects_nonmatching_real_runner_context_before_model(
    tmp_path, fault,
):
    async def scenario(f, lane, server):
        loop, step, first, receipts, initial_calls = await _run_multi(f, lane, server)
        stdout = tmp_path / "synthetic-post-l0-owned-native.jsonl"
        post = _new_probe(receipts[-1])
        _setup(stdout, post)
        opts = dict(
            loop=loop, step=step,
            first_action_probe=first,
            last_settled_probe=receipts[-1].settled_probe,
            physical=f.physical, lane=lane, bridge=f.bridge,
            evidence=tmp_path, world_uuid=f.lifecycle.world.world_id,
            original_native_stdout=stdout,
            fresh_probe=lambda: asyncio.sleep(0, result=post),
        )
        if fault == "foreign-world":
            opts["world_uuid"] = "forged-unrelated-world"
        elif fault == "foreign-branch":
            f.bridge.paper.branch_id = "foreign"
        elif fault == "foreign-native":
            opts["last_settled_probe"] = replace(
                opts["last_settled_probe"], session_id="foreign-native",
            )
        elif fault == "missing-original-stdout":
            opts["original_native_stdout"] = tmp_path / "absent.jsonl"
        elif fault == "stale-first":
            opts["first_action_probe"] = replace(
                first, seq=first.seq + 1,
            )
        elif fault == "skill-already-terminal":
            skill = loop.owner.skills[loop.handoff.skill_execution_id]
            loop.owner.skills[skill.execution_id] = skill.succeed(
                reason="synthetic precondition fault",
                at_ns=skill.events[-1].at_ns+1,
                provenance=skill.events[-1].provenance,
            )
        elif fault == "wrong-last-l0":
            opts["step"] = replace(step, status="L0_CONTINUE_MOVE")
        elif fault == "foreign-peer-world":
            opts["bridge"] = object()
        with pytest.raises((
            CStage27RealReadOnlyHold, C1OwnerReviewHold,
            AttributeError, ValueError,
        )):
            await capture_stage27h_real_post_l0_readonly_review(**opts)
        assert len(server.calls) == initial_calls
        assert not (tmp_path / "c-stage27h-post-l0-l1-witness.json").exists()
    _fixture(tmp_path, scenario)


@pytest.mark.parametrize("fault", ["native-record-missing", "foreign-request"])
def test_native_stdout_original_readback_failure_does_not_adopt_success(
    tmp_path, fault,
):
    async def scenario(f, lane, server):
        loop, step, first, receipts, initial_calls = await _run_multi(f, lane, server)
        a = loop.owner
        before_mem = a.retained.memories
        post = _new_probe(receipts[-1])
        stdout = tmp_path / "synthetic-post-l0-owned-native.jsonl"
        _setup(stdout, post)
        if fault == "native-record-missing":
            stdout.write_bytes(b"")
        else:
            stdout.write_bytes(b'{"type":"observation","kind":"probe","session_id":"foreign"}\n')
        server.choice_id = "2"
        with pytest.raises(Stage27RealWorldRefusal):
            await capture_stage27h_real_post_l0_readonly_review(
                loop=loop, step=step, first_action_probe=first,
                last_settled_probe=receipts[-1].settled_probe,
                physical=f.physical, lane=lane, bridge=f.bridge,
                evidence=tmp_path, world_uuid=f.lifecycle.world.world_id,
                original_native_stdout=stdout,
                fresh_probe=lambda: asyncio.sleep(0, result=post),
            )
        assert len(server.calls) == initial_calls + 1
        assert (tmp_path / "c-stage27h-before-post-l0-l1.json").is_file()
        assert not (tmp_path / "c-stage27h-post-l0-l1-witness.json").exists()
        assert a.skills[loop.handoff.skill_execution_id].state is SkillState.STARTED
        assert a.retained.memories == before_mem
    _fixture(tmp_path, scenario)


def test_cli_optin_is_single_stage27h_mode_and_stage27i_unchanged(tmp_path):
    kwargs = dict(
        paper_jar=tmp_path / "paper.jar",
        paper_sha256="0" * 64,
        plugin_jar=tmp_path / "plugin.jar",
        plugin_sha256="0" * 64,
        scratch_parent=tmp_path,
        accepted_eula=True,
        real_world_dev_grant=True,
        gemma_l1_endpoint="http://127.0.0.1:18081/v1/chat/completions",
        gemma_l1_model="stage26-gemma",
    )
    with patch(
        "experiments.p0d_stage27_real_place_move_dev."
        "run_real_two_self_preset_checkpoint",
        new_callable=AsyncMock,
    ) as original:
        original.return_value = tmp_path / "no-world-started.json"
        for flags in (
            dict(c_lane_stage27h_post_review=True),
            dict(stage27i_precision_gait=True, c_lane_stage27h_post_review=True),
            dict(stage27h_l0_move_loop=True, stage27i_precision_gait=True),
        ):
            with pytest.raises(Stage27RealWorldRefusal):
                asyncio.run(run_stage27_real_world(**kwargs, **flags))
            original.assert_not_awaited()
        assert asyncio.run(run_stage27_real_world(
            **kwargs, stage27h_l0_move_loop=True,
            c_lane_stage27h_post_review=True,
        )) == tmp_path / "no-world-started.json"
        new_hook = original.await_args.kwargs["_stage27_motor_hook"]
        assert new_hook is not stage27h_real_a_motor_hook
        assert new_hook is not stage27i_real_a_motor_hook
        original.reset_mock()
        asyncio.run(run_stage27_real_world(
            **kwargs, stage27h_l0_move_loop=True,
        ))
        assert original.await_args.kwargs["_stage27_motor_hook"] is stage27h_real_a_motor_hook
        original.reset_mock()
        asyncio.run(run_stage27_real_world(
            **kwargs, stage27i_precision_gait=True,
        ))
        assert original.await_args.kwargs["_stage27_motor_hook"] is stage27i_real_a_motor_hook
