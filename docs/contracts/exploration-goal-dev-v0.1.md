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

## D7 real World DEV source preflight (no local execution)

Isolated D7 Draft #1023 extends D6. The output class is STRUCTURAL_TYPED_CUT_ONLY, never a claim of live Paper/Native/Gemma origin. These GitHub tools do NOT have the user's WSL RTX3060, owned Minecraft Paper process, local source World or Gemma GPU session. Actual real World DEV was NOT executed here.

### Implemented

- src/relay_self/exploration_d7_real_world_preflight_dev.py is read-only. Pin immutable COMMITTED SHA256, original World UUID, source branch, restored fork branch and generation ID. It invokes the original Stage28c full 3-dimension Paper source inspection, plus D4 full source+restored typed World, A/B, Owner, WAL and cognition integrity verification.
- It requires A and B to each retain an original OPEN Question. At least ONE Self must have an actual historical L2 attempt. A Self who chose DEFER can have zero attempts: the test must never force a model choice to invent an old RESERVED record.
- All returned attempts are inert prior-history refs. Real World, native reJOIN, Gemma L1/L2, GPU lease, physical issue and old model replay remain false.
- CLI module experiments.stage28_d7_exploration_source_inspect_dev accepts --generation, --restored, --world-id, --source-branch, --fork-branch, --committed-sha256, --generation-id and --inspect-only. It prints a read-only JSON structural candidate; --execute-once always refuses.
- B #988's real Stage28c2b executable is pinned to a SPECIFIC original World UUID, source commit SHA and fork. That B source is not equivalent to a newer D-carrying typed cut. Running the B command without source-owning integration cannot qualify D7.

### Next real LocalCodex DEV (pending, not performed)

The user has already granted continuing Minecraft EULA consent and real World DEV permission. Do not ask again. On a local branch based on D7, keeping original B #988, D #996, A/C and main untouched:

1. Verify local exact Paper 1.21.8/plugin assets, Java 21, Node/Mineflayer, real Gemma GGUF and idle one-slot GPU before launching World. No synthetic Paper, Native, Model or WAL receipts.
2. Under the ORIGINAL B owner, after actual native A/B login and genuine fresh WorldBody probes, form source-qualified D OPEN Question and run a real Gemma L1 bounded numbered choice (or record a legitimate DEFER). Only a genuine original-owner ESCALATE_L2 can reserve a D3 attempt. No forced L1 selection, no historical model result replay, and no need for an actual L2 POST.
3. Via the original Stage28b owner, actually retire A/B and stop Paper, capture all three dimension files and the original typed A/B cognitive Owner/WAL cut, verify and pin COMMITTED SHA, World UUID and fork. Never overwrite earlier source generations.
4. Restore the D-carrying typed cut into ONE new isolated fork. Run this D7 inspect-only CLI. On HOLD, do not start the new Paper process.
5. Extend original B Stage28c2b owned real runner to accept the newly independently verified D source pins, without removing its native/physical/GPU admission and stale-work fences or misusing old B hardcoded pins. Start one new Paper process, reJOIN A/B and verify genuine independent Paper main-thread tick nonce and native/raw Paper JOIN/PRESENT/QUIT evidence.
6. If a real GPU backend remains idle, run ONE new Gemma bounded L1 choice under the original GPU owner. Confirm unchanged previously attempted Question+epistemic evidence blocks an automatic repeat of L2; only new evidence may justify new owner-mediated review. Do not issue MOVE/EAT/ATTACK.
7. Cleanly terminate original owned Paper and Native children. Preserve original process, Paper stdout, native JSONL, model/GGUF and WAL hashes, verify in a SECOND Python process, and report real UUID/PID/session receipts and exact PASS/HOLD. Never auto-retry ambiguous trial or cleanup.

BLOCKER: B #988 runner has no D source-journal integration or new source-pin support yet. Therefore D7 remains PRE_WORLD_CANDIDATE_ONLY / REAL_WORLD_NOT_RUN / REAL_GEMMA_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN. A read-only source candidate must never be upgraded to real evidence by its own receipt.

## D8 original B Paper/Native runner with D exploration source pins

