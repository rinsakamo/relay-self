"""B14: matched-source OFFLINE S10-gated S11 vs minimal learned tag index.

Both policies see precisely the same source-issued simulator Actions. The S10
stage is an imposed admission criterion; it does NOT discover the World winner.
The S11 acquisition and HMAC grant remain experiments-only, not product owner
authority or a physical Minecraft observation.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field

from experiments.ac_b_b11_governed_habit import (
    CONTEXTS,
    CurrentWorld,
    ObservedOutcome,
    QualifiedHabitView,
    QualifiedLedger,
    cue_for,
    empty_repertoire,
)
from experiments.ac_b_b12_independent_grant import (
    IndependentS11Admission,
    OfflineIndependentS11Issuer,
)
from experiments.ac_b_b13_shared_world import (
    commit_existing_s10,
    exact_source_pair,
    initial_s10_state,
    propose_same_source_s11,
)
from relay_self.habit import HabitRepertoire
from relay_self.learning import LearningUpdateAuthority
from relay_self.provenance import Provenance

CHECKPOINTS = (0, 2, 4, 6, 8)


@dataclass(frozen=True, slots=True)
class ComparisonCheckpoint:
    source_revision: int
    observed_actions: int
    habit_covered: int
    habit_correct: int
    tag_covered: int
    tag_correct: int
    context_count: int = 4


@dataclass(slots=True)
class EpochComparison:
    """One explicitly source-scoped training run. No previous-epoch retention."""

    world: CurrentWorld
    source_revision: int
    owner: HabitRepertoire
    _grant_secret: bytes
    observed: list[ObservedOutcome] = field(default_factory=list)
    learned_tags: dict[tuple[int, int], int] = field(default_factory=dict)
    s10_native_commit_count: int = 0
    s11_signed_grant_count: int = 0
    s11_retained_updates: int = 0
    tag_inserts: int = 0
    evaluation_tag_lookups: int = 0
    evaluation_habit_rule_scan_upper_bound: int = 0

    def __post_init__(self) -> None:
        if self.world.revision != self.source_revision:
            raise ValueError("World source epoch changed before training")
        self._issuer = OfflineIndependentS11Issuer(self._grant_secret)
        self._gate = IndependentS11Admission(self._grant_secret)
        self.view = QualifiedHabitView(
            self.owner, self.world.session, self.source_revision,
        )

    @classmethod
    def create(cls, world: CurrentWorld) -> EpochComparison:
        return cls(
            world=world, source_revision=world.revision,
            owner=empty_repertoire(label=f"b14-owner-source-{world.revision}"),
            _grant_secret=secrets.token_bytes(32),
        )

    def _ensure_epoch(self) -> None:
        if self.world.revision != self.source_revision:
            raise ValueError("World epoch is stale for BOTH trained arms")

    def learn_pair(self, a: int, b: int) -> None:
        """Exactly two World Actions are shared; neither arm adds its own."""
        self._ensure_epoch()
        if (a, b) not in CONTEXTS or (a, b) in self.learned_tags:
            raise ValueError("unexpected/duplicate cue pair")
        new = (self.world.act(a, b, 0), self.world.act(a, b, 1))
        self.observed.extend(new)
        ledger = QualifiedLedger(self.world, tuple(self.observed))
        pair = exact_source_pair(ledger, a, b)
        # Baseline reads *exactly the same* source ledger. It is intentionally
        # computed without using the S10 decision or S11 learned rules.
        tag_action, ids = ledger.chosen(a, b)
        assert ids == pair.evidence_ids and tag_action == pair.winner
        self.learned_tags[a, b] = tag_action
        self.tag_inserts += 1

        # Genuine S10 API: independently granted owner transition for THIS
        # source pair. The scalar update gates, but does not infer, the winner.
        authority = LearningUpdateAuthority(
            authority_id=f"b14-s10-scope-{self.source_revision}-{a}-{b}",
            target_id=pair.target_id, granted=True,
            provenance=Provenance("b14.test-s10-approval", pair.digest),
        )
        actual_s10 = commit_existing_s10(
            ledger, pair, initial_s10_state(pair), authority,
        )
        self.s10_native_commit_count += 1
        draft = propose_same_source_s11(
            self.owner, ledger, pair, actual_s10,
        )

        # Different, independently supplied experimental S11 authorization.
        signed = self._issuer.grant(draft)
        updated = self._gate.commit(self.owner, draft, ledger, signed)
        self.s11_signed_grant_count += 1
        self.s11_retained_updates += 1
        self.owner = updated
        self.view = QualifiedHabitView(
            updated, self.world.session, self.source_revision,
        )

    def lookup_tag(self, a: int, b: int) -> int | None:
        self._ensure_epoch()
        self.evaluation_tag_lookups += 1
        return self.learned_tags.get((a, b))

    def score(self, trial: str) -> ComparisonCheckpoint:
        """Score independently AFTER read-only selections; abstain != right."""
        self._ensure_epoch()
        habit_covered = habit_correct = tag_covered = tag_correct = 0
        for a, b in CONTEXTS:
            cue = cue_for(a, b, trial=trial)
            status, candidate = self.view.select(cue, self.world)
            self.evaluation_habit_rule_scan_upper_bound += (
                len(self.owner.rules) * 2
            )
            tag_action = self.lookup_tag(a, b)
            if status == "selected":
                assert candidate is not None
                habit_action = int(candidate.split(":")[1])
                habit_covered += 1
                habit_correct += int(
                    self.world.heldout_score(a, b, habit_action)
                )
            elif status != "no_match":
                raise ValueError("unexpected S11 Habit selection status")
            if tag_action is not None:
                tag_covered += 1
                tag_correct += int(
                    self.world.heldout_score(a, b, tag_action)
                )
        return ComparisonCheckpoint(
            source_revision=self.source_revision,
            observed_actions=len(self.observed),
            habit_covered=habit_covered, habit_correct=habit_correct,
            tag_covered=tag_covered, tag_correct=tag_correct,
        )


def run_matched_comparison() -> dict[str, object]:
    """Three ANNOUNCED epochs 0 -> 1 -> 0; same two actions/context each."""
    world = CurrentWorld()
    epoch_reports: list[dict[str, object]] = []
    prior: EpochComparison | None = None
    for round_index in range(3):
        if round_index:
            assert prior is not None
            world.change_rule(announce=True)
            # A and B must reject stale source-scoped state before any new
            # World Action. Native S11 read-only selector itself is unscoped.
            assert prior.view.select(
                cue_for(0, 0, trial=f"stale-{round_index}"),
                world,
            ) == ("STALE", None)
            try:
                prior.lookup_tag(0, 0)
            except ValueError:
                pass
            else:
                raise AssertionError("cheap tags improperly reused old World epoch")
        current = EpochComparison.create(world)
        checkpoints: list[ComparisonCheckpoint] = [current.score("prefix-0")]
        for pair_index, (a, b) in enumerate(CONTEXTS, start=1):
            current.learn_pair(a, b)
            checkpoints.append(current.score(f"prefix-{2 * pair_index}"))
        assert tuple(x.observed_actions for x in checkpoints) == CHECKPOINTS
        assert world.actions_executed == (round_index + 1) * 8
        final_heldout = [current.score(f"heldout-{j}") for j in range(3)]
        assert all(
            x.habit_covered == x.tag_covered == 4
            and x.habit_correct == x.tag_correct == 4
            for x in final_heldout
        )
        epoch_reports.append({
            "world_revision": world.revision,
            "regime_index": round_index,
            "world_actions_this_epoch": len(current.observed),
            "checkpoints": [
                {
                    "actions": c.observed_actions,
                    "habit_covered": c.habit_covered,
                    "habit_correct": c.habit_correct,
                    "tag_covered": c.tag_covered,
                    "tag_correct": c.tag_correct,
                } for c in checkpoints
            ],
            "world_actions_to_full_coverage_habit": next(
                c.observed_actions for c in checkpoints
                if c.habit_correct == c.habit_covered == 4
            ),
            "world_actions_to_full_coverage_tag": next(
                c.observed_actions for c in checkpoints
                if c.tag_correct == c.tag_covered == 4
            ),
            "heldout_nuisance_count": 12,
            "habit_heldout_correct": sum(c.habit_correct for c in final_heldout),
            "tag_heldout_correct": sum(c.tag_correct for c in final_heldout),
            "native_s10_commits": current.s10_native_commit_count,
            "independent_s11_signed_test_grants": current.s11_signed_grant_count,
            "experiment_s11_retained_updates": current.s11_retained_updates,
            "cheap_tag_inserts": current.tag_inserts,
            "checkpoint_and_heldout_tag_lookups": current.evaluation_tag_lookups,
            "s11_rule_feature_checks_upper_bound": (
                current.evaluation_habit_rule_scan_upper_bound
            ),
            "repertoire_revision": current.owner.revision,
        })
        prior = current
    assert world.actions_executed == 24
    equal = all(
        e["world_actions_to_full_coverage_habit"] == 8
        and e["world_actions_to_full_coverage_tag"] == 8
        and e["habit_heldout_correct"] == 12
        and e["tag_heldout_correct"] == 12
        and e["native_s10_commits"] == 4
        and e["independent_s11_signed_test_grants"] == 4
        and e["experiment_s11_retained_updates"] == 4
        and e["cheap_tag_inserts"] == 4
        for e in epoch_reports
    )
    return {
        "classification": (
            "MATCHED_WORLD_SAMPLE_AND_ANNOUNCED_READAPTATION"
            if equal else "NOT_QUALIFIED"
        ),
        "world_actions_total": world.actions_executed,
        "source_revisions": [e["world_revision"] for e in epoch_reports],
        "regimes": [0, 1, 0],
        "epochs": epoch_reports,
        "native_s10_commits_total": sum(
            e["native_s10_commits"] for e in epoch_reports
        ),
        "separate_s11_test_grants_total": sum(
            e["independent_s11_signed_test_grants"] for e in epoch_reports
        ),
        "cheap_tag_inserts_total": sum(
            e["cheap_tag_inserts"] for e in epoch_reports
        ),
        "new_relevant_cues_tested": False,
        "physical_world": False,
        "latency_or_energy_measured": False,
    }
