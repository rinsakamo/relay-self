import { randomUUID } from 'node:crypto'
import { createRequire } from 'node:module'
import readline from 'node:readline'

import {
  attachHealthSynchronizedSpawnListeners,
  attachInventoryUpdateListenerAfterInjection
} from './bridge_hooks.mjs'
import {
  makeEnvelope,
  parseArgs,
  parseCommand,
  shouldEmitTimeObservation,
  snapshotFromBot
} from './protocol.mjs'

const EXPECTED_MINEFLAYER_VERSION = '4.39.0'
const require = createRequire(import.meta.url)
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
let seq = 0
let spawned = false
let closing = false
let inputReader = null
let lastObservedDay = null
let lastObservedIsDay = null
const seenActionIds = new Set()

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

function emitObservation (kind) {
  try {
    emit('observation', {
      kind,
      snapshot: snapshotFromBot(bot)
    })
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
      await bot.look(command.yaw, command.pitch)
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
