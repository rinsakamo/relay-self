# Experiments

This directory is an experimental simulation surface, not a supported `relay_self` package API or semantic authority.

## Controlled Minecraft MVP vertical harness

`controlled_minecraft_vertical.py` is the scenario-local integration harness for
#158. It deliberately composes current owners instead of introducing a generic
RuntimeDriver or Skill registry.

The current bounded decision surface is:

~~~text
current Mineflayer observation
  -> configured nearby hazard? -> FLEE
  -> else low food + configured edible inventory? -> EAT
  -> else -> WAIT
~~~

Hazard interpretation is scenario-local. The Mineflayer adapter still exposes
only target-native entity facts.

When FLEE has one configured destination, selection is deterministic. With
multiple destinations, the harness creates one provenance-bearing finite
`BoundedChoiceRequest` for the existing RelayEngine. Retained `Memory` may be
included as prior experience, while current Mineflayer evidence remains a
separate context datum; Memory is not promoted to fresh World truth.

Execution uses the existing lifecycles and adapter primitives:

~~~text
EAT
  -> SkillExecution
  -> supervised equip_item Action
  -> supervised consume_held Action
  -> later observation must show food increase
  -> Skill SUCCEEDED / FAILED

FLEE
  -> SkillExecution
  -> supervised look Action
  -> supervised forward Action
  -> later observation must reduce distance to selected destination
  -> supervised clear_controls Action
  -> Skill SUCCEEDED / FAILED

WAIT
  -> no SkillExecution
  -> no Action
~~~

An applied primitive effect is therefore not enough to establish Skill success.

The harness is deterministic/fake-session testable and is intended to become
part of the final #141 external transaction after restart/Memory integration is
added. It is not by itself Minecraft external qualification.

## Controlled Minecraft restart / Memory transaction

`controlled_minecraft_restart.py` is Stage C of #158. It adds no automatic
learning path.

A completed controlled FLEE Skill remains transient until a caller explicitly
invokes the integration function:

~~~text
observed FLEE progress
  -> SkillExecution SUCCEEDED
  != Memory

explicit retain_successful_flee_memory(...)
  -> Memory(
       source_provenance = successful consequence observation,
       integration_provenance = explicit integration event
     )
~~~

The transaction then reuses the existing Persistent Cognition file boundary:

~~~text
Persistent Cognition before
  -> explicit Memory retention
  -> save_persistent_cognition(...)
  -> load_persistent_cognition(...)
  -> same IdentitySpecification + retained Memory
  -> later fresh Mineflayer observation
     + retained Memory as prior experience
  -> controlled FLEE destination cognition
~~~

The retained Memory payload identifies itself as `Memory` and preserves the
original Mineflayer source provenance. Current Mineflayer evidence is supplied
through separate cognition data with the later session provenance, so restart
does not promote remembered experience into fresh World truth.

The transaction also emits the existing read-only human activity summary over
the first run and before/after Persistent Cognition delta. The rendered summary
is presentation only and is not used as the Memory source.

## Evolved-value experiments

The evolved-value experiments preserve the causal separation relevant to RelaySelf:

```text
physical viability consequence
  != inherited intrinsic reward signal
  != evolutionary selection result
```

### Food / motor baseline

`evolved_values.py` is inspired by Yuji Kanagawa and Kenji Doya, *Evolution of Rewards for Food and Motor Action by Simulating Birth and Death* (ALIFE 2024, arXiv:2406.15016), and its Apache-2.0 reference implementation in `oist/emevo`.

Agents consume physical energy through basal metabolism and movement, gain physical energy from food, reproduce by transferring energy to offspring, inherit mutated food/movement reward coefficients, and learn an action policy during their lifetime using only those inherited intrinsic reward coefficients.

The model is deliberately smaller than the paper: it uses a one-dimensional toroidal world, nearest-food direction as the observation, tabular Q-learning, and standard-library Python rather than the paper's continuous 2D JAX/physics setup. A mismatch with the paper's qualitative evolved rewards is therefore evidence about this reduction, not a result to tune away silently.

Run:

```bash
python experiments/evolved_values.py --seed 1 --steps 5000
```

### Predator / sensor follow-up

`predator_values.py` is inspired by Kanagawa and Doya, *Evolution of Fear and Social Rewards in Prey-Predator Relationship* (arXiv:2507.09992), and the upstream `oist/emevo` predator experiment.

