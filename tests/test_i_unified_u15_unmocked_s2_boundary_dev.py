"""U15: unmocked original I4a S2 history verifier and WAL reservation.

CPU fixtures still synthesize S1 WAL and typed Owner anchors. The actual
production verify_i4a_s2_empty_run_boundary and
verify_live_wal_history_anchor functions are NEVER stubbed in these tests.
This is not independent Native/Paper producer authentication or real L1.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from relay_self.i_lane_i4a_live_wal_anchor_dev import (
    LiveWalHistoryAnchor,
)
from relay_self.i_lane_i4a_s2_run_boundary_dev import (
    I4AS2RunBoundaryHold,
    verify_i4a_s2_empty_run_boundary,
)
from relay_self.intent import IntentCommitment
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueFenceError
from relay_self.skill import SkillExecution
from test_i_unified_i4a_place_lease_dev import P
from test_i_unified_u14_s2_original_wal_positive_dev import (
    _case,
    _reserve,
)


def _unmocked_case(tmp_path, monkeypatch):
    # U14's helper synthesizes canonical old S1 and a new proposed S2.
    # Its monkeypatch is deliberately scoped to a context that is already
    # EXITED before these tests invoke the original production verifier.
    with monkeypatch.context() as helper_patch:
        parts = _case(tmp_path, helper_patch)
    bridge, owner, gate, journal, _, boundary, lane, _, proposal, current = parts[:10]
    lane.cognitive_work = bridge.cognitive_work
    scope = bridge.cognitive_work.current_scope(owner.self_id)
    old = journal.records[0]
    old_intent = IntentCommitment()
    old_intent.commit(
        old["intent_id"], objective="EXPLORE_WORLD",
        at_ns=1, provenance=P,
    )
    old_skill = SkillExecution.start(
        old["skill_execution_id"], skill_id="MOVE",
        intent_commitment=old_intent, at_ns=2, provenance=P,
    )
    owner.skills[old_skill.execution_id] = old_skill.cancel(
        reason="explicit synthetic S1 terminal", at_ns=3, provenance=P,
    )
    anchor = LiveWalHistoryAnchor(
        owner.self_id, owner.native_session_id, scope[2],
        old["intent_id"], old["skill_execution_id"],
        (old["action_id"],), journal.digest, len(journal.records),
    )
    owner._i4a_live_wal_anchor = anchor
    owner.current_worldbody_observation = current
    for field, value in (
        ("anchor", anchor),
        ("world_epoch", scope[2]),
        ("memory_snapshot", owner.retained),
        ("registry_snapshot", owner.pattern_registry),
        ("intent_events_snapshot", owner.intent.events),
        ("skills_snapshot", tuple(sorted(owner.skills.items()))),
    ):
        object.__setattr__(boundary, field, value)
    owner._i4a_s2_empty_run_boundary = boundary
    assert not journal.unresolved
    return parts


def test_unmocked_original_s2_history_verifier_allows_one_cpu_prepared(
    tmp_path, monkeypatch,
):
    parts = _unmocked_case(tmp_path, monkeypatch)
    bridge, owner, gate, journal, old_bytes, boundary, lane = parts[:7]
    # Neither the S1-anchor verifier nor the S2 empty-run verifier is
    # monkeypatched; they read the actual original Owner and disk WAL.
    verify_i4a_s2_empty_run_boundary(
        boundary, physical=gate, lane=lane,
    )
    _reserve(parts)
    original = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id=owner.self_id,
    )
    assert len(original.records) == 2
    assert original.records[0]["status"] == "NATIVE_PLACE_MOVE_SETTLED"
    assert original.records[1]["status"] == "PREPARED_UNRESOLVED"
    assert original.unresolved
    assert gate.active_action_ids == ()
    assert journal.path.read_bytes() != old_bytes


@pytest.mark.parametrize("mutation", [
    "anchor", "owner_probe", "prior_skill", "current_skill",
    "prefix_sha", "prefix_action_id", "old_intent",
])
def test_unmocked_original_s2_verifier_denies_stale_source_before_issue(
    tmp_path, monkeypatch, mutation,
):
    parts = _unmocked_case(tmp_path, monkeypatch)
    bridge, owner, gate, journal, old_bytes, boundary, lane = parts[:7]
    if mutation == "anchor":
        owner._i4a_live_wal_anchor = replace(
            boundary.anchor, wal_sha256="0" * 64,
        )
    elif mutation == "owner_probe":
        owner.current_worldbody_observation = replace(
            owner.current_worldbody_observation,
            request_id="wrong-current-probe",
        )
    elif mutation == "prior_skill":
        owner.skills[boundary.old_skill_id] = SkillExecution.start(
            boundary.old_skill_id, skill_id="MOVE",
            intent_commitment=owner.intent, at_ns=1, provenance=P,
        )
    elif mutation == "current_skill":
        owner.skills[boundary.new_skill_id] = owner.skills[
            boundary.new_skill_id
        ].cancel(reason="expired", at_ns=200004, provenance=P)
    elif mutation == "prefix_sha":
        object.__setattr__(boundary, "prefix_digest", "0" * 64)
    elif mutation == "prefix_action_id":
        object.__setattr__(boundary, "prefix_action_ids", ("old-forged",))
    elif mutation == "old_intent":
        object.__setattr__(boundary, "old_intent_id", "foreign-old")
    with pytest.raises((I4AS2RunBoundaryHold, PhysicalIssueFenceError)):
        _reserve(parts)
    assert journal.path.read_bytes() == old_bytes
    assert not journal.unresolved
    assert gate.active_action_ids == ()
    assert "new-S2-place" not in {
        a.action_id for a in owner.supervisor.recorded_actions
    }
