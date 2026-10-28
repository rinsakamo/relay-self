# RelaySelf S49 — Native 7×6×3 local voxel Present to L1 waypoint choice

**2026-10-28 JST | DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

## Motivation

Earlier RelaySelf S49 experiments established actual native Mineflayer/S16 XZ Goal following, a real wall-induced `UNKNOWN` terminal and safe stop, fixed L1-waypoint execution, PersistentCognition/REMEMBERED route reuse, and a six-column cached-block observer that could choose between two incompatible experienced detours. The six-column probe could not express nearby floor support, head clearance, other cells or route coverage.

This isolated DEV step replaces that read-side demonstration with a bounded **7 XZ cells horizontally × 6 Z cells forward × 3 Y layers = 126 native cached block checks**. The original Mineflayer client remains the sole native block-cache owner and sender of authoritative JSONL source packets. No second native reader, no second Action issuer, no change to the default product observation path.

## Read-side source contract

New DEV-only command: `observe_local_voxels_dev` under `S49_L1_VOXEL_DEV_ONLY=1`. It requires an explicit unique correlated `request_id`, finite initial XZ and a spawned Mineflayer avatar within 6m of the supplied origin. The original bridge uses `bot.blockAt` with `false` for client-side unloaded blocks, not any Minecraft server-console stimulus as a sensor.

The response is a distinct typed `local_voxels_dev` packet with exactly **42 XZ columns**, sorted by `dz=0..5` then `dx=-3..3`, three statuses per column: `feet`, `head`, `floor`. Each cell reports `CLEAR` for observed air, `BLOCKED` for observed non-air block, `UNKNOWN` for missing/unloaded cached data. The floor must be **BLOCKED** to count as supported ground; `CLEAR` floor is unsupported and therefore not a walking corridor. The exact response shape, cell count/order, session, seq, request id, origin, coverage `mineflayer_loaded_cache_fixed_7x6x3` and `unknown_is_not_clear=true` are checked before selection.

A typed `NativeVoxelPresentDev` provides observer-local `WorldReading(origin=OBSERVED)` per actual column, with exact session/seq/request ID and source provenance. It is deliberately a **DEV SelfWorld read-side extension**, not a mutation of the frozen existing `WorldObservation` entity schema, and it does not persist or assert entire-world geometry.

## Conservative L1 local waypoint selection

Upon a genuinely new original S49 blocked S16 (`UNDETERMINED`, original Action terminal `UNKNOWN` and native CLEAR ACK), the L1 DEV selector evaluates two candidate three-segment waypoint templates: lateral **±2.5m at +1.1m forward**, straight on that side to **+3.8m**, then return to the unchanged original goal at **(0,+4.0m)** relative to the current world's initial XZ. The two route templates are bounded engineering candidates, **not learned or general pathfinding**. The side choice is derived from fresh observed voxel columns, not from operator left/right preference.

Each 3D floor/head/body column along both candidate XZ centre-line segments is visited with horizontal samples at no more than ~0.15m intervals. Any observed solid feet/head or observed missing floor support rejects that segment as BLOCKED; unknown native cells are UNKNOWN and never pass. The planner returns `SELECTED / NATIVE_VOXEL_TEMPLATE_SELECTED` only when **one candidate is entirely CLEAR with observed solid floor support, and the alternate candidate is actually BLOCKED**. Both CLEAR, both BLOCKED, or any ambiguous UNKNOWN yields `DEFER / VOXEL_ROUTE_AMBIGUOUS_OR_UNKNOWN` with no further Action. Point-centre sampling does not prove full player-body collision envelope clearance or safety between future observations.

The selected `L1DetourPlanDev` retains the original Goal ID, session and intent, original blocked S16 Action/seq, controlled new waypoint IDs and original final target. The existing original S49 supervisor alone issues the real S15 LOOK, MOVE, CLEAR and S16 consequence for each stage. Stable native WAIT_VERIFY→REACHED and actual XZ endpoint are required, and an old `UNKNOWN` Action is never retried. No real provider/LLM calls, learned L1 policy, dynamic L2 planner, autonomous novelty search or in-flight hazard interrupt during every waypoint stage is claimed.

## Verified original Minecraft DEV — three independent World sessions