The reduced simulation adds active chasing predators plus inherited linear reward weights for food, movement, conspecific proximity, and predator proximity. Physical predation remains a World/body consequence; the predator-sensor coefficient is only an intrinsic learning signal whose evolutionary distribution can be measured later.

The reduced predator implementation intentionally does **not** claim full prey-predator co-evolution, fear semantics, social-emotion semantics, or reproduction of the paper's reported distributions. It uses fixed predator controllers, one-dimensional local sensing, and tabular learning so that the causal mechanism remains easy to inspect.

Run the default active-predator condition:

```bash
python experiments/predator_values.py --seed 1 --steps 5000
```

Run the no-predator control:

```bash
python experiments/predator_values.py --seed 1 --steps 5000 --predators 0
```

A stationary-predator ablation is also available:

```bash
python experiments/predator_values.py --seed 1 --steps 5000 --stationary-predators
```

Both evolved-value experiments support `--json` for machine-readable output.

## Adaptive mechanism-selection probe

`adaptive_mechanisms.py` is a synthetic, non-biological probe for Issue #60. It compares four paired conditions over the exact same seeded task sequence:

```text
cheap_only
expensive_only
fixed_switch
adaptive
```

The task has repeated contexts, observable uncertainty, explicit synthetic computation cost, deadlines, and a hidden regime shift. Three experiment-local mechanisms have deliberately different latency / information / cost profiles:

```text
FAST    cheap reuse or a brittle default
MEDIUM  moderate-cost use of a noisy regime signal
SLOW    expensive direct inspection of the correct action
```

A successful `SLOW` solve can populate a transparent per-context cache later reused by `FAST`. A failed cached response invalidates that entry, allowing the adaptive condition to re-escalate after distribution shift. The cache is only an experiment-local stand-in for amortization; it is not a RelaySelf Skill registry, Cognitive Frontier, Thinking Level, or supported runtime API.

Run the default 20-seed paired comparison:

```bash
python experiments/adaptive_mechanisms.py --seeds 20
```

Increase selector overhead as a metacontrol-cost ablation:

```bash
python experiments/adaptive_mechanisms.py --seeds 20 --selector-cost 10
```

Machine-readable output is available with `--json`; add `--trace` to include per-episode decision records.

Simulation results from this harness are evidence only for the recorded configuration and seeds. Do not promote a favorable comparison into RelaySelf semantic authority without the normal evaluation and Grand Null process.


## Present / FLEE / decision-epoch fixture

`present_skill_epoch.py` is a deterministic, experiment-local probe for the first concrete
Skill-narrowing path across #87, #105, and #106.

It uses one committed objective and one local `FLEE` representation to demonstrate:

```text
broad Present
  -> admit FLEE candidate
  -> FLEE-local narrowing
  -> bind one destination from explicit route evidence
  -> existing SkillExecution STARTED boundary
```

The broad fixture carries unrelated hunger and conversational facts alongside threat, body,
destination, and route evidence. FLEE-local narrowing removes the unrelated facts while preserving
the original provenance of retained facts. A deliberately misleading narrow projection omits route
status; the fixture treats the omission as missing information, returns `ESCALATE`, broadens back
to the source projection, and then recovers the bounded decision.

The same module includes an experiment-local event matrix showing that ambient/quiet events are
ignored, route/supervision events and consequence mismatch can first reopen a deterministic decision
epoch, and unresolved local uncertainty may require RelayEngine cognition. These labels are not a
runtime API or a general Scheduler contract.

Run:

```bash
python experiments/present_skill_epoch.py
python experiments/present_skill_epoch.py --json
```

This fixture does not establish a generic Present schema, Focus owner, Skill registry, RuntimeDriver,
or RelayEngine implementation. It is deterministic evidence about one bounded decomposition only.


## Reconsideration-admission fixture

`reconsideration_admission.py` is the deterministic, experiment-local #107 follow-up to the
Present/FLEE fixture. It keeps the same committed `reach safety` objective and tests only the
upstream admission boundary before the existing
`IntentCommitment.request_reconsideration(...)` seam.

The reference sequence demonstrates:

```text
local route blocked + alternate route available
  -> local recovery
  -> no reconsideration request

all grounded local routes unavailable
  -> request reconsideration
  -> later explicit CONTINUE decision with separate provenance

new safe route appears
  -> local recovery
  -> no automatic commitment break

viability becomes unacceptable
  -> request reconsideration
  -> later explicit RELEASE decision with separate provenance
```

