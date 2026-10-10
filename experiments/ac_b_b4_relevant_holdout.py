"""AC-B B4: frozen prospective relevant-cue learning discriminator (offline only).

Production S10/S11/S17 and sibling Draft PRs are deliberately not imported.
This fixture models neither an LLM nor an authorized Minecraft Action.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from hashlib import sha256

FAMILIES = ("PARITY3", "OR3", "MAJORITY3", "AND3")
TRAIN = ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
VALIDATE = ((1, 1, 0),)
HELDOUT = ((0, 1, 1), (1, 0, 1), (1, 1, 1))


class UnqualifiedEvidence(ValueError):
    """Any invalid evidence fails closed; it cannot form a policy."""


@dataclass(frozen=True)
class Cue:
    a: int
    b: int
    c: int

    def __post_init__(self) -> None:
        if any(type(bit) is not int or bit not in (0, 1)
               for bit in (self.a, self.b, self.c)):
            raise UnqualifiedEvidence("cue features must be binary ints")

    @property
    def bits(self) -> tuple[int, int, int]:
        return self.a, self.b, self.c


@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    session: str
    revision: int
    sequence: int
    cue: Cue
    action: int
    success: bool
    kind: str
    digest: str


def _evaluate(family: str, cue: Cue) -> int:
    if family == "PARITY3":
        return cue.a ^ cue.b ^ cue.c
    if family == "OR3":
        return int(bool(cue.a or cue.b or cue.c))
    if family == "MAJORITY3":
        return int(cue.a + cue.b + cue.c >= 2)
    if family == "AND3":
        return int(bool(cue.a and cue.b and cue.c))
    raise UnqualifiedEvidence("unknown World/hypothesis family")


@dataclass(frozen=True)
class Rule:
    family: str
    flip: int

    def __post_init__(self) -> None:
        if self.family not in FAMILIES or type(self.flip) is not int or self.flip not in (0, 1):
            raise UnqualifiedEvidence("invalid rule")

    def select(self, cue: Cue) -> int:
        if not isinstance(cue, Cue):
            raise UnqualifiedEvidence("invalid cue")
        return _evaluate(self.family, cue) ^ self.flip


HYPOTHESES = tuple(Rule(family, flip) for family in FAMILIES for flip in (0, 1))


class ResetWorld:
    """Offline evaluator with actual, individually witnessed simulated Actions.

    Every act is a deterministic independent reset trial. The rule is private
    evaluator state; neither learner is passed the target family or flip.
    """

    def __init__(
        self, family: str, flip: int, *, session: str = "ac-b4",
    ) -> None:
        if not session or session.strip() != session:
            raise UnqualifiedEvidence("invalid session")
        self._rule = Rule(family, flip)
        self.session = session
        self.revision = 0
        self._ledger: dict[str, Receipt] = {}
        self._sequence = 0

    def act(self, cue: Cue, action: int) -> Receipt:
        if not isinstance(cue, Cue) or type(action) is not int or action not in (0, 1):
            raise UnqualifiedEvidence("invalid Action")
        self._sequence += 1
        receipt_id = f"{self.session}:observed:{self._sequence}"
        success = action == self._rule.select(cue)
        payload = (
            receipt_id, self.session, self.revision, self._sequence,
            *cue.bits, action, success, "OBSERVED",
        )
        digest = sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()
        receipt = Receipt(
            receipt_id, self.session, self.revision, self._sequence,
            cue, action, success, "OBSERVED", digest,
        )
        self._ledger[receipt_id] = receipt
        return receipt

    def verify(self, receipt: Receipt) -> None:
        if (
            not isinstance(receipt, Receipt) or receipt.kind != "OBSERVED"
            or self._ledger.get(receipt.receipt_id) != receipt
        ):
            raise UnqualifiedEvidence("receipt is not exact observed World evidence")

    def flip_rule(self, *, announce_revision: bool) -> None:
        self._rule = Rule(self._rule.family, self._rule.flip ^ 1)
        if announce_revision:
            self.revision += 1

    @property
    def count(self) -> int:
        return self._sequence


def observe(world: ResetWorld, contexts: tuple[tuple[int, int, int], ...]) -> tuple[Receipt, ...]:
    """Both actions actually executed in independent reset trials."""
    return tuple(world.act(Cue(*bits), action) for bits in contexts for action in (0, 1))


def _qualified_labels(
    world: ResetWorld, receipts: tuple[Receipt, ...],
    contexts: tuple[tuple[int, int, int], ...],
) -> dict[tuple[int, int, int], int]:
    if len(set(contexts)) != len(contexts) or len(receipts) != 2 * len(contexts):
        raise UnqualifiedEvidence("invalid predefined split or missing Action")
    records: dict[tuple[int, int, int], dict[int, Receipt]] = {}
    seen: set[str] = set()
    for receipt in receipts:
        world.verify(receipt)
        if (
            receipt.receipt_id in seen
            or receipt.session != world.session
            or receipt.revision != world.revision
            or receipt.cue.bits not in contexts
        ):
            raise UnqualifiedEvidence("duplicate, wrong-source, stale or split leakage")
        seen.add(receipt.receipt_id)
        group = records.setdefault(receipt.cue.bits, {})
        if receipt.action in group:
            raise UnqualifiedEvidence("repeated Action for one training cue")
        group[receipt.action] = receipt
    if set(records) != set(contexts):
        raise UnqualifiedEvidence("required cue coverage incomplete")
    labels = {}
    for context, actions in records.items():
        if set(actions) != {0, 1} or sum(int(r.success) for r in actions.values()) != 1:
            raise UnqualifiedEvidence("must observe exactly one success from two Actions")
        labels[context] = next(action for action, r in actions.items() if r.success)
    return labels


def _check_disjoint(train: tuple[Receipt, ...], qualification: tuple[Receipt, ...]) -> None:
    if set(r.receipt_id for r in train) & set(r.receipt_id for r in qualification):
        raise UnqualifiedEvidence("training and validation are not independent receipts")


def version_space(
    world: ResetWorld, train: tuple[Receipt, ...],
    qualification: tuple[Receipt, ...] = (),
) -> tuple[Rule, ...]:
    """Full eight-hypothesis source-only enumerator: a strong cheap null arm."""
    labels = _qualified_labels(world, train, TRAIN)
    if qualification:
        _check_disjoint(train, qualification)
        labels.update(_qualified_labels(world, qualification, VALIDATE))
    return tuple(rule for rule in HYPOTHESES if all(
        rule.select(Cue(*bits)) == expected for bits, expected in labels.items()
    ))


def cheap_analytic_rule(
    world: ResetWorld, train: tuple[Receipt, ...],
    qualification: tuple[Receipt, ...],
) -> Rule | None:
    """Separate simple analytic rule comparator, no retained Habit state.

    Its cost is a fixed handful of labeled cue comparisons after the same
    World evidence verification and is deliberately strong, not a strawman.
    """
    _check_disjoint(train, qualification)
    t = _qualified_labels(world, train, TRAIN)
    q = _qualified_labels(world, qualification, VALIDATE)
    baseline = t[(0, 0, 0)]
    singles = {t[bits] for bits in TRAIN if bits != (0, 0, 0)}
    if len(singles) != 1:
        return None
    singleton = next(iter(singles))
    pair = q[(1, 1, 0)]
    if singleton != baseline:
        family = "PARITY3" if pair == baseline else "OR3"
    else:
        family = "MAJORITY3" if pair != baseline else "AND3"
    candidate = Rule(family, baseline)
    if any(candidate.select(Cue(*bits)) != target for bits, target in {**t, **q}.items()):
        return None
    return candidate


@dataclass(frozen=True)
class GuardedHabitCandidate:
    """Compiled non-authoritative memory-to-selection representation."""

    rule: Rule
    session: str
    revision: int
    training_ids: tuple[str, ...]
    qualification_ids: tuple[str, ...]
    quarantined: bool = False

    def select(self, session: str, revision: int, cue: Cue) -> int | None:
        if self.quarantined or session != self.session or revision != self.revision:
            return None
        return self.rule.select(cue)

    def reconsider(self, world: ResetWorld, observed: Receipt) -> GuardedHabitCandidate:
        world.verify(observed)
        predicted = self.select(observed.session, observed.revision, observed.cue)
        if predicted is None or (observed.action == predicted) != observed.success:
            return replace(self, quarantined=True)
        return self


def compile_habit(
    world: ResetWorld, train: tuple[Receipt, ...],
    qualification: tuple[Receipt, ...],
) -> GuardedHabitCandidate | None:
    space = version_space(world, train, qualification)
    if len(space) != 1:
        return None
    return GuardedHabitCandidate(
        space[0], world.session, world.revision,
        tuple(sorted(r.receipt_id for r in train)),
        tuple(sorted(r.receipt_id for r in qualification)),
    )


def exact_full_cue_replay(train: tuple[Receipt, ...], cue: Cue) -> int | None:
    """A genuinely exact full cue case lookup; unseen combinations abstain."""
    seen = {r.cue.bits: r.action for r in train if r.success}
    return seen.get(cue.bits)


def run_fixture() -> dict[str, object]:
    totals = {arm: {"success": 0, "coverage": 0} for arm in (
        "no_retention", "exact_full_cue", "cheap_rule", "compiled_habit",
    )}
    families = {}
    stale_count = 0
    recovered = 0
    quarantines = 0
    train_only_spaces = []
    requalify_actions = 0
    for family in FAMILIES:
        for flip in (0, 1):
            label = f"{family}:{flip}"
            world = ResetWorld(family, flip, session=f"b4-{label}")
            train = observe(world, TRAIN)
            qualification = observe(world, VALIDATE)
            ambiguity = version_space(world, train)
            cheap = cheap_analytic_rule(world, train, qualification)
            compiled = compile_habit(world, train, qualification)
            if compiled is None or cheap is None:
                raise UnqualifiedEvidence("prospective candidate not identified")
            train_only_spaces.append(len(ambiguity))
            per_case = {}
            for bits in HELDOUT:
                cue = Cue(*bits)
                choices = {
                    "no_retention": 0,
                    "exact_full_cue": exact_full_cue_replay(train, cue),
                    "cheap_rule": cheap.select(cue),
                    "compiled_habit": compiled.select(world.session, world.revision, cue),
                }
                per_case["".join(str(x) for x in bits)] = choices
                for arm, action in choices.items():
                    if action is None:
                        continue
                    outcome = world.act(cue, action)
                    totals[arm]["coverage"] += 1
                    totals[arm]["success"] += int(outcome.success)
            world.flip_rule(announce_revision=True)
            stale_count += sum(
                compiled.select(world.session, world.revision, Cue(*bits)) is None
                for bits in HELDOUT
            )
            before = world.count
            new_train = observe(world, TRAIN)
            new_qualification = observe(world, VALIDATE)
            requalify_actions += world.count - before
            renewed = compile_habit(world, new_train, new_qualification)
            if renewed is None:
                raise UnqualifiedEvidence("shifted World could not be requalified")
            recovered += sum(
                world.act(Cue(*bits), renewed.select(world.session, world.revision,
                                                     Cue(*bits))).success
                for bits in HELDOUT
            )
            # SILENT second flip: no revision signal; one real failure must
            # invalidate the current candidate. Recovery is NOT credited.
            world.flip_rule(announce_revision=False)
            cue = Cue(*HELDOUT[0])
            selected = renewed.select(world.session, world.revision, cue)
            mismatch = world.act(cue, selected)
            if not mismatch.success:
                stopped = renewed.reconsider(world, mismatch)
                quarantines += int(
                    stopped.select(world.session, world.revision, cue) is None
                )
            families[label] = {"train_only_hypotheses": len(ambiguity),
                               "heldout_choices": per_case}
    return {
        "classification": (
            "CHEAP_RULE_SUFFICIENT_FOR_RELEVANT_HOLDOUT"
            if totals["cheap_rule"] == totals["compiled_habit"]
            else "UNDETERMINED"
        ),
        "heldout": totals,
        "heldout_contexts_per_world": len(HELDOUT),
        "world_families": len(families),
        "train_only_hypothesis_sizes": train_only_spaces,
        "stale_abstentions": stale_count,
        "fresh_requalification_actions": requalify_actions,
        "recovered_successes": recovered,
        "silent_mismatch_quarantines": quarantines,
        "families": families,
    }


if __name__ == "__main__":
    print(json.dumps(run_fixture(), ensure_ascii=False, sort_keys=True, indent=2))
