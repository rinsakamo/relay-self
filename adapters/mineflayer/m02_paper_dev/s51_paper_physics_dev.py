"""S-owned M0.2 isolated Paper physics DEV, reusing existing S31A/S50/S51 owners.

This is NOT R qualification or V science. Unlike legacy B0, there is no
separate M0 energy ledger or virtual EAT credit. Original native source
records and server console remain evidence, with honest operator fixtures.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import re
import shutil
import socket
import stat
import tempfile
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.eat_execution import IssuedEatingExecutor
from adapters.mineflayer.m02_paper_dev.native_l0 import PaperNativeL0
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig, MineflayerPosition
from adapters.mineflayer.s31a_real_server_ci import (
    BOT_USERNAME,
    MINECRAFT_VERSION,
    SERVER_HOST,
    SERVER_PORT,
    _await_spawn,
    _command,
    _correlated_observe,
    _ready_server,
    _shutdown_server,
    _write_config,
)
from adapters.mineflayer.s51_eat_real_ci import _recording_session_type
from adapters.mineflayer.seek_execution import SeekConsequenceKind, execute_seek_step
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.seek_waypoint import SeekCursor, SeekStatus, SeekWaypoint
from relay_self.skill import SkillExecution

PLUGIN_ROOT = Path(__file__).resolve().parent
M02_CONFIRM = "M02-DEV-I-OWN-DISPOSABLE-PAPER-WORLD"

# Mirrors the immutable R #610 M0.2 preworld V1 *input identities*.
# These digests describe an earlier DEV source candidate; they confer no grant.
PAPER_PREWORLD_ASSET_PINS = {
    "paper-1.21.8.jar": "8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e",
    "relay-metabolism-paper-dev.jar": "0ed8a00a7ebf577bdbea361e2c6facf7ed4b24001c017d362823da5cb60398e5",
    "config.yml": "e9361faa7eac2e3c63bf2f6760765f7f8ae5a4b3631c6819f7ad8ac5c04a540e",
    "server.properties": "11aaf903bae3d92f3b667f464f301a513bee559f04acc33d722c7a2e966d03ae",
}
PAPER_PREWORLD_PROFILE = "RSEE_M02_PAPER_PREWORLD_PROFILE_V1"


class M02DevRejected(RuntimeError):
    """Invalid disposable profile, source, owner authorization or cleanup."""


def _sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as inp:
        while chunk := inp.read(1024 * 1024):
            sha.update(chunk)
    return sha.hexdigest()


def _fresh_asset(path: Path, digest: str) -> Path:
    if (not path.is_absolute() or not path.is_file() or path.is_symlink()
            or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)):
        raise M02DevRejected("absolute unlinked jar and full sha256 required")
    if _sha256(path) != digest:
        raise M02DevRejected("jar SHA256 mismatch")
    return path


def _port_free() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((SERVER_HOST, SERVER_PORT)) != 0


def _p(tag: str) -> Provenance:
    return Provenance("s51-m02-paper-explicit-dev-fixture", tag)


def _issue(
    supervisor: ActionSupervisor, action_id: str, skill_id: str,
    intent_id: str, objective: str, *, time_base: int,
) -> ActionLifecycle:
    intent = IntentCommitment()
    intent.commit(intent_id, objective=objective, at_ns=time_base,
                  provenance=_p(action_id + "-intent"))
    skill = SkillExecution.start(
        action_id + "-skill", skill_id=skill_id, intent_commitment=intent,
        at_ns=time_base + 1, provenance=_p(action_id + "-skill"),
    )
    proposed = ActionLifecycle.propose(
        action_id, skill_execution=skill, intent_commitment=intent,
        at_ns=time_base + 2, provenance=_p(action_id + "-proposed"),
    )
    authorized = proposed.authorize(
        at_ns=time_base + 3, authority="explicit-s51-m02-dev-operator",
        provenance=_p(action_id + "-authorized"),
    )
    return supervisor.issue(authorized, at_ns=time_base + 4,
                            deadline_ns=time_base + 50,
                            provenance=_p(action_id + "-issued"))


async def _motor_walk(session: MineflayerProcessSession, *,
                      issuer=None, provenance=None,
                      expected_start: MineflayerPosition | None = None,
                      v7_phase_source: tuple | None = None,
                      v7_clock_gate_dev: bool = False,
                      v7_tick_meter_dev: bool = False,
                      v7_tick_meter_walk_rate: float | None = None,
                      v7_p1_wait_evidence_dev: bool = False) -> dict:
    issuer = issuer or _issue
    provenance = provenance or _p
    before = await _correlated_observe(session, "m02-before-walk")
    p = before.snapshot.position
    if expected_start is not None and any(
            abs(getattr(p, field) - getattr(expected_start, field)) > 1e-3
            for field in ("x", "y", "z")):
        raise M02DevRejected("controlled DEV native pre-MOVE pose drift")
    # Nominal 1-block S50 plan, *not* an exact 1-block outcome guarantee.
    waypoint = SeekWaypoint(
        "m02-one-block-forward-goal",
        MineflayerPosition(p.x + 2.0, p.y, p.z),
        tolerance_m=0.7, max_step_m=1.0,
    )
    step = SeekCursor(session.started.session_id).plan(before, waypoint)
    if step.status is not SeekStatus.STEER or step.step_distance_m != 1.0:
        raise M02DevRejected("not a valid one-block S50 steering proposal")
    supervisor = ActionSupervisor()
    issued = issuer(
        supervisor, "m02-paper-walk-1", "seek-waypoint",
        "m02-walk", "move one nominal block in isolated test World", time_base=10,
    )
    phase_hook = None
    marker_id = None
    if v7_clock_gate_dev and v7_phase_source is None:
        raise M02DevRejected("source-driven tick gate requires controlled Paper DEV")
    if v7_tick_meter_dev and (not v7_clock_gate_dev
                              or v7_tick_meter_walk_rate not in (0.0, 0.01)):
        raise M02DevRejected("tick-meter requires known controlled DEV rate")
    if v7_p1_wait_evidence_dev and not v7_tick_meter_dev:
        raise M02DevRejected("P1 WAIT source requires native tick-meter DEV")
    if v7_phase_source is not None:
        if expected_start is None or len(v7_phase_source) != 2:
            raise M02DevRejected("S50 phase markers require controlled DEV source")
        server, paper_log = v7_phase_source
        marker_id = issued.action_id + "-" + session.started.session_id
        async def phase_hook(phase: str) -> None:
            await _v7_source_phase_command(server, paper_log, marker_id, phase)
    tick_gate_hook = None
    if v7_clock_gate_dev:
        async def tick_gate_hook() -> None:
            await _v7_wait_clock_gate_source(paper_log, marker_id)
    journal = (paper_log.parent / "s50_action_original.jsonl"
               if v7_phase_source is not None else None)
    def save_lifecycle(lifecycle, **extra):
        if journal is not None:
            with journal.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({
                    "action_id": lifecycle.action_id,
                    "session_id": session.started.session_id,
                    "clock": "SYNTHETIC_DEV_LOGICAL_ORDER_NOT_WORLD_TIME",
                    "state": lifecycle.state.value,
                    "events": [asdict(e) for e in lifecycle.events],
                    **extra,
                }) + "\n")
    save_lifecycle(issued)
    settle_hook = None
    if v7_clock_gate_dev:
        from adapters.mineflayer.m02_paper_dev.s50_boundary import await_quiet
        async def settle_hook():
            await await_quiet(paper_log, marker_id)
    try:
        effect = await execute_seek_step(
            session, supervisor, issued, step, phase_hook=phase_hook,
            tick_gate_hook=tick_gate_hook, settle_hook=settle_hook)
        if v7_clock_gate_dev:
            from adapters.mineflayer.m02_paper_dev.s50_boundary import (
                reconcile,
                reconcile_tick_meter,
                rows,
            )
            arm_rows = rows(paper_log.read_text(), "M02_DEV_MOTION ")
            # Use the actual per-event source rate; full arm agreement is also
            # checked against the configured arm after server shutdown.
            rate = (float(arm_rows[0]["billed"]) / float(arm_rows[0]["blocks"])
                    if arm_rows else 0.0)
            (reconcile_tick_meter if v7_tick_meter_dev else reconcile)(
                paper_log.read_text(), {
                "action_id": issued.action_id, "source_session": effect.session_id,
                "v7_phase_marker_id": marker_id,
                "native_start_position": asdict(p),
                "native_target_position": asdict(step.target),
                "observed_progress_blocks": effect.progress_m,
            }, walk_rate=v7_tick_meter_walk_rate if v7_tick_meter_dev else rate)
    except Exception as exc:
        unknown = supervisor.mark_unknown(
            issued.action_id, at_ns=15, provenance=provenance("s50-unknown"))
        save_lifecycle(unknown, error=repr(exc), physical_outcome="NOT_ATTESTED")
        raise
    closed = supervisor.record_outcome(
        issued.action_id, at_ns=15,
        provenance=provenance("m02-paper-walk-1-outcome"),
    )
    save_lifecycle(closed, consequence=asdict(effect))
    p1_wait_candidate = None
    if v7_p1_wait_evidence_dev and closed.state is ActionState.OUTCOME:
        # Original source starts AFTER genuine S50 terminal/clear, but a
        # separate R whole-tick activity witness is STILL REQUIRED.
        await _s50_p1_source_wait_window(server, paper_log, marker_id)
        from adapters.mineflayer.m02_paper_dev.s50_boundary import phases
        from adapters.mineflayer.m02_paper_dev.s50_p1_wait import candidate_wait_ticks
        p1_wait_candidate = candidate_wait_ticks(
            paper_log.read_text(encoding="utf-8"), marker_id=marker_id,
            expected_world=phases(paper_log.read_text(encoding="utf-8"), marker_id)[0]["world"],
            source_action_terminal=closed.state.value,
        )
        from adapters.mineflayer.m02_paper_dev.s50_p1_scope import review_scope
        p1_wait_candidate["source_scope"] = review_scope(
            paper_log.read_text(encoding="utf-8"),
            marker=marker_id, world=p1_wait_candidate["world"],
            wait_first_tick=p1_wait_candidate["first_world_tick"],
            wait_last_tick=p1_wait_candidate["last_world_tick"],
            original_outcome=closed.state.value,
        )
    if (closed.state is not ActionState.OUTCOME
            or supervisor.open_actions
            or effect.kind is SeekConsequenceKind.BLOCKED
            or effect.progress_m < 0.05):
        raise M02DevRejected("one authorized S50 walk had no actual World progress")
    return {
        "source_session": effect.session_id,
        "native_start_position": asdict(p),
        "native_target_position": asdict(step.target),
        "controlled_pose_pre_move_verified": expected_start is not None,
        "v7_phase_marker_id": marker_id,
        "v7_clock_gate_dev": v7_clock_gate_dev,
        "v7_tick_meter_dev": v7_tick_meter_dev,
        "v7_p1_wait_evidence_dev": v7_p1_wait_evidence_dev,
        "p1_wait_candidate": p1_wait_candidate,
        "action_id": issued.action_id,
        "action_state": closed.state.value,
        "requested_max_step_blocks": 1.0,
        "observed_progress_blocks": effect.progress_m,
        "kind": effect.kind.value,
        "source_before_seq": effect.before_seq,
        "source_after_seq": effect.after_seq,
        "look_seq": effect.look_seq,
        "forward_seq": effect.forward_seq,
        "clear_seq": effect.clear_seq,
    }


async def _native_steak(session: MineflayerProcessSession, server, *,
                        issuer=None, preowned: bool = False) -> dict:
    issuer = issuer or _issue
    if server.stdin is None:
        raise M02DevRejected("owned server console absent")
    if not preowned:
        _command(server, "give RelaySelf minecraft:cooked_beef 3")
        _command(server, "effect give RelaySelf minecraft:hunger 25 20 true")
        await server.stdin.drain()
    l0 = PaperNativeL0(session.started.session_id, hunger_threshold=14)
    before = choice = None
    seen: list[dict] = []
    for i in range(16):
        await asyncio.sleep(2)
        probe = await _correlated_observe(session, f"m02-steak-appetite-{i:02d}")
        decision = l0.decide(probe)
        seen.append({
            "source_seq": probe.seq,
            "food": probe.snapshot.food,
            "saturation": probe.snapshot.food_saturation,
            "steak_count": sum(x.count for x in probe.snapshot.inventory
                               if x.name == "cooked_beef"),
            "paper_native_l0_kind": decision.kind,
            "issued_action": False,
        })
        if (decision.kind == "EAT" and decision.eat_choice is not None
                and decision.eat_choice.item_name == "cooked_beef"):
            before, choice = probe, decision.eat_choice
            break
    if before is None or choice is None:
        raise M02DevRejected("no authenticated native hunger+steak observation")
    _command(server, "effect clear RelaySelf minecraft:hunger")
    await server.stdin.drain()
    supervisor = ActionSupervisor()
    issued = issuer(
        supervisor, "m02-paper-eat-steak-1", "eat",
        "m02-eat", "eat owned cooked_beef when actually hungry", time_base=100,
    )
    eating = await IssuedEatingExecutor().execute(
        session, supervisor, issued, choice, before,
    )
    outcome = eating.outcome
    if (
        eating.terminal.state is not ActionState.OUTCOME
        or supervisor.open_actions
        or outcome.food_after <= outcome.food_before
        or outcome.count_before - outcome.count_after != 1
    ):
        raise M02DevRejected("real S51 steak consume+inventory effect absent")
    after = await _correlated_observe(session, "m02-after-steak")
    return {
        "source_session": before.session_id,
        "appetite_trace": seen,
        "l0_choice": "EAT_FROM_NATIVE_WORLD_FOOD_NOT_VIRTUAL_M0",
        "action_id": issued.action_id,
        "action_state": eating.terminal.state.value,
        "native_outcome": asdict(outcome),
        "saturation_before": before.snapshot.food_saturation,
        "saturation_after": after.snapshot.food_saturation,
        "food_after_followup": after.snapshot.food,
        "after_source_seq": after.seq,
        "virtual_energy_credit": 0,
    }


def _read_world_receipts(
    server_log: Path, *, max_path_blocks: float = 2,
    allow_packet_only_walk: bool = False,
) -> dict:
    lines = server_log.read_text(encoding="utf-8").splitlines()
    enabled = [x for x in lines if "M02_DEV_ONLY: candidate physics" in x]
    body = [x for x in lines if "M02_DEV_BODY sampled_tick=" in x]
    walk = [x for x in lines if "M02_DEV_EVENT " in x and "reason=WALK " in x]
    motion = [x for x in lines if "M02_DEV_MOTION " in x and "reason=WALK " in x]
    if not enabled or not body or not motion or (not walk and not allow_packet_only_walk):
        raise M02DevRejected("Paper plugin startup/basal/WALK and packet motion absent")
    if not all("original=0.0 " in x and "replaced=0.0" in x for x in walk):
        raise M02DevRejected("land WALK native event must be replaced by zero")
    blocks = 0.0
    charged = 0.0
    for line in motion:
        distance = re.search(r"\bblocks=([0-9.eE+-]+)", line)
        cost = re.search(r"\bbilled=([0-9.eE+-]+)", line)
        if distance is None or cost is None:
            raise M02DevRejected("missing typed real packet movement evidence")
        blocks += float(distance.group(1))
        charged += float(cost.group(1))
    if not 0.5 < blocks < max_path_blocks:
        raise M02DevRejected("World packet distance is not one bounded physical step")
    if abs(charged - 0.01 * blocks) > 1e-7:
        raise M02DevRejected("per-block WALK charge differs from measured path")
    return {
        "plugin_enabled_original_log_lines": enabled,
        "basal_world_tick_samples": body[:8],
        "walk_native_event_samples": walk[:12],
        "world_packet_walk_samples": motion[:12],
        "count_walk_native_events": len(walk),
        "walk_native_callbacks_present": bool(walk),
        "physical_walk_billing_source": "PLAYER_MOVE_EVENT_COORDINATE_PATH",
        "count_walk_motion_packets": len(motion),
        "world_measured_walk_blocks": blocks,
        "world_billed_walk_exhaustion": charged,
        "expected_rate_exhaustion_per_block": 0.01,
        "native_original_log_available": True,
        "native_event_identity_independently_qualified": False,
    }





def _v7_direct_basal_write_receipt(content: str, arm: str) -> dict:
    """First 200 actual Paper source-write callbacks, *not* an Action bracket."""
    from adapters.mineflayer.m02_paper_dev.v7_paired_config import ARMS

    if arm not in ARMS or not isinstance(content, str):
        raise M02DevRejected("unregistered V7 basal original source")
    pattern = re.compile(
        r"M02_DEV_BASAL_WRITE id=(\d+) world_full_time=(\d+) "
        r"before=([0-9.eE+\-]+) requested=([0-9.eE+\-]+) "
        r"write_target=([0-9.eE+\-]+) "
        r"observed_after=([0-9.eE+\-]+) "
        r"cumulative_requested=([0-9.eE+\-]+)"
    )
    records = []
    for line in content.splitlines():
        if "M02_DEV_BASAL_WRITE " not in line:
            continue
        match = pattern.search(line)
        if match is None:
            raise M02DevRejected("malformed BASAL source write")
        idx, world = (int(match.group(1)), int(match.group(2)))
        values = tuple(float(match.group(i)) for i in range(3, 8))
        if not all(math.isfinite(v) and v >= 0 for v in values):
            raise M02DevRejected("nonfinite BASAL original write")
        records.append((idx, world, *values))
    if len(records) < 200:
        raise M02DevRejected("insufficient direct Paper BASAL writes")
    first200 = records[:200]
    if ([x[0] for x in first200] != list(range(1, 201))
            or any(first200[i][1] != first200[i-1][1] + 1
                   for i in range(1, 200))):
        raise M02DevRejected("missing/duplicate Paper player tick or World time")
    total = 0.
    rate = ARMS[arm][0] * 0.001
    for _, _, before, requested, write_target, observed_after, cumulative in first200:
        total += requested
        if (abs(requested - rate) > 1e-8
                or abs(write_target - (before + requested)) > 1e-6
                or abs(cumulative - total) > 1e-6
                or observed_after > 40):
            raise M02DevRejected("BASAL source write/rate/cumulative mismatch")
    return {
        "source": "ACTUAL_PAPER_SETEXHAUSTION_WRITE_INPUT",
        "source_write_count": 200,
        "world_full_time_first": first200[0][1],
        "world_full_time_200th": first200[-1][1],
        "cumulative_requested_basal_exhaustion": total,
        "configured_basal_multiplier": ARMS[arm][0],
        "requested_not_ecological_effect": True,
        "full_move_action_bracket_attested": False,
    }


def _v7_world_geometry_source(content: str, expected_seed: int) -> dict:
    """First living-player Paper tick only; no movement-start causal proof."""
    prefix = "M02_DEV_WORLD_V7_FIRST_TICK "
    original = [line.split(prefix, 1)[1] for line in content.splitlines()
                if prefix in line]
    if len(original) != 1:
        raise M02DevRejected("missing/duplicate native Paper World first tick")
    fields = {}
    for token in original[0].split():
        if "=" not in token:
            raise M02DevRejected("malformed World pose/corridor token")
        name, value = token.split("=", 1)
        if name in fields or not value:
            raise M02DevRejected("duplicate/empty native World source")
        fields[name] = value
    if set(fields) != {
        "seed", "full_time", "x", "y", "z", "yaw", "pitch", "corridor",
    }:
        raise M02DevRejected("incomplete native World seed/pose/geometry")
    try:
        seed, full_time = int(fields["seed"]), int(fields["full_time"])
        pose = {p: float(fields[p]) for p in ("x", "y", "z", "yaw", "pitch")}
        if (seed != expected_seed or full_time < 0
                or not all(math.isfinite(v) for v in pose.values())):
            raise ValueError("mismatched World seed/time/pose")
        samples = []
        for expected_dx, encoded in enumerate(fields["corridor"].split(";")):
            dx, ground, solid, feet, pass_feet, head, pass_head = encoded.split(":")
            if (int(dx) != expected_dx
                    or any(not re.fullmatch("[A-Z0-9_]+", v)
                           for v in (ground, feet, head))
                    or any(v not in ("0", "1")
                           for v in (solid, pass_feet, pass_head))):
                raise ValueError("invalid native corridor")
            samples.append({
                "dx": expected_dx,
                "ground": ground, "ground_solid": solid == "1",
                "feet": feet, "feet_passable": pass_feet == "1",
                "head": head, "head_passable": pass_head == "1",
            })
        if len(samples) != 4:
            raise ValueError("incomplete native corridor")
    except (ValueError, OverflowError) as exc:
        raise M02DevRejected("invalid native World seed/pose/corridor source") from exc
    return {
        "source": "PAPER_FIRST_LIVING_PLAYER_TICK",
        "native_world_seed": seed,
        "native_world_full_time": full_time,
        "native_first_tick_pose": pose,
        "local_plus_x_corridor": samples,
        "all_four_columns_ground_solid_and_clear": all(
            x["ground_solid"] and x["feet_passable"] and x["head_passable"]
            for x in samples
        ),
        "native_first_tick_pre_move_boundary_proven": False,
        "dynamic_collision_excluded": False,
        "paired_same_spawn_and_pose": "NOT_TESTED_ACROSS_ARMS",
    }



def _v7_native_motion_tick_trace(content: str) -> dict:
    """Validate *observed* Paper movement packets and native World times.

    This does NOT time-attest the Mineflayer control-on/clear commands:
    server tick observations and client control issuance are distinct sources.
    Only invoked for new controlled-pose DEV, not old frozen V7 evidence.
    """
    prefix = "M02_DEV_MOTION "
    rows = [line.split(prefix, 1)[1].split()
            for line in content.splitlines() if prefix in line]
    if not rows or len(rows) > 300:
        raise M02DevRejected("missing/excess native tick-stamped motion source")
    required = {
        "id", "reason", "blocks", "billed", "cumulative_blocks",
        "cumulative_billed", "from_x", "from_y", "from_z", "to_x",
        "to_y", "to_z", "world_full_time",
    }
    packets = []
    for expected_id, row in enumerate(rows, 1):
        fields = {}
        for item in row:
            if "=" not in item:
                raise M02DevRejected("malformed native motion tick token")
            key, value = item.split("=", 1)
            if key in fields or not value:
                raise M02DevRejected("duplicated native motion tick token")
            fields[key] = value
        if set(fields) not in (required, required | {"world", "marker_id"}) or fields["reason"] != "WALK":
            raise M02DevRejected("incomplete or non-WALK native motion tick source")
        try:
            packet_id = int(fields["id"])
            world_tick = int(fields["world_full_time"])
            values = {key: float(fields[key]) for key in (
                "blocks", "billed", "cumulative_blocks", "cumulative_billed",
                "from_x", "from_y", "from_z", "to_x", "to_y", "to_z",
            )}
        except (ValueError, OverflowError) as exc:
            raise M02DevRejected("invalid native motion tick number") from exc
        if (packet_id != expected_id or world_tick < 0
                or not all(math.isfinite(v) for v in values.values())
                or min(values["blocks"], values["billed"],
                       values["cumulative_blocks"],
                       values["cumulative_billed"]) < 0):
            raise M02DevRejected("invalid packet ID, World tick or motion values")
        dist = math.hypot(
            values["to_x"] - values["from_x"],
            values["to_z"] - values["from_z"],
        )
        if (dist <= 0 or dist > 1 or abs(dist - values["blocks"]) > 1e-8):
            raise M02DevRejected("native motion distance/coordinate mismatch")
        if packets:
            previous = packets[-1]
            if world_tick < previous["world_tick"]:
                raise M02DevRejected("regressed native motion World tick")
            if any(abs(values["from_" + axis] -
                       previous["to"][axis]) > 1e-6
                   for axis in ("x", "y", "z")):
                raise M02DevRejected("discontinuous native motion packet position")
        packets.append({
            "id": packet_id,
            "world_tick": world_tick,
            "blocks": values["blocks"],
            "billed": values["billed"],
            "from": {axis: values["from_" + axis] for axis in ("x", "y", "z")},
            "to": {axis: values["to_" + axis] for axis in ("x", "y", "z")},
        })
        if (abs(values["cumulative_blocks"] -
                sum(p["blocks"] for p in packets)) > 1e-7
                or abs(values["cumulative_billed"] -
                       sum(p["billed"] for p in packets)) > 1e-7):
            raise M02DevRejected("native motion cumulative source mismatch")
    counts = {}
    for packet in packets:
        tick = str(packet["world_tick"])
        counts[tick] = counts.get(tick, 0) + 1
    return {
        "source": "ACTUAL_PAPER_PLAYER_MOVE_EVENT_WORLD_FULL_TIME",
        "packet_count": len(packets),
        "first_motion_world_tick": packets[0]["world_tick"],
        "last_motion_world_tick": packets[-1]["world_tick"],
        "world_tick_packet_counts": counts,
        "packet_trace": packets,
        "total_horizontal_path_blocks": sum(x["blocks"] for x in packets),
        "total_walk_exhaustion": sum(x["billed"] for x in packets),
        "native_control_on_world_tick_attested": False,
        "native_control_off_world_tick_attested": False,
        "same_duration_across_arms_attested": False,
        "observed_server_packet_timing_not_client_control_timing": True,
    }



async def _s50_p1_source_wait_window(server, paper_log: Path, marker_id: str) -> None:
    """S-owned post-OUTCOME Paper observation only, NEVER apply P1 recovery."""
    if (re.fullmatch(r"[A-Za-z0-9_-]{1,128}", marker_id) is None
            or server.returncode is not None or server.stdin is None):
        raise M02DevRejected("foreign P1 WAIT window / disconnected Paper")
    _command(server, f"relaydevwait {marker_id}")
    await server.stdin.drain()
    for _ in range(150):
        if not paper_log.is_file():
            raise M02DevRejected("missing original Paper WAIT window")
        original = paper_log.read_text(encoding="utf-8")
        started = [x for x in original.splitlines()
                   if "S50_DEV_WAIT_BEGIN " in x and
                   f"marker_id={marker_id} " in x]
        frames = [x for x in original.splitlines()
                  if "S50_DEV_WAIT_TICK " in x and
                  f"marker_id={marker_id} " in x]
        if len(started) > 1 or len(frames) > 8:
            raise M02DevRejected("duplicate/overlong Paper WAIT source")
        if len(started) == 1 and len(frames) == 8:
            return
        await asyncio.sleep(0.05)
    raise M02DevRejected("8 observed Paper WAIT source ticks missing")


_V7_PHASES = ("PRE_FORWARD", "POST_FORWARD", "PRE_CLEAR", "POST_CLEAR")


async def _v7_source_phase_command(server, server_log: Path, marker_id: str,
                                   phase: str) -> None:
    """One console-only Paper World-tick marker; no new Action authority."""
    if (phase not in _V7_PHASES
            or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", marker_id) is None
            or server.returncode is not None or server.stdin is None):
        raise M02DevRejected("invalid DEV Paper phase marker host")
    _command(server, f"relaydevphase {marker_id} {phase}")
    await server.stdin.drain()
    prefix = "M02_DEV_S50_PHASE "
    for _ in range(80):
        if not server_log.is_file():
            raise M02DevRejected("Paper phase original server log missing")
        entries = [
            x.split(prefix, 1)[1]
            for x in server_log.read_text(encoding="utf-8").splitlines()
            if prefix in x
        ]
        matching = [
            x for x in entries
            if f"marker_id={marker_id} phase={phase} " in x
        ]
        if len(matching) > 1:
            raise M02DevRejected("duplicate Paper phase source marker")
        if len(matching) == 1:
            return
        await asyncio.sleep(0.05)
    raise M02DevRejected("Paper phase marker not acknowledged by server")



_V7_GATE_DELTA_TICKS = 6


async def _v7_wait_clock_gate_source(server_log: Path, marker_id: str) -> None:
    """Await an actual scheduled Paper World callback, not host-duration sleep."""
    if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", marker_id) is None:
        raise M02DevRejected("unsafe Paper World clock gate marker")
    prefix = "M02_DEV_S50_CLOCK_GATE "
    invalid = "M02_DEV_S50_CLOCK_GATE_INVALID "
    for _ in range(120):
        if not server_log.is_file():
            raise M02DevRejected("Paper World clock gate original log missing")
        content = server_log.read_text(encoding="utf-8")
        if any(invalid in x and "marker_id=" + marker_id + " " in x
               for x in content.splitlines()):
            raise M02DevRejected("Paper World clock gate rejected by server")
        candidates = [
            x for x in content.splitlines()
            if prefix in x and "marker_id=" + marker_id + " " in x
        ]
        if len(candidates) > 1:
            raise M02DevRejected("duplicate Paper clock gate original")
        if len(candidates) == 1:
            return
        await asyncio.sleep(0.05)
    raise M02DevRejected("scheduled Paper World clock gate missing")


def _v7_clock_gate_source(content: str, marker_id: str, phase: dict) -> dict:
    """Read one server tick gate; control effects remain separately unproven."""
    prefix = "M02_DEV_S50_CLOCK_GATE "
    rows = [x.split(prefix, 1)[1] for x in content.splitlines()
            if prefix in x]
    if len(rows) != 1:
        raise M02DevRejected("missing/duplicate Paper clock gate source")
    fields = {}
    for token in rows[0].split():
        if "=" not in token:
            raise M02DevRejected("malformed Paper clock gate field")
        key, value = token.split("=", 1)
        if key in fields or not value:
            raise M02DevRejected("duplicate Paper clock gate field")
        fields[key] = value
    if (set(fields) != {
            "marker_id", "scheduler_delay", "target_world_delta",
            "base_full_time",
            "reached_full_time", "player_tick", "x", "y", "z"}
            or fields["marker_id"] != marker_id
            or marker_id != phase["marker_id"]):
        raise M02DevRejected("foreign/incomplete Paper clock gate")
    try:
        delay = int(fields["scheduler_delay"])
        delta = int(fields["target_world_delta"])
        base = int(fields["base_full_time"])
        reached = int(fields["reached_full_time"])
        player_tick = int(fields["player_tick"])
        xyz = {a: float(fields[a]) for a in ("x", "y", "z")}
    except (ValueError, OverflowError) as exc:
        raise M02DevRejected("invalid Paper clock gate numeric source") from exc
    phases = phase["server_world_ticks"]
    if (delay != 7 or delta != _V7_GATE_DELTA_TICKS or base < 0
            or base != phases["POST_FORWARD"]
            or reached - base != delta or player_tick < 0
            or not all(math.isfinite(v) for v in xyz.values())
            or not (phases["POST_FORWARD"] <= reached
                    <= phases["PRE_CLEAR"])):
        raise M02DevRejected("Paper clock gate time/phase/source mismatch")
    return {
        "source": "PAPER_SCHEDULED_DEV_GATE_ORIGINAL",
        "marker_id": marker_id,
        "scheduler_delay_ticks": delay,
        "target_world_fulltime_delta": delta,
        "observed_world_fulltime_delta": reached - base,
        "base_post_forward_world_tick": base,
        "observed_callback_world_tick": reached,
        "callback_player_tick": player_tick,
        "callback_position": xyz,
        "phase_pre_clear_world_tick": phases["PRE_CLEAR"],
        "phase_pre_clear_lag_ticks": phases["PRE_CLEAR"] - reached,
        "host_walltime_sleep_replaced": True,
        "server_effective_motion_control_stop_attested": False,
        "cross_arm_identical_actual_motion_attested": False,
        "qualified": False,
        "science_go": False,
    }


def _v7_phase_bracket_source(content: str, marker_id: str) -> dict:
    """Verify four actual server markers bracketing S50 *client commands*.

    Cross-machine command receipt intervals are not the exact server-effective
    movement-control intervals. No admission to V7 matched-duration SCIENCE.
    """
    if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", marker_id) is None:
        raise M02DevRejected("unsafe source marker ID")
    prefix = "M02_DEV_S50_PHASE "
    events = []
    for line in content.splitlines():
        if prefix not in line:
            continue
        fields = {}
        for token in line.split(prefix, 1)[1].split():
            if "=" not in token:
                raise M02DevRejected("malformed Paper phase source")
            key, value = token.split("=", 1)
            if key in fields or not value:
                raise M02DevRejected("duplicated Paper phase source field")
            fields[key] = value
        if set(fields) != {
                "marker_id", "phase", "world_full_time", "player_tick",
                "x", "y", "z"} and set(fields) != {
                "marker_id", "phase", "world_full_time", "player_tick",
                "x", "y", "z", "world", "packets", "blocks", "billed"} or fields["marker_id"] != marker_id:
            raise M02DevRejected("foreign/incomplete Paper phase source")
        try:
            tick = int(fields["world_full_time"])
            player_tick = int(fields["player_tick"])
            xyz = {p: float(fields[p]) for p in ("x", "y", "z")}
        except (ValueError, OverflowError) as exc:
            raise M02DevRejected("invalid Paper phase numeric source") from exc
        if (tick < 0 or player_tick < 0
                or not all(math.isfinite(v) for v in xyz.values())):
            raise M02DevRejected("nonfinite Paper phase World source")
        events.append({"phase": fields["phase"], "world_tick": tick,
                       "player_tick": player_tick, "position": xyz})
    if tuple(x["phase"] for x in events) != _V7_PHASES:
        raise M02DevRejected("missing/reordered/duplicated Paper S50 phases")
    if any(events[i]["world_tick"] < events[i-1]["world_tick"]
           or events[i]["player_tick"] < events[i-1]["player_tick"]
           for i in range(1, len(events))):
        raise M02DevRejected("Paper S50 phase World clock regression")
    ticks = {x["phase"]: x["world_tick"] for x in events}
    return {
        "source": "PAPER_CONSOLE_CALLBACK_PHASE_BOUNDARY_WORLD_TICKS",
        "marker_id": marker_id,
        "ordered_originals": events,
        "server_world_ticks": ticks,
        "client_forward_command_bracket_world_ticks": [
            ticks["PRE_FORWARD"], ticks["POST_FORWARD"]],
        "client_clear_command_bracket_world_ticks": [
            ticks["PRE_CLEAR"], ticks["POST_CLEAR"]],
        "between_post_forward_and_pre_clear_marker_ticks":
            ticks["PRE_CLEAR"] - ticks["POST_FORWARD"],
        "same_world_tick_control_effect_attested": False,
        "server_effective_forward_start_tick_attested": False,
        "server_effective_forward_stop_tick_attested": False,
        "cross_arm_fixed_control_duration_attested": False,
        "phase_marker_is_observation_only": True,
    }


async def _v7_wait_source_tick(server_log: Path, arm: str, *,
                               minimum_player_basal_ticks: int = 200,
                               expected_world_seed: int = 61021,
                               require_native_motion_tick_trace: bool = False,
                               phase_marker_id: str | None = None,
                               require_paper_clock_gate: bool = False,
                               require_tick_motion_meter: bool = False) -> dict:
    """Bounded original Paper plugin sample gate; DEV only, not V science.

    Sampled tick counts the plugin's living-player callbacks, not host time,
    nor an independently time-matched experimental bracket.
    """
    from adapters.mineflayer.m02_paper_dev.v7_paired_config import ARMS

    if arm not in ARMS or minimum_player_basal_ticks != 200:
        raise M02DevRejected("unregistered V7 tick sample")
    samples: list[tuple[int, float, float]] = []
    for _ in range(300):
        if not server_log.is_file():
            raise M02DevRejected("V7 original Paper source log absent")
        content = server_log.read_text(encoding="utf-8")
        samples = []
        for line in content.splitlines():
            match = re.search(
                r"M02_DEV_BODY sampled_tick=(\d+).*?exhaustion=([0-9.eE+\-]+)"
                r".*?motion_blocks=([0-9.eE+\-]+)", line,
            )
            if match:
                samples.append((int(match.group(1)), float(match.group(2)),
                                float(match.group(3))))
        if samples and samples[-1][0] >= minimum_player_basal_ticks:
            break
        await asyncio.sleep(0.15)
    else:
        raise M02DevRejected("V7 source never reached 200 native player ticks")
    pairs = [
        (float(b.group(1)), float(q.group(1)))
        for line in content.splitlines()
        if "M02_DEV_MOTION " in line and " reason=WALK " in line
        for b in [re.search(r"\bblocks=([0-9.eE+\-]+)", line)]
        for q in [re.search(r"\bbilled=([0-9.eE+\-]+)", line)]
        if b is not None and q is not None
    ]
    total_blocks = sum(x for x, _ in pairs)
    total_charge = sum(x for _, x in pairs)
    if not (0.5 < total_blocks < 2
            and pairs and all(x > 0 and y >= 0 for x, y in pairs)
            and abs(total_charge - (0 if require_tick_motion_meter
                                    else total_blocks * 0.01 * ARMS[arm][1])) < 1e-7):
        raise M02DevRejected("V7 source WALK physical path/charge mismatch")
    if not samples or samples[0][0] != 1:
        raise M02DevRejected("V7 missing first native player tick sample")
    if samples[-1][0] < 200 or sorted(t for t, _, _ in samples) != [
        t for t, _, _ in samples
    ]:
        raise M02DevRejected("V7 non-monotone Paper living-player tick")
    direct = _v7_direct_basal_write_receipt(content, arm)
    world = _v7_world_geometry_source(content, expected_seed=expected_world_seed)
    trace = (_v7_native_motion_tick_trace(content)
             if require_native_motion_tick_trace else None)
    phase = (_v7_phase_bracket_source(content, phase_marker_id)
             if phase_marker_id is not None else None)
    if require_native_motion_tick_trace and phase is None:
        raise M02DevRejected("controlled V7 missing S50 phase source")
    gate = (_v7_clock_gate_source(content, phase_marker_id, phase)
            if require_paper_clock_gate and phase is not None else None)
    if require_paper_clock_gate and gate is None:
        raise M02DevRejected("controlled V7 native World clock gate missing")
    tick_meter = None
    if require_tick_motion_meter:
        from adapters.mineflayer.m02_paper_dev.s50_boundary import tick_motion_source
        tick_meter = tick_motion_source(content, phase, 0.01 * ARMS[arm][1])
    if trace is not None and phase is not None and (
            trace["first_motion_world_tick"] <
            phase["server_world_ticks"]["PRE_FORWARD"]):
        raise M02DevRejected("movement preceded S50 source phase")
    if trace is not None and (
            trace["packet_count"] != len(pairs)
            or abs(trace["total_horizontal_path_blocks"] - total_blocks) > 1e-7
            or abs(trace["total_walk_exhaustion"] - total_charge) > 1e-7):
        raise M02DevRejected("native tick-stamped packet/path mismatch")
    return {
        "classification": "S_V7_PAPER_DEV_OBSERVED_SOURCE_SHAPE_ONLY",
        "direct_basal_source": direct,
        "native_motion_tick_trace": trace,
        "s50_server_phase_brackets": phase,
        "s50_paper_scheduled_clock_gate": gate,
        "s50_tick_motion_meter": tick_meter,
        "native_world_geometry_source": world,
        "arm": arm, "physical_java_world": True,
        "source_player_ticks_minimum": minimum_player_basal_ticks,
        "last_sampled_player_tick": samples[-1][0],
        "source_samples": samples,
        "observed_motion_packets": len(pairs),
        "observed_motion_path_blocks": total_blocks,
        "observed_motion_debit": total_charge,
        "candidate_basal_rate_per_tick": 0.001 * ARMS[arm][0],
        "candidate_walk_rate_per_path_block": 0.01 * ARMS[arm][1],
        "basal_source_charge_inferred_not_independently_attested": False,
        "basal_write_inputs_directly_source_logged": True,
        "basal_native_food_meter_effect_independently_quantified": False,
        "exact_200_tick_move_phase_bracket_attested": False,
        "qualified": False, "science_go": False,
    }


async def _save_and_capture_initial_world(
    server, world: Path, evidence_root: Path,
) -> dict:
    """Create a pre-Action immutable raw World seed receipt in isolated DEV/QUAL.

    Paper may not materialize level.dat by the server-ready marker. A flush
    happens BEFORE the first issued World Action and while S owns the World.
    """
    level = world / "s31a-ephemeral" / "level.dat"
    if (server.returncode is not None or server.stdin is None
            or not evidence_root.is_dir()
            or (evidence_root / "initial_world_level.dat").exists()):
        raise M02DevRejected("not an owned pre-Action World snapshot scope")
    _command(server, "save-all flush")
    await server.stdin.drain()
    for _ in range(100):
        if level.is_file() and not level.is_symlink():
            info = level.stat()
            if 16 <= info.st_size <= 16 * 1024 * 1024:
                raw = level.read_bytes()
                after = level.stat()
                if (len(raw) != info.st_size
                        or (info.st_ino, info.st_mtime_ns) !=
                           (after.st_ino, after.st_mtime_ns)):
                    raise M02DevRejected("initial level.dat changed during read")
                target = evidence_root / "initial_world_level.dat"
                with target.open("xb") as output:
                    output.write(raw)
                digest = hashlib.sha256(raw).hexdigest()
                if _sha256(target) != digest:
                    raise M02DevRejected("snapshot original copy mismatch")
                return {
                    "source_world_path": "s31a-ephemeral/level.dat",
                    "sha256": digest,
                    "size_bytes": len(raw),
                    "snapshot_phase": "AFTER_SERVER_READY_SAVE_FLUSH_BEFORE_ACTION",
                }
        await asyncio.sleep(0.15)
    raise M02DevRejected("pre-Action level.dat absent after save-all flush")


def qualification_asset_preflight(asset_root: Path) -> dict:
    """Read-only S source admission packet; NEVER launches or authorizes World.

    The four bytes are already pinned by an independent R preworld profile.
    Seed/World/STOP/source qualification remains absent even on a full match.
    """
    if (not isinstance(asset_root, Path)
            or not asset_root.is_absolute()
            or not asset_root.is_dir()
            or asset_root.is_symlink()
            or any(parent.is_symlink() for parent in asset_root.parents)):
        raise M02DevRejected("isolated absolute non-symlink asset root required")
    if {entry.name for entry in asset_root.iterdir()} != set(PAPER_PREWORLD_ASSET_PINS):
        raise M02DevRejected("exact four pinned Paper input files required")
    measured = {}
    for name, digest in sorted(PAPER_PREWORLD_ASSET_PINS.items()):
        asset = asset_root / name
        if not asset.is_file() or asset.is_symlink() or not stat.S_ISREG(asset.lstat().st_mode):
            raise M02DevRejected("unsafe Paper preworld source asset")
        before = asset.stat()
        limit = 200_000_000 if name.endswith(".jar") else 65_536
        if not 0 < before.st_size <= limit:
            raise M02DevRejected("invalid Paper asset size")
        actual = _sha256(asset)
        after = asset.stat()
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                or actual != digest):
            raise M02DevRejected("changed or non-pinned Paper asset: " + name)
        measured[name] = actual
    config = (asset_root / "config.yml").read_text(encoding="utf-8")
    props = (asset_root / "server.properties").read_text(encoding="utf-8")
    if ("dev-enabled: true" not in config
            or "target-player: RelaySelf" not in config
            or "online-mode=false" not in props
            or "gamemode=survival" not in props):
        raise M02DevRejected("Paper test plugin or World mode does not match")
    # No validated source grant is possible from four pinned assets alone.
    return {
        "classification": "S_M02_PAPER_QUALIFICATION_ASSET_PREFLIGHT_ONLY",
        "preworld_profile": PAPER_PREWORLD_PROFILE,
        "pinned_historical_s_producer_head":
            "52d9bbf1b4ee2e8ff810d213e36d0caf347652ee",
        "pinned_reference_m_head": "4c2f549c6b9ed3fbe2ee04230526ac5577da8feb",
        "verified_assets_sha256": measured,
        "asset_root": str(asset_root),
        "new_paper_world": "NOT_CREATED",
        "new_world_snapshot_seed": "NOT_BOUND",
        "native_originals": "NOT_CAPTURED",
        "runtime_stop_pid_port": "NOT_ATTESTED",
        "qualification_physical_start_permission": "NOT_GRANTED",
        "physical_world_launches": 0,
        "qualified": False,
        "science_go": False,
        "production_go": False,
        "virtual_m0_ledger_used": False,
        "cognition_cost_enabled": False,
        "rates_ecologically_calibrated": False,
    }


async def run(
    output_dir: Path, paper_jar: Path, paper_sha: str,
    plugin_jar: Path, plugin_sha: str, *, confirmation: str,
    forage_dev: bool = False,
    b1_retention: bool | None = None,
    v7_arm: str | None = None,
    v7_seed: int | None = None,
    v7_controlled_calibration_dev: bool = False,
    v7_server_clock_calibration_dev: bool = False,
    v7_tick_meter_dev: bool = False,
    v7_p1_wait_evidence_dev: bool = False,
) -> int:
    report: dict = {
        "milestone": "M0.2_PAPER_DEV",
        "status": "BLOCKED",
        "classification": "DEV_ONLY",
        "qualified": False,
        "science_go": False,
        "production_go": False,
        "physical_world": "NOT_RUN",
        "m0_virtual_ledger_used": False,
        "steak": "cooked_beef",
        "scenario": (
            f"V7_{v7_arm}_PHYSICS_DEV" if v7_arm is not None else
            f"PAPER_B1_{'ON' if b1_retention else 'OFF'}_DEV"
            if b1_retention is not None else
            "PAPER_NATIVE_GROUND_FORAGE" if forage_dev else "PAPER_STEAK_FIXTURE"
        ),
        "minecraft_version": MINECRAFT_VERSION,
        "v7_calibration_controlled_dev": v7_controlled_calibration_dev,
        "v7_server_clock_calibration_dev": v7_server_clock_calibration_dev,
        "v7_tick_meter_dev": v7_tick_meter_dev,
        "v7_calibration_not_existing_science_roster": True,
    }
    root = None
    server = collector = session = native_file = commands_file = b1_memory_file = None
    rc = 2
    try:
        if confirmation != M02_CONFIRM:
            raise M02DevRejected("explicit disposable-Paper DEV confirmation missing")
        if type(v7_controlled_calibration_dev) is not bool:
            raise M02DevRejected("controlled calibration requires bool")
        if v7_controlled_calibration_dev and v7_arm is None:
            raise M02DevRejected("controlled calibration requires V7 arm")
        if type(v7_server_clock_calibration_dev) is not bool or (
                v7_server_clock_calibration_dev
                and not v7_controlled_calibration_dev):
            raise M02DevRejected("server clock gate requires controlled V7 DEV")
        if type(v7_tick_meter_dev) is not bool or (
                v7_tick_meter_dev and not v7_server_clock_calibration_dev):
            raise M02DevRejected("tick metering requires server-clock V7 DEV")
        if type(v7_p1_wait_evidence_dev) is not bool or (
                v7_p1_wait_evidence_dev and not v7_tick_meter_dev):
            raise M02DevRejected("P1 WAIT observation requires tick meter DEV")
        if v7_arm is not None:
            from adapters.mineflayer.m02_paper_dev.v7_paired_config import ARMS
            if (v7_arm not in ARMS or type(v7_seed) is not int
                    or v7_seed not in (61021, 61022, 61023, 61024)
                    or forage_dev or b1_retention is not None):
                raise M02DevRejected("V7 requires registered arm/seed, no food/forage/B1")
        elif v7_seed is not None:
            raise M02DevRejected("V7 seed requires a registered arm")
        if b1_retention is not None and (type(b1_retention) is not bool or not forage_dev):
            raise M02DevRejected("Paper B1 requires explicit forage DEV and retention bool")
        if (not output_dir.is_absolute() or output_dir.exists()
                or output_dir.is_symlink() or output_dir.parent.is_symlink()
                or not output_dir.parent.is_dir()
                or os.environ.get("NODE_OPTIONS")):
            raise M02DevRejected("fresh absolute owned output root and native Node required")
        paper_jar = _fresh_asset(paper_jar, paper_sha)
        plugin_jar = _fresh_asset(plugin_jar, plugin_sha)
        if not _port_free():
            raise M02DevRejected("existing Minecraft port must not be disturbed")
        output_dir.mkdir()
        server_log = output_dir / "paper_server.log"
        native_file = (output_dir / "original_native.jsonl").open("xb")
        commands_file = (output_dir / "owner_commands.jsonl").open("xb")
        if b1_retention is not None:
            b1_memory_file = (output_dir / "paper_b1_memory_original.jsonl").open("xb")
        (output_dir / "owned-worlds").mkdir()
        root = tempfile.TemporaryDirectory(prefix="m02-paper-dev-",
                                            dir=str(output_dir / "owned-worlds"))
        world = Path(root.name)
        jar = world / "paper-1.21.8.jar"
        shutil.copyfile(paper_jar, jar)
        _write_config(world)
        # Override generic S31A creative settings for real food/exhaustion.
        props = world / "server.properties"
        props.write_text(props.read_text(encoding="utf-8")
                         .replace("gamemode=creative", "gamemode=survival")
                         .replace("motd=RelaySelf S31A disposable loopback qualification",
                                  "motd=RelaySelf M0.2 isolated DEV"), encoding="utf-8")
        if v7_arm is not None:
            with props.open("a", encoding="utf-8") as destination:
                destination.write(f"level-seed={v7_seed}\n")
        plugin_dir = world / "plugins"
        plugin_dir.mkdir()
        shutil.copyfile(plugin_jar, plugin_dir / "relay-metabolism-paper-dev.jar")
        conf_dir = plugin_dir / "RelayMetabolismDev"
        conf_dir.mkdir()
        source_conf = PLUGIN_ROOT / "src/main/resources/config.yml"
        config = source_conf.read_text(encoding="utf-8")
        if config.count("dev-enabled: false") != 1:
            raise M02DevRejected("untrusted default plugin config shape")
        if v7_arm is not None:
            from adapters.mineflayer.m02_paper_dev.v7_paired_config import render_arm
            config = render_arm(source_conf.read_bytes(), v7_arm).decode("utf-8")
        else:
            config = config.replace("dev-enabled: false", "dev-enabled: true")
        if v7_tick_meter_dev:
            if config.count("dev-enabled: true") != 1:
                raise M02DevRejected("unexpected DEV config for tick meter")
            config = config.replace("dev-enabled: true",
                                    "dev-enabled: true\ns50-tick-meter-dev: true", 1)
        (conf_dir / "config.yml").write_text(config, encoding="utf-8")
        report.update({
            "paper_sha256": paper_sha,
            "plugin_sha256": plugin_sha,
            "server_properties_sha256": _sha256(props),
            "plugin_config_sha256": _sha256(conf_dir / "config.yml"),
            "source_config_default_disabled": True,
        })
        report["stage"] = "JAVA_PAPER_DISPOSABLE_START"
        server, collector, _ = await _ready_server(world, jar, server_log)
        report["physical_world"] = "STARTED_NEW_DEV_PAPER"
        report["java_pid"] = server.pid
        report["stage"] = "INITIAL_WORLD_PREACTION_SOURCE_CHECKPOINT"
        report["initial_world_receipt"] = await _save_and_capture_initial_world(
            server, world, output_dir)
        report["stage"] = "S51_EXISTING_RECORDED_SOURCE"
        session_type = _recording_session_type(native_file, commands_file)
        session = await session_type.launch(MineflayerLaunchConfig(
            host=SERVER_HOST, port=SERVER_PORT,
            username=BOT_USERNAME, version=MINECRAFT_VERSION,
        ), startup_timeout_s=12)
        await _await_spawn(session)
        report["node_pid"] = session._process.pid
        report["source_session_id"] = session.started.session_id
        assert server.stdin is not None
        _command(server, "gamerule doMobSpawning false")
        _command(server, "gamemode survival RelaySelf")
        await server.stdin.drain()
        if v7_arm is not None:
            controlled_pose = None
            if v7_controlled_calibration_dev:
                controlled_pose = MineflayerPosition(0.5, -60.0, 0.5)
                _command(server, "tp RelaySelf 0.5 -60 0.5 0 0")
                await server.stdin.drain()
                for retry in range(24):
                    probe = await _correlated_observe(
                        session, f"v7-fixedpose-post-tp-{retry:02d}")
                    if all(abs(getattr(probe.snapshot.position, field)
                               - getattr(controlled_pose, field)) <= 1e-3
                           for field in ("x", "y", "z")):
                        break
                    await asyncio.sleep(0.15)
                else:
                    raise M02DevRejected("fixedpose tp not native-observed")
                report["v7_calibration_pose_source"] = {
                    "operator_command": "tp RelaySelf 0.5 -60 0.5 0 0",
                    "native_confirmed_position": asdict(probe.snapshot.position),
                    "native_confirmation_source_seq": probe.seq,
                    "source_session": probe.session_id,
                    "native_yaw_after_tp": "NOT_ATTESTED",
                    "exact_move_tick_phase_attested": False,
                }
            report["stage"] = "V7_PREMOVE_NATIVE_BASELINE"
            observed = await _correlated_observe(session, "v7-pre-move")
            report["v7_initial_body"] = {
                "food": observed.snapshot.food,
                "saturation": observed.snapshot.food_saturation,
                "source_seq": observed.seq,
                "position": asdict(observed.snapshot.position),
                "yaw_pitch_in_native_snapshot": "NOT_EXPOSED",
            }
            report["stage"] = "V7_S50_GOVERNED_SINGLE_MOVE_NO_EAT"
            report["movement"] = await _motor_walk(
                session, expected_start=controlled_pose,
                v7_phase_source=(server, server_log)
                if v7_controlled_calibration_dev else None,
                v7_clock_gate_dev=v7_server_clock_calibration_dev,
                v7_tick_meter_dev=v7_tick_meter_dev,
                v7_tick_meter_walk_rate=0.01 * ARMS[v7_arm][1]
                if v7_tick_meter_dev else None,
                v7_p1_wait_evidence_dev=v7_p1_wait_evidence_dev)
            report["stage"] = "V7_SOURCE_WORLD_TICK_200"
            report["v7_source"] = await _v7_wait_source_tick(
                server_log, v7_arm, minimum_player_basal_ticks=200,
                expected_world_seed=v7_seed,
                require_native_motion_tick_trace=v7_controlled_calibration_dev,
                phase_marker_id=report["movement"]["v7_phase_marker_id"],
                require_paper_clock_gate=v7_server_clock_calibration_dev,
                require_tick_motion_meter=v7_tick_meter_dev)
            final = await _correlated_observe(session, "v7-final-no-food")
            report["v7_final_body"] = {
                "food": final.snapshot.food,
                "saturation": final.snapshot.food_saturation,
                "source_seq": final.seq,
                "position": asdict(final.snapshot.position),
                "yaw_pitch_in_native_snapshot": "NOT_EXPOSED",
            }
            report["v7_world_geometry_attested"] = False
            report["v7_collision_explanation"] = "UNKNOWN"
            report["v7_pairing_005_blocks_proven"] = False
            report["v7_arm"] = v7_arm
            report["v7_seed"] = v7_seed
            report["v7_food_introduced_by_runner"] = False
            report["v7_real_science_trials"] = 0
        elif forage_dev:
            from adapters.mineflayer.m02_paper_dev.paper_foraging_dev import (
                paper_ground_forage,
            )

            report["stage"] = "PAPER_L0_GROUND_SEEK"
            progress: dict = {}
            report["ground_foraging_attempt"] = progress
            report["ground_foraging"] = await paper_ground_forage(
                session, server, issuer=_issue, provenance=_p,
                trace=progress,
                b1_retention=b1_retention,
                b1_memory_original=b1_memory_file,
            )
            report["stage"] = "S51_GOVERNED_PICKED_STEAK_EAT"
            report["eating"] = await _native_steak(session, server, preowned=True)
        else:
            report["stage"] = "S50_GOVERNED_ONE_BLOCK_MOVE"
            report["movement"] = await _motor_walk(session)
            report["stage"] = "S51_GOVERNED_STEAK_EAT"
            report["eating"] = await _native_steak(session, server)
        report["stage"] = "PHYSICAL_SOURCE_COLLECTION"
        report["owner_status"] = "PASS"
        rc = 0
    except Exception as exc:
        report["owner_status"] = "BLOCKED" if isinstance(exc, (M02DevRejected, OSError)) else "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        rc = 2 if report["owner_status"] == "BLOCKED" else 1
    finally:
        if session is not None:
            try:
                report["node_exit"] = await session.shutdown(timeout_s=12)
                if report["node_exit"] != 0:
                    raise M02DevRejected("nonzero Node shutdown")
            except Exception as exc:
                report["cleanup_failure"] = "node: " + str(exc)
                rc = 1
                report["owner_status"] = "FAIL"
                try:
                    await session.terminate()
                except Exception:
                    pass
        if server is not None:
            try:
                await _shutdown_server(server, collector)
                report["java_exit"] = server.returncode
                if server.returncode != 0:
                    raise M02DevRejected("nonzero Paper shutdown")
            except Exception as exc:
                report["cleanup_failure"] = "java: " + str(exc)
                rc = 1
                report["owner_status"] = "FAIL"
        for stream in (native_file, commands_file, b1_memory_file):
            if stream is not None:
                stream.close()
        if root is not None:
            root.cleanup()
        report["port_released_after_shutdown"] = _port_free()
        if not report["port_released_after_shutdown"] and server is not None:
            report["owner_status"] = "FAIL"
            rc = 1
        if output_dir.is_dir():
            server_log = output_dir / "paper_server.log"
            if rc == 0:
                try:
                    if v7_arm is not None:
                        report["paper_native_diagnostics"] = report["v7_source"]
                    else:
                        report["paper_native_diagnostics"] = _read_world_receipts(
                            server_log, max_path_blocks=16 if forage_dev else 2,
                            allow_packet_only_walk=forage_dev,
                        )
                    if v7_server_clock_calibration_dev:
                        from adapters.mineflayer.m02_paper_dev.s50_boundary import (
                            reconcile,
                            reconcile_tick_meter,
                            verify_native,
                        )
                        from adapters.mineflayer.m02_paper_dev.v7_paired_config import ARMS
                        movement = report["movement"]
                        verify_native(
                            [json.loads(x) for x in (output_dir / "original_native.jsonl").read_text().splitlines()],
                            [json.loads(x) for x in (output_dir / "owner_commands.jsonl").read_text().splitlines()],
                            movement)
                        report["s50_physical_boundary"] = (
                            reconcile_tick_meter if v7_tick_meter_dev else reconcile
                        )(server_log.read_text(), movement,
                          walk_rate=0.01 * ARMS[v7_arm][1])
                    report["status"] = "PASS"
                    report["classification"] = "M02_PAPER_DEV_ONLY_PHYSICS_OBSERVED"
                except Exception as exc:
                    report["owner_status"] = "FAIL"
                    report["status"] = "FAIL"
                    report["error"] = f"unverified World effects: {exc}"
                    rc = 1
            else:
                report["status"] = report.get("owner_status", "BLOCKED")
            raw = output_dir / "original_native.jsonl"
            log = output_dir / "paper_server.log"
            report["evidence_hashes"] = {
                x.name: _sha256(x)
                for x in (
                    raw, log, output_dir / "owner_commands.jsonl",
                    output_dir / "s50_action_original.jsonl",
                    output_dir / "paper_b1_memory_original.jsonl",
                ) if x.is_file()
            }
            if b1_retention is not None:
                memory_source = output_dir / "paper_b1_memory_original.jsonl"
                report["b1_memory_original"] = {
                    "path": memory_source.name,
                    "sha256": report["evidence_hashes"].get(memory_source.name),
                    "source_kind": "S_IMMEDIATE_APPEND_BEFORE_NEXT_MOVE_NOT_R_ATTESTED",
                    "retention_enabled": b1_retention,
                }
            (output_dir / "m02_report.json").write_text(
                json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)+"\n",
                encoding="utf-8",
            )
        print("M02_PAPER_DEV_REPORT="+json.dumps(report, sort_keys=True))
    return rc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M0.2 Paper DEV or OFFLINE qualification asset preflight")
    parser.add_argument("--v7-arm", choices=(
        "BASE_ON", "SHAM_ON", "BASAL_ZERO", "WALK_ZERO", "BOTH_ZERO"))
    parser.add_argument("--v7-seed", type=int)
    parser.add_argument("--v7-controlled-calibration-dev", action="store_true",
                        help="separate fixed-pose Paper DEV, never science")
    parser.add_argument("--v7-server-clock-calibration-dev", action="store_true",
                        help="six-Paper-tick gate in controlled V7 DEV; never science")
    parser.add_argument("--v7-tick-meter-dev", action="store_true",
                        help="new isolated World-tick motion-chord WALK writer; DEV only")
    parser.add_argument("--v7-p1-wait-evidence-dev", action="store_true",
                        help="post-outcome Paper eight-tick inactivity source only; no P1 recovery")
    parser.add_argument("--paper-b1", choices=("on", "off"),
                        help="Paper B1 BLOCKED→Memory/cheap OFF→lateral S50→pickup→EAT DEV")
    parser.add_argument("--forage-dev", action="store_true",
                        help="new disposable Paper-only L0 SEEK→S50 MOVE→pickup→EAT DEV")
    parser.add_argument("--qualification-preflight", action="store_true",
                        help="read-only four-asset S check; NO World start or qualification")
    parser.add_argument("--asset-root", type=Path,
                        help="new isolated directory of four R-pinned candidate assets")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--paper-jar", type=Path)
    parser.add_argument("--paper-sha256")
    parser.add_argument("--plugin-jar", type=Path)
    parser.add_argument("--plugin-sha256")
    parser.add_argument("--confirm")
    args = parser.parse_args(argv)
    if args.qualification_preflight:
        if args.asset_root is None or any(v is not None for v in (
            args.output_dir, args.paper_jar, args.paper_sha256, args.plugin_jar,
            args.plugin_sha256, args.confirm,
            True if args.forage_dev else None,
            args.paper_b1,
            True if args.v7_controlled_calibration_dev else None,
            True if args.v7_server_clock_calibration_dev else None,
            True if args.v7_tick_meter_dev else None,
            args.v7_arm, args.v7_seed,
        )):
            parser.error("qualification preflight accepts ONLY --asset-root; no DEV/World options")
        try:
            result = qualification_asset_preflight(args.asset_root)
            status = 0
        except (M02DevRejected, OSError, ValueError, UnicodeError) as exc:
            result = {
                "classification": "S_M02_PAPER_QUALIFICATION_ASSET_PREFLIGHT_BLOCKED",
                "reason": f"{type(exc).__name__}: {exc}",
                "physical_world_launches": 0, "qualified": False,
                "science_go": False, "production_go": False,
            }
            status = 2
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return status
    if args.asset_root is not None:
        parser.error("--asset-root requires --qualification-preflight")
    if args.v7_arm is not None and (
            args.v7_seed not in (61021, 61022, 61023, 61024)
            or args.forage_dev or args.paper_b1 is not None):
        parser.error("V7 DEV requires allowed paired seed/arm, no forage or B1")
    if args.v7_arm is None and args.v7_seed is not None:
        parser.error("--v7-seed requires --v7-arm")
    if args.v7_controlled_calibration_dev and args.v7_arm is None:
        parser.error("--v7-controlled-calibration-dev requires --v7-arm")
    if (args.v7_server_clock_calibration_dev
            and not args.v7_controlled_calibration_dev):
        parser.error("--v7-server-clock-calibration-dev requires controlled V7 DEV")
    if args.v7_tick_meter_dev and not args.v7_server_clock_calibration_dev:
        parser.error("--v7-tick-meter-dev requires --v7-server-clock-calibration-dev")
    if args.v7_p1_wait_evidence_dev and not args.v7_tick_meter_dev:
        parser.error("--v7-p1-wait-evidence-dev requires --v7-tick-meter-dev")
    if args.paper_b1 is not None and not args.forage_dev:
        parser.error("--paper-b1 requires --forage-dev")
    if any(v is None for v in (
        args.output_dir, args.paper_jar, args.paper_sha256,
        args.plugin_jar, args.plugin_sha256, args.confirm,
    )):
        parser.error("DEV requires explicit output, verified jars and confirmation")
    return asyncio.run(run(
        args.output_dir, args.paper_jar, args.paper_sha256,
        args.plugin_jar, args.plugin_sha256, confirmation=args.confirm,
        forage_dev=args.forage_dev,
        b1_retention=(args.paper_b1 == "on" if args.paper_b1 is not None else None),
        v7_arm=args.v7_arm, v7_seed=args.v7_seed,
        v7_controlled_calibration_dev=args.v7_controlled_calibration_dev,
        v7_server_clock_calibration_dev=args.v7_server_clock_calibration_dev,
        v7_tick_meter_dev=args.v7_tick_meter_dev,
        v7_p1_wait_evidence_dev=args.v7_p1_wait_evidence_dev,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
