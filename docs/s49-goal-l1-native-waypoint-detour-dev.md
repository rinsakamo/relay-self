# RelaySelf — L1 waypoint detour and return to original L2 goal (2026-10-28)

**DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

## Scope

This is the follow-on from the real native S49 TURN/WALL DEV. It preserves a single original S49 `NormalSessionActionExecutor` / `ActionSupervisor`, typed S15 LOOK and WALK effects, original S16 observations, and the fixed L2 goal across a wall obstruction and L1-subgoal traversal.

**What is new:** An explicit L1-style detour plan is admitted after a real original S16 no-progress/UNKNOWN Action. It consists of three versioned stage targets, all tied to original session/intent/parent Goal, a source Action ID, a source S16 sequence, a concrete revision, and a provenance. Each stage uses a separate `ObservedGoalL0` with a source-grounded native XZ start, heading toward the stage target, normal bounded WALK/LOOK Actions, fresh probe feedback and stable WAIT_VERIFY→REACHED checks. After stage 3, actual observed XZ returns to the unchanged initial L2 destination.

**Scope boundary:** the waypoint geometry is explicitly provided by a DEV operator acting as L1, NOT discovered from native obstacle perception or a learned L1 policy. The stone wall is placed by the disposable World operator and does not count as Self seeing a wall. The old `UNKNOWN` Action ID is never retried; this is a new, explicitly authorized L1 route revision from an uncertain previous motor outcome, not retroactive conversion of UNKNOWN into OUTCOME. No real L2 model call, no actual learned L1, no new packet reader or Action issuer, and no successful dodge or combat claim.

## Experimental route

Original parent L2 XZ target offset **(0,+4.0)m** relative to actual starting Mineflayer position. A three-block-wide stone wall is inserted in the World at +2m forward. Same physical Minecraft 1.21.8 / Java21 / Mineflayer4.39.0, no phase-forced TPS.

1. Original S49 L0 attempts forward movement toward immutable parent goal. First typed S16 MOVE is executed; second runs into wall (near-zero native displacement), yielding `UNDETERMINED` S16 and original Action `UNKNOWN`, after actual CLEAR ACK.
2. The DEV L1 route is defined only after that closed original Action: intermediate **(+2.5,+1.1)m** to move laterally alongside the wall; next **(+2.5,+3.8)m** beyond its far side; final **(0,+4.0)m**, exactly the initial L2 target. Stage positions are fixed relative to original World start, not selected using future movement outcomes.
3. Under the same original executor and supervisor, stage transitions require the prior Action closed and the most recent original native probe strictly newer. Stage 0 requires the exact source UNKNOWN Action and S16 sequence; stages 1/2 require the preceding original S49 Action OUTCOME. Each stage declares a fresh subgoal ID under the same parent, a bounded L1-style precision and its own L0 probe/act loop.
4. All three stages must reach a stable native XZ endpoint inside their respective tolerance, and the final endpoint must lie inside the final L1 tolerance of the unchanged original parent target. Otherwise fail closed, preserve raw World source and do not claim a completed parent goal.

DEV gates: `S49_REAL_SERVER_CI`, `S49_FORWARD_MOTOR_DEV_ONLY`, `S49_L0_GOAL_LOOP_DEV_ONLY`, `S49_L0_TURN_DEV_ONLY`, `S49_L0_WALL_DEV_ONLY`, `S49_L1_WAYPOINT_DEV_ONLY` each `=1`. No main / Draft PR #545/#634 / historical S18 changes. Changes remain in new DEV lane branch `self/dev-goal-l1-waypoint-bypass-20261028`.

## Verified native Minecraft DEV result

[GitHub Actions #40674371816](https://github.com/rinsakamo/relay-self/actions/runs/40674371816) **completed/SUCCESS**. Exact tested code HEAD `3a1f01a488f4f439640482a611aaab589aad0925`. Python3.12 focused **30 PASS**, Ruff and Node22 PASS, original Java21 Mojang 1.21.8 and Mineflayer. Two independent disposable Worlds (wall-only negative control and wall+detour), real raw source reports, Node/server exits 0.

Sessions:
- WALL_STOP: `82d899ef-5aa5-48ac-a260-4dd0e7ee261d`. Original blocked second Action `UNKNOWN`, no further physical Actions.
- DETOUR: `b3dd3425-cdd0-4aa8-8d0a-def7c51a9648`. Original blocked Action `goal-approach-demo-step-2`, S16 after seq43, `UNKNOWN`, retained original Goal target WORLD XZ **(-5.5,13.5)**. Same original ActionSupervisor then continues via L1 revision 1.

| Original native stage | Actual target WORLD XZ | Original Action OUTCOMEs | Final actual XZ error | Stage tolerance |
|---|---|---:|---:|---:|
| L1 lateral-before-wall | (-3.0,10.6) | 3 | 0.09919747345620673m | 0.3502798880894357m |
| L1 past-wall | (-3.0,13.3) | 3 | 0.0775243445719669m | 0.37064734331575444m |
| L1 original-destination | **(-5.5,13.5)** | 3 | **0.029311377855436593m** | 0.3583772530926027m |

All nine subsequent original physical Actions have distinct IDs and native S16 EXECUTED/OUTCOME sources, with successful S15 LOOK ACKs and fresh positional observations. The final native observed endpoint is WORLD XZ **(-5.525480505810052,13.485512049991524)**, distance **0.029311377855436593m** from original L2 Goal. Distinct independent baseline World retains prior wall-stop behavior. Original route `S49_L1_NATIVE_WAYPOINT_DETOUR_DEV_PASS` report audit accepted final parent, route revision and all required sources. No second native packet reader / additional Action owner / invented obstacle observation.

Artifact: [GitHub raw two-World sources](https://github.com/rinsakamo/relay-self/actions/runs/40674371816/artifacts/12809782153), artifact ID **12809782153**, ZIP SHA256 **c61a4fbed630f18552f45e308935b8981810d5cdb0d25fbf2f1a7cafb8226535** (GitHub artifact retention 7 days).

Historical failed preflights remain available (#40674096795, #40674273267): Ruff import formatting failed **before** physical Minecraft, then isolated import corrections and exact-HEAD real verification succeeded. No silent reclassification.

## Qualification limits / next

This proves source-consistent explicit three-waypoint L1-style **execution** and restoration of a parent goal in one bounded artificial wall geometry. It does not demonstrate self-derived collision geometry, autonomous L1 plan synthesis, reusable learned detours, real L2 replan or generic pathfinding. The existing mid-Action native L0 danger preemption path was verified in a separate DEV, but this particular waypoint-run does not activate the in-flight poll callback for each stage; it checks threats on fresh between-Action probes. Do not assert whole-route continuous emergency preemption without a separate combined live test.

Future development: actual SelfWorld-based obstacle representation, L1 memory/experience selection and dynamic goal revision, with real-world multiple wall geometries and hazard interrupts, retaining exactly one native owner and fail-closed terminal accounting.