D8 Draft #1031 is an isolated integration stacked on D7. It imports B
Stage28c2b's original Paper/Native ownership components without changing
B #988, D #996 or main.

New modules and contracts:

- exploration_d8_owned_source_dev.py demands exact original World,
  source/fork branches, generation, COMMITTED SHA256 and historical evidence
  SHA256 plus actual file count. It rechecks D7 original typed A/B/D history
  and the original B Stage28b full historical Native source inventory.
  Old fixed B source pins are not reused.
- stage28_d8_assets_dev.py preserves original Paper/plugin binary SHA pins.
- stage28_d8_real_rejoin_dev.py adapts original B one-shot real Paper and A/B
  Native observer to source-specific D8 pins. It keeps observation-only
  physical admission, original ownership, cleanup and raw evidence capture.
- exploration_d8_online_owner_dev.py checks the actual recovered Owner A/B
  current native/Paper links, D OPEN Questions, historical L2 attempts,
  canonical cognition file and original WAL under B's shared lock.
- stage28_d8_independent_rejoin_audit_dev.py independently rechecks original
  D source pins, raw Paper and Native witnesses, plus the original Owner's
  post-rejoin Question/attempt readback. This is a separate audit process.
- The inspect-only mode never starts Paper. The execute-once mode requires
  a new source-specific D8 manifest and original B local execution gates.

**Verification limitations:** All GitHub CI tests remain CPU offline. The
original real Stage28b producer has not yet generated a newly observed
D Question/L2-bearing source generation. The prior B-only checkpoint does
not qualify for D8. There has been no local Paper, Native or Gemma run
from this environment. No old L2 attempt can be replayed; a genuine DEFER
may leave one Self with no historical attempt. Further local source
generation and independent raw-event verification are still required.
QUAL_NO_GO / SCIENCE_NOT_RUN.

## D9 actual original B Source Producer / one real bounded L1 (isolated DEV)

D9 Draft #1035 extends D8. It is a source-owning implementation seam,
not a completed real World/Gemma run. Original B #988, D #996, A/C, and
main are untouched; only the isolated D9 branch contains its B source
producer fork and B model raw entity-body adapter.

- exploration_d9_original_l1_dev.py projects a new UNKNOWN exploration
  Question from the current original Mineflayer native probe and limited
  observational coverage. It creates Present/Need through the existing
  innate schema and current B original PatternRegistry, not a fake Target
  or hardcoded path. A missing original innate exploration predicate,
  foreign native request, stale epoch or mismatched cognition is HOLD.
  The bounded original L1 presents only ESCALATE_L2 and DEFER.
- The production path submits one new BoundedChoiceRequest only through
  the existing ResidentLlamaInferenceLane backed by the current original
  ResidentCognitiveWorkOwner and the single-slot llama provider. It awaits
  terminal actual ProviderDecision and rechecks the original owner scope
  before adoption. It cannot dispatch L2 or physical effects.
- retain_d9_question_without_model produces an actual owner-durable OPEN
  Question for A, explicitly NOT an inference or fabricated DEFER. Only
  B makes the ONE real model POST in this source trial. If the model
  genuinely chooses ESCALATE_L2, the original Owner stores a D3 RESERVED
  record before any hypothetical future L2. If it chooses DEFER or is
  unresolved, no previous L2 reservation is manufactured and D7's
  non-replay qualification remains HOLD for that source trial.
- exploration_d9_original_source_cut_dev.py performs the original Owner
  memory/Question/Attempt/readback/WAL comparison and then calls B's
  unchanged Stage28b capture_retired_resident_typed_world after all
  original native children retire. It never creates a second owner or
  alternative WAL. The old B source branch was not modified.
- experiments/stage28_d9_real_source_dev.py is a D9-only isolated fork
  of B's original real Paper A/B source launcher. It forbids physical
  MOVE/legacy B L1 modes. Before World launch it requires original
  Stage24g GGUF bytes, llama PID, RTX 3060, live GPU-owner catalog and
  idle singleton slot readback; actual Paper/plugin jar hashes, Java 21,
  Node and explicit EULA/real DEV grants are still required.
  It verifies actual Paper A/B presence before one original L1 GPU POST.
  The B original /v1/systemone HTTP request/response entity bytes are
  captured exactly once, with their SHA256 manifest.
