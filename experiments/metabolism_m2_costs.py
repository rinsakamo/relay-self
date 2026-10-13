"""Prespecified M2c factorial cost contrast: physical costs, not food rewards.

The 4x4 cost/seed matrix is frozen in source before its first CI trial.
It extends, never overwrites, M2a and M2b prior fixed-seed results.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace

from experiments.metabolism_m2 import (
    M2Config,
    HoldoutScore,
    Member,
    _heldout,
    founder_population,
    run_episode,
    run_evolution,
    world_schedule,
)

# Separate from the already viewed M2b family (101,211,307,419).
COST_SEEDS = (503, 607, 709, 811)
COST_LEVELS: tuple[tuple[str, float, float], ...] = (
    ("original", 0.12, 0.28),
    ("costly_move", 1.10, 0.28),
    ("costly_fight", 0.12, 1.45),
    ("costly_both", 1.10, 1.45),
)


@dataclass(frozen=True)
class LedgerMeans:
    # Same frozen founding cohort and heldout encounter seeds for every arm.
    episodes: int
    mean_wait_ticks: float
    mean_move_ticks: float
    mean_fight_ticks: float
    mean_intake: float
    mean_expenditure: float
    mean_overflow: float
    mean_shortfall: float
    mean_final_energy: float


def config_for_costs(name: str) -> M2Config:
    matches = [(move, fight) for label, move, fight in COST_LEVELS if label == name]
    if len(matches) != 1:
        raise ValueError("unknown preregistered cost combination")
    move, fight = matches[0]
    base = M2Config(world_profile="scarce_active")
    return replace(
        base,
        physics=replace(base.physics, move_cost=move, fight_cost=fight),
    )


def ledger_means(
    *,
    seed: int,
    config: M2Config,
    control: str,
    members: tuple[Member, ...] | None = None,
) -> LedgerMeans:
    if seed not in COST_SEEDS or control not in (
        "genetic", "wait", "move", "fight", "oracle", "random"
    ):
        raise ValueError("invalid preregistered cost-ledger request")
    if config.world_profile != "scarce_active":
        raise ValueError("cost-ledger World must be scarce_active")
    cohort = members if members is not None else founder_population(seed, config)
    if not cohort:
        raise ValueError("extinct cohort is not silently reseeded")
    episodes = []
    for holdout_index in range(3):
        schedule = world_schedule((seed ^ 0x484F4C44) + holdout_index, config)
        for slot, member in enumerate(cohort):
            episodes.append(run_episode(
                member=member, generation=config.generations + 1,
                schedule=schedule, config=config,
                seed=seed + 1000 * (holdout_index + 1) + slot,
                passive_learning=False, control=control,
            ))
    from statistics import fmean

    return LedgerMeans(
        episodes=len(episodes),
        mean_wait_ticks=fmean(ep.wait_ticks for ep in episodes),
        mean_move_ticks=fmean(ep.move_ticks for ep in episodes),
        mean_fight_ticks=fmean(ep.fight_ticks for ep in episodes),
        mean_intake=fmean(ep.energy_intake for ep in episodes),
        mean_expenditure=fmean(ep.energy_expenditure for ep in episodes),
        mean_overflow=fmean(ep.energy_overflow for ep in episodes),
        mean_shortfall=fmean(ep.terminal_shortfall for ep in episodes),
        mean_final_energy=fmean(ep.final_energy for ep in episodes),
    )


def fixed_cost_family() -> tuple[dict[str, object], ...]:
    rows = []
    for label, move, fight in COST_LEVELS:
        cfg = config_for_costs(label)
        for seed in COST_SEEDS:
            inherited = run_evolution(
                seed=seed, inheritance="inherited", config=cfg
            )
            disconnected = run_evolution(
                seed=seed, inheritance="disconnected", config=cfg
            )
            founders = founder_population(seed, cfg)
            move_score = _heldout(founders, seed=seed, config=cfg, control="move")
            fight_score = _heldout(founders, seed=seed, config=cfg, control="fight")
            # These are absolute outcome comparators, NOT automatic scientific GO.
            rows.append({
                "cost_profile": label,
                "seed": seed,
                "world_profile": cfg.world_profile,
                "costs_per_tick": {
                    "wait": cfg.physics.basal_cost,
                    "move": cfg.physics.basal_cost + move,
                    "fight": cfg.physics.basal_cost + fight,
                    "food_intake": cfg.physics.food_energy,
                },
                "inherited": (
                    asdict(inherited.holdout_final)
                    if inherited.holdout_final is not None else None
                ),
                "disconnected": (
                    asdict(disconnected.holdout_final)
                    if disconnected.holdout_final is not None else None
                ),
                "extinct_inherited": inherited.extinct,
                "extinct_disconnected": disconnected.extinct,
                "cheap_wait": asdict(inherited.holdout_wait),
                "cheap_move": asdict(move_score),
                "cheap_fight": asdict(fight_score),
                "cheap_cue": asdict(inherited.holdout_oracle),
                "ledger_fixed_move": asdict(ledger_means(
                    seed=seed, config=cfg, control="move", members=founders
                )),
                "ledger_fixed_fight": asdict(ledger_means(
                    seed=seed, config=cfg, control="fight", members=founders
                )),
                "ledger_fixed_cue": asdict(ledger_means(
                    seed=seed, config=cfg, control="oracle", members=founders
                )),
                "status": "DESCRIPTIVE_ONLY_NOT_VALUE_EMERGENCE",
            })
    return tuple(rows)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="M2c fixed physical-cost matrix")
    parser.add_argument("--fixed-matrix", action="store_true")
    args = parser.parse_args()
    _ = args.fixed_matrix
    print(json.dumps(fixed_cost_family(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
