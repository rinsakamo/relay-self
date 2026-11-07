# D6-B DEV — Ground-item candidate → ONE original S49 fenced physical MOVE

Parent: [D6-A Draft PR #769](https://github.com/rinsakamo/relay-self/pull/769), exact parent HEAD `362deb5b5178e80a4eb6bf85de7900f0a4eb1c84`. Earlier [D5 #768](https://github.com/rinsakamo/relay-self/pull/768) genuine one-World evidence is retained unchanged, not combined into D6 qualification.

## New explicit DEV-only owner seam

The **existing** `NormalSessionActionExecutor` now has `require_d6_loot_move_authorizations` and `execute_d6_loot_move`, taking:

- A recomputed, source-only `D6LootApproach` and the original correlated native W4-orientation probes with exactly one stable item, no zombie/other entity, bounded distance and backward-facing corridor.
- Two independent, one-use `NormalLootMoveAuthorization` PROPOSE and ISSUE grants scoped to the **same** Intent, session, item ID and exact native seq/request; the typed grants themselves do not attest the operator/principal.
- A required `OriginalS49PhysicalFence` (C1 MOVE-only ledger), fsynced `PREPARED_UNRESOLVED` before the **original** `ActionSupervisor.issue` and before Mineflayer IO. No unfenced invocation.
- The original `SkillExecution` / `ActionLifecycle` / original `ActionSupervisor`, existing S15 `MOVE_BACKWARD` 0.2s `set_control`, `clear_controls` and before/after native probes; existing S16 interpretation and the exact physical C1 seal. A failed/undetermined transport keeps Action UNKNOWN and journal unresolved, never silently reissues.

This is deliberately a **narrow Action-level DEV admission**, like the current S49 ATTACK/EAT seams: it does **not** assert that the generic S14 candidate/route adjudication for `COLLECT_LOOT` is complete. In particular it must not impersonate zombie-target `MOVE_AWAY` or rewrite old `NormalActionAuthorization`. No new supervisor or backend physics exists.

The resulting S16 MOVE outcome proves a bounded actual movement, **not** successful PICKUP, natural drop identity or ItemSpawn relation. A later caller must correlate actual Paper ItemSpawn/Pickup UUID, timestamps, native inventory increase and a motion toward the item. Existing `_post_move_settling_unqualified` is set and EAT remains forbidden until an independent native/WorldBody settling owner qualifies it, not just `clear_controls`.

## Offline qualification / boundaries

The tests execute S15 against a fully scripted typed native session with exact original Action ID/S16 and C1 ledger restore. They include stale/foreign grants, a forged item candidate, pre-ISSUE I/O refusal (Action0/native IO0), transport failure (one attempt→S16 UNKNOWN, ledger unresolved on restart), and explicit post-MOVE EAT prohibition.

**No real World yet.** Next bounded experiments need an explicit W4-orientation opt-in and a purpose-specific disposable World. A staged-item one-World run can only prove movement-to-staged-item, not a genuine zombie drop; a second proof must use actual Paper natural drops and true item-pickup identity. After physical STOP qualification, permit a separate EAT admission; do not bypass the present post-MOVE fence.

`DEV_ONLY / D6_B_ORIGINAL_S49_LOOT_MOVE_OFFLINE_ONLY / WORLD_NOT_RUN_D6 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
