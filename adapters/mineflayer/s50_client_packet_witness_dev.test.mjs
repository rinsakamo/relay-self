import test from 'node:test'
import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import {
  attachS50ClientPacketWitness, openS50PacketSidecar
} from './s50_client_packet_witness_dev.mjs'

function fake () {
  const bot = new EventEmitter()
  const writes = []
  const native = function (name, payload) {
    writes.push({ name, payload, receiver: this })
    return { written: name, identity: payload }
  }
  const client = { write: native }
  bot._client = client
  bot.entity = { position: { x: 1, y: 64, z: 2 } }
  bot.getControlState = name => name === 'forward'
  return { bot, client, writes, native }
}

test('single writer wrapper observes input and movement WITHOUT sending packets', () => {
  const { bot, client, writes } = fake()
  const source = []
  const witness = attachS50ClientPacketWitness(bot, row => source.push(row),
    () => 123456n)
  assert.equal(witness.new_packet_writes, 0)
  assert.equal(writes.length, 0)
  bot.emit('physicsTick')
  const input = { flags: 1 }
  const position = { x: 1.5, y: 64, z: 2 }
  assert.deepEqual(client.write('player_input', input),
    { written: 'player_input', identity: input })
  assert.deepEqual(client.write('position', position),
    { written: 'position', identity: position })
  assert.equal(writes.length, 2)
  assert.equal(writes[0].receiver, client)
  assert.equal(writes[1].payload, position)
  assert.equal(source.length, 3)
  assert.equal(source[0].kind, 'PHYSICS_EVENT_SAMPLE')
  assert.equal(source[0].applied_controls_sample.forward, true)
  assert.equal(source[1].packet_name, 'player_input')
  assert.deepEqual(source[1].packet_shape,
    { fields: ['flags'], input_flags_raw: 1 })
  assert.equal(source[1].network_delivered, false)
  assert.equal(source[1].paper_received, false)
  assert.equal(source[2].packet_name, 'position')
  assert.deepEqual(source[2].packet_pose, position)
  assert.equal(source[2].clock_scope, 'NODE_ONLY')
  assert.equal(source[2].last_physics_index, 1)
})

test('zero player_input is distinguishable from position writes and no trace', () => {
  const { bot, client } = fake()
  const source = []
  const witness = attachS50ClientPacketWitness(bot, row => source.push(row))
  client.write('position', { x: 4, y: 64, z: 5 })
  witness.effect('clear_controls')
  client.write('flying', { flags: 1 })
  client.write('custom_payload', { private: 'never log this' })
  assert.equal(source.filter(x => x.packet_name === 'player_input').length, 0)
  assert.equal(source.filter(x => x.kind === 'PACKET_WRITE_RETURNED').length, 2)
  assert.equal(source.filter(x => x.kind === 'NATIVE_CONTROL_EFFECT_RETURNED').length, 1)
  assert.equal(source[1].effect, 'clear_controls')
  assert.equal(source[2].packet_pose, null)
  assert.equal(source.length, 3)
})

test('original writer exceptions and this/arguments preserved unchanged', () => {
  const { bot, client } = fake()
  let hits = 0
  client.write = function (name) {
    hits++
    if (name === 'player_input') throw Error('original serializer failure')
    return this === client ? 42 : 0
  }
  const rows = []
  attachS50ClientPacketWitness(bot, row => rows.push(row))
  assert.equal(client.write('position', {}), 42)
  assert.throws(() => client.write('player_input', { flags: 1 }), /original serializer failure/)
  assert.equal(hits, 2)
  assert.equal(rows.filter(x => x.packet_name === 'player_input').length, 0)
})

test('client witness rejects alternate/nonexistent writer', () => {
  assert.throws(() => attachS50ClientPacketWitness({}, () => {}),
    /existing native client/)
})

test('writer attaches before asynchronous physics plugin control injection', () => {
  const { bot, client, writes } = fake()
  delete bot.getControlState
  const rows = []
  const witness = attachS50ClientPacketWitness(bot, row => rows.push(row))
  client.write('look', { yaw: 0, pitch: 0 })
  assert.equal(writes.length, 1)
  assert.equal(rows[0].packet_name, 'look')
  bot.getControlState = () => false
  bot.emit('physicsTick')
  witness.effect('clear_controls')
  assert.equal(rows[1].physics_index, 1)
  assert.equal(rows[2].controls_after_sample.forward, false)
  assert.equal(writes.length, 1)
})

test('sidecar enforces new absolute file, footer, backpressure failure', () => {
  const lines = []
  const stream = {
    write (line) { lines.push(JSON.parse(line)); return true },
    end (line) { lines.push(JSON.parse(line)) },
    on () {}
  }
  const sidecar = openS50PacketSidecar('/tmp/s50-witness-dev.jsonl',
    (path, options) => {
      assert.equal(path, '/tmp/s50-witness-dev.jsonl')
      assert.equal(options.flags, 'wx')
      return stream
    })
  sidecar.write({ kind: 'PACKET_WRITE_RETURNED' })
  sidecar.close()
  sidecar.close()
  assert.equal(lines.length, 2)
  assert.equal(lines[1].kind, 'TRACE_END')
  assert.equal(lines[1].recorded_rows, 1)
  assert.equal(lines[1].complete, true)
  assert.equal(lines[1].input_write_authority, false)
  assert.throws(() => openS50PacketSidecar('relative-path'), /absolute/)
  const broken = []
  const backpressure = openS50PacketSidecar('/tmp/s50-witness-bad.jsonl',
    () => ({
      write (line) { broken.push(JSON.parse(line)); return false },
      end (line) { broken.push(JSON.parse(line)) },
      on () {}
    }))
  backpressure.write({ kind: 'PHYSICS_EVENT_SAMPLE' })
  backpressure.close()
  assert.equal(broken.at(-1).complete, false)
  assert.equal(broken.at(-1).lost, true)
})
