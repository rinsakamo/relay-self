# Stateless Epoch Plans

## Purpose

S3 turns enabled capability metadata plus explicitly admitted due work into one immutable execution plan.

The plan is stateless. It does not own a clock, cognition, intent, world state, belief, memory, skill state, or action state.

The execution shape is:

```
CapabilityPlan
+ CapabilityDescriptorSet
+ caller/source-owned due items
+ explicit concrete bindings
-> immutable EpochPlan
-> existing deadline-first decision coordinator
```

No descriptor string is dynamically imported or executed.

## Due work

An `EpochWorkItem` records:

- `work_id`;
- `operator_id`;
- `trigger_ref`.

The caller/source owns why the work is due. S3 does not infer relevance, priority, urgency, or a clock from the descriptor.

The tuple order supplied by the caller is preserved as the inner execution order.

Disabled capability work is not executed. It is retained in `EpochPlan.suppressed` so capability OFF is visible rather than silently disappearing.

## Explicit bindings

An `EpochBinding` associates one due `work_id` with one explicitly supplied callable.

The binding is separate from descriptor metadata:

```
OperatorDescriptor.implementation_ref
  = audit reference only

EpochBinding.invoke
  = explicit caller-supplied concrete integration
```

S3 never auto-imports `implementation_ref`.

Bindings must exactly correspond to enabled due work. Bindings for suppressed or nonexistent work fail closed.

## Ordering constraints

The outer `coordinate_decision_epoch` remains authoritative for the first ordering rule:

```
Action supervision / due lifecycle deadlines
  BEFORE
planned inner capability work
```

Within the inner plan:

- caller/source order is preserved;
- the outer coordination operator itself cannot be scheduled as inner work;
- at most one cognition call is admitted per epoch;
- the cognition call must be the final inner step.

These restrictions match the currently admitted RelaySelf decision-epoch seam rather than inventing a more general scheduler.

## Deterministic / owner-transition work

For non-cognition steps, the explicit binding executes in plan order and must return `None`.

A binding may call an existing owner transition such as:

```
PersistentCognition.retain_memory(...)
SkillExecution.start(...)
ActionLifecycle.propose(...)
```

Ownership remains with that existing object. The plan does not absorb the state merely because it ordered the operation.

## Cognition work

A cognition step does not directly call a descriptor reference.

Its binding returns a `CognitionInvocation`:

```
request
+ explicitly supplied runner
```

The existing `coordinate_decision_epoch` then invokes that runner exactly once through its cognition seam.

This supports concrete existing surfaces such as:

```
RelayEngine.__call__   # bounded cognition
RelayEngine.open       # open/TALK cognition
```

without teaching S3 how to discover or own a RelayEngine.

A raw arbitrary non-`None` value from a cognition binding is rejected. A deterministic binding likewise cannot smuggle a cognition request by returning a value.

## Capability ON/OFF behavior

S3 is the first slice where capability selection changes admitted runtime work.

For example:

```
MEM ON
+ due mem.retain
+ explicit binding
-> mem.retain appears in EpochPlan.steps

MEM OFF
+ same due mem.retain
-> mem.retain appears in EpochPlan.suppressed
-> no binding is required or permitted
```

OFF changes route availability. It does not delete retained Memory or mutate any other owner.

## What S3 still does not provide

S3 is not:

- a persistent Scheduler;
- a global event loop;
- a priority learner;
- a relevance classifier;
- a trigger detector;
- a world model;
- a cognition registry;
- a generic capability implementation;
- an LLM-per-tick loop.

The caller remains responsible for producing admitted due work from concrete owner state, evidence, deadlines, or experiment-local logic.

## Boundary toward S4

S4 can now qualify concrete capability profiles over existing paths, especially:

- MEM only;
- CTL only;
- CTL + SKL;
- TALK;
- MEM + CTL + SKL;
- MEM + TALK.

Qualification should demonstrate that toggling capabilities changes admitted routes while preserving existing ownership, action authority, consequence observation, and cognition call-count guarantees.


## S4 continuation

S4 qualifies the existing-profile surface described in
[`capability-profile-qualification.md`](capability-profile-qualification.md).

It does not generalize the planner. It tests concrete current MEM / CTL / SKL / TALK
bindings and verifies selective ON/OFF route effects while preserving authority boundaries.
