"""S50 real Mojang 1.21.8 + Mineflayer 4.39.0 supervised SEEK step.

A caller-selected target position is not a learned goal. The strict bounded
test physically verifies that issued look/forward/clear changes body position.
No obstacle avoiding navigation or complete route finding is claimed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from adapters.mineflayer.python_protocol import MineflayerPosition
from adapters.mineflayer.s31a_real_server_ci import (
    MINECRAFT_VERSION,
    MINEFLAYER_VERSION,
    S31ABlocked,
    _correlated_observe,
    _fetch_official_server,
    _ready_server,
    _shutdown_server,
    _write_config,
)
from adapters.mineflayer.s34_native_world_cognition_ci import _new_session
from adapters.mineflayer.seek_execution import (
    SeekConsequenceKind,
    SeekExecutionRejected,
    execute_seek_step,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.seek_waypoint import SeekCursor, SeekStatus, SeekWaypoint
from relay_self.skill import SkillExecution


def p(tag: str) -> Provenance:
    return Provenance("s50-independent-operator", tag)


async def qualify(report_path: Path, server_log: Path) -> int:
    report: dict[str, Any] = {
        "milestone": "S50", "status": "BLOCKED", "stage": "START",
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "navigation_plan_author": "EXPLICIT_TEST_GOAL",
        "automatic_pathfinding": False,
        "model_calls": 0,
    }
    server = collector = session = temp = None
    rc = 2
    try:
        if os.environ.get("S50_REAL_SERVER_CI") != "1" or os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("S50 real World opt-in and unmodified Node required")
        report["stage"] = "PROVISION_REAL_MOJANG_SERVER"
        temp = tempfile.TemporaryDirectory(prefix="relay-self-s50-")
        root = Path(temp.name)
        report.update(await asyncio.to_thread(_fetch_official_server, root / "minecraft.jar"))
        _write_config(root)
        server, collector, _ = await _ready_server(
            root, root / "minecraft.jar", server_log,
        )
        session = await _new_session()
        report["session_id"] = session.started.session_id
        read = await _correlated_observe(session, "s50-origin-probe")
        pos = read.snapshot.position
        goal = SeekWaypoint(
            "s50-explicit-flat-goal",
            MineflayerPosition(pos.x + 4.0, pos.y, pos.z),
            max_step_m=1.0,
        )
        cursor = SeekCursor(read.session_id)
        proposal = cursor.plan(read, goal)
        if proposal.status is not SeekStatus.STEER:
            raise SeekExecutionRejected("fresh native World did not support a SEEK step")
        intent = IntentCommitment()
        intent.commit(
            "seek-explicit-waypoint", objective="go to commanded safe flat coordinate",
            at_ns=1, provenance=p("intent-commitment"),
        )
        skill = SkillExecution.start(
            "s50-seek-skill",
            skill_id="seek-waypoint",
            intent_commitment=intent,
            at_ns=2,
            provenance=p("skill-started"),
        )
        proposed = ActionLifecycle.propose(
            "s50-seek-forward",
            skill_execution=skill,
            intent_commitment=intent,
            at_ns=3,
            provenance=p("action-proposed"),
        )
        authorized = proposed.authorize(
            at_ns=4,
            authority="s50-independent-action-authorizer",
            provenance=p("separate-action-authorization"),
        )
        supervisor = ActionSupervisor()
        issued = supervisor.issue(
            authorized, at_ns=5, deadline_ns=100,
            provenance=p("supervisor-issue"),
        )
        report["stage"] = "AUTHENTIC_ISSUED_SEEK_NATIVE_EFFECT"
        effect = await execute_seek_step(session, supervisor, issued, proposal)
        report["seek_effect"] = {
            "kind": effect.kind.value,
            "action_id": effect.action_id,
            "start_seq": effect.before_seq,
            "after_seq": effect.after_seq,
            "look_seq": effect.look_seq,
            "forward_seq": effect.forward_seq,
            "clear_seq": effect.clear_seq,
            "progress_m": effect.progress_m,
            "remaining_m": effect.remaining_m,
        }
        if effect.kind not in (
            SeekConsequenceKind.PROGRESSED, SeekConsequenceKind.ARRIVED,
        ) or effect.progress_m < 0.05:
            raise SeekExecutionRejected("real SEEK did not make progress")
        closed = supervisor.record_outcome(
            issued.action_id, at_ns=6, provenance=p("world-observed-closed"),
        )
        if closed.state is not ActionState.OUTCOME or supervisor.open_actions:
            raise SeekExecutionRejected("real SEEK Action failed to close terminal")
        try:
            await execute_seek_step(session, supervisor, issued, proposal)
        except SeekExecutionRejected:
            report["duplicate_issued_action_denied"] = True
        else:
            raise SeekExecutionRejected("same issued physical command replayed")
        report["status"] = "PASS"
        report["classification"] = "REAL_ISSUED_SEEK_ONE_STEP_PROGRESS_QUALIFIED"
        report["stage"] = "CLOSED"
        rc = 0
    except (S31ABlocked, OSError) as exc:
        report["status"] = "BLOCKED"
        report["error"] = f"{type(exc).__name__}: {exc}"
        rc = 2
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        print(f"S50 FAIL: {exc}", file=sys.stderr)
        rc = 1
    finally:
        if session is not None:
            try:
                report["node_exit"] = await session.shutdown(timeout_s=10)
            except Exception as exc:
                report["node_cleanup_error"] = str(exc)
                await session.terminate()
        try:
            await _shutdown_server(server, collector)
        except Exception as exc:
            report["server_cleanup_error"] = str(exc)
            report["status"] = "FAIL"
            rc = 1
        if server is not None:
            report["server_exit"] = server.returncode
        if temp is not None:
            temp.cleanup()
        if report["status"] == "PASS" and report.get("server_exit") != 0:
            report["status"] = "FAIL"
            report["error"] = "Java server did not exit cleanly"
            rc = 1
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, sort_keys=True, indent=2)+"\n")
        print("S50_REPORT="+json.dumps(report, sort_keys=True))
    return rc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--server-log", required=True, type=Path)
    args = parser.parse_args()
    return asyncio.run(qualify(args.report, args.server_log))


if __name__ == "__main__":
    raise SystemExit(main())
