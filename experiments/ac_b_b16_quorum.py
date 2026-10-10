"""B16: repeated B11 OFFLINE observations, native S10 quorum gate vs cheap counts.

Never treat B11 World-issued reports as physical ground truth. Full five-trial
source lineage is local-process object identity only. B12's two-witness grant
CANNOT certify five independent repetitions; the separate B16 test grant
covers the entire batch but is forgeable and is NOT product S11 authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace

from experiments.ac_b_b11_governed_habit import (
    CONTEXTS,
    CurrentWorld,
    ObservedOutcome,
    cue_for,
    empty_repertoire,
)
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
MIN_VOTES = 4
NOISY_FLIPS: frozenset[tuple[int, int, int, int]] = frozenset(
    [(0, 0, 0, 0), (0, 0, 0, 1), (0, 1, 0, 0)]
    + [(1, 0, trial, action) for trial in range(3) for action in (0, 1)]
    + [(1, 1, trial, action) for trial in range(5) for action in (0, 1)]
)
RULE = LearningUpdateRule("b16-test-quorum-step", version=1, step=1)


class QuorumNotQualified(ValueError):
    """Evidence incomplete, ambiguous, stale or not owner authorized."""


@dataclass(frozen=True, slots=True)
class PairedTrial:
    trial: int
    action0: ObservedOutcome
    action1: ObservedOutcome

    def vote(self) -> int | None:
        # A pair gives one vote only if one observed success and one failure.
        if self.action0.success == self.action1.success:
            return None
        return 0 if self.action0.success else 1


def issue_observed_trial(
    world: CurrentWorld, a: int, b: int, trial: int, *,
    noisy: bool,
) -> PairedTrial:
    if (a, b) not in CONTEXTS or type(trial) is not int or not 0 <= trial < 5:
        raise QuorumNotQualified("invalid fixed source cue/trial")
    records = []
    for action in (0, 1):
        observed = world.act(a, b, action)
        if noisy and (a, b, trial, action) in NOISY_FLIPS:
            observed = replace(observed, success=not observed.success)
            # Experimentally source-registered FALSE report; no real sensor.
            world._issued[observed.event_id] = observed
        records.append(observed)
    return PairedTrial(trial=trial, action0=records[0], action1=records[1])


class BatchLedger:
    """Validate multi-trial evidence WITHOUT misusing B11 single-pair ledger."""

    def __init__(
        self, world: CurrentWorld, a: int, b: int,
        trials: tuple[PairedTrial, ...],
    ) -> None:
        if not isinstance(world, CurrentWorld) or (a, b) not in CONTEXTS:
            raise QuorumNotQualified("current offline World and valid cue required")
        if not isinstance(trials, tuple) or len(trials) > N_TRIALS:
            raise QuorumNotQualified("bounded tuple of at most five trials")
        self.world, self.a, self.b = world, a, b
        self.session, self.revision = world.session, world.revision
        self.trials = trials
        seen: set[str] = set()
        for idx, pair in enumerate(trials):
            if not isinstance(pair, PairedTrial) or pair.trial != idx:
                raise QuorumNotQualified("trial order/count mismatch")
            for expected_action, item in enumerate((pair.action0, pair.action1)):
                if (
                    not isinstance(item, ObservedOutcome)
                    or not world.observed(item)
                    or item.session != self.session
                    or item.revision != self.revision
                    or (item.a, item.b) != (a, b)
                    or item.action != expected_action
                    or type(item.success) is not bool
                    or item.kind != "OBSERVED_ACTION"
                ):
                    raise QuorumNotQualified("source-owned exact Action required")
                if item.event_id in seen:
                    raise QuorumNotQualified("duplicated source Action event")
                seen.add(item.event_id)

    def assert_current(self) -> None:
        if self.world.session != self.session or self.world.revision != self.revision:
            raise QuorumNotQualified("stale World session/revision")
        for pair in self.trials:
            if not self.world.observed(pair.action0) or not self.world.observed(
                pair.action1
            ):
                raise QuorumNotQualified("source witness no longer current")

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(
            item.event_id for p in self.trials for item in (p.action0, p.action1)
        )

    @property
    def digest(self) -> str:
        self.assert_current()
        return hashlib.sha256(
            json.dumps({
                "source": "b16.offline-reported-five-trials.v1",
                "session": self.session, "revision": self.revision,
                "world_local_id": id(self.world), "cue": (self.a, self.b),
                "votes": [p.vote() for p in self.trials],
                "records": [
                    (p.trial, p.action0.event_id, p.action0.success,
                     p.action1.event_id, p.action1.success)
                    for p in self.trials
                ],
            }, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def first_shot(self) -> int | None:
        self.assert_current()
        return self.trials[0].vote() if self.trials else None

    def counted_quorum(self) -> int | None:
        self.assert_current()
        if len(self.trials) != N_TRIALS:
            return None  # full five-trial evidence preregistered
        votes = tuple(pair.vote() for pair in self.trials)
        for action in (0, 1):
            if votes.count(action) >= MIN_VOTES:
                return action
        return None


@dataclass(frozen=True, slots=True)
class QuorumDraft:
    owner_id: str
    owner_revision: int
    session: str
    source_revision: int
    world_local_id: int
    a: int
    b: int
    winner: int
    evidence_ids: tuple[str, ...]
    evidence_digest: str
    rule: HabitRule


@dataclass(frozen=True, slots=True)
class ExperimentQuorumAuthority:
    """EXPERIMENT ONLY; ordinary forgeable dataclass, NOT cryptographic."""

    owner_id: str
    owner_revision: int
    session: str
    source_revision: int
    world_local_id: int
    evidence_digest: str
    winner: int
    granted: bool


def initial_state(ledger: BatchLedger) -> LearningPreferenceState:
    ledger.assert_current()
    return LearningPreferenceState(
        target_id=f"b16-{ledger.session}-{ledger.a}-{ledger.b}",
        value=1, minimum=0, maximum=2, revision=0,
        origin_provenance=Provenance("b16.test-s10-owner", ledger.digest),
    )


def expected_feedback(ledger: BatchLedger) -> LearningFeedback:
    winner = ledger.counted_quorum()
    if winner is None:
        raise QuorumNotQualified("five source trials lack a four-vote quorum")
    return LearningFeedback(
        feedback_id=f"b16-feedback-{ledger.digest}",
        target_id=initial_state(ledger).target_id,
        direction=(
            FeedbackDirection.INCREASE if winner else FeedbackDirection.DECREASE
        ),
        provenance=Provenance("b16.test-quorum-orientation", ledger.digest),
        consequence_ref=f"b16-all-ten-actions-{ledger.digest}",
    )


def native_s10_commit(
    ledger: BatchLedger, authority: LearningUpdateAuthority | None,
) -> LearningCommitResult:
    state = initial_state(ledger)
    feedback = expected_feedback(ledger)
    proposal = propose_learning_update(state, feedback, RULE)
    return commit_learning_update(
        state, proposal, authority,
        provenance=Provenance("b16.test-native-s10-commit", ledger.digest),
    )


def _validate_actual_s10(
    ledger: BatchLedger, committed: LearningCommitResult | None,
) -> None:
    if not isinstance(committed, LearningCommitResult):
        raise QuorumNotQualified("actual native S10 committed owner required")
    state = initial_state(ledger)
    feedback = expected_feedback(ledger)
    proposal = propose_learning_update(state, feedback, RULE)
    winner = ledger.counted_quorum()
    assert winner is not None
    if (
        committed.previous_state != state
        or committed.proposal != proposal
        or committed.new_state.revision != 1
        or committed.new_state.value != (2 if winner else 0)
        or committed.new_state.last_update != committed.record
        or committed.record.target_id != state.target_id
        or committed.record.feedback_id != feedback.feedback_id
        or committed.record.feedback_provenance != feedback.provenance
        or committed.record.rule_id != RULE.rule_id
        or committed.record.rule_version != RULE.version
        or committed.record.committed_revision != 1
        or committed.record.previous_revision != 0
        or not committed.record.authority_id
    ):
        raise QuorumNotQualified("native S10 quorum/source/commit mismatch")


def propose_quorum_habit(
    ledger: BatchLedger,
    owner: HabitRepertoire,
    committed: LearningCommitResult | None,
) -> QuorumDraft:
    ledger.assert_current()
    if not isinstance(owner, HabitRepertoire):
        raise QuorumNotQualified("native S11 owner required")
    _validate_actual_s10(ledger, committed)
    winner = ledger.counted_quorum()
    assert winner is not None
    rule = HabitRule(
        habit_id=f"b16-{ledger.a}-{ledger.b}-{ledger.digest[:16]}",
        cue_requirements=(CueFeature("a", ledger.a), CueFeature("b", ledger.b)),
        candidate_ref=f"action:{winner}", priority=10,
        provenance=Provenance("b16.test-full-quorum-source", ledger.digest),
    )
    return QuorumDraft(
        owner_id=owner.repertoire_id, owner_revision=owner.revision,
        session=ledger.session, source_revision=ledger.revision,
        world_local_id=id(ledger.world), a=ledger.a, b=ledger.b, winner=winner,
        evidence_ids=ledger.evidence_ids, evidence_digest=ledger.digest, rule=rule,
    )


def issue_test_authority(draft: QuorumDraft) -> ExperimentQuorumAuthority:
    """EXPLICIT test caller grant, still forgeable in-process."""
    return ExperimentQuorumAuthority(
        owner_id=draft.owner_id, owner_revision=draft.owner_revision,
        session=draft.session, source_revision=draft.source_revision,
        world_local_id=draft.world_local_id,
        evidence_digest=draft.evidence_digest, winner=draft.winner,
        granted=True,
    )


def commit_test_quorum_habit(
    ledger: BatchLedger,
    owner: HabitRepertoire,
    committed: LearningCommitResult | None,
    draft: QuorumDraft,
    authority: ExperimentQuorumAuthority | None,
) -> HabitRepertoire:
    if not isinstance(draft, QuorumDraft):
        raise QuorumNotQualified("typed full-quorum Habit draft required")
    recomputed = propose_quorum_habit(ledger, owner, committed)
    if recomputed != draft:
        raise QuorumNotQualified("source-bound quorum draft/owner mismatch")
    if (
        not isinstance(authority, ExperimentQuorumAuthority)
        or authority.granted is not True
        or authority.owner_id != draft.owner_id
        or authority.owner_revision != draft.owner_revision
        or authority.session != draft.session
        or authority.source_revision != draft.source_revision
        or authority.world_local_id != draft.world_local_id
        or authority.evidence_digest != draft.evidence_digest
        or authority.winner != draft.winner
    ):
        raise QuorumNotQualified("separate test-only full-quorum owner grant required")
    cue = cue_for(ledger.a, ledger.b, trial="b16-prior-rule-collision")
    if select_habit(owner, cue).status is not HabitSelectionStatus.NO_MATCH:
        raise QuorumNotQualified("prior Habit conflicts with new quorum")
    return HabitRepertoire(
        repertoire_id=owner.repertoire_id, revision=owner.revision + 1,
        rules=owner.rules + (draft.rule,), provenance=owner.provenance,
    )


def _policy_score(
    world: CurrentWorld, selected: dict[tuple[int, int], int],
) -> tuple[int, int]:
    # World oracle used ONLY for scoring already chosen Actions.
    return (
        len(selected),
        sum(int(world.heldout_score(a, b, action))
            for (a, b), action in selected.items()),
    )


def run_episode(*, noisy: bool) -> dict[str, object]:
    world = CurrentWorld(session="b16-offline-noisy" if noisy else "b16-offline-clean")
    batches: dict[tuple[int, int], list[PairedTrial]] = {
        key: [] for key in CONTEXTS
    }
    first: dict[tuple[int, int], int] = {}
    one_shot_issued_when_complete: int | None = None
    for trial in range(N_TRIALS):
        for a, b in CONTEXTS:
            pair = issue_observed_trial(world, a, b, trial, noisy=noisy)
            batches[a, b].append(pair)
            ledger = BatchLedger(world, a, b, tuple(batches[a, b]))
            if trial == 0:
                v = ledger.first_shot()
                if v is not None:
                    first[a, b] = v
            if trial < N_TRIALS - 1:
                assert ledger.counted_quorum() is None
        if trial == 0:
            one_shot_issued_when_complete = world.actions_executed
    assert world.actions_executed == 40
    counted: dict[tuple[int, int], int] = {}
    owner = empty_repertoire(label=f"b16-habit-owner-{'noisy' if noisy else 'clean'}")
    prior_owner = owner
    actual_s10 = 0
    separate_test_grants = 0
    for a, b in CONTEXTS:
        ledger = BatchLedger(world, a, b, tuple(batches[a, b]))
        winner = ledger.counted_quorum()
        if winner is None:
            continue
        counted[a, b] = winner
        state = initial_state(ledger)
        s10_authority = LearningUpdateAuthority(
            authority_id=f"b16-explicit-s10-{a}-{b}",
            target_id=state.target_id,
            provenance=Provenance("b16.test-explicit-s10-authority", ledger.digest),
        )
        s10_commit = native_s10_commit(ledger, s10_authority)
        actual_s10 += 1
        draft = propose_quorum_habit(ledger, owner, s10_commit)
        owner = commit_test_quorum_habit(
            ledger, owner, s10_commit, draft, issue_test_authority(draft),
        )
        separate_test_grants += 1

    habit: dict[tuple[int, int], int] = {}
    for a, b in CONTEXTS:
        choice = select_habit(owner, cue_for(a, b, trial="b16-fresh-nuisance"))
        if choice.status is HabitSelectionStatus.SELECTED:
            assert choice.selected_candidate_ref is not None
            habit[a, b] = int(choice.selected_candidate_ref.split(":")[1])
    first_covered, first_correct = _policy_score(world, first)
    habit_covered, habit_correct = _policy_score(world, habit)
    count_covered, count_correct = _policy_score(world, counted)
    assert owner.rules == tuple(owner.rules) and prior_owner.rules == ()
    heldout: dict[str, tuple[int, int]] = {}
    for key, policy in (
        ("first", first), ("s10_s11_quorum", habit), ("cheap_counts", counted)
    ):
        covered = correct = 0
        for j in range(3):
            for a, b in CONTEXTS:
                cue = cue_for(a, b, trial=f"b16-heldout-{j}")
                if key == "s10_s11_quorum":
                    # Run the ACTUAL existing S11 read-only selector for every
                    # heldout cue ID, rather than copying the train-time vote.
                    selected = select_habit(owner, cue)
                    action = (
                        int(selected.selected_candidate_ref.split(":")[1])
                        if selected.status is HabitSelectionStatus.SELECTED
                        and selected.selected_candidate_ref is not None
                        else None
                    )
                    assert action == policy.get((a, b))
                else:
                    action = policy.get((a, b))
                if action is not None:
                    covered += 1
                    correct += int(world.heldout_score(a, b, action))
        heldout[key] = (covered, correct)
    return {
        "episode": "adversarial" if noisy else "clean",
        "total_actual_world_actions": world.actions_executed,
        "one_shot_available_after_actions": one_shot_issued_when_complete,
        "quorum_available_after_actions": world.actions_executed,
        "first": (first_covered, first_correct),
        "s10_s11_quorum": (habit_covered, habit_correct),
        "cheap_counts": (count_covered, count_correct),
        "quorum_agrees_cheap_counts": habit == counted,
        "actual_native_s10_commits": actual_s10,
        "separate_b16_test_s11_grants": separate_test_grants,
        "new_s11_rules": len(owner.rules),
        "original_owner_revision": prior_owner.revision,
        "new_owner_revision": owner.revision,
        "heldout": heldout,
        "vote_sequences": {
            f"{a}{b}": tuple(p.vote() for p in batches[a, b])
            for a, b in CONTEXTS
        },
        "truth_visible_to_learner": False,
    }


def run_b16_comparison() -> dict[str, object]:
    clean = run_episode(noisy=False)
    adversarial = run_episode(noisy=True)
    return {
        "classification": "B16_EXPERIMENT_ONLY_MATCHED_NOISY_QUORUM_TEST",
        "episodes": [clean, adversarial],
        "shared_actual_world_actions_total": (
            clean["total_actual_world_actions"]
            + adversarial["total_actual_world_actions"]
        ),
        "no_physical_source_attestation": True,
        "no_production_s11_acquisition_owner": True,
        "no_autonomous_l2_to_l1_distillation": True,
    }
