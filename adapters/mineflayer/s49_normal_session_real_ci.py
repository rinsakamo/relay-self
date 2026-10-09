"""S49 physical feature gate: autonomous host L0 with two real Actions.

Disposable Mojang Java 1.21.8 and unmodified Mineflayer 4.39.0. The
experimenter changes only external World zombies; the persistent host loop,
not the staging coroutine, decides WAIT/MOVE and issues independently granted
Action through frozen S14/S15/S16. No language model or durable learned policy.
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
from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.normal_action import (
    NormalActionAuthorization,
    NormalActionStage,
    NormalSessionActionExecutor,
    NormalWorldL0,
)
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerEntityHurt,
    MineflayerObservation,
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
from relay_self.action_supervision import ActionSupervisor
from relay_self.execution_binding import (
    ExecutionBinding,
    resolve_execution_binding,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant
from relay_self.world_conditioned_choice import WorldChoiceKind


class S49PhysicalFailure(RuntimeError):
    """The real native World did not support the claimed autonomous behavior."""


class NativeObservationOnly:
    """Adapter-local native frame filter; never manufactures observations.

    Mineflayer entity_hurt notifications may arrive unsolicited and do not
    themselves request the S44 entity-geometry policy. Every other unexpected
    protocol message remains fail-closed, with its exact type recorded.
    """

    def __init__(self, session: MineflayerProcessSession) -> None:
        self.session = session
        self.started = session.started
        self.ignored_hurt_frames = 0
        self.ignored_non_target_entities = 0

    async def receive(self):
        for _ in range(60):
            frame = await self.session.receive()
            if isinstance(frame, MineflayerObservation):
                if (
                    frame.kind == "entities"
                    and not any(e.name == "zombie" for e in frame.snapshot.nearby_entities)
                ):
                    # Other World entities do not trigger *zombie* control,
                    # but we do not infer that the World is otherwise safe.
                    self.ignored_non_target_entities += 1
                    continue
                return frame
            if isinstance(frame, MineflayerEntityHurt):
                self.ignored_hurt_frames += 1
                continue
            raise S49PhysicalFailure(
                f"unexpected native host frame {type(frame).__name__}: {frame!r}"
            )
        raise S49PhysicalFailure("non-observation native frame bound exhausted")


def source(tag: str) -> Provenance:
    return Provenance("s49-independent-operator", tag)


async def qualify(report_path: Path, server_log: Path) -> int:
    report: dict[str, Any] = {
        "milestone": "S49", "stage": "START", "status": "BLOCKED",
        "classification": "PENDING_REAL_NATIVE_EVIDENCE",
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "actual_native_actions": [],
        "decisions": [],
        "real_model_calls": 0,
        "learning_in_world": False,
        "retained_origin": "S19_FROZEN_SYNTHETIC_GOVERNED_REV1",
        "automatic_goal_selection": False,
        "auto_crash_recovery": False,
    }
    server = collector = session = staging = temp = None
    rc = 2
    try:
        if os.environ.get("S49_REAL_SERVER_CI") != "1" or os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("explicit S49 real server env and no Node shim required")
        report["stage"] = "PROVISION_DISPOSABLE_MOJANG_GAME"
        temp = tempfile.TemporaryDirectory(prefix="relay-self-s49-")
        root = Path(temp.name)
        report.update(await asyncio.to_thread(_fetch_official_server, root / "minecraft.jar"))
        _write_config(root)
        server, collector, _ = await _ready_server(
            root, root / "minecraft.jar", server_log,
        )
        report["stage"] = "AUTHENTIC_NATIVE_SELF_SESSION"
        session = await _new_session()
        sid = session.started.session_id
        report["session_id"] = sid
        _, committed, _, _, _, _ = await asyncio.to_thread(s19._epoch_one)
        retained = committed.new_state
        if retained.target_id != "risk_weight" or retained.revision != 1 or retained.value != 4:
            raise S49PhysicalFailure("frozen governed retained source changed")
        intent = IntentCommitment()
        intent.commit(
            "escape-threat", objective="escape near zombie", at_ns=1,
            provenance=source("committed-existing-intent"),
        )
        host = NormalWorldL0(
            sid, "escape-threat", retained, max_events=3, max_action_requests=2,
        )
        executor = NormalSessionActionExecutor(sid, intent)
        probes = {}

        async def reprobe(frame):
            request_id = f"s49-actual:{sid}:event-{frame.seq}"
            reading = await _correlated_observe(session, request_id)
            probes[reading.seq] = reading
            report.setdefault("source_pair_trace", []).append({
                "event_seq": frame.seq,
                "event_kind": frame.kind,
                "event_entities": [
                    {"name": e.name, "id": e.entity_id, "d": e.distance}
                    for e in frame.snapshot.nearby_entities
                ],
                "probe_seq": reading.seq,
                "probe_entities": [
                    {"name": e.name, "id": e.entity_id, "d": e.distance}
                    for e in reading.snapshot.nearby_entities
                ],
            })
            return reading

        def decide_grant(choice, event_seq):
            if choice.selection is not WorldChoiceKind.MOVE_AWAY:
                raise S49PhysicalFailure("WAIT attempted to request Action")
            return L0ActionGrant(
                authority_id=f"s49-preconfigured-escape-{event_seq}",
                action_id=f"s49-native-move-{event_seq}",
                intent_id="escape-threat", session_id=sid,
                event_seq=event_seq, probe_seq=choice.probe_seq,
                entity_id=choice.entity_id, granted=True,
                provenance=source(f"l0-request-{event_seq}"),
            )

        def authorize(step, stage):
            return NormalActionAuthorization(
                stage=stage, authority_id=f"s49-{stage.value.lower()}-{step.event_seq}",
                intent_id="escape-threat", session_id=sid,
                action_id=step.action_request_id, event_seq=step.event_seq,
                probe_seq=step.choice.probe_seq, entity_id=step.choice.entity_id,
                granted=True,
                provenance=source(f"independent-{stage.value.lower()}-{step.event_seq}"),
            )

        async def on_action(step):
            probe = probes[step.choice.probe_seq]
            native = _native_threat(
                probe, probe.request_id, expected_entity_id=step.choice.entity_id,
            )
            if native.distance_m >= 4:
                raise S49PhysicalFailure("actual Action without a close zombie")
            values, epoch = _native_epoch_two(
                ActionSupervisor(), intent, retained, retained,
                expected_revision=1, native=native,
            )
            if (
                epoch.cognition_requested
                or values["plan"].selected is None
                or values["plan"].selected.candidate_id != "MOVE_AWAY"
                or values["admission"].status.value != "admitted"
            ):
                raise S49PhysicalFailure("full S14 native admission was not independently satisfied")
            binding = ExecutionBinding(
                binding_id=f"s49-binding-{step.event_seq}",
                candidate_ref="MOVE_AWAY", required_intent_id="escape-threat",
                skill_execution_id=f"s49-skill-{step.event_seq}",
                skill_ref="escape-movement", action_id=step.action_request_id,
                action_ref="MOVE_BACKWARD",
                provenance=source(f"binding-{step.event_seq}"),
            )
            bound = resolve_execution_binding(
                values["admission"], values["control"], values["route"],
                intent, values["policies"][-2], binding,
                provenance=source(f"admitted-{step.event_seq}"),
            )
            receipt = await executor.execute(
                session, step, bound, probe,
                authorize(step, NormalActionStage.PROPOSE),
                authorize(step, NormalActionStage.ISSUE),
            )
            if (
                receipt.terminal.state is not ActionState.OUTCOME
                or receipt.consequence.status is not WorldConsequenceStatus.EXECUTED
                or receipt.consequence.movement_distance is None
                or receipt.consequence.movement_distance < 0.05
            ):
                raise S49PhysicalFailure("World movement or existing S16 OUTCOME absent")
            report["actual_native_actions"].append({
                "action": receipt.terminal.action_id,
                "terminal": receipt.terminal.state.value,
                "source": receipt.consequence.session_id,
                "movement_m": receipt.consequence.movement_distance,
                "event_seq": step.event_seq,
                "probe_seq": step.choice.probe_seq,
            })

        async def stage_world():
            assert server is not None and server.stdin is not None
            _command(server, "gamerule doMobSpawning false")
            await server.stdin.drain()
            await asyncio.sleep(2)
            for distance_m, hold in ((10, 5), (2, 8), (2, 8)):
                _command(server, "kill @e[type=minecraft:zombie]")
                await server.stdin.drain()
                await asyncio.sleep(2)
                _command(
                    server,
                    f"execute at RelaySelf run summon minecraft:zombie ~{distance_m} ~ ~ "
                    "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}",
                )
                await server.stdin.drain()
                await asyncio.sleep(hold)

        report["stage"] = "UNATTENDED_NATIVE_EVENT_LOOP"
        staging = asyncio.create_task(stage_world())
        observation_source = NativeObservationOnly(session)
        trace = await asyncio.wait_for(
            host.run_session(
                observation_source, probe=reprobe, grant=decide_grant,
                on_action_request=on_action, max_frames=320,
            ),
            timeout=95,
        )
        report["ignored_hurt_frames"] = observation_source.ignored_hurt_frames
        report["ignored_non_target_entities"] = observation_source.ignored_non_target_entities
        report["decisions"] = [{
            "event_seq": s.event_seq,
            "entity_id": s.choice.entity_id,
            "probe_seq": s.choice.probe_seq,
            "distance_m": s.choice.distance_m,
            "selected": s.choice.selection.value,
            "issued": s.asks_for_action,
        } for s in trace]
        if (
            len(trace) != 3
            or [s.choice.selection.value for s in trace]
            != ["WAIT", "MOVE_AWAY", "MOVE_AWAY"]
            or len({s.choice.entity_id for s in trace}) != 3
            or len(report["actual_native_actions"]) != 2
            or executor.supervisor.open_actions
            or executor.supervisor.get(trace[1].action_request_id).state is not ActionState.OUTCOME
            or executor.supervisor.get(trace[2].action_request_id).state is not ActionState.OUTCOME
            or trace[0].asks_for_action
            or host.action_requests != 2
            or host.events != 3
        ):
            raise S49PhysicalFailure("not three unattended decisions and two real closures")
        report["status"] = "PASS"
        report["classification"] = "REAL_ONE_SESSION_L0_WAIT_TWO_AUTHORIZED_MOVES_QUALIFIED"
        report["stage"] = "CLOSED"
        rc = 0
    except (S31ABlocked, OSError) as exc:
        report["status"] = "BLOCKED"
        report["error"] = f"{type(exc).__name__}: {exc}"
        print("S49 BLOCKED: " + str(exc), file=sys.stderr)
        rc = 2
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        print("S49 FAIL: " + str(exc), file=sys.stderr)
        rc = 1
    finally:
        if staging is not None:
            staging.cancel()
            try:
                await staging
            except asyncio.CancelledError:
                pass
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
            report["error"] = "Java World failed clean shutdown"
            rc = 1
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("S49_REPORT=" + json.dumps(report, sort_keys=True))
    return rc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    args = parser.parse_args()
    return asyncio.run(qualify(args.report, args.server_log))


if __name__ == "__main__":
    raise SystemExit(main())
