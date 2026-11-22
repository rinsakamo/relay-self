"""U18 Q4 original B two-MOVE owned-process DEV entry.

Existing Original B Stage26 L1 -> Stage27 S1 -> settled WAL -> fresh L1 ->
new Intent/Skill/Action -> U15 S2; one Native stdin/stdout capture throughout.
The caller owns a newly isolated Paper/bridge/actual llama.cpp backend. No
synthetic S1 callback, alternate issuer, WAL, Paper event or model choice.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.process_session import MineflayerProcessSession
from experiments.cognitive_physical_executor_dev import PhysicalDevGrant
from experiments.cognitive_physical_place_move_issue_dev import Stage27PlaceMoveReceipt
from experiments.i_unified_q4_raw_evidence_manifest_dev import (
    Q4RawManifestHold,
    seal_q4_original_raw_manifest,
)
from experiments.p0d_real_paper_smoke_dev import _write_bytes_new
from relay_self.checkpointed_cognitive_runtime_dev import StagedRecoveredCognition
from relay_self.i_lane_i4a_s1_owned_native_runner_dev import (
    issue_original_s1_place_on_owned_native_dev,
)
from relay_self.i_lane_i4a_s2_owned_native_runner_dev import (
    I4AS2OwnedNativeHold,
    continue_original_s1_to_s2_owned_native_dev,
)
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.p0d_stage27h_bounded_l0_move_dev import Stage27hBoundedMoveLoop
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalActionBinding
from relay_self.provenance import Provenance
from relay_self.q4_original_paper_position_dev import (
    Q4OriginalPaperPositionWindow,
    await_original_q4_paper_position_window,
)
from relay_self.q4_place_abort_dev import Q4DevOperatorPermit


@dataclass(frozen=True, slots=True)
class U17OriginalS1Settled:
    """S1 data derived INSIDE the original product execution path."""

    loop: Stage27hBoundedMoveLoop
    receipt: Stage27PlaceMoveReceipt
    paper_window: Q4OriginalPaperPositionWindow
    forward_ms: float
    host_ms: float


async def run_original_u17_two_place_trial_dev(
    *, bridge: OwnedResidentPhysicalBridge,
    self_id: str,
    evidence_dir: Path,
    restored: StagedRecoveredCognition,
    grant_for_action: Callable[
        [PhysicalActionBinding], tuple[PhysicalDevGrant, PhysicalDevGrant],
    ],
    s1_operator_permit: Q4DevOperatorPermit,
    s2_operator_permit: Q4DevOperatorPermit,
    provenance: Provenance,
    real_world_granted: bool = False,
    trial_mode: str = "two_moves",
) -> tuple[Stage27PlaceMoveReceipt, Stage27PlaceMoveReceipt]:
    """One real parent: no fabricated S1 callback, no second Native session.

    This function is NOT a Paper/Minecraft launcher. The caller must supply
    its existing genuine single-Self OwnedResidentPhysicalBridge and original
    recovered cognition. Actual World pass requires the independent Q audit
    of seven raw originals; this entry never asserts real-world approval.
    """
    if (
        type(bridge) is not OwnedResidentPhysicalBridge
        or self_id != "B"
        or type(real_world_granted) is not bool or not real_world_granted
        or not isinstance(evidence_dir, Path)
        or not evidence_dir.is_absolute() or not evidence_dir.is_dir()
        or evidence_dir.is_symlink()
        or not isinstance(restored, StagedRecoveredCognition)
        or restored.self_id != self_id
        or not callable(grant_for_action)
        or not isinstance(s1_operator_permit, Q4DevOperatorPermit)
        or not isinstance(s2_operator_permit, Q4DevOperatorPermit)
        or s1_operator_permit is s2_operator_permit
        or not isinstance(provenance, Provenance)
        or trial_mode not in ("two_moves", "stop_failure")
        or tuple(bridge.lifecycle.self_roster) != (self_id,)
        or len(bridge.sessions) != 1
        or bridge.inference_lane is None
        or bridge.cognitive_work is None
        or bridge.physical.observation_only
    ):
        raise I4AS2OwnedNativeHold("isolated Original B Q4 World/Owner opt-in missing")
    session = bridge.sessions.get(self_id)
    owner = bridge.owners.get(self_id)
    if (
        type(session) is not MineflayerProcessSession
        or session.process_returncode is not None
        or session.owned_child_pid is None
        or not session.bounded_place_dev_mode
        or owner is None or owner.native_session_id != session.started.session_id
        or bridge.physical.current_native_sessions.get(self_id)
        != session.started.session_id
        or bridge.physical.resident_states.get(self_id) != "ONLINE"
        or bridge.physical._original_place_s1.get(self_id) is not None
        or bridge.paper.owned_session_id is None
        or bridge.paper.held_uncertain
    ):
        raise I4AS2OwnedNativeHold("fresh original S1/Native/Paper scope absent")
    bridge._check_world()
    journal = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id=self_id,
    )
    journal.require_clear()
    if journal.records or owner.supervisor.recorded_actions:
        raise I4AS2OwnedNativeHold("fresh S1 cannot replay an earlier physical Action")

    started_ns = time.monotonic_ns()
    stdout = evidence_dir / "original-native-stdout.jsonl"
    stdin = evidence_dir / "original-native-stdin.jsonl"
    session.start_raw_source_audit(stdout)
    try:
        session.start_raw_stdin_audit(stdin)
    except BaseException:
        session.finish_raw_source_audit()
        raise
    first = None
    second = None
    first_metrics = None
    failure: BaseException | None = None
    try:
        # Sole original gate snapshots the empty canonical WAL after the
        # original Bridge/Owner login; there is no rearming before first use.
        bridge.physical.arm_original_place_s1(
            bridge=bridge, self_id=self_id, journal=journal,
        )
        initial = await issue_original_s1_place_on_owned_native_dev(
            bridge=bridge, restored=restored,
            native_stdout_path=stdout,
            grant_for_action=grant_for_action,
            operator_permit=s1_operator_permit,
            provenance=provenance,
            inject_stop_failure=trial_mode == "stop_failure",
        )
        if trial_mode == "stop_failure":
            raise I4AS2OwnedNativeHold(
                "STOP fault injection unexpectedly returned a settled original Action"
            )
        first = initial.receipt
        first_metrics = (initial.forward_ms, initial.host_ms)
        paper_window = await await_original_q4_paper_position_window(
            bridge, self_id, first,
        )
        original = U17OriginalS1Settled(
            initial.loop, first, paper_window,
            initial.forward_ms, initial.host_ms,
        )
        _, second = await continue_original_s1_to_s2_owned_native_dev(
            bridge=bridge, s1_loop=original.loop, s1_receipt=original.receipt,
            paper_window=original.paper_window,
            native_stdout_path=stdout, evidence_dir=evidence_dir,
            grant_for_action=grant_for_action,
            operator_permit=s2_operator_permit, provenance=provenance,
            s1_forward_ms=original.forward_ms,
            s1_host_ms=original.host_ms,
        )
        PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=self_id,
        ).require_clear()
        if (
            first.action_id == second.action_id
            or first.native_session_id != second.native_session_id
            or second.journal_status != "NATIVE_PLACE_MOVE_SETTLED"
        ):
            raise I4AS2OwnedNativeHold("second original PLACE not terminal/new")
    except BaseException as exc:
        failure = exc
        raise
    finally:
        # All paths revoke the original physical gate and force-confirm Node
        # process exit before the raw archive is sealed, including on CANCEL.
        try:
            if session.process_returncode is None:
                try:
                    bridge.quarantine(self_id)
                except Exception:
                    bridge.physical.hold_for_operator()
                await session.force_terminate_owned(timeout_s=0.5)
            if session.process_returncode is None:
                raise I4AS2OwnedNativeHold("original Node exit unconfirmed")
            final_wal = PhysicalActionJournal.restore(
                owner.files.physical_wal_file, self_id=self_id,
            )
            _write_bytes_new(
                evidence_dir / "original-node-process-exit.json",
                (json.dumps({
                    "schema": 1, "owned_pid": session.owned_child_pid,
                    "native_session": session.started.session_id,
                    "returncode": session.process_returncode,
                    "trial_started_monotonic_ns": started_ns,
                    "trial_finished_monotonic_ns": time.monotonic_ns(),
                    "s1_action_id": first.action_id if first else None,
                    "s2_action_id": second.action_id if second else None,
                    "s2_terminal": failure is None and second is not None,
                    "trial_mode": trial_mode,
                    "stop_fault_injection_consumed": bool(
                        session._q4_stop_failure_used
                    ),
                    "wal_unresolved": bool(final_wal.unresolved),
                    "real_world_dev_pass": False,
                    "paper_causation_attested": False,
                }, sort_keys=True) + "\n").encode(),
            )
            _write_bytes_new(
                evidence_dir / "original-host-monotonic.json",
                (json.dumps({
                    "schema": 1,
                    "start_monotonic_ns": started_ns,
                    "end_monotonic_ns": time.monotonic_ns(),
                    "s1_forward_ms": first_metrics[0] if first_metrics else None,
                    "s1_start_stop_host_ms": first_metrics[1]
                    if first_metrics else None,
                    "no_real_world_pass_claim": True,
                }, sort_keys=True) + "\n").encode(),
            )
            _write_bytes_new(
                evidence_dir / "original-paper-process.log",
                bridge.paper.read_owned_log(bridge.paper.owned_session_id),
            )
            _write_bytes_new(
                evidence_dir / "original-owner-wal.json",
                owner.files.physical_wal_file.read_bytes(),
            )
            _write_bytes_new(
                evidence_dir / "original-owner-persistent-cognition.json",
                owner.files.cognition_file.read_bytes(),
            )
        finally:
            if session._raw_stdin_audit_fd is not None:
                session.finish_raw_stdin_audit()
            if session._raw_source_audit_fd is not None:
                session.finish_raw_source_audit()
        if all((
            stdout.is_file(), stdin.is_file(),
            (evidence_dir / "original-paper-process.log").is_file(),
            (evidence_dir / "original-owner-wal.json").is_file(),
            (evidence_dir / "original-owner-persistent-cognition.json").is_file(),
            (evidence_dir / "original-host-monotonic.json").is_file(),
            (evidence_dir / "original-node-process-exit.json").is_file(),
        )):
            try:
                seal_q4_original_raw_manifest(
                    root=evidence_dir, mode=trial_mode,
                    evidence={
                        "native_stdout": stdout,
                        "native_stdin": stdin,
                        "paper_ticks": evidence_dir / "original-paper-process.log",
                        "owner_wal": evidence_dir / "original-owner-wal.json",
                        "owner_cognition": (
                            evidence_dir / "original-owner-persistent-cognition.json"
                        ),
                        "host_monotonic": evidence_dir / "original-host-monotonic.json",
                        "process_exit": evidence_dir / "original-node-process-exit.json",
                    },
                    output=evidence_dir / (
                        "original-u17-" + trial_mode.replace("_", "-")
                        + "-manifest.json"
                    ),
                )
            except Q4RawManifestHold:
                if failure is None:
                    raise
    assert first is not None and second is not None
    return first, second
