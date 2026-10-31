# S17 explicit Action-outcome learning-feedback closure

## Purpose

S17 closes one bounded, explicit learning loop without creating a new learner.

The only new semantic bridge is:

```
existing terminal Action
+ exact S16 ActionOutcomeInterpretation
+ explicit ActionFeedbackCriterion
    -> LearningFeedback
```

All retained adaptation remains the existing S10 LRN:

```
LearningFeedback
    -> propose_learning_update(...)
    -> LearningUpdateProposal
    -> explicit LearningUpdateAuthority
    -> commit_learning_update(...)
    -> new LearningPreferenceState
```

S17 stops after that one governed retained update. It does not trigger a second
cognitive/action epoch.

## Distinctions preserved

S17 preserves:

```
WorldConsequence
!= Action outcome
!= LearningFeedback
!= LearningUpdateProposal
!= committed retained update
```

It also preserves:

```
Action OUTCOME != success
Action UNKNOWN != negative feedback
```

Action terminal state alone never chooses a feedback direction.

## ActionFeedbackCriterion

One immutable caller-owned criterion states exactly how one known Action result
should be interpreted for one retained learning target.

Fields:

- criterion_id;
- target_id;
- required_action_id;
- required_binding_id;
- required_action_ref;
- required_action_state;
- required_outcome_disposition;
- required_outcome_reason;
- feedback_direction;
- provenance.

S17 intentionally requires the criterion to name either the existing OUTCOME
or UNKNOWN Action/S16 disposition pair. TIMEOUT and nonterminal states have no
default learning meaning.

The criterion contains the cognitive orientation. Structural identity checks
remain ordinary contract validation.

## Exact lineage

The Action and S16 interpretation must exactly agree on:

- action_id;
- skill_execution_id;
- intent_id.

The explicit criterion then additionally matches:

- exact action_id;
- exact S14 binding_id;
- exact physical action_ref;
- exact terminal Action state;
- exact S16 outcome disposition;
- exact S16 reason_code.

Semantic similarity is never enough.

## Deterministic feedback identity

When an exact criterion matches, S17 produces the existing S10
`LearningFeedback`.

The feedback identity is deterministically derived only from exact structured
identity:

```
criterion_id
target_id
action_id
binding_id
Mineflayer session_id
S16 reason_code
```

No random value, wall-clock time, provider output, or mutable counter
participates.

The existing `LearningFeedback.consequence_ref` points to the deterministic
exact Action-outcome reference built from:

```
action_id
binding_id
session_id
reason_code
```

`LearningFeedbackInterpretation` separately preserves:

- criterion provenance;
- exact S16 ActionOutcomeInterpretation provenance;
- source WorldConsequence provenance;
- S17 interpretation provenance.

## Same outcome, different explicit meaning

The same exact Action OUTCOME may legitimately produce different learning
directions under different explicit criteria.

For example:

```
same observed_execution OUTCOME
+ criterion A -> INCREASE risk_weight

same observed_execution OUTCOME
+ criterion B -> HOLD risk_weight
```

This is intentional evidence that Action semantics and learning semantics remain
separate. There is no global rule such as OUTCOME -> reward.

## UNKNOWN / TIMEOUT / ISSUED

UNKNOWN produces no feedback unless a criterion explicitly names the exact
UNKNOWN disposition/state/reason.

TIMEOUT has no S16 ActionOutcomeInterpretation and therefore produces no
feedback in S17.

An ISSUED Action has no established terminal Action result and cannot produce
feedback. S16 UNAVAILABLE/UNDETERMINED remains feedback-UNDETERMINED with no
`LearningFeedback`.

No absence-of-result learning is implemented.

## Existing S10 LRN is unchanged

S17 does not duplicate:

- LearningFeedback;
- LearningPreferenceState;
- LearningUpdateRule;
- LearningUpdateProposal;
- LearningUpdateAuthority;
- propose_learning_update(...);
- commit_learning_update(...).

Qualification reuses the exact S10 semantics:

```
risk_weight = 3, revision 0
+ explicit INCREASE feedback
+ step = 1
    -> pure proposal: 4, expected revision 0
+ explicit granted exact-target authority
    -> retained state: 4, revision 1
```

Proposal creation does not mutate the owner.

Missing/denied/wrong-target authority, stale proposal, and feedback replay keep
their existing fail-closed S10 behavior.

## Replay

S17 adds no replay ledger.

Same exact outcome + same exact criterion deterministically produces the same
feedback identity.

After that feedback is committed, the existing S10 owner rejects immediate
feedback replay. Old proposals are rejected by exact revision/value/bounds
checks.

## FEEDBACK metadata

EpochPlan scheduling uses one narrow integration-only metadata ID:

```
FEEDBACK
```

It depends on `ACTION_OUTCOME` and does not depend on LRN.

This is deliberate:

```
Action outcome availability
!= feedback availability
!= retained adaptation availability
```

The single operator is:

```
learning.interpret_action_outcome_feedback
effect = READ_ONLY
```

Criterion:

```
learning.explicit_outcome_feedback_orientation
kind = COGNITIVE_ORIENTATION
```

No duplicate LRN propose/apply operators are added.

## ON/OFF isolation

### FEEDBACK OFF, LRN ON

With Action closure available but FEEDBACK disabled:

- terminal Action remains available;
- no LearningFeedback is produced;
- retained LearningPreferenceState is unchanged.

### FEEDBACK ON, LRN OFF

With FEEDBACK enabled:

- LearningFeedback may be produced;
- LRN proposal/apply work remains suppressed;
- retained LearningPreferenceState remains unchanged.

Turning LRN off never deletes retained state.

## HABIT / PLAN / BLF / MEM / Skill boundaries

S17 changes only one explicit LearningPreferenceState when the existing S10
commit is explicitly invoked.

It does not:

- reinforce HabitRepertoire;
- alter HabitSelection;
- mutate PlanningCriterion or PlanSelection;
- inject the learned value into PLAN;
- create BeliefEvidence or rerun BLF;
- write outcome/feedback/proposal/commit into PersistentCognition Memory;
- close or modify SkillExecution;
- replace Current Intent.

A future epoch may explicitly read retained learning state. S17 does not start
that epoch.

## Provider boundary

ProviderExpression cannot become:

- ActionOutcomeInterpretation;
- ActionFeedbackCriterion;
- LearningFeedback;
- LearningUpdateAuthority.

Natural-language claims such as "that worked well", "increase the risk weight",
or "learn from this" have no feedback or update authority.

No model/provider call is required anywhere in the deterministic S17 loop.

## No autonomous reentry

The complete qualification executes exactly one bounded cognition-to-action
path, one explicit Action closure, one explicit feedback interpretation, and
one explicit governed retained update.

There is no:

- second ATT/PLAN pass;
- next Action proposal;
- autonomous agent loop;
- background learner;
- retry queue.

## Live-field status

The frozen S15/S16 limitation remains:

```
LIVE FIELD = NOT RUN / BLOCKED
blocker = genuine Minecraft endpoint unavailable
```

S17 closes the loop only on deterministic structured test-apparatus evidence.
It does not claim a live Minecraft learning loop.

## Deferred functionality

S17 intentionally does not implement autonomous reentry, continuous agent
loops, RL/TD learning, generic reward models, policy learning, Habit
reinforcement, concept/belief/model learning, automatic PLAN mutation, Memory
logging, natural-language reward interpretation, global or temporal credit
assignment, or live-field claims without a genuine receipt.
