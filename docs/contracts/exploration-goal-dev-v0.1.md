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


## D5 actual B Stage28 class integration (isolated Draft #1014)

D5 integrates the **actual** source of B Stage28 `CheckpointedCognitiveOwner`, `ResidentCognitiveWorkOwner`, `SelfOwnerCut`, `stage28_inert_cognitive_recovery`, and their minimal dependency closure on an **isolated** `dev/cognitive-v01-d5-bd-stage28-integration-20261119` branch. The original D #996 branch, B #988 branch, and main remain unchanged. B/D whole-branch merge was refused because their histories conflict; this staged integration is *not* a claim that every parallel B feature, fixture or live runner has merged.

**Verified offline in actual B Python classes (not the D4 test double):**

- Original per-Self resident gate's lock/ONLINE epoch and the D adapter's same-file durable Question+L2 reservation are exercised with two independent Self objects A/B, including per-Self quarantine. Synthetic WorldBody probe objects in the fixture are **not** real Mineflayer observations, JNI or Paper evidence.
- A real B `SelfOwnerCut` / `capture_typed_generation` creates one A/B typed World+Self+WAL generation, `restore_generation` branches it, and `stage28_inert_cognitive_recovery` plus the D5 adapter return only inert open Questions and attempted L2 refs. No old Skill/Intent/Action replay, actual model call or physical issue is authorized.
- A D5 issue was found: while B's World and typed owner gate validated the source generation, the first D bridge did not additionally compare all **restored per-Self files** against their archived copy. Now cognition.json, owner-state.json and physical-wal.json are SHA256-equal checked for each Self before any inert D references are returned; tampering the restored A cognition produces HOLD.
- A second D5 issue was found: B's legacy typed `SelfOwnerCut` schema1 serialized only PatternRegistry revision/patterns and could silently lose D's Self-accepted parameter Presets. The **integration branch only** adds opt-in `SelfOwnerCut` schema2 when accepted Presets exist, using D's strict `encode_pattern_registry` / `decode_pattern_registry` codec and Self ID checking. Schema1 remains byte-compatible for legacy owner cuts.
- On the **same-generation copied Self cohort before COMMITTED**, verify persisted cognition Registry (if present) matches the typed owner Registry and every D OPEN Question is included in `pending_question_refs`. A typed Preset whose persisted cognition is missing it produces a failed precommit and **no COMMITTED marker**. This is additive to B's original full World/roster/peer/WAL checks.

**Boundary / remaining integration:** These tests run **real B class code but synthetic fixtures**, with manually constructed stopped World/quiescence receipts. They do not prove B's live `freeze` was used end-to-end, nor native/Paper/world restart, actual Gemma L2 invocation, real Checkpoint generation cadence, authentic reJOIN probe, external GPU task cancellation or accepted-Preset mutation through a live owner. The copied B modules are *source-pinned*, and the opt-in schema2 reconciliation needs B-lane owner acceptance and cross-stack review; avoid merging isolated D5 as a production replacement. **DEV_REAL_B_PYTHON_CLASSES_OFFLINE_ONLY / QUAL_NO_GO / SCIENCE_NOT_RUN.**

## D6 original Stage28 freeze → full A/B typed recovery → fresh L1 readmission (isolated)

D6 is an isolated Draft #1018 stacked on D5 #1014. B #988, D #996, C Lane and main are unchanged. This is real B Python-class execution using SYNTHETIC Paper, Mineflayer and GPU receipts; it is NOT a real World/Paper, real model, or science/qualification trial.

- The D6 tests call the original CognitionOwnerCohort.close and concurrent freeze(A/B) through CoordinatedAutosaveRuntime with strict typed cuts and the required Overworld, Nether and End. This is an original-owner immutable snapshot, not D5's manually serialized SelfOwnerCut. The synthetic Paper stopped receipt remains a fixture, not source attestation.
- The original owner persists D3 OPEN Questions and RESERVED L2 attempts with its existing canonical cognition writer; D5 opt-in SelfOwnerCut schema2 preserves accepted Skill Presets. The original verify_typed_generation, restore_generation and prepare_recovered_a_b_resident_owners require same-generation A/B, Source World, typed cut, clear WAL and canonical copied file hashes. The fork is inert.
- Missing original pending Question prevents COMMITTED; the autosave runtime stays HELD and does not release the original external physical fence. An old L2 reservation never becomes a fresh session/model request on rebind.
- New read-only exploration_stage28_fresh_gate_dev.py invokes the ACTUAL B stage28_require_fresh_l1_eligibility with new Paper boot, two native logins, independently paired Paper/Native body refs and a single idle GPU slot. Under the original Resident lock it then compares each real B original Owner ONLINE epoch/native ID, typed Mineflayer probe and exact request ref, current native tick, canonical saved cognition, accepted PatternRegistry and OPEN Questions.
- Its output contains only current Question and historical attempt references. Old L1 reuse, L2 model invocation and physical Action issue remain false. A fresh CPU-built bounded L1 can evaluate a Question after this gate; the D3 retained attempt ledger refuses automatic reissue of the same Question plus evidence.
- Adversarial tests cover missing B, mismatched or missing OPEN Question, no real owner login despite synthetic receipt, old native session, wrong native probe ID, stale GPU, foreign Paper, busy slot, inconsistent cognition, and original freeze HOLD with no COMMITTED.

**OPEN:** actual Paper stop/restart and native joining, real current native/Paper source proofs, real GPU L1/L2 work and cancellation, and B Lane acceptance of opt-in typed OwnerCut schema2. Offline evidence does not attest witness origin from real hardware, QUAL_NO_GO / SCIENCE_NOT_RUN.
