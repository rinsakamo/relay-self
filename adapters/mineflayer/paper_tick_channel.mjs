// #150 DEV-only Paper server tick transport over the EXISTING Mineflayer client.
// Not a motor writer, L0 execution receipt, Action ID or Paper source attestation.
export const PAPER_TICK_CHANNEL = 'relayself:world_tick_dev'
const SOURCE = 'PAPER_SCHEDULER_CALLBACK_ONLY'
const FIELDS = [
  'index', 'server_tick', 'world_full_time', 'wall_nanos',
  'world', 'player', 'source', 'l0_checked', 'action_bound'
]
const DECIMAL = /^(0|[1-9][0-9]*)$/
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
const MAX_I64 = 9223372036854775807n

function natural (v, name, positive = false) {
  if (!DECIMAL.test(v)) throw new Error('bad ' + name)
  const n = BigInt(v)
  if (n > MAX_I64 || (positive && n === 0n)) throw new Error('out of range ' + name)
  return n
}

export function decodePaperTickPayload (bytes, recvMonoNs) {
  if (!Buffer.isBuffer(bytes) || bytes.length === 0 || bytes.length > 512 ||
      typeof recvMonoNs !== 'bigint' || recvMonoNs < 0n) {
    throw new Error('invalid Paper plugin payload or receive timestamp')
  }
  const raw = bytes.toString('utf8')
  if (!/^[\x20-\x7e]+$/.test(raw)) throw new Error('non-ASCII payload')
  const pairs = raw.split(' ')
  const fields = {}
  for (const pair of pairs) {
    const ix = pair.indexOf('=')
    if (ix < 1 || ix === pair.length - 1) throw new Error('invalid field syntax')
    const name = pair.slice(0, ix)
    if (Object.hasOwn(fields, name)) throw new Error('duplicate key')
    fields[name] = pair.slice(ix + 1)
  }
  if (Object.keys(fields).length !== FIELDS.length ||
      FIELDS.some(k => !Object.hasOwn(fields, k))) throw new Error('wrong Paper tick fields')
  if (fields.source !== SOURCE || fields.l0_checked !== 'false' ||
      fields.action_bound !== 'false' ||
      !UUID.test(fields.world) || !UUID.test(fields.player)) {
    throw new Error('invalid tick source or false native authority')
  }
  const index = natural(fields.index, 'index', true)
  const tick = natural(fields.server_tick, 'server_tick')
  const worldTime = natural(fields.world_full_time, 'world_full_time')
  const wallNs = natural(fields.wall_nanos, 'wall_nanos')
  if (index > 256n) throw new Error('bounded tick probe exceeded')
  return Object.freeze({
    source: SOURCE,
    observation_precision: 'PAPER_PLUGIN_MESSAGE_RECEIVED_LATER',
    index: Number(index),
    server_tick: tick.toString(),
    world_full_time: worldTime.toString(),
    wall_nanos: wallNs.toString(),
    world: fields.world,
    player: fields.player,
    bridge_recv_monotonic_ns: recvMonoNs.toString(),
    l0_checked: false,
    action_bound: false,
    paper_native_source_authenticated: false
  })
}

export function attachPaperTickChannel (bot, onSample, onInvalid) {
  if (!bot?._client || typeof bot._client.on !== 'function' ||
      typeof bot._client.registerChannel !== 'function' ||
      typeof onSample !== 'function' || typeof onInvalid !== 'function') {
    throw new TypeError('real client and callbacks required')
  }
  // registerChannel sends the register packet when custom=true. No second
  // socket/listener or registered incoming command/action channel.
  bot._client.registerChannel(PAPER_TICK_CHANNEL, null, true)
  let previous = null
  bot._client.on(PAPER_TICK_CHANNEL, bytes => {
    try {
      const sample = decodePaperTickPayload(bytes, process.hrtime.bigint())
      const tick = BigInt(sample.server_tick)
      if (previous) {
        if (BigInt(sample.index) !== BigInt(previous.index) + 1n ||
            tick !== BigInt(previous.server_tick) + 1n ||
            BigInt(sample.world_full_time) !== BigInt(previous.world_full_time) + 1n ||
            BigInt(sample.wall_nanos) <= BigInt(previous.wall_nanos) ||
            BigInt(sample.bridge_recv_monotonic_ns) <=
              BigInt(previous.bridge_recv_monotonic_ns) ||
            sample.world !== previous.world || sample.player !== previous.player) {
          throw new Error('Paper wire tick lineage discontinuous')
        }
      } else if (sample.index !== 1) {
        throw new Error('Paper wire first tick missing')
      }
      previous = sample
      onSample(sample)
    } catch (error) {
      // Forward invalid data; do not hide gaps or pretend a tick was checked.
      onInvalid(error)
    }
  })
}