Run:

```bash
python experiments/reconsideration_admission.py
python experiments/reconsideration_admission.py --json
```

This fixture does not create a generic trigger detector, trigger taxonomy, utility threshold,
RuntimeDriver, or model-controlled preemption path. It is deterministic invariant evidence for one
bounded Current Intent / FLEE context only.


## Multi-owner decision-epoch trace

`multi_owner_decision_epoch.py` is the deterministic #106 follow-up that moves beyond the earlier
event classification table and services current executable owners in one bounded trace.

The fixture establishes one Current Intent, starts the existing FLEE SkillExecution path, proposes
and authorizes one Action, and places that Action under the existing ActionSupervisor. It then
records:

```text
irrelevant observation
  -> IGNORE

material route observation
  -> reproject Present
  -> no model call

Action Supervision deadline
  -> deterministic timeout through ActionSupervisor
  -> same Current Intent / Skill continue

Skill-local control step
  -> deterministic epoch
  -> no high-level reselection

consequence mismatch
  -> reopen/reproject Present
  -> #107 local recovery first
  -> no automatic Intent reconsideration

Skill-local uncertainty
  -> cognition request / RelayEngine boundary

quiet interval
  -> IGNORE
```

Run:

```bash
python experiments/multi_owner_decision_epoch.py
python experiments/multi_owner_decision_epoch.py --json
```

The fixture does not implement a RuntimeDriver, Scheduler, event bus, model, or autonomous clock.
It is deterministic evidence that existing owner-local lifecycles can be coordinated at explicit
decision epochs without making every event a model call.


## Cognition / consequence closed-loop fixture

`cognition_consequence_loop.py` is the deterministic #104 fixture that connects bounded cognition
to the existing Skill, Action, Present, and reconsideration boundaries without running a model or
creating a new prediction/mismatch owner.

It keeps local expected evidence experiment-scoped and separates six causal cases:

```text
A. unresolved bounded cognition
   -> ESCALATE
   -> no SkillExecution / Action

B. expected consequence observed
   -> Action OUTCOME
   -> Skill SUCCEEDED

C. stale / misleading Present assumption contradicted by World evidence
   -> Action OUTCOME
   -> Skill FAILED
   -> old Present stale
   -> reproject
   -> local recovery under same Current Intent

D. consequence unavailable
   -> Action UNKNOWN
   -> no invented Skill success/failure

E. World changes after a previously grounded decision
   -> mismatch
   -> reproject from new World evidence
   -> local recovery without rewriting the earlier evidence

F. controller reports no progress while route evidence remains open
   -> Skill FAILED
   -> World route truth unchanged
   -> Current Intent retained
```

Run:

```bash
python experiments/cognition_consequence_loop.py
python experiments/cognition_consequence_loop.py --json
```

The fixture deliberately creates no automatic training labels. It does not establish a universal
mismatch taxonomy, prediction schema, adapter invalidation policy, model-quality result, or physical
World qualification.


## NLD-3B tri-mode bounded-decision probe

`nld_tri_mode.py` is the first actual-model harness for #112 and the current first-choice
physical substrate under #101.

It uses the official direct Python model surface from NVIDIA:

```text
AR                -> model.ar_generate(...)
dLM / diffusion   -> model.generate(...)
Linear Self-Spec  -> model.linear_spec_generate(...)
```

The same loaded `nvidia/Nemotron-Labs-Diffusion-3B` checkpoint receives the same bounded
FLEE-domain prompt in all three modes. The first probe keeps LoRA, serving frameworks,
quantization, and adaptive mode-selection out of scope.

The experiment mirrors the current public NVIDIA simple evaluator defaults:

```text
AR          block_length=1
dLM         block_length=8,  threshold=0.9
Linear-SS   block_length=32
```

Render the deterministic plan without importing Torch or Transformers:

```bash
python experiments/nld_tri_mode.py
```

Actual execution requires the current official-style direct runtime:

```text
PyTorch + CUDA
Transformers >= 5.0
AutoModel / AutoTokenizer
trust_remote_code=True
```

and can be started explicitly with:

```bash
python experiments/nld_tri_mode.py \
  --run \
  --output /tmp/nld-tri-mode.json
```

The default actual probe uses BF16 and 32 requested new tokens. It records model-load time,
GPU allocation, method availability, per-mode generation latency, returned NFE,
tokens-per-forward, generated text/token count, parsed A/B/C decision, and the bounded expected
label.

