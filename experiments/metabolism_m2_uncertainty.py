"""M2d: hidden-state decision tradeoffs; experiment-only offline reduction.

No production L learner, reward, Action authority, or original World evidence.
Each policy gets ONLY noisy cue + quantized energy sensation. HMM/regime,
counterfactual food/injury draws, and terminal ledger remain evaluator-only.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import deque
from dataclasses import asdict, dataclass, replace
from statistics import fmean
from typing import Literal

from experiments.evolved_values import Agent, RewardGenes, SimulationConfig, make_child
from experiments.metabolism_m2_costs import config_for_costs
from experiments.metabolism_viability import (
    Interoception,
    initial_body,
    metabolism_step,
    observe_energy,
)

Regime = Literal["persistent", "iid"]
Policy = Literal[
    "wait", "move", "fight", "random", "current_cue", "last5",
    "bayes", "bayes_reset", "scan_bayes",
]
ACTION_NAMES = ("WAIT", "MOVE", "FIGHT", "SCAN")
POLICIES: tuple[Policy, ...] = (
    "wait", "move", "fight", "random", "current_cue", "last5",
    "bayes", "bayes_reset", "scan_bayes",
)
# New and disjoint from M2a/M2b/M2c families; frozen BEFORE any M2d trials.
M2D_SEEDS = (907, 1009, 1103, 1201, 1301, 1409, 1511, 1601)


@dataclass(frozen=True)
class M2DConfig:
    horizon: int = 96
    state_persistence: float = 0.94
    cue_accuracy: float = 0.63
    scanned_accuracy: float = 0.90
    good_food_probability: float = 0.80
    bad_food_probability: float = 0.08
    fight_damage_safe: float = 0.08
    fight_damage_dangerous: float = 0.35
    damage_cost: float = 0.70
    scan_cost: float = 0.55

    def __post_init__(self) -> None:
        if type(self.horizon) is not int or self.horizon < 2:
            raise ValueError("horizon must be an integer >= 2")
        probs = (
            self.state_persistence, self.cue_accuracy, self.scanned_accuracy,
            self.good_food_probability, self.bad_food_probability,
            self.fight_damage_safe, self.fight_damage_dangerous,
        )
        if not all(math.isfinite(x) and 0 <= x <= 1 for x in probs):
            raise ValueError("probabilities must be finite and in [0, 1]")
        if not 0.5 <= self.cue_accuracy <= self.scanned_accuracy < 1:
            raise ValueError("invalid weak/strong observation ordering")
        if self.good_food_probability <= self.bad_food_probability:
            raise ValueError("good success rate must exceed bad success rate")
        if not all(
            math.isfinite(x) and x >= 0 for x in (self.damage_cost, self.scan_cost)
        ):
            raise ValueError("invalid physical risk/information cost")


@dataclass(frozen=True)
class WorldFixture:
    """Precommitted potential outcomes, not an agent observation."""
    regime: Regime
    hidden_fight_favorable: tuple[bool, ...]
    weak_hint_fight: tuple[bool, ...]
    strong_hint_fight: tuple[bool, ...]
    move_food: tuple[bool, ...]
    fight_food: tuple[bool, ...]
    fight_injury: tuple[bool, ...]


@dataclass(frozen=True)
class M2DEpisode:
    seed: int
    regime: Regime
    policy: Policy
    ticks: int
    meals: int
    births: int
    terminal: bool
    final_energy: float
    intake: float
    expenditure: float
    overflow: float
    terminal_shortfall: float
    offspring_transfer: float
    scans: int
    injuries: int
    wait_ticks: int
    move_ticks: int
    fight_ticks: int
    action_trace: tuple[str, ...]
    observed_hints: tuple[bool, ...]
    prediction_correct: int


def make_world(*, seed: int, regime: Regime, config: M2DConfig) -> WorldFixture:
    if type(seed) is not int or regime not in ("persistent", "iid"):
        raise ValueError("unknown M2d seed or regime")
    # Independent RNG partitions avoid coupling hidden-state transitions to
    # policy actions, observation draw count, or food/damage outcomes.
    hidden_rng = random.Random(seed ^ 0x48324D32)
    cue_rng = random.Random(seed ^ 0x43454557)
    scan_rng = random.Random(seed ^ 0x5343414E)
    move_rng = random.Random(seed ^ 0x4D4F5645)
    fight_rng = random.Random(seed ^ 0x46494748)
    injury_rng = random.Random(seed ^ 0x494E4A52)
    persistence = config.state_persistence if regime == "persistent" else 0.5
    state = hidden_rng.random() < 0.5
    hidden = []
    weak = []
    strong = []
    move = []
    fight = []
    injury = []
    for i in range(config.horizon):
        if i and hidden_rng.random() >= persistence:
            state = not state
        hidden.append(state)
        weak.append(state if cue_rng.random() < config.cue_accuracy else not state)
        strong.append(
            state if scan_rng.random() < config.scanned_accuracy else not state
        )
        move.append(
            move_rng.random() < (
                config.bad_food_probability if state
                else config.good_food_probability
            )
        )
        fight.append(
            fight_rng.random() < (
                config.good_food_probability if state
                else config.bad_food_probability
            )
        )
        injury.append(
            injury_rng.random() < (
                config.fight_damage_safe if state
                else config.fight_damage_dangerous
            )
        )
    return WorldFixture(
        regime, tuple(hidden), tuple(weak), tuple(strong),
        tuple(move), tuple(fight), tuple(injury),
    )


class _Policy:
    """Tiny *experimental* signal estimator; not a reusable learning owner."""

    def __init__(
        self, policy: Policy, regime: Regime, seed: int, config: M2DConfig
    ) -> None:
        self.policy = policy
        self.regime = regime
        self.config = config
        self.history: deque[bool] = deque(maxlen=5)
        self.posterior = 0.5
        self.steps = 0
        self.rng = random.Random(seed ^ 0x50324D44)

    def choose(self, *, hint: bool, accuracy: float, sensed_energy: float) -> tuple[str, bool]:
        if not math.isfinite(sensed_energy):
            raise ValueError("invalid interoceptive reading")
        if self.policy not in POLICIES:
            raise ValueError("unknown offline policy")
        self.steps += 1
        self.history.append(hint)
        # In the pre-specified cheap Bayes comparator the world parameters
        # are supplied a priori. It is a strong MODEL-INFORMED baseline,
        # not a learned or naturally emerging belief.
        if self.policy in ("bayes", "bayes_reset", "scan_bayes"):
            persist = self.config.state_persistence if self.regime == "persistent" else 0.5
            prior = 0.5 if self.policy == "bayes_reset" or self.steps == 1 else (
                self.posterior * persist + (1 - self.posterior) * (1 - persist)
            )
            right = accuracy if hint else 1 - accuracy
            wrong = 1 - accuracy if hint else accuracy
            evidence = prior * right + (1 - prior) * wrong
            self.posterior = prior * right / evidence
            guess_fight = self.posterior >= 0.5
        elif self.policy == "last5":
            guess_fight = sum(self.history) * 2 >= len(self.history)
        else:
            guess_fight = hint
        if self.policy == "wait":
            return "WAIT", guess_fight
        if self.policy == "move":
            return "MOVE", guess_fight
        if self.policy == "fight":
            return "FIGHT", guess_fight
        if self.policy == "random":
            return self.rng.choice(("WAIT", "MOVE", "FIGHT")), guess_fight
        # A deliberately installed preference over food/energy opportunities.
        # This is not an emergent hunger/utility learned from consequences.
        if self.policy == "scan_bayes" and 0.41 < self.posterior < 0.59:
            return "SCAN", guess_fight
        return ("FIGHT" if guess_fight else "MOVE"), guess_fight


def run_episode(
    *, world: WorldFixture, policy: Policy, seed: int, config: M2DConfig
) -> M2DEpisode:
    if policy not in POLICIES or type(seed) is not int:
        raise ValueError("invalid policy/seed")
    arrays = (
        world.hidden_fight_favorable, world.weak_hint_fight,
        world.strong_hint_fight, world.move_food, world.fight_food,
        world.fight_injury,
    )
    if any(len(x) != config.horizon for x in arrays):
        raise ValueError("invalid frozen World duration")
    if world.regime not in ("persistent", "iid"):
        raise ValueError("invalid hidden World regime")
    # M2C expensive-both physics is used unchanged; high-cost failures
    # are as admissible as successes. No parameter fitted to output.
    m2 = config_for_costs("costly_both")
    physics = m2.physics
    body = initial_body(physics)
    sensor = Interoception(quantum=m2.sensor_quantum)
    chooser = _Policy(policy, world.regime, seed, config)
    past_scan = False
    meals = 0
    births = 0
    transferred = 0.0
    total_intake = 0.0
    total_cost = 0.0
    overflow = 0.0
    shortfall = 0.0
    injuries = 0
    correct = 0
    trace: list[str] = []
    hints: list[bool] = []

    for index in range(config.horizon):
        hint = (
            world.strong_hint_fight[index] if past_scan
            else world.weak_hint_fight[index]
        )
        reading = observe_energy(body, sensor).reading
        action, guess = chooser.choose(
            hint=hint,
            accuracy=config.scanned_accuracy if past_scan else config.cue_accuracy,
            sensed_energy=reading,
        )
        past_scan = action == "SCAN"
        hints.append(hint)
        trace.append(action)
        correct += guess == world.hidden_fight_favorable[index]
        consumed = (
            int(world.move_food[index]) if action == "MOVE"
            else int(world.fight_food[index]) if action == "FIGHT"
            else 0
        )
        injured = action == "FIGHT" and world.fight_injury[index]
        injuries += int(injured)
        incremental = (
            config.damage_cost if injured else
            config.scan_cost if action == "SCAN" else 0.0
        )
        # SCAN occupies the tick as WAIT+explicit information expenditure.
        physical_action = "WAIT" if action == "SCAN" else action
        step_cfg = replace(physics, basal_cost=physics.basal_cost + incremental)
        transition = metabolism_step(
            body, action=physical_action,
            consumed_food_units=consumed, config=step_cfg,
        )
        total_intake += transition.intake
        total_cost += transition.expenditure
        overflow += transition.overflow
        shortfall += max(
            0.0,
            transition.expenditure - (body.energy + transition.intake - transition.overflow),
        )
        body = transition.after
        meals += consumed
        if body.terminal:
            break

        if (
            body.tick >= m2.maturation_ticks
            and body.energy >= m2.reproduction_threshold
            and births < m2.births_per_parent
        ):
            # Reuse #42's exact energy-transfer semantics, with zero genotype
            # coefficients and no Q-memory inheritance in this M2d *individual*
            # pilot. M2's evolutionary statistics remain separately owned.
            parent = Agent(
                agent_id=seed + 1, parent_id=None, position=0,
                energy=body.energy, genes=RewardGenes(0.0, 0.0),
            )
            child = make_child(
                parent, (seed + 1) * 100 + births + 1,
                random.Random(seed ^ (births + 0x4D3244)),
                SimulationConfig(
                    reproduction_threshold=m2.reproduction_threshold,
                    reproduction_transfer=m2.reproduction_transfer,
                    mutation_sigma=0.0,
                ),
            )
            if child.q_values or child.energy != m2.reproduction_transfer:
                raise AssertionError("invalid physical reproduction adapter")
            births += 1
            transferred += child.energy
            body = replace(body, energy=parent.energy)

    return M2DEpisode(
        seed=seed, regime=world.regime, policy=policy,
        ticks=body.tick, meals=meals, births=births,
        terminal=body.terminal, final_energy=body.energy,
        intake=total_intake, expenditure=total_cost, overflow=overflow,
        terminal_shortfall=shortfall, offspring_transfer=transferred,
        scans=trace.count("SCAN"), injuries=injuries,
        wait_ticks=trace.count("WAIT"), move_ticks=trace.count("MOVE"),
        fight_ticks=trace.count("FIGHT"), action_trace=tuple(trace),
        observed_hints=tuple(hints), prediction_correct=correct,
    )


def frozen_family(
    config: M2DConfig | None = None,
) -> dict[str, object]:
    cfg = config or M2DConfig()
    # This is a NEW predeclared trial family, not a search over selected seeds.
    rows = []
    for regime in ("persistent", "iid"):
        for seed in M2D_SEEDS:
            world = make_world(seed=seed, regime=regime, config=cfg)
            for policy in POLICIES:
                episode = run_episode(
                    world=world, policy=policy, seed=seed, config=cfg,
                )
                # Present short summary but keep full per-episode trace available
                # from run_episode for audit/testing.
                rows.append({
                    "regime": regime,
                    "seed": seed,
                    "policy": policy,
                    "births": episode.births,
                    "ticks": episode.ticks,
                    "meals": episode.meals,
                    "terminal": episode.terminal,
                    "scans": episode.scans,
                    "injuries": episode.injuries,
                    "intake": episode.intake,
                    "expenditure": episode.expenditure,
                    "overflow": episode.overflow,
                    "terminal_shortfall": episode.terminal_shortfall,
                    "offspring_transfer": episode.offspring_transfer,
                    "prediction_correct": episode.prediction_correct,
                    "status": "DESCRIPTIVE_NOT_SCIENTIFIC_GO",
                })
    aggregates = []
    for regime in ("persistent", "iid"):
        for policy in POLICIES:
            sample = [r for r in rows if r["regime"] == regime and r["policy"] == policy]
            aggregates.append({
                "regime": regime,
                "policy": policy,
                "n": len(sample),
                "mean_births": fmean(r["births"] for r in sample),
                "mean_ticks": fmean(r["ticks"] for r in sample),
                "mean_meals": fmean(r["meals"] for r in sample),
                "starvation_fraction": fmean(float(r["terminal"]) for r in sample),
                "mean_scans": fmean(r["scans"] for r in sample),
                "mean_expenditure": fmean(r["expenditure"] for r in sample),
                "mean_prediction_accuracy": fmean(
                    r["prediction_correct"] / r["ticks"] for r in sample
                ),
            })
    return {
        "config": asdict(cfg),
        "seed_family": M2D_SEEDS,
        "policies": POLICIES,
        "rows": rows,
        "aggregates": aggregates,
        "classification": "M2D_OFFLINE_ENGINEERING_ONLY_NOT_VALUE_EMERGENCE",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="M2d hidden-world fixed family")
    parser.add_argument("--fixed-family", action="store_true")
    args = parser.parse_args()
    _ = args.fixed_family
    print(json.dumps(frozen_family(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
