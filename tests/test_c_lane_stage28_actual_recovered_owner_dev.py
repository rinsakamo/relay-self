"""C Lane + exact Stage28c2b restored A/B Owner: synthetic fork, no real Paper.

No Stage27 source code is imported by this test: the C1 historical episode is
an explicitly synthetic readout, not authenticated as a real physical Action.
Stage28's *actual* typed restore, native/Paper clock split, and Memory Owner
must remain in charge. L1 options remain immutable; no actual Gemma request.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from relay_self.action import ActionState
from relay_self.c_lane_stage27_source_bridge import propose_for_stage28_original_owner
from relay_self.cognitive_learning_contract import (
    Comparison,
    ConditionalReuseCandidate,
    CurrentCue,
    EvidenceOrigin,
    GuardCondition,
    OutcomeAssessment,
    RetainedRevisionRead,
    RevisionTarget,
    UnderstandingProposal,
)
from relay_self.cognitive_learning_owner_adapter import (
    BoundedSkillExperience,
    C1AdmissionError,
    WorldBodyRead,
    c3_shadow_l1_context,
)
from relay_self.common_io import Clock, ClockStamp, ScopeRef
from relay_self.persistent_cognition import (
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoice
from relay_self.three_self_present import EpistemicStatus, Lens
from test_p0d_resident_move_issuer_dev import _probe
from test_stage28c2b_native_paper_dual_clock_dev import _clock_context, _link


P = Provenance("synthetic-historical-c1", "NOT_REAL_WORLD_EVIDENCE")


def _historical_synthetic_c1() -> BoundedSkillExperience:
    """Typed historical datum, not a claim about actual Stage27 evidence."""
    old = ScopeRef("A", "native-retired-A")
    first = WorldBodyRead(
        scope=old, world_id="world-1", epoch=0,
        source_seq=10, clock=ClockStamp(Clock.WORLD_TICK, 100),
        source_refs=(P,), origin=EvidenceOrigin.WORLD_BODY_OBSERVED,
    )
    later = replace(
        first, source_seq=11, clock=ClockStamp(Clock.WORLD_TICK, 104),
    )
    return BoundedSkillExperience(
        scope=old, world_id="world-1", epoch_start=0, epoch_end=0,
        goal_ref="EXPLORE_WORLD", intent_id="old-intent-A",
        skill_execution_id="old-bounded-skill-A", skill_id="MOVE",
        target_ref="old-target", preset_ref="old-preset",
        before=first, after=later, prediction_ref=None,
        action_ids=("synthetic-child-action-A",),
        action_states=(ActionState.OUTCOME,),
        target_outcome=OutcomeAssessment.UNKNOWN, evidence_refs=(P,),
    )


def _candidate(exp):
    understanding = UnderstandingProposal(
        proposal_ref="synthetic-c2", episode_key=exp.episode_key,
        episode_revision=0, target_lens=Lens.SELF_BODY,
        target_kind=RevisionTarget.APPLICABILITY,
        semantic_owner_ref="owner-A", expected_owner_revision=4,
        candidate_ref="choice-1", comparison=Comparison.NO_PREDICTION,
        applicable_condition_refs=("synthetic-cue",),
        counterexample_refs=(), provenance=P,
    )
    candidate = ConditionalReuseCandidate(
        proposal=understanding, candidate_ref="choice-1",
        guard=(GuardCondition("visible-surface", "stone"),),
        rollback_ref="rollback-1", expected_l1_cost_ns=10, provenance=P,
    )
    return candidate


def test_stage28_exact_recovered_owner_accepts_c1_only_after_rejoin_and_self_choice(
    tmp_path, monkeypatch,
):
    copy, paper, world, boot, bridge = _clock_context(
        tmp_path, monkeypatch, native_time=123,
    )
    owner = bridge.owners["A"]
    peer = bridge.owners["B"]
    exp = _historical_synthetic_c1()
    assert owner.retained.identity.self_id == "A"
    assert peer.retained.identity.self_id == "B"
    peer_original = peer.retained
    original = owner.retained
    # No new native WorldBody admitted => the read-only C proposal HOLDS.
    proto = _probe("new-session-A", 12, "request-A", 123, 4.5)
    with pytest.raises(C1AdmissionError, match="unqualified"):
        propose_for_stage28_original_owner(
            exp, recovered_owner=owner, verified_world_id="world-1",
            new_native_probe=proto, integration_provenance=P,
        )
    updated, links = _link(copy, paper, boot, bridge, monkeypatch)
    assert updated.world_tick != owner.last_observed_tick  # Paper vs native clock
    assert len(links) == 2
    assert all(not link.physical_action_issue_authorized for link in links)
    owner.accept_rejoined_worldbody(proto, request_id="request-A")
    assert owner.current_worldbody_observation is proto
    proposed = propose_for_stage28_original_owner(
        exp, recovered_owner=owner, verified_world_id="world-1",
        new_native_probe=proto, integration_provenance=P,
    )
    assert proposed is not None
    assert owner.retained is original  # C readout never writes
    assert peer.retained is peer_original

    fixed = (BoundedChoice("1", "pre-bound MOVE"), BoundedChoice("2", "DEFER"))
    candidate = _candidate(exp)
    current = CurrentCue(
        scope=ScopeRef("A", "new-session-A"), key="visible-surface",
        value="stone", status=EpistemicStatus.OBSERVED,
        source_revision_refs=("new-original-epoch",),
        provenance=(proto.provenance,),
    )
    retained_c2 = RetainedRevisionRead(
        proposal_ref="synthetic-c2", semantic_owner_ref="owner-A",
        previous_revision=4, committed_revision=5, accepted=True, provenance=P,
    )
    context = dict(
        candidate=candidate, retained=retained_c2, current_scope=current.scope,
        current_source_revision_refs=("new-original-epoch",),
        cues=(current,), choice_set=fixed, current_owner_revision=5,
        viability_confirmed=True, cost_budget_ns=20,
    )
    # Condition A: same *one Self* without C1 Memory; no context.
    assert c3_shadow_l1_context(owner.retained, **context) == (fixed, None)
    # Simulated Self Owner explicitly chooses to adopt the proposal.
    owner.retain_memory(proposed)
    assert owner.retained is not original
    # Condition B: same current native cues and pre-bound choices, C1 retained.
    unchanged, hint = c3_shadow_l1_context(owner.retained, **context)
    assert unchanged == fixed and hint is not None
    assert "L1_RETAINED_REUSE" in hint.value_json
    # No second retained entry from duplicate historical C1.
    assert propose_for_stage28_original_owner(
        exp, recovered_owner=owner, verified_world_id="world-1",
        new_native_probe=proto, integration_provenance=P,
    ) is None
    path = tmp_path / "c-lane-retained-snapshot.json"
    save_persistent_cognition(path, owner.retained)
    recovered = load_persistent_cognition(path)
    assert recovered.memories == owner.retained.memories
    assert c3_shadow_l1_context(recovered, **context) == (fixed, hint)
    assert peer.retained is peer_original
    assert all(not x.physical_action_issue_authorized for x in links)


@pytest.mark.parametrize("fault", [
    "foreign-self", "world-mismatch", "new-native-session",
    "old-native-session", "fresh-required", "missing-probe",
])
def test_stage28_fresh_original_owner_rejects_false_c1_transfer(
    tmp_path, monkeypatch, fault,
):
    copy, paper, _world, boot, bridge = _clock_context(
        tmp_path, monkeypatch, native_time=123,
    )
    _link(copy, paper, boot, bridge, monkeypatch)
    owner = bridge.owners["A"]
    probe = _probe("new-session-A", 12, "request-A", 123, 4.5)
    owner.accept_rejoined_worldbody(probe, request_id="request-A")
    old = _historical_synthetic_c1()
    world_id = "world-1"
    if fault == "foreign-self":
        owner = bridge.owners["B"]
    elif fault == "world-mismatch":
        world_id = "other-world"
    elif fault == "new-native-session":
        probe = _probe("foreign-session", 12, "request-A", 123, 4.5)
    elif fault == "old-native-session":
        probe = _probe("native-retired-A", 12, "request-A", 123, 4.5)
    elif fault == "fresh-required":
        owner.fresh_native_observation_required = True
    elif fault == "missing-probe":
        owner.current_worldbody_observation = None
    with pytest.raises(C1AdmissionError, match="unqualified"):
        propose_for_stage28_original_owner(
            old, recovered_owner=owner, verified_world_id=world_id,
            new_native_probe=probe, integration_provenance=P,
        )
