/** L21: isolated read-only Mineflayer Goal observer.
 *
 * Separate offline-authenticated client, independent TCP connection and
 * append-only observer-owned raw JSONL. No control/attack/look/equip APIs,
 * no Action authorization, no physical time attestation or S10/L10 writes.
 * Its *presence* is a World intervention; do not claim isolation.
 */
import { randomUUID } from 'node:crypto'
import { createRequire } from 'node:module'
import {
  closeSync, existsSync, fsyncSync, lstatSync, openSync,
  readFileSync, writeSync
} from 'node:fs'
import { isAbsolute, join } from 'node:path'
import readline from 'node:readline'
import {
  positionOfTarget, readCommitment, readOnlyCommand, statusFromSamples
} from './l21_goal_observer_core.mjs'

const root = process.env.RELAYSELF_RSEE_NODE_RUNTIME_ROOT
if (root && (!isAbsolute(root) || lstatSync(root).isSymbolicLink() ||
  lstatSync(join(root, 'node_modules')).isSymbolicLink())) {
  throw new Error('untrusted RSEE Node runtime')
}
const require = createRequire(root ? join(root, 'package.json') : import.meta.url)
const mineflayer = require('mineflayer')
if (require('mineflayer/package.json').version !== '4.39.0') {
  throw new Error('L21 needs exact Mineflayer 4.39.0')
}

const argKeys = new Set([
  '--goal-file', '--goal-sha256', '--output',
  '--observer-username', '--target-username'
])
const argv = process.argv.slice(2)
if (argv.length !== 10) throw new Error('L21 requires five key/value flags')
const args = {}
for (let i = 0; i < argv.length; i += 2) {
  if (!argKeys.has(argv[i]) || Object.hasOwn(args, argv[i])) {
    throw new Error('L21 observer args must be exact and unique')
  }
  args[argv[i]] = argv[i + 1]
}
if (Object.keys(args).length !== argKeys.size ||
    args['--observer-username'] !== 'RelayGoalObserver' ||
    args['--target-username'] !== 'RelaySelf' ||
    !isAbsolute(args['--goal-file']) ||
    !isAbsolute(args['--output']) ||
    args['--goal-file'] === args['--output'] ||
    !existsSync(args['--goal-file']) ||
    lstatSync(args['--goal-file']).isSymbolicLink()) {
  throw new Error('L21 requires own output and separate physical Goal original')
}
const criterion = readCommitment(
  readFileSync(args['--goal-file']), args['--goal-sha256']
)
const observerSession = randomUUID()
const fd = openSync(args['--output'], 'wx', 0o600)
// Diagnostic clock only; never interpreted as a Minecraft tick or attestation.
const timingFd = openSync(args['--output'] + '.timing.jsonl', 'wx', 0o600)
let index = 0
let started = false
let closed = false
let sampleCount = 0
const samples = []
let bot

function original (kind, fields = {}) {
  const value = {
    schema: 'L21_SEPARATE_CLIENT_GOAL_OBSERVER_V1',
    observer_session: observerSession, index, kind, ...fields
  }
  index += 1
  const bytes = Buffer.from(JSON.stringify(value) + '\n')
  if (bytes.length > 8192) throw new Error('oversized L21 source row')
  writeSync(fd, bytes)
  fsyncSync(fd)
  writeSync(timingFd, JSON.stringify({
    observer_session: observerSession, index: value.index, kind,
    wall_time_ms: Date.now(), monotonic_ns: process.hrtime.bigint().toString()
  }) + '\n')
  fsyncSync(timingFd)
}
function ack (kind, fields = {}) {
  process.stdout.write(JSON.stringify({ type: kind, ...fields }) + '\n')
}
function stop () {
  if (closed) return
  closed = true
  original('closed', { samples: sampleCount })
  closeSync(fd)
  closeSync(timingFd)
  input.close()
  if (bot) bot.quit('L21 read-only observer shutdown')
  ack('closed', { samples: sampleCount })
}
function fail (error) {
  if (closed) return
  process.stderr.write('L21 separate observer: ' + String(error?.message || error) + '\n')
  process.exitCode = 2
  try {
    original('fault', { reason: String(error?.message || error).slice(0,200) })
    closeSync(fd)
    closeSync(timingFd)
  } catch {
    // No reconstructed claim after source IO failure.
  }
  closed = true
  if (bot) bot.quit('L21 observer failed')
  ack('fault')
}
original('start', {
  criterion_sha256: args['--goal-sha256'],
  observer_username: args['--observer-username'],
  target_username: args['--target-username'],
  observer_capabilities: 'READ_ONLY_MINEFLAYER_SECOND_TCP_CLIENT',
  goal_observation_authority: false
})

bot = mineflayer.createBot({
  host: '127.0.0.1', port: 25565, username: 'RelayGoalObserver',
  version: '1.21.8', auth: 'offline', logErrors: false, respawn: true
})
bot.once('spawn', () => {
  if (closed) return
  started = true
  original('ready', { observer_entity_id: bot.entity?.id ?? null })
  ack('ready', { observer_session: observerSession })
})
bot.on('error', fail)
bot.on('end', reason => {
  if (!closed) fail(new Error('observer connection ended: ' + String(reason)))
})
const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity })
let pending = Promise.resolve()
input.on('line', line => {
  pending = pending.then(() => {
    if (closed) return
    const cmd = readOnlyCommand(line)
    if (cmd.type === 'shutdown') {
      stop()
      return
    }
    if (!started || sampleCount >= 2) throw new Error('L21 sample not admitted')
    if (!cmd.request_id.endsWith(':goal-' + String(sampleCount + 1))) {
      throw new Error('Goal sample number or request correlation invalid')
    }
    const position = positionOfTarget(bot, 'RelaySelf')
    sampleCount += 1
    samples.push(position)
    original('sample', { request_id: cmd.request_id, position })
    ack('sample', { request_id: cmd.request_id })
    if (sampleCount === 2) {
      const status = statusFromSamples(samples[0], samples[1], criterion)
      original('goal_result', {
        first_request_id: cmd.request_id.replace(/:goal-2$/, ':goal-1'),
        second_request_id: cmd.request_id,
        goal_status: status
      })
      ack('goal_result', { goal_status: status })
    }
  }).catch(fail)
})
input.once('close', () => {
  if (!closed) fail(new Error('observer input ended before explicit shutdown'))
})
