"""M2: offline inherited predispositions with physical births, no reward signal.

Reuses #42 make_child / Gaussian mutation ONLY as evaluator-side reproduction.
Its RewardGenes fields are transport slots for policy alleles, NEVER food/motor rewards.
All actions use the M0 interoception boundary and genuine M0 energy accounting.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import asdict, dataclass, field, replace
from statistics import fmean
from typing import Literal, Sequence

from experiments.evolved_values import Agent, RewardGenes, SimulationConfig, make_child
from experiments.metabolism_m1 import ACTIONS, OPPORTUNITIES, food_schedule
from experiments.metabolism_m1_prediction import DeltaProbe
from experiments.metabolism_viability import (
    Interoception,
    MetabolismConfig,
    initial_body,
    metabolism_step,
    observe_energy,
)

Inheritance = Literal["inherited", "disconnected"]
WorldProfile = Literal["legacy_uniform", "scarce_active"]
Control = Literal["genetic", "oracle", "random", "wait", "move", "fight"]
_ACTION_SET = tuple(ACTIONS.values())


@dataclass(frozen=True)
class Traits:
    cue_bias: float
    sensor_coupling: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.cue_bias) or not math.isfinite(self.sensor_coupling):
            raise ValueError("non-finite inherited trait")


@dataclass(frozen=True)
class Member:
    member_id: int
    parent_id: int | None
    traits: Traits
    birth_energy: float


@dataclass(frozen=True)
class M2Config:
    world_profile: WorldProfile = "legacy_uniform"
    cohort_size: int = 12
    generations: int = 4
    horizon: int = 64
    max_cohort: int = 32
    births_per_parent: int = 3
    maturation_ticks: int = 6
    reproduction_threshold: float = 14.0
    reproduction_transfer: float = 8.0
    mutation_sigma: float = 0.22
    sensor_noise: float = 0.0
    sensor_gain: float = 1.0
    sensor_quantum: float = 0.25
    exploratory_probability: float = 0.12
    physics: MetabolismConfig = field(default_factory=lambda: MetabolismConfig(
        capacity=20, initial_energy=8, basal_cost=0.23,
        move_cost=0.12, fight_cost=0.28, food_energy=4,
    ))

    def __post_init__(self) -> None:
        if self.world_profile not in ("legacy_uniform", "scarce_active"):
            raise ValueError("invalid world profile")
        for name in (
            "cohort_size", "generations", "horizon", "max_cohort",
            "births_per_parent", "maturation_ticks",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"invalid {name}")
        if self.cohort_size > self.max_cohort or self.births_per_parent >= 100:
            raise ValueError("invalid cohort or offspring cap")
        values = (
            self.reproduction_threshold, self.reproduction_transfer, self.mutation_sigma,
            self.sensor_noise, self.sensor_gain, self.sensor_quantum,
            self.exploratory_probability,
        )
        if not all(math.isfinite(v) for v in values):
            raise ValueError("non-finite evolution parameter")
        if not (
            self.physics.capacity >= self.reproduction_threshold
            > self.reproduction_transfer > 0
        ):
            raise ValueError("invalid reproduction physics")
        if not 0 <= self.mutation_sigma or not 0 <= self.sensor_noise:
            raise ValueError("invalid mutation or observation noise")
        if self.sensor_gain < 0 or self.sensor_quantum <= 0:
            raise ValueError("invalid sensor")
        if not 0 <= self.exploratory_probability <= 1:
            raise ValueError("invalid exploration")


@dataclass(frozen=True)
class BirthRecord:
    generation: int
    parent_id: int
    child_id: int
    parent_traits: Traits
    child_traits: Traits
    energy_before: float
    energy_after: float
    child_energy: float


@dataclass(frozen=True)
class Episode:
    ticks: int
    meals: int
    terminal: bool
    births: tuple[BirthRecord, ...]
    forecast_updates: int
    final_energy: float
    # Evaluator-only physical ledger. These never enter the individual's policy.
    energy_intake: float
    energy_expenditure: float
    energy_overflow: float
    terminal_shortfall: float
    wait_ticks: int
    move_ticks: int
    fight_ticks: int


@dataclass(frozen=True)
class GenerationSample:
    generation: int
    starting_agents: int
    births: int
    deaths_from_starvation: int
    average_ticks: float
    meals: int
    next_agents: int
    average_bias: float
    average_coupling: float
    forecast_updates: int
    lineage: tuple[BirthRecord, ...]


@dataclass(frozen=True)
class HoldoutScore:
    episodes: int
    mean_births: float
    mean_ticks: float
    mean_meals: float
    starvation_fraction: float


@dataclass(frozen=True)
class EvolutionResult:
    seed: int
    inheritance: Inheritance
    passive_learning: bool
    samples: tuple[GenerationSample, ...]
    founder_traits: tuple[Traits, ...]
    final_traits: tuple[Traits, ...]
    extinct: bool
    holdout_founders: HoldoutScore
    holdout_final: HoldoutScore | None
    holdout_oracle: HoldoutScore
    holdout_random: HoldoutScore
    holdout_wait: HoldoutScore


def _genes(traits: Traits) -> RewardGenes:
    # #42's two float *transport slots*. Neither coefficient is ever passed to
    # apply_body_dynamics/learn: we do not install inherited intrinsic reward.
    return RewardGenes(food=traits.cue_bias, movement=traits.sensor_coupling)


def _traits(genes: RewardGenes) -> Traits:
    return Traits(cue_bias=genes.food, sensor_coupling=genes.movement)


def founder_population(seed: int, config: M2Config) -> tuple[Member, ...]:
    rng = random.Random(seed ^ 0x4D32474E)
    return tuple(
        Member(
            member_id=index + 1,
            parent_id=None,
            traits=Traits(rng.gauss(-0.2, 0.9), rng.gauss(0.0, 0.7)),
            birth_energy=config.physics.initial_energy,
        )
        for index in range(config.cohort_size)
    )


def world_schedule(seed: int, config: M2Config) -> tuple[int, ...]:
    """Immutable profile. Legacy is byte-for-byte identical to the M2 seed World.

    Scarce: exactly one opportunity every 3 ticks, exclusively MOVE/FIGHT.
    Phase and active action are seed-fixed, never based on policy outcomes.
    """
    if config.world_profile == "legacy_uniform":
        return food_schedule(seed, config.horizon)
    if config.world_profile != "scarce_active":
        raise ValueError("unrecognized World profile")
    rng = random.Random(seed ^ 0x4D325343)
    phase = rng.randrange(3)
    return tuple(
        2 + rng.randrange(2) if tick % 3 == phase else 0
        for tick in range(config.horizon)
    )


def _soft_probability(value: float) -> float:
    # Explicit *policy wiring*, not a learned hunger signal or reward.
    z = max(-30.0, min(30.0, value))
    return 1 / (1 + math.exp(-z))


def _select(
    *,
    cue: int,
    reading: float,
    traits: Traits,
    rng: random.Random,
    config: M2Config,
    control: Control,
) -> str:
    if control == "wait":
        return "WAIT"
    if control == "move":
        return "MOVE"
    if control == "fight":
        return "FIGHT"
    if control == "oracle":
        return OPPORTUNITIES[cue] or "WAIT"
    if control == "random" or cue == 0:
        return rng.choice(_ACTION_SET)
    # Public cue identifies the potentially consumable food action. This
    # knowledge is engineered in the controller. Selection only changes how
    # often the policy exploits it: it cannot establish autonomous food values.
    normalized = (reading / config.physics.capacity - 0.5) * 2
    propensity = _soft_probability(
        traits.cue_bias + traits.sensor_coupling * normalized
    )
    if rng.random() < config.exploratory_probability:
        return rng.choice(_ACTION_SET)
    if rng.random() < propensity:
        return OPPORTUNITIES[cue] or "WAIT"
    other_actions = tuple(
        action for action in _ACTION_SET if action != OPPORTUNITIES[cue]
    )
    return rng.choice(other_actions)


def run_episode(
    *,
    member: Member,
    generation: int,
    schedule: Sequence[int],
    config: M2Config,
    seed: int,
    passive_learning: bool,
    control: Control = "genetic",
) -> Episode:
    if control not in ("genetic", "oracle", "random", "wait", "move", "fight"):
        raise ValueError("invalid control")
    if type(passive_learning) is not bool or type(seed) is not int:
        raise ValueError("invalid episode flags")
    if (
        len(schedule) != config.horizon
        or any(type(cue) is not int or cue not in OPPORTUNITIES for cue in schedule)
    ):
        raise ValueError("invalid precommitted World schedule")
    if not 0 < member.birth_energy <= config.physics.capacity:
        raise ValueError("invalid inherited physical provisioning")
    if member.member_id < 1 or generation < 0:
        raise ValueError("invalid lineage identifier")

    physics = replace(config.physics, initial_energy=member.birth_energy)
    sensor = Interoception(gain=config.sensor_gain, quantum=config.sensor_quantum)
    # Action/noise/mutation draws do not share an RNG stream. Policy changes
    # never change the World opportunity schedule.
    action_rng = random.Random(seed ^ 0x414354)
    sensor_rng = random.Random(seed ^ 0x53454E)
    mutation_rng = random.Random(seed ^ 0x4D5554)
    body = initial_body(physics)
    probe = DeltaProbe(retained=True) if passive_learning else None
    births: list[BirthRecord] = []
    energy_intake = 0.0
    energy_expenditure = 0.0
    energy_overflow = 0.0
    terminal_shortfall = 0.0
    action_counts = {"WAIT": 0, "MOVE": 0, "FIGHT": 0}

    for cue in schedule:
        reading = observe_energy(body, sensor).reading
        if config.sensor_noise:
            reading += sensor_rng.gauss(0.0, config.sensor_noise)
        if not math.isfinite(reading):
            raise ValueError("non-finite agent observation")
        if probe is not None:
            probe.arrive(reading)
        action = _select(
            cue=cue,
            reading=reading,
            traits=member.traits,
            rng=action_rng,
            config=config,
            control=control,
        )
        if probe is not None:
            probe.commit(cue, action, reading)

        # Evaluator alone converts source-owned encounter outcome to food.
        eaten = int(cue != 0 and action == OPPORTUNITIES[cue])
        transition = metabolism_step(
            body, action=action, consumed_food_units=eaten, config=physics
        )
        action_counts[action] += 1
        energy_intake += transition.intake
        energy_expenditure += transition.expenditure
        energy_overflow += transition.overflow
        # M0 clamps terminal energy to zero. Preserve the physically unpaid
        # part of terminal expenditure instead of manufacturing consumption.
        terminal_shortfall += max(
            0.0,
            transition.expenditure - (body.energy + transition.intake - transition.overflow),
        )
        body = transition.after
        if body.terminal:
            break

        if (
            body.tick >= config.maturation_ticks
            and body.energy >= config.reproduction_threshold
            and len(births) < config.births_per_parent
        ):
            parent = Agent(
                agent_id=member.member_id,
                parent_id=member.parent_id,
                position=0,
                energy=body.energy,
                genes=_genes(member.traits),
            )
            child_id = member.member_id * 100 + len(births) + 1
            child = make_child(
                parent, child_id, mutation_rng,
                SimulationConfig(
                    reproduction_threshold=config.reproduction_threshold,
                    reproduction_transfer=config.reproduction_transfer,
                    mutation_sigma=config.mutation_sigma,
                ),
            )
            if child.parent_id != member.member_id or child.q_values:
                raise AssertionError("legacy child inheritance contract violated")
            births.append(
                BirthRecord(
                    generation=generation,
                    parent_id=member.member_id,
                    child_id=child_id,
                    parent_traits=member.traits,
                    child_traits=_traits(child.genes),
                    energy_before=body.energy,
                    energy_after=parent.energy,
                    child_energy=child.energy,
                )
            )
            body = replace(body, energy=parent.energy)
    return Episode(
        ticks=body.tick,
        meals=body.meals,
        terminal=body.terminal,
        births=tuple(births),
        forecast_updates=probe.scored if probe is not None else 0,
        final_energy=body.energy,
        energy_intake=energy_intake,
        energy_expenditure=energy_expenditure,
        energy_overflow=energy_overflow,
        terminal_shortfall=terminal_shortfall,
        wait_ticks=action_counts["WAIT"],
        move_ticks=action_counts["MOVE"],
        fight_ticks=action_counts["FIGHT"],
    )


def _heldout(
    members: tuple[Member, ...],
    *,
    seed: int,
    config: M2Config,
    control: Control = "genetic",
) -> HoldoutScore:
    if not members:
        raise ValueError("cannot grade an extinct cohort as survivors")
    results: list[Episode] = []
    for holdout_index in range(3):
        schedule = world_schedule((seed ^ 0x484F4C44) + holdout_index, config)
        for slot, member in enumerate(members):
            results.append(
                run_episode(
                    member=member,
                    generation=config.generations + 1,
                    schedule=schedule,
                    config=config,
                    seed=seed + 1000 * (holdout_index + 1) + slot,
                    passive_learning=False,
                    control=control,
                )
            )
    return HoldoutScore(
        episodes=len(results),
        mean_births=fmean(len(item.births) for item in results),
        mean_ticks=fmean(item.ticks for item in results),
        mean_meals=fmean(item.meals for item in results),
        starvation_fraction=fmean(float(item.terminal) for item in results),
    )


def run_evolution(
    *,
    seed: int,
    inheritance: Inheritance,
    config: M2Config | None = None,
    passive_learning: bool = False,
    schedules: Sequence[Sequence[int]] | None = None,
) -> EvolutionResult:
    if inheritance not in ("inherited", "disconnected"):
        raise ValueError("unknown inheritance arm")
    cfg = config or M2Config()
    if type(seed) is not int or type(passive_learning) is not bool:
        raise ValueError("invalid experiment flags")
    if schedules is not None and (
        len(schedules) != cfg.generations
        or any(
            len(row) != cfg.horizon
            or any(type(c) is not int or c not in OPPORTUNITIES for c in row)
            for row in schedules
        )
    ):
        raise ValueError("invalid frozen generation schedules")
    founders = founder_population(seed, cfg)
    founder_genes = tuple(m.traits for m in founders)
    current = founders
    samples: list[GenerationSample] = []
    for generation in range(cfg.generations):
        if not current:
            break
        world = (
            tuple(schedules[generation]) if schedules is not None
            else world_schedule(seed + generation * 997 + 44, cfg)
        )
        episodes = [
            run_episode(
                member=member,
                generation=generation,
                schedule=world,
                config=cfg,
                seed=seed + generation * 100000 + slot * 17,
                passive_learning=passive_learning,
            )
            for slot, member in enumerate(current)
        ]
        born = [birth for episode in episodes for birth in episode.births]
        # Ecological bottleneck, randomly allocated and independent of the
        # parents' genotype, after ALL physical births have been counted.
        bottleneck_rng = random.Random(seed + generation * 193 + 50000)
        bottleneck_rng.shuffle(born)
        accepted = born[: cfg.max_cohort]
        neutral_rng = random.Random(seed + generation * 193 + 60000)
        newborns: list[Member] = []
        for birth in accepted:
            if inheritance == "inherited":
                inherited_traits = birth.child_traits
            else:
                # A deliberate NON-BIOLOGICAL null. Physical births are still
                # real but genotype assignment is severed from biological
                # parentage and sampled from the frozen founder distribution.
                old = founder_genes[neutral_rng.randrange(len(founder_genes))]
                inherited_traits = _traits(
                    _genes(old).mutate(neutral_rng, cfg.mutation_sigma)
                )
            newborns.append(
                Member(
                    member_id=birth.child_id,
                    parent_id=birth.parent_id,
                    traits=inherited_traits,
                    birth_energy=birth.child_energy,
                )
            )
        samples.append(
            GenerationSample(
                generation=generation,
                starting_agents=len(current),
                births=len(born),
                deaths_from_starvation=sum(ep.terminal for ep in episodes),
                average_ticks=fmean(ep.ticks for ep in episodes),
                meals=sum(ep.meals for ep in episodes),
                next_agents=len(newborns),
                average_bias=fmean(m.traits.cue_bias for m in current),
                average_coupling=fmean(m.traits.sensor_coupling for m in current),
                forecast_updates=sum(ep.forecast_updates for ep in episodes),
                lineage=tuple(born),
            )
        )
        current = tuple(newborns)
    return EvolutionResult(
        seed=seed,
        inheritance=inheritance,
        passive_learning=passive_learning,
        samples=tuple(samples),
        founder_traits=founder_genes,
        final_traits=tuple(m.traits for m in current),
        extinct=not current,
        holdout_founders=_heldout(founders, seed=seed, config=cfg),
        holdout_final=(
            _heldout(current, seed=seed, config=cfg) if current else None
        ),
        holdout_oracle=_heldout(founders, seed=seed, config=cfg, control="oracle"),
        holdout_random=_heldout(founders, seed=seed, config=cfg, control="random"),
        holdout_wait=_heldout(founders, seed=seed, config=cfg, control="wait"),
    )


def paired_evolution(
    seed: int, config: M2Config | None = None, passive_learning: bool = False
) -> dict[str, EvolutionResult]:
    return {
        inheritance: run_evolution(
            seed=seed, inheritance=inheritance,
            config=config, passive_learning=passive_learning,
        )
        for inheritance in ("inherited", "disconnected")
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="M2 offline inherited-viability test")
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    results = paired_evolution(args.seed)
    payload = {
        arm: {
            "seed": trial.seed,
            "extinct": trial.extinct,
            "generations": [
                {key: value for key, value in asdict(s).items() if key != "lineage"}
                for s in trial.samples
            ],
            "holdout_founders": asdict(trial.holdout_founders),
            "holdout_final": (
                asdict(trial.holdout_final) if trial.holdout_final else None
            ),
            "holdout_oracle": asdict(trial.holdout_oracle),
            "holdout_random": asdict(trial.holdout_random),
            "holdout_wait": asdict(trial.holdout_wait),
        }
        for arm, trial in results.items()
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
