# S13 Explicit Control-Candidate Admission at the Existing Authority Boundary

## Purpose

S13 qualifies the boundary between a non-authoritative cognitive route result
and later execution-authority handling.

The qualified path is:

```
RouteDecision
     ↓
ControlCandidate
     ↓
explicit execution-admission guard
     ↓
AdmissionDecision
```

S13 stops at `AdmissionDecision`.

It does not commit or replace Current Intent, start SkillExecution, map a
candidate to a Skill, propose Action, authorize Action, issue Action, mutate
Memory, invoke LRN, or call a provider/model.

The core invariant is:

```
selection != admission != commitment != proposal != authorization != issue
```

## Why S13 is authority-boundary integration, not cognition

PLAN, HABIT, and ROUTE already determined which structured candidate reached
the control boundary. S13 does not choose among alternatives.

Admission asks only whether that already-selected candidate satisfies explicit
entry guards for later execution handling.

Therefore:

```
admission.explicit_execution_guard
kind = CONTRACT_GUARD
```

S13 adds no `COGNITIVE_ORIENTATION`.

## Existing authority is reused

The existing `IntentCommitment` remains the sole owner of Current Intent.
S13 reads `IntentCommitment.current_intent`; it does not construct a parallel
intent owner or parse the free-text intent objective.

The existing `ActionSupervisor` remains the sole owner of supervised
in-flight Action deadline processing.

The existing `coordinate_decision_epoch` remains unchanged and continues to
service ActionSupervisor before caller-owned decision work.

No second CTL is introduced.

## ADMISSION metadata

EpochPlan requires each schedulable work item to name a capability. Rather than
altering CTL semantics, S13 introduces the narrow metadata identifier:

```
ADMISSION
```

It is integration metadata only, not a cognitive capability and not an
authority owner.

It has:

- no state scopes;
- no persistent owner;
- no history;
- no retry counter;
- no queue;
- no clock or deadline;
- no scheduler;
- no executable callback;
- no provider/model call.

## ControlCandidate and RouteDecision chain

Admission requires both the `ControlCandidate` and the exact
`RouteDecision` from which it claims to have been projected.

S13 recomputes the pure S12 control projection and requires exact equality.
This preserves and validates:

- candidate_ref;
- selected source;
- S12 route status;
- route criterion identity;
- route provenance.

A mismatched or fabricated ControlCandidate is rejected.

Provenance is audit lineage only. Provenance never grants permission.

## ExecutionAdmissionCriterion

The qualified guard is intentionally narrow:

```
ExecutionAdmissionCriterion(
    criterion_id=...,
    policy=CURRENT_INTENT_ALLOW_LIST,
    required_intent_id=...,
    allowed_candidate_refs=(...),
)
```

No intent objective text is parsed.

No candidate preference is inferred.

No wildcard, confidence, recency, model output, or hidden policy exists.

The caller explicitly names both the required Current Intent identity and the
candidate references allowed under that authority context.

## AdmissionDecision

S13 uses no separate `AdmittedExecutionCandidate`; the immutable
`AdmissionDecision(status=ADMITTED)` is sufficient and avoids inventing a
second candidate type.

The result records:

- `ADMITTED | REJECTED | UNDETERMINED`;
- candidate_ref;
- actual RouteDecision status;
- selected route source when one exists;
- route criterion identity;
- ControlCandidate criterion identity;
- admission criterion identity;
- observed Current Intent identity when present;
- structured reason;
- control, route, and admission provenance.

The result contains no callable and owns no downstream object.

## Exact admission semantics

After validating the exact S12 route/control chain:

```
no Current Intent
    -> UNDETERMINED / MISSING_CURRENT_INTENT

Current Intent exists
but intent_id != required_intent_id
    -> REJECTED / CURRENT_INTENT_MISMATCH

Current Intent matches
but candidate_ref not in allowed_candidate_refs
    -> REJECTED / CANDIDATE_NOT_ALLOWED

Current Intent matches
and candidate_ref is explicitly allowed
    -> ADMITTED
```

Missing authority context never defaults to admission.

## S12 conflict preservation

S13 cannot solve S12 disagreement.

For:

```
PLAN -> WAIT
HABIT -> MOVE_AWAY
FAIL_CLOSED
-> RouteDecision.CONFLICT
-> ControlCandidate=None
```

