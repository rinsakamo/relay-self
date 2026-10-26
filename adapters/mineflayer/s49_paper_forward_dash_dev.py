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
import os
import shutil
from pathlib import Path
from unittest.mock import patch

from adapters.mineflayer import normal_action as action_owner
from adapters.mineflayer import s49_normal_session_real_ci as original
from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import _fresh_asset
from adapters.mineflayer.s49_paper_world_first_dev import (
    _await_dash_dev_line,
    _fresh_output,
    offline_uuid,
)

CONFIRM = "S49-P1-DEV-DISPOSABLE-PAPER-WORLD"


class ForwardDashDevRejected(RuntimeError):
    pass


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
                or data["input_forward_only"] != data["modifier_applied"]
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
            rows.append((tick, data["modifier_applied"] == "true"))
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
            or int(c.get("forward_boost_ticks", "-1")) != sum(on for _, on in rows)
            or int(c.get("other_direction_or_ambiguous_ticks", "-1"))
            != sum(not on for _, on in rows)):
        raise ForwardDashDevRejected("DASH completion disagrees with observed ticks")
    return {
        "paper_gait_ticks_observed": len(rows),
        "paper_forward_boost_ticks": sum(on for _, on in rows),
        "paper_other_or_ambiguous_ticks": sum(not on for _, on in rows),
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
) -> int:
    if (
        confirm != CONFIRM or os.environ.get("NODE_OPTIONS")
        or os.environ.get("S49_REAL_SERVER_CI") != "1"
        or os.environ.get("S49_FORWARD_MOTOR_DEV_ONLY") != "1"
        or os.environ.get("S49_SPRINT_MOTOR_DEV_ONLY") != "1"
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
            "enabled: true\nexpected-player-name: RelaySelf\n", encoding="utf-8"
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
        report["original_action_distances_m"] = [a["movement_m"] for a in actions]
        if review["paper_forward_boost_ticks"] < 1:
            report["status"] = "DEV_SPRINT_NO_POSITIVE_PAPER_BOOST"
            return 1
        report["status"] = "DEV_FORWARD_SPRINT_POSITIVE_PAPER_DASH_OBSERVED"
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
    a = parser.parse_args()
    return asyncio.run(run(
        a.output_dir, a.paper_jar, a.paper_sha256,
        a.dash_jar, a.dash_sha256, confirm=a.confirm,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
