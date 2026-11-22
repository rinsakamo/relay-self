import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { captureSenseTerrain, SENSE_EXPECTED_CELLS } from './sense_terrain.mjs'

import {
  admitProbeRequestId,
  makeEnvelope,
  makeProbePayload,
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

test('correlated probe request IDs follow original S49 read-only contract', () => {
  const seen = new Set()
  assert.deepEqual(parseCommand({ type: 'observe', request_id: 'cognitive-01' }), {
    type: 'observe', request_id: 'cognitive-01'
  })
  assert.equal(admitProbeRequestId(seen, 'cognitive-01'), true)
  assert.equal(admitProbeRequestId(seen, 'cognitive-01'), false)
  assert.equal(admitProbeRequestId(seen, 'cognitive-02'), true)
  assert.deepEqual(makeProbePayload({ health: 20 }, 'cognitive-02'), {
    kind: 'probe', snapshot: { health: 20 }, request_id: 'cognitive-02'
  })
  assert.deepEqual(makeProbePayload({ health: 20 }), {
    kind: 'probe', snapshot: { health: 20 }
  })
  for (const requestId of ['', 'bad space', '☃', '-bad', 'a'.repeat(129)]) {
    assert.throws(() => parseCommand({ type: 'observe', request_id: requestId }), /request_id/)
    assert.throws(() => makeProbePayload({}, requestId), /request_id/)
  }
  assert.throws(() => parseCommand({
    type: 'observe', request_id: 'probe-1', action_id: 'invalid'
  }), /fields are invalid/)
  assert.throws(() => admitProbeRequestId([], 'probe-1'), /Set/)
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

test('attack_entity requires one explicit non-negative entity id', () => {
  assert.deepEqual(
    parseCommand({
      type: 'effect',
      action_id: 'action-attack',
      effect: 'attack_entity',
      entity_id: 7
    }),
    {
      type: 'effect',
      action_id: 'action-attack',
      effect: 'attack_entity',
      entity_id: 7
    }
  )

  assert.throws(
    () => parseCommand({
      type: 'effect',
      action_id: 'action-attack-negative',
      effect: 'attack_entity',
      entity_id: -1
    }),
    /non-negative integer/
  )
  assert.throws(
    () => parseCommand({
      type: 'effect',
      action_id: 'action-attack-float',
      effect: 'attack_entity',
      entity_id: 7.5
    }),
    /non-negative integer/
  )
  assert.throws(
    () => parseCommand({
      type: 'effect',
      action_id: 'action-attack-extra',
      effect: 'attack_entity',
      entity_id: 7,
      repeat: true
    }),
    /fields are invalid/
  )
})

test('snapshot exposes survival facts without appraisal labels', () => {
  const snapshot = snapshotFromBot({
    health: 12,
    food: 7,
    foodSaturation: 5,
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
    food_saturation: 5,
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
    foodSaturation: 5,
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
    foodSaturation: 5,
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
      foodSaturation: 5,
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
    foodSaturation: 5,
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
      foodSaturation: 5,
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
    foodSaturation: 5,
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

test('E1 sense_terrain is a read-only correlated command, not physical LOOK', () => {
  assert.deepEqual(parseCommand({ type: 'sense_terrain', request_id: 'sense-7' }), {
    type: 'sense_terrain', request_id: 'sense-7'
  })
  assert.throws(() => parseCommand({ type: 'sense_terrain' }), /fields are invalid|request_id/)
  assert.throws(() => parseCommand({
    type: 'sense_terrain', request_id: 'sense-7', action_id: 'a'
  }), /fields are invalid/)
  assert.throws(() => parseCommand({
    type: 'sense_terrain', request_id: 'bad space'
  }), /request_id/)
})

test('E1 SENSE returns 100 bounded cells without inventing an AABB', () => {
  class Position {
    constructor (x, y, z) { this.x = x; this.y = y; this.z = z }
    floored () { return new Position(Math.floor(this.x), Math.floor(this.y), Math.floor(this.z)) }
    offset (dx, dy, dz) {
      return new Position(this.x + dx, this.y + dy, this.z + dz)
    }
  }
  const calls = []
  const bot = {
    entity: { position: new Position(0.5, 64, 0.5), width: 0.6, height: 1.8 },
    game: { dimension: 'minecraft:overworld' },
    blockAt: (pos, extraInfos) => {
      calls.push({ pos, extraInfos })
      if (pos.x === 2 && pos.y === 65 && pos.z === 2) return null
      if (pos.x === 1 && pos.y === 64 && pos.z === 0) {
        return { name: 'stone', shapes: [[0, 0, 0, 1, 1, 1]] }
      }
      return { name: 'air', shapes: [] }
    }
  }
  const t = captureSenseTerrain(bot)
  assert.equal(t.source_scope, 'mineflayer_loaded_blocks')
  assert.equal(t.expected_cells, SENSE_EXPECTED_CELLS)
  assert.equal(t.cells.length, 100)
  assert.equal(calls.length, 100)
  assert(calls.every(c => c.extraInfos === false))
  assert.equal(t.known_cells, 99)
  assert.equal(t.complete, false)
  assert.equal(t.body_aabb, null)
  const wall = t.cells.find(c => c.position.join(',') === '1,64,0')
  assert.deepEqual(wall.shapes, [[1, 64, 0, 2, 65, 1]])
  const missing = t.cells.find(c => c.position.join(',') === '2,65,2')
  assert.equal(missing.name, null)
  assert.equal(missing.shapes, null)
})

test('E1 invalid shapes and missing body are explicit UNKNOWN, never air/CLEAR', () => {
  class Position {
    constructor (x, y, z) { this.x = x; this.y = y; this.z = z }
    floored () { return this }
    offset (x, y, z) { return new Position(this.x + x, this.y + y, this.z + z) }
  }
  const bot = {
    entity: { position: new Position(0, 64, 0) },
    blockAt: () => ({ name: 'fence', shapes: [[0, 0, 0, 3, 1, 1]] })
  }
  const t = captureSenseTerrain(bot)
  assert.equal(t.body_aabb, null)
  assert.equal(t.known_cells, 0)
  assert.equal(t.complete, false)
  assert(t.cells.every(c => c.shapes === null))
  assert.throws(() => captureSenseTerrain({}), /live entity/)
})

test('E1 overhanging fence collision geometry survives instead of becoming air', () => {
  class Position {
    constructor (x, y, z) { this.x = x; this.y = y; this.z = z }
    floored () { return this }
    offset (dx, dy, dz) { return new Position(this.x + dx, this.y + dy, this.z + dz) }
  }
  const bot = {
    entity: { position: new Position(0, 64, 0), width: 0.6, height: 1.8 },
    blockAt: (pos) => pos.x === 1 && pos.y === 64 && pos.z === 0
      ? { name: 'oak_fence', shapes: [[0.375, 0, 0.375, 0.625, 1.5, 0.625]] }
      : { name: 'air', shapes: [] }
  }
  const terrain = captureSenseTerrain(bot)
  assert.equal(terrain.complete, true)
  const fence = terrain.cells.find(c => c.position.join(',') === '1,64,0')
  assert.deepEqual(fence.shapes, [[1.375, 64, 0.375, 1.625, 65.5, 0.625]])
})

test('E1 body motion, pose changes and world swaps during bounded scan all invalidate coverage', () => {
  class Position {
    constructor (x, y, z) { this.x = x; this.y = y; this.z = z }
    floored () { return new Position(Math.floor(this.x), Math.floor(this.y), Math.floor(this.z)) }
    offset (x, y, z) { return new Position(this.x + x, this.y + y, this.z + z) }
  }
  for (const mutation of ['pose', 'position', 'world', 'entity']) {
    const entity = { position: new Position(0.5, 64, 0.5), pose: 'standing' }
    let reads = 0
    const bot = {
      entity,
      game: { dimension: 'minecraft:overworld' },
      blockAt: () => {
        reads += 1
        if (reads === 50) {
          if (mutation === 'pose') entity.pose = 'sneaking'
          if (mutation === 'position') entity.position.x += 0.25
          if (mutation === 'world') bot.game.dimension = 'minecraft:the_nether'
          if (mutation === 'entity') bot.entity = { position: entity.position, pose: 'standing' }
        }
        return { name: 'air', shapes: [] }
      }
    }
    const sample = captureSenseTerrain(bot)
    assert.equal(reads, 100)
    assert.equal(sample.complete, false, mutation)
    assert.equal(sample.known_cells, 0, mutation)
    assert.equal(sample.body_aabb, null, mutation)
    assert(sample.cells.every(cell => cell.name === null && cell.shapes === null), mutation)
  }
})

test('E1 unchanged synchronous block read does not hallucinate body dimensions', () => {
  class Position {
    constructor (x, y, z) { this.x = x; this.y = y; this.z = z }
    floored () { return new Position(Math.floor(this.x), Math.floor(this.y), Math.floor(this.z)) }
    offset (x, y, z) { return new Position(this.x + x, this.y + y, this.z + z) }
  }
  const bot = {
    entity: { position: new Position(0.5, 64, 0.5), pose: 'sneaking', width: 0.6, height: 1.5 },
    game: { dimension: 'minecraft:overworld' },
    blockAt: () => ({ name: 'air', shapes: [] })
  }
  const sample = captureSenseTerrain(bot)
  assert.equal(sample.complete, true)
  assert.equal(sample.known_cells, 100)
  assert.equal(sample.body_pose, 'sneaking')
  assert.equal(sample.body_aabb, null)
})
