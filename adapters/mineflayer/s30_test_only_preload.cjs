/* S30 TEST-ONLY Mineflayer module seam; invoked via NODE_OPTIONS --require.
 * Executes the UNMODIFIED bridge.mjs as a genuine Node child process.
 * Not a Minecraft server, socket or production library implementation.
 */
'use strict'

const { EventEmitter } = require('node:events')
const Module = require('node:module')
const originalLoad = Module._load

function createBot () {
  const bot = new EventEmitter()
  bot.health = 20
  bot.food = 20
  bot.foodSaturation = 5
  bot.oxygenLevel = 20
  bot.time = { timeOfDay: 6000, day: 1, isDay: true }
  bot.entity = { id: 1, name: 'relay-self', type: 'player',
    position: { x: 0, y: 64, z: 0 } }
  const x = Number(process.env.S30_THREAT_DISTANCE_M || '0.2')
  if (!(Number.isFinite(x) && x > 0 && x <= 16)) {
    throw new Error('S30 test fixture threat distance invalid')
  }
  bot.entities = {
    1: bot.entity,
    42: { id: 42, name: 'zombie', type: 'mob',
      position: { x, y: 64, z: 0 } }
  }
  bot.inventory = new EventEmitter()
  bot.inventory.items = () => []
  bot.heldItem = null
  bot.setControlState = () => {}
  bot.clearControlStates = () => {}
  bot.quit = () => { setImmediate(() => bot.emit('end', 'S30 fixture shutdown')) }
  if (process.env.S30_SUPPRESS_SPAWN !== '1') {
    setImmediate(() => {
      bot.emit('inject_allowed')
      bot.emit('spawn')
      bot.emit('health')
    })
  }
  return bot
}

Module._load = function s30TestOnlyLoader (request, parent, isMain) {
  if (request === 'mineflayer') {
    return { createBot }
  }
  if (request === 'mineflayer/package.json') {
    return { version: '4.39.0' }
  }
  return originalLoad.call(this, request, parent, isMain)
}
