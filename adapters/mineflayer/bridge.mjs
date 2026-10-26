import { randomUUID } from 'node:crypto'
import { createRequire } from 'node:module'
import { lstatSync, writeFileSync } from 'node:fs'
import { isAbsolute, join } from 'node:path'
import readline from 'node:readline'

import {
  attachHealthSynchronizedSpawnListeners,
  attachInventoryUpdateListenerAfterInjection,
  entityHurtPayload,
  resolveAttackEntity
} from './bridge_hooks.mjs'
import { attachV6NativeClockPackets } from './v6_native_clock.mjs'
import { projectS49DevMovementSpeed } from './s49_speed_attribute_bridge_dev.mjs'
import {
  admitProbeRequestId,
  makeEnvelope,
  makeProbePayload,
  parseArgs,
  parseCommand,
  shouldEmitTimeObservation,
  snapshotFromBot
} from './protocol.mjs'

const EXPECTED_MINEFLAYER_VERSION = '4.39.0'
// Same physical external dependency-root contract as frozen RSEE #588.
const nodeRuntimeRoot = process.env.RELAYSELF_RSEE_NODE_RUNTIME_ROOT
if (nodeRuntimeRoot &&
    (!isAbsolute(nodeRuntimeRoot) || lstatSync(nodeRuntimeRoot).isSymbolicLink() ||
     lstatSync(join(nodeRuntimeRoot, 'node_modules')).isSymbolicLink())) {
  process.stderr.write('RSEE Node runtime must be an absolute physical directory\n')
  process.exit(2)
}
const require = createRequire(nodeRuntimeRoot
  ? join(nodeRuntimeRoot, 'package.json')
  : import.meta.url)
const mineflayer = require('mineflayer')
const mineflayerPackage = require('mineflayer/package.json')

if (mineflayerPackage.version !== EXPECTED_MINEFLAYER_VERSION) {
  process.stderr.write(
    'expected mineflayer ' + EXPECTED_MINEFLAYER_VERSION +
    ' but loaded ' + String(mineflayerPackage.version) + '\n'
  )
  process.exit(2)
}

let config
try {
  config = parseArgs(process.argv.slice(2))
} catch (error) {
  process.stderr.write('invalid adapter arguments: ' + String(error.message || error) + '\n')
  process.exit(2)
}

// Explicit candidate only: never part of frozen S51 RSEE admission.
const clockOptIn = process.env.RELAYSELF_V6_NATIVE_CLOCK_V1
if (clockOptIn !== undefined && !['0', '1'].includes(clockOptIn)) {
  process.stderr.write('invalid V6 clock opt-in\n')
  process.exit(2)
}
if (clockOptIn === '1' && config.version !== '1.21.8') {
  process.stderr.write('V6 raw source requires explicit Minecraft 1.21.8\n')
  process.exit(2)
}
// DEV-only read-side schema opt-in. Never an Action command or signer.
const w4OrientationOptIn = process.env.RELAYSELF_W4_NH1_ORIENTATION_V0
if (w4OrientationOptIn !== undefined && !['0', '1'].includes(w4OrientationOptIn)) {
  process.stderr.write('invalid W4 orientation opt-in\n')
  process.exit(2)
}
if (w4OrientationOptIn === '1' && config.version !== '1.21.8') {
  process.stderr.write('W4 native orientation requires explicit Minecraft 1.21.8\n')
  process.exit(2)
}
const sessionId = randomUUID()
let seq = 0
let spawned = false
let closing = false
let inputReader = null
let lastObservedDay = null
let lastObservedIsDay = null
const seenActionIds = new Set()
const seenProbeRequestIds = new Set()

function emit (type, payload = {}) {
  const message = makeEnvelope(sessionId, seq, type, payload)
  seq += 1
  process.stdout.write(JSON.stringify(message) + '\n')
}

function emitAdapterError (error) {
  const message = String(error && error.message ? error.message : error)
  process.stderr.write(message + '\n')
  emit('adapter_error', { message })
}

