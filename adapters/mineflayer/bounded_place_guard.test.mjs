import assert from 'node:assert/strict'
import test from 'node:test'

import {
  Q4BoundedPlaceMotionGuard,
  Q4_MAX_FORWARD_MS,
  Q4_ACCEPTANCE_DISTANCE_M,
  Q4_EARLY_STOP_DISTANCE_M
} from './bounded_place_guard.mjs'

function fixture () {
  let ms = 0
  let tick = null
  const actions = []
  const trips = []
  const bot = {
    entity: { position: { x: 0, y: 64, z: 0 } },
    clearControlStates: () => actions.push('clear'),
    setControlState: (kind, enabled) => actions.push(kind + ':' + enabled)
  }
  const guard = new Q4BoundedPlaceMotionGuard(bot, {
    onTrip: (reason) => trips.push(reason),
    now: () => ms,
    interval: (callback, delay) => {
      assert.equal(delay, 20)
      tick = callback
      return 'interval'
    },
    cancel: (handle) => {
      assert.equal(handle, 'interval')
      tick = null
    }
  })
  return {
    bot, guard, actions, trips,
    setTime: (t) => { ms = t },
    tick: () => { if (tick) tick() },
    timerActive: () => tick !== null
  }
}

test('Q4 exact caps, early-stop conservatively below 1m acceptance', () => {
  assert.equal(Q4_MAX_FORWARD_MS, 800)
  assert.equal(Q4_ACCEPTANCE_DISTANCE_M, 1)
  assert.equal(Q4_EARLY_STOP_DISTANCE_M, 0.7)
})

test('normal short WALK is stopped and can start a fresh second action', () => {
  const f = fixture()
  f.guard.start('place-1-start')
  assert.equal(f.timerActive(), true)
  assert.deepEqual(f.actions, ['clear', 'forward:true'])
  f.bot.entity.position.x = 0.4
  f.setTime(120)
  f.tick()
  assert.equal(f.guard.tripped, false)
  f.guard.stop()
  assert.equal(f.timerActive(), false)
  f.guard.start('place-2-start')
  assert.equal(f.timerActive(), true)
  f.guard.stop()
  assert.deepEqual(f.trips, [])
})

test('forward command is stopped at 800ms even when no position changed', () => {
  const f = fixture()
  f.guard.start('action-start')
  f.setTime(799)
  f.tick()
  assert.equal(f.trips.length, 0)
  f.setTime(800)
  f.tick()
  assert.equal(f.trips.length, 1)
  assert.match(f.trips[0], /watchdog_time/)
  assert.deepEqual(f.actions.slice(-1), ['clear'])
  assert.equal(f.timerActive(), false)
  assert.throws(() => f.guard.start('replay-start'), /tripped/)
})

test('horizontal distance >= 0.7m triggers early neutralization', () => {
  const f = fixture()
  f.guard.start('action-start')
  f.bot.entity.position.z = 0.71
  f.setTime(60)
  f.tick()
  assert.match(f.trips[0], /watchdog_distance/)
  assert.equal(f.guard.active, null)
  assert.throws(() => f.guard.start('second-after-watchdog'), /tripped/)
})

test('bad position or non-monotonic time trips instead of accepting motion', () => {
  const f = fixture()
  f.guard.start('action-start')
  f.bot.entity.position.x = Number.NaN
  f.tick()
  assert.equal(f.guard.tripped, true)
  assert.deepEqual(f.actions.slice(-1), ['clear'])
  const g = fixture()
  g.guard.start('action-start')
  g.setTime(-1)
  g.tick()
  assert.match(g.trips[0], /nonfinite/)
})

test('only one bounded start at a time; no timer remains after stop', () => {
  const f = fixture()
  f.guard.start('first')
  assert.throws(() => f.guard.start('second'), /busy/)
  f.guard.stop()
  f.setTime(900)
  f.tick()
  assert.equal(f.trips.length, 0)
  assert.equal(f.timerActive(), false)
})


