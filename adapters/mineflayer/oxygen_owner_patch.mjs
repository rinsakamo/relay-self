#!/usr/bin/env node
// Explicit DEV-only local backport of upstream Mineflayer PR #4052.
// Operates only on this worktree's npm-ci locked 4.39.0 installation.
// No auto-install, no symlink, no other package version, no World process.
import { createHash } from 'node:crypto'
import { lstatSync, readFileSync, realpathSync, renameSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = dirname(fileURLToPath(import.meta.url))
const ORIGINAL = [
  '      // Breathing (formerly in breath.js)',
  '      if (metas.air_supply != null) {',
  '        bot.oxygenLevel = Math.round(metas.air_supply / 15)',
  "        bot.emit('breath')",
  '      }'
].join('\n')
const FIXED = ORIGINAL.replace(
  'if (metas.air_supply != null) {',
  'if (metas.air_supply != null && entity.id === bot.entity?.id) {'
)

export function inspectOwnerPatch (content) {
  if (typeof content !== 'string') throw new TypeError('source must be text')
  const count = (sample) => content.split(sample).length - 1
  const original = count(ORIGINAL)
  const fixed = count(FIXED)
  if (fixed === 1 && original === 0) return 'PATCHED'
  if (original === 1 && fixed === 0) return 'VULNERABLE'
  throw new Error('Mineflayer 4.39.0 oxygen owner source marker absent, multiple, or altered')
}

export function exactOwnerBackport (content) {
  if (inspectOwnerPatch(content) !== 'VULNERABLE') {
    throw new Error('patch source is not exactly the unmodified vulnerable block')
  }
  const changed = content.replace(ORIGINAL, FIXED)
  if (inspectOwnerPatch(changed) !== 'PATCHED') {
    throw new Error('patch output failed independent inspection')
  }
  return changed
}

function sha256 (buffer) {
  return createHash('sha256').update(buffer).digest('hex')
}

export function inspectInstalled (root = ROOT) {
  const packagePath = join(root, 'node_modules', 'mineflayer', 'package.json')
  const sourcePath = join(root, 'node_modules', 'mineflayer', 'lib', 'plugins', 'entities.js')
  // Never follow a symlink out of the current worktree.
  for (const p of [packagePath, sourcePath]) {
    if (!lstatSync(p).isFile() || realpathSync(p) !== resolve(p)) {
      throw new Error('worktree-local Mineflayer source must be a regular non-symlink file')
    }
  }
  const manifest = JSON.parse(readFileSync(packagePath, 'utf8'))
  if (manifest.version !== '4.39.0') {
    throw new Error('only exact npm-ci locked Mineflayer 4.39.0 is patchable')
  }
  const bytes = readFileSync(sourcePath)
  const source = bytes.toString('utf8')
  if (Buffer.from(source, 'utf8').length !== bytes.length) {
    throw new Error('source is not valid UTF-8')
  }
  return { sourcePath, source, status: inspectOwnerPatch(source), digest: sha256(bytes) }
}

function main () {
  const arg = process.argv.slice(2)
  if (arg.length !== 1 || !['--inspect-only', '--apply'].includes(arg[0])) {
    throw new Error('usage: node adapters/mineflayer/oxygen_owner_patch.mjs --inspect-only|--apply')
  }
  const installed = inspectInstalled()
  if (arg[0] === '--inspect-only') {
    if (installed.status !== 'PATCHED') throw new Error('owner backport not installed')
    console.log('STAGE24D_MINEFLAYER_OWNER_PATCH_OK original=4.39.0 source_sha256=' + installed.digest)
    return
  }
  if (installed.status !== 'VULNERABLE') {
    throw new Error('patch already applied or source changed; never mutate twice')
  }
  const updated = exactOwnerBackport(installed.source)
  const tmp = installed.sourcePath + '.relay-stage24d-apply.tmp'
  try {
    writeFileSync(tmp, updated, { flag: 'wx', mode: 0o644 })
    renameSync(tmp, installed.sourcePath)
  } finally {
    try { rmSync(tmp) } catch (err) {
      if (err.code !== 'ENOENT') throw err
    }
  }
  const verified = inspectInstalled()
  if (verified.status !== 'PATCHED') throw new Error('post-write source verification failed')
  console.log(
    'STAGE24D_MINEFLAYER_OWNER_PATCH_APPLIED version=4.39.0 upstream_pr=4052 ' +
    'before_sha256=' + installed.digest + ' after_sha256=' + verified.digest
  )
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main() } catch (err) {
    console.error('STAGE24D_PATCH_HOLD=' + (err.message || String(err)))
    process.exitCode = 2
  }
}
