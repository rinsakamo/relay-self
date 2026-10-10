"""B23: a small end-to-end experiential loop; not a security experiment.

World.act executes each chosen offline Action. Actual outcome is appended to
retained episode Memory. Successful experiences can be distilled into a
native *immutable* S11 rule selected by the real read-only select_habit.
Surprising failure calls a bounded two-action reconsideration operator.
A cheap dict gets the SAME information and should match every decision.

"L2-like" here is deterministic bounded reconsideration, NOT a real LLM.
World is B11's OFFLINE toy, not Minecraft or a production S11 acquisition.
"""
from __future__ import annotations

from dataclasses import dataclass, field

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
from relay_self.provenance import Provenance

ARMS = ("HABIT", "CHEAP_TABLE", "ALWAYS_RETHINK")
N_ROUNDS = 8
FLIP_BEFORE_ROUND = 4


class InconsistentExperience(ValueError):
    """An actual observed success is required before changing learned action."""


@dataclass(frozen=True, slots=True)
class Experience:
    round_id: int
    cue: tuple[int, int]
    action: int
    succeeded: bool
    source_session: str
    source_revision: int
    original_event_id: str
    reason: str
    original_outcome: ObservedOutcome


@dataclass(frozen=True, slots=True)
class Encounter:
    round_id: int
    cue: tuple[int, int]
    first_action: int
    attempted_actions: tuple[int, ...]
    actual_event_ids: tuple[str, ...]
    recovered_action: int
    used_L1: bool
    deliberated_L2_like: bool
    surprising_failure: bool
    retained_revision_after: int
    unexpected_world_revision: bool


