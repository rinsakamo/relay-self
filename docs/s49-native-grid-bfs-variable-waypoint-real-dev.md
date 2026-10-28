# RelaySelf S49 — native local-grid route search and variable L1 waypoint execution (DEV)

**2026-10-28 JST | DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

## Objective

Move from L1 deciding between two predeclared three-waypoint detours to **deriving a bounded waypoint sequence from actual native client-cache voxel occupancy**. The old S49 ActionSupervisor remains the *sole* Action owner; every waypoint is executed through the inherited S15 LOOK + MOVE + CLEAR, original S16 native observation and settling check. Do not represent this as live L2 planning, general navigation, policy learning, production safety certification, or a completed in-flight hazard-preemption integration.

## Native observation source and body bounds

A new opt-in DEV path `S49_L1_GRID_SEARCH_DEV_ONLY=1` consumes the earlier `observe_local_voxels_dev` command, requiring `S49_L1_VOXEL_DEV_ONLY=1`, through the **same original Mineflayer process writer and packet receiver**. The native observation is a strict `7 XZ × 6 Z × 3 vertical = 126 block check` cache snapshot. Only loaded client chunks may report `CLEAR` or `BLOCKED`; a missing/unloaded block remains `UNKNOWN`. In addition to current foot Y, the packet now carries native live player X and Z so the route starts from the actual World position after an original S49 physical wall `UNKNOWN`, not from an invented start cell.

Floor support is positively required: the native bridge tests the loaded block's full-block collision status (`boundingBox === 'block'`) for the floor layer, so water, vegetation and air cannot be treated as supported floor. An occupied feet/head cell, unsupported ground or unknown cache is never passable. The origin must be aligned to the observed Minecraft cell-center basis (within 0.03m). The physically stopped original player must be within 0.65m X and 0–1.8m Z of the initial goal basis and within 0.45m of the chosen nearest cell center, otherwise no route is admitted.

**Coverage/safety limit:** The current implementation reasons about a 0.30m avatar XZ radius at cell centers with ~0.20m margin to a block boundary. Movement edges use only **cardinal 4-neighbour moves**, no diagonal edges or corner-cutting. This establishes a bounded grid-geometry check for flat, loaded World cells; it is NOT a full continuous swept-volume collision certificate for actual physics between turn waypoints, nor a vertical mobility/jump/stair or dynamic-object planner.

## L1 local search

Pure DEV `choose_grid_route_dev()` performs deterministic bounded BFS over the 42 XZ cells; each candidate requires observed feet and head `CLEAR` and floor `BLOCKED`. The native source packet carries a fresh session, sequence, request ID and actual player pose, newer than the **original physically closed S16 wall Action UNKNOWN**. The destination remains the immutable original L2 XZ Goal, +4m forward relative to start. The BFS reconstructs the entire cardinal cell path, compresses collinear edges to **1–12 turns/waypoints**, and binds the resulting immutable `L1GridRoutePlanDev` to the blocked Action and native source voxel sequence. No reachability graph beyond the 42 observed cells or synthetic voxel clearing is permitted.

When a route is found, its variable waypoint sequence is admitted with a dedicated DEV gate through the **existing** `S49GoalExecutorDev.adopt_waypoint_dev()`, preserving each stage's Action ID, original intent and native S16 terminal evidence. Previous `UNKNOWN` Action IDs are never retried. Waypoint errors are controlled with each new stage's observed L0 pose and L1-derived tolerance; stable REACHED requires settling observations. When no certified grid path exists, return `DEFER / NO_OBSERVED_BODY_SAFE_GRID_ROUTE`, with zero physical Actions after the initial blocked wall outcome. Unknown grid cells and unobserved floor do not become passable.

The earlier `L1DetourPlanDev` remains a strict three-waypoint explicit-operator plan and retains `obstacle_block_perception_attested=false`. Only the separate source-attested native-grid plan sets this report flag to true, and only for its bounded observations. There are no changes to the old default Action owner, protected evidence, `main`, Draft PR #545/#634 or QUAL/SCIENCE.

## Actual native Minecraft 1.21.8 qualification — DEV only

