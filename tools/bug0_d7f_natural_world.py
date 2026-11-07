"""D7-F: exactly one new real Paper zombie natural-drop → S49 MOVE/STOP/S51 EAT.

No artificial meat or new physical issuer. True vanilla zero or 2 meat
is a reported non-exercised source for this initial one-item EAT proof.
"""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from tools.bug0_d4_oneworld import run
from tools.bug0_d6_natural_move_world import source_qualified_natural_move
from tools.bug0_d7f_natural_eat import after_real_natural_pickup_eat


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--server-log", type=Path, required=True)
    p.add_argument("--nonmotion-fence", type=Path, required=True)
    p.add_argument("--motion-fence", type=Path, required=True)
    p.add_argument("--d7-passive-controls", type=Path, required=True)
    args = p.parse_args()
    if (
        os.environ.get("D7F_NATURAL_S49_S51_WORLD_ONLY") != "1"
        or os.environ.get("D7_PASSIVE_CONTROLS_WORLD_ONLY") != "1"
    ):
        raise SystemExit("D7-F original natural Paper World grant absent")
    raise SystemExit(asyncio.run(run(
        args.report, args.server_log,
        nonmotion_fence_path=args.nonmotion_fence,
        motion_fence_path=args.motion_fence,
        post_death_loot_move_dev=source_qualified_natural_move,
        d7_native_controls_path=args.d7_passive_controls,
        d7f_natural_eat_dev=after_real_natural_pickup_eat,
    )))


if __name__ == "__main__":
    main()
