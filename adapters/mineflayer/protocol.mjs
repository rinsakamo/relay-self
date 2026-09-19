const CONTROLS = new Set([
  'forward',
  'back',
  'left',
  'right',
  'jump',
  'sprint',
  'sneak'
])

const EFFECTS = new Set(['set_control', 'clear_controls'])

function requireObject (name, value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(name + ' must be an object')
  }
  return value
}

function requireExactKeys (name, value, keys) {
  const actual = Object.keys(value).sort()
  const expected = [...keys].sort()
  if (actual.length !== expected.length || actual.some((key, i) => key !== expected[i])) {
    throw new Error(
      name + ' fields are invalid; expected=' + expected.join(',') +
      ' actual=' + actual.join(',')
    )
  }
}

function requireText (name, value) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(name + ' must be a non-empty string')
  }
  return value
}

function requireFiniteNumber (name, value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new Error(name + ' must be a finite number')
  }
  return value
}

function parsePort (value) {
  const port = Number(value)
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error('port must be an integer in 1..65535')
  }
  return port
}

export function parseArgs (argv) {
  const config = {
    host: '127.0.0.1',
    port: 25565,
    username: 'RelaySelf',
    version: null
  }

  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index]
    const value = argv[index + 1]
    if (value === undefined) {
      throw new Error('missing value for ' + key)
    }

    if (key === '--host') {
      config.host = requireText('host', value)
    } else if (key === '--port') {
      config.port = parsePort(value)
    } else if (key === '--username') {
      config.username = requireText('username', value)
    } else if (key === '--version') {
      config.version = requireText('version', value)
    } else {
      throw new Error('unknown argument: ' + key)
    }
  }

  return Object.freeze(config)
}

export function parseCommand (raw) {
  const value = requireObject('command', raw)
  requireText('command type', value.type)

  if (value.type === 'effect') {
    requireText('action_id', value.action_id)
    requireText('effect', value.effect)
    if (!EFFECTS.has(value.effect)) {
      throw new Error('unsupported effect: ' + value.effect)
    }

    if (value.effect === 'set_control') {
      requireExactKeys(
        'set_control command',
        value,
        ['type', 'action_id', 'effect', 'control', 'state']
      )
      if (!CONTROLS.has(value.control)) {
        throw new Error('unsupported control: ' + String(value.control))
      }
      if (typeof value.state !== 'boolean') {
        throw new Error('set_control state must be boolean')
      }
      return Object.freeze({
        type: 'effect',
        action_id: value.action_id,
        effect: value.effect,
        control: value.control,
        state: value.state
      })
    }

    requireExactKeys(
      'clear_controls command',
      value,
      ['type', 'action_id', 'effect']
    )
    return Object.freeze({
      type: 'effect',
      action_id: value.action_id,
      effect: value.effect
    })
  }

  if (value.type === 'shutdown') {
    requireExactKeys('shutdown command', value, ['type'])
    return Object.freeze({ type: 'shutdown' })
  }

  throw new Error('unsupported command type: ' + value.type)
}

export function snapshotFromBot (bot) {
  if (!bot || !bot.entity || !bot.entity.position) {
    throw new Error('bot position is unavailable before spawn')
  }

  return {
    health: requireFiniteNumber('bot.health', bot.health),
    food: requireFiniteNumber('bot.food', bot.food),
    oxygen_level: requireFiniteNumber('bot.oxygenLevel', bot.oxygenLevel),
    position: {
      x: requireFiniteNumber('position.x', bot.entity.position.x),
      y: requireFiniteNumber('position.y', bot.entity.position.y),
      z: requireFiniteNumber('position.z', bot.entity.position.z)
    }
  }
}

export function makeEnvelope (sessionId, seq, type, payload = {}) {
  requireText('session_id', sessionId)
  if (!Number.isInteger(seq) || seq < 0) {
    throw new Error('seq must be a non-negative integer')
  }
  requireText('message type', type)
  requireObject('payload', payload)
  return {
    type,
    session_id: sessionId,
    seq,
    ...payload
  }
}
