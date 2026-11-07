# RelaySelf D7-D — Stage-based physical STOP sensor isolation (2026-11-07)

> **DEV_ONLY / operator-staged item / implementation; NO actual STOP certificate or EAT issue.**
> Reuses successful original [D6-C #771](https://github.com/rinsakamo/relay-self/pull/771) (Paper staged meat, genuine original S49 MOVE_BACKWARD 0.626907m and pickup) and D7-B's already existing read-only Paper `D7PaperServerTicks` plugin, and D7-A's S50 same-Mineflayer direct seven-input wrapper.

## Why a staged item

Natural [D7-C real World #42374036891](https://github.com/rinsakamo/relay-self/actions/runs/42374036891) succeeded at actual S49 ATTACK and *natural* rotten_flesh spawn, but the item was not reachable by the only existing `MOVE_BACKWARD` direction given that native yaw/geometry. D6 correctly declined issuance; there was no MOVE, pickup or physical STOP observation. This is a direction/route gate, not evidence that EAT should resume.

D7-D eliminates **only the source item direction confound** for the independent STOP observer experiment by asking the already qualified DEV Paper plugin to stage one real ground item behind the bot in the validated D6-C geometry. This staged item is never called natural zombie loot, Self-provided food, a new skill, or an unconditional EAT grant.

## Implementation change

- Original D6-C `bug0_d6_staged_move_world.py` gains **optional** `--d7-staged-controls`, valid only under both `D7_STAGED_STOP_SOURCE_WORLD_ONLY=1` and existing `D7_PASSIVE_CONTROLS_WORLD_ONLY=1`. No change to the normal D1/D6 command path.
- The original D1 disposable World launcher also loads the *preexisting* Paper natural-drop witness jar **solely as a default-off D7 server tick recorder**, with `d7-paper-tick-observer: true` in its private World config. It continues to use the original operator-staged pickup plugin for physical item, and **only one original S49 ActionSupervisor / Mineflayer bot**.
- `s50_p1_readback_bridge.mjs` wraps that same Mineflayer process and records the actual client seven `getControlState` values for physicsTicks and effects.
- A further passive 1s after Paper's **true item UUID pickup and real native inventory gain** allows distinct Paper server tick and client S50 readbacks. No native Action or EAT occurs in this observation period.
- `bug0_d6_staged_move_post.py` independently verifies original operator fixture, Paper UUID pickup, native inventory gain and **original C1 preissue-fenced S49 MOVE S16 OUTCOME**. Only then does `bug0_d7_staged_stop_post.py` independently join the exact S49 MOVE/clear IDs with S50 direct client-source and Paper main-thread tick stream, World/player/item UUID, actual pickup tick, per-server-tick seven *last received* input flags, positions and velocities; gaps/foreign sources/duplicates/truncation fail closed.
- Staged and natural evidence are **never pooled**: the physical source field remains `OPERATOR_FIXTURE_NOT_ZOMBIE_DROP`, `natural_zombie_drop_proven=false`.

## Current missing STOP → EAT contract

Even if Paper reads seven held inputs OFF and actual near-zero horizontal speed for eight consecutive ticks after a real pickup, the `Player.getCurrentInput()` source is still only Paper's *last received input* and no causal tick binding to original S49 native S15 CLEAR is established. Thus `server_effective_S49_clear_tick=NOT_CAUSALLY_ATTESTED`, `body_physically_stopped_proven=false`, `authenticated_S_owner_EAT_resume_grant=false`, and `original_EAT_issued=false` **must remain unchanged**. Never clear `_post_move_settling_unqualified` based on this report alone. Subsequent step belongs to S-owner with native Action-specific effective server input-release evidence, continuous Paper body state, fresh SelfBody/food/threat/Intent/probe and one-shot authenticated S49/S51 ISSUE with equip/consume/inventory/food effect verification.

## DEV gates

1. Offline focused regressions for existing D1/D6-C and D7-A/B/C plus new staged source falsification negatives, Maven builds of **both** Paper plugins.
2. Exactly one new disposable Paper World + single original S49 MOVE→Paper item UUID pickup→S50 client 8+ post-clear ticks→Paper 8+ postpickup ticks→independent source audits, native/Paper cleanup and SHA originals. No retries of the same World/Action.
3. If real World source is absent, insufficient ticks, client controls reactivate, or source UUID does not join, record **FAIL/UNDETERMINED** not STOP PASS. Qual and Science remain NO_GO/NOT_RUN.

Later return to natural-source D6 for actual EAT only after genuine original effective STOP and S49 owner admission; successful staged sensor readback alone does not establish complete two hunting/food cycles.
