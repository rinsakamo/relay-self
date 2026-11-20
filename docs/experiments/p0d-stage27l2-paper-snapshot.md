# Stage27l-2: bounded Paper snapshot (offline, incomplete)

Status: OFFLINE DEV PARTIAL / SOURCE QUALIFICATION UNKNOWN / NO MOVE AUTHORITY.
Based on #1051. All tests in this change use invented data. No real World snapshot,
World trial, restart, physical MOVE, Gemma, memory write, or qualification occurred.

`WorldSnapshot` polls a separate local spool, one request per tick, and captures on
Paper's main thread. Put a canonical UUID-named `<id>.request` in
`plugins/P0BRecorder/p0d-snapshots/requests/` containing Java properties:
`request_id`, `world_uuid`, `player_uuid`, `target_x`, `target_z`. The request is
consumed once into `handled/`; successful JSON is atomically renamed into `output/`.
An absent result is UNKNOWN. Snapshot boot ID identifies the plugin instance and
is not the existing TickWitness boot ID; establish an independent process binding
before relying on it. Request data and local spool are not authentication.

Capture records world UUID/key/environment, plugin boot, request, timestamp,
start/end tick, integer exclusive bounds, online player UUID, position, pose,
AABB, ground/sneak/sprint/flying and yaw/pitch; per-cell loaded flag, block data,
read status and collision boxes; and nearby entity UUID/type/valid/dead/AABB.
The swept body range has one-block horizontal and vertical margin (two below),
maximum 1024 cells, 4096 boxes, 128 entities and 5.01m horizontal displacement.
Unloaded chunks are not explicitly loaded. Read errors and limits mark terrain
incomplete. No action API is called. Neighbor queries inside Paper collision-shape
calculation have not been proven not to load neighboring chunks: a real deployment
requires further investigation and instrumentation. API search restrictions prevent
proving nearby-entity completeness; `entity_coverage_complete` is always false.

Paper 1.21.8 [Block API](https://jd.papermc.io/paper/1.21.8/org/bukkit/block/Block.html)
and [VoxelShape API](https://jd.papermc.io/paper/1.21.8/org/bukkit/util/VoxelShape.html)
provide multiple exact boxes, unlike approximate Block bounding boxes. In the
[1.21.8 CraftBlock implementation](https://github.com/PaperMC/Paper/blob/ver/1.21.8/paper-server/src/main/java/org/bukkit/craftbukkit/block/CraftBlock.java),
`getCollisionShape` wraps the local NMS shape without translating; the provider
adds block x/y/z to each box. Entity `getBoundingBox` is captured directly.
Verify local-to-world conversion against actual Paper in a later read-only trial.
Some shapes extend outside their block and Stage27k rejects them as UNKNOWN.

`stage27l2_snapshot_adapter.inspect_snapshot` validates bounded terrain and body,
then invokes the unchanged Stage27k fixture checker as an **unqualified diagnostic**.
The top-level result is always UNKNOWN: no trusted live generation, link from the
Original Owner's live native connection through Paper JOIN to player UUID, trusted
process/request binding, replay fence, time correlation, or complete dynamic
occupancy has been implemented. Session labels and a checkpoint generation do not
prove those properties. A geometry CLEAR is not PASS; diagnostic BLOCKED is not a
source-qualified BLOCKED. This is not connected to the action path or E Lane.

Next: establish owned process and native transcript/join connection provenance;
independently bind plugin boot to the owned process, current live world generation,
nonce, sequence, clock and replay state; prove Paper entity coverage and no chunk
loads, including collision-shape neighbor access; implement source qualification
and dynamic collision checks; cover full adversarial matrix and mock Paper capture.
Then review an independently qualified read-only trial on an appropriately
instrumented world with no action: inspect bounded loaded chunks, collect one
main-thread snapshot and native source originals, verify box coordinates and all
qualification fences, preserve UNKNOWN for missing proof. This change by itself
does not qualify that trial or a future 5m MOVE.
