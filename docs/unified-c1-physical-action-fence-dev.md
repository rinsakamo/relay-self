# C1/S10 original S49 physical pre-ISSUE replay fence — DEV v0

## Ownership and the exact durable boundary

This is a child of #761, which established two real Intent experiences and S10 revision 0→1→2 with a durable C1 journal. The new `OriginalS49PhysicalFence` is **not an Action issuer**. The only physical issuer remains the existing `NormalSessionActionExecutor.execute()` and its original `ActionSupervisor`.

`NormalSessionActionExecutor.execute(..., pre_issue_reservation=...)` adds one optional DEV-only synchronous hook, invoked **after** the normal original S14 admission/propose authorization, but immediately **before** `supervisor.issue()` and **before any Mineflayer send IO**. When disabled it has no effect. When enabled, the original S49 caller fsyncs a durable `PREPARED_UNRESOLVED` ledger record containing Self ID, session, current Intent, Action ID, native choice probe sequence/request/provenance and exact MOVE_BACKWARD command kind.

No logical/physical uncertainty is erased merely because `supervisor.issue()` did not appear in a surviving in-memory report. In a crash window after PREPARED, the World may or may not have received the command.

After a verified original S16 OUTCOME, the SAME S49 owner validates the original supervisor-held **identical terminal object**, current Intent, original Mineflayer decision provenance, S15 original before/set_control/clear_controls/after sequence and native movement, then atomically changes the durable entry to `S16_OUTCOME`. If a dispatch, result, cleanup, callback, crash or disk write fails, the persistent entry remains unresolved and **any next Action or new World must STOP**, with no automatic reissue.

On process restart, original S49 checks any existing pre-ISSUE fence **before provisioning a new Minecraft World**. `PREPARED_UNRESOLVED` blocks that World as `BLOCKED`; valid `S16_OUTCOME` entries can be retained for exact (session, Action) replay rejection while a *new* World obtains a new original native session. JSON payload uses deterministic SHA256 checksum, Linux advisory lock + CAS, file fsync/atomic replacement/parent-directory fsync from the existing C1 owner journal implementation. Symlinks/corrupt histories/forged states/collisions and stale writers are refused.

## Recovery and limits

This is a bounded DEV **reissue prevention fence**, **not** physical exactly-once delivery and **not** automatic reconciliation. Neither a lost command nor an actual Minecraft movement can be inferred from an unresolved PREPARED entry; the original current session may no longer exist. A human can inspect separately witnessed immutable World evidence, but this implementation does not unilaterally authorize resolving uncertainty.

The C1 learning journal and the physical pre-ISSUE fence are **two separate atomic files**. Cross-file failure between S16 outcome sealing and C1/S10 experience commit must remain terminal/UNKNOWN rather than automatically resumed. The general Persistent Cognition Self ID/Memory/appraisals snapshot is unchanged. A successful future World is only DEV evidence, not independent World truth, physical exactly-once, learned L0 policy change or qualification.

Existing Paper 600-tick zombie respawn is World-only and death-triggered. A MOVE-only C1 test cannot autonomously force that World event. Integration with original S49 ATTACK/EAT/REST and self-driven Intent cycles remains a separate step after the physical replay fence.

## DEV single-World integration

Additional gated CLI `--unified-c1-physical-fence-dev` requires `--unified-c1-dev --unified-c1-two-intents-dev --unified-c1-journal-dev` and `S49_C1_PHYSICAL_FENCE_DEV_ONLY=1` on top of all original S49 World grants. No new provider or physical issuer is introduced.

One-use workflow requires an exact source-pinned trigger. It checks the original WAIT→MOVE→MOVE and third next-Intent MOVE, all original S16 and native sequences, two C1 experiences, durable S10 restoration, **separate-process recovery of all three PREPARED→S16_OUTCOME physical Action records**, then archives original World log, source report, both durable snapshots and SHA256 manifest. Failures have no automatic retry.

Classification before physical evidence: `DEV_PARTIAL / ORIGINAL_PREISSUE_FENCE_OFFLINE_PENDING / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
