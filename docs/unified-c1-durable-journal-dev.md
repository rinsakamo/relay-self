# Unified C1/S10 durable journal — DEV v0

## Exact boundary
This child extends successful two-Intent physical #760; it does **not** change the original S49 Action issuer, the L0 risk_weight policy, Minecraft world physics, or the existing Persistent Cognition schema (identity, Memory, appraisal). The new file `src/relay_self/c1_motion_journal.py` is a persistence *backing* for the **same original S49 Intent/C1/S10 owner**, not a new Memory authority.

**Persisted together, one atomic fsynced JSON snapshot:**
- C1 `experience_id`, native session, Intent, distinct original S49 Action IDs, selected decision-probe sequence, source-binding SHA256 and outcome comparison;
- preceding/predicted motion and after-revision/value, one ordered ledger entry per completed Intent;
- exact current bounded `LearningPreferenceState(target_id='motion_decimeters')`, including its most recent original `LearningCommitRecord` (feedback, authority, provenance and revision).
- Schema version 1, deterministic checksum, file fsync, atomic replace, parent-directory fsync, Linux advisory exclusive lock, stale-writer checksum CAS.

A journal may be restored with an existing history; original S49 then uses **that** S10 retained revision for the next *new* World/Intent (not a re-run of the previous World). Historical entries stay in order. If the checksum/identity/chain is corrupt, the path is symlinked, a concurrent writer advanced it, or an earlier Action/Intent/experience identity reappears, restore/commit fails closed.

### Critical caveat: durability vs physical exactly-once
There is **no durable physical Action write-ahead fence** in this slice. Crash **before** the atomic C1+S10 commit can leave a real-world S16 outcome and a not-yet-recorded learning state. The original Intent is terminal and that process does not issue another Action; however a restarted process may not independently reconstruct that missing physical outcome. That is not evidence of automatic Action retry permission. An explicit Action write-ahead ledger and recovery/UNKNOWN reconciliation are needed before restarting continuous physical sessions autonomously.

A checksum is a corruption detector, not a cryptographic independent witness. A restored journal can reconstruct S10 owner lineage; it cannot independently attest a Minecraft World event or physical Goal success.

### Physical DEV entry
The existing `--unified-c1-dev --unified-c1-two-intents-dev` requires the extra `--unified-c1-journal-dev` and `S49_C1_JOURNAL_DEV_ONLY=1`, distinct from the original S49 World gate. Journaling occurs within the original C1 closure **before** retaining the new state in memory. The original owner uses that exact new object for the next Intent. At the end of the same physical World, the runner reopens the journal and verifies exact S10 owner equivalence, two newly committed experiences and any pre-existing history.

A one-use GitHub Actions workflow separately checks:
- original native MOVE before/dispatch/clear/after for all three Actions;
- two original C1 experiences and S10 revisions;
- a **separate Python process** recovering the durable journal and its two IDs / revision;
- original report, World log, durable file and SHA256 manifest (also on failure).

### Next architecture step
- Keep the general Persistent Cognition 60-second autosave and the C1 journal's higher-frequency terminal commit separate until an explicit, versioned owner-coordinated checkpoint is designed. No general schema migration is claimed here.
- Existing Paper 600-tick zombie respawn is a World-side physical rule. It is currently driven by death/respawn, while the C1 S49 test only MOVE responses to operator-staged zombies; connecting it to autonomous ATTACK/EAT and Intent cycles requires a separate source-bound World trial without making Self rewrite the World rule.

Classification: `DEV_ONLY / DURABLE_C1_S10_OWNER_SIDEcar / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
