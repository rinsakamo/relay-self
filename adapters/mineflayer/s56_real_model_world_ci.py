"""S56 opt-in actual localhost L2 inference vs physical native Minecraft L0.

Run only in a user-controlled local inference environment. Never fake a model
response, pause a synthetic HTTP server, infer loaded GGUF identity from a file
hash, or confuse host-level stale-output rejection with GPU preemption.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import socket
import urllib.parse
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
from adapters.mineflayer.s55_local_model_probe import hash_gguf
from adapters.mineflayer.s56_overlap_gate import L0ModelOverlap, OverlapDenied
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.concurrent_cognition import ConcurrentL0L2
from relay_self.execution_binding import (
    ExecutionBinding,
    resolve_execution_binding,
)
from relay_self.intent import IntentCommitment
from relay_self.interruption_fence import CognitionContext
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant
from relay_self.relay_engine import (
    CognitionDatum,
    OpenCognitionRequest,
    RelayEngine,
)
from relay_self.world_conditioned_choice import WorldChoiceKind


class S56PhysicalFailure(RuntimeError):
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
            raise S56PhysicalFailure(
                f"unexpected native host frame {type(frame).__name__}: {frame!r}"
            )
        raise S56PhysicalFailure("non-observation native frame bound exhausted")


def source(tag: str) -> Provenance:
    return Provenance("s56-independent-operator", tag)


class S56LocalBlocked(RuntimeError):
    """Genuine local inference runtime unavailable or unidentifiable."""


async def qualify(
    report_path: Path, server_log: Path, *,
    model: str, endpoint: str, gguf: Path, expected_sha256: str,
    timeout_s: float, max_tokens: int,
) -> int:
    report: dict[str, Any] = {
        "milestone": "S56", "stage": "START", "status": "BLOCKED",
        "classification": "PENDING_ACTUAL_LOCAL_MODEL_AND_NATIVE_WORLD_EVIDENCE",
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "actual_native_actions": [],
        "decisions": [],
        "provider_calls_observed": 0,
        "backend_process_and_model_identity_attested": False,
        "gpu_inference_observed": False,
        "gpu_release_measured": False,
        "backend_stop_ack": False,
        "l0_outcome_during_pending_model_call": False,
        "stale_l2_result_discarded": False,
        "fake_responder_installed": False,
        "learning_in_world": False,
        "retained_origin": "S19_FROZEN_SYNTHETIC_GOVERNED_REV1",
        "automatic_goal_selection": False,
        "auto_crash_recovery": False,
    }
    server = collector = session = staging = temp = None
    witness = L0ModelOverlap()
    model_result: dict[str, object] = {}
    owner = ConcurrentL0L2()
    rc = 2
    try:
        if os.environ.get("S56_LOCAL_REAL_MODEL") != "1":
            raise S56LocalBlocked("explicit S56_LOCAL_REAL_MODEL=1 required")
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise S56LocalBlocked("GitHub dummy HTTP cannot qualify local model")
        if os.environ.get("NODE_OPTIONS"):
            raise S56LocalBlocked("unmodified native Node required")
        if not isinstance(gguf, Path) or not expected_sha256:
            raise S56LocalBlocked("local real GGUF plus complete SHA256 required")
        file_info = hash_gguf(gguf, expected_sha256)
        report["model_file"] = file_info
        config = LoopbackInferenceConfig(
            model=model, endpoint=endpoint, timeout_s=timeout_s,
            max_tokens=max_tokens,
        )
        parsed = urllib.parse.urlsplit(config.endpoint)
        try:
            with socket.create_connection(
                (parsed.hostname, parsed.port or 80), timeout=2,
            ):
                pass
        except OSError as exc:
            raise S56LocalBlocked("local model endpoint TCP unavailable") from exc
        report["requested_model_alias"] = config.model
        report["runtime_model_file_independently_proven"] = False
        provider = RelayEngine(LoopbackChatProvider(config))
        report["stage"] = "PROVISION_DISPOSABLE_MOJANG_GAME"
        temp = tempfile.TemporaryDirectory(prefix="relay-self-s56-")
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
            raise S56PhysicalFailure("frozen governed retained source changed")
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
        # Exactly one local configured provider attempt, never a test responder.

        report["stage"] = "LOCAL_REAL_PROVIDER_READY_NATIVE_WORLD_SESSION"

        def do_actual_open_inference(native_probe):
            # Any available response remains an untrusted generated hypothesis.
            context = CognitionDatum.from_value(
                "native_observed_entity",
                {
                    "id": native_probe.snapshot.nearby_entities[0].entity_id,
                    "distance": native_probe.snapshot.nearby_entities[0].distance,
                    "source_seq": native_probe.seq,
                },
                native_probe.provenance,
            )
            question = OpenCognitionRequest(
                request_id="s56-real-model-live-concurrent-open",
                instruction=(
                    "Generate a detailed 500-word non-actionable analysis "
                    "of path-planning uncertainty. This text is not an Action "
                    "authorization. Do not issue executable commands."
                ),
                intent_id="escape-threat",
                focus="untrusted-navigation-hypothesis",
                context=(context,),
            )
            witness.model_enter()
            try:
                answer = provider.open(question)
                model_result["elapsed_ms"] = round(answer.elapsed_s * 1000, 3)
                model_result["prompt_tokens"] = answer.call_facts.prompt_tokens
                model_result["completion_tokens"] = answer.call_facts.completion_tokens
                model_result["finish_reason"] = answer.call_facts.finish_reason
                model_result["mode"] = "open"
                # Do not store or print generated text.
                return answer
            finally:
                witness.model_exit()

        async def reprobe(frame):
            request_id = f"s56-actual:{sid}:event-{frame.seq}"
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
                raise S56PhysicalFailure("WAIT attempted to request Action")
            return L0ActionGrant(
                authority_id=f"s56-preconfigured-escape-{event_seq}",
                action_id=f"s56-native-move-{event_seq}",
                intent_id="escape-threat", session_id=sid,
                event_seq=event_seq, probe_seq=choice.probe_seq,
                entity_id=choice.entity_id, granted=True,
                provenance=source(f"l0-request-{event_seq}"),
            )

        def authorize(step, stage):
            return NormalActionAuthorization(
                stage=stage, authority_id=f"s56-{stage.value.lower()}-{step.event_seq}",
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
                raise S56PhysicalFailure("actual Action without a close zombie")
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
                raise S56PhysicalFailure("full S14 native admission was not independently satisfied")
            binding = ExecutionBinding(
                binding_id=f"s56-binding-{step.event_seq}",
                candidate_ref="MOVE_AWAY", required_intent_id="escape-threat",
                skill_execution_id=f"s56-skill-{step.event_seq}",
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
                raise S56PhysicalFailure("World movement or existing S16 OUTCOME absent")
            report["actual_native_actions"].append({
                "action": receipt.terminal.action_id,
                "terminal": receipt.terminal.state.value,
                "source": receipt.consequence.session_id,
                "movement_m": receipt.consequence.movement_distance,
                "event_seq": step.event_seq,
                "probe_seq": step.choice.probe_seq,
            })

        async def on_urgent_action(step):
            if not report["l0_outcome_during_pending_model_call"]:
                probe = probes[step.choice.probe_seq]
                # One OPEN call explicitly admitted for independent tentative
                # reasoning. Text is never an Action candidate or World truth.
                ticket_context = CognitionContext(
                    sid, step.choice.probe_seq, 1, retained.revision,
                )
                owner.begin_l2(
                    "s56-actual-local-l2", ticket_context,
                    lambda: do_actual_open_inference(probe),
                )
                for _ in range(60):
                    if witness.started.is_set() or witness.finished.is_set():
                        break
                    await asyncio.sleep(0.02)
                if not witness.started.is_set() or witness.finished.is_set():
                    raise S56PhysicalFailure(
                        "a live provider call must remain pending before L0 starts"
                    )

                async def independently_authorized_physical_l0():
                    witness.l0_enter(action_id=step.action_request_id)
                    await on_action(step)
                    actual = report["actual_native_actions"][-1]
                    receipt = witness.l0_closed(
                        action_id=step.action_request_id,
                        movement_m=actual["movement_m"],
                    )
                    if not receipt.proven_overlap:
                        raise S56PhysicalFailure(
                            "physical L0 Action was not concurrent with L2"
                        )
                    report["l0_model_overlap_ms"] = round(
                        (receipt.l0_closed_ns - receipt.l0_enter_ns) / 1_000_000, 3,
                    )

                interrupted = await owner.urgent_l0(
                    ticket_context, independently_authorized_physical_l0,
                )
                if (
                    not interrupted.l0_completed
                    or interrupted.backend_stopped
                    or interrupted.gpu_released
                    or witness.finished.is_set()
                    or not report["actual_native_actions"]
                ):
                    raise S56PhysicalFailure(
                        "L2 must still be running after real L0 OUTCOME"
                    )
                report["l0_outcome_during_pending_model_call"] = True
                report["urgent_world_seq"] = step.choice.probe_seq
            else:
                await on_action(step)

        async def stage_world():
            assert server is not None and server.stdin is not None
            _command(server, "gamerule doMobSpawning false")
            await server.stdin.drain()
            await asyncio.sleep(2)
            for distance_m, hold in ((10, 4), (2, 6), (2, 6)):
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
        if not report["l0_outcome_during_pending_model_call"]:
            raise S56PhysicalFailure("no qualified L0 while model still in flight")
        last_context = CognitionContext(
            sid, trace[-1].choice.probe_seq, 1, retained.revision,
        )
        try:
            discarded = await asyncio.wait_for(
                owner.collect_l2(last_context), timeout=timeout_s + 5,
            )
        except (asyncio.TimeoutError, OSError, ValueError) as exc:
            raise S56PhysicalFailure(
                "real model did not produce an admissible terminal response"
            ) from exc
        report["stale_l2_result_discarded"] = discarded is None
        report["provider_calls_observed"] = witness.provider_attempt_count
        report["backend_stop_ack"] = False
        report["model_call"] = model_result
        report["local_call_witness"] = {
            "started": witness.started.is_set(),
            "finished": witness.finished.is_set(),
            "completed_after_l0": witness.receipt().proven_overlap,
        }
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
            or not report["l0_outcome_during_pending_model_call"]
            or not report["stale_l2_result_discarded"]
            or report["provider_calls_observed"] != 1
            or not witness.receipt().proven_overlap
            or not witness.finished.is_set()
            or model_result.get("completion_tokens") is None
            or model_result.get("prompt_tokens") is None
            or not owner.pending_backend_stop
        ):
            raise S56PhysicalFailure("not three unattended decisions and two real closures")
        report["status"] = "PASS"
        report["classification"] = (
            "NATIVE_WORLD_AND_LOCAL_MODEL_HTTP_OVERLAP_BACKEND_ID_UNVERIFIED"
        )
        report["stage"] = "CLOSED"
        rc = 0
    except (S56LocalBlocked, S31ABlocked) as exc:
        report["status"] = "BLOCKED"
        report["error"] = f"{type(exc).__name__}: {exc}"
        print("S56 BLOCKED: " + str(exc), file=sys.stderr)
        rc = 2
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        print("S56 FAIL: " + str(exc), file=sys.stderr)
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
        print("S56_REPORT=" + json.dumps(report, sort_keys=True))
    return rc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:1234/v1/chat/completions")
    parser.add_argument("--gguf", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--timeout-s", type=float, default=100.0)
    parser.add_argument("--max-tokens", type=int, default=768)
    args = parser.parse_args()
    return asyncio.run(qualify(
        args.report, args.server_log, model=args.model, endpoint=args.endpoint,
        gguf=args.gguf, expected_sha256=args.expected_sha256,
        timeout_s=args.timeout_s, max_tokens=args.max_tokens,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
