// S-owned, opt-in DEV process wrapper. Import the unmodified Mineflayer bridge.
// Reads all seven Mineflayer getControlState values directly; never claims
// Paper-effective motor state or derives a shared clock from this client source.
import { createRequire } from 'node:module'
import { attachPassiveS50PacketTrace, clientPose } from './s50_p1_packet_trace.mjs'
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
// Capture native bot.entity orientation only for the opt-in FLAT/P1 child.
// This is a client-local radian snapshot at source emission, never Paper yaw.
const captureFlatPose = process.env.RELAY_S50_P1_FLAT_FORCE_SERVER_LOOK_DEV === '1'
const packetTracePath = process.env.RELAYSELF_S50_PACKET_TRACE_FILE
if (captureFlatPose !== Boolean(packetTracePath)) {
  throw new Error('S50 FLAT packet trace source opt-in must match native pose opt-in')
}
if (packetTracePath && (!isAbsolute(packetTracePath) ||
    packetTracePath === path || packetTracePath.length > 4096)) {
  throw new Error('S50 packet trace requires a distinct absolute fresh evidence file')
}
const packetFd = packetTracePath ? openSync(packetTracePath, 'wx', 0o600) : null
if (packetFd !== null) process.on('exit', () => closeSync(packetFd))
let packetOrdinal = 0
const MAX_PACKET_ROWS = 16384
function packetRecord (record) {
  if (packetFd === null) return
  packetOrdinal++
  if (packetOrdinal > MAX_PACKET_ROWS) {
    throw new Error('S50 passive packet source exceeded bounded original cap')
  }
  writeSync(packetFd, JSON.stringify({
    source: 'S50_DEV_PASSIVE_PACKET_V1',
    ordinal: packetOrdinal,
    session_id: sessionId,
    client_physics_tick: physicsTick,
    ...record
  }) + '\n')
}

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
    const pose = {}
    if (captureFlatPose) {
      if (!bot.entity ||
          !Number.isFinite(bot.entity.yaw) ||
          !Number.isFinite(bot.entity.pitch)) {
        throw new Error('missing_finite_native_entity_orientation')
      }
      pose.client_yaw_radians = bot.entity.yaw
      pose.client_pitch_radians = bot.entity.pitch
    }
    write({ kind, native_seq: nativeSeq,
      native_action_id: nativeAction, controls: state, ...pose })
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
  if (packetFd !== null) {
    attachPassiveS50PacketTrace(bot, packetRecord)
  }
  bot.on('physicsTick', () => {
    physicsTick += 1
    readAll('PHYSICS_TICK')
    if (packetFd !== null) {
      packetRecord({ kind: 'CLIENT_PHYSICS_TICK', ...clientPose(bot) })
    }
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
        packetRecord({ kind: 'SESSION_START', native_seq: frame.seq })
      } else if (frame.session_id === sessionId &&
        frame.type === 'effect_result') {
        readAll('EFFECT_ACK', frame.seq, frame.action_id)
        packetRecord({
          kind: 'NATIVE_EFFECT_ACK', native_seq: frame.seq,
          native_action_id: frame.action_id,
          effect: frame.effect, result: frame.result, ...clientPose(bot)
        })
      } else if (frame.session_id === sessionId &&
        frame.type === 'observation' && frame.kind === 'probe') {
        readAll('PROBE', frame.seq, frame.request_id)
      } else if (frame.session_id === sessionId &&
        frame.type === 'shutdown_ack') {
        readAll('SHUTDOWN_ACK', frame.seq)
        packetRecord({ kind: 'SHUTDOWN_ACK', native_seq: frame.seq, ...clientPose(bot) })
      }
    } catch (error) {
      write({ kind: 'NATIVE_FRAME_PARSE_ERROR', error: String(error.message || error) })
    }
  }
  return originalWrite(chunk, encoding, callback)
}

await import('../bridge.mjs')
