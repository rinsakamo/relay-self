# D Lane — Exploration Need -> Goal -> L1/L2 (DEV-only)

Parent #828; related Schema #831, Present #833, selection #841, Skill #843, Learning #839. This isolated branch is stacked on the still-unmerged Draft #917 (#915/#912 and earlier Cognitive drafts). No main merge, World, GPU or QUAL/SCIENCE is claimed.

## Reuse and authority

| Contract | Existing owner | D Lane role |
| --- | --- | --- |
| Scope/source/currentness | CommonEnvelope, ScopeRef, SchemaSnapshot | Reject foreign/stale data |
| 3Self, active Questions/Goals/Intents | PresentFrame and PersistentCognition | Source-bound read-only motivation |
| Schema signals and activation | Innate Schema module registry | Produce EXPLORATION_NEED candidate |
| Goal, Target, accepted Preset | cpu_schema_epoch, PatternRegistry | Reuse original typed CPU matcher |
| Finite L1 | assemble_l1_select, resolve_l1_choice | Preserve numbered selection and DEFER |
| Intent, Skill, Action | Original owners and Physical ActionPort | **No writes or physical issue in D** |
| L2 | OpenCognitionRequest and existing CPU SchemaPattern parser | Proposal, not GPU run or installed rule |
| C Lane | Common I/O source and owner references | Read-only Experience reference |

No central Goal owner, extra runtime, Memory writer, physical issuer or executable code is added.

## D1: motivation is not a MOVE permission

ExplorationEvidence refers to source-qualified Present items, including open Questions, novelty, unknown Skill effect, prediction discrepancy, completed Goal and experience gap. UNKNOWN stays UNKNOWN, not false. ExplorationDisposition (MySelf SOUL and cognitive capacity) plus parallel NeedReadout values modulate a continuous exploration intensity without requiring IDLE, low hunger, oxygen sufficiency, available action or GPU. All reasons remain explicit. Evidence contributions are initially equal; this is not a hard-coded action priority. The original opt-in legacy exploration question path remains unchanged.

The result ExplorationNeed contains an eligible CognitiveSignal with kind EXPLORATION_NEED, intensity, basis and other Need readouts. The existing Schema ON/OFF/dependency and Present source fences still apply. Hunger/oxygen are independent Needs; they do not authorize or forbid physical MOVE.

## D2: original Goal candidate and finite L1

form_exploration_round projects motivated exploration into a *copy* of WorldPercept and invokes the unchanged cpu_schema_epoch with Self-accepted registered Presets. It returns the original SchemaFrame (potentially multiple Goals) plus original numbered L1Round. It does not adopt a Goal, change the original Intent, write Memory or run an Action.

Existing Intent is retained. The output includes KEEP_CURRENT_INTENT as a read-only hint. The existing IntentCommitment/resolve_l1_choice makes physical READY defer when busy. Horizon arbitration, hysteresis and actual long-Intent suspension are not yet supplied by this read-only slice; they require original Self owner integration, not a new D manager.

## D3: known Target vs unknown

KNOWN_PRESET_BOUND means the current qualified WorldPercept has a matching live Target and a current Self-accepted Pattern/Preset/Skill definition, producing an immutable Option.invocation before L1. This does not attest path feasibility or physical execution.

NEEDS_L2 means Target missing or no accepted Preset. Goal stays unresolved; no fabricated MOVE. The original L1 offers ESCALATE_L2 and DEFER as numbered choices.

prepare_exploration_l2 requires the validated ESCALATE_L2 Selection from the existing number resolver, exact owner revision, and read-only attempted-key view. The stable key (Self + Question + owner revision) prevents silent same-revision retries. It only creates an OpenCognitionRequest. CANCELLED/TIMEOUT/UNRESOLVED retains Question; no retry/Memory mutation is automatic.

review_l2_target_reference validates strict typed TARGET_REFERENCE JSON against the **current already-observed** WorldPercept Target inventory, correct question, scope and source epoch. An unobserved imagined Target remains a hypothesis until WorldBody supplies evidence. Existing parse_l2_pattern_proposal and accept_learned_pattern are reused for CPU-evaluable, Self-accepted exploration Pattern proposals; no unreviewed install and no unlimited code/loops.

## Synthetic scenarios and negative gates

A stable: independent exploration Need and Goal, qualified known Target+Preset becomes L1 option, DEFER remains possible.

B no Target: Goal unresolved; no fake invocation; L1 escalation available.

C hunger versus exploration: concurrent Need/Goal signals; no Hunger/Oxygen MOVE permission.

D new danger: D proposes no physical Action, original FAST and body owner retain arbitration; no false success on interruption.

E unresolved long inquiry: preserved Question after cancellation/timeout and deduped attempt key, no endless repetition.

