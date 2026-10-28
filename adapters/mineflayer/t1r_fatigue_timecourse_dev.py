"""T1r — same native reader, full M0/P1 tick, passive SelfBody fatigue timeline.

A read-only 'prefer rest' is not an S49 Motor command, STOP, WAIT qualification,
or a new permission. Original T1q L0 decisions and T1p Executor stay unchanged.
"""
from __future__ import annotations

from math import isfinite

from adapters.mineflayer.t1q_interoception_dev import (
    M0_SENSOR, P1_SENSOR, cognition_summary, project_t1q_selfbody,
    run_t1q_body_loop_dev,
)
from adapters.mineflayer.t2_tick_accounting import TickAccounting
from adapters.mineflayer.python_protocol import MineflayerPaperSnapshot
from experiments.fatigue_p1 import FatigueState, observe as observe_p1
from experiments.metabolism_viability import BodyState, observe_energy
from relay_self.self_body import BodyOrigin

MAX_PASSIVE_TICKS = 240
# DEV introspective preference only; not an original Action permission or
# validated physiology threshold. Existing T1q MOVE gate remains unchanged.
REST_SENSE_THRESHOLD = 0.02


class T1rRejected(ValueError):
    """Refuse stale, aliased or forged passive SelfBody/World-time samples."""


def sensed_rest_preference(view) -> str:
    """One bounded cognition-side preference, never issue/clear a Motor effect."""
    energy = view.sensed("m0_energy_sensor")
    fatigue = view.sensed("p1_fatigue_sensor")
    if (energy.origin is not BodyOrigin.INTEROCEPTION
            or fatigue.origin is not BodyOrigin.INTEROCEPTION
            or type(energy.value) not in (int, float)
            or type(fatigue.value) not in (int, float)
            or not isfinite(energy.value) or not isfinite(fatigue.value)
            or energy.value < 0 or fatigue.value < 0):
        return "UNKNOWN_HOLD"
    if energy.value <= 3.0:
        return "REST_PREFERRED"
    if fatigue.value >= REST_SENSE_THRESHOLD:
        return "REST_PREFERRED"
    return "READY_FEELING"


def capture_passive_tick(frame, owner, readings):
    """Read exactly one newly-accounted original Paper frame; zero native IO."""
    if (not isinstance(frame, MineflayerPaperSnapshot)
            or not isinstance(owner, TickAccounting)
            or type(readings) is not list
            or not owner.rows or owner.previous is not frame
            or len(readings) >= MAX_PASSIVE_TICKS):
        raise T1rRejected("no fresh or bounded owner-local tick for passive view")
    row = owner.rows[-1]
    source = frame.data["snapshot"]
    if (frame.session_id != owner.session_id
            or row["session_id"] != frame.session_id
            or row["source_seq"] != frame.seq
            or row["world_tick"] != source["world_tick"]
            or len(readings) and source["world_tick"] <= readings[-1]["world_tick"]):
        raise T1rRejected("source/ledger/clock lineage mismatch")
    view = project_t1q_selfbody(
        frame, owner, epoch_id=f"t1r-world-{source['world_tick']}",
        passive_during_action=True,
    )
    # This is a perception at a physical World tick, including in-flight
    # Action ticks; it cannot authorize, end, or mutate that Action.
    snapshot = cognition_summary(
        view, native_seq=frame.seq, world_tick=source["world_tick"],
        host_decision="NOT_EVALUATED_DURING_PASSIVE_SAMPLE",
        sensed_decision="NO_MOTOR_DECISION",
    )
    snapshot.update(
        m0_tick=owner.energy.body.tick,
        original_action_open=owner.active_action is not None,
        original_action_id=owner.active_action,
        original_activity=row["activity"],
        sensed_rest_preference=sensed_rest_preference(view),
    )
    readings.append(snapshot)
    return snapshot


