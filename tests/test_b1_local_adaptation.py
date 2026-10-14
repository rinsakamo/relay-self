"""B1 native-shaped source, retention, and cheap comparator controls (no World)."""
import json
from dataclasses import replace

import pytest

import test_feature_s46_eat as s46
from adapters.mineflayer.b0_ground_foraging import GroundTarget
from adapters.mineflayer.b1_local_adaptation import (
    B1LocalCandidate,
    B1LocalRejected,
)
from adapters.mineflayer.python_protocol import MineflayerPosition
from adapters.mineflayer.seek_execution import SeekConsequence, SeekConsequenceKind


def source():
    before = s46.case()
    pos = before.snapshot.position
    target = GroundTarget(
        before.session_id, before.seq, before.request_id, 70,
        MineflayerPosition(pos.x + 2.5, pos.y, pos.z), before.provenance,
    )
    effect = SeekConsequence(
        "b1-action-0", before.session_id, before.seq, before.seq + 4,
        0.0, 2.5, SeekConsequenceKind.BLOCKED,
        before.seq + 1, before.seq + 2, before.seq + 3,
    )
    after = replace(before, seq=before.seq + 5, request_id="b1-after-blocked")
    return before, effect, after, target


def test_retained_blocked_observation_is_only_l1_candidate():
    before, effect, after, target = source()
    l1 = B1LocalCandidate(before.session_id)
    l1.record_blocked(before, effect, after, target)
    assert len(l1.cognition.memories) == 1
    evidence = json.loads(l1.cognition.memories[0].content)
    assert evidence["action_id"] == effect.action_id
    assert evidence["effect_kind"] == "BLOCKED"
    assert evidence["correlated_followup_seq"] == after.seq
    next_probe = replace(after, seq=after.seq + 1, request_id="fresh-next")
    lateral = l1.next_waypoint(next_probe, target)
    assert lateral.goal_id == "b1-local-lateral"
    assert lateral.target.z < after.snapshot.position.z
    assert l1.evidence()["reused_for_lateral_choice"] == 1
    assert l1.evidence()["habit_created"] is False
    l1.record_alternative_outcome(replace(
        effect, action_id="b1-action-1", kind=SeekConsequenceKind.PROGRESSED,
    ))
    assert l1.evidence()["alternative_progressed"] == 1


def test_retention_off_has_no_memory_and_fixed_cheap_turn():
    before, effect, after, target = source()
    l1 = B1LocalCandidate(before.session_id, retain=False)
    l1.record_blocked(before, effect, after, target)
    probe = replace(after, seq=after.seq + 1, request_id="next")
    result = l1.next_waypoint(probe, target)
    assert result.target.z > after.snapshot.position.z
    assert len(l1.cognition.memories) == 0
    assert l1.evidence()["learning_qualified"] is False
    assert l1.evidence()["fixed_off_policy"] == "PLUS_Z_AFTER_BLOCKED"


def test_nonblocked_and_stale_cannot_become_l1_memory():
    before, effect, after, target = source()
    state = B1LocalCandidate(before.session_id)
    with pytest.raises(B1LocalRejected):
        state.record_blocked(
            before, replace(effect, kind=SeekConsequenceKind.PROGRESSED),
            after, target,
        )
    assert not state.cognition.memories
    state.record_blocked(before, effect, after, target)
    with pytest.raises(B1LocalRejected, match="stale"):
        state.next_waypoint(after, target)
    with pytest.raises(B1LocalRejected, match="foreign"):
        state.next_waypoint(
            replace(after, seq=after.seq + 1, request_id="next"),
            replace(target, entity_id=71),
        )
    with pytest.raises(B1LocalRejected):
        state.record_blocked(before, effect, after, target)


def test_foreign_session_and_bad_original_seq_cannot_retain():
    before, effect, after, target = source()
    for bad in (
        replace(effect, session_id="foreign"),
        replace(effect, before_seq=before.seq + 1),
        replace(effect, after_seq=after.seq),
    ):
        state = B1LocalCandidate(before.session_id)
        with pytest.raises(B1LocalRejected):
            state.record_blocked(before, bad, after, target)
        assert state.evidence()["retained_observations"] == 0


def test_corrupted_retained_observation_cannot_be_used_as_choice():
    before, effect, after, target = source()
    l1 = B1LocalCandidate(before.session_id)
    l1.record_blocked(before, effect, after, target)
    memory = l1.cognition.memories[0]
    tampered = json.loads(memory.content)
    tampered["session_id"] = "foreign-session"
    l1.cognition = replace(l1.cognition, memories=(
        replace(memory, content=json.dumps(tampered)),
    ))
    fresh = replace(after, seq=after.seq + 1, request_id="fresh")
    with pytest.raises(B1LocalRejected, match="retained"):
        l1.next_waypoint(fresh, target)
    assert l1.evidence()["reused_for_lateral_choice"] == 0
