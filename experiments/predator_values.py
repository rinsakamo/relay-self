from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from dataclasses import asdict, dataclass, field, replace
from statistics import fmean
from typing import Iterable

ACTIONS = (-1, 0, 1)
State = tuple[int, int, int]


@dataclass(frozen=True)
class RewardGenes:
    food: float
    movement: float
    conspecific: float
    predator: float

    def mutate(self, rng: random.Random, sigma: float) -> "RewardGenes":
        return RewardGenes(
            food=self.food + rng.gauss(0.0, sigma),
            movement=self.movement + rng.gauss(0.0, sigma),
            conspecific=self.conspecific + rng.gauss(0.0, sigma),
            predator=self.predator + rng.gauss(0.0, sigma),
        )


@dataclass(frozen=True)
class SimulationConfig:
    world_size: int = 96
    initial_population: int = 80
    initial_food: int = 24
    max_food: int = 40
    food_spawn_probability: float = 0.75
    food_energy: float = 10.0
    basal_cost: float = 0.05
    movement_cost: float = 0.08
    initial_energy: float = 20.0
    reproduction_threshold: float = 26.0
    reproduction_transfer: float = 8.0
    minimum_reproduction_age: int = 8
    maximum_age: int = 500
    mutation_sigma: float = 0.10
    epsilon: float = 0.12
    learning_rate: float = 0.20
    discount: float = 0.90
    max_population: int = 300
    initial_predators: int = 2
    predator_sensor_range: int = 10
    conspecific_sensor_range: int = 6
    sensor_reward_scale: float = 0.25
    predator_move_probability: float = 0.20
    predator_kill_probability: float = 0.30
    sample_interval: int = 100

    def __post_init__(self) -> None:
        if self.world_size < 3:
            raise ValueError("world_size must be at least 3")
        if self.initial_population < 1:
            raise ValueError("initial_population must be positive")
        if not 0 <= self.initial_food <= self.world_size:
            raise ValueError("initial_food must fit within the world")
        if self.max_food < self.initial_food:
            raise ValueError("max_food must be >= initial_food")
        if not 0.0 <= self.food_spawn_probability <= 1.0:
            raise ValueError("food_spawn_probability must be within [0, 1]")
        if self.initial_energy <= 0.0 or self.reproduction_transfer <= 0.0:
            raise ValueError("energy values must be positive")
        if self.reproduction_threshold <= self.reproduction_transfer:
            raise ValueError("reproduction_threshold must exceed reproduction_transfer")
        if self.mutation_sigma < 0.0:
            raise ValueError("mutation_sigma must be non-negative")
        if not 0.0 <= self.epsilon <= 1.0:
            raise ValueError("epsilon must be within [0, 1]")
        if not 0.0 < self.learning_rate <= 1.0:
            raise ValueError("learning_rate must be within (0, 1]")
        if not 0.0 <= self.discount <= 1.0:
            raise ValueError("discount must be within [0, 1]")
        if self.initial_predators < 0:
            raise ValueError("initial_predators must be non-negative")
        if self.predator_sensor_range < 0 or self.conspecific_sensor_range < 0:
            raise ValueError("sensor ranges must be non-negative")
        if self.sensor_reward_scale < 0.0:
            raise ValueError("sensor_reward_scale must be non-negative")
        if not 0.0 <= self.predator_move_probability <= 1.0:
            raise ValueError("predator_move_probability must be within [0, 1]")
        if not 0.0 <= self.predator_kill_probability <= 1.0:
            raise ValueError("predator_kill_probability must be within [0, 1]")
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
    q_values: dict[tuple[State, int], float] = field(default_factory=dict)

    def q(self, state: State, action: int) -> float:
        return self.q_values.get((state, action), 0.0)

    def choose_action(self, state: State, rng: random.Random, epsilon: float) -> int:
        if rng.random() < epsilon:
            return rng.choice(ACTIONS)
        values = [(self.q(state, action), action) for action in ACTIONS]
        best_value = max(value for value, _ in values)
        return rng.choice([action for value, action in values if value == best_value])

    def learn(
        self,
        state: State,
        action: int,
        intrinsic_reward: float,
        next_state: State,
        config: SimulationConfig,
    ) -> None:
        old = self.q(state, action)
        future = max(self.q(next_state, candidate) for candidate in ACTIONS)
        target = intrinsic_reward + config.discount * future
        self.q_values[(state, action)] = old + config.learning_rate * (target - old)


@dataclass(frozen=True)
class PendingTransition:
    agent: Agent
    state: State
    action: int
    food_eaten: int
    moved: int


@dataclass(frozen=True)
class PopulationSample:
    step: int
    population: int
    births: int
    deaths: int
    predation_deaths: int
    mean_energy: float
    mean_food_reward: float
    mean_movement_reward: float
    mean_conspecific_reward: float
    mean_predator_reward: float


