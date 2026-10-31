# S10 Bounded Governed Retained Learning

## Purpose

S10 introduces Learning (LRN) as one deliberately narrow owner-local retained update.

The qualified question is:

\`\`\`
Given this retained target,
this explicit structured feedback,
this explicit bounded rule,
and explicit authority,
what new retained value is committed?
\`\`\`

Unlike ATT, BLF, CNC, PRD, and PLAN, S10 includes a real retained owner transition.
It therefore separates proposal from commit and makes authority, revision, and
provenance explicit.

S10 does not implement generic self-modification, model learning, reinforcement
learning, concept learning, belief revision, transition learning, or HABIT.

## Retained owner

The semantic owner is one immutable \`LearningPreferenceState\`:

\`\`\`
target_id
value
minimum
maximum
revision
origin_provenance
last_update
\`\`\`

This is not a generic dictionary or global parameter store.

The qualified example is a bounded integer preference such as:

\`\`\`
risk_weight = 3
bounds = [0, 10]
revision = 0
\`\`\`

The Scheduler, EpochPlan, CapabilityPlan, and RelayEngine do not own this value.

## Structured feedback

\`LearningFeedback\` contains:

- explicit \`feedback_id\`;
- exactly one \`target_id\`;
- \`INCREASE\`, \`DECREASE\`, or \`HOLD\`;
- provenance;
- optional structured \`consequence_ref\`.

A World/action consequence is not automatically feedback.

\`\`\`
World consequence != LearningFeedback
\`\`\`

The optional consequence reference only records caller-supplied lineage. S10 does not
interpret the consequence.

Provider-generated text is not feedback.

## Update rule

\`LearningUpdateRule\` contains:

- \`rule_id\`;
- positive integer version;
- positive integer step.

The retained owner supplies the admissible minimum and maximum.

For one proposal:

\`\`\`
INCREASE -> min(maximum, old + step)
DECREASE -> max(minimum, old - step)
HOLD     -> old
\`\`\`

There is no randomness, floating-point learning rate, gradient, reward propagation,
or time-dependent behavior.

## Proposal vs commit

S10 has two explicit stages:

\`\`\`
state + feedback + rule
-> propose_learning_update
-> LearningUpdateProposal
\`\`\`

and:

\`\`\`
state + proposal + explicit authority
-> commit_learning_update
-> LearningCommitResult + new LearningPreferenceState
\`\`\`

Creating a proposal never mutates retained state.

Feedback is not permission.

A proposal is not a committed update.

## Authority

\`LearningUpdateAuthority\` explicitly names:

- authority identity;
- exactly one target identity;
- authority provenance;
- whether the grant is active.

Commit fails closed when authority is absent, malformed, denied, or scoped to another
target.

The feedback event itself never grants update permission.

## Revision / replay semantics

Every accepted commit requires:

- exact target identity;
- exact expected revision;
- exact expected value;
- exact retained bounds.

A successful commit advances revision by exactly one.

This includes valid no-op commits caused by:

- \`HOLD\`;
- \`INCREASE\` at the maximum;
- \`DECREASE\` at the minimum.

The scalar may remain unchanged, but the feedback event was explicitly consumed.
Advancing the revision makes the proposal single-use: replaying the same proposal is
stale even after a no-op.

The owner also retains its most recent update record. Re-proposing the immediately
committed \`feedback_id\` fails as \`ReplayLearningFeedback\`.

S10 intentionally does not add an unbounded global feedback ledger.

## Proposal statuses

\`\`\`
UPDATED
UNCHANGED_HOLD
UNCHANGED_AT_BOUND
\`\`\`

Bounds are explicit admissibility, not hidden failure.

## Provenance

The most recent owner-local \`LearningCommitRecord\` preserves:

- target identity;
- previous and resulting value;
- feedback identity;
- feedback provenance;
- rule identity and version;
- authority identity;
- authority provenance;
- update provenance;
- previous and committed revision;
- proposal status.

This is owner-local update provenance, not MEM content.

S10 does not call \`PersistentCognition.retain_memory()\`.

## Cognitive criterion vs contract validation

S10 declares:

\`\`\`
lrn.explicit_feedback_orientation
kind = COGNITIVE_ORIENTATION
\`\`\`

The cognitive orientation is the structured feedback direction determining the
bounded update orientation for the retained target.

These remain contract/admissibility validation:

- target identity syntax;
- retained value bounds;
- positive rule step/version;
- target matching;
- authority presence/scope;
- exact proposal revision/value/bounds.

## Capability and operator seams

S10 adds:

\`\`\`
LRN
dependencies = ()
state_scopes = ("owner_local.learning_preference",)
\`\`\`

Two real seams are declared:

\`\`\`
lrn.propose_update
-> relay_self.learning.propose_learning_update
effect = READ_ONLY
\`\`\`

and:

\`\`\`
lrn.apply_update
-> relay_self.learning.commit_learning_update
effect = OWNER_TRANSITION
\`\`\`

Neither descriptor contains a callable or dynamic dispatch.

## PLAN + LRN boundary

A \`PlanSelection\` is not feedback:

\`\`\`
selected plan != successful plan != LearningFeedback
\`\`\`

The integrated S10 qualification first produces:

\`\`\`
PLAN -> SELECTED MOVE_AWAY
\`\`\`

No learning occurs from that fact alone.

A caller then separately supplies:

\`\`\`
LearningFeedback(
    target_id=risk_weight,
    direction=INCREASE,
    consequence_ref=action-outcome:move-away:threat-remained,
)
\`\`\`

Only this explicit structured feedback can produce a proposal and, with authority, a
retained owner transition.

PLAN remains stateless and unchanged.

LRN does not invoke PLAN and PLAN does not read hidden learned state.

## LRN ON / OFF

LRN ON plus explicit due work, exact bindings, explicit authority, and valid state
executes proposal then owner transition.

LRN OFF suppresses both learning work items.

The S10 isolation qualification uses PLAN ON + LRN OFF:

- PLAN still executes;
- learning work is suppressed;
- retained state remains unchanged;
- no proposal or commit is fabricated.

Disabling LRN never deletes retained learned state. Re-enabling only re-admits the
route; the owner snapshot remains caller-owned.

## Learning vs other capabilities

S10 preserves:

\`\`\`
learning update != Memory write
learning update != belief revision
learning update != concept learning
learning update != transition-model learning
learning update != PlanSelection
learning update != Current Intent
learning update != Skill execution
learning update != Action authority
\`\`\`

LRN does not retry, authorize, issue, complete, or fail Actions.

An existing PROPOSED Action remains PROPOSED.

An existing ISSUED Action remains ISSUED.

## Provider-text boundary

\`\`\`
ProviderExpression("That went badly.")
\`\`\`

is not a \`LearningFeedback\`.

S10 adds no natural-language feedback interpreter and performs zero provider/model
calls.

## Why LRN is not generic self-modification

S10 can update exactly one explicitly typed bounded scalar owner through one explicit
rule family.

It cannot:

- mutate arbitrary objects;
- rewrite code;
- rewrite descriptors/capabilities;
- write arbitrary module/global state;
- update multiple targets from one feedback;
- learn neural parameters;
- change transition models;
- change concepts;
- modify beliefs;
- update planning criteria implicitly.

## Why LRN is not a central executive

LRN has no scheduler, background loop, global optimizer, event monitor, hidden state
registry, dynamic dispatch, or provider/model call.

The caller owns:

- why feedback is due;
- which retained owner is targeted;
- which rule applies;
- which authority grants the transition.

EpochPlan only runs the explicitly bound work in caller-supplied due order.

## Deferred functionality

S10 intentionally defers:

- HABIT;
- arbitrary parameter mutation;
- generic self-modification;
- code rewriting;
- online neural learning;
- gradient descent;
- reinforcement-learning algorithms;
- temporal-difference learning;
- policy learning;
- transition-model learning;
- concept learning;
- belief learning;
- automatic Memory consolidation;
- natural-language feedback interpretation;
- learned planning search;
- learned value functions;
- global reward models;
- persistent central learners;
- autonomous background training.
