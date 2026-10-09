"""S37: three genuine world incident events across 2 explicit Node reconnect sessions.

Single disposable Mojang Minecraft Java 1.21.8 server. Supervised harness
summons/clears controlled distinct zombies; bounded host loop consumes
real unsolicited entitySpawn events and automatically invokes S36 cognition.
No Action proposal, authorization, issue, execution or new learning.
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
from adapters.mineflayer.process_session import MineflayerProcessSession
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
from relay_self.bounded_native_host_loop import (
    BoundedNativeHostLoop,
    HostLoopBoundaryError,
    HostLoopBudget,
)
from relay_self.native_event_cognition import (
    EventCognitionTriggerGrant,
    NativeEventCognitionCandidate,
)


class S37EvidenceFailure(RuntimeError):
    """Fail the real multi-event/reconnect World transaction without guessing."""


async def _controlled_clear(server, session, counter: int) -> None:
    """Remove all controlled zombies, then verify no zombie remains visible."""
    _command(server, "kill @e[type=minecraft:zombie]")
    assert server.stdin is not None
    await server.stdin.drain()
    for attempt in range(6):
        await asyncio.sleep(1)
        obs = await _correlated_observe(
            session, f"s37-clear:{counter}:{attempt:03d}",
        )
        if obs.snapshot.nearby_entities_coverage.truncated:
            raise S37EvidenceFailure("no complete native coverage after kill")
        zombies = [e for e in obs.snapshot.nearby_entities if e.name == "zombie"]
        if not zombies:
            return
    raise S37EvidenceFailure("old zombie persisted after controlled clear")


async def qualify(report_path: Path, server_log: Path) -> int:
    report: dict[str, Any] = {
        "milestone": "S37", "status": "BLOCKED",
        "classification": "NOT_QUALIFIED", "stage": "START",
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "expected_sessions": 2, "expected_real_world_incidents": 3,
        "real_world_incidents": [],
        "autonomous_daemon": False,
        "unexpected_disconnect_recovered": False,
        "supervised_reconnect_only": True,
        "native_goal_discovery": False,
        "action_proposed": False, "action_authorized": False,
        "action_issued": False, "physical_action_executed": False,
        "learning_update_in_s37": False,
        "synthetic_retained_history": "FROZEN_S19_FAKESESSION_COMMITTED_REV1",
        "bounded_host_loop_qualification": "2_Sessions_3_Events_Not_Indefinite",
        "local_codex_s31b": "SKIPPED",
    }
    server = None
    collector = None
    session: MineflayerProcessSession | None = None
    tmp: tempfile.TemporaryDirectory[str] | None = None
    code = 2
    try:
        if os.environ.get("S37_REAL_SERVER_CI") != "1":
            raise S31ABlocked("S37_REAL_SERVER_CI=1 required")
        if os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("test preload forbidden for genuine World")
        report["stage"] = "OFFICIAL_MOJANG_SERVER"
        tmp = tempfile.TemporaryDirectory(prefix="relay-self-s37-")
        root = Path(tmp.name)
        report.update(await asyncio.to_thread(
            _fetch_official_server, root / "minecraft-server.jar",
        ))
        _write_config(root)
        server, collector, _ = await _ready_server(
            root, root / "minecraft-server.jar", server_log,
        )
        report["stage"] = "FROZEN_GOVERNED_RETENTION"
        past, commit, _prev_intent, closed, feedback, _ = (
            await asyncio.to_thread(s19._epoch_one)
        )
        if (
            past.get(closed.action_id) is not closed
            or past.open_actions != ()
            or feedback.feedback is None
            or commit.new_state.value != 4
            or commit.new_state.revision != 1
            or commit.new_state.last_update is None
        ):
            raise S37EvidenceFailure("unqualified frozen synthetic retained proof")

        owner = ActionSupervisor()
        intent = s19.IntentCommitment()
        intent.commit(
            "escape-threat", objective="escape nearby zombie",
            at_ns=1, provenance=s19.provenance("s37-fixed-user-intent"),
        )
        host = BoundedNativeHostLoop(
            HostLoopBudget(
                max_sessions=2, max_epochs_per_session=2,
                max_total_epochs=3, max_frames_per_event=100,
                receive_timeout_s=30,
            )
        )

        def external_grant(candidate: NativeEventCognitionCandidate):
            return EventCognitionTriggerGrant(
                authority_id="s37-independent-cognition-grant",
                candidate_id=candidate.candidate_id,
                session_id=candidate.session_id,
                event_seq=candidate.event_seq,
                target_entity_id=candidate.target_entity_id,
                granted=True,
                provenance=s19.provenance("s37-independent-cognition-grant"),
            )

        def admitted_cognition(ticket):
            host.require_current_ticket(ticket)
            native = _native_threat(
                ticket.correlated_probe, ticket.probe_request_id,
                expected_entity_id=ticket.candidate.target_entity_id,
            )
            values, epoch = _native_epoch_two(
                owner, intent, commit.new_state, commit.new_state,
                expected_revision=1, native=native,
            )
            if (
                values["external"][1].provenance != ticket.correlated_probe.provenance
                or values["plan"].selected is None
                or values["plan"].selected.candidate_id != "MOVE_AWAY"
                or values["admission"].status.value != "admitted"
                or values["read"].revision != 1
                or epoch.cognition_requested
                or owner.open_actions != ()
            ):
                raise S37EvidenceFailure("real incident did not yield bounded cognition")
            return {
                "selected": values["plan"].selected.candidate_id,
                "admission": values["admission"].status.value,
                "retained_revision": values["read"].revision,
                "native_source": ticket.correlated_probe.provenance.reference,
                "new_action_issued": False,
            }

        old_ticket = None
        ids: list[int] = []
        for generation, incident_count in ((1, 2), (2, 1)):
            report["stage"] = f"MINEFLAYER_SESSION_{generation}_SPAWN"
            session = await _new_session()
            sid = session.started.session_id
            host.begin_session(sid)
            if generation == 2 and old_ticket is not None:
                try:
                    host.require_current_ticket(old_ticket)
                except HostLoopBoundaryError:
                    report["retired_ticket_rejected_after_reconnect"] = True
                else:
                    raise S37EvidenceFailure("old event ticket accepted after reconnect")
            # The real host receives unrequested entity frames. The next
            # probe is an explicit S36 scheduler-only read, never Action.
            async def probe(candidate: NativeEventCognitionCandidate):
                assert session is not None
                return await _correlated_observe(
                    session,
                    f"s37-g{generation}-event-{candidate.event_seq}-entity-{candidate.target_entity_id}",
                )
            _command(server, "gamerule doMobSpawning false")
            _command(server, "time set midnight")
            assert server.stdin is not None
            await server.stdin.drain()
            for ordinal in range(incident_count):
                report["stage"] = f"REAL_INCIDENT_{generation}_{ordinal + 1}"
                if generation > 1 or ordinal > 0:
                    await _controlled_clear(
                        server, session, len(report["real_world_incidents"]),
                    )
                _command(
                    server,
                    "execute at RelaySelf run summon minecraft:zombie ~2 ~ ~ "
                    "{NoAI:1b,Silent:1b,PersistenceRequired:1b}",
                )
                await server.stdin.drain()
                outcome = await host.wait_for_event_cognition(
                    session, probe=probe,
                    grant=external_grant, cognition=admitted_cognition,
                )
                if outcome.session_id != sid or outcome.event_seq >= outcome.probe_seq:
                    raise S37EvidenceFailure("real native incident sequence invalid")
                if outcome.entity_id in ids:
                    raise S37EvidenceFailure("same old entity reused as new incident")
                ids.append(outcome.entity_id)
                if outcome.cognition["selected"] != "MOVE_AWAY":
                    raise S37EvidenceFailure("real event was not automatically cognized")
                report["real_world_incidents"].append({
                    "generation": generation,
                    "session_id": sid,
                    "native_event_seq": outcome.event_seq,
                    "probe_seq": outcome.probe_seq,
                    "entity_id": outcome.entity_id,
                    "request_id": outcome.probe_request_id,
                    "native_event_provenance": outcome.event_provenance,
                    "cognition": outcome.cognition,
                })
                old_ticket = outcome.ticket
            # Process shutdown is explicitly directed by the supervisor;
            # S37 does not claim recovery from crashes or network faults.
            process_code = await session.shutdown(timeout_s=10)
            if process_code != 0:
                raise S37EvidenceFailure("real Node bridge did not cleanly exit")
            report[f"node_session_{generation}_exit"] = process_code
            host.end_session(sid)
            if host.active_session_id is not None:
                raise S37EvidenceFailure("stale process generation remained active")
            session = None

        if (
            host.total_sessions != 2
            or host.total_epochs != 3
            or len(ids) != 3
            or len({x["session_id"] for x in report["real_world_incidents"]}) != 2
            or owner.open_actions != ()
        ):
            raise S37EvidenceFailure("bounded multi-event/reconnect cardinality wrong")
        try:
            owner.get("s37-never-issued-action")
        except UnknownSupervisedAction:
            report["zero_action_owner_verified"] = True
        else:
            raise S37EvidenceFailure("unexpected Action owner")
        report["host"] = {
            "total_sessions": host.total_sessions,
            "total_epochs": host.total_epochs,
            "expired_pending_on_close": host.expired_pending,
            "distinct_entity_ids": len(set(ids)),
            "rejected_same_entity_repeats": host.rejected_replays,
        }
        report["stage"] = "SUCCESS"
        report["status"] = "PASS"
        report["classification"] = (
            "THREE_REAL_NATIVE_EVENTS_TWO_SESSIONS_BOUNDED_COGNITION_NO_ACTION_QUALIFIED"
        )
        code = 0
    except (S31ABlocked, OSError) as exc:
        report["status"] = "BLOCKED"
        report["error"] = str(exc)
        code = 2
        print(f"S37 BLOCKED at {report['stage']}: {exc}", file=sys.stderr)
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        code = 1
        print(f"S37 FAIL at {report['stage']}: {exc}", file=sys.stderr)
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
            code = 1
        if server is not None:
            report["server_exit_code"] = server.returncode
        if tmp is not None:
            tmp.cleanup()
        if report["status"] == "PASS" and report.get("server_exit_code") != 0:
            report["status"] = "FAIL"
            report["classification"] = "S37_TEARDOWN_NOT_QUALIFIED"
            report["error"] = "server did not exit code0"
            report["stage"] = "TEARDOWN"
            code = 1
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("S37_REPORT=" + json.dumps(report, sort_keys=True))
    return code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    args = parser.parse_args()
    return asyncio.run(qualify(args.report, args.server_log))


if __name__ == "__main__":
    raise SystemExit(main())
