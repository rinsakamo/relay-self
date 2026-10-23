# SelfWorld v0 — source-bound observer-local Present composition (#633)

**Status:** OFFLINE DEVELOPMENT. Not physical World qualification, not science, not a permanent world model.

## Why a view, not a new owner?

Existing [Present projection](../adapters/mineflayer/present_projection.py) already
owns the bounded native observation translation; existing
[PersistentCognition](../src/relay_self/persistent_cognition.py) owns governed
Memory, [Belief](../src/relay_self/belief.py) owns fallible evidence assessment,
and [Prediction](../src/relay_self/prediction.py) owns bounded hypothetical
transitions. ATT handles candidate selection; S16/S17 handle Action result and
learning-feedback authority. No additional semantic, database, execution,
inference, or memory owner is justified merely by viewing these together.

`src/relay_self/self_world.py` composes an immutable one-epoch
`SelfWorldView` for **one observer identity, one session, and one epoch**.
No World reconstruction, global map, mutable state, observation polling,
inter-Self transport, or Action issuing takes place.

| Origin | Actual input | Meaning |
| --- | --- | --- |
| OBSERVED | `WorldObservation` from scoped target Present | exterior details actually in that bounded, attributed probe (not currently authoritative truth) |
| REMEMBERED | explicitly selected `Memory` from **own** `PersistentCognition.identity.self_id` | past governed content, not current measured reality |
| INFERRED | existing `BeliefAssessment` with source evidence | fallible BLF assessment; conflict/undetermined -> UNKNOWN |
| HYPOTHETICAL | scenario-local existing PRD `PredictionState` | possibly impossible imagined environment |
| PREDICTED | exact scenario-linked `PredictionResult` | conditional model forecast, never measured World |
| UNKNOWN | no qualified input, missing target, unqualified inference | ignorance, not evidence of physical absence |

The target-specific adapter `adapters/mineflayer/self_world_projection.py`
projects native-observable entity identifier (as BLF-compatible `entity-N`), label, 3D position and distance. The native numeric ID is session-local, not a universal entity identity.
Optional visible Action is representable but not invented if absent. It does
**not** project other Self's cognition, intent, body resource, memory or secret
attributes. Core code never imports Mineflayer packets.

## Coverage, freshness and privacy

All observations retain their source reference and
`observer_id/session_id/native_seq/request_id`, bounded coverage
scope/radius/cap/candidates/truncation, and optional source-supplied
`observed_at_ns`. This value cannot be invented by the adapter; caller-provided
timestamp is *not* self-authenticating. `minimum_native_seq`,
`seen_observation_refs`, and an optional inspected-time/max-age check fail
closed on stale/foreign/replayed evidence. These cursors are caller-owned
inputs, **not** a second persistent store. Native seq, monotonic nanoseconds,
decision epoch and Paper `World.getFullTime` are different clocks.

An unlisted entity remains UNKNOWN even when the bounded source reports
no nearby candidates: **no global absence or safety conclusion** can follow
from limited Minecraft registry coverage. A stored OBSERVED fact describes the
historical observation, not the actual present World.

For Memory, `memory_ids` must be explicitly chosen from a
`PersistentCognition` snapshot whose identity matches `self_id`;
passing private B memories as A is rejected. Two Selfs can each compose
views for the same World without automatic dissemination. B's actual
SelfBody/SelfWorld/Memory is never fetched to model B from A. A may create
a *hypothetical* estimated B perspective, explicitly attributed to A, but
cannot read B's real internal experience.

## SelfBody join and action isolation

[SelfBody v0](selfbody-v0.md) retains exclusive scope over own bodily
representation. Its existing frozen view now supports an **optional**
`self_id` (legacy callers remain valid). Joining it to SelfWorld requires
explicit identical owner/session/epoch, plus identical native
seq/request/provenance when both share a Present observation. This is a
read-only reference, not a duplicated physical Body store. Without qualified
owner attribution, SelfBody cannot be joined; legacy L0/Action paths remain
unchanged.

```text
Physical World (external) -> existing Executor / readback / Present
              -> observer-local read-only projection
                   + own governed Memory
                   + existing BLF / PRD
                   + optional matching SelfBodyView
              -> one-epoch SelfWorldView for A
              -> existing ATT / L0-L1-L2 / S12-S17 authority (unchanged)
```

Hypotheses, predictions and memory never grant Action, mutate physical
World, alter M/P1 resources, or update governed learning. S16 `OUTCOME`
remains distinct from source observation, BLF update and LRN commit.
No new controller, FLY, message channel, intent issuer, or communication
protocol exists in this work.

## Stage E — bounded ATT observation consumption (offline)

A read-only **consumer path** now uses the existing ATT owner:
`select_self_world_attention(SelfWorldView, AttentionCriterion)` generates
only neutral-priority `AttentionCandidate` references for entities explicitly
present in that observer's bounded `WorldObservation`; existing
`select_attention` does the selection. `resolve_self_world_attention(view,
selection)` looks up selected entities in **the exact view** and returns
`WorldReading(origin=OBSERVED)` without any new authority.

ATT candidate identities incorporate observer ID, session ID, decision epoch,
native observation source reference and entity ID. Selected items and the
reported considered count must match the exact view on resolution; forged
payloads, replayed selections from previous epoch/probe or another Self,
and invented candidates are rejected. No implicit priority for a Zombie,
no automatic expansion to unobserved records, and no mutation of Memory/BLF
or World is possible. Empty/UNKNOWN Present produces an empty selection,
not a claim that the World is safe. ATT does not consume imagined/forecast
states as OBSERVED.

A's observed external position of B can be attended to. A's own conjecture
about *what B perceives* remains A-owned HYPOTHETICAL, and is never B's own
SelfWorld. Direct B Memory/SelfBody/knowledge access is excluded by typed
projection. Such estimates do not imply actual communication.

**Important scope:** This is actual consumption through the existing
`AttentionSelection` contract in synthetic/offline tests; the active
`ReactiveL0` native source + separate Action grant loop is **unchanged**.
There is no new L1/L2 live decision or controller wiring yet. Physical
execution must not begin depending on SelfWorld or ATT availability until
separate source/authority qualifications.

## Stage F — PRD discrepancy and governed S17 handoff (offline)

`review_self_world_prediction(prior, later, scenario_id, variable_key,
max_native_seq_gap)` is a **read-only** cross-decision-epoch evaluation of an
existing one-step PRD result against an explicitly later bounded native
observation. The prior PRD input must be source-bound to the exact prior
Present reference and specific exterior entity target; the forecast must
equal the existing deterministic `predict_transition` result. The same
observer/session, increasing native seq, distinct epoch and nondecreasing
source-supplied timestamps (if both provided) are required. The maximum
native seq gap is **caller-specified**, not a claim about elapsed World ticks
or causal time; an excessive gap is UNDETERMINED.

The only v0 comparable PRD variables are `entity_visible` (True on actual
positive observation; never False on missing coverage), `entity_label` and
`visible_action` (only when source explicitly supplied). A missing target,
truncated or unqualified coverage, absent property/PRD value and type
incommensurability yield UNDETERMINED, **not** proof of absence. It emits an
immutable `WorldPredictionReview` with MATCH, MISMATCH or UNDETERMINED,
predicted/observed values and lineage. It never updates BLF, Memory, Habit,
LRN, M/P1 or World and cannot establish the cause of the mismatch.

The target-owned
`adapters.mineflayer.self_world_projection.interpret_self_world_mismatch_as_s17_feedback`
provides an **optional** gate into the already existing S17 function:
the mismatch must be source-qualified, must originate from a scenario
explicitly bound to the exact Action ID, and the S15 `WorldConsequence`
must be EXECUTED with a genuinely sourced native after-probe identical to
the later `WorldObservation`. The S16 outcome must be OUTCOME /
`observed_execution` with matching Action, session, binding and world
provenance. The existing S17 operator then verifies the current terminal
Action and **caller-supplied** `ActionFeedbackCriterion`. It can return
`NOT_APPLICABLE`; MISMATCH is not a default reward, and neither feedback
direction nor target is generated by SelfWorld.

Even PRODUCED S17 `LearningFeedbackInterpretation` is **not** a retained
update: `propose_learning_update` and `commit_learning_update` remain
separately owned by existing S10/LRN, requiring their own exact target,
revision, rule and explicit `LearningUpdateAuthority`. Source-limited
comparison and S17 output do not imply predicted Action causality. Real-world
matching of predicted physics to independently attested World time, R
qualification and V scientific effects are still open.

## Stage G — actual S47 bounded/THINK/OPEN request consumption and S10 readback (offline)

`bind_self_world_to_cognition_request(view, attention, request, ...)` projects
only source-qualified, selected OBSERVED exterior entities (plus explicit
UNKNOWN metadata) to existing `CognitionDatum` entries on an existing
`BoundedChoiceRequest` or `OpenCognitionRequest`. It **does not invoke** a
model, allocate cognition, change candidate choices or focus, authorize Action,
read private B cognition, infer safety, or commit any retained state. All keys
are reserved and non-overwritable; stale/foreign ATT results and past-epoch
review are rejected. Typed PRD review is separately tagged with the original
forecast, later observation, and MATCH/MISMATCH/UNDETERMINED status, **never**
as measured Action success.

An optional governed S10 read requires an explicit
`retained_owner_self_id == view.self_id`, exact currently supplied
`LearningPreferenceState` object identity, and
`RetainedPreferenceRead` accepted again by the existing
`read_retained_preference` check, including revision and commit metadata.
The **caller** must authenticate which current S10 owner belongs to which
Self: S10's scalar state has no native Self ID, and this binding makes no
unearned claim of cryptographic or autonomous cross-Self authorization.
Absent owner qualification means omit the retained datum entirely.

