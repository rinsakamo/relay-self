/** L21 source-only read-only second-client Goal observation math.
 * Pure/testable: no Minecraft imports, motor APIs, S49 or L10 authority.
 */
import { createHash } from 'node:crypto'

const SHA = /^[0-9a-f]{64}$/
const IDENT = /^[A-Za-z0-9][A-Za-z0-9_.:-]{3,127}$/
const FIELDS = [
  'action_scope', 'authorizes_learning', 'criterion_id',
  'experiment_ref', 'external_goal_owner_ref', 'independent_goal_observed',
  'schema', 'session_scope', 'stable_probe_delta_max_m',
  'target_x', 'target_z', 'tolerance_m'
]

export function readCommitment (raw, sha) {
  if (!Buffer.isBuffer(raw) || raw.length === 0 || raw.length > 4096 ||
      !SHA.test(sha) ||
      createHash('sha256').update(raw).digest('hex') !== sha ||
      raw.at(-1) !== 10 || raw.subarray(0, -1).includes(10)) {
    throw new Error('original L20 reviewer commitment SHA/shape invalid')
  }
  const text = raw.toString('utf8')
  const doc = JSON.parse(text)
  if (doc === null || Array.isArray(doc) || typeof doc !== 'object' ||
      Object.keys(doc).sort().join(',') !== FIELDS.join(',') ||
      doc.schema !== 'L20_PRE_WORLD_EXTERNAL_GOAL_COMMITMENT_V1' ||
      doc.session_scope !== 'UNKNOWN_UNTIL_S49_SESSION_START' ||
      doc.action_scope !== 'FIRST_S49_PHYSICAL_ACTION_ONLY' ||
      doc.independent_goal_observed !== false ||
      doc.authorizes_learning !== false ||
      !IDENT.test(doc.criterion_id) ||
      !IDENT.test(doc.experiment_ref) ||
      !IDENT.test(doc.external_goal_owner_ref) ||
      ![doc.target_x, doc.target_z, doc.tolerance_m, doc.stable_probe_delta_max_m]
        .every(v => typeof v === 'number' && Number.isFinite(v)) ||
      doc.tolerance_m <= 0 || doc.tolerance_m > 16 ||
      doc.stable_probe_delta_max_m <= 0 ||
      doc.stable_probe_delta_max_m > 0.1 ||
      JSON.stringify(Object.fromEntries(
        Object.keys(doc).sort().map(k => [k, doc[k]])
      )) + '\n' !== text) {
    throw new Error('L20 reviewer original fields/values/canonical order invalid')
  }
  return Object.freeze(doc)
}

export function readOnlyCommand (line) {
  if (typeof line !== 'string' || line.length > 300) throw new Error('command size invalid')
  const cmd = JSON.parse(line)
  if (cmd === null || typeof cmd !== 'object' || Array.isArray(cmd)) {
    throw new Error('command object required')
  }
  if (cmd.type === 'shutdown' && Object.keys(cmd).join(',') === 'type') {
    return Object.freeze({ type: 'shutdown' })
  }
  if (Object.keys(cmd).sort().join(',') !== 'request_id,type' ||
      cmd.type !== 'sample' ||
      !/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(cmd.request_id)) {
    throw new Error('L21 accepts only read-only sample or shutdown')
  }
  return Object.freeze({ type: 'sample', request_id: cmd.request_id })
}

export function positionOfTarget (bot, targetUsername) {
  if (targetUsername === bot.username || !bot.entity) return null
  const target = bot.players?.[targetUsername]?.entity
  if (!target || !Number.isInteger(target.id) ||
      target.id === bot.entity.id || !target.position) return null
  const { x, y, z } = target.position
  if (![x, y, z].every(Number.isFinite)) return null
  return { entity_id: target.id, x, y, z }
}

export function statusFromSamples (first, second, criterion) {
  if (first === null || second === null ||
      first.entity_id !== second.entity_id) return 'UNDETERMINED'
  const a = Math.hypot(first.x - criterion.target_x, first.z - criterion.target_z)
  const b = Math.hypot(second.x - criterion.target_x, second.z - criterion.target_z)
  const drift = Math.hypot(first.x - second.x, first.z - second.z)
  if (![a, b, drift].every(Number.isFinite) ||
      drift > criterion.stable_probe_delta_max_m ||
      (a <= criterion.tolerance_m) !== (b <= criterion.tolerance_m)) {
    return 'UNDETERMINED'
  }
  return b <= criterion.tolerance_m ? 'REACHED' : 'NOT_REACHED'
}
