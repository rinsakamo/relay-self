"""DEV-only Paper producer tick hold inside original S49 S15 Action.

No new native command, owner, reader or timer override on normal S49.
The original S15 still sends the only eventual native clear and records S16.
"""
from __future__ import annotations

import asyncio
import math
from pathlib import Path


class OriginalOwnerTickHoldRejected(ValueError):
    """The original S49 Paper callback source or target was not witnessed."""


TARGET_PAPER_INDEX = 15
MATCHED_POSITIVE_TICKS = 7


def inspect_original_paper_hold_dev(
    raw: str, *, action_id: str, session_id: str,
) -> dict | None:
    """Validate available first-Action Paper rows; None before index 15."""
    if (
        type(raw) is not str or not raw
        or type(action_id) is not str or not action_id
        or type(session_id) is not str or not session_id
    ):
        raise OriginalOwnerTickHoldRejected("invalid original Paper hold identity")
    rows: list[dict] = []
    for line in raw.splitlines():
        if "S49_DASH_DEV_TICK " not in line:
            continue
        payload = line.split("S49_DASH_DEV_TICK ", 1)[1]
        fields = dict(t.split("=", 1) for t in payload.split() if t.count("=") == 1)
        if fields.get("action_id") != action_id:
            continue
        if fields.get("session_id") != session_id:
            raise OriginalOwnerTickHoldRejected("foreign native Action session")
        rows.append(fields)
    if len(rows) > 60:
        raise OriginalOwnerTickHoldRejected("unbounded producer callback")
    if not rows:
        return None
    first_world, first_player, first_tick = None, None, None
    positive = 0
    for i, fields in enumerate(rows, 1):
        try:
            index = int(fields["index"])
            tick = int(fields["tick"])
            p1idx = int(fields["p1_world_ticks"])
            power = float(fields["p1_current_applied_power"])
        except (ValueError, TypeError, KeyError) as exc:
            raise OriginalOwnerTickHoldRejected("Paper tick fields invalid") from exc
        if (
            index != i or p1idx != i
            or (first_tick is not None and tick != first_tick + 1)
            or not math.isfinite(power) or not 0 <= power <= 1
            or fields.get("modifier_applied") not in ("true", "false")
            or (fields["modifier_applied"] == "true") != (power > 0)
        ):
            raise OriginalOwnerTickHoldRejected("noncontiguous or inconsistent Paper gait")
        if first_world is None:
            first_world = fields.get("world")
            first_player = fields.get("player_uuid")
        if (
            not first_world or not first_player
            or fields.get("world") != first_world
            or fields.get("player_uuid") != first_player
        ):
            raise OriginalOwnerTickHoldRejected("Paper actor/World changed")
        if fields["modifier_applied"] == "true":
            positive += 1
            if i >= TARGET_PAPER_INDEX:
                raise OriginalOwnerTickHoldRejected("modifier active after held boundary")
        first_tick = tick
    if len(rows) < TARGET_PAPER_INDEX:
        return None
    if (
        positive != MATCHED_POSITIVE_TICKS
        or rows[TARGET_PAPER_INDEX - 1]["modifier_applied"] != "false"
    ):
        raise OriginalOwnerTickHoldRejected("seven-boost cap not exhausted at held tick")
    return {
        "classification": "ORIGINAL_S49_S15_PAPER_PRODUCER_TICK_HOLD_DEV_ONLY",
        "action_id": action_id,
        "session_id": session_id,
        "world": first_world,
        "player_uuid": first_player,
        "paper_first_sample_tick": int(rows[0]["tick"]),
        "paper_hold_target_sample_index": TARGET_PAPER_INDEX,
        "paper_hold_target_world_tick": int(rows[TARGET_PAPER_INDEX - 1]["tick"]),
        "paper_positive_boost_ticks_before_release": positive,
        "same_original_s15_clear_owner": True,
        "native_client_effect_world_tick_attested": False,
        "node_paper_host_clocks_synchronized": False,
        "native_action_duration_world_ticks_exact": False,
        "physical_p1_recovery_attested": False,
        "qualification_go": False,
        "science_go": False,
    }


async def await_original_paper_hold_dev(
    path: Path, *, action_id: str, session_id: str,
) -> dict:
    if (
        not isinstance(path, Path) or path.is_symlink() or not path.is_file()
        or type(action_id) is not str or not action_id
        or type(session_id) is not str or not session_id
    ):
        raise OriginalOwnerTickHoldRejected("unavailable original producer log")
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 2.0
    while loop.time() < deadline:
        if path.is_symlink() or path.stat().st_size > 8_000_000:
            raise OriginalOwnerTickHoldRejected("Paper producer source changed")
        raw = path.read_text(encoding="utf-8")
        result = inspect_original_paper_hold_dev(
            raw, action_id=action_id, session_id=session_id,
        )
        if result is not None:
            return result
        await asyncio.sleep(0.018)
    raise OriginalOwnerTickHoldRejected("original Paper target tick not delivered")
