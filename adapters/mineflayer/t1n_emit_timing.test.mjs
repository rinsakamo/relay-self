import test from 'node:test'
import assert from 'node:assert/strict'
import { emitWithT1nTiming, openT1nSidecar } from './t1n_emit_timing_dev.mjs'

function scenario ({ diagnosticFails = false, traceWaitMs = 0n,
                     stdoutWaitMs = 0n } = {}) {
  const trace = []; const stdout = []; const sidecar = []
  let seq = 8; let now = 1000000000n; let inc = 0
  const timestamp = () => { now += 1000n; return now }
  const makeEnvelope = (session_id, n, type, body) =>
    ({ session_id, seq: n, type, ...body })
  const msg = emitWithT1nTiming({
    sessionId: 'S', seq, type: 'paper_snapshot',
    payload: { data: { status: 'ADMITTED',
      snapshot: { index: 17, challenge: 'a'.repeat(32) + ':17' } } },
    makeEnvelope,
    advanceSequence: () => { seq += 1; inc++ },
    traceEnabled: true,
    traceWriter: line => { trace.push(line); now += traceWaitMs*1000000n },
    stdoutWriter: line => { stdout.push(line); now += stdoutWaitMs*1000000n; return true },
    diagnosticWriter: line => {
      if (diagnosticFails) throw Error('disk full DEV sidecar only')
      sidecar.push(JSON.parse(line))
    },
    clock: timestamp,
    cpuUsage: prev => prev ? { user: 120, system: 15 } : { user: 0, system: 0 }
  })
  return { msg, trace, stdout, sidecar, seq, inc }
}

test('T1n creates exactly the prior native envelope and one stdout, without new effect', () => {
  const x = scenario()
  assert.equal(x.seq, 9)
  assert.equal(x.inc, 1)
  assert.deepEqual(JSON.parse(x.stdout[0]), x.msg)
  assert.equal(x.msg.seq, 8)
  assert.equal(x.msg.type, 'paper_snapshot')
  assert.equal(JSON.parse(x.trace[0]).node_monotonic_ns.length > 0, true)
  assert.equal(JSON.parse(x.trace[0]).seq, 8)
  assert.equal(x.sidecar[0].seq, 8)
  assert.equal(x.sidecar[0].source_index, 17)
  assert.equal(x.sidecar[0].source_status, 'ADMITTED')
  assert.equal(x.sidecar[0].stdout_write_return_is_delivery_ack, false)
  assert.equal(x.sidecar[0].source_qualification, false)
})

test('T1n retains 52ms sync trace write as trace phase, does not change admission', () => {
  const x = scenario({ traceWaitMs: 52n })
  const d = x.sidecar[0]
  assert.equal(Number(BigInt(d.trace_write_return_ns)
                       - BigInt(d.trace_serialize_return_ns))/1e6, 52.001)
  assert.equal(d.process_cpu_user_us, 120)
  assert.equal(d.stdout_write_accepted, true)
  assert.equal(x.msg.data.status, 'ADMITTED')
})

test('T1n stdout write duration is separate from sync trace write', () => {
  const x = scenario({ stdoutWaitMs: 58n })
  const d = x.sidecar[0]
  assert.equal(Number(BigInt(d.stdout_write_return_ns)
                       - BigInt(d.stdout_serialize_return_ns))/1e6, 58.001)
  assert.equal(x.stdout.length, 1)
})

test('T1n diagnostic sidecar error never alters canonical Paper emission', () => {
  const x = scenario({ diagnosticFails: true })
  assert.equal(x.sidecar.length, 0)
  assert.equal(x.trace.length, 1)
  assert.equal(x.stdout.length, 1)
  assert.equal(x.inc, 1)
})

test('T1n instrumented emitter refuses use for non-Paper messages', () => {
  assert.throws(() => emitWithT1nTiming({
    sessionId: 'S', seq: 0, type: 'effect_result',
    payload: {}, makeEnvelope: () => ({}),
    advanceSequence: () => {}, stdoutWriter: () => {},
    diagnosticWriter: () => {}, traceEnabled: false
  }), /Paper-only/)
})


test('sidecar open failure leaves instrumentation disabled and old path available', () => {
  assert.equal(openT1nSidecar('/missing/file', () => { throw Error('ENOENT') }), null)
  assert.equal(openT1nSidecar('/fresh/file', (...args) => {
    assert.deepEqual(args, ['/fresh/file', 'wx', 0o600]); return 42
  }), 42)
})


test('instrumented native operations preserve legacy order, bytes and STALE status', () => {
  const legacy = []; const instrumented = []
  const body = { data: { status: 'STALE', snapshot: { index: 1, challenge: 'old' } } }
  const envelope = (session_id, seq, type, payload) => ({ session_id, seq, type, ...payload })
  const msg = envelope('S', 7, 'paper_snapshot', body)
  legacy.push(['envelope', msg], ['trace', JSON.stringify({ node_monotonic_ns: '1', ...msg }) + '\n'],
    ['advance'], ['stdout', JSON.stringify(msg) + '\n'])
  const d = []
  emitWithT1nTiming({
    sessionId: 'S', seq: 7, type: 'paper_snapshot', payload: body,
    makeEnvelope: (...args) => { const m = envelope(...args); instrumented.push(['envelope', m]); return m },
    traceEnabled: true, clock: () => 1n,
    traceWriter: line => instrumented.push(['trace', line]),
    advanceSequence: () => instrumented.push(['advance']),
    stdoutWriter: line => { instrumented.push(['stdout', line]); return false },
    diagnosticWriter: line => d.push(JSON.parse(line))
  })
  assert.deepEqual(instrumented, legacy)
  assert.equal(d[0].source_status, 'STALE')
  assert.equal(d[0].stdout_write_accepted, false)
  assert.equal(d[0].stdout_write_return_is_delivery_ack, false)
})
