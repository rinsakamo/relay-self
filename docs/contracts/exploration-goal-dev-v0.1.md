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
