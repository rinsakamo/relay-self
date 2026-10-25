"""DEV-only P1 movement/WAIT model exposed through existing SelfBody interface.

Without a newly correlated native Present *after* Paper WAIT, a model
value must remain BodyHypothesis, NEVER BodyInteroception or OBSERVATION.
This adapter grants no action, memory, energy, resource or R qualification.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_paper_postwait_dev import review_postaction_wait_dev
from experiments.fatigue_p1 import (
    FatigueProfile,
    FatigueSensor,
    FatigueState,
    capability,
    observe,
)
from relay_self.prediction import PredictionState, StateVariable
from relay_self.provenance import Provenance
from relay_self.self_body import (
    BodyHypothesis,
    BodyOrigin,
    SelfBodyView,
    compose_self_body_view,
)

MODEL = "p1-dev-distance-wait"
SOURCE_SCOPE = "DEV_ACTION_DISTANCE_AND_PAPER_WAIT_MODEL_NO_NATIVE_POSTWAIT"
SENSOR = FatigueSensor(gain=1.0, bias=0.0, quantum=0.01)


@dataclass(frozen=True, slots=True)
class P1DevSelfBodyHandoff:
    """Two immutable cognition epochs, not persistent actual Body state."""

    after_move: SelfBodyView
    after_wait: SelfBodyView
    session_id: str
    action_id: str
    world: str
    observer_run_id: str
    model_source_digest: str
    observed_wait_samples: int
    source_scope: str = SOURCE_SCOPE

    def next_cognition_readback(self) -> dict[str, object]:
        """Read the *model* through the same SelfBody hypothetical API."""
        prior = self.after_move.hypothetical(MODEL, "p1_sensor_pct")
        latest = self.after_wait.hypothetical(MODEL, "p1_sensor_pct")
        if (prior.origin is not BodyOrigin.HYPOTHESIS
                or latest.origin is not BodyOrigin.HYPOTHESIS
                or self.after_wait.observed("p1_fatigue").value is not None
                or self.after_wait.sensed("p1_fatigue_sensor").value is not None):
            raise BoundaryRejected("DEV P1 model leaked into physical SelfBody sources")
        return {
            "source_scope": self.source_scope,
            "body_model_origin": "hypothesis",
            "session_id": self.session_id,
            "action_id": self.action_id,
            "world": self.world,
            "observer_run_id": self.observer_run_id,
            "model_source_digest": self.model_source_digest,
            "move_epoch": self.after_move.epoch_id,
            "wait_epoch": self.after_wait.epoch_id,
            "p1_sensor_pct_after_move": prior.value,
            "p1_sensor_pct_after_wait": latest.value,
            "p1_model_capability_pct_after_move": self.after_move.hypothetical(
                MODEL, "p1_capability_pct",
            ).value,
            "p1_model_capability_pct_after_wait": self.after_wait.hypothetical(
                MODEL, "p1_capability_pct",
            ).value,
            "paper_wait_sample_count": self.observed_wait_samples,
            "native_postwait_observation": None,
            "native_postwait_sensor_handoff": None,
            "additional_action_issuers": 0,
            "additional_native_receivers": 0,
            "actual_next_l0_decision_consumed": False,
            "qualification_go": False,
            "science_go": False,
        }


def _body_epoch(
    profile: FatigueProfile, session_id: str, action_id: str,
    source_sha256: str, *, world: str, fatigue: float,
    phase: str, tick: int, self_id: str,
) -> SelfBodyView:
    # Pure P1 sensor: quantized, not raw true P1 fatigue in the Cognition view.
    state = FatigueState(session_id, profile.sha256, tick, fatigue)
    reading = observe(profile, state, SENSOR)
    pct = int(round(reading.reading * 100))
    efficiency = int(round(capability(profile, state).efficiency * 100))
    if not 0 <= pct <= 100 or not 0 <= efficiency <= 100:
        raise BoundaryRejected("invalid DEV P1 sensor/capability range")
    native_ref = f"s49-closed-action:{session_id}:{action_id}"
    world_ref = f"paper-dev-window-sha256:{source_sha256}"
    origin = Provenance(
        "p1-dev-model-not-native-interoception",
        f"{session_id}:{action_id}:{phase}:{source_sha256}",
    )
    scenario = BodyHypothesis(
        MODEL,
        PredictionState(
            state_id=f"p1-dev-{phase}-{action_id}",
            variables=(
                StateVariable("p1_sensor_pct", pct),
                StateVariable("p1_capability_pct", efficiency),
                StateVariable("p1_phase", phase),
                StateVariable("p1_source_scope", SOURCE_SCOPE),
            ),
            provenance=origin,
            source_refs=(native_ref, world_ref, f"paper-dev-world:{world}"),
            source_provenance=(origin,),
        ),
    )
    return compose_self_body_view(
        session_id=session_id,
        self_id=self_id,
        epoch_id=f"p1-dev-{phase}-{tick}",
        # Paper records did not provide a new native Present. Never invent one.
        observation=None,
        hypotheses=(scenario,),
    )


def compose_s49_p1_dev_self_body(
    original_s49: dict,
    paper_window: str, *,
    expected_player_uuid: str,
    profile: FatigueProfile,
    self_id: str = "RelaySelf",
) -> tuple[P1DevSelfBodyHandoff, dict]:
    """Recheck original S49+Paper sources before producing two SelfBody views."""
    reviewed = review_postaction_wait_dev(
        original_s49,
        paper_window,
        expected_player_uuid=expected_player_uuid,
        profile=profile,
        fatigue_mode="MOVE_DISTANCE",
    )
    move = reviewed["dev_move"]
    if (move is None or move["fatigue_accumulated"] <= 0
            or reviewed["dev_wait_count"] != 8
            or reviewed["dev_fatigue_recovered"] <= 0
            or reviewed["dev_continuous_world_tick_fatigue_history"] is not False
            or reviewed["world_run_verified"] is not False
            or reviewed["qualification_go"] is not False):
        raise BoundaryRejected("DEV original MOVE and Paper WAIT replay required")

    sid = reviewed["session_id"]
    action_id = reviewed["action_id"]
    source_sha = reviewed["paper_window_sha256"]
    world = reviewed["world"]
    begin_tick = reviewed["uncertain_release_tick_excluded"]
    final_tick = reviewed["dev_wait_ticks"][-1]["tick"]
    after_move = _body_epoch(
        profile, sid, action_id, source_sha,
        world=world, fatigue=reviewed["dev_fatigue_before"],
        phase="after-move", tick=begin_tick, self_id=self_id,
    )
    after_wait = _body_epoch(
        profile, sid, action_id, source_sha,
        world=world, fatigue=reviewed["dev_fatigue_after"],
        phase="after-wait", tick=final_tick, self_id=self_id,
    )
    handoff = P1DevSelfBodyHandoff(
        after_move, after_wait, sid, action_id,
        world, reviewed["observer_run_id"], source_sha,
        reviewed["dev_wait_count"],
    )
    handoff.next_cognition_readback()  # fail closed before publishing
    return handoff, reviewed
