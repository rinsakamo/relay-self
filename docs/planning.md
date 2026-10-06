# S9 Bounded Deterministic Candidate-Plan Selection

## Purpose

S9 introduces Planning (PLAN) as bounded deterministic preference selection over a
finite caller-supplied candidate set.

The qualified question is:

\`\`\`
Given these explicit candidates and their explicit outcome features,
which candidate best satisfies this explicit planning criterion?
\`\`\`

PLAN does not generate candidates, search a tree, predict outcomes, commit Intent, or
authorize Action.

The qualified mechanism is stateless:

\`\`\`
PlanCandidate tuple
+ PlanningCriterion
        -> select_plan
        -> PlanSelection
\`\`\`

No PlanStore, PlanningSession, search tree, candidate graph, planning cache, scheduler,
or executive controller is introduced.

## PlanCandidate

A \`PlanCandidate\` contains:

- structured \`candidate_id\`;
- immutable \`outcome_features\`;
- explicit provenance;
- optional stable \`prediction_ref\`;
- optional source references/provenance;
- optional \`action_ref\` metadata.

\`action_ref\` is metadata only. It does not propose, authorize, issue, or execute an
Action.

\`PlanFeature\` values are bounded to:

- \`bool\`;
- \`int\`;
- one structured string token.

Feature keys must be unique. Arbitrary mutable values and free-text plan payloads are
not accepted.

## PlanningCriterion

S9 intentionally uses one narrow criterion style:

\`\`\`
PlanningCriterion(
    feature_key=<one explicit outcome feature>,
    direction=MINIMIZE | MAXIMIZE,
)
\`\`\`

The comparison feature must contain an integer value in every candidate.

S9 does not implement:

- weighted sums;
- multiple objectives;
- arbitrary expressions;
- caller-supplied executable scorers;
- learned value functions.

The comparison value must already be explicit structured input. PLAN never infers,
for example, that \`immediate\` is riskier than \`near\` unless an explicit integer
comparison feature already represents that preference.

## Exact selection semantics

All candidates are validated first.

For the criterion feature:

\`\`\`
one or more candidates missing the feature
    -> UNDETERMINED

all candidates rankable
and exactly one candidate has the best integer score
    -> SELECTED

all candidates rankable
and multiple candidates share the best score
    -> TIED
\`\`\`

For \`MINIMIZE\`, lower is better.

For \`MAXIMIZE\`, higher is better.

Caller order never resolves ties.

Missing comparison input is never interpreted as zero, false, best, or worst.

If any candidate is unrankable, S9 conservatively returns \`UNDETERMINED\` rather than
selecting from only the rankable subset.

## PlanSelection

The immutable result contains:

- exact \`PlanningCriterion\`;
- exact candidate objects;
- \`SELECTED\`, \`TIED\`, or \`UNDETERMINED\`;
- selected candidate only when uniquely determined;
- tied best candidates when tied;
- explicit unrankable candidate IDs when underdetermined.

A selected plan means only:

\`\`\`
among this supplied finite candidate set,
this candidate best satisfies this supplied criterion
\`\`\`

It does not mean:

- commit this as Current Intent;
- execute this plan;
- start a Skill;
- propose an Action;
- authorize or issue an Action;
- treat the predicted future as true.

## Cognitive criterion vs validation

S9 declares:

\`\`\`
plan.explicit_preference_orientation
kind = COGNITIVE_ORIENTATION
\`\`\`

This is a genuine cognitive orientation because it determines preference among
otherwise valid alternatives.

These remain contract validation:

- malformed candidate identity;
- empty candidate set;
- duplicate candidate identity;
- duplicate feature key;
- malformed criterion;
- unsupported feature value;
- non-integer comparison input.

## Capability and operator

S9 adds:

\`\`\`
PLAN
dependencies = ()
state_scopes = ()
\`\`\`

Operator:

\`\`\`
plan.select
-> relay_self.planning.select_plan
effect = READ_ONLY
hidden_persistent_state = false
\`\`\`

Port:

\`\`\`
plan.selection.out
\`\`\`

PLAN does not globally depend on PRD because callers may provide already-structured
candidate outcomes directly.

## PRD -> PLAN bridge

\`plan_candidate_from_prediction\` is a narrow explicit pure bridge.

It accepts only a \`PREDICTED PredictionResult\`.

The caller explicitly supplies which predicted-state variable keys should become
\`PlanFeature\` values. The bridge copies only those requested structured fields.

It does not:

- rerun PRD;
- infer a score;
- infer utility;
- infer truth;
- generate a candidate identity;
- commit Intent;
- propose an Action.

The bridge preserves stable prediction references and predicted-state provenance.

A missing PredictionResult, a non-PREDICTED result, or a requested variable absent
from the predicted state fails closed through \`PlanSourceUnavailable\`.

## PRD + PLAN qualification

The S9 qualification uses two independently explicit PRD outcomes:

\`\`\`
WAIT prediction:
comparison_score=8

MOVE_AWAY prediction:
comparison_score=3
\`\`\`

PLAN criterion:

\`\`\`
feature_key=comparison_score
direction=MINIMIZE
\`\`\`

Result:

\`\`\`
SELECTED MOVE_AWAY
\`\`\`

The score is explicit. PLAN does not infer it from threat-state labels.

PRD runs before PLAN through separate explicit EpochPlan bindings. PLAN receives the
completed structured results and does not rerun PRD.

## Full deterministic chain

The S9 full chain is:

\`\`\`
evidence candidates
    -> ATT
selected evidence
    -> BLF
BeliefAssessment
    -> CNC
ConceptRepresentation
    -> explicit structured prediction state
    -> PRD WAIT
    -> PRD MOVE_AWAY
PredictionResults
    -> explicit candidate projection
    -> PLAN
PlanSelection
\`\`\`

Scenario:

\`\`\`
E1/E2 SUPPORT entity:zombie-1:nearby, focus=zombie-1
E3 unrelated, focus=other

ATT -> E1/E2
BLF -> SUPPORTED
CNC -> MATCHED(spatial:nearby_threat)

PRD WAIT -> comparison_score=8
PRD MOVE_AWAY -> comparison_score=3

PLAN MINIMIZE comparison_score
-> SELECTED MOVE_AWAY
\`\`\`

E3 never reaches BLF.

BLF does not perform CNC.

CNC does not perform PRD.

Each PRD binding applies exactly one explicit transition.

PLAN does not rerun PRD.

Every stage performs zero provider/model calls.

## Prediction vs plan

S9 preserves:

\`\`\`
PredictionResult != PlanCandidate
PredictionResult != PlanSelection
prediction != plan
\`\`\`

A prediction is an outcome under an explicit transition model.

A plan selection is a preference comparison among explicit candidate outcomes.

Prediction availability alone does not fabricate a plan selection.

## Plan vs Intent

S9 preserves:

\`\`\`
PlanSelection != IntentCommitment
\`\`\`

PLAN never creates or changes Current Intent.

A future caller may explicitly use a plan selection when considering an Intent
transition, but that is outside S9.

## Plan vs Action and Skill

S9 preserves:

\`\`\`
PlanSelection != SkillExecution
PlanSelection != Action proposal
PlanSelection != authorization
PlanSelection != issue
\`\`\`

An \`action_ref\` carried by a candidate remains inert metadata.

S9 does not add an automatic PLAN -> CTL, Skill, or Action bridge.

## ON / OFF semantics

PLAN ON plus explicit due work and exact binding executes the real \`select_plan\`
mechanism.

PLAN OFF suppresses PLAN work only.

The isolation qualification uses PRD ON + PLAN OFF:

- PRD executes;
- \`PredictionResult\` exists;
- PLAN work is suppressed;
- no \`PlanSelection\` is fabricated.

Therefore:

\`\`\`
having a prediction != having a plan
\`\`\`

Capability OFF changes route admission only.

## Provider-output boundary

A generated expression such as:

\`\`\`
"You should run away."
\`\`\`

is neither a \`PlanCandidate\` nor a \`PlanSelection\`.

S9 does not perform natural-language plan extraction and does not invoke RelayEngine
when structured planning input is unresolved.

## Authority boundaries

PLAN does not mutate:

- \`PersistentCognition\`;
- Current Intent;
- \`SkillExecution\`;
- \`ActionLifecycle\`;
- \`AttentionSelection\`;
- \`BeliefAssessment\`;
- \`ConceptRepresentation\`;
- \`PredictionResult\`;
- source \`PlanCandidate\` values.

An already-PROPOSED Action remains PROPOSED.

The selected candidate receives no new execution authority merely because it won the
comparison.

## Why PLAN is not a central executive

PLAN has no:

- scheduler;
- event loop;
- persistent planning session;
- trigger detector;
- search tree;
- candidate generator;
- dynamic descriptor dispatch;
- provider/model call;
- execution authority.

The source/caller owns why planning work is due, which candidates exist, and which
criterion applies. EpochPlan runs one explicit pure selection binding.

## Deferred functionality

S9 intentionally defers:

- open-ended search;
- action-sequence generation;
- recursive planning;
- multi-step PRD rollout;
- counterfactual tree search;
- MCTS;
- A*;
- beam search;
- learned value functions;
- stochastic planning;
- LLM planning;
- natural-language plan extraction;
- automatic Intent commitment;
- automatic Skill start;
- automatic Action proposal;
- automatic Action authorization;
- automatic Action issue;
- persistent planning state;
- LRN;
- HABIT.
