"""B10 offline observer-scoped issuance and SQLite local replay defense.

This is a bounded integration of *inherited* B9's exact-S16 signature verifier
and actual S15 MineflayerExecutionSession protocol. A FakeSession can invent
messages; neither observer instrumentation nor HMAC proves physical Minecraft.
SQLite is a local transactional test journal, not tamper/rollback protection.
"""
from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adapters.mineflayer.execution import (
    MineflayerCommand,
    MineflayerExecutionSession,
    WorldConsequence,
    WorldConsequenceStatus,
    build_mineflayer_command,
    execute_mineflayer_command,
)
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
)
from experiments.ac_b_b9_signed_s16 import (
    ExternalS16EvidenceGate,
    OfflineS16SourceIssuer,
    SignedS16Evidence,
    UnqualifiedWorldEvidence,
)
from relay_self.action import ActionLifecycle
from relay_self.action_outcome import ActionOutcomeInterpretation
from relay_self.execution_binding import ExecutionBindingResult
from relay_self.provenance import Provenance

JOURNAL_VERSION = "B10_OBSERVED_SOURCE_REPLAY_V1"


@dataclass(frozen=True, slots=True)
class ObservedS16Packet:
    consequence: WorldConsequence
    source_envelope: SignedS16Evidence


class ObservedAdapter:
    """Intercept actual S15 protocol returns and issued commands, in order.

    Captures what this Python app was told, NOT an independent sensor or
    authentication of the underlying Mineflayer process.
    """

    def __init__(self, underlying: MineflayerExecutionSession) -> None:
        self._underlying = underlying
        self.started = underlying.started
        self.events: list[tuple[str, Any]] = []

    async def receive(self):
        message = await self._underlying.receive()
        self.events.append(("receive", message))
        return message

    async def send_observe(self) -> None:
        await self._underlying.send_observe()
        self.events.append(("observe", None))

    async def send_set_control(
        self, action_id: str, *, control: str, state: bool,
    ) -> None:
        await self._underlying.send_set_control(
            action_id, control=control, state=state,
        )
        self.events.append(("set_control", (action_id, control, state)))

    async def send_clear_controls(self, action_id: str) -> None:
        await self._underlying.send_clear_controls(action_id)
        self.events.append(("clear_controls", action_id))

    def qualify_completed(
        self, command: MineflayerCommand, consequence: WorldConsequence,
    ) -> None:
        if (
            not isinstance(consequence, WorldConsequence)
            or consequence.status is not WorldConsequenceStatus.EXECUTED
            or consequence.session_id != self.started.session_id
        ):
            raise UnqualifiedWorldEvidence("no complete witnessed EXECUTED event")
        before = consequence.before_observation
        dispatch = consequence.dispatch_receipt
        cleanup = consequence.cleanup_receipt
        after = consequence.after_observation
        if not all(
            isinstance(item, (MineflayerObservation, MineflayerEffectResult))
            for item in (before, dispatch, cleanup, after)
        ):
            raise UnqualifiedWorldEvidence("incomplete adapter observations")
        if not (
            type(before) is MineflayerObservation
            and type(dispatch) is MineflayerEffectResult
            and type(cleanup) is MineflayerEffectResult
            and type(after) is MineflayerObservation
        ):
            raise UnqualifiedWorldEvidence("wrong adapter protocol message kinds")
        expected = (
            ("observe", None),
            ("receive", before),
            ("set_control", (command.action_id, command.control, command.state)),
            ("receive", dispatch),
            ("clear_controls", command.cleanup_action_id),
            ("receive", cleanup),
            ("observe", None),
            ("receive", after),
        )
        if tuple(self.events) != expected:
            raise UnqualifiedWorldEvidence("command/received evidence order mismatched")
        # Crucially, require that the actual received message *objects* are
        # the same ones the S15 executor used for the S16 consequence.
        if not all(
            self.events[index][1] is evidence
            for index, evidence in ((1, before), (3, dispatch),
                                    (5, cleanup), (7, after))
        ):
            raise UnqualifiedWorldEvidence("received evidence was substituted")
        messages = (before, dispatch, cleanup, after)
        if not all(m.session_id == self.started.session_id for m in messages):
            raise UnqualifiedWorldEvidence("source message session is inconsistent")
        seq = [m.seq for m in messages]
        if any(type(x) is not int or x < 1 for x in seq) or seq != sorted(
            set(seq)
        ):
            raise UnqualifiedWorldEvidence("source message sequences not strictly increasing")
        if (
            before.kind != "probe" or after.kind != "probe"
            or dispatch.action_id != command.action_id
            or dispatch.effect != command.effect
            or dispatch.result != "applied"
            or cleanup.action_id != command.cleanup_action_id
            or cleanup.effect != "clear_controls"
            or cleanup.result != "applied"
        ):
            raise UnqualifiedWorldEvidence("source message action/response mismatch")
        if (
            consequence.action_id != command.action_id
            or consequence.binding_id != command.binding_id
            or consequence.action_ref != command.action_ref
        ):
            raise UnqualifiedWorldEvidence("source issued Action mismatch")


