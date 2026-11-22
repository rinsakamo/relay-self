"""C Lane original Stage27g review: OWNED synthetic HTTP/native tests.

Uses Stage27's original resident Self/Action/WAL and its scripted provider,
NOT actual Gemma, native children, Paper, real source causal qualification
or autonomous second-stage Self approval.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from relay_self.c_lane_stage27g_original_owner_review_dev import (
    C1OwnerReviewHold,
    OriginalSelfC1Approval,
    accept_original_stage27g_c1_review,
    prepare_original_stage27g_c1_review,
)
from relay_self.p0d_stage27f_l1_evaluation_dev import prepare_stage27f_outcome_evaluation
from relay_self.p0d_stage27g_real_l1_evaluation_dev import (
    finish_stage27g_original_evaluation,
    submit_stage27g_original_evaluation,
)
from relay_self.persistent_cognition import (
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance
from relay_self.self_owner_checkpoint_dev import (
    SelfOwnerCut,
    load_self_owner_cut,
    save_self_owner_cut,
)
from relay_self.skill import SkillState
from test_p0d_real_preset_checkpoint_dev import native_probe
from test_p0d_stage27f_l1_evaluation_dev import _run_original
from test_p0d_stage27g_real_l1_evaluation_dev import _new_probe, _run_case

P = Provenance("c-lane-l1-review-synthetic", "explicit-not-autonomous-self-choice")


async def _review(f, lane, server, *, mode="moved", number="2", stale_post=False):
    pre, handoff, l0, receipt = await _run_original(f, lane, mode=mode)
    a = f.owners[f.names[0]]
    frame = prepare_stage27f_outcome_evaluation(
        pre, handoff, l0, receipt, owner=a,
        physical=f.physical, world_epoch=pre.world_epoch,
    )
    server.choice_id = number
    ticket = submit_stage27g_original_evaluation(
        frame, pre, owner=a, physical=f.physical, lane=lane,
    )
    post = _new_probe(receipt, distant=stale_post)
    choice, witness = await finish_stage27g_original_evaluation(
        frame, pre, owner=a, physical=f.physical, lane=lane,
        ticket=ticket, fresh_probe=lambda: asyncio.sleep(0, result=post),
    )
    a.observe_world_tick(
        session_id=post.session_id,
        world_tick=post.snapshot.time.day * 24000 + post.snapshot.time.time_of_day,
    )
    a.accept_rejoined_worldbody(post, request_id=post.request_id)
    # Stage27's bare ResidentFixture does not create cognition.json before
    # running; seed the existing original file as Stage25 real cut would do.
    save_persistent_cognition(a.files.cognition_file, a.retained)
    wal = PhysicalActionJournal.restore(a.files.physical_wal_file, self_id=a.self_id)
    first = wal.records[0]
    before = native_probe(
        f.names[0], first["probe_seq"], session=pre.native_session,
        request_id=first["probe_request_id"],
    )
    return dict(
        owner=a, physical=f.physical, lane=lane, ticket=ticket,
        prepared=pre, frame=frame, choice=choice, witness=witness,
        post_model_probe=post, world_id="synthetic-stage27-world",
    ), before, receipt.settled_probe


def _approve(prepared):
    return OriginalSelfC1Approval(
        self_id=prepared["owner"].self_id,
        native_session_id=prepared["frame"].native_session_id,
        evaluation_request_id=prepared["frame"].request.request_id,
        skill_execution_id=prepared["frame"].skill_execution_id,
        explicit_self_decision="ACCEPT_SKILL_SUCCESS_AND_RETAIN_C1",
        provenance=P,
    )


def test_original_l1_review_is_not_success_until_separate_self_acceptance(tmp_path):
    async def scenario(f, lane, server):
        inputs, before, settled = await _review(f, lane, server)
        a, b = f.owners[f.names[0]], f.owners[f.names[1]]
        prior_b = (b.retained, b.intent.events, dict(b.skills))
        wal = PhysicalActionJournal.restore(a.files.physical_wal_file, self_id=a.self_id)
        proposal = prepare_original_stage27g_c1_review(**inputs)
        assert proposal is not None
        assert not proposal.terminal_skill_accepted
        assert not proposal.memory_retained
        assert proposal.outcome_candidate == "C1_SKILL_SUCCESS_REVIEW_ONLY"
        assert a.skills[proposal.skill_execution_id].state is SkillState.STARTED
        assert a.retained.memories == ()
        assert a.intent.current_intent is not None
        assert inputs["choice"].selected_number == "2"

        # No implicit acceptance from number 2: explicit Self approval is
        # a separate externally sourced input. This test chooses it synthetically.
        approval = _approve(inputs)
        end_ns = max(
            a.skills[proposal.skill_execution_id].events[-1].at_ns,
            a.supervisor.get(proposal.action_id).events[-1].at_ns,
        ) + 100
        args = dict(
            proposal=proposal, approval=approval, before_probe=before,
            settled_probe=settled, at_ns=end_ns, **inputs,
        )
        receipt = accept_original_stage27g_c1_review(**args)
        assert receipt.recorded_original_owner_memory
        assert not receipt.actual_world_causality_attested
        assert not receipt.autonomous_self_approval_attested
        assert not receipt.goal_succeeded
        assert not receipt.physical_action_replayed
        assert a.skills[proposal.skill_execution_id].state is SkillState.SUCCEEDED
        assert len(a.retained.memories) == 1
        assert receipt.memory_id == a.retained.memories[0].memory_id
        assert load_persistent_cognition(a.files.cognition_file) == a.retained
        assert a.intent.current_intent is not None
        assert (b.retained, b.intent.events, dict(b.skills)) == prior_b
        # Same original owner is now ready for a typed Stage28 handoff.
        # This is NOT itself a complete World+A/B COMMITTED generation.
        typed = SelfOwnerCut(
            generation_id="g-000000000001", self_id=a.self_id,
            world_id="synthetic-stage27-world", branch_id="source",
            former_native_session_id=a.native_session_id,
            last_observed_world_tick=a.last_observed_tick,
            intent_events=a.intent.events,
            skill_executions=tuple(a.skills.values()),
            pattern_registry=a.pattern_registry,
        )
        source = a.files.self_root / "owner-state.json"
        save_self_owner_cut(source, typed)
        assert load_self_owner_cut(source) == typed
        assert typed.skill_executions[0].state is SkillState.SUCCEEDED
        assert a.retained.memories[0].memory_id == receipt.memory_id
        assert PhysicalActionJournal.restore(
            a.files.physical_wal_file, self_id=a.self_id,
        ).digest == wal.digest
        with pytest.raises(C1OwnerReviewHold):
            accept_original_stage27g_c1_review(**args)  # replay not allowed
    _run_case(tmp_path, scenario)


@pytest.mark.parametrize("fault", [
    "missing-approval", "foreign-self", "wrong-session",
    "model-http-digest", "stale-probe", "different-choice",
    "changed-original-wal", "no-completion-target",
    "unadopted-observation", "inactive-owner",
])
def test_no_terminal_skill_or_memory_when_review_source_fails(
    tmp_path, fault,
):
    async def scenario(f, lane, server):
        inputs, before, settled = await _review(
            f, lane, server,
            number="1" if fault == "different-choice" else "2",
            stale_post=fault == "no-completion-target",
        )
        a = inputs["owner"]
        approval = _approve(inputs)
        if fault == "model-http-digest":
            inputs["witness"] = replace(
                inputs["witness"], raw_http_response_sha256="f" * 64,
            )
        if fault == "stale-probe":
            inputs["post_model_probe"] = replace(
                inputs["post_model_probe"],
                seq=inputs["post_model_probe"].seq + 1,
            )
        if fault == "unadopted-observation":
            a.current_worldbody_observation = None
        if fault == "inactive-owner":
            lane.cognitive_work.fence_self(a.self_id)
        if fault == "changed-original-wal":
            a.files.physical_wal_file.write_bytes(b"corrupted wal")
        try:
            proposal = prepare_original_stage27g_c1_review(**inputs)
        except Exception:
            proposal = None
        if proposal is not None:
            if fault == "foreign-self":
                approval = replace(approval, self_id="B")
            elif fault == "wrong-session":
                approval = replace(approval, native_session_id="stale-session")
            elif fault == "missing-approval":
                approval = replace(approval, explicit_self_decision="DEFER")
            with pytest.raises(C1OwnerReviewHold):
                accept_original_stage27g_c1_review(
                    proposal=proposal, approval=approval,
                    before_probe=before, settled_probe=settled,
                    at_ns=100000000000, **inputs,
                )
        else:
            assert fault not in {
                "missing-approval", "foreign-self", "wrong-session",
            }
        assert a.skills[inputs["frame"].skill_execution_id].state is SkillState.STARTED
        assert not a.retained.memories
    _run_case(tmp_path, scenario)


def test_original_owner_rejects_direct_unreviewed_skill_terminalization(
    tmp_path,
):
    async def scenario(f, lane, server):
        inputs, _before, _settled = await _review(f, lane, server)
        a = inputs["owner"]
        from relay_self.checkpointed_cognitive_runtime_dev import (
            LiveCognitionCheckpointError,
        )
        with pytest.raises(LiveCognitionCheckpointError):
            a.finish_reviewed_skill(
                inputs["frame"].skill_execution_id,
                outcome=SkillState.STARTED,
                reason="not terminal", at_ns=10000, provenance=P,
            )
        assert a.skills[inputs["frame"].skill_execution_id].state is SkillState.STARTED
    _run_case(tmp_path, scenario)
