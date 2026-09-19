import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import test from 'node:test'

import {
  attachBodySynchronizedSpawnListeners,
  attachInventoryUpdateListenerAfterInjection
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

test('spawn observation waits for Mineflayer health and oxygen initialization', () => {
  const bot = new EventEmitter()
  const observed = []

  attachBodySynchronizedSpawnListeners(
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
  assert.deepEqual(observed, [])

  bot.oxygenLevel = 20
  bot.emit('breath')

  assert.deepEqual(observed, [
    {
      kind: 'spawn',
      health: 20,
      food: 20,
      oxygenLevel: 20
    }
  ])

  bot.health = 18
  bot.emit('health')

  assert.deepEqual(observed, [
    {
      kind: 'spawn',
      health: 20,
      food: 20,
      oxygenLevel: 20
    },
    {
      kind: 'health',
      health: 18,
      food: 20,
      oxygenLevel: 20
    }
  ])
})

test('spawn readiness tolerates oxygen arriving before health', () => {
  const bot = new EventEmitter()
  const observed = []

  attachBodySynchronizedSpawnListeners(
    bot,
    () => observed.push('spawn'),
    () => observed.push('health')
  )

  bot.emit('spawn')

  bot.oxygenLevel = 20
  bot.emit('breath')
  assert.deepEqual(observed, [])

  bot.health = 20
  bot.food = 20
  bot.emit('health')
  assert.deepEqual(observed, ['spawn'])
})

test('health before spawn remains an ordinary health event', () => {
  const bot = new EventEmitter()
  const observed = []

  attachBodySynchronizedSpawnListeners(
    bot,
    () => observed.push('spawn'),
    () => observed.push('health')
  )

  bot.emit('health')
  assert.deepEqual(observed, ['health'])
})

test('body-synchronized spawn hook validates listeners', () => {
  assert.throws(
    () => attachBodySynchronizedSpawnListeners({}, () => {}, () => {}),
    /bot must expose on/
  )

  const bot = new EventEmitter()
  assert.throws(
    () => attachBodySynchronizedSpawnListeners(bot, null, () => {}),
    /spawn listener must be a function/
  )
  assert.throws(
    () => attachBodySynchronizedSpawnListeners(bot, () => {}, null),
    /health listener must be a function/
  )
})
