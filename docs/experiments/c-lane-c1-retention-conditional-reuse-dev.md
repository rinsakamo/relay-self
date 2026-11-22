# C1 Intent Retention → Original Memory → C3 Reuse (C Lane DEV, 2026-11-22)

## Source and lane ownership

- C-only stacked Draft PR #1108 starts from I1+C+I4a integration #1076 at exact pinned parent `531a9b72b3ac23d8987d179653f33836f142f079`.
- Original Owner: `CheckpointedCognitiveOwner` / `CognitionOwnerCohort`; canonical cognition persistence `PersistentCognition` and existing `save_persistent_cognition`; original physical `PhysicalActionJournal`. No C-owned DB, second cognitive runtime, physical issuer or GPU worker.
- C child readouts: `BoundedSkillRead` / `assemble_bounded_skill_experience`. The original intent event history, original owner skill-run membership, actual WAL Action IDs and original session determine which child readouts can be joined.
- C1 marks **one terminal, actually executed original Intent** with all its executed children. This rejects deferred/unexecuted and unfinished SkillRuns, foreign Self/source/session, missing children, unresolved original WAL, and any Action ID not in the current owner's canonical WAL. S1 historical rows never silently attach to another Intent's new S2 execution.
- A stored C1 includes original Intent/Skill/Action IDs, before/after source references, learned target outcome **separate from primitive Action terminal result**, WAL status (including NO_PROGRESS), and historical Owner/WAL scope. UNKNOWN remains UNKNOWN. Duplicate Intent memory ID is refused.
- `OriginalWalPrefixPin` is required to check an earlier prefix against a changed/rehashed full canonical WAL. **The pin's author and previous capture time are not authenticated** by this module. An attacker that can rewrite both WAL and the earlier pin defeats this CPU consistency test; Q must authenticate an independent earlier external receipt.

## C1-R persistence, checkpoint and uncertainty

- `propose_intent_memory` creates an existing typed `Memory`. This is a candidate, not Self adoption.
- `retain_original_intent_memory` runs under the **existing** cohort lock, checks original Self/native session/World, source lineage, original Owner/Intent unchanged, current WAL unchanged since assessment, duplicate Memory and existing disk-vs-Owner consistency, then invokes `CheckpointedCognitiveOwner.retain_memory`, existing save and readback.
- Disk failures or mismatched readback **quarantine the original cohort** rather than representing acceptance as certain. The module does not create a separate C storage path.
- Existing B `CognitionOwnerCohort.close/freeze/rebind/release` and typed owner-cut handling are exercised with two synthetic Self owners: A retains C1 and B remains independent, frozen generation uses original `cognition_file` and `owner-state.json`, fresh reJOIN keeps old source as historical, and new current cues are required for C3. This proves an offline integration path, **not independently attested real-world rollback or complete external restore**.
- **Missing for genuine adoption:** a certified source-qualified Self decision that intentionally accepts this memory; an independent historical WAL checkpoint pin with trusted custody; a full World+A/B restored-generation audit. The caller's `integration_provenance` is not an authorization token.

## C2 and C3

- C2 is the existing `propose_c2_understanding` fallible, provenance-bearing understanding candidate, and `RetainedRevisionRead` accepted owner revision contract. No automatic L2 truth adoption.
- C3 parses original retained `c1-intent:` Memory with stable keys, rejects foreign Self/World, historical UNKNOWN or non-success as a **positive reuse claim**, known unreconciled counterexamples and any mismatched/missing current cue. Uses existing `assess_conditional_reuse` for current revision, viability, guard, budget, counterexample and accepted C2 ownership checks.
- Absent accepted C2 retained revision, the only positive output is `SHADOW_REUSE`; it is never executed. `CognitionDatum` decorates the **unchanged** prebound L1 choices. No target parameterization or additional physical capability.
- The source session in retained Experience is always historical; old session cannot substitute for a new Native/Paper observation.

## Validation and evidence categories

