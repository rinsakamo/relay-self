"""D11 original S49: genuine vanilla hunt until rotten flesh, STOP then S51 EAT.

One disposable World and native session; zero drops cause fresh S49 Intents.
No source changes are authorized: DEV World hunger is an explicitly reported
stimulus and the food decision stays with original S49 L0. S51 executes EAT.
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
from tools.bug0_d7f_natural_eat import after_real_natural_pickup_eat


def main() -> None:
    p = argparse.ArgumentParser()
    for name in (
        "report", "server-log", "nonmotion-fence", "motion-fence",
        "d7-passive-controls",
    ):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    for var in (
        "D11_HUNT_THEN_S51_EAT_WORLD_ONLY",
        "D10_HUNT_UNTIL_DROP_WORLD_ONLY",
        "D6_NATURAL_MULTIGEN_WORLD_ONLY",
        "D7F_NATURAL_S49_S51_WORLD_ONLY",
        "D7_PASSIVE_CONTROLS_WORLD_ONLY",
    ):
        if os.environ.get(var) != "1":
            raise SystemExit(f"D11 missing explicit grant: {var}")
    raise SystemExit(asyncio.run(run(
        a.report, a.server_log,
        nonmotion_fence_path=a.nonmotion_fence,
        motion_fence_path=a.motion_fence,
        post_death_loot_move_dev=source_qualified_natural_move,
        post_respawn_dev=partial(
            continue_after_first_respawn,
            d10_until_drop_dev=True,
            d11_hunt_then_eat_dev=True,
            s50_sidecar=a.d7_passive_controls,
        ),
        d7f_natural_eat_dev=after_real_natural_pickup_eat,
        d7_native_controls_path=a.d7_passive_controls,
        d6_multigen_dev=True, d10_hunt_until_drop_dev=True,
        d11_hunt_then_eat_dev=True,
    )))


if __name__ == "__main__":
    main()
