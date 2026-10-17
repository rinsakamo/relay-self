// S V6 opt-in raw clientbound update_time samples (Minecraft 1.21.8).
// This is NOT a server command-effect tick or a continuous per-tick clock.
const SOURCE = 'minecraft_1_21_8_clientbound_update_time'
const PRECISION = 'SERVER_UPDATE_TIME_PACKET_SAMPLE_ONLY'

function fromI64 (input, name) {
  if (!Array.isArray(input) || input.length !== 2 ||
      !Number.isInteger(input[0]) || !Number.isInteger(input[1]) ||
      input[0] < -2147483648 || input[0] > 2147483647 ||
      input[1] < -2147483648 || input[1] > 4294967295) {
    throw new Error(name + ': need original signed i64 [upper,lower]')
  }
  return BigInt.asIntN(64, (BigInt(input[0]) << 32n) | BigInt(input[1] >>> 0))
}

export function v6PacketSample (packet, monotonicNs) {
  if (!packet || typeof packet !== 'object' || Array.isArray(packet) ||
      typeof packet.tickDayTime !== 'boolean' ||
      typeof monotonicNs !== 'bigint' || monotonicNs < 0n) {
    throw new Error('invalid packet or host monotonic stamp')
  }
  const age = fromI64(packet.age, 'age')
  if (age < 0n) throw new Error('negative server age')
  return Object.freeze({
    source: SOURCE,
    observation_precision: PRECISION,
    world_age_ticks: age.toString(),
    world_day_time_raw_ticks: fromI64(packet.time, 'time').toString(),
    tick_day_time: packet.tickDayTime,
    host_monotonic_ns: monotonicNs.toString(),
    command_effect_tick_attested: false
  })
}

export function attachV6NativeClockPackets (bot, onSample, onInvalid) {
  if (!bot?._client || typeof bot._client.on !== 'function' ||
      typeof onSample !== 'function' || typeof onInvalid !== 'function') {
    throw new TypeError('genuine client and callbacks required')
  }
  let previousAge = null
  let previousHost = null
  bot._client.on('update_time', (packet) => {
    try {
      const sample = v6PacketSample(packet, process.hrtime.bigint())
      const age = BigInt(sample.world_age_ticks)
      const host = BigInt(sample.host_monotonic_ns)
      if ((previousAge !== null && age < previousAge) ||
          (previousHost !== null && host < previousHost)) {
        throw new Error('raw server clock regressed')
      }
      previousAge = age
      previousHost = host
      onSample(sample)
    } catch (error) {
      onInvalid(error)
    }
  })
}