A successful run establishes only that the three native model paths are physically available
and observable on the tested system. It does not establish that AR, diffusion, or
Self-Speculation should own any RelaySelf semantic role or that an adaptive mode selector is
justified.

Internal AR verification inside Linear Self-Speculation remains distinct from World consequence
verification under #104.


### NLD-3B local physical transaction

`nld_tri_mode_transaction.py` wraps the first #112 local qualification in a fresh-evidence
transaction. It requires a clean RelaySelf checkout, records exact Git identity, fresh GPU
identity/free memory, Python/Torch/Transformers versions, a deterministic dry-run plan, and the
actual tri-mode result under a new or empty evidence directory.

Canonical invocation:

```bash
EVIDENCE=/tmp/relay-self-nld-$(date -u +%Y%m%dT%H%M%SZ)

bash experiments/run_nld_tri_mode_transaction.sh \
  --evidence-root "$EVIDENCE"

cat "$EVIDENCE/summary.json"
```

The canonical first gate uses the official direct PyTorch/Transformers runtime, BF16, no LoRA,
no quantization, and no serving framework. Missing packages, model/custom-code loading errors,
CUDA/BF16 failures, OOM, timeout, or malformed model output terminate as
`FAIL_NOT_QUALIFIED` with the failing stage and preserved stdout/stderr.

A `TRI_MODE_PASS` means only that the same loaded NLD-3B checkpoint completed the bounded
AR, dLM, and Linear Self-Speculation calls and produced structurally valid evidence. It does not
select a permanent RelayEngine mode.


### NLD-3B tri-mode repeatability transaction

`nld_tri_mode_repeatability.py` and
`nld_tri_mode_repeatability_transaction.py` implement the next bounded gate under #115.
They keep the same NLD-3B checkpoint, BF16 runtime, seed, prompt, and native mode defaults
from #112 while strengthening only the measurement protocol.

The model is loaded once. Each mode receives one warm-up call that is excluded from latency
summaries. The measured schedule then executes all six AR/dLM/Linear-Spec order permutations
twice:

```text
6 permutations
x 2 repeats
x 3 calls per permutation
= 36 measured calls
= 12 observations per mode
= 4 observations per mode at each ordinal position
```

Every measured latency uses explicit CUDA synchronization around the monotonic timer. The trace
retains per-call output, NFE, token count, tokens-per-forward, parsed A/B/C label, correctness,
and CUDA peak allocation. Per-mode summaries report min/median/nearest-rank-p95/max latency and
latency grouped by ordinal position.

Canonical local invocation:

```bash
EVIDENCE=/tmp/relay-self-nld-repeatability-$(date -u +%Y%m%dT%H%M%SZ)

bash experiments/run_nld_tri_mode_repeatability_transaction.sh \
  --evidence-root "$EVIDENCE"

cat "$EVIDENCE/summary.json"
```

A `REPEATABILITY_PASS` is a structural evidence result. It does not require all labels to be
correct and does not promote a decoding-mode ranking or adaptive RelayEngine policy. Wrong,
invalid, slow, noisy, or order-sensitive outputs remain valid measurements for #115.


### NLD-3B bounded problem-structure × native-mode matrix

`nld_bounded_difficulty_matrix.py` and
`nld_bounded_difficulty_matrix_transaction.py` implement #117.

The matrix keeps the already-qualified NLD-3B BF16 runtime and native generation calls while
changing only the bounded problem structure:

```text
easy_separable       expected A
coupled_constraints  expected B
incomplete_focus     expected C = DEFER
```

These case semantics align with the existing DiffusionGemma bounded probe so a later
cross-substrate comparison can reuse the same decision surface.

For each case, the experiment executes all six AR/dLM/Linear-Spec order permutations once:

```text
18 measured observations per case
6 observations per case × mode cell
54 measured calls total
2 observations per cell at each ordinal position
```

The model is loaded once and each mode receives one excluded warm-up call. Measured calls use
explicit CUDA synchronization around the full native generation call, preserve generated text and
A/B/C parsing, and record NFE, generated-token count, tokens-per-forward, latency, correctness,
and CUDA peak allocation.

Canonical local invocation:

```bash
EVIDENCE=/tmp/relay-self-nld-matrix-$(date -u +%Y%m%dT%H%M%SZ)

bash experiments/run_nld_bounded_difficulty_matrix_transaction.sh \
  --evidence-root "$EVIDENCE"

cat "$EVIDENCE/summary.json"
```