An offline fixture now exercises the entire existing S17 (source-qualified
Action outcome with explicit INCREASE criterion) -> existing S10
`propose_learning_update` -> explicit `LearningUpdateAuthority` ->
`commit_learning_update` -> exact next-epoch read -> existing
S47 `allocate_cognition` with a deterministic fake `RelayEngine` provider.
The fake provider demonstrably *consults* governed `risk_weight` (3/rev0
vs 4/rev1) and selects different bounded choices (WAIT vs RECHECK). This is
a **known synthetic policy dependency**, not autonomous policy learning,
LLM improvement or physical action. Existing THINK and OPEN budgeted paths
also consume the same qualified context without a second engine or writer.

Outstanding before live S/L activation: certify the actual caller-owned
current scalar owner/Self identity mapping; source-clock/tick correspondence
and temporal relevance; hard-bound cognition budgets, provider sanitation
and request provenance; real L1/L2 consumer wiring, owner-qualified
subsequent epoch reuse, independent R physical qualification, and V
pre-registered adaptive-effect comparison. Existing L0 native
probe/Action-grant loop remains unmodified.

## Stage G — existing L1 Habit / L2 PRD consumption (offline)

`project_self_world_l1_l2_inputs(prior, current, retained, memory_ids,
scenario_id, variable_key, max_native_seq_gap)` rechecks the **exact
source-bound** Stage F prediction review. It projects that already-qualified
MATCH/MISMATCH/UNDETERMINED and the explicitly selected **own retained**
memory identities into the two *existing* input types:

- `HabitCue` / `CueFeature`: caller's preexisting `select_habit` may
  match explicit rules for observation/error/memory. SelfWorld does not
  invent salience, action or habitual preferences, or write new repertoire.
- `PredictionState` / `StateVariable`: caller's existing PRD
  `predict_transition` can apply explicit rules to the same source state.
  Trace retains exact prior/current observation source refs, target ref,
  PRD rule provenance, and selected Memory's source and integration provenance.

The joined `PersistentCognition.identity.self_id` must equal the current
observer, every requested `memory_id` must belong to that snapshot and be
present **identically** in the current `SelfWorldView.memories` selection.
Memory free text is **not** automatically parsed into a physical claim,
rule, cognition reward or event. A missing target is represented as
`observed_target=False` meaning *not positively seen in the bounded probe*,
not *absent in the World*. `observed_value` is omitted entirely when missing.

Synthetic tests exercise the **actual** existing `select_habit` and
`predict_transition` operations: mismatch vs match produces distinct
read-only outcomes under caller-supplied rules; a private retained Memory
changes which explicit habit/PRD rule matches; without that exact private
Memory there is no such selection. Another Self's memory, spoofed view,
stale/replayed epochs, and UNKNOWN-as-error fail closed.

This is L1-/L2-**mechanism reuse, not live cognition orchestration**.
It does not plug into the native L0+L2 executor's active asynchronous
decision loop, allocate real provider calls, commit LRN, create a route,
admit/authorize an Action, prove an earned habit or show real-world learning.
The present retained memory must originate from separately governed owner
updates: SelfWorld cannot write or elevate it.

## Tests and limits

`tests/test_self_world.py` uses offline synthetic fixtures for two observers
in one imagined World, private state non-leakage, stale/foreign/duplicate
source, bounded/truncated coverage, memory ownership, BELIEF provenance,
impossible counterfactual, SelfBody owner and source ID mismatch, and
no dependency on SelfWorld for existing L0. The test does **not** execute
the Java/Node World, qualify physical causality, test communication or show
coordination benefit.

Unresolved: independently authenticated native observation/time/World ID,
explicit L1/L2 runtime consumer, S17/LRN learning from failed predictions,
source-warranted other-Self action observations, authorized communication
and social/coordination experiments, Paper tick/control attribution and
R/V qualifications. Only future source-warranted integration may address them.


## Stage H — verify cognition-bound review before decision admission

When an optional `WorldPredictionReview` is included in
`bind_self_world_to_cognition_request`, the caller **must additionally supply**
the exact prior `SelfWorldView` and a positive `max_native_seq_gap`.
The binder reruns `review_self_world_prediction` against that prior and the
current observer-local view, then requires **full equality** of the caller
witness with the recomputed result. Missing, replaced, stale, counterfeit,
or gap-inconsistent witnesses fail closed. Supplying unmatched prior/gap
without a review also fails closed.

This hardens read-only L1/L2 cognition *inputs*, not S17's authority gate.
It does not make a forecast a reward, cause an LRN write, grant physical
actions, authenticate caller-controlled source bytes, or prove a live
adaptive effect. Tests cover a valid mismatch, missing earlier source,
forged MATCH status, substituted but internally valid earlier forecast,
and an insufficient native-seq window. The S49 native observation/Action
owner remains unmodified. Physical/qualification/science execution: none.

## Stage I — optional live S49 observation -> existing L1/L2 advisory sidecar

The S49 native host still owns **all** real probes, L0 decisions, routing and
the sole physical Action issuer. Its existing `live_probe` callback is the only
input to `LiveL2Observer`. The new **opt-in**
`self_demo --run-disposable --live-think --self-world-live` mode feeds those
already-acquired native probes through the existing `MinecraftPresent`
projection and `SelfWorldView`/ATT/PRD/HABIT/RelayEngine input datatypes.
No additional Minecraft probe, movement, executor, or second model caller is
introduced.

At the first probe containing exactly one positively observed zombie, an
ephemeral, source-bound **hypothesis** is created: the same native entity's
observed label will persist. This is a fixed baseline PRD rule, **not** learned
dynamics or expected physical truth. The following probe in the same session
yields MATCH, MISMATCH or UNDETERMINED using the existing strict review
(64-sequence maximum, not wall clock or World tick). An entity missing from
bounded/truncated coverage yields UNDETERMINED, never false absence/safety.
There is no forced L2 call if no qualifying initial probe arrives.

The existing `select_habit` reads a newly supplied **preconfigured cognitive
repertoire** with two rules: mismatch -> cognitive `RECHECK`, match ->
cognitive `OBSERVE`. Unknown leads to NO_MATCH. These refs are **neither**
movement commands nor retained learned Habits. The existing
`bind_self_world_to_cognition_request` revalidates the exact prior PRD
witness and produces a source-constrained `BoundedChoiceRequest`; the
`LiveL2Observer` submits a *read-only natural-language question* incorporating
that validated context through its existing single S60 model lease. This is
L2 **input consumption**, not a RelayEngine choice/Action run. The original
non-SelfWorld live mode behaves as before.

Malformed or unqualified optional SelfWorld source projection is rejected with `SELF_WORLD_INPUT_UNQUALIFIED` and **does not interrupt the existing S49 L0 owner**. This is an observer-side failure, not an L0 or Action veto.

Any newer native probe fences the earlier L2 reply using the existing S60
owner, including when the provider returns after World advanced. Model
output is never parsed into `Action`, `LearningFeedback`, S10 commit or
persistent Habit. A sidecar receipt records the observer-local prior/later
Present refs, review status and reason, preconfigured L1 cognitive candidate,
and L2 input-bound flag. No private other-Self Memory is exposed.

Synthetic offline `tests/test_self_live_think.py` covers a delayed single
model attempt, an observed label mismatch with identical native entity ID,
matching label, unobserved/truncated target, foreign-session/replayed probe,
and subsequent stale L2 output. No Java, Minecraft World, R qualification,
V science, energy accounting, actual learning or adaptive effectiveness is
certified. This is an opt-in product **DEV_ONLY** interface; `--self-world-live`
requires both the existing native opt-in and `--live-think`.

The next gate is an explicitly authorized disposable physical DEV check of
native input and sidecar receipts, followed separately by governed retained
Memory/S17/S10 causality and V pre-registered controls. No SCIENCE inference
from these synthetic unit tests.


## Stage J — physical DEV entry, prospective / no automatic promotion

The product CLI now admits one additional **DEV_ONLY** scenario:

```bash
# Prepare a NEW absolute evidence root under a pre-existing unprotected parent.
PYTHONPATH=src:tests:. python -m adapters.mineflayer.self_demo \
  --mode DEV --dev-scenario native-selfworld --run-disposable \
  --confirm SELF-DEMO-I-OWN-DISPOSABLE-WORLD \
  --output-dir /tmp/unique-stage-j-dev-root \
  --live-think --self-world-live \
  --model-alias stage-j-backend-not-attested --model-port 16559 \
  --model-timeout 1
```

This uses the **original S49** source World and single issuer, plus the
existing `LiveL2Observer` and S60 single-attempt loopback client. The model
alias/port are explicitly supplied but **do not certify a running L2 backend**:
an unavailable loopback model is an allowed `UNCONFIRMED` provider outcome.
This entry qualifies only whether genuine native probe sources reached the
existing SelfWorld review / L1 / read-only L2 **input boundary**, not whether
a real LLM reasoned correctly or changed an action.

The DEV receipt remains `DEV_ONLY` regardless of the native report's
classification text and cross-checks both prior/later SelfWorld source refs
against the original S49 `source_pair_trace` (exact event/probe seq + request
ID), in advancing native order. A forged sidecar cannot qualify merely by
claiming a valid SelfWorld status. The receipt records review status,
preconfigured L1 cognitive suggestion, model-attempt count, and source-bound
input qualification. It fails with `NOT_OBSERVED` if no two-source bounded
review was established; missing or cross-session sidecar, Action authority,
or bogus owner invariants fail closed. Raw owner reports and failed receipts
are retained; no existing run or grant is replaced.

An offline test with a fabricated native report proves only **the gating and
reporting code**, not physical execution. Physical DEV must additionally
attest server/client cleanup, source continuity and native probe receipts.
Independent R qualification and V science remain separate gates; real
S17/S10 causally retained updating is not part of this Stage J check.

