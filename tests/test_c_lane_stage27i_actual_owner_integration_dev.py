"""C Lane x original Stage27h/i: real Python owner/journal/interpreter, synthetic native.

This is an OFFLINE test using Stage27's own scripted physical bridge. It does
not read any actual Paper World files, run Gemma or qualify physical causality.
"""
from __future__ import annotations

from dataclasses import replace

from relay_self.c_lane_stage27_source_bridge import assemble_stage27_c1_from_canonical_wal
from relay_self.cognitive_learning_contract import (
    CurrentCue,
    OutcomeAssessment,
    RetainedRevisionRead,
)
from relay_self.cognitive_learning_owner_adapter import (
    c3_shadow_l1_context,
    propose_existing_memory,
)
from relay_self.common_io import ScopeRef
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoice
from relay_self.skill import SkillState
from relay_self.three_self_present import EpistemicStatus
from test_cognitive_learning_owner_adapter import _c3_candidate
from test_p0d_stage27h_bounded_l0_move_dev import (
    SlowPlaceNative,
    _fixture,
    _issue,
    _start,
)

P = Provenance("c-lane-integration-test", "owner-selected-training")


def test_stage27_original_issuer_wal_to_c1_and_next_epoch_shadow(tmp_path):
    """Use actual Stage27 action/journal/owner code, never a mock WAL reader."""

    async def scenario(f, lane, server):
        pre, handoff, previous, observed, loop = await _start(f, lane)
        owner = f.owners[f.names[0]]
        peer = f.owners[f.names[1]]
        before = observed
        peer_before = (peer.intent.events, peer.retained.memories)
        native = SlowPlaceNative(handoff.native_session_id)
        receipts = []
        for idx in range(4):
            gate = loop.pre_action(observed, now_ns=150 + idx * 1000)
            if gate.status != "L0_CONTINUE_MOVE":
                break
            receipt = await _issue(
                f, pre, handoff, loop, previous, observed, native,
            )
            receipts.append(receipt)
            step = loop.observe_terminal_action(
                receipt, source_probe=observed, now_ns=200 + idx * 1000,
            )
            previous = receipt.settled_probe
            if step.status != "L0_CONTINUE_MOVE":
                break
            observed = replace(
                previous, seq=previous.seq + 1,
                request_id=f"c-lane-next-probe-{idx}",
            )
        assert len(receipts) == 3
        assert step.status == "L0_TARGET_REACHED_YIELD_EVALUATION"
        assert owner.skills[handoff.skill_execution_id].state is SkillState.STARTED
        journal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        child_actions = tuple(
            owner.supervisor.get(row["action_id"]) for row in journal.records
        )
        request = dict(
            cognition=owner.retained, intent=owner.intent,
            skill=owner.skills[handoff.skill_execution_id],
            actions=child_actions,
            journal_path=owner.files.physical_wal_file,
            original_wal_sha256=journal.digest,
            selected_invocation=pre.round.frame.options[0].invocation,
            before_probe=before, after_probe=receipts[-1].settled_probe,
            world_id="synthetic-not-paper-uuid",
            world_epoch=pre.world_epoch,
            selected_provenance=P,
        )
        # Real Stage27 intentionally leaves Skill ACTIVE pending evaluation.
        assert assemble_stage27_c1_from_canonical_wal(**request) is None
        # Synthetic, EXPLICIT original owner adoption of terminal Skill. A
        # physical geometry result alone MUST NOT perform this transition.
        previous_skill = owner.skills[handoff.skill_execution_id]
        last_action_ns = max(
            a.events[-1].at_ns for a in child_actions
        )
        terminal = previous_skill.succeed(
            reason="synthetic explicit Self L1 terminal evaluation",
            at_ns=max(last_action_ns + 1, previous_skill.events[-1].at_ns),
            provenance=P,
        )
        owner.skills[handoff.skill_execution_id] = terminal
        exp = assemble_stage27_c1_from_canonical_wal(
            **(request | {"skill": terminal}),
        )
        assert exp is not None
        assert len(exp.action_ids) == 3
        assert exp.target_outcome is OutcomeAssessment.SUCCESS
        assert exp.memory_id == assemble_stage27_c1_from_canonical_wal(
            **(request | {"skill": terminal}),
        ).memory_id
        assert exp.goal_ref == "EXPLORE_WORLD"
        assert exp.intent_id == handoff.intent_id
        assert owner.intent.current_intent is not None

        # A no retained C1 yields no C3 context.
        candidate = _c3_candidate(exp)
        retained_c2 = RetainedRevisionRead(
            proposal_ref="c2-p1", semantic_owner_ref="original-memory-owner",
            previous_revision=4, committed_revision=5, accepted=True,
            provenance=P,
        )
        cues = (CurrentCue(
            scope=ScopeRef(owner.self_id, owner.native_session_id),
            key="surface", value="stone",
            status=EpistemicStatus.OBSERVED,
            source_revision_refs=("new-synthetic-epoch",),
            provenance=(P,),
        ),)
        choices = (BoundedChoice("1", "existing MOVE"), BoundedChoice("2", "DEFER"))
        c3 = dict(
            candidate=candidate, retained=retained_c2,
            current_scope=cues[0].scope,
            current_source_revision_refs=("new-synthetic-epoch",),
            cues=cues, choice_set=choices, current_owner_revision=5,
            viability_confirmed=True, cost_budget_ns=20,
        )
        assert c3_shadow_l1_context(owner.retained, **c3) == (choices, None)
        memory = propose_existing_memory(
            owner.retained, exp, integration_provenance=P,
        )
        assert memory is not None
        # Only the actual existing owner, by explicit simulated Self choice,
        # may do the write; C Lane itself never mutates the retained store.
        owner.retain_memory(memory)
        assert propose_existing_memory(
            owner.retained, exp, integration_provenance=P,
        ) is None
        unchanged, datum = c3_shadow_l1_context(owner.retained, **c3)
        assert unchanged == choices
        assert datum is not None and "L1_RETAINED_REUSE" in datum.value_json
        assert (peer.intent.events, peer.retained.memories) == peer_before
        assert not journal.unresolved
        assert PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        ).digest == journal.digest
        assert len(server.calls) >= 1  # original simulated model path
    _fixture(tmp_path, scenario)
