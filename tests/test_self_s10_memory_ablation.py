"""S10 source-shaped A/B Memory intervention engineering negative controls.

All observations are deterministic fixtures. No WSL2, Minecraft, model,
second user permission, original S9 byte readback or S10 Action.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_postmain_s42_world_contrast as s42
from adapters.mineflayer.normal_action import NormalWorldL0
from adapters.mineflayer.self_s3_experience import S3ReadOnlyExperience
from adapters.mineflayer.self_s10_memory_ablation import (
    S10AblationRejected,
    compare_shadow_ab,
)
from relay_self.experience_bridge import ExperienceRejected, ReuseStatus
from test_self_s3_experience import fixture


def _arms():
    receipt, previous = fixture()
    sid = previous.session_id
    retained = S3ReadOnlyExperience(sid)
    withheld = S3ReadOnlyExperience(sid)
    original = retained.observe_original(
        receipt, correlated_probe=previous,
        expected_action_id=receipt.terminal.action_id,
    )
    base, _, _, original_event, _ = s42._pair()
    event = replace(original_event, seq=5, session_id=sid)
    reading = replace(previous, seq=6, request_id="s10-shadow-next-source")
    a = NormalWorldL0(sid, "escape-threat", base, max_events=2,
                      max_action_requests=1)
    b = NormalWorldL0(sid, "escape-threat", base, max_events=2,
                      max_action_requests=1)
    return {
        "event": event, "probe": reading,
        "memory_present": retained, "memory_withheld": withheld,
        "l0_present": a, "l0_withheld": b,
    }, original


def test_same_source_memory_present_vs_withheld_does_not_change_l0_action():
    arms, original = _arms()
    verdict = compare_shadow_ab(**arms)
    assert verdict.session_id == original.session_id
    assert verdict.retained_memory_count == 1
    assert verdict.present_hint == ReuseStatus.RECALL.value
    assert verdict.withheld_hint != ReuseStatus.RECALL.value
    assert verdict.present_selection == verdict.withheld_selection == "MOVE_AWAY"
    assert verdict.cheap_baseline == "L1_EXISTING_FULL_SCAN"
    assert verdict.disposition == "RECALL_DIFFERENCE_NO_L0_DECISION_EFFECT"
    assert not verdict.physical_runs and not verdict.issued_actions
    assert not verdict.memory_caused_physical_action
    assert not verdict.goal_attested and not verdict.scientific_go
    assert verdict.learning_updates == verdict.habit_grants == 0
    assert arms["l0_present"].events == arms["l0_withheld"].events == 0
    assert arms["l0_present"].action_requests == arms["l0_withheld"].action_requests == 0
    assert len(arms["memory_present"].snapshot.memories) == 1
    assert len(arms["memory_withheld"].snapshot.memories) == 0


@pytest.mark.parametrize("defect", [
    "foreign_event", "foreign_probe", "stale_probe",
    "truncated_event", "truncated_probe",
    "missing_retained", "unmatched_l0", "single_arm",
    "previously_decided", "crossed_source",
])
def test_s10_rejects_unmatched_or_unqualified_ab(defect):
    arms, _ = _arms()
    if defect == "foreign_event":
        arms["event"] = replace(arms["event"], session_id="foreign")
    elif defect == "foreign_probe":
        arms["probe"] = replace(arms["probe"], session_id="foreign")
    elif defect == "stale_probe":
        arms["probe"] = replace(arms["probe"], seq=3)
    elif defect in ("truncated_event", "truncated_probe"):
        # A physical source's truncated registration cannot be used for
        # matching. Use a valid protocol-level truncated fact tuple (cap).
        key = "event" if defect == "truncated_event" else "probe"
        message = arms[key]
        fact = message.snapshot.nearby_entities[0]
        cap = message.snapshot.nearby_entities_coverage.max_entities
        snapshot = replace(
            message.snapshot,
            nearby_entities=tuple(replace(fact, entity_id=1000 + i)
                                  for i in range(cap)),
            nearby_entities_coverage=replace(
                message.snapshot.nearby_entities_coverage,
                candidate_count=cap + 1, truncated=True,
            ),
        )
        arms[key] = replace(message, snapshot=snapshot)
    elif defect == "missing_retained":
        arms["memory_present"] = S3ReadOnlyExperience(arms["event"].session_id)
    elif defect == "unmatched_l0":
        arms["l0_withheld"].intent_id = "different-intent"
    elif defect == "single_arm":
        arms["l0_withheld"] = arms["l0_present"]
    elif defect == "previously_decided":
        arms["l0_present"].events = 1
    elif defect == "crossed_source":
        arms["memory_withheld"] = S3ReadOnlyExperience("foreign")
    with pytest.raises((S10AblationRejected, ExperienceRejected)):
        compare_shadow_ab(**arms)


def test_s10_cannot_turn_stale_recall_into_behavioral_effect():
    arms, _ = _arms()
    arms["probe"] = replace(arms["probe"], seq=99, request_id="s10-late-probe")
    with pytest.raises(S10AblationRejected, match="recall contrast"):
        compare_shadow_ab(**arms)


def test_s10_memory_content_is_not_an_action_grant():
    arms, _ = _arms()
    result = compare_shadow_ab(**arms)
    assert not hasattr(result, "action_id")
    assert not hasattr(result, "authorization")
    assert not hasattr(result, "issued_action")
    assert arms["memory_present"].hint_for_next(
        arms["probe"]
    ).observed_action_refs == ("MOVE_BACKWARD",)
