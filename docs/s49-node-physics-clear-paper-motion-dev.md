# S49 original Mineflayer local physics after clear-controls / Paper post-release DEV

Date 2026-10-26. Branch: `self/dev-s49-forward-motor-admission-20261026`.
**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Completed real Minecraft result

**Latest source-tested exact HEAD** `1953f9085dd4556394bad51d02931179a914049b`:
[real Paper/Node/P1/M0 trial #40323157470 — SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40323157470).
Python3.12 focused+negative controls, Ruff, Java21 and Node22 compilation,
original S49 2/2 S16 OUTCOME, Paper release, and cleanup all PASS.
Node original first Action recorded 12 active physics ticks; all 5
postclear ticks had forward=false/sprint=false and nonzero movement
**0.21214275, 0.11582994, 0.06324315, 0.03453076,
0.01885379 meters**. Paper registered its own post-release ticks
262–266: mixed-boundary first delta 0.32797269m, then
0.06324315, 0.03453076, 0.01885379, 0m.
The two independent producer-local clocks remain unsynchronized.
S49/P1 DASH charge 0.08633238849; original B0 owner M0 remaining
10.413667611509306. This trial's native S49 action distances were
3.8892309m / 2.74973734m; separate-run distance comparisons are
uncontrolled. The earlier measurements below refer to the earlier
real World #40322594341, not this latest run.

Source result: `eea4888d8b1bf3d39d299b8ccdd9b3e2dcf9d9b9`.
[Real Paper 1.21.8 + Node22 + Java21 + Python3.12 focused validation run #40322594341: SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40322594341).
Additional exact-branch regression after S15 import sorting:
[#40322783159 focused PASS](https://github.com/rinsakamo/relay-self/actions/runs/40322783159),
[#40322782895 original ACK/Paper real World PASS](https://github.com/rinsakamo/relay-self/actions/runs/40322782895),
[#40322782990 sprint real World PASS](https://github.com/rinsakamo/relay-self/actions/runs/40322782990).
Initial DEV failure [#40322484158](https://github.com/rinsakamo/relay-self/actions/runs/40322484158)
correctly failed closed because Node JSON trace contained literal escaped
trailing newline, repaired before the positive run. No false qualification or
M0/P1/WAIT state transitions were admitted on that failure.

### New original-Node-local physical witness

Original Mineflayer bridge `bridge.mjs` receives an explicit isolated
DEV gate `S49_NODE_PHYSICS_TRACE_DEV_ONLY=1` plus a fresh absolute
`S49_NODE_PHYSICS_TRACE_DEV_PATH`, in addition to existing
`S49_SPRINT_MOTOR_DEV_ONLY=1` and Minecraft 1.21.8. No inherited default
activation, no new native stdout message, no Action issuer, no additional
reader. The first already-issued original S49 native forward-sprint
`setControlState` records **SET** followed by bounded native
`physicsTick` ACTIVE snapshots; original existing clear-controls effect
records **CLEAR**, followed by exactly five POST_CLEAR physics callbacks.
One Node producer-local JSON file is written with exclusive create
(`wx`) after five clear samples. No output is forged for missing data.

Each row records Node-local monotonic ms, physics tick ordinal, forward,
sprint, back, left, right booleans, local horizontal position and velocity.
Node physics clock is NOT paper World fullTime. Separate Python readback
checks one SET, active samples, exactly one CLEAR, five continuous
POST_CLEAR, all direction controls false thereafter, bounded numeric
positions, unique identity, and a matching Paper 5-tick passive
post-release session/action. Negative-control mutations (wrong action,
session, missing/duplicate physics, fraudulent flags, nonmonotonic clock,
NaN, teleport, forged paper WAIT or P1/M0 credit) are rejected.

### Measured result, ONE disposable Minecraft DEV World

| Evidence | Actual result |
| --- | --- |
| First S49 native original Action | `s49-native-move-19` |
| Original second Action | `s49-native-move-56` |
| Original S16 outcomes | 2/2 real native OUTCOME |
| Node physics with forward+sprint true | 11 ACTIVE physics ticks |
| Node forward+sprint after local control CLEAR | false in 5/5 subsequent physics ticks |
| Node first POST_CLEAR horizontal translation | 0.2122345417 m |
| Node second POST_CLEAR horizontal translation | 0.1158800597 m |
| Node third POST_CLEAR horizontal translation | 0.0632705126 m |
| Node fourth POST_CLEAR horizontal translation | 0.0345456999 m |
| Node fifth POST_CLEAR horizontal translation | 0.0188619521 m |
| Paper release World tick | 257 |
| Paper post-release 5 continuous World ticks | 258–262 |
| Paper first MIXED boundary delta | 0.1791505724 m |
| Paper subsequent 4 deltas | 0.0345456999, 0.0188619521, 0, 0.0159216756 m |
| Node/Paper native tick exactly synchronized | **false / unknown** |
| P1 fatigue (13 original Paper callbacks) | 0.600000→0.617712241 |
| P1 applied DASH power first→last | 0.802197252→0.767868970 |
| Original B0 M0 owner first+second Action | 12.0→10.413667611509306 |
| Extra DASH M0 debit first Action | 0.08633238849069515 |
| Native Action distances | 3.612264745m / 3.030157205m |

The Node view shows **all five local physics updates have control
forward=false and sprint=false while player local horizontal position
still changes**. This demonstrates local post-clear translation without
persistent requested forward or sprint input. The monotonically
decreasing deltas are consistent with physics coasting, but the
hypothesis that a particular Paper position change was caused by
particular Node tick cannot be proven from these separate unsynchronized
clocks. No inference of world-wide inactivity, no physical WAIT,
no P1 fatigue recovery, and no new idle M0 transaction.

### M0 time calibration still requires explicit model choice

Existing canonical `MetabolismConfig.basal_cost=0.5` is per M0
logical step, **not** per Paper 50ms world tick or per Node
`physicsTick`. Existing S49 owner still settles one
`metabolism_step(action="MOVE")` for EACH original Action outcome and
a verified P1 extra charge for DASH (one first Action only).
Node and Paper post-clear sampling is fully passive. There is
no scientifically grounded conversion of 0.5/step to energy/second from
this one experiment; adding 5/5 idle basal ticks is forbidden.

Code status: isolated DEV only. No original evidence rewrites,
no PR #545/#634/main changes. No FULL regression or R/SCI execution.
Next engineering gate: a bounded native control telemetry control test
to distinguish actual motion continuation from stale client physics
cache and optionally a trustworthy cross-source clock bridge;
separately specify energy/second and an explicit M0 rate calibration
before World-tick billing.
