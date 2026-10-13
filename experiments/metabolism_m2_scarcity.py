"""M2 resource-constraint *prospective* profile; not a new owner or World runner.

This fixed protocol was authored after the original M2 four-seed outcome;
those historical seed outcomes remain immutable. Never cherry-pick trial seeds.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace

from experiments.metabolism_m2 import (
    HoldoutScore,
    M2Config,
    EvolutionResult,
    _heldout,
    founder_population,
    run_evolution,
)

# Frozen before the new profile's first CI run; never recalibrate on these seeds.
SCARCITY_SEEDS = (101, 211, 307, 419)
PROFILE = M2Config(world_profile="scarce_active")


@dataclass(frozen=True)
class ScarcityResult:
    seed: int
    profile: str
    inherited: EvolutionResult
    disconnected: EvolutionResult
    cheap_move: HoldoutScore
    cheap_fight: HoldoutScore
    cheap_wait: HoldoutScore
    cheap_oracle: HoldoutScore


def run_scarcity(seed: int, config: M2Config = PROFILE) -> ScarcityResult:
    if seed not in SCARCITY_SEEDS:
        raise ValueError("only frozen prospective seed family permitted")
    if config.world_profile != "scarce_active":
        raise ValueError("only the predeclared scarcity profile permitted")
    a = run_evolution(seed=seed, inheritance="inherited", config=config)
    b = run_evolution(seed=seed, inheritance="disconnected", config=config)
    founders = founder_population(seed, config)
    return ScarcityResult(
        seed=seed,
        profile=config.world_profile,
        inherited=a,
        disconnected=b,
        cheap_move=_heldout(founders, seed=seed, config=config, control="move"),
        cheap_fight=_heldout(founders, seed=seed, config=config, control="fight"),
        cheap_wait=a.holdout_wait,
        cheap_oracle=a.holdout_oracle,
    )


def summarize(result: ScarcityResult) -> dict[str, object]:
    def brief(evo: EvolutionResult) -> dict[str, object]:
        return {
            "extinct": evo.extinct,
            "births_by_generation": [row.births for row in evo.samples],
            "next_cohort_by_generation": [row.next_agents for row in evo.samples],
            "starvation_by_generation": [
                row.deaths_from_starvation for row in evo.samples
            ],
            "final_heldout": (
                asdict(evo.holdout_final) if evo.holdout_final is not None
                else None
            ),
        }

    return {
        "seed": result.seed,
        "profile": result.profile,
        "newborn": "parent_funded_by_M0_physics_and_legacy_42_mutation",
        "selection": "inherited_vs_founder_redraw_only",
        "inherited": brief(result.inherited),
        "disconnected": brief(result.disconnected),
        "founders": asdict(result.inherited.holdout_founders),
        "cheap_wait": asdict(result.cheap_wait),
        "cheap_move": asdict(result.cheap_move),
        "cheap_fight": asdict(result.cheap_fight),
        "cheap_oracle": asdict(result.cheap_oracle),
        "decision": "DESCRIPTIVE_ONLY_SCIENCE_NO_GO",
    }


def run_fixed_family() -> tuple[dict[str, object], ...]:
    return tuple(summarize(run_scarcity(seed)) for seed in SCARCITY_SEEDS)


def main() -> int:
    parser = argparse.ArgumentParser(description="M2 prospective scarce-active offline family")
    parser.add_argument("--seeds", action="store_true", help="print frozen four-seed family")
    args = parser.parse_args()
    # No CLI override for seed/profile; do not tune this run to desired result.
    _ = args.seeds
    print(json.dumps(run_fixed_family(), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
