// Deterministic filesystem doubles on hosted CI; never imports Mineflayer/World.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, symlinkSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { dependencyRequire } from './dependency_runtime.mjs'

function fixture () {
  const base = mkdtempSync(join(tmpdir(), 'e13-deps-'))
  const root = join(base, 'external')
  const source = join(base, 'source')
  mkdirSync(root)
  mkdirSync(source)
  for (const directory of [root, source]) {
    for (const name of ['package.json', 'package-lock.json']) {
      writeFileSync(join(directory, name), readFileSync(new URL(name, import.meta.url)))
    }
  }
  for (const [name, version] of [['mineflayer', '4.39.0'], ['minecraft-protocol', '1.68.0']]) {
    const directory = join(root, 'node_modules', name)
    mkdirSync(directory, { recursive: true })
    writeFileSync(join(directory, 'package.json'), JSON.stringify({ version, main: 'index.cjs' }))
    writeFileSync(join(directory, 'index.cjs'), "throw new Error('must not import synthetic World module')")
  }
  return { base, root, source, url: pathToFileURL(join(source, 'bridge.mjs')).href }
}

test('explicit external createRequire resolves real transitive entries without importing World', () => {
  const f = fixture()
  try {
    const require = dependencyRequire(f.url, { RELAYSELF_RSEE_NODE_RUNTIME_ROOT: f.root })
    assert.equal(require.resolve('mineflayer'), join(f.root, 'node_modules/mineflayer/index.cjs'))
    assert.equal(require.resolve('minecraft-protocol'), join(f.root, 'node_modules/minecraft-protocol/index.cjs'))
    assert.equal(require('mineflayer/package.json').version, '4.39.0')
    assert.throws(() => require('mineflayer'), /must not import/)
  } finally { rmSync(f.base, { recursive: true }) }
})

for (const fault of ['manifest', 'lock', 'version', 'protocol-version', 'root-link', 'module-link', 'nested-protocol', 'NODE_PATH', 'NODE_OPTIONS']) {
  test(`reject ${fault} before importing any World module`, () => {
    const f = fixture()
    try {
      const env = { RELAYSELF_RSEE_NODE_RUNTIME_ROOT: f.root }
      if (fault === 'manifest' || fault === 'lock') {
        writeFileSync(join(f.root, fault === 'lock' ? 'package-lock.json' : 'package.json'), '{}wrong')
      } else if (fault === 'version' || fault === 'protocol-version') {
        const name = fault === 'version' ? 'mineflayer' : 'minecraft-protocol'
        writeFileSync(join(f.root, 'node_modules', name, 'package.json'), '{"version":"0.0.0","main":"index.cjs"}')
      } else if (fault === 'root-link') {
        symlinkSync(f.root, join(f.base, 'alias'))
        env.RELAYSELF_RSEE_NODE_RUNTIME_ROOT = join(f.base, 'alias')
      } else if (fault === 'module-link') {
        const directory = join(f.root, 'node_modules/minecraft-protocol')
        rmSync(directory, { recursive: true })
        symlinkSync(join(f.root, 'node_modules/mineflayer'), directory)
      } else if (fault === 'nested-protocol') {
        const directory = join(f.root, 'node_modules/mineflayer/node_modules/minecraft-protocol')
        mkdirSync(directory, { recursive: true })
        writeFileSync(join(directory, 'package.json'), '{"version":"1.68.0","main":"index.cjs"}')
        writeFileSync(join(directory, 'index.cjs'), '// synthetic nested shadow')
      } else {
        env[fault] = 'forbidden'
      }
      assert.throws(() => dependencyRequire(f.url, env), /RSEE/)
    } finally { rmSync(f.base, { recursive: true }) }
  })
}

test('legacy resolver remains source anchored', () => {
  const f = fixture()
  try {
    assert.throws(() => dependencyRequire(f.url, {}).resolve('mineflayer'), /Cannot find module/)
  } finally { rmSync(f.base, { recursive: true }) }
})
