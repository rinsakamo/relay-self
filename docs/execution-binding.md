# S14 Explicit Admitted-Candidate Execution Binding to PROPOSED Action

## Purpose

S14 qualifies the first explicit transition from a non-authoritative admitted
candidate into the existing Skill and Action owner APIs.

The bounded path is:

```
AdmissionDecision.ADmitted
        +
ControlCandidate
        +
RouteDecision
        +
Current Intent
        +
explicit ExecutionBinding
        ↓
resolve_execution_binding(...)
        ↓
BoundExecutionCandidate
        ↓
SkillExecution.start(...)
        ↓
ActionLifecycle.propose(...)
        ↓
PROPOSED
```

S14 stops at `PROPOSED`.

It never calls `authorize(...)`, `issue(...)`, a World adapter, or a
provider/model.

The separation remains:

```
selection
!= admission
!= binding
!= Skill start
!= Action proposal
!= authorization
!= issue
```

## Why S14 is integration, not cognition

PLAN/HABIT/ROUTE already selected a candidate and S13 already admitted it at
the Current Intent boundary.

S14 performs no preference selection. It validates explicit lineage and an
explicit caller-owned candidate-to-skill/action binding.

Its criterion is therefore:

```
execution.explicit_binding_guard
kind = CONTRACT_GUARD
```

No cognitive orientation is introduced.

## Existing ownership model

S14 reuses the actual repository APIs:

```
SkillExecution.start(...)
ActionLifecycle.propose(...)
```

These are class methods that create the first immutable lifecycle snapshots.
The repository has no separate caller-owned "unstarted SkillExecution" or
"unproposed ActionLifecycle" object.

Accordingly, S14 does not invent parallel pre-start/pre-proposal owners. The
caller supplies explicit identities in `ExecutionBinding`; the existing
constructors create exactly one STARTED Skill snapshot and one PROPOSED Action
snapshot.

## ExecutionBinding

`ExecutionBinding` is immutable declarative metadata:

```
ExecutionBinding(
    binding_id,
    candidate_ref,
    required_intent_id,
    skill_execution_id,
    skill_ref,
    action_id,
    action_ref,
    provenance,
)
```

Example:

```
candidate_ref       = MOVE_AWAY
required_intent_id  = escape-threat
skill_execution_id  = skill-exec-escape-1
skill_ref            = escape-movement
action_id            = action-move-backward-1
action_ref           = MOVE_BACKWARD
```

The object contains no callback, mutable Skill/Action object, dynamic import,
registry key, hidden authority token, model output, or executable closure.

There is no global candidate-to-Skill registry.

## Lineage validation

`resolve_execution_binding(...)` is pure and performs all lineage checks
before owner transition.

It requires the exact:

- RouteDecision;
- ControlCandidate;
- AdmissionDecision;
- S13 ExecutionAdmissionCriterion;
- actual IntentCommitment owner;
- explicit ExecutionBinding.

S14 recomputes the S13 admission result with the supplied route/control/intent
guard and the original admission provenance. The supplied AdmissionDecision
must exactly equal this recomputed result and must be `ADMITTED`.

It then requires:

```
AdmissionDecision.candidate_ref
== ControlCandidate.candidate_ref
== ExecutionBinding.candidate_ref

AdmissionDecision.current_intent_id
== actual Current Intent.intent_id
== ExecutionBinding.required_intent_id
```

Fabricated or mismatched admission lineage fails before Skill start.

## BoundExecutionCandidate

`BoundExecutionCandidate` is a pure immutable boundary witness.

It records only the validated explicit binding and lineage identities /
provenance needed for audit.

Its creation does not start SkillExecution or create ActionLifecycle.

## Prevalidation and partial-transition policy

S14 deliberately separates pure binding resolution from owner transition.

Before calling `SkillExecution.start(...)`,
`start_and_propose_bound_execution(...)` revalidates:

- every binding identifier;
- actual Current Intent presence;
- exact required-intent match;
- transition time;
- transition provenance;
- the exact STARTED SkillEvent shape;
- the exact PROPOSED ActionEvent shape.

Only after these checks pass does S14 invoke:

```
SkillExecution.start(...)
ActionLifecycle.propose(...)
```

