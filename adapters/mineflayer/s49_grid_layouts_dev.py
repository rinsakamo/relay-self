"""Seeded physical layout stimuli and passive planning in one DEV session."""
from __future__ import annotations

import asyncio
import random
from dataclasses import asdict

from adapters.mineflayer.s31a_real_server_ci import _command
from relay_self.goal_grid_search_dev import choose_grid_route_dev
from relay_self.goal_local_voxel_dev import NativeVoxelPresentDev, VoxelColumnDev
from relay_self.provenance import Provenance


async def exercise_layouts_dev(server, session, base, goal, after_seq,
                               action_id, observe):
    """No Action issuer: commands are stimuli; decisions use new native bytes."""
    seed = 20261028
    rng = random.Random(seed)
    ox, oz = base.origin_x, base.origin_z
    import math
    x0, z0, y0 = math.floor(ox), math.floor(oz), math.floor(base.player_y)
    reports = []

    async def install(cells):
        for c in cells:
            for dy, status in ((0, c.feet), (1, c.head), (-1, c.floor)):
                if status not in ("CLEAR", "BLOCKED"):
                    raise RuntimeError("cannot install UNKNOWN as physical fact")
                block = "stone" if status == "BLOCKED" else "air"
                _command(server, f"setblock {x0+c.dx} {y0+dy} {z0+c.dz} minecraft:{block}")
        await server.stdin.drain()
        await asyncio.sleep(0.5)

    for name in ("REACHABLE", "CHANGED", "SEALED", "UNSUPPORTED"):
        gap = rng.choice((-2, 2))
        cells = []
        for dz in range(6):
            for dx in range(-3, 4):
                wall = dz == 2 and (name in ("SEALED", "UNSUPPORTED") or dx != gap)
                extra = dz == 3 and dx != gap and rng.random() < 0.3
                cells.append(VoxelColumnDev(
                    dx, dz, "BLOCKED" if (wall or extra) and name != "UNSUPPORTED" else "CLEAR",
                    "CLEAR", "CLEAR" if name == "UNSUPPORTED" and dz == 2 else "BLOCKED",
                ))
        # Force a different corridor for the second layout.
        if name == "CHANGED":
            prior_gap = reports[0]["gap"]
            gap = -prior_gap
            cells = [VoxelColumnDev(c.dx, c.dz,
                     "BLOCKED" if c.dz == 2 and c.dx != gap else "CLEAR",
                     "CLEAR", "BLOCKED") for c in cells]
        await install(cells)
        packet = await observe(session, f"seed-layout-{name}", origin_x=ox, origin_z=oz)
        present = NativeVoxelPresentDev(
            session_id=packet.session_id, native_seq=packet.seq,
            request_id=packet.request_id, origin_x=float(ox), origin_z=float(oz),
            player_x=float(packet.player_x), player_z=float(packet.player_z),
            player_y=float(packet.player_y), coverage=packet.coverage,
            cells=tuple(VoxelColumnDev(c.dx,c.dz,c.feet,c.head,c.floor) for c in packet.cells),
            provenance=packet.provenance,
        )
        if present.cells != tuple(cells):
            raise RuntimeError(f"native layout did not match stimulus: {name}")
        choice = choose_grid_route_dev(
            present, goal, blocked_after_seq=after_seq, blocked_action_id=action_id,
            provenance=Provenance("s49-dev-layout", name),
        )
        expected = "DEFER" if name in ("SEALED", "UNSUPPORTED") else "SELECTED"
        if choice.status != expected:
            raise RuntimeError(f"unexpected seeded layout decision: {name} {choice.status}")
        reports.append({"name":name,"seed":seed,"gap":gap,
                        "native":asdict(present),"decision":choice.status,
                        "path":choice.chosen_cell_path,"actions_issued":0})
    if reports[0]["path"] == reports[1]["path"]:
        raise RuntimeError("seeded corridor change did not change route")
    await install(base.cells)
    restored = await observe(session, "seed-layout-restored", origin_x=ox, origin_z=oz)
    return reports, restored
