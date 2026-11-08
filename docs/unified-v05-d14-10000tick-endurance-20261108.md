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

## Next stage for full user request

Connect an original S49 event-driven epoch loop beyond the fixed D8/D12 callbacks, without an arbitrary goal of three meals or a forced failure. For each natural kill / respawn / pickup / food action, preserve exact fresh Paper/native/S16 source and original owner. Zero rotten counts are experiences, not reasons to stop. Maintain a tick horizon, current body resources, real STOP safety and bounded host cost. Do not tune the World to produce Skill success. Only once this live owner loop is operational and independently checked should full 10000-tick autonomous survival/adaptation be claimed.

Parent source is D12 R2 #803 and read-only historical Experience PR #804. Those earlier real World outcomes and new D14 logs are distinct evidence. Learning/L2 and SOUL are not connected automatically.

DEV_ONLY / TICK_HORIZON_PILOT / ACTIVE_CONTINUOUS_S49_NOT_IMPLEMENTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