- A native quits and re-JOINs inside the original B scenario. Its new
  Question is formed AFTER its final native reJOIN and accepted actual
  probe; attaching the Question to the retired A native would create an
  invalid original typed cut. B's L1 selection occurs while its original
  native stays online.
- The resulting new A/B typed stopped World source is classified
  REAL_D9_SOURCE_A_B_TYPED_CUT_CAPTURED_INDEPENDENT_AUDIT_PENDING.
  That state is a pending report, not an independently verified real
  result. An external second process must inspect raw original
  Paper/native/model HTTP evidence and the COMMITTED cut before any
  promotion; the D8 old B historical manifest format cannot be reused
  unmodified as if it described D9.
- CPU tests use actual original B owner/cognition, actual B
  ResidentLlamaInferenceLane and a deterministic local HTTP test server.
  They explicitly do NOT access a real GPU, Gemma, native Paper or WSL.
  They cover actual D4 owner Question/Cognition persistence, model
  ESCALATE vs DEFER, model-free A, double-L1 prevention, original
  selected L2 pre-cut provenance, missing pre-World GGUF/PID proof,
  and failure before creating a World.

The RelaySelf user's LocalCodex Minecraft EULA consent and World DEV
approval are already given. The code has NOT run on the user's local
hardware from this assistant. The next required gate is a new D9
independent raw source audit + genuine operator-owned local one-shot
Paper/Gemma run, then only a source-qualified new D8 restore/reJOIN.
Current status: D9_CPU_OFFLINE_DEV_ONLY / REAL_WORLD_NOT_RUN /
REAL_GEMMA_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN.

## D10 — original source seal, independent audit, D8 pin handoff

D10 isolated Draft PR #1039 adds a SOURCE-BYTES audit, not a new Owner
or a direct real Paper qualification. Original B #988, D #996 and A/C/main
are unchanged. This branch uses B's original Mineflayer process adapter,
because the D9 integration-only branch accidentally retained an older
adapter that lacked effect admission, owned native PID and raw stdout
auditing. Without this correction D9 CPU tests could pass while REAL
original B OwnedResidentPhysicalBridge.login would fail.

### Production D9 source recording

- D9 original A0/B0/A1 native launched processes now each start exclusive,
  line-fsynced original JSONL immediately AFTER the adapter_started message
  consumed by launch, and BEFORE original B verify_native_spawn_probe.
  That startup attestation is not claimed to be included in JSONL. Only
  actual subsequent messages are included. Each source is frozen after
  all its original children have exited and records original PID, native
  session ID, file SHA256 and byte count.
- D9 original first A/B login tickets are now stored independently;
  they cannot be overwritten by later Question and L1 outcome variables.
  A's final OPEN Question still uses A's final native reJOIN session.
- No modification enables physical Action, model-driven MOVE, L2 POST,
  synthetic result adoption or ambiguous automatic retry.

### Source proof sequence — LOCAL operator, one original World trial maximum

1. Start the ALREADY-approved original D9 one-shot source producer from
   its isolated D9/D10 branch, using original approved EULA, real World
   DEV and real model grant, exact Stage24g GGUF/PID/RTX3060/idle slot,
   official pinned Paper/plugin binaries and the source producer D9-only
   --d9-source-exploration-dev --typed-owner-cut-dev.
   The model may naturally choose DEFER: if so the source may be held
   and its history must not be changed to ESCALATE by the operator.
2. After all native children and owned Paper stop, identify the actual
   evidence directory and the ORIGINAL
   typed-world-self-generations/g-XXXXXXXXXXXX cut. No previous B-only
   World or historical COMMITTED marker is interchangeable.
