"""S32: genuine physical S15 Action3 -> S16 closure -> S27/S24 World evidence.

Only Action3 onward is physically executed. The pre-Action1/2 cognition,
Action closures, learning rev1 and RecoverySkill3 admission are *synthetic,
frozen S23 fixtures*; this is a bounded hybrid lineage test, NOT evidence
that all preceding epochs were run in Minecraft. No autonomous Action4.
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

# The frozen S23 test apparatus is deliberately reused as a seeded history.
# This CI-only harness must be launched with PYTHONPATH including tests/.
import test_postmain_local_recovery_action as s23
from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import (
    WorldConsequenceStatus,
    build_mineflayer_command,
    execute_mineflayer_command,
)
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from adapters.mineflayer.s31a_real_server_ci import (
    BOT_USERNAME,
    MINECRAFT_VERSION,
    MINEFLAYER_VERSION,
    SERVER_HOST,
    SERVER_PORT,
    S31ABlocked,
    _await_spawn,
    _command,
    _correlated_observe,
    _fetch_official_server,
    _ready_server,
    _shutdown_server,
    _verified_target,
    _write_config,
)
from relay_self.action import ActionState
from relay_self.action_outcome import record_interpreted_action_outcome
from relay_self.execution_admission import AdmissionDecisionStatus
from relay_self.postfailure_cognition import run_explicit_postfailure_epoch
from relay_self.source_native_world import project_source_native_threat

REQUEST_ID = "s32-after-real-action3:000"
MAX_TARGET_ATTEMPTS = 5


class S32EvidenceFailure(RuntimeError):
    """A live action, WorldConsequence, or post-action lineage is not qualified."""


async def qualify(report_path: Path, server_log: Path) -> int:
    report: dict[str, Any] = {
        "milestone": "S32", "status": "BLOCKED",
        "classification": "NOT_QUALIFIED",
        "stage": "START",
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "genuine_minecraft_server": False,
        "real_mineflayer": False,
        "synthetic_ancestry": "S19-S23 frozen deterministic Action1/2 and retained 4/rev1",
        "real_execution_scope": "Action3 only",
        "world_evidence_from_same_live_session": False,
        "automatic_action4_issued": False,
        "autonomous_epoch_reentry": False,
        "cryptographic_world_attestation": False,
    }
    server = None
    collector = None
    session: MineflayerProcessSession | None = None
    tmp: tempfile.TemporaryDirectory[str] | None = None
    exit_code = 2
    try:
        if os.environ.get("S32_REAL_SERVER_CI") != "1":
            raise S31ABlocked("explicit S32_REAL_SERVER_CI=1 required")
        if os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("NODE_OPTIONS preload forbidden in genuine World test")
        report["stage"] = "SOURCE"
        tmp = tempfile.TemporaryDirectory(prefix="relay-self-s32-")
        root = Path(tmp.name)
        jar = root / "minecraft-server.jar"
        metadata = await asyncio.to_thread(_fetch_official_server, jar)
        report.update(metadata)
        _write_config(root)

        report["stage"] = "JAVA_SERVER_START"
        server, collector, _ = await _ready_server(root, jar, server_log)
        report["genuine_minecraft_server"] = True
        report["stage"] = "MINEFLAYER_SPAWN"
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(
                host=SERVER_HOST, port=SERVER_PORT,
                username=BOT_USERNAME, version=MINECRAFT_VERSION,
            ),
            startup_timeout_s=12,
        )
        spawned = await _await_spawn(session)
        report["real_mineflayer"] = True
        report["session_id"] = session.started.session_id
        report["spawn_seq"] = spawned.seq

        # The antecedents are frozen deterministic history, NOT physical tests.
        report["stage"] = "EXPLICIT_S23_ACTION3_AUTHORITY"
        data, failed_skill, inputs = s23._prepare_recovery()
        proposed, binding, handoff = s23._propose(inputs)
        _authorized, issued = s23._issue(data, proposed)
        if issued.state is not ActionState.ISSUED:
            raise S32EvidenceFailure("Action3 was not separately ISSUED")
        command = build_mineflayer_command(issued, binding)
        report["action3"] = {
            "id": issued.action_id,
            "binding_id": binding.binding_id,
            "action_ref": command.action_ref,
            "effect": command.effect,
            "control": command.control,
            "duration_s": command.duration_s,
            "prior_handoff_action_id": handoff.action_id,
        }
        if command.action_ref != "MOVE_BACKWARD":
            raise S32EvidenceFailure("unexpected physical Action primitive")

        report["stage"] = "S15_REAL_PHYSICAL_ACTION3"
        consequence = await execute_mineflayer_command(
            session, command, timeout_s=9,
            provenance=s23.p("s32-genuine-minecraft-worldconsequence3"),
        )
        report["consequence3"] = {
            "status": consequence.status.value,
            "session_id": consequence.session_id,
            "before_seq": (
                None if consequence.before_observation is None
                else consequence.before_observation.seq
            ),
            "dispatch_seq": (
                None if consequence.dispatch_receipt is None
                else consequence.dispatch_receipt.seq
            ),
            "cleanup_seq": (
                None if consequence.cleanup_receipt is None
                else consequence.cleanup_receipt.seq
            ),
            "after_seq": (
                None if consequence.after_observation is None
                else consequence.after_observation.seq
            ),
            "movement_distance_m": consequence.movement_distance,
            "error": consequence.error,
        }
        if consequence.status is not WorldConsequenceStatus.EXECUTED:
            raise S32EvidenceFailure(
                "real S15 Action3 did not produce EXECUTED movement consequence"
            )
        if consequence.session_id != session.started.session_id:
            raise S32EvidenceFailure("S15 physical consequence session changed")

        report["stage"] = "S16_SUPERVISED_OUTCOME"
        interpretation = interpret_world_consequence(
            issued, binding, consequence,
            provenance=s23.p("s32-real-world-action3-interpretation"),
        )
        closed = record_interpreted_action_outcome(
            data["supervisor"], interpretation, at_ns=60,
        )
        if (
            closed.state is not ActionState.OUTCOME
            or data["supervisor"].get(issued.action_id) is not closed
            or data["supervisor"].open_actions != ()
        ):
            raise S32EvidenceFailure("S16 Action3 owner not terminal OUTCOME")
        report["action3"]["terminal_state"] = closed.state.value

        report["stage"] = "CONTROLLED_POST_ACTION_WORLD"
        assert server is not None
        _command(server, "gamerule doMobSpawning false")
        _command(server, "time set midnight")
        _command(
            server,
            "execute at RelaySelf run summon minecraft:zombie ~2 ~ ~ "
            "{NoAI:1b,Silent:1b,PersistenceRequired:1b}",
        )
        assert server.stdin is not None
        await server.stdin.drain()

        report["stage"] = "CORRELATED_POST_ACTION_OBSERVATION"
        observed = None
        target = None
        for attempt in range(MAX_TARGET_ATTEMPTS):
            await asyncio.sleep(2)
            request_id = f"s32-after-real-action3:{attempt:03d}"
            candidate = await _correlated_observe(session, request_id)
            report["last_request_id"] = request_id
            maybe = _verified_target(candidate)
            if maybe is not None:
                observed, target = candidate, maybe
                break
        if observed is None or target is None:
            raise S32EvidenceFailure("zombie absent in bounded post-Action3 native registry")
        if (
            observed.session_id != consequence.session_id
            or consequence.after_observation is None
            or observed.seq <= consequence.after_observation.seq
            or observed.request_id != report["last_request_id"]
        ):
            raise S32EvidenceFailure("fresh post-Action3 observation lineage mismatch")
        report["observed_target"] = target

        report["stage"] = "S27_REAL_EVIDENCE_PROJECTION"
        receipt = project_source_native_threat(
            data["supervisor"], closed, consequence, observed,
            target_entity_id=target["entity_id"],
            target_name="zombie",
            observed_at_ns=65, inspected_at_ns=67, max_age_ns=5,
        )
        if receipt.evidence.session_id != consequence.session_id:
            raise S32EvidenceFailure("S27 evidence source session mismatch")
        report["world_evidence_from_same_live_session"] = True
        report["s27"] = {
            "evidence_id": receipt.evidence.evidence_id,
            "distance_cm": receipt.evidence.threat_clearance_cm,
            "parent_action_id": receipt.evidence.action_id,
            "parent_binding_id": receipt.evidence.binding_id,
            "parent_after_seq": receipt.parent_after_seq,
            "fresh_probe_seq": observed.seq,
            "request_id": observed.request_id,
            "source_provenance": observed.provenance.reference,
        }

        report["stage"] = "S24_EXPLICIT_COGNITION"
        trace = run_explicit_postfailure_epoch(
            data["supervisor"], closed, consequence,
            inputs["recovery_skill"], data["intent"],
            data["commit"].new_state, receipt.evidence,
            at_ns=70, provenance=s23.p("s32-explicit-post-real-action3-epoch"),
        )
        report["s24"] = {
            "selected_candidate": trace.selected_candidate,
            "wait_score": trace.wait_score,
            "move_score": trace.move_score,
            "admission_status": trace.admission_status.value,
            "retained_revision": trace.retained_revision,
            "world_source_in_trace": (
                receipt.evidence.provenance in trace.source_provenance
            ),
        }
        if (
            trace.selected_candidate != "WAIT"
            or trace.admission_status is not AdmissionDecisionStatus.ADMITTED
            or trace.retained_revision != 1
            or not report["s24"]["world_source_in_trace"]
            or failed_skill.state.value != "failed"
            or inputs["recovery_skill"].state.value != "started"
            or data["supervisor"].open_actions != ()
        ):
            raise S32EvidenceFailure("post-Action3 cognition/Skill boundary failed")

        report["stage"] = "SUCCESS"
        report["status"] = "PASS"
        report["classification"] = (
            "HYBRID_SEEDED_ANCESTRY_REAL_ACTION3_S15_S16_S27_S24_QUALIFIED"
        )
        exit_code = 0
    except (S31ABlocked, OSError) as exc:
        report["status"] = "BLOCKED"
        report["error"] = str(exc)
        exit_code = 2
        print(f"S32 BLOCKED at {report['stage']}: {exc}", file=sys.stderr)
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 1
        print(f"S32 FAIL at {report['stage']}: {exc}", file=sys.stderr)
    finally:
        if session is not None:
            try:
                report["bridge_exit_code"] = await session.shutdown(timeout_s=10)
            except Exception as exc:
                report["bridge_shutdown_error"] = str(exc)
                await session.terminate()
        try:
            await _shutdown_server(server, collector)
        except Exception as exc:
            report["server_shutdown_error"] = str(exc)
            exit_code = 1
        if server is not None:
            report["server_exit_code"] = server.returncode
        if tmp is not None:
            tmp.cleanup()
        if report["status"] == "PASS" and (
            report.get("bridge_exit_code") != 0
            or report.get("server_exit_code") != 0
        ):
            report["status"] = "FAIL"
            report["classification"] = "S32_TEARDOWN_NOT_QUALIFIED"
            report["stage"] = "TEARDOWN"
            report["error"] = "bridge/server did not stop with exact code zero"
            exit_code = 1
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("S32_REPORT=" + json.dumps(report, sort_keys=True))
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    args = parser.parse_args()
    return asyncio.run(qualify(args.report, args.server_log))


if __name__ == "__main__":
    raise SystemExit(main())