- CPU/offline hostile tests use typed original Intent, Skill, Action and an explicitly synthetic canonical Native WAL with 3 sequential settled MOVE outcomes; the fixture's WAL write is **test-only**, never a production physical issuer.
- Test cases include same-Intent duplicate, foreign Self, old session, two-Self checkpoint, next-session reuse, stale/current source mismatch, world mismatch, unknown critical cue, counterexample, unattempted Intent, incomplete child, source+Memory CAS drift, WAL row rewrite with valid recalculated checksum, and disk readback uncertainty.
- Run exact-head pytest, Ruff, repository contracts, Mineflayer and Paper witness on GitHub Actions; report HEAD/results in PR #1108 and Issue #839 after CI.

## Explicit restrictions

`C1_ORIGINAL_INTENT_RETENTION_CPU_OFFLINE_DEV` may be reported **only if exact-head tests pass**. `C1_R_REAL_SELF_ADOPTION_HOLD`, `C1_AUTHENTICATED_WAL_SOURCE_HOLD`, `C1_ZERO_ACTION_REST_HOLD` (special physical-free observed attempt not connected), `C3_REAL_WORLD_REUSE_HOLD`, `L0_INSTALL_NOT_RUN`, `QUAL_NO_GO`, `SCIENCE_NOT_RUN` remain.

B #1050 owns true Memory/Checkpoint adoption; I #1061/#1076 owns live Original Owner, S1→S2 and Native/Paper World execution; Q #1088/#1089 independently checks historical producer custody, checkpoint, source and exact-run integrity. Do not promote this C-supplied pin or synthetic source claims as Q-audited real evidence.

## C1-R original physical quiescence + typed external fork (follow-up C1q)

- Two additional **opt-in C-only** adapters `assemble_quiescent_original_intent` and `retain_quiescent_original_intent_memory` require the existing `PhysicalIssueAdmission`, its resident opt-in, current native session, no active Action leases, and the original `CheckpointedCognitiveOwner.cohort.lock` before the existing physical quiescence window. They nest **original Owner → original issuer → canonical WAL** in the existing order; no new lock, WAL store, physical lease or authority. In-flight Action, stale physical native session and poisoned issuer reject without Memory write.
- Parent Intent aggregation no longer treats a mixture containing UNKNOWN as observed PARTIAL; UNKNOWN remains conservative. Conflicting independently known child outcomes can remain PARTIAL.
- The new CPU/offline integration regression uses the **existing** `CoordinatedAutosaveRuntime` to commit a full typed World+A/B generation with original B hooks, original Owner cognition files, physical WAL and owner-state. It then invokes `restore_generation` to fork a new World+Self location, `staged_recover_cognition_cohort` to read the original B owner type, and a separate Python interpreter to verify A has the historical C1 Memory while B remains isolated. It asserts no replay, no physical issue authorization, fresh Native requirement, and rejection of a byte-tampered archived Self even if its JSON remains parseable.
- The simulated World stop/restart and Native reJOIN callbacks remain supplied synthetic receipts. **The tests do not authenticate real Paper process stop, real World cut, actual new Mineflayer source, or real Self Memory adoption judgment.** This is broader typed CPU/offline integration than the prior `close/freeze/rebind/release`-only test, not real World attestation.
- C3 remains a read-only shadow unless B/I supplies a genuine prior accepted C2 owner revision and current source/viability; this module does not install or choose any Action.

### Admission recheck and same-Intent S1/S2 adversarial controls

The opt-in physical-issuer retention call now **requires the actual bounded
SkillRun readouts and the previously supplied original prefix pin again**.
While the original Owner and original Physical issuer are locked in order, it
reassembles the parent C1 Experience from the current original Intent/Skill
history and the canonical WAL, then compares the resulting typed readout to
the proposed candidate **before** invoking B's native Memory retention API.
Caller-created or modified C1 dataclasses, altered Target outcome, changed
readouts, a busy issuer, a different session, and an already held/quarantined
Owner cannot silently become a retained original memory.

A separate synthetic fixture adds a second settled SkillRun S2 with independent
Action and Native sequence after S1 under one terminal original Intent. C1
remains **one parent Intent Memory**, with both SkillRun/Action lineage sets;
mixing a SUCCESS child with an UNKNOWN child yields overall UNKNOWN (not
optimistic PARTIAL or SUCCESS), and swapped S1 Action refs are rejected.
The fixture has explicitly synthetic source receipts; a real producer/witness
and the genuine Self acceptance decision remain external B/I/Q gates.
