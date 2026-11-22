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
    // Arm the only Native watchdog BEFORE touching motor control. Even if
    // setControlState applies forward then throws, the emergency trip keeps
    // this session permanently non-restartable and asks the bot to quit.
    this.active = { actionId, origin, startedMs }
    try {
      const timer = this.interval(() => this.check(), 20)
      if (timer === null || timer === undefined) {
        throw new Error('bounded_place_native_timer_not_armed')
      }
      this.timer = timer
      if (this.tripped) throw new Error('bounded_place_native_start_tripped')
      this.bot.clearControlStates()
      if (this.tripped) throw new Error('bounded_place_native_start_tripped')
      this.bot.setControlState('forward', true)
      if (this.tripped) throw new Error('bounded_place_native_start_tripped')
      this.check() // recheck source/clock after START, not only at next tick
    } catch (error) {
      this.trip('bounded_place_native_start_failed')
      throw error
    }
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
    this.tripped = true // irreversible, before any fallible Native API call
    try {
      try {
        this.clearTimer()
      } finally {
        // Failed timer cancellation must not suppress the STOP attempt.
        this.active = null
        this.bot.clearControlStates()
      }
    } finally {
      // Including when clearControlStates or clearInterval itself throws.
      // The bridge callback disconnects this native bot; a callback failure
      // cannot turn this tripped session back into an issuing session.
      this.onTrip(reason)
    }
  }

  stop () {
    // Already tripped means disconnect underway; do not retry a broken
    // Native STOP or reopen this session from an 'end' handler.
    if (this.tripped) return
    try {
      // Native clear must SUCCEED before the last watchdog is disarmed.
      this.bot.clearControlStates()
      this.clearTimer()
      this.active = null
    } catch (error) {
      this.trip('bounded_place_native_stop_failed')
      throw error
    }
  }

  clearTimer () {
    const timer = this.timer
    this.timer = null
    if (timer !== null) this.cancel(timer)
  }
}