test('Q4 hostile START partial-apply exception always trips and requests bot quit', () => {
  let forward = false
  let tick = null
  const quits = []
  const bot = {
    entity: { position: { x: 0, z: 0 } },
    clearControlStates () { forward = false },
    setControlState () {
      forward = true
      throw new Error('fault-injected native start-after-apply failure')
    }
  }
  const guard = new Q4BoundedPlaceMotionGuard(bot, {
    now: () => 0,
    interval: (cb) => { tick = cb; return 1 },
    cancel: () => { tick = null },
    onTrip: (reason) => quits.push(reason)
  })
  assert.throws(() => guard.start('place-start'), /fault-injected/)
  assert.ok(!forward || quits.length === 1, 'partial START cannot silently run')
  assert.equal(quits.length, 1)
  assert.match(quits[0], /start_failed/)
  assert.equal(guard.tripped, true)
  assert.equal(guard.active, null)
  assert.equal(tick, null)
  assert.throws(() => guard.start('later-start'), /tripped/)
})

test('Q4 hostile STOP clear failure forces bot quit before watchdog can disappear', () => {
  let forward = false
  let tick = null
  let clearFails = false
  const quits = []
  const bot = {
    entity: { position: { x: 0, z: 0 } },
    clearControlStates () {
      if (clearFails) throw new Error('fault-injected native STOP clear failure')
      forward = false
    },
    setControlState () { forward = true }
  }
  const guard = new Q4BoundedPlaceMotionGuard(bot, {
    now: () => 0,
    interval: (cb) => { tick = cb; return 1 },
    cancel: () => { tick = null },
    onTrip: (reason) => quits.push(reason)
  })
  guard.start('place-start')
  assert.equal(forward, true)
  clearFails = true
  assert.throws(() => guard.stop(), /fault-injected/)
  assert.ok(!forward || quits.length === 1, 'failed STOP cannot silently run')
  assert.deepEqual(quits, ['bounded_place_native_stop_failed'])
  assert.equal(guard.tripped, true)
  assert.equal(tick, null)
  assert.throws(() => guard.start('replay-start'), /tripped/)
})

test('Q4 hostile timer registration exception never leaves motor unwatched', () => {
  let forward = false
  let clears = 0
  const quits = []
  const bot = {
    entity: { position: { x: 0, z: 0 } },
    clearControlStates () { forward = false; clears++ },
    setControlState () { forward = true }
  }
  const guard = new Q4BoundedPlaceMotionGuard(bot, {
    now: () => 0,
    interval: () => { throw new Error('fault-injected timer failure') },
    onTrip: (reason) => quits.push(reason)
  })
  assert.throws(() => guard.start('place-start'), /fault-injected/)
  assert.equal(forward, false)
  assert.ok(clears >= 1)
  assert.deepEqual(quits, ['bounded_place_native_start_failed'])
  assert.equal(guard.tripped, true)
  assert.throws(() => guard.start('later-start'), /tripped/)
})

test('Q4 hostile watchdog cancellation and repeated clear failure cannot skip quit', () => {
  let forward = false
  let clearFails = false
  const quits = []
  const bot = {
    entity: { position: { x: 0, z: 0 } },
    clearControlStates () {
      if (clearFails) throw new Error('fault-injected clear failure')
      forward = false
    },
    setControlState () { forward = true }
  }
  const guard = new Q4BoundedPlaceMotionGuard(bot, {
    now: () => 0,
    interval: () => 7,
    cancel: () => { throw new Error('fault-injected timer cancel failure') },
    onTrip: (reason) => quits.push(reason)
  })
  guard.start('place-start')
  clearFails = true
  assert.throws(() => guard.stop(), /fault-injected/)
  assert.equal(guard.tripped, true)
  assert.deepEqual(quits, ['bounded_place_native_stop_failed'])
  assert.throws(() => guard.start('forged-second'), /tripped/)
  // Already-tripped shutdown cannot silently revive motion or throw again.
  guard.stop()
  assert.equal(forward, true) // motor was NOT proven off; bot quit is mandatory
})
