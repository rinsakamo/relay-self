// #150: conservative host-side processing budget for the existing native
// Paper tick channel. Never attests server freshness, L0 correctness, or TPS.
// Uses ONLY the Node monotonic clock; Paper/JVM and Node clock epochs differ.
const SOURCE = 'PAPER_SCHEDULER_CALLBACK_ONLY'
const MAX_I64 = 9223372036854775807n

function requireNs(value, label) {
  if (typeof value !== 'string' || !/^(0|[1-9][0-9]*)$/.test(value)) {
    throw new Error('invalid ' + label)
  }
  const converted = BigInt(value)
  if (converted > MAX_I64) throw new Error('overflow ' + label)
  return converted
}

export class PaperTickDeadlineGuard {
  #previous = null
  #failed = false
  #numerator
  #denominator

  constructor ({ budgetNumerator = 1, budgetDenominator = 2 } = {}) {
    if (!Number.isSafeInteger(budgetNumerator) ||
        !Number.isSafeInteger(budgetDenominator) ||
        budgetNumerator < 1 || budgetDenominator < 2 ||
        budgetNumerator >= budgetDenominator || budgetDenominator > 1000) {
      throw new Error('invalid bounded local budget fraction')
    }
    this.#numerator = BigInt(budgetNumerator)
    this.#denominator = BigInt(budgetDenominator)
  }

  get failed () { return this.#failed }

  // Return an observation-only local budget result. The first sample cannot
  // estimate receive cadence; a loss poisons the whole current bridge session.
  observe (sample, { completedMonoNs }) {
    if (this.#failed) throw new Error('latched unsafe Paper tick delivery')
    try {
      if (!sample || sample.source !== SOURCE ||
          !Number.isSafeInteger(sample.index) || sample.index < 1 || sample.index > 256 ||
          typeof sample.world !== 'string' || !sample.world ||
          typeof sample.player !== 'string' || !sample.player ||
          typeof completedMonoNs !== 'bigint' || completedMonoNs < 0n) {
        throw new Error('invalid Paper tick local budget input')
      }
      const received = requireNs(sample.bridge_recv_monotonic_ns, 'receive timestamp')
      const tick = requireNs(sample.server_tick, 'server tick')
      const completed = completedMonoNs
      if (completed < received) throw new Error('local completion before receive')
      const localDuration = completed - received
      if (this.#previous === null) {
        if (sample.index !== 1) throw new Error('missing first Paper tick')
        this.#previous = { index: sample.index, tick, received,
          world: sample.world, player: sample.player }
        return Object.freeze({
          status: 'INITIAL_CADENCE_UNKNOWN',
          local_processing_ns: localDuration.toString(),
          observed_arrival_gap_ns: null,
          l0_world_freshness_attested: false,
          tps_admission_granted: false
        })
      }
      const prior = this.#previous
      if (sample.index !== prior.index + 1 || tick !== prior.tick + 1n ||
          sample.world !== prior.world || sample.player !== prior.player ||
          received <= prior.received) {
        throw new Error('Paper tick reception discontinuity')
      }
      const gap = received - prior.received
      // Relative to observed bridge arrival cadence only, not actual server
      // tick deadline. Strictly fail at the boundary to avoid optimism.
      if (localDuration * this.#denominator >= gap * this.#numerator) {
        throw new Error('Paper L0 local processing over measured tick budget')
      }
      this.#previous = { index: sample.index, tick, received,
        world: sample.world, player: sample.player }
      return Object.freeze({
        status: 'HOST_LOCAL_BUDGET_MET_ONLY',
        local_processing_ns: localDuration.toString(),
        observed_arrival_gap_ns: gap.toString(),
        l0_world_freshness_attested: false,
        tps_admission_granted: false
      })
    } catch (error) {
      this.#failed = true
      throw error
    }
  }
}

// The single bridge caller supplies its existing emit() seam. Both receipts
// are emitted atomically with respect to a *budget refusal*: no accepted
// Paper/L0 pair escapes before the deadline check. Still no native authority.
export function handleBudgetedPaperTick (sample, bot, { guard, evaluateShadow, emit, clock }) {
  if (!(guard instanceof PaperTickDeadlineGuard) ||
      typeof evaluateShadow !== 'function' || typeof emit !== 'function' ||
      typeof clock !== 'function') {
    throw new TypeError('single receiver must supply bounded local seams')
  }
  const shadow = evaluateShadow(sample, bot)
  if (!shadow || shadow.source !== 'MINEFLAYER_CACHE_SHADOW_L0_DEV' ||
      shadow.paper_sample_index !== sample?.index ||
      shadow.paper_server_tick !== sample.server_tick ||
      shadow.paper_world !== sample.world || shadow.paper_player !== sample.player ||
      shadow.l0_shadow_evaluated !== true ||
      shadow.l0_fresh_world_tick_attested !== false ||
      shadow.tps_admission_granted !== false ||
      shadow.authorized_action_issued !== false) {
    throw new Error('L0 shadow may not claim fresh native Action or TPS authority')
  }
  const result = guard.observe(sample, { completedMonoNs: clock() })
  emit('paper_tick_sample', sample)
  emit('paper_l0_shadow', shadow)
  return result
}