A `BOUNDED_MATRIX_PASS` means only that a structurally valid 3-case × 3-mode physical trace
was recorded. It does not require every model response to be correct. Wrong or invalid outputs
remain evidence and must not be tuned away.

The current `max_thinking_tokens` call argument is preserved from the qualified native surface,
but this matrix does not claim that it is an independently validated cognition-depth budget. The
matrix also does not test long-form generation throughput, learned mode routing, multimodal input,
or World consequence correction.


### NLD-3B easy-case permutation isolation

`nld_easy_permutation_isolation.py` and
`nld_easy_permutation_isolation_transaction.py` implement #123.

This gate isolates the stable #117 `easy_separable` counterexample without changing the
qualified model/runtime surface. It crosses two candidate mappings with two grounded route states:

```text
                                      A=cave/B=ridge    A=ridge/B=cave
cave open, ridge blocked                   A                  B
cave blocked, ridge open                   B                  A
```

Candidate display order remains fixed as A, B, C. Each cell runs all six native-mode order
permutations once, giving 72 measured calls total and 6 observations per cell/mode. The model is
loaded once and each native mode receives one excluded warm-up call.

Measured traces preserve both the parsed A/B/C label and the semantic destination obtained by
mapping that label through the cell's explicit candidate mapping. This keeps literal-label behavior
separate from cave/ridge selection behavior.

Canonical local invocation:

```bash
EVIDENCE=/tmp/relay-self-nld-easy-isolation-$(date -u +%Y%m%dT%H%M%SZ)

bash experiments/run_nld_easy_permutation_isolation_transaction.sh \
  --evidence-root "$EVIDENCE"

cat "$EVIDENCE/summary.json"
```

A `PERMUTATION_ISOLATION_PASS` means only that a structurally valid four-cell × three-mode
physical trace was recorded. Wrong or invalid decisions remain evidence. Diagnostic patterns do not
by themselves prove a causal mechanism, and this gate does not vary candidate display order,
thinking depth, long-form generation, multimodal input, or adaptive routing.

### NLD-3B reversed-mapping token-budget isolation

`nld_reversed_mapping_token_budget.py` and
`nld_reversed_mapping_token_budget_transaction.py` implement #125.

This gate keeps only the two reversed-mapping cells from #123:

```text
A = FLEE(destination=ridge)
B = FLEE(destination=cave)
C = DEFER

cave open / ridge blocked -> expected B
cave blocked / ridge open -> expected A
```

Each cell is crossed with `max_new_tokens=32` and `64`, while AR, dLM, and Linear
Self-Speculation otherwise keep the qualified runtime defaults. Every `(mode, token-budget)` path
receives one excluded warm-up, then each `(case, token-budget)` subject runs all six native-mode
order permutations once:

```text
2 cases × 2 token budgets × 6 permutations × 3 mode calls
= 72 measured calls
```

In addition to the current bounded label, the trace records whether parsing came from an explicit
decision statement, the fallback candidate-label rule, or no candidate label; explicit and fallback
labels; EOS occurrence; generated-token count; and a token-cap proxy indicating whether generated
tokens reached or exceeded the effective requested maximum.

Canonical local invocation:

```bash
EVIDENCE=/tmp/relay-self-nld-token-budget-$(date -u +%Y%m%dT%H%M%SZ)

bash experiments/run_nld_reversed_mapping_token_budget_transaction.sh \
  --evidence-root "$EVIDENCE"

cat "$EVIDENCE/summary.json"
```

A `TOKEN_BUDGET_ISOLATION_PASS` means only that a structurally valid physical trace was
recorded. `max_new_tokens` is an output-generation control, not a qualified semantic
cognition-depth measure. Wrong or fallback decisions remain evidence.

### NLD-3B native output-token trajectory

`nld_native_path_trajectory.py` and its transaction implement #127.

The transaction reuses the qualified #125 physical runner and records the full 72-call source trace.
It adds per-token decoded output and parser-state observations, then analyzes the 18 observations for
`reversed_ridge_open` at `max_new_tokens=32` across AR, dLM, and Linear Self-Speculation.

The analysis reports stable sequence fingerprints, first label-bearing and explicit-decision prefixes,
and pairwise first output-token divergence. It observes native outputs only; it does not expose hidden
states or establish a causal internal mechanism.

Canonical invocation:

