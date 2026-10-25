"""DEV-only P1 movement/WAIT model exposed through existing SelfBody interface.

Without a newly correlated native Present *after* Paper WAIT, a model
value must remain BodyHypothesis, NEVER BodyInteroception or OBSERVATION.
This adapter grants no action, memory, energy, resource or R qualification.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_paper_postwait_dev import review_postaction_wait_dev
from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_body_projection import project_body_present
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
    InvalidSelfBodyData,
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


def compose_s49_p1_postwait_native_dev(
    handoff: P1DevSelfBodyHandoff, reviewed: dict,
    final_original_action: dict, probe: MineflayerObservation, *,
    expected_request_id: str,
) -> tuple[SelfBodyView, dict[str, object]]:
    """Create NEXT read-only cognition epoch from one real post-WAIT native probe.

    The probe is obtained by the original S49 owner inside its suspended
    Action callback, AFTER the Paper observer COMPLETE. No other session
    reader is active. Paper World's full-tick activity and P1 true fatigue
    remain unauthenticated; observed health/food/position do not prove those.
    """
    if (not isinstance(handoff, P1DevSelfBodyHandoff)
            or not isinstance(reviewed, dict)
            or not isinstance(final_original_action, dict)
            or not isinstance(probe, MineflayerObservation)
            or not isinstance(expected_request_id, str)
            or not expected_request_id
            or expected_request_id != (
                f"s49-postwait:{handoff.session_id}:{handoff.action_id}"
            )
            or handoff.session_id != reviewed.get("session_id")
            or handoff.action_id != reviewed.get("action_id")
            or handoff.world != reviewed.get("world")
            or handoff.observer_run_id != reviewed.get("observer_run_id")
            or handoff.model_source_digest != reviewed.get("paper_window_sha256")
            or handoff.observed_wait_samples != reviewed.get("dev_wait_count")
            or reviewed.get("dev_fatigue_mode") != "MOVE_DISTANCE"
            or reviewed.get("world_run_verified") is not False
            or reviewed.get("qualification_go") is not False
            or final_original_action.get("action") != handoff.action_id
            or final_original_action.get("source") != handoff.session_id
            or final_original_action.get("terminal") != "outcome"):
        raise BoundaryRejected("post-WAIT original/model handoff mismatch")
    evidence = final_original_action.get("execution_evidence")
    if not isinstance(evidence, dict):
        raise BoundaryRejected("final original Action evidence missing")
    native_after = evidence.get("after_observation")
    if not isinstance(native_after, dict):
        raise BoundaryRejected("original S49 terminal after-probe missing")
    action_last_seq = native_after.get("seq")
    if (type(action_last_seq) is not int or action_last_seq < 0
            or type(probe.seq) is not int
            or probe.seq <= action_last_seq
            or probe.session_id != handoff.session_id
            or probe.kind != "probe"
            or probe.request_id != expected_request_id
            or probe.provenance.source != "mineflayer"
            or probe.provenance.reference != (
                f"{handoff.session_id}:{probe.seq}"
            )
            or probe.snapshot.nearby_entities_coverage.truncated):
        raise BoundaryRejected("post-WAIT native probe is stale/foreign/uncorrelated")
    try:
        observation = project_body_present(project_mineflayer_present(probe))
        body = compose_self_body_view(
            session_id=handoff.session_id,
            self_id=handoff.after_wait.self_id,
            epoch_id=f"s49-postwait-native-{probe.seq}",
            observation=observation,
            hypotheses=handoff.after_wait.hypotheses,
            minimum_native_seq=action_last_seq + 1,
        )
    except InvalidSelfBodyData as exc:
        raise BoundaryRejected("native post-WAIT SelfBody composition invalid") from exc
    assert body.observation is not None
    result: dict[str, object] = {
        "status": "DEV_REAL_NATIVE_NEXT_COGNITION_INPUT",
        "source_scope": (
            "NATIVE_POSTWAIT_PRESENT_PLUS_P1_DEV_HYPOTHESIS"
            "_NO_PAPER_TICK_NATIVE_EQUIVALENCE"
        ),
        "session_id": handoff.session_id,
        "action_id": handoff.action_id,
        "paper_world": handoff.world,
        "observer_run_id": handoff.observer_run_id,
        "paper_window_sha256": handoff.model_source_digest,
        "epoch_id": body.epoch_id,
        "native_seq": probe.seq,
        "native_request_id": probe.request_id,
        "native_source_ref": observation.source_ref,
        "previous_action_after_probe_seq": action_last_seq,
        "native_health": body.observed("health").value,
        "native_food": body.observed("food").value,
        "native_position": (
            body.observed("position_x").value,
            body.observed("position_y").value,
            body.observed("position_z").value,
        ),
        "p1_dev_hypothesis_sensor_pct": body.hypothetical(
            MODEL, "p1_sensor_pct",
        ).value,
        "p1_dev_hypothesis_capability_pct": body.hypothetical(
            MODEL, "p1_capability_pct",
        ).value,
        "p1_dev_origin": BodyOrigin.HYPOTHESIS.value,
        "p1_native_sensor": body.sensed("p1_fatigue_sensor").value,
        "p1_native_observation": body.observed("p1_fatigue").value,
        "one_original_session_reader": True,
        "extra_native_probes": 1,
        "extra_action_issuers": 0,
        "real_next_l0_decision_consumed": False,
        "qualification_go": False,
        "science_go": False,
    }
    if (result["p1_native_sensor"] is not None
            or result["p1_native_observation"] is not None):
        raise BoundaryRejected("unattested P1 model promoted to native")
    return body, result