[GitHub Actions run #40689496365](https://github.com/rinsakamo/relay-self/actions/runs/40689496365): **completed/SUCCESS**, exact tested code HEAD `495573be59019993cd79223f87e1cfeaffd7ae82`. Python3.12 focused **48 PASS**, Ruff PASS, Node22 syntax PASS, Java21 official vanilla Mojang Minecraft1.21.8 + original Mineflayer and all original Node/server cleanup exit0. Three **independent freshly started Minecraft Worlds**, no real model calls:

| World stimulus | Original session | Actual native BFS cell path (dx,dz from World start) | L1 generated stage count | Original native movement Action count | Native final error/tolerance |
|---|---|---|---:|---:|---|
| LEFT_BLOCKED: existing front wall + left side obstacle | `407b59f8-2608-4a19-bcf1-1e6dd50edba7` | (0,1)→(1,1)→(2,1)→(2,2)→(2,3)→(2,4)→(1,4)→(0,4) | 3 | 9 | **0.060986272185231734m / 0.30m** |
| RIGHT_BLOCKED: existing front wall + right side obstacle | `8635f34d-69a3-4abd-8578-37884804361a` | (0,1)→(-1,1)→(-2,1)→(-2,2)→(-2,3)→(-1,3)→(0,3)→(0,4) | 4 | 10 | **0.08683623380353299m / 0.30m** |
| BOTH_BLOCKED: existing front wall + both side obstacles | `3fb372ed-5a12-406c-85b0-228ab1811c0f` | no observed path | none / DEFER | **0 after blocked original S16** | no false Goal completion |

The existing S49 first forward Action moved. The second physically hit the front wall and closed with native S16 `UNDETERMINED` / original Action `UNKNOWN` and cleared controls; only after that did the one original Mineflayer client receive a fresh correlated local voxel probe and L1 BFS choose the next route. Two source-attested physical detours reached the original parent L2 Goal via the same S49 owner; the fully blocked World safely refused any extra Action.

Independent fixed-source auditor `S49_NATIVE_LOCAL_GRID_SEARCH_REAL_DEV_PASS` / `S49_L1_NATIVE_GRID_BFS_PHYSICAL_DEV`: reconstructed all three decisions from raw native voxel cell packets, confirmed fresh original S16 source, verified all unique S49 Action IDs, true original S16 EXECUTED/OUTCOME stage consequences, actual stable REACHED, correct unchanged L2 final coordinate, and zero post-UNKNOWN Action in the no-route world.

[Preserved three-World raw reports, native grid packets and independent audit](https://github.com/rinsakamo/relay-self/actions/runs/40689496365/artifacts/12816695981): artifact ID **12816695981**, ZIP SHA256 **15c228b6e7be262e864f774080b950f0837c318a71670851efe793f4dda25573**, retention seven days.

Preflight failed runs remain FAIL: #40689081912 had invalid workflow YAML step label (no jobs), #40689252990 failed Ruff import (before Minecraft), and #40689386389 failed two focused negatives (before Minecraft). The one source-based unaligned-player negative and legacy `obstacle_block_perception_attested` behavior were corrected without weakening original supervision, and the exact tested code subsequently passed offline + all three real Worlds.

## Changed DEV files

- `src/relay_self/goal_grid_search_dev.py`: typed immutable native-grid plan, bounded 4-connected BFS, floor/body/UNKNOWN requirements, fixed source lineage and compress-to-turns.
- `src/relay_self/goal_local_voxel_dev.py`: fresh physical native player XZ in typed observer-local SelfWorld Present.
- `adapters/mineflayer/bridge.mjs`, `python_protocol.py`: native player XZ in strict 42-column packet, loaded-cache-only collision-bearing floor support.
- `adapters/mineflayer/s49_goal_loop_real_dev.py`: opt-in L1 grid selection and DEFER after actual physically unknown wall S16; two-sided physical block stimulus DEV.
- `adapters/mineflayer/s49_goal_executor_dev.py`, `s49_goal_waypoint_route_dev.py`: original S49 Action owner accepts source-typed variable-stage DEV plan without changing earlier three-stage checks.
- `adapters/mineflayer/s49_l1_native_grid_review_dev.py`: three independent original World source/terminal audit.
- `tests/test_s49_l1_grid_search_dev.py`, `.github/workflows/self-l1-native-grid-search-dev.yml`: focused negative and physical World tests.

## Next step

Now that L1 truly *generates* a bounded route from actual observed voxels (but only in a small, flat local volume), move toward a conservative continuous-body swept footprint and **re-observe at each waypoint or when new obstacles appear**, with fail-closed replan rather than stale-map continuation. Add independent randomized obstacle layouts and a combined live L0 in-flight hazard interrupt during L1-generated route movement. Keep `DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN` and separate owner grant requirements for QUAL/SCIENCE.
