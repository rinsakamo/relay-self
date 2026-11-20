/** E Lane SENSE E1: bounded, read-only local terrain from Mineflayer.
 * No movement, chunk loading, pathfinding, Paper authority, or World truth.
 */
export const SENSE_RADIUS = 2
export const SENSE_DY_MIN = -1
export const SENSE_DY_MAX = 2
export const SENSE_EXPECTED_CELLS =
  (2 * SENSE_RADIUS + 1) ** 2 * (SENSE_DY_MAX - SENSE_DY_MIN + 1)

const finite = (v) => typeof v === 'number' && Number.isFinite(v)

function localShapes (block) {
  if (!block || typeof block.name !== 'string' || !block.name ||
      !Array.isArray(block.shapes) || block.shapes.length > 16) return null
  const result = []
  for (const shape of block.shapes) {
    if (!Array.isArray(shape) || shape.length !== 6 ||
        !shape.every(finite) ||
        !(0 <= shape[0] && shape[0] < shape[3] && shape[3] <= 1) ||
        !(0 <= shape[1] && shape[1] < shape[4] && shape[4] <= 1) ||
        !(0 <= shape[2] && shape[2] < shape[5] && shape[5] <= 1)) return null
    result.push(shape)
  }
  return result
}

function bodyAabb (entity, position) {
  const width = entity.width
  const height = entity.height
  if (!finite(width) || !finite(height) ||
      width <= 0 || width > 4 || height <= 0 || height > 4) return null
  const half = width / 2
  return [
    position.x - half, position.y, position.z - half,
    position.x + half, position.y + height, position.z + half
  ]
}

export function captureSenseTerrain (bot) {
  if (!bot || !bot.entity || !bot.entity.position ||
      typeof bot.entity.position.floored !== 'function' ||
      typeof bot.blockAt !== 'function') {
    throw new Error('SENSE requires a live entity and read-only blockAt')
  }
  const position = bot.entity.position
  if (![position.x, position.y, position.z].every(finite)) {
    throw new Error('SENSE position unavailable')
  }
  const center = position.floored()
  const origin = { x: position.x, y: position.y, z: position.z }
  const aabb = bodyAabb(bot.entity, position)
  const cells = []
  let known = 0
  for (let dx = -SENSE_RADIUS; dx <= SENSE_RADIUS; dx++) {
    for (let dz = -SENSE_RADIUS; dz <= SENSE_RADIUS; dz++) {
      for (let dy = SENSE_DY_MIN; dy <= SENSE_DY_MAX; dy++) {
        const x = center.x + dx
        const y = center.y + dy
        const z = center.z + dz
        let block = null
        try {
          // false = do not request sign/block-entity extra information.
          block = bot.blockAt(center.offset(dx, dy, dz), false)
        } catch {
          // Sensor read failure is explicitly UNKNOWN, never empty air.
        }
        const shapes = localShapes(block)
        const isKnown = shapes !== null
        if (isKnown) known += 1
        cells.push({
          position: [x, y, z],
          name: isKnown ? block.name : null,
          shapes: isKnown
            ? shapes.map(s => [
              s[0] + x, s[1] + y, s[2] + z,
              s[3] + x, s[4] + y, s[5] + z
            ])
            : null
        })
      }
    }
  }
  return {
    source_scope: 'mineflayer_loaded_blocks',
    sample_monotonic_ns: process.hrtime.bigint().toString(),
    position: origin,
    dimension: typeof bot.game?.dimension === 'string' ? bot.game.dimension : null,
    body_pose: typeof bot.entity.pose === 'string' ? bot.entity.pose : null,
    body_aabb: aabb,
    radius: SENSE_RADIUS,
    dy_min: SENSE_DY_MIN,
    dy_max: SENSE_DY_MAX,
    expected_cells: SENSE_EXPECTED_CELLS,
    known_cells: known,
    complete: known === SENSE_EXPECTED_CELLS,
    cells
  }
}
