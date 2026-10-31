import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { test } from 'node:test'
import {
  positionOfTarget, readCommitment, readOnlyCommand, statusFromSamples
} from '../adapters/mineflayer/l21_goal_observer_core.mjs'

const criterion = Object.freeze({
  target_x: 10, target_z: -4, tolerance_m: 0.49,
  stable_probe_delta_max_m: 0.05
})
const make = (x, z, entity_id = 44) => ({ entity_id, x, y: 64, z })
function original () {
  const doc = {
    schema: 'L20_PRE_WORLD_EXTERNAL_GOAL_COMMITMENT_V1',
    criterion_id: 'separate-observer-goal-001',
    external_goal_owner_ref: 'reviewer-123',
    experiment_ref: 'physical-epoch-one',
    session_scope: 'UNKNOWN_UNTIL_S49_SESSION_START',
    action_scope: 'FIRST_S49_PHYSICAL_ACTION_ONLY',
    independent_goal_observed: false,
    authorizes_learning: false,
    ...criterion
  }
  return Buffer.from(JSON.stringify(Object.fromEntries(
    Object.keys(doc).sort().map(k => [k, doc[k]])
  )) + '\n')
}
test('accepts fixed external original by exact SHA but no physical authority', () => {
  const raw = original()
  const sha = createHash('sha256').update(raw).digest('hex')
  const doc = readCommitment(raw, sha)
  assert.equal(doc.target_x, 10)
  assert.equal(doc.external_goal_owner_ref, 'reviewer-123')
  assert.equal(doc.authorizes_learning, false)
  assert.throws(() => readCommitment(raw, '0'.repeat(64)))
  assert.throws(() => readCommitment(Buffer.concat([raw, raw]), sha))
})
test('read-only command vocabulary rejects any motor-like command', () => {
  assert.deepEqual(readOnlyCommand('{"type":"shutdown"}'), { type: 'shutdown' })
  assert.equal(
    readOnlyCommand('{"type":"sample","request_id":"l16:sid:a:goal-1"}').request_id,
    'l16:sid:a:goal-1'
  )
  for (const command of [
    '{"type":"effect","effect":"set_control","control":"forward"}',
    '{"type":"attack_entity","entity_id":12}',
    '{"type":"sample","request_id":"bad id"}',
    '{"type":"sample","request_id":"ok","move":"forward"}',
    '{"type":"shutdown","force":true}',
    '{"type":"observe"}',
    'null'
  ]) assert.throws(() => readOnlyCommand(command))
})
test('one separate player entity only; no RelaySelf lookalike or self entity', () => {
  const target = { id: 44, position: { x: 10, y: 64, z: -4 } }
  const bot = {
    username: 'RelayGoalObserver', entity: { id: 99 },
    players: { RelaySelf: { entity: target } }
  }
  assert.deepEqual(positionOfTarget(bot, 'RelaySelf'), make(10, -4))
  assert.equal(positionOfTarget(bot, 'RelayGoalObserver'), null)
  assert.equal(positionOfTarget(bot, 'OtherPlayer'), null)
  target.id = 99
  assert.equal(positionOfTarget(bot, 'RelaySelf'), null)
  target.id = 44
  target.position.x = Number.NaN
  assert.equal(positionOfTarget(bot, 'RelaySelf'), null)
})
test('Goal from two read-only samples fails closed for unknown drift mismatch', () => {
  assert.equal(statusFromSamples(make(10, -4), make(10.02, -4), criterion), 'REACHED')
  assert.equal(statusFromSamples(make(0, 0), make(0.01, 0), criterion), 'NOT_REACHED')
  assert.equal(statusFromSamples(make(10, -4), make(10.8, -4), criterion), 'UNDETERMINED')
  assert.equal(statusFromSamples(make(0, 0), make(0, 0, 55), criterion), 'UNDETERMINED')
  assert.equal(statusFromSamples(null, make(10, -4), criterion), 'UNDETERMINED')
  assert.equal(statusFromSamples(make(10, -4), null, criterion), 'UNDETERMINED')
  assert.equal(statusFromSamples(make(10, -4), make(10, -4.7), criterion), 'UNDETERMINED')
})