F two Self: separate Present/Owner/Question/Preset and source fences. A's evidence, authority and Intent do not transfer to B.

Additional tests: Schema OFF, UNKNOWN not false, busy incumbent Intent, different disposition/Need changes, malformed L2 target/Pattern proposals, no automatic Memory or Action.

## C Lane and follow-up

ExplorationExperienceRef is an optional *read-only* typed reference package (Self scope, Question/Goal/Intent, optional Action Outcome pointer, epistemic status, current source revision). C Lane must use its existing Experience Assembly and owner-qualified physical witnesses to decide whether an attempted Intent creates experience or understanding, preserving hypotheses as hypotheses. A later qualified C Memory/Question revision may motivate D reevaluation.

Next slice: actual resident Self owner admission of Goal/Question and owner-owned hysteresis, resource/horizon HOLD and retained L2 attempt key, with cross-epoch source fences. Separately qualify CPU owner integration before real Gemma/Paper. Stage27, Stage28 and C branch code/evidence are untouched.

Status: **DEV CPU OFFLINE candidate only**. No real autonomous exploration, GPU L2 model call, native action, checkpoint continuity, QUAL or SCIENCE claim.


## D2 Owner review integration (next offline slice, #996 continuation)

The original Present/Intent owners remain authoritative. D Lane adds a **stateless owner adapter**, not a second Goal owner: exploration_owner_admission_dev.py.

1. **Owner supplies current Goal view**: scope, owner revision, previously adopted Goal ref (must appear in existing Present.active_goal_refs), previously recorded strength/transition time and provenance. The D function does not retain this. Source and Present/Schema revisions must agree.
2. **Self asks explicitly for ADOPT, HOLD or CONTINUE**. review_exploration_goal returns a typed **review receipt**. Existing different CurrentIntent always HOLDs until the original IntentCommitment explicitly reconsiders/releases it. A caller-supplied minimum Goal tenure and strength-switch margin prevent epoch-to-epoch flips; urgent CPU L0 remains entirely outside this non-emergency review. No action permission or automatic winner.
3. **ADOPTION_PROPOSED is not adopted**. The actual Present owner must publish the Goal in active_goal_refs and advance its revision; D neither mutates Present nor writes checkpoint/Memory.
4. **Intent start is separate**. A fresh Present + updated original owner revision + new original numbered L1 result for the *same complete accepted SkillInvocation* are required by begin_adopted_exploration_intent. Only this explicit, validated second call invokes the existing IntentCommitment.commit; it does not start a SkillRun or propose/issue any Action.
5. **Fail closed**: old Intent history, foreign Self, changed Question, wrong owner revision, absent adopted Goal, DEFER/ESCALATE_L2, missing Target/Preset and stale sources never start an Intent. A review receipt cannot be replayed even if the original Intent was subsequently released.

Offline test fixtures demonstrate incumbent Intent reconsideration using the existing IntentCommitment request_reconsideration -> reconsider(RELEASE) APIs. Their use is **not** automatic interruption and does not attest FAST/WorldBody/GPU. Physical continuation is deferred to the existing SkillExecution/ActionPort owner rather than creating a second D issuer.

Still open: real resident Present Goal publication and persistent owner revision/Question/attempt-key snapshots across Stage28 typed checkpoints, owner-managed concurrent Intent horizon arbitration and L2 GPU admission, C Lane experience revisions. No new Checkpoint format is introduced here. Any committed Intent in the synthetic tests is a **cognition-only original-owner event**; no World motor, success or scientific evidence.


## D3 original-owner Question and L2 attempt continuity

**DEV CPU OFFLINE / no live Stage28 or GPU qualification.** This is not a second Goal owner, database, physical issuer, or GPU scheduler.

