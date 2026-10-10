"""B17: offline mixed-source correlation and exact 4/5 decision-value stopping.

Purely EXPERIMENTAL. P and S are distinct Python simulator instances,
NOT authenticated independent sensors. The full native S10 commit gates an
experiment-only S11 rule; direct cheap vote counts use identical evidence.
No actual production S11 acquisition or physical Minecraft attestation.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from experiments.ac_b_b11_governed_habit import (
    CONTEXTS,
    CurrentWorld,
    ObservedOutcome,
    cue_for,
    empty_repertoire,
)
from experiments.ac_b_b16_quorum import PairedTrial
from relay_self.habit import (
    CueFeature,
    HabitRepertoire,
    HabitRule,
    HabitSelectionStatus,
    select_habit,
)
from relay_self.learning import (
    FeedbackDirection,
    LearningCommitResult,
    LearningFeedback,
    LearningPreferenceState,
    LearningUpdateAuthority,
    LearningUpdateRule,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance

N_TRIALS = 5
THRESHOLD = 4
PLANS = {
    "SINGLE": ("P", "P", "P", "P", "P"),
    "DIVERSIFIED": ("P", "P", "P", "S", "S"),
}
PRIMARY_PAIR_COST = 1
SECONDARY_PAIR_COST = 2
DECISION_REWARD = 5
WRONG_PENALTY = -5
S10_TEST_CONTROL_UNIT_PER_RULE = 1
RULE = LearningUpdateRule("b17-exact-source-vote-step", version=1, step=1)


class InvalidB17Evidence(ValueError):
    """Source, action, quorum or independent test-owner mismatch."""


@dataclass(frozen=True, slots=True)
class ChannelTrial:
    trial_index: int
    channel: str
    source: CurrentWorld
    pair: PairedTrial


class MixedSourceLedger:
    """Local object-identity verification against EACH issuing source owner."""

    def __init__(
        self, sources: dict[str, CurrentWorld],
        plan: tuple[str, ...],
        a: int,
        b: int,
        trials: tuple[ChannelTrial, ...],
    ) -> None:
        if (a, b) not in CONTEXTS or plan not in PLANS.values():
            raise InvalidB17Evidence("prespecified cue and source plan required")
        if type(trials) is not tuple or len(trials) > N_TRIALS:
            raise InvalidB17Evidence("bounded original source trial tuple required")
        if set(sources) != {"P", "S"} or sources["P"] is sources["S"]:
            raise InvalidB17Evidence("distinct local P and S sources required")
        if (
            not all(isinstance(world, CurrentWorld) for world in sources.values())
            or sources["P"].session == sources["S"].session
        ):
            raise InvalidB17Evidence("separate local source sessions required")
        self.sources = sources
        self.plan = plan
        self.a = a
        self.b = b
        self.trials = trials
        self.revisions = {
            channel: source.revision for channel, source in sources.items()
        }
        self.seen: set[str] = set()
        for i, entry in enumerate(trials):
            if (
                not isinstance(entry, ChannelTrial)
                or entry.trial_index != i
                or entry.channel != plan[i]
                or entry.source is not sources[plan[i]]
                or not isinstance(entry.pair, PairedTrial)
                or entry.pair.trial != i
            ):
                raise InvalidB17Evidence("trial/channel source mismatch")
            self._validate_trial(entry)

    def _validate_trial(self, entry: ChannelTrial) -> None:
        w = entry.source
        for action, event in enumerate((entry.pair.action0, entry.pair.action1)):
            if (
                not isinstance(event, ObservedOutcome)
                or not w.observed(event)
                or event.session != w.session
                or event.revision != self.revisions[entry.channel]
                or (event.a, event.b, event.action) != (self.a, self.b, action)
                or type(event.success) is not bool
                or event.kind != "OBSERVED_ACTION"
            ):
                raise InvalidB17Evidence("unissued or incorrectly bound source Action")
            key = f"{entry.channel}:{event.event_id}"
            if key in self.seen:
                raise InvalidB17Evidence("source Action replayed")
            self.seen.add(key)

    def current(self) -> None:
        for channel, w in self.sources.items():
            if w.revision != self.revisions[channel]:
                raise InvalidB17Evidence("stale source revision")
        for entry in self.trials:
            if not entry.source.observed(entry.pair.action0) or not (
                entry.source.observed(entry.pair.action1)
            ):
                raise InvalidB17Evidence("source observation no longer registered")

    @property
    def votes(self) -> tuple[int | None, ...]:
        self.current()
        return tuple(entry.pair.vote() for entry in self.trials)

    @property
    def fingerprint(self) -> str:
        self.current()
        data = {
            "kind": "B17_LOCAL_CHANNEL_SOURCE_PAIRS",
            "cue": (self.a, self.b),
            "plan": self.plan,
            "owners": [
                (channel, world.session, self.revisions[channel], id(world))
                for channel, world in sorted(self.sources.items())
            ],
            "observations": [
                (e.trial_index, e.channel, e.pair.action0.event_id,
                 e.pair.action0.success, e.pair.action1.event_id,
                 e.pair.action1.success)
                for e in self.trials
            ],
        }
        return hashlib.sha256(
            json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def decision(self) -> tuple[bool, int | None]:
        """Exact worst-case decision determinacy under the fixed 4/5 rule."""
        votes = self.votes
        t = len(votes)
        if votes.count(0) >= THRESHOLD:
            return True, 0
        if votes.count(1) >= THRESHOLD:
            return True, 1
        possible_remaining = N_TRIALS - t
        if max(votes.count(0), votes.count(1)) + possible_remaining < THRESHOLD:
            return True, None
        return (t == N_TRIALS), None


@dataclass(frozen=True, slots=True)
class B17Draft:
    repertoire_id: str
    expected_revision: int
    source_fingerprint: str
    cue: tuple[int, int]
    winner: int
    rule: HabitRule


@dataclass(frozen=True, slots=True)
class B17TestHabitGrant:
    """Test-only and same-process forgeable, NOT a product authority."""

    repertoire_id: str
    expected_revision: int
    source_fingerprint: str
    cue: tuple[int, int]
    winner: int
    granted: bool


def expected_s10_state(ledger: MixedSourceLedger) -> LearningPreferenceState:
    return LearningPreferenceState(
        target_id=f"b17-preference-{ledger.a}-{ledger.b}",
        value=1, minimum=0, maximum=2, revision=0,
        origin_provenance=Provenance("b17.test-native-s10-owner", ledger.fingerprint),
    )


def expected_s10_feedback(ledger: MixedSourceLedger) -> LearningFeedback:
    terminal, winner = ledger.decision()
    if not terminal or winner is None:
        raise InvalidB17Evidence("only terminal definite decision has S10 feedback")
    return LearningFeedback(
        feedback_id=f"b17-{ledger.fingerprint}",
        target_id=expected_s10_state(ledger).target_id,
        direction=FeedbackDirection.INCREASE if winner else FeedbackDirection.DECREASE,
        provenance=Provenance("b17.test-source-winner", ledger.fingerprint),
        consequence_ref=f"b17-original-source-{ledger.fingerprint}",
    )


def commit_native_s10(
    ledger: MixedSourceLedger, authority: LearningUpdateAuthority | None,
) -> LearningCommitResult:
    state = expected_s10_state(ledger)
    feedback = expected_s10_feedback(ledger)
    proposal = propose_learning_update(state, feedback, RULE)
    return commit_learning_update(
        state, proposal, authority,
        provenance=Provenance("b17.test-explicit-s10-commit", ledger.fingerprint),
    )


def propose_s11_rule(
    ledger: MixedSourceLedger,
    owner: HabitRepertoire,
    native: LearningCommitResult | None,
) -> B17Draft:
    if not isinstance(owner, HabitRepertoire):
        raise InvalidB17Evidence("native frozen S11 typed repertoire required")
    terminal, winner = ledger.decision()
    if not terminal or winner is None:
        raise InvalidB17Evidence("no source-certified 4/5 Action winner")
    if not isinstance(native, LearningCommitResult):
        raise InvalidB17Evidence("actual S10 committed owner required")
    state = expected_s10_state(ledger)
    feedback = expected_s10_feedback(ledger)
    proposal = propose_learning_update(state, feedback, RULE)
    if (
        native.previous_state != state
        or native.proposal != proposal
        or native.new_state.value != (2 if winner else 0)
        or native.new_state.revision != 1
        or native.new_state.last_update != native.record
        or native.record.feedback_id != feedback.feedback_id
        or native.record.feedback_provenance != feedback.provenance
        or native.record.previous_revision != 0
        or native.record.committed_revision != 1
        or native.record.rule_id != RULE.rule_id
        or native.record.rule_version != RULE.version
        or not native.record.authority_id
    ):
        raise InvalidB17Evidence("native S10 source/owner commit mismatch")
    rule = HabitRule(
        habit_id=f"b17-habit-{ledger.a}{ledger.b}-{ledger.fingerprint[:16]}",
        cue_requirements=(CueFeature("a", ledger.a), CueFeature("b", ledger.b)),
        candidate_ref=f"action:{winner}", priority=10,
        provenance=Provenance("b17.test-mixed-source", ledger.fingerprint),
    )
    return B17Draft(
        repertoire_id=owner.repertoire_id,
        expected_revision=owner.revision,
        source_fingerprint=ledger.fingerprint,
        cue=(ledger.a, ledger.b),
        winner=winner,
        rule=rule,
    )


def test_grant(draft: B17Draft) -> B17TestHabitGrant:
    return B17TestHabitGrant(
        draft.repertoire_id, draft.expected_revision,
        draft.source_fingerprint, draft.cue, draft.winner, True,
    )


def retain_experiment_s11(
    ledger: MixedSourceLedger,
    owner: HabitRepertoire,
    native: LearningCommitResult,
    draft: B17Draft,
    grant: B17TestHabitGrant | None,
) -> HabitRepertoire:
    if not isinstance(draft, B17Draft):
        raise InvalidB17Evidence("B17 typed draft required")
    if draft != propose_s11_rule(ledger, owner, native):
        raise InvalidB17Evidence("source or retained owner proposal mismatch")
    if not isinstance(grant, B17TestHabitGrant) or grant != test_grant(draft):
        raise InvalidB17Evidence("separate exact B17 test-only Habit grant required")
    if select_habit(
        owner, cue_for(ledger.a, ledger.b, trial="b17-collision-check")
    ).status is not HabitSelectionStatus.NO_MATCH:
        raise InvalidB17Evidence("retained rule collides with prior Habit")
    return HabitRepertoire(
        repertoire_id=owner.repertoire_id, revision=owner.revision + 1,
        rules=owner.rules + (draft.rule,), provenance=owner.provenance,
    )


def execute_trial(
    sources: dict[str, CurrentWorld],
    cue: tuple[int, int],
    trial: int,
    channel: str,
    *,
    correlated: bool,
) -> ChannelTrial:
    if channel not in ("P", "S") or trial not in range(N_TRIALS) or cue not in CONTEXTS:
        raise InvalidB17Evidence("not a prespecified World action request")
    world = sources[channel]
    reported = []
    for action in (0, 1):
        item = world.act(*cue, action)
        if correlated and channel == "P" and cue == (0, 0):
            # Identical *source-channel* systematic error across repeated
            # attempts. Reported success remains locally registered, not TRUE.
            from dataclasses import replace

            item = replace(item, success=not item.success)
            world._issued[item.event_id] = item
        reported.append(item)
    return ChannelTrial(trial, channel, world, PairedTrial(trial, *reported))


def run_scenario(
    *, correlated: bool, diversified: bool, adaptive: bool,
) -> dict[str, object]:
    label = (
        f"{'correlated' if correlated else 'clean'}-"
        f"{'diversified' if diversified else 'single'}-"
        f"{'adaptive' if adaptive else 'fixed'}"
    )
    sources = {
        "P": CurrentWorld(session=f"b17-{label}-P"),
        "S": CurrentWorld(session=f"b17-{label}-S"),
    }
    plan = PLANS["DIVERSIFIED" if diversified else "SINGLE"]
    owner = empty_repertoire(label=f"b17-owner-{label}")
    initial_owner = owner
    flat: dict[tuple[int, int], int] = {}
    consumed: dict[str, int] = {"P": 0, "S": 0}
    trials_per_cue: dict[str, int] = {}
    votes_per_cue: dict[str, tuple[int | None, ...]] = {}
    native_commits = 0
    s11_test_grants = 0
    for cue in CONTEXTS:
        records: list[ChannelTrial] = []
        for trial, channel in enumerate(plan):
            records.append(
                execute_trial(sources, cue, trial, channel, correlated=correlated)
            )
            consumed[channel] += 1
            ledger = MixedSourceLedger(sources, plan, *cue, tuple(records))
            terminal, _ = ledger.decision()
            if adaptive and terminal:
                break
        ledger = MixedSourceLedger(sources, plan, *cue, tuple(records))
        terminal, winner = ledger.decision()
        assert terminal
        trials_per_cue[f"{cue[0]}{cue[1]}"] = len(records)
        votes_per_cue[f"{cue[0]}{cue[1]}"] = ledger.votes
        if winner is None:
            continue
        flat[cue] = winner
        authority = LearningUpdateAuthority(
            authority_id=f"b17-native-{label}-{cue[0]}{cue[1]}",
            target_id=expected_s10_state(ledger).target_id,
            provenance=Provenance("b17.test-owner-approval", ledger.fingerprint),
        )
        native = commit_native_s10(ledger, authority)
        native_commits += 1
        draft = propose_s11_rule(ledger, owner, native)
        owner = retain_experiment_s11(
            ledger, owner, native, draft, test_grant(draft)
        )
        s11_test_grants += 1

    actual_from_S11: dict[tuple[int, int], int] = {}
    # Real read-only frozen S11 choice for each NEW nuisance ID.
    for index in range(3):
        for cue in CONTEXTS:
            chosen = select_habit(owner, cue_for(*cue, trial=f"b17-heldout-{index}"))
            if index == 0 and chosen.status is HabitSelectionStatus.SELECTED:
                assert chosen.selected_candidate_ref is not None
                actual_from_S11[cue] = int(
                    chosen.selected_candidate_ref.split(":")[1]
                )
            if chosen.status is HabitSelectionStatus.SELECTED:
                assert chosen.selected_candidate_ref == f"action:{flat[cue]}"
            else:
                assert chosen.status is HabitSelectionStatus.NO_MATCH
                assert cue not in flat

    assert actual_from_S11 == flat
    # World oracle accessed for scoring AFTER both policies choose.
    correct = sum(
        int(sources["P"].heldout_score(*cue, action))
        for cue, action in flat.items()
    )
    wrong = len(flat) - correct
    world_actions = sum(w.actions_executed for w in sources.values())
    cost_units = consumed["P"] + 2 * consumed["S"]
    reward = 5 * correct - 5 * wrong
    return {
        "scenario": label,
        "source_paired_trials": sum(consumed.values()),
        "actual_world_action_executions": world_actions,
        "primary_pairs": consumed["P"],
        "secondary_pairs": consumed["S"],
        "source_pair_cost_units": cost_units,
        "source_net_utility_units": reward - cost_units,
        "s10_s11_control_units_extra": native_commits,
        "s10_s11_net_utility_with_control_units": (
            reward - cost_units - native_commits
        ),
        "correct": correct,
        "wrong": wrong,
        "covered": len(flat),
        "abstained": len(CONTEXTS) - len(flat),
        "actual_native_s10_commits": native_commits,
        "separate_s11_test_grants": s11_test_grants,
        "retained_s11_rules": len(owner.rules),
        "old_owner_unmodified": (
            initial_owner.revision == 0 and initial_owner.rules == ()
        ),
        "habit_matches_cheap_adaptive_or_fixed_count": actual_from_S11 == flat,
        "trials_per_cue": trials_per_cue,
        "votes_per_cue": votes_per_cue,
        "new_relevant_cues": False,
        "physical_source_independence_qualified": False,
        "no_actual_energy_latency_measurements": True,
    }


def run_b17_comparison() -> dict[str, object]:
    reports: dict[str, dict[str, object]] = {}
    for correlated in (False, True):
        for diversified in (False, True):
            for adaptive in (True, False):
                r = run_scenario(
                    correlated=correlated,
                    diversified=diversified,
                    adaptive=adaptive,
                )
                reports[r["scenario"]] = r
    return {
        "terminal": "B17_BOUNDED_EXPERIMENT_ONLY_DECISION_VALUE_AND_SOURCE_VARIETY",
        "reports": reports,
        "matched_exogenous_source_schedule": True,
        "adaptive_S10_S11_and_cheap_count_share_exact_source_actions": True,
        "fixed_five_uses_separate_matched_source_world_instances": True,
        "no_production_Habit_owner": True,
        "no_autonomous_L2_to_L1": True,
    }
