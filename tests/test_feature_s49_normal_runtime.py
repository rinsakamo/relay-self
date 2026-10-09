"""S49 source-local Present projection and double-issued Action gate."""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_postmain_s42_world_contrast as s42
from adapters.mineflayer.normal_action import (
    NormalActionAuthorization,
    NormalActionRejected,
    NormalActionStage,
    NormalWorldL0,
)
from adapters.mineflayer.present_projection import (
    InvalidMineflayerPresent,
    project_mineflayer_present,
)
from relay_self.provenance import Provenance


def test_projection_preserves_scope_and_does_not_invent_safety():
    _, near, _, _, _ = s42._pair()
    p = project_mineflayer_present(near.observation)
    assert p.session_id == near.observation.session_id
    assert p.coverage_scope == "mineflayer_entity_registry"
    assert p.coverage_candidates == len(p.observed_entities)
    assert p.provenance == near.observation.provenance
    assert p.observed_entities[0].entity_id == near.entity_id
    assert not hasattr(p, "danger") and not hasattr(p, "safe")
    with pytest.raises(InvalidMineflayerPresent):
        project_mineflayer_present(replace(near.observation, request_id=None))


def test_normal_grants_have_separate_explicit_purpose_and_source():
    grant = NormalActionAuthorization(
        NormalActionStage.PROPOSE, "supervisor:proposal", "escape-threat",
        "session", "action", 2, 3, 9, True,
        Provenance("operator", "propose-1"),
    )
    assert grant.stage is NormalActionStage.PROPOSE
    with pytest.raises(NormalActionRejected):
        replace(grant, provenance=Provenance("mineflayer", "forged"))
    with pytest.raises(NormalActionRejected):
        replace(grant, event_seq=-1)
    with pytest.raises(NormalActionRejected):
        replace(grant, granted="true")


def test_normal_world_l0_tracks_one_zombie_amid_unrelated_minecraft_entities():
    retained, _, far, _, event = s42._pair()
    probe = far.observation
    zombie = probe.snapshot.nearby_entities[0]
    dropped_item = replace(zombie, entity_id=zombie.entity_id + 10, name="item")
    group = (zombie, dropped_item)
    native_snapshot = replace(
        probe.snapshot,
        nearby_entities=group,
        nearby_entities_coverage=replace(
            probe.snapshot.nearby_entities_coverage, candidate_count=2,
        ),
    )
    event = replace(event, snapshot=native_snapshot)
    probe = replace(probe, snapshot=native_snapshot)
    l0 = NormalWorldL0(
        probe.session_id, "escape-threat", retained,
        max_events=2, max_action_requests=1,
    )
    first = l0.decide(event, probe)
    assert first.choice.selection.value == "WAIT"
    assert first.choice.entity_id == zombie.entity_id
    assert not first.asks_for_action

    # Another unsolicited native registry update for the SAME zombie does
    # not provide a fresh decision-bearing target, even with a newer seq.
    repeated = replace(event, seq=probe.seq + 1)
    later_probe = replace(
        probe, seq=probe.seq + 2, request_id="later-same-zombie",
    )
    with pytest.raises(ValueError):
        l0.decide(repeated, later_probe)
    assert l0.events == 1 and l0.action_requests == 0


def test_normal_world_l0_rejects_ambiguous_native_zombie_registry():
    retained, _, far, _, event = s42._pair()
    probe = far.observation
    original = probe.snapshot.nearby_entities[0]
    other_zombie = replace(original, entity_id=original.entity_id + 50)
    snapshot = replace(
        probe.snapshot, nearby_entities=(original, other_zombie),
        nearby_entities_coverage=replace(
            probe.snapshot.nearby_entities_coverage, candidate_count=2,
        ),
    )
    event = replace(event, snapshot=snapshot)
    probe = replace(probe, snapshot=snapshot)
    l0 = NormalWorldL0(probe.session_id, "escape-threat", retained)
    with pytest.raises(ValueError):
        l0.decide(event, probe)
    assert l0.events == 0
