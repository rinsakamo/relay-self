"""DEV-only native S49 motor-clock observer: instrument a temporary bridge copy.

The original bridge.mjs and original S49 owner/protocol remain untouched.
A generated sibling ESM file has the same imports, sends the identical
stdout JSONL protocol, and adds bounded synchronous, file-only clock rows.
Instrumentation *can perturb scheduling*. Node hrtime and Paper fullTime
are distinct clocks. Nothing here attests Paper-effective control ticks.
"""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected

BRIDGE_SOURCE = Path(__file__).with_name("bridge.mjs")
PREFIX = ".relay-s49-motor-clock-dev-"
MARKER = "DEV_MOTOR_CLOCK_V0"


def _one(source: str, before: str, after: str) -> str:
    if source.count(before) != 1:
        raise BoundaryRejected("original bridge instrumentation point changed")
    return source.replace(before, after, 1)


def instrument_native_bridge_dev(log_path: Path) -> Path:
    """Clone the bridge for ONE disposable session; no second receive owner."""
    if (not log_path.is_absolute() or not log_path.parent.is_dir()
            or log_path.exists() or log_path.is_symlink()
            or BRIDGE_SOURCE.is_symlink()):
        raise BoundaryRejected("fresh absolute isolated telemetry path required")
    source = BRIDGE_SOURCE.read_text("utf-8")
    source = _one(source,
        "import { lstatSync } from 'node:fs'",
        "import { lstatSync, appendFileSync } from 'node:fs'")
    source = _one(source,
        "const seenProbeRequestIds = new Set()",
        """const seenProbeRequestIds = new Set()
const motionClockDevFile = """ + json.dumps(str(log_path)) + """
let motionClockDevIndex = 0
let motionClockDevTicks = 0
let motionClockDevActive = null
const motionClockDevSeen = new Set()
function motionClockDevRow(kind, actionId) {
  if (motionClockDevIndex >= 120) return
  const xyz = spawned && bot.entity && bot.entity.position
    ? { x: bot.entity.position.x, z: bot.entity.position.z } : null
  appendFileSync(motionClockDevFile, JSON.stringify({
    schema: 'DEV_MOTOR_CLOCK_V0', kind, action_id: actionId,
    index: motionClockDevIndex++,
    node_monotonic_ns: process.hrtime.bigint().toString(),
    mineflayer_physics_tick_counter: motionClockDevTicks,
    mineflayer_position_xz: xyz,
    paper_world_tick_attested: false,
    new_action_issuer: false
  }) + '\\n')
}
""")
    source = _one(source,
        "bot.on('move', () => {",
        """bot.on('physicsTick', () => {
  motionClockDevTicks += 1
  if (motionClockDevActive !== null) {
    motionClockDevRow('physics_tick', motionClockDevActive)
  }
})

bot.on('move', () => {""")
    source = _one(source,
        """      bot.setControlState(command.control, command.state)
      emitEffectResult(command, 'applied')""",
        """      bot.setControlState(command.control, command.state)
      if (command.control === 'back' && command.state === true &&
          !motionClockDevSeen.has(command.action_id)) {
        motionClockDevSeen.add(command.action_id)
        motionClockDevActive = command.action_id
        motionClockDevRow('back_on', command.action_id)
      }
      emitEffectResult(command, 'applied')""")
    source = _one(source,
        """      bot.clearControlStates()
      emitEffectResult(command, 'applied')""",
        """      bot.clearControlStates()
      if (motionClockDevActive !== null) {
        motionClockDevRow('back_off', motionClockDevActive)
        motionClockDevActive = null
      }
      emitEffectResult(command, 'applied')""")
    dev_path = BRIDGE_SOURCE.with_name(PREFIX + uuid4().hex + ".mjs")
    try:
        with dev_path.open("x", encoding="utf-8") as out:
            out.write(source)
    except BaseException:
        dev_path.unlink(missing_ok=True)
        raise
    return dev_path


def remove_native_bridge_dev(path: Path) -> None:
    if (path.parent != BRIDGE_SOURCE.parent or not path.name.startswith(PREFIX)
            or path.suffix != ".mjs" or path.is_symlink()):
        raise BoundaryRejected("cannot remove non-DEV bridge")
    path.unlink(missing_ok=True)
