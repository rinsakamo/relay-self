# #860 — Owner-backed multi-Self autosave seam (P0-D next slice)

Status: **offline actual cognitive-owner objects**, not real Minecraft 1.21.8/Gemma or complete Self persistence. Stacked on #864.

## Scope

- Preserve user policy: 60-second autosave cadence, whole World and **all** Self as one committed generation, discard all post-cut history, **no replay**, and tolerate small save-time skew. No new UUID matching.
- Integrates the **existing mutable** PersistentCognition, IntentCommitment, SkillExecution, PatternRegistry, PhysicalActionJournal, ActionSupervisor into `CheckpointedCognitiveOwner`. These are not reimplementations of the semantic owners.
- `CognitionOwnerCohort` has one in-process reentrant lock and shared admission gate for its *own* cognition and delivered-message mutation methods. `delivered` records a completed peer exchange for sender and recipient atomically in that cohort. Undelivered messages cannot enter that ledger.
- `close` fences cohort mutation first, then calls an **external** physical Action issuer closure and requires a no-in-flight receipt. This receipt is not independently authenticated. `freeze` checks actual `ActionSupervisor.open_actions`, on-disk physical journal `require_clear()`, captures current owner object state and writes/reads back PersistentCognition plus typed owner file scoped to the generation.
- Reuses **strict_typed_owner_cut** in the existing 60-second runtime to check all Self roster/pairwise communication before committing the World+Self generation.
- Rebind hooks require externally attested new native session, old session fencing, cancelled GPU tasks and stale transport disposal. After rebind, the old native session is refused by the facade. No physical issue grant is generated.
- `staged_recover_cognition_cohort` verifies restored generation and materializes inert **actual** Intent/Skill/learning owner candidates plus retained PersistentCognition, while keeping native-session-bound=false / fresh-WorldBody-required=true / physical-action-issue-authorized=false. This does NOT start Self cognition or deliver stored messages.
- Failures leave global admission closed, including if the external Action issuer refuses to fence, even if a generation already reached COMMITTED.

## Offline tests

`tests/test_checkpointed_cognitive_runtime_dev.py`: genuine existing Intent/Skill/Cognition objects are mutated to form A and B, completed A→B message delivered, typed cut captured with a stub World process, then new A/B memory/learning and B→A message occur. A World Zombie is altered after the cut. Recovery from the prior generation brings back the earlier World bytes and both earlier Self states, no new skills or messages, no replay. Also test stale native observation, owner mutation while paused, missing external physical gate, incomplete rejoin, duplicate peer receipt and inert STARTED Skills.

## Remaining blockers for REAL autosave

The existing real physical ActionPort, native Mineflayer sessions and the complete multi-Self cognitive owner (Goal graphs, Log/Structured Memory, Recent3Self, Schema activation, persistent message transport, running Skill IR and timing) are **not yet wired through this facade**. Its lock cannot stop a direct call into those other modules. The physical admission fence/rejoin providers are external callback contracts, not independent attestation. The stub World in tests is not Paper. There is no installed unattended host loop here.

Before promoting beyond offline DEV: wire source physical gate to the existing ActionPort, serialize every deployed Self semantic owner, use server-source tick and real Paper save receipts, and prove two independent Self sessions and both causal memories roll back after a crash while no stale native/GPU/Action payload crosses the boundary. Keep original evidence and branch separate. Qual and science are NO GO.

Evidence classification: `OWNER_BACKED_MULTI_SELF_CHECKPOINT_OFFLINE_DEV_PASS` **only when same-HEAD CI succeeds**, `FULL_SELF_RUNTIME_RESTORE_NOT_ATTESTED`, `REAL_PAPER_AUTOSAVE_NOT_RUN`.
