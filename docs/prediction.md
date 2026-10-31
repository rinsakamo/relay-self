# S8 Bounded Deterministic Transition Prediction

## Purpose

S8 introduces Prediction (PRD) as a bounded deterministic one-step transformation over
an explicitly supplied structured current state and one explicitly supplied
declarative transition rule.

The qualified question is:

\`\`\`
Given this current structured state and this explicit transition rule,
what one-step state follows?
\`\`\`

S8 does not answer:

\`\`\`
BLF: what is currently supported?
CNC: how is this represented/classified?
CTL / PLAN: what should be chosen?
Intent: what is wanted?
\`\`\`

The S8 mechanism is deliberately stateless:

\`\`\`
PredictionState
+ TransitionRule
        -> predict_transition
        -> PredictionResult
\`\`\`

No WorldModel, Simulator owner, PredictionStore, rollout cache, scheduler, or learned
transition model is introduced.

## One-step scope

S8 intentionally implements one-step prediction only.

A bounded multi-step rollout could be built later by an explicitly governed caller,
but S8 does not add a loop, cache, search procedure, or repeated simulation owner.

This keeps the PRD/PLAN boundary sharp: S8 applies one supplied transition and never
searches among trajectories.

## Structured current state

\`PredictionState\` contains:

- structured \`state_id\`;
- immutable tuple of \`StateVariable\`;
- explicit provenance;
- explicit \`step_index\`;
- optional source references and source provenance lineage.

State variable keys must be unique.

\`StateVariable\` values are deliberately bounded to:

- \`bool\`;
- \`int\`;
- one non-empty structured string token.

Arbitrary mutable objects and natural-language payloads are not state variables.

## Transition rule

\`TransitionRule\` is declarative and contains:

- structured \`rule_id\`;
- exact-value \`preconditions\`;
- deterministic \`assignments\`;
- explicit provenance.

Precondition keys must be unique. Assignment keys must be unique.

The rule is data. S8 does not execute arbitrary caller code or parse natural-language
transition descriptions.

## Exact deterministic semantics

For each precondition:

- if the variable exists and exactly equals the required value, it matches;
- if the variable exists with a different value, it is an explicit mismatch;
- if the variable is absent, it is missing.

The result is:

\`\`\`
any explicit mismatch
    -> NO_TRANSITION

no mismatch + at least one missing required variable
    -> UNDETERMINED

all required values present and equal
    -> PREDICTED
\`\`\`

An explicit mismatch dominates missing because the rule is already known not to
apply.

When a transition applies:

- assignments replace variables with the same key;
- assignment keys not already present are appended in explicit rule order;
- every variable not mentioned by an assignment remains unchanged;
- the derived state receives \`step_index + 1\`;
- the result retains the exact source state and exact rule objects;
- derived provenance explicitly identifies \`predict_transition\`, source state, rule,
  and step.

Missing is never silently treated as false.

## Prediction is not truth

A \`PREDICTED\` result means only:

\`\`\`
under this explicit rule, this structured next state follows
\`\`\`

It does not mean:

- the future will actually occur;
- the current World already has the predicted values;
- an action should be chosen;
- the Self should make or prevent the prediction.

S8 preserves:

\`\`\`
current evidence != belief
belief != concept
concept != prediction
prediction != World truth
prediction != plan
prediction != intent
prediction != action authority
\`\`\`

## No forced cognitive criterion

S8 deliberately adds no new \`CriterionDescriptor\`.

The implemented mechanism is most faithfully represented as a typed deterministic
K + T transition:

\`\`\`
current X
+ explicit K
-> next X at step T+1
\`\`\`

Exact precondition matching is part of the declared transition semantics and ordinary
contract/rule evaluation. S8 does not invent a \`COGNITIVE_ORIENTATION\` Q merely to
match ATT, BLF, or CNC.

The PRD \`CapabilitySpec\` therefore has:

\`\`\`
criterion_ids = ()
\`\`\`

## Capability and operator

S8 adds:

\`\`\`
PRD
dependencies = ()
state_scopes = ()
\`\`\`

Operator:

\`\`\`
prd.predict
-> relay_self.prediction.predict_transition
effect = READ_ONLY
hidden_persistent_state = false
\`\`\`

Port:

\`\`\`
prediction.result.out
\`\`\`

PRD does not globally depend on ATT, BLF, or CNC.

## CNC -> PRD bridge

\`prediction_state_from_concept\` is an explicit pure bridge.

It accepts only a \`MATCHED ConceptRepresentation\`, preserves concept identity and
source provenance, and projects structured fields:

\`\`\`
source_kind=concept_representation
concept=<structured concept identity>
concept_status=matched
\`\`\`

The caller may explicitly supply additional structured state variables.

The bridge does not rerun CNC, assign World truth, or choose an action.

No \`ConceptRepresentation\` or a non-MATCHED concept fails closed through
\`PredictionSourceUnavailable\`.

## BLF -> PRD bridge

\`prediction_state_from_belief\` is also explicit and pure. It projects only the
already-established:

- belief status;
- proposition identity;
- evidence references and provenance.

It does not reassess evidence or turn a belief into truth.

A missing \`BeliefAssessment\` fails closed.

## CNC + PRD qualification

The bounded CNC + PRD case uses a pre-qualified:

\`\`\`
MATCHED(spatial:nearby_threat)
\`\`\`

Explicit projection adds:

\`\`\`
distance_band=near
moving_toward_self=true
\`\`\`

The PRD rule requires:

\`\`\`
concept=spatial:nearby_threat
distance_band=near
moving_toward_self=true
\`\`\`

and assigns:

\`\`\`
distance_band=immediate
\`\`\`

The concept remains MATCHED and unchanged. PRD does not reclassify it.

Both mechanisms make zero provider/model calls.

## ATT -> BLF -> CNC -> PRD qualification

The complete deterministic chain uses:

\`\`\`
E1: SUPPORT entity:zombie-1:nearby, focus=zombie-1
E2: SUPPORT entity:zombie-1:nearby, focus=zombie-1
E3: unrelated SUPPORT evidence, focus=other
\`\`\`

ATT selects E1/E2 only.

BLF receives E1/E2 and returns:

\`\`\`
entity:zombie-1:nearby = SUPPORTED
\`\`\`

CNC explicitly represents the structured BLF output as:

\`\`\`
MATCHED(spatial:nearby_threat)
\`\`\`

The CNC result is explicitly projected into prediction state and PRD applies:

\`\`\`
nearby threat + threat_state=near + moving_toward_self=true
-> threat_state=immediate
\`\`\`

E3 never reaches BLF. BLF does not rerun ATT. CNC does not reassess evidence. PRD
does not reclassify the concept.

ATT / BLF / CNC / PRD provider-model call counts are all zero.

## ON / OFF semantics

PRD ON plus explicit due work and an exact binding invokes the real
\`predict_transition\` function.

PRD OFF suppresses only PRD work.

The qualification includes CNC ON + PRD OFF:

- CNC still executes;
- PRD is suppressed;
- no prediction is fabricated merely because a concept or source state exists.

Capability OFF changes route admission only.

## Provider-output boundary

A provider expression such as:

\`\`\`
"The zombie will reach you next."
\`\`\`

is neither a \`PredictionState\` nor a \`TransitionRule\`.

S8 does not parse it into either one and cannot automatically produce a
\`PredictionResult\` from generated language.

A future explicit interpretation mechanism would be required.

## Authority boundaries

PRD does not mutate:

- \`PersistentCognition\`;
- Current Intent;
- \`SkillExecution\`;
- \`ActionLifecycle\`;
- \`AttentionSelection\`;
- \`BeliefAssessment\`;
- \`ConceptRepresentation\`;
- the source \`PredictionState\`.

An already-PROPOSED Action remains PROPOSED.

PRD does not authorize, issue, complete, or fail an Action. It does not retain Memory,
revise belief, change concept classification, or update current World truth.

## Why PRD is not PLAN

PRD applies exactly one caller-supplied transition rule.

It contains no:

- objective;
- utility;
- action candidates;
- sequence search;
- best-path selection;
- counterfactual optimization;
- policy selection.

Prediction is therefore descriptive under an explicit model, not prescriptive.

## Why PRD is not a central executive

PRD has no scheduler, event loop, clock owner, trigger detector, dynamic descriptor
dispatch, provider, persistent model state, or background task.

The caller/source owns why prediction work is due. EpochPlan executes only exact
explicit bindings under the already-qualified Action-supervision and ordering rules.

## Deferred functionality

S8 intentionally defers:

- PLAN;
- multi-step rollout;
- action-sequence search;
- utility optimization;
- stochastic transitions;
- transition learning;
- neural or learned World models;
- LLM forecasting;
- prediction persistence;
- rollout caches;
- counterfactual planning;
- LRN;
- HABIT.

If retained or repeated prediction becomes useful, that is a separate ownership and
reuse question rather than a prerequisite for PRD.