class ObservationBoundIssuer:
    """Can sign only by performing its own observed S15 protocol transaction.

    The inherited B9 signer is private implementation detail. This Python
    restriction alone is NOT cryptographic key isolation or source attestation.
    """

    def __init__(self, source_key: bytes, session_id: str) -> None:
        self.__source = OfflineS16SourceIssuer(source_key, session_id)
        self._issued_actions: set[tuple[str, str]] = set()

    async def execute_and_sign(
        self,
        issued: ActionLifecycle,
        binding: ExecutionBindingResult,
        adapter: MineflayerExecutionSession,
        *, provenance: Provenance,
    ) -> ObservedS16Packet:
        command = build_mineflayer_command(issued, binding)
        if adapter.started.session_id != self.__source.session:
            raise UnqualifiedWorldEvidence("observer session not bound to signer")
        key = (self.__source.session, command.action_id)
        if key in self._issued_actions:
            raise UnqualifiedWorldEvidence("one issuance per issued Action")
        # Reserve before any execution. If execution fails, no replay/reattempt.
        self._issued_actions.add(key)
        instrumented = ObservedAdapter(adapter)
        consequence = await execute_mineflayer_command(
            instrumented, command, provenance=provenance,
        )
        instrumented.qualify_completed(command, consequence)
        return ObservedS16Packet(
            consequence=consequence,
            source_envelope=self.__source.sign(consequence),
        )


class PersistentReplayJournal:
    """An explicitly initialized, fail-closed local SQLite replay ledger."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._validate_schema()

    @classmethod
    def initialize(cls, path: Path) -> PersistentReplayJournal:
        path = Path(path)
        if path.exists() or path.is_symlink() or not path.parent.is_dir():
            raise UnqualifiedWorldEvidence("journal must be a fresh explicit local file")
        # SQLite's create is only allowed here, never from the gate/read path.
        connection = sqlite3.connect(str(path))
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("CREATE TABLE authority (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute(
                "INSERT INTO authority(key,value) VALUES ('schema',?)",
                (JOURNAL_VERSION,),
            )
            connection.execute(
                "CREATE TABLE consumed (event_id TEXT PRIMARY KEY, "
                "session_id TEXT NOT NULL, action_id TEXT NOT NULL, "
                "world_digest TEXT NOT NULL, "
                "UNIQUE(session_id,action_id))"
            )
            connection.commit()
        finally:
            connection.close()
        return cls(path)

    def _connect(self) -> sqlite3.Connection:
        if not self.path.is_file() or self.path.is_symlink():
            raise UnqualifiedWorldEvidence("trusted initialized journal missing")
        try:
            connection = sqlite3.connect(
                self.path.absolute().as_uri() + "?mode=rw", uri=True,
                timeout=3.0, isolation_level=None,
            )
            connection.execute("PRAGMA busy_timeout=3000")
            return connection
        except sqlite3.Error as exc:
            raise UnqualifiedWorldEvidence("journal cannot be opened") from exc

    def _validate_schema(self) -> None:
        connection = self._connect()
        try:
            valid = connection.execute("PRAGMA quick_check").fetchone()
            schema = connection.execute(
                "SELECT value FROM authority WHERE key='schema'"
            ).fetchone()
            rows = connection.execute("PRAGMA table_info(consumed)").fetchall()
            if (
                valid != ("ok",) or schema != (JOURNAL_VERSION,)
                or [r[1] for r in rows] != [
                    "event_id", "session_id", "action_id", "world_digest",
                ]
            ):
                raise UnqualifiedWorldEvidence("journal schema/integrity mismatch")
        except sqlite3.Error as exc:
            raise UnqualifiedWorldEvidence("journal corrupt or incompatible") from exc
        finally:
            connection.close()

    def claim(self, signed: SignedS16Evidence) -> None:
        self._validate_schema()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO consumed (event_id,session_id,action_id,world_digest) "
                "VALUES (?,?,?,?)",
                (
                    signed.event_id, signed.session_id, signed.action_id,
                    signed.consequence_digest,
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            raise UnqualifiedWorldEvidence(
                "durable event or session/action replay rejected"
            ) from exc
        except sqlite3.Error as exc:
            connection.rollback()
            raise UnqualifiedWorldEvidence("durable replay journal unavailable") from exc
        finally:
            connection.close()


class DurableReadOnlyGate:
    """Inherited B9 source/epoch/S16 validation, then atomic SQLite admission."""

    def __init__(
        self, b9: ExternalS16EvidenceGate, journal: PersistentReplayJournal,
    ) -> None:
        if not isinstance(b9, ExternalS16EvidenceGate) or not isinstance(
            journal, PersistentReplayJournal
        ):
            raise UnqualifiedWorldEvidence("explicit B9 gate and replay store needed")
        self.b9 = b9
        self.journal = journal

    def qualify(
        self,
        issued: ActionLifecycle,
        binding: ExecutionBindingResult,
        packet: ObservedS16Packet,
    ) -> ActionOutcomeInterpretation:
        if not isinstance(packet, ObservedS16Packet):
            raise UnqualifiedWorldEvidence("observation-bound typed evidence required")
        result = self.b9.qualify(
            issued, binding, packet.consequence, packet.source_envelope,
        )
        self.journal.claim(packet.source_envelope)
        return result


async def run_once(
    issued: ActionLifecycle,
    binding: ExecutionBindingResult,
    adapter: MineflayerExecutionSession,
    key: bytes,
    *,
    provenance: Provenance,
) -> ObservedS16Packet:
    issuer = ObservationBoundIssuer(key, adapter.started.session_id)
    return await issuer.execute_and_sign(
        issued, binding, adapter, provenance=provenance,
    )


def run_offline_transaction(
    issued: ActionLifecycle,
    binding: ExecutionBindingResult,
    adapter: MineflayerExecutionSession,
    key: bytes,
    provenance: Provenance,
) -> ObservedS16Packet:
    return asyncio.run(run_once(issued, binding, adapter, key, provenance=provenance))
