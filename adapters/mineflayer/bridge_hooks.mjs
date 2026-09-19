export function attachInventoryUpdateListenerAfterInjection (
  bot,
  listener
) {
  if (!bot || typeof bot.once !== 'function') {
    throw new TypeError('bot must expose once(event, listener)')
  }
  if (typeof listener !== 'function') {
    throw new TypeError('inventory update listener must be a function')
  }

  bot.once('inject_allowed', () => {
    if (!bot.inventory || typeof bot.inventory.on !== 'function') {
      throw new Error(
        'Mineflayer inventory unavailable after inject_allowed'
      )
    }
    bot.inventory.on('updateSlot', listener)
  })
}

export function attachBodySynchronizedSpawnListeners (
  bot,
  spawnListener,
  healthListener
) {
  if (!bot || typeof bot.on !== 'function') {
    throw new TypeError('bot must expose on(event, listener)')
  }
  if (typeof spawnListener !== 'function') {
    throw new TypeError('spawn listener must be a function')
  }
  if (typeof healthListener !== 'function') {
    throw new TypeError('health listener must be a function')
  }

  let spawnPendingBody = false
  let healthSynchronized = false
  let oxygenSynchronized = false

  function completeSpawnIfReady () {
    if (
      !spawnPendingBody ||
      !healthSynchronized ||
      !oxygenSynchronized
    ) return false

    spawnPendingBody = false
    healthSynchronized = false
    oxygenSynchronized = false
    spawnListener()
    return true
  }

  bot.on('spawn', () => {
    spawnPendingBody = true
    healthSynchronized = false
    oxygenSynchronized = Number.isFinite(bot.oxygenLevel)
  })

  bot.on('health', () => {
    if (spawnPendingBody) {
      healthSynchronized = true
      completeSpawnIfReady()
      return
    }
    healthListener()
  })

  bot.on('breath', () => {
    if (!spawnPendingBody) return
    oxygenSynchronized = true
    completeSpawnIfReady()
  })
}