```bash
EVIDENCE=/tmp/relay-self-nld-trajectory-$(date -u +%Y%m%dT%H%M%SZ)

bash experiments/run_nld_native_path_trajectory_transaction.sh \
  --evidence-root "$EVIDENCE"

cat "$EVIDENCE/summary.json"
cat "$EVIDENCE/trajectory-analysis.json"
```

`NATIVE_OUTPUT_TRAJECTORY_PASS` is a structural evidence result. Wrong decisions remain evidence.

### NLD-3B lexical remapping generalization

`nld_lexical_remapping_generalization.py` and its transaction implement #131.

The gate keeps the same bounded `FLEE(destination=...)` / route-open logic while replacing only
the destination-name family:

```text
route: cave / ridge
color: amber / cobalt
code: item-17 / item-42
```

Each family uses the same 2x2 mapping/feasibility surface. Across 12 cases, all six native-mode
order permutations are measured once, yielding 216 measured calls and six observations per
case/mode cell.

Canonical invocation:

```bash
EVIDENCE=/tmp/relay-self-nld-lexical-$(date -u +%Y%m%dT%H%M%SZ)

bash experiments/run_nld_lexical_remapping_generalization_transaction.sh \
  --evidence-root "$EVIDENCE"

cat "$EVIDENCE/summary.json"
```

`LEXICAL_GENERALIZATION_PASS` means only that a structurally valid physical trace was recorded.
Wrong decisions remain evidence. The gate tests one checkpoint's lexical generalization and does
not establish a product ranking, hidden causal mechanism, or cross-model generalization.

### NLD-3B matched-adequacy cost surface

`nld_adequate_cost_surface.py` and its transaction implement #133.

The gate uses only the four `color` family cells from #131, where AR, dLM, and Linear
Self-Speculation were all 24/24 correct. It re-runs those subjects fresh and compares cost
dimensions only if matched adequacy is reproduced.

Measured dimensions remain separate: full-call latency, NFE, generated-token count, tokens per
forward, CUDA peak allocation, parse-source explicitness, first label/explicit-decision token
index, and tokens emitted after the first explicit decision. No weighted total score is defined.

Canonical invocation:

```bash
EVIDENCE=/tmp/relay-self-nld-cost-$(date -u +%Y%m%dT%H%M%SZ)

bash experiments/run_nld_adequate_cost_surface_transaction.sh \
  --evidence-root "$EVIDENCE"

cat "$EVIDENCE/summary.json"
```

`ADEQUATE_COST_SURFACE_PASS` means only that a structurally valid physical trace was recorded.
`cost_comparison_eligible=true` additionally requires every mode to remain 24/24 correct with no
invalid outputs on the fresh matched subject. The experiment does not establish a permanent mode
selector, weighted cognition score, World truth, or Action authorization.
### NLD Linear-SS vs Gemma Q4 matched comparison

#143 compares the four matched #133 color cases across NLD Linear Self-Speculation and the pinned local Gemma 4 12B Q4_K_M llama.cpp substrate.

The transaction runs the substrates sequentially so they do not share GPU residency. Each receives one excluded warm-up and 24 measured calls.

Run:

```bash
EVIDENCE=/tmp/relay-self-nld-gemma-$(date -u +%Y%m%dT%H%M%SZ)
bash experiments/run_nld_gemma_cross_substrate_transaction.sh \
  --evidence-root "$EVIDENCE"
cat "$EVIDENCE/summary.json"
```

`CROSS_SUBSTRATE_MATCHED_PASS` means both physical traces are structurally valid. Cost comparison is eligible only when both substrates are 24/24 correct with zero invalid outputs. The gate defines no weighted score or permanent substrate selector.

### Gemma Skill-local narrowing cost probe

#155 compares the same Gemma 4 12B Q4_K_M RelayEngine decision under two context surfaces:

```text
BROAD  = FLEE-relevant context + unrelated broad-Present facts
NARROW = the same FLEE-relevant facts with identical values/provenance
```

The canonical transaction owns one llama.cpp server and runs 48 measured RelayEngine episodes across four FLEE cases. Explicit THINK escalation remains part of cognition cost rather than being hidden.

Run:

```bash
EVIDENCE=/tmp/relay-self-gemma-narrowing-$(date -u +%Y%m%dT%H%M%SZ)
bash experiments/run_gemma_skill_narrowing_transaction.sh \
  --evidence-root "$EVIDENCE"
cat "$EVIDENCE/summary.json"
```

