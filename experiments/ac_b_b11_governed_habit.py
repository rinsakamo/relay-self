"""B11: offline World-experience -> explicitly governed S11 Habit repertoire copy.

This is an experiment-only owner adapter. Actual S11 intentionally exposes
select_habit (READ_ONLY), not a retained acquisition/commit API. No B7/B10
cryptographic/physical source attestation or S10-to-S11 authority is implied.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    HabitSelectionStatus,
    select_habit,
)
from relay_self.provenance import Provenance

CONTEXTS = ((0, 0), (0, 1), (1, 0), (1, 1))
WORLD_SOURCE = "b11.offline-world.source"
ACTIONS = (0, 1)


class UnqualifiedHabitAcquisition(ValueError):
    """No source-qualified and explicitly authorized retained Habit change."""


@dataclass(slots=True)
class CurrentWorld:
    """Test oracle; not a production World evidence or trust issuer."""

    session: str = "b11-sim-world"
    revision: int = 0
    _rule: int = 0
    _count: int = 0
    _issued: dict[str, ObservedOutcome] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.session or type(self.revision) is not int or self.revision < 0:
            raise UnqualifiedHabitAcquisition("invalid World scope")

    def act(self, a: int, b: int, action: int) -> ObservedOutcome:
        for name, value in (("a", a), ("b", b), ("action", action)):
            if type(value) is not int or value not in (0, 1):
                raise UnqualifiedHabitAcquisition(f"{name} must be binary")
        self._count += 1
        item = ObservedOutcome(
            event_id=f"{self.session}:event:{self._count}",
            session=self.session,
            revision=self.revision,
            a=a,
            b=b,
            action=action,
            success=bool(action == (a ^ b ^ self._rule)),
            kind="OBSERVED_ACTION",
        )
        self._issued[item.event_id] = item
        return item

    @property
    def actions_executed(self) -> int:
        return self._count

    def observed(self, outcome: ObservedOutcome) -> bool:
        return (
            isinstance(outcome, ObservedOutcome)
            and self._issued.get(outcome.event_id) is outcome
            and outcome.kind == "OBSERVED_ACTION"
        )

    def change_rule(self, *, announce: bool) -> None:
        self._rule ^= 1
        if announce:
            self.revision += 1

    def heldout_score(self, a: int, b: int, selected_action: int) -> bool:
        """Independent score ONLY after inference; not available to learner."""
        return selected_action == (a ^ b ^ self._rule)


@dataclass(frozen=True, slots=True)
class ObservedOutcome:
    event_id: str
    session: str
    revision: int
    a: int
    b: int
    action: int
    success: bool
    kind: str


def observe_training(world: CurrentWorld) -> tuple[ObservedOutcome, ...]:
    """Execute BOTH real simulator Actions for every exact source cue."""
    return tuple(world.act(a, b, action) for a, b in CONTEXTS for action in ACTIONS)


class QualifiedLedger:
    """Read-only snapshot; source identity is an external test-World registry.

    Object identity checks are only local process evidence, NOT serialized
    attestation or production source security.
    """

    def __init__(
        self, world: CurrentWorld, outcomes: tuple[ObservedOutcome, ...],
    ) -> None:
        if not isinstance(world, CurrentWorld) or not isinstance(outcomes, tuple):
            raise UnqualifiedHabitAcquisition("trusted test-World ledger required")
        self.world = world
        self.session = world.session
        self.revision = world.revision
        pairs: dict[tuple[int, int], dict[int, ObservedOutcome]] = {}
        seen: set[str] = set()
        for item in outcomes:
            if not world.observed(item):
                raise UnqualifiedHabitAcquisition("World did not issue this outcome")
            if item.session != self.session or item.revision != self.revision:
                raise UnqualifiedHabitAcquisition("stale or foreign observed outcome")
            if type(item.success) is not bool or item.kind != "OBSERVED_ACTION":
                raise UnqualifiedHabitAcquisition("unqualified outcome semantics")
            if item.event_id in seen:
                raise UnqualifiedHabitAcquisition("duplicate source event")
            seen.add(item.event_id)
            pair = pairs.setdefault((item.a, item.b), {})
            if item.action in pair:
                raise UnqualifiedHabitAcquisition("conflicting same-cue Action outcome")
            pair[item.action] = item
        self.rows: Mapping[tuple[int, int], Mapping[int, ObservedOutcome]] = (
            MappingProxyType({
                k: MappingProxyType(v) for k, v in pairs.items()
            })
        )

    def chosen(
        self, a: int, b: int,
    ) -> tuple[int, tuple[str, str]]:
        if (
            self.session != self.world.session
            or self.revision != self.world.revision
        ):
            raise UnqualifiedHabitAcquisition("source epoch stale")
        pair = self.rows.get((a, b), {})
        if set(pair) != {0, 1}:
            raise UnqualifiedHabitAcquisition("both real competing Actions required")
        if sum(bool(item.success) for item in pair.values()) != 1:
            raise UnqualifiedHabitAcquisition("winner not uniquely observed")
        for action, item in pair.items():
            if not self.world.observed(item):
                raise UnqualifiedHabitAcquisition("World witness was lost")
        winner = next(a for a, item in pair.items() if item.success)
        return winner, tuple(sorted(item.event_id for item in pair.values()))

    def observed_contradiction(self, item: ObservedOutcome) -> bool:
        if not self.world.observed(item) or (
            item.session != self.session or item.revision != self.revision
        ):
            raise UnqualifiedHabitAcquisition("cannot compare unauthenticated events")
        old = self.rows.get((item.a, item.b), {}).get(item.action)
        if old is None:
            raise UnqualifiedHabitAcquisition("no prior same Action to contrast")
        return old.success != item.success


@dataclass(frozen=True, slots=True)
class HabitAcquisitionDraft:
    proposal_id: str
    owner_id: str
    expected_revision: int
    source_session: str
    source_revision: int
    a: int
    b: int
    observed_ids: tuple[str, str]
    rule: HabitRule


@dataclass(frozen=True, slots=True)
class ExperimentHabitAuthority:
    """Explicit test-only permission; NOT an S11 production authority token."""

    authority_id: str
    owner_id: str
    expected_revision: int
    proposal_id: str
    observed_ids: tuple[str, str]
    source_session: str
    source_revision: int
    granted: bool
    provenance: Provenance


@dataclass(frozen=True, slots=True)
class QualifiedHabitView:
    """Source-epoch-scoped wrapper; raw existing S11 selection is NOT scoped."""

    repertoire: HabitRepertoire
    session: str
    source_revision: int

    def select(self, cue: HabitCue, world: CurrentWorld) -> tuple[str, str | None]:
        if world.session != self.session or world.revision != self.source_revision:
            return ("STALE", None)
        choice = select_habit(self.repertoire, cue)
        return (choice.status.value, choice.selected_candidate_ref)


def cue_for(a: int, b: int, *, trial: str) -> HabitCue:
    return HabitCue(
        cue_id=f"b11-{trial}-{a}-{b}",
        features=(
            CueFeature("a", a),
            CueFeature("b", b),
            CueFeature("nuisance", trial),
        ),
        provenance=Provenance("b11.offline-cue", f"{trial}:{a}:{b}"),
    )


def propose_habit(
    owner: HabitRepertoire,
    ledger: QualifiedLedger,
    a: int,
    b: int,
) -> HabitAcquisitionDraft:
    if not isinstance(owner, HabitRepertoire) or not isinstance(
        ledger, QualifiedLedger
    ):
        raise UnqualifiedHabitAcquisition("S11 owner and World ledger required")
    winner, ids = ledger.chosen(a, b)
    new = HabitRule(
        habit_id=f"b11-rule-r{ledger.revision}-{a}-{b}",
        cue_requirements=(CueFeature("a", a), CueFeature("b", b)),
        candidate_ref=f"action:{winner}",
        priority=10,
        provenance=Provenance(WORLD_SOURCE, ",".join(ids)),
    )
    return HabitAcquisitionDraft(
        proposal_id=f"b11-proposal-r{ledger.revision}-{a}-{b}-{owner.revision}",
        owner_id=owner.repertoire_id,
        expected_revision=owner.revision,
        source_session=ledger.session,
        source_revision=ledger.revision,
        a=a,
        b=b,
        observed_ids=ids,
        rule=new,
    )


def grant_test_authority(
    draft: HabitAcquisitionDraft, *, granted: bool = True,
) -> ExperimentHabitAuthority:
    """Explicit caller issuance in TEST fixture, no cryptographic protection."""
    return ExperimentHabitAuthority(
        authority_id=f"b11-test-grant:{draft.proposal_id}",
        owner_id=draft.owner_id,
        expected_revision=draft.expected_revision,
        proposal_id=draft.proposal_id,
        observed_ids=draft.observed_ids,
        source_session=draft.source_session,
        source_revision=draft.source_revision,
        granted=granted,
        provenance=Provenance("b11.test-owner", draft.proposal_id),
    )


def commit_experiment_habit(
    owner: HabitRepertoire,
    draft: HabitAcquisitionDraft,
    authority: ExperimentHabitAuthority | None,
    ledger: QualifiedLedger,
) -> HabitRepertoire:
    """ONLY an experiment's explicit S11 typed snapshot copy, never prod."""

    if not isinstance(draft, HabitAcquisitionDraft):
        raise UnqualifiedHabitAcquisition("qualified proposed Habit required")
    recomputed = propose_habit(owner, ledger, draft.a, draft.b)
    if recomputed != draft:
        raise UnqualifiedHabitAcquisition("source-bound proposal/owner mismatch")
    if (
        not isinstance(authority, ExperimentHabitAuthority)
        or authority.granted is not True
        or authority.owner_id != owner.repertoire_id
        or authority.expected_revision != owner.revision
        or authority.proposal_id != draft.proposal_id
        or authority.observed_ids != draft.observed_ids
        or authority.source_session != ledger.session
        or authority.source_revision != ledger.revision
    ):
        raise UnqualifiedHabitAcquisition("separate exact test Habit authority required")
    if any(rule.habit_id == draft.rule.habit_id for rule in owner.rules):
        raise UnqualifiedHabitAcquisition("duplicate retained Habit rule")
    # Refuse to override even a less-specific existing habit on this cue.
    choice = select_habit(owner, cue_for(draft.a, draft.b, trial="collision-check"))
    if choice.status is not HabitSelectionStatus.NO_MATCH:
        raise UnqualifiedHabitAcquisition("preexisting Habit conflict needs adjudication")
    return HabitRepertoire(
        repertoire_id=owner.repertoire_id,
        revision=owner.revision + 1,
        rules=owner.rules + (draft.rule,),
        provenance=owner.provenance,
    )


