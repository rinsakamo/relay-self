"""#860 DEV: bound actual MineflayerProcessSession ownership for A/B rejoin.

This is a process-side adapter, NOT a physical issuer or a Minecraft proof.
The real Node/Mineflayer launch method is the default factory; tests inject
process-shaped fakes. Paper and the authoritative GPU/transport owner remain
independent attestations.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Awaitable, Callable

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerLaunchConfig,
    MineflayerObservation,
)
from relay_self.checkpoint_stop_neutralization_dev import StopParticipant
from relay_self.cohort_parallel_barrier_dev import (
    require_bounded_workers,
    run_async_cohort_barrier,
)
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission


class NativeCohortRejoinError(RuntimeError):
    """Missing or stale owned native process prevents checkpoint release."""


@dataclass(frozen=True, slots=True)
class NativePreparedRejoin:
    self_id: str
    paper_session_id: str
    old_native_session_id: str
    new_native_session_id: str
    spawn_seq: int
    probe_seq: int
    probe_request_id: str
    probe_world_tick: int = -1
    old_process_terminated: bool = True
    effect_admission_installed: bool = True
    gpu_tasks_fenced: bool = False
    stale_transport_fenced: bool = False
    physical_issue_authorized: bool = False


async def verify_native_spawn_probe(
    session: MineflayerProcessSession, *, timeout_s: float,
    probe_sink: Callable[[MineflayerObservation], None] | None = None,
) -> tuple[int, int, str, int]:
    """Verify this owned native child's spawn + request-correlated World tick.

    Common source checker for full-cohort rejoin and per-Self LOGIN.
    Native sensor evidence alone is NOT authenticated Paper/world identity.
    """
    if (
        type(timeout_s) not in (int, float)
        or not 0 < timeout_s <= 60
    ):
        raise NativeCohortRejoinError("bounded native source timeout required")
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    sid = session.started.session_id

    async def received():
        left = deadline - loop.time()
        if left <= 0:
            raise NativeCohortRejoinError("native rejoin probe timed out")
        return await asyncio.wait_for(session.receive(), left)

    spawn = None
    for _ in range(256):
        entry = await received()
        if entry.session_id != sid or isinstance(
            entry, (
                MineflayerConnectionEnd, MineflayerAdapterErrorMessage,
                MineflayerCommandError,
            ),
        ):
            raise NativeCohortRejoinError("native startup source/error mismatch")
        if isinstance(entry, MineflayerObservation) and entry.kind in {"spawn", "respawn"}:
            spawn = entry
            break
    if spawn is None:
        raise NativeCohortRejoinError("native spawn not independently observed")
    request_id = "p0d-rejoin-" + uuid.uuid4().hex
    await session.send_observe(request_id)
    for _ in range(256):
        entry = await received()
        if entry.session_id != sid or isinstance(
            entry, (
                MineflayerConnectionEnd, MineflayerAdapterErrorMessage,
                MineflayerCommandError,
            ),
        ):
            raise NativeCohortRejoinError("native probe source/error mismatch")
        if isinstance(entry, MineflayerObservation) and entry.kind == "probe":
            if (
                entry.request_id != request_id
                or entry.seq <= spawn.seq
                or entry.snapshot.time is None
            ):
                raise NativeCohortRejoinError("unmatched or unclocked native rejoin probe")
            native_time = entry.snapshot.time
            tick = native_time.day * 24000 + native_time.time_of_day
            if type(tick) is not int or tick < 0:
                raise NativeCohortRejoinError("invalid native source World clock")
            if probe_sink is not None:
                probe_sink(entry)
            return spawn.seq, entry.seq, request_id, tick
    raise NativeCohortRejoinError("native rejoin probe not received")


class OwnedNativeRejoinCohort:
    """Own one session per Self and guard its final native stdin effect boundary.

    The initial sessions must already have been started by the actual
    MineflayerProcessSession.launch API; none may be attached to an unrelated
    process. Only the exact shared PhysicalIssueAdmission gates their effects.
    """

    def __init__(
        self, *,
        sessions: dict[str, MineflayerProcessSession],
        configs: dict[str, MineflayerLaunchConfig],
        physical: PhysicalIssueAdmission,
        launch: Callable[
            [MineflayerLaunchConfig], Awaitable[MineflayerProcessSession]
        ] | None = None,
        probe_timeout_s: float = 12.0,
        initial_probe_workers: int = 1,
    ) -> None:
        if not isinstance(physical, PhysicalIssueAdmission):
            raise NativeCohortRejoinError("physical owner required")
        if (
            type(sessions) is not dict or type(configs) is not dict
            or set(sessions) != set(configs)
            or tuple(sorted(sessions)) != physical.self_roster
            or len({id(x) for x in sessions.values()}) != len(sessions)
        ):
            raise NativeCohortRejoinError("unique complete native Self roster required")
        if (
            type(probe_timeout_s) not in (float, int)
            or not 0 < probe_timeout_s <= 60
        ):
            raise NativeCohortRejoinError("bounded probe timeout required")
        if (
            len({c.username for c in configs.values()}) != len(configs)
            or len({(c.host, c.port) for c in configs.values()}) != 1
            or any(
                not isinstance(c, MineflayerLaunchConfig)
                or c.host != "127.0.0.1"
                or c.version != "1.21.8"
                for c in configs.values()
            )
        ):
            raise NativeCohortRejoinError(
                "disposable localhost Paper 1.21.8 and distinct Self names required"
            )
        if physical.closed:
            raise NativeCohortRejoinError("initial native cohort already fenced")
        for sid, session in sessions.items():
            if (
                session.started.session_id != physical.current_native_sessions[sid]
                or session.started.config != configs[sid]
                or session.process_returncode is not None
            ):
                raise NativeCohortRejoinError("unqualified current native process")
        self.physical = physical
        self.configs = dict(configs)
        self.sessions = dict(sessions)
        self.launch = launch or MineflayerProcessSession.launch
        self.probe_timeout_s = float(probe_timeout_s)
        self.initial_probe_workers = require_bounded_workers(initial_probe_workers)
        self._prepared: dict[str, NativePreparedRejoin] = {}
        self._initial_verified: dict[str, tuple[int, int, str]] = {}
        self._verified_probe_ticks: dict[str, int] = {}
        try:
            for sid, session in self.sessions.items():
                self._install(sid, session)
        except BaseException:
            self.physical.hold_for_operator()
            raise

    def _install(self, sid: str, session: MineflayerProcessSession) -> None:
        def check(native_id: str, effect: str, action_id: str) -> None:
            self.physical.require_native_effect(
                self_id=sid, native_session_id=native_id,
                effect=effect, action_id=action_id,
            )

        session.install_effect_admission(check)

    def participants_now(self) -> tuple[StopParticipant, ...]:
        """Use the current owned processes in the existing STOP cohort."""
        return tuple(
            StopParticipant(sid, self.sessions[sid])
            for sid in sorted(self.sessions)
        )

    def prepared_receipt(
        self, self_id: str, paper_session: str, former_native: str,
    ) -> NativePreparedRejoin:
        """Read-only input to the existing external native/GPU owner callback.

        This method does not rotate PhysicalIssueAdmission or claim GPU cleanup.
        """
        receipt = self._prepared.get(self_id)
        if (
            receipt is None
            or receipt.paper_session_id != paper_session
            or receipt.old_native_session_id != former_native
            or self.sessions[self_id].started.session_id != receipt.new_native_session_id
        ):
            raise NativeCohortRejoinError("missing exact native rejoin evidence")
        return receipt

    async def _spawn_and_probe(self, session: MineflayerProcessSession) -> tuple[int, int, str]:
        spawn_seq, probe_seq, request_id, tick = await verify_native_spawn_probe(
            session, timeout_s=self.probe_timeout_s,
        )
        self._verified_probe_ticks[session.started.session_id] = tick
        return spawn_seq, probe_seq, request_id

    async def verify_initial_cohort(self) -> dict[str, tuple[int, int, str]]:
        """Require spawn and correlated native probe from every initial process.

        This is a read-only process-side witness. It cannot certify a Paper
        World UUID, GPU task disposal, or a durable Self cognitive snapshot.
        Never silently retry a partially read initial native session.
        """
        if self._initial_verified or self.physical.closed:
            raise NativeCohortRejoinError("initial native cohort already read/held")
        try:
            ordered = tuple(sorted(self.sessions))

            async def verified_initial(sid: str) -> tuple[int, int, str]:
                current = self.sessions[sid]
                proof = await self._spawn_and_probe(current)
                if (
                    self.sessions[sid] is not current
                    or current.process_returncode is not None
                    or current.started.session_id
                    != self.physical.current_native_sessions[sid]
                ):
                    raise NativeCohortRejoinError("initial source changed during probe")
                return proof

            results = await run_async_cohort_barrier(
                ordered, verified_initial,
                workers=self.initial_probe_workers,
                total_timeout_s=180.0,
            )
            proofs = dict(zip(ordered, results, strict=True))
            self._initial_verified = proofs
            return dict(proofs)
        except BaseException:
            self.physical.hold_for_operator()
            raise

    async def prepare_rejoin(
        self, self_id: str, paper_session: str, former_native: str,
    ) -> str:
        """Terminate only the old owned Self child, launch and observe new one.

        Called after Paper has restarted but before existing cognitive owner
        rebind/release; neither this method nor a successful probe grants issue.
        """
        replacement = None
        try:
            if (
                self_id not in self.sessions
                or type(paper_session) is not str or not paper_session.strip()
                or type(former_native) is not str
                or not self.physical.closed
                or self.physical.current_native_sessions[self_id] != former_native
            ):
                raise NativeCohortRejoinError("unfenced or foreign native rejoin")
            old = self.sessions[self_id]
            if old.started.session_id != former_native:
                raise NativeCohortRejoinError("former process identity differs")
            previous = self._prepared.get(self_id)
            if previous is not None and previous.new_native_session_id != former_native:
                raise NativeCohortRejoinError("stale prepared native receipt")
            self._prepared.pop(self_id, None)
            if old.process_returncode is None:
                await old.terminate()
            if old.process_returncode is None:
                raise NativeCohortRejoinError("former native process still alive")
            replacement = await self.launch(self.configs[self_id])
            if (
                replacement.started.config != self.configs[self_id]
                or replacement.started.session_id == former_native
                or replacement.process_returncode is not None
                or replacement.started.session_id in {
                    x.started.session_id for sid, x in self.sessions.items()
                    if sid != self_id
                }
            ):
                raise NativeCohortRejoinError("new native process source not fresh")
            self._install(self_id, replacement)
            spawn_seq, probe_seq, request_id = await self._spawn_and_probe(replacement)
            self.sessions[self_id] = replacement
            evidence = NativePreparedRejoin(
                self_id, paper_session, former_native,
                replacement.started.session_id, spawn_seq, probe_seq, request_id,
                probe_world_tick=self._verified_probe_ticks[replacement.started.session_id],
            )
            self._prepared[self_id] = evidence
            return evidence.new_native_session_id
        except BaseException:
            # No automatic reattempt/physical release on uncertain native work.
            self.physical.hold_for_operator()
            if replacement is not None:
                try:
                    await replacement.terminate()
                except BaseException:
                    pass
            raise
