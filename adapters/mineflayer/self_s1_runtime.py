"""S Lane S1: one foreground S49 World process with a bounded L0 Action owner.

No staging coroutine, synthetic zombie events, model request, or learning owner.
Only a separately opted-in operator can start the disposable RSEE World.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.normal_action import (
    NormalActionAuthorization,
    NormalActionStage,
    NormalSessionActionExecutor,
    NormalWorldL0,
)
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerEntityHurt,
    MineflayerLaunchConfig,
    MineflayerObservation,
)
from adapters.mineflayer.s31a_real_server_ci import (
    _await_spawn,
    _correlated_observe,
    _ready_server,
    _shutdown_server,
)
from adapters.mineflayer.s34_native_world_cognition_ci import (
    _native_epoch_two,
    _native_threat,
)
from adapters.mineflayer.s49_normal_session_real_ci import NativeObservationOnly, source
from adapters.mineflayer.self_continuous_host import (
    AppendOnlySessionEvents,
    BoundedSessionDriver,
    SessionBudget,
    SessionRunRejected,
)
from adapters.mineflayer.self_live_think import LiveL2Observer
from adapters.mineflayer.self_s2_candidates import (
    S2ReadOnlyCandidates,
    preconfigured_wait_repertoire,
)
from adapters.mineflayer.self_s3_experience import S3ReadOnlyExperience
from adapters.mineflayer.self_s4_observation import S4NativeObservationAudit
from adapters.mineflayer.self_s7_native_receipt import NativeStreamReceipt
from adapters.mineflayer.self_s6_intervention import (
    S6ControlledIntervention,
    S6ControlledPlan,
)
from experiments.standard_env.golden_admission import verify_qualified_world
from experiments.standard_env.node_runtime import verify_node_runtime
from experiments.standard_env.preflight import _check_tools, read_profile
from experiments.standard_env.world_binding import prepare_stopped_world
from relay_self.action_supervision import ActionSupervisor
from relay_self.execution_binding import ExecutionBinding, resolve_execution_binding
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import save_persistent_cognition
from relay_self.reactive_l0 import L0ActionGrant
from relay_self.world_conditioned_choice import WorldChoiceKind


class NaturalS49ObservationSource(NativeObservationOnly):
    """S49 source rules extended only to allow non-target native observations.

    S49's real CI filter rejects health/time/move events not used by its fixed
    three-entity trial. Normal World gameplay legitimately emits those frames.
    Preserve strict source ownership, hurt handling and zombie-ID de-duplication
    while passing all native observations to the existing L0 driver (which
    ignores non-entity kinds without inventing a safety decision).
    """

    async def receive(self):
        for _ in range(60):
            frame = await self.session.receive()
            if isinstance(frame, MineflayerObservation):
                if frame.kind == "entities":
                    zombies = [
                        e for e in frame.snapshot.nearby_entities if e.name == "zombie"
                    ]
                    if not zombies:
                        self.ignored_non_target_entities += 1
                    elif len(zombies) == 1:
                        entity_id = zombies[0].entity_id
                        if entity_id in self._admitted_zombie_entities:
                            self.ignored_duplicate_target_updates += 1
                            continue
                        self._admitted_zombie_entities.add(entity_id)
                return frame
            if isinstance(frame, MineflayerEntityHurt):
                self.ignored_hurt_frames += 1
                continue
            raise SessionRunRejected(
                f"unexpected native S49 frame: {type(frame).__name__}"
            )
        raise SessionRunRejected("S49 native frame filter exceeded bound")


RSEE = Path("/home/rinsa/.local/share/relay-self/rsee-1.0-20261011")
CONFIRM = "SELF-S1-ONE-DISPOSABLE-SESSION"
INTENT_ID = "escape-threat"


def runtime_inputs(root: Path = RSEE) -> tuple[Path, Path, Path, Path, Path]:
    """Paths to existing RSEE assets, NOT a request to create/install them."""
    world = root / "bootstrap-approved-20261011-once"
    return (
        root / "minecraft-1.21.8.jar",
        world / "snapshot",
        world / "snapshot_manifest.json",
        world / "initial_native_observation.json",
        root / "npm-mineflayer-4.39.0",
    )


def preflight(root: Path, output: Path):
    """Only local read/check operations. Never launches Java, Node or a model."""
    if root != RSEE or root.is_symlink() or not root.is_dir():
        raise SessionRunRejected("canonical physical RSEE root required")
    if (
        not output.is_absolute() or not output.is_dir()
        or output.is_symlink() or output.resolve() != output
        or output == root or root in output.parents or output in root.parents
        or any(output.iterdir())
    ):
        raise SessionRunRejected("new empty external operator output dir required")
    if (
        Path(sys.prefix).resolve() != (root / "venv").resolve()
        or Path(sys.executable).resolve() != (root / "venv/bin/python").resolve()
        or os.environ.get("NODE_OPTIONS")
        or not shutil.which("java") or not shutil.which("node")
    ):
        raise SessionRunRejected("shared RSEE interpreter, Java21 and Node22 required")
    # Reuse the existing RSEE 1.0 runtime/version/import admission.
    # Only invoked after explicit physical opt-in; never from dry-run.
    profile, _ = read_profile()
    errors = _check_tools(profile)
    if errors:
        raise SessionRunRejected("RSEE host preflight: " + "; ".join(errors))
    jar, snapshot, manifest, evidence, node_root = runtime_inputs(root)
    verify_node_runtime(node_root, Path(__file__).resolve().parent)
    return verify_qualified_world(jar, snapshot, manifest, evidence)


def s49_callbacks(
    session, host: NormalWorldL0, executor: NormalSessionActionExecutor, *,
    experience: S3ReadOnlyExperience | None = None,
    events: AppendOnlySessionEvents | None = None,
):
    """Reuse original S49 native admission and independent operator stage grants.

    Calls are serialized by BoundedSessionDriver: host.receive -> probe ->
    decision -> executor.execute. These callbacks MUST NOT be made into tasks.
    """
    if session.started.session_id != host.session_id:
        raise SessionRunRejected("foreign S49 process")
    if experience is not None and (
        not isinstance(experience, S3ReadOnlyExperience)
        or experience.session_id != host.session_id
        or not isinstance(events, AppendOnlySessionEvents)
        or events.session_id != host.session_id
    ):
        raise SessionRunRejected("source-bound read-only experience and event owner required")
    probes = {}

    async def reprobe(frame):
        request_id = f"s49-actual:{host.session_id}:event-{frame.seq}"
        reading = await _correlated_observe(session, request_id)
        probes[reading.seq] = reading
        if experience is not None:
            try:
                hint = experience.hint_for_next(reading)
            except Exception as exc:
                events.write(
                    "experience_unavailable", reason=type(exc).__name__,
                    action_authority=False, learning_updates=0, habit_grants=0,
                )
            else:
                events.write(
                    "experience_read_only_hint", status=hint.status.value,
                    memory_ids=hint.memory_ids, observed_action_refs=hint.observed_action_refs,
                    examined=hint.examined, reason=hint.reason,
                    source_seq=reading.seq, action_authority=False,
                    learning_updates=0, habit_grants=0,
                )
        return reading

    def grant(choice, event_seq):
        if choice.selection is not WorldChoiceKind.MOVE_AWAY:
            raise SessionRunRejected("WAIT cannot request S49 Action")
        return L0ActionGrant(
            authority_id=f"s49-preconfigured-escape-{event_seq}",
            action_id=f"s49-native-move-{event_seq}",
            intent_id=INTENT_ID, session_id=host.session_id,
            event_seq=event_seq, probe_seq=choice.probe_seq,
            entity_id=choice.entity_id, granted=True,
            provenance=source(f"l0-request-{event_seq}"),
        )

    def authorize(step, stage):
        return NormalActionAuthorization(
            stage=stage, authority_id=f"s49-{stage.value.lower()}-{step.event_seq}",
            intent_id=INTENT_ID, session_id=host.session_id,
            action_id=step.action_request_id, event_seq=step.event_seq,
            probe_seq=step.choice.probe_seq, entity_id=step.choice.entity_id,
            granted=True,
            provenance=source(f"independent-{stage.value.lower()}-{step.event_seq}"),
        )

    async def on_action(step):
        reading = probes.pop(step.choice.probe_seq)
        native = _native_threat(
            reading, reading.request_id, expected_entity_id=step.choice.entity_id,
        )
        if native.distance_m >= 4:
            raise SessionRunRejected("no source-qualified S49 nearby threat")
        retained = host.retained
        values, epoch = _native_epoch_two(
            ActionSupervisor(), executor.intent, retained, retained,
            expected_revision=retained.revision, native=native,
        )
        if (
            epoch.cognition_requested
            or values["plan"].selected is None
            or values["plan"].selected.candidate_id != "MOVE_AWAY"
            or values["admission"].status.value != "admitted"
        ):
            raise SessionRunRejected("S49 S14 admission not independently satisfied")
        binding = ExecutionBinding(
            binding_id=f"s49-binding-{step.event_seq}",
            candidate_ref="MOVE_AWAY", required_intent_id=INTENT_ID,
            skill_execution_id=f"s49-skill-{step.event_seq}",
            skill_ref="escape-movement", action_id=step.action_request_id,
            action_ref="MOVE_BACKWARD",
            provenance=source(f"binding-{step.event_seq}"),
        )
        bound = resolve_execution_binding(
            values["admission"], values["control"], values["route"],
            executor.intent, values["policies"][-2], binding,
            provenance=source(f"admitted-{step.event_seq}"),
        )
        # Existing S49/S16 executor is the ONLY issuer and owns UNKNOWN closure.
        receipt = await executor.execute(
            session, step, bound, reading,
            authorize(step, NormalActionStage.PROPOSE),
            authorize(step, NormalActionStage.ISSUE),
        )
        if experience is not None:
            try:
                record = experience.observe_original(
                    receipt, correlated_probe=reading,
                    expected_action_id=step.action_request_id,
                )
            except Exception as exc:
                events.write(
                    "experience_not_retained", reason=type(exc).__name__,
                    action_authority=False, learning_updates=0, habit_grants=0,
                )
            else:
                events.write(
                    "experience_retained_observation", memory_id=record.memory_id,
                    evidence_sha256=record.evidence_sha256, source_seq=record.source_seq,
                    session=record.session_id, goal_success_attested=False,
                    learning_updates=0, habit_grants=0, action_authority=False,
                )
        return receipt

    return reprobe, grant, on_action


async def run_physical(
    binding, output: Path, budget: SessionBudget, *,
    l2_observer: LiveL2Observer | None = None,
    controlled_target: S6ControlledPlan | None = None,
    capture_native_originals: bool = False,
) -> dict:
    """Exactly one owned Java + Mineflayer lifetime, natural World events only."""
    if l2_observer is not None and not isinstance(l2_observer, LiveL2Observer):
        raise SessionRunRejected("existing S60 read-only owner required")
    if controlled_target is not None and not isinstance(controlled_target, S6ControlledPlan):
        raise SessionRunRejected("S6 requires an independently authorized controlled plan")
    if type(capture_native_originals) is not bool:
        raise SessionRunRejected("S7 capture requires explicit bool")
    if controlled_target is not None and l2_observer is not None:
        raise SessionRunRejected("controlled S6 target forbids additional L2 owner")
    server = collector = session = driver = temp = receipt = None
    previous = os.environ.get("RELAYSELF_RSEE_NODE_RUNTIME_ROOT")
    root = RSEE
    result: dict = {"classification": "S1_WORLD_NOT_COMPLETED", "physical_outcome": "UNKNOWN"}
    try:
        temp = tempfile.TemporaryDirectory(prefix="relay-self-s1-")
        world_dir = Path(temp.name)
        await asyncio.to_thread(
            prepare_stopped_world, world_dir, binding, eula_accepted=True,
        )
        os.environ["RELAYSELF_RSEE_NODE_RUNTIME_ROOT"] = str(runtime_inputs(root)[4])
        if capture_native_originals:
            # Only future S7 opt-in sessions; S6's already-consumed session
            # cannot be reconstructed from derived S3/S4 JSON files.
            receipt = NativeStreamReceipt(
                output / "native_bridge_received_original.jsonl",
                output / "native_bridge_sent_original.jsonl",
            )
        server, collector, _ = await _ready_server(
            world_dir, world_dir / "minecraft.jar",
            output / "minecraft_server.log",
        )
        # Hold process ownership immediately after launch; if spawn admission
        # fails, finally still shuts down the exact child, not a replacement.
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(
                host="127.0.0.1", port=25565,
                username="RelaySelf", version="1.21.8",
            ),
            startup_timeout_s=12,
            native_receipt=receipt,
        )
        native_spawn = await _await_spawn(session)
        sid = session.started.session_id
        _, committed, _, _, _, _ = await asyncio.to_thread(s19._epoch_one)
        retained = committed.new_state
        if retained.target_id != "risk_weight" or retained.revision != 1:
            raise SessionRunRejected("S49 inherited retained identity drift")
        intent = IntentCommitment()
        intent.commit(
            INTENT_ID, objective="escape near zombie", at_ns=1,
            provenance=source("committed-existing-intent"),
        )
        host = NormalWorldL0(
            sid, INTENT_ID, retained,
            max_events=budget.max_events,
            max_action_requests=budget.max_actions,
        )
        executor = NormalSessionActionExecutor(sid, intent)
        observation_source = NaturalS49ObservationSource(session)
        sink = AppendOnlySessionEvents(output / "session_events.jsonl", sid)
        driver = BoundedSessionDriver(host, observation_source, budget, sink)
        experience = S3ReadOnlyExperience(sid)
        reprobe, grant, on_action = s49_callbacks(
            session, host, executor, experience=experience, events=sink,
        )
        candidates = S2ReadOnlyCandidates(sid, preconfigured_wait_repertoire())
        audit = S4NativeObservationAudit(sid, max_frames=budget.max_frames)
        intervention = (
            S6ControlledIntervention(controlled_target, native_spawn, sink)
            if controlled_target is not None else None
        )
        # Only S49 consumes native frames; existing S60 L2 sees validated
        # already-received probes and can never supply an Action grant.
        result = await driver.run(
            probe=reprobe, grant=grant, on_action=on_action,
            on_candidate=candidates.review,
            on_l2_probe=l2_observer.observe if l2_observer is not None else None,
            observation_audit=audit,
            on_session_started=(
                (lambda: intervention.submit_once(server))
                if intervention is not None else None
            ),
        )
        if executor.supervisor.open_actions:
            raise SessionRunRejected("S49 Action supervisor has open Action")
        memory_path = output / "s3_observed_memory.json"
        if memory_path.exists() or memory_path.is_symlink():
            raise SessionRunRejected("memory snapshot must not overwrite existing evidence")
        save_persistent_cognition(memory_path, experience.snapshot)
        result["s3_observed_memories"] = len(experience.snapshot.memories)
        result["s3_learning_updates"] = 0
        result["s3_habit_grants"] = 0
        return result
    finally:
        if driver is not None:
            driver.stop()
        if l2_observer is not None:
            # Advisory shutdown does not imply backend STOP/GPU release and
            # cannot prevent the Java/Node owner cleanup.
            sidecar = output / "s2_l2_advisory.jsonl"
            try:
                observation = await l2_observer.close()
            except BaseException as exc:
                observation = {
                    "kind": "l2_live_observer",
                    "status": "UNCONFIRMED",
                    "reason_type": type(exc).__name__,
                    "authorized_actions": 0,
                    "l2_used_as_action": False,
                    "backend_stop_ack": False,
                    "gpu_release_verified": False,
                }
            try:
                with sidecar.open("x", encoding="utf-8") as stream:
                    stream.write(json.dumps(observation, sort_keys=True) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError:
                result["l2_sidecar_unconfirmed"] = True
        try:
            if session is not None:
                try:
                    result["node_exit"] = await session.shutdown(timeout_s=10)
                except BaseException:
                    result["node_cleanup_unconfirmed"] = True
                    try:
                        result["node_exit"] = await session.terminate()
                    except BaseException as exc:
                        result["node_terminate_error_type"] = type(exc).__name__
            try:
                await _shutdown_server(server, collector)
            except BaseException as exc:
                result["server_cleanup_unconfirmed"] = type(exc).__name__
            if server is not None:
                result["server_exit"] = server.returncode
        finally:
            try:
                if temp is not None:
                    temp.cleanup()
            finally:
                try:
                    if receipt is not None:
                        details = receipt.close()
                        report = output / "native_bridge_source_receipt.json"
                        with report.open("x", encoding="utf-8") as file:
                            file.write(json.dumps(details, sort_keys=True) + "\n")
                            file.flush()
                            os.fsync(file.fileno())
                    cleanup_file = output / "owned_cleanup.json"
                    if cleanup_file.exists() or cleanup_file.is_symlink():
                        raise SessionRunRejected("cleanup receipt would overwrite evidence")
                    cleanup_file.write_text(json.dumps({
                        "schema": "SELF1_S1_OWNER_CLEANUP_V1",
                        "session": session.started.session_id if session is not None else None,
                        "node_exit": result.get("node_exit"),
                        "server_exit": result.get("server_exit"),
                        "node_cleanup_unconfirmed": result.get("node_cleanup_unconfirmed", False),
                        "node_terminate_error_type": result.get("node_terminate_error_type"),
                        "server_cleanup_unconfirmed": result.get("server_cleanup_unconfirmed"),
                        "native_stop_ack": False,
                        "model_stop_ack": False,
                        "gpu_release_claimed": False,
                        "physical_action_replay": False,
                    }, sort_keys=True) + "\n", encoding="utf-8")
                finally:
                    if previous is None:
                        os.environ.pop("RELAYSELF_RSEE_NODE_RUNTIME_ROOT", None)
                    else:
                        os.environ["RELAYSELF_RSEE_NODE_RUNTIME_ROOT"] = previous


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Self S1: offline dry-run by default")
    parser.add_argument("--run-disposable", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--standing-eula-confirmed", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--max-events", type=int, default=12)
    parser.add_argument("--max-actions", type=int, default=3)
    parser.add_argument("--max-frames", type=int, default=500)
    parser.add_argument("--max-seconds", type=float, default=180)
    args = parser.parse_args(argv)
    if not args.run_disposable:
        print(json.dumps({
            "classification": "S1_DRY_RUN_NO_EFFECTS",
            "world": "NOT_STARTED", "action": "NOT_ISSUED",
            "model_calls": 0, "new_physical_permission": False,
        }, sort_keys=True))
        return 0
    if args.confirm != CONFIRM or not args.standing_eula_confirmed:
        print('{"classification":"S1_OPERATOR_AUTHORITY_MISSING"}')
        return 2
    if args.output_dir is None:
        print('{"classification":"S1_OUTPUT_DIR_MISSING"}')
        return 2
    try:
        budget = SessionBudget(
            max_events=args.max_events, max_actions=args.max_actions,
            max_frames=args.max_frames, max_seconds=args.max_seconds,
        )
        binding = preflight(RSEE, args.output_dir)
        result = asyncio.run(run_physical(binding, args.output_dir, budget))
        if (
            result.get("node_exit") != 0 or result.get("server_exit") != 0
            or result.get("node_cleanup_unconfirmed")
            or result.get("server_cleanup_unconfirmed")
            or result.get("l2_sidecar_unconfirmed")
        ):
            raise SessionRunRejected("owned physical processes not cleanly closed")
    except (Exception, KeyboardInterrupt) as exc:
        print(json.dumps({
            "classification": "S1_UNKNOWN_OR_BLOCKED",
            "reason": type(exc).__name__, "safe_to_replay": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
