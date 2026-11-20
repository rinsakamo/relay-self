# E Lane — SENSE v0.1, minimal read-only fanout (offline DEV)

## Scope and baseline

Stacked from A Lane [Stage27l PR #1051](https://github.com/rinsakamo/relay-self/pull/1051)
at `a3d0adfab69200e11236388e4428136fd93565d4`. It does **not**
change A's Stage27l intake, original ActionPort, Stage27k operator geometry
checker, Physical WAL, Mineflayer protocol, B/C/D owners, or the runtime.

SENSE is the **CPU-side perception fanout** of already received native
observations. It is *not* the physical `LOOK` Action. The same immutable
`MineflayerObservation` becomes (1) a cheap L0 MOVE input and (2)
source-referenced SelfWorld lens claims. No separate World truth, Memory
writer, Action issuer, new Owner, GPU requirement or invented BlockState
is introduced.

This is the minimal seam for future **local** wiring, not an end-to-end
running L0 SENSE loop or real-world collision avoidance proof.

## Implemented contract

- `sense_from_native`: owner-supplied native `spawn/respawn/move/forcedMove/entities/probe`
  event; check typed source, expected native session, strict sequence advance,
  and exact request ID on `probe`. Caller must already own the receive
  stream and authenticate its original World/Self mapping.
- `sense_for_l0_move`: expose the same native position and bounded nearby
  entity observations without waiting for any L1/L2, Memory flush or
  world-model build. The route status is **UNKNOWN**: the current native
  probe has no BlockState/collision shapes, full chunk coverage or measured
  AABB. No auto-move, no fake CLEAR, no implicit STOP or retarget.
- `sense_for_self_world`: produce `LensClaim` references for
  `three_self_present.Lens.SELF_WORLD` with native source/revision and
  `EpistemicStatus.OBSERVED` for actually present position and entity
  facts. Terrain collision remains explicitly UNKNOWN; missing entity
  records do not prove absence. Caller uses existing `LensView` /
  `project_three_self` with exact source revision.
- All paths are read-only, immutable, finite and CPU-only. No automatic
  Log/Structured Memory adoption. A later original Log owner can retain
  the underlying Percept with the same source refs.

## Authority and known gaps

The World UUID, generation, Paper tick, native/Paper atomicity, loaded chunk
scope, live collision shapes, body AABB and grounded state are **not**
supplied by these events. Caller-supplied `ScopeRef` and sequence
checks are not independent Owner authentication. The original L0 MOVE
executor is not yet a consumer of this seam, and ordinary L1/L2 current
context must still pass through the existing Perceptual Schema /
`CurrentSchemaFrame` contract, not inject SelfWorld raw data directly.

Moving beyond this slice needs:

1. An explicitly owned, bounded **read-only native terrain/shape sensor**
   with measured body geometry and complete coverage/freshness metadata.
2. The original Self/World Owner binding and stale rejection for both
   geometry and SENSE, plus actual live L0 MOVE consumer integration.
3. SENSE event-loop admission, backpressure and Log observation policy,
   then normal Schema → L1/L2 summaries.
4. One fresh isolated real Paper/Mineflayer DEV test proving pre-MOVE
   detection/STOP and observing actual physical effect, keeping WAL
   and qualification boundaries intact.

## Safety cases (offline)

Wrong native session/request, duplicate/stale sequence, foreign or absent
native event, unsupported kind, missing World session, stale SelfWorld
source revision and absent terrain are refused or UNKNOWN. Only current
native observation records become OBSERVED; passive absence is not safety.

**Classification:** SENSE_MINIMAL_OFFLINE_SEAM_ONLY / L0_MOVE_CLEARANCE_UNKNOWN /
SELF_WORLD_LENS_OFFLINE / NO_REAL_WORLD / NO_GEMMA / QUAL_NO_GO / SCIENCE_NOT_RUN.
