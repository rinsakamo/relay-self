import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import test from 'node:test'

import {
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
