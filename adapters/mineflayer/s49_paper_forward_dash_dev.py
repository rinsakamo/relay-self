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
from pathlib import Path
from unittest.mock import patch

from adapters.mineflayer import normal_action as action_owner
from adapters.mineflayer import s49_normal_session_real_ci as original
from adapters.mineflayer.b0_energy_bridge import DashM0InvoiceDev
from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import _fresh_asset
from adapters.mineflayer.s49_paper_world_first_dev import (
    _await_dash_dev_line,
    _fresh_output,
    offline_uuid,
)
from experiments.fatigue_p1 import FatigueProfile, initial_state
from experiments.p1_gait_dev import (
    GaitTickDev,
    advance_gait_dev,
    p1_motor_power_limit_dev,
)

CONFIRM = "S49-P1-DEV-DISPOSABLE-PAPER-WORLD"


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


def audit_native_paper_p1_dev(raw: str, *, action_id: str, session_id: str) -> dict:
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
    cfg = FatigueProfile(enabled=True, initial=0.6)
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
    if len(boosts) < 3 or boosts[0] - boosts[-1] < 0.01:
        raise ForwardDashDevRejected("P1 power fade unobserved")
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
            if (applied != (packet or motion) or (packet and motion)
                    or source != (
                        "PACKET" if packet else "MOTION_PROJECTION"
                        if motion else "NONE"
                    )):
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
            != sum(row[2] for row in rows)):
        raise ForwardDashDevRejected("inferred boost source count mismatch")
    speeds = [row[3] for row in rows if row[3] is not None]
    return {
        "paper_motion_inferred_boost_ticks": sum(row[2] for row in rows),
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
) -> int:
    if (
        confirm != CONFIRM or os.environ.get("NODE_OPTIONS")
        or os.environ.get("S49_REAL_SERVER_CI") != "1"
        or os.environ.get("S49_FORWARD_MOTOR_DEV_ONLY") != "1"
        or os.environ.get("S49_SPRINT_MOTOR_DEV_ONLY") != "1"
        or type(p1_live_dev) is not bool
        or type(m0_live_dev) is not bool
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
    report: dict = {"status": "FAIL_CLOSED", "classification": "DEV_ONLY",
                    "qualification_go": False, "science_go": False}
    subject = {"server": None, "session": None, "action_id": None, "complete": None}
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
            + ("p1-live-dev: true\np1-initial-fatigue: 0.6\n" if p1_live_dev else ""),
            encoding="utf-8"
        )

    async def paper_ready(*args):
        ready = await base_ready(*args)
        subject["server"] = ready[0]
        return ready

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
        try:
            return await base_execute(
                session, command, timeout_s=timeout_s, provenance=provenance,
            )
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
        ):
            rc = await original.qualify(
                original_report, paper_log,
                dev_forward_motor=True, dev_sprint_motor=True,
                dev_m0_dash_invoice=invoice_from_original_outcome if m0_live_dev else None,
            )
        original_bytes = json.loads(original_report.read_text(encoding="utf-8"))
        report["original_s49_rc"] = rc
        report["original_s49_status"] = original_bytes.get("status")
        if rc != 0 or original_bytes.get("status") != "PASS":
            raise ForwardDashDevRejected("original S49 single Action World did not PASS")
        if (original_bytes.get("node_exit") != 0
                or original_bytes.get("server_exit") != 0
                or len(original_bytes["actual_native_actions"]) != 2):
            raise ForwardDashDevRejected("original S49 cleanup/outcome mismatch")
        actions = original_bytes["actual_native_actions"]
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
        if m0_live_dev:
            report["m0_s49_original_owner_postings"] = (
                original_bytes.get("dev_m0_dash_postings", [])
            )
            report["m0_s49_original_owner_remaining"] = (
                original_bytes.get("dev_m0_dash_energy_remaining")
            )
        if p1_live_dev:
            report["p1_paper_motor_dev"] = audit_native_paper_p1_dev(
                paper_log.read_text(encoding="utf-8"),
                action_id=subject["action_id"], session_id=subject["session"],
            )
        if m0_live_dev:
            postings = report["m0_s49_original_owner_postings"]
            expected_charge = report["p1_paper_motor_dev"]["m0_charge_proposal_not_posted"]
            if (len(postings) != 1
                    or postings[0]["action_id"] != subject["action_id"]
                    or postings[0]["session_id"] != subject["session"]
                    or not math.isclose(postings[0]["posted_extra"],
                                        expected_charge, abs_tol=1e-10)
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
                raise ForwardDashDevRejected("Original S49 M0 ledger debit not source bound")
            report["m0_debit_classification"] = (
                "ORIGINAL_S49_LOCAL_B0_OWNER_POSTED_DEV_NOT_ATTESTED"
            )
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
    a = parser.parse_args()
    return asyncio.run(run(
        a.output_dir, a.paper_jar, a.paper_sha256,
        a.dash_jar, a.dash_sha256, confirm=a.confirm,
        p1_live_dev=a.p1_live_dev,
        m0_live_dev=a.m0_live_dev,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
