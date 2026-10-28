# RelaySelf S49 — L1 grid refresh and original L0 in-flight hazard interrupt (DEV)

2026-10-28 JST. **DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Source and isolation

The verified predecessor is commit `3b3bfa2721b2dbc95c41f8a81d6283e39428069a` on `self/dev-l1-grid-waypoint-refresh-20261028`, derived from prior bounded BFS `f93b7e3c2fd0e20f62d861b9de20b371f70d9b05`.
This follow-up is isolated on `self/dev-l1-grid-refresh-inflight-l0-20261028`.
No changes to `main`, Draft PR #545 or Draft PR #634. No QUAL or SCIENCE runs.

## First milestone: re-observation across settled waypoints

[Real Minecraft 1.21.8 two-World PASS run 40692254820](https://github.com/rinsakamo/relay-self/actions/runs/40692254820), tested code HEAD `3b3bfa2721b2dbc95c41f8a81d6283e39428069a`. Both Python 3.12 focused and native physical job PASS.

- UNCHANGED: 2 revisions, 9 physical native actions after the original wall UNKNOWN, last parent Goal error **0.060986272185233656 m**.
- MIDROUTE_BLOCKED: after first settled waypoint, a DEV operator placed real stone at local grid (2,2); the sole original Mineflayer session re-observed the block and L1 re-planned via (3,2). 3 revisions, 11 physical native actions, parent Goal error **0.20860596185667196 m**.
- Both final native positions are within original 0.30m Goal tolerance, on fresh settled S16/ACK source with unique original S49 Action IDs.
- Independent recorder/auditor class: `S49_L1_NATIVE_GRID_REFRESH_PHYSICAL_DEV`.
- [2 World raw artifacts 12817054195](https://github.com/rinsakamo/relay-self/actions/runs/40692254820/artifacts/12817054195) (seven-day retention).

## Second milestone: native L0 interruption during revised route

[Real Minecraft 1.21.8 one-World PASS run 40693206492](https://github.com/rinsakamo/relay-self/actions/runs/40693206492), tested code HEAD `f73ba18ff82abb1afa4aa0dcdfd0768863add8e1`, Python 3.12 focused/Ruff/Node syntax and real original Minecraft startup all PASS.

- Original first grid route: settled waypoint stage REACHED with 3 true S16 OUTCOME actions.
- Genuine new local voxel source triggered one revision to L1 route **revision 2**, preserving original parent L2 target.
- Original Action `goal-approach-demo-grid-2-grid-turn-0-step-6` applied native MOVE at seq **103**.
- Only after real S15 APPLIED did the DEV World operator summon a zombie. The same original Mineflayer reader's native live observation detected it at seq **108**, observed distance **0.7047723901068899 m**, L0 issued **INTERRUPT**.
- S15 `goal-approach-demo-grid-2-grid-turn-0-step-6-s15-clear` acknowledged clear at seq **109**.
- Original S16 closed as `UNKNOWN` at seq **110**, status `FAILED`, error `DEV_L0_INFLIGHT_NATIVE_THREAT_PREEMPTED` (deliberate safe preemption, not execution success).
- Original Action owner open count was zero; **zero additional Actions** after interrupt, parent L2 Goal unchanged, no false REACHED.
- Independent auditor classification `S49_L1_GRID_REFRESH_PLUS_L0_INFLIGHT_PHYSICAL_DEV`.
- [Native hazard raw artifact 12818770118](https://github.com/rinsakamo/relay-self/actions/runs/40693206492/artifacts/12818770118) (seven-day retention).

Preflight FAILs are retained: import ordering, missing pytest dependency, revision-duplicated native request ID, and initially incorrectly expected CLEAR action ID. Crucially the last native FAIL's preserved diagnostic established correct physical APPLIED→native threat→CLEAR→UNKNOWN and exposed that CLEAR's native action ID uses the original `-s15-clear` suffix, then the strict guard was corrected rather than bypassed.

## Proven boundary and remaining work

This is **waypoint-boundary**, not arbitrary mid-Action L1 replanning. L0 can interrupt a currently active Action; L1 reroutes only after physically closed S16 and stable waypoint arrival. Coverage is a bounded local loaded-cache **7×6 horizontal columns, three vertical cells**; BFS is four-connected without diagonal cuts, requiring observed floor support and free feet/head cells. Unknown cells are nontraversable. Not a proof of full swept-body clearance, arbitrary obstacle physics, jump/stair/vertical navigation, crowd dynamics, continuous hazard avoidance, generalizable learned intelligence, or production safety. No new Action issuer or native packet reader, no real model calls.

Next DEV: randomized multiple blocked layouts with observed source audit; unexpected/disappearing block or UNKNOWN cell negative controls; combined **new stone + native in-flight threat in one physical World**; conservative swept-footprint check before progressing to broader maps. QUAL/SCIENCE require separate owner grants.
