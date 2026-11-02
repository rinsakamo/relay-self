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
from collections import deque
from dataclasses import replace
from typing import Any

from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s60b1_loopback_adapter import (
    S60_WB_ADVISORY_JSON_FORMAT,
    LoopbackDisplacementAdapter,
    LoopbackTransportConfig,
)
from adapters.mineflayer.self_body_projection import project_body_present
from adapters.mineflayer.self_world_projection import project_self_world_present
from relay_self.attention import AttentionCriterion
from relay_self.best_effort_displacement import BestEffortDisplacement
from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    select_habit,
)
from relay_self.interruption_fence import CognitionContext
from relay_self.prediction import (
    PredictionState,
    StateVariable,
    TransitionRule,
    predict_transition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoice, BoundedChoiceRequest
from relay_self.self_body import compose_self_body_view
from relay_self.self_cognition_slice import CognitionTier, project_cognition_slice
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
        wb_cognition_slice: bool = False,
        structured_json_off: bool = False,
    ) -> None:
        if type(self_world_live) is not bool:
            raise ValueError("self_world_live must be explicit bool")
        if type(wb_cognition_slice) is not bool or (wb_cognition_slice and not self_world_live):
            raise ValueError("WB cognition slice requires explicit SelfWorld live mode")
        if type(structured_json_off) is not bool or (structured_json_off and not wb_cognition_slice):
            raise ValueError("structured L2 requires explicit WB cognition slice")
        self.self_world_live = self_world_live
        self.wb_cognition_slice = wb_cognition_slice
        self.structured_json_off = structured_json_off
        self._wb_l2_source: str | None = None
        self._wb_world_cues: int = 0
        self._wb_world_omitted: int = 0
        self.config = LoopbackTransportConfig(
            model=model, port=port, slots=1, max_tokens=96,
            connect_s=min(3.0, timeout_s), read_s=timeout_s, whole_s=timeout_s,
            structured_json_off=structured_json_off,
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
        # Host callback order only; no Paper tick timing or server attestation.
        self._wb_acceptance_host_order: dict[str, object] | None = None
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
        self._body_l2_bound: bool = False
        # WB-only readout of pre-existing S60 receipts. No transport hooks,
        # wall-clock conclusions or extra provider/model/native calls.
        self._wb_source_advance: deque[dict[str, object]] = deque(maxlen=8)

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
        epoch = f"native-{reading.seq}"
        body = compose_self_body_view(
            self_id=observer, session_id=reading.session_id,
            epoch_id=epoch, observation=project_body_present(present),
        )
        current = compose_self_world_view(
            self_id=observer, session_id=reading.session_id,
            epoch_id=epoch, observation=world_obs, self_body=body,
        )
        # The same already-received S49 native probe is the only source for
        # both cognition interfaces; no new native read or owner is created.
        if (
            current.self_body is not body or body.observation is None
            or current.observation is None
            or body.observation.native_seq != current.observation.native_seq
            or body.observation.request_id != current.observation.request_id
            or body.observation.source_provenance != current.observation.provenance
        ):
            raise ValueError("SelfBody/SelfWorld native source mismatch")
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
        self._body_l2_bound = True
        # This string is only untrusted user data for an existing read-only L2
        # provider. Model output cannot enter L0 or any physical Action route.
        data = {
            "observer": fields["self_world_observer"],
            "observed": fields["self_world_observed"],
            "prediction_review": fields["self_world_prediction_review"],
            "self_body": {
                "source_ref": body.observation.source_ref,
                "native_seq": body.observation.native_seq,
                "health": {
                    "origin": body.observed("health").origin.value,
                    "value": body.observed("health").value,
                },
                "food": {
                    "origin": body.observed("food").origin.value,
                    "value": body.observed("food").value,
                },
                # M/P1 energy and fatigue have no qualified source in Present.
                "energy": {"origin": "unknown", "value": None},
                "fatigue": {"origin": "unknown", "value": None},
            },
            "preconfigured_l1_cognitive_candidate": habit.selected_candidate_ref,
        }
        if self.wb_cognition_slice:
            # The existing source-bound World/Body join is read exactly once.
            # L2 gets a bounded view, not another packet, model or Action owner.
            wb = project_cognition_slice(current, tier=CognitionTier.L2)
            if (wb.world_source_ref != world_obs.source_ref
                    or wb.body_source_ref != body.observation.source_ref):
                raise ValueError("WB projection does not match current native source")
            data["observed"] = [
                {
                    "entity_ref": cue.entity.entity_ref,
                    "label": cue.entity.label,
                    "position": cue.entity.position,
                    "distance_m": cue.entity.distance_m,
                    "visible_action": cue.entity.visible_action,
                    "origin": "observed",
                }
                for cue in wb.visible_world
            ]
            data["wb_cognition_budget"] = {
                "tier": wb.tier.value,
                "world_status": wb.world_status,
                "body_status": wb.body_status,
                "world_source_ref": wb.world_source_ref,
                "body_source_ref": wb.body_source_ref,
                "visible_world_count": len(wb.visible_world),
                "world_omitted": wb.world_omitted,
                "detail_available": wb.detail_available,
                "source_attested": wb.source_attested,
                "memory_id_count": len(wb.remembered_ids),
                "scenario_id_count": len(wb.scenario_ids),
            }
            self._wb_l2_source = wb.world_source_ref
            self._wb_world_cues = len(wb.visible_world)
            self._wb_world_omitted = wb.world_omitted
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
            if self.wb_cognition_slice:
                # Snapshot existing receipts BEFORE original S60 observes the
                # newer epoch. This is local host order, not backend stop ACK
                # or independently verified Paper callback chronology.
                self._wb_source_advance.append({
                    "new_native_seq": reading.seq,
                    "provider_receipts_before": [
                        event for event, _ in self._adapter.receipts
                    ] if self._adapter is not None else [],
                    "owner_receipts_before": [
                        event.event for event in self._owner.receipts
                    ],
                })
            # The next actual World source invalidates all prior L2 cognition;
            # even a completed old thought cannot authorize the new epoch.
            self._owner.observe(context)
            if self._accepted_text is not None:
                self._phase = "EXPIRED_WORLD_ADVANCED"
            return
        if self._model_attempts:
            raise ValueError("one model attempt per owned World session")
        if self.self_world_live:
            try:
                prompt = self._live_self_world_prompt(reading)
            except (ValueError, TypeError):
                # An optional observer must not interrupt S49's existing
                # single-owner L0 loop when its evidence is unsuitable.
                self._phase = "SELF_WORLD_INPUT_UNQUALIFIED"
                return
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
                **({
                    "reasoning_effort": "none",
                    "response_format": S60_WB_ADVISORY_JSON_FORMAT,
                } if self.structured_json_off else {}),
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
                    if self.structured_json_off:
                        try:
                            datum = json.loads(value)
                            if (not isinstance(datum, dict)
                                    or set(datum) != {"uncertainty"}
                                    or not isinstance(datum["uncertainty"], str)
                                    or not 0 < len(datum["uncertainty"].strip()) <= 300):
                                raise ValueError("invalid bounded structured L2 advisory")
                        except (ValueError, TypeError):
                            # S60 transport success is not semantic L2 acceptance.
                            self._phase = "STRUCTURED_CONTENT_UNCONFIRMED"
                            self._ended_at = time.monotonic()
                            return
                        value = json.dumps(datum, sort_keys=True, ensure_ascii=True)
                    self._accepted_text = value[:1000]
                    self._accepted_source_seq = result.request.context.world_seq
                    if self.wb_cognition_slice and self.structured_json_off:
                        self._wb_acceptance_host_order = {
                            "source_world_seq": result.request.context.world_seq,
                            "latest_native_seq_at_acceptance": self._current_seq,
                            "native_callbacks_seen_at_acceptance": self._source_observations,
                            "observer_closed_at_acceptance": self._closed,
                            "owner_completion_observed_at_acceptance": any(
                                r.event == "BACKEND_COMPLETION_OBSERVED"
                                for r in self._owner.receipts
                            ),
                        }
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
        wb_pre_close_transport = (
            [event for event, _ in self._adapter.receipts]
            if self.wb_cognition_slice and self._adapter is not None else []
        )
        wb_pre_close_owner = (
            [event.event for event in self._owner.receipts]
            if self.wb_cognition_slice and self._owner is not None else []
        )
        wb_pre_close_lease_active = (
            self._owner is not None and self._owner.active is not None
        ) if self.wb_cognition_slice else False
        if self._adapter is not None:
            await self._adapter.aclose()
        if self._owner is not None and self._accepted_text is not None:
            if self._accepted_source_seq != self._current_seq:
                self._phase = "EXPIRED_WORLD_ADVANCED"
        elif self._phase == "IN_FLIGHT":
            # Local task cancellation is NOT proof of backend stop/slot release.
            self._phase = "UNCONFIRMED_LOCAL_CLIENT_CLOSED"
        result = {
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
            "wb_cognition_slice": self.wb_cognition_slice,
            "structured_json_off": self.structured_json_off,
            "wb_structured_acceptance_host_order": (
                dict(self._wb_acceptance_host_order)
                if self.structured_json_off and self._wb_acceptance_host_order is not None
                else None
            ),
            "wb_l2_source_ref": self._wb_l2_source,
            "wb_world_cues": self._wb_world_cues,
            "wb_world_omitted": self._wb_world_omitted,
            "self_world_prior_source": self._world_prior_source,
            "self_world_after_source": self._world_after_source,
            "self_world_review_status": self._world_review_status,
            "self_world_review_reason": self._world_review_reason,
            "preconfigured_l1_cognitive_candidate": self._world_l1_candidate,
            "self_world_l2_input_bound": self._world_l2_bound,
            "self_body_l2_input_bound": self._body_l2_bound,
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
        if self.wb_cognition_slice:
            # Existing owner and adapter events are evidence, not a root-cause
            # verdict. Transport completion can be real yet stale for S60.
            # These are independent host facts. In particular, a false HTTP
            # completion flag cannot distinguish unread HTTP from rejected JSON.
            http_completed = "HTTP_COMPLETION_OBSERVED" in wb_pre_close_transport
            owner_completed = "BACKEND_COMPLETION_OBSERVED" in wb_pre_close_owner
            if self._accepted_text is not None:
                completion_state = (
                    "ACCEPTED_CURRENT" if result["text_current"]
                    else "ACCEPTED_THEN_WORLD_ADVANCED"
                )
            elif http_completed and "STALE_REJECTED" in wb_pre_close_owner:
                completion_state = "HTTP_COMPLETED_S60_STALE_REJECTED"
            elif http_completed:
                completion_state = "HTTP_COMPLETED_S60_ACCEPTANCE_UNCONFIRMED"
            elif "PROVIDER_UNCONFIRMED" in wb_pre_close_owner:
                completion_state = "PROVIDER_FAILED_HTTP_COMPLETION_UNCONFIRMED"
            else:
                completion_state = "HTTP_COMPLETION_UNCONFIRMED"
            result["wb_s60_diagnostic"] = {
                "classification": "HOST_RECEIPT_ONLY_NOT_PHYSICAL_ATTESTATION",
                "transport_events_before_cleanup": wb_pre_close_transport,
                "transport_events_after_cleanup": (
                    [event for event, _ in self._adapter.receipts]
                    if self._adapter is not None else []
                ),
                "owner_events_before_cleanup": wb_pre_close_owner,
                "source_advance_samples": list(self._wb_source_advance),
                "http_completion_observed_before_cleanup": (
                    "HTTP_COMPLETION_OBSERVED" in wb_pre_close_transport
                ),
                "accepted_current_text": result["text_current"],
                "completion_state": completion_state,
                "owner_completion_observed_before_cleanup": owner_completed,
                "accepted_text_ever_observed": self._accepted_text is not None,
                "source_world_seq": self._initial_seq,
                "latest_world_seq": self._current_seq,
                "lease_active_before_cleanup": wb_pre_close_lease_active,
                "http_status": "UNRECORDED",
                "http_framing": "UNRECORDED",
                "completion_envelope": "UNRECORDED",
                "root_cause": "UNDETERMINED",
                "native_stop_ack": "UNATTESTED",
            }
        return result
