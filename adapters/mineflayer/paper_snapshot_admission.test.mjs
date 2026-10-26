import test from 'node:test'
import assert from 'node:assert/strict'
import { SnapshotAdmission, decodeSnapshot } from './paper_snapshot_admission.mjs'
const uuid = '11111111-1111-1111-1111-111111111111'
export const snapshot = (i = 1) => ({ version: 1, boot: uuid, index: i, tick: 100 + i,
  world_tick: 200 + i, paper_ns: 50000000 * i, world: uuid, player: uuid,
  challenge: 'NONE', x: 0, y: 1, z: 0, health: 20, food: 20, input: 0,
  threats_complete: true, threats: [], basal_ticks: i, basal_exhaustion: i * .001,
  motion_blocks: 0, motion_exhaustion: 0 })
function step (g, s, overrides = {}) {
  s.challenge = g.issue(BigInt(s.index) * 50000000n).toString()
  return g.evaluate(s, { received: BigInt(s.index) * 50000000n + 1000000n,
    start: BigInt(s.index) * 50000000n + 1001000n,
    completed: BigInt(s.index) * 50000000n + 1002000n, ...overrides })
}
test('Paper body, never stale Mineflayer cache, chooses L0', () => {
  const s = snapshot(); s.health = 3
  const r = step(new SnapshotAdmission(), s, { cache: { health: 20, food: 20 } })
  assert.equal(r.status, 'ADMITTED'); assert.equal(r.assessment, 'LOW_HEALTH')
  assert.equal(r.cache_mismatch, true); assert.equal(r.paper_to_node_exact_ns, null)
})
for (const [name, mutate, status] of [
  ['replay', s => { s.index = 1; s.tick = 101; s.world_tick = 201 }, 'STALE'],
  ['missing', s => { s.index = 3; s.tick++; s.world_tick++ }, 'MISSING'],
  ['reverse', s => { s.tick = 99 }, 'STALE'],
  ['foreign world', s => { s.world = '22222222-2222-2222-2222-222222222222' }, 'UNDETERMINED'],
  ['foreign player', s => { s.player = '22222222-2222-2222-2222-222222222222' }, 'UNDETERMINED'],
  ['restarted Paper', s => { s.boot = '22222222-2222-2222-2222-222222222222' }, 'UNDETERMINED'],
  ['truncated nearby', s => { s.threats_complete = false }, 'MISSING']
]) test(name + ' refuses and latches', () => {
  const g = new SnapshotAdmission(); step(g, snapshot())
  const s = snapshot(2); mutate(s)
  assert.equal(step(g, s).status, status)
  assert.equal(step(g, snapshot(3)).status, 'UNDETERMINED')
})
test('Node queue / slow evaluation fails deadline', () => {
  const g = new SnapshotAdmission()
  assert.equal(step(g, snapshot(), { start: 80000000n, completed: 81000000n }).status, 'LATE')
})
test('transport backlog before receive is included in causal upper age', () => {
  const g = new SnapshotAdmission()
  assert.equal(step(g, snapshot(), { received: 300000000n, start: 300001000n,
    completed: 300002000n }).status, 'STALE')
})
test('latest confirmed tick supersedes old input', () => {
  assert.equal(step(new SnapshotAdmission(), snapshot(), { latestTick: 102 }).status, 'STALE')
})
test('foreign session challenge cannot attest freshness', () => {
  const g = new SnapshotAdmission(); g.issue(0n)
  assert.equal(g.evaluate(snapshot(), { received: 1n, start: 2n, completed: 3n }).status, 'UNDETERMINED')
})
test('missing and nonfinite Paper values are rejected', () => {
  for (const k of ['health', 'input', 'threats', 'world_tick']) {
    const s = snapshot(); delete s[k]
    assert.throws(() => decodeSnapshot(Buffer.from(JSON.stringify(s))))
  }
  const s = snapshot(); s.x = null
  assert.throws(() => decodeSnapshot(Buffer.from(JSON.stringify(s))))
})
test('20TPS consecutive frames each admitted, no cadence freshness assumption', () => {
  const g = new SnapshotAdmission()
  for (let i = 1; i <= 50; i++) assert.equal(step(g, snapshot(i)).status, 'ADMITTED')
})
test('catch-up tick reuses earlier causal challenge without losing age bound', () => {
  const g = new SnapshotAdmission()
  const s1 = snapshot(); s1.challenge = g.issue(0n).toString()
  const c = s1.challenge
  assert.equal(g.evaluate(s1, { received: 50000000n, start: 50000001n, completed: 50000002n }).status, 'ADMITTED')
  g.issue(50000003n)
  const s2 = snapshot(2); s2.challenge = c
  const r = g.evaluate(s2, { received: 51000000n, start: 51000001n, completed: 51000002n })
  assert.equal(r.status, 'ADMITTED'); assert.equal(r.age_upper_ns, '51000002')
})
test('single channel dispatch gate refuses aged snapshot even if Python consumer was delayed', async () => {
  const { attachPaperSnapshotChannel } = await import('./paper_snapshot_admission.mjs')
  const handlers = {}; const writes = []; const emitted = []
  let now = 0n
  const bot = { once: (n, cb) => { handlers[n] = cb },
    _client: { on: (n, cb) => { handlers[n] = cb }, registerChannel: () => {},
      write: (name, data) => writes.push(data) } }
  const g = attachPaperSnapshotChannel(bot, (t, d) => emitted.push(d.data), e => { throw e }, () => now)
  assert.equal(g.canDispatch(), false)
  handlers.login()
  const s = snapshot(); s.challenge = writes[0].data.toString()
  now = 50000000n
  handlers['relayself:world_tick_dev'](Buffer.from(JSON.stringify(s)))
  assert.equal(emitted[0].status, 'ADMITTED'); assert.equal(g.canDispatch(), true)
  now = 151000000n
  assert.equal(g.canDispatch(), false)
})
