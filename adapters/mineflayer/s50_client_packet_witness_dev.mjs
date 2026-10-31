// S50 opt-in DEV witness on the *existing* Mineflayer client's write path.
// Inspired by existing T1w passive witness; never synthesizes any packet,
// Action, clear command, server tick or causal clock alignment.
import { createWriteStream } from 'node:fs'
import { isAbsolute } from 'node:path'

const PACKETS = new Set([
  'player_input', 'position', 'position_look', 'flying', 'look',
  'entity_action'
])
const CONTROLS = ['forward', 'back', 'left', 'right', 'jump', 'sneak', 'sprint']
const MAX_ROWS = 8192

function controls (bot) {
  // Mineflayer injects this API asynchronously after createBot returns.
  // Attach the writer immediately; require controls only when sampling.
  if (typeof bot.getControlState !== 'function') {
    throw Error('S50 controls unavailable at native sample')
  }
  return Object.fromEntries(CONTROLS.map(name => [name, bot.getControlState(name)]))
}

function pose (packet) {
  if (!packet || typeof packet !== 'object' ||
      !['x', 'y', 'z'].every(key => Number.isFinite(packet[key]))) return null
  return { x: packet.x, y: packet.y, z: packet.z }
}

function safePacketShape (packet) {
  if (!packet || typeof packet !== 'object' || Array.isArray(packet)) {
    return { fields: [], input_flags_raw: null }
  }
  // No arbitrary user payload, only its keys and a native raw flag value.
  const fields = Object.keys(packet).filter(x => /^[A-Za-z_]{1,48}$/.test(x)).slice(0, 16)
  return {
    fields,
    input_flags_raw: Number.isInteger(packet.flags) &&
      packet.flags >= 0 && packet.flags <= 255 ? packet.flags : null
  }
}

export function openS50PacketSidecar (path, createStream = createWriteStream) {
  if (typeof path !== 'string' || !isAbsolute(path)) {
    throw Error('S50 packet DEV source requires an absolute fresh path')
  }
  const stream = createStream(path, {
    flags: 'wx', mode: 0o600, highWaterMark: 4 * 1024 * 1024
  })
  let rows = 0
  let lost = false
  let closed = false
  const write = row => {
    if (closed || lost) return
    if (rows === MAX_ROWS) {
      lost = true
      return
    }
    try {
      if (!stream.write(JSON.stringify(row) + '\n')) lost = true
      rows++
    } catch { lost = true }
  }
  stream.on?.('error', () => { lost = true })
  const close = () => {
    if (closed) return
    closed = true
    try {
      stream.end(JSON.stringify({
        revision: 1, kind: 'TRACE_END', complete: !lost,
        lost, recorded_rows: rows, input_write_authority: false,
        server_packet_received: false, effective_s15_clear_tick: 'NOT_ATTESTED'
      }) + '\n')
    } catch { /* incomplete source must be rejected */ }
  }
  return { write, close, get lost () { return lost } }
}

export function attachS50ClientPacketWitness (
  bot, record, clock = () => process.hrtime.bigint()
) {
  const client = bot?._client
  if (!client || typeof client.write !== 'function' ||
      typeof bot.on !== 'function' ||
      typeof record !== 'function' || typeof clock !== 'function') {
    throw Error('S50 packet witness needs the existing native client')
  }
  let physicsIndex = 0
  let packetIndex = 0
  let recordIndex = 0
  const capture = row => record({
    revision: 1, index: ++recordIndex, node_ns: String(clock()),
    clock_scope: 'NODE_ONLY', server_world_tick: 'NOT_OBSERVED',
    source: 'CLIENT_WRITE_RETURNED_NOT_NETWORK_DELIVERY', ...row
  })
  bot.on('physicsTick', () => {
    physicsIndex++
    capture({
      kind: 'PHYSICS_EVENT_SAMPLE', physics_index: physicsIndex,
      applied_controls_sample: controls(bot),
      client_pose_sample: bot.entity?.position
        ? pose(bot.entity.position) : null
    })
  })
  // Exactly one writer wrapper; same original invocation, args, receiver,
  // result and exception. No new write calls, no packet mutation.
  const nativeWrite = client.write
  client.write = function (name, ...args) {
    const result = Reflect.apply(nativeWrite, this, [name, ...args])
    if (PACKETS.has(name)) {
      packetIndex++
      capture({
        kind: 'PACKET_WRITE_RETURNED', packet_index: packetIndex,
        packet_name: name, last_physics_index: physicsIndex,
        packet_pose: pose(args[0]),
        packet_shape: name === 'player_input' ? safePacketShape(args[0]) : null,
        network_delivered: false, paper_received: false
      })
    }
    return result
  }
  const effect = (name, state = null) => {
    capture({
      kind: 'NATIVE_CONTROL_EFFECT_RETURNED', effect: name,
      requested_state: state,
      controls_after_sample: controls(bot),
      last_physics_index: physicsIndex
    })
  }
  return Object.freeze({
    effect,
    new_packet_writes: 0,
    source_coverage: 'ONE_EXISTING_CLIENT_WRITE_CALL_PATH_ONLY',
    client_server_clock_aligned: false,
    effective_input_clear_attested: false
  })
}
