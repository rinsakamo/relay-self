# Unified v0.5 DEV — ATTACK/EAT original S49 pre-ISSUE durable physical fence

Parent: [Draft PR #765](https://github.com/rinsakamo/relay-self/pull/765), pinned `ad8218c0519b725bcde050cb0512a9b117d78d7e`. This child adds type-specific physical uncertainty protection while retaining the **same** D5/C1 original `NormalSessionActionExecutor` and `ActionSupervisor`. No new issuance owner or authorization issuer exists.

## Original physical Action boundaries

`execute_attack(..., physical_fence=...)` and `execute_eat(..., physical_fence=...)` are optional explicit DEV paths. The executor first verifies original native S49 source and independently scoped PROPOSE/ISSUE grants. It then atomically fsyncs a `PREPARED_UNRESOLVED` row (exact original Self-owner file identity, session, current Intent, original Action ID, native probe seq/request/provenance and action-specific target) **before** `ActionSupervisor.issue()` and any adapter IO. Any I/O/disk/authority failure before the reservation prevents Action ISSUE. A prepared row must remain UNKNOWN until a verified original S16 terminal closes it. No auto-retry, no speculative replay, no silent ledger reset.

- **ATTACK closure:** Require same-original-supervisor terminal object in OUTCOME, matching original Intent/Action, native probe/target ID, `attack_entity` applied ACK, and verified subsequent native probe. This proves command delivery to the Mineflayer adapter boundary, **not target damage, death, loot or kill attribution**. `death_attested=false` is structural and cannot be upgraded by this ledger.
- **EAT closure:** Require same-original-supervisor terminal object in OUTCOME, exact original `EatChoice` source and food item, separate native `equip_item` ACK, `consume_held` ACK, correlated after-EAT probe, improved food and reduced inventory count. The original S51 issued executor now retains the two typed child receipts and after probe in its original `EatingActionReceipt`; fields are optional for older read-only receipt consumers, but **mandatory** to seal a durable EAT.
- Both use the C1 durable store primitives (file lock, compare-and-swap, canonical JSON+SHA256, file and directory fsync, atomic replace). The new `OriginalS49NonMotionFence` is a physical sidecar, **not C1 S10 training or a new Persistent Cognition owner**.

## Crash boundary and safety

- On restart, the caller MUST `OriginalS49NonMotionFence.restore(path, self_id=...).require_clear()` **before provisioning another World**. An unresolved `PREPARED_UNRESOLVED` is a permanent STOP/UNKNOWN until independently audited and explicitly reconciled in a separate future design. This child does not provide a manual reconciliation bypass or infer absence of physical effects. Every additional Action requires a different native source and Action ID.
- The legacy MOVE fence `OriginalS49PhysicalFence` and C1 motion journal are **separate atomic files**; this child does not create a cross-file transaction, nor grant physical exactly-once semantics. In particular, ATTACK/EAT native outcome rows must not be matched to C1 motion Action lineage or treated as motion feedback.
- Original D5 source and test workflows still invoke the **unfenced default** unless they explicitly pass `physical_fence`; code integration is **not** a proof of protected D5 physical World execution. D5's uninterrupted single-session resumption and S49 owner restrictions remain unchanged. Existing C1 post-MOVE settling barriers still block unqualified EAT.
- This child does not run a real World, select a Goal/Plan, update a combat/food policy, create an infinite survival cycle, add a daemon, or claim SCIENCE/QUALIFICATION. It lays down the required action-specific durable safety contracts before a separate single-use integration World.

## Offline qualification

`tests/test_s49_nonmotion_physical_fence.py` includes original ScriptedNativeSession ATTACK/EAT terminal, cross-process restart, fail-closed missing EAT child effects, genuine native rejection→UNKNOWN, stale CAS, duplicate Action, source/corruption/tampering, and pre-ISSUE disk failure stopping the issuer before native IO. Runs beside original D5 ATTACK/EAT/C1 MOVE tests in `.github/workflows/unified-v05-s49-nonmotion-fence-offline.yml`.

**Classification:** `DEV_ONLY / S49_ATTACK_EAT_PREISSUE_FENCE_OFFLINE_PENDING / JOINT_REAL_WORLD_NOT_RUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
