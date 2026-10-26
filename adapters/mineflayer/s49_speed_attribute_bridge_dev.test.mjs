import test from 'node:test'
import assert from 'node:assert/strict'

import { projectS49DevMovementSpeed as project } from './s49_speed_attribute_bridge_dev.mjs'

const base = () => ({
  value: 0.10000000149011612,
  modifiers: [
    { uuid: 'minecraft:sprinting', amount: 0.30000001192092896,
      operation: 2 }
  ]
})
test('recognizes natural sprint and removes its duplicate simulator modifier', () => {
  const source = base()
  const out = project(source)
  assert.deepEqual(out.attribute.modifiers, [])
  assert.equal(out.dash, false)
  assert.equal(out.targetName, 'minecraft:movement_speed')
  assert.equal(source.modifiers.length, 1)
})
test('projects exact Paper modifier only once for +50 percent', () => {
  const source = base()
  source.modifiers.push({
    uuid: 'relays49dashdev:forward_dash_only', amount: 0.5, operation: 2
  })
  const out = project(source)
  assert.deepEqual(out.attribute.modifiers, [
    { uuid: 'relays49dashdev:forward_dash_only', amount: 0.5, operation: 2 }
  ])
  assert.equal(out.dash, true)
  const expectedSpeed = out.attribute.value * 1.5 * 1.3
  assert.ok(Math.abs(expectedSpeed - 0.195) < 1e-5)
})
test('strict fail closed on any unknown, repeated or forged native material', () => {
  const candidates = [
    {}, { value: 1, modifiers: [] }, { value: 0.1, modifiers: [] },
    { ...base(), modifiers: [...base().modifiers, ...base().modifiers] },
    { ...base(), modifiers: [{ uuid: 'minecraft:sprinting', amount: 0.3, operation: 1 }] },
    { ...base(), modifiers: [{ uuid: 'minecraft:sprinting', amount: 0.4, operation: 2 }] },
    { ...base(), modifiers: [{ uuid: 'foreign:boost', amount: 0.5, operation: 2 }] },
    { ...base(), modifiers: [...base().modifiers,
      { uuid: 'relays49dashdev:forward_dash_only', amount: 0.501, operation: 2 }] },
    { ...base(), modifiers: [...base().modifiers,
      { uuid: 'relays49dashdev:forward_dash_only', amount: Infinity, operation: 2 }] },
    { ...base(), modifiers: [...base().modifiers,
      { uuid: 'relays49dashdev:forward_dash_only', amount: 0.5, operation: 2 },
      { uuid: 'extra:boost', amount: 0.1, operation: 2 }] }
  ]
  for (const x of candidates) assert.equal(project(x), null)
})