function emitObservation (kind, requestId = undefined) {
  try {
    const snapshot = snapshotFromBot(bot, {
      includeNativeOrientation: w4OrientationOptIn === '1'
    })
    if (kind === 'probe') {
      emit('observation', makeProbePayload(snapshot, requestId))
    } else {
      emit('observation', { kind, snapshot })
    }
  } catch (error) {
    emitAdapterError(error)
  }
}

const options = {
  host: config.host,
  port: config.port,
  username: config.username,
  auth: 'offline',
  logErrors: false,
  respawn: true
}
if (config.version !== null) {
  options.version = config.version
}

emit('adapter_started', {
  mineflayer_version: mineflayerPackage.version,
  config
})

const bot = mineflayer.createBot(options)
const attrSyncDev = process.env.S49_SPEED_ATTR_SYNC_DEV_ONLY === '1' &&
  process.env.S49_SPRINT_MOTOR_DEV_ONLY === '1' && config.version === '1.21.8'
const attrDiag = process.env.S49_SPEED_ATTR_DIAG_DEV_ONLY === '1' &&
  process.env.S49_SPRINT_MOTOR_DEV_ONLY === '1' && config.version === '1.21.8'
// S49 DEV_ONLY producer-local Node physics witness, NOT a protocol message.
// Ring-buffer first original forward sprint only, seal on 5 physicsTicks
// following clearControls. No extra native reader, Action or server command.
const nativePhysicsTracePath = process.env.S49_NODE_PHYSICS_TRACE_DEV_PATH
const nativePhysicsTraceEnabled =
  process.env.S49_NODE_PHYSICS_TRACE_DEV_ONLY === '1' &&
  process.env.S49_SPRINT_MOTOR_DEV_ONLY === '1' &&
  config.version === '1.21.8' &&
  typeof nativePhysicsTracePath === 'string' &&
  isAbsolute(nativePhysicsTracePath)
let nativePhysicsTrace = null
let nativePhysicsSealed = false
let nativePhysicsIndex = 0
function captureNativePhysicsDev (phase) {
  if (!nativePhysicsTrace || nativePhysicsSealed || !bot.entity) return
  if (nativePhysicsTrace.rows.length >= 100) return
  const pos = bot.entity.position
  const vel = bot.entity.velocity
  if (!pos || !vel) return
  nativePhysicsTrace.rows.push({
    phase, index: nativePhysicsIndex,
    monotonic_ms: Number(process.hrtime.bigint() / 1000000n),
    forward: bot.getControlState('forward'),
    sprint: bot.getControlState('sprint'),
    back: bot.getControlState('back'),
    left: bot.getControlState('left'),
    right: bot.getControlState('right'),
    x: pos.x, z: pos.z, vx: vel.x, vz: vel.z,
    // Mineflayer time is a cached client snapshot, NOT a per-tick Paper clock.
    client_time_of_day_cached: bot.time ? bot.time.timeOfDay : null
  })
}
if (nativePhysicsTraceEnabled) {
  bot.on('physicsTick', () => {
    if (!nativePhysicsTrace || nativePhysicsSealed) return
    nativePhysicsIndex++
    const phase = nativePhysicsTrace.clear_seen ? 'POST_CLEAR' : 'ACTIVE'
    captureNativePhysicsDev(phase)
    if (phase !== 'POST_CLEAR') return
    nativePhysicsTrace.post_clear_ticks++
    if (nativePhysicsTrace.post_clear_ticks !== 5) return
    nativePhysicsSealed = true
    nativePhysicsTrace.complete = true
    try {
      // Exclusive create: a stale, duplicated or foreign trace cannot be
      // overwritten. Source evidence is Node-local and stays DEV_ONLY.
      writeFileSync(nativePhysicsTracePath, JSON.stringify(nativePhysicsTrace) + '\n',
        { flag: 'wx', encoding: 'utf8', mode: 0o600 })
    } catch (error) {
      emitAdapterError(new Error('S49_NODE_PHYSICS_TRACE_WRITE_FAILED'))
    }
  })
}
// The only physical input custodian remains this existing Mineflayer bot.
// Bounded DEV witness from original S15 first clear through second SET.
// This file provides NO Paper World-tick synchronization or WAIT authority.
const interActionPath = process.env.S49_INTER_ACTION_CONTROL_DEV_PATH
const interActionEnabled =
  nativePhysicsTraceEnabled &&
  process.env.S49_INTER_ACTION_CONTROL_DEV_ONLY === '1' &&
  typeof interActionPath === 'string' && isAbsolute(interActionPath)