### Prospective one-shot DEV run gate (2026-10-18)

The one-time push marker `[selfworld-stage-j-dev-once]` is admitted only on
`self/product-self-one-command-selfbody-20261018`, `github.run_attempt == 1`,
and *after* all four same-HEAD FAST jobs succeed. The job operates within a
unique runner-local absolute output root and uploads unchanged DEV receipts,
native report, logs and sidecar even if the run fails. This is not a reusable
qualification grant; no rerun is assumed, and the first result controls the
run's recorded DEV outcome. The model port is explicitly unverified, so
this run measures native-source input binding rather than model inference.

## Stage K — retrospective same-target native S16 before/after replay

The three live S49 stimulus identities are **deliberately distinct**; a
Stage J first/next S49 L0 event pair cannot be promoted to same-entity PRD
verification. Stage K therefore reuses the original decoded **S16 before +
after native Action snapshots** already captured in each closed S49 Action
receipt. This does not send any Minecraft probe or modify the frozen S49
Action owner. The fixed `entity_label` persistence hypothesis is reconstructed
**after the run** from a positively observed pre-Action zombie and compared to
a later source with the exact same native entity ID.

The adapter `review_saved_s16_action_self_world` re-verifies the original
S16 frame sequence, dispatch, cleanup and horizontal movement against the
unchanged action evidence; it decodes both snapshots with the canonical native
snapshot parser. `review_s49_action_self_world_report` separately checks the
original completed S49 event/action binding. Result statuses may be MATCH,
MISMATCH or UNDETERMINED; not seeing the same target after the Action is
**UNDETERMINED**, never presumed absence, death or goal success. The
`s16-evidence-...` strings are explicitly **local receipt locators**, not
native wire request IDs.

Crucially, because the hypothesis was reconstructed retrospectively, a
MATCH or MISMATCH only tests typed evidence comparison. It **cannot** attest
prospective cognition, actual in-World prediction issued before Action,
causation, learned S11 Habit, S17 Feedback or S10 learning authority.

First apply this read-only replay to the separately preserved Stage J
physical DEV artifact #12128397812, without rerunning the world, after
focused CI and artifact-byte integrity checks. A verified physical-source
review can motivate a *separate* future prospective live prediction test.
The existing Stage J original results and qualification limits are immutable.

### Stage K archive readback — one-shot diagnostic run (2026-10-18)

`[selfworld-stage-k-archive-once]` permits exactly one push-triggered,
same-HEAD, FAST-CI-gated, read-only review of immutable Stage J artifact
`12128397812` (upload ZIP SHA256
`3b127778a8a6a2483a8f30649edbb3334229fb2f2f92cba720f084f36dfc467e`).
The job uses only saved original `native_report.json` /
`dev_receipt.json`, never starts Java/Node/Minecraft, and keeps the
retrospective comparison separate from Stage J's prior-live UNDETERMINED.
A label-persistence agreement is a **retrospective deterministic source
comparison**, not evidence of prospective inference, genuine model skill,
reward, S10 update, or physical causation.

## Stage L — prospectively sealed S49 native observation -> S16 review

Stage K reconstructed the label-persistence baseline AFTER physical execution. It
must never be used to assert prospective capability. Stage L supplies a new,
explicitly opt-in `--self-world-prospective` flag for the existing
`--mode DEV --dev-scenario native-selfworld --live-think --self-world-live`.
The flag is disallowed for non-DEV and non-SelfWorld scenarios. It never
changes S49, grants an Action or creates a second observation/LLM route.

The existing S49 `live_probe` receives an already-correlated native
`MineflayerObservation` **before the S49 host selects/executes an Action**.
A product-only source observer builds an existing typed `SelfWorldView` and
`PredictionState/TransitionRule` for the one positively observed zombie.
The fixed, deliberately weak rule is `entity_label: zombie -> zombie`; this
rule is **not learned** and it does not encode Action effects. Its original
observer/session/event/probe/request/target IDs, original bounded coverage,
source ref and predicted value are appended to a fresh exclusive
`stage_l_prospective.jsonl` with hash chaining and an `fsync` **before the
callback returns to S49**. Failure of this optional product recorder is
contained and cannot veto L0. Ordinary Stage J mode does not create it.

Only after S49 has finished can `verify_prospective_native_reviews`
compare those sealed source claims to independently saved S49 event/probe
source pairs, original decision target/issued flag, and S16 native
before/dispatch/cleanup/after observations. S16 evidence is validated with
the existing strict `verify_native_action_evidence`. It rejects forged
hashes, reordered/missing prior records, wrong session/target, invented
pre-Action source order, and mismatch between the original before snapshot
and earlier observed subject. The **actual later** bounded observation
produces MATCH, MISMATCH, or UNDETERMINED using the existing
`review_self_world_prediction` contract. An unseen target remains
UNDETERMINED. The existing Stage J L2 model attempt is independent; an
unreachable model remains UNCONFIRMED, not a failure of source projection.

Source files, checksums, receipts, provider status and the forecast witness
remain **DEV_ONLY**. A local hash-chain plus a sequential callback is strong
development evidence of pre-Action software ordering, but is not an
independent trusted timestamp or native protocol attestation and cannot
demonstrate that the Self learned an effective model, acted because of a
prediction, or deserved S17 reward. S17 Feedback, S10 commit, retained Habit,
other-Self private data and R/V privileges are all absent.

A prospective one-shot job is gated by same-HEAD FAST 4/4 CI and commit
marker `[selfworld-stage-l-dev-once]`. It uses one NEW isolated disposable
Minecraft World and preserves the complete Stage L original evidence on
success or failure; it does not reuse the consumed Stage J physical grant.
No SCIENCE status can be inferred from this development check.


## Stage M — governed evaluation / retained next-epoch controls

A forecast outcome alone is **not** an S17 reward, S10 learning event,
retained Habit, or Action authority. In particular Stage L's two prospective
`entity_label` MATCH witnesses only establish a weak fixed-rules
source comparison. This does not satisfy the separately owned S17
`ActionLifecycle`, `ActionOutcomeInterpretation`, explicit
`ActionFeedbackCriterion` and current S10 owner authority.

The pure, opt-in
`adapters/mineflayer/self_world_learning_gate.py`
`evaluate_governed_stage_m` composes the **existing** source-bound SelfWorld
review, S17 bridge, `propose_learning_update`,
`commit_learning_update`, exact-owner `read_retained_preference`,
ATT and one-call existing `RelayEngine` bounded cognition. It requires
a *newer same-self/session native observation* as the next epoch.
Positive observed MISMATCH + matched explicit S17 criterion + granted
current S10 authority are the only permitted learning branch.
MATCH, UNDETERMINED, feedback OFF, unmatched criterion, LRN OFF, denied
authority, stale owner and forged source cannot commit. The resulting
read-only cognition cannot issue Minecraft Actions.

The **synthetic** S17 source chain and deterministic threshold provider in
`tests/test_self_world_learning_gate.py` yield ON
`risk_weight:3/rev0 -> 4/rev1` and next cognitive `WAIT -> RECHECK`.
OFF, learning OFF and mismatched-criterion sham keep rev0/value3 and WAIT;
missing or denied authority fails closed. This measures the **interface
dependency** with a fixed test provider; it does NOT demonstrate Self
learning, real model reasoning, causal behavioral improvement, fatigue
adaptation, or any new World attempt.

The separately retained Stage L physical DEV artifact
`12129387412` is a valid source of original pre-Action prediction and
S16 readback, but is **not** a portable S17/10 permission. The source-only
readback function `audit_stage_l_physical_learning_readiness` verifies
the exact Stage L source and leaves the result
`BLOCKED_MISSING_TYPED_S17_AND_S10_AUTHORITY`; it refuses to fabricate
typed Action lifecycle, criterion, owner snapshot or update grant from a
JSON report. An exact-archive read-only GitHub job
`[selfworld-stage-m-source-gate-once]` checks immutable ZIP SHA-256
`3993d389617bd32fd2e24030cbf6fa3434f609ff5473a56dcf3405a7efa58216`,
original DEV receipt identity and internal SHA256SUMS, and stores a
separate *DEV_ONLY* blocked/not-qualified audit output. It runs no Java,
Minecraft, Node, Action, L2 provider or learning state transition.

A future **actual physical adaptive** Stage N requires a prospective,
authorized S17 Action/outcome receipt and criterion source, with a
current S10 owner grant and a subsequent real World epoch. Its ON/OFF/sham
control and stop/cleanup must be separately attested before any R or V
claim. Do not merge existing PR #634 or rewrite Stage J/K/L evidence merely
because synthetic Stage M tests passed.


## Stage N — original typed S49 closure, read-only S17 (DEV)

Stage M demonstrated the S17->S10->next-epoch dependency ONLY with a
synthetic Action/Outcome and a fixed test provider. The original physical
Stage L artifact must not be rewritten as live S17 authority.

Stage N adds an explicitly opt-in `--self-world-typed-closure` that requires
`--mode DEV --dev-scenario native-selfworld --live-think
--self-world-live --self-world-prospective`. The normal S49
`NormalSessionActionExecutor` retains the **only** physical Action
grant/issuer and original immutable S16 closure. An off-by-default
context-local observer is called only **after** its existing
`ActionSupervisor` has reached terminal state. The observer receives
the original typed `ActionLifecycle`, `ActionOutcomeInterpretation`,
`WorldConsequence` and correlated original native probe. No report
is deserialized into Action capabilities, and no second executor is created.
A failed observer cannot stop L0; its failure is retained and denies Stage N
DEV certification.