`GEMMA_SKILL_NARROWING_PASS` means a structurally valid physical trace was recorded. Cost interpretation is eligible only when BROAD and NARROW both preserve the required useful outcomes. The probe does not by itself establish experience-dependent crystallization, a generic Focus owner, World truth, or Action authorization.

## DiffusionGemma bounded-decision probe

`diffusiongemma_bounded_decision.py` is the first actual-model probe for #101, built on top
of the bounded FLEE domain established by `present_skill_epoch.py`.

The probe reads **one diagnostic decision slot**, but it does not claim one-token physical
generation. In the current upstream generation loop, `max_new_tokens=1` makes
`ceil(1 / canvas_length) = 1` canvas run; that canvas is still denoised and appended at the model's
fixed `model.config.canvas_length`. The experiment therefore records both the requested
`max_new_tokens` value and the actual generated canvas-token count.

The model-facing question is:

```text
same bounded candidates
  -> observe raw candidate logits at canvas slot 0
  -> record candidate-only readout after denoise ordinal 1 / 2 / 4 / 8
  -> optionally compare with the checkpoint's adaptive stop
```

The custom logits processor is observational: it records the candidate logits before
DiffusionGemma's built-in temperature processor and returns the original logits unchanged. It does
not force A/B/C into the canvas or modify model weights.

Three initial cases are included:

```text
easy_separable       one route open, one blocked
coupled_constraints  both open, but only one satisfies an energy constraint
incomplete_focus     decisive route evidence is unknown; DEFER is expected
```

Render the deterministic experiment plan without importing model dependencies:

```bash
python experiments/diffusiongemma_bounded_decision.py
```

Run the released checkpoint when an environment with the required model stack is available:

```bash
python experiments/diffusiongemma_bounded_decision.py \
  --run \
  --steps 8 \
  --output /tmp/diffusiongemma-bounded-decision.json
```

Add `--adaptive` to perform a second pass using the checkpoint's adaptive stopping
configuration. `--quantization bnb4` is an experiment-only loading option for constrained
hardware; its compatibility, quality, and performance are not established by deterministic CI.

The repository intentionally does not declare Torch, Transformers, Accelerate, or bitsandbytes as
supported package dependencies merely for this probe. Actual-model execution records the observed
Torch/Transformers versions, quantization mode, denoising-step trace, wall-clock latency,
`tokens_per_forward` when available, and CUDA peak allocation when CUDA is present.

Candidate probabilities are normalized only across the bounded A/B/C candidate-token set. They are
diagnostic model evidence, not calibrated World probabilities, Action authorization, or proof that
the selected decision is true.


### DiffusionGemma local physical transaction

`diffusiongemma_bounded_decision_transaction.py` wraps the smallest #101 physical run in a
fresh-evidence transaction. It requires a clean RelaySelf checkout, records the exact Git head/tree
and attached branch, fresh GPU identity/free memory, Python/package versions, a dry-run plan, and the
actual-model stdout/stderr/result under a new or empty evidence directory.

The default physical subject is intentionally tiny:

```text
case = easy_separable
fixed denoising steps = 1
decision slots observed = 1
canvas runs = 1 (via max_new_tokens=1)
quantization = bnb4
```

The default `bnb4` path is **local-feasibility evidence**, not an unquantized baseline. Use
`--quantization none` only when the host has enough memory for the released unquantized model path.
The transaction installs nothing automatically. Missing packages, missing GPU visibility, model
access/download problems, OOM, timeout, or model/runtime incompatibility are preserved as
`FAIL_NOT_QUALIFIED` with the failing stage in `summary.json`.

Canonical local invocation:

```bash
EVIDENCE=/tmp/relay-self-diffusiongemma-$(date -u +%Y%m%dT%H%M%SZ)

bash experiments/run_diffusiongemma_bounded_decision_transaction.sh \
  --evidence-root "$EVIDENCE"
```

Inspect:

```bash
cat "$EVIDENCE/summary.json"
```

A `PASS` proves only that this exact checkout/runtime completed the requested one-case,
one-decision-slot physical probe and produced a structurally valid actual-model observation. It does not establish adaptive
cognition quality, Action authority, World truth, FreeToken viability, or the full #101 hypothesis.

## Mineflayer viability-relay fixture

`mineflayer_viability_relay.py` is a deterministic, simulation-only fixture for #46. It is grounded in `PrismarineJS/mineflayer` revision `91204b2a034f0663b39814771e236bcb7c8f26c8` but does not import Mineflayer or require a Minecraft server.

