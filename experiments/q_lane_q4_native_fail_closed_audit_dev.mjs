/** Q4 independent read-only hostile guard auditor.
 * Usage: node experiments/q_lane_q4_native_fail_closed_audit_dev.mjs \
 *        /path/to/I/adapters/mineflayer/bounded_place_guard.mjs <expected-git-blob-sha>
 * Does not send Native commands or grant World access. Requires Node >=18 and git.
 */
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { pathToFileURL } from 'node:url'

const [target, expectedBlob] = process.argv.slice(2)
if (!target || !/^[0-9a-f]{40}$/.test(expectedBlob || '')) {
  throw new Error('provide an explicit target module and exact expected Git blob SHA')
}
const actualBlob = execFileSync('git', ['hash-object', target], { encoding: 'utf8' }).trim()
assert.equal(actualBlob, expectedBlob, 'target source bytes differ from pinned I HEAD')
const { Q4BoundedPlaceMotionGuard } = await import(pathToFileURL(target).href)

function fixture (fault) {
  let forward = false
  let tick = null
  let terminated = false
  const bot = {
    entity: { position: { x: 0, y: 64, z: 0 } },
    clearControlStates () {
      if (fault.clear) throw new Error('fault-injected native clear failure')
      forward = false
    },
    setControlState (control, enabled) {
      assert.equal(control, 'forward')
      forward = enabled
      if (fault.setAfterApply) throw new Error('fault-injected native start-after-apply failure')
    }
  }
  const guard = new Q4BoundedPlaceMotionGuard(bot, {
    now: () => 0,
    onTrip: () => { terminated = true },
    interval: (fn) => {
      if (fault.timer) throw new Error('fault-injected timer failure')
      tick = fn
      return 1
    },
    cancel: () => { tick = null }
  })
  return { bot, guard, get forward () { return forward }, get tick () { return tick }, get terminated () { return terminated } }
}

const checks = [
  ['start applies forward then throws', () => {
    const f = fixture({ setAfterApply: true })
    assert.throws(() => f.guard.start('place-start'), /fault-injected/)
    assert.ok(!f.forward || f.terminated, 'UNSAFE: forward remains active after START error, no native forced shutdown')
  }],
  ['stop clear-controls throws', () => {
    const f = fixture({})
    f.guard.start('place-start')
    f.bot.clearControlStates = () => { throw new Error('fault-injected native STOP failure') }
    assert.throws(() => f.guard.stop(), /fault-injected/)
    assert.ok(!f.forward || f.terminated, 'UNSAFE: STOP error cancels watchdog and leaves forward active')
  }],
  ['timer registration fails after start', () => {
    const f = fixture({ timer: true })
    assert.throws(() => f.guard.start('place-start'), /fault-injected/)
    assert.ok(!f.forward || f.terminated, 'UNSAFE: forward remains active without watchdog timer')
  }]
]
let failed = 0
for (const [name, fn] of checks) {
  try { fn(); process.stdout.write('PASS ' + name + '\n') }
  catch (error) { failed += 1; process.stderr.write('FAIL ' + name + ': ' + String(error.message || error) + '\n') }
}
process.stdout.write(`Q4 independent guard assertions: ${checks.length - failed} PASS / ${failed} FAIL; target blob ${actualBlob}\n`)
if (failed) process.exitCode = 1
