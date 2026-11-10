# RelaySelf Cognitive Architecture v0.1 / 06 — Learning & Crystallization Contract

> Parent [#828](https://github.com/rinsakamo/relay-self/issues/828); child [#839](https://github.com/rinsakamo/relay-self/issues/839); learning owner [#431](https://github.com/rinsakamo/relay-self/issues/431). Stacked dependencies [Common I/O #830](https://github.com/rinsakamo/relay-self/pull/830) → [Innate Schema #832](https://github.com/rinsakamo/relay-self/pull/832) → [3Self / Present #834](https://github.com/rinsakamo/relay-self/pull/834) → [Task/Profile #836](https://github.com/rinsakamo/relay-self/pull/836) → [Preemption #838](https://github.com/rinsakamo/relay-self/pull/838).
>
> **DRAFT / PURE OFFLINE EVIDENCE-ASSOCIATION & CANDIDATE-READ CONTRACT / NO WORLD, GEMMA, ACTUAL LEARNING OWNER WRITE, HABIT INSTALLATION, PHYSICAL ACTION, QUALIFICATION OR SCIENCE.** This is NOT proof of self-learning, memory generalization, outcome improvement or runtime L0 installation.

## 1. Existing source and owner audit (read before implementation)

| Source and actual branch | What currently exists | Non-claim / integration decision |
| --- | --- | --- |
| **main** `relay_self.intent.IntentCommitment`, `IntentEvent`, `IntentEventKind` | One current Intent instance per existing owner; commit/reconsider/complete/fail/invalidate with terminal provenance and monotonic timestamps | Terminal Intent transition is **owner decision**, not proof of fulfilled physical objective. One attempted-Intent episode aggregation is not implemented on main |
| **main** `persistent_cognition.PersistentCognition`, `Memory` | Narrow immutable identity, Memory content/provenance, appraisal disposition; explicit `retain_memory` and persistence | A C1 readout or C2 candidate **cannot silently write** to this or an invented Knowledge DB |
| **main** `action.ActionLifecycle`, `ActionSupervisor` | Original physical Action proposal/authorization/outcome/UNKNOWN/timeout owner; separate from Goal satisfaction | S16 Action OUTCOME is **not** verified Intent-level success. The current #839 slice never issues S49 Action |
| **separate WB Draft #634 at `087fe095a87594505392262da1d341cf0c65b2b2`**: `action_outcome.py`, `action_feedback.py` | Action outcome readout and bounded proposed feedback; not full C1 aggregation | This code is **not in main** or this stacked PR. Later adapter should consume original typed receipts, not copy their owners |
| **same unmerged WB Draft #634**: `learning.py`, `epoch_continuation.py` | `LearningFeedback`, revision-checked `LearningUpdateProposal`, `LearningUpdateAuthority`, `commit_learning_update`, `RetainedPreferenceRead` for an existing bounded **scalar preference** owner | Does not yet offer a general C2 model/Goal/Habit/Identity write API. This contract creates no new Learning store and no bogus owner commit |
| **same unmerged WB Draft #634**: `habit.py` | `HabitCue`, `HabitRule`, `HabitRepertoire`, read-only `select_habit` with `SELECTED/TIED/NO_MATCH` | Future C3 adapter should reuse it; **do not duplicate `select_habit` or assume installed main habit capability** |
| **Unified v0.5 Draft #718** documents `intent-experience-c1-v0.5.md`, `understanding-revision-c2-v0.5.md`, `conditional-crystallization-c3-v0.5.md`, `learning-admission-c4-v0.5.md` | DESIGN COMPLETE / IMPLEMENTATION PENDING: one assessed attempted Intent→one experience, many fallible C2 proposals, guarded L1 & proposed L0, governed owner updates | These are **design decisions**, not implemented production features |
| **#830/832/834/836/838 stacked Drafts** | Source/epoch refs, 3Self views, Schema candidates, compute Task/Profile, cancelled L2 result fencing | Cancelled L2 output or a successful model text cannot substitute for a native Action, real Outcome or retained evidence |

**Autonomy:** existing owner APIs and actual World/WorldBody resources constrain *correct operation*, not Self's right to learn. Self need not ask a human for each cognitive revision. If/when a genuinely implemented bounded L0 installer exists, Self can be allowed to use it autonomously under physical/runtime safeguards. No such self-installing L0 interface is claimed here.

## 2. One Intent attempt — one C1 episode (not per S49 Action)

```text
Self's existing IntentCommitment COMMITTED (original owner event)
        |
        +-- BeforePrediction(model/version/conditions/time) or NO_PREDICTION
        |
        +-- IntentAttempt (actual, source-qualified; ACTIONS or GUARDED_REST)
        |     original S49 Action ref(s) / native Body/World evidence refs
        |     several actions/replans are NOT separate C1 experiences
        |
        +-- Existing Intent terminal transition (COMPLETED/FAILED/
        |                                    RECONSIDERED_RELEASE/INVALIDATED)
        |
        +-- IntentOutcomeReadout (Intent-level result SUCCESS/FAILURE/
        |                             PARTIAL/UNKNOWN, source+objective check)
        |
        v
   IntentExperience (C1, immutable **readout**; per-attempt key)
        |
        +--> zero or several C2 UnderstandingProposal hypotheses
        +--> separate existing owner retention / later C3 reuse
```

The minimal C1 episode key is `(self_id, world_session_id, attempt_ref)`, **not the textual Intent ID alone**. A caller supplies **existing owner** `IntentCommitment.events`, one actual `IntentAttempt` with source/attempt witness and an assessed `IntentOutcomeReadout`. The pure `project_intent_experience` refuses nonterminal Intent history and duplicate episode keys supplied from the current owner. This check **is not a durable concurrent dedup ledger**; actual owner needs one atomic write/uniqueness gate when integrated. No second store, no autonomous action generator, and no assumption that a constructed `Provenance` object authenticates a native event.

- `AttemptKind.ACTIONS` requires actual Action references (one or more, not one C1 per Action).
- `AttemptKind.GUARDED_REST` admits **zero primitive physical Action refs** when the real resting Intent was actually attempted and externally witnessed. WAIT alone or an idle observation without an attempted Intent is not a measured recovery.
- `EvidenceOrigin.WORLD_BODY_OBSERVED` marks caller-qualified original physical source; `COGNITION_ONLY` and `UNKNOWN` cannot be passed off as the attempted native event. This is a *typed negative control*, **not proof of the caller's honesty**. A real owner must bind native receipt IDs, session, epoch, owner authority and sequence.
- An externally evaluated Intent `SUCCESS/FAILURE/PARTIAL` requires a **WorldBody observation ref and objective-check ref**. `IntentCommitment.complete()` or S49 `OUTCOME` alone is insufficient. If Goal progress cannot be assessed, C1 uses `UNKNOWN`, no fabricated success or eternal blocking.
- Pre-execution prediction must have a prior timestamp and original model/cue ref; later L2 explanations cannot be retrospectively treated as Before. `None` is explicit **NO_PREDICTION**, not a guessed comparison.
- The experience closes on Intent-level assessment after a real attempt, never on a tick, temporary Present frame, deferred/cancelled CognitiveTask, autosave, non-attempted Question or mere LLM expression.
- New later physical evidence can **amend the same C1 episode** using `amend_experience_assessment` with a monotonically revised readout retaining original assessments. It does not create another episode, delete previous UNKNOWN, forge a new native source or directly write Memory.

## 3. C2 — Understanding hypotheses vs accepted owner revision

`UnderstandingProposal` points back to the *same C1 episode key and revision*, with target `Lens` (MySelf, SelfWorld, SelfBody), type `RevisionTarget` and existing semantic owner/expected revision. Four proposed targets are predictive model, applicability conditions, plan tendency and cognitive allocation. One C1 experience may yield zero, one or several **independent** hypotheses, including competing explanations and explicit counterexamples.

Comparison statuses distinguish `MISMATCH`, `CONSISTENT`, `NO_PREDICTION`, `INCOMPARABLE`. A mismatch/consistent classification requires an actual **before** and a known assessed physical result. UNKNOWN cannot be misreported as a measured prediction error; `INCOMPARABLE` is legitimate. A C2 `MISMATCH` is evidence that a prediction differed from a result, **not proof of the proposed causal explanation**. A language model's proposed cause remains a hypothesis until evaluated against independent World/Body evidence.

`RetainedRevisionRead` is an **externally supplied owner report**, not a new learning API, authority token or implementation of a memory write. It carries proposal ref, semantic owner, previous revision, committed revision, accepted flag and provenance. For a retained candidate to be considered current, the owner must have performed a real authorized update. In this pure contract, all such reports are synthetic caller statements: strings/booleans **do not authenticate retention**.

## 4. C3 conditional crystallization and C4 autonomous reuse

| Status in code | Meaning | Does not mean |
| --- | --- | --- |
| `CANDIDATE` | Fallible understanding proposed from C1/C2 | True World rule, learned advantage, persistent Memory or installed Skill |
| `SHADOW_REUSE` | Current qualified cues match a nonretained candidate or Self intentionally keeps it shadow | A physical Action, adopted retained owner update or World outcome improvement |
| `L1_RETAINED_REUSE` | **Owner-reported** revision and critical cue/source/viability/cost conditions match for Self-selected conditional L1 consideration | Actual Habit execution, GPU grant, Action issue or proof that L1 improved performance |
| `ABSTAIN` | Missing/unknown/remembered-only/old/foreign/conflicting cue; Owner revision stale; body viability unknown or compute cost over budget | Rewrite or erase prior experience, or mandatory L2 fallback |

`GuardCondition` is **abstract**, e.g. any typed key/value selected from observed source-bound SelfWorld/SelfBody cues. It is **not** a Minecraft skill table or code-generated physical rule. `CurrentCue` carries an exact Self/session, `EpistemicStatus`, source revisions and original provenance. Missing or UNKNOWN is not equal to a match, a remembered old-session cue is not current World evidence. L1 selection considers the candidate only after current critical source+guard matching; actual #634 `HabitCue/select_habit` selection, model inference and eventual S49 admission remain separate. On another World session, the *understanding* may transfer, but the *old World observation* cannot: new session observations must revalidate the conditions.

The Self may use `SHADOW_REUSE` even before formal retention, then choose actual L1 later if supported. It may **autonomously** decide to try a new theory under adequate World/resource constraints. Neither a fixed sample count nor one-shot statistical superiority over cheap L0 is a universal initiation rule.

`IndependentReuseObservation` links to an independent later Intent attempt and distinguishes `NOT_TESTED`, `REUSED_OUTCOME_UNKNOWN`, `CHEAP_EQUIVALENT`, `POSSIBLE_BENEFIT`, `WORSE_OUTCOME`. A different attempt with the same Self (possibly another World session) is essential to demonstrate *reuse*; a later measured outcome still needs actual owner attestation and an appropriate fair baseline to demonstrate any *benefit*. A `POSSIBLE_BENEFIT` label is a fallible readout, **not SCIENCE**. Reusing text without behavior change does not establish learned generalization. Single-episode advantage is not mandatory for subsequent DEV exploration.

### L0 promotion and reversal

`propose_l0_crystallization` returns only `L0PromotionProposal(status=PROPOSAL_ONLY)`, with a nonempty guard, deadline, rollback ref and fallback ref. It **never** produces executable code, performs a CPU rule install, claims an existing L0 installation API, changes WorldBody physics or grants native Action authority. The real embodiment/runtime owner must later define bounded CPU guards, worst-case timing, counterexamples, missed-trigger/misfire behavior, actual installer and rollback. These are implementation and safety conditions, **not a policy requiring a human to approve every Self-discovered routine**.

Decrystallization is **withdrawal of applicability/selection**, preserving prior evidence. New counterexample, out-of-distribution cue, changed World session/Body viability, stale owner version, cost/deadline failure or repeated physical mismatch suppresses L1 reuse; a further authorized owner revision may narrow, replace or roll back the habit. No rollback can undo a past World Action. An available proven safe original L0 may remain the best choice without forcing new L1 machinery.

## 5. Unit tests and negative controls (offline, fixtures only)

| Check | Positive | Required negative |
| --- | --- | --- |
| C1-01 Intent unit | Existing committed+terminated Intent, 2 S49 Action refs, one C1 experience | No duplicate per Action; duplicate key by current owner index rejected |
| C1-02 Unattempted | Valid REST attempt even with zero issued Action, UNKNOWN final result | Open/deferred Intent and passive observation do not create C1 |
| C1-03 Source vs Owner | Original commit/terminal, attempted source and goal-level result separate | Intent COMPLETE or S16 OUTCOME alone cannot create physical SUCCESS; L2 text cannot become WorldBody evidence |
| C1-04 Before/After | True prior prediction timestamp/ref, known or UNKNOWN result | Post-hoc prediction or outcome pre-dating attempt rejected |
| C1-05 Amendment | UNKNOWN→later World-checked result, same episode + history retained | Duplicate episode, stale revision, wrong Self/World/attempt, repeated assessment rejected |
| C2-01 Interpretations | Multiple target-specific proposed revisions from same C1 | Missing prior prediction or UNKNOWN outcome cannot claim comparable MISMATCH; no Memory write |
| C3-01 Conditional cue | Qualified actual cue and accepted owner report → L1 consideration | UNKNOWN, REMEMBERED, source stale, wrong scope, mismatched value/viability/cost → ABSTAIN |
| C3-02 Retention | Owner accepted version + expected prior version matches | No retention→SHADOW, stale owner/revision→ABSTAIN; report alone not real write |
| C3-03 Across Worlds | Same Self may reuse interpretation in another session after newly observed match | Prior session's old native cue cannot be reused directly |
| C3-04 Independent outcome | Later attempt with fair cheap comparator can be `CHEAP_EQUIVALENT` | Same attempt, foreign Self or UNKNOWN later outcome cannot prove benefit |
| C3-05 L0 | Non-executable, bounded-guard L0 proposal only | No auto-install, no S49 Action bypass, unbounded guard/empty fallback rejected |
| C4-01 Original owners | Existing `IntentCommitment`, `PersistentCognition` remain unchanged | No speculative triple-DB/identity rewrite or automatic durable update |

## 6. Remaining integration / qualification gates

1. **Original Intent/S49/WorldBody proof:** Connect real physical attempt and qualified Intent-level objective readback across multiple Actions. Must guarantee uniqueness and owner checkpoint revisions across crash/replay; `existing_episode_keys` is a *caller's set*, not an atomic DB. Historical events and inferred achievements must not be conflated.
2. **Real #431 learning and Habit owner:** When WB #634 branch is integrated, reuse its revision-protected scalar `learning.py`, `epoch_continuation.py` and read-only `habit.py`; expand only actual owner APIs needed for typed C2 model/reuse and rollbacks, without introducing a parallel store.
3. **Source credentials and L2 preemption:** Real native capture/coverage and action causal lineage must verify the declared `EvidenceOrigin.WORLD_BODY_OBSERVED`. Text/typed provenance can be forged. #838's cancelled output may be logged as a failed *compute task*, **not** used to assert observed physical attempt or Intent result.
4. **Real developmental test:** Observe prediction vs outcome, tentative C2 revision, actual retained owner update, next independent Intent with source-current cue-driven L1 consult, and later adverse/OOD cue invalidation. Compare to existing L0 on the same actual World conditions, track cumulative mistakes, WorldBody cost, cognition GPU/token/latency, and L2 avoided under fixed hardware constraints. `CHEAP_EQUIVALENT` is not training benefit.
5. **L0 installation path / embodiment:** Only once actually implemented should Self be able to install a guarded CPU rule; require original S49 Action/Skill authority, bounded latency and rollback. Self autonomy in learning is maintained; runtime correctness is enforced.
6. **QUAL/SCIENCE:** Offline consistency tests prove neither physical attempt qualification, learned generalization, model-training success, autonomous physical strategy improvement, source authenticity nor repeatable causation. Keep DEV/QUAL/SCIENCE boundaries unchanged.

**Handoff to #828/07:** Reference Action / Skill & Embodiment should define what an already learned candidate may *ask* the body to do, what the World/WorldBody actually makes possible, and how candidate action passes original S49 without hardcoded Minecraft know-how or second issuer. #828/08 then plans integration with actual owner, server and resource constraints.
