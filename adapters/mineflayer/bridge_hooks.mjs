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
