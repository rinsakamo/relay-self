"""S40 actual Minecraft: post-dispatch SIGKILL -> existing S16 UNKNOWN.

Runs one genuine Mojang server and two genuine Mineflayer processes. After
S38's first quarantine and fresh native revalidation, kill the successor
Node child only AFTER a genuine applied set_control effect result. Existing
S15 returns incomplete FAILED evidence; existing S16 must close UNKNOWN.
A physically finished movement is NOT claimed.
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
from adapters.mineflayer.execution import (
    WorldConsequenceStatus,
    execute_mineflayer_command,
)
from adapters.mineflayer.process_session import (
    MineflayerProcessEnded,
    MineflayerProcessSession,
)
from adapters.mineflayer.python_protocol import MineflayerEffectResult
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
from relay_self.inflight_node_loss import close_inflight_node_loss_unknown
from relay_self.native_event_cognition import (
    EventCognitionTriggerGrant,
    NativeEventCognitionCandidate,
)


class S40EvidenceFailure(RuntimeError):
    """Do not claim in-flight unknown without genuine process/dead-source evidence."""


class KillAfterAppliedEffect:
    """Test-only transparent S15 adapter: kill actual Node on applied effect.

    The actual Mineflayer effect_result is decoded by the real process
    session first. This wrapper provides no forged protocol messages.
    """

    def __init__(self, session: MineflayerProcessSession, action_id: str) -> None:
        self.session = session
        self.started = session.started
        self.action_id = action_id
        self.killed_returncode: int | None = None
        self.actual_applied: MineflayerEffectResult | None = None

    async def receive(self):
        frame = await self.session.receive()
        if (
            isinstance(frame, MineflayerEffectResult)
            and frame.action_id == self.action_id
            and frame.effect == "set_control"
            and frame.result == "applied"
        ):
            if self.actual_applied is not None:
                raise S40EvidenceFailure("duplicate applied dispatch")
            if self.session.process_returncode is not None:
                raise S40EvidenceFailure("child died before actual applied dispatch")
            self.actual_applied = frame
            # Exactly here, after the native applied receipt and before S15
            # cleanup/final observation, kill the actual OS child process.
            self.session._process.kill()
            self.killed_returncode = await asyncio.wait_for(
                self.session._process.wait(), timeout=10,
            )
            if self.killed_returncode >= 0:
                raise S40EvidenceFailure("actual OS SIGKILL did not exit negative")
        return frame

    async def send_observe(self):
        await self.session.send_observe()

    async def send_set_control(self, action_id: str, *, control: str, state: bool):
        await self.session.send_set_control(
            action_id, control=control, state=state,
        )

    async def send_clear_controls(self, action_id: str):
        await self.session.send_clear_controls(action_id)


async def qualify(report_path: Path, server_log: Path) -> int:
    report: dict[str, Any] = {
        "milestone": "S40", "status": "BLOCKED",
        "classification": "NOT_QUALIFIED", "stage": "START",
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "induced_fault": "TWO_REAL_NODE_SIGKILL_INITIAL_AND_POST_APPLIED_DISPATCH",
        "real_fault_injected": False,
        "old_ticket_proposal_denied": False,
        "old_ticket_post_revalidation_denied": False,
        "independent_action_proposal_grant": False,
        "independent_action_issue_grant": False,
        "action_issue_count": 0,
        "physical_actions": [],
        "physical_completion_observed": False,
        "world_effect_final_state": "UNDETERMINED",
        "inflight_applied_observed": False,
        "inflight_node_killed": False,
        "terminal_action_state": "NOT_CLOSED",
        "no_retry_enforced": False,
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
        if os.environ.get("S40_REAL_SERVER_CI") != "1":
            raise S31ABlocked("S40_REAL_SERVER_CI=1 required")
        if os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("Node test preload forbidden")
        report["stage"] = "PROVISION_REAL_GAME"
        temp = tempfile.TemporaryDirectory(prefix="relay-self-s40-")
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
            raise S40EvidenceFailure("frozen S19 retained source not qualified")
        supervisor = ActionSupervisor()
        intent = s19.IntentCommitment()
        intent.commit(
            "escape-threat", objective="escape nearby zombie", at_ns=1,
            provenance=s19.provenance("s40-existing-intent"),
        )
        fence = ForcedNodeLossFence()

        def cognition_grant(candidate: NativeEventCognitionCandidate):
            return EventCognitionTriggerGrant(
                authority_id="s40-cognition-only",
                candidate_id=candidate.candidate_id,
                session_id=candidate.session_id,
                event_seq=candidate.event_seq,
                target_entity_id=candidate.target_entity_id,
                granted=True,
                provenance=s19.provenance("s40-independent-cognition-grant"),
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
                raise S40EvidenceFailure("source-linked cognition failed")
            return {
                "selected": "MOVE_AWAY", "admission": "admitted",
                "source": ticket.correlated_probe.provenance.reference,
                "values": values,
            }

        async def native_probe(candidate: NativeEventCognitionCandidate):
            assert session is not None
            return await _correlated_observe(
                session,
                f"s40-{candidate.session_id}-event-{candidate.event_seq}"
                f"-entity-{candidate.target_entity_id}",
            )

        def action_grant(event, purpose: str):
            return FreshSourceActionGrant(
                authority_id=f"s40-external-{purpose.lower()}-authority",
                purpose=purpose, session_id=event.session_id,
                event_seq=event.event_seq, probe_seq=event.probe_seq,
                entity_id=event.entity_id, action_id="s40-native-action",
                binding_id="s40-native-binding", granted=True,
                provenance=s19.provenance(
                    f"s40-independent-{purpose.lower()}-grant",
                ),
            )

        def native_binding():
            return ExecutionBinding(
                binding_id="s40-native-binding", candidate_ref="MOVE_AWAY",
                required_intent_id="escape-threat",
                skill_execution_id="s40-native-skill",
                skill_ref="escape-movement",
                action_id="s40-native-action",
                action_ref="MOVE_BACKWARD",
                provenance=s19.provenance("s40-external-binding"),
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
            raise S40EvidenceFailure("pre-fault cognition issued Action")

        report["stage"] = "REAL_PRE_ACTION_NODE_SIGKILL"
        if session.process_returncode is not None:
            raise S40EvidenceFailure("Node already dead before forced loss")
        session._process.kill()
        negative = await asyncio.wait_for(session._process.wait(), timeout=10)
        if type(negative) is not int or negative >= 0:
            raise S40EvidenceFailure("real negative process returncode absent")
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
            raise S40EvidenceFailure("no real EOF after child loss")
        if fence.state is not WorldLossState.QUARANTINED:
            raise S40EvidenceFailure("old source not quarantined")
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
            raise S40EvidenceFailure("old cognition released physical Action")
        session = None

        report["stage"] = "SUPERVISED_FRESH_NATIVE_SOURCE"
        _command(server, "kill @e[type=minecraft:zombie]")
        await server.stdin.drain()
        await asyncio.sleep(2)
        session = await _new_session()
        new_id = session.started.session_id
        if new_id == old_id:
            raise S40EvidenceFailure("Node source UUID reused")
        fence.begin_successor(new_id)
        if fence.state is not WorldLossState.PROBATION:
            raise S40EvidenceFailure("successor not in PROBATION")
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
            raise S40EvidenceFailure("new genuine World cognition not qualified")
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
            raise S40EvidenceFailure("old proposal resurrected after reconnect")

        report["stage"] = "FRESH_SOURCE_EXPLICIT_ACTION_PROPOSAL_ISSUE"
        gate = FreshSourceActionGate(fence, supervisor, fresh)
        skill, proposed, binding_result = gate.propose(
            intent, native_binding(), action_grant(fresh, "PROPOSE"),
            at_ns=31, provenance=s19.provenance("s40-action-proposal"),
        )
        report["independent_action_proposal_grant"] = True
        if proposed.state is not ActionState.PROPOSED:
            raise S40EvidenceFailure("Action proposal owner missing")
        issued = gate.authorize_issue(
            proposed, native_binding(), action_grant(fresh, "ISSUE"),
            at_ns=32, deadline_ns=100,
            provenance=s19.provenance("s40-action-issue"),
        )
        report["independent_action_issue_grant"] = True
        if (
            issued.state is not ActionState.ISSUED
            or supervisor.get(issued.action_id) is not issued
            or binding_result.action_id != issued.action_id
            or skill.execution_id != issued.skill_execution_id
        ):
            raise S40EvidenceFailure("separate supervised Action not ISSUED")
        report["action_issue_count"] = 1
        command = gate.claim_command(issued, session)
        try:
            gate.claim_command(issued, session)
        except FreshSourceActionRejected:
            report["duplicate_dispatch_denied"] = True
        else:
            raise S40EvidenceFailure("reused one-shot command release")

        report["stage"] = "KILL_REAL_NODE_AFTER_NATIVE_APPLIED_DISPATCH"
        intercepted = KillAfterAppliedEffect(session, command.action_id)
        consequence = await execute_mineflayer_command(
            intercepted, command, timeout_s=9,
            provenance=s19.provenance("s40-incomplete-inflight-world-consequence"),
        )
        if (
            intercepted.actual_applied is None
            or intercepted.killed_returncode is None
            or intercepted.killed_returncode >= 0
            or consequence.status is not WorldConsequenceStatus.FAILED
            or consequence.dispatch_receipt is None
            or consequence.dispatch_receipt != intercepted.actual_applied
            or consequence.dispatch_receipt.result != "applied"
            or consequence.before_observation is None
            or consequence.after_observation is not None
            or consequence.cleanup_receipt is not None
            or consequence.movement_distance is not None
            or consequence.error is None
            or "MineflayerProcessEnded" not in consequence.error
        ):
            raise S40EvidenceFailure(
                "live Node loss did not interrupt actual applied in-flight Action"
            )
        report["inflight_applied_observed"] = True
        report["inflight_node_killed"] = True
        report["inflight_node_exit_code"] = intercepted.killed_returncode
        report["inflight_dispatch"] = {
            "session_id": consequence.session_id,
            "before_seq": consequence.before_observation.seq,
            "applied_effect_seq": consequence.dispatch_receipt.seq,
            "effect_result": consequence.dispatch_receipt.result,
            "cleanup_receipt": None,
            "after_observation": None,
            "world_consequence_status": consequence.status.value,
            "error": consequence.error,
        }

        # Genuine stdout EOF: no test substitute, no invented World result.
        report["stage"] = "GENUINE_INFLIGHT_NODE_EOF_QUARANTINE"
        observed_end = None
        for _ in range(64):
            try:
                await asyncio.wait_for(session.receive(), timeout=2)
            except MineflayerProcessEnded as exc:
                observed_end = exc
                break
        if observed_end is None:
            raise S40EvidenceFailure("real post-dispatch Node EOF missing")
        second_fault = fence.observe_forced_failure(
            new_id,
            transport_error=observed_end,
            process_returncode=intercepted.killed_returncode,
        )
        if fence.state is not WorldLossState.QUARANTINED:
            raise S40EvidenceFailure("inflight dead World source not quarantined")
        report["second_fault"] = {
            "session": second_fault.session_id,
            "returncode": second_fault.process_returncode,
            "typed_error": second_fault.transport_error,
        }

        report["stage"] = "EXISTING_S16_UNKNOWN_TERMINAL"
        unknown, unknown_receipt = close_inflight_node_loss_unknown(
            fence, supervisor, issued, binding_result, command, consequence,
            session_id=new_id,
            transport_error=observed_end,
            process_returncode=intercepted.killed_returncode,
            at_ns=40,
            provenance=s19.provenance("s40-supervised-unknown-interpretation"),
        )
        if (
            unknown.state is not ActionState.UNKNOWN
            or supervisor.get(issued.action_id) is not unknown
            or supervisor.open_actions != ()
            or unknown_receipt.replay_authorized
        ):
            raise S40EvidenceFailure("inflight uncertainty not terminal UNKNOWN")
        report["unknown_receipt"] = {
            "action": unknown_receipt.action_id,
            "binding": unknown_receipt.binding_id,
            "session": unknown_receipt.session_id,
            "before_seq": unknown_receipt.before_seq,
            "applied_seq": unknown_receipt.applied_dispatch_seq,
            "returncode": unknown_receipt.process_returncode,
            "source_status": unknown_receipt.raw_world_status,
            "interpretation_reason": unknown_receipt.interpretation_reason,
            "action_state": unknown_receipt.terminal_action_state,
            "replay_authorized": unknown_receipt.replay_authorized,
        }
        try:
            gate.claim_command(issued, session)
        except (FreshSourceActionRejected, WorldLossBoundaryError):
            report["no_retry_enforced"] = True
        else:
            raise S40EvidenceFailure("dead source permitted second Action dispatch")
        report["terminal_action_state"] = "UNKNOWN"
        report["inflight_unknown_outcome_qualified"] = True
        report["skill_state_after_action"] = skill.state.value
        report["action_issue_count"] = 1
        report["physical_completion_observed"] = False
        # This test cannot determine if the Minecraft body moved before
        # SIGKILL. It must neither report observed success nor no movement.
        report["world_effect_final_state"] = "UNDETERMINED"
        session = None  # The real second Node is already dead.

        report["status"] = "PASS"
        report["classification"] = (
            "REAL_INFLIGHT_NODE_SIGKILL_APPLIED_DISPATCH_UNKNOWN_NO_RETRY_QUALIFIED"
        )
        report["stage"] = "SUCCESS"
        result = 0
    except (S31ABlocked, OSError) as exc:
        report["status"] = "BLOCKED"
        report["error"] = f"{type(exc).__name__}: {exc}"
        result = 2
        print(f"S40 BLOCKED at {report['stage']}: {exc}", file=sys.stderr)
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        result = 1
        print(f"S40 FAIL at {report['stage']}: {exc}", file=sys.stderr)
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
            report["classification"] = "S40_SERVER_TEARDOWN_NOT_QUALIFIED"
            report["error"] = "real Java game server did not exit0"
            result = 1
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8",
        )
        print("S40_REPORT=" + json.dumps(report, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    args = parser.parse_args()
    return asyncio.run(qualify(args.report, args.server_log))


if __name__ == "__main__":
    raise SystemExit(main())
