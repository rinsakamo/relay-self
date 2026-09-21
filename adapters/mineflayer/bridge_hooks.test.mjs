import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import test from 'node:test'

import {
  attachHealthSynchronizedSpawnListeners,
  attachInventoryUpdateListenerAfterInjection,
  entityHurtPayload,
  resolveAttackEntity
} from './bridge_hooks.mjs'

test('inventory listener waits for Mineflayer plugin injection', () => {
  const bot = new EventEmitter()
  let updateCount = 0

  attachInventoryUpdateListenerAfterInjection(bot, () => {
    updateCount += 1
  })

  assert.equal(bot.inventory, undefined)
  assert.equal(bot.listenerCount('inject_allowed'), 1)

  bot.inventory = new EventEmitter()
  bot.emit('inject_allowed')

  assert.equal(bot.listenerCount('inject_allowed'), 0)
  assert.equal(bot.inventory.listenerCount('updateSlot'), 1)

  bot.inventory.emit('updateSlot', 9)
  assert.equal(updateCount, 1)
})

test('missing inventory after injection fails explicitly', () => {
  const bot = new EventEmitter()

  attachInventoryUpdateListenerAfterInjection(bot, () => {})

  assert.throws(
    () => bot.emit('inject_allowed'),
    /inventory unavailable after inject_allowed/
  )
})

test('inventory hook validates its narrow bridge inputs', () => {
  assert.throws(
    () => attachInventoryUpdateListenerAfterInjection({}, () => {}),
    /bot must expose once/
  )

  const bot = new EventEmitter()
  assert.throws(
    () => attachInventoryUpdateListenerAfterInjection(bot, null),
    /listener must be a function/
  )
})

test('spawn observation waits for Mineflayer health initialization only', () => {
  const bot = new EventEmitter()
  const observed = []

  attachHealthSynchronizedSpawnListeners(
    bot,
    () => {
      observed.push({
        kind: 'spawn',
        health: bot.health,
        food: bot.food,
        oxygenLevel: bot.oxygenLevel
      })
    },
    () => {
      observed.push({
        kind: 'health',
        health: bot.health,
        food: bot.food,
        oxygenLevel: bot.oxygenLevel
      })
    }
  )

  bot.emit('spawn')
  assert.deepEqual(observed, [])

  bot.health = 20
  bot.food = 20
  bot.emit('health')

  assert.deepEqual(observed, [
    {
      kind: 'spawn',
      health: 20,
      food: 20,
      oxygenLevel: undefined
    }
  ])

  bot.oxygenLevel = 20
  bot.emit('breath')
  assert.equal(observed.length, 1)

  bot.health = 18
  bot.emit('health')

  assert.deepEqual(observed, [
    {
      kind: 'spawn',
      health: 20,
      food: 20,
      oxygenLevel: undefined
    },
    {
      kind: 'health',
      health: 18,
      food: 20,
      oxygenLevel: 20
    }
  ])
})

test('health before spawn remains an ordinary health event', () => {
  const bot = new EventEmitter()
  const observed = []

  attachHealthSynchronizedSpawnListeners(
    bot,
    () => observed.push('spawn'),
    () => observed.push('health')
  )

  bot.emit('health')
  assert.deepEqual(observed, ['health'])
})

test('health-synchronized spawn hook validates listeners', () => {
  assert.throws(
    () => attachHealthSynchronizedSpawnListeners({}, () => {}, () => {}),
    /bot must expose on/
  )

  const bot = new EventEmitter()
  assert.throws(
    () => attachHealthSynchronizedSpawnListeners(bot, null, () => {}),
    /spawn listener must be a function/
  )
  assert.throws(
    () => attachHealthSynchronizedSpawnListeners(bot, () => {}, null),
    /health listener must be a function/
  )
})


test('attack target resolver returns only the exact current entity id', () => {
  const zombie = { id: 7, name: 'zombie' }
  const cow = { id: 8, name: 'cow' }
  const bot = {
    entity: { id: 1 },
    entities: { 7: zombie, 8: cow }
  }

  assert.equal(resolveAttackEntity(bot, 7), zombie)
  assert.equal(resolveAttackEntity(bot, 8), cow)
})

test('attack target resolver fails closed on missing, self, or invalid ids', () => {
  const bot = {
    entity: { id: 1 },
    entities: { 7: { id: 7, name: 'zombie' } }
  }

  assert.throws(() => resolveAttackEntity(bot, 99), /entity_not_found/)
  assert.throws(() => resolveAttackEntity(bot, 1), /self_target/)
  assert.throws(() => resolveAttackEntity(bot, -1), /non-negative integer/)
  assert.throws(() => resolveAttackEntity(bot, 7.5), /non-negative integer/)
})


test('entityHurt payload preserves target and source identity', () => {
  assert.deepEqual(
    entityHurtPayload({ id: 7 }, { id: 1 }),
    {
      entity_id: 7,
      source_entity_id: 1
    }
  )
})

test('entityHurt payload preserves missing source without inventing one', () => {
  assert.deepEqual(
    entityHurtPayload({ id: 7 }, undefined),
    {
      entity_id: 7,
      source_entity_id: null
    }
  )
  assert.throws(
    () => entityHurtPayload({}, { id: 1 }),
    /hurt entity must expose a non-negative integer id/
  )
})
