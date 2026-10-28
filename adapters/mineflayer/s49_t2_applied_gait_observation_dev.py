"""G1 passive observed gait facts from the ORIGINAL admitted Paper/T1f stream.

This is a source-bound *candidate* observer, not a second P1 owner, an
Action motor, native packet ACK or full WorldTick gait certification.
A blocked commanded RUN cannot become observed WALK merely from 0m travel.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerPaperSnapshot

_CONTROLS = ("forward", "back", "left", "right", "jump", "sneak", "sprint")


@dataclass(frozen=True, slots=True)
class AppliedGaitObservationDev:
    """One passive Paper interval, NEVER a GaitTickDev transition."""

    session_id: str
    source_seq: int
    world_tick: int
    kind: str
    dxz_m: float | None
    paper_motion_blocks_delta: float | None
    paper_input_bits: int
    applied_controls: dict[str, bool]
    paper_gait: dict
    t2_activity: str | None
    full_tick_gait_attested: bool = False
    p1_transition_posted: bool = False
    m0_extra_charge_posted: bool = False


class G1AppliedGaitObserverDev:
    """A single bounded post-T2 consumer on one MineflayerProcessSession."""

    def __init__(self, session_id: str):
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("gait observer needs original session")
        self.session_id = session_id
        self.previous: MineflayerPaperSnapshot | None = None
        self.rows: list[AppliedGaitObservationDev] = []
        self.failed = False

    def observe(self, frame: MineflayerPaperSnapshot, *, t2_activity: str | None) -> None:
        try:
            self._observe(frame, t2_activity=t2_activity)
        except Exception:
            self.failed = True
            raise

    def _observe(self, frame: MineflayerPaperSnapshot, *, t2_activity: str | None) -> None:
        if (self.failed or not isinstance(frame, MineflayerPaperSnapshot)
                or frame.session_id != self.session_id
                or frame.data["status"] != "ADMITTED"):
            raise ValueError("G1_SOURCE_NOT_ADMITTED")
        s = frame.data["snapshot"]
        controls = frame.data.get("applied_controls_dev")
        gait = s.get("gait_dev")
        if (not isinstance(gait, dict) or not isinstance(controls, dict)
                or set(controls) != set(_CONTROLS)
                or not all(type(controls[k]) is bool for k in _CONTROLS)):
            raise ValueError("G1_ORIGINAL_PAPER_GAIT_FACTS_MISSING")
        if len(self.rows) >= 2400:
            raise ValueError("G1_BOUNDED_OBSERVER_EXHAUSTED")
        prior = self.previous
        dxz = delta = None
        kind = "INITIAL_NO_INTERVAL"
        if prior is not None:
            p = prior.data["snapshot"]
            if (frame.seq <= prior.seq
                    or any(s[k] != p[k] for k in ("boot", "world", "player"))
                    or any(s[k] != p[k] + 1 for k in ("world_tick", "tick", "index"))):
                raise ValueError("G1_PAPER_INTERVAL_DISCONTINUOUS")
            dxz = math.hypot(s["x"] - p["x"], s["z"] - p["z"])
            delta = s["motion_blocks"] - p["motion_blocks"]
            if delta < 0:
                raise ValueError("G1_MOTION_COUNTER_REVERSED")
            old_controls = prior.data.get("applied_controls_dev")
            old_gait = p.get("gait_dev")
            phase = frame.data["control"]
            old_phase = prior.data["control"]
            stable = (
                controls == old_controls
                and isinstance(old_gait, dict)
                and gait["sneaking"] == old_gait["sneaking"]
                and gait["sprinting"] == old_gait["sprinting"]
                and gait["speed_modifiers"] == old_gait["speed_modifiers"]
                and math.isclose(gait["speed_value"], old_gait["speed_value"], rel_tol=1e-6)
                and phase["phase"] == old_phase["phase"]
                and phase["generation"] == old_phase["generation"]
            )
            no_controls = not any(controls.values())
            forward = controls["forward"] and not any(
                controls[k] for k in _CONTROLS if k not in ("forward", "sprint", "sneak")
            )
            back = controls["back"] and not any(
                controls[k] for k in _CONTROLS if k != "back"
            )
            ordinary = (
                not gait["sprinting"] and not gait["sneaking"]
                and gait["speed_modifiers"] == 0
                and math.isclose(gait["speed_base"], 0.1, abs_tol=1e-6)
                and math.isclose(gait["speed_value"], 0.1, abs_tol=1e-6)
            )
            if (stable and no_controls and phase["phase"] in ("CLEARED", "INITIAL")
                    and s["input"] == p["input"] == 0
                    and dxz < 1e-9 and delta < 1e-9
                    and not gait["sprinting"] and not gait["sneaking"]):
                kind = "STABLE_PHYSICAL_IDLE_CANDIDATE"
            elif stable and phase["phase"] == "MOVING" and dxz > 1e-6 and delta > 0:
                if forward and not controls["sprint"] and not controls["sneak"] and ordinary:
                    kind = "STABLE_ORDINARY_FORWARD_CANDIDATE"
                elif back and ordinary:
                    kind = "STABLE_ORDINARY_BACK_CANDIDATE"
                elif (forward and controls["sprint"] and not controls["sneak"]
                        and gait["sprinting"] and gait["speed_value"] > gait["speed_base"]):
                    kind = "STABLE_SPRINT_FORWARD_CANDIDATE"
                elif (forward and controls["sneak"] and not controls["sprint"]
                        and gait["sneaking"]):
                    kind = "STABLE_SNEAK_FORWARD_CANDIDATE"
                else:
                    kind = "MOVING_MODE_UNDETERMINED"
            elif stable and (controls["forward"] or controls["back"]) and dxz < 1e-6:
                kind = "BLOCKED_OR_STALLED_CONTROL_UNDETERMINED"
            else:
                kind = "TRANSITION_OR_UNDETERMINED"
        self.rows.append(AppliedGaitObservationDev(
            session_id=self.session_id, source_seq=frame.seq,
            world_tick=s["world_tick"], kind=kind, dxz_m=dxz,
            paper_motion_blocks_delta=delta, paper_input_bits=s["input"],
            applied_controls=dict(controls), paper_gait=dict(gait),
            t2_activity=t2_activity,
        ))
        self.previous = frame