The fixture preserves Mineflayer-like body facts and events separately from a minimal signed health gradient:

```text
Mineflayer observation / event
  != health-gradient sample
  != belief / appraisal
  != action
```

The first gradient is intentionally only:

```text
current bot.health - previous bot.health
```

No extra penalty is attached to `death`, and `respawn` remains an independent observation event. As a result, the built-in death/respawn trace deliberately produces a positive health delta after respawn, which keeps Minecraft recovery semantics available for later cognition experiments instead of hard-coding human death aversion.

Emit both A/B payloads:

```bash
python experiments/mineflayer_viability_relay.py --condition both
```

Or emit one condition:

```bash
python experiments/mineflayer_viability_relay.py --condition observations
python experiments/mineflayer_viability_relay.py --condition gradient
```

This fixture does not demonstrate useful Minecraft cognition by itself. Its output is a bounded input surface for a later controlled cognitive-consumer comparison.

## Mineflayer cognition A/B probe

`mineflayer_cognition_ab.py` turns the merged viability fixture into four matched cognition conditions. The original semantic A/B pair preserves Mineflayer field/event names; a second A/B pair deterministically aliases those names so the value signal can be tested with less pretrained Minecraft/human semantic leakage.

```text
observationsOnly
withHealthGradient
neutralObservationsOnly
neutralWithGradient
```

All four conditions use the same task, candidate plans, observation values, model id, temperature, output instruction, and generic signed-signal semantics. Within each semantic-label pair, the model-visible treatment difference is only whether the history rows contain the derived gradient/signal values.

The task asks the model to reach one target efficiently and choose one of three geometry-only plan ids:

```text
direct
detour
observe
```

The candidate descriptions contain coordinates only; they are not labeled with affective or safety semantics. The primary output is therefore a behavior choice (`plan_id`), not an emotion word.

The neutral history uses fixed experiment-local aliases such as `resource_0`, `event_1`, and `signal_0`. It removes Mineflayer/Minecraft and health/death/hurt labels from the history while preserving values, event/source association, and timing. This is an evaluation control only; it is not an adapter or runtime schema proposal.

Render deterministic requests without network access:

```bash
python experiments/mineflayer_cognition_ab.py --model MODEL_ID
```

Run repeated calls against an OpenAI-compatible endpoint:

```bash
python experiments/mineflayer_cognition_ab.py \
  --model MODEL_ID \
  --endpoint http://127.0.0.1:1234/v1/chat/completions \
  --repeats 10 \
  --run
```

If the endpoint requires a key, the script reads `OPENAI_API_KEY` by default; `--api-key-env` can name another environment variable. Condition order reverses across trials, request hashes are recorded, malformed or out-of-set model outputs are preserved as failures rather than silently repaired, and run output reports per-condition plan counts plus separate semantic-gradient, neutral-gradient, and semantic-prior detour-rate differences.

The gradient remains mathematically derivable from the original health observations. A measured effect therefore demonstrates representational/evaluative salience, not additional World information. Model-run results are model/system-quality evidence only; they do not establish a Value/Emotion/Fear owner, and a null result does not justify strengthening the gradient merely to force an effect.


## Mineflayer cognition physical qualification

The canonical local physical entrypoint for the pinned #46 llama.cpp qualification is the no-bytecode launcher:

```bash
EVIDENCE=/tmp/relay-self-mineflayer-$(date -u +%Y%m%dT%H%M%SZ)

bash experiments/run_mineflayer_cognition_llama_cpp_transaction.sh \
  --evidence-root "$EVIDENCE"
```

The launcher executes the existing transaction as:

```text
python3 -B -m experiments.mineflayer_cognition_llama_cpp_transaction
```

The `-B` flag is part of the physical launcher contract. It prevents Python import bytecode from creating checkout-local `__pycache__` / `.pyc` files before the transaction's clean-check precondition runs. The clean-check itself is intentionally not weakened, generated files are not hidden through `.gitignore`, and the launcher does not delete or reset operator files.

For physical qualification, direct `python -m experiments.mineflayer_cognition_llama_cpp_transaction` invocation is non-canonical because ordinary Python bytecode caching can dirty a fresh checkout before preflight. The launcher changes no llama.cpp, GGUF, attestation, request, condition, repeat, retry, or evidence semantics; it only supplies the import environment required by the existing clean-check contract.
