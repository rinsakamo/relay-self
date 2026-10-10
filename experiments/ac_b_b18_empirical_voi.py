"""B18 OFFLINE empirical marginal VOI, not native L2 cognition or physical world.

Eight fully executed exploratory traces train four-action empirical Q tables.
The real frozen S10 scalar owner commits independently record historical
feedback, but DO NOT calculate Q or cause its learned policy. A second,
plain forgeable test grant makes an immutable S11 repertoire containing the
same cheapest trained decision table. S11 read-only selection is exercised.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction

from experiments.ac_b_b11_governed_habit import (
    CONTEXTS,
    CurrentWorld,
    cue_for,
    empty_repertoire,
)
from experiments.ac_b_b17_source_value import (
    ChannelTrial,
    execute_trial,
)
from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    HabitSelectionStatus,
    select_habit,
)
from relay_self.learning import (
    FeedbackDirection,
    LearningFeedback,
    LearningPreferenceState,
    LearningUpdateAuthority,
    LearningUpdateRule,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance

OPTIONS = ("STOP", "ABSTAIN", "QUERY_P", "QUERY_S")
RISKS = {"HIGH": -15, "LOW": -5}
COST = {"P": 1, "S": 2}
CORRECT_REWARD = 5
ABSTAIN_REWARD = -1
STEP = LearningUpdateRule("b18-native-historical-feedback-step", version=1, step=1)


class InvalidB18Source(ValueError):
    """Fail closed on non-issued source receipt or experiment owner mismatch."""


@dataclass(frozen=True, slots=True)
class TracedCase:
    label: str
    cue: tuple[int, int]
    sources: dict[str, CurrentWorld]
    first: ChannelTrial
    second: ChannelTrial
    optional_primary: ChannelTrial
    optional_secondary: ChannelTrial

    def verify(self) -> None:
        if self.cue not in CONTEXTS or set(self.sources) != {"P", "S"}:
            raise InvalidB18Source("unrecognized context or source")
        if (
            self.sources["P"] is self.sources["S"]
            or self.sources["P"].session == self.sources["S"].session
        ):
            raise InvalidB18Source("distinct offline channel owners required")
        seen: set[tuple[str, str]] = set()
        for source_key, trial_index, entry in (
            ("P", 0, self.first), ("P", 1, self.second),
            ("P", 2, self.optional_primary), ("S", 2, self.optional_secondary),
        ):
            w = self.sources[source_key]
            if (
                entry.source is not w
                or entry.channel != source_key
                or entry.trial_index != trial_index
                or entry.pair.trial != trial_index
            ):
                raise InvalidB18Source("wrong source channel or trial")
            for expected_action, item in enumerate(
                (entry.pair.action0, entry.pair.action1)
            ):
                if (
                    not w.observed(item)
                    or item.session != w.session
                    or item.revision != w.revision
                    or (item.a, item.b, item.action)
                    != (self.cue[0], self.cue[1], expected_action)
                    or type(item.success) is not bool
                    or item.kind != "OBSERVED_ACTION"
                ):
                    raise InvalidB18Source("unissued, cloned or stale Action source")
                source_identity = source_key, item.event_id
                if source_identity in seen:
                    raise InvalidB18Source("duplicate/replayed Action receipt")
                seen.add(source_identity)

    @property
    def digest(self) -> str:
        self.verify()
        entries = (self.first, self.second, self.optional_primary,
                   self.optional_secondary)
        return hashlib.sha256(json.dumps({
            "cue": self.cue, "label": self.label,
            "sources": [
                (channel, world.session, world.revision, id(world))
                for channel, world in sorted(self.sources.items())
            ],
            "receipts": [
                (e.trial_index, e.channel,
                 e.pair.action0.event_id, e.pair.action0.success,
                 e.pair.action1.event_id, e.pair.action1.success)
                for e in entries
            ],
        }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @property
    def prefix_vote(self) -> int | None:
        self.verify()
        v0, v1 = self.first.pair.vote(), self.second.pair.vote()
        return v0 if v0 is not None and v0 == v1 else None


def sources_for(label: str) -> dict[str, CurrentWorld]:
    return {
        "P": CurrentWorld(session=f"b18-{label}-P"),
        "S": CurrentWorld(session=f"b18-{label}-S"),
    }


def training_case(*, cue: tuple[int, int], correlated: bool) -> TracedCase:
    name = f"train-{'correlated' if correlated else 'clean'}-{cue[0]}{cue[1]}"
    worlds = sources_for(name)
    case = TracedCase(
        name, cue, worlds,
        execute_trial(worlds, cue, 0, "P", correlated=correlated),
        execute_trial(worlds, cue, 1, "P", correlated=correlated),
        execute_trial(worlds, cue, 2, "P", correlated=correlated),
        execute_trial(worlds, cue, 2, "S", correlated=correlated),
    )
    case.verify()
    assert sum(w.actions_executed for w in worlds.values()) == 8
    return case


def source_action(
    prefix: int | None,
    option: str,
    third: int | None = None,
) -> int | None:
    """Policy receives reported votes ONLY. Contradiction means abstention."""
    if option not in OPTIONS:
        raise InvalidB18Source("unknown decision candidate")
    if option == "ABSTAIN" or prefix not in (0, 1):
        return None
    if option == "STOP":
        return prefix
    if third not in (0, 1):
        return None
    return prefix if third == prefix else None


def realized_incremental_utility(
    case: TracedCase, option: str, *, wrong_penalty: int,
) -> int:
    """TRAINING adjudicator; truth is read only AFTER reported options fixed."""
    prefix = case.prefix_vote
    third = (
        case.optional_primary.pair.vote() if option == "QUERY_P"
        else case.optional_secondary.pair.vote() if option == "QUERY_S"
        else None
    )
    proposed = source_action(prefix, option, third)
    extra_cost = COST["P"] if option == "QUERY_P" else (
        COST["S"] if option == "QUERY_S" else 0
    )
    if proposed is None:
        reward = ABSTAIN_REWARD
    else:
        reward = (
            CORRECT_REWARD
            if case.sources["P"].heldout_score(*case.cue, proposed)
            else wrong_penalty
        )
    return reward - extra_cost


@dataclass(frozen=True, slots=True)
class TrainingReceipt:
    trace_digest: str
    cases: tuple[TracedCase, ...]
    native_s10_commits: int
    native_s10_final_values: tuple[int, int]
    native_s10_final_revisions: tuple[int, int]

    def verify(self) -> None:
        if len(self.cases) != 8 or self.native_s10_commits != 8:
            raise InvalidB18Source("actual eight-event training owner required")
        for case in self.cases:
            case.verify()
        digest = hashlib.sha256(
            "|".join(c.digest for c in self.cases).encode()
        ).hexdigest()
        if digest != self.trace_digest:
            raise InvalidB18Source("training source lineage mismatch")


def _initial_owner(vote: int) -> LearningPreferenceState:
    return LearningPreferenceState(
        target_id=f"b18-historical-stop-correctness-vote-{vote}",
        value=0, minimum=-32, maximum=32, revision=0,
        origin_provenance=Provenance("b18.explicit-s10-owner", f"vote-{vote}"),
    )


def train_actual_s10_feedback(
    cases: tuple[TracedCase, ...],
) -> TrainingReceipt:
    """Native S10 actual commits, supervised by POST-observation toy score."""
    state = {0: _initial_owner(0), 1: _initial_owner(1)}
    count = 0
    for case in cases:
        vote = case.prefix_vote
        if vote is None:
            raise InvalidB18Source("training prefix lacks two agreeing votes")
        # This TRAINING-ONLY label is revealed by toy World post-outcome
        # scoring. It is not S17 or a physical autonomous observation.
        correct = case.sources["P"].heldout_score(*case.cue, vote)
        feedback = LearningFeedback(
            feedback_id=f"b18-history-{case.digest}",
            target_id=state[vote].target_id,
            direction=(
                FeedbackDirection.INCREASE if correct
                else FeedbackDirection.DECREASE
            ),
            provenance=Provenance("b18.test-scored-history", case.digest),
            consequence_ref=f"b18-training-world-{case.digest}",
        )
        proposal = propose_learning_update(state[vote], feedback, STEP)
        authority = LearningUpdateAuthority(
            authority_id=f"b18-native-owner-{case.digest}",
            target_id=state[vote].target_id,
            granted=True,
            provenance=Provenance("b18.explicit-native-S10-grant", case.digest),
        )
        committed = commit_learning_update(
            state[vote], proposal, authority,
            provenance=Provenance("b18.actual-native-S10-update", case.digest),
        )
        assert committed.previous_state == state[vote]
        assert committed.new_state.revision == state[vote].revision + 1
        state[vote] = committed.new_state
        count += 1
    return TrainingReceipt(
        trace_digest=hashlib.sha256(
            "|".join(c.digest for c in cases).encode()
        ).hexdigest(),
        cases=cases,
        native_s10_commits=count,
        native_s10_final_values=(state[0].value, state[1].value),
        native_s10_final_revisions=(state[0].revision, state[1].revision),
    )


@dataclass(frozen=True, slots=True)
class EmpiricalTable:
    risk: str
    trace_digest: str
    votes: tuple[int, int]
    choices: tuple[str, str]
    mean_scores: tuple[tuple[tuple[str, Fraction], ...], ...]


def learn_empirical_table(
    receipt: TrainingReceipt, *, risk: str,
) -> EmpiricalTable:
    receipt.verify()
    if risk not in RISKS:
        raise InvalidB18Source("pre-fixed HIGH/LOW cost required")
    choice: list[str] = []
    all_scores: list[tuple[tuple[str, Fraction], ...]] = []
    for vote in (0, 1):
        bucket = tuple(
            case for case in receipt.cases if case.prefix_vote == vote
        )
        if not bucket:
            raise InvalidB18Source("missing relevant source vote training data")
        scores = tuple(
            (option, Fraction(sum(
                realized_incremental_utility(
                    case, option, wrong_penalty=RISKS[risk]
                ) for case in bucket
            ), len(bucket)))
            for option in OPTIONS
        )
        # Frozen OPTIONS gives stable tie-breaking, no outcome-informed
        # selection of rules or parameters after HOLDOUT.
        choice.append(max(scores, key=lambda x: x[1])[0])
        all_scores.append(scores)
    return EmpiricalTable(
        risk=risk, trace_digest=receipt.trace_digest,
        votes=(0, 1), choices=tuple(choice),
        mean_scores=tuple(all_scores),
    )


@dataclass(frozen=True, slots=True)
class B18TestGrant:
    owner_id: str
    owner_revision: int
    trace_digest: str
    vote: int
    option: str
    granted: bool


def grant_experiment_only(
    owner: HabitRepertoire, table: EmpiricalTable, vote: int,
) -> B18TestGrant:
    return B18TestGrant(
        owner.repertoire_id, owner.revision, table.trace_digest,
        vote, table.choices[vote], True,
    )


def retain_test_policy(
    owner: HabitRepertoire,
    receipt: TrainingReceipt,
    table: EmpiricalTable,
    vote: int,
    grant: B18TestGrant | None,
) -> HabitRepertoire:
    receipt.verify()
    if not isinstance(owner, HabitRepertoire) or not isinstance(
        table, EmpiricalTable
    ) or vote not in (0, 1):
        raise InvalidB18Source("actual S11 owner and complete learned table required")
    if table != learn_empirical_table(receipt, risk=table.risk):
        raise InvalidB18Source("empirical Q table/source mismatch")
    required = grant_experiment_only(owner, table, vote)
    if not isinstance(grant, B18TestGrant) or grant != required:
        raise InvalidB18Source("separate exact B18 experimental Habit grant required")
    selector_cue = HabitCue(
        cue_id="b18-conflict-check", features=(CueFeature("p_vote", vote),),
        provenance=Provenance("b18.test-cue", "owner-collision"),
    )
    if select_habit(owner, selector_cue).status is not HabitSelectionStatus.NO_MATCH:
        raise InvalidB18Source("prior retained Habit conflicts")
    rule = HabitRule(
        habit_id=f"b18-learned-{table.risk}-{vote}-{table.trace_digest[:16]}",
        cue_requirements=(CueFeature("p_vote", vote),),
        candidate_ref=table.choices[vote], priority=10,
        provenance=Provenance("b18.test-native-training-Q", table.trace_digest),
    )
    return HabitRepertoire(
        repertoire_id=owner.repertoire_id, revision=owner.revision + 1,
        rules=owner.rules + (rule,), provenance=owner.provenance,
    )


def selected_s11_option(
    owner: HabitRepertoire, vote: int, *, trial: str,
) -> str | None:
    cue = HabitCue(
        cue_id=f"b18-heldout-{trial}", features=(
            CueFeature("p_vote", vote), CueFeature("nuisance", trial),
        ),
        provenance=Provenance("b18.offline-new-cue", trial),
    )
    match = select_habit(owner, cue)
    if match.status is HabitSelectionStatus.NO_MATCH:
        return None
    if match.status is not HabitSelectionStatus.SELECTED:
        raise InvalidB18Source("ambiguous native S11 retained choice")
    if match.selected_candidate_ref not in OPTIONS:
        raise InvalidB18Source("unknown Habit decision candidate")
    return match.selected_candidate_ref


def heldout_episode(
    table: EmpiricalTable,
    owner: HabitRepertoire,
) -> dict[str, object]:
    correct = wrong = abstained = 0
    stop_correct = stop_wrong = 0
    queried_secondary = queried_primary = 0
    actual_world_actions = 0
    active_cost = 0
    all_cases: list[dict[str, object]] = []
    for correlated in (False, True):
        for a, b in CONTEXTS:
            name = (
                f"eval-{table.risk}-"
                f"{'corr' if correlated else 'clean'}-{a}{b}"
            )
            worlds = sources_for(name)
            first = execute_trial(
                worlds, (a, b), 0, "P", correlated=correlated
            )
            second = execute_trial(
                worlds, (a, b), 1, "P", correlated=correlated
            )
            # Issued original P prefix receipts are checked; unobserved
            # optional third source is NOT read or fabricated.
            for entry in (first, second):
                assert entry.source.observed(entry.pair.action0)
                assert entry.source.observed(entry.pair.action1)
            prefix = first.pair.vote()
            if prefix is None or prefix != second.pair.vote():
                option = "ABSTAIN"
            else:
                option = selected_s11_option(
                    owner, prefix, trial=f"{name}-fresh-nuisance"
                )
                cheap = table.choices[prefix]
                if option != cheap:
                    raise InvalidB18Source("S10 gated Habit differs from cheap table")
            if option not in OPTIONS:
                raise InvalidB18Source("missing approved S11 policy for vote")
            third_vote = None
            if option in ("QUERY_P", "QUERY_S"):
                channel = "P" if option == "QUERY_P" else "S"
                third = execute_trial(
                    worlds, (a, b), 2, channel, correlated=correlated
                )
                for item in (third.pair.action0, third.pair.action1):
                    if not worlds[channel].observed(item):
                        raise InvalidB18Source("unregistered additional source")
                third_vote = third.pair.vote()
                if channel == "P":
                    queried_primary += 1
                else:
                    queried_secondary += 1
            decision = source_action(prefix, option, third_vote)
            # Read hidden outcome truth ONLY AFTER the choice and possible
            # query are fully completed. No evaluation-time Q refit.
            was_right = (
                worlds["P"].heldout_score(a, b, decision)
                if decision is not None else None
            )
            if was_right is None:
                abstained += 1
            elif was_right:
                correct += 1
            else:
                wrong += 1
            # The cheapest STOP baseline gets only the same already-issued
            # prefix. Its source budget is a separately *estimated* 32,
            # not another executed 32 Actions in this run.
            stop_truth = worlds["P"].heldout_score(a, b, prefix)
            stop_correct += int(stop_truth)
            stop_wrong += int(not stop_truth)
            actual_world_actions += sum(
                w.actions_executed for w in worlds.values()
            )
            active_cost += (
                2
                + (1 if option == "QUERY_P" else 2 if option == "QUERY_S" else 0)
            )
            all_cases.append({
                "case": name, "p_vote": prefix, "option": option,
                "decision": decision, "right": was_right,
                "world_actions": sum(w.actions_executed for w in worlds.values()),
            })
    assert len(all_cases) == 8
    net = (
        correct * CORRECT_REWARD
        + wrong * RISKS[table.risk]
        + abstained * ABSTAIN_REWARD
        - active_cost
    )
    cheap_stopped_utility = (
        stop_correct * CORRECT_REWARD
        + stop_wrong * RISKS[table.risk] - 16
    )
    return {
        "risk": table.risk,
        "actual_world_actions_shared_Habit_and_cheap_Q": actual_world_actions,
        "actual_source_pair_cost_units": active_cost,
        "query_secondary_count": queried_secondary,
        "query_primary_count": queried_primary,
        "correct": correct, "wrong": wrong, "abstained": abstained,
        "trained_policy_net_utility": net,
        "cheap_empirical_Q_net_utility": net,
        "fixed_stop_correct": stop_correct,
        "fixed_stop_wrong": stop_wrong,
        "fixed_stop_counterfactual_actions": 32,
        "fixed_stop_counterfactual_net_utility": cheap_stopped_utility,
        "cases": tuple(all_cases),
        "no_new_relevant_cues": True,
    }


def run_b18_comparison() -> dict[str, object]:
    cases = tuple(
        training_case(cue=cue, correlated=correlated)
        for correlated in (False, True) for cue in CONTEXTS
    )
    trained_actual_actions = sum(
        sum(w.actions_executed for w in case.sources.values())
        for case in cases
    )
    assert trained_actual_actions == 64
    receipt = train_actual_s10_feedback(cases)
    receipt.verify()
    risk_results = []
    for risk in ("HIGH", "LOW"):
        table = learn_empirical_table(receipt, risk=risk)
        owner = empty_repertoire(label=f"b18-retained-{risk}")
        prior_owner = owner
        for vote in (0, 1):
            grant = grant_experiment_only(owner, table, vote)
            owner = retain_test_policy(owner, receipt, table, vote, grant)
        heldout = heldout_episode(table, owner)
        risk_results.append({
            **heldout,
            "trained_votes": table.votes,
            "learned_options": table.choices,
            "learned_mean_Q_by_vote": tuple(
                {name: str(score) for name, score in values}
                for values in table.mean_scores
            ),
            "retained_s11_revision": owner.revision,
            "old_s11_owner_unmodified": (
                prior_owner.rules == () and prior_owner.revision == 0
            ),
            "retained_s11_rules": len(owner.rules),
        })
    return {
        "classification": "B18_BOUNDED_EMPIRICAL_VOI_WITH_CHEAP_Q_NULL",
        "training_actual_sim_world_actions": trained_actual_actions,
        "actual_native_s10_training_commits": receipt.native_s10_commits,
        "s10_final_scalar_values": receipt.native_s10_final_values,
        "s10_final_scalar_revisions": receipt.native_s10_final_revisions,
        "risk_runs": risk_results,
        "training_trace_digest": receipt.trace_digest,
        "real_physical_source": False,
        "production_s11_authority": False,
        "l2_to_l1_autonomous": False,
        "actual_energy_cpu_latency_measured": False,
    }
