// S50 #627 — passive native packet and client pose witness for FLAT DEV only.
// No controller, artificial ACK, packet construction, retries or Paper authority.
// Inbound BEFORE/AFTER refer to this listener's order only, not a shared tick.
const INBOUND = new Set(['position', 'player_rotation'])
const OUTBOUND = new Set(['look', 'position_look', 'teleport_confirm'])
const FIELDS = ['x', 'y', 'z', 'yaw', 'pitch', 'teleportId', 'teleport_id', 'flags', 'onGround']

export function packetFields (packet) {
  if (packet === null || typeof packet !== 'object' || Array.isArray(packet)) {
    return { shape_valid: false }
  }
  const fields = { shape_valid: true }
  for (const key of FIELDS) {
    if (!Object.hasOwn(packet, key)) continue
    const value = packet[key]
    if (key === 'flags' && value !== null && typeof value === 'object' && !Array.isArray(value)) {
      const flags = {}
      for (const name of ['x', 'y', 'z', 'yaw', 'pitch']) {
        if (Object.hasOwn(value, name)) {
          flags[name] = typeof value[name] === 'boolean' ? value[name] : null
          if (flags[name] === null) fields.shape_valid = false
        }
      }
      fields.flags = flags
    } else if (key === 'flags' && Number.isSafeInteger(value) && value >= 0) {
      fields.flags = value
    } else if (typeof value === 'number' && Number.isFinite(value)) {
      fields[key] = value
    } else if (typeof value === 'boolean') {
      fields[key] = value
    } else {
      fields.shape_valid = false
      fields[key] = null
    }
  }
  return fields
}

export function clientPose (bot) {
  const yaw = bot?.entity?.yaw
  const pitch = bot?.entity?.pitch
  return {
    client_yaw_radians: typeof yaw === 'number' && Number.isFinite(yaw) ? yaw : null,
    client_pitch_radians: typeof pitch === 'number' && Number.isFinite(pitch) ? pitch : null
  }
}

export function attachPassiveS50PacketTrace (bot, emit) {
  if (!bot?._client || typeof bot._client.write !== 'function' ||
      typeof bot._client.prependListener !== 'function' ||
      typeof bot._client.on !== 'function' || typeof emit !== 'function') {
    throw new Error('S50 passive trace needs a single initialized Mineflayer client')
  }
  const client = bot._client
  // Preserves the exact original method, receiver, arguments, return and thrown error.
  // This is a DEV-only *observability* wrapper, not another packet writer.
  const originalWrite = client.write
  client.write = function (name, ...args) {
    if (OUTBOUND.has(name)) {
      emit({
        kind: 'PACKET_OUT', packet_name: name,
        packet_fields: packetFields(args[0]), ...clientPose(bot)
      })
    }
    return Reflect.apply(originalWrite, this, [name, ...args])
  }
  for (const name of INBOUND) {
    client.prependListener(name, (packet) => {
      emit({
        kind: 'PACKET_IN_BEFORE', packet_name: name,
        packet_fields: packetFields(packet), ...clientPose(bot)
      })
    })
    client.on(name, (packet) => {
      emit({
        kind: 'PACKET_IN_AFTER', packet_name: name,
        packet_fields: packetFields(packet), ...clientPose(bot)
      })
    })
  }
  return Object.freeze({
    inbound_names: [...INBOUND],
    outbound_names: [...OUTBOUND],
    passive_only: true,
    effective_paper_tick_attested: false
  })
}
