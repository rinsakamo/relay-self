"""M1 offline causal ablation; no production action, reward, or learning owner.

Uses M0 energy physics and #42's existing tabular Q controller. The only
positive food target is an EXPLICIT, non-emergent positive-control arm.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import asdict, dataclass, field, replace
from typing import Callable, Literal, Sequence

from experiments.evolved_values import Agent, RewardGenes, SimulationConfig
from experiments.metabolism_viability import (
    BodyState,
    Interoception,
    MetabolismConfig,
    initial_body,
    metabolism_step,
    observe_energy,
)

Policy = Literal["q_zero", "q_food", "random", "fixed_wait", "fixed_cue", "reactive", "external"]
ACTIONS = {-1: "WAIT", 0: "MOVE", 1: "FIGHT"}
OPPORTUNITIES = {0: None, 1: "WAIT", 2: "MOVE", 3: "FIGHT"}
_Q_CONFIG = SimulationConfig(epsilon=0.12, learning_rate=0.3, discount=0.8)


@dataclass(frozen=True)
class M1Config:
    horizon: int = 48
    physics: MetabolismConfig = field(
        default_factory=lambda: MetabolismConfig(
            initial_energy=12.0,
            basal_cost=0.55,
            move_cost=0.25,
            fight_cost=0.8,
            food_energy=2.0,
        )
    )
    sensor: Interoception = field(default_factory=Interoception)
    noise_sigma: float = 0.0
    observation_cost: float = 0.0
    reactive_threshold: float = 7.0

    def __post_init__(self) -> None:
        if type(self.horizon) is not int or self.horizon < 1:
            raise ValueError("horizon must be positive integer")
        if not all(
            math.isfinite(value)
            for value in (self.noise_sigma, self.observation_cost, self.reactive_threshold)
        ):
            raise ValueError("non-finite M1 parameter")
        if self.noise_sigma < 0 or self.observation_cost < 0:
            raise ValueError("negative sensing expenditure/noise")
        # Cost is real physics, not a reward or an arbitrary change to Q utility.
        if not math.isfinite(self.physics.basal_cost + self.observation_cost):
            raise ValueError("non-finite total basal cost")


@dataclass(frozen=True)
class M1Tick:
    tick: int
    opportunity: int
    reading: float
    action: str
    food_eaten: int
    true_energy_after: float  # evaluator trace only: never an argument to controller
    expenditure: float
    overflow: float
    terminal_now: bool


@dataclass(frozen=True)
class M1Result:
    seed: int
    policy: Policy
    learning: bool
    requested_ticks: int
    completed_ticks: int
    terminal: bool
    meals: int
    total_intake: float
    total_expenditure: float
    total_overflow: float
    final_energy: float
    q_updates: int
    q_nonzero: int
    ticks: tuple[M1Tick, ...]


def food_schedule(seed: int, horizon: int) -> tuple[int, ...]:
    if type(horizon) is not int or horizon < 1:
        raise ValueError("invalid schedule horizon")
    rng = random.Random(seed ^ 0x4D31574F)
    return tuple(rng.randrange(4) for _ in range(horizon))


def _reading(body: BodyState, config: M1Config, rng: random.Random) -> float:
    # Only this narrow evaluator-side function sees the real BodyState.
    value = observe_energy(body, config.sensor).reading
    if config.noise_sigma:
        value += rng.gauss(0.0, config.noise_sigma)
    if not math.isfinite(value):
        raise ValueError("non-finite interoception")
    return value


def _encoded_state(reading: float, cue: int) -> int:
    # Q sees only noisy/quantized interoception and public opportunity cue.
    return 4 * math.floor(reading / 4.0) + cue


def run_trial(
    *,
    seed: int,
    policy: Policy,
    learning: bool,
    config: M1Config | None = None,
    schedule: Sequence[int] | None = None,
    external_selector: Callable[[int, float], str] | None = None,
) -> M1Result:
    cfg = config or M1Config()
    if policy not in ("q_zero", "q_food", "random", "fixed_wait", "fixed_cue", "reactive", "external"):
        raise ValueError("unknown M1 policy")
    if (policy == "external") != (external_selector is not None):
        raise ValueError("external selector must appear only with external policy")
    opportunities = tuple(schedule) if schedule is not None else food_schedule(seed, cfg.horizon)
    if len(opportunities) != cfg.horizon or any(type(c) is not int or c not in OPPORTUNITIES for c in opportunities):
        raise ValueError("invalid externally frozen World schedule")

    # Separate random streams: paired World conditions cannot be reshuffled by
    # changes to a policy's exploratory actions or sensor-noise consumption.
    chooser_rng = random.Random(seed ^ 0x51414354)
    sensor_rng = random.Random(seed ^ 0x53454E53)
    learner = Agent(
        agent_id=0,
        parent_id=None,
        position=0,
        energy=0.0,  # sentinel only, NEVER populated with physical energy
        genes=RewardGenes(food=0.0, movement=0.0),
    )
    physics = replace(cfg.physics, basal_cost=cfg.physics.basal_cost + cfg.observation_cost)
    body = initial_body(physics)
    seen = _reading(body, cfg, sensor_rng)
    records: list[M1Tick] = []
    updates = 0
    total_exp = 0.0
    total_intake = 0.0
    total_overflow = 0.0

    for i, cue in enumerate(opportunities):
        state = _encoded_state(seen, cue)
        if policy == "external":
            assert external_selector is not None
            action = external_selector(cue, seen)
            if action not in ACTIONS.values():
                raise ValueError("invalid external experimental action")
            selected = next(key for key, name in ACTIONS.items() if name == action)
        elif policy in ("q_zero", "q_food"):
            selected = learner.choose_action(state, chooser_rng, _Q_CONFIG.epsilon)
            action = ACTIONS[selected]
        elif policy == "random":
            action = chooser_rng.choice(tuple(ACTIONS.values()))
            selected = next(key for key, name in ACTIONS.items() if name == action)
        elif policy == "fixed_wait":
            action, selected = "WAIT", -1
        elif policy == "fixed_cue":
            action = OPPORTUNITIES[cue] or "WAIT"
            selected = next(key for key, name in ACTIONS.items() if name == action)
        else:
            # An explicitly *engineered* interoception-to-food coupling.
            # This heuristic is a cheap baseline, never evidence of emergence.
            action = (OPPORTUNITIES[cue] or "WAIT") if seen <= cfg.reactive_threshold else "WAIT"
            selected = next(key for key, name in ACTIONS.items() if name == action)

        consumed = int(cue != 0 and action == OPPORTUNITIES[cue])
        change = metabolism_step(
            body,
            action=action,
            consumed_food_units=consumed,  # evaluator-computed, not policy proposal
            config=physics,
        )
        total_intake += change.intake
        total_exp += change.expenditure
        total_overflow += change.overflow
        records.append(
            M1Tick(
                tick=change.after.tick,
                opportunity=cue,
                reading=seen,
                action=action,
                food_eaten=consumed,
                true_energy_after=change.after.energy,
                expenditure=change.expenditure,
                overflow=change.overflow,
                terminal_now=change.terminal_now,
            )
        )
        body = change.after
        if body.terminal:
            break

        next_seen = _reading(body, cfg, sensor_rng)
        if learning and policy in ("q_zero", "q_food"):
            next_cue = opportunities[i + 1] if i + 1 < len(opportunities) else 0
            # Zero: no teaching signal at all. Food: overt, engineered reward
            # used ONLY as a positive control; never label it emergent.
            explicit_reward = float(consumed) if policy == "q_food" else 0.0
            learner.learn(
                state,
                selected,
                explicit_reward,
                _encoded_state(next_seen, next_cue),
                _Q_CONFIG,
            )
            updates += 1
        seen = next_seen

    return M1Result(
        seed=seed,
        policy=policy,
        learning=learning,
        requested_ticks=cfg.horizon,
        completed_ticks=body.tick,
        terminal=body.terminal,
        meals=body.meals,
        total_intake=total_intake,
        total_expenditure=total_exp,
        total_overflow=total_overflow,
        final_energy=body.energy,
        q_updates=updates,
        q_nonzero=sum(value != 0.0 for value in learner.q_values.values()),
        ticks=tuple(records),
    )


def paired_suite(seed: int, config: M1Config | None = None) -> dict[str, M1Result]:
    cfg = config or M1Config()
    schedule = food_schedule(seed, cfg.horizon)
    arms: tuple[tuple[str, Policy, bool, M1Config], ...] = (
        ("reward_free_learning_on", "q_zero", True, cfg),
        ("reward_free_learning_off", "q_zero", False, cfg),
        ("blind_reward_free", "q_zero", True, replace(cfg, sensor=Interoception(gain=0.0))),
        ("explicit_food_positive_control", "q_food", True, cfg),
        ("explicit_food_no_learning", "q_food", False, cfg),
        ("fixed_cue_oracle", "fixed_cue", False, cfg),
        ("fixed_wait", "fixed_wait", False, cfg),
        ("random", "random", False, cfg),
        ("engineered_reactive", "reactive", False, cfg),
    )
    return {
        label: run_trial(seed=seed, policy=policy, learning=learning, config=arm_cfg, schedule=schedule)
        for label, policy, learning, arm_cfg in arms
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="M Lane M1 label-free and overt-reward controls")
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--horizon", type=int, default=48)
    args = parser.parse_args()
    suite = paired_suite(args.seed, M1Config(horizon=args.horizon))
    compact = {
        name: {key: value for key, value in asdict(result).items() if key != "ticks"}
        for name, result in suite.items()
    }
    print(json.dumps(compact, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
