"""S35 actual Minecraft unsolicited entity event -> separately admitted cognition.

Genuine Mineflayer emits the 'entities' event BEFORE any observe request.
The event alone creates a typed cognition candidate, NOT an Action. A
distinct correlated probe verifies the target; an independent caller grant
admits one cognitive epoch through frozen S34 ATT/BLF/.../ADMISSION.
No S15 effect commands, no Action proposal/authorization/issue, no learner.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerConnectionEnd,
    MineflayerObservation,
)
from adapters.mineflayer.s31a_real_server_ci import (
    MINECRAFT_VERSION,
    MINEFLAYER_VERSION,
    S31ABlocked,
    _await_spawn,
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
from relay_self.action_supervision import (
    ActionSupervisor,
    UnknownSupervisedAction,
)
from relay_self.native_event_cognition import (
    EventCognitionLedger,
    EventCognitionNotAdmitted,
    EventCognitionTriggerGrant,
    NativeEventCognitionCandidate,
    native_entity_event_to_cognition_candidate,
)


class S35EvidenceFailure(RuntimeError):
    """Actual unsolicited event or admitted cognitive boundary was not qualified."""


async def _await_native_entity_trigger(
    session: MineflayerProcessSession, *, timeout_s: float = 35,
) -> tuple[MineflayerObservation, NativeEventCognitionCandidate]:
    deadline = time.monotonic() + timeout_s
    for _ in range(200):
        seconds = deadline - time.monotonic()
        if seconds <= 0:
            break
        try:
            message = await asyncio.wait_for(
                session.receive(), timeout=max(0.05, seconds),
            )
        except TimeoutError as exc:
            raise S35EvidenceFailure(
                "no unsolicited actual Mineflayer entitySpawn event"
            ) from exc
        if isinstance(message, (MineflayerAdapterErrorMessage, MineflayerConnectionEnd)):
            raise S35EvidenceFailure(f"Mineflayer died before event: {message}")
        if not isinstance(message, MineflayerObservation):
            continue
        if message.kind != "entities":
            continue
        candidate = native_entity_event_to_cognition_candidate(message)
        if candidate is not None:
            return message, candidate
    raise S35EvidenceFailure("no qualifying unsolicited native entity event")


async def qualify(report_path: Path, server_log: Path) -> int:
    report: dict[str, Any] = {
        "milestone": "S35",
        "status": "BLOCKED",
        "classification": "NOT_QUALIFIED",
        "stage": "START",
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "unsolicited_event_required": True,
        "first_explicit_probe_after_unsolicited_event": True,
        "new_action_proposed": False,
        "new_action_authorized": False,
        "new_action_issued": False,
        "automatic_action_issued": False,
        "relay_engine_called": False,
        "autonomous_scheduler": False,
        "retained_source": "CALLER_SEEDED_REV1_NOT_LEARNED_IN_S35",
        "physical_action_executed": False,
        "world_authenticity_attested": False,
        "local_codex_s31b": "SKIPPED",
    }
    server = None
    collector = None
    session: MineflayerProcessSession | None = None
    tmp: tempfile.TemporaryDirectory[str] | None = None
    exit_code = 2
    try:
        if os.environ.get("S35_REAL_SERVER_CI") != "1":
            raise S31ABlocked("S35_REAL_SERVER_CI=1 required")
        if os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("S30 test-only Mineflayer preload forbidden")
        report["stage"] = "OFFICIAL_SERVER_PROVISION"
        tmp = tempfile.TemporaryDirectory(prefix="relay-self-s35-")
        root = Path(tmp.name)
        report.update(await asyncio.to_thread(
            _fetch_official_server, root / "minecraft-server.jar",
        ))
        _write_config(root)
        report["stage"] = "JAVA_START"
        server, collector, _ = await _ready_server(
            root, root / "minecraft-server.jar", server_log,
        )
        report["stage"] = "MINEFLAYER_SPAWN"
        session = await _new_session()
        report["session_id"] = session.started.session_id
        # The helper _new_session already calls the unchanged actual
        # Mineflayer session launcher and _await_spawn once.
        report["stage"] = "SPONTANEOUS_ENTITY_SPAWN_EVENT"
        _command(server, "gamerule doMobSpawning false")
        _command(server, "time set midnight")
        _command(
            server,
            "execute at RelaySelf run summon minecraft:zombie ~2 ~ ~ "
            "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}",
        )
        assert server.stdin is not None
        await server.stdin.drain()
        # No observe command has been sent yet. This must be a real
        # unsolicited entities frame from bridge.mjs entitySpawn listener.
        native_event, candidate = await _await_native_entity_trigger(session)
        if native_event.session_id != session.started.session_id:
            raise S35EvidenceFailure("native event was not in actual Node session")
        report["unsolicited_event"] = {
            "kind": native_event.kind,
            "seq": native_event.seq,
            "session_id": candidate.session_id,
            "entity_id": candidate.target_entity_id,
            "distance_m": candidate.distance_m,
            "candidate_id": candidate.candidate_id,
            "source_provenance": candidate.source_provenance.reference,
            "request_id": native_event.request_id,
        }

        report["stage"] = "INDEPENDENT_CORRELATED_PROBE"
        request_id = "s35-native-event-probe:001"
        probe = await _correlated_observe(session, request_id)
        if probe.seq <= native_event.seq:
            raise S35EvidenceFailure("correlated follow-up did not advance event seq")
        native = _native_threat(
            probe, request_id, expected_entity_id=candidate.target_entity_id,
        )
        report["followup_probe"] = {
            "request_id": native.request_id,
            "kind": probe.kind,
            "seq": probe.seq,
            "distance_m": native.distance_m,
            "entity_id": native.entity_id,
            "session_id": probe.session_id,
            "source_provenance": probe.provenance.reference,
        }

        report["stage"] = "SEPARATE_TRIGGER_AUTHORITY"
        ledger = EventCognitionLedger()
        denied = EventCognitionTriggerGrant(
            authority_id="s35-explicit-trigger-denial",
            candidate_id=candidate.candidate_id,
            session_id=candidate.session_id,
            event_seq=candidate.event_seq,
            target_entity_id=candidate.target_entity_id,
            granted=False,
            provenance=s19.provenance("s35-independent-trigger-denial"),
        )
        try:
            ledger.admit(candidate, probe, denied, request_id=request_id)
        except EventCognitionNotAdmitted:
            report["denied_trigger_rejected"] = True
        else:
            raise S35EvidenceFailure("denied event authority incorrectly admitted")

        grant = EventCognitionTriggerGrant(
            authority_id="s35-explicit-cognition-only-authority",
            candidate_id=candidate.candidate_id,
            session_id=candidate.session_id,
            event_seq=candidate.event_seq,
            target_entity_id=candidate.target_entity_id,
            granted=True,
            provenance=s19.provenance("s35-independent-trigger-authorization"),
        )
        ticket = ledger.admit(candidate, probe, grant, request_id=request_id)
        try:
            ledger.admit(candidate, probe, grant, request_id=request_id)
        except EventCognitionNotAdmitted:
            report["replayed_trigger_rejected"] = True
        else:
            raise S35EvidenceFailure("replayed cognition ticket admitted twice")

        report["stage"] = "EXPLICIT_BOUNDED_COGNITIVE_EPOCH"
        supervisor = ActionSupervisor()
        intent = s19.IntentCommitment()
        intent.commit(
            "escape-threat", objective="escape the nearby threat",
            at_ns=1, provenance=s19.provenance("s35-caller-current-intent"),
        )
        # Rev1 here is an explicitly seeded cognitive policy input.
        # There is no S35 learning, feedback or preceding physical Action.
        state = s19.LearningPreferenceState(
            target_id="risk_weight", value=4, minimum=0, maximum=10,
            revision=1, origin_provenance=s19.provenance("s35-caller-owned-retained"),
        )
        values, epoch = _native_epoch_two(
            supervisor, intent, state, state,
            expected_revision=1, native=native,
        )
        if (
            values["external"][1].provenance != ticket.correlated_probe.provenance
            or values["attention"].selected[0].candidate_id != "E1"
            or values["plan"].selected is None
            or values["plan"].selected.candidate_id != "MOVE_AWAY"
            or values["admission"].status.value != "admitted"
            or epoch.cognition_requested
            or supervisor.open_actions != ()
        ):
            raise S35EvidenceFailure("event-driven bounded cognition did not qualify")
        try:
            supervisor.get("action-s35-should-not-exist")
        except UnknownSupervisedAction:
            report["supervisor_action_absence_checked"] = True
        else:
            raise S35EvidenceFailure("unexpected Action issue owner after cognition")

        report["cognition"] = {
            "source_event_id": ticket.event_id,
            "source_probe_id": ticket.probe_request_id,
            "source_provenance": ticket.correlated_probe.provenance.reference,
            "selected_candidate": values["plan"].selected.candidate_id,
            "execution_admission": values["admission"].status.value,
            "retained_revision": values["read"].revision,
            "outer_coordinator_requested_model": epoch.cognition_requested,
            "action_proposal": False,
            "action_authorization": False,
            "action_issue": False,
        }

        await session.shutdown(timeout_s=10)
        report["bridge_exit_code"] = session.process_returncode
        if report["bridge_exit_code"] != 0:
            raise S35EvidenceFailure("Node bridge failed clean shutdown")
        session = None
        report["stage"] = "SUCCESS"
        report["status"] = "PASS"
        report["classification"] = (
            "REAL_ENTITY_EVENT_EXPLICIT_COGNITION_TRIGGER_NO_ACTION_QUALIFIED"
        )
        exit_code = 0
    except (S31ABlocked, OSError) as exc:
        report["status"] = "BLOCKED"
        report["error"] = str(exc)
        exit_code = 2
        print(f"S35 BLOCKED at {report['stage']}: {exc}", file=sys.stderr)
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 1
        print(f"S35 FAIL at {report['stage']}: {exc}", file=sys.stderr)
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
            report.get("server_exit_code") != 0
            or report.get("bridge_exit_code") != 0
        ):
            report["status"] = "FAIL"
            report["classification"] = "TEARDOWN_FAILED_NOT_QUALIFIED"
            report["stage"] = "TEARDOWN"
            report["error"] = "process teardown not exact exit0"
            exit_code = 1
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("S35_REPORT=" + json.dumps(report, sort_keys=True))
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    args = parser.parse_args()
    return asyncio.run(qualify(args.report, args.server_log))


if __name__ == "__main__":
    raise SystemExit(main())
