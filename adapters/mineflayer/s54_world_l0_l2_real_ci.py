"""S54: Real Minecraft L0 physical actions while an L2 HTTP call is blocked.

This is a genuinely blocked localhost HTTP responder, NOT a language model.
Native Mineflayer and actual Action OUTCOME must finish while HTTP remains
blocked; a late admissible L2 answer is subsequently discarded as stale.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.local_chat_provider import (
    LoopbackChatProvider,
    LoopbackInferenceConfig,
)
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
from relay_self.concurrent_cognition import ConcurrentL0L2
from relay_self.interruption_fence import CognitionContext
from relay_self.action_supervision import ActionSupervisor
from relay_self.execution_binding import (
    ExecutionBinding,
    resolve_execution_binding,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionMode,
    DecisionStatus,
)
from relay_self.world_conditioned_choice import WorldChoiceKind


class S54PhysicalFailure(RuntimeError):
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
        self._admitted_zombie_entities: set[int] = set()
        self.ignored_duplicate_target_updates = 0

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
                if frame.kind == "entities":
                    zombies = [
                        e for e in frame.snapshot.nearby_entities if e.name == "zombie"
                    ]
                    if len(zombies) == 1:
                        if zombies[0].entity_id in self._admitted_zombie_entities:
                            # Same target event may recur when an unrelated
                            # native item changes. It is not a new stimulus.
                            self.ignored_duplicate_target_updates += 1
                            continue
                        self._admitted_zombie_entities.add(zombies[0].entity_id)
                return frame
            if isinstance(frame, MineflayerEntityHurt):
                self.ignored_hurt_frames += 1
                continue
            raise S54PhysicalFailure(
                f"unexpected native host frame {type(frame).__name__}: {frame!r}"
            )
        raise S54PhysicalFailure("non-observation native frame bound exhausted")


def source(tag: str) -> Provenance:
    return Provenance("s54-independent-operator", tag)


async def qualify(report_path: Path, server_log: Path) -> int:
    report: dict[str, Any] = {
        "milestone": "S54", "stage": "START", "status": "BLOCKED",
        "classification": "PENDING_REAL_NATIVE_WORLD_X_HTTP_EVIDENCE",
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "actual_native_actions": [],
        "decisions": [],
        "real_model_calls": 0,
        "fake_loopback_http_calls": 0,
        "http_responder_is_real_model": False,
        "gpu_release_measured": False,
        "backend_stop_ack": False,
        "l0_completed_before_fake_http_response": False,
        "stale_l2_result_discarded": False,
        "learning_in_world": False,
        "retained_origin": "S19_FROZEN_SYNTHETIC_GOVERNED_REV1",
        "automatic_goal_selection": False,
        "auto_crash_recovery": False,
    }
    server = collector = session = staging = temp = None
    httpd = http_thread = None
    http_request_seen = threading.Event()
    http_release = threading.Event()
    http_response_sent = threading.Event()
    request_log: list[str] = []
    rc = 2
    try:
        if os.environ.get("S54_REAL_SERVER_CI") != "1" or os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("explicit S54 real server env and no Node shim required")
        report["stage"] = "PROVISION_DISPOSABLE_MOJANG_GAME"
        temp = tempfile.TemporaryDirectory(prefix="relay-self-s54-")
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
            raise S54PhysicalFailure("frozen governed retained source changed")
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
        owner = ConcurrentL0L2()
        pre_l2 = CognitionContext(
            session_id=sid, world_seq=0, intent_revision=1,
            retained_revision=retained.revision,
        )

        class BlockedFakeModel(BaseHTTPRequestHandler):
            def log_message(self, *args):
                return

            def do_POST(self):
                if self.path != "/v1/chat/completions":
                    self.send_error(404)
                    return
                n = int(self.headers.get("Content-Length", "-1"))
                if not 0 <= n <= 16384:
                    self.send_error(413)
                    return
                payload = json.loads(self.rfile.read(n))
                if (
                    payload.get("model") != "S54_FAKE_TEST_RESPONDER"
                    or payload.get("stream") is not False
                ):
                    self.send_error(400)
                    return
                request_log.append(payload["model"])
                http_request_seen.set()
                if not http_release.wait(timeout=75):
                    self.send_error(504)
                    return
                body = json.dumps({
                    "choices": [{
                        "message": {"content": "MOVE_AWAY"},
                        "finish_reason": "stop",
                    }],
                    "usage": {
                        "prompt_tokens": 9, "completion_tokens": 2,
                        "total_tokens": 11,
                    },
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                http_response_sent.set()

        httpd = ThreadingHTTPServer(("127.0.0.1", 0), BlockedFakeModel)
        http_thread = threading.Thread(
            target=httpd.serve_forever, daemon=True,
            name="s54-fake-localhost-http",
        )
        http_thread.start()
        model_transport = LoopbackChatProvider(LoopbackInferenceConfig(
            model="S54_FAKE_TEST_RESPONDER",
            endpoint=(
                f"http://127.0.0.1:{httpd.server_port}/v1/chat/completions"
            ),
            timeout_s=100, max_tokens=16,
        ))
        l2_request = BoundedChoiceRequest(
            request_id="s54-stale-possible-action", instruction="Choose one",
            intent_id="escape-threat", focus="hypothetical zombie",
            choices=(
                BoundedChoice("WAIT", "stay"),
                BoundedChoice("MOVE_AWAY", "move away"),
            ),
            context=(),
        )
        owner.begin_l2(
            "s54-blocked-l2", pre_l2,
            lambda: model_transport(l2_request, mode=CognitionMode.BOUNDED),
        )
        for _ in range(120):
            if http_request_seen.is_set():
                break
            await asyncio.sleep(0.05)
        if not http_request_seen.is_set() or http_response_sent.is_set():
            raise S54PhysicalFailure(
                "a genuinely in-flight blocked loopback HTTP request required"
            )
        report["stage"] = "BLOCKED_FAKE_HTTP_ACTIVE_REAL_WORLD_RUNTIME"

        async def reprobe(frame):
            request_id = f"s54-actual:{sid}:event-{frame.seq}"
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
                raise S54PhysicalFailure("WAIT attempted to request Action")
            return L0ActionGrant(
                authority_id=f"s54-preconfigured-escape-{event_seq}",
                action_id=f"s54-native-move-{event_seq}",
                intent_id="escape-threat", session_id=sid,
                event_seq=event_seq, probe_seq=choice.probe_seq,
                entity_id=choice.entity_id, granted=True,
                provenance=source(f"l0-request-{event_seq}"),
            )

        def authorize(step, stage):
            return NormalActionAuthorization(
                stage=stage, authority_id=f"s54-{stage.value.lower()}-{step.event_seq}",
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
                raise S54PhysicalFailure("actual Action without a close zombie")
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
                raise S54PhysicalFailure("full S14 native admission was not independently satisfied")
            binding = ExecutionBinding(
                binding_id=f"s54-binding-{step.event_seq}",
                candidate_ref="MOVE_AWAY", required_intent_id="escape-threat",
                skill_execution_id=f"s54-skill-{step.event_seq}",
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
                raise S54PhysicalFailure("World movement or existing S16 OUTCOME absent")
            report["actual_native_actions"].append({
                "action": receipt.terminal.action_id,
                "terminal": receipt.terminal.state.value,
                "source": receipt.consequence.session_id,
                "movement_m": receipt.consequence.movement_distance,
                "event_seq": step.event_seq,
                "probe_seq": step.choice.probe_seq,
            })

        async def on_urgent_action(step):
            if not report["l0_completed_before_fake_http_response"]:
                if (
                    not http_request_seen.is_set() or http_release.is_set()
                    or http_response_sent.is_set()
                ):
                    raise S54PhysicalFailure(
                        "urgent L0 did not begin during blocked L2"
                    )
                current = CognitionContext(
                    sid, step.choice.probe_seq, 1, retained.revision,
                )
                result = await owner.urgent_l0(
                    current, lambda: on_action(step),
                )
                if (
                    not result.l0_completed or result.backend_stopped
                    or result.gpu_released or http_release.is_set()
                    or http_response_sent.is_set()
                    or not report["actual_native_actions"]
                ):
                    raise S54PhysicalFailure(
                        "physical L0 must reach OUTCOME before model HTTP release"
                    )
                report["l0_completed_before_fake_http_response"] = True
                report["urgent_world_seq"] = step.choice.probe_seq
                http_release.set()
            else:
                await on_action(step)

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
                on_action_request=on_urgent_action, max_frames=320,
            ),
            timeout=95,
        )
        if not http_release.is_set() or not http_request_seen.is_set():
            raise S54PhysicalFailure("L0 never released outstanding HTTP request")
        last_context = CognitionContext(
            sid, trace[-1].choice.probe_seq, 1, retained.revision,
        )
        discarded = await asyncio.wait_for(owner.collect_l2(last_context), timeout=12)
        report["fake_loopback_http_calls"] = len(request_log)
        report["stale_l2_result_discarded"] = discarded is None
        report["http_response_sent_after_l0"] = http_response_sent.is_set()
        report["backend_stop_ack"] = not owner.pending_backend_stop
        report["ignored_hurt_frames"] = observation_source.ignored_hurt_frames
        report["ignored_non_target_entities"] = observation_source.ignored_non_target_entities
        report["ignored_duplicate_target_updates"] = observation_source.ignored_duplicate_target_updates
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
            or not report["l0_completed_before_fake_http_response"]
            or not report["stale_l2_result_discarded"]
            or not report["http_response_sent_after_l0"]
            or report["fake_loopback_http_calls"] != 1
            or not owner.pending_backend_stop
        ):
            raise S54PhysicalFailure("not three unattended decisions and two real closures")
        report["status"] = "PASS"
        report["classification"] = (
            "REAL_MINECRAFT_L0_ACTION_BEFORE_FAKE_HTTP_L2_RELEASE_QUALIFIED"
        )
        report["stage"] = "CLOSED"
        rc = 0
    except (S31ABlocked, OSError) as exc:
        report["status"] = "BLOCKED"
        report["error"] = f"{type(exc).__name__}: {exc}"
        print("S54 BLOCKED: " + str(exc), file=sys.stderr)
        rc = 2
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        print("S54 FAIL: " + str(exc), file=sys.stderr)
        rc = 1
    finally:
        http_release.set()
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
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()
        if http_thread is not None:
            http_thread.join(timeout=3)
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
        print("S54_REPORT=" + json.dumps(report, sort_keys=True))
    return rc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    args = parser.parse_args()
    return asyncio.run(qualify(args.report, args.server_log))


if __name__ == "__main__":
    raise SystemExit(main())
