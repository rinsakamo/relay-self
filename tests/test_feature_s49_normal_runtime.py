"""S49 source-local Present projection and double-issued Action gate."""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_postmain_s42_world_contrast as s42
from adapters.mineflayer.normal_action import (
    NormalActionAuthorization,
    NormalActionRejected,
    NormalActionStage,
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
