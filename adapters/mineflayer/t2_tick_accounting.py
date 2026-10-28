"""S-owned DEV WorldTick -> existing M0/P1; no qualification/source promotion.

20 ticks = 1 reference World second. No target TPS parameter. M0 E is virtual,
separate from Paper M0.2 exhaustion. Costs below are explicit uncalibrated DEV
bridge units. P1 source is bounded callback/input evidence, not R full-tick proof.
"""
from __future__ import annotations

import math
from dataclasses import asdict, replace

from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from adapters.mineflayer.python_protocol import MineflayerPaperSnapshot
from experiments.fatigue_p1 import FatigueFrame, FatigueProfile, advance, initial_state
from experiments.metabolism_viability import MetabolismConfig
from experiments.p1_gait_dev import GaitTickDev, advance_gait_dev


class TickAccounting:
    def __init__(self, session_id, *, fatigue_profile: FatigueProfile | None = None,
                 gait_source=None):
        self.session_id = session_id
        self.energy = B0EnergyLedger(session_id, config=MetabolismConfig(
            basal_cost=.001, move_cost=.002, fight_cost=.01))
        if fatigue_profile is not None and not isinstance(fatigue_profile, FatigueProfile):
            raise TypeError("fatigue_profile must be an existing P1 profile")
        self.profile = fatigue_profile if fatigue_profile is not None else FatigueProfile(enabled=True)
        if gait_source is not None and not callable(gait_source):
            raise TypeError("gait_source must be a World-owner applied-gait callback")
        if gait_source is not None and (
            not self.profile.enabled
            or getattr(self.profile, "recovery_time_constant_world_seconds", None) is not None
        ):
            # Gait transition already contains its own mode-specific recovery.
            # Never mix the T1s 40s WAIT transition into this state.
            raise ValueError("single gait P1 requires enabled non-tau profile")
        self.gait_source = gait_source
        self.fatigue = None
        self.previous = None
        self.active_action = None
        self.clear_seq = None
        self.terminal_seq = None
        self.pending_meal = None
        self.rows = []
        self.failed = False
        self.gait_refusal = None

    def begin(self, action_id):
        if self.active_action is not None or self.failed:
            raise ValueError("prior motor/action not closed")
        self.active_action = action_id
        self.clear_seq = self.terminal_seq = None

    def finish(self, result, terminal):
        if result.action_id != self.active_action or terminal.action_id != self.active_action:
            raise ValueError("foreign epoch outcome")
        ack = result.cleanup_receipt
        if ack is None or ack.result != "applied" or ack.effect != "clear_controls":
            self.failed = True
            return
        self.clear_seq = ack.seq
        # Account only snapshots received AFTER the actual supervisor terminal.
        self.terminal_seq = max(ack.seq, result.after_observation.seq if result.after_observation else ack.seq)
        self.active_action = None

    def queue_meal(self, receipt):
        if self.pending_meal is not None:
            raise ValueError("uncredited previous meal")
        self.pending_meal = receipt

    def observe(self, frame):
        try:
            return self._observe(frame)
        except Exception:
            self.failed = True
            raise

    def _observe(self, frame):
        if not isinstance(frame, MineflayerPaperSnapshot) or frame.session_id != self.session_id:
            self.failed = True
            raise ValueError("foreign source")
        d, s = frame.data, frame.data["snapshot"]
        if d["status"] != "ADMITTED":
            if self.previous is not None:
                self.failed = True
            return
        if self.failed:
            raise ValueError("tick accounting latched after lost source")
        if self.previous is None:
            self.previous = frame
            self.fatigue = initial_state(self.profile, self.session_id, world_tick=s["world_tick"])
            return
        p, pd = self.previous.data["snapshot"], self.previous.data
        if (any(s[k] != p[k] for k in ("world", "player", "boot"))
                or s["world_tick"] != p["world_tick"] + 1 or s["tick"] != p["tick"] + 1
                or s["index"] != p["index"] + 1 or frame.seq <= self.previous.seq):
            self.failed = True
            raise ValueError("nonconsecutive T2 source; no invented zero/WAIT ticks")
        chord = math.dist([s[k] for k in ("x", "z")], [p[k] for k in ("x", "z")])
        blocks = s["motion_blocks"] - p["motion_blocks"]
        if (blocks < 0 or s["basal_ticks"] != p["basal_ticks"] + 1
                or s["basal_exhaustion"] < p["basal_exhaustion"]
                or s["motion_exhaustion"] < p["motion_exhaustion"]):
            self.failed = True
            raise ValueError("Paper metabolism counter discontinuity")
        phase = d["control"]
        old_phase = pd["control"]
        causal_clear = (
            self.active_action is None and self.clear_seq is not None
            and self.terminal_seq is not None and self.previous.seq > self.terminal_seq
            and phase["phase"] == old_phase["phase"] == "CLEARED"
            and phase["generation"] == old_phase["generation"]
            and int(pd["challenge_sent_ns"]) > int(old_phase["since_ns"])
            and int(d["challenge_sent_ns"]) > int(phase["since_ns"]))
        idle = (s["input"] == p["input"] == 0 and chord < 1e-9
                and abs(s["y"] - p["y"]) < 1e-9
                and s["motion_blocks"] == p["motion_blocks"])
        wait = causal_clear and idle and not s["threats"] and not p["threats"]
        # Unknown/blocked/clearing intervals NEVER recover. Feed MOVE with zero
        # measured displacement to preserve P1's consecutive clock, retaining
        # UNDETERMINED in the source ledger instead of calling it WAIT.
        activity = "WAIT" if wait else "MOVE"
        gait_tick = None
        physical_idle = False
        if self.gait_source is None:
            fatigue_step = advance(self.profile, self.fatigue, FatigueFrame(
                self.session_id, s["world_tick"], activity,
                observed_blocks=0 if wait else blocks,
                blocked=not wait and blocks < 1e-9))
        else:
            # T2 has already established the single admitted consecutive source.
            # Gait evidence is owned outside this ledger (S49/World); T2 does
            # not guess WALK, DASH, or recovery from a motor request alone.
            try:
                gait_tick = self.gait_source(frame, self.previous, wait)
                if isinstance(gait_tick, GaitTickDev) and wait and gait_tick.gait != "WAIT":
                    raise ValueError("applied gait disagrees with WAIT_DEV")
                if isinstance(gait_tick, GaitTickDev) and gait_tick.gait == "WAIT" and not wait:
                    # Rest of the *body* before an Action/clear is not a
                    # causally closed S49 WAIT. Do not mint WAIT_DEV credit.
                    from adapters.mineflayer.t1v_physical_idle_dev import physical_idle_witness_dev
                    physical_idle = physical_idle_witness_dev(frame, self.previous)
                if (not isinstance(gait_tick, GaitTickDev)
                        or gait_tick.session_id != self.session_id
                        or gait_tick.world_tick != s["world_tick"]
                        or (gait_tick.gait == "WAIT") != (wait or physical_idle)):
                    raise ValueError("applied gait missing, foreign or unproven body rest")
                # The existing Paper input bitmap can disprove obvious
                # contradictions, but it cannot independently authenticate
                # speed attributes, sprint or complete control state.
                if ((s["input"] == 2 and gait_tick.direction == "forward")
                        or (s["input"] == 1 and gait_tick.direction == "back")):
                    raise ValueError("applied gait direction contradicts Paper input")
                fatigue_step = advance_gait_dev(
                    self.profile, self.fatigue, gait_tick)
                if fatigue_step.added_m0_charge != 0:
                    # The existing M0 owner has no atomic DASH charge posting
                    # here. Do not adopt a charge proposal as paid energy.
                    raise ValueError("DASH extra M0 must be posted by existing owner")
            except Exception as error:
                self.failed = True
                self.gait_refusal = {
                    "classification": "UNDETERMINED", "source_seq": frame.seq,
                    "world_tick": s["world_tick"], "previous_source_seq": self.previous.seq,
                    "reason": str(error), "p1_updated": False, "m0_updated": False,
                }
                raise
        cognition = .0001  # one bounded L0 evaluation, symbolic bridge, not joules
        self.energy.config = replace(self.energy.config, basal_cost=.001 + cognition,
                                     move_cost=blocks * .002)
        meal = self.pending_meal
        if meal is not None and frame.seq <= meal.outcome.after_probe_seq:
            meal = None
        if meal is not None and (blocks > 1e-9 or chord > 1e-9 or self.active_action is not None):
            raise ValueError("meal credit requires stationary post-EAT source tick")
        energy_step = self.energy.step(
            "WAIT" if wait or physical_idle or meal else "MOVE", eating=meal)
        if meal is not None:
            self.pending_meal = None
        self.fatigue = fatigue_step.after
        row = {"session_id": self.session_id, "world": s["world"],
            "world_tick": s["world_tick"], "server_tick": s["tick"], "source_seq": frame.seq,
            "sim_seconds": 1 / 20, "activity": (
                "WAIT_DEV" if wait else "PHYSICAL_IDLE_DEV"
                if physical_idle else "MOVE_OR_UNDETERMINED"),
            "motor_mode": "WALK" if phase["phase"] == "MOVING" else "UNDETERMINED",
            "blocks_chord": chord, "native_motion_blocks": blocks, "active_action": self.active_action,
            "clear_seq": self.clear_seq, "terminal_seq": self.terminal_seq,
            "wait_causal_clear": causal_clear, "input_idle": idle,
            "m0_basal": .001, "m0_cognition": cognition,
            "l0_work_units": 1, "node_evaluation_ns": int(d["evaluation_completed_ns"]) - int(d["evaluation_start_ns"]),
            "m0_move": 0 if wait or meal else blocks * .002,
            "m0": asdict(energy_step), "p1": asdict(fatigue_step),
            "paper_basal_ticks": s["basal_ticks"],
            "paper_basal_exhaustion": s["basal_exhaustion"],
            "paper_motion_exhaustion": s["motion_exhaustion"],
            "full_tick_R_attested": False, "qualification": False}
        if gait_tick is not None:
            row["motor_mode"] = gait_tick.gait
            row.update(
                p1_transition="SINGLE_P1_APPLIED_GAIT_DEV",
                applied_gait=gait_tick.gait, applied_direction=gait_tick.direction,
                applied_dash_power=gait_tick.applied_dash_power,
                p1_gait_extra_m0_posted=False,
                gait_source_authenticated_R=False,
                physical_idle_model_only=physical_idle,
                qualified_physical_wait=False,
                gait_physical_idle_without_action_wait=physical_idle,
                gait_evidence={"source_seq": frame.seq,
                               "previous_source_seq": self.previous.seq,
                               "paper_input": s["input"],
                               "paper_gait_dev": s.get("gait_dev"),
                               "applied_controls_dev": d.get("applied_controls_dev"),
                               "world": s["world"], "player": s["player"], "boot": s["boot"]},
            )
        self.rows.append(row)
        self.previous = frame
