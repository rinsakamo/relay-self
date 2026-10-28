# RelaySelf — actual Mineflayer block Present resolves conflicting remembered L1 routes

**2026-10-28 JST / DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

## Motivation and exact scope

Previously, two *independently physically successful* operator-supplied L1 detours (left and right) were retained as `PersistentCognition` Memories and exposed through SelfWorld `REMEMBERED`. A fourth real Minecraft World could see the original wall prevent movement, but had no sensory evidence to prefer left or right, and safely returned `DEFER / CONFLICTING_RECALLED_ROUTES`.

This DEV iteration adds a **separately correlated native Mineflayer block probe** through the existing sole session writer and reader. The same original Mineflayer `bot.blockAt` queries its already-loaded client block cache at a *fixed 3 columns per side, 2 vertical cells per column*, relative to the initial player World XZ and current foot Y. Each column is:
- `BLOCKED` if either of the two actually cached block types is not air;
- `UNKNOWN` if no cached data is available for either cell and neither is BLOCKED;
- `CLEAR` only when both actual cached block types are recognized air.

Unloaded/missing chunks are **never interpreted as absence of blocks**. The coverage is literally `loaded_client_cache_only`, with only 6 vertical columns (12 cells) and explicit per-lane source states. These samples cannot prove the entire corridor, headroom along continuous movement, floor support or arbitrary diagonal path collision-free.

The new DEV-only command is `observe_route_blocks_dev`, with a mandatory unique correlated request ID and finite bounded initial World origin. It is rejected unless `S49_L1_NATIVE_BLOCKS_DEV_ONLY=1` and the original Mineflayer client has actually spawned. The native bridge remains the sole block-cache reader and JSONL producer, and Python's **existing original session receive owner** handles a strict new `route_blocks_dev` packet, with native session/seq/request ID and exact limited coverage. There is no sidecar native packet consumer, Action issuer, Paper-world attestation or synthetic assertion that the operator's stone stimulus is Self's own observation.

### Observer and memory integration

`MineflayerRouteBlocksDev` is decoded to immutable `NativeRouteBlockPresentDev`. Its `observed_lane` returns a `WorldReading(WorldOrigin.OBSERVED)` with exact native source session/sequence/request ID. This is a **DEV-only observer-local SelfWorld Present extension**: it does not mutate the frozen SelfWorld v0 `WorldObservation` entity schema nor promote the observed block data to permanent Memory. The old successful route episodes stay `REMEMBERED` and source-audited by `PersistentCognition`.

L1's typed selector, when conflicting different route signatures are both eligible, now resolves the conflict only if **one entire sampled lane is CLEAR and the alternate lane has actually observed BLOCKED columns**. A lane with `UNKNOWN`, two equally `CLEAR` lanes, or two `BLOCKED` lanes returns `DEFER` rather than creating a guess. Foreign sessions, stale native sequence (not after the newly blocked S16), wrong origin, unbounded states, missing packet, malformed packet, mismatched memory source or altered parent Goal fail closed.

The final chosen L1 plan still requires *a new original physically closed S49 S16 `UNDETERMINED` and ActionSupervisor `UNKNOWN`* on that particular World. No old Action is retried or silently labeled OUTCOME. Only the original S49 ActionSupervisor issues new route Actions. The L0 stage controller uses the same S15 LOOK ACK, S16 native motion/position, stable WAIT_VERIFY→REACHED and original immutable L2 XZ Goal.

## Actual four original Minecraft Worlds

