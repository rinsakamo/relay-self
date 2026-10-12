"""S6 controlled S49 physical integration experiment: default side-effect-free.

This is an explicit *intervention* arm, not a natural Mob-spawning trial.
An independently read-back user permission is needed for even one physical run.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from adapters.mineflayer import self_s1_runtime as s1
from adapters.mineflayer.self_continuous_host import SessionBudget
from adapters.mineflayer.self_s5_world_opportunity import assess_qualified_rsee_world
from adapters.mineflayer.self_s6_intervention import (
    CONFIRM,
    S6ControlledPlan,
    S6InterventionRejected,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S6: explicit one controlled-target World session (dry-run default)"
    )
    parser.add_argument("--run-disposable", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--standing-eula-confirmed", action="store_true")
    parser.add_argument("--authorization-reference", default="")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--max-events", type=int, default=12)
    parser.add_argument("--max-actions", type=int, default=3)
    parser.add_argument("--max-frames", type=int, default=500)
    parser.add_argument("--max-seconds", type=float, default=180)
    args = parser.parse_args(argv)
    if not args.run_disposable:
        print(json.dumps({
            "classification": "S6_DRY_RUN_NO_EFFECTS",
            "world": "NOT_STARTED", "controlled_commands": 0,
            "actions": 0, "model_posts": 0, "physical_authorization": False,
        }, sort_keys=True))
        return 0
    if (
        args.confirm != CONFIRM or not args.standing_eula_confirmed
        or not args.authorization_reference or args.output_dir is None
    ):
        print(json.dumps({
            "classification": "S6_OPERATOR_AUTHORITY_MISSING",
            "world": "NOT_STARTED", "safe_to_replay": False,
        }, sort_keys=True))
        return 2
    try:
        # A reference is necessary but is NOT itself proof of user approval.
        # The operator must independently read back the fresh one-shot grant.
        plan = S6ControlledPlan(args.authorization_reference)
        if (
            args.max_seconds > 180
            or args.max_actions > 3
            or args.max_events > 12
            or args.max_frames > 500
        ):
            raise S6InterventionRejected("S6 has fixed maximum physical limits")
        budget = SessionBudget(
            max_events=args.max_events, max_actions=args.max_actions,
            max_frames=args.max_frames, max_seconds=args.max_seconds,
        )
        binding = s1.preflight(s1.RSEE, args.output_dir)
        native = assess_qualified_rsee_world(s1.RSEE)
        if native.classification != "FROZEN_WORLD_NATURAL_MOB_SPAWNING_DISABLED":
            raise S6InterventionRejected("S6 must use exact frozen World with natural spawns off")
        result = asyncio.run(
            s1.run_physical(
                binding, args.output_dir, budget, controlled_target=plan,
            )
        )
        if (
            result.get("node_exit") != 0 or result.get("server_exit") != 0
            or result.get("node_cleanup_unconfirmed")
            or result.get("server_cleanup_unconfirmed")
        ):
            raise S6InterventionRejected("owned controlled session cleanup unconfirmed")
    except (Exception, KeyboardInterrupt) as exc:
        print(json.dumps({
            "classification": "S6_UNKNOWN_OR_BLOCKED",
            "reason_type": type(exc).__name__,
            "safe_to_replay": False,
            "model_posts": 0,
        }, sort_keys=True))
        return 2
    print(json.dumps({
        **result,
        "classification": "S6_ONE_CONTROLLED_SESSION_TERMINATED_NOT_AUTONOMY_PROOF",
        "world_intervention": "S31A_NOAI_ONE_SHOT",
        "natural_spawn_claimed": False,
        "controlled_target_native_identity_attested": False,
        "command_execution_ack_attested": False,
        "model_posts": 0,
        "s10_learnt_automatically": False,
        "s11_habit_granted": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
