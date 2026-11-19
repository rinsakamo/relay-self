# C Lane v0.1 — bounded SkillRun learning handoff (DEV)

**Status:** offline owner-snapshot adapter; no real Paper/WAL verification, automatic Learning adoption, GPU inference, L1 decision difference, QUAL or SCIENCE.

## Source-of-truth audit

- `main` has `IntentCommitment`, `SkillExecution`, `ActionLifecycle`, `PersistentCognition`/`Memory`, and existing snapshot save/load. No new Memory owner is needed.
- Draft [#840](https://github.com/rinsakamo/relay-self/pull/840) is **not merged**. It carries v0.1 C1–C4 proposal and guarded C3 reuse, stacked on #838 → #836 → #834 → #832 → #830; this C branch stacks **directly on #840 HEAD 521fe04b**.
- The older #840 C1 contract models a *terminal Intent*. Architecture #828 §22 and issue #839 later adopted **one executed bounded child SkillRun** as the C1 unit even when its parent Intent remains active. Do not promote the older terminal-Intent restriction to the new adapter.
- [Stage27 #951](https://github.com/rinsakamo/relay-self/issues/951): latest reviewed Draft [#990](https://github.com/rinsakamo/relay-self/pull/990), stacked on #979, HEAD 4d13c70b. Native PLACE MOVE, STOP, settling and canonical WAL owners stay there.
- [Stage28 #966](https://github.com/rinsakamo/relay-self/issues/966): latest reviewed Draft [#988](https://github.com/rinsakamo/relay-self/pull/988), HEAD a8be2f7a. World + A/B cohort restore, Paper/native fresh-session admission and checkpoint ownership stay there.
- C Lane neither depends on nor modifies Stage27/28 branches, executable World or their checkpoint/WAL code. It imports only the inherited #840 contracts and original main owners.

## Current dataflow (not a scheduler)

```text
Original IntentCommitment (one parent; may remain ACTIVE)
  └─ SkillExecution (executed bounded child, terminal)
        ├─ ActionLifecycle[] (ISSUED then terminal)
        ├─ source-scoped original WAL readout[]
        ├─ before/after WorldBody observations + clock domain
        └─ independent TargetRead, optional pre-action prediction
            → assemble_bounded_skill_experience (read-only C1 candidate)
                → propose_existing_memory (native Memory candidate, stable ID)
                    → **Self OWNER policy/acceptance only**
                        → PersistentCognition.retain_memory
                           → existing save/load/checkpoint persistence
                            ↘ C2 UnderstandingDraft (hypothetical only)
                            ↘ C3 original candidate + retained C2 revision
                              + current source-qualified cues
                              → unchanged finite L1 BoundedChoice[]
                                + optional read-only CognitionDatum
```

C1 event key: SHA256 of `[self_id, world_id, world_session_id, child_skill_execution_id]`. Native `Memory.memory_id` is stable across repeated Outcome/readout and checkpoint reload; duplicate retention is rejected by the original `PersistentCognition` owner. This is **not** a concurrency-safe/CAS persistent dedup ledger; simultaneous owner writes require the real single-owner revision protocol. No new store is introduced.

### C1 decisions and missing proof

1. Original Self identity, Intent commit and terminal Skill lineage must agree; `ActionLifecycle[]` each references the exact child execution and Intent, has an ISSUED event, and is terminal. Multiple actions produce **one** child experience. A second executed child is a separate experience.
2. WAL refs must have an exact Action ID bijection, same World/session and terminal dispositions corresponding to the original Action lifecycle. `PREPARED_UNRESOLVED`, nonterminal or unissued inputs **HOLD**, without declaring physical failure or success.
3. Before/after must be original WorldBody readings with comparable clock domain and forward time/sequence; a new native session cannot silently continue old-session evidence. Foreign Self or World is rejected.
4. `ActionState.OUTCOME`, `SkillState.SUCCEEDED`, or terminal WAL are **not** Goal/Target success. Known Target evaluation needs an independent, after-linked `TargetRead`; absent evidence yields UNKNOWN. Earlier prediction is optional, never fabricated post hoc.
5. These are **input admission checks, not an independent WAL/source verifier**. A caller can fabricate a `WalActionRead`. Real C1 qualification remains HOLD until Stage27's canonical WAL verifier and Stage28's fresh-session/epoch readback are integrated via a read-only source-verification gate, and any original readout independently attested. No existing World original was opened by this slice.

### C2/C3 limits

- C2 only structures source refs, a prior prediction ref, lens, interpretation, hypothesis, uncertainty and counterexample references. All resulting text remains `HYPOTHETICAL`; no model invocation, inferred World fact, owner write or Skill generation occurs.
- C3 only considers `ConditionalReuseCandidate` from #840 if the original Self's `PersistentCognition` actually contains the C1 key and `assess_conditional_reuse` accepts the current cues, sources, Owner revision, viability, budget and absence of contradiction. It creates `CognitionDatum` to attach at the **existing L1 candidate/context construction seam**; the original `BoundedChoice[]` is unchanged. No L1/GPU is invoked, and no parameter, Action authorization or L0 installation is gained.
- A/B no-retention vs retained-C1 + accepted-C2 may differ in *availability of a contextual readout*, not yet in an actual Gemma choice or World outcome. `CHEAP_EQUIVALENT` is an allowed result. No hard-coded MOVE physics is inferred.

### Follow-up slice (separate PR)

Make a strict read-only bridge from Stage27's **independently verified** canonical WAL/physical TargetAssessment to `BoundedSkillRead`, with complete original source IDs and verified digest bindings. Then wire C1 candidate acceptance to Stage28's restored A/B original Memory owner via explicit owner revision/currentness acceptance, retaining durable dedup. Finally attach C3 `CognitionDatum` to existing L1 fixed-choice builder behind opt-in shadow, measure source-consistent A/B next-epoch decisions. Only later consider owner-approved L2 C2 proposals and limited L1 reuse. No automatic L0 crystallization.

**Classification:** DEV offline contract and owner adapter; QUAL NO-GO / SCIENCE NOT RUN / REAL_WORLD_LEARNING_NOT_ATTESTED.
