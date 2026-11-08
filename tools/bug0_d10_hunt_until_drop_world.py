"""D10 DEV: hunt new genuine 600tick zombies until vanilla rotten flesh drops.

Reuses the original D6 multi-generation S49 owner/Intent, S15/S16 and
persistent physical fences. No artificial item/food, no second issuer.
Stops on first source-qualified natural drop and real inventory pickup.
The 12-generation guard is exclusively a bounded disposable CI World budget;
it is NOT a Self goal, and exhaustion is NOT a successful hunt.
"""
from __future__ import annotations

import argparse
import asyncio
import os
from functools import partial
from pathlib import Path

from tools.bug0_d4_oneworld import run
from tools.bug0_d6_multigen_world import continue_after_first_respawn
from tools.bug0_d6_natural_move_world import source_qualified_natural_move


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--server-log", type=Path, required=True)
    p.add_argument("--nonmotion-fence", type=Path, required=True)
    p.add_argument("--motion-fence", type=Path, required=True)
    args = p.parse_args()
    if (
        os.environ.get("D10_HUNT_UNTIL_DROP_WORLD_ONLY") != "1"
        or os.environ.get("D6_NATURAL_MULTIGEN_WORLD_ONLY") != "1"
        or os.environ.get("D6_NATURAL_DROP_MOVE_WORLD_ONLY") != "1"
    ):
        raise SystemExit("explicit D10 first-natural-drop real World grant absent")
    raise SystemExit(asyncio.run(run(
        args.report, args.server_log,
        nonmotion_fence_path=args.nonmotion_fence,
        motion_fence_path=args.motion_fence,
        post_death_loot_move_dev=source_qualified_natural_move,
        post_respawn_dev=partial(
            continue_after_first_respawn, d10_until_drop_dev=True,
        ),
        d6_multigen_dev=True, d10_hunt_until_drop_dev=True,
    )))


if __name__ == "__main__":
    main()
