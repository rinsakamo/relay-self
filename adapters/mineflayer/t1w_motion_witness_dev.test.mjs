import test from 'node:test'
import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import {
  attachT1wMotionWitness, openT1wSidecar
} from './t1w_motion_witness_dev.mjs'

function fake () {
  const bot = new EventEmitter()
  const writes = []
  const client = {
    write (name, payload) {
      writes.push([name, payload, this])
      return { ok: true, name }
    }
  }
  bot._client = client
  bot.entity = { position: { x: 1, y: 64, z: 2 } }
  bot.getControlState = name => name === 'back'
  return { bot, client, writes }
}

test('passive same-client physics/packet witness preserves writer identity and return', () => {
  const { bot, client, writes } = fake()
  const trace = []
  const original = client.write
  let ns = 100n
  const contract = attachT1wMotionWitness(bot, r => trace.push(r), () => ++ns)
  assert.equal(contract.new_packet_writes, 0)
  assert.equal(contract.paper_move_attested, false)
  bot.emit('physicsTick')
  const payload = { x: 1.1, y: 64, z: 2, onGround: true }
  assert.deepEqual(client.write('position', payload), { ok: true, name: 'position' })
  assert.deepEqual(client.write('custom_payload', { data: Buffer.alloc(0) }),
    { ok: true, name: 'custom_payload' })
  assert.equal(writes.length, 2)
  assert.equal(writes[0][1], payload)
  assert.equal(writes[0][2], client)
  assert.equal(trace.length, 2)
  assert.equal(trace[0].kind, 'PHYSICS_EVENT_SAMPLE')
  assert.equal(trace[0].applied_controls_sample.back, true)
  assert.equal(trace[1].kind, 'MOVEMENT_WRITE_RETURNED')
  assert.equal(trace[1].packet_index, 1)
  assert.equal(trace[1].last_physics_event_index, 1)
  assert.deepEqual(trace[1].packet_pose, { x: 1.1, y: 64, z: 2 })
  assert.equal(trace[1].paper_accepted, false)
  assert.equal(trace[1].network_delivered, false)
  assert.equal(trace[1].clock_scope, 'NODE_ONLY')
  assert.equal(typeof original, 'function')
})

test('failed original write is never logged as a successful returned packet', () => {
  const { bot, client } = fake()
  client.write = function () { throw Error('transport failed') }
  const trace = []
  attachT1wMotionWitness(bot, row => trace.push(row), () => 3n)
  assert.throws(() => client.write('position', { x: 1, y: 2, z: 3 }),
    /transport failed/)
  assert.deepEqual(trace, [])
})

test('invalid geometry does not become accepted packet location', () => {
  const { bot, client } = fake()
  const rows = []
  attachT1wMotionWitness(bot, row => rows.push(row), () => 1n)
  client.write('flying', { onGround: true })
  assert.equal(rows.length, 1)
  assert.equal(rows[0].packet_pose, null)
  assert.equal(rows[0].packet_pose_valid, false)
})

test('dedicated noncanonical sidecar is fresh, bounded and footered', () => {
  const calls = []
  const stream = {
    write (line) { calls.push(JSON.parse(line)); return true },
    end (line) { calls.push(JSON.parse(line)) },
    on () {}
  }
  const witness = openT1wSidecar('/tmp/t1w-dev-only.jsonl',
    (path, opts) => {
      assert.equal(opts.flags, 'wx')
      assert.equal(path, '/tmp/t1w-dev-only.jsonl')
      return stream
    })
  witness.write({ kind: 'PHYSICS_EVENT_SAMPLE' })
  witness.close()
  witness.close()
  assert.equal(calls.length, 2)
  assert.equal(calls[1].kind, 'TRACE_END')
  assert.equal(calls[1].recorded_rows, 1)
  assert.equal(calls[1].complete, true)
  assert.equal(calls[1].motion_authority, false)
  assert.throws(() => openT1wSidecar('relative', () => stream), /absolute/)
})

test('backpressure invalidates trace for independent review', () => {
  const calls = []
  const stream = {
    write (line) { calls.push(JSON.parse(line)); return false },
    end (line) { calls.push(JSON.parse(line)) },
    on () {}
  }
  const trace = openT1wSidecar('/tmp/t1w-backpressure.jsonl', () => stream)
  trace.write({ kind: 'PHYSICS_EVENT_SAMPLE' })
  trace.write({ kind: 'MOVEMENT_WRITE_RETURNED' })
  trace.close()
  assert.equal(calls.length, 2)
  assert.equal(calls[1].lost, true)
  assert.equal(calls[1].complete, false)
})