let interActionTrace = null
function localControlsDev () {
  return ['forward', 'sprint', 'back', 'left', 'right', 'jump', 'sneak']
    .map(control => [control, bot.getControlState(control)])
}
if (interActionEnabled) {
  bot.on('physicsTick', () => {
    if (!interActionTrace || interActionTrace.complete) return
    if (!bot.entity || !bot.entity.position) {
      interActionTrace.overflow = true
      return
    }
    if (interActionTrace.rows.length >= 1200) {
      interActionTrace.overflow = true
      return
    }
    const controls = Object.fromEntries(localControlsDev())
    const pos = bot.entity.position
    interActionTrace.rows.push({
      ordinal: interActionTrace.rows.length + 1,
      monotonic_ms: Number(process.hrtime.bigint() / 1000000n),
      controls, x: pos.x, z: pos.z
    })
  })
}
function sealInterActionDev (command) {
  if (!interActionEnabled || !interActionTrace || interActionTrace.complete) return
  interActionTrace.second_action_id = command.action_id
  interActionTrace.before_second_set_controls =
    Object.fromEntries(localControlsDev())
  interActionTrace.complete = true
  try {
    writeFileSync(interActionPath, JSON.stringify(interActionTrace) + '\n',
      { flag: 'wx', encoding: 'utf8', mode: 0o600 })
  } catch (error) {
    emitAdapterError(new Error('S49_INTER_ACTION_CONTROL_WRITE_FAILED'))
  }
}
let attrDiagActive = false
let attrDiagSamples = 0
function traceDevAttr (stage, info = {}) {
  if (!attrDiag) return
  const entity = bot.entity
  const attrs = entity && entity.attributes ? entity.attributes : {}
  const selected = Object.fromEntries(Object.entries(attrs)
    .filter(([key]) => /movement.?speed|movementSpeed/.test(key))
    .map(([key, value]) => [key, {
      value: value && value.value,
      modifiers: value && value.modifiers
    }]))
  process.stderr.write('S49_SPEED_ATTR_DIAG ' + JSON.stringify({
    stage, selfEntityId: entity && entity.id,
    knownKeys: Object.keys(attrs).slice(0, 36),
    speedAttributes: selected,
    ...info
  }) + '\n')
}
if (attrDiag) {
  bot._client.on('entity_update_attributes', packet => {
    if (bot.entity && packet.entityId === bot.entity.id) {
      traceDevAttr('RAW_SPEED_PACKET', {
        rawPropertyCount: Array.isArray(packet.properties) ? packet.properties.length : null,
        properties: (packet.properties || []).slice(0, 36).map(p => ({
          key: p.key, base: p.value,
          modifierCount: Array.isArray(p.modifiers) ? p.modifiers.length : null,
          modifiers: (p.modifiers || []).slice(0, 3)
        }))
      })
    }
  })
  bot.on('entityAttributes', entity => {
    if (bot.entity && entity.id === bot.entity.id) traceDevAttr('DECODED_SPEED_PACKET')
  })
  bot.on('physicsTick', () => {
    if (!attrDiagActive || attrDiagSamples >= 20) return
    attrDiagSamples++
    traceDevAttr('MOTOR_PHYSICS', {
      sample: attrDiagSamples, onGround: bot.entity.onGround,
      controlForward: bot.getControlState('forward'),
      controlSprint: bot.getControlState('sprint'),
      pos: bot.entity.position,
      velocity: bot.entity.velocity
    })
  })
}
if (attrSyncDev) {
  bot.on('entityAttributes', entity => {
    if (!attrDiagActive || !bot.entity || entity.id !== bot.entity.id) return
    const attrs = entity.attributes
    const projected = projectS49DevMovementSpeed(attrs && attrs['generic.scale'])
    if (projected === null) {
      delete attrs['minecraft:movement_speed']
      traceDevAttr('SPEED_SYNC_REJECTED')
      return
    }
    attrs['minecraft:movement_speed'] = projected.attribute
    traceDevAttr('SPEED_SYNC_APPLIED', {
      projectedDash: projected.dash,
      projectedValue: projected.attribute.value,
      projectedModifiers: projected.attribute.modifiers
    })
  })
}
if (clockOptIn === '1') {
  attachV6NativeClockPackets(
    bot,
    (sample) => emit('native_clock_packet', sample),
    (error) => emitAdapterError(error)
  )
}

