import assert from 'node:assert/strict'
import test from 'node:test'

import { exactOwnerBackport, inspectOwnerPatch } from './oxygen_owner_patch.mjs'
import { OwnedOxygenWitness } from './oxygen_owner_witness.mjs'
import { snapshotFromBot } from './protocol.mjs'

const ORIGINAL = [
  '      // Breathing (formerly in breath.js)',
  '      if (metas.air_supply != null) {',
  '        bot.oxygenLevel = Math.round(metas.air_supply / 15)',
  "        bot.emit('breath')",
  '      }'
].join('\n')

function simulateMineflayerMetadata (code, packetEntityId, selfId) {
  const start = code.indexOf('      if (metas.air_supply')
  const snippet = code.slice(start, code.indexOf('      }', start) + 7)
  const events = []
  const bot = { entity: { id: selfId }, oxygenLevel: undefined, emit: (event) => events.push(event) }
  // The executed code is a local fixed-string fixture, never network data.
  const handler = new Function('entity', 'bot', 'metas', snippet)
  handler({ id: packetEntityId }, bot, { air_supply: 150 })
  return { level: bot.oxygenLevel, events }
}

function bot (oxygenLevel = 20) {
  return {
    health: 20, food: 20, foodSaturation: 5, oxygenLevel,
    entity: { id: 7, position: { x: 10, y: 64, z: 20 } },
    time: { timeOfDay: 6000, day: 0, isDay: true },
    inventory: { items: () => [] }, entities: {}
  }
}

test('exact backport demonstrably removes foreign Entity air_supply contamination', () => {
  assert.equal(inspectOwnerPatch(ORIGINAL), 'VULNERABLE')
  const fixed = exactOwnerBackport(ORIGINAL)
  assert.equal(inspectOwnerPatch(fixed), 'PATCHED')
  const foreignBefore = simulateMineflayerMetadata(ORIGINAL, 99, 7)
  assert.equal(foreignBefore.level, 10)
  assert.deepEqual(foreignBefore.events, ['breath'])
  const foreignAfter = simulateMineflayerMetadata(fixed, 99, 7)
  assert.equal(foreignAfter.level, undefined)
  assert.deepEqual(foreignAfter.events, [])
  const selfAfter = simulateMineflayerMetadata(fixed, 7, 7)
  assert.equal(selfAfter.level, 10)
  assert.deepEqual(selfAfter.events, ['breath'])
})

test('backport refuses unrecognised and already-patched source', () => {
  const fixed = exactOwnerBackport(ORIGINAL)
  assert.throws(() => exactOwnerBackport(fixed), /not exactly/)
  assert.throws(() => inspectOwnerPatch(''), /marker absent/)
  assert.throws(() => inspectOwnerPatch(ORIGINAL + ORIGINAL), /marker absent/)
  assert.throws(
    () => inspectOwnerPatch(ORIGINAL + fixed),
    /marker absent/,
  )
  assert.throws(
    () => inspectOwnerPatch(ORIGINAL.replace('bot.oxygenLevel', 'other.oxygenLevel')),
    /marker absent/,
  )
})

test('owned breath receipt proves owner, generation and finite freshness only', () => {
  let t = 0
  const witness = new OwnedOxygenWitness({ sessionId: 'native-B', clock: () => t, maxAgeMs: 5000 })
  assert.equal(witness.read(7).epistemic_status, 'UNKNOWN')
  witness.bindSelf(7)
  assert.equal(witness.acceptBreath({ entityId: 99, oxygenLevel: 20 }), false)
  assert.equal(witness.read(7).level, null)
  assert.equal(witness.acceptBreath({ entityId: 7, oxygenLevel: 20 }), true)
  let receipt = witness.read(7)
  assert.equal(receipt.level, 20)
  assert.equal(receipt.epistemic_status, 'FRESH_OWNED')
  assert.equal(receipt.self_entity_id, 7)
  assert.equal(receipt.session_id, 'native-B')
  assert.equal(receipt.source_seq, 1)
  assert.equal(receipt.physical_authorized, false)
  t = 5000
  assert.equal(witness.read(7).level, 20)
  t = 5001
  receipt = witness.read(7)
  assert.equal(receipt.epistemic_status, 'STALE_OR_UNVERIFIED')
  assert.equal(receipt.level, null)
})

test('death/respawn and owner replacement invalidate even the same old Entity ID', () => {
  const witness = new OwnedOxygenWitness({ sessionId: 'native-B' })
  witness.bindSelf(7)
  witness.acceptBreath({ entityId: 7, oxygenLevel: 15 })
  assert.equal(witness.read(7).level, 15)
  witness.invalidate()
  assert.equal(witness.read(7).level, null)
  witness.bindSelf(7)
  assert.equal(witness.read(7).level, null)
  assert.equal(witness.acceptBreath({ entityId: 7, oxygenLevel: NaN }), false)
  assert.equal(witness.acceptBreath({ entityId: 7, oxygenLevel: -1 }), false)
  assert.equal(witness.acceptBreath({ entityId: 7, oxygenLevel: 12 }), true)
  assert.equal(witness.read(99).level, null)
  witness.bindSelf(8)
  assert.equal(witness.read(8).level, null)
  assert.equal(witness.acceptBreath({ entityId: 7, oxygenLevel: 20 }), false)
  assert.equal(witness.acceptBreath({ entityId: 8, oxygenLevel: 10 }), true)
  assert.equal(witness.read(8).level, 10)
})

test('physical snapshot cannot consume unqualified/stale bot.oxygenLevel', () => {
  let t = 0
  const witness = new OwnedOxygenWitness({ sessionId: 'native-B', clock: () => t, maxAgeMs: 5000 })
  witness.bindSelf(7)
  const stub = bot(20)
  assert.equal(snapshotFromBot(stub, witness.read(7)).oxygen_level, null)
  witness.acceptBreath({ entityId: 7, oxygenLevel: 10 })
  assert.equal(snapshotFromBot(stub, witness.read(7)).oxygen_level, 10)
  // This is deliberately NOT the original unqualified bot.oxygenLevel=20.
  t = 6000
  assert.equal(snapshotFromBot(stub, witness.read(7)).oxygen_level, null)
  witness.bindSelf(7)
  assert.equal(snapshotFromBot(stub, witness.read(7)).oxygen_level, null)
})
