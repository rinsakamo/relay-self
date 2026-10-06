# S12 Stateless Explicit PLAN/HABIT Route Adjudication

## Purpose

S12 integrates already-qualified cognitive routes without adding a central
executive. It answers one bounded question:

```
Given already-produced PLAN and/or HABIT selections,
which structured candidate reference is admitted by this explicit route criterion?
```

S12 does not rerun PLAN or HABIT and does not inspect raw evidence. It does not
perform ATT, BLF, CNC, PRD, learning, memory retention, intent commitment,
Skill execution, Action proposal, authorization, or issue.

The bounded route is:

```
PlanSelection ----\
                   -> adjudicate_routes -> RouteDecision
HabitSelection ---/                         |
                                             -> pure ControlCandidate projection
```

`RouteDecision` and `ControlCandidate` are non-authoritative metadata.

## Why ROUTE is integration metadata, not a cognitive capability

EpochPlan requires schedulable operators to belong to an explicit
`CapabilitySpec`. S12 therefore adds the narrow identifier `ROUTE` only so
route work can be explicitly enabled or suppressed.

`ROUTE` has:

- no state scopes;
- no owner;
- no scheduler;
- no background loop;
- no history;
- no hidden policy;
- no provider/model call;
- no ActionSupervisor ownership.

It is not an EXEC, BRAIN, CORE, GLOBAL_CTL, or central executive.

## RouteCandidate

A `RouteCandidate` is an immutable projection containing only:

- `source = PLAN | HABIT`;
- structured `candidate_ref`;
- stable `source_ref`;
- source provenance.

Only `PlanSelectionStatus.SELECTED` can produce a PLAN route candidate.
PLAN `TIED` and `UNDETERMINED` produce no candidate.

Only `HabitSelectionStatus.SELECTED` can produce a HABIT route candidate.
HABIT `TIED` and `NO_MATCH` produce no candidate.

An unresolved source is not a negative vote.

## RouteCriterion

`RouteCriterion` is explicit and immutable:

```
RouteCriterion(
    criterion_id=...,
    conflict_policy=FAIL_CLOSED | PLAN_WINS | HABIT_WINS,
    allow_single_source=True | False,
)
```

There is no implicit PLAN dominance, HABIT dominance, recency rule, confidence
rule, caller-order tie breaker, usage counter, or natural-language policy
extraction.

`route.explicit_arbitration_orientation` is a
`COGNITIVE_ORIENTATION` descriptor because it determines which otherwise
valid selected route is admitted. Input shape and consistency checks remain
contract validation.

## RouteDecision semantics

With one usable route and `allow_single_source=True`:

```
PLAN only  -> SELECTED(PLAN)
HABIT only -> SELECTED(HABIT)
```

With one usable route and `allow_single_source=False`:

```
-> UNDETERMINED
```

With two usable routes selecting the same `candidate_ref`:

```
-> AGREED(candidate)
```

Agreement grants no additional authority. It is not two votes and does not
become Current Intent or Action authorization.

With two different candidates:

```
FAIL_CLOSED -> CONFLICT, selected=None
PLAN_WINS   -> SELECTED(PLAN)
HABIT_WINS  -> SELECTED(HABIT)
```

Explicit override decisions retain both route candidates so the disagreement is
not erased.

With no usable candidate:

```
-> NO_CANDIDATE
```

For example, PLAN `UNDETERMINED` plus HABIT `NO_MATCH` is
`NO_CANDIDATE`. No provider fallback is attempted.

## Fail-closed conflict boundary

The primary S12 conflict qualification is:

```
PLAN  -> WAIT
HABIT -> MOVE_AWAY
criterion = FAIL_CLOSED

RouteDecision -> CONFLICT
ControlCandidate -> None
```

This produces no:

- Current Intent mutation;
- SkillExecution start;
- Action proposal;
- Action authorization;
- Action issue;
- LearningFeedback;
- Memory write.

Therefore unresolved cognitive disagreement has no execution authority.

## Agreement integration

The deterministic agreement qualification is:

```
PLAN  -> MOVE_AWAY
HABIT -> MOVE_AWAY

RouteDecision -> AGREED(MOVE_AWAY)
ControlCandidate -> MOVE_AWAY
```

