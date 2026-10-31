"""S39 actual Minecraft: pre-dispatch Node SIGKILL -> fresh-world Action.

Runs a new standalone real Mojang server. S38 quarantines the old generation;
S39 independently grants one Action only for the recovered genuine entitySpawn
and closes its real physical movement through unchanged S15/S16.
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
from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import (
    WorldConsequenceStatus,
    execute_mineflayer_command,
)
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
from relay_self.action import ActionState
from relay_self.action_outcome import record_interpreted_action_outcome
from relay_self.action_supervision import ActionSupervisor
from relay_self.execution_binding import ExecutionBinding
from relay_self.forced_node_loss_fence import (
    ForcedNodeLossFence,
    WorldLossBoundaryError,
    WorldLossState,
)
from relay_self.fresh_source_action import (
    FreshSourceActionGate,
    FreshSourceActionGrant,
    FreshSourceActionRejected,
)
from relay_self.native_event_cognition import (
    EventCognitionTriggerGrant,
    NativeEventCognitionCandidate,
)


class S39EvidenceFailure(RuntimeError):
    """Physical post-fault Action evidence insufficient for qualification."""


async def qualify(report_path: Path, server_log: Path) -> int:
    report: dict[str, Any] = {
        "milestone": "S39", "status": "BLOCKED",
        "classification": "NOT_QUALIFIED", "stage": "START",
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "induced_fault": "ACTUAL_NODE_OS_SIGKILL_BEFORE_ACTION_PROPOSAL",
        "real_fault_injected": False,
        "old_ticket_proposal_denied": False,
        "old_ticket_post_revalidation_denied": False,
        "independent_action_proposal_grant": False,
        "independent_action_issue_grant": False,
        "action_issue_count": 0,
        "physical_actions": [],
        "world_server_survives_fault": True,
        "unattended_reconnect": False,
        "real_world_learning": False,
        "retained_origin": "FROZEN_S19_SYNTHETIC_GOVERNED_REV1",
        "s31b_wsl2_reproduction": "SKIPPED",
        "inflight_unknown_outcome_qualified": False,
    }
    server = collector = None
    session: MineflayerProcessSession | None = None
    temp: tempfile.TemporaryDirectory[str] | None = None
    result = 2
    try:
        if os.environ.get("S39_REAL_SERVER_CI") != "1":
            raise S31ABlocked("S39_REAL_SERVER_CI=1 required")
        if os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("Node test preload forbidden")
        report["stage"] = "PROVISION_REAL_GAME"
        temp = tempfile.TemporaryDirectory(prefix="relay-self-s39-")
        root = Path(temp.name)
        report.update(await asyncio.to_thread(
            _fetch_official_server, root / "minecraft-server.jar",
        ))
        _write_config(root)
        server, collector, _ = await _ready_server(
            root, root / "minecraft-server.jar", server_log,
        )
        past, committed, _, closed, feedback, _ = await asyncio.to_thread(
            s19._epoch_one,
        )
        if (
            past.get(closed.action_id) is not closed
            or past.open_actions != ()
            or committed.new_state.value != 4
            or committed.new_state.revision != 1
            or feedback.feedback is None
        ):
            raise S39EvidenceFailure("frozen S19 retained source not qualified")
        supervisor = ActionSupervisor()
        intent = s19.IntentCommitment()
        intent.commit(
            "escape-threat", objective="escape nearby zombie", at_ns=1,
            provenance=s19.provenance("s39-existing-intent"),
        )
        fence = ForcedNodeLossFence()

        def cognition_grant(candidate: NativeEventCognitionCandidate):
            return EventCognitionTriggerGrant(
                authority_id="s39-cognition-only",
                candidate_id=candidate.candidate_id,
                session_id=candidate.session_id,
                event_seq=candidate.event_seq,
                target_entity_id=candidate.target_entity_id,
                granted=True,
                provenance=s19.provenance("s39-independent-cognition-grant"),
            )

        def cognitive_callback(ticket):
            native = _native_threat(
                ticket.correlated_probe, ticket.probe_request_id,
                expected_entity_id=ticket.candidate.target_entity_id,
            )
            values, epoch = _native_epoch_two(
                supervisor, intent, committed.new_state,
                committed.new_state, expected_revision=1, native=native,
            )
            if (
                epoch.cognition_requested
                or values["plan"].selected is None
                or values["plan"].selected.candidate_id != "MOVE_AWAY"
                or values["admission"].status.value != "admitted"
                or values["external"][1].provenance
                != ticket.correlated_probe.provenance
                or supervisor.open_actions != ()
            ):
                raise S39EvidenceFailure("source-linked cognition failed")
            return {
                "selected": "MOVE_AWAY", "admission": "admitted",
                "source": ticket.correlated_probe.provenance.reference,
                "values": values,
            }

        async def native_probe(candidate: NativeEventCognitionCandidate):
            assert session is not None
            return await _correlated_observe(
                session,
                f"s39-{candidate.session_id}-event-{candidate.event_seq}"
                f"-entity-{candidate.target_entity_id}",
            )

        def action_grant(event, purpose: str):
            return FreshSourceActionGrant(
                authority_id=f"s39-external-{purpose.lower()}-authority",
                purpose=purpose, session_id=event.session_id,
                event_seq=event.event_seq, probe_seq=event.probe_seq,
                entity_id=event.entity_id, action_id="s39-native-action",
                binding_id="s39-native-binding", granted=True,
                provenance=s19.provenance(
                    f"s39-independent-{purpose.lower()}-grant",
                ),
            )

        def native_binding():
            return ExecutionBinding(
                binding_id="s39-native-binding", candidate_ref="MOVE_AWAY",
                required_intent_id="escape-threat",
                skill_execution_id="s39-native-skill",
                skill_ref="escape-movement",
                action_id="s39-native-action",
                action_ref="MOVE_BACKWARD",
                provenance=s19.provenance("s39-external-binding"),
            )

        report["stage"] = "INITIAL_GENUINE_ENTITY_EVENT"
        session = await _new_session()
        old_id = session.started.session_id
        fence.begin_initial(old_id)
        _command(server, "gamerule doMobSpawning false")
        _command(server, "time set midnight")
        _command(
            server,
            "execute at RelaySelf run summon minecraft:zombie ~2 ~ ~ "
            "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}",
        )
        assert server.stdin is not None
        await server.stdin.drain()
        old_event = await fence.run_active(
            session, probe=native_probe, grant=cognition_grant,
            cognition=cognitive_callback,
        )
        report["old_event"] = {
            "session": old_event.session_id, "entity_id": old_event.entity_id,
            "event_seq": old_event.event_seq, "probe_seq": old_event.probe_seq,
        }
        if supervisor.open_actions != ():
            raise S39EvidenceFailure("pre-fault cognition issued Action")

        report["stage"] = "REAL_PRE_ACTION_NODE_SIGKILL"
        if session.process_returncode is not None:
            raise S39EvidenceFailure("Node already dead before forced loss")
        session._process.kill()
        negative = await asyncio.wait_for(session._process.wait(), timeout=10)
        if type(negative) is not int or negative >= 0:
            raise S39EvidenceFailure("real negative process returncode absent")
        report["real_fault_injected"] = True
        report["forced_node_exit_code"] = negative
        try:
            await fence.run_active(
                session, probe=native_probe, grant=cognition_grant,
                cognition=cognitive_callback,
            )
        except MineflayerProcessEnded as exc:
            receipt = fence.observe_forced_failure(
                old_id, transport_error=exc, process_returncode=negative,
            )
        else:
            raise S39EvidenceFailure("no real EOF after child loss")
        if fence.state is not WorldLossState.QUARANTINED:
            raise S39EvidenceFailure("old source not quarantined")
        report["observed_process_fault"] = {
            "old_session": receipt.session_id,
            "returncode": receipt.process_returncode,
            "error": receipt.transport_error,
        }
        old_gate = FreshSourceActionGate(fence, supervisor, old_event)
        try:
            old_gate.propose(
                intent, native_binding(), action_grant(old_event, "PROPOSE"),
                at_ns=31, provenance=s19.provenance("denied-old-proposal"),
            )
        except (FreshSourceActionRejected, WorldLossBoundaryError):
            report["old_ticket_proposal_denied"] = True
        else:
            raise S39EvidenceFailure("old cognition released physical Action")
        session = None

        report["stage"] = "SUPERVISED_FRESH_NATIVE_SOURCE"
        _command(server, "kill @e[type=minecraft:zombie]")
        await server.stdin.drain()
        await asyncio.sleep(2)
        session = await _new_session()
        new_id = session.started.session_id
        if new_id == old_id:
            raise S39EvidenceFailure("Node source UUID reused")
        fence.begin_successor(new_id)
        if fence.state is not WorldLossState.PROBATION:
            raise S39EvidenceFailure("successor not in PROBATION")
        _command(
            server,
            "execute at RelaySelf run summon minecraft:zombie ~2 ~ ~ "
            "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}",
        )
        await server.stdin.drain()
        fresh = await fence.revalidate_successor(
            session, probe=native_probe, grant=cognition_grant,
            cognition=cognitive_callback,
        )
        if (
            fence.state is not WorldLossState.ACTIVE
            or fresh.session_id != new_id
            or fresh.entity_id == old_event.entity_id
            or fresh.event_seq >= fresh.probe_seq
            or fence.host.total_epochs != 2
        ):
            raise S39EvidenceFailure("new genuine World cognition not qualified")
        report["fresh_event"] = {
            "session": fresh.session_id, "entity_id": fresh.entity_id,
            "event_seq": fresh.event_seq, "probe_seq": fresh.probe_seq,
            "probe_request_id": fresh.probe_request_id,
            "source": fresh.ticket.correlated_probe.provenance.reference,
            "selection": fresh.cognition["selected"],
        }
        try:
            old_gate.propose(
                intent, native_binding(), action_grant(old_event, "PROPOSE"),
                at_ns=31, provenance=s19.provenance("old-after-reconnect"),
            )
        except (FreshSourceActionRejected, WorldLossBoundaryError):
            report["old_ticket_post_revalidation_denied"] = True
        else:
            raise S39EvidenceFailure("old proposal resurrected after reconnect")

        report["stage"] = "FRESH_SOURCE_EXPLICIT_ACTION_PROPOSAL_ISSUE"
        gate = FreshSourceActionGate(fence, supervisor, fresh)
        skill, proposed, binding_result = gate.propose(
            intent, native_binding(), action_grant(fresh, "PROPOSE"),
            at_ns=31, provenance=s19.provenance("s39-action-proposal"),
        )
        report["independent_action_proposal_grant"] = True
        if proposed.state is not ActionState.PROPOSED:
            raise S39EvidenceFailure("Action proposal owner missing")
        issued = gate.authorize_issue(
            proposed, native_binding(), action_grant(fresh, "ISSUE"),
            at_ns=32, deadline_ns=100,
            provenance=s19.provenance("s39-action-issue"),
        )
        report["independent_action_issue_grant"] = True
        if (
            issued.state is not ActionState.ISSUED
            or supervisor.get(issued.action_id) is not issued
            or binding_result.action_id != issued.action_id
            or skill.execution_id != issued.skill_execution_id
        ):
            raise S39EvidenceFailure("separate supervised Action not ISSUED")
        report["action_issue_count"] = 1
        command = gate.claim_command(issued, session)
        try:
            gate.claim_command(issued, session)
        except FreshSourceActionRejected:
            report["duplicate_dispatch_denied"] = True
        else:
            raise S39EvidenceFailure("reused one-shot command release")

        report["stage"] = "REAL_ACTION_MOVEMENT_AND_S16_TERMINAL_OUTCOME"
        consequence = await execute_mineflayer_command(
            session, command, timeout_s=9,
            provenance=s19.provenance("s39-physical-world-consequence"),
        )
        if (
            consequence.status is not WorldConsequenceStatus.EXECUTED
            or consequence.session_id != new_id
            or consequence.movement_distance is None
            or consequence.movement_distance < 0.05
        ):
            raise S39EvidenceFailure("genuine physical movement not EXECUTED")
        outcome = interpret_world_consequence(
            issued, binding_result, consequence,
            provenance=s19.provenance("s39-outcome-interpretation"),
        )
        closed = record_interpreted_action_outcome(
            supervisor, outcome, at_ns=40,
        )
        if (
            closed.state is not ActionState.OUTCOME
            or supervisor.get(issued.action_id) is not closed
            or supervisor.open_actions != ()
        ):
            raise S39EvidenceFailure("S16 terminal outcome not closed")
        report["physical_actions"] = [{
            "action_id": closed.action_id,
            "status": consequence.status.value, "terminal": closed.state.value,
            "session_id": consequence.session_id,
            "before_seq": consequence.before_observation.seq,
            "dispatch_seq": consequence.dispatch_receipt.seq,
            "cleanup_seq": consequence.cleanup_receipt.seq,
            "after_seq": consequence.after_observation.seq,
            "movement_m": consequence.movement_distance,
            "evidence": consequence.after_observation.provenance.reference,
        }]
        report["skill_state_after_action"] = skill.state.value
        report["stage"] = "REAL_NODE_CLEAN_SHUTDOWN"
        exit_code = await session.shutdown(timeout_s=10)
        report["recovered_node_exit_code"] = exit_code
        if exit_code != 0:
            raise S39EvidenceFailure("successor Mineflayer failed clean shutdown")
        fence.close_successor(new_id)
        session = None

        report["status"] = "PASS"
        report["classification"] = (
            "FRESH_SOURCE_POST_FAULT_REAL_ACTION_OUTCOME_QUALIFIED"
        )
        report["stage"] = "SUCCESS"
        result = 0
    except (S31ABlocked, OSError) as exc:
        report["status"] = "BLOCKED"
        report["error"] = f"{type(exc).__name__}: {exc}"
        result = 2
        print(f"S39 BLOCKED at {report['stage']}: {exc}", file=sys.stderr)
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        result = 1
        print(f"S39 FAIL at {report['stage']}: {exc}", file=sys.stderr)
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
            report["status"] = "FAIL"
            report["error"] = f"server cleanup: {exc}"
            result = 1
        if server is not None:
            report["server_exit_code"] = server.returncode
        if temp is not None:
            temp.cleanup()
        if report["status"] == "PASS" and report.get("server_exit_code") != 0:
            report["status"] = "FAIL"
            report["classification"] = "S39_SERVER_TEARDOWN_NOT_QUALIFIED"
            report["error"] = "real Java game server did not exit0"
            result = 1
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8",
        )
        print("S39_REPORT=" + json.dumps(report, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    args = parser.parse_args()
    return asyncio.run(qualify(args.report, args.server_log))


if __name__ == "__main__":
    raise SystemExit(main())
