"""One disposable Mineflayer physics sync; original bridge remains fixed.

The source is cloned as a temporary sibling ESM to preserve relative imports.
Only exact operator-DEV dash-sprint control synchronizes the client-side
movement attribute with Paper's dedicated +0.50 modifier. This does not
authorize any S Action. No global toggles, new input receiver, or retries.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected

SOURCE = Path(__file__).with_name("bridge.mjs")
PREFIX = ".relay-p1-dash-physics-dev-"


def _replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise BoundaryRejected("Mineflayer source changed: refuse DEV motor patch")
    return text.replace(old, new, 1)


def install_dev_bridge() -> Path:
    source = SOURCE.read_text(encoding="utf-8")
    source = _replace_once(
        source,
        "const seenProbeRequestIds = new Set()",
        """const seenProbeRequestIds = new Set()
let p1DashOldAttribute = undefined
let p1DashOldKey = undefined
let p1DashActive = false
function p1DashSyncDev(enable) {
  if (!bot.entity || !bot.physics || !bot.entity.attributes) {
    throw new Error('DEV physics attributes unavailable')
  }
  if (enable) {
    if (p1DashActive) throw new Error('DEV DASH physics already active')
    const key = bot.physics.movementSpeedAttribute
    if (typeof key !== 'string' || key.length === 0) {
      throw new Error('DEV physics attribute key unavailable')
    }
    p1DashOldKey = key
    p1DashOldAttribute = Object.hasOwn(bot.entity.attributes, key)
      ? structuredClone(bot.entity.attributes[key]) : undefined
    const fallback = p1DashOldAttribute && p1DashOldAttribute.value > 0
      ? p1DashOldAttribute.value : 0.1
    // DEV-only client prediction matches Paper's +0.5 scalar modifier.
    const base = p1DashOldAttribute && Array.isArray(p1DashOldAttribute.modifiers)
      ? p1DashOldAttribute.modifiers.filter(m => m.uuid !== 'relay-p1-dash-dev')
      : []
    bot.entity.attributes[key] = {
      value: fallback,
      modifiers: [...base, { uuid: 'relay-p1-dash-dev', amount: 0.5, operation: 2 }]
    }
    p1DashActive = true
  } else if (p1DashActive) {
    if (p1DashOldAttribute === undefined) {
      delete bot.entity.attributes[p1DashOldKey]
    } else {
      bot.entity.attributes[p1DashOldKey] = p1DashOldAttribute
    }
    p1DashActive = false
    p1DashOldKey = undefined
    p1DashOldAttribute = undefined
  }
}
""",
    )
    source = _replace_once(
        source,
        """      bot.setControlState(command.control, command.state)
      emitEffectResult(command, 'applied')""",
        """      bot.setControlState(command.control, command.state)
      if (command.action_id === 'dash-sprint') {
        if (command.control !== 'sprint' || command.state !== true ||
            bot.getControlState('back') || bot.getControlState('left') ||
            bot.getControlState('right') || !bot.getControlState('forward')) {
          throw new Error('DEV DASH client requires forward sprint only')
        }
        p1DashSyncDev(true)
      }
      emitEffectResult(command, 'applied')""",
    )
    source = _replace_once(
        source,
        """      bot.clearControlStates()
      emitEffectResult(command, 'applied')""",
        """      bot.clearControlStates()
      p1DashSyncDev(false)
      emitEffectResult(command, 'applied')""",
    )
    source = _replace_once(
        source,
        """    bot.clearControlStates()
  }
  emit('shutdown_ack')""",
        """    bot.clearControlStates()
    p1DashSyncDev(false)
  }
  emit('shutdown_ack')""",
    )
    target = SOURCE.with_name(PREFIX + uuid4().hex + ".mjs")
    if SOURCE.is_symlink() or target.exists():
        raise BoundaryRejected("DEV bridge source or output invalid")
    try:
        with target.open("x", encoding="utf-8") as out:
            out.write(source)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return target


def remove_dev_bridge(path: Path) -> None:
    if (path.parent != SOURCE.parent or not path.name.startswith(PREFIX)
            or path.suffix != ".mjs" or path.is_symlink()):
        raise BoundaryRejected("unexpected DEV generated bridge")
    path.unlink(missing_ok=True)