1. Original `PersistentCognition` gains an optional `exploration_continuity` plus CAS `retain_exploration_continuity`. Existing v3 JSON is **unchanged** when unset. When present, the same original atomic `save_persistent_cognition` path uses strict **opt-in v4**, adding exactly one `exploration_continuity` field. Stage28 captures that same cognition file; its separate unmerged typed owner-cut parser/resident schema has **not** been extended or qualified to ingest v4 yet.
2. Original Self owner explicitly retains only Question refs already in Present. Restored `open_question_refs` are inert cognition refs, NOT current observations, Targets, Goals, Intent, GPU status or skills. Stage28 World/branch/cohort/generation attestation and fresh WorldBody observation remain obligatory before acting.
3. `reserve_exploration_l2` consumes original owner provenance, source-qualified Present, explicit L1 ESCALATE_L2 and fresh owner revision, returning a changed **original owner cognition snapshot** and a request reservation. D does NOT call any model. The owner must first atomically **persist through its normal cognition writer**; `validate_persisted_l2_reservation` rereads that file and checks the native session, Self/World scope, owner revision and source refs before releasing an inert L2 request to a separately authorized GPU worker. A reservation is not an inference grant or an actual work lease.
4. Attempt identity is a stable hash of Self, Question and canonical evidence kind/ref/epistemic status; native JOIN/session ID, source epoch and owner revision do **not** create a new retry identity. Rejoin or unrelated owner epoch advancement alone therefore cannot relaunch the same Question. A genuinely changed qualified evidence basis permits one new reservation. History is bounded to 64 questions and 256 attempts; exceeding limits fails closed.
5. RESERVED is retained **before** possible GPU call; interruption between reservation and actual call is ambiguous, so automatic retry remains suppressed. CANCELLED/TIMEOUT/UNRESOLVED are recorded without deleting the open Question. Positive target-ref audit requires typed validation, never an L2-imagined WorldBody target. Existing GPU cancellation authority remains external, and exactly-once GPU execution is **not** claimed.
6. Two Self, wrong owner CAS, stale native session, edited JSON/hash, duplicate attempts, wrong-version cuts, forged provenance and incomplete durable persistence are adversarially tested.

**OPEN:** actual Stage28 B resident owner publication / typed SelfOwnerCut ingestion, W100 generation/WAL coherence and lease coordination; real GPU execution and cancellation; Question close-on-result policy; C Lane feedback; physical World. A rollback to an older generation with a forgotten later reservation is only safe if Stage28 generation fencing first authorizes the cognition snapshot. D's single-file codec does not solve cross-generation rollback reconciliation. **QUAL_NO_GO / SCIENCE_NOT_RUN.**


## D4 Stage28 original-resident integration adapter (stacks remain unmerged)

New `src/relay_self/exploration_checkpoint_bridge_dev.py` is deliberately **import-lazy**. It only accepts `CheckpointedCognitiveOwner` and `ResidentCognitiveWorkOwner` from the actual **B Lane Stage28** tree. On the current separate #917-based D branch, those modules are not present, so actual resident mutation and typed World/Self restore deliberately **HOLD**. No second owner, synthetic substitute in production, new ActionPort, new checkpoint writer or external GPU dispatch exists. CPU tests may inject an explicitly labeled **B-shape contract harness**, which does NOT qualify the actual B owner.

**When stacks are integrated, the adapter enforces the following original owner boundaries:**

- Under `resident.lock` and the existing `CheckpointedCognitiveOwner._eligible()` call, verify resident `current_scope(self_id)` (cognition epoch/native session/World epoch), current retained Identity, original Intent event count/time, and an already accepted fresh WorldBody probe. The resident must be ONLINE, not QUARANTINED/OFFLINE; no guessed native/World equivalence.
- Use the **original** `owner.files.cognition_file` for CAS write and durable readback, and update **the same** `owner.pending_questions` as the typed B `SelfOwnerCut.pending_question_refs`, under that same existing resident lock. Both D open Question refs and B owner pending refs must agree by subset: B may also have non-D Questions, so equality would erase valid independent work.
- Before mutation, compare the original disk cognition to the current original owner snapshot; mismatch fences the original resident. A partial write or failed readback also fences using B `resident.fence_self` before leaving the lock. The returned D L2 reservation is inert; external GPU owner still must separately authorize work.
- `inspect_d4_inert_recovery` can operate **only** with B `stage28_inert_cognitive_recovery` actually available and its verified full World + A/B typed owner/WAL/cohort/commit/fork evidence. It additionally pins exact `COMMITTED.json` SHA256 and checks each source-cut Self ID, World/branch/generation and D open Question subset of the B `pending_question_refs`. Output is *inert*, with old L2/Skill/Action replay explicitly false.
- Source-qualified terminal L2 results must be committed through the resident owner gate; changed native session, owner epoch, original Intent history or stale World source rejects old result. A recorded Target reference still requires a **current** WorldPercept in the D3 typed validator; no “L2 imagined target = observed target”.
- The actual B cohort freeze records `owner.pending_questions` in `SelfOwnerCut` and `owner.retained` in the original canonical cognition file, under its own closed owner epoch. D4 expects both to be atomically consistent under B's generation verifier; it never decides W100 vs W110, relaxes full roster checks or mints a new generation.

**D4 verification limits:** The D-only branch tests simulate the B **exact method/field surface** for original-owner mutation and provide a deliberately identified simulated Stage28 recovery plan. Since B's implementations are on another unmerged branch, **no claim of real Stage28 class integration, real Paper reJOIN, end-to-end N=2 checkpoint qualification, or L2 GPU execution** follows. The adapter is merge-ready at the API level but needs an actual combined-stack CI run and supervised DEV real World run after B permits integration. `QUAL_NO_GO / SCIENCE_NOT_RUN`.
