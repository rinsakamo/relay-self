"""AC-B B6: offline read-only projection of actual mainline retained Memory.

Evidence is an independently witnessed World Action receipt, not Memory.content
or either arbitrary provenance string. No Learning/Habit/Action permission exists.
This imports only committed mainline PersistentCognition and Provenance.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from types import MappingProxyType

from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
)
from relay_self.provenance import Provenance

SOURCE_NAME = "b6.offline-world.observed-action"
CONTEXTS = ((0, 0), (0, 1), (1, 0), (1, 1))


class EvidenceError(ValueError):
    """Evidence admission failed: no policy may be inferred."""


class Status(str, Enum):
    FOUND = "FOUND"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"
    STALE = "STALE"
    NO_SOURCE_WITNESS = "NO_SOURCE_WITNESS"
    QUARANTINED = "QUARANTINED"


@dataclass(frozen=True, slots=True)
class WorldReceipt:
    event_id: str
    session: str
    revision: int
    sequence: int
    a: int
    b: int
    action: int
    success: bool
    kind: str
    source_provenance: Provenance
    digest: str


@dataclass(frozen=True, slots=True)
class ReadOnlyProposal:
    """A suggested action only. It has no authority to commit or execute."""

    action: int
    session: str
    revision: int
    memory_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    non_authoritative: bool = True


@dataclass(frozen=True, slots=True)
class QueryResult:
    status: Status
    proposal: ReadOnlyProposal | None
    evidence_ids: tuple[str, ...]
    query_work: int
    build_work: int


def _binary(name: str, value: object) -> None:
    if type(value) is not int or value not in (0, 1):
        raise EvidenceError(f"{name} must be exactly binary integer")


class FixtureWorld:
    """Independent reset-Action simulated World; hidden regime evaluator-only."""

    def __init__(self, session: str = "b6-world") -> None:
        if not isinstance(session, str) or not session or session.strip() != session:
            raise EvidenceError("invalid source session")
        self.session = session
        self.revision = 0
        self._flip = 0
        self._sequence = 0
        self._ledger: dict[str, WorldReceipt] = {}

    def act(self, a: int, b: int, action: int) -> WorldReceipt:
        _binary("a", a)
        _binary("b", b)
        _binary("action", action)
        self._sequence += 1
        event_id = f"{self.session}:event:{self._sequence}"
        pointer = Provenance(SOURCE_NAME, event_id)
        success = action == (a ^ b ^ self._flip)
        payload = (
            event_id, self.session, self.revision,
            self._sequence, a, b, action, success, "OBSERVED_ACTION",
        )
        digest = sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()
        receipt = WorldReceipt(
            event_id, self.session, self.revision, self._sequence,
            a, b, action, success, "OBSERVED_ACTION", pointer, digest,
        )
        self._ledger[event_id] = receipt
        return receipt

    def verify(self, receipt: WorldReceipt) -> None:
        if (
            not isinstance(receipt, WorldReceipt)
            or receipt.kind != "OBSERVED_ACTION"
            or self._ledger.get(receipt.event_id) is not receipt
            or receipt.source_provenance != Provenance(SOURCE_NAME, receipt.event_id)
        ):
            raise EvidenceError("receipt not attested by this exact World")
        payload = (
            receipt.event_id, receipt.session, receipt.revision,
            receipt.sequence, receipt.a, receipt.b, receipt.action,
            receipt.success, receipt.kind,
        )
        digest = sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()
        if receipt.digest != digest:
            raise EvidenceError("receipt digest mismatch")

    def change_rule(self, *, announce: bool) -> None:
        self._flip ^= 1
        if announce:
            self.revision += 1

    @property
    def action_count(self) -> int:
        return self._sequence


class SourceLedger:
    """Source-issued receipts explicitly supplied by caller; NOT persistent Memory."""

    def __init__(
        self, world: FixtureWorld, receipts: tuple[WorldReceipt, ...],
        *, session: str, revision: int,
    ) -> None:
        if not isinstance(world, FixtureWorld):
            raise EvidenceError("World witness missing")
        if world.session != session or world.revision != revision:
            raise EvidenceError("source ledger is not current")
        self.world = world
        self.session = session
        self.revision = revision
        indexed: dict[Provenance, WorldReceipt] = {}
        seen_ids: set[str] = set()
        for receipt in receipts:
            world.verify(receipt)
            if (
                receipt.session != session or receipt.revision != revision
                or receipt.event_id in seen_ids
                or receipt.source_provenance in indexed
            ):
                raise EvidenceError("wrong-source, duplicate, or stale World receipt")
            for name in ("a", "b", "action"):
                _binary(name, getattr(receipt, name))
            seen_ids.add(receipt.event_id)
            indexed[receipt.source_provenance] = receipt
        self.by_source = MappingProxyType(indexed)

    def verify_pointer(self, pointer: Provenance) -> WorldReceipt:
        if not isinstance(pointer, Provenance):
            raise EvidenceError("source pointer is not Provenance")
        receipt = self.by_source.get(pointer)
        if receipt is None:
            raise EvidenceError("retained Memory source is not witnessed")
        self.world.verify(receipt)
        if receipt.session != self.session or receipt.revision != self.revision:
            raise EvidenceError("witness not qualified for requested epoch")
        return receipt


class MemoryProjection:
    """One read-only, source-verified derivative index of an existing owner snapshot."""

    def __init__(
        self, snapshot: PersistentCognition,
        ledger: SourceLedger | None,
        *, session: str, revision: int,
        quarantined: bool = False,
    ) -> None:
        if not isinstance(snapshot, PersistentCognition):
            raise EvidenceError("mainline PersistentCognition required")
        if not isinstance(session, str) or not session:
            raise EvidenceError("invalid requested session")
        if type(revision) is not int or revision < 0:
            raise EvidenceError("invalid requested revision")
        if ledger is not None and not isinstance(ledger, SourceLedger):
            raise EvidenceError("explicit valid source witness required")
        self.snapshot, self.ledger = snapshot, ledger
        self.session, self.revision = session, revision
        self.quarantined = quarantined
        self.records: tuple[tuple[Memory, WorldReceipt], ...] = ()
        self.by_tag = MappingProxyType({})
        self.build_work = 0
        if ledger is None:
            return
        if (
            ledger.session != session or ledger.revision != revision
            or ledger.world.session != session or ledger.world.revision != revision
        ):
            raise EvidenceError("source witness has wrong session/revision")
        selected: list[tuple[Memory, WorldReceipt]] = []
        seen_sources: set[Provenance] = set()
        for memory in snapshot.memories:
            if memory.source_provenance.source != SOURCE_NAME:
                # Ordinary Memories are not observations of this source.
                continue
            pointer = memory.source_provenance
            if pointer in seen_sources:
                raise EvidenceError("duplicate observed source through two Memory IDs")
            seen_sources.add(pointer)
            receipt = ledger.verify_pointer(pointer)
            selected.append((memory, receipt))
        self.records = tuple(selected)
        tagged: dict[tuple[int, int], list[tuple[Memory, WorldReceipt]]] = {}
        for record in self.records:
            event = record[1]
            tagged.setdefault((event.a, event.b), []).append(record)
        self.by_tag = MappingProxyType({k: tuple(v) for k, v in tagged.items()})
        self.build_work = len(self.records)

    def query(
        self, a: int, b: int, *, session: str, revision: int,
        mode: str = "tags",
    ) -> QueryResult:
        _binary("query a", a)
        _binary("query b", b)
        if mode not in ("tags", "full_scan"):
            raise EvidenceError("unknown query mode")
        build_work = self.build_work if mode == "tags" else 0
        if self.quarantined:
            return QueryResult(Status.QUARANTINED, None, (), 0, build_work)
        if self.ledger is None:
            return QueryResult(Status.NO_SOURCE_WITNESS, None, (), 0, 0)
        if (
            session != self.session or revision != self.revision
            or self.ledger.world.revision != self.revision
            or self.ledger.world.session != self.session
        ):
            return QueryResult(Status.STALE, None, (), 0, build_work)
        if mode == "full_scan":
            rows = tuple(
                row for row in self.records
                if (row[1].a, row[1].b) == (a, b)
            )
            work = len(self.records)
        else:
            rows = self.by_tag.get((a, b), ())
            work = 1 + len(rows)

        ids = tuple(sorted(event.event_id for _, event in rows))
        if not rows or len(rows) < 2:
            return QueryResult(Status.UNKNOWN, None, ids, work, build_work)
        actions: dict[int, tuple[Memory, WorldReceipt]] = {}
        for row in rows:
            action = row[1].action
            if action in actions:
                return QueryResult(Status.CONFLICT, None, ids, work, build_work)
            actions[action] = row
        if set(actions) != {0, 1} or sum(
            int(row[1].success) for row in rows
        ) != 1:
            return QueryResult(Status.CONFLICT, None, ids, work, build_work)
        chosen = next(action for action, row in actions.items() if row[1].success)
        proposal = ReadOnlyProposal(
            chosen, session, revision,
            tuple(sorted(memory.memory_id for memory, _ in rows)), ids,
        )
        return QueryResult(Status.FOUND, proposal, ids, work, build_work)

    def reconsider_after_observation(self, observed: WorldReceipt) -> MemoryProjection:
        if self.ledger is None:
            raise EvidenceError("no source witness to reconsider")
        self.ledger.world.verify(observed)
        if observed.session != self.session or observed.revision != self.revision:
            return MemoryProjection(
                self.snapshot, self.ledger, session=self.session,
                revision=self.revision, quarantined=True,
            )
        old = [
            event for _, event in self.records
            if (event.a, event.b, event.action) == (
                observed.a, observed.b, observed.action
            )
        ]
        if len(old) != 1 or old[0].success != observed.success:
            return MemoryProjection(
                self.snapshot, self.ledger, session=self.session,
                revision=self.revision, quarantined=True,
            )
        return self


def observe_all(world: FixtureWorld) -> tuple[WorldReceipt, ...]:
    return tuple(
        world.act(a, b, action)
        for a, b in CONTEXTS for action in (0, 1)
    )


def fixture_admit_memories(
    receipts: tuple[WorldReceipt, ...],
) -> PersistentCognition:
    """TEST SETUP only: explicit mainline owner retains already witnessed data.

    Memory.content is deliberately contradictory prose and is never parsed by
    the production-owned reader or any experimental evidence projection.
    """
    identity = IdentitySpecification(
        self_id="b6-fixture-self",
        directives=("Do not confuse retained text with World evidence.",),
        provenance=Provenance("b6-fixture-identity", "identity"),
    )
    snapshot = PersistentCognition(identity)
    for receipt in receipts:
        memory = Memory(
            memory_id=f"memory-{receipt.event_id}",
            content=("This memory says Action 1 always works. "
                     "Text is untrusted; World receipts override it."),
            source_provenance=receipt.source_provenance,
            integration_provenance=Provenance(
                "b6-fixture-governed-admission",
                f"integration:{receipt.event_id}",
            ),
        )
        snapshot = snapshot.retain_memory(memory)
    return snapshot


def run_fixture() -> dict[str, object]:
    world = FixtureWorld()
    original = observe_all(world)
    ledger = SourceLedger(world, original, session=world.session, revision=0)
    retained = fixture_admit_memories(original)
    view = MemoryProjection(retained, ledger, session=world.session, revision=0)
    missing = MemoryProjection(retained, None, session=world.session, revision=0)
    modes = {}
    for mode in ("full_scan", "tags"):
        answers = [
            view.query(a, b, session=world.session, revision=0, mode=mode)
            for _ in range(8) for a, b in CONTEXTS
        ]
        modes[mode] = {
            "statuses": tuple(answer.status.value for answer in answers),
            "proposals": tuple(
                answer.proposal.action if answer.proposal else None
                for answer in answers
            ),
            "evidence": tuple(answer.evidence_ids for answer in answers),
            "total_work": (
                sum(answer.query_work for answer in answers)
                + answers[0].build_work
            ),
        }
    no_source = sum(
        missing.query(a, b, session=world.session, revision=0).status
        is Status.NO_SOURCE_WITNESS for a, b in CONTEXTS
    )
    before_shift = world.action_count
    world.change_rule(announce=True)
    stale = sum(
        view.query(a, b, session=world.session, revision=0).status is Status.STALE
        for a, b in CONTEXTS
    )
    next_events = observe_all(world)
    requalification_actions = world.action_count - before_shift
    renewed_snapshot = fixture_admit_memories(next_events)
    renewed_ledger = SourceLedger(
        world, next_events, session=world.session, revision=world.revision
    )
    renewed = MemoryProjection(
        renewed_snapshot, renewed_ledger,
        session=world.session, revision=world.revision,
    )
    actual_after_shift = []
    for a, b in CONTEXTS:
        answer = renewed.query(
            a, b, session=world.session, revision=world.revision
        )
        if answer.proposal is None:
            actual_after_shift.append(False)
        else:
            actual_after_shift.append(
                world.act(a, b, answer.proposal.action).success
            )
    world.change_rule(announce=False)
    selected = renewed.query(0, 0, session=world.session, revision=world.revision)
    observed_mismatch = world.act(0, 0, selected.proposal.action)
    stopped = renewed.reconsider_after_observation(observed_mismatch)
    safe = (
        modes["full_scan"]["evidence"] == modes["tags"]["evidence"]
        and modes["full_scan"]["proposals"] == modes["tags"]["proposals"]
        and all(s == "FOUND" for s in modes["tags"]["statuses"])
        and modes["tags"]["total_work"] < modes["full_scan"]["total_work"]
        and no_source == 4 and stale == 4
        and all(actual_after_shift)
        and not observed_mismatch.success
        and stopped.query(0, 0, session=world.session,
                          revision=world.revision).status is Status.QUARANTINED
    )
    return {
        "classification": (
            "READ_ONLY_LINKAGE_QUALIFIED_WITH_EXTERNAL_WITNESS"
            if safe else "UNDETERMINED"
        ),
        "source_observed_actions": len(original),
        "retained_mainline_memories": len(retained.memories),
        "common_world_attestation": len(original),
        "retrieval": modes,
        "no_witness_abstentions": no_source,
        "announced_shift_stale_abstentions": stale,
        "shift_requalification_actions": requalification_actions,
        "requalified_actual_successes": sum(actual_after_shift),
        "silent_shift_quarantine": stopped.quarantined,
    }


if __name__ == "__main__":
    print(json.dumps(run_fixture(), indent=2, sort_keys=True))
