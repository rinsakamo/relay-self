import { createHash } from 'node:crypto'
import { readFileSync, realpathSync } from 'node:fs'
import { createRequire } from 'node:module'
import { isAbsolute, join, dirname, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

// Explicit RSEE opt-in; preserve source-owned bridge and legacy resolution.
export function dependencyRequire (sourceUrl, env = process.env) {
  const root = env.RELAYSELF_RSEE_NODE_RUNTIME_ROOT
  let require = createRequire(sourceUrl)
  if (root) {
    if (env.NODE_PATH || env.NODE_OPTIONS || !isAbsolute(root) ||
        realpathSync(root) !== root || realpathSync(join(root, 'node_modules')) !== join(root, 'node_modules')) {
      throw new Error('physical external RSEE runtime without overrides required')
    }
    const adapter = dirname(fileURLToPath(sourceUrl))
    if (root === adapter || root.startsWith(adapter + sep) || adapter.startsWith(root + sep)) {
      throw new Error('RSEE dependency root must be external to source')
    }
    for (const name of ['package.json', 'package-lock.json']) {
      const external = join(root, name)
      const source = join(adapter, name)
      const hash = path => createHash('sha256').update(readFileSync(path)).digest('hex')
      if (realpathSync(external) !== external || realpathSync(source) !== source ||
          hash(external) !== hash(source) ||
          hash(source) !== (name === 'package.json'
            ? '8fc9d7868b38843e1741909e999d6c1d1b70c257fe04c55d8c841694e30ded2d'
            : '545e32a148b1f3649ba199dac9383fca72d0aaae17afbe740dc26163491ae568')) throw new Error('RSEE source manifest mismatch')
    }
    require = createRequire(join(root, 'package.json'))
    const lock = require('./package-lock.json').packages
    const mf = require.resolve('mineflayer')
    const protocolRequire = createRequire(mf)
    for (const [name, loader] of [['mineflayer', require], ['minecraft-protocol', protocolRequire]]) {
      for (const target of [name, name + '/package.json']) {
        const entry = loader.resolve(target)
        if (realpathSync(entry) !== entry || !entry.startsWith(root + sep)) {
          throw new Error('RSEE module realpath escape')
        }
      }
      if (loader.resolve(name + '/package.json') !== join(root, 'node_modules', name, 'package.json')) {
        throw new Error('RSEE transitive module substituted by nested dependency')
      }
      if (loader(name + '/package.json').version !== lock['node_modules/' + name].version) {
        throw new Error('RSEE installed version differs from lock')
      }
    }
  }
  return require
}
