"""S8: one disposable original-source TWO-epoch trial; dry run by default.

NO new real-world permit exists. One NEW explicit #537 grant and independent
readback are required. Prior S6 grant is consumed. This CLI never starts a
model; no learned Habit, natural-threat or goal-success claim is possible.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from adapters.mineflayer import self_s1_runtime as s1
from adapters.mineflayer.self_continuous_host import SessionBudget
from adapters.mineflayer.self_s5_world_opportunity import assess_qualified_rsee_world
from adapters.mineflayer.self_s7_native_trial import CONSUMED_S6_GRANT
from adapters.mineflayer.self_s8_two_epoch import S8TwoEpochPlan

CONFIRM = "SELF-S8-TWO-EPOCH-ORIGINAL-ONE-SESSION"
SPENT_PHYSICAL_REFS = frozenset({
    CONSUMED_S6_GRANT,
    "https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6118976649",
    "https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6116304704",
})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-disposable", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--standing-eula-confirmed", action="store_true")
    parser.add_argument("--authorization-reference", default="")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--max-events", type=int, default=12)
    parser.add_argument("--max-actions", type=int, default=2)
    parser.add_argument("--max-frames", type=int, default=500)
    parser.add_argument("--max-seconds", type=float, default=180.0)
    args = parser.parse_args(argv)

    if not args.run_disposable:
        print(json.dumps({
            "classification": "S8_DRY_RUN_NO_EFFECTS",
            "world_started": False, "external_commands": 0,
            "action_requests": 0, "model_posts": 0, "permission": False,
        }, sort_keys=True))
        return 0
    if (
        args.confirm != CONFIRM or not args.standing_eula_confirmed
        or not args.authorization_reference
        or args.authorization_reference in SPENT_S6_REFS
        or args.output_dir is None
    ):
        print(json.dumps({
            "classification": "S8_NEW_TWO_EPOCH_AUTHORITY_REQUIRED",
            "world_started": False, "old_grant_consumed": True,
        }, sort_keys=True))
        return 2
    try:
        # A syntactically valid issue comment URL is not itself a permission.
        # An operator MUST independently read back a fresh S8-specific grant.
        plan = S8TwoEpochPlan(args.authorization_reference)
        if (
            args.max_actions != 2 or args.max_events > 12
            or args.max_frames > 500 or args.max_seconds > 180
        ):
            raise ValueError("S8 one-session fixed experiment ceiling")
        budget = SessionBudget(
            max_events=args.max_events, max_actions=args.max_actions,
            max_frames=args.max_frames, max_seconds=args.max_seconds,
        )
        binding = s1.preflight(s1.RSEE, args.output_dir)
        world = assess_qualified_rsee_world(s1.RSEE)
        if world.classification != "FROZEN_WORLD_NATURAL_MOB_SPAWNING_DISABLED":
            raise ValueError("only exact frozen RSEE #583 World permitted")
        result = asyncio.run(s1.run_physical(
            binding, args.output_dir, budget, controlled_target=plan,
            capture_native_originals=True,
        ))
        if (
            result.get("node_exit") != 0 or result.get("server_exit") != 0
            or result.get("node_cleanup_unconfirmed")
            or result.get("server_cleanup_unconfirmed")
        ):
            raise ValueError("owned Java/Node cleanup unconfirmed")
    except (Exception, KeyboardInterrupt) as exc:
        print(json.dumps({
            "classification": "S8_PHYSICAL_UNKNOWN_OR_BLOCKED",
            "reason_type": type(exc).__name__,
            "world_outcome_unknown": True, "safe_to_replay": False,
        }, sort_keys=True))
        return 2
    print(json.dumps({
        **result,
        "classification": "S8_CONTROLLED_SESSION_TERMINATED_NOT_LEARNING_PROOF",
        "two_closed_actions_observed": (
            result.get("closed_outcomes") == 2
            and result.get("s3_observed_memories", 0) >= 2
            and result.get("s8_distinct_second_target_closed") is True
        ),
        "native_bridge_originals_captured": True,
        "natural_threat_or_goal_attested": False,
        "memory_caused_action_attested": False,
        "s10_learning_updates": 0, "s11_habit_grants": 0,
        "science_go": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
