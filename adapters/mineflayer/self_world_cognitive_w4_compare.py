"""Optional Stage-3 W4 read-only cognition projection comparison (DEV/OFFLINE).

Input MUST already come from pinned saved-source replay. Calls the existing
W4 source/review validator without reinterpreting its evidence. No provider,
physical Action, World, saved-record writing or learning side effects.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.self_world_observation_only_cognition import (
    W4OfflineCognitionInputs,
    prepare_w4_offline_cognition_inputs,
)
from adapters.mineflayer.self_world_observation_only_epoch_replay import (
    W4OfflineEpochReplay,
)
from relay_self.cognition_view import (
    CognitiveView,
    CognitionTier,
    bind_cognitive_view_to_request,
    project_cognitive_view,
)
from relay_self.relay_engine import BoundedChoiceRequest, OpenCognitionRequest


class W4CognitiveComparisonBlocked(ValueError):
    """Unexpected source or ability to promote a DEV replay to World truth."""


@dataclass(frozen=True, slots=True)
class W4CognitiveContextComparison:
    """Paired requests; no model calls or claims of performance improvement."""

    source_head: str
    report_sha256: str
    run_id: str
    tier: CognitionTier
    baseline: W4OfflineCognitionInputs
    prior_view: CognitiveView
    following_view: CognitiveView
    prior_bounded: BoundedChoiceRequest
    following_bounded: BoundedChoiceRequest
    prior_open: OpenCognitionRequest
    following_open: OpenCognitionRequest
    # Serialization-size proxy, not measured token usage, latency or M0 cost.
    prior_context_bytes_baseline: int
    prior_context_bytes_projected: int
    following_context_bytes_baseline: int
    following_context_bytes_projected: int
    classification: str = "DEV_ONLY_W4_SAVED_SOURCE_CONTEXT_COMPARISON"
    model_calls: int = 0
    physical_actions: int = 0
    outcomes: int = 0
    memory_writes: int = 0
    s10_updates: int = 0
    source_world_qualified: bool = False
    science_qualified: bool = False


def _bytes(request: BoundedChoiceRequest | OpenCognitionRequest) -> int:
    return sum(
        len(item.value_json.encode("utf-8")) for item in request.context
    )


def prepare_w4_cognitive_context_comparison(
    replay: W4OfflineEpochReplay,
    *,
    tier: CognitionTier,
    max_native_seq_gap: int = 8,
    max_world_facts: int = 8,
) -> W4CognitiveContextComparison:
    """Run the SAME replay/ATT/PRD gate, then compare contexts only.

    The replay loader requires operator-pinned saved bytes. This function
    cannot itself authenticate the origin of a caller-created replay object;
    it revalidates the typed W4 contents using the existing owner gate.
    Source freshness without a trusted clock remains UNVERIFIED_FRESHNESS.
    No Body signal or World revision is invented for older W4 evidence.
    """
    if not isinstance(tier, CognitionTier):
        raise W4CognitiveComparisonBlocked("typed tier required")
    baseline = prepare_w4_offline_cognition_inputs(
        replay, max_native_seq_gap=max_native_seq_gap,
    )
    before, after = replay.prior, replay.following
    a = project_cognitive_view(
        before, tier=tier, max_world_facts=max_world_facts,
        max_body_facts=0, expected_epoch_id=before.epoch_id,
    )
    b = project_cognitive_view(
        after, tier=tier, max_world_facts=max_world_facts,
        max_body_facts=0, expected_epoch_id=after.epoch_id,
        minimum_native_seq=before.observation.native_seq + 1,
    )
    for frame in (a, b):
        if (
            frame.body_status != "UNKNOWN"
            or frame.body_facts
            or frame.world_status != "UNVERIFIED_FRESHNESS"
            or frame.world_revision is not None
            or frame.world_source_ref is None
        ):
            raise W4CognitiveComparisonBlocked(
                "W4 lacks body observation, clock and attested World revision"
            )

    def bind(world, old):
        return bind_cognitive_view_to_request(
            world, old, tier=tier, max_world_facts=max_world_facts,
            max_body_facts=0, expected_epoch_id=world.epoch_id,
            minimum_native_seq=(before.observation.native_seq + 1)
            if world is after else 0,
        )

    prior_bounded = bind(before, baseline.prior_bounded)
    following_bounded = bind(after, baseline.following_bounded)
    prior_open = bind(before, baseline.prior_open)
    following_open = bind(after, baseline.following_open)
    for original, projected in (
        (baseline.prior_bounded, prior_bounded),
        (baseline.following_bounded, following_bounded),
        (baseline.prior_open, prior_open),
        (baseline.following_open, following_open),
    ):
        if (
            projected.context[:len(original.context)] != original.context
            or len(projected.context) != len(original.context) + 3
            or type(projected) is not type(original)
            or projected.request_id != original.request_id
            or projected.instruction != original.instruction
            or projected.intent_id != original.intent_id
            or projected.focus != original.focus
        ):
            raise W4CognitiveComparisonBlocked(
                "projector altered existing owner cognition request"
            )
        if (isinstance(original, BoundedChoiceRequest)
                and (original.choices != projected.choices
                     or original.think_allowed != projected.think_allowed)):
            raise W4CognitiveComparisonBlocked(
                "cognitive comparison may not alter action/choice admission"
            )
    if (
        prior_bounded.context != prior_open.context
        or following_bounded.context != following_open.context
    ):
        raise W4CognitiveComparisonBlocked(
            "bounded and open must share one evidence projection"
        )
    return W4CognitiveContextComparison(
        source_head=replay.source_head,
        report_sha256=replay.report_sha256, run_id=replay.run_id,
        tier=tier, baseline=baseline, prior_view=a, following_view=b,
        prior_bounded=prior_bounded, following_bounded=following_bounded,
        prior_open=prior_open, following_open=following_open,
        prior_context_bytes_baseline=_bytes(baseline.prior_bounded),
        prior_context_bytes_projected=_bytes(prior_bounded),
        following_context_bytes_baseline=_bytes(baseline.following_bounded),
        following_context_bytes_projected=_bytes(following_bounded),
    )