[Actions #40685584091](https://github.com/rinsakamo/relay-self/actions/runs/40685584091) **completed / SUCCESS**, exact tested code HEAD `6ee4b04a2827dbefcf6744ef7b419f57a9e73043`. Python3.12 focused **54 PASS**; Ruff, Node22 syntax, original Java21 official Mojang Minecraft 1.21.8 / Mineflayer4.39.0 and clean Node/server shutdowns PASS. Four independent disposable World sessions, no real provider/model calls:

| Arm | Native session | Result |
|---|---|---|
| WALL_STOP | `5489fa79-1f4f-4451-9d09-cb21380f0c57` | Original wall S16 uncertain Action `UNKNOWN`, no extra Action |
| right DETOUR | `e01308a6-42b8-47a9-8a26-6b3c03ea1af0` | Genuine prior successful +2.5m lateral detour, parent Goal reached |
| left DETOUR_B | `3915cca8-2dce-4476-b0b7-4c2979c4f79a` | Genuine independent successful −2.5m lateral detour |
| TRANSFER | `e3f095e0-d516-4307-ae7b-a7e29daaaba8` | Fresh original wall S16 UNKNOWN; left-side extra wall is *operator-set stimulus*; actual native read chooses RIGHT; L0 executes 8 fresh Actions and reaches original L2 Goal |

The TRANSFER World has the same original front stone obstruction at +2m; an additional operator-set stone obstacle blocks only the left-side corridor. That command is **not itself a sensor**. After the blocked Action's original S16 seq30, the existing Mineflayer client produced actual correlated block packet **seq31** with request ID `goal-e3f095e0-d516-4307-ae7b-a7e29daaaba8-native-route-after-30`. It measured:

- **LEFT:** `[BLOCKED, BLOCKED, BLOCKED]` (actual loaded-cache samples);
- **RIGHT:** `[CLEAR, CLEAR, CLEAR]` (actual loaded-cache samples);
- coverage `loaded_client_cache_only`; `unknown_is_not_clear=true`.

The two successful route Memories and one blocked failure remained `REMEMBERED`. The new native lane Present resolved that conflict with `NATIVE_PRESENT_RESOLVED_CONFLICT`, selecting `l1-route-success-a` (RIGHT). The original Action owner then executed **8 real waypoint Actions**, observing native stage arrivals and finishing with **0.10137837892729153m** original L2 XZ residual, inside its L1-derived **0.34545639008188705m** tolerance.

Independent reviewer result: `S49_L1_NATIVE_BLOCK_ROUTE_RESOLUTION_DEV_PASS`; classification `S49_L1_NATIVE_BLOCK_PRESENT_RESOLVES_ROUTE_CONFLICT_DEV`. New Action issuers **0**, new native packet readers **0**, learned L1 policy attested **false**, real L2 planning attested **false**. First preflight on the new branch failed on Ruff E741 naming and import ordering, before any World; isolated corrections then passed and this exact final code was tested in the four real Worlds.

[Raw original four-World evidence and saved Memory snapshot](https://github.com/rinsakamo/relay-self/actions/runs/40685584091/artifacts/12814378844): artifact ID **12814378844**, ZIP SHA256 **ec3925f1ecb11edabd2aac25f4180c9b95a296fe37e25a415cef9be614475b60** (7-day artifact retention).

## Files and constraints

- `adapters/mineflayer/protocol.mjs`, `bridge.mjs`: explicit bounded read-only route block command and actual client-cache probe.
- `adapters/mineflayer/python_protocol.py`, `process_session.py`: typed lane packet decoding and original native session write/receive.
- `src/relay_self/goal_native_blocks_dev.py`: typed observer-local `WorldOrigin.OBSERVED` lane Present with explicit UNKNOWN coverage.
- `src/relay_self/goal_memory_choice_dev.py`: native evidence-backed conflict resolution only for one clear lane and observed opposite blockage; otherwise DEFER.
- `adapters/mineflayer/s49_l1_selfworld_memory_dev.py`, `s49_goal_loop_real_dev.py`: same owner, native S16 after observed physical wall, present + memory select, and staged original L0 move loop.
- `adapters/mineflayer/s49_l1_native_blocks_review_dev.py`: four-World native-source and physical original-goal independent audit.
- `tests/test_s49_l1_native_blocks_route_dev.py`, `.github/workflows/self-l1-native-blocks-route-dev.yml`: positive and negative source/coverage unit tests and real-world DEV check.

**Qualification limits:** A single special fixed six-column geometry and two pre-specified route shapes. One real run resolved the right side; opposite-side source behavior, unknown/unloaded memory cache and two-clear-lane DEFER are tested offline only. This is not generalized continuous path obstacle perception or learned route generation, cannot guarantee safe passage, and does not claim in-flight L0 hazard preemption through this entire route. No changes to `main`, protected Draft PR #545/#634, historical evidence, QUAL or SCIENCE.

**Next DEV:** Extend from six-column fixed sampling toward a bounded local voxel grid with typed coverage, and test both an *actual* opposite-side open corridor and an *actual* no-loaded-block/unknown negative World. Keep the existing S49 owner, fail-closed evidence requirements, and avoid treating missing chunk data or DEV operator stimulus as sensor truth.
