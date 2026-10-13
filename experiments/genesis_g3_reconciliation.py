"""G3: M-source/readback reconciliation for G2 funded-parent lineage commit.

OFFLINE PROTOCOL ONLY. This is not an authenticating M/R adapter.
The caller supplies a fixed expected source identity, an M funding event, and
an independently captured M-ledger readback. Equality/digests check
consistency, NOT source genuineness or energy payment in a live World.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Literal

from experiments.genesis_g2_handoff import (
    BirthPlan,
    FundedBirthReceipt,
    FundedGenesisRegistry,
)
from experiments.genesis_heredity import Individual, _finite_number, _positive_int


def _name(value: str) -> bool:
    return isinstance(value, str) and bool(value.strip())


@dataclass(frozen=True)
class MSourceIdentity:
    """External M/R-specified identity; not a signature or source proof."""

    source_session: str
    world_snapshot: str
    metabolism_ledger: str

    def __post_init__(self) -> None:
        if not all(
            _name(value) for value in (
                self.source_session, self.world_snapshot, self.metabolism_ledger
            )
        ):
            raise ValueError("invalid M source identity")


@dataclass(frozen=True)
class ParentBalance:
    parent_id: int
    energy: float

    def __post_init__(self) -> None:
        if type(self.parent_id) is not int or self.parent_id < 0:
            raise ValueError("invalid parent balance ID")
        if not _finite_number(self.energy) or self.energy <= 0:
            raise ValueError("invalid parent energy balance")


def _balances(records: tuple[ParentBalance, ...]) -> dict[int, float]:
    if not isinstance(records, tuple) or not records:
        raise ValueError("missing balance roster")
    ids = [item.parent_id for item in records]
    if len(ids) != len(set(ids)) or ids != sorted(ids):
        raise ValueError("duplicate or unsorted balance roster")
    return {record.parent_id: record.energy for record in records}


@dataclass(frozen=True)
class MFundedEvent:
    """Caller-reported M transaction tied to G's already fixed birth plan."""

    event_id: str
    source: MSourceIdentity
    receipt: FundedBirthReceipt
    ledger_before_revision: int
    ledger_after_revision: int
    balances_before: tuple[ParentBalance, ...]
    balances_after: tuple[ParentBalance, ...]

    def __post_init__(self) -> None:
        if not _name(self.event_id):
            raise ValueError("invalid M event ID")
        if (
            type(self.ledger_before_revision) is not int
            or self.ledger_before_revision < 0
            or type(self.ledger_after_revision) is not int
            or self.ledger_after_revision <= self.ledger_before_revision
        ):
            raise ValueError("invalid ledger revision transition")
        if set(_balances(self.balances_before)) != set(_balances(self.balances_after)):
            raise ValueError("M balance roster changed across birth event")


