"""S7 prospective one-session original-source capture; dry-run by default.

No S7 physical grant exists. The consumed S6 grant #6115833076 MUST NOT
be reused; CLI references never prove a new actual human authorization.
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
    S6ControlledPlan,
    S6InterventionRejected,
)

CONFIRM = "SELF-S7-ORIGINAL-NATIVE-ONE-SESSION"
CONSUMED_S6_GRANT = (
    "https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6115833076"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
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
            "classification": "S7_NATIVE_ORIGINALS_DRY_RUN_NO_EFFECTS",
            "physical_permission": False,
            "world_started": False,
            "original_source_captured": False,
            "model_posts": 0,
        }, sort_keys=True))
        return 0
    if (
        args.confirm != CONFIRM
        or not args.standing_eula_confirmed
        or args.output_dir is None
        or not args.authorization_reference
        or args.authorization_reference == CONSUMED_S6_GRANT
    ):
        print(json.dumps({
            "classification": "S7_NEW_PHYSICAL_AUTHORITY_REQUIRED",
            "world_started": False, "previous_grant_consumed": True,
        }, sort_keys=True))
        return 2
    try:
        plan = S6ControlledPlan(args.authorization_reference)
        if (
            args.max_seconds > 180 or args.max_actions > 3
            or args.max_events > 12 or args.max_frames > 500
        ):
            raise S6InterventionRejected("bounded S7 source trial only")
        budget = SessionBudget(
            max_events=args.max_events, max_actions=args.max_actions,
            max_frames=args.max_frames, max_seconds=args.max_seconds,
        )
        binding = s1.preflight(s1.RSEE, args.output_dir)
        world = assess_qualified_rsee_world(s1.RSEE)
        if world.classification != "FROZEN_WORLD_NATURAL_MOB_SPAWNING_DISABLED":
            raise S6InterventionRejected("S7 requires frozen #583 controlled World")
        result = asyncio.run(s1.run_physical(
            binding, args.output_dir, budget,
            controlled_target=plan,
            capture_native_originals=True,
        ))
        if (
            result.get("node_exit") != 0 or result.get("server_exit") != 0
            or result.get("node_cleanup_unconfirmed")
            or result.get("server_cleanup_unconfirmed")
        ):
            raise S6InterventionRejected("independently owned processes not cleanly ended")
    except (Exception, KeyboardInterrupt) as exc:
        print(json.dumps({
            "classification": "S7_PHYSICAL_UNKNOWN_OR_BLOCKED",
            "reason_type": type(exc).__name__,
            "safe_to_replay": False,
        }, sort_keys=True))
        return 2
    print(json.dumps({
        **result,
        "classification": "S7_ONE_CONTROLLED_NATIVE_CAPTURE_SESSION_TERMINATED",
        "raw_mineflayer_bridge_stream_bytes_written": True,
        "original_world_protocol_packets_attested": False,
        "natural_mob_encounter_attested": False,
        "new_learning_attested": False,
        "science_go": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
