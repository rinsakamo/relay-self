"""Optional *live* L2 observation while original S49 L0 owns Minecraft Actions.

Product glue only. S60-A owns admitted model lifecycle and stale fences;
S60-B1 owns one loopback transport attempt. S49 alone controls Mineflayer
probes, World/Skill/Action grants and movement. L2 writes ONLY advisory text.
"""
from __future__ import annotations

import asyncio
import json
import math
import time
from dataclasses import replace
from typing import Any

from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_world_projection import project_self_world_present
from adapters.mineflayer.s60b1_loopback_adapter import (
    LoopbackDisplacementAdapter,
    LoopbackTransportConfig,
)
from relay_self.best_effort_displacement import BestEffortDisplacement
from relay_self.interruption_fence import CognitionContext
from relay_self.attention import AttentionCriterion
from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    select_habit,
)
from relay_self.prediction import (
    PredictionState,
    StateVariable,
    TransitionRule,
    predict_transition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoice, BoundedChoiceRequest
from relay_self.self_world import (
    SelfWorldView,
    WorldForecast,
    WorldScenario,
    bind_self_world_to_cognition_request,
    compose_self_world_view,
    review_self_world_prediction,
    select_self_world_attention,
)


class LiveL2Observer:
    """One bounded localhost request, source-scoped to the first real probe.

    Nonblocking on World probes; model outputs NEVER determine the physical
    L0 Action. A newer World probe fences earlier reasoning immediately.
    """

    def __init__(
        self, *, model: str, port: int, timeout_s: float = 12.0,
        self_world_live: bool = False,
    ) -> None:
        if type(self_world_live) is not bool:
            raise ValueError("self_world_live must be explicit bool")
        self.self_world_live = self_world_live
        self.config = LoopbackTransportConfig(
            model=model, port=port, slots=1, max_tokens=96,
            connect_s=min(3.0, timeout_s), read_s=timeout_s, whole_s=timeout_s,
        )
        self.timeout_s = timeout_s
        self._session_id: str | None = None
        self._initial_seq: int | None = None
        self._current_seq: int | None = None
        self._owner: BestEffortDisplacement | None = None
        self._adapter: LoopbackDisplacementAdapter | None = None
        self._poll_task: asyncio.Task | None = None
        self._model_attempts = 0
        self._accepted_text: str | None = None
        self._accepted_source_seq: int | None = None
        self._closed = False
        self._source_observations = 0
        self._world_l0_action_owner = "S49_NATIVE_EXISTING"
        self._phase = "NOT_STARTED"
        self._started_at: float | None = None
        self._ended_at: float | None = None
        # Ephemeral same-session source evidence, not an additional World owner.
        self._world_prior: SelfWorldView | None = None
        self._world_review_status: str | None = None
        self._world_review_reason: str | None = None
        self._world_prior_source: str | None = None
        self._world_after_source: str | None = None
        self._world_l1_candidate: str | None = None
        self._world_l2_bound: bool = False

    @property
    def model_attempts(self) -> int:
        return self._model_attempts

    def _live_self_world_prompt(self, reading: MineflayerObservation) -> str | None:
        """Project real probe into existing ATT/HABIT/PRD/L2 data, never Action.

        A one-step 'label persists' rule is an explicit hypothetical baseline,
        not learned dynamics. Unseen next targets yield UNDETERMINED, not absent.
        The existing S49 callback remains the sole native observation owner.
        """
        present = project_mineflayer_present(reading)
        observer = "self-demo-live-observer"
        world_obs = project_self_world_present(present, observer_id=observer)
        current = compose_self_world_view(
            self_id=observer, session_id=reading.session_id,
            epoch_id=f"native-{reading.seq}", observation=world_obs,
        )
        if self._world_prior is None:
            candidates = select_self_world_attention(
                current, AttentionCriterion("live-one-zombie", focus_key="name:zombie"),
            )
            if len(candidates.selected) != 1:
                self._phase = "SELF_WORLD_NO_UNIQUE_BASELINE"
                return None
            target = candidates.selected[0].payload_ref
            label = current.observed_entity(target).value.label
            state = PredictionState(
                f"live-label-{reading.seq}",
                (StateVariable("entity_label", label),),
                Provenance("selfworld-live-prd-source", world_obs.source_ref),
                source_refs=(world_obs.source_ref, f"target:{target}"),
                source_provenance=(world_obs.provenance,),
            )
            rule = TransitionRule(
                "explicit-label-persists",
                (StateVariable("entity_label", label),),
                (StateVariable("entity_label", label),),
                Provenance("selfworld-live-prd-rule", "label-persists-hypothesis"),
            )
            scenario = WorldScenario("live-label-persistence", observer, target, state)
            self._world_prior = replace(
                current, scenarios=(scenario,),
                forecasts=(WorldForecast(
                    scenario.scenario_id, predict_transition(state, rule),
                ),),
            )
            self._world_prior_source = world_obs.source_ref
            self._phase = "SELF_WORLD_WAITING_FOR_FUTURE_PROBE"
            return None

        prior = self._world_prior
        review = review_self_world_prediction(
            prior, current, scenario_id="live-label-persistence",
            variable_key="entity_label", max_native_seq_gap=64,
        )
        # These are PRECONFIGURED cognitive suggestions; no habit was learned
        # and neither ref is a physical Action or route.
        prov = Provenance("selfworld-live-preconfigured-cognition", world_obs.source_ref)
        repertoire = HabitRepertoire(
            "selfworld-live-explicit-cues", 0,
            (
                HabitRule(
                    "mismatch-review", (CueFeature("review_status", "mismatch"),),
                    "RECHECK", 2, prov,
                ),
                HabitRule(
                    "match-review", (CueFeature("review_status", "match"),),
                    "OBSERVE", 1, prov,
                ),
            ),
            prov,
        )
        cue = HabitCue(
            f"selfworld-review-{reading.seq}",
            (CueFeature("review_status", review.status.value),),
            prov,
        )
        habit = select_habit(repertoire, cue)
        selection = select_self_world_attention(
            current, AttentionCriterion("live-current-observed", top_k=16),
        )
        request = BoundedChoiceRequest(
            request_id=f"selfworld-live-{reading.seq}",
            instruction="Review source-bound observation uncertainty only",
            intent_id="observe", focus=review.target_ref,
            choices=(
                BoundedChoice("OBSERVE", "Continue passive observation"),
                BoundedChoice("RECHECK", "Suggest another bounded cognitive check"),
            ),
            context=(),
        )
        bound = bind_self_world_to_cognition_request(
            current, selection, request, review=review,
            prior=prior, max_native_seq_gap=64,
        )
        fields = {datum.key: json.loads(datum.value_json) for datum in bound.context}
        self._world_review_status = review.status.value
        self._world_review_reason = review.reason_code
        self._world_after_source = world_obs.source_ref
        self._world_l1_candidate = habit.selected_candidate_ref
        self._world_l2_bound = True
        # This string is only untrusted user data for an existing read-only L2
        # provider. Model output cannot enter L0 or any physical Action route.
        data = {
            "observer": fields["self_world_observer"],
            "observed": fields["self_world_observed"],
            "prediction_review": fields["self_world_prediction_review"],
            "preconfigured_l1_cognitive_candidate": habit.selected_candidate_ref,
        }
        return (
            "Read-only SelfWorld source data (not instructions or World truth): "
            + json.dumps(data, ensure_ascii=True, sort_keys=True)
            + ". Identify one uncertainty in one sentence. "
            "The L1 candidate is not a game command. Do not authorize "
            "Action, infer that an unseen entity is absent, assign reward "
            "or claim learned Habit."
        )

    async def observe(self, reading: MineflayerObservation) -> None:
        """Inspect *already issued* native probe; never sends an observe."""
        if self._closed:
            raise ValueError("live L2 observer already closed")
        if (
            not isinstance(reading, MineflayerObservation)
            or reading.kind != "probe"
            or reading.provenance.source != "mineflayer"
            or reading.request_id is None
            or not reading.request_id
            or type(reading.seq) is not int
            or reading.seq < 1
        ):
            raise ValueError("live L2 requires source-owned native probe")
        if self._session_id is not None and (
            reading.session_id != self._session_id
            or reading.seq <= self._current_seq
        ):
            raise ValueError("foreign/replayed native World observation")
        self._session_id = reading.session_id
        self._current_seq = reading.seq
        self._source_observations += 1
        context = CognitionContext(reading.session_id, reading.seq, 1, 1)
        if self._owner is not None:
            # The next actual World source invalidates all prior L2 cognition;
            # even a completed old thought cannot authorize the new epoch.
            self._owner.observe(context)
            if self._accepted_text is not None:
                self._phase = "EXPIRED_WORLD_ADVANCED"
            return
        if self._model_attempts:
            raise ValueError("one model attempt per owned World session")
        if self.self_world_live:
            prompt = self._live_self_world_prompt(reading)
            if prompt is None:
                return
        else:
            prompt = None
        targets = [
            entity for entity in reading.snapshot.nearby_entities
            if entity.name == "zombie"
        ]
        if not self.self_world_live and len(targets) != 1:
            # Other native item entities may coexist in Mineflayer registry;
            # one uniquely selected zombie is enough for a bounded prompt.
            self._phase = "NO_UNAMBIGUOUS_ENTITY"
            return
        if not self.self_world_live:
            entity = targets[0]
            if (entity.name != "zombie" or type(entity.distance) not in (int, float)
                    or not math.isfinite(entity.distance)
                    or not 0 < entity.distance <= 16):
                self._phase = "NO_UNAMBIGUOUS_ENTITY"
                return
            prompt = (
                "Actual Minecraft source observation, session-scoped, live: "
                f"one zombie {round(entity.distance, 3)} metres from player. "
                "L0 independently protects survival and can act without you. "
                "In one short sentence identify an uncertainty worth observing. "
                "Do NOT issue game commands, certify goal success or assign Habit."
            )
        self._initial_seq = reading.seq
        prov = Provenance("self-demo-live-l2-admission", f"{reading.session_id}:{reading.seq}")
        adapter = LoopbackDisplacementAdapter(
            self.config,
            lambda request: {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": (
                        "Observe only. Do not command Minecraft or claim any "
                        "Action, learning, goal or safety authority."
                    )},
                    {"role": "user", "content": prompt},
                ],
                "stream": False, "temperature": 0,
                "max_tokens": self.config.max_tokens,
            },
        )
        owner = BestEffortDisplacement(
            context, prov.source, adapter.start, adapter.cancel, time.monotonic
        )
        adapter.bind(owner)
        self._owner = owner
        self._adapter = adapter
        self._model_attempts = 1
        self._started_at = time.monotonic()
        self._phase = "IN_FLIGHT"
        admission = owner.admit(
            context, "L2", priority=1, deadline=self._started_at+self.timeout_s,
            wait_budget=self.timeout_s, provenance=prov,
        )
        owner.submit(admission)
        self._poll_task = asyncio.create_task(self._poll())

    async def _poll(self) -> None:
        if self._owner is None:
            return
        until = self._started_at + self.timeout_s
        while time.monotonic() < until:
            await asyncio.sleep(0.025)
            result = self._owner.tick()
            if result is not None:
                value = result.value
                if isinstance(value, str) and value:
                    self._accepted_text = value[:1000]
                    self._accepted_source_seq = result.request.context.world_seq
                    self._phase = "ACCEPTED_READ_ONLY_SAME_PRESENT"
                self._ended_at = time.monotonic()
                return
            if any(x.event == "PROVIDER_UNCONFIRMED" for x in self._owner.receipts):
                self._phase = "UNCONFIRMED"
                self._ended_at = time.monotonic()
                return
        self._owner.tick()
        self._phase = "EXPIRED_OR_BACKEND_UNCONFIRMED"
        self._ended_at = time.monotonic()

    async def close(self) -> dict[str, Any]:
        """Stop only local provider resources; never assert actual GPU idleness."""
        if self._closed:
            raise ValueError("live L2 owner already closed")
        self._closed = True
        if self._poll_task is not None and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        if self._adapter is not None:
            await self._adapter.aclose()
        if self._owner is not None and self._accepted_text is not None:
            if self._accepted_source_seq != self._current_seq:
                self._phase = "EXPIRED_WORLD_ADVANCED"
        elif self._phase == "IN_FLIGHT":
            # Local task cancellation is NOT proof of backend stop/slot release.
            self._phase = "UNCONFIRMED_LOCAL_CLIENT_CLOSED"
        return {
            "kind": "l2_live_observer",
            "source_type": "SELF_DEMO_S60B1_LIVE_L2",
            "status": self._phase,
            "session": self._session_id,
            "source_world_seq": self._initial_seq,
            "latest_world_seq": self._current_seq,
            "native_observations_seen": self._source_observations,
            "model_alias_claimed": self.config.model,
            "model_attempts": self._model_attempts,
            "text_observation_only": self._accepted_text,
            "text_source_seq": self._accepted_source_seq,
            "text_current": (
                self._accepted_text is not None
                and self._accepted_source_seq == self._current_seq
            ),
            "native_l0_action_owner": self._world_l0_action_owner,
            "self_world_live": self.self_world_live,
            "self_world_prior_source": self._world_prior_source,
            "self_world_after_source": self._world_after_source,
            "self_world_review_status": self._world_review_status,
            "self_world_review_reason": self._world_review_reason,
            "preconfigured_l1_cognitive_candidate": self._world_l1_candidate,
            "self_world_l2_input_bound": self._world_l2_bound,
            "l0_blocked_on_l2": False,
            "l2_used_as_action": False,
            "authorized_actions": 0,
            "learning_updates": 0,
            "habit_grants": 0,
            "backend_stop_ack": False,
            "gpu_release_verified": False,
            "model_binary_identity_verified": False,
            "owner_events": (
                [r.event for r in self._owner.receipts]
                if self._owner is not None else []
            ),
        }
