# D6-D3 — zero loot continues into the next zombie generation (same World)

Parent original World: [Draft #773](https://github.com/rinsakamo/relay-self/pull/773), HEAD `97121e931eea1e2b616ac0c21059c135c9e23cc8`, verified second fresh natural zero-drop World [#42349591164](https://github.com/rinsakamo/relay-self/actions/runs/42349591164) SUCCESS. Both #772 and #773 independently had exactly one genuine original S49 ATTACK, Paper death, rotten_flesh=0, world 600-tick respawn, zero MOVE, no EAT. Neither is reissued or recast as failed.

## Requested behavior

A **real zero rotten-flesh drop** is a complete experience, **NOT** a STOP condition for Self: record death and native inventory, WAIT for the actual Paper-owned 600-tick next zombie, reobserve native entity, COMPLETE prior Intent, COMMIT next Intent and **rearm SAME original S49 ActionSupervisor** without losing old S16 terminal Action IDs. Repeat for newly generated zombies in same session/World until a substantive actual safety constraint (death, unknown Action, loss of source, physical STOP obligation etc.) blocks.

For real positive naturally dropped rotten flesh, S49's existing D6 native item geometry can propose the **same original supervised physical MOVE** through C1 preISSUE journal; genuine Paper item UUID and native inventory increase must independently confirm pickup. After any MOVE, leave `_post_move_settling_unqualified=True` and STOP the experiment without EAT until valid S50 effective-release/continuous tick coverage is available. Do not treat S15 clear_ACK as physically stopped.

The DEV **CI experiment** deliberately restricts this first sample to at most four World generations because it is a one-use bounded test, **not a goal/epoch limit imposed by Self policy**. Existing `NormalSessionActionExecutor(max_intent_epochs<=4)` is a bounded DEV admission gate and not presented as an indefinitely running runtime. User's actual design goal is continuity while alive and resourced, not a four-generation policy; production unbounded runtime is NOT claimed here.

Operator only places genuine Paper-respawned zombie 2.2m behind Self and sets it to NoAI/Health0.8 for each generation. No operator-created meat, /give, forced drop probability, hunger stimulus, self-teleport or player movement. Paper's actual `EntityDeathEvent`, `ItemSpawnEvent`, `EntityPickupItemEvent`, managed 600 tick generation, source order and UUID remain authoritative external source, never fed as SelfWorld's private oracle.

Every actual ATTACK and MOVE has its own distinct original Action ID and fsynced preISSUE reservation in same-session **ATTACK nonmotion** and **C1 MOVE** ledgers, respectively. Both ledgers must be preflighted empty/clear before disposable World. Never replay uncertain Actions, never create a second S49 issuer, never clear previous terminal Action history. Independent read-only post-audit verifies each generation's Paper managed spawn/death/killer UUID/tick, natural rotten drop, native source and Intent epochs, original S49 terminal action order and journal identities, genuine item pickup if positive, 600tick intervals and cleanup. No global exactly-once, autonomous target strategy, post-MOVE EAT or learning benefit claimed.

### Gate

1. Offline focused native/Paper/old D4/D5/D6 regression + source-negative tests, pinned Paper plugin build, `ruff`, no World.
2. Independent docs-only exact source-HEAD trigger: at most one pinned Paper 1.21.8/Mineflayer 4.39.0 real World, at most four genuine zombie deaths and four item-directed MOVEs, distinct original scoped per-generation grants. Source artifact always preserved with report, original Paper log, ATTACK/MOVE physical ledgers, read-only audit and SHA256SUMS.
3. Stop on verified genuine pickup (EAT fenced), missing actual source, UNKNOWN action, player death or explicit CI generation limit; nothing is silently retried. Both zero-drop and positive-drop paths are valid physical RNG observations.

**Status pre-real-World:** `DEV_ONLY / D6_D3_MULTIGEN_PREWORLD / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
