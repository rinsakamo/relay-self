"""S36 real-Minecraft event-loop automatic bounded cognition without Action.

The experimenter sets up a controlled native zombie, not an autonomous
planning goal. Upon genuine unsolicited entitySpawn the event consumer hands
native event to S36 scheduler, which schedules independent probe, grant and
bounded cognition. It never invokes a Mineflayer effect or Action issue.
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
from adapters.mineflayer.s35_native_event_cognition_ci import (
    _await_native_entity_trigger,
)
from relay_self.action_supervision import ActionSupervisor, UnknownSupervisedAction
from relay_self.bounded_event_scheduler import (
    BoundedEventCognitionScheduler,
    EventQueueDisposition,
    EventSchedulerBudget,
)
from relay_self.native_event_cognition import (
    EventCognitionTriggerGrant,
    NativeEventCognitionCandidate,
)


class S36EvidenceFailure(RuntimeError):
    """Real event-driven cognitive scheduler did not meet bounded contract."""


async def qualify(report_path: Path, server_log: Path) -> int:
    report: dict[str, Any] = {
        "milestone": "S36",
        "status": "BLOCKED",
        "classification": "NOT_QUALIFIED",
        "stage": "START",
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "native_event_drives_cognition": False,
        "first_probe_only_after_entity_event": True,
        "real_physical_actions": 0,
        "new_action_proposals": 0,
        "new_action_authorizations": 0,
        "new_action_issues": 0,
        "relay_engine_calls": 0,
        "learning_commits_in_s36": 0,
        "retained_ancestry": "FROZEN_S19_SYNTHETIC_VALID_GOVERNED_REV1",
        "resource_limit_scope": "PER_BATCH_AND_CUMULATIVE_EPOCHS; PROBE_TIMEOUT_ONLY",
        "priority_fairness_evidence": "DETERMINISTIC_OFFLINE_FIXTURES_NOT_LIVE_WORLD",
        "autonomous_daemon": False,
        "local_codex_s31b": "SKIPPED",
        "game_world_cryptographically_attested": False,
    }
    server = None
    collector = None
    session: MineflayerProcessSession | None = None
    tmp: tempfile.TemporaryDirectory[str] | None = None
    result = 2
    try:
        if os.environ.get("S36_REAL_SERVER_CI") != "1":
            raise S31ABlocked("S36_REAL_SERVER_CI=1 required")
        if os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("S30 test shim not allowed")
        report["stage"] = "OFFICIAL_MINECRAFT_PROVISION"
        tmp = tempfile.TemporaryDirectory(prefix="relay-self-s36-")
        root = Path(tmp.name)
        report.update(await asyncio.to_thread(
            _fetch_official_server, root / "minecraft-server.jar",
        ))
        _write_config(root)
        report["stage"] = "SERVER_BOOT"
        server, collector, _ = await _ready_server(
            root, root / "minecraft-server.jar", server_log,
        )
        report["stage"] = "REAL_MINEFLAYER_SPAWN"
        session = await _new_session()
        report["native_session_id"] = session.started.session_id

        # A correct rev1 owner snapshot needs actual governed *receipt*,
        # not a naked revision integer. This frozen S19 FakeSession history
        # is synthetic and never misrepresented as a real Minecraft action.
        hist_supervisor, hist_commit, _hist_intent, hist_closed, feedback, _ = (
            await asyncio.to_thread(s19._epoch_one)
        )
        if (
            hist_supervisor.get(hist_closed.action_id) is not hist_closed
            or hist_supervisor.open_actions != ()
            or hist_commit.new_state.revision != 1
            or hist_commit.new_state.value != 4
            or hist_commit.new_state.last_update is None
            or feedback.feedback is None
        ):
            raise S36EvidenceFailure("synthetic S19 learning authority was not qualified")

        supervisor = ActionSupervisor()
        intent = s19.IntentCommitment()
        intent.commit(
            "escape-threat",
            objective="escape the nearby threat",
            at_ns=1,
            provenance=s19.provenance("s36-explicit-existing-current-intent"),
        )

        budget = EventSchedulerBudget(
            max_pending=4,
            max_epochs_per_batch=2,
            max_total_cognition=2,
            max_event_age_seq=16,
            max_urgent_burst=2,
            per_probe_timeout_s=10,
        )
        scheduler = BoundedEventCognitionScheduler(budget)
        report["scheduler_budget"] = {
            "max_pending": budget.max_pending,
            "max_epochs_per_batch": budget.max_epochs_per_batch,
            "max_total_cognition": budget.max_total_cognition,
            "max_event_age_seq": budget.max_event_age_seq,
            "max_urgent_burst": budget.max_urgent_burst,
            "per_probe_timeout_s": budget.per_probe_timeout_s,
        }

        # There is no trigger grant embedded in the native event. A
        # caller-owned separate grant factory is configured *before* seeing
        # which exact entity appears, and exact identities are bound at call.
        def external_grant(candidate: NativeEventCognitionCandidate):
            return EventCognitionTriggerGrant(
                authority_id="s36-explicit-independent-cognition-only-authority",
                candidate_id=candidate.candidate_id,
                session_id=candidate.session_id,
                event_seq=candidate.event_seq,
                target_entity_id=candidate.target_entity_id,
                granted=True,
                provenance=s19.provenance("s36-preconfigured-independent-trigger"),
            )

        async def actual_probe(candidate: NativeEventCognitionCandidate):
            assert session is not None
            return await _correlated_observe(
                session,
                f"s36-auto-probe:{candidate.event_seq}:{candidate.target_entity_id}",
            )

        def admitted_cognition(ticket):
            # This callback is scheduled automatically by S36 on an admitted
            # event. It does not propose, authorize, issue or execute Action.
            native = _native_threat(
                ticket.correlated_probe,
                ticket.probe_request_id,
                expected_entity_id=ticket.candidate.target_entity_id,
            )
            values, epoch = _native_epoch_two(
                supervisor, intent,
                hist_commit.new_state, hist_commit.new_state,
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
                raise S36EvidenceFailure("automatic bounded cognition did not qualify")
            return {
                "selection": values["plan"].selected.candidate_id,
                "execution_admission": values["admission"].status.value,
                "model_cognition_requested": epoch.cognition_requested,
                "retained_revision": values["read"].revision,
                "native_probe_provenance": ticket.correlated_probe.provenance.reference,
                "actions_issued": 0,
            }

        report["stage"] = "UNSOLICITED_MINEFLAYER_ENTITY_EVENT"
        assert server is not None and server.stdin is not None
        _command(server, "gamerule doMobSpawning false")
        _command(server, "time set midnight")
        _command(
            server,
            "execute at RelaySelf run summon minecraft:zombie ~2 ~ ~ "
            "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}",
        )
        await server.stdin.drain()
        event, candidate = await _await_native_entity_trigger(session)
        if event.kind != "entities" or event.request_id is not None:
            raise S36EvidenceFailure("native entity event was not unsolicited")
        report["source_event"] = {
            "kind": event.kind,
            "seq": event.seq,
            "session_id": event.session_id,
            "entity_id": candidate.target_entity_id,
            "distance_m": candidate.distance_m,
            "candidate_id": candidate.candidate_id,
            "source_provenance": event.provenance.reference,
            "request_id": event.request_id,
        }

        # The caller handles generic native stream delivery. Unlike S35,
        # it does NOT explicitly call any cognition operation here:
        # on_native_event handles admission and scheduling in one bounded
        # callback, after the independently configured policy grant.
        report["stage"] = "AUTOMATIC_BOUNDED_SCHEDULER_CALLBACK"
        disposition, batch = await scheduler.on_native_event(
            event,
            probe=actual_probe,
            grant=external_grant,
            cognition=admitted_cognition,
        )
        if (
            disposition is not EventQueueDisposition.ENQUEUED
            or batch.work_attempted != 1
            or len(batch.outcomes) != 1
            or batch.remaining_pending != 0
            or scheduler.total_cognition != 1
            or batch.outcomes[0].ticket.candidate.candidate_id != candidate.candidate_id
        ):
            raise S36EvidenceFailure("automatic event-to-cognition scheduler not qualified")
        outcome = batch.outcomes[0]
        if (
            outcome.ticket.correlated_probe.seq <= event.seq
            or outcome.ticket.correlated_probe.session_id != event.session_id
        ):
            raise S36EvidenceFailure("auto probe does not bind actual event source")
        report["trigger_result"] = {
            "queue_disposition": disposition.value,
            "batch_work_attempted": batch.work_attempted,
            "total_cognition": scheduler.total_cognition,
            "remaining_pending": batch.remaining_pending,
            "event_id": outcome.event_id,
            "probe_request_id": outcome.ticket.probe_request_id,
            "probe_seq": outcome.ticket.correlated_probe.seq,
            "probe_session_id": outcome.ticket.correlated_probe.session_id,
            "cognition": outcome.cognition_result,
        }
        report["native_event_drives_cognition"] = True

        # Native retransmission of the exact event must not reschedule.
        replay_disposition, replay_batch = await scheduler.on_native_event(
            event, probe=actual_probe, grant=external_grant,
            cognition=admitted_cognition,
        )
        if (
            replay_disposition is not EventQueueDisposition.STALE
            or replay_batch.work_attempted != 0
            or scheduler.total_cognition != 1
        ):
            raise S36EvidenceFailure("same native source event scheduled twice")
        report["source_replay_rejected"] = True
        if supervisor.open_actions != ():
            raise S36EvidenceFailure("scheduler accidentally issued an Action")
        try:
            supervisor.get("s36-unissued-action")
        except UnknownSupervisedAction:
            report["no_action_owner_proven"] = True
        else:
            raise S36EvidenceFailure("scheduler created unknown Action owner")

        await session.shutdown(timeout_s=10)
        report["node_exit_code"] = session.process_returncode
        if report["node_exit_code"] != 0:
            raise S36EvidenceFailure("Node bridge did not shut down cleanly")
        session = None
        report["stage"] = "SUCCESS"
        report["status"] = "PASS"
        report["classification"] = (
            "REAL_EVENT_AUTO_BOUNDED_COGNITION_WITHOUT_ACTION_QUALIFIED"
        )
        result = 0
    except (S31ABlocked, OSError) as exc:
        report["status"] = "BLOCKED"
        report["error"] = str(exc)
        result = 2
        print(f"S36 BLOCKED at {report['stage']}: {exc}", file=sys.stderr)
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        result = 1
        print(f"S36 FAIL at {report['stage']}: {exc}", file=sys.stderr)
    finally:
        if session is not None:
            try:
                report["node_exit_code"] = await session.shutdown(timeout_s=10)
            except Exception as exc:
                report["node_shutdown_error"] = str(exc)
                await session.terminate()
        try:
            await _shutdown_server(server, collector)
        except Exception as exc:
            report["server_shutdown_error"] = str(exc)
            result = 1
        if server is not None:
            report["server_exit_code"] = server.returncode
        if tmp is not None:
            tmp.cleanup()
        if report["status"] == "PASS" and (
            report.get("node_exit_code") != 0
            or report.get("server_exit_code") != 0
        ):
            report["status"] = "FAIL"
            report["classification"] = "TEARDOWN_FAILED_NOT_QUALIFIED"
            report["stage"] = "TEARDOWN"
            report["error"] = "Node / Java did not exit zero"
            result = 1
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        print("S36_REPORT=" + json.dumps(report, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    args = parser.parse_args()
    return asyncio.run(qualify(args.report, args.server_log))


if __name__ == "__main__":
    raise SystemExit(main())