3. Run
   python -m experiments.stage28_d10_seal_original_dev
   --evidence-dir /absolute/original/evidence
   --generation /absolute/original/evidence/typed-world-self-generations/g-...
   --world-id ACTUAL_ORIGINAL_UUID
   --source-branch ACTUAL_ORIGINAL_BRANCH

   The sealer verifies the complete three-Paper-dimension typed A/B
   source, stopped-cut report and the exact A/B/Jev/Node files. It writes
   SHA256SUMS once using exclusive create and fsync, and prints the new
   manifest SHA and file count. No mutable or untracked file after this
   sealing may be accepted. Re-running seal is HOLD, not an overwrite.
4. In a NEW independent Python process, run
   python -m experiments.stage28_d10_independent_source_audit_dev
   --evidence-dir SAME_SEALED_ORIGINAL_EVIDENCE
   --generation SAME_ORIGINAL_TYPED_GENERATION
   --manifest-sha256 EXACT_SEALED_SHA
   --manifest-files EXACT_FILE_COUNT
   --world-id ACTUAL_ORIGINAL_UUID
   --source-branch ACTUAL_ORIGINAL_BRANCH
   --committed-sha256 EXACT_ORIGINAL_COMMITTED_SHA

   This re-hashes the whole source and all three Paper dimensional
   manifests, checks B's original A0/A1/B0 Native lineage and individual
   owned Node source raw logs, parses full Paper A-first-QUIT/B-continued/
   A-reJOIN ordered main-thread events, independently parses one original
   Jev/SystemOne HTTP request/response entity-body selection (must be
   original bounded number 1, not an invented reservation), checks
   pre-World GGUF SHA and RTX3060 single slot metadata, original A/B
   cognition/Question/RESERVED/Owner and clear physical WAL.
   Output is exclusive d10-independent-audit.json OUTSIDE sealed evidence.
   It is SOURCE_BYTES_CORRELATED_DEV, not direct Paper/Gemma execution proof.
5. A NEW D8 source-pins JSON (same previous 7 mandatory fields plus
   d10_source_audit_sha256 containing SHA of this external independent
   audit file) names the exact D9 original committed generation,
   source/fork World IDs, the sealed evidence SHA and file count. D8
   inspect_real_recovered_sources will rerun the D7 typed source and
   full D10 original raw proof; it compares the external audit file
   contents with its independent recalculation. Old B original
   historical check keeps its old call signature and classification,
   but D10 explicitly demands D9's INDEPENDENT_AUDIT_PENDING report.
6. Only after BOTH source proof and D7 restored fork match can original
   B-owned D8 native/Paper reJOIN be started, for at most one real DEV
   attempt, followed by its separate independent process audit. Old
   L2 RESERVED is inert source history, never re-POSTed automatically;
   no real physical Action or L1 automatic replay permission follows.

### Limits and evidence policy

All tests performed in GitHub Actions are CPU/synthetic data tests,
including adapter, stub and synthetic typed World source fixtures. No
external tool in this D10 conversation can access the user's actual
WSL2 Paper process, native Node children, RTX3060 or Gemma model.
The audit detects altered/missing original files and internally inconsistent
model/native/Paper source but cannot cryptographically prove the origin
of a fully fabricated self-consistent source directory. A qualified real
World classification additionally requires operator-owned process and
independent raw witness observations at local DEV time. D10 must remain
REAL_WORLD_NOT_RUN / REAL_GEMMA_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN
until that separate source review is actually performed.

## D11 — source-qualified inert restore handoff, then LOCAL real World DEV

D11 adds `experiments/stage28_d11_prepare_inert_handoff_dev.py` to
connect the existing D10 **external, second-process** audit to the
original D8 B-owned restored World/A+B reJOIN runner. It is a CPU-only
inert fork handoff. It launches **no** Paper, Node, GPU model, L2 or Action.
D10's original raw sources and external independent audit are recomputed
**before** any restore directory is created. New D8 eight-field pins are
published **only after** D8 itself validates the newly restored cohort.
Every output is exclusive-create; failed restores are frozen rather than
silently deleted or retried. This is not SCIENCE/QUAL authorization.

### Local operator sequence (new D9 source, then D11)

