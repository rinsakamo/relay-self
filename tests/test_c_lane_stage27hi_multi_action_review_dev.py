"""C Lane Stage27h/i multi-child review: source-shaped SYNTHETIC DEV only.

The original Stage27h CPU loop and 3 native issuer receipts/Action supervisor/
fsynced canonical WAL execute. The only LLM is the original resident
single-slot provider backed by the test's synthetic HTTP server.
Explicit Self approval is synthetic, never autonomous or real-World evidence.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from relay_self.c_lane_stage27g_original_owner_review_dev import (
    C1OwnerReviewHold,
    OriginalSelfC1Approval,
)
from relay_self.c_lane_stage27hi_multi_action_review_dev import (
    accept_stage27hi_original_c1,
    finish_stage27hi_multi_review,
    prepare_stage27hi_multi_review,
    submit_stage27hi_multi_review,
)
from relay_self.persistent_cognition import (
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal, PhysicalJournalError
from relay_self.provenance import Provenance
from relay_self.resident_llama_inference_lane_dev import ResidentGpuLaneError
from relay_self.self_owner_checkpoint_dev import (
    SelfOwnerCut,
    load_self_owner_cut,
    save_self_owner_cut,
)
from relay_self.skill import SkillState
from test_p0d_stage27g_real_l1_evaluation_dev import _new_probe
from test_p0d_stage27h_bounded_l0_move_dev import (
    SlowPlaceNative,
    _fixture,
    _issue,
    _start,
)

P = Provenance("c-lane-synthetic-multi-review", "not-autonomous-approval")


async def _run_multi(f, lane, server):
    pre, handoff, former, observed, loop = await _start(f, lane)
    owner = f.owners[f.names[0]]
    original_first = observed
    native = SlowPlaceNative(handoff.native_session_id)
    receipts = []
    step = None
    count_before = len(server.calls)
    for index in range(4):
        gate = loop.pre_action(observed, now_ns=150 + index * 1000)
        assert gate.status == "L0_CONTINUE_MOVE"
        receipt = await _issue(
            f, pre, handoff, loop, former, observed, native,
        )
        receipts.append(receipt)
        step = loop.observe_terminal_action(
            receipt, source_probe=observed, now_ns=200 + index * 1000,
        )
        former = receipt.settled_probe
        if step.status != "L0_CONTINUE_MOVE":
            break
        observed = replace(
            former, seq=former.seq + 1,
            request_id=f"c-lane-after-multi-{index}",
        )
    assert step is not None
    assert step.status == "L0_TARGET_REACHED_YIELD_EVALUATION"
    assert len(receipts) == 3
    assert loop._settlement_reserved == 0
    assert owner.skills[handoff.skill_execution_id].state is SkillState.STARTED
    assert len(server.calls) == count_before
    return loop, step, original_first, receipts, count_before


async def _review_multi(f, lane, server, *, number="2", move_away=False):
    loop, step, first, receipts, calls_before = await _run_multi(f, lane, server)
    owner = loop.owner
    physical = f.physical
    last = receipts[-1].settled_probe
    common = {
        "physical": physical, "lane": lane, "bridge": f.bridge,
        "first_action_probe": first, "last_settled_probe": last,
    }
    save_persistent_cognition(owner.files.cognition_file, owner.retained)
    frame = prepare_stage27hi_multi_review(
        loop, step, world_id=f.lifecycle.world.world_id, **common,
    )
    assert frame.action_ids == tuple(r.action_id for r in receipts)
    assert frame.completion_review_offered
    assert len(frame.request.choices) == 4
    assert frame.request.context[0].key == "original_multi_action_wal_and_target"
    ctx = json.loads(frame.request.context[0].value_json)
    assert ctx["original_action_ids"] == list(frame.action_ids)
    assert not ctx["goal_success_attested"]
    assert not ctx["skill_success_attested"]
    assert not ctx["next_physical_action_authorized"]
    assert owner.skills[frame.skill_execution_id].state is SkillState.STARTED
    assert owner.retained.memories == ()
    server.choice_id = number
    ticket = submit_stage27hi_multi_review(frame, loop, **common)
    assert ticket.action_issue_authorized is False
    fresh = _new_probe(receipts[-1], distant=move_away)
    async def post_model_native():
        assert len(server.calls) == calls_before + 1
        assert lane.require_world_idle().n_slots == 1
        return fresh
    witness, actual_fresh = await finish_stage27hi_multi_review(
        frame, loop, ticket=ticket,
        fresh_probe=post_model_native, **common,
    )
    assert actual_fresh == fresh
    assert witness.original_model_http_request_sha256
    assert witness.original_model_http_response_sha256
    assert witness.choice_number == number
    assert not witness.original_self_approval_attested
    assert not witness.skill_succeeded
    assert not witness.goal_succeeded
    assert not witness.physical_action_issued
    owner.observe_world_tick(
        session_id=fresh.session_id,
        world_tick=(
            fresh.snapshot.time.day * 24000 + fresh.snapshot.time.time_of_day
        ),
    )
    owner.accept_rejoined_worldbody(fresh, request_id=fresh.request_id)
    return loop, witness, first, last, fresh


def _approval(witness):
    frame = witness.frame
    return OriginalSelfC1Approval(
        self_id=frame.self_id, native_session_id=frame.native_session_id,
        evaluation_request_id=frame.request.request_id,
        skill_execution_id=frame.skill_execution_id,
        explicit_self_decision="ACCEPT_SKILL_SUCCESS_AND_RETAIN_C1",
        provenance=P,
    )


def _accept_kwargs(loop, witness, first, last, fresh, f, lane):
    owner = loop.owner
    rows = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id=owner.self_id,
    ).records
    stamp = max(
        owner.skills[witness.frame.skill_execution_id].events[-1].at_ns,
        *(owner.supervisor.get(r["action_id"]).events[-1].at_ns for r in rows),
    )
    return {
        "witness": witness, "approval": _approval(witness),
        "loop": loop, "physical": f.physical, "lane": lane, "bridge": f.bridge,
        "first_action_probe": first, "last_settled_probe": last,
        "post_model_probe": fresh, "at_ns": stamp + 100,
    }


def test_original_three_actions_review_then_separate_self_c1_approval(tmp_path):
    async def scenario(f, lane, server):
        peer = f.owners[f.names[1]]
        loop, witness, first, last, fresh = await _review_multi(f, lane, server)
        # Stage27's original preset restore updates B during _start().
        # Compare B AFTER that baseline, before C-only explicit adoption.
        initial_peer = (peer.retained, peer.intent.events, dict(peer.skills))
        owner = loop.owner
        wal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        assert len(wal.records) == 3
        assert owner.retained.memories == ()  # L1 review alone changes nothing.
        args = _accept_kwargs(loop, witness, first, last, fresh, f, lane)
        receipt = accept_stage27hi_original_c1(**args)
        assert receipt.terminal_skill_in_original_owner
        assert receipt.original_cognition_file_readback
        assert receipt.action_ids == tuple(r["action_id"] for r in wal.records)
        assert receipt.original_wal_sha256 == wal.digest
        assert not receipt.autonomous_approval_attested
        assert not receipt.actual_paper_native_causality_attested
        assert not receipt.parent_goal_completed
        assert not receipt.physical_action_replayed
        assert owner.skills[witness.frame.skill_execution_id].state is SkillState.SUCCEEDED
        assert owner.intent.current_intent is not None
        assert len(owner.retained.memories) == 1
        assert owner.retained.memories[0].memory_id == receipt.memory_id
        assert load_persistent_cognition(owner.files.cognition_file) == owner.retained
        assert (peer.retained, peer.intent.events, dict(peer.skills)) == initial_peer
        assert PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        ).digest == wal.digest
        typed = SelfOwnerCut(
            generation_id="g-000000000001", self_id=owner.self_id,
            world_id=f.lifecycle.world.world_id,
            branch_id=f.lifecycle.world.branch_id,
            former_native_session_id=owner.native_session_id,
            last_observed_world_tick=owner.last_observed_tick,
            intent_events=owner.intent.events,
            skill_executions=tuple(owner.skills.values()),
            pattern_registry=owner.pattern_registry,
        )
        file = owner.files.self_root / "stage28-ready-owner.json"
        save_self_owner_cut(file, typed)
        assert load_self_owner_cut(file) == typed
        assert typed.skill_executions[0].state is SkillState.SUCCEEDED
        with pytest.raises(C1OwnerReviewHold):
            accept_stage27hi_original_c1(**args)
    _fixture(tmp_path, scenario)


@pytest.mark.parametrize("fault", [
    "missing-approval", "foreign-self", "stale-native", "http-hash",
    "wrong-skill", "altered-wal", "fenced-self", "model-defer", "moved-away",
    "wrong-c1-world", "altered-proposal", "response-bytes", "current-changed",
    "gpu-result-fenced",
])
def test_original_multi_action_c1_rejects_foreign_or_stale_sources(
    tmp_path, fault,
):
    async def scenario(f, lane, server):
        loop, witness, first, last, fresh = await _review_multi(
            f, lane, server, number="4" if fault == "model-defer" else "2",
            move_away=fault == "moved-away",
        )
        owner = loop.owner
        args = _accept_kwargs(loop, witness, first, last, fresh, f, lane)
        if fault == "missing-approval":
            args["approval"] = replace(
                args["approval"], explicit_self_decision="DEFER",
            )
        elif fault == "foreign-self":
            args["approval"] = replace(args["approval"], self_id=f.names[1])
        elif fault == "stale-native":
            args["post_model_probe"] = replace(fresh, seq=fresh.seq + 1)
        elif fault == "http-hash":
            args["witness"] = replace(
                witness, original_model_http_response_sha256="f" * 64,
            )
        elif fault == "wrong-skill":
            args["approval"] = replace(
                args["approval"], skill_execution_id="foreign-skill",
            )
        elif fault == "altered-wal":
            owner.files.physical_wal_file.write_bytes(b"broken original WAL")
        elif fault == "fenced-self":
            lane.cognitive_work.fence_self(owner.self_id)
        elif fault == "wrong-c1-world":
            args["witness"] = replace(
                witness, frame=replace(witness.frame, world_id="foreign"),
            )
        elif fault == "altered-proposal":
            args["witness"] = replace(
                witness, frame=replace(
                    witness.frame, action_ids=("forged-action",),
                ),
            )
        elif fault == "response-bytes":
            raw = lane.provider.stage26_raw_receipt(witness.ticket.request_id)
            Path(raw.response_path).write_bytes(b"altered model response")
        elif fault == "current-changed":
            owner.current_worldbody_observation = replace(fresh, seq=fresh.seq + 1)
        elif fault == "gpu-result-fenced":
            lane.fence_self(owner.self_id)
        with pytest.raises((C1OwnerReviewHold, PhysicalJournalError, ResidentGpuLaneError)):
            accept_stage27hi_original_c1(**args)
        assert owner.skills[loop.handoff.skill_execution_id].state is SkillState.STARTED
        assert owner.retained.memories == ()
    _fixture(tmp_path, scenario)


def test_multi_child_review_is_one_new_l1_call_no_physical_extra(tmp_path):
    async def scenario(f, lane, server):
        loop, witness, _first, _last, _fresh = await _review_multi(
            f, lane, server, number="3",
        )
        assert witness.choice_number == "3"
        assert not witness.review_completion_selected
        assert len(loop._seen_action_ids) == 3
        assert not loop.physical.active_action_ids
        assert loop.owner.skills[loop.handoff.skill_execution_id].state is SkillState.STARTED
    _fixture(tmp_path, scenario)


def test_one_settled_action_budget_stop_allows_partial_review_not_success(tmp_path):
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
        common = dict(
            physical=f.physical, lane=lane, bridge=f.bridge,
            first_action_probe=observed, last_settled_probe=receipt.settled_probe,
        )
        frame = prepare_stage27hi_multi_review(
            loop, step, world_id=f.lifecycle.world.world_id, **common,
        )
        assert len(frame.action_ids) == 1
        assert not frame.completion_review_offered
        assert "EVALUATE_PARTIAL" in frame.request.choices[1].description
        server.choice_id = "2"
        ticket = submit_stage27hi_multi_review(frame, loop, **common)

        async def fresh_probe():
            return _new_probe(receipt)

        witness, _ = await finish_stage27hi_multi_review(
            frame, loop, ticket=ticket, fresh_probe=fresh_probe, **common,
        )
        assert witness.choice_number == "2"
        assert not witness.review_completion_selected
        assert loop.owner.retained.memories == ()
        assert loop.owner.skills[handoff.skill_execution_id].state is SkillState.STARTED
    _fixture(tmp_path, scenario)
