// #150 DEV: one bounded shadow evaluation per Paper tick delivery, on the
// existing Mineflayer process.  NEVER issues motor effects or attests that
// the client cache contains a fresh server snapshot for that WorldTick.
const HOSTILE = new Set(['zombie', 'skeleton', 'creeper', 'spider', 'drowned', 'husk', 'stray'])
const PRECISION = 'CLIENT_CACHE_POST_PAPER_MESSAGE_NOT_EPOCH_FRESH'

function validPosition (p) {
  return p && Number.isFinite(p.x) && Number.isFinite(p.y) && Number.isFinite(p.z)
}

export function paperL0Shadow (sample, bot, startNs, endNs) {
  if (!sample || sample.source !== 'PAPER_SCHEDULER_CALLBACK_ONLY' ||
      !Number.isInteger(sample.index) || sample.index < 1 || sample.index > 256 ||
      typeof sample.server_tick !== 'string' ||
      typeof sample.world !== 'string' || typeof sample.player !== 'string' ||
      typeof startNs !== 'bigint' || typeof endNs !== 'bigint' ||
      endNs < startNs || startNs < 0n) {
    throw new Error('invalid bound Paper L0 shadow request')
  }
  let assessment = 'UNKNOWN'
  let observations = 0
  if (bot && Number.isFinite(bot.health) && Number.isFinite(bot.food) &&
      bot.entity && validPosition(bot.entity.position)) {
    observations = 1
    if (bot.health <= 6) assessment = 'LOW_HEALTH'
    else if (bot.food <= 6) assessment = 'LOW_FOOD'
    else if (bot.entities && typeof bot.entities === 'object') {
      const entities = Object.values(bot.entities)
      if (entities.length <= 128) {
        let threat = false
        for (const e of entities) {
          if (!e || typeof e.name !== 'string' || !validPosition(e.position)) continue
          if (!HOSTILE.has(e.name)) continue
          const dx = e.position.x - bot.entity.position.x
          const dy = e.position.y - bot.entity.position.y
          const dz = e.position.z - bot.entity.position.z
          if (dx * dx + dy * dy + dz * dz <= 16) {
            threat = true
            break
          }
        }
        assessment = threat ? 'KNOWN_NEAR_HOSTILE' : 'NO_KNOWN_URGENT_SIGNAL'
      }
    }
  }
  // No safety authorization: a client-side cache may be stale or incomplete.
  return Object.freeze({
    source: 'MINEFLAYER_CACHE_SHADOW_L0_DEV',
    observation_precision: PRECISION,
    paper_sample_index: sample.index,
    paper_server_tick: sample.server_tick,
    paper_world: sample.world,
    paper_player: sample.player,
    evaluation_duration_ns: (endNs - startNs).toString(),
    assessment,
    cached_body_observed: observations === 1,
    l0_shadow_evaluated: true,
    l0_fresh_world_tick_attested: false,
    authorized_action_issued: false,
    tps_admission_granted: false
  })
}

export function evaluatePaperL0Shadow (sample, bot) {
  const start = process.hrtime.bigint()
  // Avoid a second reader or asynchronous callbacks, finish in same Node
  // event-loop turn as the delivered Paper message.
  const result = paperL0Shadow(sample, bot, start, start)
  const completed = process.hrtime.bigint()
  return Object.freeze({
    ...result,
    evaluation_duration_ns: (completed - start).toString()
  })
}
