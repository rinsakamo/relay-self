import { randomUUID } from 'node:crypto'
import { createRequire } from 'node:module'
import { lstatSync } from 'node:fs'
import { isAbsolute, join } from 'node:path'
import readline from 'node:readline'

import {
  attachHealthSynchronizedSpawnListeners,
  attachInventoryUpdateListenerAfterInjection,
  entityHurtPayload,
  resolveAttackEntity
} from './bridge_hooks.mjs'
import { attachV6NativeClockPackets } from './v6_native_clock.mjs'
import { attachPaperTickChannel } from './paper_tick_channel.mjs'
import { evaluatePaperL0Shadow } from './paper_l0_shadow.mjs'
import { PaperTickDeadlineGuard, handleBudgetedPaperTick } from './paper_tick_deadline.mjs'
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
// Explicitly opt-in. Both time and Action events remain on the same native
// Mineflayer stdout receiver (no new process, socket, or physical issuer).
const paperTickOptIn = process.env.RELAYSELF_PAPER_TICK_DEV
if (paperTickOptIn !== undefined && !['0', '1'].includes(paperTickOptIn)) {
  process.stderr.write('invalid Paper tick DEV opt-in\n')
  process.exit(2)
}
if (paperTickOptIn === '1' && config.version !== '1.21.8') {
  process.stderr.write('Paper tick DEV requires explicit 1.21.8\n')
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
    const snapshot = snapshotFromBot(bot)
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
if (paperTickOptIn === '1') {
  const deadline = new PaperTickDeadlineGuard()
  attachPaperTickChannel(
    bot,
    (sample) => handleBudgetedPaperTick(sample, bot, {
      guard: deadline,
      evaluateShadow: evaluatePaperL0Shadow,
      emit,
      clock: () => process.hrtime.bigint()
    }),
    (error) => emitAdapterError(error)
  )
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

    if (command.effect === 'clear_controls') {
      bot.clearControlStates()
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