def cheap_flat_tags(ledger: QualifiedLedger) -> Mapping[tuple[int, int], int]:
    """Exactly the same qualified source training data as Habit acquisition."""
    return MappingProxyType({
        (a, b): ledger.chosen(a, b)[0] for a, b in CONTEXTS
    })


def empty_repertoire(label: str = "b11-retained-habit") -> HabitRepertoire:
    return HabitRepertoire(
        repertoire_id=label, revision=0, rules=(),
        provenance=Provenance("b11.test-owner", "initial-empty"),
    )


def qualify_fixture() -> dict[str, object]:
    world = CurrentWorld()
    ledger = QualifiedLedger(world, observe_training(world))
    owner = empty_repertoire()
    initial_owner = owner
    for a, b in CONTEXTS:
        draft = propose_habit(owner, ledger, a, b)
        owner = commit_experiment_habit(
            owner, draft, grant_test_authority(draft), ledger,
        )
    view = QualifiedHabitView(owner, world.session, world.revision)
    flat = cheap_flat_tags(ledger)
    test_inputs = tuple(
        (a, b, f"heldout-{round_id}") for round_id in range(3)
        for a, b in CONTEXTS
    )
    habit_correct = 0
    flat_correct = 0
    selected = 0
    for a, b, trial in test_inputs:
        status, selected_ref = view.select(cue_for(a, b, trial=trial), world)
        if status == HabitSelectionStatus.SELECTED.value:
            selected += 1
            chosen = int(selected_ref.split(":")[1])
            habit_correct += int(world.heldout_score(a, b, chosen))
        flat_correct += int(world.heldout_score(a, b, flat[a, b]))
    qualified = (
        world.actions_executed == 8 and initial_owner.rules == ()
        and initial_owner.revision == 0 and owner.revision == 4
        and len(owner.rules) == 4 and selected == habit_correct == flat_correct == 12
    )
    return {
        "classification": (
            "EXPERIMENT_ONLY_GOVERNED_HABIT_ACQUISITION_QUALIFIED"
            if qualified else "UNDETERMINED"
        ),
        "training_world_actions": world.actions_executed,
        "new_s11_rules": len(owner.rules),
        "original_owner_rules": len(initial_owner.rules),
        "new_owner_revision": owner.revision,
        "heldout_nuisance_variants": len(test_inputs),
        "heldout_relevant_contexts_novel": False,
        "habit_selected": selected,
        "habit_correct": habit_correct,
        "cheap_tag_correct": flat_correct,
        "habit_rule_feature_checks_upper_bound": len(test_inputs) * len(owner.rules) * 2,
        "cheap_tag_dictionary_lookups": len(test_inputs),
        "no_action_issue_by_selection": True,
    }
