import { randomUUID } from 'node:crypto'
import { createRequire } from 'node:module'
import { appendFileSync } from 'node:fs'
import readline from 'node:readline'

import {
  attachHealthSynchronizedSpawnListeners,
  attachInventoryUpdateListenerAfterInjection,
  entityHurtPayload,
  probeIdentityWitness,
  resolveAttackEntity
} from './bridge_hooks.mjs'
import { inspectInstalled } from './oxygen_owner_patch.mjs'
import { OwnedOxygenWitness } from './oxygen_owner_witness.mjs'
import { Q4BoundedPlaceMotionGuard } from './bounded_place_guard.mjs'
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
const require = createRequire(import.meta.url)
// Refuse unowned oxygen metadata BEFORE spawning a real native bot.
let oxygenPatch
try {
  oxygenPatch = inspectInstalled()
  if (oxygenPatch.status !== 'PATCHED') {
    throw new Error('explicit Mineflayer oxygen owner backport missing')
  }
} catch (error) {
  process.stderr.write('STAGE24D_OXYGEN_SOURCE_HOLD=' + String(error.message || error) + '\n')
  process.exit(2)
}
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

const sessionId = randomUUID()
const ownedOxygen = new OwnedOxygenWitness({ sessionId })
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
    const receipt = ownedOxygen.read(bot.entity?.id)
    const snapshot = snapshotFromBot(bot, receipt)
    if (kind === 'probe') {
      // A passive witness is a separate source audit, not an added field to
      // the original strict native protocol or a physical action authority.
      if (process.env.RELAY_P0B_OXYGEN_WITNESS_PATH) {
        appendFileSync(process.env.RELAY_P0B_OXYGEN_WITNESS_PATH, JSON.stringify({
          ...receipt,
          native_session_id: sessionId,
          native_seq: seq,
          native_request_id: requestId ?? null
        }) + '\n')
      }
      if (process.env.RELAY_P0B_IDENTITY_WITNESS_PATH) {
        appendFileSync(process.env.RELAY_P0B_IDENTITY_WITNESS_PATH, JSON.stringify(
          probeIdentityWitness(bot, snapshot, sessionId, seq)
        ) + '\n')
      }
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
const q4BoundedDev = process.env.RELAY_Q4_BOUNDED_PLACE_DEV === '1'
const q4PlaceGuard = q4BoundedDev
  ? new Q4BoundedPlaceMotionGuard(bot, {
      onTrip: (reason) => {
        // Native guard, not an ACK/settling receipt. Fail closed by ending
        // this bot generation when a time/distance/sample cap trips.
        emitAdapterError(new Error('Q4_NATIVE_PLACE_TRIP_' + reason))
        bot.quit('RelaySelf Q4 bounded motion trip')
      }
    })
  : null

attachHealthSynchronizedSpawnListeners(
  bot,
  () => {
    ownedOxygen.bindSelf(bot.entity?.id)
    spawned = true
    emitObservation('spawn')
  },
  () => {
    if (spawned) emitObservation('health')
  }
)

// Source is the *patched* self-only metadata 'breath' event. The witness
// resets at each body generation and has an explicit finite freshness window.
bot.on('breath', () => {
  if (spawned) {
    ownedOxygen.acceptBreath({
      entityId: bot.entity?.id,
      oxygenLevel: bot.oxygenLevel
    })
  }
})

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
  if (q4PlaceGuard !== null) q4PlaceGuard.trip('native_death')
  if (spawned) emitObservation('death')
  ownedOxygen.invalidate()
  spawned = false
})

bot.on('respawn', () => {
  ownedOxygen.bindSelf(bot.entity?.id)
  spawned = true
  emitObservation('respawn')
})

bot.on('error', (error) => {
  emitAdapterError(error)
})

bot.on('end', (reason) => {
  if (q4PlaceGuard !== null) q4PlaceGuard.stop()
  ownedOxygen.invalidate()
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
      if (q4PlaceGuard !== null) {
        if (command.control !== 'forward' || command.state !== true) {
          emitEffectResult(command, 'rejected', 'q4_walk_only')
          return
        }
        q4PlaceGuard.start(command.action_id)
      } else {
        bot.setControlState(command.control, command.state)
      }
      emitEffectResult(command, 'applied')
      return
    }

    if (command.effect === 'clear_controls') {
      if (q4PlaceGuard !== null) q4PlaceGuard.stop()
      else bot.clearControlStates()
      emitEffectResult(command, 'applied')
      return
    }

    if (q4BoundedDev && command.effect !== 'look') {
      emitEffectResult(command, 'rejected', 'q4_only_place_look_start_stop')
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
      await bot.look(command.yaw, command.pitch)
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
  if (q4PlaceGuard !== null) q4PlaceGuard.stop()
  if (spawned) {
    bot.clearControlStates()
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
