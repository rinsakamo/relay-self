import assert from 'node:assert/strict'
import test from 'node:test'
import { paperL0Shadow, evaluatePaperL0Shadow } from './paper_l0_shadow.mjs'

const sample = { source: 'PAPER_SCHEDULER_CALLBACK_ONLY', index: 1,
  server_tick: '100', world: 'world', player: 'bot' }
const bot = { health: 20, food: 20,
  entity: { position: { x: 0, y: 65, z: 0 } }, entities: {} }

test('no action authorizations from a fully evaluated cache shadow', () => {
  const v = paperL0Shadow(sample, bot, 100n, 101n)
  assert.equal(v.assessment, 'NO_KNOWN_URGENT_SIGNAL')
  assert.equal(v.l0_shadow_evaluated, true)
  assert.equal(v.l0_fresh_world_tick_attested, false)
  assert.equal(v.authorized_action_issued, false)
  assert.equal(v.tps_admission_granted, false)
  assert.equal(v.evaluation_duration_ns, '1')
})
test('detects known body urgency and nearby cached threats', () => {
  assert.equal(paperL0Shadow(sample, {...bot, health: 4}, 100n, 120n).assessment, 'LOW_HEALTH')
  assert.equal(paperL0Shadow(sample, {...bot, food: 4}, 100n, 120n).assessment, 'LOW_FOOD')
  const threat = {...bot, entities: {z: {name: 'zombie', position: {x: 2, y: 65, z: 0}}}}
  assert.equal(paperL0Shadow(sample, threat, 100n, 120n).assessment, 'KNOWN_NEAR_HOSTILE')
})
test('missing/stale bot state is never a safe observation', () => {
  for (const b of [null, {}, {...bot, health: NaN}, {...bot, entities: undefined}]) {
    const v = evaluatePaperL0Shadow(sample, b)
    assert.equal(v.assessment, 'UNKNOWN')
    assert.equal(v.l0_fresh_world_tick_attested, false)
  }
  assert.equal(paperL0Shadow(sample, {...bot, entities: Object.fromEntries(Array.from({length:129}, (_,i)=>[i,{}]))}, 1n, 2n).assessment, 'UNKNOWN')
})
test('malformed Paper metadata or time is rejected', () => {
  for (const s of [{...sample,index:257}, {...sample,index:1.5}, {...sample,source:'fake'}]) {
    assert.throws(() => paperL0Shadow(s, bot, 1n, 2n))
  }
  assert.throws(() => paperL0Shadow(sample,bot,3n,2n))
})
