"""Generated DEV-only Mineflayer attribute / physics readback, never core bridge.

Uses the same sole Node bridge and unchanged stdout protocol. Optional explicit
mirror mode changes only the throwaway local Mineflayer movement speed state,
matching an independently armed Paper modifier. No S49 Action changes.
"""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected

BRIDGE = Path(__file__).with_name("bridge.mjs")
PREFIX = ".relay-s49-dash-attr-dev-"


def generate_forward_attr_bridge_dev(log_path: Path, *, mirror_speed: bool = False) -> Path:
    if type(mirror_speed) is not bool:
        raise BoundaryRejected("explicit boolean client speed mirror mode required")
    if (not log_path.is_absolute() or not log_path.parent.is_dir()
            or log_path.exists() or log_path.is_symlink()
            or BRIDGE.is_symlink()):
        raise BoundaryRejected("fresh isolated forward client attribute telemetry required")
    source = BRIDGE.read_text("utf-8")
    mirror_logic = """
let devMirrorOwned = null
function syncDevMirror() {
  if (!devMirrorEnabled) return
  const key = bot.physics?.movementSpeedAttribute
  const c = bot.controlState
  const canBoost = devAttrEnabled && c && c.forward && c.sprint &&
    !c.back && !c.left && !c.right && !c.sneak
  if (canBoost && devMirrorOwned === null) {
    if (key !== 'minecraft:movement_speed' ||
        !bot.entity?.attributes ||
        bot.entity.attributes[key] !== undefined ||
        bot.physics?.playerSpeed !== 0.1) {
      throw new Error('foreign or unmatched self movement attribute; fail closed')
    }
    const own = { value: 0.1, modifiers: [{
      uuid: '2390810b-946c-4b51-8400-4aba4c042031',
      amount: 0.5, operation: 2
    }] }
    bot.entity.attributes[key] = own
    devMirrorOwned = own
  }
  if (!canBoost && devMirrorOwned !== null) {
    if (bot.entity.attributes[key] !== devMirrorOwned) {
      throw new Error('self movement attribute replaced while mirrored')
    }
    delete bot.entity.attributes[key]
    devMirrorOwned = null
  }
}
"""
    edits = (
        ("import { lstatSync } from 'node:fs'",
         "import { lstatSync, appendFileSync } from 'node:fs'"),
        ("const seenProbeRequestIds = new Set()",
         """const seenProbeRequestIds = new Set()
let devAttrEnabled = false
const devMirrorEnabled = """ + ("true" if mirror_speed else "false") + """
""" + mirror_logic + """

let devAttrTickCount = 0
const devAttrFile = """ + json.dumps(str(log_path)) + """
function writeDevAttr() {
  if (!devAttrEnabled || devAttrTickCount++ >= 30) return
  const key = bot.physics?.movementSpeedAttribute
  const keys = Object.keys(bot.entity?.attributes || {})
  const attr = key ? bot.entity?.attributes?.[key] : null
  appendFileSync(devAttrFile, JSON.stringify({
    tick_index: devAttrTickCount,
    minecraft_movement_speed_resource: key,
    player_speed_physics: bot.physics?.playerSpeed,
    self_attribute_keys: keys,
    self_attribute: attr || null,
    control_sprint: bot.controlState?.sprint ?? null,
    entity_sprinting: bot.entity?.isSprinting ?? null,
    on_ground: bot.entity?.onGround ?? null,
    dash_issuer_is_original_s49: false
  }) + '\\n')
}
"""),
        ("bot.on('move', () => {",
         """bot.on('physicsTick', () => { syncDevMirror(); writeDevAttr() })

bot.on('move', () => {"""),
        ("""      bot.setControlState(command.control, command.state)
      emitEffectResult(command, 'applied')""",
         """      bot.setControlState(command.control, command.state)
      if (command.action_id === 's49-forward-operator-dev-dash-sprint' &&
          command.control === 'sprint' && command.state === true) {
        devAttrEnabled = true
        syncDevMirror()
      }
      emitEffectResult(command, 'applied')"""),
    )
    for before, after in edits:
        if source.count(before) != 1:
            raise BoundaryRejected("frozen bridge attribute instrumentation point changed")
        source = source.replace(before, after, 1)
    if mirror_speed:
        before = """      bot.clearControlStates()
      emitEffectResult(command, 'applied')"""
        after = """      bot.clearControlStates()
      devAttrEnabled = false
      syncDevMirror()
      emitEffectResult(command, 'applied')"""
        if source.count(before) != 1:
            raise BoundaryRejected("clear hook changed; cannot restore mirror")
        source = source.replace(before, after, 1)
        before = """    bot.clearControlStates()
  }
  emit('shutdown_ack')"""
        after = """    bot.clearControlStates()
    devAttrEnabled = false
    syncDevMirror()
  }
  emit('shutdown_ack')"""
        if source.count(before) != 1:
            raise BoundaryRejected("shutdown hook changed; cannot restore mirror")
        source = source.replace(before, after, 1)
    target = BRIDGE.with_name(PREFIX + uuid4().hex + ".mjs")
    with target.open("x", encoding="utf-8") as sink:
        sink.write(source)
    return target


def remove_forward_attr_bridge_dev(path: Path) -> None:
    if (path.parent != BRIDGE.parent or not path.name.startswith(PREFIX)
            or path.suffix != ".mjs" or path.is_symlink()):
        raise BoundaryRejected("foreign client diagnostic bridge")
    path.unlink(missing_ok=True)
