# RelaySelf — SelfWorld REMEMBERED + PersistentCognition multiple-route L1 choice (DEV)

**2026-10-28 JST | DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

## Objective and ownership boundary

Move beyond replaying one successful hardcoded DEV route by retaining **two independently successful real Minecraft navigation episodes and one genuine blocked/no-route experience** into the already-existing `PersistentCognition` Memory owner, then exposing those Memories read-only as `SelfWorldView.remembered(...)` in a fresh World decision epoch. This does **not** give SelfWorld a mutable registry or Action authority. The original S49 `ActionSupervisor` and the original native S15 LOOK/MOVE and S16 feedback continue to own every physical Action. Never convert a previous `UNKNOWN` into `OUTCOME`, and never use an old World Action ID in a new World.

The new selector groups only matching successful **relative waypoint signatures**. When all eligible successful route memories share one signed geometry, one is selected by bounded observed source Action count then final error. If multiple incompatible route geometries fit indistinguishable evidence, it yields **DEFER**, not an invented collision map or forced guess. No eligible route, a changed goal vector, changed DEV environment class or mismatching actual blocked Action => DEFER, and **no physical Action is issued from that memory**.

The matcher does not claim that a native Minecraft client observed the wall geometry: environment fixture scope is passed as an **explicit DEV operator label**. One actual current World S16 must have terminal `UNKNOWN` and physical consequence `UNDETERMINED` with a fresh sequence before the catalog may be queried. The catalog and every retained Memory are verified against the SHA256 of original real-World source reports, and each remembered success episode's full decoded route must equal its authenticated source, with JSON arrays/tuples canonically normalized. The failure memory is a real blocked wall source, not a demonstrated failed bypass attempt.

## Files

- `src/relay_self/goal_memory_choice_dev.py`: `L1RecallStatusDev`, source-bound `Memory` content and provenance, read-only `SelfWorldView.remembered()` and deterministic consensus/abstain route selection.
- `adapters/mineflayer/s49_l1_selfworld_memory_dev.py`: after physically verified first-World sources, export two genuine three-stage successful episodes, retain those + one control failure via **existing** `PersistentCognition.retain_memory()` and `save_persistent_cognition()`; create immutable source catalog; re-load source-linked memory and compose a fresh `SelfWorldView` for read-only recall.
- `adapters/mineflayer/s49_goal_loop_real_dev.py`: alternate isolated DEV-only recall path after a **new original closed S16 `UNKNOWN`**, preserving original L2 goal, S49 Action ownership and the prior versioned waypoint runner. On DEFER, stop without issuing another physical Action.
- `adapters/mineflayer/s49_l1_selfworld_memory_review_dev.py`: independent four-World evidence audit, including exact source sessions, persisted Memory snapshot, recalled chosen ID, current goal geometry, S15 LOOK ACK and original S16 outcomes / final settled actual XZ.
- `tests/test_s49_l1_selfworld_memory_choice_dev.py`: two agreeing successes + one blocked failure, conflicting-success signature abstention, forged Memory, stolen owner, stale or foreign session, changed Goal or fixture context, denied fake motor outcome.
- `.github/workflows/self-l1-selfworld-memory-dev.yml`: Python3.12 focused/Ruff and Node22 first; original Java21 official Mojang Minecraft1.21.8 and Mineflayer4.39.0 in **four independent disposable Worlds**; preserve source RAW reports, persistent snapshot, episode manifests and failure reports.

## Four-world DEV test sequence

1. `WALL_STOP`: original S49 physical wall STOP, second Action `UNKNOWN`, no further original movement.
2. `DETOUR`: first real explicit three-stage successful L1-style route, original parent L2 Goal reached in its World.
3. `DETOUR_B`: second independently started real World and successful original route, not a duplicate JSON. It is audited against the original control without pretending its Action/probe IDs are the same as World 2.
4. Source audit extracts both successful World-relative waypoint experiences + the blocked failure into an existing `PersistentCognition` snapshot. Another World `TRANSFER` encounters its own S16 motor `UNKNOWN`, receives the previously stored Memories as `SelfWorldView` `REMEMBERED`, selects the one supported relative geometry, issues **new** native S49 waypoint Actions and checks final parent-goal XZ/tolerance.

The second audit workspace only contains a *copy of the same real WALL_STOP report* and the original DETOUR_B report; it does **not** create a fifth World or claim two independent failure sessions. All source session IDs are checked before retaining memory. A separate wrong-fixture/mismatching goal or conflicting memory geometry negative test must return DEFER; with no native wall shape sensor, this is not evidence for robust unknown-layout navigation.

**Boundary:** These are explicitly DEV operator-provided successful route geometries, not generated by a learned model. Matching multiple episodes is an engineering prototype of episodic L1 decision support, **not** proven autonomous L1 learning, a general route policy, perception of hidden blocks or live L2 planning. Do not apply this to main, Draft PR #545/#634, QUAL or SCIENCE without separate owner approval.

## Evidence / status

Pending final exact-HEAD native real World run. Preliminary run #40679473157 archived all original three source Worlds and retained three Memories but safely rejected recall because a tuple-vs-JSON-array structural comparison treated identical normalized source content as unequal. The DEV source was corrected to canonical JSON structural equality, retaining full source digest checking; subsequent verification is reported separately, not silently conflated with the failure.
