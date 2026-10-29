// G3.2 Paper T1u modifier identity: exact Node decoder opt-in, unchanged wire owner.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { decodeSnapshot } from './paper_snapshot_admission.mjs'

function source (details) {
  const gait_dev = {
    sneaking: false, sprinting: true, speed_base: 0.1,
    speed_value: 0.195, speed_modifiers: 2
  }
  if (details !== undefined) gait_dev.speed_modifier_details = details
  return {
    version: 1, boot: '00000000-0000-0000-0000-000000000001',
    index: 1, tick: 50, world_tick: 50, paper_ns: 1,
    world: '00000000-0000-0000-0000-000000000002',
    player: '00000000-0000-0000-0000-000000000003',
    challenge: 'NONE', x: 0, y: 65, z: 0, health: 20, food: 20,
    input: 0, threats_complete: true, threats: [],
    basal_ticks: 1, basal_exhaustion: 0, motion_blocks: 0,
    motion_exhaustion: 0, gait_dev
  }
}
const exact = [
  { key: 'minecraft:sprinting', operation: 'MULTIPLY_SCALAR_1', amount: 0.3 },
  { key: 'relays49dashdev:forward_dash_only', operation: 'MULTIPLY_SCALAR_1', amount: 0.5 }
]
const decode = x => decodeSnapshot(Buffer.from(JSON.stringify(x), 'utf8'))

test('original T1u legacy five-field Paper source stays accepted', () => {
  assert.equal(decode(source()).gait_dev.speed_modifier_details, undefined)
})
test('exact same-Paper-tick modifiers preserve keys, power and operation', () => {
  assert.deepEqual(decode(source(exact)).gait_dev.speed_modifier_details, exact)
})
test('G3 Paper modifier source refuses foreign shape, duplicates and size', () => {
  for (const details of [
    exact.slice(0, 1), [...exact, exact[1]], [...exact].reverse(),
    [{ ...exact[0], operation: 'BOGUS' }, exact[1]],
    [exact[0], { ...exact[1], amount: Number.NaN }],
    [exact[0], { ...exact[1], amount: 5 }],
    [exact[0], { ...exact[1], key: 'not-namespaced' }],
    [exact[0], { ...exact[1], other: 'injected' }]
  ]) assert.throws(() => decode(source(details)))
})
test('G3 identity cannot be smuggled outside gait_dev', () => {
  const s = source(exact)
  s.unexpected = true
  assert.throws(() => decode(s))
})
