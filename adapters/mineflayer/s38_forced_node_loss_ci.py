"""S38 real Minecraft Node SIGKILL -> quarantine -> source-revalidated reconnect.

Two genuine Mineflayer 4.39.0 Node processes against ONE surviving official
Minecraft server. This experimental test harness intentionally SIGKILLs the
first Node process after one native event-driven cognitive epoch; this is
an induced child process crash, not real packet-loss or Java-server failure.
New observed world evidence is compulsory before the second epoch.
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

import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.process_session import (
    MineflayerProcessEnded,
    MineflayerProcessSession,
)
from adapters.mineflayer.s31a_real_server_ci import (
    MINECRAFT_VERSION,
    MINEFLAYER_VERSION,
    S31ABlocked,
    _command,
    _correlated_observe,
    _fetch_official_server,
    _ready_server,
    _shutdown_server,
    _write_config,
)
from adapters.mineflayer.s34_native_world_cognition_ci import (
    _native_epoch_two,
    _native_threat,
    _new_session,
)
from relay_self.action_supervision import ActionSupervisor, UnknownSupervisedAction
from relay_self.bounded_native_host_loop import HostLoopBoundaryError
from relay_self.forced_node_loss_fence import (
    ForcedNodeLossFence,
    WorldLossBoundaryError,
    WorldLossState,
)
from relay_self.native_event_cognition import (
    EventCognitionTriggerGrant,
    NativeEventCognitionCandidate,
)


class S38EvidenceFailure(RuntimeError):
    """Unexpected child loss or revalidation contract was not qualified."""


async def qualify(report_path: Path, server_log: Path) -> int:
    report: dict[str, Any] = {
        "milestone": "S38", "status": "BLOCKED",
        "classification": "NOT_QUALIFIED", "stage": "START",
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "fault_type": "INTENTIONALLY_FORCED_SIGKILL_NODE_CHILD_NOT_WORLD_SERVER",
        "automatic_reconnect": False,
        "supervised_reconnect": True,
        "real_fault_injected": False,
        "old_ticket_rejected_during_quarantine": False,
        "old_ticket_rejected_after_reconnect": False,
        "new_world_source_required": True,
        "action_issued": False,
        "action_authorized": False,
        "action_proposed": False,
        "physical_action_executed": False,
        "learning_updated_in_s38": False,
        "retained_history": "FROZEN_S19_SYNTHETIC_GOVERNED_REV1",
        "local_codex_s31b": "SKIPPED",
        "daemon_crash_resume": False,
    }
    server = None
    collector = None
    session: MineflayerProcessSession | None = None
    temp: tempfile.TemporaryDirectory[str] | None = None
    result = 2
    try:
        if os.environ.get("S38_REAL_SERVER_CI") != "1":
            raise S31ABlocked("S38_REAL_SERVER_CI=1 required")
        if os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("S30 test-only preload forbidden")
        report["stage"] = "OFFICIAL_MOJANG_SERVER"
        temp = tempfile.TemporaryDirectory(prefix="relay-self-s38-")
        root = Path(temp.name)
        report.update(await asyncio.to_thread(
            _fetch_official_server, root / "minecraft-server.jar",
        ))
        _write_config(root)
        server, collector, _ = await _ready_server(
            root, root / "minecraft-server.jar", server_log,
        )
        past, committed, _past_intent, closed, feedback, _ = (
            await asyncio.to_thread(s19._epoch_one)
        )
        if (
            past.get(closed.action_id) is not closed
            or past.open_actions != ()
            or committed.new_state.value != 4
            or committed.new_state.revision != 1
            or committed.new_state.last_update is None
            or feedback.feedback is None
        ):
            raise S38EvidenceFailure("frozen governed synthetic S19 retained proof missing")

        supervisor = ActionSupervisor()
        intent = s19.IntentCommitment()
        intent.commit(
            "escape-threat", objective="escape nearby zombie",
            at_ns=1, provenance=s19.provenance("s38-explicit-existing-intent"),
        )
        fence = ForcedNodeLossFence()

        def independent_grant(candidate: NativeEventCognitionCandidate):
            return EventCognitionTriggerGrant(
                authority_id="s38-external-cognition-only-grant",
                candidate_id=candidate.candidate_id,
                session_id=candidate.session_id,
                event_seq=candidate.event_seq,
                target_entity_id=candidate.target_entity_id,
                granted=True,
                provenance=s19.provenance("s38-independent-cognition-grant"),
            )

        def cognitive_callback(ticket):
            native = _native_threat(
                ticket.correlated_probe,
                ticket.probe_request_id,
                expected_entity_id=ticket.candidate.target_entity_id,
            )
            values, epoch = _native_epoch_two(
                supervisor, intent,
                committed.new_state, committed.new_state,
                expected_revision=1, native=native,
            )
            if (
                values["external"][1].provenance != ticket.correlated_probe.provenance
                or values["plan"].selected is None
                or values["plan"].selected.candidate_id != "MOVE_AWAY"
                or values["admission"].status.value != "admitted"
                or values["read"].revision != 1
                or epoch.cognition_requested
                or supervisor.open_actions != ()
            ):
                raise S38EvidenceFailure("native source failed bounded cognitive recovery")
            return {
                "selected": values["plan"].selected.candidate_id,
                "admission": values["admission"].status.value,
                "retained_revision": values["read"].revision,
                "source": ticket.correlated_probe.provenance.reference,
                "new_action_issued": False,
            }

        report["stage"] = "PRE_FAULT_REAL_NATIVE_INCIDENT"
        session = await _new_session()
        sid1 = session.started.session_id
        fence.begin_initial(sid1)
        _command(server, "gamerule doMobSpawning false")
        _command(server, "time set midnight")
        _command(
            server,
            "execute at RelaySelf run summon minecraft:zombie ~2 ~ ~ "
            "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}",
        )
        assert server.stdin is not None
        await server.stdin.drain()

        async def actual_probe(candidate: NativeEventCognitionCandidate):
            assert session is not None
            return await _correlated_observe(
                session,
                f"s38-g-{candidate.session_id}-seq-{candidate.event_seq}"
                f"-entity-{candidate.target_entity_id}",
            )

        first = await fence.run_active(
            session, probe=actual_probe, grant=independent_grant,
            cognition=cognitive_callback,
        )
        report["first_event"] = {
            "session": first.session_id,
            "event_seq": first.event_seq,
            "probe_seq": first.probe_seq,
            "entity_id": first.entity_id,
            "request_id": first.probe_request_id,
            "cognition": first.cognition,
        }

        # This is a real OS child signal, NOT a graceful bridge shutdown.
        # The _process handle is deliberately used only in this isolated
        # test runner, not exposed through production Self semantics.
        report["stage"] = "ACTUAL_NODE_SIGKILL"
        if session.process_returncode is not None:
            raise S38EvidenceFailure("bridge died before intentional SIGKILL")
        session._process.kill()
        killed_code = await asyncio.wait_for(session._process.wait(), timeout=10)
        report["forced_node_exit_code"] = killed_code
        if type(killed_code) is not int or killed_code >= 0:
            raise S38EvidenceFailure("intended negative SIGKILL code was not observed")
        report["real_fault_injected"] = True

        report["stage"] = "UNEXPECTED_STDOUT_EOF_MUST_QUARANTINE"
        try:
            await fence.run_active(
                session, probe=actual_probe, grant=independent_grant,
                cognition=cognitive_callback,
            )
        except MineflayerProcessEnded as exc:
            fault = fence.observe_forced_failure(
                sid1, transport_error=exc, process_returncode=killed_code,
            )
        else:
            raise S38EvidenceFailure("dead Node unexpectedly ran another cognition")
        if fence.state is not WorldLossState.QUARANTINED or fence.host.active_session_id:
            raise S38EvidenceFailure("dead session did not become quarantined")
        report["fault_receipt"] = {
            "session_id": fault.session_id,
            "actual_returncode": fault.process_returncode,
            "stdout_error": fault.transport_error,
            "prior_epochs": fault.old_epochs,
            "expired_pending": fault.expired_pending,
            "state_after_failure": fence.state.value,
        }
        try:
            fence.require_active_ticket(first.ticket)
        except WorldLossBoundaryError:
            report["old_ticket_rejected_during_quarantine"] = True
        else:
            raise S38EvidenceFailure("old ticket works after forced Node crash")
        try:
            await fence.run_active(
                session, probe=actual_probe, grant=independent_grant,
                cognition=cognitive_callback,
            )
        except WorldLossBoundaryError:
            report["quarantined_epoch_denied"] = True
        else:
            raise S38EvidenceFailure("quarantine allowed cognition without new source")
        session = None

        # Kill the former target while the bot is DISCONNECTED so that the
        # new session's source MUST come from a new genuine world incident.
        report["stage"] = "WORLD_RESET_DURING_BOT_DISCONNECT"
        _command(server, "kill @e[type=minecraft:zombie]")
        await server.stdin.drain()
        await asyncio.sleep(2)

        report["stage"] = "NEW_NODE_SESSION_PROBATION"
        session = await _new_session()
        sid2 = session.started.session_id
        if sid2 == sid1:
            raise S38EvidenceFailure("new node unexpectedly reused session UUID")
        fence.begin_successor(sid2)
        if fence.state is not WorldLossState.PROBATION:
            raise S38EvidenceFailure("no explicit successor probation")
        try:
            fence.require_active_ticket(first.ticket)
        except WorldLossBoundaryError:
            report["old_ticket_denied_in_probation"] = True
        else:
            raise S38EvidenceFailure("old ticket admitted during probation")
        # The source of revalidation is an independently emitted real
        # entitySpawn from a newly console-summoned World entity.
        _command(
            server,
            "execute at RelaySelf run summon minecraft:zombie ~2 ~ ~ "
            "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}",
        )
        await server.stdin.drain()
        report["stage"] = "FRESH_NATIVE_REVALIDATION_AFTER_SIGKILL"
        second = await fence.revalidate_successor(
            session, probe=actual_probe, grant=independent_grant,
            cognition=cognitive_callback,
        )
        if (
            fence.state is not WorldLossState.ACTIVE
            or second.session_id != sid2
            or second.entity_id == first.entity_id
            or second.event_seq >= second.probe_seq
            or second.cognition["selected"] != "MOVE_AWAY"
            or fence.host.total_epochs != 2
            or fence.host.total_sessions != 2
        ):
            raise S38EvidenceFailure("real forced-crash new source cognition did not qualify")
        report["new_event"] = {
            "session": second.session_id,
            "event_seq": second.event_seq,
            "probe_seq": second.probe_seq,
            "entity_id": second.entity_id,
            "request_id": second.probe_request_id,
            "cognition": second.cognition,
        }
        try:
            fence.require_active_ticket(first.ticket)
        except (WorldLossBoundaryError, HostLoopBoundaryError):
            report["old_ticket_rejected_after_reconnect"] = True
        else:
            raise S38EvidenceFailure("old ticket resurrected after revalidation")
        fence.require_active_ticket(second.ticket)
        if supervisor.open_actions != ():
            raise S38EvidenceFailure("forced recovery created unexpected Action owner")
        try:
            supervisor.get("s38-action-that-was-never-issued")
        except UnknownSupervisedAction:
            report["no_action_owner_verified"] = True
        else:
            raise S38EvidenceFailure("new Action minted by recovery")

        report["stage"] = "SUCCESSOR_CLEAN_SHUTDOWN"
        ret = await session.shutdown(timeout_s=10)
        report["new_node_exit_code"] = ret
        if ret != 0:
            raise S38EvidenceFailure("new Node bridge did not cleanly exit")
        fence.close_successor(sid2)
        if fence.state is not WorldLossState.CLOSED:
            raise S38EvidenceFailure("successor not terminally closed")
        session = None
        report["status"] = "PASS"
        report["stage"] = "SUCCESS"
        report["classification"] = (
            "REAL_SIGKILL_FAIL_CLOSED_FRESH_SESSION_REVALIDATION_NO_ACTION_QUALIFIED"
        )
        result = 0
    except (S31ABlocked, OSError) as exc:
        report["status"] = "BLOCKED"
        report["error"] = str(exc)
        result = 2
        print(f"S38 BLOCKED at {report['stage']}: {exc}", file=sys.stderr)
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        result = 1
        print(f"S38 FAIL at {report['stage']}: {exc}", file=sys.stderr)
    finally:
        if session is not None:
            try:
                report["cleanup_node_exit"] = await session.shutdown(timeout_s=10)
            except Exception as exc:
                report["cleanup_node_error"] = str(exc)
                await session.terminate()
        try:
            await _shutdown_server(server, collector)
        except Exception as exc:
            report["server_cleanup_error"] = str(exc)
            report["status"] = "FAIL"
            result = 1
        if server is not None:
            report["server_exit_code"] = server.returncode
        if temp is not None:
            temp.cleanup()
        if report["status"] == "PASS" and report.get("server_exit_code") != 0:
            report["status"] = "FAIL"
            report["classification"] = "S38_TEARDOWN_FAILED_NOT_QUALIFIED"
            report["error"] = "Minecraft Java server did not exit code0"
            result = 1
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8",
        )
        print("S38_REPORT=" + json.dumps(report, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    args = parser.parse_args()
    return asyncio.run(qualify(args.report, args.server_log))


if __name__ == "__main__":
    raise SystemExit(main())
