"""U17 DEV-only one-World two-PLACE call site for the ORIGINAL B bridge.

No World launcher, synthetic L1, alternate issuer, or approval principal:
the caller must supply its already-authorized *original* Stage27h S1
operation in a disposable, process-backed, single-Self Bridge. This module
owns only the continuous original IO transcripts and terminal process exit.
Missing genuine Paper position producer remains PRE_WORLD_HOLD.
"""
from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.process_session import MineflayerProcessSession
from experiments.cognitive_physical_executor_dev import PhysicalDevGrant
from experiments.cognitive_physical_place_move_issue_dev import Stage27PlaceMoveReceipt
from experiments.p0d_real_paper_smoke_dev import _write_bytes_new
from relay_self.i_lane_i4a_s2_owned_native_runner_dev import (
    I4AS2OwnedNativeHold,
    continue_original_s1_to_s2_owned_native_dev,
)
from relay_self.owned_paper_world_dev import PaperTickReceipt
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.p0d_stage27h_bounded_l0_move_dev import Stage27hBoundedMoveLoop
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance
from relay_self.q4_place_abort_dev import Q4DevOperatorPermit


@dataclass(frozen=True, slots=True)
class U17OriginalS1Settled:
    """Original issuer result; independently rechecked against live raw IO."""

    loop: Stage27hBoundedMoveLoop
    receipt: Stage27PlaceMoveReceipt
    paper_stop: PaperTickReceipt
    paper_first: PaperTickReceipt
    paper_settled: PaperTickReceipt
    forward_ms: float
    host_ms: float


async def run_original_u17_two_place_trial_dev(
    *, bridge: OwnedResidentPhysicalBridge,
    self_id: str,
    evidence_dir: Path,
    original_s1: Callable[[], Awaitable[U17OriginalS1Settled]],
    propose_grant: PhysicalDevGrant,
    issue_grant: PhysicalDevGrant,
    operator_permit: Q4DevOperatorPermit,
    provenance: Provenance,
    real_world_granted: bool = False,
) -> tuple[Stage27PlaceMoveReceipt, Stage27PlaceMoveReceipt]:
    """One original process/capture across original S1 and L1-selected S2.

    This is a call site around the ORIGINAL Stage27h issuer, not an S1
    implementation or an ActionPort. The callback MUST run actual S1; neither
    its returned receipt nor typed Paper samples are World qualifications.
    Any uncertain error terminates the bridge-owned process and does not
    invent terminal WAL, successful STOP or Paper provenance.
    """
    if (
        type(bridge) is not OwnedResidentPhysicalBridge
        or type(self_id) is not str or not self_id
        or not real_world_granted
        or not isinstance(evidence_dir, Path)
        or not evidence_dir.is_absolute() or not evidence_dir.is_dir()
        or evidence_dir.is_symlink()
        or not callable(original_s1)
        or not isinstance(propose_grant, PhysicalDevGrant)
        or not isinstance(issue_grant, PhysicalDevGrant)
        or not isinstance(operator_permit, Q4DevOperatorPermit)
        or not isinstance(provenance, Provenance)
        or tuple(bridge.lifecycle.self_roster) != (self_id,)
        or len(bridge.sessions) != 1
        or bridge.inference_lane is None
        or bridge.cognitive_work is None
        or bridge.physical.observation_only
    ):
        raise I4AS2OwnedNativeHold("isolated original B U17 World grant missing")
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
        or bridge.physical._original_place_s1.get(self_id) is None
        or bridge.paper.owned_session_id is None
        or bridge.paper.held_uncertain
    ):
        raise I4AS2OwnedNativeHold("original S1/Native/Paper scope absent")
    bridge._check_world()
    PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id=self_id,
    ).require_clear()
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
    failure = None
    try:
        s1 = await original_s1()
        if not isinstance(s1, U17OriginalS1Settled):
            raise I4AS2OwnedNativeHold("original Stage27h S1 result absent")
        first = s1.receipt
        _, second = await continue_original_s1_to_s2_owned_native_dev(
            bridge=bridge, s1_loop=s1.loop, s1_receipt=s1.receipt,
            paper_stop=s1.paper_stop, paper_first=s1.paper_first,
            paper_settled=s1.paper_settled,
            native_stdout_path=stdout, evidence_dir=evidence_dir,
            propose_grant=propose_grant, issue_grant=issue_grant,
            operator_permit=operator_permit, provenance=provenance,
            s1_forward_ms=s1.forward_ms, s1_host_ms=s1.host_ms,
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
        # A disposable DEV trial never leaves the original active Native
        # controlling a moving body after partial failure/cancellation.
        try:
            if session.process_returncode is None:
                try:
                    bridge.quarantine(self_id)
                except Exception:
                    bridge.physical.hold_for_operator()
                await session.force_terminate_owned(timeout_s=0.5)
            if session.process_returncode is None:
                raise I4AS2OwnedNativeHold("owned Node exit not confirmed")
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
                    "real_world_dev_pass": False,
                    "paper_causation_attested": False,
                }, sort_keys=True) + "\n").encode(),
            )
        finally:
            if session._raw_stdin_audit_fd is not None:
                session.finish_raw_stdin_audit()
            if session._raw_source_audit_fd is not None:
                session.finish_raw_source_audit()
    assert first is not None and second is not None
    return first, second