The DEV operator's narrow `StageNDeclaredPolicy` must be fixed before
World startup: exact native `MOVE_BACKWARD`, observed `OUTCOME` and
`observed_execution` qualify an existing S17 **HOLD** feedback for
`risk_weight`. The target/action/binding/session are then bound to the
actual independently closed Action. The direction is NOT inferred from
forecast MATCH/MISMATCH, survival success, or reward. The original S17
`interpret_action_outcome_as_learning_feedback` owns interpretation,
not the Stage N observer. The source probe is not reissued. Optional errors
and typed result refs are saved in `stage_n_native_feedback.jsonl`.
The next read-only native source is observed only via original S49 probes;
no learned behavior is fed into Action or L0.

There is **no** automatic S10 owner grant, proposal/commit, new learned
Habit, selected new Action, or real adaptive-effect proof. A HOLD feedback
is deliberately conservative (it does not alter the retained scalar);
it demonstrates live *qualified Action-feedback wiring*, not a discovered
training signal. R qualification, V science, independent STOP ACK and L2
model-identity attestation remain separate.

The new `selfworld-stage-n-typed-closure-once` GitHub job runs only on a
new single-use `[selfworld-stage-n-typed-closure-once]` marker commit on
the S feature branch, after all four required FAST jobs succeed, with a new
unique disposable World/evidence root. Success and failures preserve a new
original evidence artifact; previous Stage J/K/L/M runs, grants and
receipts remain untouched.

## Stage O — original S49 L0 retained owner identity handoff (DEV_ONLY)

Stage N confirmed the actual typed S16 Action/OUTCOME -> S17 HOLD path in one
new disposable World, **without** granting S10 updates. The original S49
host's `NormalWorldL0` retains a particular immutable
`LearningPreferenceState` constructed from frozen S19 (value 4/rev1), not
a value reconstructed from a native-report JSON file. The S10 contract
requires *object identity*, exact owner/target/revision, and independently
supplied learning-update authority.

Stage O adds an OFF-by-default, context-local
`observe_original_retained_owner` tap at construction of the existing
`NormalWorldL0`. It forwards exactly the original `self.retained` object
to a typed read-only `NormalRetainedOwnerReadback`; it does not overwrite
the host's retained snapshot, subscribe to a second executor, change
S49 decision logic or call `commit_learning_update`. Stage O product code
`StageOOwnerReadback` uses the original
`read_retained_preference(owner, owner, ...)` identity check for each
already-correlated future S49 probe. Replayed/foreign sources, owner copies,
denied/no S10 update authority and duplicate handoffs have negative
controls. An observer failure is isolated from the original L0 owner,
and any missing live witness causes DEV receipt rejection.

The explicit `--self-world-retained-handoff` requires the full Stage
L/N native-selfworld DEV source/typed-closure flags. The one-shot
`[selfworld-stage-o-owner-once]` marker causes **one new independent
disposable DEV World** only after exact-head FAST 4/4 gates pass. It
records the original S49 owner value/revision and every existing epoch
probe in `stage_o_retained_owner.jsonl`. The expected development witness
is exact original owner identity, `risk_weight` 4/rev1, all 3 native
probes, and unchanged original L0 policy and Action owner. S17 typed
readback remains available from the separate Stage N sidecar.

This is only an owner **read handoff**, NOT learning. In particular an
observer does not receive a physical Action grant, current S10 update
authority, ownership transfer, permitted mutation of original S49 L0, or
a genuine learned policy. S10 commits remain 0. A later, separately
governed Stage P must establish a real predeclared learning direction and
authoritative commit/next-epoch owner transfer with ON/OFF/sham controls;
a manufactured equal-looking copy or a preconfigured cognitive threshold
does not count.


### Stage O follow-up — live typed S17 to owner-bound S10 HOLD *proposal* (DEV gate)

The existing original S49 owner remains the only L0 policy/Action issuer.
The Stage N typed terminal observer now returns its original in-memory
`LearningFeedbackInterpretation` after the S16/Action and S17 checks.
The opt-in Stage O owner sidecar composes this with the SAME exact S49
retained owner and the already-correlated native probe to call existing
`propose_learning_update` for the independently predeclared conservative
HOLD rule. It never deserializes a JSON authority, constructs a S10 grant,
invokes `commit_learning_update` in the live World, or replaces
`NormalWorldL0.retained`. All feedback proposals are tagged
`s10_commit_attempted=false`; the additional source counts are advisory
DEV evidence and are not learning. A missing/foreign/duplicate/stale
source, mismatched Action/binding/session, sham S17 result, or attempted
directional reward fails closed.

The offline tests separately show that a **synthetic test-only grant** can
commit an unchanged HOLD state with a +1 revision in S10. A missing grant
is rejected, a replay is rejected, and the resulting new object is NOT
automatically the original physical L0 owner's current snapshot.
This offline test does not qualify a genuine S49/S10 authority source.
The frozen S49 runner stores `retained` as an independent local rev1
variable and its native S14 admission is explicitly anchored to revision
1; changing the host's L0 snapshot in an observer callback would create
a split owner/admission and is therefore prohibited.

**Physical Stage O2/O3/O4 remain BLOCKED.** A future owner-controlled
DEV-only epoch boundary must simultaneously transfer a legitimate
non-observer S10 update authority and the resulting exact immutable
snapshot to BOTH L0 choice and S14 admission, without silently
rewriting frozen S49 or issuing an extra Action. The current S10
`LearningUpdateAuthority` dataclass validates target/granted/provenance
but does not itself attest live-session issuer/owner identity: arbitrary
construction in a sidecar is not proof of rightful physical authority.
Only after a real owner-issued handoff and ON/OFF/sham controls should a
new disposable World be launched; HOLD commits would prove revision
bookkeeping, not a learned policy difference or causal adaptive effect.

Stage O typed-proposal physical DEV note (2026-10-18): the next
`selfworld-stage-o-owner-once` attempt is a new, disposable,
CI-gated World run for typed-S17-to-S10 **HOLD proposal only**.
No S10 grant, revision commit, policy update, or adapted Action is
expected; all earlier Stage N/O original artifacts remain immutable.

## Stage P — S10 dual-consumer next-epoch *offline rehearsal*

Fresh audit of S49 at Stage O final HEAD showed two **independent frozen
revision-1 assumptions** that prevent real-world post-commit adaptation:

1. `adapters/mineflayer/s49_normal_session_real_ci.py` builds
   `NormalWorldL0(..., retained)` from S19's synthetic rev1/value4
   and separately closes over that SAME initial `retained` for
   `_native_epoch_two(..., expected_revision=1)` inside `on_action`.
   Updating the host's L0 snapshot alone would split Action admission.
2. `relay_self.world_conditioned_choice.select_world_conditioned_choice`
   itself only accepts `risk_weight` 4/rev1. A legitimate S10 **HOLD**
   commit advances rev1 to rev2 (even with unchanged value4), so the L0
   chooser rejects the newly committed input *before any native decision*.

These are intentional frozen S49 contracts, not authority defects to bypass.
Stage P does NOT loosen them, patch the pinned S49 runner, or fabricate an
independent physical Action issuer.

The new S-only
`adapters/mineflayer/self_world_epoch_handoff.py`
`prepare_stage_p_offline_dual_read` is an **OFFLINE-only pure rehearsal**:
it requires the identical pre-commit owner object for both L0 and S14
consumers, original typed S17 HOLD/proposal provenance, a later correlated
same-session native probe (synthetic in focused tests), and caller-supplied
`LearningUpdateAuthority`; it invokes existing S10
`commit_learning_update`, then existing `read_retained_preference` TWICE
against the SAME exact new `LearningPreferenceState`. The returned frozen
`StagePOfflineDualRead` explicitly says no original S49 owner installation,
no real-world commit attestation and no adaptive Action. It does not claim
the caller-provided authority was issued by the legitimate live S49 owner:
existing S10 authority validates target/granted/provenance but carries no
independent current-session issuer proof. The positive test grant is
**synthetic and test-only**.

Focused tests compare absent/denied/wrong-target grants, stale proposal,
forged S17/action/next native source, next-source absence, source replay,
split or reconstructed initial owner references, sham/non-HOLD, and
feedback-instance substitution. A separate frozen-contract negative test
proves even a correctly S10-committed HOLD **rev2/value4** read is rejected
by current S49 `select_world_conditioned_choice`. These are development
interface checks, not a physical/causal learning demonstration.

**Qualification:** Stage P offline common-owner/dual-read contract only.
Live S49 S10 issuer authorization: **BLOCKED**; physical S10 commit: **0**;
post-commit native L0 and S14 both consuming rev2: **NOT PROVEN**;
learned ON/OFF/sham action effect: **NOT PROVEN**. To advance safely, S
must first obtain an explicit owner-controlled, DEV-only replacement for
the frozen S49 revision and admission coupling, with provenance/identity
proof and single-writer Actions. Such a migration requires separate
contract review; adding a sidecar that merely flips `host.retained`
would be incorrect. No automatic R/V promotion.

## Stage Q — joint original choice/S14 offline DEV successor

**No new real World run or independent S10 authority**. Stage P preserves
the exact next native `MineflayerObservation` object (not merely a seq/request
string). Stage Q exposes a separate, opt-in
`select_stage_q_dev_committed_world_choice` in
`src/relay_self/world_conditioned_choice.py`. The historical
`select_world_conditioned_choice` still requires the frozen
`risk_weight=4/rev1`; the DEV entrypoint requires the exact
`LearningCommitResult` and same `LearningPreferenceState` object with
a legitimate *structural* S10 successor record, then executes **the
identical internal S42 selection/PLAN algorithm**, not a copied policy.
This guards against simply relaxing the old revision check.

