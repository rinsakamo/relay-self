"""T1q: view-only M0/P1 interoception at the T1p native L0 boundary.

Reuse the exact #634 SelfBodyView type and existing B0/P1 sensor functions.
The owner retains exact energy/fatigue, authorization and World truth. Cognition
receives only quantized readings; projection never performs native IO or Action.
"""
from __future__ import annotations

from math import isfinite

from adapters.mineflayer.python_protocol import MineflayerPaperSnapshot
from adapters.mineflayer.t1p_body_runtime_dev import decide_l0, run_body_loop_dev
from adapters.mineflayer.t2_tick_accounting import TickAccounting
from experiments.fatigue_p1 import FatigueSensor
from experiments.fatigue_p1 import observe as sense_fatigue
from experiments.metabolism_viability import Interoception, observe_energy
from relay_self.provenance import Provenance
from relay_self.self_body import (
    BodyField,
    BodyInteroception,
    BodyObservation,
    BodyOrigin,
    InvalidSelfBodyData,
    SelfBodyView,
    compose_self_body_view,
)

# Only cognition-side sensor resolution; does not modify the physical P1 model.
M0_SENSOR = Interoception(quantum=0.25)
P1_SENSOR = FatigueSensor(quantum=0.01)


class T1qRejected(ValueError):
    """No view or Action may be credited for inconsistent source/Body lineage."""


def project_t1q_selfbody(
    frame: MineflayerPaperSnapshot, owner: TickAccounting, *, epoch_id: str,
) -> SelfBodyView:
    """Join one already admitted Paper frame to same-tick owner sensor readouts.

    Paper tick and B0 metabolism tick are distinct and remain separately
    addressable. No extra native receive is issued; this is producer-local DEV,
    not independently R-authenticated source or a qualified P1 WAIT witness.
    """
    if (not isinstance(frame, MineflayerPaperSnapshot)
            or not isinstance(owner, TickAccounting)
            or owner.failed or owner.previous is not frame
            or owner.session_id != frame.session_id
            or owner.energy.session_id != frame.session_id
            or frame.data["status"] != "ADMITTED"
            or owner.active_action is not None or owner.pending_meal is not None
            or owner.fatigue is None or not owner.rows and owner.energy.body.tick != 0):
        raise T1qRejected("no same-owner admitted native + live body boundary")
    source = frame.data["snapshot"]
    if (owner.fatigue.session_id != frame.session_id
            or owner.fatigue.world_tick != source["world_tick"]
            or owner.energy.body.tick != len(owner.rows)
            or not source["threats_complete"]
            or not isinstance(epoch_id, str) or not epoch_id
            or any(char.isspace() for char in epoch_id)):
        raise T1qRejected("World/P1/M0 tick or view identity mismatch")
    # native seq and Paper World tick are different clocks.
    native = Provenance(
        "paper-t1f-native-dev",
        f"{frame.session_id}:{frame.seq}:{source['index']}:{source['world_tick']}",
    )
    request_id = f"paper-index-{source['index']}"
    observed = BodyObservation(
        session_id=frame.session_id,
        native_seq=frame.seq,
        request_id=request_id,
        fields=(
            BodyField("position_x", source["x"]),
            BodyField("position_y", source["y"]),
            BodyField("position_z", source["z"]),
            BodyField("health", source["health"]),
            BodyField("food", source["food"]),
        ),
        source_provenance=native,
    )
    m0 = observe_energy(owner.energy.body, M0_SENSOR)
    p1 = sense_fatigue(owner.profile, owner.fatigue, P1_SENSOR)
    if (m0.tick != owner.energy.body.tick
            or p1.world_tick != source["world_tick"]
            or not isfinite(m0.reading) or not isfinite(p1.reading)):
        raise T1qRejected("owner readout tick/value mismatch")
    interoceptions = (
        BodyInteroception(
            BodyField("m0_energy_sensor", m0.reading),
            frame.session_id, frame.seq, request_id, native, m0.tick,
            Provenance("m0-b0-producer-local-dev", f"{frame.session_id}:m0:{m0.tick}"),
        ),
        BodyInteroception(
            BodyField("p1_fatigue_sensor", p1.reading),
            frame.session_id, frame.seq, request_id, native, p1.world_tick,
            Provenance("p1-original-model-producer-local-dev",
                       f"{frame.session_id}:world:{p1.world_tick}"),
        ),
    )
    try:
        return compose_self_body_view(
            session_id=frame.session_id, epoch_id=epoch_id,
            observation=observed,
            minimum_native_seq=frame.seq, interoceptions=interoceptions,
        )
    except InvalidSelfBodyData as exc:
        raise T1qRejected("SelfBody composition rejected owner inputs") from exc


