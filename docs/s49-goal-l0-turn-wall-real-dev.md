# RelaySelf — Native XZ goal turn and obstacle-triggered fail-closed replan DEV

**2026-10-28 / DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

This isolated branch extends the original S49 Goal→L0 observation loop to an XZ target requiring an actual change in forward direction, and exercises conservative behavior when a physical obstacle stops progress. It does NOT yet provide pathfinding or bypass around an obstacle.

## Design

- L2 operator-specified immutable WORLD-XZ goal and deterministic L1 purpose/distance tolerance remain the same typed DEV contracts: no real L2 call, no learned L1.
- `compute_goal_bearing_dev` computes the XZ unit vector and Minecraft yaw (atan2(-dx,-dz)) from the original L2/L1 goal. The same original `ObservedGoalL0` uses this axis to compute signed forward remaining distance and cross-track deviation. No fixed +Z assumption.
- Original inherited S49 `ActionSupervisor` is still sole owner of physical S15 MOVE_FORWARD. A DEV-only S15 sub-effect `send_look(f"{action_id}-s15-look", yaw, pitch=0)` goes through the **same native reader** before sending forward controls, checks actual `look` APPLIED ACK for the same action binding and session, and fails closed if missing. This is a subordinate motor setup under the already-ISSUED Action, not a second Action issuer. Look ACK alone does not prove orientation; native first S16 XZ displacement is checked against the predeclared goal axis.
- Physical Action gives native S16 observation/XZ movement and terminal status. Only actual World position and stable WAIT_VERIFY→REACHED justify goal completion.
- In the WALL disposable World, an official Minecraft server command places a stone wall two blocks in the +Z direction ahead of the original player. The command is a **World stimulus, not Self's observation**. If the physical forward motor stops and S16 cannot determine execution, the original Action is `UNKNOWN`; no further Action is dispatched and a conservative `NEEDS_REPLAN` record preserves target/owner. This is not a general obstacle sensor, not an actual new L1/L2 plan, and not successful wall avoidance.

No forced Minecraft tick or Paper/Node clock synchronization. No new Mineflayer receiver or Action issuer; default product motor unchanged when opt-in disabled. DEV flags `S49_L0_GOAL_LOOP_DEV_ONLY=1`, `S49_L0_TURN_DEV_ONLY=1`, wall additionally `S49_L0_WALL_DEV_ONLY=1`.

## Exact independent native Minecraft test results

[Actions #40672057382](https://github.com/rinsakamo/relay-self/actions/runs/40672057382) **completed/SUCCESS**. Exact source HEAD `892d1e391c8a99bdefdb7c341b09069795816ec5`. Python3.12 focused **24 PASS**, Ruff PASS, Node22 syntax PASS, Java21 official Mojang Minecraft1.21.8 two independent disposable World sessions, Node/server clean exits. One earlier workflow #40671981206 failed *before Minecraft* due one test text assertion checking `look_yaw_dev=float(yaw)` instead of the actual optional-kwargs key `"look_yaw_dev":float(yaw)`; test fixed and re-run PASS. No code behavior was inferred from the failed preflight.

### TURN World — genuine non-axial movement

- Session `592fc26d-5dad-4c1c-b225-af71d1892a7f`, immutable target offset from initial XZ **(+1.4m,+2.6m)**.
- Original target WORLD XZ = **(-0.10000000000000009, 8.1)**; final native XZ **(-0.17181712584556297, 7.965209975110761)**.
- L1-derived acceptance radius **0.4134150456865352m**; final actual Euclidean XZ error **0.15272868222556968m**, passing stable WAIT_VERIFY/REACHED. Three original S49 native S16 successful MOVEs.
- First real S16 X-direction movement **+0.5960244093049121m**. Physical displacement alignment with goal bearing **0.9999996306522263**. This is physical movement, not just a look acknowledgement.
- Limits: this is one diagonal fixed target, no continuously varying yaw, unknown terrain heading, or obstacle.

### WALL World — no false Action success

- Session `f91b408b-9203-485d-b11b-fe72728bbac2`, original goal fixed 2.6m +Z from (0.5,10.5) to (0.5,13.1).
- DEV World stimulus: `execute at RelaySelf run fill ~-1 ~ ~2 ~1 ~2 ~2 minecraft:stone`, before issuing the first Action.
- First S16 `EXECUTED / OUTCOME` with native horizontal displacement **1.1571676753670648m**, endpoint Z11.657167675367065. A fresh next original native probe observes Z11.7.
- Second original forward S15 LOOK ACK + motor dispatch + CLEAR; actual S16 horizontal displacement ~**1.149080830487037e-13m** (within numerical precision of zero), typed status **UNDETERMINED**, original Action terminal **UNKNOWN**. The runner records `MOTOR_CONSEQUENCE_UNDETERMINED` and `NEEDS_REPLAN`, preserves original Goal XZ, and does not issue Action #3.
- Crucially, **no client-side block perception or explicit collision classification was attested**; the physical stimulus plus observed lack of progress supports a fail-closed control result, not a general obstacle avoidance algorithm. `upper_layer_replan_executed=false`.

Audit verdict `S49_L0_GOAL_REAL_TURN_AND_WALL_FAILCLOSED_DEV`. Original exact source ZIP artifact `s49-turn-wall-two-worlds-40672057382-1`, artifact ID **12808293037**, ZIP SHA256 **8fbece243dcf37f4334475fd13d230cf9cf107664ccecf05d3a439555e91df27**.

Source changes:
- `src/relay_self/goal_navigation.py` bounded pure goal heading and yaw.
- `adapters/mineflayer/execution.py` original S15 opt-in LOOK before motor with same-reader ACK.
- `adapters/mineflayer/s49_goal_executor_dev.py` same owner bounded goal LOOK authority.
- `adapters/mineflayer/s49_goal_loop_real_dev.py` real goal turn XZ and stone-wall original World DEV cases.
- `adapters/mineflayer/s49_goal_turn_wall_review_dev.py` two-World independent result auditor.
- `tests/test_s49_goal_turn_wall_dev.py` new pure bearing and authority negatives.
- `.github/workflows/self-goal-turn-wall-dev.yml` Python3.12/Node22/Java21 two isolated worlds.

## Remaining steps

1. Develop a **new L1-defined waypoint/replan handoff**, with explicit revision, reason and preserved parent Goal ID. Do not invent block perception from a server stimulus.
2. Under a separate DEV grant, evaluate an actual bypass path using observed physical native S16 +X/+Z movement, near obstacles and safe turns. The original S49 Action owner must remain unique; uncertain previous Actions cannot be silently retried.
3. Test dynamic L0 heading correction, lateral error, moving hazards / in-flight interruption while changing bearing, memory-based L1 policy retention and true L2 replan. Neither trained L1 nor actual L2 is yet present.

**No changes to main, Draft PR #545/#634, protected historical blobs, QUAL or SCIENCE.**