`adapters/mineflayer/self_world_epoch_control.py` calls the original
`_native_epoch_two` (ATT/BLF/CNC/PRD/PLAN/ROUTE/ADMISSION) with
`expected_revision=current.revision` and both S14 owner arguments set to
the same Stage P committed object. It requires exactly the next native
observation object and precommit L0/S14 owner identity, an active
`escape-threat` intent, preexisting rev1/value4 source, value-preserving
rev2 HOLD, original near-threat MOVE selection, and agreement between
S42 and S14 candidate selection. It returns a **nonexecuting** readback
whose fields make the limitations explicit: no Action issued, no original
S49 owner installed, no independently attested S10 issuer, no evidence of
causal learning. Synthetic negative controls reject copied owners,
reconstructed successors, foreign source/intent, stale revisions,
sham feedback lineage and non-MOVE admission.

**Critical remaining physical blocker:** `NormalWorldL0._check` still
uses the frozen S42 entrypoint, and original S49 `on_action` still closes
over its initial rev1 snapshot. Stage Q shows both existing calculations
can be coupled on a successor without creating a second Action issuer;
it deliberately does not mutate either original live object or claim the
physical S49 host used the DEV function. To become runnable Stage R must
add one explicit, reviewed, single-writer owner transition at a terminal
Action/epoch boundary **inside the original S49 owner** and route both
original L0 and native S14 through that same owner. Any independently
supplied `LearningUpdateAuthority` must be authenticated by the actual
learning-authority owner; the synthetic test object is NOT that proof.
HOLD increments revision but provides no policy improvement or changed
Action evidence. DEV/QUALIFICATION/SCIENCE remain separate; no auto-upgrade.

## Stage R — opt-in S49 single-writer terminal → S10 HOLD → next epoch (DEV)

The **original** S49 `qualify` and `NormalWorldL0` now have
**default-off** `stage_r_dev` extensions, in an isolated Draft.
The previously frozen S49 test evidence/commit is not rewritten;
however, the *working S49 source on this Draft* has intentionally changed.
It cannot be described as bit-identical to the frozen original.

The change keeps S49 as the **sole** physical Action issuer:
`NormalSessionActionExecutor.execute` still requires the original
L0/S14, independently sourced PROPOSE and ISSUE grants. When explicitly
enabled *and* `S49_STAGE_R_DEV_ONLY=1`, S49 constructs exactly one
`StageRDevSingleWriter` bound to the same live `NormalWorldL0`,
`NormalSessionActionExecutor` and `IntentCommitment`.

The DEV transition has two separate phases. The existing
`observe_closed_native_actions` callback passes the **typed, already
terminal** original S16/S17 source to Stage N's predeclared
`MOVE_BACKWARD / observed_execution → HOLD` criterion; Stage O
proposes against the exact original S49 owner. The callback is NOT
learning authority. Only after S49's original `execute` returned a
verified OUTCOME, the same original S49 `on_action` seals that
witness against the executor receipt. No state changes at Action ISSUE
time, unknown outcome, or during a pending Action. At an independent
later original-session native probe (never invented or re-requested),
a separately scoped **S49 DEV operator-local** S10 HOLD authority is
created with the exact original Action ID/session/feedback. Existing
S10 `commit_learning_update` advances `risk_weight=4 rev1→rev2`
without scalar gain, and a synchronous token-guarded single-use
publication switches the **same original L0 host** to that immutable
successor. The original `on_action` obtains its S14 owner through the
same Stage R getter, not a captured initial snapshot; its
`_native_epoch_two` reads the owner's real revision. The default,
Stage-R-disabled path keeps the rev1 frozen selector, old snapshot and
normal Action admission. There is never a second S49 runner or a
new physical action loop.

**Important limits:** The separate S49 DEV learning permission comes
from the explicitly opted-in local operator role in this one process.
It is NOT cryptographically or externally independently attested.
The original S10 `LearningUpdateAuthority` dataclass validates
scoped fields, but does not prove a cross-run issuer. A PASS here would
be a **DEV-only owner-bound S10 HOLD update**; it is NOT evidence of
value learning, reward inference, new habit, better behavior, a
causal ON/OFF/sham result, or qualification for R/V. External issuer
qualification and non-HOLD adaptive criteria remain separate work.

CI includes synthetic terminal/owner/probe identity and stale/replay/
foreign/native-source and open-Action negative controls, plus direct
frozen-default regression. S49 emits original decision revisions and
requires the three decisions to read `[1,1,2]` and two real
closed Actions. The `self_demo` explicit
`--mode DEV --dev-scenario native --self-world-stage-r-dev` path
cross-checks these native readbacks and keeps engineering/science
claims false. A new GHA one-shot job is conditioned on the exact
`[selfworld-stage-r-dev-once]` marker, exact branch/head,
FAST four gates, fresh isolated root and pre-existing explicit
disposable-World consent. Registration alone does not execute it.

Stage R code must not be called an actual Minecraft PASS until a
fresh one-shot run with independently readable original
`native_report.json`, owner/Action/callback order and cleanup evidence
has succeeded, with every failed run preserved. This is not a
retroactive qualification of earlier Stage O evidence.

### Stage R one-shot DEV activation

The offline FAST check for the pre-trigger implementation completed 4/4 at
`e395c27859aa6f68a18a112df3b399d52b0b3463` (workflow
`39136131977`). The following marker commit is the distinct
**single-use**, **DEV_ONLY** physical attempt gate. The exact-head FAST
checks of the marker itself must all pass before one fresh disposable S49
World can run. Any World success/failure belongs exclusively to the new
attempt receipt; no earlier J–Q evidence is rewritten or promoted.

## Stage S — prospective separation-based S17 feedback, offline DEV only

**Qualification target:** distinguish *observed physical separation from one
verified zombie* from mere Action execution and SelfWorld prediction agreement.
Do not infer survival utility or cognitive adaptation from a signed distance.

The fixed, immutable `StageSPredeclaredSeparationRule` in
`adapters/mineflayer/self_world_stage_s_feedback.py` is a **candidate
future-trial criterion**, not a claim that the Stage R trial was
preregistered. An original S49 `NormalActionClosedReadback` must contain
a true terminal S16 OUTCOME and `MOVE_BACKWARD/observed_execution`;
its original S49 request ID, session, action/binding, and native typed
before and after World observations must agree. Exactly one original
zombie is required; the **same entity ID** must be observable in the
original, executor-before and executor-after registered entities.
All native coverage must be complete and nontruncated; the recorded
entity.distance must match its reported 3D positions to 1e-6 m.
Foreign sessions, repeated/scrambled seq, fabricated distance, swapped
Action/binding, incomplete coverage and duplicate target identities are
rejected. Missing target in a complete frame → **UNDETERMINED**,
not HOLD and not a fabricated reward.

The frozen prospective rule computes
`delta = exact_same_zombie_distance_after - distance_before`:
- `delta >= +0.100 m`: `SEPARATION_INCREASED → INCREASE` risk_weight.
- `delta <= -0.100 m`: `SEPARATION_DECREASED → DECREASE` risk_weight.
- otherwise `NO_RESOLVED_CHANGE → HOLD`.
Each qualified outcome is passed through the existing *S17 typed*
`interpret_action_outcome_as_learning_feedback` with full original
Action/S16/binding lineage. No S10 issuer/commit or Action issuer exists
in this module. These are local distance/candidate scalar preferences,
not biological reward, ultimate fitness, independent causal
consequences, or grounds for SelfWorld prediction-as-reward.
Threshold 10 cm is a **new heuristic requiring calibration**, not an
empirically validated effect size. Additional standards must pre-register
calibration, observation precision and missingness before SCIENCE.

