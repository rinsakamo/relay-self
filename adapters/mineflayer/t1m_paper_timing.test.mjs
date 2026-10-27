import test from 'node:test'
import assert from 'node:assert/strict'
import { attachPaperSnapshotChannel } from './paper_snapshot_admission.mjs'

// No second native reader, packet type or qualification can be minted by T1m.
const uuid = '11111111-1111-1111-1111-111111111111'
function snapshot (challenge) {
  return { version: 1, boot: uuid, index: 1, tick: 101,
    world_tick: 201, paper_ns: 50000000, world: uuid, player: uuid,
    challenge, x: 0, y: 1, z: 0, health: 20, food: 20, input: 0,
    threats_complete: true, threats: [], basal_ticks: 1,
    basal_exhaustion: .001, motion_blocks: 0, motion_exhaustion: 0 }
}

test('T1m opt-in diagnostics preserve canonical Paper admission, challenge and single emitter', () => {
  const callbacks = {}; const sent = []; const native = []; const dev = []
  let now = 0n
  const bot = {
    once: (name, callback) => { callbacks[name] = callback },
    _client: {
      on: (name, callback) => { callbacks[name] = callback },
      registerChannel: () => {},
      write: (name, payload) => { sent.push({ name, payload }) }
    }
  }
  const channel = attachPaperSnapshotChannel(
    bot, (type, body) => native.push({ type, body }),
    error => { throw error },
    () => now, undefined, event => dev.push(event)
  )
  callbacks.login()
  assert.equal(sent.length, 1)
  const challenge = sent[0].payload.data.toString('ascii')
  assert.equal(dev[0].kind, 'challenge_write_return')
  assert.equal(dev[0].challenge, challenge)
  assert.equal(dev[0].node_sent_ns, '0')
  now = 50000000n
  callbacks['relayself:world_tick_dev'](Buffer.from(JSON.stringify(snapshot(challenge))))
  assert.deepEqual(native.map(x => x.type), ['paper_snapshot'])
  assert.equal(native[0].body.data.status, 'ADMITTED')
  assert.equal(native[0].body.data.paper_to_node_exact_ns, null)
  assert.equal(channel.canDispatch(), true)
  assert.equal(dev[1].kind, 'snapshot_callback')
  assert.equal(dev[1].challenge, challenge)
  assert.equal(dev[1].node_received_ns, '50000000')
  assert.equal(dev[1].age_upper_ns, '50000000')
  assert.equal(dev[1].status, 'ADMITTED')
  assert.equal(dev[2].kind, 'challenge_write_return')
  assert.notEqual(dev[2].challenge, challenge)
  assert.equal(sent.length, 2)
  assert(sent.every(x => x.name === 'custom_payload'))
})

test('T1m diagnostic hook cannot promote an aged Paper snapshot', () => {
  const callbacks = {}; const sent = []; const native = []; const dev = []
  let now = 0n
  const bot = {
    once: (name, cb) => { callbacks[name] = cb },
    _client: {
      on: (name, cb) => { callbacks[name] = cb },
      registerChannel: () => {},
      write: (_name, payload) => sent.push(payload.data.toString('ascii'))
    }
  }
  const channel = attachPaperSnapshotChannel(
    bot, (type, body) => native.push({ type, body }),
    error => { throw error },
    () => now, undefined, event => dev.push(event)
  )
  callbacks.login()
  now = 155000000n
  callbacks['relayself:world_tick_dev'](Buffer.from(JSON.stringify(snapshot(sent[0]))))
  assert.equal(native[0].body.data.status, 'STALE')
  assert.equal(channel.canDispatch(), false)
  assert.equal(dev[1].status, 'STALE')
  assert.equal(dev[1].reason, 'CAUSAL_AGE_UPPER_BOUND_EXCEEDED')
  assert.equal(native.length, 1)
})

test('diagnostic write failure cannot poison source admission or suppress next challenge', () => {
  const callbacks = {}; const sent = []; const native = []; const invalid = []
  let now = 0n
  const bot = { once: (n, cb) => { callbacks[n] = cb }, _client: {
    on: (n, cb) => { callbacks[n] = cb }, registerChannel: () => {},
    write: (_n, p) => sent.push(p.data.toString('ascii'))
  } }
  const channel = attachPaperSnapshotChannel(bot,
    (type, body) => native.push(body.data), e => invalid.push(e),
    () => now, undefined, () => { throw Error('sidecar write failed') })
  callbacks.login()
  now = 50000000n
  callbacks['relayself:world_tick_dev'](Buffer.from(JSON.stringify(snapshot(sent[0]))))
  assert.equal(native[0].status, 'ADMITTED')
  assert.equal(sent.length, 2)
  assert.equal(invalid.length, 0)
  assert.equal(channel.canDispatch(), true)
})

test('post-evaluation diagnostics measure emit and hook separately from admission', () => {
  const callbacks = {}; const sent = []; const dev = []
  let now = 0n
  const bot = { once: (n, cb) => { callbacks[n] = cb }, _client: {
    on: (n, cb) => { callbacks[n] = cb }, registerChannel: () => {},
    write: (_n, p) => sent.push(p.data.toString('ascii'))
  } }
  attachPaperSnapshotChannel(bot, () => { now += 1000000n },
    e => { throw e }, () => now, undefined,
    e => { dev.push(e); now += 2000000n })
  callbacks.login()
  now = 50000000n
  callbacks['relayself:world_tick_dev'](Buffer.from(JSON.stringify(snapshot(sent[0]))))
  const next = dev.at(-1)
  assert.equal(next.previous_complete_ns, '50000000')
  assert.equal(next.previous_emit_return_ns, '51000000')
  assert.equal(next.previous_diagnostic_start_ns, '51000000')
  assert.equal(next.previous_diagnostic_return_ns, '53000000')
  assert.equal(next.node_sent_ns, '53000000')
  assert.equal(dev[1].status, 'ADMITTED')
  assert.equal(dev[1].node_complete_ns, '50000000')
})