attachHealthSynchronizedSpawnListeners(
  bot,
  () => {
    spawned = true
    emitObservation('spawn')
  },
  () => {
    if (spawned) emitObservation('health')
  }
)

bot.on('time', () => {
  if (!spawned) return
  if (
    !bot.time ||
    !Number.isFinite(bot.time.day) ||
    typeof bot.time.isDay !== 'boolean'
  ) return

  if (!shouldEmitTimeObservation(
    lastObservedDay,
    lastObservedIsDay,
    bot.time
  )) return

  lastObservedDay = bot.time.day
  lastObservedIsDay = bot.time.isDay
  emitObservation('time')
})

attachInventoryUpdateListenerAfterInjection(bot, () => {
  if (spawned) emitObservation('inventory')
})

bot.on('entitySpawn', (entity) => {
  if (spawned && entity.id !== bot.entity.id) emitObservation('entities')
})

bot.on('entityGone', (entity) => {
  if (spawned && entity.id !== bot.entity.id) emitObservation('entities')
})

bot.on('entityHurt', (entity, source) => {
  if (!spawned) return
  try {
    emit(
      'entity_hurt',
      entityHurtPayload(entity, source, bot.entity.id)
    )
  } catch (error) {
    emitAdapterError(error)
  }
})

bot.on('move', () => {
  if (spawned) emitObservation('move')
})

bot.on('forcedMove', () => {
  if (spawned) emitObservation('forcedMove')
})

bot.on('death', () => {
  if (spawned) emitObservation('death')
  spawned = false
})

bot.on('respawn', () => {
  spawned = true
  emitObservation('respawn')
})

bot.on('error', (error) => {
  emitAdapterError(error)
})

bot.on('end', (reason) => {
  spawned = false
  emit('connection_end', { reason: String(reason || 'connection ended') })
  if (inputReader !== null) inputReader.close()
  process.exitCode = closing ? 0 : 3
})

function emitEffectResult (command, result, error = null) {
  emit('effect_result', {
    action_id: command.action_id,
    effect: command.effect,
    result,
    error
  })
}

