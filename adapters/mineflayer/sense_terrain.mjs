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
        !(-1 <= shape[0] && shape[0] < shape[3] && shape[3] <= 2) ||
        !(-1 <= shape[1] && shape[1] < shape[4] && shape[4] <= 2) ||
        !(-1 <= shape[2] && shape[2] < shape[5] && shape[5] <= 2)) return null
    result.push(shape)
  }
  return result
}

export function captureSenseTerrain (bot) {
  if (!bot || !bot.entity || !bot.entity.position ||
      typeof bot.entity.position.floored !== 'function' ||
      typeof bot.blockAt !== 'function') {
    throw new Error('SENSE requires a live entity and read-only blockAt')
  }
  // Sample one synchronous Node turn. A changing entity/pose/dimension makes
  // the entire readout UNKNOWN; a hybrid of two body generations is not SENSE.
  const entity = bot.entity
  const position = entity.position
  const startPose = entity.pose
  const startDimension = bot.game?.dimension
  if (![position.x, position.y, position.z].every(finite)) {
    throw new Error('SENSE position unavailable')
  }
  const center = position.floored()
  const origin = { x: position.x, y: position.y, z: position.z }
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
  const atEnd = bot.entity?.position
  const stable = bot.entity === entity &&
    atEnd && [atEnd.x, atEnd.y, atEnd.z].every(finite) &&
    atEnd.x === origin.x && atEnd.y === origin.y && atEnd.z === origin.z &&
    bot.entity.pose === startPose && bot.game?.dimension === startDimension
  // Never publish a partial cross-pose, cross-position or cross-world sample
  // as observed blocks. A synchronous scan is still NOT Paper tick authority.
  const qualifiedCells = stable
    ? cells
    : cells.map(cell => ({ position: cell.position, name: null, shapes: null }))
  return {
    source_scope: 'mineflayer_loaded_blocks',
    sample_monotonic_ns: process.hrtime.bigint().toString(),
    position: origin,
    dimension: stable && typeof startDimension === 'string' ? startDimension : null,
    body_pose: stable && typeof startPose === 'string' ? startPose : null,
    // Entity dimensions do not attest the pose-specific physical hitbox.
    // Mineflayer does not expose a source-qualified server AABB here.
    body_aabb: null,
    radius: SENSE_RADIUS,
    dy_min: SENSE_DY_MIN,
    dy_max: SENSE_DY_MAX,
    expected_cells: SENSE_EXPECTED_CELLS,
    known_cells: stable ? known : 0,
    complete: stable && known === SENSE_EXPECTED_CELLS,
    cells: qualifiedCells
  }
}
