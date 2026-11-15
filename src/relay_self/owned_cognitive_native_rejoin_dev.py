"""#860 DEV: bind owned native rejoin to *existing* A/B cognition and work owners.

The only accepted scope is a closed, explicitly read-only/no-external-work DEV
cohort. This module does not launch a model, contact a GPU engine, send peer
messages, issue EAT/ATTACK, or attest arbitrary processes outside this owner.
The existing PhysicalIssueAdmission and CognitionOwnerCohort remain canonical.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass

from relay_self.checkpointed_cognitive_runtime_dev import (
    CognitionOwnerCohort,
    ExternalPhysicalFence,
    ExternalRejoin,
)
from relay_self.owned_native_rejoin_cohort_dev import NativePreparedRejoin
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission


class OwnedWorkRejoinError(RuntimeError):
    """Source/fence/epoch mismatch; never replace it with a synthetic TRUE."""


@dataclass(frozen=True, slots=True)
class ScopedRetirementProof:
    self_id: str
    old_native_session_id: str
    new_native_session_id: str
    new_paper_session_id: str
    epoch: int
    old_epoch_retired: bool
    uncompleted_gpu_tasks: tuple[str, ...]
    discarded_transport_message_ids: tuple[str, ...]
    no_external_work_scope: bool
    historical_replay_performed: bool = False


class InertScopedWorkEpoch:
    """An inspectable NO-INFERENCE/NO-EXTERNAL-TRANSPORT DEV work boundary.

    All GPU task and outgoing transport registration for this *owned boundary*
    is either refused or explicitly reported dirty before a checkpoint.
    This only proves absence of work *through this narrow registered owner*.
    No guarantee is made about unregistered, out-of-process LLM/GPU work.
    """

    def __init__(self, current_sessions: dict[str, str]) -> None:
        if (
            type(current_sessions) is not dict or not current_sessions
            or any(
                type(sid) is not str or not sid
                or type(native) is not str or not native
                for sid, native in current_sessions.items()
            )
            or len(set(current_sessions.values())) != len(current_sessions)
        ):
            raise OwnedWorkRejoinError("unique native work roster required")
        self._lock = threading.RLock()
        self._sessions = dict(current_sessions)
        self._closed = False
        self._epoch = 0
        self._active_gpu_refs: dict[str, set[str]] = {
            sid: set() for sid in current_sessions
        }
        self._queued_message_refs: dict[str, set[str]] = {
            sid: set() for sid in current_sessions
        }
        self._prepared: dict[str, ScopedRetirementProof] = {}
        self._discarded: dict[str, tuple[str, ...]] = {}

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._closed

    @property
    def sessions(self) -> dict[str, str]:
        with self._lock:
            return dict(self._sessions)

    def register_external_gpu_task(
        self, self_id: str, native_session_id: str, task_ref: str,
    ) -> None:
        """Explicitly refuse GPU task admission in this read-only cohort."""
        with self._lock:
            if self._closed or self._sessions.get(self_id) != native_session_id:
                raise OwnedWorkRejoinError("old/closed work epoch")
            if type(task_ref) is not str or not task_ref.strip():
                raise OwnedWorkRejoinError("named GPU task required")
            self._active_gpu_refs[self_id].add(task_ref)
            raise OwnedWorkRejoinError(
                "external GPU work invalidates read-only cohort qualification"
            )

    def queue_peer_message(
        self, self_id: str, native_session_id: str, message_ref: str,
    ) -> None:
        """Record attempted outbound work; do not send through this owner."""
        with self._lock:
            if self._closed or self._sessions.get(self_id) != native_session_id:
                raise OwnedWorkRejoinError("old/closed peer work epoch")
            if type(message_ref) is not str or not message_ref.strip():
                raise OwnedWorkRejoinError("named peer message required")
            self._queued_message_refs[self_id].add(message_ref)
            raise OwnedWorkRejoinError(
                "external peer transport disabled for read-only DEV cohort"
            )

    def close_after_physical_stop(self, physical: PhysicalIssueAdmission) -> None:
        with self._lock:
            if self._closed or not physical.closed:
                raise OwnedWorkRejoinError("physical gate must close first")
            if self._sessions != physical.current_native_sessions:
                raise OwnedWorkRejoinError("work roster differs from physical owner")
            self._closed = True
            self._epoch += 1
            self._prepared.clear()
            if any(self._active_gpu_refs.values()):
                raise OwnedWorkRejoinError(
                    "external GPU work attempted; no scoped retirement certificate"
                )
            self._discarded = {
                sid: tuple(sorted(ids))
                for sid, ids in self._queued_message_refs.items()
            }
            for ids in self._queued_message_refs.values():
                ids.clear()
            if any(self._discarded.values()):
                raise OwnedWorkRejoinError(
                    "external transport attempted; not an inert cohort"
                )

    def prepare(self, proof: NativePreparedRejoin) -> ScopedRetirementProof:
        with self._lock:
            if (
                not self._closed
                or not isinstance(proof, NativePreparedRejoin)
                or self._sessions.get(proof.self_id) != proof.old_native_session_id
                or proof.new_native_session_id in self._sessions.values()
                or proof.new_native_session_id == proof.old_native_session_id
                or proof.self_id in self._prepared
                or not proof.old_process_terminated
                or not proof.effect_admission_installed
                or proof.gpu_tasks_fenced or proof.stale_transport_fenced
                or proof.physical_issue_authorized
                or proof.probe_world_tick < 0
            ):
                raise OwnedWorkRejoinError(
                    "native rejoin/old work epoch not independently closed"
                )
            if (
                any(self._active_gpu_refs.values())
                or any(self._queued_message_refs.values())
                or any(self._discarded.values())
            ):
                raise OwnedWorkRejoinError("unretired scoped work at native rejoin")
            result = ScopedRetirementProof(
                proof.self_id, proof.old_native_session_id,
                proof.new_native_session_id, proof.paper_session_id, self._epoch,
                True, (), (), True,
            )
            self._prepared[proof.self_id] = result
            return result

    def checked(self, proof: NativePreparedRejoin) -> ScopedRetirementProof:
        with self._lock:
            ready = self._prepared.get(proof.self_id)
            if (
                ready is None or ready.old_native_session_id != proof.old_native_session_id
                or ready.new_native_session_id != proof.new_native_session_id
                or ready.new_paper_session_id != proof.paper_session_id
                or ready.epoch != self._epoch or not self._closed
            ):
                raise OwnedWorkRejoinError("old/foreign scoped retirement proof")
            return ready

    def release_after_physical_rebind(
        self, current_physical_sessions: dict[str, str],
    ) -> None:
        with self._lock:
            if (
                not self._closed
                or set(self._prepared) != set(self._sessions)
                or current_physical_sessions != {
                    sid: p.new_native_session_id
                    for sid, p in self._prepared.items()
                }
            ):
                raise OwnedWorkRejoinError("not all scoped Self epochs rebound")
            self._sessions = dict(current_physical_sessions)
            self._closed = False


class OwnedCognitiveNativeBridge:
    """Optional bridge, only for a bounded no-LLM/no-peer-transport experiment.

    The native launch and probe are async. The existing cognition owner's
    rebind is synchronous and accepts the prepared receipt only AFTER all
    out-of-scope work has been rejected by the scoped ledger.
    """

    def __init__(
        self, *, native: object, physical: PhysicalIssueAdmission,
        work: InertScopedWorkEpoch, cognition: CognitionOwnerCohort,
    ) -> None:
        if (
            not isinstance(physical, PhysicalIssueAdmission)
            or not isinstance(work, InertScopedWorkEpoch)
            or not isinstance(cognition, CognitionOwnerCohort)
            or tuple(o.self_id for o in cognition.owners) != physical.self_roster
            or any(
                o.native_session_id != physical.current_native_sessions[o.self_id]
                for o in cognition.owners
            )
            or work.sessions != physical.current_native_sessions
            or set(getattr(native, "sessions", {})) != set(work.sessions)
        ):
            raise OwnedWorkRejoinError("single complete A/B physical/native/work roster required")
        self.native = native
        self.physical = physical
        self.work = work
        self.cognition = cognition
        self._verified: dict[str, NativePreparedRejoin] = {}
        self._fence_ref: str | None = None

    def close_physical(self) -> ExternalPhysicalFence:
        receipt = self.physical.close()
        # A dirty inert work registry makes the *already closed* physical gate
        # HOLD. It must not be released on failure.
        self.work.close_after_physical_stop(self.physical)
        self._verified.clear()
        return receipt

    async def prepare_native_rejoin(
        self, self_id: str, new_paper_session: str, old_native_session: str,
    ) -> str:
        if not self.work.closed or not self.physical.closed:
            raise OwnedWorkRejoinError("native rejoin while epoch not fenced")
        try:
            new_id = await self.native.prepare_rejoin(
                self_id, new_paper_session, old_native_session,
            )
            proof = self.native.prepared_receipt(
                self_id, new_paper_session, old_native_session,
            )
            if (
                not isinstance(proof, NativePreparedRejoin)
                or proof.new_native_session_id != new_id
                or proof.self_id != self_id
                or proof.paper_session_id != new_paper_session
            ):
                raise OwnedWorkRejoinError("native process receipt mismatch")
            self.work.prepare(proof)
            self._verified[self_id] = proof
            return new_id
        except BaseException:
            self.physical.hold_for_operator()
            raise

    def external_native_rejoin(
        self, self_id: str, new_paper_session: str, old_native_session: str,
    ) -> ExternalRejoin:
        proof = self._verified.get(self_id)
        if (
            proof is None
            or proof.paper_session_id != new_paper_session
            or proof.old_native_session_id != old_native_session
            or proof.self_id != self_id
        ):
            raise OwnedWorkRejoinError("missing native+work source proof")
        self.work.checked(proof)
        # Re-query the *currently owned* child and its receipt; do not trust
        # an old prepared ID once the native cohort has changed.
        current = self.native.prepared_receipt(
            self_id, new_paper_session, old_native_session,
        )
        if (
            current != proof
            or self.native.sessions[self_id].started.session_id
            != proof.new_native_session_id
        ):
            raise OwnedWorkRejoinError("native source swapped after preparation")
        if self.physical.current_native_sessions.get(self_id) != old_native_session:
            raise OwnedWorkRejoinError("physical owner session already rotated")
        # Canonical PhysicalIssueAdmission is the *only* session issuer owner.
        if not self.physical.closed:
            raise OwnedWorkRejoinError("physical gate unexpectedly open")
        # Canonical CognitionOwnerCohort supplies the current physical fence
        # token by invoking this callback while its own close() is active.
        if self._fence_ref is None:
            raise OwnedWorkRejoinError("missing current physical fence")
        self.physical.rotate_native_session(
            fence_ref=self._fence_ref, self_id=self_id,
            old_session_id=old_native_session,
            new_session_id=proof.new_native_session_id,
        )
        return ExternalRejoin(
            proof.new_native_session_id, True, True, True,
        )

    def close(self) -> ExternalPhysicalFence:
        result = self.close_physical()
        self._fence_ref = result.fence_ref
        return result

    def release(self, fence_ref: str) -> None:
        """Admit A+B source clocks WHILE HELD, then release the physical gate.

        This closes the dangerous interval in which new native sessions
        could acquire a physical lease before their new WorldBody was known.
        """
        try:
            if fence_ref != self._fence_ref or self._fence_ref is None:
                raise OwnedWorkRejoinError("foreign/stale full-cohort release")
            if (
                set(self._verified) != set(self.work.sessions)
                or not self.cognition.closed
                or not self.physical.closed
                or not self.work.closed
            ):
                raise OwnedWorkRejoinError("one native Self missing at cohort release")
            for owner in self.cognition.owners:
                proof = self._verified[owner.self_id]
                current = self.native.sessions[owner.self_id]
                if (
                    owner.native_session_id != proof.new_native_session_id
                    or self.physical.current_native_sessions.get(owner.self_id)
                    != proof.new_native_session_id
                    or current.started.session_id != proof.new_native_session_id
                    or getattr(current, "process_returncode", None) is not None
                    or proof.probe_world_tick < owner.last_observed_tick
                    or not owner.fresh_native_observation_required
                ):
                    raise OwnedWorkRejoinError(
                        "fenced new WorldBody proof stale or native process ended"
                    )
            for owner in self.cognition.owners:
                proof = self._verified[owner.self_id]
                self.cognition.observe_fenced_rejoin_world_tick(
                    self_id=owner.self_id,
                    native_session_id=proof.new_native_session_id,
                    world_tick=proof.probe_world_tick,
                )
            self.work.release_after_physical_rebind(
                self.physical.current_native_sessions,
            )
            self.physical.release(fence_ref)
            self._fence_ref = None
        except BaseException:
            self.physical.hold_for_operator()
            raise
