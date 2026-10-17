// S-owned, opt-in DEV process wrapper. Import the unmodified Mineflayer bridge.
// Reads all seven Mineflayer getControlState values directly; never claims
// Paper-effective motor state or derives a shared clock from this client source.
import { createRequire } from 'node:module'
import { closeSync, lstatSync, openSync, writeSync } from 'node:fs'
import { isAbsolute, join } from 'node:path'

const path = process.env.RELAYSELF_S50_P1_READBACK_FILE
const runtimeRoot = process.env.RELAYSELF_RSEE_NODE_RUNTIME_ROOT
if (!path || !isAbsolute(path) || path.length > 4096) {
  throw new Error('S50 native readback requires absolute fresh evidence file')
}
if (runtimeRoot && (!isAbsolute(runtimeRoot) ||
    lstatSync(runtimeRoot).isSymbolicLink() ||
    lstatSync(join(runtimeRoot, 'node_modules')).isSymbolicLink())) {
  throw new Error('S50 Node runtime root must be physical')
}
const fd = openSync(path, 'wx', 0o600)
process.on('exit', () => closeSync(fd))
const require = createRequire(runtimeRoot
  ? join(runtimeRoot, 'package.json')
  : import.meta.url)
const mineflayer = require('mineflayer')
const controls = Object.freeze([
  'forward', 'back', 'left', 'right', 'jump', 'sprint', 'sneak'
])
let bot = null
let sessionId = null
let ordinal = 0
let physicsTick = 0
let capped = false
const MAX_ROWS = 8192

function write (record) {
  ordinal += 1
  if (ordinal > MAX_ROWS) {
    if (!capped) {
      capped = true
      writeSync(fd, JSON.stringify({
        source: 'S50_DEV_NATIVE_READBACK_V1',
        ordinal, kind: 'TRUNCATED', session_id: sessionId
      }) + '\n')
    }
    return
  }
  writeSync(fd, JSON.stringify({
    source: 'S50_DEV_NATIVE_READBACK_V1',
    ordinal,
    session_id: sessionId,
    client_physics_tick: physicsTick,
    ...record
  }) + '\n')
}

function readAll (kind, nativeSeq = null, nativeAction = null) {
  if (!sessionId || bot === null) {
    write({ kind: 'READBACK_UNAVAILABLE', native_seq: nativeSeq,
      native_action_id: nativeAction })
    return
  }
  try {
    const state = {}
    for (const control of controls) {
      const value = bot.getControlState(control)
      if (typeof value !== 'boolean') throw new Error('not_boolean_' + control)
      state[control] = value
    }
    write({ kind, native_seq: nativeSeq,
      native_action_id: nativeAction, controls: state })
  } catch (error) {
    write({ kind: 'READBACK_ERROR', native_seq: nativeSeq,
      native_action_id: nativeAction, error: String(error.message || error) })
  }
}

// One and only one child Mineflayer bot. Do not patch any control setters.
const originalCreateBot = mineflayer.createBot
mineflayer.createBot = function (...args) {
  if (bot !== null) throw new Error('readback permits only one Mineflayer bot')
  bot = originalCreateBot.apply(this, args)
  bot.on('physicsTick', () => {
    physicsTick += 1
    readAll('PHYSICS_TICK')
  })
  return bot
}

// The original bridge owns the canonical native seq/session, and remains
// unchanged. Capture a direct getControlState snapshot synchronously BEFORE
// forwarding its already-produced ACK/observation to the recording session.
const originalWrite = process.stdout.write.bind(process.stdout)
process.stdout.write = function (chunk, encoding, callback) {
  if (typeof chunk === 'string') {
    try {
      const frame = JSON.parse(chunk.trimEnd())
      if (frame.type === 'adapter_started' && typeof frame.session_id === 'string') {
        sessionId = frame.session_id
        write({ kind: 'SESSION_START', native_seq: frame.seq })
      } else if (frame.session_id === sessionId &&
        frame.type === 'effect_result') {
        readAll('EFFECT_ACK', frame.seq, frame.action_id)
      } else if (frame.session_id === sessionId &&
        frame.type === 'observation' && frame.kind === 'probe') {
        readAll('PROBE', frame.seq, frame.request_id)
      } else if (frame.session_id === sessionId &&
        frame.type === 'shutdown_ack') {
        readAll('SHUTDOWN_ACK', frame.seq)
      }
    } catch (error) {
      write({ kind: 'NATIVE_FRAME_PARSE_ERROR', error: String(error.message || error) })
    }
  }
  return originalWrite(chunk, encoding, callback)
}

await import('../bridge.mjs')