@dataclass(frozen=True)
class SimulationResult:
    seed: int
    requested_steps: int
    completed_steps: int
    extinct: bool
    births: int
    deaths: int
    predation_deaths: int
    final_population: int
    final_predators: int
    samples: tuple[PopulationSample, ...]

    def as_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def signed_distance(source: int, target: int, world_size: int) -> int:
    clockwise = (target - source) % world_size
    return clockwise if clockwise <= world_size // 2 else clockwise - world_size


def nearest_direction(position: int, points: Iterable[int], world_size: int) -> int:
    points = tuple(points)
    if not points:
        return 0
    distance = min(
        (signed_distance(position, point, world_size) for point in points),
        key=abs,
    )
    return (distance > 0) - (distance < 0)


def predator_sensor(
    position: int,
    predators: Iterable[int],
    config: SimulationConfig,
) -> tuple[int, float]:
    predators = tuple(predators)
    if not predators or config.predator_sensor_range == 0:
        return 0, 0.0
    distances = [
        signed_distance(position, predator, config.world_size) for predator in predators
    ]
    distance = min(distances, key=abs)
    absolute = abs(distance)
    if absolute > config.predator_sensor_range:
        return 0, 0.0
    signal = (config.predator_sensor_range - absolute + 1) / (
        config.predator_sensor_range + 1
    )
    return (distance > 0) - (distance < 0), signal


def conspecific_sensor(
    position: int,
    counts: Counter[int],
    config: SimulationConfig,
) -> tuple[int, float]:
    if config.conspecific_sensor_range == 0:
        return 0, 0.0
    if counts[position] > 1:
        return 0, 1.0

    for distance in range(1, config.conspecific_sensor_range + 1):
        left = (position - distance) % config.world_size
        right = (position + distance) % config.world_size
        has_left = counts[left] > 0
        has_right = counts[right] > 0
        if has_left or has_right:
            signal = (config.conspecific_sensor_range - distance + 1) / (
                config.conspecific_sensor_range + 1
            )
            if has_left and has_right:
                return 0, signal
            return (-1 if has_left else 1), signal
    return 0, 0.0


def observe_state(
    position: int,
    foods: set[int],
    counts: Counter[int],
    predators: list[int],
    config: SimulationConfig,
) -> State:
    food_direction = nearest_direction(position, foods, config.world_size)
    conspecific_direction, _ = conspecific_sensor(position, counts, config)
    predator_direction, _ = predator_sensor(position, predators, config)
    return food_direction, conspecific_direction, predator_direction


def apply_body_dynamics(
    agent: Agent,
    action: int,
    foods: set[int],
    config: SimulationConfig,
) -> tuple[int, int, float]:
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
    return food_eaten, moved, physical_delta


def intrinsic_reward(
    genes: RewardGenes,
    *,
    food_eaten: int,
    moved: int,
    conspecific_signal: float,
    predator_signal_value: float,
    config: SimulationConfig,
) -> float:
    return (
        food_eaten * genes.food
        + moved * genes.movement
        + config.sensor_reward_scale
        * (
            conspecific_signal * genes.conspecific
            + predator_signal_value * genes.predator
        )
    )


def move_predators(
    predators: list[int],
    prey: list[Agent],
    rng: random.Random,
    config: SimulationConfig,
) -> list[int]:
    if not prey:
        return predators[:]

    moved: list[int] = []
    for position in predators:
        new_position = position
        if rng.random() < config.predator_move_probability:
            target = min(
                prey,
                key=lambda agent: abs(
                    signed_distance(position, agent.position, config.world_size)
                ),
            )
            distance = signed_distance(position, target.position, config.world_size)
            if distance != 0:
                new_position = (
                    position + (1 if distance > 0 else -1)
                ) % config.world_size
        moved.append(new_position)
    return moved


