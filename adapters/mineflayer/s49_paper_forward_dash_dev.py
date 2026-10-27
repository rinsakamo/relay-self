"""Disposable original S49 forward+sprint Action and Paper positive DASH DEV.

The original S49 qualify() owns the ONLY Action issuer and Mineflayer reader.
This wrapper merely supplies an explicitly pinned Paper binary, one opt-in
Paper modifier, and passive logs around an ALREADY ISSUED S49 Action.
No output here authenticates a Paper-to-Node tick edge or posts P1/M0.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import shutil
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from adapters.mineflayer import normal_action as action_owner
from adapters.mineflayer import s49_normal_session_real_ci as original
from adapters.mineflayer.b0_energy_bridge import DashM0InvoiceDev
from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import _fresh_asset
from adapters.mineflayer.s49_causal_wait_fence_dev import (
    review_original_owner_causal_paper_fence_dev,
)
from adapters.mineflayer.s49_inter_action_stillness_dev import (
    review_inter_action_stillness_dev,
    review_original_owner_no_issued_action_gap_dev,
)
from adapters.mineflayer.s49_m0_world_time_shadow_dev import (
    M0WorldRateDev,
    project_s49_world_time_m0_shadow_dev,
)
from adapters.mineflayer.s49_node_physics_postclear_dev import (
    NativePhysicsTraceRejected,
    audit_node_paper_motion_fingerprint_dev,
    audit_node_physics_postclear_dev,
)
from adapters.mineflayer.s49_p1_dev_wait_observed import (
    replay_p1_observed_static_wait_dev,
)
from adapters.mineflayer.s49_p1_fenced_recovery_shadow_dev import (
    project_p1_fenced_wait_shadow_dev,
)
from adapters.mineflayer.s49_p1_native_l0_comparison_dev import (
    review_next_native_p1_l0_comparison_dev,
)
from adapters.mineflayer.s49_p1_selfbody_epoch_shadow_dev import (
    project_p1_static_next_body_epoch_dev,
)
from adapters.mineflayer.s49_paper_world_first_dev import (
    _await_dash_dev_line,
    _fresh_output,
    offline_uuid,
)
from adapters.mineflayer.s49_speed_attr_boundary_dev import (
    review_speed_attr_boundary_dev,
)
from adapters.mineflayer.s49_two_action_world_timeline_dev import (
    review_two_action_world_timeline_dev,
)
from adapters.mineflayer.self_action_evidence import capture_native_action_evidence
from experiments.fatigue_p1 import FatigueProfile, initial_state
from experiments.p1_gait_dev import (
    GaitTickDev,
    advance_gait_dev,
    p1_motor_power_limit_dev,
)

CONFIRM = "S49-P1-DEV-DISPOSABLE-PAPER-WORLD"
# Earlier *model*, not observed P1 Body. Frozen from World #40476376338.
PAIR_FATIGUE = {"CARRY": 0.6177122410202606, "WAIT_ASSUMED": 0.21616083122103735}
PAIR_SOURCE_DIGEST = "f126d16f42caa27230a02e4c818d7b7ae3c1d2e39e8ad75c55cd2ce9ddc16bd4"


class ForwardDashDevRejected(RuntimeError):
    pass


def evaluate_native_dash_gain_dev(
    *, armed_m: float, unarmed_m: float, peak_mps: float | None,
    boost_ticks: int,
) -> dict:
    """Require native displacement and Paper velocity, not modifier presence."""
    if (any(type(value) not in (int, float) or not math.isfinite(value)
            for value in (armed_m, unarmed_m))
            or type(boost_ticks) is not int or boost_ticks < 1
            or type(peak_mps) not in (int, float)
            or not math.isfinite(peak_mps)
            or armed_m < 0.05 or unarmed_m < 0.05):
        raise ForwardDashDevRejected("native DASH gain inputs absent or nonfinite")
    delta = armed_m - unarmed_m
    # Conservative DEV smoke gate; NOT a calibration or terminal speed cap.
    if delta < 0.40 or peak_mps < 7.5:
        raise ForwardDashDevRejected("Paper attribute on, but native DASH gain absent")
    return {
        "native_displacement_gain_m": delta,
        "native_gain_observed_dev": True,
        "paper_sampled_peak_mps": peak_mps,
        "uncontrolled_single_world_comparison": True,
        "speed_cap_or_direction_qualified": False,
    }


def audit_native_paper_p1_dev(raw: str, *, action_id: str, session_id: str,
                              model_initial: float = 0.6) -> dict:
    """Independently replay Paper World callbacks against existing single P1.

    Paper's motor outcome is DEV evidence only; host custody of every actual
    World tick and P1/M0 ledger authorization are not inferred.
    """
    rows = []
    for line in raw.splitlines():
        if "S49_DASH_DEV_TICK " not in line:
            continue
        data = dict(t.split("=", 1)
                    for t in line.split("S49_DASH_DEV_TICK ", 1)[1].split()
                    if t.count("=") == 1)
        if data.get("action_id") != action_id:
            continue
        if data.get("session_id") != session_id or data.get("p1_motor_dev") != "true":
            raise ForwardDashDevRejected("foreign/non-P1 Paper tick")
        rows.append(data)
    if len(rows) < 5:
        raise ForwardDashDevRejected("too few P1 Paper ticks")
    if (type(model_initial) is not float
            or model_initial not in (0.6, *PAIR_FATIGUE.values())):
        raise ForwardDashDevRejected("unadmitted P1 preload state")
    cfg = FatigueProfile(enabled=True, initial=model_initial)
    state = initial_state(cfg, session_id)
    prev_power = 0.0
    last_world = None
    proposed_m0 = 0.0
    boosts = []
    for i, line in enumerate(rows, 1):
        try:
            world = int(line["tick"])
            index = int(line["p1_world_ticks"])
            before = float(line["p1_before"])
            after = float(line["p1_after"])
            prev = float(line["p1_prev_applied_power"])
            output = float(line["p1_current_applied_power"])
        except (KeyError, ValueError) as exc:
            raise ForwardDashDevRejected("malformed P1 World tick") from exc
        if (index != i or world <= 0
                or (last_world is not None and world != last_world + 1)
                or not all(math.isfinite(v) for v in (before, after, prev, output))
                or not math.isclose(prev_power, prev, abs_tol=2e-10)
                or not math.isclose(state.fatigue, before, abs_tol=2e-10)):
            raise ForwardDashDevRejected("P1 state / World tick continuity violation")
        result = advance_gait_dev(
            cfg, state,
            GaitTickDev(session_id, i,
                        "DASH" if prev_power > 0 else "RUN", "forward",
                        prev_power, 1.0 if prev_power > 0 else None),
        )
        if not math.isclose(result.after.fatigue, after, abs_tol=2e-10):
            raise ForwardDashDevRejected("Paper fatigue is not one-P1 transition")
        state = result.after
        proposed_m0 += result.added_m0_charge
        requested = p1_motor_power_limit_dev(cfg, state, 1.0, 1.0)
        if (line.get("modifier_applied") not in ("true", "false")
                or not math.isclose(
                    output, requested if line["modifier_applied"] == "true" else 0.0,
                    abs_tol=2e-10,
                )):
            raise ForwardDashDevRejected("Paper output does not obey single P1 bound")
        if output > 0:
            boosts.append(output)
        prev_power = output
        last_world = world
    if len(boosts) < 3:
        raise ForwardDashDevRejected("P1 forward boost never observed")
    if model_initial > 0.5 and boosts[0] - boosts[-1] < 0.01:
        raise ForwardDashDevRejected("high-fatigue P1 fade unobserved")
    if model_initial < 0.5 and (state.fatigue >= 0.5 or
                                not all(math.isclose(v, 1.0, abs_tol=1e-10) for v in boosts)):
        raise ForwardDashDevRejected("low-fatigue full power DEV plateau mismatch")
    return {
        "world_ticks_replayed": len(rows),
        "fatigue_initial": cfg.initial,
        "fatigue_final": state.fatigue,
        "initial_boost_power": boosts[0],
        "last_boost_power": boosts[-1],
        "actual_power_fade": boosts[0] - boosts[-1],
        "m0_charge_proposal_not_posted": proposed_m0,
        "single_p1_model_replayed": True,
        "source_qualified": False,
        "p1_ledger_posted": False,
        "m0_ledger_posted": False,
    }


def review_paper_action_bracket_dev(raw: str, *, action_id: str, session_id: str) -> dict:
    """Paper-only arm/tick/release custody; NOT a cross-host clock attestation."""
    groups = {"ARM": [], "TICK": [], "COMPLETE": []}
    for line in raw.splitlines():
        for kind in groups:
            mark = "S49_DASH_DEV_" + kind + " "
            if mark not in line:
                continue
            fields = dict(t.split("=", 1) for t in line.split(mark, 1)[1].split()
                          if t.count("=") == 1)
            if fields.get("action_id") == action_id:
                if fields.get("session_id") != session_id:
                    raise ForwardDashDevRejected("Paper cross-session Action bracket")
                groups[kind].append(fields)
            break
    arm, rows, stop = groups["ARM"], groups["TICK"], groups["COMPLETE"]
    if len(arm) != 1 or len(stop) != 1 or not 5 <= len(rows) <= 80:
        raise ForwardDashDevRejected("missing/duplicated Paper Action bracket")
    start, release = arm[0], stop[0]
    try:
        arm_tick = int(start["tick"])
        release_tick = int(release["tick"])
    except (ValueError, KeyError) as exc:
        raise ForwardDashDevRejected("malformed Paper start/release tick") from exc
    world, player = start.get("world"), start.get("player_uuid")
    if (not isinstance(world, str) or len(world) != 36
            or not isinstance(player, str) or len(player) != 36
            or release.get("reason") != "OWNER_RELEASE"
            or release.get("world") != world or release.get("player_uuid") != player
            or release_tick < arm_tick or release_tick - arm_tick > 80):
        raise ForwardDashDevRejected("Paper owner/world/release changed")
    prior = arm_tick
    positives = 0
    for fields in rows:
        try:
            tick = int(fields["tick"])
        except (ValueError, KeyError) as exc:
            raise ForwardDashDevRejected("invalid Paper observed tick") from exc
        if (fields.get("world") != world or fields.get("player_uuid") != player
                or tick != prior + 1 or tick > release_tick
                or fields.get("modifier_applied") not in ("true", "false")):
            raise ForwardDashDevRejected("Paper duplicated/foreign/gapped World tick")
        positives += fields["modifier_applied"] == "true"
        prior = tick
    if (not 0 <= release_tick - prior <= 20 or positives < 1
            or int(release.get("forward_boost_ticks", "-1")) != positives):
        raise ForwardDashDevRejected("Paper boost count or release delay mismatch")
    return {
        "classification": "PAPER_LOCAL_ARM_TICK_RELEASE_BRACKET_DEV_ONLY",
        "action_id": action_id, "session_id": session_id,
        "world_uuid": world, "player_uuid": player,
        "arm_tick": arm_tick, "first_tick": arm_tick + 1,
        "last_tick": prior, "release_tick": release_tick,
        "elapsed_callbacks": len(rows), "boosted_callbacks": positives,
        "original_owner_release": True,
        "independent_source_attested": False,
        "mineflayer_paper_tick_synchronized": False,
    }


def review_original_s49_native_effect_edges_dev(
    raw: str, *, action_id: str, session_id: str, native_evidence: dict,
    bracket: dict,
) -> dict:
    """Join native typed ACKs to Paper marker *delivery* time, not effect time.

    Both receipts were consumed in the ORIGINAL S15 reader. The owner writes
    Paper timestamps only AFTER receiving each ACK. Hence their World tick
    values are upper bounds on operator receipt/marker delivery; no clock
    synchronization, native effect tick, or packet timestamp is attested.
    """
    found = []
    for row in raw.splitlines():
        tag = "S49_DASH_DEV_EDGE "
        if tag not in row:
            continue
        fields = dict(
            token.split("=", 1) for token in row.split(tag, 1)[1].split()
            if token.count("=") == 1
        )
        if fields.get("action_id") == action_id:
            found.append(fields)
    if (len(found) != 2
            or [x.get("phase") for x in found] != ["APPLIED", "CLEARED"]
            or bracket.get("action_id") != action_id
            or bracket.get("session_id") != session_id
            or not bracket.get("original_owner_release")
            or bracket.get("independent_source_attested") is not False
            or type(native_evidence) is not dict
            or native_evidence.get("action_id") != action_id
            or native_evidence.get("session_id") != session_id
            or native_evidence.get("action_ref") != "MOVE_FORWARD_SPRINT_DEV"
            or native_evidence.get("status") != "executed"):
        raise ForwardDashDevRejected("native effect markers missing or foreign")
    receipts = [
        native_evidence.get("dispatch_receipt"),
        native_evidence.get("cleanup_receipt"),
    ]
    if any(type(x) is not dict for x in receipts):
        raise ForwardDashDevRejected("original S49 typed ACK receipts absent")
    times = []
    for i, row in enumerate(found):
        receipt = receipts[i]
        try:
            native_seq = int(row["native_seq"])
            paper_tick = int(row["tick"])
        except (ValueError, KeyError, TypeError) as exc:
            raise ForwardDashDevRejected("invalid native/Paper ACK lineage") from exc
        if (row.get("session_id") != session_id
                or row.get("world") != bracket["world_uuid"]
                or row.get("player_uuid") != bracket["player_uuid"]
                or row.get("marker_after_native_ack") != "true"
                or row.get("synchronized_native_effect_tick") != "false"
                or native_seq != receipt.get("seq")
                or str(native_seq) != row["native_seq"]
                or receipt.get("session_id") != session_id
                or receipt.get("result") != "applied"
                or receipt.get("effect") != (
                    "set_forward_sprint_dev" if i == 0 else "clear_controls"
                )
                or receipt.get("action_id") != (
                    action_id if i == 0 else action_id + "-s15-clear"
                )
                or paper_tick < bracket["arm_tick"]
                or paper_tick > bracket["release_tick"]):
            raise ForwardDashDevRejected("Paper marker not same original native ACK")
        times.append(paper_tick)
    if (receipts[1]["seq"] <= receipts[0]["seq"]
            or times[1] < times[0]):
        raise ForwardDashDevRejected("native dispatch/cleanup ACK order inverted")
    elapsed_in_bracket = max(
        0, min(bracket["last_tick"], times[1])
        - max(bracket["first_tick"], times[0]) + 1,
    )
    # An after-ACK marker alone is NOT movement evidence. Require at least
    # one actual Paper speed-boost callback inside the bounded marker window
    # before original S49 can settle any corresponding M0 DASH invoice.
    boosted_inside = 0
    for line in raw.splitlines():
        marker = "S49_DASH_DEV_TICK "
        if marker not in line:
            continue
        fields = dict(
            token.split("=", 1) for token in line.split(marker, 1)[1].split()
            if token.count("=") == 1
        )
        if fields.get("action_id") != action_id:
            continue
        if fields.get("session_id") != session_id:
            raise ForwardDashDevRejected("Paper boost callback foreign session")
        try:
            tick = int(fields["tick"])
        except (ValueError, KeyError, TypeError) as exc:
            raise ForwardDashDevRejected("malformed Paper native ACK callback tick") from exc
        if (times[0] <= tick <= times[1]
                and fields.get("modifier_applied") == "true"):
            boosted_inside += 1
    if elapsed_in_bracket < 1 or boosted_inside < 1:
        raise ForwardDashDevRejected("native ACK marker window has no physical DASH callback")
    return {
        "classification": "S49_NATIVE_ACK_TO_PAPER_MARKER_DELIVERY_DEV_ONLY",
        "action_id": action_id, "session_id": session_id,
        "native_dispatch_ack_seq": receipts[0]["seq"],
        "native_cleanup_ack_seq": receipts[1]["seq"],
        "paper_dispatch_ack_marker_tick": times[0],
        "paper_cleanup_ack_marker_tick": times[1],
        "paper_sample_ticks_within_marker_window": elapsed_in_bracket,
        "boosted_paper_callbacks_inside_ack_marker_window": boosted_inside,
        "paper_arm_tick": bracket["arm_tick"],
        "paper_release_tick": bracket["release_tick"],
        "native_single_reader": True,
        "marker_after_native_ack": True,
        "client_effect_world_tick_attested": False,
        "cross_host_clock_synchronized": False,
        "independent_source_attested": False,
    }


def review_post_release_motion_dev(
    raw: str, *, action_id: str, session_id: str, bracket: dict, edges: dict,
) -> dict:
    """Conservative Paper translation witness through five post-release ticks.

    Not a client's control bit or L0 WAIT. A post-release translation may be
    inertia, packet timing, or another cause; the plugin never changes speed,
    P1, M0 or the original S49 Action in this passive window.
    """
    rows = []
    for line in raw.splitlines():
        tag = "S49_DASH_DEV_POST_RELEASE "
        if tag not in line:
            continue
        fields = dict(t.split("=", 1) for t in line.split(tag, 1)[1].split()
                      if t.count("=") == 1)
        if fields.get("action_id") == action_id:
            rows.append(fields)
    if (
        len(rows) != 5
        or bracket.get("action_id") != action_id
        or bracket.get("session_id") != session_id
        or edges.get("action_id") != action_id
        or edges.get("session_id") != session_id
        or edges.get("paper_release_tick") != bracket.get("release_tick")
        or edges.get("native_single_reader") is not True
        or edges.get("independent_source_attested") is not False
    ):
        raise ForwardDashDevRejected("post-release witness not source joined")
    observed = []
    for i, row in enumerate(rows, 1):
        try:
            tick = int(row["tick"])
            index = int(row["index"])
            delta = float(row["horizontal_delta_m"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ForwardDashDevRejected("malformed passive Paper sample") from exc
        if (
            row.get("session_id") != session_id
            or row.get("world") != bracket["world_uuid"]
            or row.get("player_uuid") != bracket["player_uuid"]
            or tick != bracket["release_tick"] + i
            or index != i
            or not math.isfinite(delta)
            or not 0 <= delta <= 2.0
            or row.get("boundary") != ("MIXED" if i == 1 else "POST_RELEASE")
            or row.get("modifier_present") != "false"
            or row.get("motor_write") != "false"
            or row.get("P1_APPLIED") != "false"
            or row.get("M0_POSTED") != "false"
            or row.get("WAIT_ATTESTED") != "false"
        ):
            raise ForwardDashDevRejected("post-release World tick/actor/motor violation")
        observed.append(delta)
    # The first delta may contain movement before the clear-controls ACK.
    # Include it in disclosure but exclude it from post-release translation.
    # Even 4 consecutive small deltas cannot establish zero control inputs.
    return {
        "classification": "PAPER_PASSIVE_POST_RELEASE_TRANSLATION_DEV_ONLY",
        "action_id": action_id,
        "session_id": session_id,
        "first_sample_tick": bracket["release_tick"] + 1,
        "last_sample_tick": bracket["release_tick"] + 5,
        "paper_callbacks": 5,
        "first_delta_m_mixed_boundary": observed[0],
        "post_release_deltas_m": observed[1:],
        "post_release_positive_translation_ticks": sum(v > 0.002 for v in observed[1:]),
        "post_release_low_delta_ticks": sum(v <= 0.002 for v in observed[1:]),
        "speed_modifier_present": False,
        "action_authority": False,
        "P1_posted": False,
        "M0_posted": False,
        "WAIT_sourcebound_admitted": False,
        "native_control_effect_tick_attested": False,
    }


def review_forward_dash_rows(raw: str, *, action_id: str, session_id: str) -> dict:
    """Parse only relevant native Paper lines, never invent missing positive ticks."""
    rows = []
    completed = []
    for line in raw.splitlines():
        if "S49_DASH_DEV_TICK " in line:
            payload = line.split("S49_DASH_DEV_TICK ", 1)[1]
            data = dict(
                token.split("=", 1) for token in payload.split()
                if token.count("=") == 1
            )
            if data.get("action_id") != action_id:
                continue
            if (
                data.get("session_id") != session_id
                or data.get("dash_stance_active") != "true"
                or data.get("modifier_applied") not in ("true", "false")
                or data.get("input_forward_only") not in ("true", "false")
                or data.get("motion_forward_inferred", "false")
                not in ("true", "false")
            ):
                raise ForwardDashDevRejected("Paper DASH input/modifier mismatch")
            try:
                index = int(data["index"])
                tick = int(data["tick"])
            except (KeyError, ValueError) as exc:
                raise ForwardDashDevRejected("malformed Paper DASH clock") from exc
            if (
                index != len(rows) + 1 or tick <= (rows[-1][0] if rows else 0)
                or str(index) != data["index"] or str(tick) != data["tick"]
            ):
                raise ForwardDashDevRejected("Paper DASH tick gap/replay")
            packet = data["input_forward_only"] == "true"
            motion = data.get("motion_forward_inferred") == "true"
            applied = data["modifier_applied"] == "true"
            source = data.get("boost_source", "PACKET" if packet else "NONE")
            # Preserve true input/motion signals even after the explicit
            # seven-positive-Paper-tick DEV motor modifier cap expires.
            # The original S49 native Action is NOT canceled by this cap.
            cap = data.get("p1_matched_boost_cap", "0")
            exhausted = data.get(
                "p1_matched_boost_exhausted_before_sample", "false"
            )
            prior_positive = sum(row[1] for row in rows)
            if (
                cap not in ("0", "7")
                or exhausted not in ("true", "false")
                or (cap == "0" and exhausted != "false")
                or (cap == "7") != (
                    data.get("p1_motor_dev") == "true"
                ) and exhausted == "true"
                or (cap == "7" and (
                    (prior_positive >= 7) != (exhausted == "true")
                    or prior_positive > 7
                ))
                or applied != ((packet or motion) and exhausted != "true")
                or (packet and motion)
                or source != (
                    "PACKET" if packet else "MOTION_PROJECTION"
                    if motion else "NONE"
                )
            ):
                raise ForwardDashDevRejected("invalid DASH source/motor classification")
            speed = data.get("sampled_speed_mps")
            if speed is not None:
                try:
                    speed_value = float(speed)
                except ValueError as exc:
                    raise ForwardDashDevRejected("bad sampled Paper speed") from exc
                if not math.isfinite(speed_value) or speed_value < 0:
                    raise ForwardDashDevRejected("nonfinite sampled Paper speed")
            else:
                speed_value = None
            rows.append((tick, applied, motion, speed_value))
        if "S49_DASH_DEV_COMPLETE " in line:
            payload = line.split("S49_DASH_DEV_COMPLETE ", 1)[1]
            data = dict(
                token.split("=", 1) for token in payload.split()
                if token.count("=") == 1
            )
            if data.get("action_id") == action_id:
                if data.get("session_id") != session_id:
                    raise ForwardDashDevRejected("foreign Paper DASH completion")
                completed.append(data)
    if len(completed) != 1:
        raise ForwardDashDevRejected("missing or repeated DASH completion")
    c = completed[0]
    if (c.get("modifier_applied") != "false"
            or int(c.get("forward_boost_ticks", "-1")) != sum(row[1] for row in rows)
            or int(c.get("other_direction_or_ambiguous_ticks", "-1"))
            != sum(not row[1] for row in rows)):
        raise ForwardDashDevRejected("DASH completion disagrees with observed ticks")
    if ("motion_estimated_boost_ticks" in c
            and int(c["motion_estimated_boost_ticks"])
            != sum(row[2] and row[1] for row in rows)):
        raise ForwardDashDevRejected("inferred boost source count mismatch")
    speeds = [row[3] for row in rows if row[3] is not None]
    return {
        "paper_motion_inferred_boost_ticks": sum(row[2] and row[1] for row in rows),
        "sampled_peak_server_horizontal_speed_m_s": max(speeds) if speeds else None,
        "paper_gait_ticks_observed": len(rows),
        "paper_forward_boost_ticks": sum(row[1] for row in rows),
        "paper_other_or_ambiguous_ticks": sum(not row[1] for row in rows),
        "paper_first_tick": rows[0][0] if rows else None,
        "paper_last_tick": rows[-1][0] if rows else None,
        "paper_modifier_removed": True,
        "action_id": action_id,
        "session_id": session_id,
        "server_effective_node_tick_sync": False,
        "measured_forward_speed_m_s": None,
        "m0_posted": False,
        "p1_native_updated": False,
        "qualification_go": False,
        "science_go": False,
    }


async def run(
    output_dir: Path, paper_jar: Path, paper_sha: str,
    dash_jar: Path, dash_sha: str, *, confirm: str,
    p1_live_dev: bool = False,
    m0_live_dev: bool = False,
    m0_move_dev: bool = False,
    native_edges_dev: bool = False,
    post_release_dev: bool = False,
    node_physics_dev: bool = False,
    m0_worldtime_shadow_dev: bool = False,
    two_action_timeline_dev: bool = False,
    inter_action_stillness_dev: bool = False,
    causal_owner_fence_dev: bool = False,
    p1_fenced_recovery_shadow_dev: bool = False,
    p1_observed_wait_model_dev: bool = False,
    p1_next_selfbody_epoch_dev: bool = False,
    p1_next_native_l0_review_dev: bool = False,
    p1_model_pair_case_dev: str | None = None,
    speed_attr_boundary_dev: bool = False,
    p1_matched_boost_dev: bool = False,
) -> int:
    if (
        confirm != CONFIRM or os.environ.get("NODE_OPTIONS")
        or os.environ.get("S49_REAL_SERVER_CI") != "1"
        or os.environ.get("S49_FORWARD_MOTOR_DEV_ONLY") != "1"
        or os.environ.get("S49_SPRINT_MOTOR_DEV_ONLY") != "1"
        or type(p1_live_dev) is not bool
        or type(m0_live_dev) is not bool
        or type(m0_move_dev) is not bool
        or type(native_edges_dev) is not bool
        or type(post_release_dev) is not bool
        or type(node_physics_dev) is not bool
        or type(m0_worldtime_shadow_dev) is not bool
        or type(two_action_timeline_dev) is not bool
        or type(inter_action_stillness_dev) is not bool
        or type(causal_owner_fence_dev) is not bool
        or type(p1_fenced_recovery_shadow_dev) is not bool
        or type(p1_observed_wait_model_dev) is not bool
        or type(p1_next_selfbody_epoch_dev) is not bool
        or type(p1_next_native_l0_review_dev) is not bool
        or type(speed_attr_boundary_dev) is not bool
        or type(p1_matched_boost_dev) is not bool
        or (p1_matched_boost_dev and (
            p1_model_pair_case_dev not in PAIR_FATIGUE
            or not speed_attr_boundary_dev
            or os.environ.get('S49_SPEED_ATTR_SYNC_DEV_ONLY') != '1'
            or os.environ.get('S49_P1_MATCHED_BOOST_DEV_ONLY') != '1'
        ))
        or (speed_attr_boundary_dev and (
            p1_model_pair_case_dev not in PAIR_FATIGUE
            or os.environ.get('S49_SPEED_ATTR_BOUNDARY_DEV_ONLY') != '1'
        ))
        or (p1_model_pair_case_dev is not None and (
            type(p1_model_pair_case_dev) is not str
            or p1_model_pair_case_dev not in PAIR_FATIGUE
            or not p1_live_dev
            or os.environ.get("S49_P1_DASH_PAIR_DEV_ONLY") != "1"
            or p1_fenced_recovery_shadow_dev
        ))
        or (p1_next_native_l0_review_dev and (
            not p1_next_selfbody_epoch_dev
            or os.environ.get("S49_P1_NEXT_NATIVE_L0_REVIEW_DEV_ONLY") != "1"
        ))
        or (p1_next_selfbody_epoch_dev and (
            not p1_observed_wait_model_dev
            or os.environ.get("S49_P1_NEXT_SELFBODY_EPOCH_DEV_ONLY") != "1"
        ))
        or (p1_observed_wait_model_dev and (
            not p1_fenced_recovery_shadow_dev
            or os.environ.get("S49_P1_OBSERVED_WAIT_MODEL_DEV_ONLY") != "1"
        ))
        or (p1_fenced_recovery_shadow_dev and (
            not causal_owner_fence_dev or not p1_live_dev
            or os.environ.get("S49_P1_FENCED_SHADOW_DEV_ONLY") != "1"
        ))
        or (causal_owner_fence_dev and (
            not inter_action_stillness_dev
            or os.environ.get("S49_CAUSAL_OWNER_PAPER_FENCE_DEV_ONLY") != "1"
        ))
        or (inter_action_stillness_dev and (
            not two_action_timeline_dev
            or os.environ.get("S49_INTER_ACTION_CONTROL_DEV_ONLY") != "1"
        ))
        or (two_action_timeline_dev and (
            not m0_worldtime_shadow_dev
            or os.environ.get("S49_TWO_ACTION_WORLD_TIMELINE_DEV_ONLY") != "1"
        ))
        or (m0_worldtime_shadow_dev and (
            not node_physics_dev
            or os.environ.get("S49_M0_WORLDTIME_SHADOW_DEV_ONLY") != "1"
        ))
        or (node_physics_dev and (
            not post_release_dev
            or os.environ.get("S49_NODE_PHYSICS_TRACE_DEV_ONLY") != "1"
        ))
        or (post_release_dev and (
            not native_edges_dev
            or os.environ.get("S49_POST_RELEASE_MOTION_DEV_ONLY") != "1"
        ))
        or (native_edges_dev and (
            not m0_move_dev
            or os.environ.get("S49_NATIVE_EFFECT_EDGE_DEV_ONLY") != "1"
        ))
        or (m0_move_dev and (
            not m0_live_dev
            or os.environ.get("S49_M0_ACTION_STEP_DEV_ONLY") != "1"
        ))
        or (m0_live_dev and (
            not p1_live_dev or os.environ.get("S49_M0_DASH_DEBIT_DEV_ONLY") != "1"
        ))
        or (p1_live_dev and os.environ.get("S49_P1_LIVE_DASH_DEV_ONLY") != "1")
    ):
        raise ForwardDashDevRejected("explicit isolated one-World/sprint gates required")
    paper_jar = _fresh_asset(paper_jar, paper_sha)
    dash_jar = _fresh_asset(dash_jar, dash_sha)
    if paper_jar.resolve() == dash_jar.resolve():
        raise ForwardDashDevRejected("Paper server and plugin must differ")
    _fresh_output(output_dir)
    paper_log = output_dir / "paper_server.log"
    original_report = output_dir / "original_s49_report.json"
    results = output_dir / "paper_forward_dash_dev_report.json"
    node_physics_path = output_dir.resolve() / "node_local_physics_dev.json"
    inter_action_path = output_dir.resolve() / "node_inter_action_controls_dev.json"
    attr_boundary_path = output_dir.resolve() / "node_speed_attr_boundary_dev.json"
    if speed_attr_boundary_dev and attr_boundary_path.exists():
        raise ForwardDashDevRejected("stale DEV attribute boundary source")
    if inter_action_stillness_dev and inter_action_path.exists():
        raise ForwardDashDevRejected("Node original inter-Action file already exists")
    if node_physics_dev and node_physics_path.exists():
        raise ForwardDashDevRejected("Node physics DEV trace preexisting")
    report: dict = {"status": "FAIL_CLOSED", "classification": "DEV_ONLY",
                    "qualification_go": False, "science_go": False}
    subject = {"server": None, "session": None, "action_id": None, "complete": None,
               "second_action_id": None}
    base_config = original._write_config
    base_ready = original._ready_server
    base_execute = action_owner.execute_mineflayer_command

    def paper_fetch(target: Path) -> dict:
        shutil.copyfile(paper_jar, target)
        return {"runtime": "PAPER_1_21_8_DISPOSABLE_DEV",
                "paper_asset_sha256": paper_sha}

    def paper_config(root: Path) -> None:
        base_config(root)
        plugins = root / "plugins"
        plugins.mkdir(exist_ok=False)
        shutil.copyfile(dash_jar, plugins / "s49-dash-dev.jar")
        cfg = plugins / "RelayS49DashDev"
        cfg.mkdir()
        (cfg / "config.yml").write_text(
            "enabled: true\nexpected-player-name: RelaySelf\n"
            + ("p1-live-dev: true\np1-initial-fatigue: "
               + (repr(PAIR_FATIGUE[p1_model_pair_case_dev]) if p1_model_pair_case_dev else "0.6")
               + "\np1-model-pair-dev: " + ("true" if p1_model_pair_case_dev else "false")
               + "\n" if p1_live_dev else "")
            + ("p1-matched-boost-cap-dev: 7\n" if p1_matched_boost_dev else "")
            + ("native-edge-dev: true\n" if native_edges_dev else "")
            + ("post-release-motion-dev: true\n" if post_release_dev else "")
            + ("two-action-trace-dev: true\n" if two_action_timeline_dev else "")
            + ("causal-owner-fence-dev: true\n" if causal_owner_fence_dev else ""),
            encoding="utf-8"
        )

    async def paper_ready(*args):
        ready = await base_ready(*args)
        subject["server"] = ready[0]
        return ready

    async def original_owner_paper_fence(phase: str, first_id: str, second_id: str):
        if (
            not causal_owner_fence_dev
            or phase not in ("START", "END")
            or first_id != subject["action_id"]
            or subject["session"] is None
            or (phase == "START" and second_id != "NONE")
            or (phase == "END" and (
                subject["second_action_id"] is not None
                or not second_id.startswith("s49-native-move-")
                or second_id == first_id
            ))
        ):
            raise ForwardDashDevRejected("foreign original S49 owner fence")
        server = subject["server"]
        if server is None or server.stdin is None:
            raise ForwardDashDevRejected("original S49 Paper fence owner missing")
        offset = paper_log.stat().st_size if paper_log.exists() else 0
        original._command(
            server,
            "relays49dashownerfence " + first_id + " "
            + subject["session"] + " " + offline_uuid("RelaySelf")
            + " " + phase + " " + second_id,
        )
        await server.stdin.drain()
        # Only await the original Paper console's ACK before the second
        # original Action proceeds. No new native reader or Paper Action.
        end = asyncio.get_running_loop().time() + 8
        while asyncio.get_running_loop().time() < end:
            if paper_log.is_file() and not paper_log.is_symlink():
                with paper_log.open("rb") as stream:
                    stream.seek(offset)
                    b = stream.read(65537)
                if len(b) > 65536:
                    raise ForwardDashDevRejected("Paper fence log overflow")
                window = b.decode("utf-8")
                if "S49_DASH_DEV_OWNER_FENCE_DENIED" in window:
                    raise ForwardDashDevRejected("Paper rejected original owner fence")
                for line in window.splitlines():
                    if ("S49_DASH_DEV_OWNER_FENCE " in line
                            and "action_id=" + first_id + " " in line
                            and "session_id=" + subject["session"] + " " in line
                            and "phase=" + phase + " " in line
                            and "second_action_id=" + second_id + " " in line):
                        subject.setdefault("owner_fences", []).append(phase)
                        return
            await asyncio.sleep(0.04)
        raise ForwardDashDevRejected("Paper did not acknowledge original owner " + phase)

    async def issued_original_transport(session, command, *, timeout_s, provenance):
        if (
            command.action_ref != "MOVE_FORWARD_SPRINT_DEV"
            or command.effect != "set_forward_sprint_dev"
            or command.control != "forward"
            or command.state is not True
            or not command.action_id.startswith("s49-native-move-")
            or (subject["session"] is not None
                and subject["session"] != session.started.session_id)
        ):
            raise ForwardDashDevRejected("not an original issued forward+sprint Action")
        subject["session"] = session.started.session_id
        first = subject["action_id"] is None
        server = subject["server"]
        if server is None or server.stdin is None:
            raise ForwardDashDevRejected("original Paper owner unavailable")
        if first:
            subject["action_id"] = command.action_id
            offset = paper_log.stat().st_size if paper_log.exists() else 0
            original._command(
                server, "relays49dasharm " + command.action_id + " "
                + subject["session"] + " " + offline_uuid("RelaySelf") + " 1.0",
            )
            await server.stdin.drain()
            await _await_dash_dev_line(
                paper_log, offset, marker="ARM", action_id=command.action_id,
            )
        elif two_action_timeline_dev:
            if subject["second_action_id"] is not None:
                raise ForwardDashDevRejected("only two original native Actions allowed")
            subject["second_action_id"] = command.action_id
        async def paper_effect_ack_marker(phase, result):
            # Already-consumed by the SAME original S15 Mineflayer receiver.
            # Only mark operator receipt delivery on Paper; do not issue Action.
            if (result.action_id != (
                command.action_id if phase == "APPLIED"
                else command.cleanup_action_id
            ) or result.session_id != subject["session"]):
                raise ForwardDashDevRejected("foreign native S15 effect ACK")
            # Write-and-flush once without polling Paper log. A blocking
            # Paper round-trip here artificially extends the actual native
            # control interval (observer effect). Console input is FIFO:
            # subsequent S49 dashoff follows both effect markers; the final
            # S16/producer-local bracket audit rejects any lost marker before
            # touching the original owner's B0 M0 balance.
            original._command(
                server, "relays49dashmark " + command.action_id + " "
                + subject["session"] + " " + offline_uuid("RelaySelf")
                + " " + phase + " " + str(result.seq),
            )
            await server.stdin.drain()
        async def paper_second_native_ack_marker(phase, result):
            # The same original S49 S15 reader has already received the
            # typed native effect result. Paper only timestamps its receipt.
            if (first or not two_action_timeline_dev
                    or result.action_id != (
                        command.action_id if phase == "APPLIED"
                        else command.cleanup_action_id
                    ) or result.session_id != subject["session"]):
                raise ForwardDashDevRejected("second original native ACK identity mismatch")
            original._command(
                server, "relays49dashtrailmark " + command.action_id + " "
                + subject["session"] + " " + offline_uuid("RelaySelf")
                + " " + phase + " " + str(result.seq),
            )
            # No Paper round-trip or log polling while the Action is moving.
            await server.stdin.drain()

        try:
            result = await base_execute(
                session, command, timeout_s=timeout_s, provenance=provenance,
                **({"on_effect_ack_dev": paper_effect_ack_marker
                    if first else paper_second_native_ack_marker}
                   if native_edges_dev and (first or two_action_timeline_dev) else {}),
            )
            if two_action_timeline_dev and not first:
                # Native control is already cleared and S15 ACK received;
                # allow five genuine Paper callbacks BEFORE the original
                # S49 session shutdown, not a second Action or extra reader.
                await asyncio.sleep(0.35)
            return result
        finally:
            if first:
                offset = paper_log.stat().st_size if paper_log.exists() else 0
                original._command(
                    server, "relays49dashoff " + command.action_id + " "
                    + subject["session"] + " " + offline_uuid("RelaySelf"),
                )
                await server.stdin.drain()
                subject["complete"] = await _await_dash_dev_line(
                    paper_log, offset, marker="COMPLETE",
                    action_id=command.action_id,
                )
    def invoice_from_original_outcome(receipt):
        # S49 only invokes this after the original Action reached S16 OUTCOME.
        # No second Action issue or adapter reader exists in this callback.
        if receipt.terminal.action_id != subject["action_id"]:
            return None  # The second unboosted original Action incurs no DASH extra.
        if subject["complete"] is None:
            raise ForwardDashDevRejected("Paper cleanup must precede M0 posting")
        raw = paper_log.read_text(encoding="utf-8")
        paper = review_forward_dash_rows(
            raw, action_id=subject["action_id"], session_id=subject["session"],
        )
        p1 = audit_native_paper_p1_dev(
            raw, action_id=subject["action_id"], session_id=subject["session"],
            model_initial=(PAIR_FATIGUE[p1_model_pair_case_dev] if p1_model_pair_case_dev else 0.6),
        )
        if m0_move_dev:
            bracket = review_paper_action_bracket_dev(
                raw, action_id=subject["action_id"], session_id=subject["session"],
            )
            if bracket["elapsed_callbacks"] != p1["world_ticks_replayed"]:
                raise ForwardDashDevRejected("Paper Action bracket/P1 tick mismatch")
            if native_edges_dev:
                receipt_evidence = capture_native_action_evidence(
                    receipt.consequence, allow_dev_forward=True, allow_dev_sprint=True,
                )
                subject["edge_review"] = review_original_s49_native_effect_edges_dev(
                    raw, action_id=subject["action_id"],
                    session_id=subject["session"],
                    native_evidence=receipt_evidence, bracket=bracket,
                )
        if (paper["paper_gait_ticks_observed"] != p1["world_ticks_replayed"]
                or paper["paper_forward_boost_ticks"] < 1
                or not paper["paper_modifier_removed"]
                or p1["m0_ledger_posted"] is not False):
            raise ForwardDashDevRejected("M0 invoice lacked Paper/P1 same-source proof")
        return DashM0InvoiceDev(
            session_id=subject["session"], action_id=subject["action_id"],
            first_world_tick=paper["paper_first_tick"],
            last_world_tick=paper["paper_last_tick"],
            observed_world_ticks=p1["world_ticks_replayed"],
            boost_ticks=paper["paper_forward_boost_ticks"],
            charge=p1["m0_charge_proposal_not_posted"],
        )

    try:
        with (
            patch.object(original, "_fetch_official_server", paper_fetch),
            patch.object(original, "_write_config", paper_config),
            patch.object(original, "_ready_server", paper_ready),
            patch.object(action_owner, "execute_mineflayer_command",
                         issued_original_transport),
            (patch.dict(os.environ, {
                "S49_NODE_PHYSICS_TRACE_DEV_ONLY": "1",
                "S49_NODE_PHYSICS_TRACE_DEV_PATH": str(node_physics_path),
                **({
                    "S49_INTER_ACTION_CONTROL_DEV_ONLY": "1",
                    "S49_INTER_ACTION_CONTROL_DEV_PATH": str(inter_action_path),
                } if inter_action_stillness_dev else {}),
            }) if node_physics_dev else nullcontext()),
            (patch.dict(os.environ, {
                'S49_SPEED_ATTR_BOUNDARY_DEV_ONLY': '1',
                'S49_SPEED_ATTR_BOUNDARY_DEV_PATH': str(attr_boundary_path),
            }) if speed_attr_boundary_dev else nullcontext()),
        ):
            rc = await original.qualify(
                original_report, paper_log,
                dev_forward_motor=True, dev_sprint_motor=True,
                dev_m0_dash_invoice=invoice_from_original_outcome if m0_live_dev else None,
                dev_m0_action_move_step=m0_move_dev,
                dev_inter_action_owner_gap=inter_action_stillness_dev,
                dev_inter_action_owner_paper_fence=(
                    original_owner_paper_fence if causal_owner_fence_dev else None
                ),
            )
        original_bytes = json.loads(original_report.read_text(encoding="utf-8"))
        report["original_s49_rc"] = rc
        report["original_s49_status"] = original_bytes.get("status")
        if rc != 0 or original_bytes.get("status") != "PASS":
            raise ForwardDashDevRejected(
                "original S49 sole issuer FAIL_CLOSED: "
                + str(original_bytes.get("error", original_bytes.get("stage")))[:300]
            )
        if causal_owner_fence_dev and subject.get("owner_fences") != ["START", "END"]:
            raise ForwardDashDevRejected(
                "original owner Paper causal fences missing/order: "
                + repr(subject.get("owner_fences"))
            )
        if (original_bytes.get("node_exit") != 0
                or original_bytes.get("server_exit") != 0
                or len(original_bytes["actual_native_actions"]) != 2):
            raise ForwardDashDevRejected("original S49 cleanup/outcome mismatch")
        actions = original_bytes["actual_native_actions"]
        if speed_attr_boundary_dev:
            report["node_speed_attribute_boundary_dev"] = (
                review_speed_attr_boundary_dev(
                    attr_boundary_path, session_id=subject["session"],
                    action_id=subject["action_id"],
                    sync_expected=os.environ.get("S49_SPEED_ATTR_SYNC_DEV_ONLY") == "1",
                )
            )
        if any(
            a["terminal"] != "outcome"
            or a["execution_evidence"]["action_ref"] != "MOVE_FORWARD_SPRINT_DEV"
            or a["execution_evidence"]["dispatch_receipt"]["effect"]
            != "set_forward_sprint_dev"
            for a in actions
        ):
            raise ForwardDashDevRejected("issued sprint evidence missing")
        if subject["complete"] is None:
            raise ForwardDashDevRejected("Paper release was not acknowledged")
        review = review_forward_dash_rows(
            paper_log.read_text(encoding="utf-8"),
            action_id=subject["action_id"], session_id=subject["session"],
        )
        report["paper"] = review
        if m0_move_dev:
            report["paper_action_bracket"] = review_paper_action_bracket_dev(
                paper_log.read_text(encoding="utf-8"),
                action_id=subject["action_id"], session_id=subject["session"],
            )
            if native_edges_dev:
                report["original_s49_effect_ack_paper_edges"] = subject.get(
                    "edge_review",
                )
                if report["original_s49_effect_ack_paper_edges"] is None:
                    raise ForwardDashDevRejected("original native ACK markers absent")
                if post_release_dev:
                    report["post_release_paper_motion_dev"] = review_post_release_motion_dev(
                        paper_log.read_text(encoding="utf-8"),
                        action_id=subject["action_id"],
                        session_id=subject["session"],
                        bracket=report["paper_action_bracket"],
                        edges=report["original_s49_effect_ack_paper_edges"],
                    )
                    if node_physics_dev:
                        report["node_physics_postclear_dev"] = (
                            audit_node_physics_postclear_dev(
                                node_physics_path,
                                action_id=subject["action_id"],
                                session_id=subject["session"],
                                paper_post_release=report["post_release_paper_motion_dev"],
                            )
                        )
                        try:
                            report["node_paper_motion_fingerprint_dev"] = (
                                audit_node_paper_motion_fingerprint_dev(
                                    report["node_physics_postclear_dev"],
                                    report["post_release_paper_motion_dev"],
                                    action_id=subject["action_id"],
                                    session_id=subject["session"],
                                )
                            )
                        except NativePhysicsTraceRejected as exc:
                            if not two_action_timeline_dev:
                                raise
                            # With a continuous Paper callback per World tick,
                            # the separately scheduled producer-local Node
                            # callbacks can shift. Keep failed 1um correlation
                            # as UNDETERMINED, never mint matching evidence.
                            report["node_paper_motion_fingerprint_dev"] = {
                                "classification": (
                                    "NODE_PAPER_GEOMETRIC_FINGERPRINT_UNDETERMINED"
                                ),
                                "diagnostic": str(exc),
                                "exact_match_confirmed": False,
                                "native_Paper_tick_correspondence_attested": False,
                                "WAIT_sourcebound_admitted": False,
                                "P1_posted": False, "M0_posted": False,
                            }
        if m0_live_dev:
            report["m0_s49_original_owner_postings"] = (
                original_bytes.get(
                    "dev_m0_action_move_postings" if m0_move_dev
                    else "dev_m0_dash_postings", [],
                )
            )
            report["m0_s49_original_owner_remaining"] = (
                original_bytes.get("dev_m0_dash_energy_remaining")
            )
        if p1_live_dev:
            report["p1_paper_motor_dev"] = audit_native_paper_p1_dev(
                paper_log.read_text(encoding="utf-8"),
                action_id=subject["action_id"], session_id=subject["session"],
                model_initial=(PAIR_FATIGUE[p1_model_pair_case_dev] if p1_model_pair_case_dev else 0.6),
            )
        if m0_live_dev:
            postings = report["m0_s49_original_owner_postings"]
            expected_charge = report["p1_paper_motor_dev"]["m0_charge_proposal_not_posted"]
            if m0_move_dev:
                if (len(postings) != 2
                        or [a["action_id"] for a in postings]
                           != [a["action"] for a in actions]
                        or any(a["session_id"] != subject["session"] for a in postings)
                        or postings[0]["dash_extra_debit"] <= 0
                        or not math.isclose(postings[0]["dash_extra_debit"],
                                            expected_charge, abs_tol=1e-10)
                        or postings[1]["dash_extra_debit"] != 0
                        or postings[0]["m0_tick_after"] != 1
                        or postings[1]["m0_tick_after"] != 2
                        or any(not math.isclose(a["basal_debit"], 0.5)
                               or not math.isclose(a["move_debit"], 0.25)
                               for a in postings)
                        or not math.isclose(
                            original_bytes["dev_m0_dash_energy_initial"]
                            - original_bytes["dev_m0_dash_energy_remaining"],
                            1.5 + expected_charge, abs_tol=1e-10)
                        or original_bytes.get("dev_m0_dash_m0_tick") != 2
                        or report["paper_action_bracket"]["elapsed_callbacks"]
                           != report["p1_paper_motor_dev"]["world_ticks_replayed"]):
                    raise ForwardDashDevRejected("S49 original owner MOVE step/M0 source mismatch")
                report["m0_debit_classification"] = (
                    "S49_NATIVE_OUTCOME_TWO_M0_MOVE_STEPS_PAPER_BRACKET_DEV_ONLY"
                )
                report["m0_world_tick_basal_accounted"] = False
                if (m0_worldtime_shadow_dev
                        and report["node_paper_motion_fingerprint_dev"].get(
                            "exact_match_confirmed", True
                        )):
                    report["m0_worldtime_basal_shadow_dev"] = (
                        project_s49_world_time_m0_shadow_dev(
                            action_id=subject["action_id"],
                            session_id=subject["session"],
                            paper_action_bracket=report["paper_action_bracket"],
                            passive_post_release=report["post_release_paper_motion_dev"],
                            native_edges=report["original_s49_effect_ack_paper_edges"],
                            node_paper_moving_footprint=report[
                                "node_paper_motion_fingerprint_dev"
                            ],
                            original_m0_postings=postings,
                            original_energy_remaining=report[
                                "m0_s49_original_owner_remaining"
                            ],
                            # Explicit DEV World-second assumption. Never
                            # derive the real M0 rate from legacy 0.5/Action.
                            rate=M0WorldRateDev(basal_energy_per_world_second=0.5),
                        )
                    )
                if two_action_timeline_dev:
                    if subject["second_action_id"] != actions[1]["action"]:
                        raise ForwardDashDevRejected("second original Action timeline ID mismatch")
                    report["m0_two_action_worldtime_shadow_dev"] = (
                        review_two_action_world_timeline_dev(
                            paper_log.read_text(encoding="utf-8"),
                            action_id=subject["action_id"],
                            session_id=subject["session"],
                            bracket=report["paper_action_bracket"],
                            passive=report["post_release_paper_motion_dev"],
                            first_native_ack=report[
                                "original_s49_effect_ack_paper_edges"
                            ],
                            original_actions=actions,
                            original_m0_postings=postings,
                            final_original_energy=report[
                                "m0_s49_original_owner_remaining"
                            ],
                        )
                    )
                if inter_action_stillness_dev:
                    report["inter_action_stillness_dev"] = (
                        review_inter_action_stillness_dev(
                            paper_log.read_text(encoding="utf-8"),
                            inter_action_path,
                            timeline=report["m0_two_action_worldtime_shadow_dev"],
                            first_action_id=actions[0]["action"],
                            second_action_id=actions[1]["action"],
                            session_id=subject["session"],
                        )
                    )
                    report["original_owner_inputoff_static_join_dev"] = (
                        review_original_owner_no_issued_action_gap_dev(
                            original_bytes["dev_inter_action_original_owner_gap"],
                            report["inter_action_stillness_dev"],
                            first_action_id=actions[0]["action"],
                            second_action_id=actions[1]["action"],
                            session_id=subject["session"],
                        )
                    )
                    if causal_owner_fence_dev:
                        report["original_owner_causal_paper_wait_candidate_dev"] = (
                            review_original_owner_causal_paper_fence_dev(
                                paper_log.read_text(encoding="utf-8"),
                                owner=report["original_owner_inputoff_static_join_dev"],
                                original_owner=original_bytes[
                                    "dev_inter_action_original_owner_gap"
                                ],
                                stillness=report["inter_action_stillness_dev"],
                                timeline=report["m0_two_action_worldtime_shadow_dev"],
                                first_action_id=actions[0]["action"],
                                second_action_id=actions[1]["action"],
                                session_id=subject["session"],
                            )
                        )
                        if p1_fenced_recovery_shadow_dev:
                            report["p1_fenced_recovery_shadow_dev"] = (
                                project_p1_fenced_wait_shadow_dev(
                                    fence=report["original_owner_causal_paper_wait_candidate_dev"],
                                    p1_replay=report["p1_paper_motor_dev"],
                                    action_bracket=report["paper_action_bracket"],
                                    profile=FatigueProfile(enabled=True, initial=0.6),
                                    session_id=subject["session"],
                                    first_action_id=actions[0]["action"],
                                    second_action_id=actions[1]["action"],
                                    original_m0_energy_remaining=report[
                                        "m0_s49_original_owner_remaining"
                                    ],
                                )
                            )
                            if p1_observed_wait_model_dev:
                                report["p1_observed_wait_model_dev"] = (
                                    replay_p1_observed_static_wait_dev(
                                        paper_log.read_text(encoding="utf-8"),
                                        fence=report["original_owner_causal_paper_wait_candidate_dev"],
                                        shadow=report["p1_fenced_recovery_shadow_dev"],
                                        stillness=report["inter_action_stillness_dev"],
                                        timeline=report["m0_two_action_worldtime_shadow_dev"],
                                        profile=FatigueProfile(enabled=True, initial=0.6),
                                        session_id=subject["session"],
                                        first_action_id=actions[0]["action"],
                                        second_action_id=actions[1]["action"],
                                    )
                                )
                                if p1_next_selfbody_epoch_dev:
                                    report["p1_next_selfbody_epoch_shadow_dev"] = (
                                        project_p1_static_next_body_epoch_dev(
                                            report["p1_observed_wait_model_dev"],
                                            report["original_owner_causal_paper_wait_candidate_dev"],
                                            profile=FatigueProfile(enabled=True, initial=0.6),
                                            session_id=subject["session"],
                                            first_action_id=actions[0]["action"],
                                            second_action_id=actions[1]["action"],
                                        )
                                    )
                                    if p1_next_native_l0_review_dev:
                                        report["p1_next_native_l0_review_dev"] = (
                                            review_next_native_p1_l0_comparison_dev(
                                                original_bytes,
                                                report["p1_next_selfbody_epoch_shadow_dev"],
                                                report["p1_observed_wait_model_dev"],
                                                report["original_owner_causal_paper_wait_candidate_dev"],
                                                report["m0_two_action_worldtime_shadow_dev"],
                                            )
                                        )
            else:
                if (len(postings) != 1
                        or postings[0]["action_id"] != subject["action_id"]
                        or postings[0]["session_id"] != subject["session"]
                        or not math.isclose(
                            postings[0]["posted_extra"], expected_charge,
                            abs_tol=1e-10,
                        )
                        or not math.isclose(
                            postings[0]["energy_before"] - postings[0]["energy_after"],
                            expected_charge, abs_tol=1e-10)
                        or original_bytes.get("dev_m0_dash_m0_tick") != 1
                        or not math.isclose(
                            original_bytes["dev_m0_dash_energy_initial"]
                            - original_bytes["dev_m0_dash_energy_remaining"],
                            expected_charge, abs_tol=1e-10)
                        or len(original_bytes["dev_m0_dash_unboosted_actions"]) != 1
                        or original_bytes["dev_m0_dash_unboosted_actions"][0]
                           != actions[1]["action"]):
                    raise ForwardDashDevRejected("Original S49 M0 DASH extra not source bound")
                report["m0_debit_classification"] = (
                    "ORIGINAL_S49_LOCAL_B0_OWNER_POSTED_DEV_NOT_ATTESTED"
                )
        if p1_matched_boost_dev:
            completion_lines = [
                line for line in subject["complete"].splitlines()
                if "S49_DASH_DEV_COMPLETE " in line
                and "action_id=" + subject["action_id"] + " " in line
                and "session_id=" + subject["session"] + " " in line
            ]
            if (
                review["paper_forward_boost_ticks"] != 7
                or len(completion_lines) != 1
                or "p1_matched_boost_cap=7 " not in completion_lines[0]
                or "p1_matched_boost_cap_reached=true " not in completion_lines[0]
            ):
                raise ForwardDashDevRejected(
                    "Paper failed to reach exact 7 matched positive boost World ticks"
                )
            report["p1_matched_paper_boost_dev"] = {
                "paper_positive_boost_ticks": 7,
                "paper_dev_modifier_only_capped": True,
                "original_native_action_issuer_changed": False,
                "client_world_tick_synchronized": False,
                "physical_p1_wait_recovery_attested": False,
                "qualification_go": False,
                "science_go": False,
            }
        if p1_model_pair_case_dev:
            report["p1_pair_preloaded_model_dev"] = {
                "case": p1_model_pair_case_dev,
                "input_fatigue": PAIR_FATIGUE[p1_model_pair_case_dev],
                "frozen_candidate_source_sha256": PAIR_SOURCE_DIGEST,
                "model_preloaded_in_new_disposable_world": True,
                "actual_same_self_wait_recovery_attested": False,
                "production_p1_state_updated": False,
                "additional_action_issuers": 0,
                "qualification_go": False, "science_go": False,
            }
        report["original_action_distances_m"] = [a["movement_m"] for a in actions]
        report["first_minus_unboosted_second_distance_m"] = (
            actions[0]["movement_m"] - actions[1]["movement_m"]
        )
        report["comparison_classification"] = (
            "UNCONTROLLED_SAME_RUN_DISTANCE_COMPARISON_DEV_ONLY"
        )
        if review["paper_forward_boost_ticks"] < 1:
            report["status"] = "DEV_SPRINT_NO_POSITIVE_PAPER_BOOST"
            return 1
        try:
            report["physical_gain_dev"] = evaluate_native_dash_gain_dev(
                armed_m=actions[0]["movement_m"],
                unarmed_m=actions[1]["movement_m"],
                peak_mps=review["sampled_peak_server_horizontal_speed_m_s"],
                boost_ticks=review["paper_forward_boost_ticks"],
            )
        except ForwardDashDevRejected as exc:
            if p1_model_pair_case_dev:
                # A genuine negative native motor response is DATA in this
                # preloaded MODEL sensitivity comparison, not an imaginary
                # recovered-fatigue success or a violation of the sole owner.
                report["status"] = "DEV_PAIR_PAPER_OUTPUT_REAL_WORLD_NO_NATIVE_GAIN"
                report["native_gain_unobserved_reason"] = str(exc)
                report["physical_gain_dev"] = None
                return 0
            report["status"] = "DEV_PAPER_BOOST_BUT_NO_NATIVE_SPEED_GAIN"
            report["error"] = str(exc)
            return 1
        report["status"] = (
            "DEV_FORWARD_SPRINT_MOTION_GATED_PAPER_DASH_OBSERVED"
            if review["paper_motion_inferred_boost_ticks"] > 0
            else "DEV_FORWARD_SPRINT_POSITIVE_PAPER_DASH_OBSERVED"
        )
        return 0
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        return 1
    finally:
        results.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print("S49_PAPER_FORWARD_DASH_REPORT=" + json.dumps(report, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--paper-jar", type=Path, required=True)
    parser.add_argument("--paper-sha256", required=True)
    parser.add_argument("--dash-jar", type=Path, required=True)
    parser.add_argument("--dash-sha256", required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--p1-live-dev", action="store_true")
    parser.add_argument("--m0-live-dev", action="store_true")
    parser.add_argument("--m0-move-dev", action="store_true")
    parser.add_argument("--native-edges-dev", action="store_true")
    parser.add_argument("--post-release-dev", action="store_true")
    parser.add_argument("--node-physics-dev", action="store_true")
    parser.add_argument("--m0-worldtime-shadow-dev", action="store_true")
    parser.add_argument("--two-action-timeline-dev", action="store_true")
    parser.add_argument("--inter-action-stillness-dev", action="store_true")
    parser.add_argument("--causal-owner-fence-dev", action="store_true")
    parser.add_argument("--p1-fenced-recovery-shadow-dev", action="store_true")
    parser.add_argument("--p1-observed-wait-model-dev", action="store_true")
    parser.add_argument("--p1-next-selfbody-epoch-dev", action="store_true")
    parser.add_argument("--p1-next-native-l0-review-dev", action="store_true")
    parser.add_argument("--p1-model-pair-case-dev", choices=tuple(PAIR_FATIGUE))
    parser.add_argument("--speed-attr-boundary-dev", action="store_true")
    parser.add_argument("--p1-matched-boost-dev", action="store_true")
    a = parser.parse_args()
    return asyncio.run(run(
        a.output_dir, a.paper_jar, a.paper_sha256,
        a.dash_jar, a.dash_sha256, confirm=a.confirm,
        p1_live_dev=a.p1_live_dev,
        m0_live_dev=a.m0_live_dev,
        m0_move_dev=a.m0_move_dev,
        native_edges_dev=a.native_edges_dev,
        post_release_dev=a.post_release_dev,
        node_physics_dev=a.node_physics_dev,
        m0_worldtime_shadow_dev=a.m0_worldtime_shadow_dev,
        two_action_timeline_dev=a.two_action_timeline_dev,
        inter_action_stillness_dev=a.inter_action_stillness_dev,
        causal_owner_fence_dev=a.causal_owner_fence_dev,
        p1_fenced_recovery_shadow_dev=a.p1_fenced_recovery_shadow_dev,
        p1_observed_wait_model_dev=a.p1_observed_wait_model_dev,
        p1_next_selfbody_epoch_dev=a.p1_next_selfbody_epoch_dev,
        p1_next_native_l0_review_dev=a.p1_next_native_l0_review_dev,
        p1_model_pair_case_dev=a.p1_model_pair_case_dev,
        speed_attr_boundary_dev=a.speed_attr_boundary_dev,
        p1_matched_boost_dev=a.p1_matched_boost_dev,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
