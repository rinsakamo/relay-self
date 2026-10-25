"""DEV-only third observed S49 MOVE -> P1 hypothesis -> same native Self views.

No second native receiver, new executor, S10 update, true fatigue telemetry, or
Paper/source-qualified World tick. The P1 model's post-WAIT zero starting
value must be independently checked against the earlier Paper replay when
the original S49 process report is finalized. This provisional DEV view
never grants an Action and never alters the frozen L0 choice.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_action_evidence import (
    NativeEvidenceRejected,
    verify_native_action_evidence,
)
from adapters.mineflayer.self_body_projection import project_body_present
from adapters.mineflayer.self_world_projection import project_self_world_present
from experiments.fatigue_p1 import (
    FatigueFrame,
    FatigueProfile,
    FatigueRejected,
    FatigueSensor,
    advance,
    capability,
    initial_state,
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
from relay_self.self_world import InvalidSelfWorldData, compose_self_world_view

MODEL = "p1-dev-distance-wait"
SCOPE = "THIRD_ORIGINAL_MOVE_DISTANCE_AFTER_PAPER_WAIT_DEV_MODEL_NOT_NATIVE"
SENSOR = FatigueSensor(gain=1.0, bias=0.0, quantum=0.01)


@dataclass(frozen=True, slots=True)
class ThirdMoveDevModel:
    third_action_id: str
    third_after_probe: MineflayerObservation
    body: SelfBodyView
    model_fatigue: float
    move_distance_m: float
    model_profile_sha256: str
    model_source_scope: str = SCOPE


def _native_view(probe: MineflayerObservation, hypotheses: tuple[BodyHypothesis, ...],
                 *, prior_seq: int, epoch: str) -> tuple[SelfBodyView, dict]:
    if (probe.provenance.source != "mineflayer"
            or probe.provenance.reference != f"{probe.session_id}:{probe.seq}"
            or probe.snapshot.nearby_entities_coverage.truncated
            or probe.seq <= prior_seq):
        raise BoundaryRejected("fresh original native probe required")
    try:
        present = project_mineflayer_present(probe)
        body = compose_self_body_view(
            session_id=probe.session_id, self_id="RelaySelf",
            epoch_id=epoch, observation=project_body_present(present),
            hypotheses=hypotheses, minimum_native_seq=prior_seq + 1,
        )
        world = compose_self_world_view(
            session_id=probe.session_id, self_id="RelaySelf",
            epoch_id=epoch,
            observation=project_self_world_present(present, observer_id="RelaySelf"),
            self_body=body,
        )
    except (InvalidSelfBodyData, InvalidSelfWorldData, TypeError, ValueError) as exc:
        raise BoundaryRejected("native SelfBody/SelfWorld projection rejected") from exc
    if (body.observation is None or world.observation is None
            or world.self_body is not body
            or body.observation.native_seq != probe.seq
            or world.observation.native_seq != probe.seq
            or body.observation.request_id != probe.request_id
            or world.observation.request_id != probe.request_id
            or body.observed("p1_fatigue").origin is not BodyOrigin.UNKNOWN
            or body.sensed("p1_fatigue_sensor").origin is not BodyOrigin.UNKNOWN
            or body.hypothetical(MODEL, "p1_phase").origin is not BodyOrigin.HYPOTHESIS):
        raise BoundaryRejected("P1 DEV hypothesis wrongly promoted into native view")
    return body, {
        "session_id": probe.session_id, "epoch_id": epoch,
        "native_seq": probe.seq, "request_id": probe.request_id,
        "selfworld_body_same_object": True,
        "native_health": body.observed("health").value,
        "native_food": body.observed("food").value,
        "p1_origin": "hypothesis",
        "p1_model_sensor_pct": body.hypothetical(MODEL, "p1_sensor_pct").value,
        "p1_model_capability_pct": body.hypothetical(MODEL, "p1_capability_pct").value,
        "p1_native_fatigue": None, "new_action_authority": False,
        "qualification_go": False, "science_go": False,
    }


def compose_third_move_native_dev(
    third_action: dict, third_probe: MineflayerObservation,
    *, previous_wait_native_seq: int,
) -> tuple[ThirdMoveDevModel, dict]:
    """Recheck original third native terminal and debit only that MOVE.

    A fatigue zero base here is a conditional DEV *model* continuation,
    verified later from the stored previous Paper WAIT replay. It is never
    permission to fill unobserved gaps with continuous physical WAIT.
    """
    if (not isinstance(third_action, dict)
            or not isinstance(third_probe, MineflayerObservation)
            or third_action.get("terminal") != "outcome"
            or third_action.get("source") != third_probe.session_id
            or not isinstance(third_action.get("action"), str)
            or not third_action["action"]
            or third_probe.kind != "probe"
            or third_probe.request_id != (
                f"s49-third-move:{third_probe.session_id}:{third_action['action']}"
            )
            or third_probe.seq <= previous_wait_native_seq):
        raise BoundaryRejected("third S49 Action or post-move native source invalid")
    evidence = third_action.get("execution_evidence")
    if not isinstance(evidence, dict):
        raise BoundaryRejected("third original Action evidence missing")
    try:
        verify_native_action_evidence(
            evidence, action_id=third_action["action"],
            session_id=third_probe.session_id,
            movement_m=third_action.get("movement_m"),
        )
    except (NativeEvidenceRejected, TypeError, ValueError) as exc:
        raise BoundaryRejected("third S49 execution receipt rejected") from exc
    native_after = evidence.get("after_observation")
    if (not isinstance(native_after, dict)
            or type(native_after.get("seq")) is not int
            or third_probe.seq <= native_after["seq"]):
        raise BoundaryRejected("third post-move correlated probe not later than native OUTCOME")
    profile = FatigueProfile(enabled=True, initial=0.0)
    try:
        transition = advance(
            profile,
            initial_state(profile, third_probe.session_id, world_tick=0),
            FatigueFrame(
                session_id=third_probe.session_id, world_tick=1,
                activity="MOVE", observed_blocks=third_action["movement_m"],
            ),
        )
        sensor = observe(profile, transition.after, SENSOR)
        cap = capability(profile, transition.after)
    except (FatigueRejected, TypeError, ValueError) as exc:
        raise BoundaryRejected("P1 third MOVE model rejected") from exc
    if (transition.before.fatigue != 0
            or transition.accumulated <= 0
            or transition.after.fatigue <= 0):
        raise BoundaryRejected("third MOVE must debit a nonzero P1 model fatigue")
    origin = Provenance(
        "p1-dev-third-move-model-not-native",
        f"{third_probe.session_id}:{third_action['action']}:{third_probe.seq}",
    )
    hypothesis = BodyHypothesis(
        MODEL,
        PredictionState(
            state_id=f"p1-dev-third-move-{third_action['action']}",
            variables=(
                StateVariable("p1_sensor_pct", int(round(sensor.reading * 100))),
                StateVariable("p1_capability_pct", int(round(cap.efficiency * 100))),
                StateVariable("p1_phase", "after-third-move"),
                StateVariable("p1_source_scope", SCOPE),
            ),
            provenance=origin,
            source_refs=(
                f"s49-closed-action:{third_probe.session_id}:{third_action['action']}",
                f"native-probe:{third_probe.session_id}:{third_probe.seq}",
            ),
            source_provenance=(origin,),
        ),
    )
    body, projected = _native_view(
        third_probe, (hypothesis,),
        prior_seq=native_after["seq"],
        epoch=f"s49-third-move-native-{third_probe.seq}",
    )
    model = ThirdMoveDevModel(
        third_action["action"], third_probe, body,
        transition.after.fatigue, third_action["movement_m"], profile.sha256,
    )
    return model, {
        **projected, "status": "DEV_THIRD_ORIGINAL_MOVE_P1_MODEL_SELF_VIEWS",
        "third_action_id": model.third_action_id,
        "movement_m": model.move_distance_m,
        "p1_model_fatigue_before": transition.before.fatigue,
        "p1_model_fatigue_after": transition.after.fatigue,
        "p1_model_fatigue_accumulated": transition.accumulated,
        "p1_profile_sha256": profile.sha256,
        "model_step_only": 1, "observed_move_world_tick": None,
        "continuous_world_tick_fatigue_history": False,
        "p1_model_prior_wait_zero_pending_report_review": True,
    }


def project_fifth_l0_view_dev(
    model: ThirdMoveDevModel, next_probe: MineflayerObservation,
) -> dict:
    """Read-only SelfBody/SelfWorld before same original host's L0 decide."""
    if (not isinstance(model, ThirdMoveDevModel)
            or not isinstance(next_probe, MineflayerObservation)
            or next_probe.session_id != model.third_after_probe.session_id
            or next_probe.kind != "probe"
            or not next_probe.request_id
            or not next_probe.request_id.startswith(
                f"s49-actual:{next_probe.session_id}:event-"
            )):
        raise BoundaryRejected("fifth L0 native probe not original host-owned")
    body, result = _native_view(
        next_probe, model.body.hypotheses,
        prior_seq=model.third_after_probe.seq,
        epoch=f"s49-fifth-native-{next_probe.seq}",
    )
    if (body.hypotheses != model.body.hypotheses
            or body.hypothetical(MODEL, "p1_phase").value != "after-third-move"):
        raise BoundaryRejected("fifth original L0 view lost prior P1 hypothesis")
    return {
        **result, "status": "DEV_FIFTH_NATIVE_SELF_WORLD_BODY_PROJECTED_PRE_L0",
        "third_action_id": model.third_action_id,
        "third_post_move_native_seq": model.third_after_probe.seq,
        "p1_model_fatigue": model.model_fatigue,
        "p1_model_profile_sha256": model.model_profile_sha256,
        "model_only": True,
        "original_l0_policy_consumes_p1": False,
        "original_l0_receives_same_native_probe": True,
        "projection_before_original_l0_decide": True,
    }
