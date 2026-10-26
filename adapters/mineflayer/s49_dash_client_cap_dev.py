"""DEV-only one-client motor cap, scoped to SECOND original S49 BACK Action.

Generate a temporary sibling bridge.mjs (same imports, one sole session).
The original JS/JSONL protocol and Action authority are unchanged. For the
second already-issued BACK effect only, the physical executor also applies
Minecraft's native SNEAK slow control; normal S49 CLEAR resets both.
This is a conservative cap feasibility probe, NOT the final side/back speed.
"""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected

BRIDGE_SOURCE = Path(__file__).with_name("bridge.mjs")
PREFIX = ".relay-s49-dash-client-cap-dev-"


def instrument_backward_sneak_dev(receipt_path: Path) -> Path:
    if (
        not receipt_path.is_absolute()
        or not receipt_path.parent.is_dir()
        or receipt_path.exists()
        or receipt_path.is_symlink()
        or BRIDGE_SOURCE.is_symlink()
    ):
        raise BoundaryRejected("fresh absolute DEV receipt path required")
    source = BRIDGE_SOURCE.read_text(encoding="utf-8")
    replacements = (
        (
            "import { lstatSync } from 'node:fs'",
            "import { lstatSync, appendFileSync } from 'node:fs'",
        ),
        (
            "const seenProbeRequestIds = new Set()",
            """const seenProbeRequestIds = new Set()
const dashClientCapDevReceipt = """ + json.dumps(str(receipt_path)) + """
let dashClientCapDevBackCount = 0
""",
        ),
        (
            """      bot.setControlState(command.control, command.state)
      emitEffectResult(command, 'applied')""",
            """      bot.setControlState(command.control, command.state)
      if (command.control === 'back' && command.state === true) {
        dashClientCapDevBackCount += 1
        if (dashClientCapDevBackCount > 2) {
          bot.clearControlStates()
          emitEffectResult(command, 'rejected', 'dev_back_action_overrun')
          return
        }
        if (dashClientCapDevBackCount === 2) {
          // Same S49 BACK Action, one Node effect and one receipt: cap gait
          // physically in Mineflayer. No additional action/JSONL command.
          bot.setControlState('sneak', true)
          appendFileSync(dashClientCapDevReceipt, JSON.stringify({
            schema: 'S49_DASH_CLIENT_BACK_SNEAK_DEV_V1',
            action_id: command.action_id, original_control: 'back',
            additional_gait_control: 'sneak', original_effect_count: 1,
            new_action_issuer: false, server_tick_attested: false,
            source_authenticated_by_file_alone: false
          }) + '\\n')
        }
      }
      emitEffectResult(command, 'applied')""",
        ),
    )
    for before, after in replacements:
        if source.count(before) != 1:
            raise BoundaryRejected("original Node bridge changed or dev seam missing")
        source = source.replace(before, after, 1)
    dev_path = BRIDGE_SOURCE.with_name(PREFIX + uuid4().hex + ".mjs")
    try:
        with dev_path.open("x", encoding="utf-8") as stream:
            stream.write(source)
    except BaseException:
        dev_path.unlink(missing_ok=True)
        raise
    return dev_path


def remove_backward_sneak_dev(path: Path) -> None:
    if (
        path.parent != BRIDGE_SOURCE.parent
        or not path.name.startswith(PREFIX)
        or path.suffix != ".mjs"
        or path.is_symlink()
    ):
        raise BoundaryRejected("cannot remove non-DEV bridge")
    path.unlink(missing_ok=True)