def resolve_predation(
    population: list[Agent],
    predators: list[int],
    rng: random.Random,
    config: SimulationConfig,
) -> tuple[list[Agent], set[int]]:
    predator_positions = set(predators)
    survivors: list[Agent] = []
    killed: set[int] = set()
    for agent in population:
        if (
            agent.position in predator_positions
            and rng.random() < config.predator_kill_probability
        ):
            killed.add(agent.agent_id)
        else:
            survivors.append(agent)
    return survivors, killed


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
    predation_deaths: int,
) -> PopulationSample:
    return PopulationSample(
        step=step,
        population=len(population),
        births=births,
        deaths=deaths,
        predation_deaths=predation_deaths,
        mean_energy=fmean(agent.energy for agent in population),
        mean_food_reward=fmean(agent.genes.food for agent in population),
        mean_movement_reward=fmean(agent.genes.movement for agent in population),
        mean_conspecific_reward=fmean(agent.genes.conspecific for agent in population),
        mean_predator_reward=fmean(agent.genes.predator for agent in population),
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

    foods = set(
        rng.sample(range(config.world_size), min(config.initial_food, config.world_size))
    )
    predators = [
        rng.randrange(config.world_size) for _ in range(config.initial_predators)
    ]
    next_agent_id = config.initial_population
    population = [
        Agent(
            agent_id=agent_id,
            parent_id=None,
            position=rng.randrange(config.world_size),
            energy=config.initial_energy,
            genes=RewardGenes(
                food=rng.gauss(0.0, 1.0),
                movement=rng.gauss(0.0, 1.0),
                conspecific=rng.gauss(0.0, 1.0),
                predator=rng.gauss(0.0, 1.0),
            ),
        )
        for agent_id in range(config.initial_population)
    ]

    births = 0
    deaths = 0
    predation_deaths = 0
    samples: list[PopulationSample] = []
    completed_steps = 0

    for step in range(1, steps + 1):
        if (
            rng.random() < config.food_spawn_probability
            and len(foods) < config.max_food
        ):
            foods.add(rng.randrange(config.world_size))

        rng.shuffle(population)
        counts = Counter(agent.position for agent in population)
        transitions: list[PendingTransition] = []

        for agent in population:
            state = observe_state(agent.position, foods, counts, predators, config)
            action = agent.choose_action(state, rng, config.epsilon)
            food_eaten, moved, _ = apply_body_dynamics(agent, action, foods, config)
            transitions.append(
                PendingTransition(
                    agent=agent,
                    state=state,
                    action=action,
                    food_eaten=food_eaten,
                    moved=moved,
                )
            )

        physically_alive = [
            transition.agent
            for transition in transitions
            if transition.agent.energy > 0.0
            and transition.agent.age < config.maximum_age
        ]
        natural_deaths = len(transitions) - len(physically_alive)
        deaths += natural_deaths

        predators = move_predators(predators, physically_alive, rng, config)
        survivors, killed_ids = resolve_predation(
            physically_alive, predators, rng, config
        )
        predation_deaths += len(killed_ids)
        deaths += len(killed_ids)

        next_counts = Counter(agent.position for agent in survivors)
        transition_by_id = {
            transition.agent.agent_id: transition for transition in transitions
        }

        for agent in survivors:
            transition = transition_by_id[agent.agent_id]
            _, conspecific_signal_value = conspecific_sensor(
                agent.position, next_counts, config
            )
            _, predator_signal_value = predator_sensor(
                agent.position, predators, config
            )
            reward = intrinsic_reward(
                agent.genes,
                food_eaten=transition.food_eaten,
                moved=transition.moved,
                conspecific_signal=conspecific_signal_value,
                predator_signal_value=predator_signal_value,
                config=config,
            )
            next_state = observe_state(
                agent.position, foods, next_counts, predators, config
            )
            agent.learn(
                transition.state,
                transition.action,
                reward,
                next_state,
                config,
            )

        children: list[Agent] = []
        for agent in survivors:
            if (
                agent.energy >= config.reproduction_threshold
                and agent.age >= config.minimum_reproduction_age
                and len(survivors) + len(children) < config.max_population
            ):
                children.append(make_child(agent, next_agent_id, rng, config))
                next_agent_id += 1
                births += 1

        population = survivors + children
        completed_steps = step
        if not population:
            break

        if step == 1 or step % config.sample_interval == 0 or step == steps:
            samples.append(
                _sample_population(
                    step,
                    population,
                    births,
                    deaths,
                    predation_deaths,
                )
            )

    return SimulationResult(
        seed=seed,
        requested_steps=steps,
        completed_steps=completed_steps,
        extinct=not population,
        births=births,
        deaths=deaths,
        predation_deaths=predation_deaths,
        final_population=len(population),
        final_predators=len(predators),
        samples=tuple(samples),
    )


def _format_table(samples: Iterable[PopulationSample]) -> str:
    rows = [
        "step\tpop\tbirths\tdeaths\tpred_deaths\tenergy\tfood_reward\t"
        "move_reward\tconspecific_reward\tpredator_reward"
    ]
    for sample in samples:
        rows.append(
            f"{sample.step}\t{sample.population}\t{sample.births}\t"
            f"{sample.deaths}\t{sample.predation_deaths}\t"
            f"{sample.mean_energy:.3f}\t{sample.mean_food_reward:.3f}\t"
            f"{sample.mean_movement_reward:.3f}\t"
            f"{sample.mean_conspecific_reward:.3f}\t"
            f"{sample.mean_predator_reward:.3f}"
        )
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the reduced predator-sensor value-evolution experiment."
    )
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--steps", type=int, default=5_000)
    parser.add_argument("--predators", type=int, default=2)
    parser.add_argument(
        "--stationary-predators",
        action="store_true",
        help="retain predators but disable their chase movement",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = parser.parse_args()

    if args.predators < 0:
        parser.error("--predators must be non-negative")

    default_config = SimulationConfig()
    config = replace(
        default_config,
        initial_predators=args.predators,
        predator_move_probability=(
            0.0 if args.stationary_predators else default_config.predator_move_probability
        ),
    )
    result = run_simulation(seed=args.seed, steps=args.steps, config=config)
    print(result.as_json() if args.json else _format_table(result.samples))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
