"""AC-B B5: offline observed-transition retrieval, with strong cheap comparators.

Only source-native reset-World Action receipts ground two-hop predictions.
Untrusted association/causal claims can NEVER act as observed transitions.
No production, Mineflayer, LLM, or sibling Draft imports.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from enum import Enum
from hashlib import sha256
from types import MappingProxyType
from typing import Mapping

STATES = 16
ACTIONS = (0, 1)
MODES = ("full_scan", "tags", "flat", "typed_graph")


class EvidenceError(ValueError):
    """Malformed or unqualified evidence cannot ground retrieval."""


class Status(str, Enum):
    FOUND = "FOUND"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    QUARANTINED = "QUARANTINED"


class ClaimKind(str, Enum):
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    CAUSAL_HYPOTHESIS = "CAUSAL_HYPOTHESIS"
    HABIT_CANDIDATE = "HABIT_CANDIDATE"


@dataclass(frozen=True, slots=True)
class ObservedTransition:
    receipt_id: str
    session: str
    revision: int
    sequence: int
    source_state: int
    action: int
    target_state: int
    kind: str
    digest: str


@dataclass(frozen=True, slots=True)
class Claim:
    claim_id: str
    kind: ClaimKind
    source_state: int
    action: int
    target_state: int

    def __post_init__(self) -> None:
        if not self.claim_id or not isinstance(self.kind, ClaimKind):
            raise EvidenceError("unqualified or untyped claim")
        _state(self.source_state)
        _state(self.target_state)
        _action(self.action)


@dataclass(frozen=True, slots=True)
class Query:
    start: int
    actions: tuple[int, int]

    def __post_init__(self) -> None:
        _state(self.start)
        if (
            not isinstance(self.actions, tuple) or len(self.actions) != 2
        ):
            raise EvidenceError("two actions required")
        for action in self.actions:
            _action(action)


@dataclass(frozen=True, slots=True)
class PathResult:
    status: Status
    final_state: int | None
    receipt_ids: tuple[str, ...]
    query_work: int
    build_work: int


def _state(state: int) -> None:
    if type(state) is not int or not 0 <= state < STATES:
        raise EvidenceError("state must be exact integer 0..15")


def _action(action: int) -> None:
    if type(action) is not int or action not in ACTIONS:
        raise EvidenceError("action must be exact binary integer")


class ResetWorld:
    """Private deterministic World evaluator; every Action is a real fixture event."""

    def __init__(self, session: str = "b5-world") -> None:
        if not isinstance(session, str) or not session or session.strip() != session:
            raise EvidenceError("invalid session")
        self.session = session
        self.revision = 0
        self._regime = 0
        self._sequence = 0
        self._ledger: dict[str, ObservedTransition] = {}

    def act(self, state: int, action: int) -> ObservedTransition:
        """Execute exactly one independently reset simulation Action."""
        _state(state)
        _action(action)
        next_state = (5 * state + 1 + 3 * action + 4 * self._regime) % STATES
        self._sequence += 1
        identity = f"{self.session}:step:{self._sequence}"
        payload = (
            identity, self.session, self.revision, self._sequence,
            state, action, next_state, "OBSERVED_TRANSITION",
        )
        digest = sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()
        receipt = ObservedTransition(
            identity, self.session, self.revision, self._sequence,
            state, action, next_state, "OBSERVED_TRANSITION", digest,
        )
        self._ledger[identity] = receipt
        return receipt

    def verify(self, receipt: ObservedTransition) -> None:
        # Object identity is experiment-local source ownership, NOT
        # cross-process/serialized cryptographic attestation.
        if (
            not isinstance(receipt, ObservedTransition)
            or receipt.kind != "OBSERVED_TRANSITION"
            or self._ledger.get(receipt.receipt_id) is not receipt
        ):
            raise EvidenceError("receipt not attested by this exact World instance")

    def change_regime(self, *, announce: bool) -> None:
        self._regime ^= 1
        if announce:
            self.revision += 1

    def rollout(
        self, start: int, actions: tuple[int, int],
    ) -> tuple[ObservedTransition, ObservedTransition]:
        """Evaluator-only actual two-step reset trajectory, never training input."""
        q = Query(start, actions)
        first = self.act(q.start, q.actions[0])
        second = self.act(first.target_state, q.actions[1])
        if second.source_state != first.target_state:
            raise EvidenceError("World did not preserve sequential rollout continuity")
        return first, second

    @property
    def action_count(self) -> int:
        return self._sequence


class Corpus:
    """Source-qualified, immutable view of shared receipts + untrusted claims."""

    def __init__(
        self, world: ResetWorld, receipts: tuple[ObservedTransition, ...],
        claims: tuple[Claim, ...], *, session: str, revision: int,
    ) -> None:
        if not isinstance(world, ResetWorld):
            raise EvidenceError("source World witness required")
        if world.session != session or world.revision != revision:
            raise EvidenceError("snapshot currentness mismatch")
        if not isinstance(receipts, tuple) or not isinstance(claims, tuple):
            raise EvidenceError("immutable receipt/claim tuples required")
        self.world, self.session, self.revision = world, session, revision
        self.receipts = receipts
        self.claims = claims
        self.common_validation_work = len(receipts) + len(claims)
        receipt_ids: set[str] = set()
        observed: dict[tuple[int, int], ObservedTransition] = {}
        for receipt in receipts:
            world.verify(receipt)
            _state(receipt.source_state)
            _state(receipt.target_state)
            _action(receipt.action)
            if receipt.session != session or receipt.revision != revision:
                raise EvidenceError("stale or cross-session observed transition")
            if receipt.receipt_id in receipt_ids:
                raise EvidenceError("duplicate observed receipt identity")
            receipt_ids.add(receipt.receipt_id)
            key = (receipt.source_state, receipt.action)
            if key in observed:
                raise EvidenceError("same-key duplicate or contradictory World outcome")
            observed[key] = receipt
        claim_ids: set[str] = set()
        for claim in claims:
            if not isinstance(claim, Claim) or claim.claim_id in claim_ids:
                raise EvidenceError("duplicate or invalid untrusted claim")
            claim_ids.add(claim.claim_id)
            # Claims have neither source-ledger receipts nor observed status.
        self.validated = MappingProxyType(observed)


class ReadOnlyIndex:
    """Four algorithmic representations of IDENTICAL evidence, no semantic owner."""

    def __init__(
        self, corpus: Corpus, mode: str, *, quarantined: bool = False,
    ) -> None:
        if not isinstance(corpus, Corpus) or mode not in MODES:
            raise EvidenceError("invalid corpus/retrieval method")
        self.corpus = corpus
        self.mode = mode
        self.quarantined = quarantined
        self.build_work = 0 if mode == "full_scan" else len(corpus.receipts)
        self._index: Mapping[object, object]
        if mode == "tags":
            self._index = MappingProxyType({
                (r.source_state, r.action, r.kind): r for r in corpus.receipts
            })
        elif mode == "flat":
            self._index = MappingProxyType({
                (r.source_state, r.action): r for r in corpus.receipts
            })
        elif mode == "typed_graph":
            grouped: dict[int, list[ObservedTransition]] = {}
            for r in corpus.receipts:
                grouped.setdefault(r.source_state, []).append(r)
            self._index = MappingProxyType({
                key: tuple(sorted(items, key=lambda x: x.action))
                for key, items in grouped.items()
            })
        else:
            self._index = MappingProxyType({})

    def query(
        self, q: Query, *, session: str, revision: int,
    ) -> PathResult:
        if not isinstance(q, Query):
            raise EvidenceError("query is not typed")
        if self.quarantined:
            return PathResult(Status.QUARANTINED, None, (), 0, self.build_work)
        corpus = self.corpus
        if (
            session != corpus.session or revision != corpus.revision
            or corpus.world.revision != corpus.revision
            or corpus.world.session != corpus.session
        ):
            return PathResult(Status.STALE, None, (), 0, self.build_work)
        state = q.start
        witness_ids: list[str] = []
        work = 0
        for action in q.actions:
            receipt: ObservedTransition | None = None
            if self.mode == "full_scan":
                for candidate in corpus.receipts:
                    work += 1
                    if candidate.source_state == state and candidate.action == action:
                        receipt = candidate
            elif self.mode == "tags":
                work += 1
                receipt = self._index.get((state, action, "OBSERVED_TRANSITION"))
            elif self.mode == "flat":
                work += 1
                receipt = self._index.get((state, action))
            else:
                for candidate in self._index.get(state, ()):
                    work += 1
                    if candidate.action == action and candidate.kind == "OBSERVED_TRANSITION":
                        receipt = candidate
                        break
                if state not in self._index:
                    work += 1  # explicitly count absent adjacency read
            if receipt is None:
                return PathResult(Status.UNKNOWN, None, tuple(witness_ids),
                                  work, self.build_work)
            # Corpus verification already proved exact ownership. Recheck typed
            # relation at access; claims are not included in *any* index.
            if receipt.kind != "OBSERVED_TRANSITION":
                raise EvidenceError("hypothesis edge cannot ground World transition")
            witness_ids.append(receipt.receipt_id)
            state = receipt.target_state
        return PathResult(Status.FOUND, state, tuple(witness_ids),
                          work, self.build_work)

    def reconsider_after_observation(
        self, observed: ObservedTransition,
    ) -> ReadOnlyIndex:
        """Return a quarantined new view on one source-qualified mismatch."""
        corpus = self.corpus
        corpus.world.verify(observed)
        previous = corpus.validated.get((observed.source_state, observed.action))
        if (
            observed.session != corpus.session
            or observed.revision != corpus.revision
            or previous is None
            or previous.target_state != observed.target_state
        ):
            return ReadOnlyIndex(corpus, self.mode, quarantined=True)
        return self


def make_claims() -> tuple[Claim, ...]:
    return tuple(
        Claim(
            f"claim:{state}:{action}:{kind.value}",
            kind, state, action, (state + 7 + action) % STATES,
        )
        for state in range(STATES)
        for action in ACTIONS
        for kind in (ClaimKind.ASSOCIATED_WITH, ClaimKind.CAUSAL_HYPOTHESIS)
    )


def sample_world(world: ResetWorld) -> tuple[ObservedTransition, ...]:
    return tuple(world.act(state, action)
                 for state in range(STATES) for action in ACTIONS)


def queries() -> tuple[Query, ...]:
    return tuple(
        query
        for s in range(STATES)
        for query in (
            Query(s, (s % 2, (s // 2) % 2)),
            Query(s, (1 - s % 2, 1 - (s // 2) % 2)),
        )
    )


def evaluate(
    world: ResetWorld, corpus: Corpus,
    *, before_world_action_count: int | None = None,
) -> dict[str, object]:
    """Score each arm on identical frozen queries; rollout is evaluator only."""
    if before_world_action_count is None:
        before_world_action_count = world.action_count
    views = {mode: ReadOnlyIndex(corpus, mode) for mode in MODES}
    totals = {
        mode: {"found": 0, "correct": 0, "wrong": 0, "unknown": 0,
               "lookup_work": 0, "build_work": views[mode].build_work,
               "witnesses": []}
        for mode in MODES
    }
    for q in queries():
        # Freeze predictions before evaluator executes rollout; all methods
        # use exactly the same snapshots and receipts.
        outputs = {
            mode: view.query(q, session=world.session, revision=world.revision)
            for mode, view in views.items()
        }
        first, second = world.rollout(q.start, q.actions)
        actual = second.target_state
        assert first.target_state == second.source_state
        for mode, output in outputs.items():
            count = totals[mode]
            count["lookup_work"] += output.query_work
            count["witnesses"].append(output.receipt_ids)
            if output.status is Status.FOUND:
                count["found"] += 1
                if output.final_state == actual:
                    count["correct"] += 1
                else:
                    count["wrong"] += 1
            else:
                count["unknown"] += 1
    for mode in MODES:
        totals[mode]["total_work"] = (
            totals[mode]["lookup_work"] + totals[mode]["build_work"]
        )
    # Keep cost of source filtering distinct, once and same for every arm.
    reliable = all(totals[m]["correct"] == len(queries())
                   and totals[m]["wrong"] == 0 for m in MODES)
    equivalent = all(
        totals[m]["witnesses"] == totals[MODES[0]]["witnesses"] for m in MODES[1:]
    )
    tagged = totals["tags"]["total_work"]
    flat = totals["flat"]["total_work"]
    graph = totals["typed_graph"]["total_work"]
    if not reliable or not equivalent:
        classification = "UNDETERMINED"
    elif graph < tagged and graph < flat:
        classification = "BOUNDED_GRAPH_RETRIEVAL_GAIN"
    else:
        classification = "GRAPH_NOT_JUSTIFIED"
    return {
        "classification": classification,
        "common_validation_work": corpus.common_validation_work,
        "queries": len(queries()),
        "world_rollout_actions": world.action_count - before_world_action_count,
        "equal_provenance_paths": equivalent,
        "arm_results": totals,
    }


def run_fixture() -> dict[str, object]:
    world = ResetWorld()
    observed = sample_world(world)
    claims = make_claims()
    corpus = Corpus(world, observed, claims, session=world.session, revision=0)
    original = evaluate(world, corpus)
    old_views = {mode: ReadOnlyIndex(corpus, mode) for mode in MODES}
    world.change_regime(announce=True)
    stale = sum(
        old_views[mode].query(queries()[0], session=world.session,
                              revision=world.revision).status is Status.STALE
        for mode in MODES
    )
    start = world.action_count
    next_receipts = sample_world(world)
    training_actions = world.action_count - start
    new_corpus = Corpus(world, next_receipts, claims,
                        session=world.session, revision=world.revision)
    recovery = evaluate(world, new_corpus)
    # Silent switch is not an observable revision increment. Detect it from
    # a *new actual Action* mismatch and quarantine the old observed mapping.
    world.change_regime(announce=False)
    witness = world.act(0, 0)
    quarantine = sum(
        ReadOnlyIndex(new_corpus, mode).reconsider_after_observation(
            witness
        ).query(queries()[0], session=world.session,
                revision=world.revision).status is Status.QUARANTINED
        for mode in MODES
    )
    return {
        "initial": original,
        "announced_shift_stale_views": stale,
        "shift_training_actions": training_actions,
        "recovery": recovery,
        "silent_shift_quarantined_views": quarantine,
        "claim_edge_count": len(claims),
        "qualified_one_step_receipts": len(observed),
    }


if __name__ == "__main__":
    print(json.dumps(run_fixture(), indent=2, sort_keys=True))
