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

export function attachHealthSynchronizedSpawnListeners (
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

  let spawnPendingHealth = false

  bot.on('spawn', () => {
    spawnPendingHealth = true
  })

  bot.on('health', () => {
    if (spawnPendingHealth) {
      spawnPendingHealth = false
      spawnListener()
      return
    }
    healthListener()
  })
}


export function resolveAttackEntity (bot, entityId) {
  if (!bot || !bot.entity || !Number.isInteger(bot.entity.id)) {
    throw new TypeError('bot must expose an integer entity id')
  }
  if (!Number.isInteger(entityId) || entityId < 0) {
    throw new TypeError('entityId must be a non-negative integer')
  }
  if (entityId === bot.entity.id) {
    throw new Error('self_target')
  }
  const entity = bot.entities && bot.entities[entityId]
  if (!entity) {
    throw new Error('entity_not_found')
  }
  return entity
}
