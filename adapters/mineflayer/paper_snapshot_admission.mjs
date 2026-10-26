// T1f DEV: same-connection causal challenge bounds observation age without
// subtracting JVM and Node clocks. Source is the Paper callback, not bot cache.
import { randomBytes } from 'node:crypto'
import { PAPER_TICK_CHANNEL } from './paper_tick_channel.mjs'
const UUID = /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/
const KEYS = ['version', 'boot', 'index', 'tick', 'world_tick', 'paper_ns',
  'world', 'player', 'challenge', 'x', 'y', 'z', 'health', 'food', 'input',
  'threats_complete', 'threats', 'basal_ticks', 'basal_exhaustion',
  'motion_blocks', 'motion_exhaustion']
const nat = n => Number.isSafeInteger(n) && n >= 0
export function decodeSnapshot (bytes) {
  if (!Buffer.isBuffer(bytes) || bytes.length > 32768) throw Error('snapshot size')
  const s = JSON.parse(bytes.toString('utf8'))
  if (!s || Object.keys(s).length !== KEYS.length || KEYS.some(k => !Object.hasOwn(s, k)) ||
      s.version !== 1 || ![s.boot, s.world, s.player].every(v => typeof v === 'string' && UUID.test(v)) ||
      ![s.index, s.tick, s.world_tick, s.paper_ns, s.basal_ticks].every(nat) ||
      s.index < 1 || s.index > 2400 || !nat(s.input) || s.input > 127 ||
      ![s.x, s.y, s.z, s.health, s.food, s.basal_exhaustion, s.motion_blocks,
        s.motion_exhaustion].every(Number.isFinite) || s.health < 0 || s.health > 2048 ||
      !nat(s.food) || s.food > 20 || typeof s.threats_complete !== 'boolean' ||
      !Array.isArray(s.threats) || s.threats.length > 128 ||
      typeof s.challenge !== 'string' || !/^(NONE|[0-9a-f]{32}:[1-9][0-9]{0,3})$/.test(s.challenge)) {
    throw Error('missing/invalid Paper snapshot values')
  }
  for (const t of s.threats) {
    if (!t || Object.keys(t).sort().join() !== 'distance,id,kind,x,y,z' ||
        !UUID.test(t.id) || typeof t.kind !== 'string' || !/^[A-Z_]+$/.test(t.kind) ||
        ![t.x, t.y, t.z, t.distance].every(Number.isFinite) || t.distance < 0 ||
        Math.abs(Math.hypot(t.x - s.x, t.y - s.y, t.z - s.z) - t.distance) > 1e-6 ||
        t.distance > 4) throw Error('invalid threat observation')
  }
  return s
}
export class SnapshotAdmission {
  constructor ({ token = randomBytes(16).toString('hex'), maxAgeNs = 150000000n,
    evaluationBudgetNs = 25000000n } = {}) {
    if (!/^[0-9a-f]{32}$/.test(token) || typeof maxAgeNs !== 'bigint' || maxAgeNs <= 0n ||
        typeof evaluationBudgetNs !== 'bigint' || evaluationBudgetNs <= 0n) throw Error('policy')
    Object.assign(this, { token, maxAgeNs, evaluationBudgetNs, previous: null,
      challenge: null, history: new Map(), counter: 0, failed: false })
  }
  issue (now) {
    if (typeof now !== 'bigint' || now < 0n || this.counter >= 2400) throw Error('challenge clock/budget')
    const id = `${this.token}:${++this.counter}`
    this.challenge = { id, sent: now }
    this.history.set(id, now)
    if (this.history.size > 16) this.history.delete(this.history.keys().next().value)
    return Buffer.from(id, 'ascii')
  }
  evaluate (s, { received, start, completed, cache = null, latestTick = s.tick }) {
    let status = 'ADMITTED'; let reason = 'CAUSAL_AGE_UPPER_BOUND_MET'
    const prior = this.previous
    const sent = this.history.get(s.challenge)
    const age = sent !== undefined ? completed - sent : null
    const refuse = (v, why) => { status = v; reason = why }
    if (this.failed) refuse('UNDETERMINED', 'SESSION_LATCHED')
    else if ([received, start, completed].some(n => typeof n !== 'bigint' || n < 0n) ||
             received > start || start > completed || (age !== null && age < completed - received)) {
      refuse('UNDETERMINED', 'CLOCK_ORDER')
    } else if (prior && [s.boot, s.world, s.player].join() !== [prior.boot, prior.world, prior.player].join()) {
      refuse('UNDETERMINED', 'FOREIGN_IDENTITY')
    } else if (prior && (s.tick <= prior.tick || s.index <= prior.index || s.world_tick <= prior.world_tick)) {
      refuse('STALE', 'DUPLICATE_OR_REORDERED')
    } else if ((!prior && s.index !== 1) || (prior && (s.tick !== prior.tick + 1 ||
               s.index !== prior.index + 1 || s.world_tick !== prior.world_tick + 1))) {
      refuse('MISSING', 'TICK_GAP')
    } else if (latestTick !== s.tick) refuse('STALE', 'NEWER_CONFIRMED_TICK')
    else if (!s.threats_complete) refuse('MISSING', 'INCOMPLETE_NEARBY')
    else if (completed - start >= this.evaluationBudgetNs || completed - received >= this.evaluationBudgetNs) {
      refuse('LATE', 'NODE_QUEUE_OR_EVALUATION_DEADLINE')
    } else if (age === null) refuse('UNDETERMINED', 'NO_MATCHING_CAUSAL_CHALLENGE')
    else if (age >= this.maxAgeNs) refuse('STALE', 'CAUSAL_AGE_UPPER_BOUND_EXCEEDED')
    // First NONE is expected during subscription startup. All other refusals
    // poison this bounded session; no skipped gap is later credited as fresh.
    if (status !== 'ADMITTED' && !(s.index === 1 && s.challenge === 'NONE' && !prior)) this.failed = true
    this.previous = s
    const assessment = status !== 'ADMITTED' ? 'UNKNOWN' : s.health <= 6 ? 'LOW_HEALTH'
      : s.food <= 6 ? 'LOW_FOOD' : s.threats.length ? 'KNOWN_NEAR_HOSTILE' : 'NO_KNOWN_URGENT_SIGNAL'
    return { snapshot: s, status, reason, assessment, latest_confirmed_tick: latestTick,
      challenge_sent_ns: sent?.toString() ?? null,
      received_ns: received.toString(), evaluation_start_ns: start.toString(),
      evaluation_completed_ns: completed.toString(), age_upper_ns: age?.toString() ?? null,
      age_lower_ns: (completed - received).toString(),
      paper_to_node_exact_ns: null,
      cache_mismatch: cache && Number.isFinite(cache.health) ? cache.health !== s.health ||
        cache.food !== s.food || !cache.entity?.position ||
        Math.hypot(cache.entity.position.x - s.x, cache.entity.position.y - s.y,
          cache.entity.position.z - s.z) > 1e-6 : null,
      qualification: false, tps_admission_granted: false }
  }
}
export function attachPaperSnapshotChannel (bot, emit, onInvalid, clock = () => process.hrtime.bigint(), controlState = () => ({ phase: "INITIAL", since_ns: "0", generation: 0 })) {
  const guard = new SnapshotAdmission()
  let lastResult = null
  const challenge = () => bot._client.write('custom_payload', {
    channel: PAPER_TICK_CHANNEL, data: guard.issue(clock())
  })
  bot.once('login', () => {
    bot._client.registerChannel(PAPER_TICK_CHANNEL, null, true)
    challenge()
  })
  bot._client.on(PAPER_TICK_CHANNEL, bytes => {
    const received = clock()
    try {
      const s = decodeSnapshot(bytes)
      const start = clock()
      // Assessment is deliberately tiny and synchronous; record completion
      // AFTER both the input checks and the actual decision have executed.
      const result = guard.evaluate(s, { received, start, completed: clock(), cache: bot })
      const end = clock()
      result.evaluation_completed_ns = end.toString()
      if (end - received >= guard.evaluationBudgetNs) {
        result.status = 'LATE'; result.reason = 'EVALUATION_COMPLETION_DEADLINE'
        result.assessment = 'UNKNOWN'; guard.failed = true
      }
      if (result.age_upper_ns !== null) {
        // Recompute directly using the still-unconsumed challenge.
        result.age_upper_ns = (end - BigInt(result.challenge_sent_ns)).toString()
        if (BigInt(result.age_upper_ns) >= guard.maxAgeNs) {
          result.status = 'STALE'; result.reason = 'CAUSAL_AGE_UPPER_BOUND_EXCEEDED'
          result.assessment = 'UNKNOWN'; guard.failed = true
        }
      }
      result.age_lower_ns = (end - received).toString()
      result.control = controlState()
      lastResult = result
      emit('paper_snapshot', { data: result })
      challenge()
    } catch (error) { guard.failed = true; onInvalid(error) }
  })
  return { canDispatch: () => lastResult?.status === 'ADMITTED' && !guard.failed &&
    lastResult.assessment === 'NO_KNOWN_URGENT_SIGNAL' &&
    BigInt(lastResult.age_upper_ns) + clock() - BigInt(lastResult.evaluation_completed_ns) < guard.maxAgeNs }
}
