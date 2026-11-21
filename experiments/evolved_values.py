from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass, field
from statistics import fmean
from typing import Iterable

ACTIONS = (-1, 0, 1)


@dataclass(frozen=True)
class RewardGenes:
    food: float
    movement: float

    def mutate(self, rng: random.Random, sigma: float) -> "RewardGenes":
        return RewardGenes(
            food=self.food + rng.gauss(0.0, sigma),
            movement=self.movement + rng.gauss(0.0, sigma),
        )


@dataclass(frozen=True)
class SimulationConfig:
    world_size: int = 64
    initial_population: int = 48
    initial_food: int = 12
    max_food: int = 20
    food_spawn_probability: float = 0.45
    food_energy: float = 8.0
    basal_cost: float = 0.12
    movement_cost: float = 0.18
    initial_energy: float = 16.0
    reproduction_threshold: float = 28.0
    reproduction_transfer: float = 8.0
    minimum_reproduction_age: int = 12
    maximum_age: int = 240
    mutation_sigma: float = 0.12
    epsilon: float = 0.10
    learning_rate: float = 0.20
    discount: float = 0.90
    max_population: int = 240
    sample_interval: int = 100

    def __post_init__(self) -> None:
        if self.world_size < 3:
            raise ValueError("world_size must be at least 3")
        if self.initial_population < 1:
            raise ValueError("initial_population must be positive")
        if not 0.0 <= self.food_spawn_probability <= 1.0:
            raise ValueError("food_spawn_probability must be within [0, 1]")
        if self.initial_energy <= 0 or self.reproduction_transfer <= 0:
            raise ValueError("energy values must be positive")
        if self.reproduction_threshold <= self.reproduction_transfer:
            raise ValueError("reproduction_threshold must exceed reproduction_transfer")
        if self.mutation_sigma < 0:
            raise ValueError("mutation_sigma must be non-negative")
        if not 0.0 <= self.epsilon <= 1.0:
            raise ValueError("epsilon must be within [0, 1]")
        if not 0.0 < self.learning_rate <= 1.0:
            raise ValueError("learning_rate must be within (0, 1]")
        if not 0.0 <= self.discount <= 1.0:
            raise ValueError("discount must be within [0, 1]")
        if self.sample_interval < 1:
            raise ValueError("sample_interval must be positive")


@dataclass
class Agent:
    agent_id: int
    parent_id: int | None
    position: int
    energy: float
    genes: RewardGenes
    age: int = 0
    q_values: dict[tuple[int, int], float] = field(default_factory=dict)

    def q(self, state: int, action: int) -> float:
        return self.q_values.get((state, action), 0.0)

    def choose_action(self, state: int, rng: random.Random, epsilon: float) -> int:
        if rng.random() < epsilon:
            return rng.choice(ACTIONS)
        values = [(self.q(state, action), action) for action in ACTIONS]
        best_value = max(value for value, _ in values)
        return rng.choice([action for value, action in values if value == best_value])

    def learn(
        self,
        state: int,
        action: int,
        intrinsic_reward: float,
        next_state: int,
        config: SimulationConfig,
    ) -> None:
        old = self.q(state, action)
        future = max(self.q(next_state, candidate) for candidate in ACTIONS)
        target = intrinsic_reward + config.discount * future
        self.q_values[(state, action)] = old + config.learning_rate * (target - old)


@dataclass(frozen=True)
class StepResult:
    food_eaten: int
    moved: int
    physical_energy_delta: float
    intrinsic_reward: float


@dataclass(frozen=True)
class PopulationSample:
    step: int
    population: int
    births: int
    deaths: int
    mean_energy: float
    mean_food_reward: float
    mean_movement_reward: float


@dataclass(frozen=True)
class SimulationResult:
    seed: int
    requested_steps: int
    completed_steps: int
    extinct: bool
    births: int
    deaths: int
    final_population: int
    samples: tuple[PopulationSample, ...]

    def as_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def nearest_food_direction(position: int, foods: set[int], world_size: int) -> int:
    if not foods or position in foods:
        return 0

    def signed_distance(food: int) -> int:
        clockwise = (food - position) % world_size
        return clockwise if clockwise <= world_size // 2 else clockwise - world_size

    distance = min((signed_distance(food) for food in foods), key=lambda value: abs(value))
    return 1 if distance > 0 else -1


