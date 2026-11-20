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

## E1 incremental implementation — bounded native terrain (offline only)

A new **opt-in** `sense_terrain` command uses the original Mineflayer process
stdin/stdout and the same sequence-validated `MineflayerStreamDecoder`.
No automatically running scanner, second socket, camera `LOOK`, physical
effect or new receive-stream owner is created. Normal native observation
messages are unchanged.

- `adapters/mineflayer/sense_terrain.mjs` synchronously reads an
  intentionally small **5×5×4 = 100-cell** region around the *client-side*
  Self position using `bot.blockAt(..., false)`. The sensor sends each cell's
  block name and Prismarine BlockState collision boxes translated to world
  coordinates, or **null/UNKNOWN** if the block is unloaded, malformed or
  cannot be read. Empty shape array is only known empty when the block
  observation itself is valid. Local shape overhangs (e.g., fence height
  1.5) are retained within a bounded [-1,2] local range rather than dropped.
- The observation carries current native position, optional pose/dimension,
  native monotonic sample clock, known-count and complete flag. Body AABB is
  UNKNOWN: entity width/height do not establish a pose-specific physical
  hitbox. Local Node monotonic time is not Paper time.
- `protocol.mjs`, `bridge.mjs`, `python_protocol.py` and
  `process_session.py` add one exact request/response pair; the
  coordinated original final-stdin admission explicitly permits this
  read-only command. Physical `effect` admission is unchanged.
- `sense_projection.py` exposes a bounded `SenseTerrainMoveInput` to
  original L0 MOVE and source-qualified `LensClaim` for SelfWorld.
  A conservative <=1m level swept-envelope helper may return
  `POTENTIAL_COLLISION` (advisory), but the route remains **UNKNOWN** and
  no motor action, STOP, retarget, pathfinding, clearance, or Memory mutation
  is performed. A complete client-side snapshot alone NEVER proves safe
  passage; dynamics, support, Paper equality, control and actual collision
  still require their original Owner validation.
- Standalone Node and Python synthetic tests verify valid blocks, unloaded
  cells, malformed shapes, fence overhang, incomplete AABB, source request,
  duplicate/stale sequence, false CLEAR refusal, and SelfWorld UNKNOWN.

**Not yet done:** an actual event-loop consumer / recurring SENSE L0 cycle,
original certified World/Paper UUID-generation/currentness readback,
full physics/pose source correlation, original L0 MOVE native STOP integration,
original durable Log adoption, Real-World/Gemma DEV, independent outcome audit
or any QUAL/SCIENCE claim. E1 is a read-only **transport and projection
candidate**, not an A Stage27l preflight qualification.

**Current classification:** E1_OFFLINE_IMPLEMENTATION_UNVERIFIED /
NATIVE_TERRAIN_READONLY_ADAPTER / ROUTE_CLEARANCE_UNKNOWN /
SELFWORLD_REFERENCE_ONLY / REAL_WORLD_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN.

### E2a-1 receiver prototype (HOLD)

`MineflayerProcessSession.start_dispatcher` is an opt-in, single stdout
reader with a bounded ordered owner queue. A full queue applies backpressure;
no action/audit message is discarded. The existing decoder and raw source
transcript remain on the read path. Concurrent calls to `receive` are refused.
Observer exceptions are exposed through `observer_error` and do not remove
messages from the owner queue.

This is a prototype, not an operational SENSE integration. It is not enabled
by the resident owner, does not validate owner identity, world generation,
login/retirement or checkpoint restore, and does not invoke the SENSE
converters. In particular, if the owner does not drain its queue, reception
and observation stop at the queue bound. Thus continuous perception during
L1/L2 and request/ACK coexistence have not been demonstrated. Do not enable
this prototype as a production perception path. SelfWorld and L0 MOVE remain
unconnected. No real World qualification is implied.
# Resident owner dispatcher (E2a-3A)

`OwnedResidentPhysicalBridge(enable_sense=True)` starts the existing session
dispatcher only after its original spawn/probe, World epoch, WAL and owner
login checks succeed. The ordered bounded queue remains the sole source for
the original `receive()` callers, including correlated probes and effect
results. Passive observations additionally replace one in-memory SENSE frame;
probes and effect results do not update that frame. The Paper session and Self
scope come from the verified login, not from the callback. Access is fenced by
the current owner/session/World state and logout or quarantine clears the frame.
This does not authenticate a Paper World UUID or establish freshness by time.

The E2a-3A owner queue was loss-preserving and stopped native reading when full.
The E2a-3B change below introduces limited passive aggregation. The latest frame is bounded, is not persistent
Memory or a consumer integration, and does not establish a physical body AABB
or route clearance. Rejoin/restore paths outside this opt-in resident login
have not been integrated or qualified.

## E2a-3B bounded dispatch (CPU/offline)

The opt-in resident dispatcher keeps one native reader and the original strict
sequence decoder and raw source audit. Its 256-entry owner queue may replace
only the trailing uncorrelated `move` or `entities` snapshot when full, while
the shared physical admission has no active lease and is open. Other messages
retain their original order. Before a physical effect is sent, and permanently
thereafter for that native session, all messages are preserved; encountering an
active lease or closed admission at a compaction boundary also permanently
disables compaction. This conservative boundary includes STOP and settling; it
does not attempt to infer when Action evidence is no longer needed.

`passive_aggregation` is a bounded cumulative summary: source session, first
and last replaced sequence, latest retained sequence, number replaced, and
local monotonic receipt times. The sequence bounds need not be contiguous and
cannot reconstruct the discarded events. The native protocol supplies no
observation timestamp; receipt time is not World time. The full raw stream is
preserved only when the existing raw source audit is enabled. SENSE retains one
latest frame. A callback failure or dispatcher failure invalidates current
SENSE. Queue saturation on a non-compactable message sets `backpressure_hold`
while the one reader waits; the pending decoded message is retained. Sustained
lossless operation beyond that boundary is not claimed. Native pipe and child
buffers are outside the Python queue bound.

The offline integration exercises 1,000 rapid passive events with 256 owner
slots, 744 replacements, a correlated probe and STOP ACK. This is a finite
synthetic stream, not a duration, CPU utilization or real World qualification.