**Historical Stage R artifact retrospective replay only:** the
unchanged [Stage R artifact #12139674420](https://github.com/rinsakamo/relay-self/actions/runs/39136472105/artifacts/12139674420)
(the original ZIP digest begins `a7e43d79`; archived files SHA256
5/5) includes the following exact source-native measurements:
- `s49-native-move-19`, same zombie ID 3: distance
  `2.000000000 → 2.166266053 m`, delta `+0.166266053 m`, hence
  retrospective `INCREASE` under the **new** Stage S criterion.
- `s49-native-move-48`, same zombie ID 5: distance
  `2.000000000 → 2.095951300 m`, delta `+0.095951300 m`, hence
  retrospective `HOLD` under that criterion.
These observations were collected **BEFORE the Stage S criterion was
declared**. They are post hoc calibration illustrations, **not**
prospective Stage S feedback delivered by S17 or any new S10 commit.
Do not retroactively change Stage R's sole authorized HOLD update,
relabel its artifact as preregistered, or turn its movement into reward.

The focused synthetic ON/OFF/sham tests require separately supplied
test-only `LearningUpdateAuthority`; absent grants abort. Original
rev1/value4 retains identity in OFF. Typed positive candidate with
synthetic S10 produces rev2/value5, but both old and new near-threat
choice are still `MOVE_AWAY`; **a changed scalar is NOT a changed
Action**. A negative-separation candidate proposes rev2/value3, and
original S42 `World geometry did not determine required route` rejects
its WAIT near-threat choice. This is a legitimate admission obstacle:
do not silently bypass S42's frozen near-MOVE invariant, let S14
admit contradictory Actions, or mint extra Action authority. A fake
feedback_id can pass S10's *structural* proposal check, so actual Stage
S deployment additionally requires independent typed S17 evidence and
an authentic learning issuer: `LearningUpdateAuthority` by itself
is not an external issuer proof.

**Stage S qualification:** interface/negative-control OFFLINE tests
may PASS; external learning-grant issuer qualification, physically
preregistered non-HOLD feedback, policy admitting a changed action,
causal ON/OFF/sham efficacy, independent R/V Science, and STOP ACK
attestation **remain unproven**. Keep current #634 Draft open and
protect historical Stage R runs; no new physical World is necessary
merely to replay this archive.

## Stage T — original L0 + native S14 directional-policy OFFLINE DEV preview

This stage is an **explicit alternative policy**, not a silent relaxation of
S42's original near-threat MOVE guard. Default `select_world_conditioned_choice`
still requires rev1/value4, and Stage Q / Stage R's original HOLD path retains
its frozen near-threat invariant. An opt-in Stage T entrypoint instead
accepts a *typed* Stage S directional S17 feedback, an exact same-object
S10 `LearningCommitResult`, `stage-t-dev-risk-weight-one-step` v1 step1,
and original rev1/value4 owner. It checks feedback identity against the
commit proposal, genuine Stage S criterion identifier/provenance, session,
original S49 Action event suffix, S16 observed-execution reason, S10
revision and record lineage. It accepts only bounded rev2/value3
(DECREASE) or rev2/value5 (INCREASE); HOLD or fabricated/duplicate owners
are denied. **This proves structural source lineage, not independently
authenticated S10 issuer identity.**

Under the separate, explicitly labeled policy
`stage-t-dev-retained-cost-v0`, the **same** S42 PLAN scoring is reused:
near zombie WAIT cost `2*risk_weight`, MOVE cost 7.
At value3, WAIT cost6 wins versus MOVE7; at value5, MOVE cost7 wins
against WAIT10. The existing near→MOVE invariant is changed **only**
for the non-HOLD Stage T DEV branch, and only when the exact typed
decrease shows value3. Far-distance WAIT remains the safe default.

`NormalWorldL0` has an independently guarded offline preview binding
(`bind_stage_t_dev_preview` /`install_stage_t_dev_preview`) accepting
exactly one matching previously requested S49 Action and the exact
S10 successor/typed S17. It is mutually exclusive with Stage R's live
owner token. **Original S49 `qualify` never calls these preview methods,
and the DEV CLI has no Stage T live flag**; the single original physical
Action issuer is unchanged. `self_world_stage_t_policy.py` invokes
the *original host's* `_check` and the *existing* native
`_native_epoch_two` ATT/BLF/CNC/PRD/PLAN/ROUTE/ADMISSION
against the SAME immutable retained snapshot/next native observation.
The preview mutates neither original Action supervisor, World nor
the next L0 cursor. A WAIT result is non-Action, whereas MOVE still
requires a **separate original L0 Action grant**, and subsequent
PROPOSE/ISSUE controls if physically executed.

Synthetic OFFLINE negative controls target copied old/new owner,
unauthorized or duplicate install, fake typed criterion/feedback,
foreign session/source, stale sequence, altered entity ID, missing
Intent, Stage R cross-bind and an unqualified Action grant. The ON
candidate (value3) can make original next L0 choose WAIT rather than
the OFF frozen value4→MOVE; the independent original S14 plan must
also select/admit WAIT. The value5 path still selects/admit MOVE, and
without a fresh Action grant it cannot be requested.
**No Minecraft run, physical non-HOLD commit or causal ON/OFF/sham
improvement is claimed.** Synthetic grants are not independent
issuer attestation, Stage S's 10cm threshold remains provisional,
and physically changing behavior requires a separately reviewed
original S49 operator grant and one-shot DEV preflight. Do not
equate selecting WAIT with an actual survival advantage. No
SCIENCE or R qualification promotion is permitted.

## Stage U — original S49 terminal-owner S10 issuer gate and near-WAIT safety split

**Scope: local, OFFLINE, DEV only.** This is NOT an independently
authenticated external S10 authority; it is independent of the S17
interpreter in-process, and only validates the *original* Action executor
state and exact terminal object identities. No Stage U live mode or
physical one-shot trigger is wired into S49.

`adapters/mineflayer/self_world_stage_u_gate.py` adds
`StageUDevOriginalExecutorIssuer`. It is constructed with the original
`NormalWorldL0`, its original `NormalSessionActionExecutor` and
the same `IntentCommitment`, plus the explicitly bound Stage T offline
preview token. It refuses Stage R mixed control and enforces an exact
initial S19 rev1/value4 owner. To issue its **one single-use local S10
authority**, it requires the actual original executor supervisor
`get(action_id)` object to be **identical** to the Action terminal in
both the closed S16 callback and the returned original receipt.
The same action must already have consumed its independent L0 Action
grant and be recorded in `executor._dispatched`; no issued Action may
remain open, terminal must be an OUTCOME, the original probe and
intent/session must agree, and its native after-observation must precede
a fresh, correlated later original native entities-event and probe.
An independently recomputed Stage S geometry-qualified, *directional*
typed S17 separation result is required. Unresolved/neutral or
prediction-only evidence is rejected without producing a grant.

When all evidence is consistent, the operator-local grant is consumed
before invoking the existing S10 `propose_learning_update` /
`commit_learning_update`. Only that exact immutable S10 successor
is installed for a **non-executing Stage T preview** on the original
L0 host, with original native S14 PLAN/ROUTE/ADMISSION reading the
same state; the return type contains all readbacks and explicit
`external_issuer_attested=False`,
`minecraft_session_started=False`, and
`on_off_sham_causal_gain_attested=False` flags. One-use prevents
duplicate terminal replay. This local in-process check DOES NOT
authenticate the host process itself, defeat a malicious host, or
replace an independent signed/qualified cross-process issuer.

**Crucial distinction:** S14 `WAIT admitted` is a **formal
PLAN/admission** decision, not a World safety qualification.
For a zombie inside the near-threat threshold, the Stage U disposition
is `NEAR_WAIT_READ_ONLY_NO_ACTION`: no new Action is issued, and
`physical_wait_permitted=False`,
`near_wait_safety_attested=False` without independently measured
damage/health/survival constraints and prior eligibility rules.
This read-only preview MUST NOT be wired into the live S49 WAIT path
merely because it is legal under the candidate allowlist.
The alternative MOVE choice is
`MOVE_NEEDS_SEPARATE_ACTION_GRANTS`: it still cannot issue a physical
action without the original distinct PROPOSE and ISSUE permissions.

Synthetic tests insert *explicitly synthetic* terminal snapshots into
the original executor supervisor and mark dispatch as synthetic.
They exercise object identity, closure/receipt equality, action
ownership and one-use, original native source ordering, typed
separation vs forged World/outcome, owner/Intent cross-swap, and
non-executing L0/S14 candidate agreement. The test-only primed
supervisor is **not** proof that the physical original executor
actually issued those actions. Future physical SCIENCE requires an
independently verifiable grant issuer, a preregistered meaningful
outcome metric, a safe-WAIT rule backed by World consequences,
controlled ON/OFF/sham assignment and independent analysis. Historical
Stage R evidence is left frozen and cannot be retrospectively promoted.

## Stage V (SelfWorld, not V Science lane) — signed grant proof and WAIT safety screens

Stage V is **OFFLINE DEV only**: `self_world_stage_v_attestation.py`
creates a canonical, schema-checked, domain-separated JSON grant request
bound to a run ID, original S49 session / Action, Stage S typed S17 feedback
ID/direction, original S16 after-native seq and correlated later probe,
the original `risk_weight=4 rev1` and bounded `value3/5 rev2`
candidate, and SHA256 of selected original S16/source fields.
Only resolved INCREASE/DECREASE native-geometry evidence qualifies to
form the request. A *separate Python signer process* signs the immutable
request bytes with OpenSSL's RSA-SHA256 signature using a private key not
provided to the verifier. The verifier receives a **separately pinned**
PEM public key and expected SHA256 fingerprint, checks the exact run,
full request and actual signature, and consumes each grant key once per
verifier session. No public key is accepted from the untrusted envelope.

**Trust boundary:** cryptographic verification proves the bytes came
from a holder of that signing key, *not* that the keyholder is an
independently authorized issuer, that the presented Python World objects
actually originated from live S49, or that the signer examined the raw
physical evidence. In focused tests, an ephemeral RSA key is deliberately
generated by the test harness; its independently launched signer process
demonstrates process separation and tamper rejection **only**.
This key/PEM is NOT a production issuer or attested trust root.
No private key is added to this repository. The envelope is **never
automatically converted into LearningUpdateAuthority**, nor is
`commit_learning_update` or physical `qualify` invoked from Stage V.
The future real-world gate must provision an independently trusted
issuer identity/pinned public key out-of-band and independently verify
that issuer's receipt refers to ORIGINAL immutable native evidence,
plus a persistent consumed-key store across restarts. In-process replay
protection alone cannot prove cross-run once-only delivery.

`self_world_stage_v_wait_safety.py` preregisters a candidate,
nonbinding `stage-v-near-zombie-wait-screen-v0`:
world-age exposure of >=20 ticks as sampled by the existing native
clock packets, same zombie within 2.5m, camera/bot drift <=0.01m,
nontruncated entity registry with positional-distance consistency,
no decrease in health, no avatar hurt event, and no death event.
Any health loss, hurt event or death is `HARM_OBSERVED`; insufficient
ticks, positional drift, missing/changed target, or confounded health
increase is `UNDETERMINED`. A bounded apparent no-harm result is
**NO_HARM_WINDOW_CANDIDATE only**. Original clock packets report
server update-time samples, **not command effect-tick attestation**.
Raw stream continuity/coverage and absence of unreported damage or
healing CANNOT be independently established from these typed objects.
Hence `physical_wait_permitted`,
`safe_to_wait_near_zombie`, `survival_gain_proven` and
`science_qualified` are always **False**, even for the candidate.
The arbitrary 20-tick/2.5m/1cm criteria must be calibrated before
prospective SCIENCE. S14's `WAIT admitted` never supplies safety evidence.

Stage V tests exercise an **actual separate signer subprocess**
using ephemeral test-only keys and pinned verification with
signature modification, cross-run/session/action/feedback replay and
copied-source negatives, plus synthetic health/hurt/death/tick
screens. Stage U's in-process original executor gate and Stage T
original L0/native S14 preview remain unmodified; S49 live entrypoint
remains the sole physical Action issuer and is **not** routed through
these new signer or WAIT safety routines. No new Minecraft, Model,
Action or real S10 commit is undertaken by Stage V. The preregistration
here is for future experiments; retrospective Stage R movement is
never promoted into a preregistered Stage V result.

## Stage W1 — separately pinned source audit + durable replay reservation (OFFLINE DEV)

Stage W1 does **not** wire the Stage V signature mechanism into live
`LearningUpdateAuthority`, `NormalSessionActionExecutor`, or Minecraft.
It adds two standalone opt-in modules:

- `self_world_stage_w_archive.py`: read a canonical
  `stage-w1-source-extract-v0` JSON **extraction** held separately from
  the signed request. The verifier's expected SHA256 of the *whole*
  extracted document is supplied out of band; it is NEVER read from
  the untrusted grant envelope. Reconstruct the **original Stage V
  signed evidence digest** from the source subrecord and independently
  check original S49 session/action/binding, source event and native
  seq order; strict Action OUTCOME / S16 observed execution; nontruncated
  entity-registry claim; real 3D bot/target positions vs declared
  distance and horizontal motion; Stage S fixed +/-10cm criterion;
  exact S17 feedback ID and original action-outcome reference. The
  source digest must equal the exact already-signed grant request.
  A changed archive, fake source, alternate run or missing native
  geometry must fail even if its attacker recomputes the archive hash.
  **The extraction is NOT the untouched Minecraft raw native stream.**
  Claiming to be a native observation via JSON, or providing a
  requester's own source hash or a self-minted archive pin, does NOT
  qualify physical ground truth. A separately authorized archivist and
  immutable raw stream receipts are still W2 work.
- `self_world_stage_w_gate.py`: `StageWPersistentGrantLedger`
  provisions a **new-only**, absolute-path SQLite ledger with
  `journal_mode=DELETE` and `synchronous=FULL`. The W1 offline
  consumer verifies the separately pinned RSA public key/issuer
  fingerprint, the above source evidence, the Stage V canonical
  signature/exact request and run ID, then issues a SQLite
  `BEGIN IMMEDIATE` / unique insert / `COMMIT` **BEFORE**
  returning a read-only reservation receipt. Constraints include
  unique `(run,session,action)`, `(run,feedback)` and
  `(run,evidence hash)`. After restart a new verifier cannot consume
  the same signed Action; concurrent consumers receive only one
  success. Missing, corrupt, locked or tampered ledgers fail closed.
  Ledger deletion, rollback from backup, cloning across hosts,
  privilege separation, file/directory permission controls and
  crash/power-loss durability on the actual WSL2 filesystem require
  W2 physical execution and are NOT asserted by CI.

There are **two independent operator pins**: trusted issuer public PEM
fingerprint and an independently obtained SHA256 of an immutable source
extraction. Merely passing both pins as caller-owned strings does not
create a trust anchor. No trusted signer identity or independent
source archive custodian has yet been provisioned. The receipt
explicitly sets external issuer qualification, real S10 commit
permission, physical WAIT permission and scientific qualification
to **false**. The one-use ledger is *a durable reservation*, not an
Action issuer or a license for S10 commits.

FAST regression includes separate-issuer-subprocess synthetic RSA
signature and pinned offline extraction replay, new-process/-object
restart, concurrent ledger reservation, missing and malformed ledger,
changed/foreign grant, changed archive/hash, spoofed bot/zombie
coordinates and distances, altered S16 state and S17 feedback, stale
native seq, HOLD and noncanonical evidence. The synthetic test
harness explicitly mints its own disposable issuer key and archive
pin. This is an engineering test of the verification contract,
**not independent authority or actual World verification**.

### W2 LocalCodex handoff (not executed by W1)

On isolated WSL2: provision a public-key trust root **separately** from
the signer/key custody; seal original Minecraft/Node source records
and create externally pinned immutable SHA receipts; compare the
W1 extracted source against the native raw stream in an independent
auditor; restrict signer process and private key; instantiate a
dedicated persistent SQLite database with tested ownership/permissions,
restart/crash/concurrent consumers and malicious replay; check backup
restore and integrity failure policy. Record independent evidence,
cleanup and exact commits. Do NOT wire the receipt to S10 or authorize
near-threat WAIT until those gates and explicit physical safety
measurements qualify. No SCIENCE success should be inferred from DEV.

## Stage W2 — LocalCodex isolation execution boundary (prepared, NOT executed here)

The W2 operator playbook is [`docs/selfworld-w2-localcodex.md`](selfworld-w2-localcodex.md).
Two isolated **offline** command-line utilities were added:

- `self_world_stage_w2_ledger_worker.py`: one W1 receipt reservation per
  actual consumer OS process, public-key-only; explicit arguments for
  separately pinned signed request, public PEM, archived extract and
  pre-provisioned SQLite ledger, plus exclusive-create evidence receipt.
  No private key, physical action or real S10 update input exists.
- `self_world_stage_w2_local_preflight.py`: read-only Linux/WSL2
  filesystem/identity observation. Checks pinned public + raw-file hashes,
  SQLite owner/mode/read-only integrity, process UID separation assertion,
  and whether the consumer can open the issuer's private key. It **never
  reads private PEM contents** and cannot attest ACL/privilege isolation,
  trusted authority, raw source provenance, stream completeness or
  crash/rollback durability. Any unmet check is BLOCKED; if all metadata
  checks pass the result is `W2_LOCAL_FILESYSTEM_PRECHECK_ONLY`.
  Its durable receipt is exclusive-create to avoid overwriting evidence.

Dedicated synthetic CI tests spawn real separate consumer Python processes
to demonstrate exactly one SQLite reservation, resumed-process replay
denial, altered public/source pin denial, and preflight BLOCKED when
a supposedly separated private PEM can still be opened by the consumer.
These tests have NO real WSL2 host privileges or Minecraft raw stream.

The existing original S49 report's parsed `execution_evidence` is
insufficient to prove continuous *raw* original Mineflayer receipt
provenance. The raw-input hash in W2 preflight is only a file integrity
predicate, NOT proof its contents are authentic original native frames.
Therefore **full W2 LocalCodex QUALIFICATION is pending local execution,
and raw-stream attestation is blocked until a genuinely independent
unchanged native stream is available**. W1 offline and previous DEV
evidence MUST NOT be retrospectively relabelled as physical SCIENCE.

## Stage W3 — pre-decode Node stdout original-bytes capture (DEV opt-in)

See [`docs/selfworld-w3-native-capture.md`](selfworld-w3-native-capture.md).
The opt-in original S49 model-free DEV flow creates an exclusive binary
JSONL transcript at the **Node bridge stdout → Python readline** boundary,
before decoder and S49 host frame filtering, plus an exclusive 0600 sealed
receipt with full raw SHA256, session/seq order, ACK/EOF and exit status.
Missing/untrusted/invalid frames remain `INCOMPLETE_UNQUALIFIED`, not
forensically repaired. The existing default S49 route never enables it.

This captures original Node stdout received by Python, NOT original
Minecraft TCP network packets; Node bridge emission completeness and
externally trusted archivist are not proven. W3 cannot retroactively
qualify the original Stage R artifact, cannot create real S10 authority,
cannot permit near-zombie WAIT, and cannot turn DEV into SCIENCE.
No physical DEV is started by importing/testing this addition; a fresh
World needs the separate explicit `--self-world-w3-raw-capture` DEV grant.

## W4 PREHOST original-component DEV integration (2026-10-20)

Scope: offline JSONL/fake transport only; `W4_EXTERNAL_TRUST_NO_GO / PREWORLD_BLOCKED`
remains mandatory. The original S49 runner, Action issuer/executor, S16, Stage S,
S10 authority and all physical launch defaults are unchanged.

### Source ownership audit

- `_new_session()` in `s34_native_world_cognition_ci.py` awaits
  `MineflayerProcessSession.launch()` (which consumes `adapter_started`), then
  `_await_spawn()` before returning. Spawn is an observed frame, not a sleep.
- S49 constructs `NormalWorldL0` and `NormalSessionActionExecutor` once. Its
  staging task changes only World entities. It is scheduled immediately before
  `host.run_session(NativeObservationOnly(session), ...)`. This is concurrent
  scheduling, not proof of placement completion.
- The foreground host calls its observation source, then awaits `reprobe()`
  only after an entity stimulus. That callback and the executor share the
  original session; the original sequential callback contract supplies their
  ordering. `_correlated_observe()` consumes interleaved frames without
  returning them. It cannot be substituted for a loss-accounted preworld read.
- S31A `_ready_server()` owns the only Java stdout `collect()` task. W4 logtap
  tails that task's flushed file; it never reads Java stdout. The local marker
  establishes content/order only, not an independent World tick or authenticity.
- S49 cancels/awaits staging, then shuts down/terminates the session, then
  shuts down the server/collector. Session shutdown itself can receive until
  EOF. A future live integration must finish/revoke the host reader before
  shutdown; this offline seam makes no live cleanup qualification claim.
- Original `_new_session()` does not opt into W4 orientation. Original runner
  startup remains unchanged. No W4 live launcher or real command entry is added.

### Implemented seam and evidence boundaries

`W4OfflineS49Owner` constructs the existing `MineflayerProcessSession` directly
around internally created fixture pipes, sharing its decoder and observe writer.
It accepts only a tuple of JSONL bytes, not a live session, process, collector,
executor or issuer. Startup uses the original spawn waiter. A context-local
receive scope, one in-flight read, one calling task/owner and terminal phases
separate startup, prehost, evidence transfer, staging and original host access.
An unauthorized/competing read poisons the lease. Cancellation, timeout, EOF and
protocol rejection prevent reuse. Public phase metadata cannot grant a reader
scope. The original process session remains a private implementation detail;
this is a cooperative in-process ownership contract, not protection against
arbitrary Python code accessing private attributes.

Prehost delegates to the existing bridge/port/handoff gate. Its ledger includes
all accepted preworld frames (including the correlated source), while
`buffered_frames` contains the unsolicited evidence only. Contiguous seq,
session and request checks fail closed. Raw consumed fixture bytes (including
malformed input/EOF) and decoded `(phase, frame)` records are separate from
frames actually returned by the original native filter to the host. Preworld
frames are never re-enqueued into the postworld stream. Ledger transfer is once
only and requires the capturing owner task. This ledger grants no live source
qualification or physical permission.

Tests execute the original `NativeObservationOnly`, `_correlated_observe()` and
`NormalWorldL0.run_session()` WAIT path. MOVE cannot execute: the seam installs
no grant/executor and its Action callback rejects. The placement-window test
also executes the unmodified `_ready_server()` collector closure and `_command()`
with a patched subprocess factory that always returns fake pipes. A real
collector cursor/marker and W4 window reconcile the pre/post decoded probes,
command bytes hashes and zombie identity/XYZ. A NEW synthetic S16 fixture is
aligned to this test's sequence namespace and read through the unchanged
S16/Stage S join; it remains HOLD and is not a physical S16 creation. No frozen
receipt is edited or substituted.

The handoff also requires the bridge's original handoff gate to accept a typed
collector marker. Unit tests supply explicit synthetic markers; the complete
collector test obtains it through the original collector. These checks do not
independently attest a real server or authorize a live integration. Existing
owner/window/logtap negative controls remain required alongside these tests.

### Qualification ceiling and next boundary

This engineering result establishes reuse of original implementation components
under offline transports. It does not establish the live `_new_session()`
orientation path, external custody, independent marker truth, World tick,
physical yaw, physical Action/S16, or S10 permission. The next minimal step is
review of an owner-local DEV launch proposal and its explicit reader lease,
marker barrier, shutdown/cancellation protocol and independent native source
qualification; physical execution needs separate authority. W3's two
`+0.09595129995869334m` results stay HOLD; Stage S `delta_m=0.100m` and
`min_motion_m=0.050m` remain fixed. R/V qualification is unchanged.

The explicit target-substitution negative exposed an existing readback gap:
Stage S returns HOLD when the original target is absent from consequence-native
before/after, and the old W4 join did not treat that HOLD as an identity veto.
`join_w4_prehost_s16_offline` therefore requires one identical zombie ID across
the original probe and both native consequence observations before delegating
to the unchanged window/S16/Stage S readback. The original HOLD definition and
protected files are unchanged; missing identity now blocks this DEV join.


## W4 saved-DEV observation -> SelfWorld two-epoch offline replay (2026-10-23)

`adapters/mineflayer/self_world_observation_only_epoch_replay.py` supplies
`replay_w4_saved_self_world_epochs()` as a **strictly read-only offline
developer projection**, not a runtime connector. It requires an operator-pinned
SHA256 for the *original report.json* (e.g. the separate 2026-10-23 W4 DEV
report already archived by LocalCodex), the original exact HEAD and run ID,
the unaltered local sealed W3 Node JSONL/receipt and sole Java collector RAW
file in the SAME absolute evidence directory. Never reconstruct missing
source from a summary or synthesize "real" frames.

The routine recomputes the report hash, audits the saved Node byte stream
with the existing W3 decoder/receipt, binds exactly one original started/spawn/
correlated before/after probe to the original dataclass report snapshots,
checks Java marker byte-offset/hash/content, replays existing local
readback/lifetime validation, and checks the producer-local disposition
and zero-Action/OUTCOME/S10 limits. The reporter remains the original local
producer: these checks do not make Java console gametime or Node stdout
independently attested Minecraft ticks. No timestamp or cross-clock relation
is invented.

It then invokes the **existing** `project_mineflayer_present`,
`project_self_world_present`, `compose_self_world_view`, ATT
`select_self_world_attention` and PRD `predict_transition`/
`review_self_world_prediction` on two different read-only epochs of the
same session. A simple **explicit hypothetical label-persistence baseline**
is only generated if an earlier entity and its label were positively
observed; it is NOT a learned transition law. If the source has no
positively seen entity, no forecast is created. A later target omission
is UNKNOWN/UNDETERMINED, not proof of physical disappearance.
Missing, forged, cross-session, changed, reused or out-of-bounds source
material is rejected. The earlier view is carried only as a typed
comparison source, not committed Memory, BLF, S10 or a second owner.

**Scope limit:** the returned next-epoch SelfWorld and ATT result are
prepared for inspection, not injected into existing L0/S14 or used to
make physical decisions. Connecting these to RelayEngine's existing
bounded/L1/L2 choice routes would require separately validated owner
snapshots; this DEV replay intentionally grants none.

How to check on LocalCodex (without new World):
```python
from pathlib import Path
from adapters.mineflayer.self_world_observation_only_epoch_replay import (
    replay_w4_saved_self_world_epochs,
)
replay = replay_w4_saved_self_world_epochs(
    evidence_root=Path("/ABSOLUTE/ORIGINAL/EVIDENCE/w4-observe-1e86a714f3ea3374"),
    expected_report_sha256="a2f16d3bec33fcb6ea86d225858da8bf4df6dbedf5908eba950a0998f18c755f",
    expected_source_head="1b221d845e42ea0e8be003239525c50de20e7fef",
    expected_run_id="1e86a714f3ea3374",
    self_id="w4-offline-observer",
)
print(replay.classification, replay.prior.observation.source_ref,
      replay.following.observation.source_ref,
      replay.prediction_review)
```
This documented path is an **operator placeholder**, not evidence that this
ChatGPT environment accessed the original WSL2 files.

Synthetic tests cover local byte joins, match/mismatch/undetermined,
zero-entity/source-gap and rejection of tampering, cross-session errors,
invalid cleanup and authority promotion. They are *not* real source run
verification. On this GitHub code-only branch there was NO original evidence
access and NO Python 3.12 run; all results remain unverified until LocalCodex
checks the saved original run and reruns focused regressions at exact HEAD.
CI/FULL/new Minecraft/Action/S10/SCIENCE remain 0/NOT_RUN.


### Local source verification and replay repair (2026-10-23)

The local Python 3.12 replay accessed the original run `1e86a714f3ea3374`
at source HEAD `1b221d845e42ea0e8be003239525c50de20e7fef`, with report
SHA256 `a2f16d3bec33fcb6ea86d225858da8bf4df6dbedf5908eba950a0998f18c755f`.
JSON-normalized dataclass comparison preserves exact source fields while
accounting for tuple-to-array serialization. Synthetic entities use the
existing wire keys `id` and `type`. Receipt symlinks, conflicting PID absence
records and an inventory bound to another source HEAD are rejected.

Original before/after native seq 3/5 produced distinct immutable epochs of
the same Self/session. Both have zero observed entities: ATT selects none,
no hypothetical forecast is constructed and `prediction_review` is `None`.
Both probes report time_of_day 19; the local Java marker reports gametime 24.
These are separate source fields, not proof of elapsed physical ticks.
Fifteen tampering cases on disposable copies were rejected; original bytes
and the existing archive SHA256 index were unchanged. MATCH/MISMATCH/
UNDETERMINED remain separately tested synthetic behaviors.

This verifies offline representation of an earlier DEV run, not a new-HEAD
World run or independent physical custody. DEV_ONLY / QUALIFICATION_NO_GO /
SCIENCE_NOT_RUN / NO_NEW_WORLD_RUN remain in force.


### W4 two-epoch observations -> existing RelayEngine cognition inputs (2026-10-23)

`adapters/mineflayer/self_world_observation_only_cognition.py` provides
`prepare_w4_offline_cognition_inputs(replay, max_native_seq_gap=8)`.
It consumes a previously source-pinned `W4OfflineEpochReplay`; verifies
the exact same Self/session/sequence/provenance and re-derives ATT/PRD
reviews. Earlier/later immutable SelfWorld views are projected through
the existing `bind_self_world_to_cognition_request` into *prepared*
`BoundedChoiceRequest` and `OpenCognitionRequest` values. No model/provider
is called by this module. The two bounded choices are explicitly about
source inspection versus deferring an unsupported claim, NOT physical WAIT,
MOVE or Action authority. No generated intent, retained memory or S10 grant.

The saved real run `1e86a714f3ea3374` has two positively captured
probes but zero positively observed entities in both. Consequently, both
`self_world_observed` fields should be empty and NO PRD review appears;
`self_world_observer.status == "observed"` means a *probe* exists, NOT that
any entity has been positively observed or that the World is empty.
Synthetic positive-entity cases instead produce observed-target context
and, if the prior explicit hypothesis exists, a next-epoch review with
MATCH/MISMATCH/UNDETERMINED and `action_success: null`. The baseline
hypothesis is not learned, and missing targets remain epistemically unknown.

Synthetic tests demonstrate a **deterministic stub provider** receiving
these immutable requests via existing RelayEngine BOUNDED -> THINK and OPEN.
This is not real-model policy improvement, HABIT/L1 owner execution,
Action routing, world qualification or science. Model calls in those tests
are synthetic only; the prepared object itself makes zero calls.

The above comparison is source-shape/epistemic availability measurement,
not a causal performance estimate. Real-source input binding still
requires LocalCodex to load the original saved W4 evidence as in the
preceding section, run Python3.12 focused tests at the exact new HEAD,
and confirm no new World, model, physical Action, OUTCOME or S10 writes.
Code pushed to an isolated branch does NOT mean PR #634 has been updated.
