"""Opt-in SelfBody DEV host derived from pinned L23 owner 2afb7250.

Requires exactly the existing L23 single Action; no Stage-R observer.

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
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.l16_first_action_goal_originals import (
    L16GoalPlan,
    inspect_l16_first_action_prefix,
)
from adapters.mineflayer.l18_s16_terminal_original import (
    S16_FILE,
    write_s16_owner_original,
)
from adapters.mineflayer.l21_goal_observer_source import (
    ORIGINAL_NAME as L21_ORIGINAL_NAME,
)
from adapters.mineflayer.l21_goal_observer_source import (
    L21ObserverRejected,
    L21ObserverSession,
    review_l21_observer_original,
)
from adapters.mineflayer.l22_post_s16_settling import inspect_l22_settling
from adapters.mineflayer.l22_runtime_settling import observe_bounded_settling
from adapters.mineflayer.l23_paper_live_assets import (
    L23PaperAssets,
    L23PaperBlocked,
    paper_marker,
    stage_paper_assets,
    verify_paper_assets,
    wait_paper_line,
)
from adapters.mineflayer.l23_paper_s7_settling import (
    _paper_rows,
    inspect_l23_paper_s7,
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
from adapters.mineflayer.self_action_evidence import capture_native_action_evidence
from adapters.mineflayer.self_body_s50_motion_companion import SelfBodyS50MotionCompanion
from adapters.mineflayer.self_body_s50_original_closure import (
    SelfBodyS50ClosedOwnerLease,
    observe_original_s49_selfbody_closure,
)
from adapters.mineflayer.self_body_s50_postworld_epoch import PostWorldInternalEpochLease
from adapters.mineflayer.self_s7_native_receipt import NativeStreamReceipt
from experiments.standard_env.world_binding import (
    WorldBinding,
    WorldBindingRejected,
    prepare_stopped_world,
)
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.execution_binding import (
    ExecutionBinding,
    resolve_execution_binding,
)
from relay_self.intent import IntentCommitment
from relay_self.l20_external_goal_commitment import (
    L20GoalCommitmentRejected,
    review_external_pre_world_criterion,
)
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant
from relay_self.world_conditioned_choice import WorldChoiceKind
from tools.s50_selfbody_motion_readback import review_originals


def normalize_s50_diagnostic(source: dict[str, object]) -> dict[str, object]:
    """Use the existing S50 CLI JSON shape; typed SelfBody never enters here."""
    return json.loads(json.dumps(source, allow_nan=False))


def review_postworld_internal_epoch(
    joined: SelfBodyS50MotionCompanion, *, node_exit: int,
    server_exit: int, cleanup_errors: bool = False,
) -> dict[str, object]:
    """Original host's opt-in post-process boundary; NO new native epoch.

    This function is a pure in-process projection after real shutdown has
    already been observed by S49. Synthetic owner fixture calls test only the
    consumer contract, not the original physical World itself.
    """
    epoch = PostWorldInternalEpochLease(joined)
    try:
        readout = epoch.enter_after_owner_shutdown(
            node_exit=node_exit, java_exit=server_exit,
            cleanup_errors=cleanup_errors,
        )
        return {
            "classification": "DEV_POSTWORLD_INTERNAL_EPOCH_PRIOR_EXPERIENCE_READ_PASS",
            "readback": readout,
            "source_lease": epoch.status(),
            "actual_new_native_present": False,
            "actual_new_l0_decision": False,
        }
    finally:
        epoch.close()


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
            raise S49PhysicalFailure(
                f"unexpected native host frame {type(frame).__name__}: {frame!r}"
            )
        raise S49PhysicalFailure("non-observation native frame bound exhausted")


def source(tag: str) -> Provenance:
    return Provenance("s49-independent-operator", tag)


async def qualify(
    report_path: Path, server_log: Path, *,
    live_probe: Callable[[MineflayerObservation], Awaitable[None]] | None = None,
    rsee_world: WorldBinding | None = None,
    rsee_eula_accepted: bool = False,
    l16_capture_root: Path | None = None,
    l16_goal_plan: L16GoalPlan | None = None,
    l20_external_goal_original: Path | None = None,
    l20_admitted_sha256: str | None = None,
    l21_observer_root: Path | None = None,
    l22_settling_probes: int | None = None,
    l23_paper_assets: L23PaperAssets | None = None,
    postworld_internal_epoch_dev: bool = False,
) -> int:
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
    l21_observer: L21ObserverSession | None = None
    l21_closed = False
    recorder: NativeStreamReceipt | None = None
    capture_sealed = False
    l23_session_id: str | None = None
    l23_action_id: str | None = None
    l23_marker_id: str | None = None
    lease = None
    original_closure = None
    original_body = None
    rc = 2
    try:
        if type(postworld_internal_epoch_dev) is not bool:
            raise S31ABlocked("post-world cognitive opt-in must be boolean")
        if (l23_paper_assets is None or l22_settling_probes is None
                or l21_observer_root is not None
                or not os.environ.get("RELAYSELF_S50_PACKET_WITNESS_DEV")):
            raise S31ABlocked("SelfBody host requires single-Action L23 and S50; no second client")
        if os.environ.get("S49_REAL_SERVER_CI") != "1" or os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("explicit S49 real server env and no Node shim required")
        if (l16_capture_root is None) != (l16_goal_plan is None):
            raise S31ABlocked("L16 capture root and pre-World Goal must be paired")
        if (l20_external_goal_original is None) != (l20_admitted_sha256 is None):
            raise S31ABlocked("L20 external criterion and admitted SHA must be paired")
        if l22_settling_probes is not None and (
            type(l22_settling_probes) is not int
            or not 3 <= l22_settling_probes <= 8
            or l16_capture_root is None
            or not isinstance(l16_goal_plan, L16GoalPlan)
        ):
            raise S31ABlocked(
                "L22 opt-in requires bounded 3..8 probes and paired L16 originals"
            )
        if l23_paper_assets is not None:
            if (l22_settling_probes is None
                    or l16_goal_plan is None or l16_capture_root is None):
                raise S31ABlocked(
                    "L23 Paper requires explicit L22 settling and sealed L16 originals"
                )
            report["l23_paper"] = {
                "status": "PREFLIGHT_ONLY",
                **verify_paper_assets(l23_paper_assets),
                "effective_s15_clear_world_tick": "NOT_ATTESTED",
                "l10_pairs": 0,
            }
        if l21_observer_root is not None:
            if (
                l20_external_goal_original is None
                or l20_admitted_sha256 is None
                or not isinstance(l16_goal_plan, L16GoalPlan)
                or not isinstance(l21_observer_root, Path)
                or not l21_observer_root.is_absolute()
                or not l21_observer_root.is_dir()
                or l21_observer_root.is_symlink()
                or l21_observer_root.resolve(strict=True) != l21_observer_root
                or l16_capture_root is None
                or l21_observer_root == l16_capture_root
                or l21_observer_root.is_relative_to(l16_capture_root)
                or l16_capture_root.is_relative_to(l21_observer_root)
                or (l21_observer_root / L21_ORIGINAL_NAME).exists()
            ):
                raise S31ABlocked(
                    "L21 requires separate fresh observer directory and paired L20 source"
                )
        if l20_external_goal_original is not None:
            # Fail before Java, Node or a new S7 recorder is launched.
            if (
                not isinstance(l16_goal_plan, L16GoalPlan)
                or not isinstance(l16_capture_root, Path)
                or not isinstance(l20_external_goal_original, Path)
                or not l20_external_goal_original.is_absolute()
                or l20_external_goal_original.is_symlink()
                or not l20_external_goal_original.is_file()
                or l20_external_goal_original.resolve(strict=True)
                != l20_external_goal_original
                or l20_external_goal_original.is_relative_to(l16_capture_root)
                or not 0 < l20_external_goal_original.stat().st_size <= 4096
            ):
                raise S31ABlocked(
                    "L20 requires a bounded external reviewer original outside S49"
                )
            l20_preflight = review_external_pre_world_criterion(
                original=l20_external_goal_original.read_bytes(),
                admitted_sha256=l20_admitted_sha256,
                operator_plan=l16_goal_plan,
            )
            report["l20_external_goal_preflight"] = asdict(l20_preflight)
            report["l20_external_goal_preflight_status"] = (
                "SOURCE_MATCH_BEFORE_WORLD_UNQUALIFIED"
            )
        if l16_capture_root is not None:
            if (not isinstance(l16_goal_plan, L16GoalPlan)
                    or not isinstance(l16_capture_root, Path)
                    or not l16_capture_root.is_absolute()):
                raise S31ABlocked("L16 requires explicit absolute capture root and fixed Goal")
            # Write the operator's fixed target BEFORE Java/World/session starts.
            # This is an operator-local claim, not external Goal qualification.
            plan_file = l16_capture_root / "l16_pre_world_goal_plan.json"
            original_plan = l16_goal_plan.original_bytes()
            with plan_file.open("xb") as out:
                out.write(original_plan)
                out.flush()
                os.fsync(out.fileno())
            recorder = NativeStreamReceipt(
                l16_capture_root / "native_bridge_received_original.jsonl",
                l16_capture_root / "native_bridge_sent_original.jsonl",
            )
            report["l16_capture"] = {
                "status": "STARTED_PRE_WORLD",
                "root": str(l16_capture_root),
                "goal_owner_independent": False,
                "real_l10_pairs": 0,
            }
        report["stage"] = "PROVISION_DISPOSABLE_MOJANG_GAME"
        temp = tempfile.TemporaryDirectory(prefix="relay-self-s49-")
        root = Path(temp.name)
        if l23_paper_assets is not None:
            if rsee_world is not None:
                raise S31ABlocked("L23 Paper cannot consume shared/stopped RSEE World")
            report["stage"] = "PROVISION_L23_DISPOSABLE_PAPER"
            report["l23_paper"]["assets_staged"] = stage_paper_assets(
                l23_paper_assets, root,
            )
            _write_config(root)
        elif rsee_world is not None:
            report["stage"] = "RSEE_BIND_STOPPED_WORLD_BEFORE_JAVA"
            report["rsee_world_binding"] = await asyncio.to_thread(
                prepare_stopped_world, root, rsee_world,
                eula_accepted=rsee_eula_accepted,
            )
        else:
            # Original standalone S49 mode is unchanged, not an RSEE run.
            report.update(await asyncio.to_thread(
                _fetch_official_server, root / "minecraft.jar",
            ))
            _write_config(root)
        server, collector, _ = await _ready_server(
            root, root / "minecraft.jar", server_log,
        )
        report["stage"] = "AUTHENTIC_NATIVE_SELF_SESSION"
        if l21_observer_root is not None:
            assert l20_external_goal_original is not None
            assert l20_admitted_sha256 is not None
            l21_observer = await L21ObserverSession.launch(
                source_path=l21_observer_root / L21_ORIGINAL_NAME,
                criterion_path=l20_external_goal_original,
                criterion_sha256=l20_admitted_sha256,
            )
            report["l21_observer"] = {
                "status": "SEPARATE_TCP_CLIENT_READY_NOT_PHYSICALLY_AUTHENTICATED",
                "root": str(l21_observer_root),
                "qualified_real_learning_pairs": 0,
            }
        session = await _new_session(native_receipt=recorder)
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
            sid, "escape-threat", retained,
            max_events=2 if l22_settling_probes is not None else 3,
            max_action_requests=1 if l22_settling_probes is not None else 2,
        )
        executor = NormalSessionActionExecutor(sid, intent)
        probes = {}

        async def reprobe(frame):
            request_id = f"s49-actual:{sid}:event-{frame.seq}"
            reading = await _correlated_observe(session, request_id)
            probes[reading.seq] = reading
            if live_probe is not None:
                # Product-only observer sees an already received native probe.
                # Original S49 L0 selection, Action ownership and receipt
                # collection run exactly as before and never await L2 inference.
                await live_probe(reading)
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
            first_terminal_source: dict[str, object] = {}

            def on_first_s16_terminal(terminal, interpretation, consequence):
                if recorder is not None and not capture_sealed:
                    assert l16_capture_root is not None
                    first_terminal_source.update(write_s16_owner_original(
                        capture_root=l16_capture_root, terminal=terminal,
                        outcome=interpretation, consequence=consequence,
                        # Operator-declared revision; later SelfWorld/Body
                        # must independently match it before any L10 join.
                        source_revision=0,
                    ))
                    report["l18_first_terminal_source"] = dict(first_terminal_source)

            if l23_paper_assets is not None:
                assert server is not None and server.stdin is not None
                nonlocal l23_marker_id, l23_session_id, l23_action_id
                l23_session_id, l23_action_id = sid, step.action_request_id
                l23_marker_id = paper_marker(l23_action_id, sid)
                _command(
                    server, f"relaydevphase {l23_marker_id} PRE_FORWARD",
                )
                await server.stdin.drain()
                await wait_paper_line(
                    server_log, marker=l23_marker_id,
                    kind="M02_DEV_S50_PHASE", phase="PRE_FORWARD",
                )
                report["l23_paper"]["marker_id"] = l23_marker_id
                report["l23_paper"]["status"] = "PRE_ACTION_PAPER_MARKER_OBSERVED"
            nonlocal lease, original_closure, original_body

            class OriginalLease(SelfBodyS50ClosedOwnerLease):
                def observe_original_closed(self, original):
                    nonlocal original_closure, original_body
                    super().observe_original_closed(original)
                    original_closure = original
                    original_body = self._body
                    on_first_s16_terminal(
                        original.terminal, original.interpretation, original.consequence,
                    )

            if lease is not None:
                raise S49PhysicalFailure("single-Action SelfBody lease already allocated")
            lease = OriginalLease(self_id="self", expected_action_id=step.action_request_id)
            with observe_original_s49_selfbody_closure(lease):
                receipt = await executor.execute(
                    session, step, bound, probe,
                    authorize(step, NormalActionStage.PROPOSE),
                    authorize(step, NormalActionStage.ISSUE),
                    correlate_native_probes_dev=True,
                )
            report["selfbody_original_lease"] = lease.status()

            if (
                receipt.terminal.state is not ActionState.OUTCOME
                or receipt.consequence.status is not WorldConsequenceStatus.EXECUTED
                or receipt.consequence.movement_distance is None
                or receipt.consequence.movement_distance < 0.05
            ):
                raise S49PhysicalFailure("World movement or existing S16 OUTCOME absent")
            if l23_paper_assets is not None:
                assert server is not None and server.stdin is not None
                assert l23_marker_id is not None
                # Observed after S16 terminal and actual S15 clear ACK,
                # but command acceptance is NOT effective clear tick.
                _command(server, f"relaydevphase {l23_marker_id} POST_CLEAR")
                await server.stdin.drain()
                await wait_paper_line(
                    server_log, marker=l23_marker_id,
                    kind="M02_DEV_S50_PHASE", phase="POST_CLEAR",
                )
                _command(server, f"relaydevwait {l23_marker_id}")
                await server.stdin.drain()
                await wait_paper_line(
                    server_log, marker=l23_marker_id,
                    kind="S50_DEV_WAIT_BEGIN",
                )
                report["l23_paper"]["status"] = "PAPER_WAIT_STARTED_SOURCE_ONLY"
            report["actual_native_actions"].append({
                "action": receipt.terminal.action_id,
                "terminal": receipt.terminal.state.value,
                "source": receipt.consequence.session_id,
                "movement_m": receipt.consequence.movement_distance,
                "event_seq": step.event_seq,
                "probe_seq": step.choice.probe_seq,
                # Decoded original before/after observations and exact effect
                # receipts, captured BEFORE the immutable consequence is lost.
                # Legacy reports have no such field and remain EVIDENCE_PARTIAL.
                "execution_evidence": capture_native_action_evidence(
                    receipt.consequence
                ),
            })
            if not lease.status()["typed_original_ready"]:
                raise S49PhysicalFailure("original typed SelfBody closure rejected")
            nonlocal capture_sealed, l21_closed
            if recorder is not None and not capture_sealed:
                assert l16_goal_plan is not None and l16_capture_root is not None
                action_id = receipt.terminal.action_id
                first_id = f"l16:{sid}:{action_id}:goal-1"
                second_id = f"l16:{sid}:{action_id}:goal-2"
                # Existing S16 OUTCOME/control clear precedes every L22
                # sample. Its diagnostic observations use the SAME S7 reader.
                l22_runtime = None
                if l22_settling_probes is not None:
                    l22_runtime = await observe_bounded_settling(
                        session, session_id=sid, action_id=action_id,
                        max_probes=l22_settling_probes,
                        initial_observation=receipt.consequence.after_observation,
                        drift_limit_m=l16_goal_plan.stable_probe_delta_max_m,
                    )
                    report["l22_settling"] = {
                        "status": "RUNTIME_SAMPLES_UNQUALIFIED",
                        "runtime": asdict(l22_runtime),
                        "accepted_goal_status": "UNDETERMINED",
                        "qualified_real_learning_pairs": 0,
                    }
                # Both Goal probes follow the optional bounded settling
                # window. No alternate native reader or Action issuer.
                # The optional second TCP client samples the RelaySelf
                # player separately; S49 does not write observer coordinates
                # or the Goal status into its original file.
                if l21_observer is not None:
                    await l21_observer.sample(first_id)
                first = await _correlated_observe(session, first_id)
                if l21_observer is not None:
                    await l21_observer.sample(second_id)
                second = await _correlated_observe(session, second_id)
                # Seal the independent source before the stricter L16 audit.
                # Its failure must not destroy already observed positions.
                observer_original = None
                if l21_observer is not None:
                    observer_original = await l21_observer.close()
                    l21_closed = True
                    report["l21_observer"]["status"] = "SEALED_PENDING_L16_REVIEW"
                index = session.finish_native_receipt()
                capture_sealed = True
                index_file = l16_capture_root / "native_bridge_source_receipt.json"
                with index_file.open("xb") as out:
                    out.write((json.dumps(index, sort_keys=True) + "\n").encode())
                    out.flush()
                    os.fsync(out.fileno())
                window = None
                if l22_settling_probes is not None:
                    assert l22_runtime is not None
                    l22_review = inspect_l22_settling(
                        received_original=recorder.received.read_bytes(),
                        sent_original=recorder.sent.read_bytes(),
                        s7_receipt=index,
                        s16_original=(
                            l16_capture_root / S16_FILE
                        ).read_bytes(),
                        plan=l16_goal_plan, action_id=action_id, session_id=sid,
                    )
                    if (
                        l22_review.settling_probe_seqs
                        != l22_runtime.observed_probe_seqs
                        or not set(l22_runtime.observed_move_seqs).issubset(
                            l22_review.move_event_seqs
                        )
                    ):
                        raise S49PhysicalFailure(
                            "L22 runtime and source original settling disagree"
                        )
                    report["l22_settling"] = {
                        "status": "S7_SOURCE_REVIEWED_GOAL_UNDETERMINED",
                        "runtime": asdict(l22_runtime),
                        "audit": asdict(l22_review),
                        "qualified_real_learning_pairs": 0,
                        "s10_updates": 0,
                        "s11_grants": 0,
                    }
                else:
                    window = inspect_l16_first_action_prefix(
                        received_original=recorder.received.read_bytes(),
                        sent_original=recorder.sent.read_bytes(),
                        s7_receipt=index,
                        plan=l16_goal_plan,
                        plan_original=(
                            l16_capture_root / "l16_pre_world_goal_plan.json"
                        ).read_bytes(),
                        action_id=action_id, session_id=sid,
                        before_seq=receipt.consequence.before_observation.seq,
                        dispatch_seq=receipt.consequence.dispatch_receipt.seq,
                        cleanup_seq=receipt.consequence.cleanup_receipt.seq,
                        after_seq=receipt.consequence.after_observation.seq,
                        first_probe_seq=first.seq, second_probe_seq=second.seq,
                        first_probe_request_id=first_id,
                        second_probe_request_id=second_id,
                    )
                if l21_observer is not None:
                    assert observer_original is not None
                    assert l20_external_goal_original is not None
                    assert l20_admitted_sha256 is not None
                    review = review_l21_observer_original(
                        raw=observer_original,
                        criterion_original=l20_external_goal_original.read_bytes(),
                        criterion_sha256=l20_admitted_sha256,
                        plan=l16_goal_plan,
                        session_id=sid, action_id=action_id,
                        native_goal_status=(
                            window.observed_goal_status
                            if window is not None else "UNDETERMINED"
                        ),
                    )
                    report["l21_observer"] = {
                        "status": "SECOND_CLIENT_SOURCE_ONLY_UNQUALIFIED",
                        "root": str(l21_observer_root),
                        "source_file": str(l21_observer.source_path),
                        "review": asdict(review),
                        "qualified_real_learning_pairs": 0,
                        "observer_presence_is_world_intervention": True,
                    }
                report["l16_capture"] = {
                    "status": (
                        "SOURCE_PREFIX_CAPTURED_UNQUALIFIED"
                        if window is not None
                        else "L16_NOT_RUN_L22_EXTRA_PROBES"
                    ),
                    "root": str(l16_capture_root),
                    "s7_index": index,
                    "window": asdict(window) if window is not None else None,
                    "l18_s16_owner_source": first_terminal_source,
                    "first_action_only": True,
                    "later_session_actions_not_in_recorded_prefix": True,
                    "real_l10_pairs": 0,
                    "external_goal_owner_independent": False,
                }

        async def stage_world():
            assert server is not None and server.stdin is not None
            _command(server, "gamerule doMobSpawning false")
            await server.stdin.drain()
            await asyncio.sleep(2)
            stages = ((10, 5), (2, 8)) if l22_settling_probes is not None else (
                (10, 5), (2, 8), (2, 8),
            )
            for distance_m, hold in stages:
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
        report["ignored_duplicate_target_updates"] = observation_source.ignored_duplicate_target_updates
        report["decisions"] = [{
            "event_seq": s.event_seq,
            "entity_id": s.choice.entity_id,
            "probe_seq": s.choice.probe_seq,
            "distance_m": s.choice.distance_m,
            "selected": s.choice.selection.value,
            "issued": s.asks_for_action,
        } for s in trace]
        expected_moves = 1 if l22_settling_probes is not None else 2
        if (
            len(trace) != expected_moves + 1
            or [s.choice.selection.value for s in trace]
            != ["WAIT"] + ["MOVE_AWAY"] * expected_moves
            or len({s.choice.entity_id for s in trace}) != expected_moves + 1
            or len(report["actual_native_actions"]) != expected_moves
            or executor.supervisor.open_actions
            or any(executor.supervisor.get(s.action_request_id).state
                   is not ActionState.OUTCOME for s in trace[1:])
            or trace[0].asks_for_action
            or host.action_requests != expected_moves
            or host.events != expected_moves + 1
        ):
            raise S49PhysicalFailure("bounded native decisions/Action closures disagree")
        if l23_paper_assets is not None:
            assert l23_marker_id is not None
            # L22 may finish after only three quiet probes. Keep the existing
            # session alive until Paper emits its eighth callback; otherwise
            # disconnect can truncate the source. Final audit still validates
            # all eight rows, their order and consecutive World ticks.
            await wait_paper_line(
                server_log, marker=l23_marker_id, kind="S50_DEV_WAIT_TICK",
            )
        report["status"] = "PASS"
        report["classification"] = (
            "DEV_ONLY_REAL_WORLD_L22_SOURCE_REVIEWED_GOAL_UNDETERMINED"
            if l22_settling_probes is not None
            else "REAL_ONE_SESSION_L0_WAIT_TWO_AUTHORIZED_MOVES_QUALIFIED"
        )
        report["stage"] = "CLOSED"
        rc = 0
    except (
        S31ABlocked, WorldBindingRejected, L20GoalCommitmentRejected,
        L21ObserverRejected, L23PaperBlocked, OSError,
    ) as exc:
        # Invalid asset preflight is BLOCKED; a missing Paper marker after a
        # server has launched is a *real run failure*, never a pre-World block.
        report["status"] = (
            "FAIL" if isinstance(exc, L23PaperBlocked) and server is not None
            else "BLOCKED"
        )
        report["error"] = f"{type(exc).__name__}: {exc}"
        print("S49 BLOCKED: " + str(exc), file=sys.stderr)
        rc = 2
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        print("S49 FAIL: " + str(exc), file=sys.stderr)
        rc = 1
    finally:
        if l21_observer is not None and not l21_closed:
            try:
                await l21_observer.terminate()
            except Exception as exc:
                report["l21_observer_cleanup_error"] = (
                    f"{type(exc).__name__}: {exc}"
                )
            report["l21_observer_status"] = "INCOMPLETE_SEPARATE_CLIENT_SOURCE"
        if staging is not None:
            staging.cancel()
            try:
                await staging
            except asyncio.CancelledError:
                pass
        if recorder is not None and not capture_sealed:
            try:
                index = (session.finish_native_receipt()
                         if session is not None else recorder.close())
                capture_sealed = True
                assert l16_capture_root is not None
                with (l16_capture_root / "native_bridge_source_receipt.json").open("xb") as out:
                    out.write((json.dumps(index, sort_keys=True) + "\n").encode())
                    out.flush()
                    os.fsync(out.fileno())
                report["l16_capture"] = {
                    "status": "INCOMPLETE_NO_GOAL_LABEL",
                    "s7_index": index,
                    "real_l10_pairs": 0,
                }
            except Exception as exc:
                report["l16_capture_error"] = f"{type(exc).__name__}: {exc}"
                report["status"] = "FAIL"
                rc = 1
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
        if (
            l23_paper_assets is not None
            and l23_session_id is not None
            and l23_action_id is not None
            and l23_marker_id is not None
            and capture_sealed
            and l16_capture_root is not None
        ):
            try:
                raw = server_log.read_bytes()  # complete stdout after Java exit
                starts = _paper_rows(raw, "S50_DEV_WAIT_BEGIN ")
                if (
                    len(starts) != 1
                    or starts[0].get("marker_id") != l23_marker_id
                    or not starts[0].get("world")
                ):
                    raise S49PhysicalFailure("L23 source has no bound Paper World")
                index = json.loads((
                    l16_capture_root / "native_bridge_source_receipt.json"
                ).read_bytes())
                audit = inspect_l23_paper_s7(
                    received_original=(
                        l16_capture_root / "native_bridge_received_original.jsonl"
                    ).read_bytes(),
                    sent_original=(
                        l16_capture_root / "native_bridge_sent_original.jsonl"
                    ).read_bytes(),
                    s7_receipt=index,
                    s16_original=(l16_capture_root / S16_FILE).read_bytes(),
                    plan=l16_goal_plan, action_id=l23_action_id,
                    session_id=l23_session_id, paper_original=raw,
                    expected_world=starts[0]["world"],
                )
                report["l23_paper"]["status"] = "PAPER_SOURCE_SHAPE_REVIEWED_ONLY"
                report["l23_paper"]["readback"] = asdict(audit)
                report["l23_paper"]["server_console_source"] = str(server_log)
            except Exception as exc:
                report["l23_paper"]["status"] = "PAPER_SOURCE_REJECTED"
                report["l23_paper"]["readback_error"] = (
                    f"{type(exc).__name__}: {exc}"
                )
                report["status"] = "FAIL"
                rc = 1
        try:
            if (rc == 0 and report.get("status") == "PASS"
                    and report.get("node_exit") == 0 and report.get("server_exit") == 0):
                assert lease is not None and original_closure is not None
                assert original_body is not None
                paper = server_log.read_bytes()
                inputs = _paper_rows(paper, "S50_DEV_INPUT_TICK ")
                subject_uuid = inputs[0]["subject_uuid"]
                s50_source = review_originals(
                    report_original=json.dumps(report).encode(), paper_original=paper,
                    client_original=Path(os.environ[
                        "RELAYSELF_S50_PACKET_WITNESS_DEV"
                    ]).read_bytes(), subject_uuid=subject_uuid,
                )
                # S50 CLI JSON representation only; never serialize typed S16/Present.
                s50_source = normalize_s50_diagnostic(s50_source)
                (report_path.parent / "selfbody-s50-producer.json").write_text(
                    json.dumps(s50_source, indent=2) + "\n",
                )
                joined = lease.consume_s50_once(s50_source["physical_body_diagnostic"])
                c, o = original_closure.consequence, original_closure.interpretation
                obs = joined.self_body.observation
                assert joined.self_body is original_body
                assert joined.self_body.outcome is o
                assert obs.session_id == c.after_observation.session_id
                assert obs.native_seq == c.after_observation.seq
                assert obs.request_id == c.after_observation.request_id
                assert obs.source_provenance == c.after_observation.provenance
                assert obs.consequence_provenance == c.provenance == o.world_provenance
                assert all(joined.sampled_at(t.world_tick) is t for t in joined.ticks)
                report["selfbody_s50_join"] = {
                    "classification": "DEV_WORLD_SELFBODY_S16_S50_JOIN_PASS",
                    "in_process_original_identity_checks": True,
                    "same_selfbody_view_identity": True,
                    "same_s16_identity": True,
                    "original_consequence_type": type(c).__name__,
                    "original_outcome_type": type(o).__name__,
                    "observation": asdict(obs),
                    "outcome": asdict(o),
                    "original_probe_seq": original_closure.original_probe.seq,
                    "before_seq": c.before_observation.seq,
                    "after_seq": c.after_observation.seq,
                    "source": s50_source,
                    "companion": asdict(joined),
                    "cognitive_summary": joined.cognitive_summary(),
                    "next_cognitive_epoch_referenced": False,
                    "next_epoch_handoff": "READ_ONLY_COMPANION_AVAILABLE_NO_EPOCH_EXECUTED",
                }
                (report_path.parent / "selfbody-s50-producer.json").write_text(
                    json.dumps(s50_source, indent=2) + "\n",
                )
                if postworld_internal_epoch_dev:
                    # An explicitly new INTERNAL cognition epoch, only after
                    # original Node/Java exit. No fresh native Present or L0.
                    report["selfbody_postworld_internal_epoch"] = (
                        review_postworld_internal_epoch(
                            joined, node_exit=report["node_exit"],
                            server_exit=report["server_exit"],
                            cleanup_errors=bool(
                                report.get("node_cleanup_error")
                                or report.get("server_cleanup_error")
                            ),
                        )
                    )
                    report["selfbody_s50_join"]["next_cognitive_epoch_referenced"] = True
                    report["selfbody_s50_join"]["next_epoch_handoff"] = (
                        "POST_SHUTDOWN_INTERNAL_EPOCH_PRIOR_EXPERIENCE_ONLY"
                    )
        except Exception as exc:
            report["selfbody_join_error"] = f"{type(exc).__name__}: {exc}"
            report["status"] = "FAIL"
            rc = 1
        finally:
            if lease is not None:
                lease.close()
                report["selfbody_lease_final"] = lease.status()
            original_closure = original_body = None
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
    parser.add_argument("--l16-capture-root", type=Path)
    parser.add_argument("--l16-goal-target-x", type=float)
    parser.add_argument("--l16-goal-target-z", type=float)
    parser.add_argument("--l16-goal-tolerance-m", type=float, default=0.49)
    parser.add_argument("--l16-goal-stability-m", type=float, default=0.05)
    parser.add_argument("--l16-confirm", default="")
    parser.add_argument("--l20-external-goal-original", type=Path)
    parser.add_argument("--l20-admitted-sha256")
    parser.add_argument("--l21-observer-root", type=Path)
    parser.add_argument("--l22-settling-probes", type=int)
    parser.add_argument("--l23-paper-server-jar", type=Path)
    parser.add_argument("--l23-paper-server-sha256")
    parser.add_argument("--l23-paper-plugin-jar", type=Path)
    parser.add_argument("--l23-paper-plugin-sha256")
    parser.add_argument("--l23-paper-config", type=Path)
    parser.add_argument("--l23-paper-config-sha256")
    parser.add_argument("--selfbody-postworld-internal-epoch-dev", action="store_true")
    args = parser.parse_args()
    goal = None
    if (args.l16_capture_root is not None
            or args.l16_goal_target_x is not None
            or args.l16_goal_target_z is not None
            or args.l16_confirm):
        if (args.l16_confirm != "L16-S49-FIRST-ACTION-ORIGINAL-DEV"
                or args.l16_capture_root is None
                or args.l16_goal_target_x is None
                or args.l16_goal_target_z is None):
            parser.error("L16 requires explicit fresh root, fixed x/z and confirmation")
        goal = L16GoalPlan(
            args.l16_goal_target_x, args.l16_goal_target_z,
            args.l16_goal_tolerance_m, args.l16_goal_stability_m,
        )
    if (
        (args.l20_external_goal_original is None)
        != (args.l20_admitted_sha256 is None)
    ):
        parser.error("L20 requires both original external file and SHA")
    if args.l20_external_goal_original is not None and goal is None:
        parser.error("L20 requires explicit L16 Goal plan and capture root")
    l23_fields = (
        args.l23_paper_server_jar, args.l23_paper_server_sha256,
        args.l23_paper_plugin_jar, args.l23_paper_plugin_sha256,
        args.l23_paper_config, args.l23_paper_config_sha256,
    )
    if any(x is not None for x in l23_fields) and not all(
        x is not None for x in l23_fields
    ):
        parser.error("L23 Paper requires all six pinned DEV asset arguments")
    paper_assets = (
        L23PaperAssets(*l23_fields) if all(
            x is not None for x in l23_fields
        ) else None
    )
    return asyncio.run(qualify(
        args.report, args.server_log,
        l16_capture_root=args.l16_capture_root, l16_goal_plan=goal,
        l20_external_goal_original=args.l20_external_goal_original,
        l20_admitted_sha256=args.l20_admitted_sha256,
        l21_observer_root=args.l21_observer_root,
        l22_settling_probes=args.l22_settling_probes,
        l23_paper_assets=paper_assets,
        postworld_internal_epoch_dev=args.selfbody_postworld_internal_epoch_dev,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