normal admission is not invoked because there is no ControlCandidate.

If a caller fabricates a ControlCandidate and presents it alongside a
CONFLICT, NO_CANDIDATE, or UNDETERMINED RouteDecision, S13 returns:

```
REJECTED / ROUTE_NOT_ADMISSIBLE
```

There is no admission-policy override of unresolved S12 state.

## Current Intent interaction

A valid admission example is:

```
Current Intent = escape-threat
ControlCandidate = MOVE_AWAY
criterion requires escape-threat
criterion allows MOVE_AWAY

-> ADMITTED
```

The Current Intent remains `escape-threat` with unchanged event history.

A negative example is:

```
Current Intent = hold-position
criterion requires escape-threat
ControlCandidate = MOVE_AWAY

-> REJECTED / CURRENT_INTENT_MISMATCH
```

S13 does not create `escape-threat`, rewrite `hold-position`, or request
reconsideration.

## Admission is not Skill or Action execution

S13 preserves:

```
ADMITTED != Current Intent
ADMITTED != SkillExecution
ADMITTED != Action proposal
ADMITTED != Action authorization
ADMITTED != Action issue
```

There is no candidate_ref-to-Skill mapping in S13.

Existing PROPOSED, AUTHORIZED, and ISSUED Action snapshots remain unchanged.

## CTL and deadline ordering

Admission can run as ordinary deterministic READ_ONLY EpochPlan work.

`coordinate_planned_epoch` still delegates to the existing
`coordinate_decision_epoch`, which services ActionSupervisor first.

S13 qualification explicitly verifies that a due Action deadline becomes
TIMEOUT before the admission binding executes.

Admission owns no clock or deadline.

## Full deterministic qualification

S13 qualifies:

```
ATT
 ↓
BLF
 ↓
CNC
 ├─> PRD WAIT -> comparison_score=8
 │    PRD MOVE_AWAY -> comparison_score=3
 │    PLAN MINIMIZE -> MOVE_AWAY
 └─> HABIT -> MOVE_AWAY
            ↓
ROUTE -> AGREED(MOVE_AWAY)
            ↓
ControlCandidate(MOVE_AWAY)
            ↓
ADMISSION guard for Current Intent escape-threat
            ↓
ADMITTED
```

Every stage is deterministic and the whole path performs zero provider/model
calls.

S13 stops at ADMITTED.

## ON/OFF isolation

With ROUTE ON and ADMISSION OFF:

- RouteDecision exists;
- ControlCandidate exists;
- admission work is suppressed;
- AdmissionDecision does not exist.

Therefore:

```
cognitive candidate availability != authority admission availability
```

The upstream route result remains intact.

## Provider boundary

Provider text such as:

```
Yes, do it.
That action is safe.
```

is not an `ExecutionAdmissionCriterion`, authority token, Current Intent,
Skill start, or Action authorization.

S13 performs no natural-language permission extraction and has no provider/model
fallback.

## LRN and MEM boundaries

S13 preserves:

```
ADMITTED != positive LearningFeedback
REJECTED != negative LearningFeedback
```

No admission result updates learning state or admission policy.

AdmissionDecision, accepted candidates, and rejected candidates are not
automatically retained in Memory.

Auditability comes from immutable result data and provenance, not implicit MEM
writes.

## Descriptor

Operator:

```
execution.admit_candidate
-> relay_self.execution_admission.admit_control_candidate

effect = READ_ONLY
hidden_persistent_state = false
writes = transient.admission_decision
```

Criterion:

```
admission.explicit_execution_guard
kind = CONTRACT_GUARD
```

## No central executive

S13 introduces no persistent object owning candidate selection, Intent, Skill,
Action, authorization, scheduler timing, Memory, Belief, Learning, arbitration,
or World state.

Admission evaluates the boundary. It owns neither side.

## Deferred functionality

S13 intentionally defers:

- automatic Intent commitment or replacement;
- candidate-to-Skill mapping;
- automatic Skill start;
- Action proposal;
- Action authorization;
- Action issue;
- central executive behavior;
- persistent admission state;
- learned admission policy;
- model/provider permission;
- automatic LRN feedback;
- automatic Memory logging;
- background execution queue;
- Minecraft-specific action policy.
