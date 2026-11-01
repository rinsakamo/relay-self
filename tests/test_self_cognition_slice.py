"""WB read-only cognition budget: synthetic DEV tests only."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from relay_self.provenance import Provenance
from relay_self.self_body import (
    BodyField,
    BodyObservation,
    BodyOrigin,
    compose_self_body_view,
)
from relay_self.self_cognition_slice import CognitionTier, project_cognition_slice
from relay_self.self_world import (
    InvalidSelfWorldData,
    WorldEntityObservation,
    WorldObservation,
    compose_self_world_view,
)


def sample(*, count: int = 5, truncated: bool = False, with_body: bool = True):
    provenance = Provenance("mineflayer", "s:9")
    observed = WorldObservation(
        observer_id="A", session_id="s", native_seq=9, request_id="p9",
        entities=tuple(
            WorldEntityObservation(
                entity_ref=f"entity-{i}", label="zombie",
                position=(float(i), 64.0, 0.0),
                distance_m=float(count - i),
            )
            for i in range(count)
        ),
        coverage_scope="nearby", coverage_radius_m=16.0,
        coverage_cap=16, coverage_candidates=count,
        coverage_truncated=truncated, provenance=provenance,
    )
    body = None
    if with_body:
        body = compose_self_body_view(
            self_id="A", session_id="s", epoch_id="e9",
            observation=BodyObservation(
                session_id="s", native_seq=9, request_id="p9",
                fields=(
                    BodyField("health", 10.0),
                    BodyField("food", 6.0),
                    BodyField("position_x", 1.0),
                    BodyField("position_y", 64.0),
                    BodyField("position_z", 2.0),
                    BodyField("food_saturation", 3.0),
                ),
                source_provenance=provenance,
            ),
        )
    return compose_self_world_view(
        self_id="A", session_id="s", epoch_id="e9",
        observation=observed, self_body=body,
    )


def test_minimal_unknown_does_not_mean_world_clear():
    v = compose_self_world_view(
        self_id="A", session_id="s", epoch_id="e9",
    )
    for tier in CognitionTier:
        x = project_cognition_slice(v, tier=tier)
        assert x.world_status == "UNKNOWN"
        assert x.body_status == "UNKNOWN"
        assert x.visible_world == x.body_cues == ()
        assert x.world_source_ref is None and x.body_source_ref is None
        assert not x.source_attested


def test_bounded_lanes_share_original_observation_and_dont_overclaim():
    v = sample()
    l0 = project_cognition_slice(v, tier=CognitionTier.L0)
    l1 = project_cognition_slice(v, tier=CognitionTier.L1)
    l2 = project_cognition_slice(v, tier=CognitionTier.L2)
    assert (len(l0.visible_world), len(l1.visible_world), len(l2.visible_world)) == (1, 3, 5)
    assert (len(l0.body_cues), len(l1.body_cues), len(l2.body_cues)) == (2, 4, 6)
    assert l0.visible_world[0].entity.entity_ref == "entity-4"
    assert l0.visible_world[0].source_ref == "present:s:9:p9"
    assert all(c.source_provenance == v.observation.provenance for c in l2.visible_world)
    assert all(c.origin is BodyOrigin.OBSERVATION for c in l2.body_cues)
    assert l0.world_omitted == 4 and l1.world_omitted == 2 and l2.world_omitted == 0
    assert l0.detail_available and l1.detail_available
    assert l2.world_status == "BOUNDED"  # bounded coverage != full-world census
    assert l0.remembered_ids == l1.remembered_ids == ()
    assert l0.scenario_ids == l1.scenario_ids == ()


def test_missing_body_does_not_prevent_l0():
    x = project_cognition_slice(sample(with_body=False), tier=CognitionTier.L0)
    assert x.body_status == "UNKNOWN"
    assert x.body_cues == ()
    assert len(x.visible_world) == 1


def test_truncation_not_converted_to_absence_or_safety():
    x = project_cognition_slice(sample(count=0, truncated=True), tier=CognitionTier.L2)
    assert x.world_status == "TRUNCATED"
    assert x.visible_world == ()
    assert x.world_source_ref == "present:s:9:p9"


def test_foreign_session_and_synthetic_body_source_cannot_sneak_into_projection():
    v = sample()
    foreign_body = replace(v.self_body, session_id="other")
    with pytest.raises(InvalidSelfWorldData, match="body owner/session/epoch"):
        project_cognition_slice(replace(v, self_body=foreign_body), tier=CognitionTier.L1)
    wrong_source = replace(
        v.self_body.observation,
        request_id="forged",
    )
    with pytest.raises(InvalidSelfWorldData, match="original Present"):
        project_cognition_slice(
            replace(v, self_body=replace(v.self_body, observation=wrong_source)),
            tier=CognitionTier.L2,
        )
    with pytest.raises(InvalidSelfWorldData, match="world owner/session"):
        project_cognition_slice(
            replace(v, observation=replace(v.observation, observer_id="B")),
            tier=CognitionTier.L0,
        )


def test_budget_is_not_requested_by_untrusted_caller():
    v = sample()
    with pytest.raises(InvalidSelfWorldData, match="cognition tier"):
        project_cognition_slice(v, tier="L2")
    with pytest.raises(FrozenInstanceError):
        project_cognition_slice(v, tier=CognitionTier.L0).world_status = "CLEAR"


def test_tiers_cannot_promote_unobserved_hypotheses_or_old_memory_as_truth():
    v = sample(count=1)
    # Externally supplied fake epoch views are not trusted; even with optional
    # metadata inputs the projection only reveals typed observed Body/World cues.
    for tier in CognitionTier:
        x = project_cognition_slice(v, tier=tier)
        assert x.world_status == "BOUNDED"
        assert all(c.entity.label == "zombie" for c in x.visible_world)
        assert x.remembered_ids == x.scenario_ids == ()
        assert x.body_source_ref == "present:s:9:p9"
