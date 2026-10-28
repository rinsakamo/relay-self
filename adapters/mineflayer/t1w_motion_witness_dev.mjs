// T1w isolated DEV: passive client-physics samples and outbound movement
// packet write-return evidence. This is NOT a shared WorldTick clock, packet
// acceptance ACK, applied fractional-tick gait or additional Motor owner.
import { createWriteStream } from 'node:fs'
import { isAbsolute } from 'node:path'

const MOVEMENT = new Set(['position', 'position_look', 'flying', 'look'])
const CONTROLS = ['forward', 'back', 'left', 'right', 'jump', 'sneak', 'sprint']
const MAX_ROWS = 8192

function location (bot) {
  const p = bot?.entity?.position
  if (!p || ![p.x, p.y, p.z].every(Number.isFinite)) return null
  return { x: p.x, y: p.y, z: p.z }
}

function controls (bot) {
  return Object.fromEntries(CONTROLS.map(name => [name, bot.getControlState(name)]))
}

function packetPose (packet) {
  if (packet === null || typeof packet !== 'object' || Array.isArray(packet)) return null
  if (!['x', 'y', 'z'].every(key => Number.isFinite(packet[key]))) return null
  return { x: packet.x, y: packet.y, z: packet.z }
}

// A sidecar path is an absolute, new file. Event-loop asynchronous writes are
// intentionally separate from both canonical native.jsonl and sync T1n trace.
export function openT1wSidecar (path, createStream = createWriteStream) {
  if (typeof path !== 'string' || !isAbsolute(path)) throw Error('T1w trace requires absolute path')
  const stream = createStream(path, { flags: 'wx', mode: 0o600 })
  let rows = 0
  let lost = false
  let closed = false
  const write = (row) => {
    if (closed || lost) return
    if (rows >= MAX_ROWS) {
      lost = true
      return
    }
    try {
      if (!stream.write(JSON.stringify(row) + '\n')) {
        // Backpressure is not a guarantee of a lost row, but we cannot
        // certify a complete, non-intrusive trace. Fail the audit closed.
        lost = true
      }
      rows++
    } catch {
      lost = true
    }
  }
  stream.on?.('error', () => { lost = true })
  const close = () => {
    if (closed) return
    closed = true
    try {
      stream.end(JSON.stringify({
        revision: 1, kind: 'TRACE_END', complete: !lost,
        lost, recorded_rows: rows, motion_authority: false
      }) + '\n')
    } catch { /* partial sidecar is explicitly audit-invalid */ }
  }
  return { write, close, get lost () { return lost } }
}

export function attachT1wMotionWitness (bot, record, clock = () => process.hrtime.bigint()) {
  const client = bot?._client
  if (!client || typeof client.write !== 'function' ||
      typeof bot.on !== 'function' || typeof bot.getControlState !== 'function' ||
      typeof record !== 'function' || typeof clock !== 'function') {
    throw Error('T1w needs original Mineflayer client and passive sidecar')
  }

  let physicsEventIndex = 0
  let outgoingIndex = 0
  let recordIndex = 0
  const capture = (row) => {
    record({
      revision: 1, index: ++recordIndex, node_ns: String(clock()),
      clock_scope: 'NODE_ONLY', source_authority: 'PASSIVE_LOCAL_DIAGNOSTIC',
      ...row
    })
  }

  // Mineflayer 4.39 physicsTick is an event sample, NOT an authenticated
  // start/end of a physics integration step. Do not infer a pre/post gait.
  bot.on('physicsTick', () => {
    physicsEventIndex++
    capture({
      kind: 'PHYSICS_EVENT_SAMPLE', physics_event_index: physicsEventIndex,
      applied_controls_sample: controls(bot), client_pose_sample: location(bot)
    })
  })

  // Following pre-existing S50 passive trace design: wrap exactly one native
  // write function without issuing additional packets or changing arguments.
  const nativeWrite = client.write
  client.write = function (name, ...args) {
    if (!MOVEMENT.has(name)) return Reflect.apply(nativeWrite, this, [name, ...args])
    const originalResult = Reflect.apply(nativeWrite, this, [name, ...args])
    outgoingIndex++
    capture({
      kind: 'MOVEMENT_WRITE_RETURNED', packet_index: outgoingIndex,
      packet_name: name, packet_pose: packetPose(args[0]),
      packet_pose_valid: packetPose(args[0]) !== null,
      last_physics_event_index: physicsEventIndex,
      client_pose_sample: location(bot),
      network_delivered: false, paper_accepted: false
    })
    return originalResult
  }
  return Object.freeze({
    passive_only: true, new_packet_writes: 0,
    shared_client_paper_clock: false, paper_move_attested: false,
    correlation_proven: false
  })
}