def audit_t1r_trace(readings, owner, *, completed_moves):
    """Independently replay original per-tick owner accounting into sensors.

    True M0/P1 is read *only* by this external verifier; the SelfBody trace
    contains the already-projected interoception but no true host ledger.
    """
    if (type(completed_moves) is not int or completed_moves < 2
            or not isinstance(owner, TickAccounting)
            or not isinstance(readings, list)
            or len(readings) != len(owner.rows)
            or len(readings) < completed_moves):
        raise T1rRejected("unmatched original owner tick/sensor stream")
    rest = ready = observed_fatigue = 0
    first_fatigue_rest_tick = None
    recovered_ready_tick = None
    saw_wait_recovery = False
    for index, (rec, row) in enumerate(zip(readings, owner.rows, strict=True)):
        if (rec.get("native_seq") != row["source_seq"]
                or rec.get("world_tick") != row["world_tick"]
                or rec.get("m0_tick") != index + 1
                or rec.get("body_session_id") != row["session_id"]
                or rec.get("energy_origin") != "interoception"
                or rec.get("fatigue_origin") != "interoception"
                or rec.get("physical_permission_from_view") is not False
                or rec.get("p1_qualified_wait") is not False
                or rec.get("original_activity") != row["activity"]
                or rec.get("original_action_id") != row["active_action"]
                or rec.get("original_action_open") is not (row["active_action"] is not None)
                or not rec.get("energy_source_refs")
                or not rec.get("fatigue_source_refs")):
            raise T1rRejected("false or ungrounded SelfBody per-tick sensor")
        # The original TickAccounting's full ledger provides an independent
        # DEV reconstruction. Never read future state to construct the view.
        m0 = BodyState(**row["m0"]["after"])
        p1 = FatigueState(**row["p1"]["after"])
        if (observe_energy(m0, M0_SENSOR).reading != rec["energy_sensed"]
                or observe_p1(owner.profile, p1, P1_SENSOR).reading
                != rec["fatigue_sensed"]):
            raise T1rRejected("SelfBody sensor differs from original ledger")
        expected_preference = (
            "REST_PREFERRED"
            if rec["energy_sensed"] <= 3.0
            or rec["fatigue_sensed"] >= REST_SENSE_THRESHOLD
            else "READY_FEELING"
        )
        if rec.get("sensed_rest_preference") != expected_preference:
            raise T1rRejected("reported perceptual choice contradicts sensed inputs")
        if row["p1"]["accumulated"] > 0:
            observed_fatigue += 1
        if row["activity"] == "WAIT_DEV" and row["p1"]["recovered"] > 0:
            saw_wait_recovery = True
        if rec.get("sensed_rest_preference") == "REST_PREFERRED":
            rest += 1
            if rec["fatigue_sensed"] >= REST_SENSE_THRESHOLD:
                if first_fatigue_rest_tick is None:
                    first_fatigue_rest_tick = rec["world_tick"]
        elif rec.get("sensed_rest_preference") == "READY_FEELING":
            ready += 1
            if (first_fatigue_rest_tick is not None and saw_wait_recovery
                    and rec["world_tick"] > first_fatigue_rest_tick):
                recovered_ready_tick = rec["world_tick"]
        else:
            raise T1rRejected("unexpected/unknown perception in successful run")
    return {
        "source_bound_tick_samples": len(readings),
        "rest_preferred_samples": rest,
        "ready_feeling_samples": ready,
        "original_fatigue_accumulation_ticks": observed_fatigue,
        "first_fatigue_rest_tick": first_fatigue_rest_tick,
        "recovered_ready_tick": recovered_ready_tick,
        "observed_change_in_sensed_preference": bool(
            first_fatigue_rest_tick is not None
            and recovered_ready_tick is not None and observed_fatigue
        ),
        "physical_action_permission_from_sensor": False,
        "original_p1_qualified_wait": False,
        "classification": (
            "T1R_PASSIVE_PERCEPTUAL_SHIFT_OBSERVED_DEV"
            if first_fatigue_rest_tick is not None
            and recovered_ready_tick is not None and observed_fatigue
            else "T1R_PASSIVE_SENSOR_TIMECOURSE_WITHOUT_SHIFT_DEV"
        ),
    }


async def run_t1r_body_recovery_dev(session, report, *, move_limit=2):
    """T1q 2-epoch Action unchanged; passive callback on the same T1e reader."""
    if getattr(session, "passive_body_tick_observer", None) is not None:
        raise T1rRejected("a passive sensor observer is already installed")
    readings = []
    report["t1r"] = {
        "classification": "T1R_UNFORCED_PASSIVE_BODY_TIMECOURSE_DEV",
        "readings": readings,
        "additional_native_receivers": 0,
        "additional_action_issuers": 0,
        "extra_motor_commands": 0,
        "physical_permission_from_view": False,
        "threshold_status": "DESIGNED_DEV_NOT_PHYSIOLOGY",
    }

    def on_tick(frame, owner):
        capture_passive_tick(frame, owner, readings)

    # Scope the observer strictly to original T1q runner. If it fails, the
    # original T1e owner handles physical cleanup and records the FAIL.
    session.passive_body_tick_observer = on_tick
    try:
        await run_t1q_body_loop_dev(session, report, move_limit=move_limit)
    finally:
        session.passive_body_tick_observer = None
    if report.get("status") != "PASS":
        return report["t1r"]
    audit = audit_t1r_trace(
        readings, session.tick_owner,
        completed_moves=report["t1q"]["completed_moves"],
    )
    report["t1r"]["audit"] = audit
    # Do not reinterpret absence of a visible preference shift as success
    # in this specific T1r DEV trial, but retain all real source/Action proof.
    if not audit["observed_change_in_sensed_preference"]:
        report["status"] = "FAIL"
    return report["t1r"]
