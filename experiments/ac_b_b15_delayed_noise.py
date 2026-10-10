"""B15 matched offline delayed/noisy source probe; NOT physical Mineflayer.

Actual native S10 updates and exact existing S11 read-only selector are reused.
S11 learning/grant and World-report authentication are experiment-only. The
two policy arms see identical RELEASED source records and the same shared
contradiction detector, never the simulator's hidden regime/true outcome.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass, replace

from experiments.ac_b_b11_governed_habit import (
    CONTEXTS,
    CurrentWorld,
    ObservedOutcome,
    QualifiedHabitView,
    QualifiedLedger,
    UnqualifiedHabitAcquisition,
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

DELAYS = (2, 0, 3, 1, 2, 0, 3, 1)
CONTEXT_ACTIONS = tuple(
    (a, b, action) for a, b in CONTEXTS for action in (0, 1)
)
# Sensor-reported corruption, NOT a mutation of the independently scored
# World success criterion. No learner reads this experimental fixture.
NOISE_PHASE_TWO = frozenset({
    (0, 0, 0), (1, 1, 0), (1, 1, 1),
})


@dataclass(frozen=True, slots=True)
class PendingReport:
    execution_tick: int
    due_tick: int
    report: ObservedOutcome


@dataclass(frozen=True, slots=True)
class PolicyScore:
    tick: int
    delivered: int
    habit_covered: int
    habit_correct: int
    tag_covered: int
    tag_correct: int


class MatchedPolicies:
    """The exact same published World pair trains both retained policy arms."""

    def __init__(self, world: CurrentWorld, label: str) -> None:
        self.world = world
        self.owner: HabitRepertoire = empty_repertoire(label=f"b15-owner-{label}")
        self.tag: dict[tuple[int, int], int] = {}
        self.view = QualifiedHabitView(
            self.owner, world.session, world.revision,
        )
        key = secrets.token_bytes(32)
        self.__issuer = OfflineIndependentS11Issuer(key)
        self.__gate = IndependentS11Admission(key)
        self.native_s10_commits = 0
        self.independent_s11_grants = 0
        self.tag_inserts = 0

    def learn(
        self, ledger: QualifiedLedger, a: int, b: int,
    ) -> None:
        winner, ids = ledger.chosen(a, b)
        if (a, b) in self.tag:
            raise ValueError("duplicate policy training for one cue")
        pair = exact_source_pair(ledger, a, b)
        assert pair.evidence_ids == ids and pair.winner == winner
        # Cheap arm is trained without the S10 update and from the same pair.
        self.tag[a, b] = winner
        self.tag_inserts += 1

        # Real native S10 scalar update, only as an admission condition.
        s10_authority = LearningUpdateAuthority(
            authority_id=f"b15-s10:{self.owner.repertoire_id}:{a}:{b}",
            target_id=pair.target_id,
            provenance=Provenance("b15.test-s10-owner", pair.digest),
        )
        committed = commit_existing_s10(
            ledger, pair, initial_s10_state(pair), s10_authority,
        )
        self.native_s10_commits += 1
        draft = propose_same_source_s11(self.owner, ledger, pair, committed)

        # A separate B12 signed TEST grant; not actual S11 product authority.
        signed = self.__issuer.grant(draft)
        self.owner = self.__gate.commit(self.owner, draft, ledger, signed)
        self.independent_s11_grants += 1
        self.view = QualifiedHabitView(
            self.owner, self.world.session, self.world.revision,
        )

    def decide(self, a: int, b: int, trial: str) -> tuple[int | None, int | None]:
        cue = cue_for(a, b, trial=trial)
        status, candidate = self.view.select(cue, self.world)
        if status == "selected":
            if candidate not in ("action:0", "action:1"):
                raise ValueError("nonbinary selected Habit")
            habit: int | None = int(candidate[-1])
        elif status in ("no_match", "STALE"):
            habit = None
        else:
            raise ValueError("unresolved Habit selection ambiguity")
        return habit, self.tag.get((a, b))

    def score(self, tick: int, published: int, trial: str) -> PolicyScore:
        """Use hidden scoring truth ONLY after both read-only decisions."""
        hc = hr = tc = tr = 0
        for a, b in CONTEXTS:
            habit, tags = self.decide(a, b, trial)
            if habit is not None:
                hc += 1
                hr += int(self.world.heldout_score(a, b, habit))
            if tags is not None:
                tc += 1
                tr += int(self.world.heldout_score(a, b, tags))
        return PolicyScore(tick, published, hc, hr, tc, tr)


class DelayedEpisode:
    """Publish immutable source-observed records ONLY when their due tick arrives."""

    def __init__(
        self,
        world: CurrentWorld,
        phase: int,
        previous: MatchedPolicies | None,
        previous_reports: dict[tuple[int, int, int], bool] | None,
    ) -> None:
        if phase not in (0, 1, 2):
            raise ValueError("phase must be 0/1/2")
        self.world = world
        self.phase = phase
        self.previous_reports = previous_reports
        self.policies = previous if previous is not None else MatchedPolicies(
            world, "initial",
        )
        self.pending: list[PendingReport] = []
        self.published: list[ObservedOutcome] = []
        self.alarm_tick: int | None = None
        self.completed: set[tuple[int, int]] = set()
        self.ambiguous: set[tuple[int, int]] = set()
        self.ticks: list[PolicyScore] = []
        self.command_count = 0
        self.delivered_count = 0

    def issue_at(self, tick: int) -> None:
        """One genuine simulator Action per tick; outcome not yet delivered."""
        if type(tick) is not int or not 0 <= tick < 8:
            raise ValueError("exact execution tick 0..7 required")
        if tick != self.command_count:
            raise ValueError("duplicate or skipped World Action execution")
        a, b, action = CONTEXT_ACTIONS[tick]
        reported = self.world.act(a, b, action)
        if self.phase == 2 and (a, b, action) in NOISE_PHASE_TWO:
            # Experimental source emits corrupted *reported* success while
            # hidden World scoring truth remains governed by CurrentWorld.
            reported = replace(reported, success=not reported.success)
            self.world._issued[reported.event_id] = reported
        assert self.world.observed(reported)
        self.pending.append(PendingReport(tick, tick + DELAYS[tick], reported))
        self.command_count += 1

    def _take_published(self, report: ObservedOutcome, tick: int) -> None:
        if not self.world.observed(report):
            raise ValueError("unissued World receipt")
        if any(x.event_id == report.event_id for x in self.published):
            raise ValueError("duplicate observed receipt released")
        self.published.append(report)
        self.delivered_count += 1

        # Both arms share the same externally defined evidence contradiction
        # detector, not native S10 learning or oracle World truth.
        previous_value = (
            self.previous_reports.get((report.a, report.b, report.action))
            if self.previous_reports is not None else None
        )
        if (
            self.previous_reports is not None
            and previous_value is not None
            and previous_value != report.success
            and self.alarm_tick is None
        ):
            self.alarm_tick = tick
            self.policies = MatchedPolicies(
                self.world, label=f"alarm-phase-{self.phase}-tick-{tick}",
            )
            self.completed.clear()
            self.ambiguous.clear()

        if self.phase > 0 and self.alarm_tick is None:
            # Preserve old policy until contradictory SOURCE evidence arrives.
            return
        ledger = QualifiedLedger(self.world, tuple(self.published))
        for a, b in CONTEXTS:
            if (a, b) in self.completed or (a, b) in self.ambiguous:
                continue
            if set(ledger.rows.get((a, b), {})) != {0, 1}:
                continue
            try:
                ledger.chosen(a, b)
            except UnqualifiedHabitAcquisition:
                # One reported pair is ambiguous. Neither arm may call an
                # oracle, invent a winner or silently assume a success.
                self.ambiguous.add((a, b))
                continue
            self.policies.learn(ledger, a, b)
            self.completed.add((a, b))

    def release_at(self, tick: int) -> tuple[ObservedOutcome, ...]:
        due = sorted(
            (x for x in self.pending if x.due_tick <= tick),
            key=lambda x: (x.due_tick, x.execution_tick),
        )
        released: list[ObservedOutcome] = []
        for item in due:
            self.pending.remove(item)
            self._take_published(item.report, tick)
            released.append(item.report)
        return tuple(released)

    def run(self) -> dict[str, object]:
        previous_action_count = self.world.actions_executed
        for tick in range(10):
            if tick < 8:
                self.issue_at(tick)
            self.release_at(tick)
            self.ticks.append(
                self.policies.score(
                    tick, len(self.published), trial=f"tick-{self.phase}-{tick}",
                )
            )
        assert not self.pending
        assert self.command_count == self.delivered_count == 8
        assert len(self.published) == 8
        assert self.world.actions_executed - previous_action_count == 8
        end = self.ticks[-1]
        heldout = [
            self.policies.score(9, 8, f"heldout-{self.phase}-{i}")
            for i in range(3)
        ]
        return {
            "phase": self.phase,
            "source_revision": self.world.revision,
            "command_count": self.command_count,
            "receipt_count": self.delivered_count,
            "pending_after_completion": len(self.pending),
            "first_contradiction_release_tick": self.alarm_tick,
            "alarm_is_actual_world_shift": self.phase == 1 if self.alarm_tick is not None else None,
            "released_ticks": tuple(
                (x.tick, x.delivered) for x in self.ticks
            ),
            "pre_completion": tuple(
                (x.tick, x.delivered, x.habit_covered, x.tag_covered)
                for x in self.ticks
            ),
            "first_tick": (
                self.ticks[0].habit_covered, self.ticks[0].habit_correct,
                self.ticks[0].tag_covered, self.ticks[0].tag_correct,
            ),
            "final_covered": (end.habit_covered, end.tag_covered),
            "final_correct": (end.habit_correct, end.tag_correct),
            "ambiguous_cues": tuple(sorted(self.ambiguous)),
            "admitted_cues": tuple(sorted(self.completed)),
            "native_s10_commits_in_current_policy": self.policies.native_s10_commits,
            "separate_s11_test_grants_in_current_policy": (
                self.policies.independent_s11_grants
            ),
            "tag_inserts_in_current_policy": self.policies.tag_inserts,
            "heldout_nuisance_count": 12,
            "heldout_habit_correct": sum(x.habit_correct for x in heldout),
            "heldout_tag_correct": sum(x.tag_correct for x in heldout),
            "heldout_habit_covered": sum(x.habit_covered for x in heldout),
            "heldout_tag_covered": sum(x.tag_covered for x in heldout),
        }

    def delivered_index(self) -> dict[tuple[int, int, int], bool]:
        if len(self.published) != 8:
            raise ValueError("not all source outcomes have been delivered")
        return {(x.a, x.b, x.action): x.success for x in self.published}


def run_b15_matched_probe() -> dict[str, object]:
    world = CurrentWorld()
    previous: MatchedPolicies | None = None
    last_results: dict[tuple[int, int, int], bool] | None = None
    phases: list[dict[str, object]] = []
    for phase in (0, 1, 2):
        if phase == 1:
            world.change_rule(announce=False)
        # Phase 2 has no actual hidden regime change. Only reported noise.
        engine = DelayedEpisode(world, phase, previous, last_results)
        phases.append(engine.run())
        previous = engine.policies
        last_results = engine.delivered_index()

    assert world.revision == 0  # no externally announced shift
    assert world.actions_executed == 24
    return {
        "classification": "DELAY_NOISE_SILENT_SHIFT_MATCHED_SOURCE_PROBE",
        "world_actions_shared": world.actions_executed,
        "world_revision_never_announced": world.revision,
        "delivery_offsets": DELAYS,
        "phase_reports": phases,
        "no_new_relevant_cues": True,
        "source_is_physical_minecraft": False,
        "native_s10_is_causal_habit_discovery": False,
    }
