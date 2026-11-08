# D14 — 10,000 Paper server-tick observation DEV

User direction: stop treating third zombie as an experiment goal. Use 10,000 elapsed Paper server ticks as the observation horizon. Keep genuine World-owned zombie respawns (death + 600 World ticks), normal vanilla loot RNG and old original S49 Action authority. Time-to-end is not based on the number of food cycles.

## Critical limitation of this first slice

This branch implements a true 10,000-tick Paper clock and read-only SelfBody sampling. It reuses D12/D8 physical source for initial activities and then watches the SAME World, but does NOT yet include a generic third-and-later S49 ATTACK/PICKUP/STOP/S51 EAT owner loop. The Paper respawner supports as many generations as genuine deaths occur before the World tick limit, with one living managed zombie at a time. If Self never kills a later zombie, no further zombie is generated. A 10,000-tick source horizon PASS is not autonomous long-life survival or continual combat learning.

The inherited first two cycles use the disclosed D8 DEV arena enemy/hunger staging, not unmodified fully autonomous Minecraft survival. The D14 watcher itself never alters food, loot RNG, entity health, player hunger, inventory, S49 Action permission or L2 behavior.

## Paper opt-in

Existing adapter zombie_respawn_dev default remains disabled. An explicit D14 World config enables a 10000 tick source horizon with 200-tick samples. It starts on the first genuine Paper managed zombie spawn tick. Markers:

- RSELF_ENDURANCE_START: immutable World UUID, start_tick and stop_tick.
- RSELF_ENDURANCE_SAMPLE: one at elapsed 200, 400, ..., 9800 World ticks, with source generation/living UUID.
- RSELF_ENDURANCE_LIMIT: exactly at elapsed 10000, no new zombie spawns after horizon, no forced death or food mutation.

The original respawn delay remains 600 server ticks after a real death, not a periodic synthetic mass spawn. World-owned times are authoritative. The host watchdog is only for a stuck/crashed World and cannot make a short run a horizon PASS.

## DEV observer and audits

tools/bug0_d14_tick_horizon_world.py uses the original D4/D8/D12 owner and observes Paper marker progress, live native SelfBody probes (Food, Health, oxygen, rotten inventory, source seq). Native probes are asynchronous; they are NOT attested as exactly simultaneous with Paper heartbeat ticks. No Action is issued by this observation path, and no Memory/Learning/Skill changes occur.

tools/bug0_d14_tick_horizon_post.py independently verifies parent D12/D8 original Paper/S50/S49/S51 physical journals; a natural 0 drop is a normal NOT_EXERCISED parent result, not a fabricated meal. D14 tick 10000 PASS requires 49 unique ordered Paper samples, same World UUID, exact tick arithmetic, no post-limit spawns, no World fault, clean original owner evidence and no extra physical Action from watcher. A live Self death/disconnect before 10000 is an observed early termination, NOT horizon PASS.

Pure Java horizon test and Python negative controls cover malformed tick/source, duplicate or omitted marker, action/learning overclaims. The D14 offline CI builds the plugin and runs old D8/D12 regressions and contracts. D14 one-use real-World workflow only activates on exact preauthorized doc-trigger commit and preserves originals plus independent auditor result in a separate artifact.

20 TPS gives an approximate 8m20s for 10000 ticks but the true runtime can differ with server TPS. The World, not wall-clock, determines completion.

## R1 actual outcome and structural correction

R1 original Actions #42476188647 produced immutable artifact #13615936528 with SHA256SUMS 7/7. One original S49 ATTACK killed the managed Paper zombie at tick524; genuine vanilla rotten flesh count=2. One original MOVE then closed as S16_OUTCOME, but the existing D6 follow-on native item approach was rejected (D6StagedMoveRejected). This stopped the old D8 driver at Paper tick around 580. R1 did NOT reach 10000 ticks; it remains an early source-qualified failure rather than a food or horizon success.

The earlier D14 wrapper still depended on D8's success path, which contradicted unattended tick-based World observation. R2 preserves the failed Action route in the report but, only when the original S49 supervisor and BOTH physical journals are fully closed with no outstanding Action, may observe the existing World until its real tick limit. The previously rejected Action is never automatically retried. Separate independent auditors will verify each issued original S49 Action and the tick horizon, and will distinguish action-path FAIL from clock-horizon PASS. Unresolved physical Action must still stop the run.

A separate R2 one-use trigger and fresh evidence namespace are used. R1 records remain unchanged.

## Next stage for full user request

Connect an original S49 event-driven epoch loop beyond the fixed D8/D12 callbacks, without an arbitrary goal of three meals or a forced failure. For each natural kill / respawn / pickup / food action, preserve exact fresh Paper/native/S16 source and original owner. Zero rotten counts are experiences, not reasons to stop. Maintain a tick horizon, current body resources, real STOP safety and bounded host cost. Do not tune the World to produce Skill success. Only once this live owner loop is operational and independently checked should full 10000-tick autonomous survival/adaptation be claimed.

Parent source is D12 R2 #803 and read-only historical Experience PR #804. Those earlier real World outcomes and new D14 logs are distinct evidence. Learning/L2 and SOUL are not connected automatically.

DEV_ONLY / TICK_HORIZON_PILOT / ACTIVE_CONTINUOUS_S49_NOT_IMPLEMENTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.


## R2 facts → R3 log/termination remediation (2026-11-08)

R2 [Actions #42477201083](https://github.com/rinsakamo/relay-self/actions/runs/42477201083) was CANCELLED by the 35-minute job timeout. Artifact [#13617071861](https://github.com/rinsakamo/relay-self/actions/runs/42477201083/artifacts/13617071861) retained 6/6 SHA256-verified originals. Paper start tick15 / planned end tick10015, genuine first kill tick526 / natural rotten count0, generation2 spawn tick1126 (+600 tick), and actual RelaySelf death near tick1337. The managed horizon RESET at death, so no 10000-tick terminal marker was produced. D7 and S50 original source rows each reached their legacy 8192-row cap. The later Paper tick8206 is not evidence of Self survival or horizon completion.

Changes after R2 in this branch:
- Paper now writes RSELF_ENDURANCE_TERMINAL with actual World/tick/reason before death, disconnect or scope-loss cleanup. This is explicitly an early termination, never a horizon PASS.
- Python D14 watcher reads incremental appended Paper bytes, detects early terminal before requesting stale native probes and bounds any correlated readback to 9 seconds.
- The fresh exclusive fsync'd derivative d14_paper_world_events.jsonl captures START, each 200-tick SAMPLE, TERMINAL/LIMIT and asynchronous native observations; this source-referencing derivative can survive a cancelled runner.
- With explicit D14 World opt-in only, original full-rate Paper D7 and native S50 source row caps are 12000 rather than the normal 8192. Other v0.5 tests retain 8192. These original sources remain distinct from the derivative 200-tick event journal.
- Offline negative tests include forged Paper death/disconnect ticks and reason, and both Paper plugin builds.

**R3 is not yet run.** Use a fresh exact-head documentation-only one-use trigger after independent LocalCodex preflight, never reuse R1/R2 evidence or an already consumed trigger. Treat a natural early Self death as a real observation and finite end of the Self. Never silently respawn the old owner or count it as 10000-tick success. Preserve original physical Action fences. Full third-and-later original S49 combat/food continuation is still not integrated in this watcher: a successful World clock is not autonomous survival or Skill learning.