def apply_body_dynamics(
    agent: Agent,
    action: int,
    foods: set[int],
    config: SimulationConfig,
) -> StepResult:
    moved = int(action != 0)
    agent.position = (agent.position + action) % config.world_size
    food_eaten = int(agent.position in foods)
    if food_eaten:
        foods.remove(agent.position)

    physical_delta = (
        food_eaten * config.food_energy - config.basal_cost - moved * config.movement_cost
    )
    agent.energy += physical_delta
    agent.age += 1

    intrinsic_reward = food_eaten * agent.genes.food + moved * agent.genes.movement
    return StepResult(
        food_eaten=food_eaten,
        moved=moved,
        physical_energy_delta=physical_delta,
        intrinsic_reward=intrinsic_reward,
    )


def make_child(
    parent: Agent,
    child_id: int,
    rng: random.Random,
    config: SimulationConfig,
) -> Agent:
    if parent.energy < config.reproduction_threshold:
        raise ValueError("parent lacks reproduction energy")
    parent.energy -= config.reproduction_transfer
    return Agent(
        agent_id=child_id,
        parent_id=parent.agent_id,
        position=parent.position,
        energy=config.reproduction_transfer,
        genes=parent.genes.mutate(rng, config.mutation_sigma),
    )


def _sample_population(
    step: int,
    population: list[Agent],
    births: int,
    deaths: int,
) -> PopulationSample:
    return PopulationSample(
        step=step,
        population=len(population),
        births=births,
        deaths=deaths,
        mean_energy=fmean(agent.energy for agent in population),
        mean_food_reward=fmean(agent.genes.food for agent in population),
        mean_movement_reward=fmean(agent.genes.movement for agent in population),
    )


def run_simulation(
    *,
    seed: int,
    steps: int,
    config: SimulationConfig | None = None,
) -> SimulationResult:
    if steps < 1:
        raise ValueError("steps must be positive")
    config = config or SimulationConfig()
    rng = random.Random(seed)

    foods = set(rng.sample(range(config.world_size), min(config.initial_food, config.world_size)))
    next_agent_id = config.initial_population
    population = [
        Agent(
            agent_id=agent_id,
            parent_id=None,
            position=rng.randrange(config.world_size),
            energy=config.initial_energy,
            genes=RewardGenes(food=rng.gauss(0.0, 1.0), movement=rng.gauss(0.0, 1.0)),
        )
        for agent_id in range(config.initial_population)
    ]

    births = 0
    deaths = 0
    samples: list[PopulationSample] = []
    completed_steps = 0

    for step in range(1, steps + 1):
        if rng.random() < config.food_spawn_probability and len(foods) < config.max_food:
            foods.add(rng.randrange(config.world_size))

        rng.shuffle(population)
        survivors: list[Agent] = []
        children: list[Agent] = []

        for agent in population:
            state = nearest_food_direction(agent.position, foods, config.world_size)
            action = agent.choose_action(state, rng, config.epsilon)
            body_result = apply_body_dynamics(agent, action, foods, config)
            next_state = nearest_food_direction(agent.position, foods, config.world_size)
            agent.learn(state, action, body_result.intrinsic_reward, next_state, config)

            if (
                agent.energy >= config.reproduction_threshold
                and agent.age >= config.minimum_reproduction_age
                and len(population) + len(children) < config.max_population
            ):
                children.append(make_child(agent, next_agent_id, rng, config))
                next_agent_id += 1
                births += 1

            if agent.energy > 0.0 and agent.age < config.maximum_age:
                survivors.append(agent)
            else:
                deaths += 1

        population = survivors + children
        completed_steps = step
        if not population:
            break

        if step == 1 or step % config.sample_interval == 0 or step == steps:
            samples.append(_sample_population(step, population, births, deaths))

    return SimulationResult(
        seed=seed,
        requested_steps=steps,
        completed_steps=completed_steps,
        extinct=not population,
        births=births,
        deaths=deaths,
        final_population=len(population),
        samples=tuple(samples),
    )


def _format_table(samples: Iterable[PopulationSample]) -> str:
    rows = ["step\tpop\tbirths\tdeaths\tenergy\tfood_reward\tmove_reward"]
    for sample in samples:
        rows.append(
            f"{sample.step}\t{sample.population}\t{sample.births}\t{sample.deaths}\t"
            f"{sample.mean_energy:.3f}\t{sample.mean_food_reward:.3f}\t"
            f"{sample.mean_movement_reward:.3f}"
        )
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the minimal evolved-value experiment.")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--steps", type=int, default=5_000)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = parser.parse_args()

    result = run_simulation(seed=args.seed, steps=args.steps)
    print(result.as_json() if args.json else _format_table(result.samples))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
