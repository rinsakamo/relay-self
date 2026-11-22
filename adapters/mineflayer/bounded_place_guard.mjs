/** Q4 isolated DEV ONLY: native-side bounded WALK and self-terminating guard.
 *
 * Explicit process launch opt-in is required. This is not a World-motion PASS;
 * sampling latency and momentum can exceed the early-stop threshold.
 */
import { performance } from 'node:perf_hooks'

export const Q4_MAX_FORWARD_MS = 800
export const Q4_ACCEPTANCE_DISTANCE_M = 1.0
export const Q4_EARLY_STOP_DISTANCE_M = 0.7

function horizontalPosition (bot) {
  const p = bot.entity?.position
  if (!p || !Number.isFinite(p.x) || !Number.isFinite(p.z)) {
    throw new Error('bounded_place_native_position_unavailable')
  }
  return { x: p.x, z: p.z }
}

export class Q4BoundedPlaceMotionGuard {
  constructor (bot, { onTrip, now = () => performance.now(), interval = setInterval, cancel = clearInterval } = {}) {
    if (typeof onTrip !== 'function') throw new Error('Q4 onTrip required')
    this.bot = bot
    this.onTrip = onTrip
    this.now = now
    this.interval = interval
    this.cancel = cancel
    this.active = null
    this.timer = null
    this.tripped = false
  }

  start (actionId) {
    if (this.tripped || this.active !== null) {
      throw new Error('bounded_place_native_session_busy_or_tripped')
    }
    const origin = horizontalPosition(this.bot)
    const startedMs = this.now()
    if (!Number.isFinite(startedMs)) throw new Error('bounded_place_bad_clock')
    this.bot.clearControlStates()
    this.bot.setControlState('forward', true)
    this.active = { actionId, origin, startedMs }
    this.timer = this.interval(() => this.check(), 20)
  }

  check () {
    if (this.active === null) return
    try {
      const position = horizontalPosition(this.bot)
      const { origin, startedMs } = this.active
      const dt = this.now() - startedMs
      const distance = Math.hypot(position.x - origin.x, position.z - origin.z)
      if (!Number.isFinite(dt) || dt < 0 || !Number.isFinite(distance)) {
        this.trip('bounded_place_nonfinite_observation')
      } else if (dt >= Q4_MAX_FORWARD_MS || distance >= Q4_EARLY_STOP_DISTANCE_M) {
        this.trip('bounded_place_native_watchdog_' + (dt >= Q4_MAX_FORWARD_MS ? 'time' : 'distance'))
      }
    } catch (error) {
      this.trip(String(error.message || error))
    }
  }

  trip (reason) {
    if (this.tripped) return
    this.tripped = true
    this.clearTimer()
    this.active = null
    try {
      this.bot.clearControlStates()
    } finally {
      this.onTrip(reason)
    }
  }

  stop () {
    this.clearTimer()
    this.active = null
    this.bot.clearControlStates()
  }

  clearTimer () {
    if (this.timer !== null) {
      this.cancel(this.timer)
      this.timer = null
    }
  }
}