Use the exact D10/D11 stacked branch and verify its exact HEAD and CI.
The user's Minecraft EULA and real World DEV grants are already approved.
Use the previously successful Stage24g llama-server bootstrap procedure:
discover/check real GGUF SHA, resident owned PID, RTX3060 GPU mapping,
listening HTTP endpoint and **one idle slot**; start the owner-matched
server yourself if necessary. Never infer actual PID/GPU from CLI flags.
Use official pinned Paper 1.21.8 build 60, pinned plugin and current
original B Native/Owner. An unavailable or busy GPU results in
`PRE_WORLD_HOLD`, not a model substitute.

1. Run exactly one D9 source producer with
   `--d9-source-exploration-dev --typed-owner-cut-dev --grant-real-llm`
   and `--eula-accepted --real-world-dev-grant`; pass verified
   `--gguf-path --llama-pid --llama-endpoint --systemone-endpoint --model`
   as well as pinned `--paper-jar --paper-sha256 --plugin-jar
   --plugin-sha256 --scratch-parent`. Do **not** pass the B legacy MOVE
   or autonomous-L1 flags. Record real PID/source/GPU/HTTP/Paper native
   raw output in the original evidence directory and stop all children.
2. Run D10 `stage28_d10_seal_original_dev` once on the original
   `typed-world-self-generations/g-...` with actual World UUID and source
   branch. Then run D10 `stage28_d10_independent_source_audit_dev` in a
   **new process** using the emitted SHA256SUMS digest, file count and
   real original COMMITTED digest. It must produce an external,
   unmodified `d10-independent-audit.json` and its SHA256.
   If the model selected DEFER/UNRESOLVED, keep that result and HOLD.
   Never manufacture an L2 reservation to pass the D7/D10 gate.
3. In another new Python process, inspect the sealed source using
   `python -m experiments.stage28_d11_prepare_inert_handoff_dev`
   with `--inspect-only --evidence-dir EVIDENCE --generation GENERATION
   --manifest-sha256 SEALED_SHA --manifest-files SEALED_COUNT
   --world-id WORLD_UUID --source-branch ORIGINAL_BRANCH
   --committed-sha256 ORIGINAL_COMMITTED_SHA`. No output directories
   or World processes may be created at this step.
4. Repeat the same command with `--prepare-once` instead of
   `--inspect-only`, and add `--restored FRESH_EXTERNAL_FORK
   --restore-id NEW_UNIQUE_RESTORE_ID
   --source-pins-json FRESH_EXTERNAL_PINS_JSON`. This rechecks D10 bytes
   and external audit first, creates the inert World+3 Paper dimensions+
   A/B cognitive cohort **once**, and only publishes the D8 source
   pins after successful D8 original-source inspection.
5. Run `python -m experiments.stage28_d8_real_rejoin_dev --inspect-only`
   with `--generation GENERATION --restored FRESH_EXTERNAL_FORK
   --stage28b-evidence EVIDENCE --source-pins-json FRESH_EXTERNAL_PINS_JSON
   --paper-jar PAPER_JAR --plugin-jar PLUGIN_JAR --eula-accepted`.
   Only if that read-only command passes, invoke the **same** original
   D8 runner with `--execute-once --real-world-dev-grant`, plus fresh
   `--execution-dir` and `--evidence-dir`; this is a NEW isolated
   restored Paper/native A/B real World DEV attempt, no model POST/Action.
6. Once the runner has exited and all its owned processes are stopped,
   execute `python -m experiments.stage28_d8_independent_rejoin_audit_dev`
   in a new independent process with `--result` (actual captured
   run receipt), `--generation`, `--restored`, `--stage28b-evidence`,
   `--source-pins-json` and `--execution-dir`. Save final audit raw
   output, SHA256, PID/session/world/clock receipts and classifications.

D11 is **not** permission for prior L2 replay, physical issue, a new
post-reJOIN L1 request, synthetic reservation, automatic retry or a
60-second live autosave claim. D9 selection 1 and D8 reJOIN are distinct
observations, with model and World process provenance individually
reported. No GitHub Actions success is equivalent to a real Paper/Gemma
measurement. Any incomplete raw witness, stale epoch, mismatched
manifest/PID, nonterminal native process, expired GPU slot, or uncertain
cleanup is `HOLD` without relabeling history.
