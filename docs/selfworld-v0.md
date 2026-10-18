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