@dataclass(slots=True)
class CognitiveAgent:
    arm: str
    world: CurrentWorld
    memory: tuple[Experience, ...] = ()
    owner: HabitRepertoire = field(default_factory=empty_repertoire)
    cheap: dict[tuple[int, int], int] = field(default_factory=dict)
    encounters: list[Encounter] = field(default_factory=list)
    deliberations: int = 0
    surprises: int = 0
    L1_selected_attempts: int = 0
    learned_updates: int = 0
    prior_owners: list[HabitRepertoire] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.arm not in ARMS or not isinstance(self.world, CurrentWorld):
            raise InconsistentExperience("bounded cognitive policy and World required")

    def select_previous(self, a: int, b: int, round_id: int) -> int | None:
        if self.arm == "ALWAYS_RETHINK":
            return None
        if self.arm == "CHEAP_TABLE":
            return self.cheap.get((a, b))
        selected = select_habit(
            self.owner, cue_for(a, b, trial=f"b23-round-{round_id}"),
        )
        if selected.status is HabitSelectionStatus.NO_MATCH:
            return None
        if (
            selected.status is not HabitSelectionStatus.SELECTED
            or selected.selected_candidate_ref not in ("action:0", "action:1")
        ):
            raise InconsistentExperience("previous S11 rule is not uniquely selected")
        return int(selected.selected_candidate_ref.split(":")[1])

    def actually_try(
        self, round_id: int, cue: tuple[int, int], action: int, reason: str,
    ) -> ObservedOutcome:
        """Only original World.act produces an experience; no evaluator call."""
        if cue not in CONTEXTS or action not in (0, 1):
            raise InconsistentExperience("invalid actual World choice")
        observed = self.world.act(*cue, action)
        if not self.world.observed(observed):
            raise InconsistentExperience("Action not present in executing World")
        if (
            observed.revision != self.world.revision
            or (observed.a, observed.b, observed.action) != (*cue, action)
            or observed.kind != "OBSERVED_ACTION"
        ):
            raise InconsistentExperience("World Action record disagrees with source")
        if any(row.original_event_id == observed.event_id for row in self.memory):
            raise InconsistentExperience("Action already stored in experience")
        self.memory = self.memory + (
            Experience(
                round_id=round_id, cue=cue, action=action,
                succeeded=observed.success,
                source_session=observed.session,
                source_revision=observed.revision,
                original_event_id=observed.event_id,
                reason=reason, original_outcome=observed,
            ),
        )
        return observed

    def _retain(self, cue: tuple[int, int], observed: ObservedOutcome) -> None:
        """Retain the successful original Action, not inferred opposite truth."""
        if not self.world.observed(observed) or not observed.success or (
            observed.a, observed.b
        ) != cue:
            raise InconsistentExperience("cannot learn from unexecuted or failed Action")
        if self.arm == "ALWAYS_RETHINK":
            return
        new_action = observed.action
        if self.arm == "CHEAP_TABLE":
            if self.cheap.get(cue) != new_action:
                self.cheap[cue] = new_action
                self.learned_updates += 1
            return
        requirements = (CueFeature("a", cue[0]), CueFeature("b", cue[1]))
        matching = [
            old for old in self.owner.rules if old.cue_requirements == requirements
        ]
        if len(matching) > 1:
            raise InconsistentExperience("ambiguous source-specific previous Habit")
        if matching and matching[0].candidate_ref == f"action:{new_action}":
            return
        prior = self.owner
        rule = HabitRule(
            habit_id=f"b23-{cue[0]}{cue[1]}-r{prior.revision + 1}",
            cue_requirements=requirements,
            candidate_ref=f"action:{new_action}",
            priority=10,
            provenance=Provenance(
                "b23.original-world-action-success", observed.event_id,
            ),
        )
        self.prior_owners.append(prior)
        self.owner = HabitRepertoire(
            repertoire_id=prior.repertoire_id,
            revision=prior.revision + 1,
            rules=tuple(
                r for r in prior.rules if r.cue_requirements != requirements
            ) + (rule,),
            provenance=prior.provenance,
        )
        self.learned_updates += 1

    def encounter(self, round_id: int, cue: tuple[int, int]) -> Encounter:
        if not (1 <= round_id <= N_ROUNDS) or cue not in CONTEXTS:
            raise InconsistentExperience("not a preregistered World encounter")
        previous = self.select_previous(*cue, round_id=round_id)
        used_L1 = previous is not None
        if used_L1:
            self.L1_selected_attempts += 1
        else:
            self.deliberations += 1
        chosen = previous if previous is not None else 0
        first = self.actually_try(
            round_id, cue, chosen,
            reason="L1_HABIT" if used_L1 else "BOUNDED_FRESH_THOUGHT",
        )
        issued = [first]
        surprise = used_L1 and not first.success
        if surprise:
            self.surprises += 1
            self.deliberations += 1
        if first.success:
            successful = first
        else:
            # Bounded reconsideration, only after observing the failed Action.
            alternate = 1 - chosen
            successful = self.actually_try(
                round_id, cue, alternate,
                reason="PREDICTION_ERROR_RECONSIDERATION"
                if surprise else "FRESH_ALTERNATIVE",
            )
            issued.append(successful)
            if not successful.success:
                raise InconsistentExperience(
                    "both actual attempts failed; no rule may be retained"
                )
        self._retain(cue, successful)
        result = Encounter(
            round_id=round_id,
            cue=cue,
            first_action=chosen,
            attempted_actions=tuple(o.action for o in issued),
            actual_event_ids=tuple(o.event_id for o in issued),
            recovered_action=successful.action,
            used_L1=used_L1,
            deliberated_L2_like=(not used_L1 or surprise),
            surprising_failure=surprise,
            retained_revision_after=self.owner.revision,
            unexpected_world_revision=self.world.revision != 0,
        )
        self.encounters.append(result)
        return result


