"""Prepare W4 saved SelfWorld epochs for existing cognition API (DEV/OFFLINE).

No L0, S14, physical Action, BLF, Memory, S17 or S10 ownership, provider
invocation, World access, or authority. Replay and original report hashes
must be verified by the separate read-only saved source loader.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from adapters.mineflayer.self_world_observation_only_epoch_replay import (
    W4OfflineEpochReplay,
)
from relay_self.attention import AttentionCriterion
from relay_self.prediction import (
    PredictionState,
    StateVariable,
    TransitionRule,
    predict_transition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    OpenCognitionRequest,
)
from relay_self.self_world import (
    WorldForecast,
    WorldPredictionReviewStatus,
    WorldScenario,
    bind_self_world_to_cognition_request,
    review_self_world_prediction,
    select_self_world_attention,
)


class W4CognitionInputBlocked(ValueError):
    """A foreign, stale or counterfeit offline source cannot become cognition."""


@dataclass(frozen=True, slots=True)
class W4OfflineCognitionInputs:
    """Prepared, nonexecuting RelayEngine request comparison, not a route."""

    prior_bounded: BoundedChoiceRequest
    following_bounded: BoundedChoiceRequest
    prior_open: OpenCognitionRequest
    following_open: OpenCognitionRequest
    prior_selected: int
    following_selected: int
    review_status: str | None
    source_scope: str = "LOCAL_DEV_SAVED_SOURCE_COGNITION_INPUT_ONLY"
    model_calls: int = 0
    action_count: int = 0
    outcome_count: int = 0
    s10_update_count: int = 0
    memory_writes: int = 0
    world_qualified: bool = False
    science_qualified: bool = False


def _request_pair(run_id: str, epoch: str):
    bounded = BoundedChoiceRequest(
        request_id=f"w4-offline-{run_id}-{epoch}-bounded",
        instruction=(
            "Compare observer-local evidence. Unobserved is UNKNOWN, not "
            "physically absent. Never authorize or request a World action."
        ),
        intent_id=None,
        focus="selfworld-read-only-review",
        choices=(
            BoundedChoice("INSPECT_SOURCE", "Inspect only positively observed source"),
            BoundedChoice("DEFER_RECHECK", "Defer claims unsupported by current source"),
        ),
        context=(),
        think_allowed=True,
    )
    opened = OpenCognitionRequest(
        request_id=f"w4-offline-{run_id}-{epoch}-open",
        instruction="Offer only a hypothesis without observation or Action authority.",
        intent_id=None,
        focus="selfworld-read-only-hypothesis",
        context=(),
    )
    return bounded, opened


def prepare_w4_offline_cognition_inputs(
    replay: W4OfflineEpochReplay, *, max_native_seq_gap: int = 8,
) -> W4OfflineCognitionInputs:
    """Recompute provenance-bound ATT and PRD before projecting to RelayEngine.

    This does not itself attest origin: the caller must first use the pinned
    saved-evidence replay. A synthetic provider may inspect requests in tests;
    no model is called from this code.
    """
    if type(replay) is not W4OfflineEpochReplay or (
        replay.source_scope != "LOCAL_DEV_SAVED_NODE_JSONL_NOT_MINECRAFT_TCP"
        or replay.classification != "DEV_ONLY_OFFLINE_SELF_WORLD_EPOCH_REPLAY"
        or any(type(getattr(replay, k)) is not int or getattr(replay, k) != 0
               for k in ("physical_action_count", "outcome_count", "s10_update_count"))
        or replay.retained_memory_written is not False
        or replay.cognition_route_executed is not False
        or replay.world_qualification is not False
        or replay.science_qualified is not False
        or re.fullmatch(r"[0-9a-f]{40}", replay.source_head) is None
        or re.fullmatch(r"[0-9a-f]{16}", replay.run_id) is None
        or re.fullmatch(r"[0-9a-f]{64}", replay.report_sha256) is None
        or re.fullmatch(r"[0-9a-f]{64}", replay.node_stdout_sha256) is None
        or type(max_native_seq_gap) is not int or max_native_seq_gap <= 0
    ):
        raise W4CognitionInputBlocked("unqualified DEV replay or bound")
    previous, current = replay.prior, replay.following
    prior, following = previous.observation, current.observation
    if prior is None or following is None or (
        previous.self_id != current.self_id
        or previous.session_id != current.session_id
        or prior.observer_id != previous.self_id
        or following.observer_id != current.self_id
        or prior.session_id != previous.session_id
        or following.session_id != current.session_id
        or previous.epoch_id != f"w4-{replay.run_id}-before-{prior.native_seq}"
        or current.epoch_id != f"w4-{replay.run_id}-after-{following.native_seq}"
        or prior.native_seq >= following.native_seq
        or prior.source_ref == following.source_ref
        or prior.provenance.source != "mineflayer"
        or following.provenance.source != "mineflayer"
        or prior.provenance.reference != f"{prior.session_id}:{prior.native_seq}"
        or following.provenance.reference != f"{following.session_id}:{following.native_seq}"
        or previous.self_body is not None or current.self_body is not None
        or previous.memories or current.memories
        or previous.beliefs or current.beliefs
        or current.scenarios or current.forecasts
    ):
        raise W4CognitionInputBlocked("foreign, replayed or enriched SelfWorld epoch")
    criterion = AttentionCriterion(
        criterion_id="w4-offline-first-positive-source", top_k=1,
    )
    if (
        replay.prior_attention != select_self_world_attention(previous, criterion)
        or replay.following_attention != select_self_world_attention(current, criterion)
    ):
        raise W4CognitionInputBlocked("forged or stale ATT")
    expected_review = None
    if replay.prior_attention.selected:
        selected_ref = replay.prior_attention.selected[0].payload_ref
        fact = previous.observed_entity(selected_ref).value
        if fact is not None and fact.label is not None:
            if len(previous.scenarios) != 1 or len(previous.forecasts) != 1:
                raise W4CognitionInputBlocked("missing prior forecast")
            # Match the saved replay's specific hypothesis, not merely any
            # internally self-consistent forecast supplied with a new review.
            state = PredictionState(
                f"w4-local-{replay.run_id}-{prior.native_seq}",
                (StateVariable("entity_label", fact.label),),
                Provenance("w4-offline-dev-forecast", prior.source_ref),
                source_refs=(prior.source_ref, f"target:{selected_ref}"),
                source_provenance=(prior.provenance,),
            )
            rule = TransitionRule(
                "hypothetical-label-persistence",
                (StateVariable("entity_label", fact.label),),
                (StateVariable("entity_label", fact.label),),
                Provenance("w4-offline-hypothesis", "not-a-learned-world-law"),
            )
            scenario = WorldScenario(
                f"w4-{replay.run_id}-label", previous.self_id, selected_ref, state,
            )
            forecast = WorldForecast(scenario.scenario_id, predict_transition(state, rule))
            if previous.scenarios != (scenario,) or previous.forecasts != (forecast,):
                raise W4CognitionInputBlocked("forecast differs from saved replay hypothesis")
            expected_review = review_self_world_prediction(
                previous, current, scenario_id=scenario.scenario_id,
                variable_key="entity_label", max_native_seq_gap=max_native_seq_gap,
            )
    if (
        (expected_review is None and (previous.scenarios or previous.forecasts))
        or replay.prediction_review != expected_review
    ):
        raise W4CognitionInputBlocked("missing or forged PRD review")
    before_bounded, before_open = _request_pair(replay.run_id, "before")
    after_bounded, after_open = _request_pair(replay.run_id, "after")
    kwargs = (
        dict(review=expected_review, prior=previous,
             max_native_seq_gap=max_native_seq_gap)
        if expected_review is not None else {}
    )
    b0 = bind_self_world_to_cognition_request(
        previous, replay.prior_attention, before_bounded,
    )
    o0 = bind_self_world_to_cognition_request(
        previous, replay.prior_attention, before_open,
    )
    b1 = bind_self_world_to_cognition_request(
        current, replay.following_attention, after_bounded, **kwargs,
    )
    o1 = bind_self_world_to_cognition_request(
        current, replay.following_attention, after_open, **kwargs,
    )
    assert type(b0) is BoundedChoiceRequest and type(b1) is BoundedChoiceRequest
    assert type(o0) is OpenCognitionRequest and type(o1) is OpenCognitionRequest
    status: WorldPredictionReviewStatus | None = (
        expected_review.status if expected_review is not None else None
    )
    return W4OfflineCognitionInputs(
        prior_bounded=b0, following_bounded=b1,
        prior_open=o0, following_open=o1,
        prior_selected=len(replay.prior_attention.selected),
        following_selected=len(replay.following_attention.selected),
        review_status=status.value if status is not None else None,
    )