def decide_sensed_l0(view: SelfBodyView, *, host_decision: str) -> str:
    """Sensor may restrict a move but cannot override the original host gate."""
    if host_decision != "MOVE":
        return host_decision
    if not isinstance(view, SelfBodyView):
        raise T1qRejected("missing typed SelfBody view")
    energy = view.sensed("m0_energy_sensor")
    fatigue = view.sensed("p1_fatigue_sensor")
    if (energy.origin is not BodyOrigin.INTEROCEPTION
            or fatigue.origin is not BodyOrigin.INTEROCEPTION
            or type(energy.value) not in (int, float)
            or type(fatigue.value) not in (int, float)
            or not isfinite(energy.value) or not isfinite(fatigue.value)
            or energy.value < 0 or fatigue.value < 0
            or not energy.source_refs or not fatigue.source_refs):
        # UNKNOWN is allowed as a view state but cannot authorize a new move.
        return "HALT"
    if energy.value <= 3.0:
        return "HALT"
    if fatigue.value >= 0.05:
        return "HOLD_BODY"
    return "MOVE"


def cognition_summary(view: SelfBodyView, *, native_seq: int, world_tick: int,
                      host_decision: str, sensed_decision: str) -> dict:
    """No exact M0/P1 true state, imaginary capability, or Action permit."""
    energy = view.sensed("m0_energy_sensor")
    fatigue = view.sensed("p1_fatigue_sensor")
    health = view.observed("health")
    food = view.observed("food")
    return {
        "epoch_id": view.epoch_id, "native_seq": native_seq,
        "world_tick": world_tick, "paper_clock_kind": "WORLD_FULL_TIME",
        "m0_clock_kind": "B0_LEDGER_TICKS",
        "body_session_id": view.session_id,
        "energy_origin": energy.origin.value, "energy_sensed": energy.value,
        "fatigue_origin": fatigue.origin.value, "fatigue_sensed": fatigue.value,
        "health_origin": health.origin.value, "health_observed": health.value,
        "food_origin": food.origin.value, "food_observed": food.value,
        "energy_source_refs": energy.source_refs,
        "fatigue_source_refs": fatigue.source_refs,
        "host_decision": host_decision, "sensed_decision": sensed_decision,
        "physical_permission_from_view": False,
        "p1_qualified_wait": False,
    }


async def run_t1q_body_loop_dev(session, report, *, move_limit=2):
    """Use T1p original execution once; insert only read-only L0 cognition."""
    records = []
    report["t1q"] = {
        "classification": "T1Q_INTEROCEPTION_PRODUCER_LOCAL_DEV_ONLY",
        "selfbody_source_head": "PR634_TYPED_VIEW_STAGED_EXACT_BLOB",
        "readings": records, "additional_native_reads": 0,
        "additional_actions": 0, "model_calls": 0,
        "physical_permission_from_view": False,
    }

    def choose(frame, owner, *, completed, limit):
        host = decide_l0(frame, owner, completed=completed, limit=limit)
        if host in ("HALT", "COMPLETE"):
            return host
        view = project_t1q_selfbody(frame, owner, epoch_id=f"t1q-epoch-{completed}")
        choice = decide_sensed_l0(view, host_decision=host)
        records.append(cognition_summary(
            view, native_seq=frame.seq,
            world_tick=frame.data["snapshot"]["world_tick"],
            host_decision=host, sensed_decision=choice,
        ))
        return choice

    await run_body_loop_dev(
        session, report, move_limit=move_limit, l0_decider=choose,
    )
    report["t1q"]["completed_moves"] = report["t1p"].get("completed_moves", 0)
    report["t1q"]["decision_count"] = len(records)
    return report["t1q"]
