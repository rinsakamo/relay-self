import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import test from 'node:test'
import {
  PAPER_TICK_CHANNEL, attachPaperTickChannel, decodePaperTickPayload
} from './paper_tick_channel.mjs'

const W = '11111111-1111-4111-8111-111111111111'
const P = '22222222-2222-4222-8222-222222222222'
function payload (i = 1, overrides = {}) {
  const d = { index: i, server_tick: 100 + i,
    world_full_time: 400 + i, wall_nanos: 10000 + i * 100,
    world: W, player: P, source: 'PAPER_SCHEDULER_CALLBACK_ONLY',
    l0_checked: 'false', action_bound: 'false', ...overrides }
  return Buffer.from(Object.entries(d).map(([k, v]) => k + '=' + v).join(' '), 'utf8')
}

test('strict Paper tick wire is a receipt, not an L0 check', () => {
  const x = decodePaperTickPayload(payload(), 12345n)
  assert.equal(x.server_tick, '101')
  assert.equal(x.observation_precision, 'PAPER_PLUGIN_MESSAGE_RECEIVED_LATER')
  assert.equal(x.bridge_recv_monotonic_ns, '12345')
  assert.equal(x.l0_checked, false)
  assert.equal(x.action_bound, false)
  assert.equal(x.paper_native_source_authenticated, false)
})

test('invalid flags, UUIDs and numeric scope are rejected', () => {
  for (const d of [
    { l0_checked: 'true' }, { action_bound: 'true' }, { world: 'other' },
    { player: 'other' }, { index: 0 },
    { server_tick: -1 }, { server_tick: '1.5' },
    { world_full_time: 'nan' }, { wall_nanos: '0.5' },
    { source: 'FORGED' }
  ]) assert.throws(() => decodePaperTickPayload(payload(1, d), 123n))
  assert.throws(() => decodePaperTickPayload(Buffer.from('hello'), 123n))
  assert.throws(() => decodePaperTickPayload(payload(1), -1n))
})

test('channel listener checks consecutive ticks, never produces action outputs', () => {
  const client = new EventEmitter()
  const channels = []
  client.registerChannel = (...a) => channels.push(a)
  const seen = []; const invalid = []
  attachPaperTickChannel({ _client: client }, x => seen.push(x), e => invalid.push(e))
  assert.deepEqual(channels, [[PAPER_TICK_CHANNEL, null, true]])
  client.emit(PAPER_TICK_CHANNEL, payload(1))
  client.emit(PAPER_TICK_CHANNEL, payload(2))
  client.emit(PAPER_TICK_CHANNEL, payload(4))
  client.emit(PAPER_TICK_CHANNEL, payload(3))
  assert.equal(seen.length, 3)
  assert.deepEqual(seen.map(x => x.server_tick), ['101', '102', '103'])
  assert.equal(invalid.length, 1)
  assert.ok(seen.every(x => !x.l0_checked && !x.action_bound))
})

test('no first index, foreign player, duplicate tick or non-Buffer rejected', () => {
  for (const kind of ['no-first', 'foreign', 'duplicate', 'not-buffer']) {
    const client = new EventEmitter(); client.registerChannel = () => {}
    const seen = []; const invalid = []
    attachPaperTickChannel({ _client: client }, x => seen.push(x), e => invalid.push(e))
    if (kind === 'no-first') client.emit(PAPER_TICK_CHANNEL, payload(2))
    else {
      client.emit(PAPER_TICK_CHANNEL, payload(1))
      if (kind === 'foreign') client.emit(PAPER_TICK_CHANNEL, payload(2, { player: W }))
      if (kind === 'duplicate') client.emit(PAPER_TICK_CHANNEL, payload(1))
      if (kind === 'not-buffer') client.emit(PAPER_TICK_CHANNEL, 'not binary')
    }
    assert.equal(invalid.length, 1)
  }
})

test('bounded payload, duplicates, non-ASCII and out-of-range i64 reject', () => {
  const basic = payload().toString()
  for (const p of [
    Buffer.from(basic + ' x=true'),
    Buffer.from(basic + ' index=1'),
    Buffer.alloc(513),
    Buffer.from(basic.replace('server_tick=101', 'server_tick=9223372036854775808')),
    Buffer.from(basic.replace('index=1', 'index=257')),
    Buffer.from(basic.replace('player=' + P, 'player=ああ')),
  ]) assert.throws(() => decodePaperTickPayload(p, 5n))
})
