import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import test from 'node:test'
import { attachV6NativeClockPackets, v6PacketSample } from './v6_native_clock.mjs'

const packet = (age, time = [0, 3]) => ({ age, time, tickDayTime: true })

test('server packet age, raw display time and host time are independent', () => {
  const x = v6PacketSample(packet([0, 151], [-1, -12]), 123n)
  assert.deepEqual([x.world_age_ticks, x.world_day_time_raw_ticks, x.host_monotonic_ns],
    ['151', '-12', '123'])
  assert.equal(x.command_effect_tick_attested, false)
  assert.equal(x.observation_precision, 'SERVER_UPDATE_TIME_PACKET_SAMPLE_ONLY')
  assert.equal(v6PacketSample(packet([1, 0]), 124n).world_age_ticks, '4294967296')
})

test('fake values, negatives, float and missing genuine fields reject', () => {
  for (const p of [{}, packet(151), packet([0]), packet([0, 1.5]),
    packet([-1, -1]), { age: [0, 1], time: [0, 2], tickDayTime: 1 }]) {
    assert.throws(() => v6PacketSample(p, 2n))
  }
  assert.throws(() => v6PacketSample(packet([0, 2]), -1n))
  assert.throws(() => v6PacketSample(packet([0, 2]), 2))
})

test('only real update_time callbacks emit; day reset does not reset age', () => {
  const client = new EventEmitter(), rows = [], errors = []
  attachV6NativeClockPackets({ _client: client }, v => rows.push(v), e => errors.push(e))
  assert.equal(rows.length, 0)
  client.emit('update_time', packet([0, 100], [0, 450]))
  client.emit('update_time', packet([0, 110], [0, 1]))
  client.emit('update_time', packet([0, 110], [0, 1]))
  client.emit('update_time', packet([0, 109], [0, 2]))
  client.emit('update_time', packet([0, 130], [0, 3]))
  assert.deepEqual(rows.map(v => v.world_age_ticks), ['100', '110', '110', '130'])
  assert.deepEqual(rows.map(v => v.world_day_time_raw_ticks), ['450', '1', '1', '3'])
  assert.equal(errors.length, 1)
  assert.ok(rows.every(v => !v.command_effect_tick_attested))
})