async function handleEffect (command) {
  if (seenActionIds.has(command.action_id)) {
    emitEffectResult(command, 'rejected', 'duplicate_action_id')
    return
  }
  seenActionIds.add(command.action_id)

  if (!spawned) {
    emitEffectResult(command, 'rejected', 'not_spawned')
    return
  }

  try {
    if (command.effect === 'set_control') {
      bot.setControlState(command.control, command.state)
      emitEffectResult(command, 'applied')
      return
    }

    if (command.effect === 'set_forward_sprint_dev') {
      if (process.env.S49_SPRINT_MOTOR_DEV_ONLY !== '1' ||
          command.forward !== true || command.sprint !== true) {
        emitEffectResult(command, 'rejected', 'sprint_dev_gate_or_pair')
        return
      }
      sealInterActionDev(command)
      try {
        bot.setControlState('sprint', true)
        bot.setControlState('forward', true)
      } catch (error) {
        bot.clearControlStates()
        throw error
      }
      if (nativePhysicsTraceEnabled && nativePhysicsTrace === null) {
        nativePhysicsTrace = {
          version: 'S49_NODE_PHYSICS_POST_CLEAR_DEV_V1',
          action_id: command.action_id,
          session_id: sessionId,
          post_clear_ticks: 0, clear_seen: false,
          complete: false, source_attested: false, rows: []
        }
        captureNativePhysicsDev('SET')
      }
      attrDiagActive = true
      attrDiagSamples = 0
      traceDevAttr('SPRINT_DISPATCH_APPLIED')
      emitEffectResult(command, 'applied')
      return
    }

    if (command.effect === 'clear_controls') {
      bot.clearControlStates()
      if (nativePhysicsTraceEnabled && nativePhysicsTrace !== null &&
          !nativePhysicsTrace.clear_seen) {
        nativePhysicsTrace.clear_seen = true
        captureNativePhysicsDev('CLEAR')
        if (interActionEnabled && interActionTrace === null) {
          interActionTrace = {
            version: 'S49_NODE_INTER_ACTION_INPUT_OFF_DEV_V1',
            session_id: sessionId,
            first_action_id: nativePhysicsTrace.action_id,
            first_cleanup_action_id: command.action_id,
            source_attested: false, clock_synchronized: false,
            complete: false, overflow: false,
            start_controls: Object.fromEntries(localControlsDev()),
            rows: []
          }
        }
      }
      if (attrSyncDev && bot.entity && bot.entity.attributes) {
        delete bot.entity.attributes['minecraft:movement_speed']
      }
      traceDevAttr('ACTION_CLEAR')
      attrDiagActive = false
      emitEffectResult(command, 'applied')
      return
    }

    if (command.effect === 'equip_item') {
      const item = bot.inventory.items().find(
        (candidate) => candidate.name === command.item_name
      )
      if (!item) {
        emitEffectResult(command, 'rejected', 'item_not_found')
        return
      }
      await bot.equip(item, 'hand')
      emitEffectResult(command, 'applied')
      return
    }

    if (command.effect === 'consume_held') {
      if (!bot.heldItem) {
        emitEffectResult(command, 'rejected', 'no_held_item')
        return
      }
      await bot.consume()
      emitEffectResult(command, 'applied')
      return
    }

    if (command.effect === 'look') {
      // S-owned disposable FLAT P1 launch can request immediate server
      // yaw synchronization without adding fields to the frozen protocol.
      // All historical/default LOOK effects retain the prior behavior.
      await bot.look(
        command.yaw, command.pitch,
        process.env.RELAY_S50_P1_FLAT_FORCE_SERVER_LOOK_DEV === '1'
      )
      emitEffectResult(command, 'applied')
      return
    }

    if (command.effect === 'attack_entity') {
      const target = resolveAttackEntity(bot, command.entity_id)
      await bot.attack(target)
      emitEffectResult(command, 'applied')
      return
    }

    emitEffectResult(command, 'rejected', 'unsupported_effect')
  } catch (error) {
    emitEffectResult(
      command,
      'rejected',
      String(error && error.message ? error.message : error)
    )
  }
}

function handleShutdown () {
  closing = true
  if (spawned) {
    bot.clearControlStates()
    if (attrSyncDev && bot.entity && bot.entity.attributes) {
      delete bot.entity.attributes['minecraft:movement_speed']
    }
  }
  emit('shutdown_ack')
  if (inputReader !== null) inputReader.close()
  bot.quit('RelaySelf adapter shutdown')
}

async function handleLine (line) {
  let raw
  try {
    raw = JSON.parse(line)
  } catch (error) {
    emit('command_error', { message: 'invalid_json' })
    return
  }

  let command
  try {
    command = parseCommand(raw)
  } catch (error) {
    emit('command_error', {
      message: String(error && error.message ? error.message : error)
    })
    return
  }

  if (command.type === 'effect') {
    await handleEffect(command)
    return
  }

  if (command.type === 'observe') {
    if (!spawned) {
      emit('command_error', { message: 'observe_before_spawn' })
      return
    }
    if (command.request_id !== undefined) {
      if (!admitProbeRequestId(seenProbeRequestIds, command.request_id)) {
        emit('command_error', { message: 'duplicate_probe_request_id' })
        return
      }
    }
    emitObservation('probe', command.request_id)
    return
  }

  if (command.type === 'shutdown') {
    handleShutdown()
  }
}

inputReader = readline.createInterface({
  input: process.stdin,
  crlfDelay: Infinity
})

let commandQueue = Promise.resolve()
inputReader.on('line', (line) => {
  commandQueue = commandQueue
    .then(() => handleLine(line))
    .catch((error) => {
      emitAdapterError(error)
    })
})