[GitHub Actions #40687298563](https://github.com/rinsakamo/relay-self/actions/runs/40687298563) **completed / SUCCESS**, exact tested code HEAD `501d67b6797562f6ca0f8982a9209336c1af82a9`. Python 3.12 focused **47 PASS**, Ruff PASS, Node22 syntax PASS; actual official Minecraft 1.21.8 with Java21 and original Mineflayer 4.39.0, independent World sessions, clean original Node/server exits and no model calls.

| Environment | Original native session | Physically observed candidate | L1 result | Original native route Actions | Final original L2 XZ error / tolerance |
|---|---|---|---|---:|---:|
| LEFT_BLOCKED, original front wall + operator left-side stone stimulus | `ce72f4c7-a294-4878-a7f9-ca8a5dbbc4e8` | LEFT=BLOCKED, RIGHT=CLEAR | RIGHT / REACHED | 9 | **0.07302715578376677m / 0.3416037456401915m** |
| RIGHT_BLOCKED, original front wall + operator right-side stone stimulus | `89ed03b5-d389-4123-996f-d339e0c1298e` | LEFT=CLEAR, RIGHT=BLOCKED | LEFT / REACHED | 9 | **0.19273136140666056m / 0.35837742890123137m** |
| BOTH_OPEN, original front wall only | `73aa0457-c0d5-44ee-85c3-0d78a504ba59` | LEFT=CLEAR, RIGHT=CLEAR | **DEFER** | **0 after original blocked S16** | no false REACHED |

The first original forward Action in each World executed, and the next closed as S16 `UNDETERMINED` / Action `UNKNOWN` with an actual control-clear ACK at the front wall. Only after that does a **fresh correlated native voxel response** become the L1 decision source. In LEFT_BLOCKED and RIGHT_BLOCKED, original S49 S15/S16 carried all 9 unique waypoint Actions with native position and ACK sources, and stable reaching of the unchanged parent L2 Goal. The independent source reviewer reproduced all three choices from the saved native voxel column packets and checked physical terminal/position facts.

Reviewer: `S49_L1_LOCAL_VOXEL_THREE_WORLD_DEV_PASS`, classification `S49_L1_REAL_VOXEL_LOCAL_WAYPOINT_DEV`. **No new native packet readers or Action issuers**, no QUAL or SCIENCE.

[Original three-World real source logs, voxel packets and reviewer JSON](https://github.com/rinsakamo/relay-self/actions/runs/40687298563/artifacts/12816325050), artifact ID **12816325050**, ZIP SHA256 **50365e8e16ae0f43006f6accabbc34e8a37b9d18dc71b9d36e787a5b8144f1ac** (seven-day retention).

Two earlier pre-final workflow attempts had safe FAILs: #40687024044 stopped before World at Ruff import sorting; #40687142669 stopped before World due the original six-column left-side DEV gate not recognizing the *distinct* new voxel probe authority. The latter was corrected while retaining the old six-column gate; #40687298563 executed all three actual Worlds and passed at its exact HEAD. Preserve failures as failures.

## Changes

- `adapters/mineflayer/bridge.mjs`, `protocol.mjs`: new opt-in read-only native 42-column local voxel probe; unchanged normal probe/motor commands.
- `adapters/mineflayer/python_protocol.py`, `process_session.py`: strict original-session typed message and bounded source request.
- `src/relay_self/goal_local_voxel_dev.py`: observer-local 3-height Present, source-provenance binding, conservative local three-waypoint candidate evaluation; `DEFER` on missing or ambiguous coverage.
- `adapters/mineflayer/s49_goal_loop_real_dev.py`: native voxel packet after original blocked S16, explicit DEMO physical left/right stimuli, same owner waypoint execution and no-waypoint DEFER.
- `adapters/mineflayer/s49_l1_local_voxel_review_dev.py`: independent three-World source/terminal/Goal audit.
- `tests/test_s49_l1_local_voxel_dev.py`, `.github/workflows/self-l1-local-voxel-dev.yml`: 47 focused tests including wrong session, altered origin, stale seq, unsupported floors, unknown partial cache, malformed/reordered cell coverage; plus all physical scenarios.

## Limits and next DEV direction

This is still a **small bounded geometry and two fixed three-segment templates**. The voxel grid is an observed partial near-term representation, not a persistent full World map or a guarantee of physical passage, and no moving obstacle/different height stair or jump behavior is established. Only the two asymmetric obstacle Worlds and a both-clear DEFER World are physically observed. UNKNOWN, unloaded cells, missing floor, and malformed packet negatives are unit-tested offline; no separate physically-unloaded-chunk World yet.

Next: integrate a generic *bounded waypoint search* over this same source-tracked grid (with conservative body footprint and no diagonal corner-cutting), then compare its generated path against this bounded template baseline. Test a genuinely different obstacle configuration in a fresh real Minecraft World without changing original S49 Action ownership, and separately combine L0 in-flight danger preemption with multi-waypoint movement. Avoid converting speculative geometry to observed facts.

**Isolated DEV branch only:** `self/dev-l1-local-voxel-waypoints-20261028`. No edits to `main`, protected Draft PR #545/#634, frozen S18/historical source evidence; QUAL_NO_GO, SCIENCE_NOT_RUN.