in that order.

The newly returned Skill snapshot is fresh, current, STARTED, and associated
with the same actual Current Intent. In the synchronous function there is no
callback or external mutation point between start and propose.

Therefore all known proposal prerequisites are validated before Skill start.
No rollback manager or hidden transaction owner is introduced.

Repository-specific note: because start/propose are constructors for first
snapshots, there is no existing Skill or Action state input for S14 to reset or
replace. Existing STARTED/terminal Skill snapshots and
PROPOSED/AUTHORIZED/ISSUED/terminal Action snapshots are not accepted as S14
inputs at all.

## ExecutionBindingResult

Successful transition returns the actual existing owner snapshots plus a small
immutable audit result:

```
(
    SkillExecution(STARTED),
    ActionLifecycle(PROPOSED),
    ExecutionBindingResult(...),
)
```

`ExecutionBindingResult` stores IDs, refs, state snapshots, and provenance
only. It does not own Skill or Action state.

## Current Intent

The actual `IntentCommitment.current_intent` is reused.

S14 never:

- commits a new Intent;
- replaces Current Intent;
- parses the Intent objective;
- reinterprets the candidate as an Intent.

If the Current Intent no longer matches the admitted/bound intent, execution
binding fails before Skill start.

## Proposal is not authorization

Successful S14 ends exactly at:

```
SkillExecution.state = STARTED
ActionLifecycle.state = PROPOSED
```

and preserves:

```
PROPOSED != AUTHORIZED != ISSUED
```

No authority field or deadline exists on the proposal event.

## S12/S13 failure preservation

S14 cannot bypass earlier gates.

S12 conflict:

```
PLAN -> WAIT
HABIT -> MOVE_AWAY
FAIL_CLOSED -> CONFLICT
-> ControlCandidate=None
-> no ADMITTED
-> no binding
-> no Skill start
-> no Action proposal
```

S13 rejected or undetermined admission is rejected by
`resolve_execution_binding(...)`.

## EXEC_BIND metadata and ON/OFF isolation

EpochPlan requires schedulable work to belong to a capability identity. S14
therefore adds:

```
EXEC_BIND
```

as integration-only metadata.

It is not a cognitive capability and not an authority owner.

It depends on existing `ADMISSION` and `SKL` metadata; SKL retains its
existing CTL dependency.

Operators:

```
execution.resolve_binding
    READ_ONLY

execution.start_and_propose
    OWNER_TRANSITION
```

With ADMISSION ON and EXEC_BIND OFF:

- AdmissionDecision may be ADMITTED;
- binding/proposal work is suppressed;
- no SkillExecution is created;
- no ActionLifecycle is created.

Thus:

```
admission availability != execution-binding availability
```

## Provider, LRN, and MEM boundaries

Provider text such as:

```
Use the escape skill.
Move backward.
```

is not an ExecutionBinding and cannot invoke ActionLifecycle.propose.

No natural-language mapping or model-selected Skill/Action exists.

Likewise:

```
Skill STARTED != positive feedback
Action PROPOSED != successful consequence
```

S14 emits no LearningFeedback and performs no habit reinforcement.

No Skill, Action proposal, binding result, or proposal audit is automatically
written to Memory.

## ActionSupervisor ordering

S14 does not change `coordinate_decision_epoch` or ActionSupervisor.

Qualification verifies an overdue supervised ISSUED Action is processed to
TIMEOUT before explicitly due S14 transition work runs.

S14 owns no clock or deadline.

## No central executive

S14 introduces no persistent object owning cognition, route selection,
admission, Current Intent, Skill, Action, authorization, scheduler, deadlines,
learning, Memory, or World state.

ExecutionBinding is caller-owned declarative metadata.
BoundExecutionCandidate and ExecutionBindingResult are immutable transient
boundary/audit values.

## Deferred functionality

S14 intentionally does not implement:

- Action authorization;
- Action issue;
- physical/World execution;
- dynamic Skill registry;
- model-selected Skill;
- model-selected Action;
- automatic Intent replacement;
- automatic LearningFeedback;
- Memory logging;
- central executive behavior;
- persistent execution queue;
- background retry;
- Minecraft-specific action mapping.
