// RelaySelf S49 DEV_ONLY: strictly bounded normalization of a mis-labelled
// Minecraft 1.21.8 speed attribute into prismarine-physics's expected key.
//
// Pinned Mineflayer 4.39.0 packet reports player movement speed (base 0.1,
// minecraft:sprinting +0.3 and Paper's relays49dashdev:forward_dash_only +0.5)
// under "generic.scale". prismarine-physics 1.11.1 expects
// "minecraft:movement_speed"; passing original sprinting modifier as well as
// client-side sprinting would double apply +30%.
//
// This function cannot issue any commands and rejects all unrecognized
// modifiers, non-native shapes, and values. The caller additionally gates
// this on the already-issued original S49 forward+sprint Action and 1.21.8.
export function projectS49DevMovementSpeed (source) {
  if (!source || typeof source !== 'object' || Array.isArray(source) ||
      typeof source.value !== 'number' || !Number.isFinite(source.value) ||
      Math.abs(source.value - 0.1) > 1e-5 ||
      !Array.isArray(source.modifiers) || source.modifiers.length > 2) {
    return null
  }
  let sprint = false
  let dash = false
  for (const mod of source.modifiers) {
    if (!mod || typeof mod !== 'object' || Array.isArray(mod) ||
        typeof mod.uuid !== 'string' || typeof mod.amount !== 'number' ||
        !Number.isFinite(mod.amount) || !Number.isInteger(mod.operation)) {
      return null
    }
    if (mod.uuid === 'minecraft:sprinting') {
      if (sprint || mod.operation !== 2 ||
          Math.abs(mod.amount - 0.3) > 1e-5) return null
      sprint = true
    } else if (mod.uuid === 'relays49dashdev:forward_dash_only') {
      if (dash || mod.operation !== 2 ||
          mod.amount < 0.01 || mod.amount > 0.5) return null
      dash = true
    } else {
      return null
    }
  }
  if (!sprint || (dash && source.modifiers.length !== 2)) return null
  return {
    attribute: {
      value: source.value,
      // prismarine-physics adds its own sprinting +30% from the issued
      // sprint control. Keep ONLY the genuine Paper bonus +50%.
      modifiers: dash
        ? [{ uuid: 'relays49dashdev:forward_dash_only',
            amount: source.modifiers.find(m =>
              m.uuid === 'relays49dashdev:forward_dash_only').amount,
            operation: 2 }]
        : []
    },
    dash: dash,
    sourceName: 'generic.scale',
    targetName: 'minecraft:movement_speed',
    nativeSprintCount: 1
  }
}
