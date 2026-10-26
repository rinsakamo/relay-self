import assert from 'node:assert/strict'
import test from 'node:test'
import { PaperTickDeadlineGuard } from './paper_tick_deadline.mjs'

const sample = (index, received, changes = {}) => ({
  source: 'PAPER_SCHEDULER_CALLBACK_ONLY', index,
  server_tick: String(100 + index),
  bridge_recv_monotonic_ns: String(received),
  world: 'world-uuid', player: 'bot-uuid', ...changes
})

test('first tick has no cadence baseline and never attests fresh L0', () => {
  const g = new PaperTickDeadlineGuard()
  const a = g.observe(sample(1, 10_000), { completedMonoNs: 10_150n })
  assert.equal(a.status, 'INITIAL_CADENCE_UNKNOWN')
  assert.equal(a.observed_arrival_gap_ns, null)
  assert.equal(a.tps_admission_granted, false)
  assert.equal(a.l0_world_freshness_attested, false)
})

test('observed 20 and 200 TPS arrival cadences use the same relative budget', () => {
  for (const gap of [50_000_000n, 5_000_000n]) {
    const guard = new PaperTickDeadlineGuard()
    guard.observe(sample(1, 100_000n), { completedMonoNs: 200_000n })
    const out = guard.observe(sample(2, 100_000n + gap),
      { completedMonoNs: 100_000n + gap + gap / 4n })
    assert.equal(out.status, 'HOST_LOCAL_BUDGET_MET_ONLY')
    assert.equal(out.observed_arrival_gap_ns, gap.toString())
    assert.equal(out.tps_admission_granted, false)
    assert.equal(guard.failed, false)
  }
})

test('over-budget callback poisons the sequence permanently', () => {
  const guard = new PaperTickDeadlineGuard()
  guard.observe(sample(1, 10_000), { completedMonoNs: 11_000n })
  assert.throws(() => guard.observe(sample(2, 20_000), { completedMonoNs: 25_000n }),
    /over measured tick budget/)
  assert.equal(guard.failed, true)
  assert.throws(() => guard.observe(sample(3, 30_000), { completedMonoNs: 30_010n }),
    /latched unsafe/)
})

test('missing/reordered tick, replay, session scope mismatch and impossible clock fail', () => {
  for (const { second, completed } of [
    { second: sample(3, 20_000), completed: 21_000n },
    { second: sample(1, 20_000), completed: 21_000n },
    { second: sample(2, 20_000, { server_tick: '900' }), completed: 21_000n },
    { second: sample(2, 20_000, { player: 'another' }), completed: 21_000n },
    { second: sample(2, 10_000), completed: 11_000n },
    { second: sample(2, 20_000), completed: 19_000n }
  ]) {
    const guard = new PaperTickDeadlineGuard()
    guard.observe(sample(1, 10_000), { completedMonoNs: 11_000n })
    assert.throws(() => guard.observe(second, { completedMonoNs: completed }))
    assert.equal(guard.failed, true)
  }
})

test('invalid fractions and impossible samples fail closed', () => {
  for (const p of [{ budgetNumerator: 1, budgetDenominator: 1 },
    { budgetNumerator: 0 }, { budgetDenominator: 1001 },
    { budgetNumerator: 1.5 }, { budgetNumerator: 2, budgetDenominator: 2 }]) {
    assert.throws(() => new PaperTickDeadlineGuard(p))
  }
  const guard = new PaperTickDeadlineGuard()
  assert.throws(() => guard.observe(sample(1, 1, { bridge_recv_monotonic_ns: '-1' }),
    { completedMonoNs: 2n }))
  assert.equal(guard.failed, true)
})
