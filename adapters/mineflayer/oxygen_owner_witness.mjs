// Stage24d: source-qualified self oxygen witness. Read-only, no motor authority.
// A patched Mineflayer 4.39.0+4052 'breath' event is the input boundary.
// Neither stale bot.oxygenLevel nor foreign Entity data is ever substituted.
const DEFAULT_MAX_AGE_MS = 5000

export class OwnedOxygenWitness {
  constructor ({ sessionId, clock = () => performance.now(), maxAgeMs = DEFAULT_MAX_AGE_MS }) {
    if (typeof sessionId !== 'string' || sessionId.length === 0 ||
        typeof clock !== 'function' || !Number.isFinite(maxAgeMs) || maxAgeMs <= 0) {
      throw new TypeError('owned oxygen witness needs session/clock/finite max age')
    }
    this.sessionId = sessionId
    this.clock = clock
    this.maxAgeMs = maxAgeMs
    this.generation = 0
    this.selfEntityId = null
    this.latest = null
    this.sourceCount = 0
  }

  bindSelf (entityId) {
    if (!Number.isInteger(entityId) || entityId < 0) {
      throw new TypeError('self Entity ID must be nonnegative integer')
    }
    this.generation += 1
    this.selfEntityId = entityId
    this.latest = null
  }

  invalidate () {
    this.generation += 1
    this.selfEntityId = null
    this.latest = null
  }

  acceptBreath ({ entityId, oxygenLevel }) {
    // A live breath event only comes from the *verified patched* Mineflayer
    // Entity metadata owner. This tracker cannot independently read the
    // raw packet; it therefore does not claim raw self-metadata attestation.
    if (this.selfEntityId === null || entityId !== this.selfEntityId ||
        !Number.isFinite(oxygenLevel) || oxygenLevel < 0) return false
    this.sourceCount += 1
    this.latest = {
      level: oxygenLevel,
      ageOriginMs: this.clock(),
      generation: this.generation,
      sourceSeq: this.sourceCount
    }
    return true
  }

  read (entityId) {
    const now = this.clock()
    const receipt = {
      schema: 'STAGE24D_OWNED_OXYGEN_RECEIPT_V0',
      session_id: this.sessionId,
      self_entity_id: this.selfEntityId,
      requested_entity_id: Number.isInteger(entityId) ? entityId : null,
      generation: this.generation,
      origin: 'mineflayer-4.39.0+upstream-4052-self-breath-event',
      epistemic_status: 'UNKNOWN',
      source_seq: null,
      age_ms: null,
      level: null,
      physical_authorized: false
    }
    const latest = this.latest
    if (this.selfEntityId === null || entityId !== this.selfEntityId ||
        latest === null || latest.generation !== this.generation) return receipt
    const age = now - latest.ageOriginMs
    receipt.source_seq = latest.sourceSeq
    receipt.age_ms = Number.isFinite(age) && age >= 0 ? age : null
    if (receipt.age_ms === null || age > this.maxAgeMs) {
      receipt.epistemic_status = 'STALE_OR_UNVERIFIED'
      return receipt
    }
    receipt.epistemic_status = 'FRESH_OWNED'
    receipt.level = latest.level
    return receipt
  }
}
