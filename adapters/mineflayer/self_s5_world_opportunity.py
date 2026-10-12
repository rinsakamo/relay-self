"""S5: read-only natural-target opportunity gate for the frozen #583 World.

This is NOT a World launcher or Action/learning authority. A positive native
gamerule alone can never prove a real zombie will appear in the World.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from experiments.standard_env.golden_admission import verify_qualified_world
from experiments.standard_env.world_bootstrap import _parse_native_nbt
from experiments.standard_env.world_binding import WorldBindingRejected

RSEE = Path("/home/rinsa/.local/share/relay-self/rsee-1.0-20261011")


class OpportunityRejected(ValueError):
    """Saved native rule or exact frozen asset identity is unavailable."""


@dataclass(frozen=True, slots=True)
class NaturalTargetOpportunity:
    classification: str
    do_mob_spawning: str
    world_identity: str
    source: str = "PINNED_STOPPED_MOJANG_LEVEL_DAT"
    natural_zombie_spawn_opportunity_qualified: bool = False
    existing_zombie_absence_proven: bool = False
    world_wide_entity_coverage_proven: bool = False
    physical_execution_authorized: bool = False
    minecraft_sessions_started: int = 0
    llm_posts: int = 0
    action_authority: bool = False
    learning_or_habit_qualified: bool = False


def read_stopped_world_gamerule(snapshot: Path) -> str:
    """Parse the original saved NBT, with no Minecraft/Node process or mutation."""
    if not isinstance(snapshot, Path):
        raise OpportunityRejected("saved stopped World path required")
    try:
        root = _parse_native_nbt(snapshot / "level.dat")
        data = root["Data"]
        rules = data["GameRules"]
        if type(data) is not dict or type(rules) is not dict:
            raise OpportunityRejected("native GameRules object required")
        rule = rules.get("doMobSpawning")
    except (OSError, KeyError, TypeError, IndexError, ValueError, EOFError) as exc:
        raise OpportunityRejected("cannot independently read stored native gamerule") from exc
    if rule not in ("true", "false") or type(rule) is not str:
        raise OpportunityRejected("no exact native doMobSpawning value")
    return rule


def assess_qualified_rsee_world(root: Path = RSEE) -> NaturalTargetOpportunity:
    """Qualify *bytes*, then diagnose a natural-hostile-spawn mismatch.

    The original #583 manifest and jar/initial evidence still must match; an
    internally consistent *new* world is never admitted by this function.
    """
    if (root != RSEE or root.is_symlink() or not root.is_dir()):
        raise OpportunityRejected("canonical RSEE 1.0 root required")
    bootstrap = root / "bootstrap-approved-20261011-once"
    try:
        binding = verify_qualified_world(
            root / "minecraft-1.21.8.jar",
            bootstrap / "snapshot",
            bootstrap / "snapshot_manifest.json",
            bootstrap / "initial_native_observation.json",
        )
    except (OSError, TypeError, WorldBindingRejected) as exc:
        raise OpportunityRejected("exact #583 World byte admission failed") from exc
    rule = read_stopped_world_gamerule(binding.snapshot)
    return NaturalTargetOpportunity(
        classification=(
            "FROZEN_WORLD_NATURAL_MOB_SPAWNING_DISABLED"
            if rule == "false"
            else "NATURAL_MOB_SPAWNING_RULE_ENABLED_TARGET_UNPROVEN"
        ),
        do_mob_spawning=rule,
        world_identity=binding.manifest_sha256,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S5 read-only frozen World natural target eligibility check"
    )
    parser.add_argument("--rsee-root", type=Path, default=RSEE)
    args = parser.parse_args(argv)
    try:
        row = asdict(assess_qualified_rsee_world(args.rsee_root))
    except (OpportunityRejected, OSError, ValueError) as exc:
        print(json.dumps({
            "classification": "S5_WORLD_OPPORTUNITY_UNKNOWN_BLOCKED",
            "reason_type": type(exc).__name__,
            "natural_zombie_spawn_opportunity_qualified": False,
            "physical_execution_authorized": False,
            "minecraft_sessions_started": 0,
            "llm_posts": 0,
            "action_authority": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(row, sort_keys=True))
    # Completed diagnosis is not a physical GO; both values remain fail-closed.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
