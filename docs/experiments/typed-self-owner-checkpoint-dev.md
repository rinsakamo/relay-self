# P0-D #860 — Typed Self owner checkpoint v0.1 (stage 4 DEV)

Stack: P0-C #859 → P0-D generation #861 → runtime barrier #862 → owned Paper adapter #863 → this change. This is a **bounded typed owner persistence slice**, not a complete live multi-Self recovery.

## Why

Prior generation bundling stored an opaque owner-state.json with no schema or cross-Self validation. Saving bytes alone did not establish that a Self could recover its Goal/Intent/Skill/learning state, or that A and B shared a consistent delivered-message cut.

## Implemented typed, source-owner reuse

- Existing PersistentCognition remains the canonical separate saved file for Identity/SOUL, retained Memory and appraisal dispositions. The existing physical Action WAL is captured separately and is **never replayed**.
- SelfOwnerCut holds a source World, original branch, generation ID, old native-session ID, last observed World tick, **existing IntentCommitment event history**, SkillExecution event histories, **existing PatternRegistry with learned and innate SchemaPattern definitions**, completed peer-message receipts and unresolved Question refs.
- Intent history rehydrates solely through the existing IntentCommitment public transition methods. Illegal order/time/duplicate Intent changes are rejected.
- Skill histories are reconstructed via validated SkillExecution transitions; a STARTED Skill is **inert** after restore and never automatically receives Action issue/resume authority.
- Saved PatternRegistry is reconstructed through existing validated data types, not executable/generated Python source. No new Skill capability or physical permission is conferred by learning.
- PeerDelivery is a **completed** message between roster Self identities. Both sender and recipient Self must save identical message ID, ticks, payload reference and participants. One-sided deliveries and unpaired peer observations reject the entire generation. In-flight/unacknowledged messages must be drained or fenced *before* capture by the runtime barrier.
- save_self_owner_cut writes exclusive fsynced generation-scoped JSON envelope with SHA256. Invalid digest or semantically impossible content is rejected.
- capture_typed_generation reuses stage-1 World/Self bundling but inserts a **typed cohort precommit validator** BEFORE the final COMMITTED.json marker. An invalid or partial cohort cannot become a committed typed generation.
- verify_typed_generation revalidates the original bytes and typed cross-Self semantic cut. A legacy opaque generation cannot masquerade as typed owner recovery.
- prepare_typed_owner_restore validates the same generation on a fresh World fork, compares recovered state to the archived cohort, and returns inert owner candidates with no old Skill, message or physical Action replay.

## Clock and cut assumptions

Host event at_ns and World tick are distinct clocks. Saved owner Intent history preserves original event times; runtime scheduling, current Present, fresh WorldBody session and monotonic time need separate reevaluation after restore. Small save-time skew is allowed; this does NOT excuse a delivered message without a matching peer receipt, Action still in PREPARED_UNRESOLVED, or an unmatched cohort.

## Still outside typed v0.1

- Real runtime Goal owner beyond IntentCommitment, multi-Goal plan and execution arbitration, custom Skill graphs, Log Memory/event indexing, full communication payload transport state, transport ACKs, Recent3SelfView (not a canonical writable owner here), Body/World lease state, SchemaSnapshot module activation and actual current Present cannot be reconstructed by this codec.
- `pending_question_refs` are references only and are not proof of the full Question content being persisted elsewhere.
- Full Self owner reactivation, physical action grants, stale GPU result cancellation and live Paper 1.21.8 actor sessions are not implemented by this slice. Rehydration is inert and requires fresh observation/reassessment.
- The generic stage-1 API retains a legacy opaque DEV option for existing tests; **only the explicit typed capture/verify/prepare entrypoints qualify typed cohorts**. Never promote a generic COMMITTED marker alone to a typed owner qualification.

## Offline acceptance tests

- Two Self A/B committed message and distinct learned Schema state save/restore, later World + A Intent changes discarded, no replay.
- Missing B, mismatched message, wrong generation, duplicate native session, foreign peer, tampered hash, recomputed hash with impossible Intent history: REJECT or HOLD before typed COMMIT.
- Legacy opaque generation explicitly fails typed verification.
- STARTED Skill materializes as a record only; no automatic continuation.
- Corrupted/foreign restored branch receipt blocks owner rehydration.

## Next owned runtime integration

Wire the *existing* close/freeze/rebind barrier to typed Self owner snapshots and typed precommit verification, using real Self owner revision fencing, then implement missing owners and real two-Self Paper save/crash/restore. Preserve the 60-second cadence, small skew allowance, wholesale discard of later histories and no replay. No QUAL or SCIENCE promotion from offline tests.

Classification on exact-HEAD green CI: TYPED_SELF_OWNER_CUT_OFFLINE_DEV_PASS / FULL_SELF_RESTART_NOT_ATTESTED / REAL_PAPER_60S_AUTOSAVE_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN.