@dataclass(frozen=True, slots=True)
class ArmResult:
    arm: str
    actual_world_actions: int
    total_encounters: int
    confirmed_successful_encounters: int
    failed_attempts: int
    first_phase_world_revision: int
    end_world_revision: int
    L1_selected_attempts: int
    L2_like_deliberations: int
    surprise_reconsiderations: int
    source_observations_in_memory: int
    learned_updates: int
    final_s11_revision: int
    final_retained_rule_count: int
    matched_traces: tuple[tuple[object, ...], ...]


def execute_arm(arm: str) -> tuple[CognitiveAgent, ArmResult]:
    world = CurrentWorld(session=f"b23-offline-{arm.lower()}")
    agent = CognitiveAgent(
        arm=arm, world=world,
        owner=empty_repertoire(label=f"b23-retained-{arm.lower()}"),
    )
    for round_id in range(1, N_ROUNDS + 1):
        if round_id == FLIP_BEFORE_ROUND:
            world.change_rule(announce=False)
        for cue in CONTEXTS:
            agent.encounter(round_id, cue)
    if agent.world.actions_executed != len(agent.memory):
        raise InconsistentExperience("every actual Action must appear in Memory")
    if not all(
        agent.world.observed(row.original_outcome)
        and row.original_event_id == row.original_outcome.event_id
        and row.succeeded == row.original_outcome.success
        for row in agent.memory
    ):
        raise InconsistentExperience("unverified original Action history")
    result = ArmResult(
        arm=arm,
        actual_world_actions=world.actions_executed,
        total_encounters=len(agent.encounters),
        confirmed_successful_encounters=len(agent.encounters),
        failed_attempts=sum(not e.succeeded for e in agent.memory),
        first_phase_world_revision=0,
        end_world_revision=world.revision,
        L1_selected_attempts=agent.L1_selected_attempts,
        L2_like_deliberations=agent.deliberations,
        surprise_reconsiderations=agent.surprises,
        source_observations_in_memory=len(agent.memory),
        learned_updates=agent.learned_updates,
        final_s11_revision=agent.owner.revision,
        final_retained_rule_count=len(agent.owner.rules),
        matched_traces=tuple(
            (
                e.round_id, e.cue, e.first_action,
                e.attempted_actions, e.recovered_action,
                e.used_L1, e.surprising_failure,
            )
            for e in agent.encounters
        ),
    )
    return agent, result


def run_b23_comparison() -> dict[str, object]:
    results = {arm: execute_arm(arm)[1] for arm in ARMS}
    habit, cheap, rethink = (
        results["HABIT"], results["CHEAP_TABLE"], results["ALWAYS_RETHINK"]
    )
    return {
        "classification": "B23_OFFLINE_EXPERIENCE_MEMORY_HABIT_LOOP",
        "arms": {key: {
            "actual_world_actions": r.actual_world_actions,
            "encounters": r.total_encounters,
            "successful_encounters": r.confirmed_successful_encounters,
            "failed_attempts": r.failed_attempts,
            "L1_selected_attempts": r.L1_selected_attempts,
            "L2_like_deliberations": r.L2_like_deliberations,
            "surprise_reconsiderations": r.surprise_reconsiderations,
            "memory_events": r.source_observations_in_memory,
            "learned_updates": r.learned_updates,
            "retained_s11_revision": r.final_s11_revision,
            "retained_s11_rules": r.final_retained_rule_count,
            "world_revision": r.end_world_revision,
        } for key, r in results.items()},
        "same_exogenous_schedule_different_world_sources": True,
        "habit_and_cheap_exact_stepwise_parity": (
            habit.matched_traces == cheap.matched_traces
            and habit.actual_world_actions == cheap.actual_world_actions
        ),
        "generic_retention_actions_saved_vs_no_reuse": (
            rethink.actual_world_actions - habit.actual_world_actions
        ),
        "total_separately_executed_simulator_actions": sum(
            r.actual_world_actions for r in results.values()
        ),
        "no_real_L2_or_Minecraft": True,
        "no_production_s11_owner": True,
        "no_B22_security_dependency": True,
    }
