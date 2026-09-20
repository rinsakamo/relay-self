import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import {
  makeEnvelope,
  parseArgs,
  parseCommand,
  shouldEmitTimeObservation,
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

test('observe is a target-local snapshot probe, not an effect', () => {
  assert.deepEqual(
    parseCommand({ type: 'observe' }),
    { type: 'observe' }
  )
  assert.throws(
    () => parseCommand({ type: 'observe', action_id: 'not-an-action' }),
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

test('look accepts only explicit finite yaw and pitch', () => {
  assert.deepEqual(
    parseCommand({
      type: 'effect',
      action_id: 'action-look',
      effect: 'look',
      yaw: Math.PI / 2,
      pitch: 0
    }),
    {
      type: 'effect',
      action_id: 'action-look',
      effect: 'look',
      yaw: Math.PI / 2,
      pitch: 0
    }
  )

  assert.throws(
    () => parseCommand({
      type: 'effect',
      action_id: 'action-look-bad',
      effect: 'look',
      yaw: Infinity,
      pitch: 0
    }),
    /finite number/
  )
  assert.throws(
    () => parseCommand({
      type: 'effect',
      action_id: 'action-look-extra',
      effect: 'look',
      yaw: 0,
      pitch: 0,
      destination: 'cave'
    }),
    /fields are invalid/
  )
})

test('equip_item and consume_held remain separate primitive effects', () => {
  assert.deepEqual(
    parseCommand({
      type: 'effect',
      action_id: 'action-equip',
      effect: 'equip_item',
      item_name: 'bread'
    }),
    {
      type: 'effect',
      action_id: 'action-equip',
      effect: 'equip_item',
      item_name: 'bread'
    }
  )
  assert.deepEqual(
    parseCommand({
      type: 'effect',
      action_id: 'action-consume',
      effect: 'consume_held'
    }),
    {
      type: 'effect',
      action_id: 'action-consume',
      effect: 'consume_held'
    }
  )
  assert.throws(
    () => parseCommand({
      type: 'effect',
      action_id: 'action-eat',
      effect: 'consume_held',
      item_name: 'bread'
    }),
    /fields are invalid/
  )
})

test('snapshot exposes survival facts without appraisal labels', () => {
  const snapshot = snapshotFromBot({
    health: 12,
    food: 7,
    oxygenLevel: 20,
    time: {
      timeOfDay: 13000,
      day: 2,
      isDay: false
    },
    entity: {
      id: 1,
      position: { x: 1.5, y: 64, z: -2.25 }
    },
    inventory: {
      items: () => [
        { name: 'bread', count: 3, slot: 10 },
        { name: 'oak_log', count: 5, slot: 9 }
      ]
    },
    entities: {
      1: {
        id: 1,
        name: 'player',
        type: 'player',
        position: { x: 1.5, y: 64, z: -2.25 }
      },
      2: {
        id: 2,
        name: 'zombie',
        type: 'mob',
        position: { x: 4.5, y: 64, z: -2.25 }
      },
      3: {
        id: 3,
        name: 'cow',
        type: 'mob',
        position: { x: 100, y: 64, z: 100 }
      }
    }
  })

  assert.deepEqual(snapshot, {
    health: 12,
    food: 7,
    oxygen_level: 20,
    position: { x: 1.5, y: 64, z: -2.25 },
    time: {
      time_of_day: 13000,
      day: 2,
      is_day: false
    },
    inventory: [
      { name: 'oak_log', count: 5, slot: 9 },
      { name: 'bread', count: 3, slot: 10 }
    ],
    nearby_entities: [
      {
        id: 2,
        name: 'zombie',
        type: 'mob',
        distance: 3,
        position: { x: 4.5, y: 64, z: -2.25 }
      }
    ],
    nearby_entities_coverage: {
      source_scope: 'mineflayer_entity_registry',
      max_distance: 16,
      max_entities: 16,
      candidate_count: 1,
      truncated: false
    }
  })
  const serialized = JSON.stringify(snapshot)
  assert.equal(serialized.includes('danger'), false)
  assert.equal(serialized.includes('fear'), false)
  assert.equal(serialized.includes('hostile'), false)
})

test('bounded entity snapshot declares truncation coverage', () => {
  const entities = {
    1: {
      id: 1,
      name: 'player',
      type: 'player',
      position: { x: 0, y: 64, z: 0 }
    }
  }
  for (let id = 2; id <= 18; id += 1) {
    entities[id] = {
      id,
      name: 'zombie',
      type: 'mob',
      position: { x: id - 1, y: 64, z: 0 }
    }
  }

  const snapshot = snapshotFromBot({
    health: 20,
    food: 20,
    oxygenLevel: 20,
    time: {
      timeOfDay: null,
      day: null,
      isDay: null
    },
    entity: {
      id: 1,
      position: { x: 0, y: 64, z: 0 }
    },
    inventory: {
      items: () => []
    },
    entities
  })

  assert.equal(snapshot.nearby_entities.length, 16)
  assert.deepEqual(
    snapshot.nearby_entities.map((entity) => entity.id),
    Array.from({ length: 16 }, (_, index) => index + 2)
  )
  assert.deepEqual(snapshot.nearby_entities_coverage, {
    source_scope: 'mineflayer_entity_registry',
    max_distance: 16,
    max_entities: 16,
    candidate_count: 16,
    truncated: false
  })
})

test('bounded entity snapshot marks in-radius candidates truncated at cap', () => {
  const entities = {
    1: {
      id: 1,
      name: 'player',
      type: 'player',
      position: { x: 0, y: 64, z: 0 }
    }
  }
  for (let id = 2; id <= 19; id += 1) {
    const angle = (id - 2) * (Math.PI * 2 / 18)
    entities[id] = {
      id,
      name: 'zombie',
      type: 'mob',
      position: {
        x: Math.cos(angle) * 5,
        y: 64,
        z: Math.sin(angle) * 5
      }
    }
  }

  const snapshot = snapshotFromBot({
    health: 20,
    food: 20,
    oxygenLevel: 20,
    time: {
      timeOfDay: null,
      day: null,
      isDay: null
    },
    entity: {
      id: 1,
      position: { x: 0, y: 64, z: 0 }
    },
    inventory: {
      items: () => []
    },
    entities
  })

  assert.equal(snapshot.nearby_entities.length, 16)
  assert.equal(snapshot.nearby_entities_coverage.candidate_count, 18)
  assert.equal(snapshot.nearby_entities_coverage.truncated, true)
})

test('snapshot still fails closed when health is not initialized', () => {
  assert.throws(
    () => snapshotFromBot({
      health: undefined,
      food: 20,
      oxygenLevel: 20,
      time: {
        timeOfDay: null,
        day: null,
        isDay: null
      },
      entity: {
        id: 1,
        position: { x: 0, y: 64, z: 0 }
      },
      inventory: {
        items: () => []
      },
      entities: {}
    }),
    /bot\.health must be a finite number/
  )
})

test('snapshot represents unobserved oxygen as null', () => {
  const snapshot = snapshotFromBot({
    health: 20,
    food: 20,
    oxygenLevel: undefined,
    time: {
      timeOfDay: null,
      day: null,
      isDay: null
    },
    entity: {
      id: 1,
      position: { x: 0, y: 64, z: 0 }
    },
    inventory: {
      items: () => []
    },
    entities: {}
  })

  assert.equal(snapshot.oxygen_level, null)
})

test('snapshot still fails closed for malformed observed oxygen', () => {
  assert.throws(
    () => snapshotFromBot({
      health: 20,
      food: 20,
      oxygenLevel: Number.NaN,
      time: {
        timeOfDay: null,
        day: null,
        isDay: null
      },
      entity: {
        id: 1,
        position: { x: 0, y: 64, z: 0 }
      },
      inventory: {
        items: () => []
      },
      entities: {}
    }),
    /bot\.oxygenLevel must be a finite number/
  )
})

test('snapshot allows time to remain null before first time update', () => {
  const snapshot = snapshotFromBot({
    health: 20,
    food: 20,
    oxygenLevel: 20,
    time: {
      timeOfDay: null,
      day: null,
      isDay: null
    },
    entity: {
      id: 1,
      position: { x: 0, y: 64, z: 0 }
    },
    inventory: {
      items: () => []
    },
    entities: {}
  })

  assert.equal(snapshot.time, null)
  assert.deepEqual(snapshot.inventory, [])
  assert.deepEqual(snapshot.nearby_entities, [])
  assert.deepEqual(snapshot.nearby_entities_coverage, {
    source_scope: 'mineflayer_entity_registry',
    max_distance: 16,
    max_entities: 16,
    candidate_count: 0,
    truncated: false
  })
})

test('time admission ignores ordinary clock progression within one phase', () => {
  assert.equal(
    shouldEmitTimeObservation(null, null, { day: 2, isDay: true }),
    true
  )
  assert.equal(
    shouldEmitTimeObservation(2, true, { day: 2, isDay: true }),
    false
  )
  assert.equal(
    shouldEmitTimeObservation(2, true, { day: 2, isDay: false }),
    true
  )
  assert.equal(
    shouldEmitTimeObservation(2, false, { day: 3, isDay: true }),
    true
  )
  assert.equal(
    shouldEmitTimeObservation(2, false, { day: null, isDay: null }),
    false
  )
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
