import { EventEmitter } from 'node:events'
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { attachPassiveS50PacketTrace, clientPose, packetFields } from './s50_p1_packet_trace.mjs'

function makeBot () {
  const client = new EventEmitter()
  const writes = []
  client.write = function (...args) {
    writes.push({ receiver: this, args })
    return 'original-return'
  }
  const bot = { _client: client, entity: { yaw: 0, pitch: 0 } }
  return { bot, client, writes }
}

test('one passive outbound look packet delegates exactly once with same receiver and args', () => {
  const { bot, client, writes } = makeBot()
  const rows = []
  const contract = attachPassiveS50PacketTrace(bot, (row) => rows.push(row))
  assert.equal(contract.passive_only, true)
  const payload = { yaw: 270, pitch: 0, onGround: true }
  const answer = client.write('look', payload)
  assert.equal(answer, 'original-return')
  assert.equal(writes.length, 1)
  assert.equal(writes[0].receiver, client)
  assert.equal(writes[0].args[0], 'look')
  assert.equal(writes[0].args[1], payload)
  assert.deepEqual(rows.map((x) => [x.kind, x.packet_name]), [['PACKET_OUT', 'look']])
  assert.deepEqual(rows[0].packet_fields, { shape_valid: true, yaw: 270, pitch: 0, onGround: true })
  client.write('other_packet', { foo: 'opaque' })
  assert.equal(writes.length, 2)
  assert.equal(rows.length, 1)
})

test('clientbound correction has observable BEFORE -> unchanged original callback -> AFTER', () => {
  const { bot, client, writes } = makeBot()
  const callbackOrder = []
  client.on('position', (packet) => {
    callbackOrder.push('mineflayer-core')
    bot.entity.yaw = Math.PI
    client.write('teleport_confirm', { teleportId: packet.teleportId })
  })
  const rows = []
  attachPassiveS50PacketTrace(bot, (row) => { callbackOrder.push(row.kind); rows.push(row) })
  const packet = { x: 0.5, y: -60, z: 0.5, yaw: 0, pitch: 0, flags: { yaw: false }, teleportId: 123 }
  client.emit('position', packet)
  assert.deepEqual(callbackOrder, [
    'PACKET_IN_BEFORE', 'mineflayer-core', 'PACKET_OUT', 'PACKET_IN_AFTER'
  ])
  assert.deepEqual(rows.map((r) => r.kind), [
    'PACKET_IN_BEFORE', 'PACKET_OUT', 'PACKET_IN_AFTER'
  ])
  assert.equal(rows[0].client_yaw_radians, 0)
  assert.equal(rows[2].client_yaw_radians, Math.PI)
  assert.equal(writes.length, 1)
  assert.equal(writes[0].args[0], 'teleport_confirm')
  assert.equal(writes[0].args[1].teleportId, 123)
  assert.equal(packet.yaw, 0)
})

test('passive rotation never creates a new motor packet or overwrites client yaw', () => {
  const { bot, client, writes } = makeBot()
  client.on('player_rotation', (p) => { bot.entity.yaw = p.yaw })
  const rows = []
  attachPassiveS50PacketTrace(bot, (row) => rows.push(row))
  client.emit('player_rotation', { yaw: 1.5, pitch: 0 })
  assert.equal(bot.entity.yaw, 1.5)
  assert.equal(writes.length, 0)
  assert.deepEqual(rows.map((x) => x.kind), ['PACKET_IN_BEFORE', 'PACKET_IN_AFTER'])
})

test('invalid source stays explicitly invalid rather than fabricated yaw', () => {
  assert.deepEqual(clientPose({}), { client_yaw_radians: null, client_pitch_radians: null })
  assert.equal(packetFields({ yaw: Infinity }).shape_valid, false)
  assert.equal(packetFields({ flags: { yaw: 'false' } }).shape_valid, false)
  assert.equal(packetFields(null).shape_valid, false)
})

test('source recorder failure fails before packet write, never silently bypasses audit', () => {
  const { bot, client, writes } = makeBot()
  attachPassiveS50PacketTrace(bot, () => { throw new Error('source write failed') })
  assert.throws(() => client.write('look', { yaw: 45 }), /source write failed/)
  assert.equal(writes.length, 0)
})