def event_fingerprint(event: MFundedEvent) -> str:
    """Deterministic content hash for readback matching; NOT authentication."""
    payload = {
        "event_id": event.event_id,
        "source": [
            event.source.source_session,
            event.source.world_snapshot,
            event.source.metabolism_ledger,
        ],
        "receipt": [
            event.receipt.receipt_id,
            event.receipt.plan_id,
            event.receipt.batch_id,
            event.receipt.tick,
        ],
        "revisions": [event.ledger_before_revision, event.ledger_after_revision],
        "debits": [
            [item.debit_id, item.parent_id, item.before, item.after, item.child_energy]
            for item in event.receipt.debits
        ],
        "before": [[entry.parent_id, entry.energy] for entry in event.balances_before],
        "after": [[entry.parent_id, entry.energy] for entry in event.balances_after],
    }
    wire = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(wire.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MReadback:
    """Independent source/ledger readback assertion; actual access is M/R-owned."""

    source: MSourceIdentity
    ledger_revision: int
    event_sha256: str
    balances_after: tuple[ParentBalance, ...]

    def __post_init__(self) -> None:
        if type(self.ledger_revision) is not int or self.ledger_revision < 0:
            raise ValueError("invalid readback revision")
        if (
            not isinstance(self.event_sha256, str)
            or len(self.event_sha256) != 64
            or any(char not in "0123456789abcdef" for char in self.event_sha256)
        ):
            raise ValueError("invalid readback digest")
        _balances(self.balances_after)


@dataclass(frozen=True)
class G3Commit:
    source: MSourceIdentity
    event_id: str
    receipt_id: str
    plan_id: str
    ledger_after_revision: int
    fingerprint_sha256: str
    child_ids: tuple[int, ...]
    evidence_status: Literal["OFFLINE_READBACK_CONSISTENT"] = "OFFLINE_READBACK_CONSISTENT"


class MFundedLineageBridge:
    """A fail-closed wrapper, not another birth or metabolism owner.

    Each bridge is bound to an externally chosen M source and monotone ledger
    revision. Cross-process source ownership / restart recovery is NOT supplied.
    """

    def __init__(
        self,
        registry: FundedGenesisRegistry,
        *,
        expected_source: MSourceIdentity,
        ledger_revision: int,
    ) -> None:
        if not isinstance(registry, FundedGenesisRegistry):
            raise ValueError("G3 requires G2 funded registry")
        if type(ledger_revision) is not int or ledger_revision < 0:
            raise ValueError("invalid initial M ledger revision")
        self.registry = registry
        self.expected_source = expected_source
        self._ledger_revision = ledger_revision
        self._used_events: set[str] = set()
        self._history: list[G3Commit] = []

    @property
    def ledger_revision(self) -> int:
        return self._ledger_revision

    @property
    def commits(self) -> tuple[G3Commit, ...]:
        return tuple(self._history)

    def reconcile_and_commit(
        self,
        plan: BirthPlan,
        event: MFundedEvent,
        readback: MReadback,
        *,
        inherit: bool = True,
        mutate: bool = True,
    ) -> tuple[Individual, ...]:
        if type(inherit) is not bool or type(mutate) is not bool:
            raise ValueError("invalid G3 controls")
        if self.registry.pending_plan != plan:
            raise ValueError("G2 preselected plan is not pending")
        if (
            event.source != self.expected_source
            or readback.source != self.expected_source
        ):
            raise ValueError("source identity mismatch")
        if event.event_id in self._used_events:
            raise ValueError("replayed M event")
        if (
            event.ledger_before_revision != self._ledger_revision
            or event.ledger_after_revision != readback.ledger_revision
        ):
            raise ValueError("stale, mismatched or missing ledger revision")
        if event.receipt.plan_id != plan.plan_id or event.receipt.batch_id != plan.batch_id:
            raise ValueError("event not bound to G plan")
        if event.receipt.tick != plan.tick:
            raise ValueError("event tick differs from G plan")
        before = _balances(event.balances_before)
        after = _balances(event.balances_after)
        if set(before) != set(plan.parent_ids):
            raise ValueError("incomplete or foreign parent balance snapshot")
        if (
            readback.balances_after != event.balances_after
            or readback.event_sha256 != event_fingerprint(event)
        ):
            raise ValueError("M readback does not match funded event")

        running = before.copy()
        if len(event.receipt.debits) != len(plan.parent_ids):
            raise ValueError("missing physical child transfer")
        for parent_id, debit in zip(plan.parent_ids, event.receipt.debits):
            if debit.parent_id != parent_id:
                raise ValueError("physical payer differs from preselected parent")
            if not math.isclose(
                running[parent_id], debit.before, rel_tol=1e-12, abs_tol=1e-12
            ):
                raise ValueError("debit not backed by before-energy snapshot")
            running[parent_id] = debit.after
        for parent_id in before:
            if not math.isclose(
                running[parent_id], after[parent_id], rel_tol=1e-12, abs_tol=1e-12
            ):
                raise ValueError("M ledger after-energy mismatch")

        # Validation only through this point. G2 now checks its own receipt
        # identities, replay, mutation and capacity before birth commit.
        children = self.registry.commit_funded_births(
            event.receipt, inherit=inherit, mutate=mutate
        )
        self._used_events.add(event.event_id)
        self._ledger_revision = event.ledger_after_revision
        self._history.append(
            G3Commit(
                self.expected_source,
                event.event_id,
                event.receipt.receipt_id,
                plan.plan_id,
                event.ledger_after_revision,
                event_fingerprint(event),
                tuple(item.individual_id for item in children),
            )
        )
        return children
