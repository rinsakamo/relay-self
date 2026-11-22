/** Q4 read-only race/error follow-up for U9 Native bounded guard.
 * node q_lane_q4_native_race_audit_dev.mjs <native-guard-file> <expected-Git-blob>
 * Never launches Minecraft or sends effects. Explicit source identity required.
 */
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { pathToFileURL } from 'node:url'

const [target, expected] = process.argv.slice(2)
if (!target || !/^[0-9a-f]{40}$/.test(expected || '')) {
  throw new Error('exact guard source file and git blob SHA required')
}
const actual = execFileSync('git', ['hash-object', target], { encoding: 'utf8' }).trim()
assert.equal(actual, expected, 'wrong native guard source bytes')
const { Q4BoundedPlaceMotionGuard } = await import(pathToFileURL(target).href)

const checks = [
  ['synchronous timeout during interval() registration', () => {
    let clock = 0
    let forward = false
    let trips = 0
    const cancelled = []
    const bot = {
      entity: { position: { x: 0, z: 0 } },
      clearControlStates () { forward = false },
      setControlState () { forward = true }
    }
    const guard = new Q4BoundedPlaceMotionGuard(bot, {
      now: () => clock,
      interval (callback) { clock = 900; callback(); return 99 },
      cancel (id) { cancelled.push(id) },
      onTrip () { trips += 1 }
    })
    assert.throws(() => guard.start('sync-timeout'), /tripped/)
    assert.equal(forward, false)
    assert.equal(trips, 1)
    assert.equal(guard.tripped, true)
    assert.equal(guard.active, null)
    assert.deepEqual(cancelled, [99])
    assert.throws(() => guard.start('replayed-start'), /tripped/)
  }],
  ['timer cancellation fails during otherwise successful STOP', () => {
    let forward = false
    let trips = 0
    const bot = {
      entity: { position: { x: 0, z: 0 } },
      clearControlStates () { forward = false },
      setControlState () { forward = true }
    }
    const guard = new Q4BoundedPlaceMotionGuard(bot, {
      now: () => 0,
      interval: () => 77,
      cancel () { throw new Error('cancel-failed') },
      onTrip () { trips += 1 }
    })
    guard.start('start')
    assert.throws(() => guard.stop(), /cancel-failed/)
    assert.equal(forward, false)
    assert.equal(trips, 1)
    assert.equal(guard.tripped, true)
    assert.throws(() => guard.start('replayed-start'), /tripped/)
  }],
  ['repeated motor clear failure preserves irreversible quit request', () => {
    let forward = false
    let fails = false
    let trips = 0
    const bot = {
      entity: { position: { x: 0, z: 0 } },
      clearControlStates () {
        if (fails) throw new Error('clear-failed')
        forward = false
      },
      setControlState () { forward = true }
    }
    const guard = new Q4BoundedPlaceMotionGuard(bot, {
      now: () => 0,
      interval: () => 1,
      cancel: () => {},
      onTrip () { trips += 1 }
    })
    guard.start('start')
    fails = true
    assert.throws(() => guard.stop(), /clear-failed/)
    assert.equal(forward, true) // clearance NOT proven: external quit/host kill required
    assert.equal(trips, 1)
    assert.equal(guard.tripped, true)
    assert.throws(() => guard.start('replayed-start'), /tripped/)
  }]
]
let failures = 0
for (const [name, fn] of checks) {
  try { fn(); process.stdout.write('PASS ' + name + '\n') }
  catch (error) { failures += 1; process.stderr.write('FAIL ' + name + ': ' + String(error.message || error) + '\n') }
}
process.stdout.write(`Q4 supplemental Native race/error: ${checks.length - failures} PASS / ${failures} FAIL; pinned blob ${actual}\n`)
if (failures) process.exitCode = 1
