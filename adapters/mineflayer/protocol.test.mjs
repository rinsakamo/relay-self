import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import {
  makeEnvelope,
  parseArgs,
  parseCommand,
  snapshotFromBot
} from './protocol.mjs'

test('package pins the qualified Mineflayer major surface and Node floor', () => {
  const manifest = JSON.parse(
    readFileSync(new URL('./package.json', import.meta.url), 'utf8')
  )
  assert.equal(manifest.dependencies.mineflayer, '4.39.0')
  assert.equal(manifest.engines.node, '>=22')
})

test('adapter arguments default to local offline MVP connection values', () => {
  assert.deepEqual(parseArgs([]), {
    host: '127.0.0.1',
    port: 25565,
    username: 'RelaySelf',
    version: null
  })
})

test('adapter arguments accept explicit local server coordinates', () => {
  assert.deepEqual(
    parseArgs([
      '--host', 'localhost',
      '--port', '25566',
      '--username', 'Rin',
      '--version', '1.21.8'
    ]),
    {
      host: 'localhost',
      port: 25566,
      username: 'Rin',
      version: '1.21.8'
    }
  )
})

test('adapter arguments reject unknown or malformed values', () => {
  assert.throws(() => parseArgs(['--port', '0']), /1\.\.65535/)
  assert.throws(() => parseArgs(['--mystery', 'x']), /unknown argument/)
  assert.throws(() => parseArgs(['--host']), /missing value/)
})

test('set_control accepts only exact bounded control commands', () => {
  const command = parseCommand({
    type: 'effect',
    action_id: 'action-1',
    effect: 'set_control',
    control: 'forward',
    state: true
  })
  assert.deepEqual(command, {
    type: 'effect',
    action_id: 'action-1',
    effect: 'set_control',
    control: 'forward',
    state: true
  })

  assert.throws(
    () => parseCommand({
      type: 'effect',
      action_id: 'action-2',
      effect: 'set_control',
      control: 'teleport',
      state: true
    }),
    /unsupported control/
  )
  assert.throws(
    () => parseCommand({
      type: 'effect',
      action_id: 'action-3',
      effect: 'set_control',
      control: 'forward',
      state: true,
      duration: 10
    }),
    /fields are invalid/
  )
})

test('clear_controls remains a primitive effect without hidden duration', () => {
  assert.deepEqual(
    parseCommand({
      type: 'effect',
      action_id: 'action-4',
      effect: 'clear_controls'
    }),
    {
      type: 'effect',
      action_id: 'action-4',
      effect: 'clear_controls'
    }
  )
})

test('snapshot exposes body resources and position without appraisal labels', () => {
  const snapshot = snapshotFromBot({
    health: 12,
    food: 7,
    oxygenLevel: 20,
    entity: {
      position: { x: 1.5, y: 64, z: -2.25 }
    }
  })

  assert.deepEqual(snapshot, {
    health: 12,
    food: 7,
    oxygen_level: 20,
    position: { x: 1.5, y: 64, z: -2.25 }
  })
  assert.equal(JSON.stringify(snapshot).includes('danger'), false)
  assert.equal(JSON.stringify(snapshot).includes('fear'), false)
})

test('envelope preserves target-local session and monotonic sequence fields', () => {
  assert.deepEqual(
    makeEnvelope('session-1', 3, 'observation', { kind: 'health' }),
    {
      type: 'observation',
      session_id: 'session-1',
      seq: 3,
      kind: 'health'
    }
  )
})