The ControlCandidate is still only a structured candidate suitable for a later
explicit execution-authority path.

S12 intentionally stops there.

## Full deterministic branch integration

S12 qualifies:

```
ATT
 ↓
BLF
 ↓
CNC
 ├─> PRD WAIT -> comparison_score=8
 │    PRD MOVE_AWAY -> comparison_score=3
 │    PLAN MINIMIZE -> MOVE_AWAY
 └─> HABIT cue nearby_threat -> MOVE_AWAY
                         \
                          -> ROUTE -> AGREED MOVE_AWAY
```

ATT, BLF, CNC, PRD, PLAN, HABIT, and ROUTE all run as explicit immutable
EpochPlan bindings. The integrated route performs zero provider/model calls.

The same upstream structure is also qualified with PLAN preferring WAIT while
HABIT retains MOVE_AWAY. Under FAIL_CLOSED the result is CONFLICT and no
ControlCandidate exists.

## Relation to CTL

The existing CTL authority remains unchanged:

- `coordinate_decision_epoch` services `ActionSupervisor` first;
- callers own why work is due;
- bounded RelayEngine cognition remains a separate optional seam;
- CTL does not become a route owner.

S12 adds only `control_candidate_from_route_decision`, a pure projection from
`SELECTED` or `AGREED` decisions. It does not call
`IntentCommitment.commit`, `SkillExecution.start`, or
`ActionLifecycle.propose`.

No new CTL is introduced and S12 does not own epoch deadlines.

## Route decision versus Intent, Skill, and Action

S12 preserves:

```
RouteDecision != Current Intent
RouteDecision != SkillExecution
RouteDecision != Action proposal
RouteDecision != Action authorization
RouteDecision != Action issue
```

Likewise:

```
ControlCandidate != Current Intent
ControlCandidate != SkillExecution
ControlCandidate != Action proposal
```

A later explicit authority path may consume an admitted candidate, but that is
outside S12.

## Learning boundary

S12 preserves:

```
RouteDecision != LearningFeedback
CONFLICT != negative feedback
AGREED != positive feedback
```

There is no automatic habit reinforcement, PLAN preference update, or learned
arbitration policy. S10 LRN remains separate and authority governed.

## Memory boundary

Route agreement, conflict, selected candidates, and ControlCandidate values are
not automatically stored. S12 never calls
`PersistentCognition.retain_memory()`.

## Provider boundary

Provider text such as:

```
Follow the habit this time.
Do whatever the plan says.
```

is not a `RouteCriterion`.

S12 performs no natural-language route-policy extraction, no model arbitration,
and no provider fallback.

## ON/OFF semantics

With ROUTE ON, explicit due work plus exact binding plus explicit route inputs
and criterion can produce one `RouteDecision`.

With ROUTE OFF, route work is suppressed while PLAN and HABIT may still execute
and retain their independent results.

Therefore:

```
candidate availability != arbitration availability
```

Disabling ROUTE does not delete a HabitRepertoire or any upstream result.

## Descriptor

```
route.adjudicate
-> relay_self.route_adjudication.adjudicate_routes

effect = READ_ONLY
hidden_persistent_state = false
writes = transient.route_decision
```

Criterion:

```
route.explicit_arbitration_orientation
kind = COGNITIVE_ORIENTATION
```

`implementation_ref` remains audit metadata only. EpochPlan performs no
dynamic import or hidden dispatch.

## No central executive

S12 introduces no object that owns Memory, Belief, Concept, Prediction, Plan,
Habit, Current Intent, Skill state, Action authority, scheduler timing, or
learning state.

The adjudicator receives immutable outputs and returns an immutable decision.
There is no persistent route owner, universal arbiter, background polling loop,
or hidden global policy.

## Deferred functionality

S12 intentionally defers:

- central executive behavior;
- persistent arbitration state;
- learned arbitration policy;
- model-based arbitration;
- implicit conflict resolution;
- automatic Intent commitment;
- automatic Skill start;
- Action proposal;
- Action authorization;
- Action issue;
- automatic LearningFeedback;
- automatic habit reinforcement;
- Memory logging;
- background route polling;
- Minecraft-specific route policy;
- automatic execution of ControlCandidate.
